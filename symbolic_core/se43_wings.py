"""SE4.3 Wings/Aletheia symbolic helpers.

This module keeps the bring-up experience lightweight while maintaining
compatibility with downstream components (QPIR, avatar policy, master key).
It provides a small deterministic engine that yields the key SE4.3 signals
expected by the rest of the stack.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import sqrt
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

try:  # Optional YAML dependency (PowerShell bring-up drops a YAML file)
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fall back to JSON parser
    yaml = None  # type: ignore

PHI = (1 + 5 ** 0.5) / 2.0
LOTUS = sqrt(2.0)
NORM = LOTUS / PHI

DEFAULT_CFG_PATH = Path("config/se43.yml")
DEFAULT_GATE12 = [0.97, 0.96, 0.95, 0.98, 0.94, 0.93, 0.97, 0.99, 0.95, 0.96, 0.94, 0.92]
DEFAULT_CONTEXT: Dict[str, Any] = {
    "alignment": 0.94,
    "memory_integrity": 0.91,
    "consent_delta": 0.05,
    "risk_guard": 0.93,
    "audit_fidelity": 0.91,
    "sovereignty_ratio": 0.9,
    "uncertainty": 0.12,
    "mirror_consistency": 0.9,
    "gate12": 0.96,
    "gate12_array": DEFAULT_GATE12,
    "omega": 0.04,
    "operator_focus": True,
    "incident_pressure": 0.03,
    "reality_alignment": 0.9,
}


def clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to [lo, hi] converting to float when possible."""

    try:
        val = float(value)
    except (TypeError, ValueError):
        val = float(lo)
    return max(lo, min(hi, val))


def weighted(values: Sequence[float], weights: Sequence[float]) -> float:
    """Return a weighted average with absolute weight normalisation."""

    if not values or not weights or len(values) != len(weights):
        return 0.0
    acc = 0.0
    wsum = 0.0
    for value, weight in zip(values, weights):
        acc += value * weight
        wsum += abs(weight)
    return acc / wsum if wsum else 0.0


def _normalise_gate(values: Optional[Iterable[Any]]) -> List[float]:
    seq = list(values) if values is not None else []
    if not seq:
        seq = list(DEFAULT_GATE12)
    if len(seq) < 12:
        seq = seq + [seq[-1]] * (12 - len(seq))
    return [clamp(item) for item in seq[:12]]


