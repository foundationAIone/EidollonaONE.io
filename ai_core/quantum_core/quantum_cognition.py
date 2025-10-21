"""quantum_cognition.py

Deterministic quantum cognition harmonizer for the EidollonaONE SAFE stack.

The module provides:
- Stable quantum alignment tracking with bounded 0..1 outputs.
- Recalibration based on symbolic reasoning signals and brain metrics.
- Optional ingestion of SAFE quantum telemetry summaries (no raw sensor data).
- MasterKey-driven seed extras so repeated runs remain reproducible.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

from symbolic_core.context_builder import assemble_se41_context
from symbolic_core.symbolic_equation import SE41Signals, SymbolicEquation41

try:  # Optional deterministic seed/context
    from master_key.quantum_master_key import get_master_key
except Exception:  # pragma: no cover
    get_master_key = None  # type: ignore

__all__ = ["QuantumCognition"]


class QuantumCognition:
    """SAFE-first quantum cognition manager."""

    def __init__(self) -> None:
        self._alignment: float = 0.93
        self._stability: float = 0.9
        self._drift: float = 0.04
        self._last_update: Optional[str] = None
        self._symbolic = SymbolicEquation41()
        self._mk = get_master_key() if callable(get_master_key) else None
        self._signals: Optional[SE41Signals] = None
        self._hints: Dict[str, float] = {
            "phase_bias": 0.0,
            "noise_floor": 0.08,
            "comfort": 0.82,
        }

    # ------------------------------------------------------------------
    # External hint ingestion
    # ------------------------------------------------------------------
    def ingest_quantum_summary(
        self,
        *,
        phase_bias: Optional[float] = None,
        noise_floor: Optional[float] = None,
        comfort: Optional[float] = None,
    ) -> None:
        """Ingest SAFE summary metrics to influence quantum recalibration."""

        if isinstance(phase_bias, (int, float)):
            self._hints["phase_bias"] = self._clip(phase_bias, -0.25, 0.25)
        if isinstance(noise_floor, (int, float)):
            self._hints["noise_floor"] = self._clip(noise_floor, 0.0, 1.0)
        if isinstance(comfort, (int, float)):
            self._hints["comfort"] = self._clip(comfort, 0.0, 1.0)

    # ------------------------------------------------------------------
    # Public API consumed by AIAgent / Manager
    # ------------------------------------------------------------------
    def current_alignment(self) -> float:
        """Return bounded quantum alignment (0..1)."""

        return self._clip(self._alignment, 0.0, 1.0)

    def get_status(self) -> Dict[str, Any]:
        """Status snapshot used by diagnostics when available."""

        return {
            "alignment": round(self.current_alignment(), 6),
            "stability": round(self._stability, 6),
            "drift": round(self._drift, 6),
            "last_update": self._last_update,
            "phase_bias": self._hints["phase_bias"],
            "noise_floor": self._hints["noise_floor"],
        }

    def recalibrate(self, signal_bundle: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """Recalibrate quantum alignment using symbolic reasoning outputs."""

        signals_map = self._extract_signals(signal_bundle)
        brain_state = self._extract_brain_state(signal_bundle)

        context = self._build_context(signals_map, brain_state)
        self._signals = self._symbolic.evaluate(context)

        self._alignment = self._blend(self._alignment, float(self._signals.coherence))
        self._stability = self._blend(self._stability, float(self._signals.mirror_consistency))
        self._drift = self._blend(self._drift, float(brain_state.get("cognitive_load", 0.2)))
        self._last_update = datetime.utcnow().isoformat()

        recalibration_report = {
            "alignment": self.current_alignment(),
            "stability": round(self._stability, 6),
            "drift": round(self._drift, 6),
            "impetus": float(self._signals.impetus) if self._signals else None,
            "risk": float(self._signals.risk) if self._signals else None,
            "uncertainty": float(self._signals.uncertainty) if self._signals else None,
            "last_update": self._last_update,
        }

        return recalibration_report

    async def assimilate(self) -> str:
        """Async assimilation hook for coordinated system resets."""

        await asyncio.sleep(0)
        self._alignment = self._blend(self._alignment, 0.96)
        self._stability = self._blend(self._stability, 0.95)
        self._drift = self._blend(self._drift, 0.02)
        self._last_update = datetime.utcnow().isoformat()
        return (
            "QuantumCognition assimilation complete; "
            f"alignment={self._alignment:.3f} stability={self._stability:.3f}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_context(
        self,
        signals_map: Mapping[str, float],
        brain_state: Mapping[str, float],
    ) -> Dict[str, Any]:
        coherence_hint = signals_map.get("coherence", self._alignment)
        impetus = signals_map.get("impetus", 0.6)
        risk_hint = signals_map.get("risk", 0.18)
        uncertainty_hint = signals_map.get("uncertainty", 0.25)

        load = self._clip(brain_state.get("cognitive_load", 0.25), 0.0, 1.0)
        clarity = self._clip(brain_state.get("reasoning_clarity", 0.8), 0.0, 1.0)
        learning = self._clip(brain_state.get("learning_rate", 0.01), 0.0001, 0.1)

        extras = self._masterkey_extras(
            phase_bias=self._hints["phase_bias"],
            learning_rate=learning,
            comfort=self._hints["comfort"],
        )
        context = assemble_se41_context(
            coherence_hint=self._clip(coherence_hint, 0.0, 1.0),
            risk_hint=self._clip(risk_hint + load * 0.1 + self._hints["noise_floor"] * 0.05, 0.0, 1.0),
            uncertainty_hint=self._clip(uncertainty_hint + (1.0 - clarity) * 0.2, 0.0, 1.0),
            mirror_consistency=self._clip(self._stability, 0.0, 1.0),
            s_em=self._clip(0.85 + (impetus - 0.5) * 0.1, 0.7, 0.98),
        )
        for key, value in extras.items():
            if isinstance(value, Mapping) and isinstance(context.get(key), Mapping):
                merged = dict(context[key])
                merged.update(value)
                context[key] = merged
            else:
                context[key] = value

        context.setdefault("quantum", {})
        context["quantum"].update(
            {
                "alignment_memory": float(self._alignment),
                "stability": float(self._stability),
                "recent_impetus": float(impetus),
            }
        )

        return context

    def _masterkey_extras(
        self,
        *,
        phase_bias: float,
        learning_rate: float,
        comfort: float,
    ) -> Dict[str, Any]:
        extras: Dict[str, Any] = {
            "quantum": {
                "phase_bias": phase_bias,
                "learning_rate": learning_rate,
                "comfort": comfort,
            }
        }
        if not self._mk:
            return extras
        try:
            se41_extractor = getattr(self._mk, "se41_extras", None)
            if callable(se41_extractor):
                mk_extras: Any = se41_extractor()
            elif isinstance(self._mk, Mapping):
                mk_extras = dict(self._mk)
            else:
                return extras
        except Exception:
            return extras
        if isinstance(mk_extras, Mapping):
            extras.update(dict(mk_extras))
        else:
            extras["master_key_extras"] = mk_extras
        return extras

    def _extract_signals(self, payload: Optional[Mapping[str, Any]]) -> Dict[str, float]:
        if not payload:
            return {}
        signals = payload.get("signals") if isinstance(payload, Mapping) else None
        if isinstance(signals, Mapping):
            return {
                "coherence": float(signals.get("coherence", 0.85)),
                "impetus": float(signals.get("impetus", 0.6)),
                "risk": float(signals.get("risk", 0.18)),
                "uncertainty": float(signals.get("uncertainty", 0.24)),
            }
        return {}

    def _extract_brain_state(self, payload: Optional[Mapping[str, Any]]) -> Dict[str, float]:
        if not payload:
            return {}
        brain_state = payload.get("brain_state") if isinstance(payload, Mapping) else None
        if isinstance(brain_state, Mapping):
            return {
                "cognitive_load": float(brain_state.get("cognitive_load", 0.25)),
                "reasoning_clarity": float(brain_state.get("reasoning_clarity", 0.82)),
                "learning_rate": float(brain_state.get("learning_rate", 0.01)),
            }
        return {}

    @staticmethod
    def _blend(current: float, incoming: float, weight: float = 0.55) -> float:
        current = float(current)
        incoming = float(incoming)
        return current * (1.0 - weight) + incoming * weight

    @staticmethod
    def _clip(value: float, lower: float, upper: float) -> float:
        if value < lower:
            return float(lower)
        if value > upper:
            return float(upper)
        return float(value)
