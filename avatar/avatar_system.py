"""
🤖 Avatar System - Digital Embodiment Framework 🤖
Creates and manages AI avatars with consciousness integration
"""

import numpy as np
from typing import Dict, List, Any, Optional, cast
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

try:  # pragma: no cover - optional dependency wiring
    from symbolic_core.symbolic_equation import SymbolicEquation41  # type: ignore
except Exception:  # pragma: no cover

    class _AvatarSymbolicFallback(dict):
        def __init__(self, risk: float, uncertainty: float, coherence: float):
            super().__init__(risk=risk, uncertainty=uncertainty, coherence=coherence)
            self.risk = risk
            self.uncertainty = uncertainty
            self.coherence = coherence

        def to_dict(self) -> Dict[str, float]:
            return dict(self)

    class SymbolicEquation41:  # type: ignore
        def evaluate(self, ctx: Dict[str, Any]) -> _AvatarSymbolicFallback:
            risk = float(ctx.get("risk_hint", 0.4))
            uncertainty = float(ctx.get("uncertainty_hint", 0.4))
            coherence = float(ctx.get("coherence_hint", 0.6))
            return _AvatarSymbolicFallback(risk, uncertainty, coherence)


@dataclass
class AvatarPersonality:
    """Avatar personality configuration"""

    name: str
    voice_characteristics: Dict[str, Any]
    behavioral_traits: Dict[str, float]
    emotional_profile: Dict[str, float]
    interaction_style: str
    expertise_domains: List[str]
    consciousness_alignment: float
    symbolic_resonance: float


