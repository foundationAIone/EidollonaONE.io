from __future__ import annotations
import os
import json
import time
import hashlib
import hmac
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Iterable

# === Config ===
_DEFAULT_AUDIT_DIR = Path("web_planning/backend/state/audit")
AUDIT_DIR = Path(os.getenv("EID_AUDIT_DIR", str(_DEFAULT_AUDIT_DIR)))
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def _audit_dir() -> Path:
    """Return the current audit directory, refreshing from environment."""
    global AUDIT_DIR
    env_dir = os.getenv("EID_AUDIT_DIR")
    target = Path(env_dir) if env_dir else _DEFAULT_AUDIT_DIR
    if target != AUDIT_DIR:
        target.mkdir(parents=True, exist_ok=True)
        AUDIT_DIR = target
    else:
        target.mkdir(parents=True, exist_ok=True)
    return AUDIT_DIR

# Keep legacy readers working: JSONL lines remain dicts, we only ADD fields.
# Files are per-day: audit_YYYY-MM-DD.jsonl
# Each entry contains: ts, actor, action, ctx, payload_digest, prev_hash, entry_hash, v
# v is a schema/minor version to help future changes.
SCHEMA_VERSION = "1.0"

# Consent keys: only store salted hashes
CONSENT_SALT = os.getenv("EID_CONSENT_SALT", "change-me-IN-ENV").encode("utf-8")


def _today_str(ts: Optional[float] = None) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts or time.time()))


def _file_for(date_str: str) -> Path:
    return _audit_dir() / f"audit_{date_str}.jsonl"


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_obj(obj: Any) -> str:
    # stable json encoding for digest
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(blob)


def consent_hash(consent_key: str) -> str:
    # salted HMAC-SHA256; one-way
    return hmac.new(
        CONSENT_SALT, consent_key.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _read_last_entry_hash(date_str: str) -> str:
    fp = _file_for(date_str)
    if not fp.exists():
        return "GENESIS"
    last = "GENESIS"
    try:
        with fp.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    last = rec.get("entry_hash", last)
                except Exception:
                    # Skip malformed lines; verifier will catch later
                    pass
    except Exception:
        return "GENESIS"
    return last or "GENESIS"


@dataclass
class AuditEvent:
    ts: float
    actor: str
    action: str
    ctx: Dict[str, Any]
    payload_digest: str  # caller computes: _sha256_obj(minimal_payload)
    prev_hash: str
    entry_hash: str
    v: str = SCHEMA_VERSION


def append_event(
    actor: str,
    action: str,
    ctx: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
    date_override: Optional[str] = None,
) -> str:
    """
    Append an event and return entry_hash.
    ctx: non-sensitive context (run_id, plan_id, endpoint, SAFE_MODE, etc.)
    payload: MINIMAL fields to represent the event; caller should NOT include secrets.
    """
    date_str = date_override or _today_str()
    prev = _read_last_entry_hash(date_str)
    ts = time.time()
    ctx = ctx or {}
    payload = payload or {}
    payload_d = _sha256_obj(payload)
    # Canonical content to hash entry
    content = {
        "ts": ts,
        "actor": actor,
        "action": action,
        "ctx": ctx,
        "payload_digest": payload_d,
        "prev_hash": prev,
        "v": SCHEMA_VERSION,
    }
    entry_h = _sha256_obj(content)
    event = AuditEvent(
        ts=ts,
        actor=actor,
        action=action,
        ctx=ctx,
        payload_digest=payload_d,
        prev_hash=prev,
        entry_hash=entry_h,
    )
    fp = _file_for(date_str)
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
    return entry_h


# === Verification ===


@dataclass
class VerifyResult:
    ok: bool
    date: str
    first_bad_index: Optional[int]
    reason: Optional[str]
    entries_checked: int


def _iter_entries(date_str: str) -> Iterable[Dict[str, Any]]:
    fp = _file_for(date_str)
    if not fp.exists():
        return []
    try:
        with fp.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except Exception:
                    yield {"_corrupt_line": line}
    except Exception:
        return []


def verify_day(date_str: str) -> VerifyResult:
    prev = "GENESIS"
    idx = -1
    checked = 0
    for idx, rec in enumerate(_iter_entries(date_str)):
        checked += 1
        if "_corrupt_line" in rec:
            return VerifyResult(False, date_str, idx, "malformed_json", checked)
        # Recompute entry hash deterministically
        canon = {
            "ts": rec.get("ts"),
            "actor": rec.get("actor"),
            "action": rec.get("action"),
            "ctx": rec.get("ctx", {}),
            "payload_digest": rec.get("payload_digest"),
            "prev_hash": rec.get("prev_hash"),
            "v": rec.get("v", SCHEMA_VERSION),
        }
        calc = _sha256_obj(canon)
        if rec.get("prev_hash") != prev:
            return VerifyResult(False, date_str, idx, "prev_hash_mismatch", checked)
        if rec.get("entry_hash") != calc:
            return VerifyResult(False, date_str, idx, "entry_hash_mismatch", checked)
        prev = rec.get("entry_hash")
    return VerifyResult(True, date_str, None, None, checked)


def verify_range(start_date: str, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify each day independently and return a report.
    If end_date is None, verifies a single day.
    """
    if not end_date:
        r = verify_day(start_date)
        return {
            "ok": r.ok,
            "days": [
                {
                    "date": r.date,
                    "ok": r.ok,
                    "first_bad_index": r.first_bad_index,
                    "reason": r.reason,
                    "checked": r.entries_checked,
                }
            ],
        }
    # iterate sequentially (UTC lexicographic dates)
    from datetime import datetime, timedelta, timezone

    def parse(d: str) -> datetime:
        return datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    def fmt(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")

    cur = parse(start_date)
    end = parse(end_date)
    days = []
    ok_all = True
    while cur <= end:
        ds = fmt(cur)
        r = verify_day(ds)
        days.append(
            {
                "date": ds,
                "ok": r.ok,
                "first_bad_index": r.first_bad_index,
                "reason": r.reason,
                "checked": r.entries_checked,
            }
        )
        ok_all = ok_all and r.ok
        cur += timedelta(days=1)
    return {"ok": ok_all, "days": days}
