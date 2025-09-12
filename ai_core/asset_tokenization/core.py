"""Core tokenization domain models & services (SE41 v4.1+ aligned).

Lightweight, dependency-minimal primitives for asset token lifecycle:
  - TokenProfile: definition & governance metadata
  - TokenRegistry: integrity-tracked catalog
  - ComplianceEngine: simple allow/deny gating (KYC / jurisdiction / watchlist)
  - PricingOracle: sliding window of price observations
  - TokenIssuer: orchestrates issuance flows with ethos gating and SE41 numeric

No external persistence: callers can persist registry snapshots as needed.
Falls back safely if SE41 helpers unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from time import time
import hashlib

try:  # SE41 helpers (optional)
    from trading.helpers.se41_trading_gate import se41_numeric, ethos_decision  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return {"score": 0.55}

    def ethos_decision(_tx):  # type: ignore
        return {"decision": "allow"}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class TokenProfile:
    symbol: str
    name: str
    category: str  # e.g. equity, real_estate, commodity, credit, utility
    total_supply: float
    decimals: int = 18
    issuer: str = "system"
    created_ts: float = field(default_factory=time)
    mutable: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)
    governance: Dict[str, float] = field(default_factory=dict)  # e.g. risk scores
    integrity_hash: str = ""

    def snapshot(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "category": self.category,
            "total_supply": self.total_supply,
            "decimals": self.decimals,
            "issuer": self.issuer,
            "created_ts": self.created_ts,
            "mutable": self.mutable,
            "metadata": dict(self.metadata),
            "governance": dict(self.governance),
            "integrity_hash": self.integrity_hash,
        }


# ---------------------------------------------------------------------------
@dataclass
class IssueResult:
    ok: bool
    reason: str = ""
    profile: Optional[TokenProfile] = None
    decision: str = "allow"


# ---------------------------------------------------------------------------
class TokenRegistry:
    """In-memory token registry with integrity hashing."""

    def __init__(self) -> None:
        self._tokens: Dict[str, TokenProfile] = {}
        self._integrity_index: Dict[str, str] = {}

    def upsert(self, profile: TokenProfile) -> TokenProfile:
        profile.integrity_hash = self._compute_hash(profile)
        self._tokens[profile.symbol.upper()] = profile
        self._integrity_index[profile.symbol.upper()] = profile.integrity_hash
        return profile

    def get(self, symbol: str) -> Optional[TokenProfile]:
        return self._tokens.get(symbol.upper())

    def list(self) -> List[TokenProfile]:
        return list(self._tokens.values())

    def verify(self, symbol: str) -> bool:
        p = self.get(symbol)
        if not p:
            return False
        return (
            p.integrity_hash
            == self._integrity_index.get(symbol.upper())
            == self._compute_hash(p)
        )

    @staticmethod
    def _compute_hash(profile: TokenProfile) -> str:
        h = hashlib.sha256(
            f"{profile.symbol}|{profile.name}|{profile.total_supply:.8f}|{profile.decimals}|{profile.category}|{profile.mutable}".encode()
        ).hexdigest()[:16]
        return h


# ---------------------------------------------------------------------------
class ComplianceEngine:
    """Minimal compliance gating (allow/deny lists & risk flags)."""

    def __init__(self) -> None:
        self._allow_symbols: set[str] = set()
        self._deny_symbols: set[str] = set()
        self._jurisdiction_denies: set[str] = {"unknown", "sanctioned"}
        self._kyc_required_categories: set[str] = {"equity", "credit"}

    def allow(self, symbol: str) -> None:
        self._allow_symbols.add(symbol.upper())

    def deny(self, symbol: str) -> None:
        self._deny_symbols.add(symbol.upper())

    def check(
        self, symbol: str, category: str, jurisdiction: str, kyc_passed: bool
    ) -> Tuple[bool, str]:
        if symbol.upper() in self._deny_symbols:
            return False, "deny_list"
        if symbol.upper() in self._allow_symbols:
            return True, "allow_list"
        if jurisdiction.lower() in self._jurisdiction_denies:
            return False, "jurisdiction_blocked"
        if category.lower() in self._kyc_required_categories and not kyc_passed:
            return False, "kyc_required"
        return True, "ok"


# ---------------------------------------------------------------------------
class PricingOracle:
    """Sliding-window median & average price aggregator."""

    def __init__(self, window: int = 300) -> None:
        self.window = window
        self._prices: Dict[str, List[Tuple[float, float]]] = {}

    def record(self, symbol: str, price: float, ts: Optional[float] = None) -> None:
        ts = ts or time()
        buf = self._prices.setdefault(symbol.upper(), [])
        buf.append((ts, float(price)))
        # prune
        cutoff = ts - self.window
        i = 0
        while i < len(buf) and buf[i][0] < cutoff:
            i += 1
        if i:
            del buf[:i]

    def snapshot(self, symbol: str) -> Dict:
        buf = self._prices.get(symbol.upper(), [])
        if not buf:
            return {
                "symbol": symbol.upper(),
                "last": None,
                "twap": None,
                "median": None,
                "count": 0,
            }
        prices = [p for _, p in buf]
        last = prices[-1]
        twap = sum(prices) / len(prices)
        median = sorted(prices)[len(prices) // 2]
        return {
            "symbol": symbol.upper(),
            "last": last,
            "twap": twap,
            "median": median,
            "count": len(prices),
        }


# ---------------------------------------------------------------------------
class TokenIssuer:
    """Controlled token creation & supply adjustment."""

    def __init__(
        self,
        registry: TokenRegistry,
        compliance: ComplianceEngine,
        oracle: Optional[PricingOracle] = None,
    ) -> None:
        self.registry = registry
        self.compliance = compliance
        self.oracle = oracle or PricingOracle()

    def issue(
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
    ) -> IssueResult:
        symbol_u = symbol.upper()
        ok, reason = self.compliance.check(symbol_u, category, jurisdiction, kyc_passed)
        if not ok:
            return IssueResult(False, reason=reason, decision="deny")
        # Gate via ethos
        numeric = (
            se41_numeric(M_t=0.6, DNA_states=[1.0, supply, decimals, 1.1])
            if callable(se41_numeric)
            else {"score": 0.55}
        )
        gate = ethos_decision(
            {
                "scope": "token_issue",
                "symbol": symbol_u,
                "supply": supply,
                "numeric": getattr(numeric, "get", lambda *_: 0.55)("score", 0.55),
            }
        )
        decision = (
            gate.get("decision", "allow")
            if isinstance(gate, dict)
            else gate[0] if isinstance(gate, tuple) else "allow"
        )
        if decision == "deny":
            return IssueResult(False, reason="ethos_deny", decision="deny")
        profile = TokenProfile(
            symbol=symbol_u,
            name=name,
            category=category,
            total_supply=float(supply),
            issuer=issuer,
            decimals=decimals,
            metadata=metadata or {},
            governance={
                "numeric_score": getattr(numeric, "get", lambda *_: 0.55)("score", 0.55)
            },
        )
        self.registry.upsert(profile)
        return IssueResult(True, profile=profile, decision=decision)

    def adjust_supply(
        self,
        symbol: str,
        delta: float,
        reason: str = "adjust",
        max_pct: float = 0.10,
    ) -> IssueResult:
        profile = self.registry.get(symbol)
        if not profile:
            return IssueResult(False, reason="unknown_symbol")
        if not profile.mutable:
            return IssueResult(False, reason="immutable")
        if profile.total_supply <= 0:
            return IssueResult(False, reason="invalid_supply")
        # Bound change
        pct = abs(delta) / profile.total_supply
        if pct > max_pct:
            return IssueResult(False, reason="delta_exceeds_limit")
        numeric = (
            se41_numeric(M_t=0.62, DNA_states=[1.0, pct, profile.total_supply, 1.12])
            if callable(se41_numeric)
            else {"score": 0.55}
        )
        gate = ethos_decision(
            {
                "scope": "supply_adjust",
                "symbol": symbol,
                "pct": pct,
                "numeric": getattr(numeric, "get", lambda *_: 0.55)("score", 0.55),
            }
        )
        decision = (
            gate.get("decision", "allow")
            if isinstance(gate, dict)
            else gate[0] if isinstance(gate, tuple) else "allow"
        )
        if decision == "deny":
            return IssueResult(False, reason="ethos_deny", decision="deny")
        if decision == "hold":
            return IssueResult(
                False, reason="ethos_hold", decision="hold", profile=profile
            )
        profile.total_supply = max(0.0, profile.total_supply + delta)
        self.registry.upsert(profile)
        return IssueResult(True, reason=reason, profile=profile, decision=decision)


# ---------------------------------------------------------------------------
__all__ = [
    "TokenProfile",
    "TokenRegistry",
    "TokenIssuer",
    "ComplianceEngine",
    "PricingOracle",
    "IssueResult",
]