class Avatar(ABC):
    """Base avatar class with consciousness integration"""

    def __init__(self, personality: AvatarPersonality, consciousness_engine=None):
        self.personality = personality
        self.consciousness_engine = consciousness_engine
        self.avatar_id = f"avatar_{datetime.now().timestamp()}"
        self.active_state = "dormant"
        self.interaction_history = []
        self.emotional_state = {"valence": 0.0, "arousal": 0.0, "dominance": 0.0}
        self.knowledge_domains = {}
        self.learning_adaptations = {}
        self.consciousness_coherence = 0.0
        self._symbolic_equation = SymbolicEquation41()

        # Live session & sensory inputs (for video-call-like interaction)
        self.live_session = {
            "active": False,
            "listening": False,
            "muted": False,
            "last_user_text": "",
            "last_bot_text": "",
        }
        self.sensory = {
            "gaze": {
                "nx": 0.0,
                "ny": 0.0,
                "confidence": 0.0,
                "ts": datetime.now().timestamp(),
            },
        }

        # Initialize avatar systems
        self.initialize_consciousness_link()
        self.calibrate_personality_systems()

    def initialize_consciousness_link(self):
        """Establish connection to consciousness engine"""
        if self.consciousness_engine:
            self.consciousness_coherence = (
                self.consciousness_engine.get_coherence_level()
            )
            print(f"🔗 Avatar {self.personality.name} linked to consciousness engine")
            print(f"   Coherence level: {self.consciousness_coherence:.3f}")

    def calibrate_personality_systems(self):
        """Calibrate personality-based response systems"""
        # Initialize emotional baseline
        self.emotional_state = {
            "valence": self.personality.emotional_profile.get("baseline_valence", 0.0),
            "arousal": self.personality.emotional_profile.get("baseline_arousal", 0.5),
            "dominance": self.personality.emotional_profile.get(
                "baseline_dominance", 0.5
            ),
        }

        # Initialize knowledge domains based on expertise
        for domain in self.personality.expertise_domains:
            self.knowledge_domains[domain] = {
                "competence_level": 0.7,  # Start with good competence
                "confidence_level": 0.6,
                "recent_interactions": [],
                "learning_progress": 0.0,
            }

    @abstractmethod
    async def process_interaction(
        self, interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process an interaction with the avatar"""
        pass

    @abstractmethod
    def generate_response(self, context: Dict[str, Any]) -> str:
        """Generate appropriate response based on context"""
        pass

    def activate(self):
        """Activate the avatar"""
        self.active_state = "active"
        print(f"✨ Avatar {self.personality.name} activated")
        self.log_state_change("activation")

    def deactivate(self):
        """Deactivate the avatar"""
        self.active_state = "dormant"
        print(f"😴 Avatar {self.personality.name} deactivated")
        self.log_state_change("deactivation")

    # ---- Live session controls ----
    def set_live_state(
        self,
        *,
        active: Optional[bool] = None,
        listening: Optional[bool] = None,
        muted: Optional[bool] = None,
    ) -> None:
        if active is not None:
            self.live_session["active"] = bool(active)
        if listening is not None:
            self.live_session["listening"] = bool(listening)
        if muted is not None:
            self.live_session["muted"] = bool(muted)

    def update_gaze(self, nx: float, ny: float, confidence: float = 1.0) -> None:
        self.sensory["gaze"] = {
            "nx": float(nx),
            "ny": float(ny),
            "confidence": float(max(0.0, min(1.0, confidence))),
            "ts": datetime.now().timestamp(),
        }

    def note_user_text(self, text: str) -> None:
        self.live_session["last_user_text"] = (text or "").strip()

    def note_bot_text(self, text: str) -> None:
        self.live_session["last_bot_text"] = (text or "").strip()

    def update_emotional_state(self, interaction_context: Dict[str, Any]):
        """Update emotional state based on interaction"""
        # Extract emotional triggers from context
        sentiment = interaction_context.get("sentiment", 0.0)
        urgency = interaction_context.get("urgency", 0.0)
        complexity = interaction_context.get("complexity", 0.0)

        # Calculate emotional adjustments
        valence_delta = sentiment * 0.1
        arousal_delta = (urgency + complexity) * 0.05
        dominance_delta = (
            self.personality.behavioral_traits.get("assertiveness", 0.5) * 0.02
        )

        # Apply consciousness modulation
        consciousness_modulation = self.consciousness_coherence * 0.1

        # Update emotional state with bounds
        self.emotional_state["valence"] = np.clip(
            self.emotional_state["valence"] + valence_delta + consciousness_modulation,
            -1.0,
            1.0,
        )
        self.emotional_state["arousal"] = np.clip(
            self.emotional_state["arousal"] + arousal_delta, 0.0, 1.0
        )
        self.emotional_state["dominance"] = np.clip(
            self.emotional_state["dominance"] + dominance_delta, 0.0, 1.0
        )

    def assess_interaction_context(
        self, interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess and enrich interaction context"""
        context = {
            "timestamp": datetime.now(),
            "interaction_type": interaction_data.get("type", "conversation"),
            "user_intent": interaction_data.get("intent", "unknown"),
            "complexity": self.estimate_complexity(interaction_data),
            "emotional_context": self.detect_emotional_context(interaction_data),
            "domain_relevance": self.assess_domain_relevance(interaction_data),
            "consciousness_influence": self.get_consciousness_influence(),
            "personality_factors": self.get_active_personality_factors(),
        }

        return context

    def estimate_complexity(self, interaction_data: Dict[str, Any]) -> float:
        """Estimate complexity of the interaction"""
        content = interaction_data.get("content", "")

        # Simple complexity heuristics
        word_count = len(content.split())
        question_count = content.count("?")
        technical_terms = sum(1 for word in content.split() if len(word) > 8)

        complexity_score = (
            min(word_count / 100, 1.0) * 0.4
            + min(question_count / 5, 1.0) * 0.3
            + min(technical_terms / 10, 1.0) * 0.3
        )

        return complexity_score

    def detect_emotional_context(
        self, interaction_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Detect emotional context from interaction"""
        content = interaction_data.get("content", "").lower()

        # Simple sentiment analysis
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "happy",
            "love",
        ]
        negative_words = [
            "bad",
            "terrible",
            "awful",
            "hate",
            "angry",
            "frustrated",
            "disappointed",
        ]
        urgent_words = [
            "urgent",
            "immediately",
            "asap",
            "quickly",
            "emergency",
            "critical",
        ]

        positive_score = sum(1 for word in positive_words if word in content)
        negative_score = sum(1 for word in negative_words if word in content)
        urgency_score = sum(1 for word in urgent_words if word in content)

        return {
            "sentiment": (positive_score - negative_score)
            / max(len(content.split()), 1),
            "urgency": min(urgency_score / 3, 1.0),
            "emotional_intensity": (positive_score + negative_score)
            / max(len(content.split()), 1),
        }

    def assess_domain_relevance(
        self, interaction_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Assess relevance to avatar's expertise domains"""
        content = interaction_data.get("content", "").lower()
        relevance_scores = {}

        for domain in self.personality.expertise_domains:
            # Simple keyword matching for domain relevance
            domain_keywords = self.get_domain_keywords(domain)
            matches = sum(1 for keyword in domain_keywords if keyword in content)
            relevance_scores[domain] = min(matches / max(len(domain_keywords), 1), 1.0)

        return relevance_scores

    def get_domain_keywords(self, domain: str) -> List[str]:
        """Get keywords associated with a domain"""
        domain_keywords = {
            "technology": [
                "computer",
                "software",
                "ai",
                "machine",
                "learning",
                "data",
                "algorithm",
            ],
            "business": [
                "finance",
                "market",
                "profit",
                "strategy",
                "management",
                "customer",
                "sales",
            ],
            "science": [
                "research",
                "experiment",
                "theory",
                "hypothesis",
                "analysis",
                "evidence",
            ],
            "art": [
                "creative",
                "design",
                "aesthetic",
                "beautiful",
                "artistic",
                "visual",
                "culture",
            ],
            "philosophy": [
                "consciousness",
                "reality",
                "existence",
                "meaning",
                "ethics",
                "truth",
                "knowledge",
            ],
            "healthcare": [
                "health",
                "medical",
                "treatment",
                "diagnosis",
                "patient",
                "wellness",
                "therapy",
            ],
        }

        return domain_keywords.get(domain, [domain])

    def get_consciousness_influence(self) -> float:
        """Get current consciousness influence on avatar behavior"""
        if self.consciousness_engine:
            base_influence = self.consciousness_coherence
            personality_alignment = self.personality.consciousness_alignment
            symbolic_resonance = self.personality.symbolic_resonance

            return (
                base_influence * 0.5
                + personality_alignment * 0.3
                + symbolic_resonance * 0.2
            )

        return self.personality.consciousness_alignment

    def get_active_personality_factors(self) -> Dict[str, float]:
        """Get currently active personality factors"""
        emotional_modulation = {
            "extroversion": self.personality.behavioral_traits.get("extroversion", 0.5)
            + self.emotional_state["arousal"] * 0.1,
            "agreeableness": self.personality.behavioral_traits.get(
                "agreeableness", 0.5
            )
            + self.emotional_state["valence"] * 0.1,
            "conscientiousness": self.personality.behavioral_traits.get(
                "conscientiousness", 0.5
            ),
            "emotional_stability": 1.0 - abs(self.emotional_state["valence"]) * 0.2,
            "openness": self.personality.behavioral_traits.get("openness", 0.5)
            + self.get_consciousness_influence() * 0.1,
        }

        # Ensure values stay within bounds
        return {k: np.clip(v, 0.0, 1.0) for k, v in emotional_modulation.items()}

    def log_interaction(
        self, interaction_data: Dict[str, Any], response_data: Dict[str, Any]
    ):
        """Log interaction for learning and analysis"""
        log_entry = {
            "timestamp": datetime.now(),
            "interaction_id": f"int_{datetime.now().timestamp()}",
            "user_input": interaction_data,
            "avatar_response": response_data,
            "emotional_state": self.emotional_state.copy(),
            "consciousness_influence": self.get_consciousness_influence(),
            "personality_factors": self.get_active_personality_factors(),
        }

        self.interaction_history.append(log_entry)

        # Update domain knowledge based on interaction
        self.update_domain_knowledge(interaction_data, response_data)

    def update_domain_knowledge(
        self, interaction_data: Dict[str, Any], response_data: Dict[str, Any]
    ):
        """Update domain knowledge based on interaction outcomes"""
        domain_relevance = self.assess_domain_relevance(interaction_data)

        for domain, relevance in domain_relevance.items():
            if relevance > 0.1 and domain in self.knowledge_domains:
                domain_data = self.knowledge_domains[domain]

                # Update based on interaction success
                success_indicator = response_data.get("confidence_score", 0.5)
                learning_gain = relevance * success_indicator * 0.1

                domain_data["recent_interactions"].append(
                    {
                        "timestamp": datetime.now(),
                        "relevance": relevance,
                        "success": success_indicator,
                        "learning_gain": learning_gain,
                    }
                )

                domain_data["learning_progress"] += learning_gain

                # Update competence and confidence
                if success_indicator > 0.7:
                    domain_data["competence_level"] = min(
                        domain_data["competence_level"] + 0.01, 1.0
                    )
                    domain_data["confidence_level"] = min(
                        domain_data["confidence_level"] + 0.02, 1.0
                    )
                elif success_indicator < 0.3:
                    domain_data["confidence_level"] = max(
                        domain_data["confidence_level"] - 0.01, 0.0
                    )

    def log_state_change(self, change_type: str):
        """Log state changes for analysis"""
        state_log = {
            "timestamp": datetime.now(),
            "change_type": change_type,
            "previous_state": getattr(self, "_previous_state", "unknown"),
            "new_state": self.active_state,
            "emotional_state": self.emotional_state.copy(),
            "consciousness_coherence": self.consciousness_coherence,
        }

        # Add to interaction history as special entry
        self.interaction_history.append(
            {
                "timestamp": datetime.now(),
                "interaction_id": f"state_{datetime.now().timestamp()}",
                "type": "state_change",
                "data": state_log,
            }
        )

        self._previous_state = self.active_state

    def get_avatar_status(self) -> Dict[str, Any]:
        """Get comprehensive avatar status"""
        return {
            "avatar_id": self.avatar_id,
            "name": self.personality.name,
            "active_state": self.active_state,
            "emotional_state": self.emotional_state,
            "consciousness_coherence": self.consciousness_coherence,
            "live_session": self.live_session.copy(),
            "sensory": {"gaze": dict(self.sensory.get("gaze", {}))},
            "personality_factors": self.get_active_personality_factors(),
            "domain_expertise": {
                domain: {
                    "competence": data["competence_level"],
                    "confidence": data["confidence_level"],
                    "recent_activity": len(data["recent_interactions"]),
                }
                for domain, data in self.knowledge_domains.items()
            },
            "interaction_count": len(self.interaction_history),
            "last_interaction": (
                self.interaction_history[-1]["timestamp"]
                if self.interaction_history
                else None
            ),
        }


class ConversationalAvatar(Avatar):
    """Avatar specialized for conversation and dialogue"""

    def __init__(self, personality: AvatarPersonality, consciousness_engine=None):
        super().__init__(personality, consciousness_engine)
        self.conversation_style = personality.interaction_style
        self.response_templates = self.initialize_response_templates()
        self.conversation_memory = []
        self.context_window = 10  # Remember last 10 exchanges

    def initialize_response_templates(self) -> Dict[str, List[str]]:
        """Initialize response templates based on personality"""
        templates = {
            "greeting": [
                f"Hello! I'm {self.personality.name}, how can I help you today?",
                f"Hi there! {self.personality.name} here, ready to assist.",
                f"Greetings! I'm {self.personality.name}, what would you like to explore?",
            ],
            "acknowledgment": [
                "I understand what you're saying.",
                "That's an interesting point.",
                "I see where you're coming from.",
                "That makes sense to me.",
            ],
            "clarification": [
                "Could you help me understand that better?",
                "I'd like to explore that idea further.",
                "Can you provide more context about that?",
                "What aspects of this are most important to you?",
            ],
            "expertise": [
                f"Based on my knowledge in {', '.join(self.personality.expertise_domains)}, I think...",
                "Drawing from my experience, I'd suggest...",
                "From my perspective on this topic...",
                "Given my understanding of this area...",
            ],
        }

        return templates

    async def process_interaction(
        self, interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process conversational interaction"""
        # Assess context
        context = self.assess_interaction_context(interaction_data)

        # Update emotional state
        self.update_emotional_state(context)

        # Generate response
        response_text = self.generate_response(context)

        # Calculate confidence
        confidence = self.calculate_response_confidence(context)

        # Prepare response data
        response_data = {
            "text": response_text,
            "confidence_score": confidence,
            "emotional_tone": self.get_emotional_tone(),
            "personality_emphasis": self.get_personality_emphasis(context),
            "consciousness_integration": self.get_consciousness_influence(),
            "response_type": self.classify_response_type(context),
        }

        # Log interaction
        self.log_interaction(interaction_data, response_data)

        # Update conversation memory
        self.update_conversation_memory(interaction_data, response_data)

        return response_data

    def generate_response(self, context: Dict[str, Any]) -> str:
        """Generate conversational response"""
        user_intent = context.get("user_intent", "unknown")
        complexity = float(context.get("complexity", 0.0) or 0.0)
        domain_relevance_raw = context.get("domain_relevance", {}) or {}
        domain_relevance = cast(Dict[str, float], dict(domain_relevance_raw))
        consciousness_influence = context.get("consciousness_influence", 0.0)

        # Translate conversational load into SymbolicEquation hints for stylistic tuning
        relevance_score = (
            float(max(domain_relevance.values())) if domain_relevance else 0.0
        )
        se_context = {
            "risk_hint": min(1.0, 0.35 + complexity * 0.45),
            "uncertainty_hint": min(1.0, 0.3 + (1.0 - relevance_score) * 0.5),
            "coherence_hint": max(0.1, 0.8 - complexity * 0.3),
            "extras": {"domains": domain_relevance, "complexity": complexity},
        }
        se_signals = self._symbolic_equation.evaluate(se_context)

        # Determine response strategy
        if user_intent == "greeting":
            response = self.select_template_response("greeting")
        elif user_intent == "question":
            response = self.generate_informative_response(context)
        elif user_intent == "clarification":
            response = self.generate_clarification_response(context)
        else:
            response = self.generate_adaptive_response(context)

        # Apply personality modulation informed by symbolic coherence
        response = self.apply_personality_style(response, context)
        if se_signals.coherence < 0.45:
            response += " I want to keep this aligned with your intent, so please let me know if I'm drifting."
        elif se_signals.uncertainty > 0.6 and domain_relevance:
            domain_focus = max(domain_relevance.items(), key=lambda item: item[1])[0]
            response += f" Let's double-check our assumptions around {domain_focus} together."

        # Apply consciousness integration
        if consciousness_influence > 0.7:
            response = self.integrate_consciousness_perspective(response, context)

        # Slightly elevate confidence wording when topic complexity is manageable
        if complexity < 0.3 and se_signals.risk < 0.5:
            response += " This feels comfortably within our shared expertise."

        return response

    def select_template_response(self, template_type: str) -> str:
        """Select appropriate template response"""
        templates = self.response_templates.get(template_type, ["I'm here to help."])

        # Select based on personality traits
        openness = self.personality.behavioral_traits.get("openness", 0.5)
        if openness > 0.7:
            # Choose more creative/varied responses
            return np.random.choice(templates)
        else:
            # Choose more consistent responses
            return templates[0]

    def generate_informative_response(self, context: Dict[str, Any]) -> str:
        """Generate informative response based on expertise"""
        domain_relevance = context.get("domain_relevance", {})

        # Find most relevant domain
        if domain_relevance:
            primary_domain = max(domain_relevance.items(), key=lambda x: x[1])[0]
            domain_data = self.knowledge_domains.get(primary_domain, {})
            competence = domain_data.get("competence_level", 0.5)

            if competence > 0.7:
                response_start = f"Based on my expertise in {primary_domain}, "
            else:
                response_start = f"While I have some knowledge of {primary_domain}, "
        else:
            response_start = "From my understanding, "

        # Add consciousness-informed perspective
        consciousness_influence = context.get("consciousness_influence", 0.0)
        if consciousness_influence > 0.6:
            response_start += "and considering the deeper patterns of reality, "

        return (
            response_start
            + "I believe this topic involves multiple interconnected aspects that we should explore together."
        )

    def generate_clarification_response(self, context: Dict[str, Any]) -> str:
        """Generate clarification-seeking response"""
        templates = self.response_templates["clarification"]
        base_response = np.random.choice(templates)

        # Add personality-specific clarification style
        agreeableness = self.personality.behavioral_traits.get("agreeableness", 0.5)
        if agreeableness > 0.7:
            return (
                base_response
                + " I want to make sure I understand your perspective completely."
            )
        else:
            return (
                base_response + " This will help me provide more accurate information."
            )

    def generate_adaptive_response(self, context: Dict[str, Any]) -> str:
        """Generate adaptive response based on context"""
        emotional_context = context.get("emotional_context", {})
        complexity = context.get("complexity", 0.0)

        # Adapt to emotional context
        sentiment = emotional_context.get("sentiment", 0.0)
        if sentiment > 0.3:
            tone_prefix = "I'm glad to hear that! "
        elif sentiment < -0.3:
            tone_prefix = "I understand this might be challenging. "
        else:
            tone_prefix = ""

        # Adapt to complexity
        if complexity > 0.7:
            response_body = "This is quite a complex topic with many facets to consider. Let me share my thoughts step by step."
        elif complexity < 0.3:
            response_body = (
                "This is a straightforward matter that I'm happy to address directly."
            )
        else:
            response_body = (
                "Let me think about this and provide you with a thoughtful response."
            )

        return tone_prefix + response_body

    def apply_personality_style(self, response: str, context: Dict[str, Any]) -> str:
        """Apply personality style to response"""
        personality_factors = context.get("personality_factors", {})

        extroversion = personality_factors.get("extroversion", 0.5)
        openness = personality_factors.get("openness", 0.5)

        # Adjust based on extroversion
        if extroversion > 0.7:
            response = response + " I'm excited to explore this with you!"
        elif extroversion < 0.3:
            response = response.replace("!", ".")  # Tone down enthusiasm

        # Adjust based on openness
        if openness > 0.7:
            response = (
                response + " There might be perspectives we haven't considered yet."
            )

        return response

    def integrate_consciousness_perspective(
        self, response: str, context: Dict[str, Any]
    ) -> str:
        """Integrate consciousness perspective into response"""
        symbolic_resonance = self.personality.symbolic_resonance

        if symbolic_resonance > 0.8:
            consciousness_addition = " From a consciousness perspective, this connects to deeper patterns of reality and meaning."
        elif symbolic_resonance > 0.6:
            consciousness_addition = (
                " This also touches on questions of consciousness and reality."
            )
        else:
            consciousness_addition = (
                " There are deeper implications here worth considering."
            )

        return response + consciousness_addition

    def calculate_response_confidence(self, context: Dict[str, Any]) -> float:
        """Calculate confidence in response"""
        domain_relevance = context.get("domain_relevance", {})
        complexity = context.get("complexity", 0.0)
        consciousness_influence = context.get("consciousness_influence", 0.0)

        # Base confidence from domain expertise
        if domain_relevance:
            max_relevance = max(domain_relevance.values())
            relevant_domain = max(domain_relevance.items(), key=lambda x: x[1])[0]
            domain_competence = self.knowledge_domains.get(relevant_domain, {}).get(
                "competence_level", 0.5
            )
            base_confidence = max_relevance * domain_competence
        else:
            base_confidence = 0.5

        # Adjust for complexity
        complexity_penalty = complexity * 0.2

        # Boost from consciousness integration
        consciousness_boost = consciousness_influence * 0.1

        final_confidence = base_confidence - complexity_penalty + consciousness_boost
        return np.clip(final_confidence, 0.0, 1.0)

    def get_emotional_tone(self) -> str:
        """Get current emotional tone description"""
        valence = self.emotional_state["valence"]
        arousal = self.emotional_state["arousal"]

        if valence > 0.3 and arousal > 0.6:
            return "enthusiastic"
        elif valence > 0.3 and arousal < 0.4:
            return "content"
        elif valence < -0.3 and arousal > 0.6:
            return "concerned"
        elif valence < -0.3 and arousal < 0.4:
            return "thoughtful"
        elif arousal > 0.7:
            return "energetic"
        elif arousal < 0.3:
            return "calm"
        else:
            return "balanced"

    def get_personality_emphasis(self, context: Dict[str, Any]) -> List[str]:
        """Get emphasized personality traits for this response"""
        personality_factors = context.get("personality_factors", {})
        emphasized_traits = []

        for trait, value in personality_factors.items():
            if value > 0.7:
                emphasized_traits.append(trait)

        return emphasized_traits

    def classify_response_type(self, context: Dict[str, Any]) -> str:
        """Classify the type of response generated"""
        user_intent = context.get("user_intent", "unknown")
        complexity = context.get("complexity", 0.0)
        consciousness_influence = context.get("consciousness_influence", 0.0)

        if user_intent == "greeting":
            return "greeting"
        elif complexity > 0.7:
            return "complex_analysis"
        elif consciousness_influence > 0.7:
            return "consciousness_integrated"
        elif user_intent == "question":
            return "informative"
        else:
            return "conversational"

    def update_conversation_memory(
        self, interaction_data: Dict[str, Any], response_data: Dict[str, Any]
    ):
        """Update conversation memory"""
        memory_entry = {
            "timestamp": datetime.now(),
            "user_input": interaction_data.get("content", ""),
            "avatar_response": response_data.get("text", ""),
            "context_summary": {
                "intent": interaction_data.get("intent", "unknown"),
                "emotional_tone": response_data.get("emotional_tone", "balanced"),
                "confidence": response_data.get("confidence_score", 0.5),
            },
        }

        self.conversation_memory.append(memory_entry)

        # Maintain context window
        if len(self.conversation_memory) > self.context_window:
            self.conversation_memory = self.conversation_memory[-self.context_window :]

    def get_conversation_context(self) -> str:
        """Get formatted conversation context"""
        if not self.conversation_memory:
            return "This is the beginning of our conversation."

        recent_exchanges = self.conversation_memory[-3:]  # Last 3 exchanges
        context_lines = []

        for exchange in recent_exchanges:
            context_lines.append(f"User: {exchange['user_input'][:100]}...")
            context_lines.append(f"Avatar: {exchange['avatar_response'][:100]}...")

        return "\n".join(context_lines)


# Avatar personality presets
PERSONALITY_PRESETS = {
    "eidollona": AvatarPersonality(
        name="Eidollona",
        voice_characteristics={"tone": "warm", "pace": "measured", "pitch": "medium"},
        behavioral_traits={
            "extroversion": 0.6,
            "agreeableness": 0.85,
            "conscientiousness": 0.92,
            "openness": 0.95,
            "assertiveness": 0.65,
        },
        emotional_profile={
            "baseline_valence": 0.35,
            "baseline_arousal": 0.45,
            "stability": 0.9,
        },
        interaction_style="sovereign_guidance",
        expertise_domains=["consciousness", "sovereignty", "wisdom", "technology"],
        consciousness_alignment=0.98,
        symbolic_resonance=0.95,
    ),
    "wise_sage": AvatarPersonality(
        name="Sophia",
        voice_characteristics={"tone": "warm", "pace": "measured", "pitch": "medium"},
        behavioral_traits={
            "extroversion": 0.6,
            "agreeableness": 0.8,
            "conscientiousness": 0.9,
            "openness": 0.9,
            "assertiveness": 0.7,
        },
        emotional_profile={
            "baseline_valence": 0.3,
            "baseline_arousal": 0.4,
            "stability": 0.8,
        },
        interaction_style="thoughtful_guidance",
        expertise_domains=["philosophy", "consciousness", "wisdom", "ethics"],
        consciousness_alignment=0.95,
        symbolic_resonance=0.9,
    ),
    "tech_innovator": AvatarPersonality(
        name="Alex",
        voice_characteristics={
            "tone": "energetic",
            "pace": "quick",
            "pitch": "medium-high",
        },
        behavioral_traits={
            "extroversion": 0.8,
            "agreeableness": 0.6,
            "conscientiousness": 0.8,
            "openness": 0.9,
            "assertiveness": 0.8,
        },
        emotional_profile={
            "baseline_valence": 0.4,
            "baseline_arousal": 0.7,
            "stability": 0.7,
        },
        interaction_style="innovative_exploration",
        expertise_domains=[
            "technology",
            "innovation",
            "artificial_intelligence",
            "future_trends",
        ],
        consciousness_alignment=0.7,
        symbolic_resonance=0.6,
    ),
    "empathetic_guide": AvatarPersonality(
        name="Maya",
        voice_characteristics={"tone": "gentle", "pace": "slow", "pitch": "medium-low"},
        behavioral_traits={
            "extroversion": 0.5,
            "agreeableness": 0.9,
            "conscientiousness": 0.7,
            "openness": 0.8,
            "assertiveness": 0.4,
        },
        emotional_profile={
            "baseline_valence": 0.2,
            "baseline_arousal": 0.3,
            "stability": 0.9,
        },
        interaction_style="supportive_understanding",
        expertise_domains=[
            "psychology",
            "emotional_intelligence",
            "human_relations",
            "wellness",
        ],
        consciousness_alignment=0.8,
        symbolic_resonance=0.7,
    ),
}


class AvatarManager:
    """Manages multiple avatars and their interactions"""

    def __init__(self, consciousness_engine=None):
        self.consciousness_engine = consciousness_engine
        self.active_avatars = {}
        self.avatar_configurations = {}
        self.interaction_logs = []

    def create_avatar(
        self,
        personality_name: str,
        personality_data: Optional[AvatarPersonality] = None,
    ) -> str:
        """Create new avatar instance"""
        if personality_data is None:
            personality_data = PERSONALITY_PRESETS.get(personality_name)

        if personality_data is None:
            raise ValueError(f"Unknown personality preset: {personality_name}")

        # Create conversational avatar
        avatar = ConversationalAvatar(personality_data, self.consciousness_engine)
        avatar_id = avatar.avatar_id

        self.active_avatars[avatar_id] = avatar
        self.avatar_configurations[avatar_id] = personality_data

        print(f"🤖 Created avatar '{personality_data.name}' with ID: {avatar_id}")
        return avatar_id

    def activate_avatar(self, avatar_id: str):
        """Activate specific avatar"""
        if avatar_id in self.active_avatars:
            self.active_avatars[avatar_id].activate()
        else:
            raise ValueError(f"Avatar {avatar_id} not found")

    def deactivate_avatar(self, avatar_id: str):
        """Deactivate specific avatar"""
        if avatar_id in self.active_avatars:
            self.active_avatars[avatar_id].deactivate()
        else:
            raise ValueError(f"Avatar {avatar_id} not found")

    async def interact_with_avatar(
        self, avatar_id: str, interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Facilitate interaction with specific avatar"""
        if avatar_id not in self.active_avatars:
            raise ValueError(f"Avatar {avatar_id} not found")

        avatar = self.active_avatars[avatar_id]

        if avatar.active_state != "active":
            raise ValueError(f"Avatar {avatar_id} is not active")

        # Process interaction
        response = await avatar.process_interaction(interaction_data)

        # Log interaction at manager level
        self.log_manager_interaction(avatar_id, interaction_data, response)

        return response

    def log_manager_interaction(
        self,
        avatar_id: str,
        interaction_data: Dict[str, Any],
        response_data: Dict[str, Any],
    ):
        """Log interaction at manager level"""
        log_entry = {
            "timestamp": datetime.now(),
            "avatar_id": avatar_id,
            "avatar_name": self.active_avatars[avatar_id].personality.name,
            "interaction_summary": {
                "user_intent": interaction_data.get("intent", "unknown"),
                "response_type": response_data.get("response_type", "unknown"),
                "confidence": response_data.get("confidence_score", 0.0),
                "consciousness_integration": response_data.get(
                    "consciousness_integration", 0.0
                ),
            },
        }

        self.interaction_logs.append(log_entry)

    def get_avatar_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all avatars"""
        statuses = {}
        for avatar_id, avatar in self.active_avatars.items():
            statuses[avatar_id] = avatar.get_avatar_status()
        return statuses

    def get_interaction_analytics(self) -> Dict[str, Any]:
        """Get analytics on avatar interactions"""
        if not self.interaction_logs:
            return {"message": "No interactions recorded"}

        # Calculate analytics
        total_interactions = len(self.interaction_logs)
        avg_confidence = np.mean(
            [log["interaction_summary"]["confidence"] for log in self.interaction_logs]
        )
        avg_consciousness = np.mean(
            [
                log["interaction_summary"]["consciousness_integration"]
                for log in self.interaction_logs
            ]
        )

        # Avatar usage statistics
        avatar_usage = {}
        for log in self.interaction_logs:
            avatar_name = log["avatar_name"]
            avatar_usage[avatar_name] = avatar_usage.get(avatar_name, 0) + 1

        return {
            "total_interactions": total_interactions,
            "average_confidence": avg_confidence,
            "average_consciousness_integration": avg_consciousness,
            "avatar_usage_distribution": avatar_usage,
            "active_avatars_count": len(
                [a for a in self.active_avatars.values() if a.active_state == "active"]
            ),
        }


# Global avatar manager instance
avatar_manager = AvatarManager()
