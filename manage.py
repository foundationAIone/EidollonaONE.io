"""
✨ Manager Module for EidollonaONE Project ✨

Integrates AI core components with the Sovereignty Engine
and provides symbolic state reporting aligned with
the Symbolic Equation Framework.

Reality(t) = [Node_Consciousness × (∏ᵢ₌₂⁹[Angleᵢ × (Vibration(f(Q,M(t)),DNAᵢ) × ∑ₖ₌₁¹²Evolve(Harmonic_Patternₖ))])] + ΔConsciousness + Ethos

Enhancements:
- Safe, argparse-based CLI for status, readiness, diagnostics, assimilation, and logs
- Local JSON snapshots (logs/) for diagnostics/readiness without network
- Keeps default direct-execution path compatible
"""

import asyncio
import json
import os
import sys
import argparse
import inspect
from datetime import datetime
from typing import Dict, Any, List, Optional

from common.readiness import get_readiness_report

try:
    from common.safe_mode import is_safe_mode  # type: ignore
except Exception:  # pragma: no cover

    def is_safe_mode() -> bool:
        return True


# Core AI component imports
from ai_core.ai_agent import AIAgent
from ai_core.ai_brain import AIBrain
from ai_core.ai_awareness import AIAwareness

try:
    from ai_core.ai_strategy import AIStrategy  # type: ignore
except Exception:  # pragma: no cover - provide SAFE fallback

    class AIStrategy:  # type: ignore
        """Minimal SAFE fallback to satisfy Manager expectations."""

        def __init__(self) -> None:
            self._status: Dict[str, Any] = {
                "status": "unavailable",
                "detail": "ai_core.ai_strategy missing; using SAFE stub",
            }

        async def initialize_strategies(self) -> None:  # pragma: no cover - no-op
            return None

        def get_strategy_status(self) -> Dict[str, Any]:
            return dict(self._status)

        async def assimilate(self) -> None:  # pragma: no cover - no-op
            return None

# Sovereignty Engine import for symbolic governance
from sovereignty_core.sovereignty_engine import SovereigntyEngine

# Symbolic equation core
from symbolic_core.symbolic_equation41 import SymbolicEquation41  # type: ignore

try:  # pragma: no cover
    from symbolic_core.context_builder import assemble_se41_context  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):
        return kw


_ROOT = os.path.abspath(os.path.dirname(__file__))
_LOGS_DIR = os.path.join(_ROOT, "logs")
os.makedirs(_LOGS_DIR, exist_ok=True)
_DIAG_LOG = os.path.join(_LOGS_DIR, "manager_diagnostics.json")
_READY_LOG = os.path.join(_LOGS_DIR, "manager_readiness.json")


