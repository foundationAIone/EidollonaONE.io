from __future__ import annotations

from trading_engine.options.bsm import implied_vol, price
from market_analysis.regime.hmm_regime import SimpleHMM


def test_bs_roundtrip() -> None:
    S, K, r, q, sigma, t = 100.0, 100.0, 0.02, 0.0, 0.20, 0.5
    premium = price("call", S, K, r, q, sigma, t)
    iv = implied_vol("call", S, K, r, q, t, premium)
    assert abs(iv - sigma) < 1e-4


def test_hmm_smoke() -> None:
    series = [0.0, 0.01, -0.005, 0.012, -0.006, 0.003, 0.02, -0.01]
    hmm = SimpleHMM()
    hmm.fit(series, iters=3)
    out = hmm.infer(series)
    assert "p_regime0" in out and "p_regime1" in out
    assert 0.0 <= out["p_regime0"] <= 1.0
    assert 0.0 <= out["p_regime1"] <= 1.0
