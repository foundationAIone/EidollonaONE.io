from __future__ import annotations

from typing import Any, Dict, Optional

from serplus.accounts import ensure_account
from serplus.ledger import ndjson_ledger as ledger
from utils.audit import audit_ndjson


def _normalize_amount(amount: float, decimals: int) -> float:
    try:
        value = float(amount)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("amount must be numeric") from exc
    if value <= 0:
        raise ValueError("amount must be positive")
    return round(value, max(0, int(decimals)))


def _authorized(actor: Optional[str], policy: Dict[str, Any]) -> bool:
    allowed = policy.get("mint_authority") or []
    if not allowed:  # no restriction defined
        return True
    if actor is None:
        return False
    return actor in allowed


def _ensure_authority(actor: Optional[str], policy: Dict[str, Any]) -> None:
    if not _authorized(actor, policy):
        raise PermissionError("actor is not authorized for this operation")


def _supply_cap_ok(asset: str, amount: float, policy: Dict[str, Any]) -> bool:
    cap = policy.get("max_supply")
    if cap is None:
        return True
    return ledger.total_supply(asset) + amount <= float(cap) + 1e-9


def mint_asset(
    asset: str,
    *,
    to: str,
    amount: float,
    actor: Optional[str],
    policy: Dict[str, Any],
    reference: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    decimals = int(policy.get("decimals", 2))
    normalized = _normalize_amount(amount, decimals)
    _ensure_authority(actor, policy)
    if not _supply_cap_ok(asset, normalized, policy):
        raise ValueError("max supply would be exceeded")

    ensure_account(to, meta)
    entry = {
        "asset": asset,
        "type": "mint",
        "amount": normalized,
        "decimals": decimals,
        "to": to,
        "by": actor,
    }
    if reference:
        entry["reference"] = reference
    if meta:
        entry["meta"] = meta
    ledger.append(entry)
    audit_ndjson(
        "serplus_mint",
        asset=asset,
        amount=normalized,
        to=to,
        actor=actor,
        reference=reference,
    )
    return entry


def burn_asset(
    asset: str,
    *,
    account: str,
    amount: float,
    actor: Optional[str],
    policy: Dict[str, Any],
    reference: Optional[str] = None,
) -> Dict[str, Any]:
    decimals = int(policy.get("decimals", 2))
    normalized = _normalize_amount(amount, decimals)
    balances = ledger.balances(asset)
    current_balance = balances.get(account, 0.0)
    if current_balance < normalized - 1e-9:
        raise ValueError("insufficient balance to burn")
    # allow either the account holder or policy authority
    if actor not in (account, None) and not _authorized(actor, policy):
        raise PermissionError("actor is not permitted to burn from this account")

    entry = {
        "asset": asset,
        "type": "burn",
        "amount": normalized,
        "decimals": decimals,
        "from": account,
        "by": actor,
    }
    if reference:
        entry["reference"] = reference
    ledger.append(entry)
    audit_ndjson(
        "serplus_burn",
        asset=asset,
        amount=normalized,
        account=account,
        actor=actor,
        reference=reference,
    )
    return entry


def ser_mint(**kwargs: Any) -> Dict[str, Any]:
    from serplus.policy import get_ser_policy  # local import to avoid cycles

    policy = get_ser_policy()
    return mint_asset("SER", policy=policy, **kwargs)


def ser_burn(**kwargs: Any) -> Dict[str, Any]:
    from serplus.policy import get_ser_policy

    policy = get_ser_policy()
    return burn_asset("SER", policy=policy, **kwargs)


__all__ = [
    "mint_asset",
    "burn_asset",
    "ser_mint",
    "ser_burn",
]
