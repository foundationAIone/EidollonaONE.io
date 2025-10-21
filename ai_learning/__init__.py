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
from .eval import EvaluationConfig, EvaluationHarness, EvaluationSummary, run_with_config_path

__all__ = [
    "ModelEvolver",
    "SelfCoderGen",
    "LearningMetricsTracker",
    "AIMemoryManager",
    "EvaluationHarness",
    "EvaluationConfig",
    "EvaluationSummary",
    # Instances
    "self_coder_instance",
    "learning_metrics_instance",
    "ai_memory_manager_instance",
    "run_with_config_path",
]
