from __future__ import annotations

from typing import Any, Dict, Optional

from serplus.accounts import ensure_account
from serplus.ledger import ndjson_ledger as ledger
from serplus.minting import _authorized  # reuse internal helper
from utils.audit import audit_ndjson


def _normalize(amount: float, decimals: int) -> float:
    try:
        value = float(amount)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("amount must be numeric") from exc
    if value <= 0:
        raise ValueError("amount must be positive")
    return round(value, max(0, int(decimals)))


def transfer_asset(
    asset: str,
    *,
    source: str,
    target: str,
    amount: float,
    actor: Optional[str],
    policy: Dict[str, Any],
    reference: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if source == target:
        raise ValueError("source and target must differ")
    decimals = int(policy.get("decimals", 2))
    normalized = _normalize(amount, decimals)
    balances = ledger.balances(asset)
    source_balance = balances.get(source, 0.0)
    if source_balance < normalized - 1e-9:
        raise ValueError("insufficient balance for transfer")
    if actor not in (source, None) and not _authorized(actor, policy):
        raise PermissionError("actor is not permitted to transfer from this account")

    ensure_account(target, meta)
    entry = {
        "asset": asset,
        "type": "transfer",
        "amount": normalized,
        "decimals": decimals,
        "from": source,
        "to": target,
        "by": actor,
    }
    if reference:
        entry["reference"] = reference
    if meta:
        entry["meta"] = meta
    ledger.append(entry)
    audit_ndjson(
        "serplus_transfer",
        asset=asset,
        amount=normalized,
        source=source,
        target=target,
        actor=actor,
        reference=reference,
    )
    return entry


def ser_transfer(**kwargs: Any) -> Dict[str, Any]:
    from serplus.policy import get_ser_policy

    policy = get_ser_policy()
    return transfer_asset("SER", policy=policy, **kwargs)


__all__ = ["transfer_asset", "ser_transfer"]
