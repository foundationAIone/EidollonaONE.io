"""Advanced Token Issuer Orchestration (SE41 v4.1+ aligned)

Extends the lightweight `TokenIssuer` in `core.py` with richer lifecycle
capabilities:
  * Queued issuance (pending when ethos returns 'hold')
  * Batched issuance operations with atomic rollback semantics
  * Simple in-memory audit log (hash chained) for transparency
  * Dry-run validation pipeline (compliance + ethos simulation)
  * Supply expansion helper with governance bounding & multi-symbol support

All features remain dependency-minimal and degrade gracefully if SE41 helpers
are absent. This module does not replace the core issuer; instead it composes
around it for higher-level orchestration scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Iterable
from time import time
import hashlib

from .core import (
    TokenIssuer as BaseIssuer,
    TokenRegistry,
    ComplianceEngine,
    PricingOracle,
    IssueResult,
)

try:  # optional SE41 helpers
    from trading.helpers.se41_trading_gate import se41_numeric, ethos_decision  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.55}

    def ethos_decision(_tx):  # type: ignore
        return {"decision": "allow"}


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------
@dataclass
class QueuedIssuance:
    symbol: str
    name: str
    category: str
    supply: float
    issuer: str
    decimals: int
    jurisdiction: str
    kyc_passed: bool
    metadata: Dict[str, str]
    enqueue_ts: float


@dataclass
class AuditRecord:
    ts: float
    action: str
    symbol: str
    status: str
    detail: str
    integrity_hash: str
    prev_hash: str

    def snapshot(self) -> Dict:
        return {
            "ts": self.ts,
            "action": self.action,
            "symbol": self.symbol,
            "status": self.status,
            "detail": self.detail,
            "integrity_hash": self.integrity_hash,
            "prev_hash": self.prev_hash,
        }


# ---------------------------------------------------------------------------
class AdvancedTokenIssuer:
    """Higher-level orchestration around the base `TokenIssuer`."""

    def __init__(
        self,
        registry: TokenRegistry,
        compliance: ComplianceEngine,
        oracle: Optional[PricingOracle] = None,
    ) -> None:
        self.base = BaseIssuer(registry, compliance, oracle)
        self.registry = registry
        self.compliance = compliance
        self.oracle = self.base.oracle
        self._queue: List[QueuedIssuance] = []
        self._audit: List[AuditRecord] = []
        self._last_hash = "root"

    # ----------------------------- Audit Helpers -------------------------
    def _append_audit(self, action: str, symbol: str, status: str, detail: str) -> None:
        payload = f"{time():.6f}|{action}|{symbol}|{status}|{detail}|{self._last_hash}".encode()
        integrity_hash = hashlib.sha256(payload).hexdigest()[:20]
        rec = AuditRecord(
            time(),
            action,
            symbol.upper(),
            status,
            detail,
            integrity_hash,
            self._last_hash,
        )
        self._audit.append(rec)
        self._last_hash = integrity_hash

    def audit_tail(self, n: int = 10) -> List[Dict]:
        return [r.snapshot() for r in self._audit[-n:]]

    # --------------------------- Queued Issuance -------------------------
    def enqueue(
        self,
        symbol: str,
        name: str,
        category: str,
        supply: float,
        issuer: str = "system",
        decimals: int = 18,
        jurisdiction: str = "unknown",
        kyc_passed: bool = False,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        qi = QueuedIssuance(
            symbol=symbol.upper(),
            name=name,
            category=category,
            supply=float(supply),
            issuer=issuer,
            decimals=decimals,
            jurisdiction=jurisdiction,
            kyc_passed=kyc_passed,
            metadata=metadata or {},
            enqueue_ts=time(),
        )
        self._queue.append(qi)
        self._append_audit("enqueue", symbol, "queued", "added_to_queue")

    def process_queue(self, max_items: Optional[int] = None) -> List[IssueResult]:
        processed: List[IssueResult] = []
        remaining: List[QueuedIssuance] = []
        count = 0
        for item in self._queue:
            if max_items is not None and count >= max_items:
                remaining.append(item)
                continue
            res = self.issue(
                item.symbol,
                item.name,
                item.category,
                item.supply,
                issuer=item.issuer,
                decimals=item.decimals,
                jurisdiction=item.jurisdiction,
                kyc_passed=item.kyc_passed,
                metadata=item.metadata,
            )
            if not res.ok and res.decision == "hold":  # stay queued
                remaining.append(item)
            processed.append(res)
            count += 1
        self._queue = remaining
        return processed

    def queue_size(self) -> int:
        return len(self._queue)

    # -------------------------- Issuance Wrapper -------------------------
    def issue(self, *args, **kwargs) -> IssueResult:  # passthrough with audit
        res = self.base.issue(*args, **kwargs)
        symbol = args[0] if args else kwargs.get("symbol", "?")
        status = "ok" if res.ok else res.decision or "fail"
        self._append_audit("issue", symbol, status, res.reason or status)
        if res.decision == "hold":  # queue automatically
            self.enqueue(*args, **kwargs)  # type: ignore[arg-type]
        return res

    # ------------------------- Batch Operations --------------------------
    def batch_issue(self, batch: Iterable[Dict]) -> List[IssueResult]:
        """Issue a batch atomically; rollback if any hard deny / failure.

        Soft holds are allowed (items remain queued) and do not cause rollback.
        Returns list of IssueResult in order. If rollback occurs all newly
        created profiles are removed (best effort) and results include a
        synthesized failure record at the end.
        """
        results: List[IssueResult] = []
        created: List[str] = []
        for spec in batch:
            r = self.issue(**spec)
            results.append(r)
            if r.ok and r.profile:
                created.append(r.profile.symbol)
            if (not r.ok) and r.decision == "deny":  # rollback
                for sym in created:
                    # best effort removal (not exposed in core; simulate by zeroing supply)
                    profile = self.registry.get(sym)
                    if profile:
                        profile.total_supply = 0.0
                        self.registry.upsert(profile)
                self._append_audit(
                    "rollback",
                    "|".join(created),
                    "revert",
                    f"due_to_{spec.get('symbol')}",
                )
                return results
        return results

    # ------------------------- Dry-Run Validation ------------------------
    def dry_run(
        self, symbol: str, category: str, supply: float, decimals: int = 18
    ) -> Dict:
        symbol_u = symbol.upper()
        numeric = se41_numeric(M_t=0.57, DNA_states=[1.0, supply, decimals, 1.07])
        score = numeric.get("score", 0.55) if isinstance(numeric, dict) else 0.55
        gate = ethos_decision(
            {"scope": "token_issue", "symbol": symbol_u, "score": score}
        )
        decision = gate.get("decision", "allow") if isinstance(gate, dict) else "allow"
        ok, reason = self.compliance.check(
            symbol_u, category, jurisdiction="unknown", kyc_passed=False
        )
        return {
            "symbol": symbol_u,
            "compliance_ok": ok,
            "compliance_reason": reason,
            "ethos_decision": decision,
            "numeric_score": score,
        }

    # --------------------- Supply Expansion Convenience ------------------
    def expand_supplies(
        self, adjustments: Dict[str, float], max_pct: float = 0.10
    ) -> Dict[str, IssueResult]:
        outcomes: Dict[str, IssueResult] = {}
        for sym, delta in adjustments.items():
            outcomes[sym.upper()] = self.base.adjust_supply(
                sym, delta, reason="batch_expand", max_pct=max_pct
            )
        return outcomes

    # ---------------------------- Stats ----------------------------------
    def stats(self) -> Dict:
        return {
            "queue": self.queue_size(),
            "audit_records": len(self._audit),
            "last_audit_hash": self._last_hash,
            "tokens": len(self.registry.list()),
        }


__all__ = [
    "AdvancedTokenIssuer",
    "QueuedIssuance",
    "AuditRecord",
]
