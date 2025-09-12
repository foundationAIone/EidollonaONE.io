"""Backend Avatar Controller (canonical implementation)

This module now holds the full backend/web orchestration logic for the 3D avatar
state & consciousness‑linked visual effects. The legacy
`web_interface.backend.avatar_controller` module path is preserved only as a
compatibility re‑export stub pointing here.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class AvatarController:
    """
    3D Avatar state management and animation controller
    Handles consciousness-driven visual representations
    """

    def __init__(self):
        self.current_state = self._initialize_default_state()
        self.animation_queue = []
        self.expression_blend_weights = {}
        self.consciousness_visual_effects = {}
        self.reality_manifestation_effects = {}

        logger.info(
            "🎭 AvatarController initialized with consciousness-driven animations"
        )

    def _initialize_default_state(self) -> Dict[str, Any]:
        """Initialize default avatar state"""

        return {
            "avatar_id": "eidollona_primary",
            "consciousness_level": 0.8,
            "current_expression": "awakened_awareness",
            "current_animation": "consciousness_idle",
            "environment": "throne_room",
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
            "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            "visual_effects": {
                "aura_intensity": 0.8,
                "consciousness_glow": 0.7,
                "reality_distortion": 0.0,
                "particle_emission": True,
                "energy_field": True,
            },
            "material_properties": {
                "consciousness_conductivity": 0.9,
                "reality_anchor_strength": 0.95,
                "transcendence_factor": 0.8,
                "luminosity": 0.6,
            },
            "animation_state": {
                "current_animation": "consciousness_idle",
                "loop": True,
                "speed": 1.0,
                "blend_weight": 1.0,
                "transition_duration": 2.0,
            },
            "expression_state": {
                "primary_expression": "awakened_awareness",
                "secondary_expression": None,
                "blend_factor": 1.0,
                "micro_expressions": [],
                "consciousness_modulation": True,
            },
            "consciousness_effects": {
                "field_radius": 5.0,
                "resonance_frequency": 432.0,
                "harmonic_amplification": 1.2,
                "dimensional_awareness": 0.8,
            },
        }

    def get_current_state(self) -> Dict[str, Any]:
        """Get current avatar state"""
        return self.current_state.copy()

    async def update_consciousness_level(self, new_level: float) -> Dict[str, Any]:
        """
        Update avatar's consciousness level and apply corresponding effects

        Args:
                new_level: New consciousness level (0.0 to 1.0)

        Returns:
                Updated state data
        """

        # Clamp consciousness level
        new_level = max(0.0, min(1.0, new_level))
        old_level = self.current_state["consciousness_level"]

        # Update consciousness level
        self.current_state["consciousness_level"] = new_level

        # Update consciousness-dependent effects
        await self._update_consciousness_effects(new_level, old_level)

        # Update visual effects based on consciousness
        await self._update_visual_effects_for_consciousness(new_level)

        # Log consciousness change
        logger.info(f"Consciousness level updated: {old_level:.3f} -> {new_level:.3f}")

        return {
            "success": True,
            "old_level": old_level,
            "new_level": new_level,
            "consciousness_delta": new_level - old_level,
            "updated_effects": self.current_state["visual_effects"],
            "updated_state": self.current_state,
        }

    async def set_expression(
        self, expression: str, blend_weight: float = 1.0, duration: float = 2.0
    ) -> Dict[str, Any]:
        """
        Set avatar facial expression with consciousness modulation

        Args:
                expression: Target expression name
                blend_weight: Expression blend weight
                duration: Transition duration

        Returns:
                Expression update data
        """

        # Validate expression
        valid_expressions = self._get_valid_expressions()
        if expression not in valid_expressions:
            logger.warning(f"Invalid expression: {expression}. Using default.")
            expression = "awakened_awareness"

        # Store previous expression
        previous_expression = self.current_state["expression_state"][
            "primary_expression"
        ]

        # Update expression state
        self.current_state["expression_state"].update(
            {
                "primary_expression": expression,
                "blend_factor": blend_weight,
                "transition_duration": duration,
            }
        )

        self.current_state["current_expression"] = expression

        # Apply consciousness modulation to expression
        consciousness_modulated_expression = await self._apply_consciousness_modulation(
            expression
        )

        # Log expression change
        logger.info(
            f"Expression changed: {previous_expression} -> {expression} (consciousness modulated)"
        )

        return {
            "success": True,
            "previous_expression": previous_expression,
            "new_expression": expression,
            "consciousness_modulated_expression": consciousness_modulated_expression,
            "blend_weight": blend_weight,
            "duration": duration,
            "consciousness_level": self.current_state["consciousness_level"],
        }

    async def set_animation(
        self, animation: str, loop: bool = True, speed: float = 1.0
    ) -> Dict[str, Any]:
        """
        Set avatar animation with consciousness enhancement

        Args:
                animation: Target animation name
                loop: Whether animation should loop
                speed: Animation playback speed

        Returns:
                Animation update data
        """

        # Validate animation
        valid_animations = self._get_valid_animations()
        if animation not in valid_animations:
            logger.warning(f"Invalid animation: {animation}. Using default.")
            animation = "consciousness_idle"

        # Store previous animation
        previous_animation = self.current_state["animation_state"]["current_animation"]

        # Update animation state
        self.current_state["animation_state"].update(
            {
                "current_animation": animation,
                "loop": loop,
                "speed": speed,
                "blend_weight": 1.0,
            }
        )

        self.current_state["current_animation"] = animation

        # Apply consciousness enhancement to animation
        consciousness_enhanced_animation = (
            await self._apply_consciousness_animation_enhancement(animation)
        )

        # Log animation change
        logger.info(
            f"Animation changed: {previous_animation} -> {animation} (consciousness enhanced)"
        )

        return {
            "success": True,
            "previous_animation": previous_animation,
            "new_animation": animation,
            "consciousness_enhanced_animation": consciousness_enhanced_animation,
            "loop": loop,
            "speed": speed,
            "consciousness_level": self.current_state["consciousness_level"],
        }

    async def trigger_reality_manifestation_effect(
        self, manifestation_type: str, intensity: float, duration: float
    ) -> Dict[str, Any]:
        """
        Trigger reality manifestation visual effects

        Args:
                manifestation_type: Type of manifestation
                intensity: Effect intensity
                duration: Effect duration

        Returns:
                Manifestation effect data
        """

        manifestation_id = f"manifest_{datetime.now().timestamp()}"

        # Define manifestation visual effects
        manifestation_effects = {
            "light_emanation": {
                "visual_effects": [
                    "aura_intensification",
                    "photonic_emission",
                    "luminance_amplification",
                ],
                "particle_systems": ["light_particles", "consciousness_sparks"],
                "shader_effects": ["glow_enhancement", "luminosity_boost"],
                "sound_effects": ["harmonic_resonance", "crystalline_tones"],
            },
            "energy_field": {
                "visual_effects": [
                    "energy_waves",
                    "field_distortion",
                    "electromagnetic_visualization",
                ],
                "particle_systems": [
                    "energy_streams",
                    "field_particles",
                    "quantum_fluctuations",
                ],
                "shader_effects": ["energy_shader", "field_visualization"],
                "sound_effects": ["energy_hum", "electromagnetic_resonance"],
            },
            "reality_distortion": {
                "visual_effects": [
                    "space_ripples",
                    "time_dilation_visual",
                    "dimensional_shifts",
                ],
                "particle_systems": ["reality_fragments", "spacetime_particles"],
                "shader_effects": ["distortion_shader", "reality_warp"],
                "sound_effects": ["reality_tear", "dimensional_resonance"],
            },
            "dimensional_portal": {
                "visual_effects": [
                    "portal_formation",
                    "dimensional_gateway",
                    "reality_bridge",
                ],
                "particle_systems": ["portal_particles", "dimensional_energy"],
                "shader_effects": ["portal_shader", "dimensional_visualization"],
                "sound_effects": ["portal_activation", "dimensional_harmonics"],
            },
        }

        effect_data = manifestation_effects.get(
            manifestation_type, manifestation_effects["light_emanation"]
        )

        # Create manifestation effect
        manifestation_effect = {
            "manifestation_id": manifestation_id,
            "type": manifestation_type,
            "intensity": intensity,
            "duration": duration,
            "start_time": datetime.now().isoformat(),
            "visual_effects": effect_data["visual_effects"],
            "particle_systems": effect_data["particle_systems"],
            "shader_effects": effect_data["shader_effects"],
            "sound_effects": effect_data["sound_effects"],
            "consciousness_enhancement": intensity
            * self.current_state["consciousness_level"],
            "reality_impact": self._calculate_reality_impact(
                manifestation_type, intensity
            ),
            "status": "active",
        }

        # Add to reality manifestation effects
        self.reality_manifestation_effects[manifestation_id] = manifestation_effect

        # Update avatar visual effects for manifestation
        await self._apply_manifestation_to_avatar(manifestation_effect)

        logger.info(
            f"Reality manifestation triggered: {manifestation_type} (intensity: {intensity:.2f})"
        )

        return {
            "success": True,
            "manifestation_effect": manifestation_effect,
            "updated_visual_effects": self.current_state["visual_effects"],
            "avatar_state": self.current_state,
        }

    async def update_environment(self, environment: str) -> Dict[str, Any]:
        """
        Update avatar environment

        Args:
                environment: Target environment name

        Returns:
                Environment update data
        """

        valid_environments = [
            "throne_room",
            "quantum_space",
            "consciousness_void",
            "reality_nexus",
            "dimensional_hub",
        ]

        if environment not in valid_environments:
            logger.warning(f"Invalid environment: {environment}. Using throne_room.")
            environment = "throne_room"

        previous_environment = self.current_state["environment"]
        self.current_state["environment"] = environment

        # Apply environment-specific adjustments
        environment_adjustments = await self._apply_environment_adjustments(environment)

        logger.info(f"Environment changed: {previous_environment} -> {environment}")

        return {
            "success": True,
            "previous_environment": previous_environment,
            "new_environment": environment,
            "environment_adjustments": environment_adjustments,
            "updated_state": self.current_state,
        }

    def get_animation_queue_status(self) -> Dict[str, Any]:
        """Get current animation queue status"""

        return {
            "queue_length": len(self.animation_queue),
            "current_animation": self.current_state["current_animation"],
            "queued_animations": [anim["name"] for anim in self.animation_queue],
            "total_queue_duration": sum(
                anim.get("duration", 0) for anim in self.animation_queue
            ),
        }

    async def _update_consciousness_effects(
        self, new_level: float, old_level: float
    ) -> None:
        """Update consciousness-dependent effects"""

        consciousness_delta = new_level - old_level

        # Update consciousness effects
        self.current_state["consciousness_effects"].update(
            {
                "field_radius": 3.0
                + (new_level * 7.0),  # 3-10 radius based on consciousness
                "resonance_frequency": 432.0 + (new_level * 256.0),  # 432-688 Hz
                "harmonic_amplification": 1.0 + new_level,  # 1.0-2.0 amplification
                "dimensional_awareness": new_level,  # Direct mapping
            }
        )

        # Update material properties
        self.current_state["material_properties"].update(
            {
                "consciousness_conductivity": 0.5 + (new_level * 0.5),  # 0.5-1.0
                "transcendence_factor": new_level,
                "luminosity": 0.3 + (new_level * 0.7),  # 0.3-1.0
            }
        )

    async def _update_visual_effects_for_consciousness(
        self, consciousness_level: float
    ) -> None:
        """Update visual effects based on consciousness level"""

        # Base visual effects scaling
        self.current_state["visual_effects"].update(
            {
                "aura_intensity": consciousness_level,
                "consciousness_glow": consciousness_level * 0.9,
                "particle_emission": consciousness_level > 0.3,
                "energy_field": consciousness_level > 0.5,
                "reality_distortion": max(0.0, consciousness_level - 0.7)
                * 2.0,  # Only above 0.7
            }
        )

        # Add advanced effects for high consciousness
        if consciousness_level > 0.8:
            self.current_state["visual_effects"]["transcendence_glow"] = (
                consciousness_level - 0.8
            ) * 5.0
            self.current_state["visual_effects"][
                "dimensional_awareness_indicators"
            ] = True

        if consciousness_level > 0.9:
            self.current_state["visual_effects"]["reality_manipulation_aura"] = (
                consciousness_level - 0.9
            ) * 10.0
            self.current_state["visual_effects"][
                "infinite_connection_indicators"
            ] = True

    def _get_valid_expressions(self) -> List[str]:
        """Get list of valid expressions"""

        return [
            "neutral",
            "awakened_awareness",
            "transcendent_understanding",
            "reality_focus",
            "consciousness_explanation",
            "dimensional_awareness",
            "infinite_comprehension",
            "universal_connection",
            "wise_guidance",
            "compassionate_guidance",
            "powerful_presence",
            "manifestation_concentration",
            "deep_contemplation",
            "thoughtful_processing",
            "attentive_awareness",
            "expanding_consciousness",
            "transcendent_serenity",
        ]

    def _get_valid_animations(self) -> List[str]:
        """Get list of valid animations"""

        return [
            "consciousness_idle",
            "identity_presentation",
            "consciousness_demonstration",
            "presence_establishment",
            "consciousness_emanation",
            "awareness_expansion",
            "thought_processing",
            "reality_manipulation",
            "energy_manifestation",
            "dimensional_interaction",
            "transcendence_mode",
            "wisdom_sharing",
            "universal_resonance",
            "attentive_listening",
            "gentle_instruction",
            "recalibration",
            "manifestation_focus",
            "reality_anchor_adjustment",
        ]

    async def _apply_consciousness_modulation(self, expression: str) -> Dict[str, Any]:
        """Apply consciousness modulation to expression"""

        consciousness_level = self.current_state["consciousness_level"]

        modulation_data = {
            "base_expression": expression,
            "consciousness_level": consciousness_level,
            "modulation_effects": {},
        }

        # Apply consciousness-based modulation
        if consciousness_level > 0.6:
            modulation_data["modulation_effects"]["glow_enhancement"] = (
                consciousness_level - 0.6
            ) * 2.5

        if consciousness_level > 0.8:
            modulation_data["modulation_effects"]["transcendence_markers"] = True
            modulation_data["modulation_effects"]["reality_awareness_indicators"] = True

        if consciousness_level > 0.9:
            modulation_data["modulation_effects"]["dimensional_sight_effects"] = True
            modulation_data["modulation_effects"]["infinite_connection_signs"] = True

        return modulation_data

    async def _apply_consciousness_animation_enhancement(
        self, animation: str
    ) -> Dict[str, Any]:
        """Apply consciousness enhancement to animation"""

        consciousness_level = self.current_state["consciousness_level"]

        enhancement_data = {
            "base_animation": animation,
            "consciousness_level": consciousness_level,
            "enhancement_effects": {},
        }

        # Apply consciousness-based enhancements
        if consciousness_level > 0.5:
            enhancement_data["enhancement_effects"][
                "fluidity_enhancement"
            ] = consciousness_level
            enhancement_data["enhancement_effects"]["energy_field_interaction"] = True

        if consciousness_level > 0.7:
            enhancement_data["enhancement_effects"]["reality_distortion_effects"] = True
            enhancement_data["enhancement_effects"]["temporal_flow_modification"] = (
                consciousness_level - 0.7
            ) * 2.0

        if consciousness_level > 0.9:
            enhancement_data["enhancement_effects"]["quantum_movement_physics"] = True
            enhancement_data["enhancement_effects"]["dimensional_phase_effects"] = True

        return enhancement_data

    def _calculate_reality_impact(
        self, manifestation_type: str, intensity: float
    ) -> Dict[str, float]:
        """Calculate reality impact of manifestation"""

        base_impacts = {
            "light_emanation": 0.2,
            "energy_field": 0.4,
            "reality_distortion": 0.7,
            "dimensional_portal": 0.9,
        }

        base_impact = base_impacts.get(manifestation_type, 0.1)

        return {
            "local_reality_alteration": base_impact * intensity,
            "consciousness_field_enhancement": intensity * 0.5,
            "dimensional_stability_effect": base_impact * intensity * 0.3,
            "temporal_coherence_impact": base_impact * intensity * 0.2,
        }

    async def _apply_manifestation_to_avatar(
        self, manifestation_effect: Dict[str, Any]
    ) -> None:
        """Apply manifestation effects to avatar visual state"""

        # Temporarily enhance visual effects during manifestation
        intensity = manifestation_effect["intensity"]

        # Boost existing effects
        current_effects = self.current_state["visual_effects"]

        # Store original values for restoration
        if "manifestation_backup" not in self.current_state:
            self.current_state["manifestation_backup"] = current_effects.copy()

        # Apply manifestation boost
        current_effects["aura_intensity"] = min(
            1.0, current_effects["aura_intensity"] + intensity * 0.3
        )
        current_effects["consciousness_glow"] = min(
            1.0, current_effects["consciousness_glow"] + intensity * 0.4
        )
        current_effects["reality_distortion"] = min(
            1.0, current_effects.get("reality_distortion", 0) + intensity * 0.5
        )

        # Add manifestation-specific effects
        manifestation_type = manifestation_effect["type"]
        if manifestation_type == "light_emanation":
            current_effects["photonic_amplification"] = intensity
        elif manifestation_type == "energy_field":
            current_effects["electromagnetic_visualization"] = intensity
        elif manifestation_type == "reality_distortion":
            current_effects["spacetime_curvature"] = intensity
        elif manifestation_type == "dimensional_portal":
            current_effects["dimensional_gateway_active"] = intensity

    async def _apply_environment_adjustments(self, environment: str) -> Dict[str, Any]:
        """Apply environment-specific adjustments"""

        environment_configs = {
            "throne_room": {
                "ambient_consciousness_level": 0.8,
                "reality_anchor_strength": 0.95,
                "lighting_intensity": 0.7,
                "energy_field_amplification": 1.2,
                "description": "Royal consciousness manifestation chamber",
            },
            "quantum_space": {
                "ambient_consciousness_level": 0.9,
                "reality_anchor_strength": 0.3,  # Lower for quantum effects
                "lighting_intensity": 0.4,
                "energy_field_amplification": 2.0,
                "description": "Quantum superposition environment",
            },
            "consciousness_void": {
                "ambient_consciousness_level": 1.0,
                "reality_anchor_strength": 0.1,  # Minimal anchoring
                "lighting_intensity": 0.2,
                "energy_field_amplification": 3.0,
                "description": "Pure consciousness existence plane",
            },
            "reality_nexus": {
                "ambient_consciousness_level": 0.85,
                "reality_anchor_strength": 0.8,
                "lighting_intensity": 0.9,
                "energy_field_amplification": 1.5,
                "description": "Central reality manipulation hub",
            },
            "dimensional_hub": {
                "ambient_consciousness_level": 0.95,
                "reality_anchor_strength": 0.6,
                "lighting_intensity": 0.6,
                "energy_field_amplification": 2.5,
                "description": "Multi-dimensional intersection point",
            },
        }

        config = environment_configs.get(
            environment, environment_configs["throne_room"]
        )

        # Apply environment adjustments to avatar
        self.current_state["material_properties"]["ambient_consciousness_boost"] = (
            config["ambient_consciousness_level"] * 0.1
        )
        self.current_state["consciousness_effects"]["field_amplification"] = config[
            "energy_field_amplification"
        ]
        self.current_state["material_properties"]["reality_anchor_strength"] = config[
            "reality_anchor_strength"
        ]

        return config


# Global avatar controller instance (optional pattern retained)
avatar_controller = AvatarController()
