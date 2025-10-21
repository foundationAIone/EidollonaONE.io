"""SAFE placeholder for the legal framework engine.

This minimal implementation provides deterministic, side-effect-free
responses so higher-level trading systems can remain operational in
development environments without the extended legal framework package.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LegalCheckResult:
    compliant: bool
    advisories: List[str]
    jurisdiction: str
    timestamp: _dt.datetime
    context: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "compliant": self.compliant,
            "advisories": list(self.advisories),
            "jurisdiction": self.jurisdiction,
            "timestamp": self.timestamp.isoformat(),
            "context": dict(self.context),
        }


class LegalFrameworkEngine:
    """Deterministic SAFE placeholder legal checks.

    The placeholder enforces basic guard rails and records advisory messages
    but never blocks execution in development environments.
    """

    def __init__(self) -> None:
        self._jurisdiction = "SAFE-PLACEHOLDER"

    def evaluate_trade(self, trade: Dict[str, Any]) -> LegalCheckResult:
        symbol = trade.get("symbol", "UNKNOWN")
        risk = float(trade.get("risk", 0.5))
        advisories: List[str] = []
        if risk > 0.8:
            advisories.append("Risk exceeds recommended threshold for SAFE mode.")
        if trade.get("market") in {"restricted", "embargo"}:
            advisories.append("Market flagged for additional compliance review.")
        compliant = risk <= 0.95
        return LegalCheckResult(
            compliant=compliant,
            advisories=advisories or ["No critical compliance blockers."],
            jurisdiction=self._jurisdiction,
            timestamp=_dt.datetime.utcnow(),
            context={"symbol": symbol, "risk": risk},
        )

    def health_status(self) -> Dict[str, Any]:
        return {
            "status": "placeholder",
            "jurisdiction": self._jurisdiction,
            "checks_available": True,
        }


__all__ = ["LegalFrameworkEngine", "LegalCheckResult"]
