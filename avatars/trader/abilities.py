from __future__ import annotations

from typing import Any, Dict, cast

from utils.audit import audit_ndjson

from avatars.orchestrator.api import AvatarIntent, ModuleAdapter

from .ledger import TradeSide, dashboard_widget, portfolio_snapshot, record_trade


def _ability_status(_: AvatarIntent) -> Dict[str, Any]:
    snap = portfolio_snapshot()
    cash = snap.get("cash", 0.0)
    equity = snap.get("equity", cash)
    realized = snap.get("realized_pnl", 0.0)
    unrealized = snap.get("unrealized_pnl", 0.0)
    positions = snap.get("positions", {})
    speech = (
        f"Paper account equity {equity:.2f} with cash {cash:.2f}. "
        f"Realized PnL {realized:.2f}, unrealized drift {unrealized:.2f}. "
        f"Holding {len(positions)} positions."
    )
    return {"speech": speech, "snapshot": snap}


def _ability_positions(_: AvatarIntent) -> Dict[str, Any]:
    widget = dashboard_widget()
    return {
        "speech": f"Tracked {len(widget['rows'])} open paper positions." if widget.get("rows") else "No open paper positions.",
        "widget": widget,
    }


def _ability_paper_trade(intent: AvatarIntent) -> Dict[str, Any]:
    args = intent.args
    symbol = str(args.get("symbol") or args.get("ticker") or "SER").upper()
    side_value = str(args.get("side") or "buy").lower()
    if side_value not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    side = cast(TradeSide, side_value)
    quantity = float(args.get("quantity", 1.0))
    price = float(args.get("price", args.get("price_usd", 10.0)))
    state = record_trade(symbol, side, quantity, price, session_id=intent.session_id)
    speech = (
        f"Paper {side} {quantity:.4f} {symbol} at {price:.2f}. "
        f"Cash now {state['cash']:.2f}, realized PnL {state['realized_pnl']:.2f}."
    )
    return {
        "speech": speech,
        "state": state,
    }


def _intent_from_text(payload: AvatarIntent) -> str:
    text = (payload.text or "").lower()
    if "buy" in text or "sell" in text or "trade" in text:
        return "paper_trade"
    if "position" in text:
        return "positions"
    return "status"


def _route_intent(payload: AvatarIntent) -> Dict[str, Any]:
    intent = payload.intent or _intent_from_text(payload)
    if intent == "status":
        return _ability_status(payload)
    if intent == "positions":
        return _ability_positions(payload)
    if intent == "paper_trade":
        return _ability_paper_trade(payload)
    raise ValueError(f"unsupported intent: {intent}")


def handle_intent(payload: AvatarIntent) -> Dict[str, Any]:
    try:
        response = _route_intent(payload)
    except ValueError as exc:
        return {"speech": str(exc), "error": str(exc)}
    audit_ndjson(
        "trader_avatar_intent",
        intent=payload.intent or payload.text,
        session_id=payload.session_id,
        avatar_id="trader",
    )
    return response


def get_state() -> Dict[str, Any]:
    return portfolio_snapshot()


def get_dashboard() -> Dict[str, Any]:
    return {"widgets": [dashboard_widget()], "snapshot": portfolio_snapshot()}


def get_module_adapter() -> ModuleAdapter:
    return ModuleAdapter(
        avatar_id="trader",
        handle_intent=handle_intent,
        fetch_state=get_state,
        fetch_dashboard=get_dashboard,
        stream_events=None,
    )
