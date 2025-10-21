"""SAFE quantum lane orchestration for advisory portfolio proposals."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, cast

from ai_core.common import GateDecisionDict, as_gate_decision, load
from ai_core.common.audit_log import gate_logger
from settings.brand import BRANDS, CURRENCY_NAME
from settings.feature_flags import quantum_config

from .optimizers import build_portfolio_qubo

_quantum_driver = load("ai_core.quantum_core.quantum_driver")
_sim_annealer_cls = load(
    "ai_core.quantum_core.sim_annealer", "SimulatedAnnealerOptimizer"
)

QuantumDriver = cast(Any, getattr(_quantum_driver, "QuantumDriver", None))
QuantumRunRecord = cast(Any, getattr(_quantum_driver, "QuantumRunRecord", None))
available_optimizers = cast(
    Any, getattr(_quantum_driver, "available_optimizers", lambda: [])
)
get_optimizer = cast(
    Any, getattr(_quantum_driver, "get_optimizer", lambda *_args, **_kwargs: None)
)
qubo_energy = cast(
    Any, getattr(_quantum_driver, "qubo_energy", lambda *_args, **_kwargs: 0.0)
)
qubo_variables = cast(
    Any, getattr(_quantum_driver, "qubo_variables", lambda *_args, **_kwargs: {})
)
redact_qubo = cast(
    Any, getattr(_quantum_driver, "redact_qubo", lambda *_args, **_kwargs: {})
)

if isinstance(_sim_annealer_cls, type):
    SimulatedAnnealerOptimizer = cast(Any, _sim_annealer_cls)
else:
    SimulatedAnnealerOptimizer = cast(
        Any, getattr(_quantum_driver, "SimulatedAnnealerOptimizer", None)
    )
    if SimulatedAnnealerOptimizer is None:

        class SimulatedAnnealerOptimizer:  # type: ignore
            def info(self) -> Dict[str, Any]:
                return {"provider": "sim"}

            def solve_qubo(self, *_args, **_kwargs) -> Dict[int, int]:
                return {}


@dataclass
class QuantumLaneResult:
    corridor: str
    provider: str
    weights: Dict[str, float]
    bits: Dict[int, int]
    energy: float
    qubits: int
    shots: int
    runtime_s: float
    cost_cents: int
    decision: str
    reason: str
    payload_hash: str

    def summary(self) -> Dict[str, Any]:
        return {
            "corridor": self.corridor,
            "provider": self.provider,
            "weights": self.weights,
            "energy": self.energy,
            "qubits": self.qubits,
            "shots": self.shots,
            "decision": self.decision,
            "reason": self.reason,
            "runtime_s": round(self.runtime_s, 4),
            "cost_cents": self.cost_cents,
        }


@dataclass
class _Metrics:
    jobs_today: int = 0
    last_cost_cents: int = 0
    last_provider: str = "sim"
    last_decision: str = "HOLD"
    last_reason: str = "quantum_disabled"
    last_ts: float = 0.0
    last_bits: Dict[int, int] = field(default_factory=dict)
    last_energy: float = 0.0
    day_stamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d"))

    def reset_if_needed(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if today != self.day_stamp:
            self.day_stamp = today
            self.jobs_today = 0

    def record(
        self,
        *,
        cost_cents: int,
        provider: str,
        decision: str,
        reason: str,
        bits: Mapping[int, int],
        energy: float,
    ) -> None:
        self.reset_if_needed()
        self.jobs_today += 1
        self.last_cost_cents = int(cost_cents)
        self.last_provider = provider
        self.last_decision = decision
        self.last_reason = reason
        self.last_bits = dict(bits)
        self.last_energy = float(energy)
        self.last_ts = time.time()


_METRICS = _Metrics()


class _StubDriver:
    def record(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - noop
        pass


if isinstance(QuantumDriver, type):
    try:
        _LEGACY_DRIVER = QuantumDriver()
    except Exception:  # pragma: no cover - optional dependency missing
        _LEGACY_DRIVER = _StubDriver()
else:
    _LEGACY_DRIVER = _StubDriver()


def quantum_lane_state() -> Dict[str, Any]:
    cfg = quantum_config()
    return {
        "feature_enabled": bool(cfg.get("feature_enabled")),
        "provider": cfg.get("provider", "sim"),
        "max_qubits": int(cfg.get("max_qubits", 40)),
        "max_cost_cents": int(cfg.get("max_cost_cents", 200)),
        "max_latency_sec": int(cfg.get("max_latency_sec", 300)),
        "redact_payload": bool(cfg.get("redact_payload", True)),
        "jobs_today": _METRICS.jobs_today,
        "last_cost_cents": _METRICS.last_cost_cents,
        "last_provider": _METRICS.last_provider,
        "last_decision": _METRICS.last_decision,
        "last_reason": _METRICS.last_reason,
        "last_ts": _METRICS.last_ts,
        "available": available_optimizers(),
    }


def _build_constraints(assets: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    expected_returns: Dict[str, float] = {}
    liquidity: Dict[str, float] = {}
    turnover: Dict[str, float] = {}
    for idx, item in enumerate(assets):
        sym = str(item.get("symbol", idx))
        expected_returns[sym] = float(item.get("expected_return", 0.01))
        liquidity[sym] = float(item.get("liquidity", 1.0))
        turnover[sym] = float(item.get("turnover", 0.0))
    budget = max(1.0, float(len(assets) // 2 or 1))
    return {
        "expected_returns": expected_returns,
        "liquidity": liquidity,
        "turnover": turnover,
        "budget": budget,
    }


def _prepare_prices(assets: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    prices: Dict[str, float] = {}
    for idx, item in enumerate(assets):
        sym = str(item.get("symbol", idx))
        px = float(item.get("price", 1.0) or 1.0)
        prices[sym] = abs(px)
    return prices


def _sparse_covariance(
    assets: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, str], float]:
    cov: Dict[Tuple[str, str], float] = {}
    symbols = [str(item.get("symbol", idx)) for idx, item in enumerate(assets)]
    vol_hint = [abs(float(item.get("volatility", 0.05))) for item in assets]
    for idx, sym in enumerate(symbols):
        sigma = vol_hint[idx] if idx < len(vol_hint) else 0.05
        cov[(sym, sym)] = (sigma**2) + 1e-6
        for jdx in range(idx + 1, len(symbols)):
            other_sigma = vol_hint[jdx] if jdx < len(vol_hint) else 0.05
            cov[(sym, symbols[jdx])] = 0.5 * sigma * other_sigma
    return cov


def _decode_weights(
    bits: Mapping[int, int], ordering: Sequence[str]
) -> Dict[str, float]:
    selected = [
        ordering[idx] for idx, val in bits.items() if idx < len(ordering) and val
    ]
    if not selected:
        return {}
    weight = 1.0 / len(selected)
    return {asset: round(weight, 6) for asset in selected}


def maybe_run_quantum_lane(
    *,
    corridor: str,
    assets: Sequence[Mapping[str, Any]],
    gate_decision: Any,
    context_tags: Optional[Mapping[str, Any]] = None,
    shots_override: Optional[int] = None,
) -> Optional[QuantumLaneResult]:
    cfg = quantum_config()
    if not bool(cfg.get("feature_enabled")):
        return None
    if not assets:
        return None

    decision_payload: GateDecisionDict = as_gate_decision(gate_decision)

    prices = _prepare_prices(assets)
    covariance = _sparse_covariance(assets)
    constraints = _build_constraints(assets)

    Q, ordering = build_portfolio_qubo(prices, covariance, constraints)
    if not Q:
        return None

    qubits = len(ordering)
    max_qubits = int(cfg.get("max_qubits", 40))
    if qubits > max_qubits:
        return None

    default_shots = max(32, min(256, qubits * 32))
    shots = int(shots_override or default_shots)

    provider_key = str(cfg.get("provider", "sim"))
    seed = int(time.time() * 1000) % 2_147_483_647
    start = time.time()

    try:
        optimizer = cast(Any, get_optimizer(provider_key))
        provider_info = optimizer.info()
    except Exception:
        optimizer = SimulatedAnnealerOptimizer()
        provider_info = optimizer.info()

    provider_name = provider_info.get("provider", provider_key)
    try:
        raw_bits = optimizer.solve_qubo(Q, shots=shots, seed=seed)
    except Exception:
        fallback = SimulatedAnnealerOptimizer()
        raw_bits = fallback.solve_qubo(Q, shots=shots, seed=seed)
        provider_info = fallback.info()
        provider_name = provider_info.get("provider", "sim")

    bits: Dict[int, int] = {}
    for key, value in raw_bits.items():
        idx = int(key)
        bits[idx] = 1 if int(value) else 0

    runtime = time.time() - start
    energy = qubo_energy(Q, bits)
    cost_cents = min(int(cfg.get("max_cost_cents", 200)), max(1, qubits * shots // 128))

    payload = redact_qubo(Q)
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    payload_digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()[:24]

    weights = _decode_weights(bits, ordering)

    record = None
    if callable(QuantumRunRecord):
        try:
            record = QuantumRunRecord(  # type: ignore[misc]
                bits=dict(bits),
                energy=float(energy),
                shots=shots,
                seed=seed,
                provider=provider_name,
            )
        except Exception:
            record = None
    if record is not None and hasattr(_LEGACY_DRIVER, "record"):
        try:
            _LEGACY_DRIVER.record(record)
        except Exception:
            pass
    _METRICS.record(
        cost_cents=cost_cents,
        provider=provider_name,
        decision=decision_payload["decision"],
        reason=decision_payload["reason"],
        bits=bits,
        energy=energy,
    )

    audit_rec: Dict[str, Any] = {
        "component": "quantum.opt",
        "provider": provider_name,
        "qubits": qubits,
        "shots": shots,
        "queue_s": 0.0,
        "runtime_s": runtime,
        "cost_cents": cost_cents,
        "decision": decision_payload["decision"],
        "reason": decision_payload["reason"],
        "corridor": corridor,
        "weights": weights,
        "payload": payload,
        "payload_hash": payload_digest,
        "currency_system": CURRENCY_NAME,
        "brands": BRANDS,
        "feature_flags": {
            "FEATURE_Q_OPT": bool(cfg.get("feature_enabled")),
            "Q_PROVIDER": provider_key,
        },
    }
    if context_tags:
        for key, value in context_tags.items():
            audit_rec[f"tag_{key}"] = value

    try:
        gate_logger().write(audit_rec)
    except Exception:
        pass

    return QuantumLaneResult(
        corridor=corridor,
        provider=provider_name,
        weights=weights,
        bits=dict(bits),
        energy=float(energy),
        qubits=qubits,
        shots=shots,
        runtime_s=float(runtime),
        cost_cents=int(cost_cents),
        decision=decision_payload["decision"],
        reason=decision_payload["reason"],
        payload_hash=payload_digest,
    )


__all__ = ["maybe_run_quantum_lane", "quantum_lane_state", "QuantumLaneResult"]
