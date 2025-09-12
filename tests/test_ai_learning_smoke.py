import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_learning import (
    ModelEvolver,
    SelfCoderGen,
    LearningMetricsTracker,
    AIMemoryManager,
    self_coder_instance,
    learning_metrics_instance,
    ai_memory_manager_instance,
)


def test_ai_learning_exports_and_instances():
    # classes available
    assert ModelEvolver and SelfCoderGen and LearningMetricsTracker and AIMemoryManager
    # instances available
    assert (
        self_coder_instance and learning_metrics_instance and ai_memory_manager_instance
    )


def test_memory_manager_basic_store_and_retrieve():
    mm = ai_memory_manager_instance
    mm.store_memory(
        "episodic", "boot_event", {"ok": True}, importance=0.9, tags=["boot", "startup"]
    )
    res = mm.retrieve_memory("episodic", "boot")
    assert res and res[0]["key"] == "boot_event"
    stats = mm.stats()
    assert "episodic" in stats and stats["episodic"]["count"] >= 1
