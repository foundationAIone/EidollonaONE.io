from __future__ import annotations

from collections import OrderedDict, defaultdict
from pathlib import Path
from threading import RLock
from typing import Dict, Any, List, Optional, Callable, Tuple
import hashlib
import json
import os
import time
import uuid

# ----------------------------
# Tunables & global singletons
# ----------------------------

MAX_WIDGETS = 200
# Soft caps for stored state (JSON) and daily patch logs
MAX_STATE_BYTES = 2_000_000  # ~2 MB
MAX_PATCH_FILE_BYTES = 5_000_000  # ~5 MB, rotate after
IDEMP_CACHE_SIZE = 4096
PUSH_MIN_INTERVAL_MS_DEFAULT = 150

# Idempotency cache: O(1) membership with bounded size
_IDEMP_CACHE: "OrderedDict[str, float]" = OrderedDict()
_LAST_PUSH_AT = defaultdict(float)

_GLOBAL_STORE: Optional["DashboardStore"] = None
_BROADCAST: Optional[Callable[[Dict[str, Any]], None]] = None
_LOCK = RLock()  # guards globals & store writes


# ----------------------------
# Helpers
# ----------------------------


def _now() -> float:
    return time.time()


def _atomic_write(path: Path, data: bytes) -> None:
    """Durable-ish write to avoid torn state files."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _sha256(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _gen_widget_id(version_hint: Optional[int] = None) -> str:
    # Stable, readable, and collision-resistant enough for UI
    base = f"w_{version_hint or 0}_{uuid.uuid4().hex[:8]}"
    return base


# ----------------------------
# Rate-limit & idempotency
# ----------------------------


def is_idempotent(key: Optional[str]) -> bool:
    if not key:
        return False
    with _LOCK:
        if key in _IDEMP_CACHE:
            return True
        _IDEMP_CACHE[key] = _now()
        # Drop oldest if we exceed the bound
        while len(_IDEMP_CACHE) > IDEMP_CACHE_SIZE:
            _IDEMP_CACHE.popitem(last=False)
    return False


def push_allowed(
    actor: str, min_interval_ms: int = PUSH_MIN_INTERVAL_MS_DEFAULT
) -> bool:
    now = _now()
    with _LOCK:
        last = _LAST_PUSH_AT[actor]
        if (now - last) * 1000.0 < float(min_interval_ms):
            return False
        _LAST_PUSH_AT[actor] = now
    return True


# ----------------------------
# Store
# ----------------------------


class DashboardStore:
    """
    Thread-safe, durable widget store with:
      - atomic snapshots
      - daily JSONL patch streams
      - rotation/compaction safeguards
      - broadcast hooks
    """

    def __init__(self, state_dir: Path):
        self.dir = state_dir
        self.dir.mkdir(parents=True, exist_ok=True)

        self.state_path = self.dir / "dashboard_state.json"
        self.patch_dir = self.dir / "dashboard_patches"
        self.patch_dir.mkdir(parents=True, exist_ok=True)

        self.version = 0
        self.widgets: List[Dict[str, Any]] = []
        self._index: Dict[str, int] = {}  # widget_id -> list index
        self._lock = RLock()

        self._load()

    # -------- IO & rotation --------

    def _load(self) -> None:
        with self._lock:
            if not self.state_path.exists():
                self.widgets = []
                self.version = 0
                self._rebuild_index()
                return
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                self.widgets = list(data.get("widgets", []))
                self.version = int(data.get("version", 0))
                self._rebuild_index()
            except Exception:
                # Corrupt state: preserve a copy, reset cleanly
                try:
                    bad = self.state_path.with_suffix(".corrupt.json")
                    self.state_path.replace(bad)
                except Exception:
                    pass
                self.widgets = []
                self.version = 0
                self._index.clear()

    def snapshot(self) -> None:
        with self._lock:
            payload = {"version": self.version, "widgets": self.widgets}
            raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            if len(raw) > MAX_STATE_BYTES:
                # Minimal safety: drop oldest until we fit, then write
                self._shrink_to_fit()
                payload = {"version": self.version, "widgets": self.widgets}
                raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            try:
                _atomic_write(self.state_path, raw)
            except Exception:
                pass  # best-effort; router already returns 200 on success path

    def _patch_file(self) -> Path:
        day = time.strftime("%Y%m%d")
        return self.patch_dir / f"patches_{day}.jsonl"

    def _rotate_patch_if_needed(self, pfile: Path) -> Path:
        try:
            if pfile.exists() and pfile.stat().st_size >= MAX_PATCH_FILE_BYTES:
                ts = time.strftime("%H%M%S")
                rotated = pfile.with_name(pfile.stem + f"_{ts}.jsonl")
                pfile.replace(rotated)
        except Exception:
            pass
        return self._patch_file()

    def record_patch(self, patch: Dict[str, Any]) -> None:
        with self._lock:
            p = dict(patch)
            p["ts"] = _now()
            p["entry_hash"] = _sha256(p)
            try:
                pfile = self._rotate_patch_if_needed(self._patch_file())
                with open(pfile, "a", encoding="utf-8") as f:
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # Audit (best-effort)
            try:
                from common.audit_chain import append_event as _audit

                _audit(
                    actor="dashboard",
                    action="patch",
                    ctx={"version": self.version},
                    payload=p,
                )
            except Exception:
                pass

    # -------- Core ops --------

    def _rebuild_index(self) -> None:
        self._index = {}
        for i, w in enumerate(self.widgets):
            wid = str(w.get("id") or "")
            if wid:
                self._index[wid] = i

    def _shrink_to_fit(self) -> None:
        # Keep most recent widgets (assume append order), respect MAX_WIDGETS first
        if len(self.widgets) > MAX_WIDGETS:
            self.widgets = self.widgets[-MAX_WIDGETS:]
        # If still too big on bytes, drop from the front until serialized fits
        while True:
            raw = json.dumps(
                {"version": self.version, "widgets": self.widgets}, ensure_ascii=False
            ).encode("utf-8")
            if len(raw) <= MAX_STATE_BYTES or not self.widgets:
                break
            self.widgets.pop(0)
        self._rebuild_index()

    def upsert_add(self, w: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Add a widget (append; evict oldest if at cap).
        Returns (widget_id, replaced=False).
        """
        with self._lock:
            wid = str(w.get("id") or _gen_widget_id(self.version + 1))
            w["id"] = wid
            if len(self.widgets) >= MAX_WIDGETS:
                # evict oldest
                evicted = self.widgets.pop(0)
                self._index.pop(str(evicted.get("id")), None)
            self.widgets.append(w)
            self._index[wid] = len(self.widgets) - 1
            self.version += 1
            self.record_patch(
                {
                    "op": "add",
                    "widget": wid,
                    "type": w.get("type"),
                    "version": self.version,
                }
            )
            return wid, False

    def replace(self, target_id: str, w: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Replace widget by id; if not found, append it.
        Returns (widget_id, replaced_flag).
        """
        with self._lock:
            wid = str(w.get("id") or target_id or _gen_widget_id(self.version + 1))
            w["id"] = wid
            if target_id in self._index:
                idx = self._index[target_id]
                self.widgets[idx] = w
                # index might change if ids differ
                self._index.pop(target_id, None)
                self._index[wid] = idx
                replaced = True
            else:
                if len(self.widgets) >= MAX_WIDGETS:
                    evicted = self.widgets.pop(0)
                    self._index.pop(str(evicted.get("id")), None)
                self.widgets.append(w)
                self._index[wid] = len(self.widgets) - 1
                replaced = False
            self.version += 1
            self.record_patch(
                {
                    "op": "replace",
                    "widget": wid,
                    "type": w.get("type"),
                    "version": self.version,
                }
            )
            return wid, replaced

    def remove(self, target_id: str) -> bool:
        with self._lock:
            if target_id not in self._index:
                return False
            idx = self._index.pop(target_id)
            self.widgets.pop(idx)
            # rebuild index (simple & safe)
            self._rebuild_index()
            self.version += 1
            self.record_patch(
                {"op": "remove", "widget": target_id, "version": self.version}
            )
            return True

    def clear(self) -> None:
        with self._lock:
            self.widgets = []
            self._index.clear()
            self.version += 1
            self.record_patch({"op": "clear", "version": self.version})


# ----------------------------
# Singletons & broadcast
# ----------------------------


def get_store(state_dir: Path) -> DashboardStore:
    global _GLOBAL_STORE
    with _LOCK:
        if _GLOBAL_STORE is None:
            _GLOBAL_STORE = DashboardStore(state_dir)
        return _GLOBAL_STORE


def set_broadcaster(fn: Callable[[Dict[str, Any]], None]) -> None:
    global _BROADCAST
    with _LOCK:
        _BROADCAST = fn


def broadcast(payload: Dict[str, Any]) -> None:
    try:
        fn = None
        with _LOCK:
            fn = _BROADCAST
        if fn:
            fn(payload)
    except Exception:
        # Never let a UI subscriber crash the backend path
        pass
