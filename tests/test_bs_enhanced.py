from __future__ import annotations

from black_scholes.black_scholes_model import greeks, implied_vol, price


def test_bs_roundtrip():
    params = {"S": 100.0, "K": 100.0, "r": 0.02, "q": 0.0, "sigma": 0.20, "t": 0.5}
    premium = price("call", **params)
    iv = implied_vol("call", params["S"], params["K"], params["r"], params["q"], params["t"], premium)
    assert abs(iv - params["sigma"]) < 1e-4


def test_greeks_signs():
    g = greeks("call", 100.0, 100.0, 0.01, 0.0, 0.25, 1.0)
    assert g["gamma"] > 0.0
    assert g["vega"] > 0.0
