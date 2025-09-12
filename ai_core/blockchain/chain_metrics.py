"""
🧭 EidollonaONE Chain Metrics v4.1 (SE41-aligned)

Purpose
-------
Unified, low‑overhead blockchain metrics engine for:
• Throughput (TPS, block time, utilization)
• Fees / gas (base fee, priority fee, fee rate percentiles)
• Mempool congestion / pressure
• Security/protocol health (uncle/orphan rate, reorg risk proxy)
• Node health (peers, sync lag, resource pressure)
• Composite Chain Health Score + actionable recommendations

Design
------
• Model‑agnostic: supports EVM‑like (gas, EIP‑1559) and UTXO‑like (bytes/weight, sat/vB).
• Event‑driven ingestion: feed BlockSample/MempoolSample/NodeHealth snapshots.
• Sliding window analytics: configurable deques maintain recent state.
• Deterministic numerics: pure stdlib, no external deps.
• Optional SE41 signal: non‑blocking hook to se41_numeric() to produce an alignment score.

This module does not perform RPC. Plug in your own data source to populate
BlockSample/MempoolSample/NodeHealth and call `engine.compute_snapshot()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple, Literal
from collections import deque
import statistics
import math
import time

# ---------------------------------------------------------------------------
# Optional SE41 alignment hook (harmless stub if unavailable)
# ---------------------------------------------------------------------------
try:  # pragma: no cover
    from trading.helpers.se41_trading_gate import se41_numeric  # type: ignore
except Exception:  # pragma: no cover

    def se41_numeric(**_kw):  # type: ignore
        return 0.5  # neutral stub


# ---------------------------------------------------------------------------
# Types & data containers
# ---------------------------------------------------------------------------


class ChainKind:
    EVM = "evm"
    UTXO = "utxo"


@dataclass
class ChainParams:
    """Static chain parameters."""

    kind: Literal["evm", "utxo"] = "evm"
    target_block_time_sec: float = 12.0  # e.g., 12 sec for many EVM L1s
    fee_unit_name: str = "gwei"  # "gwei" for EVM, "sat/vB" for Bitcoin
    base_currency: str = "ETH"  # or "BTC", etc.
    supports_eip1559: bool = True  # baseFee/priorityFee dynamics
    # Capacity hints for mempool pressure (per-block)
    evm_target_gas_per_block: float = 15_000_000.0  # example value
    utxo_target_weight_wu: float = 4_000_000.0  # Bitcoin vbytes weight units cap


@dataclass
class BlockSample:
    """
    Minimal per-block summary.
    For EVM: set gas_used/gas_limit/base_fee/priority_fee_median.
    For UTXO: set size_bytes and/or weight_wu, fee_rate_median (sat/vB).
    """

    height: int
    timestamp: float  # Unix epoch (seconds)
    block_time_sec: float  # time since previous block (s)
    tx_count: int
    # EVM-ish
    gas_used: Optional[float] = None
    gas_limit: Optional[float] = None
    base_fee: Optional[float] = None  # e.g., gwei
    priority_fee_median: Optional[float] = None  # e.g., gwei
    # UTXO-ish
    size_bytes: Optional[int] = None
    weight_wu: Optional[int] = None
    fee_rate_median: Optional[float] = None  # sat/vB
    # Common-ish
    uncle_orphan_count: int = (
        0  # uncles (EVM) / orphans (UTXO) seen with/near this block
    )


@dataclass
class MempoolSample:
    """
    Mempool snapshot with optional fee histogram.
    fee_histogram: list of (fee_rate, count) where fee_rate is gwei (EVM) or sat/vB (UTXO),
    ordered from high to low or low to high (order-insensitive in our estimator).
    """

    timestamp: float
    tx_count: int
    bytes_total: Optional[int] = None
    vsize_bytes_total: Optional[int] = None  # UTXO convenience
    gas_queued: Optional[float] = None  # EVM queued gas
    fee_histogram: List[Tuple[float, int]] = field(default_factory=list)


@dataclass
class NodeHealth:
    """Local node/validator health signal."""

    timestamp: float
    peers: int
    sync_lag_blocks: int
    cpu_util: float  # 0..1
    mem_util: float  # 0..1
    disk_avail_gb: float
    recent_errors_5m: int = 0


@dataclass
class ThroughputMetrics:
    tps: float = 0.0
    avg_block_time: float = 0.0
    tx_per_block: float = 0.0
    gas_util_mean: Optional[float] = None
    gas_util_p95: Optional[float] = None


@dataclass
class FeeMetrics:
    unit: str = "gwei"
    base_fee_mean: Optional[float] = None
    base_fee_p95: Optional[float] = None
    priority_fee_p50: Optional[float] = None
    priority_fee_p95: Optional[float] = None
    eff_fee_rate_p50: Optional[float] = None  # generic: gwei or sat/vB
    eff_fee_rate_p95: Optional[float] = None
    mempool_fee_p25: Optional[float] = None
    mempool_fee_p50: Optional[float] = None
    mempool_fee_p75: Optional[float] = None
    recommended_fee_rate: Optional[float] = None  # conservative "safe within N blocks"


@dataclass
class SecurityMetrics:
    orphan_uncle_rate: float = 0.0
    reorg_risk_proxy: float = 0.0  # 0..1
    finality_time_est_sec: Optional[float] = None


@dataclass
class CongestionMetrics:
    mempool_pressure: float = 0.0  # 0..1 (1=severely congested)
    backlog_blocks_equiv: Optional[float] = None
    gas_spike_risk: Optional[float] = (
        None  # 0..1 from base fee spikes / queue saturation
    )


@dataclass
class NodeHealthMetrics:
    node_health_score: float = 1.0  # 0..1
    sync_ok: bool = True
    peers_ok: bool = True
    resource_pressure: float = 0.0  # 0..1


@dataclass
class ChainMetricsSnapshot:
    timestamp: float
    window_blocks: int
    throughput: ThroughputMetrics
    fees: FeeMetrics
    congestion: CongestionMetrics
    security: SecurityMetrics
    node: NodeHealthMetrics
    chain_health_score: float
    alignment_score: float
    recommendations: List[str] = field(default_factory=list)
    # minimal raw echo for debugging
    _debug: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Utility math
# ---------------------------------------------------------------------------


def _safe_div(n: float, d: float, default: float = 0.0) -> float:
    return n / d if d not in (0, 0.0) else default


def _percentile(values: List[float], q: float) -> Optional[float]:
    """q in [0,100]. Returns None if values empty."""
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    vals = sorted(values)
    k = (len(vals) - 1) * (q / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals[int(k)]
    return vals[f] * (c - k) + vals[c] * (k - f)


def _percentile_from_histogram(
    hist: List[Tuple[float, int]], q: float
) -> Optional[float]:
    """Weighted percentile from (value, count)."""
    if not hist:
        return None
    # Normalize order
    hist_sorted = sorted(hist, key=lambda x: x[0])
    total = sum(c for _, c in hist_sorted)
    if total <= 0:
        return None
    target = total * (q / 100.0)
    cum = 0
    for value, count in hist_sorted:
        cum += count
        if cum >= target:
            return float(value)
    return float(hist_sorted[-1][0])


def _ewma(xs: List[float], alpha: float = 0.3) -> float:
    if not xs:
        return 0.0
    s = xs[0]
    for x in xs[1:]:
        s = alpha * x + (1 - alpha) * s
    return s


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


class ChainMetricsEngine:
    """
    Collects recent block/mempool/node snapshots and computes a holistic
    chain health view + recommendations.

    Usage:
        params = ChainParams(kind="evm", ...)
        engine = ChainMetricsEngine(params)
        engine.add_block(block) / engine.add_mempool(mempool) / engine.set_node_health(node)
        snap = engine.compute_snapshot()
    """

    def __init__(self, params: ChainParams, window_blocks: int = 128) -> None:
        self.params = params
        self.window_blocks = max(8, int(window_blocks))
        self.blocks: Deque[BlockSample] = deque(maxlen=self.window_blocks)
        self.mempools: Deque[MempoolSample] = deque(
            maxlen=max(8, self.window_blocks // 4)
        )
        self.node: Optional[NodeHealth] = None

    # -- ingestion -----------------------------------------------------------

    def add_block(self, block: BlockSample) -> None:
        self.blocks.append(block)

    def add_mempool(self, mempool: MempoolSample) -> None:
        self.mempools.append(mempool)

    def set_node_health(self, node: NodeHealth) -> None:
        self.node = node

    # -- computations --------------------------------------------------------

    def compute_snapshot(self) -> ChainMetricsSnapshot:
        now = time.time()
        # Throughput metrics
        tp = self._compute_throughput()
        # Fees
        fees = self._compute_fees()
        # Congestion & mempool
        cg = self._compute_congestion(tp, fees)
        # Security-ish proxies
        sec = self._compute_security(tp)
        # Node health
        nh = self._compute_node_health()
        # Composite scoring
        health, align = self._score_chain(tp, fees, cg, sec, nh)

        recs = self._recommendations(tp, fees, cg, sec, nh)

        debug = {
            "tps": tp.tps,
            "avg_block_time": tp.avg_block_time,
            "mempool_pressure": cg.mempool_pressure,
            "reorg_risk_proxy": sec.reorg_risk_proxy,
            "node_health_score": nh.node_health_score,
            "alignment_score": align,
        }

        return ChainMetricsSnapshot(
            timestamp=now,
            window_blocks=len(self.blocks),
            throughput=tp,
            fees=fees,
            congestion=cg,
            security=sec,
            node=nh,
            chain_health_score=health,
            alignment_score=align,
            recommendations=recs,
            _debug=debug,
        )

    # -- sub-metrics ---------------------------------------------------------

    def _compute_throughput(self) -> ThroughputMetrics:
        if not self.blocks:
            return ThroughputMetrics()

        times = [
            max(0.0, b.block_time_sec)
            for b in self.blocks
            if b.block_time_sec is not None
        ]
        avg_block_time = (
            statistics.fmean(times) if times else self.params.target_block_time_sec
        )

        txs = [max(0, b.tx_count) for b in self.blocks]
        tx_per_block = statistics.fmean(txs) if txs else 0.0
        tps = (
            _safe_div(sum(txs), sum(times), 0.0)
            if len(times) == len(self.blocks)
            else _safe_div(tx_per_block, avg_block_time, 0.0)
        )

        gas_utils: List[float] = []
        if self.params.kind == ChainKind.EVM:
            for b in self.blocks:
                if b.gas_used and b.gas_limit and b.gas_limit > 0:
                    gas_utils.append(min(1.0, b.gas_used / b.gas_limit))
            gas_mean = statistics.fmean(gas_utils) if gas_utils else None
            gas_p95 = _percentile(gas_utils, 95.0) if gas_utils else None
        else:
            gas_mean = None
            gas_p95 = None

        return ThroughputMetrics(
            tps=tps,
            avg_block_time=avg_block_time,
            tx_per_block=tx_per_block,
            gas_util_mean=gas_mean,
            gas_util_p95=gas_p95,
        )

    def _compute_fees(self) -> FeeMetrics:
        fees = FeeMetrics(unit=self.params.fee_unit_name)
        if not self.blocks:
            # Try mempool histogram to at least provide a recommended fee
            self._fill_mempool_fee_recs(fees)
            return fees

        if self.params.kind == ChainKind.EVM:
            base_fees = [b.base_fee for b in self.blocks if b.base_fee is not None]
            prio_meds = [
                b.priority_fee_median
                for b in self.blocks
                if b.priority_fee_median is not None
            ]
            fees.base_fee_mean = statistics.fmean(base_fees) if base_fees else None
            fees.base_fee_p95 = (
                _percentile([x for x in base_fees], 95.0) if base_fees else None
            )
            fees.priority_fee_p50 = _percentile(prio_meds, 50.0) if prio_meds else None
            fees.priority_fee_p95 = _percentile(prio_meds, 95.0) if prio_meds else None
            # Effective fee rate proxy from in-block medians
            eff = []
            for b in self.blocks:
                if b.base_fee is not None and b.priority_fee_median is not None:
                    eff.append(b.base_fee + b.priority_fee_median)
            fees.eff_fee_rate_p50 = _percentile(eff, 50.0) if eff else None
            fees.eff_fee_rate_p95 = _percentile(eff, 95.0) if eff else None
        else:
            # UTXO: median fee rate sat/vB if present
            fr = [
                b.fee_rate_median for b in self.blocks if b.fee_rate_median is not None
            ]
            fees.eff_fee_rate_p50 = _percentile(fr, 50.0) if fr else None
            fees.eff_fee_rate_p95 = _percentile(fr, 95.0) if fr else None

        # Add mempool-derived recommendation
        self._fill_mempool_fee_recs(fees)
        return fees

    def _fill_mempool_fee_recs(self, fees: FeeMetrics) -> None:
        if not self.mempools:
            return
        # Use latest mempool histogram
        latest = self.mempools[-1]
        p50 = _percentile_from_histogram(latest.fee_histogram, 50.0)
        p75 = _percentile_from_histogram(latest.fee_histogram, 75.0)
        p25 = _percentile_from_histogram(latest.fee_histogram, 25.0)
        fees.mempool_fee_p25 = p25
        fees.mempool_fee_p50 = p50
        fees.mempool_fee_p75 = p75

        # conservative recommendation: ~p75 to clear next blocks
        if p75 is not None:
            fees.recommended_fee_rate = p75
        elif p50 is not None:
            fees.recommended_fee_rate = p50

    def _compute_congestion(
        self, tp: ThroughputMetrics, fees: FeeMetrics
    ) -> CongestionMetrics:
        if not self.mempools:
            return CongestionMetrics(
                mempool_pressure=0.0, backlog_blocks_equiv=0.0, gas_spike_risk=0.0
            )

        latest = self.mempools[-1]
        # Compute an equivalent "backlog in blocks"
        if self.params.kind == ChainKind.EVM:
            cap = self.params.evm_target_gas_per_block or 1.0
            queued = latest.gas_queued or 0.0
            backlog_blocks = _safe_div(queued, cap, 0.0)
        else:
            cap = self.params.utxo_target_weight_wu or 1.0
            vsize = (
                latest.vsize_bytes_total
                if latest.vsize_bytes_total is not None
                else (latest.bytes_total or 0)
            )
            backlog_blocks = _safe_div(float(vsize), cap, 0.0)

        # Pressure mapping 0..1 using a saturating function
        pressure = min(1.0, backlog_blocks / 4.0)  # >=4 blocks backlog ~ severe

        # Gas spike risk heuristic (EVM): combine gas utilization p95 & mempool P75/P50 spread
        if self.params.kind == ChainKind.EVM:
            util_p95 = tp.gas_util_p95 if tp.gas_util_p95 is not None else 0.0
            spread = 0.0
            if (
                fees.mempool_fee_p75
                and fees.mempool_fee_p50
                and fees.mempool_fee_p50 > 0
            ):
                spread = (fees.mempool_fee_p75 / fees.mempool_fee_p50) - 1.0
            spike = max(0.0, min(1.0, 0.6 * util_p95 + 0.4 * min(1.0, spread)))
        else:
            spike = None

        return CongestionMetrics(
            mempool_pressure=pressure,
            backlog_blocks_equiv=backlog_blocks,
            gas_spike_risk=spike,
        )

    def _compute_security(self, tp: ThroughputMetrics) -> SecurityMetrics:
        if not self.blocks:
            return SecurityMetrics()

        uncles = [max(0, b.uncle_orphan_count) for b in self.blocks]
        total_uncles = sum(uncles)
        orphan_rate = _safe_div(total_uncles, len(self.blocks), 0.0)

        # Reorg risk proxy: combine orphan rate and block time variance
        bt = [b.block_time_sec for b in self.blocks if b.block_time_sec is not None]
        variance = statistics.pvariance(bt) if len(bt) > 1 else 0.0
        norm_var = min(
            1.0,
            _safe_div(variance, max(1.0, tp.avg_block_time * tp.avg_block_time), 0.0),
        )
        reorg_risk = max(
            0.0, min(1.0, 0.6 * min(1.0, 5.0 * orphan_rate) + 0.4 * norm_var)
        )

        # Finality time (rough heuristic): ~ N confirmations * avg block time
        finality_secs = None
        if self.params.kind == ChainKind.EVM:
            finality_secs = (
                12 * tp.avg_block_time
            )  # e.g., 12 confs for conservative estimate
        else:
            finality_secs = 6 * tp.avg_block_time  # UTXO example

        return SecurityMetrics(
            orphan_uncle_rate=orphan_rate,
            reorg_risk_proxy=reorg_risk,
            finality_time_est_sec=finality_secs,
        )

    def _compute_node_health(self) -> NodeHealthMetrics:
        if not self.node:
            return NodeHealthMetrics(
                node_health_score=0.8,
                sync_ok=True,
                peers_ok=True,
                resource_pressure=0.2,
            )

        n = self.node
        # Resource pressure as max of cpu/mem with a small penalty from recent errors
        res_press = min(
            1.0, max(n.cpu_util, n.mem_util) + 0.05 * min(10, n.recent_errors_5m)
        )
        sync_ok = n.sync_lag_blocks <= 2 * self.window_blocks  # arbitrarily 2 windows
        peers_ok = n.peers >= 5  # simple floor

        # Score: start from 1, subtract penalties
        score = 1.0
        score -= 0.5 * min(1.0, _safe_div(n.sync_lag_blocks, self.window_blocks, 0.0))
        score -= 0.4 * res_press
        score -= 0.1 if not peers_ok else 0.0
        score = max(0.0, min(1.0, score))

        return NodeHealthMetrics(
            node_health_score=score,
            sync_ok=sync_ok,
            peers_ok=peers_ok,
            resource_pressure=res_press,
        )

    # -- scoring & recommendations ------------------------------------------

    def _score_chain(
        self,
        tp: ThroughputMetrics,
        fees: FeeMetrics,
        cg: CongestionMetrics,
        sec: SecurityMetrics,
        nh: NodeHealthMetrics,
    ) -> Tuple[float, float]:
        """
        Compute composite Chain Health Score (0..1) + SE41 alignment (0..1).
        Higher is better.
        """
        # Normalize building blocks
        speed = (
            1.0
            - min(
                1.0,
                _safe_div(tp.avg_block_time, self.params.target_block_time_sec, 1.0)
                - 1.0,
            )
            if self.params.target_block_time_sec > 0
            else 0.8
        )
        speed = max(0.0, min(1.0, speed))  # 1 when at/below target

        util = 1.0
        if self.params.kind == ChainKind.EVM and tp.gas_util_mean is not None:
            util = 1.0 - max(
                0.0, tp.gas_util_mean - 0.9
            )  # soft penalty above 90% avg util
            util = max(0.0, min(1.0, util))

        fee_stability = 1.0
        if (
            fees.eff_fee_rate_p95
            and fees.eff_fee_rate_p50
            and fees.eff_fee_rate_p50 > 0
        ):
            spread = (fees.eff_fee_rate_p95 / fees.eff_fee_rate_p50) - 1.0
            fee_stability = max(0.0, 1.0 - min(1.0, spread))

        congestion_penalty = 1.0 - cg.mempool_pressure
        security_quality = 1.0 - sec.reorg_risk_proxy

        # Weighted aggregate
        components = [
            (speed, 0.20),
            (util, 0.15),
            (fee_stability, 0.15),
            (congestion_penalty, 0.20),
            (security_quality, 0.20),
            (nh.node_health_score, 0.10),
        ]
        score = sum(v * w for v, w in components)
        score = max(0.0, min(1.0, score))

        # Optional SE41 numeric "alignment"
        dna = [
            speed,
            util,
            fee_stability,
            congestion_penalty,
            security_quality,
            nh.node_health_score,
            1.0,
            1.1,
        ]
        align_raw = se41_numeric(
            M_t=security_quality,
            DNA_states=dna,
            harmonic_patterns=dna[:6] + [1.15, 1.2],
        )
        try:
            align = (
                float(align_raw)
                if isinstance(align_raw, (float, int))
                else float(getattr(align_raw, "value", 0.5))
            )
        except Exception:
            align = 0.5
        align = max(
            0.0, min(1.0, abs(align) / 5.0 if abs(align) > 1 else abs(align))
        )  # keep 0..1

        return score, align

    def _recommendations(
        self,
        tp: ThroughputMetrics,
        fees: FeeMetrics,
        cg: CongestionMetrics,
        sec: SecurityMetrics,
        nh: NodeHealthMetrics,
    ) -> List[str]:
        rec: List[str] = []

        if cg.mempool_pressure >= 0.75:
            rec.append(
                "Severe mempool pressure: raise fee cap to mempool p75 or higher."
            )
        elif cg.mempool_pressure >= 0.4:
            rec.append(
                "Moderate mempool pressure: target mempool p50–p75 fee rate for timely inclusion."
            )

        if self.params.kind == ChainKind.EVM:
            if tp.gas_util_p95 is not None and tp.gas_util_p95 > 0.95:
                rec.append(
                    "Gas utilization >95% (p95): expect base fee increases; consider batching or off-peak windows."
                )
            if (
                fees.priority_fee_p50
                and fees.priority_fee_p50 > 0
                and fees.base_fee_mean
            ):
                eff_mid = fees.base_fee_mean + fees.priority_fee_p50
                rec.append(
                    f"Typical effective fee ~{eff_mid:.3g} {fees.unit} (median): set maxFee >= 1.5× this for safety."
                )

        if sec.reorg_risk_proxy >= 0.5:
            rec.append(
                "Elevated reorg risk proxy: wait for extra confirmations before settlement."
            )

        if not nh.sync_ok:
            rec.append(
                "Node sync lag high: resync/optimize peers; consider failover node for routing."
            )
        if nh.resource_pressure >= 0.8:
            rec.append(
                "Node resource pressure critical: scale CPU/RAM or reduce indexing load."
            )

        if not rec:
            rec.append(
                "Network conditions normal: use standard fee recommendations (mempool p50–p75)."
            )
        return rec


# ---------------------------------------------------------------------------
# Convenience: simple in-module test/demo
# ---------------------------------------------------------------------------


def _demo() -> None:  # pragma: no cover
    params = ChainParams(
        kind="evm",
        target_block_time_sec=12.0,
        base_currency="ETH",
        supports_eip1559=True,
    )
    eng = ChainMetricsEngine(params, window_blocks=64)

    # Mock recent blocks (simplified)
    ts = time.time()
    for i in range(64):
        eng.add_block(
            BlockSample(
                height=1_000_000 + i,
                timestamp=ts - (64 - i) * 12.2,
                block_time_sec=12.0 + (0.4 if i % 7 == 0 else -0.2),
                tx_count=120 + (i % 10),
                gas_used=14.5e6 + (i % 3) * 2e5,
                gas_limit=15e6,
                base_fee=18 + (i % 5),
                priority_fee_median=1.2 + 0.2 * (i % 4),
                uncle_orphan_count=1 if i % 50 == 0 else 0,
            )
        )

    # Mock mempool
    eng.add_mempool(
        MempoolSample(
            timestamp=time.time(),
            tx_count=120_000,
            gas_queued=45e6,
            fee_histogram=[(12, 5000), (18, 7000), (25, 2000), (40, 800)],
        )
    )

    # Mock node health
    eng.set_node_health(
        NodeHealth(
            timestamp=time.time(),
            peers=25,
            sync_lag_blocks=32,
            cpu_util=0.55,
            mem_util=0.60,
            disk_avail_gb=120.0,
            recent_errors_5m=1,
        )
    )

    snap = eng.compute_snapshot()
    print("== Chain Metrics Snapshot ==")
    print(f"Window blocks     : {snap.window_blocks}")
    print(f"TPS               : {snap.throughput.tps:.3f}")
    print(f"Avg block time    : {snap.throughput.avg_block_time:.3f}s")
    print(
        f"Mempool pressure  : {snap.congestion.mempool_pressure:.2f} (backlog≈{snap.congestion.backlog_blocks_equiv:.2f} blocks)"
    )
    print(f"Reorg risk proxy  : {snap.security.reorg_risk_proxy:.2f}")
    print(f"Chain health score: {snap.chain_health_score:.2f}")
    print(f"Alignment score   : {snap.alignment_score:.2f}")
    print("Recommendations:")
    for r in snap.recommendations:
        print(" -", r)


# Public exports
__all__ = [
    "ChainParams",
    "BlockSample",
    "MempoolSample",
    "NodeHealth",
    "ThroughputMetrics",
    "FeeMetrics",
    "SecurityMetrics",
    "CongestionMetrics",
    "NodeHealthMetrics",
    "ChainMetricsSnapshot",
    "ChainMetricsEngine",
]

if __name__ == "__main__":  # pragma: no cover
    _demo()
