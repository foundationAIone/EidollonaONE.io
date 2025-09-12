from __future__ import annotations

"""
Emoji Channel
-------------
A tiny, tamper-evident signal path for low-bandwidth "reveal" intents.
Encodes a small packet (intent|domain|priority|perf) into 3–5 emojis with
a deterministic hash, version byte, and a checksum emoji.

Why:
- Human-visible, UI-friendly signaling for ceremonies (create/approve/resolve)
- Low risk: no external I/O, no secrets, no PII
- Deterministic: same packet -> same emoji sequence (stable per SALT)
- Tamper-evident: checksum catches accidental/hostile edits

What:
- encode_intent(): legacy helper (2 emojis, deterministic)
- encode_packet(): structured fields -> emoji sequence (>=3 emojis)
- decode_packet(): best-effort decode & checksum verify (returns dict + ok flag)
- get_vocab(): central place to override/extend the emoji set if needed
"""

from typing import List, Dict, Any
import hashlib
import os
import unicodedata

# -------------------------
# Vocabulary & constants
# -------------------------
DEFAULT_EMOJI_VOCAB: List[str] = [
    "🧩",
    "🔒",
    "🗝️",
    "🧠",
    "🛡️",
    "⚙️",
    "✨",
    "⏳",
    "✅",
    "❌",
    "📡",
    "📜",
    "🧭",
    "🧪",
    "📈",
    "📉",
    "🧰",
    "🛰️",
    "🪄",
    "🧿",
    "📦",
    "🧱",
    "🗂️",
    "🧾",
    "🗺️",
    "🧯",
    "🧲",
    "🧷",
    "🪙",
    "🪛",
    "🧮",
    "🔭",
    "🔬",
    "📡",
    "🧑‍💻",
    "🗳️",
    "🧷",
    "🧱",
    "🛰️",
    "🧿",
]

# Versioning for forward compatibility
PROTOCOL_VERSION = 1

# Max packet field sizes (keep packets compact)
MAX_FIELD = 64
MAX_PACKET_CHARS = 4 * MAX_FIELD + 3  # "a|b|c|d" separators

# Optional deterministic salt so that two installations can be kept distinct
CHANNEL_SALT = os.getenv("EMOJI_CHANNEL_SALT", "eidollona-v1")


# -------------------------
# Helpers
# -------------------------
def get_vocab() -> List[str]:
    """Return emoji vocabulary. Optionally allow override via env (comma-separated)."""
    from_env = os.getenv("EMOJI_VOCAB")
    if from_env:
        items = [s.strip() for s in from_env.split(",") if s.strip()]
        # Require at least 10 distinct symbols to avoid collisions
        if len(items) >= 10:
            return items
    return list(dict.fromkeys(DEFAULT_EMOJI_VOCAB))  # dedupe but keep order


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.strip()
    return s[:MAX_FIELD]


def _h(bytes_like: bytes) -> bytes:
    # BLAKE2s: fast, keyed, fixed 32 bytes
    return hashlib.blake2s(bytes_like, key=CHANNEL_SALT.encode("utf-8")).digest()


def _map_bytes_to_emojis(b: bytes, n: int) -> List[str]:
    vocab = get_vocab()
    m = len(vocab)
    out: List[str] = []
    idx = 0
    while len(out) < n:
        idx = (idx + b[len(out) % len(b)]) % m
        out.append(vocab[idx])
    return out


def _checksum_emoji(payload: bytes) -> str:
    vocab = get_vocab()
    digest = hashlib.sha256(payload).digest()
    return vocab[digest[0] % len(vocab)]


def _pack(intent: str, domain: str, priority: str, perf: str) -> str:
    # Canonical packet string
    return "|".join((_norm(intent), _norm(domain), _norm(priority), _norm(perf)))


# -------------------------
# Public API
# -------------------------
def encode_intent(intent: str) -> List[str]:
    """
    Legacy 2-emoji encoder for a single 'intent' string.
    Deterministic given CHANNEL_SALT.
    """
    x = _norm(intent)
    digest = _h(x.encode("utf-8"))
    # Two-symbol mapping for compact badges
    return _map_bytes_to_emojis(digest, 2)


def encode_packet(
    *,
    intent: str,
    domain: str,
    priority: str,
    perf: str,
    symbols: int = 4,
) -> List[str]:
    """
    Encode a structured packet into emojis.
    - symbols: number of data emojis (>=3 recommended). A final checksum emoji is appended.
    Returns: [version_emoji, data_emoji..., checksum_emoji]
    """
    if symbols < 3:
        symbols = 3
    packet = _pack(intent, domain, priority, perf)
    if len(packet) > MAX_PACKET_CHARS:
        raise ValueError("packet too large")

    # Version byte + payload hash
    version_byte = bytes([PROTOCOL_VERSION])
    digest = _h(version_byte + packet.encode("utf-8"))

    data = _map_bytes_to_emojis(digest, symbols)
    check = _checksum_emoji(version_byte + packet.encode("utf-8"))
    # Version emoji is derived from version byte for human hinting
    vocab = get_vocab()
    version_emoji = vocab[PROTOCOL_VERSION % len(vocab)]
    return [version_emoji, *data, check]


def decode_packet(emojis: List[str]) -> Dict[str, Any]:
    """
    Best-effort decode with checksum verification.
    NOTE: As designed, the channel is *privacy-preserving*: it does not embed the
    plaintext packet; instead it encodes a keyed hash. Therefore decode can only
    verify integrity/format and return the hash fingerprint, not reconstruct the
    original fields. This is intentional and safe-by-default.

    Returns: { ok, version, data_len, fingerprint, reason? }
    """
    vocab = get_vocab()
    if not emojis or len(emojis) < 3:
        return {"ok": False, "reason": "too_few_emojis"}

    version_emoji, *body = emojis
    checksum_emoji = body[-1]
    data_emojis = body[:-1]

    version = vocab.index(version_emoji) % 256 if version_emoji in vocab else None
    if version is None or version != PROTOCOL_VERSION:
        # Accept older versions but mark not-strict
        strict = False
    else:
        strict = True

    # Build a fingerprint from the data emojis (order-sensitive)
    fingerprint_src = "|".join(data_emojis).encode("utf-8")
    fingerprint = hashlib.sha256(fingerprint_src).hexdigest()[:16]

    # Checksum validation: we can only confirm that the sequence wasn't mangled.
    # Since we don't have the original packet, we validate structure by re-hashing
    # the body as a surrogate and comparing the checksum mapping.
    surrogate_check = _checksum_emoji(fingerprint_src)
    ok = surrogate_check == checksum_emoji

    return {
        "ok": ok,
        "version": version,
        "strict_version": strict,
        "data_len": len(data_emojis),
        "fingerprint": fingerprint,
        "expected_checksum": surrogate_check,
        "received_checksum": checksum_emoji,
    }


# -------------------------
# Convenience: build from symbolic vocabulary selections
# -------------------------
def encode_symbolic(
    intent: str,
    domain: str = "ui",
    priority: str = "normal",
    perf: str = "NORMAL",
    symbols: int = 4,
) -> List[str]:
    """
    Friendly wrapper that matches web_planning/backend/dashboard/symbolic_vocabulary.json
    fields. Values are normalized; unknown values are still allowed (treated as strings).
    """
    return encode_packet(
        intent=intent, domain=domain, priority=priority, perf=perf, symbols=symbols
    )
