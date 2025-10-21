from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from security.deps import require_token
from utils.audit import audit_ndjson
from black_scholes.black_scholes_model import implied_vol, greeks, price

router = APIRouter()


class BSIn(BaseModel):
    kind: Literal["call", "put"]
    S: float
    K: float
    r: float
    q: float
    sigma: float
    t: float


class IVIn(BaseModel):
    kind: Literal["call", "put"]
    S: float
    K: float
    r: float
    q: float
    t: float
    target: float


@router.post("/price")
def api_price(payload: BSIn, _: str = Depends(require_token)):
    quote = price(payload.kind, payload.S, payload.K, payload.r, payload.q, payload.sigma, payload.t)
    g = greeks(payload.kind, payload.S, payload.K, payload.r, payload.q, payload.sigma, payload.t)
    audit_ndjson("bs_price", **payload.dict(), price=quote, greeks=g)
    return {"ok": True, "price": quote, "greeks": g}


@router.post("/iv")
def api_iv(payload: IVIn, _: str = Depends(require_token)):
    iv = implied_vol(
        payload.kind,
        payload.S,
        payload.K,
        payload.r,
        payload.q,
        payload.t,
        payload.target,
    )
    if math.isnan(iv):
        raise HTTPException(status_code=400, detail="could_not_solve_iv")
    audit_ndjson("bs_iv", **payload.dict(), iv=iv)
    return {"ok": True, "iv": iv}
