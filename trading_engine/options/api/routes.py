from __future__ import annotations

from typing import Dict, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from security.deps import require_token
from trading_engine.hedging_engine import delta_hedge_notional, hedge_frequency
from trading_engine.options.bachelier import greeks as bac_greeks, price as bac_price
from trading_engine.options.bsm import OptionKind, greeks as bs_greeks, implied_vol, price as bs_price
from trading_engine.options.pde_cn import crank_nicolson_euro
from utils.audit import audit_ndjson

router = APIRouter()


class PriceIn(BaseModel):
    model: Literal["bsm", "bachelier"] = "bsm"
    kind: OptionKind
    S: float
    K: float
    r: float
    q: float = 0.0
    sigma: float
    t: float


class IVIn(BaseModel):
    model: Literal["bsm", "bachelier"] = "bsm"
    kind: OptionKind
    S: float
    K: float
    r: float
    q: float = 0.0
    t: float
    target: float


class PDEIn(BaseModel):
    kind: Literal["call", "put", "custom"] = "call"
    S0: float
    K: float
    r: float
    q: float = 0.0
    sigma: float
    T: float
    M: int = 200
    N: int = 200


class HedgeIn(BaseModel):
    sovereign_gate: Literal["ROAD", "SHOULDER", "OFFROAD"] = "ROAD"
    gate: Literal["ALLOW", "REVIEW", "HOLD"] = "ALLOW"
    kind: OptionKind
    S: float
    K: float
    r: float
    q: float = 0.0
    sigma: float
    t: float
    qty: float


@router.post("/price")
def api_price(body: PriceIn, _: str = Depends(require_token)) -> Dict[str, object]:
    if body.model == "bsm":
        px = bs_price(body.kind, body.S, body.K, body.r, body.q, body.sigma, body.t)
        greeks = bs_greeks(body.kind, body.S, body.K, body.r, body.q, body.sigma, body.t)
    else:
        px = bac_price(body.kind, body.S, body.K, body.r, body.sigma, body.t)
        greeks = bac_greeks(body.kind, body.S, body.K, body.r, body.sigma, body.t)
    audit_ndjson("opt_price", **body.dict(), price=px, greeks=greeks)
    return {"ok": True, "price": px, "greeks": greeks}


@router.post("/iv")
def api_iv(body: IVIn, _: str = Depends(require_token)) -> Dict[str, object]:
    if body.model != "bsm":
        raise HTTPException(status_code=400, detail="IV supported for BSM only")
    iv = implied_vol(body.kind, body.S, body.K, body.r, body.q, body.t, body.target)
    audit_ndjson("opt_iv", **body.dict(), iv=iv)
    return {"ok": True, "iv": iv}


@router.post("/pde")
def api_pde(body: PDEIn, _: str = Depends(require_token)) -> Dict[str, object]:
    price, grid = crank_nicolson_euro(
        body.kind,
        body.S0,
        body.K,
        body.r,
        body.q,
        body.sigma,
        body.T,
        M=body.M,
        N=body.N,
    )
    audit_ndjson("opt_pde", **body.dict(), price=price)
    return {"ok": True, "price": price, "grid": grid}


@router.post("/hedge")
def api_hedge(body: HedgeIn, _: str = Depends(require_token)) -> Dict[str, object]:
    freq = hedge_frequency(body.sovereign_gate, body.gate)
    shares = delta_hedge_notional(
        body.kind,
        body.S,
        body.K,
        body.r,
        body.q,
        body.sigma,
        body.t,
        body.qty,
    )
    audit_ndjson("opt_hedge", **body.dict(), rehedge_minutes=freq, shares=shares)
    return {"ok": True, "rehedge_minutes": freq, "shares": shares}


__all__ = ["router"]
