"""
Safe output encoder for previews, with policy-aware size limits and DLP redaction.

Enhancements:
- Applies DLP scan with optional redaction or blocking (policy + soft mode).
- Truncates previews to a configured byte limit (UTF-8 safe) before base64.
- Emits audited decisions via guardian.audit; never blocks on audit errors.
- Backward compatible: same input/output contract for safe_preview.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Tuple

from .dlp_guard import guard_dlp
from . import audit as _audit_mod


# --------------
# Policy loading
# --------------
_POLICY_PATH = os.path.join(os.path.dirname(__file__), "policy.json")
_POLICY_MTIME: float = 0.0
_POLICY: Dict[str, Any] = {}


def _load_policy(force: bool = False) -> Dict[str, Any]:
    global _POLICY, _POLICY_MTIME
    try:
        mtime = os.path.getmtime(_POLICY_PATH)
    except Exception:
        mtime = 0.0
    if force or (not _POLICY) or (mtime > _POLICY_MTIME):
        try:
            with open(_POLICY_PATH, encoding="utf-8") as f:
                _POLICY = json.load(f) or {}
        except Exception:
            _POLICY = {}
        _POLICY_MTIME = mtime
    return _POLICY


def _soft_mode() -> bool:
    # Soft mode: do not raise/block; redact/log only
    return os.getenv("GUARDIAN_OUTPUT_SOFT_MODE", "0") == "1"


def _emit_audit(action: str, payload: Dict[str, Any]) -> None:
    try:
        _audit_mod.append_event(
            actor="guardian",
            action=action,
            ctx={"module": "output_encoder"},
            payload=payload,
        )  # type: ignore[attr-defined]
    except Exception:
        pass


def _truncate_utf8(s: str, max_bytes: int) -> Tuple[str, bool, int]:
    b = s.encode("utf-8")
    if len(b) <= max_bytes:
        return s, False, len(b)
    # Truncate at byte boundary and decode ignoring trailing partial code point
    tb = b[:max_bytes]
    ts = tb.decode("utf-8", errors="ignore")
    return ts, True, len(b)


def _redact_spans(
    text: str, spans: List[Tuple[int, int]], token: str = "[REDACTED]"
) -> str:
    if not spans:
        return text
    # Merge overlapping spans
    spans = sorted(spans)
    merged: List[Tuple[int, int]] = []
    cs, ce = spans[0]
    for s, e in spans[1:]:
        if s <= ce:
            ce = max(ce, e)
        else:
            merged.append((cs, ce))
            cs, ce = s, e
    merged.append((cs, ce))

    out = []
    last = 0
    for s, e in merged:
        out.append(text[last:s])
        out.append(token)
        last = e
    out.append(text[last:])
    return "".join(out)


def _to_text(content: Any) -> str:
    if isinstance(content, bytes):
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return ""
    if isinstance(content, (dict, list)):
        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)
    return str(content if content is not None else "")


def safe_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a safe, DLP-checked base64 preview of payload['content'].

    Returns the original payload minus 'content', with:
    - content_b64: base64(utf8(preview_text))
    - preview_only: True
    - truncated: bool
    - length_bytes: int (original text bytes)
    - redacted: bool (if DLP redactions applied)
    - blocked/ reason (if DLP policy blocks and not in soft mode)
    """
    pol = _load_policy()
    cfg = pol.get("output_encoder") or {}
    max_preview_bytes = int(cfg.get("max_preview_bytes", 4096))
    redact_previews = bool(cfg.get("dlp_redact_previews", True))

    data = dict(payload)
    text = _to_text(data.get("content", ""))

    # DLP check first (on full text)
    ok, details = guard_dlp(text)
    dlp_detected = not ok
    blocked = bool(details.get("blocked")) if dlp_detected else False

    if dlp_detected:
        _emit_audit(
            "output.dlp.detect",
            {
                "types": sorted({h["type"] for h in details.get("hits", [])}),
                "blocked": blocked,
            },
        )
    if blocked and not _soft_mode():
        # Do not include any content in hard-block mode
        data.pop("content", None)
        data.update(
            {
                "preview_only": True,
                "blocked": True,
                "reason": details.get("reason", "secret-detected"),
                "dlp": {
                    "count": len(details.get("hits", [])),
                    "types": sorted({h["type"] for h in details.get("hits", [])}),
                },
                # keep response shape stable
                "redacted": False,
                "truncated": False,
                "length_bytes": len(text.encode("utf-8")),
            }
        )
        return data

    redacted = False
    if dlp_detected and redact_previews:
        spans: List[Tuple[int, int]] = [
            tuple(h.get("span", (0, 0)))
            for h in details.get("hits", [])
            if isinstance(h.get("span"), (list, tuple))
        ]
        text = _redact_spans(text, [(int(s), int(e)) for s, e in spans])
        redacted = True

    # Truncate to preview budget
    preview_text, truncated, length_bytes = _truncate_utf8(text, max_preview_bytes)
    b64 = base64.b64encode(preview_text.encode("utf-8")).decode("ascii")

    # Prepare response
    data.pop("content", None)
    data.update(
        {
            "content_b64": b64,
            "encoding": "utf-8",
            "preview_only": True,
            "truncated": truncated,
            "length_bytes": length_bytes,
            "redacted": redacted,
        }
    )

    _emit_audit(
        "output.preview",
        {"truncated": truncated, "redacted": redacted, "length": length_bytes},
    )
    return data


__all__ = ["safe_preview"]
