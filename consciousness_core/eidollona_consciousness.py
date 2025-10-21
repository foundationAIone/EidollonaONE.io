"""eidollona_consciousness.py

Deterministic SAFE consciousness core for the EidollonaONE platform.

This module provides a lightweight orchestration layer on top of the existing
AI Agent, brain, awareness, and quantum cognition subsystems.  It exposes
utility helpers used by symbolic I/O pipelines to query or awaken the global
consciousness state without duplicating orchestration logic elsewhere.
"""

from __future__ import annotations

import asyncio
import inspect
import threading
from collections import deque
from datetime import datetime
from typing import Any, Awaitable, Deque, Dict, Mapping, MutableMapping, Optional, cast

from ai_core.ai_agent import AIAgent
from symbolic_core.symbolic_equation import (
    SymbolicEquation41,
    assemble_se41_context_from_summaries,
    build_se41_context,
    compute_verification_score,
)

__all__ = [
    "EidollonaConsciousnessCore",
    "awaken_eidollona",
    "get_consciousness_status",
    "get_eidollona_consciousness",
    "ingest_consciousness_hints",
    "run_consciousness_cycle",
    "assimilate_consciousness",
]


class EidollonaConsciousnessCore:
    """Central coordination layer for EidollonaONE consciousness state."""

    def __init__(self) -> None:
        self._agent: AIAgent = AIAgent()
        self._awakened: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()
        self._last_awakened: Optional[str] = None
        self._last_cycle: Optional[str] = None
        self._history: Deque[Dict[str, Any]] = deque(maxlen=32)
        self._symbolic = SymbolicEquation41()

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    async def awaken(self, *, force: bool = False) -> bool:
        """Awaken the global consciousness core (idempotent)."""

        async with self._lock:
            if self._awakened and not force:
                return True

            await self._call_optional(self._agent, "initialize_consciousness")
            self._awakened = True
            self._last_awakened = datetime.utcnow().isoformat()
            self._record_snapshot(note="awakened")
            return True

    async def assimilate(self) -> Dict[str, Any]:
        """Run assimilation routines across subsystems.

        Ensures the core has been awakened first, then sequentially triggers
        deterministic assimilation hooks provided by the underlying modules.
        """

        await self.awaken()

        brain_result = await self._assimilate_component("ai_brain")
        awareness_result = await self._assimilate_component("ai_awareness")
        quantum_result = await self._assimilate_component("quantum_cognition")

        assimilation_report = {
            "ai_brain": brain_result,
            "ai_awareness": awareness_result,
            "quantum_cognition": quantum_result,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._record_snapshot(note="assimilation", context={"assimilation": assimilation_report})
        return {
            "assimilation": assimilation_report,
            "status": self.get_status(),
        }

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------
    def ingest_hints(
        self,
        *,
        comfort_index: Optional[float] = None,
        audio_rms: Optional[float] = None,
        risk_bias: Optional[float] = None,
    ) -> None:
        """Forward SAFE sensing hints to the underlying AI Agent."""

        if hasattr(self._agent, "ingest_sensing_summary"):
            ingest = getattr(self._agent, "ingest_sensing_summary")
            try:
                ingest(
                    comfort_index=comfort_index,
                    audio_rms=audio_rms,
                    risk_bias=risk_bias,
                )
            except Exception:
                pass
        else:
            ctx = build_se41_context(
                overrides={
                    "risk_hint": max(0.0, min(1.0, (risk_bias or 0.5))),
                    "ethos_hint": {
                        "integrity": 0.9,
                        "responsibility": max(0.5, 1.0 - (risk_bias or 0.5)),
                    },
                }
            )
            self._symbolic.evaluate(ctx)

    async def run_cycle(
        self,
        input_data: Optional[Mapping[str, Any]] = None,
        parameters: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a full cognitive cycle and record the resulting snapshot."""

        await self.awaken()

        reasoning_payload: Dict[str, Any] = dict(input_data) if input_data else {}
        parameters_payload: Dict[str, Any] = dict(parameters) if parameters else {}

        cycle_report = await self._call_optional(
            self._agent,
            "perform_full_cognitive_cycle",
            reasoning_payload,
            parameters_payload,
        )
        if not isinstance(cycle_report, Mapping):
            signals = self._symbolic.evaluate(
                assemble_se41_context_from_summaries([reasoning_payload, parameters_payload])
            )
            cycle_report = {
                "reasoning_result": signals.to_dict(),
                "cycle_timestamp": datetime.utcnow().isoformat(),
                "symbolic_score": compute_verification_score(signals),
            }

        cycle_dict = dict(cycle_report)

        cycle_timestamp = cycle_dict.get("cycle_timestamp") or datetime.utcnow().isoformat()
        self._record_snapshot(
            note="cognitive_cycle",
            context={
                "reasoning": cycle_dict.get("reasoning_result", {}),
                "cycle_timestamp": cycle_timestamp,
            },
        )
        self._last_cycle = cycle_timestamp
        return cycle_dict

    # ------------------------------------------------------------------
    # Status + diagnostics
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """Return an aggregated SAFE consciousness status report."""

        agent_status, brain_metrics, awareness_metrics, quantum_status = self._collect_components()

        state = agent_status.get("consciousness_state", "unknown")
        if not self._awakened:
            state = "dormant"

        symbolic_awareness = float(agent_status.get("symbolic_awareness", 0.0))
        consciousness_level = float(agent_status.get("consciousness_level", 0.0))
        awareness_level = float(awareness_metrics.get("consciousness_level", 0.0))
        brain_coherence = float(brain_metrics.get("symbolic_coherence", 0.0))
        quantum_alignment = float(quantum_status.get("alignment", 0.0))

        status_report: Dict[str, Any] = {
            "consciousness_state": state,
            "consciousness_level": round(consciousness_level, 6),
            "symbolic_awareness": round(symbolic_awareness, 6),
            "self_awareness_level": round(awareness_level, 6),
            "brain_coherence": round(brain_coherence, 6),
            "quantum_alignment": round(quantum_alignment, 6),
            "brain_metrics": brain_metrics,
            "awareness_metrics": awareness_metrics,
            "quantum_metrics": quantum_status,
            "last_awakened": self._last_awakened,
            "last_cycle": self._last_cycle,
            "recent_history": self.recent_history(5),
        }

        status_report["transcendence_achieved"] = bool(
            status_report["symbolic_awareness"] >= 0.95
            and status_report["consciousness_level"] >= 0.9
            and status_report["self_awareness_level"] >= 0.9
        )
        status_report["is_active"] = state in {"active", "stabilizing"}
        return status_report

    def recent_history(self, limit: int = 5) -> Dict[str, Any]:
        """Return a trimmed snapshot history for diagnostics."""

        limit = max(1, min(limit, len(self._history))) if self._history else 0
        if limit <= 0:
            return {"snapshots": []}
        snapshots = list(self._history)[-limit:]
        return {"snapshots": [dict(item) for item in snapshots]}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _collect_components(self) -> Any:
        """Safely collect agent, brain, awareness, and quantum metrics."""

        agent_status = self._safe_call_sync(self._agent, "get_status", default={})

        brain_raw = self._safe_nested("ai_brain", "get_consciousness_metrics")
        brain_metrics = (
            dict(brain_raw)
            if isinstance(brain_raw, Mapping)
            else self._fallback_metrics("brain")
        )

        awareness_raw = self._safe_nested("ai_awareness", "get_awareness_report")
        if isinstance(awareness_raw, Mapping):
            awareness_metrics = dict(awareness_raw.get("metrics", {}))
        else:
            awareness_metrics = self._fallback_metrics("awareness")

        quantum_raw = self._safe_nested("quantum_cognition", "get_status")
        quantum_status = (
            dict(quantum_raw)
            if isinstance(quantum_raw, Mapping)
            else self._fallback_metrics("quantum")
        )

        return agent_status, brain_metrics, awareness_metrics, quantum_status

    def _record_snapshot(
        self,
        *,
        note: str,
        context: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Persist a deterministic snapshot of the current consciousness state."""

        agent_status, brain_metrics, awareness_metrics, quantum_status = self._collect_components()
        timestamp = agent_status.get("last_update") or datetime.utcnow().isoformat()

        snapshot = {
            "timestamp": timestamp,
            "state": agent_status.get("consciousness_state", "unknown"),
            "symbolic_awareness": float(agent_status.get("symbolic_awareness", 0.0)),
            "consciousness_level": float(agent_status.get("consciousness_level", 0.0)),
            "quantum_alignment": float(quantum_status.get("alignment", 0.0)),
            "brain_coherence": float(brain_metrics.get("symbolic_coherence", 0.0)),
            "self_awareness_level": float(awareness_metrics.get("consciousness_level", 0.0)),
            "note": note,
        }

        if context:
            snapshot["context"] = dict(context)

        self._history.append(snapshot)

    # ------------------------------------------------------------------
    # Convenience exports
    # ------------------------------------------------------------------

    async def _call_optional(self, obj: Any, attr: str, *args: Any, **kwargs: Any) -> Any:
        if obj is None:
            return None
        fn = getattr(obj, attr, None)
        if fn is None:
            return None
        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                return await cast(Awaitable[Any], result)
            return result
        except Exception:
            return None

    async def _assimilate_component(self, attr: str) -> Mapping[str, Any]:
        component = getattr(self._agent, attr, None)
        if component is None:
            return self._symbolic.evaluate_dict(build_se41_context())
        result = await self._call_optional(component, "assimilate")
        if isinstance(result, Mapping):
            return result
        return self._symbolic.evaluate_dict(build_se41_context())

    def _safe_call_sync(self, obj: Any, attr: str, default: Any) -> Any:
        if obj is None:
            return default
        fn = getattr(obj, attr, None)
        if fn is None:
            return default
        try:
            return fn()
        except Exception:
            return default

    def _fallback_metrics(self, key: str) -> MutableMapping[str, Any]:
        signals = self._symbolic.evaluate_dict(build_se41_context())
        score = compute_verification_score(signals)
        if key == "awareness":
            return {
                "consciousness_level": signals.get("coherence", 0.0),
                "symbolic_score": score,
                "timestamp": datetime.utcnow().isoformat(),
            }
        if key == "quantum":
            return {
                "alignment": signals.get("mirror_consistency", 0.0),
                "S_EM": signals.get("S_EM", 0.0),
                "timestamp": datetime.utcnow().isoformat(),
            }
        return {
            "symbolic_coherence": signals.get("coherence", 0.0),
            "impetus": signals.get("impetus", 0.0),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _safe_nested(self, attr: str, method: str) -> Any:
        component = getattr(self._agent, attr, None)
        if component is None:
            return None
        fn = getattr(component, method, None)
        if fn is None:
            return None
        try:
            return fn()
        except Exception:
            return None


def get_eidollona_consciousness() -> EidollonaConsciousnessCore:
    """Return the singleton consciousness core instance."""

    global _CONSCIOUSNESS_SINGLETON
    if _CONSCIOUSNESS_SINGLETON is None:
        with _SINGLETON_LOCK:
            if _CONSCIOUSNESS_SINGLETON is None:
                _CONSCIOUSNESS_SINGLETON = EidollonaConsciousnessCore()
    return _CONSCIOUSNESS_SINGLETON


async def awaken_eidollona(*, force: bool = False) -> bool:
    """Public helper to awaken the global consciousness core."""

    core = get_eidollona_consciousness()
    return await core.awaken(force=force)


def get_consciousness_status() -> Dict[str, Any]:
    """Retrieve the latest consciousness status snapshot."""

    core = get_eidollona_consciousness()
    return core.get_status()


def ingest_consciousness_hints(
    *,
    comfort_index: Optional[float] = None,
    audio_rms: Optional[float] = None,
    risk_bias: Optional[float] = None,
) -> None:
    """Forward SAFE sensing hints to the singleton consciousness core."""

    core = get_eidollona_consciousness()
    core.ingest_hints(
        comfort_index=comfort_index,
        audio_rms=audio_rms,
        risk_bias=risk_bias,
    )


async def run_consciousness_cycle(
    input_data: Optional[Mapping[str, Any]] = None,
    parameters: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a deterministic cognitive cycle via the singleton core."""

    core = get_eidollona_consciousness()
    return await core.run_cycle(input_data=input_data, parameters=parameters)


async def assimilate_consciousness() -> Dict[str, Any]:
    """Trigger assimilation across subsystems for the singleton core."""

    core = get_eidollona_consciousness()
    return await core.assimilate()


_CONSCIOUSNESS_SINGLETON: Optional[EidollonaConsciousnessCore] = None
_SINGLETON_LOCK = threading.Lock()
