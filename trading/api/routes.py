from __future__ import annotations

from typing import Optional, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from security.deps import require_token
from utils.audit import audit_ndjson

from avatars.trader.ledger import TradeSide, portfolio_snapshot, record_trade

router = APIRouter(prefix="/trader", tags=["trader"])


class TradeIn(BaseModel):
    symbol: str = Field(..., min_length=1, description="Ticker symbol (paper only)")
    side: str = Field(..., pattern="^(buy|sell)$", description="Trade direction")
    quantity: float = Field(1.0, gt=0, description="Units to trade")
    price: float = Field(10.0, gt=0, description="Price in SER equivalent")
    session_id: Optional[str] = Field(None, description="Optional orchestrator session ID")


@router.get("/paper/status")
def paper_status(token: str = Depends(require_token)):
    snap = portfolio_snapshot()
    audit_ndjson(
        "trader_api_status",
        token=token,
        equity=snap.get("equity"),
        positions=len((snap.get("positions") or {})),
    )
    return {"ok": True, "snapshot": snap}


@router.post("/paper/trade")
def paper_trade(payload: TradeIn, token: str = Depends(require_token)):
    try:
        state = record_trade(
            payload.symbol.upper(),
            cast(TradeSide, payload.side.lower()),
            payload.quantity,
            payload.price,
            session_id=payload.session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit_ndjson(
        "trader_api_trade",
        token=token,
        symbol=payload.symbol.upper(),
        side=payload.side.lower(),
        quantity=payload.quantity,
        price=payload.price,
    )
    return {"ok": True, "state": state}
