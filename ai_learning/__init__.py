"""
ai_learning: model evolution, self-coding, learning metrics, and AI memory.
"""

from .model_evolver import ModelEvolver
from .self_coder import SelfCoder as SelfCoderGen, self_coder as self_coder_instance
from .learning_metrics import (
    LearningMetrics as LearningMetricsTracker,
    learning_metrics as learning_metrics_instance,
)
from .ai_memory_manager import (
    AIMemoryManager,
    ai_memory_manager as ai_memory_manager_instance,
)

__all__ = [
    "ModelEvolver",
    "SelfCoderGen",
    "LearningMetricsTracker",
    "AIMemoryManager",
    # Instances
    "self_coder_instance",
    "learning_metrics_instance",
    "ai_memory_manager_instance",
]
