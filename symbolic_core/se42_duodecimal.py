"""SE4.2 Lotus (Duodecimal) symbolic engine.

This module provides a SAFE-first upgrade path from SE4.1 by introducing
configurable smoothing, duodecimal (base-12) phase telemetry, and bounded
impetus synthesis aligned with the Lotus cadence.  It intentionally mirrors the
minimal public surface of SE4.1 while offering richer metadata for operators
that opt-in to the upgrade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Mapping, MutableSequence, Optional

from symbolic_core.audit_bridge import audit_ndjson

__all__ = [
    "SE42_VERSION",
    "SE42Signals",
    "Base12Telemetry",
    "SymbolicEquation42Lotus",
]

SE42_VERSION = "4.2.0-lotus"
_BASE12_DIGITS = "0123456789XY"


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(numeric):
        return float(default)
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


def _clamp(value: Any, lower: float, upper: float, default: float) -> float:
    try:
        numeric = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(numeric):
        return float(default)
    return float(min(max(numeric, lower), upper))


def _merge_ethos(defaults: Mapping[str, float], hint: Optional[Mapping[str, Any]]) -> Dict[str, float]:
    base = {k: _clamp01(v, 0.0) for k, v in dict(defaults or {}).items()}
    if not hint:
        return base
    for key, value in dict(hint).items():
        base[str(key)] = _clamp01(value, base.get(str(key), 0.0))
    return base


def _digit(value: int) -> str:
    value = int(value)
    if value < 0:
        value = 0
    if value >= len(_BASE12_DIGITS):
        value = len(_BASE12_DIGITS) - 1
    return _BASE12_DIGITS[value]


def _duodecimal_trace(value: float) -> str:
    bounded = _clamp01(value)
    whole = int(max(0.0, min(11.0, math.floor(bounded * 11.0 + 1e-9))))
    frac = bounded * 11.0 - whole
    first = int(max(0.0, min(11.0, math.floor(frac * 12.0 + 1e-9))))
    second = int(max(0.0, min(11.0, math.floor((frac * 12.0 - first) * 12.0 + 1e-9))))
    return f"{_digit(whole)}.{_digit(first)}{_digit(second)}"


@dataclass
class Base12Telemetry:
    vector: List[float]
    index: int
    label: str
    trace: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vector": list(self.vector),
            "index": int(self.index),
            "label": self.label,
            "trace": self.trace,
        }


@dataclass
class SE42Signals:
    version: str
    coherence: float
    impetus: float
    equilibrium: float
    risk: float
    uncertainty: float
    mirror_consistency: float
    substrate: float
    ethos: Dict[str, float]
    readiness: str
    gate_state: str
    base12: Base12Telemetry
    comfort: float
    window_avg_impetus: float
    explain: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["base12"] = self.base12.to_dict()
        return data


class SymbolicEquation42Lotus:
    """Config-driven SE4.2 engine with duodecimal smoothing."""

    def __init__(self, config: Mapping[str, Any], *, audit_event: Optional[str] = None) -> None:
        self.config = dict(config or {})
        defaults = dict(self.config.get("defaults", {}))
        self._coherence = _clamp01(defaults.get("coherence", 0.84))
        self._impetus = _clamp01(defaults.get("impetus", 0.56))
        self._risk = _clamp01(defaults.get("risk", 0.18))
        self._uncertainty = _clamp01(defaults.get("uncertainty", 0.24))
        self._phase = 0.0
        self._history: MutableSequence[float] = []
        self._ethos_defaults = dict(defaults.get("ethos", {}))
        self._comfort_default = _clamp01(defaults.get("comfort", 0.82))
        self._audit_event = audit_event
        smoothing = self.config.get("smoothing", {})
        self._alpha_coherence = _clamp(smoothing.get("coherence_alpha", 0.42), 0.0, 1.0, 0.42)
        self._alpha_impetus = _clamp(smoothing.get("impetus_alpha", 0.38), 0.0, 1.0, 0.38)
        self._history_window = max(1, int(smoothing.get("window", 6)))
        audit_ndjson("se42_engine_init", version=SE42_VERSION, window=self._history_window)

    # ------------------------------------------------------------------
    def evaluate(self, ctx: Optional[Mapping[str, Any]] = None) -> SE42Signals:
        context = dict(ctx or {})
        mirror_node = context.get("mirror") or {}
        substrate_node = context.get("substrate") or {}

        coherence_hint = _clamp01(context.get("coherence_hint", self._coherence))
        risk_hint = _clamp01(context.get("risk_hint", self._risk))
        uncertainty_hint = _clamp01(context.get("uncertainty_hint", self._uncertainty))
        mirror_consistency = _clamp01(mirror_node.get("consistency", context.get("mirror_consistency", 0.76)))
        substrate = _clamp01(substrate_node.get("S_EM", context.get("S_EM", 0.82)))
        comfort_hint = _clamp01(context.get("comfort_hint", self._comfort_default))

        # Update smoothed state
        self._coherence = self._smooth(self._coherence, coherence_hint, self._alpha_coherence)
        self._risk = self._smooth(self._risk, risk_hint, 0.35)
        self._uncertainty = self._smooth(self._uncertainty, uncertainty_hint, 0.35)

        ethos = _merge_ethos(self._ethos_defaults, context.get("ethos_hint"))
        ethos_avg = sum(float(v) for v in ethos.values()) / max(1, len(ethos))

        phase = self._resolve_phase(context)
        base12_vector = self._phase_kernel(phase)
        phase_index = int(round(phase * 12.0)) % 12
        phase_label = self._phase_labels()[phase_index]

        impetus_raw = self._compute_impetus(
            mirror=mirror_consistency,
            substrate=substrate,
            ethos_avg=ethos_avg,
            phase_alignment=base12_vector[phase_index],
            comfort=comfort_hint,
            risk=self._risk,
            uncertainty=self._uncertainty,
        )
        self._impetus = self._smooth(self._impetus, impetus_raw, self._alpha_impetus)
        self._update_history(self._impetus)
        window_avg = sum(self._history) / max(1, len(self._history))

        equilibrium = _clamp01(
            0.45 * self._coherence
            + 0.35 * self._impetus
            + 0.10 * substrate
            + 0.10 * base12_vector[phase_index]
            - 0.15 * self._risk
            - 0.12 * self._uncertainty
            + 0.05 * ethos_avg
        )

        readiness = self._readiness(self._coherence, self._impetus)
        gate_state = self._gate_state(self._impetus)

        telemetry = Base12Telemetry(
            vector=base12_vector,
            index=phase_index,
            label=phase_label,
            trace=_duodecimal_trace(self._impetus),
        )

        signals = SE42Signals(
            version=SE42_VERSION,
            coherence=self._coherence,
            impetus=self._impetus,
            equilibrium=equilibrium,
            risk=self._risk,
            uncertainty=self._uncertainty,
            mirror_consistency=mirror_consistency,
            substrate=substrate,
            ethos=ethos,
            readiness=readiness,
            gate_state=gate_state,
            base12=telemetry,
            comfort=comfort_hint,
            window_avg_impetus=window_avg,
            explain="SymbolicEquation42Lotus",
        )

        if self._audit_event:
            payload = {
                key: signals.to_dict().get(key)
                for key in self.config.get("audit", {}).get("fields", [])
                if key in signals.to_dict()
            }
            payload.setdefault("version", SE42_VERSION)
            audit_ndjson(self._audit_event, **payload)
        return signals

    def evaluate_dict(self, ctx: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        return self.evaluate(ctx).to_dict()

    # ------------------------------------------------------------------
    def phase_labels(self) -> List[str]:
        """Return the configured (or default) phase labels."""

        return self._phase_labels()

    def _smooth(self, current: float, value: float, alpha: float) -> float:
        alpha = _clamp(alpha, 0.0, 1.0, alpha)
        return float(current * (1.0 - alpha) + value * alpha)

    def _update_history(self, value: float) -> None:
        self._history.append(float(value))
        while len(self._history) > self._history_window:
            self._history.pop(0)

    def _phase_labels(self) -> List[str]:
        labels = self.config.get("phase", {}).get("labels") or []
        if isinstance(labels, Iterable):
            resolved = [str(label) for label in labels]
            if len(resolved) >= 12:
                return resolved[:12]
        # Default fallback labels
        return [f"Lotus-{str(idx).zfill(2)}" for idx in range(12)]

    def _resolve_phase(self, ctx: Mapping[str, Any]) -> float:
        phase_hint = ctx.get("phase_hint")
        if phase_hint is None:
            phase_hint = ctx.get("t", self._phase)
        base_phase = float(phase_hint) if isinstance(phase_hint, (int, float)) else self._phase
        base_phase = float(base_phase) % 1.0
        phase_cfg = self.config.get("phase", {})
        gate_bias = _clamp01(phase_cfg.get("gate12_bias", 0.0))
        noise = _clamp01(phase_cfg.get("noise", 0.0))
        adjust = gate_bias * self._impetus + noise * (self._risk - self._uncertainty)
        resolved = (base_phase + adjust) % 1.0
        self._phase = resolved
        return resolved

    def _phase_kernel(self, phase: float) -> List[float]:
        decay = float(self.config.get("phase", {}).get("decay", 1.2))
        values: List[float] = []
        for idx in range(12):
            center = idx / 12.0
            distance = min(abs(phase - center), 1.0 - abs(phase - center))
            weight = math.exp(-decay * distance)
            values.append(weight)
        total = sum(values) or 1.0
        return [float(v / total) for v in values]

    def _compute_impetus(
        self,
        *,
        mirror: float,
        substrate: float,
        ethos_avg: float,
        phase_alignment: float,
        comfort: float,
        risk: float,
        uncertainty: float,
    ) -> float:
        weights = dict(self.config.get("impetus", {}).get("weights", {}))
        mirror_w = float(weights.get("mirror", 0.26))
        substrate_w = float(weights.get("substrate", 0.18))
        ethos_w = float(weights.get("ethos", 0.14))
        phase_w = float(weights.get("phase", 0.12))
        comfort_w = float(weights.get("comfort", 0.10))
        risk_w = float(weights.get("risk", 0.10))
        uncertainty_w = float(weights.get("uncertainty", 0.10))
        total_w = mirror_w + substrate_w + ethos_w + phase_w + comfort_w
        total_w = total_w if total_w > 0 else 1.0
        drive = (
            mirror_w * _clamp01(mirror)
            + substrate_w * _clamp01(substrate)
            + ethos_w * _clamp01(ethos_avg)
            + phase_w * _clamp01(phase_alignment)
            + comfort_w * _clamp01(comfort)
        ) / total_w
        damp = (1.0 - risk_w * _clamp01(risk)) * (1.0 - uncertainty_w * _clamp01(uncertainty))
        raw = drive * damp
        gate_bias = float(self.config.get("impetus", {}).get("gate_bias", 0.05))
        biased = raw + gate_bias * (drive - (risk + uncertainty) * 0.5)
        bounded = _clamp01(biased)
        minimum = _clamp01(self.config.get("impetus", {}).get("minimum", 0.08))
        maximum = _clamp01(self.config.get("impetus", {}).get("maximum", 0.98))
        return float(min(max(bounded, minimum), maximum))

    def _readiness(self, coherence: float, impetus: float) -> str:
        cfg = self.config.get("readiness", {})
        prime = cfg.get("prime", {})
        ready = cfg.get("ready", {})
        warming = cfg.get("warming", {})
        if coherence >= float(prime.get("coherence", 0.88)) and impetus >= float(prime.get("impetus", 0.60)):
            return "lotus-prime"
        if coherence >= float(ready.get("coherence", 0.80)) and impetus >= float(ready.get("impetus", 0.52)):
            return "lotus-ready"
        if coherence >= float(warming.get("coherence", 0.68)) and impetus >= float(warming.get("impetus", 0.45)):
            return "lotus-warming"
        return "baseline"

    def _gate_state(self, impetus: float) -> str:
        thresholds = self.config.get("gate_thresholds", {})
        allow = float(thresholds.get("allow", 0.72))
        review = float(thresholds.get("review", 0.55))
        if impetus >= allow:
            return "ALLOW"
        if impetus >= review:
            return "REVIEW"
        return "HOLD"
