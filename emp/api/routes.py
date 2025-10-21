from __future__ import annotations

import json
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from emp.drones.drone_swarm import init_swarm, step_swarm
from emp.emp_core import grid
from emp.emp_sim import step as emp_step
from emp.nanobots.nano_sim import init_field, step_field
from .schemas import StateIn

router = APIRouter()


def _require_token(token: str) -> None:
    if token != "dev-token":
        raise HTTPException(status_code=401, detail="unauthorized")


_AUDIT_PATH = os.path.join("logs", "emp_api.ndjson")


def _audit(event: str, **payload: Any) -> None:
    record = {"ts": time.time(), "event": event, **payload}
    try:
        os.makedirs("logs", exist_ok=True)
        with open(_AUDIT_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


@router.get("/emp/grid")
def emp_grid(nx: int = 32, ny: int = 32, t: float = 0.0, token: str = Query(...)):
    _require_token(token)
    result = grid(nx, ny, t)
    _audit("emp_grid", nx=result["nx"], ny=result["ny"], t=result["t"])
    return result


@router.post("/emp/step")
def emp_step_api(payload: StateIn, token: str = Query(...)):
    _require_token(token)
    new_state = emp_step(payload.state)
    _audit("emp_step", state_summary={"nx": new_state.get("nx"), "ny": new_state.get("ny"), "t": new_state.get("t")})
    return new_state


@router.get("/swarm/init")
def swarm_init(n: int = 32, seed: int = 7, token: str = Query(...)):
    _require_token(token)
    state = init_swarm(n, seed)
    _audit("swarm_init", agents=len(state.get("agents", [])))
    return state


@router.post("/swarm/step")
def swarm_step_api(payload: StateIn, token: str = Query(...)):
    _require_token(token)
    state = step_swarm(payload.state)
    _audit("swarm_step", agents=len(state.get("agents", [])), t=state.get("t"))
    return state


@router.get("/nano/init")
def nano_init(nx: int = 32, ny: int = 32, token: str = Query(...)):
    _require_token(token)
    state = init_field(nx, ny)
    _audit("nano_init", nx=state["nx"], ny=state["ny"])
    return state


@router.post("/nano/step")
def nano_step_api(payload: StateIn, token: str = Query(...)):
    _require_token(token)
    state = step_field(payload.state)
    _audit("nano_step", nx=state.get("nx"), ny=state.get("ny"), t=state.get("t"))
    return state