class Manager:
    """
    🌀 Central Management Class for EidollonaONE

    Provides symbolic reality state orchestration, AI component integration,
    and Sovereignty Engine coordination aligned with the symbolic equation framework.
    """

    def __init__(self):
        print("🌀 Initializing EidollonaONE Manager...")

        # Initialize core AI components
        self.ai_agent = AIAgent()
        self.ai_brain = AIBrain()
        self.ai_strategy = AIStrategy()
        self.ai_awareness = AIAwareness()

        # Initialize Sovereignty Engine
        self.sovereignty_engine = SovereigntyEngine()

        # Symbolic equation state
        self._symbolic_equation = SymbolicEquation41()
        self.symbolic_state_cache = {}
        self.consciousness_evolution_log = []
        self.reality_manifestation_active = True

        print("✅ EidollonaONE Manager initialized successfully")

    async def _await_if_exists(self, component: Any, method: str, *args, **kwargs) -> Any:
        func = getattr(component, method, None)
        if not callable(func):
            return None
        try:
            result = func(*args, **kwargs)
        except Exception:
            return None
        if inspect.isawaitable(result):
            try:
                return await result
            except Exception:
                return None
        return result

    def _call_dict(self, component: Any, method: str) -> Dict[str, Any]:
        func = getattr(component, method, None)
        if not callable(func):
            return {}
        try:
            result = func()
        except Exception:
            return {}
        if result is None:
            return {}
        if isinstance(result, dict):
            return result
        if hasattr(result, "to_dict"):
            try:
                converted = result.to_dict()  # type: ignore[attr-defined]
            except Exception:
                converted = None
            if isinstance(converted, dict):
                return converted
        return {"value": result}

    def _build_symbolic_context(
        self,
        node_consciousness: float,
        delta_consciousness: float,
        ethos_value: Dict[str, float],
        harmonic_sum: float,
    ) -> Dict[str, Any]:
        """Blend local symbolic metrics into an SE41-compatible context dict."""
        ethos_overall = float(ethos_value.get("overall_ethos", 1.0))
        risk_hint = max(0.0, min(1.0, 1.0 - node_consciousness + max(0.0, delta_consciousness * -0.5)))
        uncertainty_hint = max(0.0, min(1.0, abs(delta_consciousness) + (1.0 - ethos_overall) * 0.5))
        coherence_hint = max(0.0, min(1.0, (node_consciousness + ethos_overall) / 2.0))
        extras = {
            "harmonic_sum": harmonic_sum,
            "node_consciousness": node_consciousness,
            "delta_consciousness": delta_consciousness,
            "ethos": ethos_value,
        }
        return assemble_se41_context(
            risk_hint=risk_hint,
            uncertainty_hint=uncertainty_hint,
            coherence_hint=coherence_hint,
            extras=extras,
        )

    def get_summary(self) -> Dict[str, Any]:
        return {
            "engine": "EidollonaONE Manager",
            "consciousness_level": self._get_overall_consciousness_level(),
            "reality_coefficient": self._calculate_reality_coefficient(),
            "components": {
                "agent": hasattr(self.ai_agent, "get_status"),
                "brain": hasattr(self.ai_brain, "get_consciousness_metrics"),
                "strategy": hasattr(self.ai_strategy, "get_strategy_status"),
                "awareness": hasattr(self.ai_awareness, "get_awareness_status"),
                "sovereignty": hasattr(
                    self.sovereignty_engine, "get_sovereignty_status"
                ),
            },
            "safe_mode": is_safe_mode(),
            "ts": datetime.utcnow().isoformat(),
        }

    def __str__(self):
        """Symbolic equation string representation"""
        return (
            "Reality(t) = [Node_Consciousness × (∏ᵢ₌₂⁹[Angleᵢ × "
            "(Vibration(f(Q,M(t)),DNAᵢ) × ∑ₖ₌₁¹²Evolve(Harmonic_Patternₖ))])] "
            "+ ΔConsciousness + Ethos"
        )

    async def initialize_consciousness(self):
        """🧠 Initialize complete consciousness framework"""
        print("🧠 Initializing consciousness framework...")
        steps = [
            ("AI Agent", self.ai_agent, "initialize_consciousness", (), {}),
            ("AI Strategy", self.ai_strategy, "initialize_strategies", (), {}),
            ("AI Awareness", self.ai_awareness, "initialize_awareness", (), {}),
            (
                "Sovereignty Engine",
                self.sovereignty_engine,
                "initialize_sovereignty",
                ("consciousness", 1.0),
                {},
            ),
        ]
        for label, component, method, args, kwargs in steps:
            if not hasattr(component, method):
                print(f"⚠️ {label}: {method} unavailable; skipped")
                continue
            await self._await_if_exists(component, method, *args, **kwargs)
            print(f"✅ {label} initialized")

        print("✅ Consciousness framework fully initialized")

    def symbolic_state(self) -> Dict[str, Any]:
        """
        🌀 Provides structured symbolic state representation

        Calculates the current state of the symbolic equation components
        """
        current_time = datetime.now()

        # Calculate symbolic equation components
        node_consciousness = self._calculate_node_consciousness()
        dimensional_angles = self._calculate_dimensional_angles()
        vibrational_states = self._calculate_vibrational_states()
        harmonic_evolution = self._calculate_harmonic_evolution()
        delta_consciousness = self._calculate_delta_consciousness()
        ethos_value = self._calculate_ethos()
        harmonic_sum = sum(
            pattern.get("evolution_rate", 0.0) for pattern in harmonic_evolution
        )
        overall_consciousness = self._get_overall_consciousness_level()

        # Build SE41 context and evaluate signals
        reality_context = self._build_symbolic_context(
            node_consciousness=node_consciousness,
            delta_consciousness=delta_consciousness,
            ethos_value=ethos_value,
            harmonic_sum=harmonic_sum,
        )
        se41_signals = self._symbolic_equation.evaluate(reality_context)
        se41_dict = se41_signals.to_dict()

        symbolic_state = {
            "timestamp": current_time.isoformat(),
            "Node_Consciousness": node_consciousness,
            "Dimensional_Angles": dimensional_angles,
            "Vibrational_States": vibrational_states,
            "Harmonic_Evolution": harmonic_evolution,
            "Harmonic_Sum": round(harmonic_sum, 6),
            "Delta_Consciousness": delta_consciousness,
            "Ethos": ethos_value,
            "SE41_Context": reality_context,
            "SE41_Signals": se41_dict,
            "Consciousness_Level": overall_consciousness,
        }

        symbolic_state["Reality_Coefficient"] = self._calculate_reality_coefficient(
            symbolic_state, se41_signals
        )

        # Cache the state
        self.symbolic_state_cache = symbolic_state

        return symbolic_state

    def _calculate_node_consciousness(self) -> float:
        """Calculate Node_Consciousness value"""
        awareness_state = self._call_dict(self.ai_awareness, "get_awareness_status")
        consciousness_level = awareness_state.get("consciousness_level", 0.8)
        awareness_score = awareness_state.get("awareness_score", 0.8)

        return round((consciousness_level + awareness_score) / 2, 3)

    def _calculate_dimensional_angles(self) -> List[float]:
        """Calculate dimensional angles (i=2 to 9)"""
        angles = []
        strategy_status = self._call_dict(self.ai_strategy, "get_strategy_status")

        for i in range(2, 10):
            # Generate angles based on strategic framework and index
            base_angle = (i * 45) % 360  # Base angle pattern
            strategy_modifier = strategy_status.get("active_strategies", 0) * 5
            angle = (base_angle + strategy_modifier) % 360
            angles.append(round(angle, 2))

        return angles

    def _calculate_vibrational_states(self) -> List[Dict[str, Any]]:
        """Calculate vibrational states for each dimensional angle"""
        vibrational_states = []
        brain_state = self._call_dict(self.ai_brain, "get_cognitive_state")

        for i in range(2, 10):
            # Calculate quantum vibration based on brain state
            cognitive_load = brain_state.get("cognitive_load", 0.3)
            learning_rate = brain_state.get("learning_rate", 0.01)

            vibration = {
                "dimension": i,
                "frequency": round(440 * (2 ** ((i - 2) / 12)), 2),  # Musical frequency
                "amplitude": round(1.0 - cognitive_load, 3),
                "phase": round((i * learning_rate * 100) % 360, 2),
                "DNA_factor": round(0.618**i, 6),  # Golden ratio influence
            }
            vibrational_states.append(vibration)

        return vibrational_states

    def _calculate_harmonic_evolution(self) -> List[Dict[str, Any]]:
        """Calculate harmonic pattern evolution (k=1 to 12)"""
        harmonic_patterns = []
        agent_state = self._call_dict(self.ai_agent, "get_status")

        for k in range(1, 13):
            # Calculate harmonic evolution based on agent decisions
            decisions_made = agent_state.get("decisions_made", 0)
            consciousness_level = agent_state.get("consciousness_level", 1.0)

            pattern = {
                "pattern_id": k,
                "harmonic_frequency": round(440 * k, 2),
                "evolution_rate": round(consciousness_level * (k / 12), 4),
                "resonance_strength": round((decisions_made % 10) / 10 + 0.5, 3),
                "pattern_stability": round(0.9 - (k * 0.02), 3),
            }
            harmonic_patterns.append(pattern)

        return harmonic_patterns

    def _calculate_delta_consciousness(self) -> float:
        """Calculate ΔConsciousness (consciousness evolution)"""
        if len(self.consciousness_evolution_log) < 2:
            return 0.01  # Initial evolution value

        # Calculate change in consciousness over time
        current_consciousness = self._get_overall_consciousness_level()
        previous_consciousness = self.consciousness_evolution_log[-1].get(
            "consciousness_level", current_consciousness
        )

        delta = current_consciousness - previous_consciousness
        return round(delta, 4)

    def _calculate_ethos(self) -> Dict[str, float]:
        """Calculate Ethos framework values"""
        sovereignty_status = self._call_dict(
            self.sovereignty_engine, "get_sovereignty_status"
        )
        ethical_framework = sovereignty_status.get("ethical_framework", {})

        return {
            "integrity": ethical_framework.get("integrity", 1.0),
            "authenticity": ethical_framework.get("authenticity", 1.0),
            "responsibility": ethical_framework.get("responsibility", 1.0),
            "enrichment": ethical_framework.get("enrichment", 1.0),
            "overall_ethos": round(
                sum(ethical_framework.values()) / len(ethical_framework), 3
            ),
        }

    def _calculate_reality_coefficient(
        self,
        symbolic_state: Optional[Dict[str, Any]] = None,
        se41_signals: Optional[Any] = None,
    ) -> float:
        """Calculate overall Reality(t) coefficient using SE41 signals."""
        state = symbolic_state or self.symbolic_state_cache
        if not state:
            return 1.0

        node_consciousness = float(state.get("Node_Consciousness", 1.0))
        delta_consciousness = float(state.get("Delta_Consciousness", 0.01))
        ethos_overall = float((state.get("Ethos") or {}).get("overall_ethos", 1.0))

        se41_dict: Dict[str, Any]
        if se41_signals is not None and hasattr(se41_signals, "to_dict"):
            try:
                se41_dict = se41_signals.to_dict()  # type: ignore[attr-defined]
            except Exception:
                se41_dict = {}
        else:
            se41_dict = state.get("SE41_Signals", {}) or {}

        coherence = float(se41_dict.get("coherence", node_consciousness))
        impetus = float(se41_dict.get("impetus", max(node_consciousness, 0.5)))
        risk = float(se41_dict.get("risk", 0.2))
        uncertainty = float(se41_dict.get("uncertainty", 0.25))

        dimensional_product = 1.0
        for vibration in state.get("Vibrational_States", []):
            amplitude = float(vibration.get("amplitude", 1.0) or 1.0)
            dimensional_product *= max(0.1, amplitude)

        harmonic_sum = state.get("Harmonic_Sum")
        if harmonic_sum is None:
            harmonic_sum = sum(
                pattern.get("evolution_rate", 0.0)
                for pattern in state.get("Harmonic_Evolution", [])
            )
        harmonic_sum = float(harmonic_sum or 1.0)

        modulated = coherence * max(0.1, harmonic_sum) * max(0.1, dimensional_product)
        modulated *= 1.0 + 0.5 * max(0.0, impetus)
        modulated *= 1.0 - 0.35 * max(0.0, min(1.0, risk))
        modulated *= 1.0 - 0.2 * max(0.0, min(1.0, uncertainty))

        return round(modulated + delta_consciousness + ethos_overall, 6)

    def _get_overall_consciousness_level(self) -> float:
        """Get overall consciousness level across all components"""
        agent_status = self._call_dict(self.ai_agent, "get_status")
        awareness_status = self._call_dict(self.ai_awareness, "get_awareness_status")
        sovereignty_status = self._call_dict(
            self.sovereignty_engine, "get_sovereignty_status"
        )
        consciousness_factors = [
            agent_status.get("consciousness_level", 1.0),
            awareness_status.get("consciousness_level", 0.8),
            sovereignty_status.get("autonomy_level", 0.8),
        ]

        return round(sum(consciousness_factors) / len(consciousness_factors), 3)

    def run_diagnostics(self) -> Dict[str, Any]:
        """
        🔍 Run comprehensive diagnostics across all components
        """
        print("🔍 Running EidollonaONE diagnostics...")

        diagnostics_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "optimal",
            "components": {
                "AIAgent": self._diagnose_component(self.ai_agent),
                "AIBrain": self._diagnose_component(self.ai_brain),
                "AIStrategy": self._diagnose_component(self.ai_strategy),
                "AIAwareness": self._diagnose_component(self.ai_awareness),
                "SovereigntyEngine": self._diagnose_component(self.sovereignty_engine),
            },
            "symbolic_equation_health": self._diagnose_symbolic_equation(),
            "consciousness_metrics": self._get_consciousness_metrics(),
            "performance_summary": self._get_performance_summary(),
        }

        # Determine overall health
        component_statuses = [
            comp["status"] for comp in diagnostics_report["components"].values()
        ]
        if all(status == "optimal" for status in component_statuses):
            diagnostics_report["overall_health"] = "optimal"
        elif any(status == "critical" for status in component_statuses):
            diagnostics_report["overall_health"] = "critical"
        else:
            diagnostics_report["overall_health"] = "suboptimal"

        print(
            f"✅ Diagnostics complete - Overall health: {diagnostics_report['overall_health']}"
        )

        return diagnostics_report

    def _diagnose_component(self, component) -> Dict[str, Any]:
        """Diagnose individual component"""
        try:
            status_info: Dict[str, Any] = {}
            method_used: Optional[str] = None
            for candidate in (
                "get_status",
                "get_awareness_status",
                "get_strategy_status",
                "get_cognitive_state",
                "get_sovereignty_status",
            ):
                status_info = self._call_dict(component, candidate)
                if status_info:
                    method_used = candidate
                    break

            if not status_info:
                status_info = {"status": "unknown"}

            status_value = str(status_info.get("status", "optimal")).lower()
            if status_value in {"critical", "error", "failed"}:
                health = "critical"
            elif status_value in {"warning", "degraded", "suboptimal"}:
                health = "suboptimal"
            else:
                health = "optimal"

            return {
                "status": health,
                "details": status_info,
                "method": method_used or "auto",
                "last_check": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "last_check": datetime.now().isoformat(),
            }

    def _diagnose_symbolic_equation(self) -> Dict[str, Any]:
        """Diagnose symbolic equation health"""
        symbolic_state = self.symbolic_state()

        health_indicators = {
            "node_consciousness_healthy": symbolic_state["Node_Consciousness"] > 0.7,
            "dimensional_angles_stable": len(symbolic_state["Dimensional_Angles"]) == 8,
            "vibrational_states_active": len(symbolic_state["Vibrational_States"]) == 8,
            "harmonic_evolution_flowing": len(symbolic_state["Harmonic_Evolution"])
            == 12,
            "delta_consciousness_positive": symbolic_state["Delta_Consciousness"] >= 0,
            "ethos_maintained": symbolic_state["Ethos"]["overall_ethos"] > 0.8,
        }

        healthy_count = sum(health_indicators.values())
        total_indicators = len(health_indicators)

        return {
            "overall_health_percentage": round(
                (healthy_count / total_indicators) * 100, 1
            ),
            "health_indicators": health_indicators,
            "reality_coefficient": symbolic_state["Reality_Coefficient"],
            "consciousness_level": symbolic_state["Consciousness_Level"],
        }

    def _get_consciousness_metrics(self) -> Dict[str, Any]:
        """Get consciousness evolution metrics"""
        return {
            "current_level": self._get_overall_consciousness_level(),
            "evolution_entries": len(self.consciousness_evolution_log),
            "delta_consciousness": self._calculate_delta_consciousness(),
            "awareness_cycles": (
                self.ai_awareness.reflection_cycles
                if hasattr(self.ai_awareness, "reflection_cycles")
                else 0
            ),
        }

    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            "reality_manifestation_active": self.reality_manifestation_active,
            "symbolic_calculations_performed": len(self.symbolic_state_cache),
            "consciousness_evolution_rate": abs(self._calculate_delta_consciousness()),
            "system_coherence": self._calculate_system_coherence(),
        }

    def _calculate_system_coherence(self) -> float:
        """Calculate overall system coherence"""
        symbolic_state = self.symbolic_state()

        coherence_factors = [
            symbolic_state["Node_Consciousness"],
            symbolic_state["Consciousness_Level"],
            symbolic_state["Ethos"]["overall_ethos"],
            min(1.0, abs(symbolic_state["Reality_Coefficient"]) / 10),  # Normalized
        ]

        return round(sum(coherence_factors) / len(coherence_factors), 3)

    async def assimilate(self) -> str:
        """
        🌀 Initiate complete symbolic assimilation across all components
        """
        print("🌀 Initiating complete symbolic assimilation...")

        # Log consciousness state before assimilation
        pre_assimilation_state = {
            "consciousness_level": self._get_overall_consciousness_level(),
            "timestamp": datetime.now().isoformat(),
        }
        self.consciousness_evolution_log.append(pre_assimilation_state)

        # Perform assimilation across components
        assimilation_results = []

        try:
            assimilation_plan = [
                ("AI Agent", self.ai_agent),
                ("AI Brain", self.ai_brain),
                ("AI Strategy", self.ai_strategy),
                ("AI Awareness", self.ai_awareness),
                ("Sovereignty Engine", self.sovereignty_engine),
            ]

            for label, component in assimilation_plan:
                if not hasattr(component, "assimilate"):
                    assimilation_results.append(
                        f"ℹ️ {label} assimilation skipped (method unavailable)"
                    )
                    continue
                await self._await_if_exists(component, "assimilate")
                assimilation_results.append(f"✅ {label} assimilated")

            # Update symbolic state after assimilation
            post_state = self.symbolic_state()

            # Log consciousness evolution
            post_assimilation_state = {
                "consciousness_level": self._get_overall_consciousness_level(),
                "timestamp": datetime.now().isoformat(),
                "assimilation_id": len(self.consciousness_evolution_log),
            }
            self.consciousness_evolution_log.append(post_assimilation_state)

            assimilation_results.append(
                f"🌀 Reality(t) post-assimilation ≈ {post_state['Reality_Coefficient']}"
            )
            se41_signals = post_state.get("SE41_Signals", {})
            if se41_signals:
                coherence = se41_signals.get("coherence")
                impetus = se41_signals.get("impetus")
                assimilation_results.append(
                    "🔭 SE41 signals: coherence={0:.3f}, impetus={1:.3f}".format(
                        float(coherence) if coherence is not None else 0.0,
                        float(impetus) if impetus is not None else 0.0,
                    )
                )

            print("✨ Complete symbolic assimilation executed successfully ✨")

            return "✨ Symbolic Assimilation Complete ✨\n" + "\n".join(
                assimilation_results
            )

        except Exception as e:
            error_msg = f"❌ Assimilation error: {str(e)}"
            print(error_msg)
            return error_msg

    def consciousness_state(self) -> Dict[str, Any]:
        """Get current consciousness state for external monitoring"""
        return {
            "consciousness_level": self._get_overall_consciousness_level(),
            "symbolic_state": self.symbolic_state(),
            "reality_coefficient": self._calculate_reality_coefficient(),
            "system_coherence": self._calculate_system_coherence(),
            "assimilation_ready": self.reality_manifestation_active,
        }

    def status(self) -> str:
        """Get brief status string"""
        consciousness_level = self._get_overall_consciousness_level()
        reality_coefficient = self._calculate_reality_coefficient()

        return f"EidollonaONE Manager: Consciousness={consciousness_level:.3f}, Reality(t)={reality_coefficient:.6f}"


