from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import time
from .settings import SETTINGS
from common.audit_chain import (
    append_event as audit_append,
    verify_range as audit_verify_range,
)
from .guardian.unicode_sanitizer import sanitize
from .guardian.ai_firewall import guard_intake, guard_outbound
from .guardian.dlp_guard import scan_text, DLPViolation
from .guardian.output_encoder import safe_preview
from .guardian.audit import AUDIT
from .reveal.orchestrator import RevealOrchestrator

try:
    from .governance_fsm import (
        fsm_create,
        fsm_queue,
        fsm_approve as fsm_approve_helper,
        fsm_execute as fsm_execute_helper,
        map_set,
    )
except Exception:  # pragma: no cover
    fsm_create = None
    fsm_queue = None
    fsm_approve_helper = None
    fsm_execute_helper = None
    map_set = None
from .symbolic.symbolic_parser import parse_envelope
from .self_build.backlog_loader import load_backlog
from .self_build.task_graph import to_dag
from .self_build.codegen import propose_patch
from .self_build.tester import run_tests
from .self_build.worker import sandbox_build
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]
ART_DIR = REPO_ROOT / "self_build" / "artifacts"
PATCH_DIR = REPO_ROOT / "self_build" / "patches"
STATE_DIR = Path(__file__).resolve().parent / "state"
MEMORY_PATH = STATE_DIR / "memory.jsonl"
PLAN_Q_PATH = STATE_DIR / "plan_queue.json"

router = APIRouter(prefix="/planning", tags=["planning"])
reveal = RevealOrchestrator()


class ChatInput(BaseModel):
    message: str
    # Optional symbolic control envelope
    intent: Optional[str] = None
    domain: Optional[str] = None
    priority: Optional[str] = None
    coherence_bias: Optional[float] = None
    perf_mode: Optional[str] = None  # e.g., BOOST, NORMAL, THROTTLE


class ChatMessage(BaseModel):
    role: str = "user"
    text: str
    ts: float = 0.0


class PlanItem(BaseModel):
    id: str
    action: str
    details: Dict[str, Any] = {}
    approved: bool = False
    created_ts: float = 0.0
    approved_ts: Optional[float] = None


_PERF_STATE = {"mode": "NORMAL", "coherence_bias": 0.5}
_PLANNING_MODE = True
_PENDING: List[Dict[str, Any]] = []
_EXECUTED_COUNT = 0


def _ensure_state_files():
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        ART_DIR.mkdir(parents=True, exist_ok=True)
        PATCH_DIR.mkdir(parents=True, exist_ok=True)
        if not MEMORY_PATH.exists():
            MEMORY_PATH.write_text("", encoding="utf-8")
        if not PLAN_Q_PATH.exists():
            PLAN_Q_PATH.write_text("[]", encoding="utf-8")
    except Exception:
        pass


