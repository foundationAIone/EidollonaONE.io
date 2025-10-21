from __future__ import annotations

from fastapi import APIRouter, Depends

from emp_guard.audit import log
from emp_guard.api.schemas import CapsIn, RebindIn
from emp_guard.hud import update_dashboard
from emp_guard.playbooks import drill_plan, ethos_rebind, run_drill
from emp_guard.policy import get_posture, update_caps
from security.deps import require_token
from utils.audit import audit_ndjson

router = APIRouter()


@router.get("/posture")
def posture(token: str = Depends(require_token)):
    posture = get_posture()
    log("posture_view", token=token)
    update_dashboard(posture, note="posture viewed")
    audit_ndjson("emp_guard_posture", token=token, posture=posture)
    return {"ok": True, "posture": posture}


@router.get("/drill/plan")
def drillplan(site: str = "primary", token: str = Depends(require_token)):
    plan = drill_plan(site)
    log("drill_plan", site=site)
    update_dashboard(get_posture(), note=f"drill plan for {site}")
    audit_ndjson("emp_guard_drill_plan", token=token, site=site, plan=plan)
    return {"ok": True, "plan": plan}


@router.post("/drill/run")
def drillrun(site: str = "primary", token: str = Depends(require_token)):
    result = run_drill(site)
    update_dashboard(get_posture(), note=f"drill run {site}")
    audit_ndjson("emp_guard_drill_run", token=token, site=site, result=result)
    return {"ok": True, "result": result}


@router.post("/rebind/ethos")
def rebind_ethos(payload: RebindIn, token: str = Depends(require_token)):
    safe_targets = [t for t in (payload.targets or []) if t]
    if not safe_targets:
        log("rebind_skip", reason="no_targets")
        update_dashboard(get_posture(), note="rebind skipped")
        result = {"rebuilt": [], "note": "no targets"}
        audit_ndjson("emp_guard_rebind_skip", token=token, result=result)
        return {"ok": True, "result": result}
    result = ethos_rebind(safe_targets)
    update_dashboard(get_posture(), note=f"rebind {len(safe_targets)} targets")
    audit_ndjson("emp_guard_rebind", token=token, rebuilt=result, count=len(safe_targets))
    return {"ok": True, "result": result}


@router.post("/posture/caps")
def posture_caps(payload: CapsIn, token: str = Depends(require_token)):
    if hasattr(payload, "model_dump"):
        caps_request = payload.model_dump(exclude_none=True)  # type: ignore[attr-defined]
    else:
        caps_request = payload.dict(exclude_none=True)  # type: ignore[attr-defined]
    updated_caps = update_caps(caps_request)
    posture = get_posture()
    note = "caps updated" if caps_request else "caps inspected"
    log("caps_update", caps=updated_caps)
    update_dashboard(posture, note=note)
    audit_ndjson("emp_guard_caps_update", token=token, caps=updated_caps, changed=bool(caps_request))
    return {"ok": True, "caps": updated_caps}