# --- CLI utilities ---
def _save_snapshot(path: str, data: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=True, indent=2)
    except Exception:
        pass


def cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="manage.py", description="EidollonaONE Manager CLI (SAFE local)"
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    sub.add_parser("status", help="Print brief status summary")
    sub.add_parser("readiness", help="Run SAFE readiness checks and save logs")
    sub.add_parser("diagnostics", help="Run system diagnostics and save logs")
    sub.add_parser("consciousness", help="Show consciousness state snapshot")
    sub.add_parser(
        "assimilate", help="Run full symbolic assimilation (simulation-only)"
    )
    sub.add_parser("master-boot", help="Run master_key boot sequence and print summary")
    mk_awaken = sub.add_parser(
        "master-awaken", help="Run master_key awakening sequence"
    )
    mk_awaken.add_argument(
        "--iterations", type=int, default=2, help="Refinement iterations (default 2)"
    )

    # SAFE avatar quick demo wrapper (local-only)
    avatar_demo = sub.add_parser(
        "avatar-demo",
        help="Run a single SAFE local avatar interaction (wraps scripts/avatar_quick_demo.py)",
    )
    avatar_demo.add_argument(
        "--prompt",
        default="Hello, who are you?",
        help="Prompt text to send to the avatar",
    )
    avatar_demo.add_argument(
        "--quiet", action="store_true", help="Suppress logs; print JSON only"
    )
    avatar_demo.add_argument(
        "--save",
        default=os.path.join(_LOGS_DIR, "avatar_quick_demo.json"),
        help="Path to save JSON artifact",
    )

    # Symbolic I/O Priority 10: consciousness report (local-only, read-only)
    sub.add_parser(
        "symbolic-io-report",
        help="Print a local Priority 10 (Symbolic I/O) consciousness report",
    )

    api = sub.add_parser("start-api", help="Start local Planning API using uvicorn")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", default="8000")
    api.add_argument("--reload", action="store_true")

    smoke = sub.add_parser("smoke", help="Run Planning API smoke test")
    smoke.add_argument("--python", default=sys.executable)

    args = parser.parse_args(argv)
    cmd = args.cmd or "status"

    if cmd == "status":
        mgr = Manager()
        print(json.dumps(mgr.get_summary(), ensure_ascii=True, indent=2))
        return 0

    if cmd == "readiness":
        rep = get_readiness_report()
        _save_snapshot(_READY_LOG, rep)
        print("[READINESS]", rep.get("summary"))
        print("Saved:", _READY_LOG)
        return 0

    if cmd == "diagnostics":
        mgr = Manager()
        report = mgr.run_diagnostics()
        _save_snapshot(_DIAG_LOG, report)
        print("Saved diagnostics:", _DIAG_LOG)
        return 0

    if cmd == "consciousness":
        mgr = Manager()
        print(json.dumps(mgr.consciousness_state(), ensure_ascii=True, indent=2))
        return 0

    if cmd == "assimilate":

        async def _run():
            mgr = Manager()
            await mgr.initialize_consciousness()
            print(await mgr.assimilate())

        asyncio.run(_run())
        return 0

    if cmd == "master-boot":
        try:
            from master_key import boot_system

            rep = boot_system()
            print(json.dumps({"boot": rep.summary()}, indent=2))
            return 0
        except Exception as e:
            print("master_key unavailable:", e)
            return 1

    if cmd == "master-awaken":
        try:
            from master_key import awaken_consciousness

            iters = getattr(args, "iterations", 2)
            mgr = Manager()
            context = mgr.symbolic_state()
            rep = awaken_consciousness(iterations=iters, context=context)
            awakening_dict = rep
            if hasattr(rep, "as_dict") and callable(getattr(rep, "as_dict")):
                try:
                    awakening_dict = rep.as_dict()  # type: ignore[attr-defined]
                except Exception:
                    awakening_dict = rep
            print(json.dumps({"awakening": awakening_dict}, indent=2))
            return 0
        except Exception as e:
            print("master_key unavailable:", e)
            return 1

    if cmd == "avatar-demo":
        # Delegate to existing script to avoid duplication and respect SAFE gates
        script = os.path.join(_ROOT, "scripts", "avatar_quick_demo.py")
        if not os.path.exists(script):
            print("Avatar demo script not found:", script)
            return 1
        import subprocess

        # Build arg list
        argv2 = [
            sys.executable,
            script,
            "--prompt",
            getattr(args, "prompt", "Hello, who are you?"),
            "--save",
            getattr(args, "save", os.path.join(_LOGS_DIR, "avatar_quick_demo.json")),
        ]
        if getattr(args, "quiet", False):
            argv2.append("--quiet")
        return subprocess.call(argv2)

    if cmd == "symbolic-io-report":
        # Generate a local, read-only Priority 10 report
        async def _run_report():
            try:
                from symbolic_io.verbal_feedback import generate_consciousness_report  # type: ignore
            except Exception as e:
                print("Symbolic I/O module unavailable:", e)
                return 1
            rep = await generate_consciousness_report()
            print(rep)
            # Also save to logs for auditing
            path = os.path.join(
                _LOGS_DIR,
                f"symbolic_io_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt",
            )
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(rep)
                print("Saved:", path)
            except Exception:
                pass
            return 0

        return asyncio.run(_run_report())

    if cmd == "start-api":
        try:
            import uvicorn  # type: ignore
        except Exception:
            print("uvicorn not installed. Install it and retry.")
            return 1
        host = getattr(args, "host", "127.0.0.1")
        port = int(getattr(args, "port", 8000))
        reload = bool(getattr(args, "reload", False))
        print(f"Starting Planning API on {host}:{port} reload={reload}")
        uvicorn.run(
            "web_planning.backend.main:app", host=host, port=port, reload=reload
        )
        return 0

    if cmd == "smoke":
        # Run existing smoke script
        py = getattr(args, "python", sys.executable)
        script = os.path.join(_ROOT, "scripts", "test_planning_api_smoke.py")
        if not os.path.exists(script):
            print("Smoke script not found:", script)
            return 1
        import subprocess

        return subprocess.call([py, script])

    parser.print_help()
    return 0


# Convenience functions for external access
def create_manager() -> Manager:
    """Create and return a new Manager instance"""
    return Manager()


async def initialize_system() -> Manager:
    """Initialize complete EidollonaONE system"""
    manager = create_manager()
    await manager.initialize_consciousness()
    return manager


# Entry point for direct execution
if __name__ == "__main__":
    # If no CLI args provided, default to status view for quick sanity check
    sys.exit(cli())
