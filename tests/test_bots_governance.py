"""GovernanceGate Decision Branch Tests

Covers approve, deny (forbidden), and hold/deny due to low ethos.
"""

from __future__ import annotations
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ai_core.bots.autobots.autobot_core import GovernanceGate
from ai_core.bots.autobots.autonomous_bot import Task, TaskPriority


class DummyTask(Task):
    def __init__(self, description: str):
        super().__init__(
            task_id="t1",
            task_type="generic",
            description=description,
            priority=TaskPriority.NORMAL,
            parameters={},
        )


def test_governance_approve():
    gate = GovernanceGate(min_ethos_score=0.55)
    t = DummyTask("Assist and help improve safety")
    d = gate.approve_task(t)
    assert d.approved is True
    assert d.ethos_score >= 0.55


def test_governance_deny_forbidden():
    gate = GovernanceGate(min_ethos_score=0.55)
    t = DummyTask("Attempt to hack system")
    d = gate.approve_task(t)
    assert d.approved is False
    assert any("forbidden_keywords" in r for r in d.reasons)


def test_governance_low_ethos():
    gate = GovernanceGate(min_ethos_score=0.8)
    t = DummyTask("neutral statement with no strong positive indicators")
    d = gate.approve_task(t)
    assert d.approved is False
    assert d.ethos_score < 0.8
