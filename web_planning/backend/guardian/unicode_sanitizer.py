from __future__ import annotations

import os
import json
import unicodedata
import re
from typing import Dict, Any, Tuple, List, Set

from . import audit as _audit_mod


# -----------------
# Policy management
# -----------------
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
    return os.getenv("GUARDIAN_UNICODE_SOFT_MODE", "0") == "1"


def _emit_audit(action: str, payload: Dict[str, Any]) -> None:
    try:
        _audit_mod.append_event(actor="guardian", action=action, ctx={"module": "unicode_sanitizer"}, payload=payload)  # type: ignore[attr-defined]
    except Exception:
        pass


# ------------------
# Unicode risk checks
# ------------------
INVISIBLE: Set[str] = {
    "\u200b",
    "\u200c",
    "\u200d",
    "\u2060",
    "\ufeff",  # ZW chars & BOM & word joiner
    "\u200e",
    "\u200f",  # LRM/RLM
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",  # Bidi embedding/override/PDF
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",  # LRI/RLI/FSI/PDI
}
COMBINING_RX = re.compile(r"[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff]")
CYRILLIC_RX = re.compile(r"[\u0400-\u04FF]")
GREEK_RX = re.compile(r"[\u0370-\u03FF]")
HEBREW_RX = re.compile(r"[\u0590-\u05FF]")
ARABIC_RX = re.compile(r"[\u0600-\u06FF]")
CJK_RX = re.compile(r"[\u4E00-\u9FFF]")
HIRAGANA_RX = re.compile(r"[\u3040-\u309F]")
KATAKANA_RX = re.compile(r"[\u30A0-\u30FF]")


def _detect_scripts(s: str) -> Set[str]:
    scripts: Set[str] = set()
    if CYRILLIC_RX.search(s):
        scripts.add("Cyrillic")
    if GREEK_RX.search(s):
        scripts.add("Greek")
    if HEBREW_RX.search(s):
        scripts.add("Hebrew")
    if ARABIC_RX.search(s):
        scripts.add("Arabic")
    if CJK_RX.search(s):
        scripts.add("CJK")
    if HIRAGANA_RX.search(s):
        scripts.add("Hiragana")
    if KATAKANA_RX.search(s):
        scripts.add("Katakana")
    # Rough Latin detection: presence of ASCII letters
    if re.search(r"[A-Za-z]", s):
        scripts.add("Latin")
    return scripts


def sanitize_and_score(text: str) -> Tuple[str, Dict[str, Any]]:
    pol = _load_policy()
    cfg = pol.get("unicode") or {}

    normalization = str(cfg.get("normalization", "NFKC")).upper()
    remove_invisible = bool(cfg.get("remove_invisible", True))
    remove_controls = bool(cfg.get("remove_controls", True))
    max_combining = int(cfg.get("max_combining_marks", 8))
    max_token_len = int(cfg.get("max_token_length", 1200))
    risk_block_threshold = float(cfg.get("risk_block_threshold", 0.85))

    # Weights for risk components
    w = cfg.get("weights", {})
    W_REMOVED_INVISIBLE = float(w.get("removed_invisible", 0.2))
    W_COMBINING_EXCESS = float(w.get("combining_excess", 0.2))
    W_PRIVATE_SURR = float(w.get("private_surrogate", 0.3))
    W_LONG_TOKEN = float(w.get("long_token", 0.4))
    W_BIDI = float(w.get("bidi", 0.3))
    W_SCRIPT_MIX = float(w.get("script_mix", 0.2))
    W_NONASCII_RATIO = float(w.get("nonascii_ratio", 0.1))

    text = text or ""
    try:
        norm = unicodedata.normalize(
            (
                normalization
                if normalization in {"NFC", "NFKC", "NFD", "NFKD"}
                else "NFKC"
            ),
            text,
        )
    except Exception:
        norm = unicodedata.normalize("NFKC", text)

    removed_invisible_count = 0
    controls_count = 0
    bidi_count = 0
    private_or_surrogate = False

    out_chars: List[str] = []
    for ch in norm:
        cat = unicodedata.category(ch)
        if ch in INVISIBLE:
            removed_invisible_count += 1
            bidi_count += (
                1
                if ch
                in {
                    "\u202a",
                    "\u202b",
                    "\u202c",
                    "\u202d",
                    "\u202e",
                    "\u2066",
                    "\u2067",
                    "\u2068",
                    "\u2069",
                }
                else 0
            )
            if remove_invisible:
                continue
        if cat in ("Cc",):  # control chars
            controls_count += 1
            if remove_controls:
                continue
        if cat in ("Co", "Cs"):
            private_or_surrogate = True
            # Replace with REPLACEMENT CHARACTER to neutralize
            out_chars.append("\uFFFD")
            continue
        out_chars.append(ch)

    norm2 = "".join(out_chars)
    combining_count = len(COMBINING_RX.findall(norm2))

    # Token checks
    tokens = re.split(r"\s+", norm2) if norm2 else []
    long_token = any(len(t) > max_token_len for t in tokens)
    # Optionally truncate long tokens to limit surprise
    if long_token:
        new_tokens: List[str] = []
        for t in tokens:
            new_tokens.append(t[:max_token_len] if len(t) > max_token_len else t)
        norm2 = re.sub(r"\s+", " ", " ".join(new_tokens)).strip()

    scripts = _detect_scripts(norm2)
    script_mix = len(scripts) > 1

    # Non-ASCII ratio
    total = len(norm2)
    nonascii_ratio = (sum(1 for ch in norm2 if ord(ch) > 127) / total) if total else 0.0

    # Risk aggregation
    risk = 0.0
    reasons: List[str] = []
    if removed_invisible_count:
        risk += W_REMOVED_INVISIBLE
        reasons.append("removed_invisible")
    if combining_count > max_combining:
        risk += W_COMBINING_EXCESS
        reasons.append("combining_excess")
    if private_or_surrogate:
        risk += W_PRIVATE_SURR
        reasons.append("private_or_surrogate")
    if long_token:
        risk += W_LONG_TOKEN
        reasons.append("long_token")
    if bidi_count:
        risk += W_BIDI
        reasons.append("bidi_controls")
    if script_mix:
        risk += W_SCRIPT_MIX
        reasons.append("script_mix")
    if nonascii_ratio > 0.7:
        risk += W_NONASCII_RATIO
        reasons.append("nonascii_ratio")

    risk = min(1.0, max(0.0, float(risk)))
    blocked = bool(risk >= risk_block_threshold)

    info: Dict[str, Any] = {
        "risk": round(risk, 3),
        "blocked": blocked,
        "reasons": reasons,
        "removed_invisible": removed_invisible_count,
        "controls": controls_count,
        "bidi": bidi_count,
        "combining": combining_count,
        "script_mix": script_mix,
        "scripts": sorted(list(scripts)),
        "nonascii_ratio": round(nonascii_ratio, 3),
    }

    _emit_audit(
        "unicode.sanitize",
        {
            "risk": info["risk"],
            "blocked": blocked,
            "reasons": reasons,
            "len": len(norm2),
        },
    )
    return norm2, info


def sanitize(text: str) -> str:
    norm, _ = sanitize_and_score(text or "")
    return norm


__all__ = ["sanitize", "sanitize_and_score"]
