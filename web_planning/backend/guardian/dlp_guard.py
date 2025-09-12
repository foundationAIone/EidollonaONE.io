from __future__ import annotations

import os
import re
import json
from typing import Dict, Any, List, Tuple

# Load policy and audit convenience
_POLICY_PATH = os.path.join(os.path.dirname(__file__), "policy.json")
try:
    _POLICY: Dict[str, Any] = json.load(open(_POLICY_PATH, encoding="utf-8"))
except Exception:
    _POLICY = {}

try:
    # Prefer guardian's governance-ready audit wrapper
    from .audit import append_event as _audit
except Exception:
    _audit = None  # type: ignore


def _audit_event(action: str, payload: Dict[str, Any]) -> None:
    if _audit:
        try:
            _audit(
                actor="guardian",
                action=action,
                ctx={"module": "dlp_guard"},
                payload=payload,
            )
        except Exception:
            pass


# Built-in default patterns (compiled once)
_DEFAULT_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("aws_secret", re.compile(r"(?i)aws(.{0,20})?(secret|key).{0,3}[:=].{16,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+")),
    ("generic_api_key", re.compile(r"(?i)(api|token|secret).{0,5}[:=].{12,}")),
]


def _load_policy_patterns() -> List[Tuple[str, re.Pattern[str]]]:
    out: List[Tuple[str, re.Pattern[str]]] = []
    try:
        items = _POLICY.get("dlp_patterns") or []
        for it in items:
            name = str(it.get("name") or "custom")
            rx = str(it.get("regex") or "").strip()
            if not rx:
                continue
            flags = re.I if it.get("ignore_case", True) else 0
            try:
                out.append((name, re.compile(rx, flags)))
            except Exception:
                continue
    except Exception:
        pass
    return out


_POLICY_PATTERNS = _load_policy_patterns()
_ALL_PATTERNS: List[Tuple[str, re.Pattern[str]]] = _DEFAULT_PATTERNS + _POLICY_PATTERNS


class DLPViolation(Exception):
    pass


def _mask(sample: str, keep: int = 2) -> str:
    if not sample:
        return sample
    if len(sample) <= keep * 2:
        return sample[0:1] + "…" * max(0, len(sample) - 2) + sample[-1:]
    return sample[:keep] + "…" + sample[-keep:]


def _is_allowed_sample(sample: str, allowlist: List[re.Pattern[str]]) -> bool:
    for rx in allowlist:
        if rx.search(sample):
            return True
    return False


def guard_dlp(text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Tuple-returning guard for DLP checks.
    Honors policy settings and emits audit events on detect/pass.
    """
    text = text or ""
    hits: List[Dict[str, Any]] = []

    # Policy knobs with safe defaults
    block_on_types = set(
        _POLICY.get("dlp_block_on_types") or [name for name, _ in _ALL_PATTERNS]
    )
    max_hits = int(_POLICY.get("dlp_max_hits", 1))
    sample_ctx = int(_POLICY.get("dlp_sample_context", 4))
    redact = bool(_POLICY.get("dlp_redact", True))
    allowlist_rx = []
    try:
        allowlist_rx = [
            re.compile(r) for r in (_POLICY.get("dlp_allow_patterns") or [])
        ]
    except Exception:
        allowlist_rx = []

    for name, rx in _ALL_PATTERNS:
        for m in rx.finditer(text):
            span = m.span()
            sample = text[
                max(0, span[0] - sample_ctx) : min(len(text), span[1] + sample_ctx)
            ]
            if _is_allowed_sample(sample, allowlist_rx):
                continue
            hits.append(
                {
                    "type": name,
                    "span": span,
                    "sample": _mask(sample) if redact else sample,
                }
            )
            if len(hits) >= max_hits:
                break
        if len(hits) >= max_hits:
            break

    if hits:
        types = sorted({h["type"] for h in hits})
        reason = "secret-detected"
        blocked = any(t in block_on_types for t in types)
        _audit_event(
            "dlp.block" if blocked else "dlp.detect",
            {"count": len(hits), "types": types},
        )
        return False, {"reason": reason, "hits": hits, "blocked": blocked}

    _audit_event("dlp.pass", {"length": len(text)})
    return True, {}


def scan_text(text: str):
    """
    Backward-compatible API: raises DLPViolation on detection (default policy).
    """
    soft_mode = bool(os.getenv("GUARDIAN_DLP_SOFT_MODE", "0") == "1")
    ok, details = guard_dlp(text)
    if not ok:
        if soft_mode:
            return False
        # Raise with the same shape as legacy callers expect
        raise DLPViolation(
            {
                "reason": details.get("reason", "secret-detected"),
                "hits": details.get("hits", []),
            }
        )
    return True
