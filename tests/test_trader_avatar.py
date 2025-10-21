from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from avatars.orchestrator.api import AvatarIntent
from avatars.trader import abilities
from avatars.trader import ledger
from trading.api.routes import router as trader_router


@pytest.fixture(autouse=True)
def _temp_ledger(tmp_path, monkeypatch):
    path = tmp_path / "paper.json"
    monkeypatch.setattr(ledger, "_LEDGER_PATH", path)
    monkeypatch.setattr("avatars.trader.abilities.audit_ndjson", lambda *args, **kwargs: None)
    monkeypatch.setattr("avatars.trader.ledger.audit_ndjson", lambda *args, **kwargs: None)
    yield


def test_record_trade_buy_and_sell_cycle():
    state = ledger.record_trade("SAFE", "buy", 10, 12.5)
    assert pytest.approx(state["cash"], abs=1e-5) == pytest.approx(100_000 - 125)
    assert "SAFE" in state["positions"]

    state = ledger.record_trade("SAFE", "sell", 5, 13.0)
    assert state["positions"]["SAFE"]["quantity"] == pytest.approx(5.0)
    assert state["realized_pnl"] == pytest.approx((13.0 - 12.5) * 5)


def test_handle_intent_status_returns_speech():
    intent = AvatarIntent(session_id="s", intent="status", args={}, text="", voice_ref="default")
    response = abilities.handle_intent(intent)
    assert "speech" in response
    assert "equity" in response["snapshot"]


def test_trader_api_trade_requires_valid_portfolio():
    app = FastAPI()
    app.include_router(trader_router, prefix="/v1")
    client = TestClient(app)

    buy_payload = {"symbol": "SAFE", "side": "buy", "quantity": 2, "price": 10.0}
    resp = client.post("/v1/trader/paper/trade", params={"token": "dev-token"}, json=buy_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True

    sell_payload = {"symbol": "SAFE", "side": "sell", "quantity": 5, "price": 9.0}
    resp = client.post("/v1/trader/paper/trade", params={"token": "dev-token"}, json=sell_payload)
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"]
