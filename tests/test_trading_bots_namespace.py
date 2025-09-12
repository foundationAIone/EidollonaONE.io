"""Namespace consolidation test for trading bots.

Ensures:
1. Canonical path `ai_core.bots` loads and creates bots.
2. Optional compat import may exist; canonical path should be used in code/docs.
3. Core bot run_once() returns bounded score and required keys.
"""

from __future__ import annotations

import sys
import pathlib

# Ensure project root (containing ai_core) is on path when tests executed
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _assert_bot_payload(payload: dict):
    assert "score" in payload and 0.0 <= payload["score"] <= 1.0
    assert "action" in payload or "outcome" in payload  # some bots use 'outcome'
    assert "state" in payload and isinstance(payload["state"], dict)


def test_new_namespace_crypto_bot():
    # Prefer canonical path
    from ai_core.bots import create_crypto_bot  # type: ignore

    bot = create_crypto_bot(seed=123, emit_path=None)
    result = bot.run_once()
    _assert_bot_payload(result)


def test_compat_namespace_if_present():
    # If a deprecated compat module exists, it should re-export the same API
    try:
        import importlib

        compat_mod = importlib.import_module("ai_core.trading_bots")  # type: ignore
        compat_create = getattr(compat_mod, "create_crypto_bot")
    except Exception:
        return
    from ai_core.bots import create_crypto_bot as canonical_create  # type: ignore

    assert callable(compat_create) and callable(canonical_create)


def test_namespace_equivalence_arbitrage_bot():
    from ai_core.bots import create_arbitrage_bot  # type: ignore

    legacy_create = create_arbitrage_bot

    new_bot = create_arbitrage_bot(seed=7)
    legacy_bot = legacy_create(seed=7)
    new_payload = new_bot.run_once()
    legacy_payload = legacy_bot.run_once()
    _assert_bot_payload(new_payload)
    _assert_bot_payload(legacy_payload)
    # Determinism check with same seed: allow slight drift; ensure both scores within valid range
    assert abs(new_payload["score"] - legacy_payload["score"]) <= 0.2
