"""
Serplus Engine (SE41 v4.1+ aligned)
-----------------------------------

Purpose
-------
Policy evaluation and (optional) execution for the Serplus token (SRP).
Seeks a reserve-coverage equilibrium using a bounded mint/buyback policy,
gated by SE41 symbolic scoring and ethos-decision.

This module is chain-agnostic via a pluggable ChainAdapter interface.
It ships with a MockAdapter for local simulation.

Key Concepts
------------
- coverage = reserves_usd / (supply * reference_price_usd)
- target_coverage = τ (e.g., 1.20)
- surplus_usd  = max(0, reserves_usd - τ * supply * price)
- deficit_usd  = max(0, τ * supply * price - reserves_usd)

Mint (bounded):
 ΔS = min( α * surplus_usd / price, daily_cap * supply )
 with small PRNG jitter for MEV-resilience; ethos gate can hold/deny.

Buyback:
 If deficit_usd > 0, suggest budget = β * reserves_usd (policy param).
 Actual buyback mechanics are adapter-specific (DEX, RFQ, etc.).

Absolutely no "quantum computing" claims are made here. Any "quantum" wording
in the broader project refers to randomization/jitter only.

Author: EidollonaONE / FanComp Foundation
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Protocol, runtime_checkable, List

# -------------------------------------------------------------------------
# SE41 integration with safe fallbacks
# -------------------------------------------------------------------------
try:  # pragma: no cover
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
    from trading.helpers.se41_trading_gate import se41_numeric, ethos_decision  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**_kw) -> Dict:
        return {"ts": time.time(), "features": {}}

    def se41_numeric(**_kw) -> float:
        return 0.55  # mid score fallback

    def ethos_decision(_tx: Dict) -> Dict:
        return {"decision": "allow", "reason": "fallback"}


# -------------------------------------------------------------------------
# Optional chain metrics adapter (fallback stub if module absent)
# -------------------------------------------------------------------------
try:  # pragma: no cover
    from blockchain.chain_metrics import ChainSnapshot, get_snapshot  # type: ignore
except Exception:  # pragma: no cover
    from dataclasses import dataclass

    @dataclass
    class ChainSnapshot:  # type: ignore
        reserves_usd: float
        price_usd: float
        twap_usd: float
        realized_vol: float
        liquidity_score: float
        ts: float

    def get_snapshot(symbol: str = "SRP") -> ChainSnapshot:  # type: ignore
        p = 1.00 + random.uniform(-0.01, 0.01)
        return ChainSnapshot(
            reserves_usd=1_000_000.0,
            price_usd=p,
            twap_usd=p,
            realized_vol=0.12,
            liquidity_score=0.7,
            ts=time.time(),
        )


# -------------------------------------------------------------------------
# Interfaces & Dataclasses
# -------------------------------------------------------------------------


@runtime_checkable
class ChainAdapter(Protocol):
    """Abstract interface the engine uses to interact with the chain."""

    def fetch_snapshot(self) -> ChainSnapshot: ...
    def current_supply(self) -> float: ...
    def mint(self, to: str, amount: float) -> str: ...
    def buyback_and_burn(self, budget_usd: float) -> str: ...
    def reference_price(self) -> float: ...
    def treasury_address(self) -> str: ...


@dataclass
class SerplusConfig:
    symbol: str = "SRP"
    target_coverage: float = 1.20  # τ
    alpha: float = 0.20  # mint dampening factor
    daily_cap: float = 0.02  # ≤ 2% of supply per epoch/day
    jitter_sigma: float = 0.02  # ±2% PRNG jitter
    buyback_budget_ratio: float = 0.05  # 5% of reserves when in deficit
    ethos_min_score: float = 0.0  # informational (gate uses ethos_decision)
    min_price_usd: float = 0.01  # guards
    min_supply: float = 1.0
    dry_run: bool = True  # do not call adapter.mint/buyback when True
    mint_recipient: str = "treasury"  # default routed to treasury
    log_decisions: bool = True


@dataclass
class PolicyDecision:
    ts: float
    coverage: float
    surplus_usd: float
    deficit_usd: float
    se41_score: float
    action: str  # "mint", "buyback", "hold", "denied"
    mint_amount: float = 0.0  # tokens
    buyback_budget_usd: float = 0.0
    reason: str = ""
    ethos_gate: str = "allow"  # allow/hold/deny
    meta: Dict = field(default_factory=dict)


@dataclass
class AuditRecord:
    decision: PolicyDecision
    tx_hashes: List[str] = field(default_factory=list)


# -------------------------------------------------------------------------
# Mock Adapter (works out of the box; replace with real chain adapter)
# -------------------------------------------------------------------------
class MockAdapter:
    """Simple in-memory adapter for local simulations."""

    def __init__(
        self, init_reserves_usd=1_000_000.0, init_supply=1_000_000.0, init_price=1.0
    ):
        self._reserves = float(init_reserves_usd)
        self._supply = float(init_supply)
        self._price = float(init_price)
        self._treasury = "0xTREASURY"

    def fetch_snapshot(self) -> ChainSnapshot:
        # mean reversion toward 1.0 w/ noise
        self._price += (1.0 - self._price) * 0.05 + random.uniform(-0.005, 0.005)
        return ChainSnapshot(
            reserves_usd=self._reserves,
            price_usd=self._price,
            twap_usd=self._price,
            realized_vol=0.12,
            liquidity_score=0.7,
            ts=time.time(),
        )

    def current_supply(self) -> float:
        return self._supply

    def mint(self, to: str, amount: float) -> str:
        self._supply += float(amount)
        return f"mint:{to}:{amount:.6f}:{int(time.time())}"

    def buyback_and_burn(self, budget_usd: float) -> str:
        spend = min(self._reserves * 0.95, max(budget_usd, 0.0))
        if self._price <= 0:
            return "buyback_skipped_price_zero"
        tokens_bought = spend / self._price
        self._reserves -= spend
        self._supply = max(0.0, self._supply - tokens_bought)
        return f"buyback_burn:{tokens_bought:.6f}:{int(time.time())}"

    def reference_price(self) -> float:
        return max(self._price, 1e-9)

    def treasury_address(self) -> str:
        return self._treasury


# -------------------------------------------------------------------------
# Core Engine
# -------------------------------------------------------------------------
class SerplusEngine:
    """SE41-aligned policy engine for Serplus (SRP)."""

    def __init__(self, config: SerplusConfig, adapter: Optional[ChainAdapter] = None):
        self.cfg = config
        self.adapter: ChainAdapter = adapter if adapter is not None else MockAdapter()
        self.log = logging.getLogger(f"{__name__}.SerplusEngine")

    # ---- Policy math ----
    def _clamp01(self, x: float) -> float:
        return max(0.0, min(1.0, x))

    def _compute_coverage(
        self, reserves_usd: float, supply: float, price: float
    ) -> float:
        denom = max(supply * max(price, self.cfg.min_price_usd), 1e-9)
        return reserves_usd / denom

    def _evaluate_se41(
        self, coverage: float, surplus_ratio: float, vol: float, liq: float
    ) -> float:
        dna = [
            coverage,
            self._clamp01(surplus_ratio),
            self._clamp01(vol),
            self._clamp01(liq),
            1.0,
        ]
        score = abs(
            float(
                se41_numeric(
                    M_t=coverage, DNA_states=dna, harmonic_patterns=list(reversed(dna))
                )
            )
        )
        return self._clamp01(score)

    def _mint_amount(
        self, surplus_usd: float, price_usd: float, supply: float
    ) -> float:
        eps = 1e-9
        base = self.cfg.alpha * surplus_usd / max(price_usd, eps)
        cap = self.cfg.daily_cap * max(supply, self.cfg.min_supply)
        amt = min(base, cap)
        amt *= 1.0 + random.gauss(0.0, self.cfg.jitter_sigma)  # jitter
        return max(0.0, amt)

    def _buyback_budget(self, reserves_usd: float) -> float:
        return max(0.0, self.cfg.buyback_budget_ratio * reserves_usd)

    # ---- Decision ----
    def evaluate(self, snapshot: Optional[ChainSnapshot] = None) -> PolicyDecision:
        snap = snapshot or self.adapter.fetch_snapshot()
        supply = self.adapter.current_supply()
        price = max(self.adapter.reference_price(), self.cfg.min_price_usd)

        coverage = self._compute_coverage(snap.reserves_usd, supply, price)
        target_value = self.cfg.target_coverage * supply * price
        surplus_usd = max(0.0, snap.reserves_usd - target_value)
        deficit_usd = max(0.0, target_value - snap.reserves_usd)
        surplus_ratio = (coverage - self.cfg.target_coverage) / max(
            self.cfg.target_coverage, 1e-9
        )

        score = self._evaluate_se41(
            coverage, surplus_ratio, snap.realized_vol, snap.liquidity_score
        )

        gate = ethos_decision(
            {
                "scope": "serplus_policy",
                "coverage": coverage,
                "surplus_usd": surplus_usd,
                "deficit_usd": deficit_usd,
                "score": score,
                "ts": snap.ts,
            }
        )
        gate_decision = (gate or {}).get("decision", "allow")

        action = "hold"
        mint_amt = 0.0
        buyback_budget = 0.0
        reason = "equilibrium"

        if gate_decision == "deny":
            action, reason = "denied", "ethos_denied"
        else:
            if surplus_usd > 0.0:
                mint_amt = self._mint_amount(surplus_usd, price, supply)
                if mint_amt > 0:
                    action, reason = "mint", "surplus_mint"
            elif deficit_usd > 0.0:
                buyback_budget = self._buyback_budget(snap.reserves_usd)
                if buyback_budget > 0:
                    action, reason = "buyback", "deficit_buyback"
            if gate_decision == "hold":  # soft gate
                action, reason = "hold", "ethos_hold"

        return PolicyDecision(
            ts=snap.ts,
            coverage=coverage,
            surplus_usd=surplus_usd,
            deficit_usd=deficit_usd,
            se41_score=score,
            action=action,
            mint_amount=mint_amt,
            buyback_budget_usd=buyback_budget,
            reason=reason,
            ethos_gate=gate_decision,
            meta={
                "supply": supply,
                "price": price,
                "target_coverage": self.cfg.target_coverage,
            },
        )

    # ---- Execution ----
    def execute(self, decision: PolicyDecision) -> AuditRecord:
        txs: List[str] = []
        if self.cfg.dry_run:
            if self.cfg.log_decisions:
                self.log.info("[DRY-RUN] %s", asdict(decision))
            return AuditRecord(decision=decision, tx_hashes=txs)
        if decision.action in ("denied", "hold"):
            if self.cfg.log_decisions:
                self.log.info(
                    "No-op action=%s reason=%s", decision.action, decision.reason
                )
            return AuditRecord(decision=decision, tx_hashes=txs)
        if decision.action == "mint" and decision.mint_amount > 0:
            recipient = (
                self.adapter.treasury_address()
                if self.cfg.mint_recipient == "treasury"
                else self.cfg.mint_recipient
            )
            tx = self.adapter.mint(recipient, decision.mint_amount)
            txs.append(tx)
            if self.cfg.log_decisions:
                self.log.info(
                    "Minted %.6f SRP to %s (tx=%s)", decision.mint_amount, recipient, tx
                )
        elif decision.action == "buyback" and decision.buyback_budget_usd > 0:
            tx = self.adapter.buyback_and_burn(decision.buyback_budget_usd)
            txs.append(tx)
            if self.cfg.log_decisions:
                self.log.info(
                    "Buyback+burn budget $%.2f (tx=%s)", decision.buyback_budget_usd, tx
                )
        else:
            if self.cfg.log_decisions:
                self.log.info("No actionable change: %s", decision.action)
        return AuditRecord(decision=decision, tx_hashes=txs)

    # ---- High level ----
    def run_epoch(self, snapshot: Optional[ChainSnapshot] = None) -> AuditRecord:
        dec = self.evaluate(snapshot)
        return self.execute(dec)

    def simulate(self, epochs: int = 14, sleep_s: float = 0.0) -> List[AuditRecord]:
        out: List[AuditRecord] = []
        for _ in range(max(0, epochs)):
            rec = self.run_epoch()
            out.append(rec)
            if sleep_s > 0:
                time.sleep(sleep_s)
        return out


# -------------------------------------------------------------------------
# Convenience factory
# -------------------------------------------------------------------------
def create_serplus_engine(**kwargs) -> SerplusEngine:
    cfg = kwargs.pop("config", SerplusConfig())
    adapter = kwargs.pop("adapter", None)
    return SerplusEngine(cfg, adapter)


# -------------------------------------------------------------------------
# CLI / Local demo
# -------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    engine = create_serplus_engine(
        config=SerplusConfig(dry_run=True, daily_cap=0.015, target_coverage=1.2),
        adapter=MockAdapter(
            init_reserves_usd=1_000_000, init_supply=1_000_000, init_price=1.0
        ),
    )
    print("=" * 72)
    print("Serplus Engine (SE41 v4.1+) — DRY RUN DEMO")
    print("=" * 72)
    records = engine.simulate(epochs=10)
    minted = sum(r.decision.mint_amount for r in records if r.decision.action == "mint")
    spent = sum(
        r.decision.buyback_budget_usd for r in records if r.decision.action == "buyback"
    )
    print(f"\nEpochs: {len(records)}")
    print(f"Total minted (sim): {minted:,.6f} SRP")
    print(f"Total buyback budget (sim): ${spent:,.2f}")
    last = records[-1].decision
    print(
        f"Last coverage: {last.coverage:.4f} | Action: {last.action} | Reason: {last.reason}"
    )
