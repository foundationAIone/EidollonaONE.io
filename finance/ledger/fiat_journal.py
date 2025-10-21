"""Simplified fiat journal used by SAFE accounting routines."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

__all__ = ["JournalEntry", "FiatJournal"]


@dataclass
class JournalEntry:
    """Immutable representation of a fiat ledger entry."""

    timestamp: datetime
    account: str
    amount: float
    currency: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FiatJournal:
    """Minimal ledger capable of recording deterministic journal entries."""

    def __init__(self, currency: str = "USD") -> None:
        self._currency = currency
        self._entries: List[JournalEntry] = []

    def record(
        self,
        account: str,
        amount: float,
        *,
        currency: Optional[str] = None,
        description: str = "",
    ) -> JournalEntry:
        entry = JournalEntry(
            timestamp=datetime.utcnow(),
            account=str(account),
            amount=float(amount),
            currency=str(currency or self._currency),
            description=str(description),
        )
        self._entries.append(entry)
        return entry

    def balance(self, account: Optional[str] = None) -> float:
        entries = self._entries if account is None else self._filter(account)
        return sum(entry.amount for entry in entries)

    def entries(self) -> List[JournalEntry]:
        return list(self._entries)

    def export(self) -> List[Dict[str, Any]]:
        return [entry.to_dict() for entry in self._entries]

    def _filter(self, account: str) -> Iterable[JournalEntry]:
        return [entry for entry in self._entries if entry.account == account]
