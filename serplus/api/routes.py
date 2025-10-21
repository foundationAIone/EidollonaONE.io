from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from security.deps import require_token
from serplus import (
    allocation_health,
    get_ser_policy,
    ledger_snapshot,
    plan_allocation,
    ser_burn,
    ser_mint,
)
from serplus.accounts import all_accounts
from serplus.api.models import (
    AllocationPlanRequest,
    BurnRequest,
    MintRequest,
    NFTRegisterRequest,
    TransferRequest,
)
from serplus.compcoin import comp_policy, comp_state, mint_comp, burn_comp, transfer_comp
from serplus.ledger import ndjson_ledger as ledger
from serplus.nft import register_token, tokens_by_owner, all_tokens as nft_all_tokens
from serplus.policy import get_comp_policy
from serplus.transfers import ser_transfer

router = APIRouter(prefix="/ser", tags=["serplus"])

OPERATOR = os.getenv("OPERATOR", "programmerONE")


def _actor(requested: Optional[str]) -> Optional[str]:
    return requested or OPERATOR


def _wrap_errors(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/policy")
def read_policies(_: str = Depends(require_token)) -> Dict[str, Any]:
    return {"ser": get_ser_policy(), "comp": comp_policy(), "raw_comp": get_comp_policy()}


@router.get("/state")
def read_state(limit: int = Query(25, ge=1, le=500), _: str = Depends(require_token)) -> Dict[str, Any]:
    entries = ledger.iter_entries(limit)
    supply = ledger.total_supply("SER")
    balances = ledger.balances("SER")
    return {
        "asset": "SER",
        "supply": round(supply, 2),
        "entry_count": len(entries),
        "recent_entries": entries,
        "balances": balances,
        "allocation": allocation_health("SER"),
    }


@router.get("/ledger")
def read_ledger(limit: int = Query(100, ge=1, le=5000), _: str = Depends(require_token)) -> Dict[str, Any]:
    return {"entries": ledger.iter_entries(limit)}


@router.get("/balances")
def read_balances(asset: str = Query("SER"), _: str = Depends(require_token)) -> Dict[str, Any]:
    asset = asset.upper()
    return {"asset": asset, "balances": ledger.balances(asset)}


@router.get("/supply")
def read_supply(asset: str = Query("SER"), _: str = Depends(require_token)) -> Dict[str, Any]:
    asset = asset.upper()
    return {"asset": asset, "supply": ledger.total_supply(asset)}


@router.get("/accounts")
def read_accounts(_: str = Depends(require_token)) -> Dict[str, Any]:
    return {"accounts": all_accounts()}


@router.post("/mint")
def mint_serplus(payload: MintRequest, _: str = Depends(require_token)) -> Dict[str, Any]:
    entry = _wrap_errors(
        ser_mint,
        to=payload.to,
        amount=payload.amount,
        actor=_actor(payload.actor),
        reference=payload.reference,
        meta=payload.meta,
    )
    return {"entry": entry, "supply": ledger.total_supply("SER")}


@router.post("/burn")
def burn_serplus(payload: BurnRequest, _: str = Depends(require_token)) -> Dict[str, Any]:
    entry = _wrap_errors(
        ser_burn,
        account=payload.account,
        amount=payload.amount,
        actor=_actor(payload.actor),
        reference=payload.reference,
    )
    return {"entry": entry, "supply": ledger.total_supply("SER")}


@router.post("/transfer")
def transfer_serplus(payload: TransferRequest, _: str = Depends(require_token)) -> Dict[str, Any]:
    entry = _wrap_errors(
        ser_transfer,
        source=payload.source,
        target=payload.target,
        amount=payload.amount,
        actor=_actor(payload.actor),
        reference=payload.reference,
        meta=payload.meta,
    )
    return {"entry": entry, "balances": ledger.balances("SER")}


@router.post("/allocation/plan")
def plan_route(payload: AllocationPlanRequest, _: str = Depends(require_token)) -> Dict[str, Any]:
    return {"plan": plan_allocation(payload.amount)}


@router.get("/allocation/snapshot")
def allocation_snapshot(limit: int = Query(10, ge=1, le=50), _: str = Depends(require_token)) -> Dict[str, Any]:
    return ledger_snapshot(limit=limit)


@router.get("/comp/state")
def read_comp_state(limit: int = Query(10, ge=1, le=50), _: str = Depends(require_token)) -> Dict[str, Any]:
    return comp_state(limit)


@router.post("/comp/mint")
def mint_compcoin(payload: MintRequest, _: str = Depends(require_token)) -> Dict[str, Any]:
    entry = _wrap_errors(
        mint_comp,
        to=payload.to,
        amount=payload.amount,
        actor=_actor(payload.actor),
        reference=payload.reference,
        meta=payload.meta,
    )
    return {"entry": entry, "supply": ledger.total_supply("COMP")}


@router.post("/comp/burn")
def burn_compcoin(payload: BurnRequest, _: str = Depends(require_token)) -> Dict[str, Any]:
    entry = _wrap_errors(
        burn_comp,
        account=payload.account,
        amount=payload.amount,
        actor=_actor(payload.actor),
        reference=payload.reference,
    )
    return {"entry": entry, "supply": ledger.total_supply("COMP")}


@router.post("/comp/transfer")
def transfer_compcoin(payload: TransferRequest, _: str = Depends(require_token)) -> Dict[str, Any]:
    entry = _wrap_errors(
        transfer_comp,
        source=payload.source,
        target=payload.target,
        amount=payload.amount,
        actor=_actor(payload.actor),
        reference=payload.reference,
        meta=payload.meta,
    )
    return {"entry": entry, "balances": ledger.balances("COMP")}


@router.get("/nft")
def list_nfts(owner: Optional[str] = Query(None), _: str = Depends(require_token)) -> Dict[str, Any]:
    if owner:
        return {"tokens": tokens_by_owner(owner)}
    return {"tokens": nft_all_tokens()}


@router.post("/nft/register")
def register_nft(payload: NFTRegisterRequest, _: str = Depends(require_token)) -> Dict[str, Any]:
    record = _wrap_errors(
        register_token,
        token_id=payload.token_id,
        owner=payload.owner,
        meta=payload.meta,
    )
    return {"token": record}


__all__ = ["router"]
