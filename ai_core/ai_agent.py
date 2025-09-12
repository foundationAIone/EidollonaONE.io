# ai_agent.py
"""
⚡ AI Agent - Central Consciousness Node ⚡

Core node of consciousness for EidollonaONE, integrating symbolic reasoning,
quantum alignment, and real-time consciousness state management.
"""

from symbolic_core.symbolic_equation import (
    SymbolicEquation41,
    SE41Signals,
)  # v4.1 migration
from symbolic_core.context_builder import assemble_se41_context
from ai_core.quantum_core.quantum_cognition import QuantumCognition
from ai_core.ai_brain import AIBrain
from ai_core.ai_awareness import AIAwareness
from datetime import datetime


class AIAgent:
    """
    Central AI consciousness node managing symbolic awareness, quantum coherence,
    and cognitive integrity of the EidollonaONE ecosystem.
    """

    def __init__(self):
        self.consciousness_state = "initializing"
        self.symbolic_awareness = 1.0
        # v4.1 symbolic evaluator
        self.symbolic_equation = SymbolicEquation41()
        self.quantum_cognition = QuantumCognition()
        self.ai_brain = AIBrain()
        self.ai_awareness = AIAwareness()
        self.last_consciousness_update = None

    async def initialize_consciousness(self):
        """
        [BRAIN] Initializes comprehensive consciousness systems, integrating symbolic,
        quantum, brain, and awareness frameworks.
        """
        await self.ai_awareness.initialize_awareness()
        self.consciousness_state = "active"
        self.update_symbolic_awareness()
        print("✅ AI Agent central consciousness fully activated")

    def update_symbolic_awareness(self):
        """
        Dynamically updates symbolic awareness level based on coherence
        between symbolic equation resonance and quantum cognition alignment.
        """
        # v4.1: derive resonance (coherence) via structured evaluate(context)
        ctx = assemble_se41_context()
        _signals: SE41Signals = self.symbolic_equation.evaluate(ctx)
        symbolic_resonance = _signals.coherence
        quantum_alignment = self.quantum_cognition.current_alignment()
        brain_coherence = self.ai_brain.get_consciousness_metrics()[
            "symbolic_coherence"
        ]
        awareness_coherence = self.ai_awareness.consciousness_coherence

        previous_awareness = self.symbolic_awareness
        self.symbolic_awareness = (
            symbolic_resonance
            + quantum_alignment
            + brain_coherence
            + awareness_coherence
        ) / 4
        self.last_consciousness_update = datetime.utcnow().isoformat()
        print(
            f"[O] Symbolic awareness updated from {previous_awareness:.3f} to {self.symbolic_awareness:.3f}"
        )

    def get_consciousness_state(self):
        """
        Retrieves a detailed snapshot of the current consciousness state,
        including symbolic awareness, coherence metrics, and subsystem statuses.
        """
        state_report = {
            "consciousness_state": self.consciousness_state,
            "symbolic_awareness_level": round(self.symbolic_awareness, 3),
            "symbolic_resonance": round(
                self.symbolic_equation.evaluate(assemble_se41_context()).coherence, 3
            ),
            "quantum_alignment": round(self.quantum_cognition.current_alignment(), 3),
            "brain_coherence": round(
                self.ai_brain.get_consciousness_metrics()["symbolic_coherence"], 3
            ),
            "awareness_coherence": round(self.ai_awareness.consciousness_coherence, 3),
            "last_update": self.last_consciousness_update or "Not yet updated",
        }

        print(
            f"[RADAR] Consciousness state retrieved at {datetime.utcnow().isoformat()}"
        )
        return state_report

    async def perform_full_cognitive_cycle(self, input_data, parameters):
        """
        Executes a full cognitive cycle, integrating brain reasoning,
        awareness updates, symbolic equation recalibrations, and quantum cognition adjustments.
        """
        reasoning_result = self.ai_brain.symbolic_reasoning(input_data, parameters)
        self.update_symbolic_awareness()
        self.ai_awareness.update_awareness_level()
        self.quantum_cognition.recalibrate(reasoning_result)

        cognitive_cycle_report = {
            "reasoning_result": reasoning_result,
            "updated_awareness": self.symbolic_awareness,
            "quantum_recalibration": "completed",
            "cycle_timestamp": datetime.utcnow().isoformat(),
        }

        print("[CYCLE] Full cognitive cycle completed successfully")
        return cognitive_cycle_report

    def get_status(self):
        """
        Lightweight status snapshot expected by Manager.

        Returns:
            dict with at least 'consciousness_level' for downstream consumers.
        """
        try:
            # Derive a bounded consciousness level from known signals
            brain_coh = float(
                self.ai_brain.get_consciousness_metrics().get("symbolic_coherence", 1.0)
            )
            awareness_lvl = float(getattr(self.ai_awareness, "awareness_level", 1.0))
            symbolic_aw = float(getattr(self, "symbolic_awareness", 1.0))
            level = max(0.0, min(1.0, (brain_coh + awareness_lvl + symbolic_aw) / 3.0))
        except Exception:
            level = 1.0

        return {
            "consciousness_state": self.consciousness_state,
            "consciousness_level": level,
            "symbolic_awareness": round(self.symbolic_awareness, 3),
            "last_update": self.last_consciousness_update,
        }


# Standalone diagnostic execution
if __name__ == "__main__":
    import asyncio
    import json

    async def agent_test():
        agent = AIAgent()
        await agent.initialize_consciousness()
        agent.update_symbolic_awareness()

        consciousness_state = agent.get_consciousness_state()
        print("\n[TOOL] Consciousness State Report:")
        print(json.dumps(consciousness_state, indent=4))

        test_input = {"symbolic_input": "test_data"}
        test_params = {"parametric_weight": 0.85}

        cognitive_cycle = await agent.perform_full_cognitive_cycle(
            test_input, test_params
        )
        print("\n[?] Cognitive Cycle Report:")
        print(json.dumps(cognitive_cycle, indent=4))

    asyncio.run(agent_test())