def _load_cfg(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    if yaml is not None:
        return dict(yaml.safe_load(text) or {})
    return dict(json.loads(text))


def assemble_se43_context(
    overrides: Optional[Mapping[str, Any]] = None,
    *,
    cfg: Optional[Mapping[str, Any]] = None,
    cfg_path: Path = DEFAULT_CFG_PATH,
) -> Dict[str, Any]:
    """Produce a baseline context for SE4.3 evaluation."""

    base = dict(DEFAULT_CONTEXT)
    config = dict(cfg) if cfg is not None else _load_cfg(cfg_path)

    gate_hint = config.get("gate_12")
    if isinstance(gate_hint, Iterable):
        base["gate12_array"] = _normalise_gate(gate_hint)
        base["gate12"] = sum(base["gate12_array"]) / len(base["gate12_array"])

    alignment_cfg = config.get("alignment") or {}
    gamma = alignment_cfg.get("gamma")
    if gamma is not None:
        base["gamma"] = clamp(gamma, 0.0, 1.0)

    if overrides:
        for key, value in overrides.items():
            if key == "gate12_array":
                base[key] = _normalise_gate(value if isinstance(value, Iterable) else None)
                base["gate12"] = sum(base[key]) / len(base[key]) if base[key] else base.get("gate12", 1.0)
            else:
                base[key] = value

    return base


@dataclass
class SE43Signals:
    coherence: float
    impetus: float
    risk: float
    uncertainty: float
    mirror_consistency: float
    readiness: str
    gate12: float
    wings: float
    reality_alignment: float
    gamma: float
    omega: float
    phi_echo: float
    gate12_array: List[float] = field(default_factory=list)
    version: str = "4.3.wings"

    @property
    def ra(self) -> float:
        return self.reality_alignment

    def as_dict(self) -> Dict[str, Any]:
        return {
            "coherence": round(self.coherence, 4),
            "impetus": round(self.impetus, 4),
            "risk": round(self.risk, 4),
            "uncertainty": round(self.uncertainty, 4),
            "mirror_consistency": round(self.mirror_consistency, 4),
            "readiness": self.readiness,
            "gate12": round(self.gate12, 4),
            "wings": round(self.wings, 4),
            "reality_alignment": round(self.reality_alignment, 4),
            "gamma": round(self.gamma, 4),
            "omega": round(self.omega, 4),
            "phi_echo": round(self.phi_echo, 4),
            "gate12_array": [round(x, 4) for x in self.gate12_array],
            "version": self.version,
        }


class WingsAletheia:
    def __init__(self, cfg: Optional[Mapping[str, Any]] = None) -> None:
        self.cfg = dict(cfg or {})
        alignment_cfg = self.cfg.get("alignment") or {}
        self.gamma = clamp(alignment_cfg.get("gamma", 0.7))
        wings_cfg = self.cfg.get("wings") or {}
        self.omega_cap = clamp(wings_cfg.get("omega_max", 0.06), 0.0, 0.2)
        compat_cfg = self.cfg.get("human_compat") or {}
        self.phi_bias = bool(compat_cfg.get("phi_echo", True))
        self._base_context = assemble_se43_context(cfg=self.cfg)

    @staticmethod
    def _vector_norm(values: Sequence[float]) -> float:
        return sqrt(sum(max(0.0, v) ** 2 for v in values)) / NORM

    def _phi_echo(self, wings: float, ra_value: float) -> float:
        base = clamp((wings + ra_value) / 2.0)
        return clamp(base * PHI / NORM) if self.phi_bias else base

    def evaluate(self, sample: Optional[Mapping[str, Any]] = None) -> SE43Signals:
        payload = dict(self._base_context)
        if sample:
            payload.update(sample)
            if "gate12_array" in sample:
                payload["gate12_array"] = _normalise_gate(sample.get("gate12_array"))

        alignment = clamp(payload.get("alignment", 0.0))
        memory = clamp(payload.get("memory_integrity", alignment))
        consent = clamp(payload.get("consent_delta", 0.0))
        wings = self._vector_norm([alignment, memory, consent])

        risk_guard = clamp(payload.get("risk_guard", 0.9))
        audit_fidelity = clamp(payload.get("audit_fidelity", 0.9))
        sovereignty = clamp(payload.get("sovereignty_ratio", 0.9))
        ra_value = clamp(weighted([risk_guard, audit_fidelity, sovereignty], [0.4, 0.35, 0.25]))

        impetus = clamp((wings + ra_value) / 2.0)

        risk_sources = [
            1.0 - risk_guard,
            1.0 - audit_fidelity,
            clamp(payload.get("incident_pressure", 0.05)),
        ]
        risk = clamp(sum(risk_sources) / len(risk_sources))

        coherence_inputs = [alignment, memory, clamp(payload.get("mirror_consistency", impetus))]
        coherence = clamp(sum(coherence_inputs) / len(coherence_inputs))

        uncertainty = clamp(payload.get("uncertainty", 1.0 - impetus * 0.8))
        mirror_consistency = clamp(payload.get("mirror_consistency", coherence))

        gate12_array = _normalise_gate(payload.get("gate12_array"))
        gate12 = clamp(payload.get("gate12", sum(gate12_array) / len(gate12_array)))

        omega_raw = clamp(payload.get("omega", wings * self.gamma))
        omega = min(omega_raw, self.omega_cap)
        phi_echo = self._phi_echo(wings, ra_value)

        gamma = self.gamma
        reality_alignment = ra_value

        readiness = "prime_ready"
        if wings < 0.85 or reality_alignment < 0.82 or risk > 0.08:
            readiness = "hold"
        if omega > self.omega_cap * 0.95 or uncertainty > 0.35:
            readiness = "watch"

        return SE43Signals(
            coherence=coherence,
            impetus=impetus,
            risk=risk,
            uncertainty=uncertainty,
            mirror_consistency=mirror_consistency,
            readiness=readiness,
            gate12=gate12,
            wings=wings,
            reality_alignment=reality_alignment,
            gamma=gamma,
            omega=omega,
            phi_echo=phi_echo,
            gate12_array=gate12_array,
        )


class SymbolicEquation43:
    """Minimal Symbolic Equation wrapper preserving the legacy interface."""

    def __init__(self, cfg: Optional[Mapping[str, Any]] = None) -> None:
        self.cfg = dict(cfg or {})
        self._engine = WingsAletheia(self.cfg)
        self._seed = assemble_se43_context(cfg=self.cfg)

    def seed_context(self) -> Dict[str, Any]:
        return dict(self._seed)

    def context_template(self) -> Dict[str, Any]:
        return self.seed_context()

    def evaluate(self, ctx: Optional[Mapping[str, Any]] = None) -> SE43Signals:
        payload = self.seed_context()
        if ctx:
            payload.update(ctx)
        return self._engine.evaluate(payload)


__all__ = [
    "SE43Signals",
    "SymbolicEquation43",
    "WingsAletheia",
    "assemble_se43_context",
    "clamp",
]

