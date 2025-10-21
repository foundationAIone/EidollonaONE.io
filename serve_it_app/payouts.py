from __future__ import annotations

from typing import Dict

from utils.audit import audit_ndjson


def payout_paper_ser(booking_id: str, account: str, amount_cents: int) -> Dict[str, object]:
    receipt = {
        "booking_id": booking_id,
        "account": account,
        "amount_cents": int(amount_cents),
        "currency": "SER-paper",
    }
    audit_ndjson("serveit_payout_paper", **receipt)
    return receipt
