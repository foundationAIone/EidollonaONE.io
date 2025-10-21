"""Symbolic Equation v4.1 compatibility module.

Restores the legacy ``symbolic_core.symbolic_equation41`` import path by
re-exporting the canonical classes from ``symbolic_core.symbolic_equation``.
If the core module is unavailable (e.g., during partial bootstrap), a minimal,
deterministic fallback is provided so dependent modules keep operating in SAFE
mode with bounded signals.

Public re-exports:
  - SE41Signals
  - SymbolicEquation41
  - SymbolicEquation    (alias of SymbolicEquation41)
  - Reality
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Type, Protocol


try:
    # Import canonical core types; Reality may not exist in core, so handle separately.
    from symbolic_core.symbolic_equation import (  # type: ignore
        SE41Signals as _CoreSE41Signals,
        SymbolicEquation41 as _CoreSymbolicEquation41,
    )
    try:
        from symbolic_core.symbolic_equation import Reality as _CoreReality  # type: ignore
    except Exception:  # pragma: no cover - provide a lightweight alias without redeclaration
        _CoreReality = _CoreSymbolicEquation41  # type: ignore[assignment]
except Exception:  # pragma: no cover - SAFE fallback kept intentionally lightweight

    def _clip01(x: float) -> float:
        return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

    class _FallbackSE41Signals:
        """Deterministic, bounded placeholder signals."""

        def __init__(
            self,
            coherence: float = 0.80,
            impetus: float = 0.60,
            risk: float = 0.20,
            uncertainty: float = 0.25,
            mirror_consistency: float = 0.70,
            S_EM: float = 0.78,
            ethos: Optional[Dict[str, float]] = None,
            embodiment: Optional[Dict[str, float]] = None,
            explain: str = "shim",
        ) -> None:
            self.coherence = _clip01(float(coherence))
            self.impetus = _clip01(float(impetus))
            self.risk = _clip01(float(risk))
            self.uncertainty = _clip01(float(uncertainty))
            self.mirror_consistency = _clip01(float(mirror_consistency))
            self.S_EM = _clip01(float(S_EM))
            self.ethos = dict(
                ethos
                or {
                    "authenticity": 0.90,
                    "integrity": 0.90,
                    "responsibility": 0.88,
                    "enrichment": 0.90,
                }
            )
            self.embodiment = dict(embodiment or {"phase": 0.0})
            self.explain = explain

        @property
        def C_realize(self) -> float:
            return self.coherence

        @property
        def FZ1(self) -> float:
            return self.impetus

    class _FallbackSymbolicEquation41:
        """Minimal, SAFE SE41 shim used when the real core is unavailable."""

        _coherence: float = 0.80

        def evaluate(self, ctx: Optional[Mapping[str, Any]] = None) -> _FallbackSE41Signals:
            ctx = dict(ctx or {})
            coherence = _clip01(float(ctx.get("coherence_hint", self._coherence)))
            risk = _clip01(float(ctx.get("risk_hint", 0.20)))
            uncertainty = _clip01(float(ctx.get("uncertainty_hint", 0.25)))
            mirror = _clip01(float(ctx.get("mirror", {}).get("consistency", 0.70)))
            substrate = _clip01(float(ctx.get("substrate", {}).get("S_EM", 0.78)))

            ethos_hint = ctx.get("ethos_hint") or {}
            ethos = {
                "authenticity": _clip01(float(ethos_hint.get("authenticity", 0.90))),
                "integrity": _clip01(float(ethos_hint.get("integrity", 0.90))),
                "responsibility": _clip01(float(ethos_hint.get("responsibility", 0.88))),
                "enrichment": _clip01(float(ethos_hint.get("enrichment", 0.90))),
            }

            impetus = _clip01(coherence * mirror * (1.0 - risk))

            self._coherence = coherence

            return _FallbackSE41Signals(
                coherence=coherence,
                impetus=impetus,
                risk=risk,
                uncertainty=uncertainty,
                mirror_consistency=mirror,
                S_EM=substrate,
                ethos=ethos,
                embodiment={"phase": float(ctx.get("t", 0.0)) % 1.0},
                explain="shim",
            )

        def reality_manifestation(self, **kwargs: Any) -> float:
            coh = float(kwargs.get("coherence_hint", kwargs.get("Q", self._coherence)))
            self._coherence = _clip01(coh)
            return self._coherence

        def validate_update_coherence(self, data: Mapping[str, Any]) -> float:
            _ = data
            return self._coherence

        def get_coherence_level(self) -> float:
            return self._coherence

        def post_update_recalibration(self) -> None:  # pragma: no cover - no-op
            return None

        def get_consciousness_metrics(self) -> Dict[str, float]:
            return {"coherence": self._coherence, "risk": 0.20, "impetus": 0.60}

        def get_current_state_summary(self) -> Dict[str, Any]:
            return {
                "coherence_level": self._coherence,
                "ethos": 0.90,
                "node_consciousness": 1.0,
            }

        def consciousness_shift(self, delta: float) -> None:
            """Legacy hook to nudge internal coherence state by a small delta.

            Included to satisfy callers that expect this convenience on SE41.
            """
            try:
                self._coherence = max(0.0, min(1.0, float(self._coherence) + float(delta)))
            except Exception:
                self._coherence = max(0.0, min(1.0, self._coherence))

    # Provide a lightweight alias without redeclaration in fallback mode as well
    _CoreReality = _FallbackSymbolicEquation41  # type: ignore[assignment]

    _CoreSE41Signals = _FallbackSE41Signals
    _CoreSymbolicEquation41 = _FallbackSymbolicEquation41


class _SE41PublicAPI(Protocol):
    def evaluate(self, ctx: Mapping[str, Any]) -> Any: ...
    def evaluate_dict(self, ctx: Mapping[str, Any]) -> Dict[str, Any]: ...
    def get_current_state_summary(self) -> Dict[str, Any]: ...
    def consciousness_shift(self, delta: float) -> None: ...
    def reality_manifestation(self, **kwargs: Any) -> float: ...
    def get_consciousness_metrics(self) -> Dict[str, float]: ...
    def validate_update_coherence(self, data: Mapping[str, Any]) -> float: ...
    def get_coherence_level(self) -> float: ...
    def post_update_recalibration(self) -> None: ...

SE41Signals = _CoreSE41Signals
SymbolicEquation41: Type[_SE41PublicAPI] = _CoreSymbolicEquation41  # type: ignore[assignment]
SymbolicEquation = SymbolicEquation41
Reality = _CoreReality

__all__ = [
    "SE41Signals",
    "SymbolicEquation41",
    "SymbolicEquation",
    "Reality",
]