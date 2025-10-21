from __future__ import annotations
from emp_guard.policy import get_posture
from emp_guard.playbooks import drill_plan, ethos_rebind

def test_posture():
    p = get_posture()
    assert "exposure" in p and "hardening" in p

def test_drill_and_rebind():
    plan = drill_plan("primary")
    assert "steps" in plan and len(plan["steps"]) >= 3
    rb = ethos_rebind(["botA", "botB"])
    assert rb["ok"] is True and len(rb["rebuilt"]) == 2