def _append_memory(event: Dict[str, Any]):
    try:
        with open(MEMORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _load_plan_queue() -> List[Dict[str, Any]]:
    try:
        data = json.loads(PLAN_Q_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_plan_queue(items: List[Dict[str, Any]]):
    try:
        PLAN_Q_PATH.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _tail_memory(limit: int = 200) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        if not MEMORY_PATH.exists():
            return rows
        lines = MEMORY_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        for ln in lines[-max(1, int(limit)) :] if lines else []:
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                # skip malformed rows
                continue
    except Exception:
        pass
    return rows


@router.get("/status")
async def status():
    # Backward compatible status and webview-facing shape
    return {
        "ok": True,
        "safe_mode": SETTINGS.SAFE_MODE,
        "planning_mode": bool(_PLANNING_MODE),
        "pending": list(_PENDING),
        "executed_count": int(_EXECUTED_COUNT),
    }


class PlanningToggleBody(BaseModel):
    enabled: bool


@router.post("/toggle")
async def planning_toggle(body: PlanningToggleBody):
    global _PLANNING_MODE
    _PLANNING_MODE = bool(body.enabled)
    try:
        audit_append(
            actor="planner",
            action="planning.toggle",
            ctx={"SAFE_MODE": bool(SETTINGS.SAFE_MODE)},
            payload={"enabled": _PLANNING_MODE},
        )
    except Exception:
        pass
    return {"planning_mode": _PLANNING_MODE}


class ManifestApproveBody(BaseModel):
    manifestation_id: str


@router.post("/approve")
async def approve_manifestation(body: ManifestApproveBody):
    # Minimal: increment executed count and drop from pending if present
    global _EXECUTED_COUNT
    removed = False
    try:
        for i, p in enumerate(list(_PENDING)):
            if p.get("manifestation_id") == body.manifestation_id:
                _PENDING.pop(i)
                removed = True
                break
    except Exception:
        pass
    _EXECUTED_COUNT += 1
    desc = f"Manifestation {body.manifestation_id} executed" + (
        " (from pending)" if removed else ""
    )
    try:
        audit_append(
            actor="approver",
            action="planning.approve",
            ctx={"SAFE_MODE": bool(SETTINGS.SAFE_MODE)},
            payload={"manifestation_id": body.manifestation_id},
        )
    except Exception:
        pass
    return {
        "executed": {"id": body.manifestation_id, "description": desc},
        "executed_count": _EXECUTED_COUNT,
    }


@router.post("/chat")
async def chat(inp: ChatInput):
    _ensure_state_files()
    m = sanitize(inp.message)
    ok, meta = guard_intake(m)
    if not ok:
        _bump("intake_block")
        AUDIT.append({"type": "intake_block", "detail": meta})
        raise HTTPException(status_code=400, detail="intake blocked")
    else:
        _bump("intake_ok")
    try:
        scan_text(m)
    except DLPViolation as e:
        AUDIT.append({"type": "dlp_block", "detail": str(e)})
        raise HTTPException(status_code=400, detail="DLP block")

    # Update symbolic control state from envelope
    env = parse_envelope(inp.dict())
    mode = env.get("perf_mode") or inp.perf_mode
    if mode:
        _PERF_STATE["mode"] = str(mode)
    cb = (
        env.get("coherence_bias")
        if env.get("coherence_bias") is not None
        else inp.coherence_bias
    )
    if cb is not None:
        try:
            _PERF_STATE["coherence_bias"] = max(0.0, min(1.0, float(cb)))
        except Exception:
            pass

    # Persist inbound chat
    chat_rec = ChatMessage(text=m, ts=time.time()).dict()
    _append_memory({"type": "chat", **chat_rec})

    # Fake planning echo with guards
    out = {
        "role": "planner",
        "content": f"Plan: {m}",
        "intent": inp.intent,
        "priority": inp.priority,
    }
    ok2, meta2 = guard_outbound(str(out))
    if not ok2:
        _bump("out_block")
        AUDIT.append({"type": "outbound_block", "detail": meta2})
        raise HTTPException(status_code=400, detail="outbound blocked")
    else:
        _bump("out_ok")
    AUDIT.append({"type": "chat", "input": m, "output": out})
    if SETTINGS.SAFE_MODE:
        return safe_preview(out)
    return out


@router.get("/audit")
async def audit_chain():
    return AUDIT.export()


@router.get("/reveal/preview")
async def reveal_preview(intent: str):
    return reveal.preview(intent)


# -------- Reveal API --------
class RevealCreateBody(BaseModel):
    content: str
    passphrase: str
    nbf: Optional[str] = None
    ttl: Optional[int] = None
    label: Optional[str] = None


@router.post("/reveal/create")
async def reveal_create(body: RevealCreateBody):
    rid = f"rv_{int(time.time()*1000)}"
    # In SAFE mode, simulate and return emoji preview; envelope optional
    AUDIT.append(
        {
            "type": "reveal_create",
            "rid": rid,
            "label": body.label or "",
            "safe": SETTINGS.SAFE_MODE,
        }
    )
    return {"rid": rid, **reveal.preview(body.label or "launch")}


class RevealApproveBody(BaseModel):
    rid: str
    role: str


@router.post("/reveal/approve")
async def reveal_approve(body: RevealApproveBody):
    reveal.gate.submit(body.role, True)
    open_ = reveal.gate.is_open()
    AUDIT.append(
        {"type": "reveal_approve", "rid": body.rid, "role": body.role, "open": open_}
    )
    return {"rid": body.rid, "quorum": open_}


class RevealResolveBody(BaseModel):
    rid: str
    passphrase: str


@router.post("/reveal/resolve")
async def reveal_resolve(body: RevealResolveBody):
    if not reveal.gate.is_open():
        raise HTTPException(403, "quorum not reached")
    AUDIT.append(
        {"type": "reveal_resolve", "rid": body.rid, "safe": SETTINGS.SAFE_MODE}
    )
    if SETTINGS.SAFE_MODE:
        return {"ok": True, "simulated": True, "preview": True}
    # When not safe, would decrypt and return plaintext; here just signal ok
    return {"ok": True, "simulated": False, "plaintext": "LAUNCH_AUTHORIZED"}


@router.get("/reveal/list")
async def reveal_list():
    # Minimal: return approvals snapshot
    try:
        status = reveal.gate.status()
        return {"approvals": status.get("approvals", [])}
    except Exception:
        return {"approvals": []}


# -------- perf and guardian metrics --------
_GUARD_METRICS = {"intake_ok": 0, "intake_block": 0, "out_ok": 0, "out_block": 0}
_SELF_METRICS = {"runs": 0, "approved": 0}


def _bump(metric: str):
    _GUARD_METRICS[metric] = _GUARD_METRICS.get(metric, 0) + 1


@router.get("/perf_state")
async def perf_state():
    return dict(_PERF_STATE)


@router.get("/guardian/metrics")
async def guardian_metrics():
    return dict(_GUARD_METRICS)


# -------- simple plan queue APIs with persistence --------
@router.get("/plans")
async def list_plans():
    _ensure_state_files()
    return _load_plan_queue()


class QueuePlanBody(BaseModel):
    action: str
    details: Dict[str, Any] = {}


@router.post("/plans/queue")
async def queue_plan(body: QueuePlanBody):
    _ensure_state_files()
    items = _load_plan_queue()
    pid = f"p_{int(time.time()*1000)}"
    item = PlanItem(
        id=pid, action=body.action, details=body.details, created_ts=time.time()
    ).dict()
    items.append(item)
    _save_plan_queue(items)
    _append_memory({"type": "plan", **item})
    # Audit append (non-sensitive digest only)
    try:
        run_ctx = {"SAFE_MODE": bool(SETTINGS.SAFE_MODE)}
        audit_append(
            actor="planner",
            action="plan.create",
            ctx=run_ctx,
            payload={"plan_id": pid, "action": body.action},
        )
    except Exception:
        pass
    # Create and queue an FSM record mapped to this plan
    try:
        if fsm_create and fsm_queue and map_set:
            fsm_id = fsm_create(
                action=body.action, details=body.details, actor="planner"
            )
            map_set(item["id"], fsm_id)
            try:
                fsm_queue(fsm_id=fsm_id, actor="planner")
            except Exception:
                pass
            item["fsm_id"] = fsm_id
    except Exception:
        pass
    return item


# Compatibility helpers for runbook examples
class PlanAddBody(BaseModel):
    id: Optional[str] = None
    kind: str = "action"
    title: str
    details: Optional[str] = None


@router.post("/plan/add")
async def plan_add(body: PlanAddBody):
    return await queue_plan(
        QueuePlanBody(
            action=body.title,
            details={"kind": body.kind, "details": body.details or ""},
        )
    )


@router.get("/plan/list")
async def plan_list():
    return await list_plans()


class ApproveBody(BaseModel):
    id: str


@router.post("/plans/approve")
async def approve_plan_api(body: ApproveBody):
    items = _load_plan_queue()
    for it in items:
        if it.get("id") == body.id:
            it["approved"] = True
            it["approved_ts"] = time.time()
            _save_plan_queue(items)
            _append_memory({"type": "plan_approved", "id": body.id, "ts": time.time()})
            try:
                audit_append(
                    actor="approver",
                    action="plan.approve",
                    ctx={"SAFE_MODE": bool(SETTINGS.SAFE_MODE)},
                    payload={"plan_id": body.id},
                )
            except Exception:
                pass
            # Mirror FSM approve
            try:
                if fsm_approve_helper:
                    # Locate mapped fsm id
                    try:
                        from .governance_fsm import map_get

                        fsm_id = map_get(body.id)
                    except Exception:
                        fsm_id = None
                    if fsm_id:
                        fsm_approve_helper(
                            fsm_id=fsm_id, consent_key="APPROVED", actor="approver"
                        )
            except Exception:
                pass
            return it
    raise HTTPException(404, "plan not found")


# -------- self_build stubs --------
@router.get("/build/tasks")
async def build_tasks():
    # Merge static seeds with backlog-derived tasks
    seeds = [
        {
            "id": "guardian_metrics",
            "title": "Implement guardian metrics counters",
            "impact": 0.6,
            "effort": 0.2,
        },
        {
            "id": "persist_chat_plan",
            "title": "Persist CHAT/PLAN to state/",
            "impact": 0.8,
            "effort": 0.1,
        },
    ]
    tasks = load_backlog() + seeds
    return to_dag(tasks)


class BuildRunBody(BaseModel):
    task_id: str


@router.post("/build/run")
async def build_run(body: BuildRunBody):
    _ensure_state_files()
    task_id = body.task_id
    candidate = propose_patch({"id": task_id, "title": task_id})
    res = sandbox_build(
        task_id=task_id, patch_text=candidate, artifacts_dir=str(ART_DIR)
    )
    # Save candidate patch
    try:
        (PATCH_DIR / f"{res.get('run_id')}.patch").write_text(
            candidate, encoding="utf-8"
        )
    except Exception:
        pass
    _append_memory(
        {
            "type": "build_run",
            "task_id": task_id,
            "rid": res.get("run_id"),
            "ts": time.time(),
            "ok": bool(res.get("ok")),
        }
    )
    _SELF_METRICS["runs"] = _SELF_METRICS.get("runs", 0) + 1
    try:
        audit_append(
            actor="builder",
            action="plan.execute",
            ctx={"SAFE_MODE": bool(SETTINGS.SAFE_MODE)},
            payload={"run_id": res.get("run_id"), "task_id": task_id},
        )
    except Exception:
        pass
    # Attempt to mark FSM executing if mapped
    try:
        if fsm_execute_helper:
            try:
                from .governance_fsm import map_get

                pid = res.get("run_id")  # use run_id as plan id mapping only if present
                if isinstance(pid, str):
                    fsm_id = map_get(pid)
                else:
                    fsm_id = None
            except Exception:
                fsm_id = None
            if fsm_id:
                fsm_execute_helper(fsm_id=fsm_id, actor="builder")
    except Exception:
        pass
    return {**res, "patch_path": str(PATCH_DIR / f"{res.get('run_id')}.patch")}


class BuildApproveBody(BaseModel):
    run_id: str


@router.post("/build/approve")
async def build_approve(body: BuildApproveBody):
    # Stub: note approval
    _append_memory({"type": "build_approve", "run_id": body.run_id, "ts": time.time()})
    _SELF_METRICS["approved"] = _SELF_METRICS.get("approved", 0) + 1
    # If SAFE is off, attempt to apply patch in staging and re-run tests
    if not SETTINGS.SAFE_MODE:
        repo = REPO_ROOT
        try:
            # Ensure git repository
            subprocess.check_call(
                ["git", "rev-parse", "--is-inside-work-tree"], cwd=repo
            )
            subprocess.check_call(
                ["git", "checkout", "-B", "awakening-staging"], cwd=repo
            )
            patch_path = PATCH_DIR / f"{body.run_id}.patch"
            if not patch_path.exists():
                raise RuntimeError("patch not found")
            subprocess.check_call(["git", "apply", "--3way", str(patch_path)], cwd=repo)
            # Re-run test worker (placeholder: just call run_tests here)
            ok, logs = run_tests(body.run_id + "_post")
            if not ok:
                raise RuntimeError("tests failed after apply")
        except Exception as e:
            # Attempt to reset changes
            try:
                subprocess.check_call(["git", "reset", "--hard"], cwd=repo)
            except Exception:
                pass
            raise HTTPException(500, f"apply failed: {e}")
    return {"approved": True, "run_id": body.run_id}


# -------- Launch endpoints --------
@router.get("/launch/dryrun")
async def launch_dryrun():
    rid = f"launch_{int(time.time()*1000)}"
    # produce a readiness report artifact
    art_dir = ART_DIR
    art_dir.mkdir(parents=True, exist_ok=True)
    report = art_dir / f"{rid}_readiness.json"
    snapshot = {
        "perf": _PERF_STATE,
        "plans": _load_plan_queue(),
        "safe": SETTINGS.SAFE_MODE,
    }
    report.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    AUDIT.append({"type": "launch_dryrun", "rid": rid})
    return {"ok": True, "run_id": rid, "artifact": str(report)}


class LaunchArmBody(BaseModel):
    window_seconds: int = 900
    checklist_ack: str


@router.post("/launch/arm")
async def launch_arm(body: LaunchArmBody):
    if SETTINGS.SAFE_MODE:
        raise HTTPException(403, "SAFE mode must be off to arm")
    if body.checklist_ack.strip().upper() != "GO":
        raise HTTPException(400, "checklist not acknowledged")
    until = time.time() + max(60, int(body.window_seconds))
    _append_memory({"type": "armed_window", "until": until, "ts": time.time()})
    AUDIT.append({"type": "armed", "until": until})
    return {"armed": True, "until": until}


@router.get("/self/metrics")
async def self_metrics():
    return dict(_SELF_METRICS)


@router.get("/build/artifacts/{run_id}")
async def get_artifacts(run_id: str):
    rd = ART_DIR / run_id
    if not rd.exists():
        return {"ok": False, "error": "not_found"}
    files = [p.name for p in rd.iterdir() if p.is_file()]
    patch = (
        str(PATCH_DIR / f"{run_id}.patch")
        if (PATCH_DIR / f"{run_id}.patch").exists()
        else None
    )
    return {"ok": True, "run_id": run_id, "files": files, "patch": patch}


@router.get("/state/snapshot")
async def state_snapshot(limit: int = 200):
    _ensure_state_files()
    mem = _tail_memory(limit)
    plans = _load_plan_queue()
    return {"memory": mem, "plans": plans}


@router.get("/audit/verify")
async def audit_verify(
    date: str = Query(..., description="YYYY-MM-DD"), end: Optional[str] = None
):
    try:
        return audit_verify_range(date, end)
    except Exception as e:
        raise HTTPException(500, f"audit verify failed: {e}")
