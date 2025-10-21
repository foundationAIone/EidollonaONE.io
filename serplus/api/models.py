from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

# ----- Pydantic v1/v2 compatibility -----------------------------------------
try:  # v2
    from pydantic import field_validator, model_validator  # type: ignore

    _V2 = True
except Exception:  # pragma: no cover - fallback to v1
    from pydantic import validator as field_validator  # type: ignore
    from pydantic import root_validator as model_validator  # type: ignore

    _V2 = False

# Currency precision (simulation / paper mode) — keep consistent with SER policy
_DECIMALS = 2


def _round_amt(value: float) -> float:
    try:
        return round(float(value), _DECIMALS)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("amount must be numeric") from exc


def _norm_acct(raw: Optional[str]) -> str:
    account = (raw or "").strip()
    if not account:
        raise ValueError("account identifier is required")
    return account


class MintRequest(BaseModel):
    """Request to mint SER (simulation/paper mode)."""

    to: str = Field(..., description="Recipient account identifier")
    amount: float = Field(..., gt=0, description="Amount of tokens to mint (rounded to 2dp)")
    actor: Optional[str] = Field(None, description="Operator requesting the mint")
    reference: Optional[str] = Field(None, description="Optional human-readable reference")
    meta: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for the recipient account")

    @field_validator("to")
    def _require_to(cls, value: str) -> str:  # noqa: N805
        return _norm_acct(value)

    @field_validator("amount")
    def _round_amount(cls, value: float) -> float:  # noqa: N805
        return _round_amt(value)


class TransferRequest(BaseModel):
    """Request to transfer SER (or other asset) between accounts."""

    source: str = Field(..., description="Source account identifier")
    target: str = Field(..., description="Target account identifier")
    amount: float = Field(..., gt=0, description="Amount to transfer (rounded to 2dp)")
    actor: Optional[str] = Field(None, description="Operator authorizing the transfer")
    reference: Optional[str] = Field(None, description="Optional transfer reference")
    meta: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")

    @field_validator("source", "target")
    def _require_accounts(cls, value: str) -> str:  # noqa: N805
        return _norm_acct(value)

    @field_validator("amount")
    def _round_transfer_amount(cls, value: float) -> float:  # noqa: N805
        return _round_amt(value)

    if _V2:  # pragma: no branch - evaluated at import time

        @model_validator(mode="after")  # type: ignore[misc]
        def _prevent_self_transfer_v2(self):  # noqa: N805
            if self.source == self.target:
                raise ValueError("source and target must differ")
            return self

        _prevent_self_transfer = _prevent_self_transfer_v2

    else:

        @model_validator  # type: ignore[misc]
        def _prevent_self_transfer_v1(cls, values):  # noqa: N805
            if values.get("source") == values.get("target"):
                raise ValueError("source and target must differ")
            return values

        _prevent_self_transfer = _prevent_self_transfer_v1


class BurnRequest(BaseModel):
    """Request to burn SER from an account (paper mode)."""

    account: str = Field(..., description="Account to burn tokens from")
    amount: float = Field(..., gt=0, description="Amount of tokens to burn (rounded to 2dp)")
    actor: Optional[str] = Field(None, description="Operator requesting the burn")
    reference: Optional[str] = Field(None, description="Optional reference")

    @field_validator("account")
    def _require_account(cls, value: str) -> str:  # noqa: N805
        return _norm_acct(value)

    @field_validator("amount")
    def _round_burn_amount(cls, value: float) -> float:  # noqa: N805
        return _round_amt(value)


class AllocationPlanRequest(BaseModel):
    """Plan an allocation amount across buckets (paper mode)."""

    amount: float = Field(0.0, ge=0, description="Total amount to plan across allocation buckets")

    @field_validator("amount")
    def _round_plan_amount(cls, value: float) -> float:  # noqa: N805
        return _round_amt(value)


class NFTRegisterRequest(BaseModel):
    """Register an NFT in the local registry (simulation)."""

    token_id: str = Field(..., description="Unique token identifier")
    owner: str = Field(..., description="Owner handle")
    meta: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata (e.g., name, tier)")

    @field_validator("token_id", "owner")
    def _require_fields(cls, value: str) -> str:  # noqa: N805
        return _norm_acct(value)


__all__ = [
    "MintRequest",
    "TransferRequest",
    "BurnRequest",
    "AllocationPlanRequest",
    "NFTRegisterRequest",
]
