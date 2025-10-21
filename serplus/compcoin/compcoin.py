from __future__ import annotations

from typing import Any, Dict, Optional

from serplus.ledger import ndjson_ledger as ledger
from serplus.minting import burn_asset, mint_asset
from serplus.policy import get_comp_policy, get_ser_policy
from serplus.transfers import transfer_asset


def comp_policy() -> Dict[str, Any]:
    policy = dict(get_comp_policy())
    if "ticker" not in policy:
        policy["ticker"] = "COMP"
    if "mint_authority" not in policy:
        policy["mint_authority"] = list(get_ser_policy().get("mint_authority", []))
    if "decimals" not in policy:
        policy["decimals"] = 2
    return policy


def comp_state(limit: int = 10) -> Dict[str, Any]:
    balances = ledger.balances("COMP")
    supply = ledger.total_supply("COMP")
    top = sorted(balances.items(), key=lambda item: item[1], reverse=True)[: max(1, limit)]
    return {
        "asset": "COMP",
        "supply": round(supply, 2),
        "holders": [{"account": k, "balance": v} for k, v in top],
    }


def mint_comp(to: str, amount: float, actor: Optional[str], reference: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return mint_asset(
        "COMP",
        to=to,
        amount=amount,
        actor=actor,
        reference=reference,
        meta=meta,
        policy=comp_policy(),
    )


def burn_comp(account: str, amount: float, actor: Optional[str], reference: Optional[str] = None) -> Dict[str, Any]:
    return burn_asset(
        "COMP",
        account=account,
        amount=amount,
        actor=actor,
        reference=reference,
        policy=comp_policy(),
    )


def transfer_comp(
    source: str,
    target: str,
    amount: float,
    actor: Optional[str],
    reference: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return transfer_asset(
        "COMP",
        source=source,
        target=target,
        amount=amount,
        actor=actor,
        reference=reference,
        meta=meta,
        policy=comp_policy(),
    )


__all__ = [
    "comp_policy",
    "comp_state",
    "mint_comp",
    "burn_comp",
    "transfer_comp",
]
