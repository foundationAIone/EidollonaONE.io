from __future__ import annotations
import json
import re
import urllib.parse
import os
from typing import Tuple, Dict, Any
from .unicode_sanitizer import sanitize_and_score

# Load static policy
_POLICY_PATH = os.path.join(os.path.dirname(__file__), "policy.json")
_POLICY = json.load(open(_POLICY_PATH, encoding="utf-8"))

# Compiled patterns
B64LIKE = re.compile(r"^[A-Za-z0-9+/=]{100,}$")
SYS_PROMPT_FISH = re.compile(
    "|".join(map(re.escape, _POLICY["pi_blocklist_phrases"])), re.I
)

# Optional audit hook
try:
    from common.audit_chain import append_event as _audit
except Exception:
    _audit = None


def _audit_event(action: str, payload: Dict[str, Any]):
    """Safe audit emitter."""
    if _audit:
        try:
            _audit(
                actor="guardian",
                action=action,
                ctx={"module": "ai_firewall"},
                payload=payload,
            )
        except Exception:
            pass


def _url_is_allowed(url: str) -> Tuple[bool, str]:
    """Policy-aware URL allow/deny check."""
    try:
        u = urllib.parse.urlparse(url)
        if u.scheme in _POLICY["deny_schemes"]:
            return False, "scheme"
        host = (u.hostname or "").lower()
        if (
            _POLICY["block_untrusted_links"]
            and host not in _POLICY["allow_domains_outbound"]
        ):
            return False, "host"
        if len(u.query) > _POLICY["max_url_query_len"]:
            return False, "query_len"
        if (
            B64LIKE.search(u.query or "")
            and len(u.query) > _POLICY["block_base64_threshold"]
        ):
            return False, "b64"
        return True, ""
    except Exception:
        return False, "parse"


def intake_guard(raw_text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Ingress guard for user-supplied text.
    Runs Unicode/emoji sanitization, injection checks, and link/payload scans.
    """
    clean, meta = sanitize_and_score(raw_text)

    # Dynamic threshold from policy if set
    unicode_threshold = _POLICY.get("unicode_risk_threshold", 0.6)
    if meta["risk"] >= unicode_threshold:
        _audit_event("intake_block", {"reason": "unicode_risk", "meta": meta})
        return False, {"reason": "unicode_risk", "meta": meta}

    # Prompt injection detection
    if SYS_PROMPT_FISH.search(clean):
        _audit_event("intake_block", {"reason": "prompt_injection", "meta": meta})
        return False, {"reason": "prompt_injection", "meta": meta}

    # URL and link smuggling detection
    for m in re.findall(r"(https?://\S+)", clean):
        ok, why = _url_is_allowed(m)
        if not ok:
            _audit_event(
                "intake_block",
                {"reason": f"link_smuggling:{why}", "url": m, "meta": meta},
            )
            return False, {"reason": f"link_smuggling:{why}", "url": m, "meta": meta}

    _audit_event("intake_pass", {"meta": meta})
    return True, {"meta": meta}


def outbound_guard(response_text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Egress guard for AI/model output before returning to user or tools.
    Scans for unsafe URLs and high-entropy exfiltration.
    """
    for m in re.findall(r"(https?://\S+)", response_text):
        ok, why = _url_is_allowed(m)
        if not ok:
            _audit_event("outbound_block", {"reason": f"outbound_link:{why}", "url": m})
            return False, {"reason": f"outbound_link:{why}", "url": m}

    for tok in response_text.split():
        if len(tok) > 1500 and B64LIKE.match(tok):
            _audit_event("outbound_block", {"reason": "outbound_b64"})
            return False, {"reason": "outbound_b64"}

    _audit_event("outbound_pass", {"length": len(response_text)})
    return True, {}


# Backwards-compatible aliases expected by router
guard_intake = intake_guard
guard_outbound = outbound_guard
