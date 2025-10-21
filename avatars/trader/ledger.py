from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, cast

from utils.audit import audit_ndjson

TradeSide = Literal["buy", "sell"]

State = Dict[str, Any]
PositionPayload = Dict[str, Any]
PositionsState = Dict[str, PositionPayload]
HistoryEntry = Dict[str, Any]

_LEDGER_PATH = Path("logs/trader_paper_ledger.json")
_DEFAULT_CASH = 100_000.0


@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"symbol": self.symbol, "quantity": self.quantity, "avg_price": self.avg_price}


def _default_state() -> State:
    return {
        "cash": _DEFAULT_CASH,
        "positions": {},
        "realized_pnl": 0.0,
        "history": [],
    }


def _load_state() -> State:
    if not _LEDGER_PATH.exists():
        return _default_state()
    try:
        with _LEDGER_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                data.setdefault("cash", _DEFAULT_CASH)
                data.setdefault("positions", {})
                data.setdefault("realized_pnl", 0.0)
                data.setdefault("history", [])
                return data
    except Exception:
        pass
    return _default_state()


def _save_state(state: State) -> None:
    try:
        os.makedirs(_LEDGER_PATH.parent, exist_ok=True)
        with _LEDGER_PATH.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _update_position(position: Position, side: TradeSide, quantity: float, price: float) -> Position:
    if side == "buy":
        total_cost = position.avg_price * position.quantity + price * quantity
        new_qty = position.quantity + quantity
        avg_price = price if new_qty <= 0 else total_cost / max(new_qty, 1e-9)
        return Position(symbol=position.symbol, quantity=new_qty, avg_price=avg_price)

    # Sell path: reduce quantity, average price unchanged
    new_qty = max(0.0, position.quantity - quantity)
    return Position(symbol=position.symbol, quantity=new_qty, avg_price=position.avg_price)


def _position_lookup(state: State, symbol: str) -> Position:
    positions = state.get("positions", {})
    if isinstance(positions, dict) and symbol in positions:
        data = positions[symbol]
        if isinstance(data, dict):
            return Position(
                symbol=symbol,
                quantity=float(data.get("quantity", 0.0)),
                avg_price=float(data.get("avg_price", 0.0)),
            )
    return Position(symbol=symbol)


def record_trade(symbol: str, side: TradeSide, quantity: float, price: float, *, session_id: Optional[str] = None) -> State:
    quantity = max(0.0, float(quantity))
    price = max(0.0, float(price))
    state = _load_state()

    if quantity <= 0 or price <= 0:
        raise ValueError("quantity and price must be positive")

    position = _position_lookup(state, symbol)
    cost = quantity * price

    if side == "buy":
        if cost > float(state.get("cash", 0.0)):
            raise ValueError("insufficient paper cash")
        state["cash"] = float(state.get("cash", 0.0)) - cost
        position = _update_position(position, side, quantity, price)
    else:
        if quantity > position.quantity:
            raise ValueError("insufficient position to sell")
        state["cash"] = float(state.get("cash", 0.0)) + cost
        pnl = (price - position.avg_price) * quantity
        state["realized_pnl"] = float(state.get("realized_pnl", 0.0)) + pnl
        position = _update_position(position, side, quantity, price)

    positions = cast(PositionsState, state.setdefault("positions", {}))
    if position.quantity <= 0:
        positions.pop(symbol, None)
    else:
        positions[symbol] = position.to_dict()

    history = cast(List[HistoryEntry], state.setdefault("history", []))
    entry = {
        "ts": time.time(),
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "value": cost,
        "session": session_id,
    }
    history.append(entry)
    # Keep last 200 trades to bound file size
    if len(history) > 200:
        del history[:-200]

    _save_state(state)
    audit_ndjson(
        "trader_paper_trade",
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        cash=float(state.get("cash", 0.0)),
        realized=float(state.get("realized_pnl", 0.0)),
        session=session_id,
    )
    return state


def portfolio_snapshot() -> State:
    state = _load_state()
    positions_raw = state.get("positions", {})
    positions: PositionsState = positions_raw if isinstance(positions_raw, dict) else {}
    total_value = float(state.get("cash", 0.0))
    unrealized = 0.0
    exposure: Dict[str, float] = {}
    for symbol, data in positions.items():
        if not isinstance(data, dict):
            continue
        qty = float(data.get("quantity", 0.0))
        avg_price = float(data.get("avg_price", 0.0))
        position_value = qty * avg_price
        unrealized += position_value * 0.01  # placeholder drift for SAFE demo
        total_value += position_value
        exposure[symbol] = position_value
    return {
        "cash": float(state.get("cash", 0.0)),
        "positions": positions,
        "realized_pnl": float(state.get("realized_pnl", 0.0)),
        "unrealized_pnl": unrealized,
        "equity": total_value,
        "exposure": exposure,
        "history": state.get("history", []),
    }


def dashboard_widget() -> Dict[str, Any]:
    snap = portfolio_snapshot()
    rows: List[Dict[str, Any]] = []
    positions_raw = snap.get("positions", {})
    positions: PositionsState = positions_raw if isinstance(positions_raw, dict) else {}
    for symbol, data in positions.items():
        if not isinstance(data, dict):
            continue
        rows.append(
            {
                "symbol": symbol,
                "quantity": round(float(data.get("quantity", 0.0)), 4),
                "avg_price": round(float(data.get("avg_price", 0.0)), 2),
            }
        )
    rows.sort(key=lambda row: row.get("symbol", ""))
    return {
        "id": "w_trader_positions",
        "type": "table",
        "title": "Trader Avatar Positions",
        "columns": [
            {"key": "symbol", "label": "Symbol"},
            {"key": "quantity", "label": "Qty"},
            {"key": "avg_price", "label": "Avg Price"},
        ],
        "rows": rows,
        "pageSize": max(1, min(10, len(rows) or 1)),
        "total": None,
    }
