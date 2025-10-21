from __future__ import annotations

from emp.drones.drone_swarm import init_swarm, step_swarm
from emp.emp_core import grid


def test_emp_grid():
    result = grid(8, 8, 0.0)
    assert result["nx"] == 8
    assert result["ny"] == 8
    assert "E" in result
    assert len(result["E"]) == 8


def test_swarm():
    state = init_swarm(4, 7)
    next_state = step_swarm(state)
    assert len(next_state["agents"]) == 4
