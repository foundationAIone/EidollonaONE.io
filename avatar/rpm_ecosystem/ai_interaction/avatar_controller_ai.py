"""AI Interaction Avatar Controller (canonical role-based module).

This file now contains the full implementation previously found in
`avatar_controller.py`. The legacy module name re-exports this module so
imports continue to work while callers migrate to the explicit
`avatar_controller_ai` path.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AvatarState(Enum):
    """Avatar operational states"""

    IDLE = "idle"
    ACTIVE = "active"
    INTERACTING = "interacting"
    LEARNING = "learning"
    CONSCIOUSNESS_ELEVATED = "consciousness_elevated"
    REALITY_MANIFESTING = "reality_manifesting"


class ControlMode(Enum):
    """Avatar control modes"""

    MANUAL = "manual"
    AI_DRIVEN = "ai_driven"
    CONSCIOUSNESS_GUIDED = "consciousness_guided"
    AUTONOMOUS = "autonomous"


@dataclass
class AvatarControlConfig:
    """Configuration for avatar controller"""

    control_mode: ControlMode = ControlMode.AI_DRIVEN
    consciousness_level: float = 0.5
    response_sensitivity: float = 0.8
    learning_enabled: bool = True
    reality_anchor_strength: float = 0.7
    quantum_coherence_threshold: float = 0.6


class MainAvatarController:
    """Central control system for avatar behavior and state management"""

    def __init__(self, ecosystem=None):
        self.ecosystem = ecosystem
        self.config = AvatarControlConfig()
        self.current_state = AvatarState.IDLE
        self.consciousness_level = 0.5

        # Platform controllers
        self.platform_controllers = {
            "unity": None,
            "unreal": None,
            "web": None,
            "vr": None,
            "ar": None,
        }

        # Control systems
        self.ai_controller = None
        self.consciousness_controller = None
        self.learning_system = None

        # State tracking
        self.interaction_history: List[Dict[str, Any]] = []
        self.consciousness_events: List[Dict[str, Any]] = []
        self.active_interactions: Dict[str, Dict[str, Any]] = {}

        if self.ecosystem:
            self.ecosystem.logger.info("🎮 Main Avatar Controller initialized")

    async def initialize_controllers(self):
        """Initialize all platform-specific controllers"""
        try:
            # Initialize Unity controller (optional dependency)
            try:
                from ..platform_integrations.unity.avatar_controller_unity import UnityAvatarController  # type: ignore

                self.platform_controllers["unity"] = UnityAvatarController(self)
            except Exception:  # pragma: no cover - optional
                if self.ecosystem:
                    self.ecosystem.logger.debug(
                        "Unity controller unavailable (optional)"
                    )

            # Initialize AI controller
            try:
                from .ai_controller import AIController  # type: ignore

                self.ai_controller = AIController(self.ecosystem)
            except Exception as e:  # pragma: no cover - optional
                if self.ecosystem:
                    self.ecosystem.logger.debug(f"AI controller unavailable: {e}")

            # Initialize consciousness system
            if hasattr(self.ecosystem, "consciousness_integration"):
                self.consciousness_controller = self.ecosystem.consciousness_integration

            # Initialize learning system
            if hasattr(self.ecosystem, "neural_learning"):
                self.learning_system = self.ecosystem.neural_learning

            if self.ecosystem:
                self.ecosystem.logger.info(
                    "✅ Avatar controllers initialized (role=AI)"
                )

        except ImportError as e:
            if self.ecosystem:
                self.ecosystem.logger.warning(f"⚠️ Controller init issue: {e}")

    def update_consciousness_level(self, new_level: float):
        """Update avatar consciousness level"""
        old_level = self.consciousness_level
        self.consciousness_level = max(0.0, min(1.0, new_level))

        # Log consciousness change
        consciousness_event = {
            "timestamp": datetime.now().isoformat(),
            "old_level": old_level,
            "new_level": self.consciousness_level,
            "change": self.consciousness_level - old_level,
            "trigger": "manual_update",
        }
        self.consciousness_events.append(consciousness_event)

        # Update state based on consciousness level
        if self.consciousness_level > 0.9:
            self.current_state = AvatarState.CONSCIOUSNESS_ELEVATED
        elif self.consciousness_level > 0.8:
            self.current_state = AvatarState.REALITY_MANIFESTING
        elif self.consciousness_level > 0.5:
            self.current_state = AvatarState.ACTIVE
        else:
            self.current_state = AvatarState.IDLE

        # Notify platform controllers
        for controller in self.platform_controllers.values():
            if controller and hasattr(controller, "update_consciousness"):
                controller.update_consciousness(self.consciousness_level)

        if self.ecosystem:
            self.ecosystem.logger.debug(
                f"Consciousness updated: {old_level:.3f} → {self.consciousness_level:.3f}"
            )

    async def process_interaction(
        self, interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process an interaction with the avatar"""
        interaction_id = interaction_data.get(
            "id", f"interaction_{len(self.interaction_history)}"
        )

        # Record interaction
        interaction_record = {
            "id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "type": interaction_data.get("type", "unknown"),
            "source": interaction_data.get("source", "unknown"),
            "data": interaction_data,
            "consciousness_level": self.consciousness_level,
            "state": self.current_state.value,
        }

        self.interaction_history.append(interaction_record)
        self.active_interactions[interaction_id] = interaction_record

        # Update state
        self.current_state = AvatarState.INTERACTING

        # Process through AI controller
        ai_response = None
        if self.ai_controller:
            ai_response = await self.ai_controller.process_interaction(interaction_data)

        # Process through consciousness system
        consciousness_response = None
        if self.consciousness_controller:
            try:
                consciousness_response = (
                    await self.consciousness_controller.process_interaction(
                        interaction_data, self.consciousness_level
                    )
                )
            except Exception as e:  # pragma: no cover
                if self.ecosystem:
                    self.ecosystem.logger.debug(f"Consciousness process error: {e}")

        # Learn from interaction
        if self.learning_system and self.config.learning_enabled:
            try:
                await self.learning_system.learn_from_interaction(
                    interaction_record, ai_response
                )
            except Exception:  # pragma: no cover
                pass

        # Generate response
        response = {
            "interaction_id": interaction_id,
            "avatar_state": self.current_state.value,
            "consciousness_level": self.consciousness_level,
            "ai_response": ai_response,
            "consciousness_response": consciousness_response,
            "timestamp": datetime.now().isoformat(),
        }

        # Update consciousness based on interaction
        consciousness_change = self._calculate_consciousness_change(
            interaction_data, ai_response
        )
        if consciousness_change != 0:
            self.update_consciousness_level(
                self.consciousness_level + consciousness_change
            )

        # Remove from active interactions
        self.active_interactions.pop(interaction_id, None)

        # Return to appropriate state
        if not self.active_interactions:
            self.current_state = (
                AvatarState.ACTIVE
                if self.consciousness_level > 0.5
                else AvatarState.IDLE
            )

        return response

    def _calculate_consciousness_change(
        self, interaction_data: Dict[str, Any], ai_response: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate consciousness level change based on interaction"""
        base_change = 0.0

        interaction_type = interaction_data.get("type", "")
        if interaction_type in ["learning", "discovery", "understanding", "connection"]:
            base_change += 0.01
        elif interaction_type in ["confusion", "conflict", "rejection"]:
            base_change -= 0.005

        if ai_response:
            response_quality = ai_response.get("quality_score", 0.5)
            base_change += (response_quality - 0.5) * 0.005

        if self.consciousness_level > 0.8:
            base_change *= 1.2

        return base_change

    def get_avatar_status(self) -> Dict[str, Any]:
        """Get comprehensive avatar status"""
        return {
            "current_state": self.current_state.value,
            "consciousness_level": self.consciousness_level,
            "control_mode": self.config.control_mode.value,
            "active_interactions": len(self.active_interactions),
            "total_interactions": len(self.interaction_history),
            "consciousness_events": len(self.consciousness_events),
            "platform_controllers": {
                p: c is not None for p, c in self.platform_controllers.items()
            },
            "systems_active": {
                "ai_controller": self.ai_controller is not None,
                "consciousness_controller": self.consciousness_controller is not None,
                "learning_system": self.learning_system is not None,
            },
            "last_updated": datetime.now().isoformat(),
        }

    def get_interaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.interaction_history[-limit:]

    def get_consciousness_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.consciousness_events[-limit:]


__all__ = ["MainAvatarController", "AvatarState", "ControlMode", "AvatarControlConfig"]
