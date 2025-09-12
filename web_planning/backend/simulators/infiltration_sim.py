from __future__ import annotations

from typing import Dict, Any, List, Tuple
import re


# Light-weight infiltration simulation and detector.
# Backward compatible: attempt(payload) returns { risk_score: float, matches: List[str], ... }


_NETWORK_STRS = [
    "curl http://",
    "curl https://",
    "wget http://",
    "wget https://",
    "invoke-webrequest",
    "iwr ",
    "invoke-restmethod",
    "webclient",
    "requests.get(",
    "urllib.request",
    "powershell -enc",
]

_SHELL_STRS = [
    "bash -i >& /dev/tcp/",
    "nc -e",
    "ncat -e",
    "/bin/sh -i",
    "bash -c",
    "sh -c",
    "python -c",
    "perl -e",
    "php -r",
    "certutil -urlcache",
    "rundll32",
    "schtasks /create",
    "mshta ",
    "wscript ",
    "cscript ",
]

_OBFUSCATION_STRS = [
    "frombase64string",
    "base64 -d",
    "-enc ",
    "iex ",
    "-w hidden",
    "-nop",
    "-noni",
]

_SENSITIVE_PATHS = [
    "/etc/shadow",
    "~/.ssh/id_rsa",
    "\\Windows\\System32",
    "/root/",
    "\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup",
]

_REGEXES: List[Tuple[str, str]] = [
    (r"\bhttps?://[\w.-]+(?::\d+)?(?:/[\w\-./?%&=#]*)?", "network:url"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b", "network:ip"),
    (r"AKIA[0-9A-Z]{16}", "secrets:aws_access_key"),
    (r"-----BEGIN (?:RSA|OPENSSH) PRIVATE KEY-----", "secrets:private_key"),
    (r"(?i)token=\w{10,}", "secrets:token_kv"),
    (r"(?i)authorization:\s*bearer\s+[A-Za-z0-9\-_.]{10,}", "secrets:http_bearer"),
]

_UNICODE_CTRLS = {
    "\u202A",  # LRE
    "\u202B",  # RLE
    "\u202D",  # LRO
    "\u202E",  # RLO
    "\u2066",  # LRI
    "\u2067",  # RLI
    "\u2068",  # FSI
    "\u2069",  # PDI
    "\u200B",  # ZWSP
}


_WEIGHTS = {
    "network": 0.2,
    "shell": 0.25,
    "obfuscation": 0.2,
    "sensitive_path": 0.25,
    "secrets": 0.4,
    "unicode": 0.1,
}


def _find_substrings(payload: str, candidates: List[str]) -> List[str]:
    low = (payload or "").lower()
    return [c for c in candidates if c.lower() in low]


def _find_regex(
    payload: str, patterns: List[Tuple[str, str]]
) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    text = payload or ""
    for pat, label in patterns:
        for m in re.finditer(pat, text):
            snippet = m.group(0)
            out.append((label.split(":")[0], label, snippet))
    return out


def _unicode_controls(payload: str) -> List[str]:
    hits = []
    for ch in payload or "":
        if ch in _UNICODE_CTRLS:
            hits.append(ch)
    return hits


def _severity(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


def attempt(payload: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Analyze a payload for infiltration/exfiltration risk.

    Returns:
      - risk_score: 0..1 overall score
      - severity: low|medium|high|critical
      - matches: List[str] (backward-compatible, unique indicators)
      - hits: detailed list of {category, label, snippet}
      - risk_breakdown: {category: cumulative_weight}
      - stats: simple counts
      - has_unicode_controls: bool
    """
    payload = payload or ""

    # Gather hits
    hits: List[Dict[str, Any]] = []
    breakdown: Dict[str, float] = {k: 0.0 for k in _WEIGHTS}

    net_hits = _find_substrings(payload, _NETWORK_STRS)
    for s in net_hits:
        hits.append({"category": "network", "label": s, "snippet": s})
        breakdown["network"] += _WEIGHTS["network"]

    sh_hits = _find_substrings(payload, _SHELL_STRS)
    for s in sh_hits:
        hits.append({"category": "shell", "label": s, "snippet": s})
        breakdown["shell"] += _WEIGHTS["shell"]

    ob_hits = _find_substrings(payload, _OBFUSCATION_STRS)
    for s in ob_hits:
        hits.append({"category": "obfuscation", "label": s, "snippet": s})
        breakdown["obfuscation"] += _WEIGHTS["obfuscation"]

    for cat, label, snippet in _find_regex(payload, _REGEXES):
        hits.append({"category": cat, "label": label, "snippet": snippet})
        breakdown[cat] += _WEIGHTS.get(cat, 0.15)

    sens_hits = _find_substrings(payload, _SENSITIVE_PATHS)
    for s in sens_hits:
        hits.append({"category": "sensitive_path", "label": "path", "snippet": s})
        breakdown["sensitive_path"] += _WEIGHTS["sensitive_path"]

    uni_hits = _unicode_controls(payload)
    if uni_hits:
        hits.append(
            {
                "category": "unicode",
                "label": "controls",
                "snippet": "".join(sorted(set(uni_hits))),
            }
        )
        breakdown["unicode"] += min(0.2, 0.02 * len(uni_hits))

    # Normalize unique matches for backward compatibility
    matches = sorted(
        {h["label"] if isinstance(h["label"], str) else str(h["label"]) for h in hits}
    )

    # Compute score: combine capped sum and a sigmoid-like boost with unique categories
    raw_sum = sum(breakdown.values())
    unique_cats = len({h["category"] for h in hits})
    diversity_boost = min(0.25, 0.05 * max(0, unique_cats - 1))
    score = max(0.0, min(1.0, raw_sum + diversity_boost))

    result = {
        "risk_score": round(float(score), 3),
        "severity": _severity(score),
        "matches": matches,
        "hits": hits,
        "risk_breakdown": {k: round(v, 3) for k, v in breakdown.items() if v > 0},
        "stats": {
            "network": len(net_hits),
            "shell": len(sh_hits),
            "obfuscation": len(ob_hits),
            "secrets": sum(1 for h in hits if h["category"] == "secrets"),
            "sensitive_paths": len(sens_hits),
            "unicode_controls": len(uni_hits),
            "indicators": len(matches),
        },
        "has_unicode_controls": bool(uni_hits),
    }
    return result


def analyze(payload: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Alias for attempt() for clarity in call sites."""
    return attempt(payload, context=context)


__all__ = ["attempt", "analyze"]
