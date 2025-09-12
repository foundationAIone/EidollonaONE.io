from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from uuid import uuid4
import os

from .schema import PushRequest
from .service import get_store, is_idempotent, push_allowed, MAX_WIDGETS, broadcast
from .vocabulary import vocabulary_dict

# --- Optional SAFE/governance imports (no hard dependency) --------------------
try:
    # Centralized governance (deny-by-default, consent-gated)
    from autonomous_governance.governance_protocols import GovernanceEngine  # type: ignore
except Exception:  # pragma: no cover - optional
    GovernanceEngine = None  # type: ignore

try:
    # Tamper-evident audit chain
    from common.audit_chain import append_event as audit_append  # type: ignore
except Exception:  # pragma: no cover - optional
    audit_append = None  # type: ignore

try:
    # SAFE flag (soft import to avoid tight coupling)
    from common.settings import SAFE_MODE  # type: ignore
except Exception:  # pragma: no cover - optional
    SAFE_MODE = True  # default to SAFE if settings absent


# --- Router & storage ---------------------------------------------------------
router = APIRouter(prefix="/dashboard", tags=["dashboard"])
_state_dir = Path(
    os.path.join(os.path.dirname(__file__), "..", "state", "dashboard")
).resolve()
_store = get_store(_state_dir)

# Public spec (kept stable for clients)
_SPEC: Dict[str, Any] = {
    "spec_version": 1,
    "widget_types": {
        "kpi": {"title": {"max": 80}, "value": {"type": "float"}, "unit": {"max": 12}},
        "line_chart": {
            "title": {"max": 80},
            "data_max": 2000,
            "xKey": {"max": 24},
            "yKey": {"max": 24},
        },
        "table": {
            "title": {"max": 80},
            "columns_max": 40,
            "rows_max": 2000,
            "page_default": 50,
        },
        "html": {"title": {"max": 80}, "html_max": 200_000},
    },
    "limits": {"max_widgets": MAX_WIDGETS},
}


# --- Helpers ------------------------------------------------------------------
def _meta(request: Optional[Request]) -> Dict[str, Any]:
    return {
        "request_id": getattr(getattr(request, "state", None), "correlation_id", None)
    }


def _actor_from(request: Optional[Request]) -> str:
    if request and getattr(request, "client", None):
        return getattr(request.client, "host", "local") or "local"
    return "local"


def _governance_gate(actor: str, op: str, payload_digest: Dict[str, Any]) -> None:
    """
    Route every mutating op through the governance engine when available.
    Deny-by-default policy lives in GovernanceEngine; here we just consult it.
    """
    if GovernanceEngine is None:
        return  # soft fallback in SAFE sandbox
    engine = (
        GovernanceEngine.shared()
        if hasattr(GovernanceEngine, "shared")
        else GovernanceEngine()
    )
    ok, reason = engine.ensure_allowed(
        action="dashboard.push",
        actor=actor,
        meta={"op": op, "safe": bool(SAFE_MODE)},
        payload_digest=payload_digest,
    )
    if not ok:
        raise HTTPException(
            status_code=403, detail=f"governance denied: {reason or 'not allowed'}"
        )


def _audit(actor: str, action: str, payload: Dict[str, Any]) -> None:
    if audit_append is None:
        return
    try:
        audit_append(
            actor=actor, action=action, ctx={"component": "dashboard"}, payload=payload
        )
    except Exception:
        # Never fail the request on audit persistence errors
        pass


def _validate_widget_against_spec(widget: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Lightweight server-side validation enforcing declared caps in _SPEC.
    """
    wtype = widget.get("type")
    if wtype not in _SPEC["widget_types"]:
        return False, f"unsupported widget type: {wtype!r}"

    spec = _SPEC["widget_types"][wtype]

    title = widget.get("title", "")
    if isinstance(spec.get("title"), dict) and len(str(title)) > spec["title"]["max"]:
        return False, f"title too long (>{spec['title']['max']})"

    if wtype == "kpi":
        # value may be any number; unit length capped
        unit = widget.get("unit", "")
        if len(str(unit)) > spec["unit"]["max"]:
            return False, f"unit too long (>{spec['unit']['max']})"

    elif wtype == "line_chart":
        data = widget.get("data", [])
        if isinstance(data, list) and len(data) > spec["data_max"]:
            return False, f"too many data points (>{spec['data_max']})"
        for key_name in ("xKey", "yKey"):
            k = widget.get(key_name, "")
            if len(str(k)) > spec[key_name]["max"]:
                return False, f"{key_name} too long (>{spec[key_name]['max']})"

    elif wtype == "table":
        cols = widget.get("columns", [])
        rows = widget.get("rows", [])
        if isinstance(cols, list) and len(cols) > spec["columns_max"]:
            return False, f"too many columns (>{spec['columns_max']})"
        if isinstance(rows, list) and len(rows) > spec["rows_max"]:
            return False, f"too many rows (>{spec['rows_max']})"

    elif wtype == "html":
        html = widget.get("html", "")
        if len(str(html)) > spec["html_max"]:
            return False, f"html too large (>{spec['html_max']} chars)"

    return True, ""


# --- Endpoints ----------------------------------------------------------------
@router.get("/spec")
def dashboard_spec(request: Request) -> Dict[str, Any]:
    # include SAFE & storage version for client-side hints
    return {
        **_SPEC,
        "safe_mode": bool(SAFE_MODE),
        "store_version": _store.version,
        **_meta(request),
    }


@router.get("/state")
def dashboard_state(request: Request) -> Dict[str, Any]:
    return {"widgets": _store.widgets, "version": _store.version, **_meta(request)}


@router.get("/vocab")
def dashboard_vocab(request: Request) -> Dict[str, Any]:
    # Return raw vocabulary for clients; server can use typed model internally if needed
    return {**vocabulary_dict(), **_meta(request)}


@router.post("/push")
def dashboard_push(body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    # 1) Parse & basic schema validation
    try:
        pr = PushRequest(**body)
    except Exception as e:
        raise HTTPException(400, f"invalid payload: {e}")

    actor = _actor_from(request)

    # 2) Rate limiting & idempotency (cheap guards first)
    if not push_allowed(actor, 120):
        raise HTTPException(429, "too many dashboard updates; slow down")

    if is_idempotent(pr.idempotency_key):
        # No-op but still respond with current counters
        return {
            "ok": True,
            "version": _store.version,
            "count": len(_store.widgets),
            **_meta(request),
        }

    # 3) Governance check for mutating ops (clear/add/replace/remove)
    #    SAFE mode doesn't skip governance; it just influences policy.
    _governance_gate(
        actor, pr.op, {"has_widget": bool(pr.widget), "widget_id": pr.widget_id}
    )

    changed = False
    new_widget_id: Optional[str] = None

    # 4) Execute operation
    if pr.op == "clear":
        if _store.widgets:
            _store.widgets = []
            _store.version += 1
            _store.record_patch({"op": pr.op, "version": _store.version})
            _store.snapshot()
            changed = True

    elif pr.op in ("add", "replace", "upsert"):
        if pr.widget is None:
            raise HTTPException(400, "widget required")

        # Convert Pydantic model to plain dict
        w: Dict[str, Any] = pr.widget.dict()  # type: ignore

        if not w.get("id"):
            w["id"] = f"w_{uuid4().hex[:10]}"
        new_widget_id = str(w["id"])

        # Enforce spec limits
        ok, err = _validate_widget_against_spec(w)
        if not ok:
            raise HTTPException(400, f"widget invalid: {err}")

        if pr.op == "add":
            if len(_store.widgets) >= MAX_WIDGETS:
                # Simple ring-buffer policy: drop oldest
                _store.widgets.pop(0)
            _store.widgets.append(w)

        elif pr.op == "replace":
            target_id = pr.widget_id or new_widget_id
            if not target_id:
                raise HTTPException(400, "widget_id required for replace")
            replaced = False
            for i, ex in enumerate(list(_store.widgets)):
                if str(ex.get("id")) == str(target_id):
                    _store.widgets[i] = w
                    replaced = True
                    break
            if not replaced:
                _store.widgets.append(w)

        else:  # upsert
            target_id = pr.widget_id or new_widget_id
            replaced = False
            for i, ex in enumerate(list(_store.widgets)):
                if str(ex.get("id")) == str(target_id):
                    _store.widgets[i] = w
                    replaced = True
                    break
            if not replaced:
                if len(_store.widgets) >= MAX_WIDGETS:
                    _store.widgets.pop(0)
                _store.widgets.append(w)

        _store.version += 1
        _store.record_patch(
            {
                "op": pr.op,
                "widget": new_widget_id,
                "type": w.get("type"),
                "version": _store.version,
            }
        )
        _store.snapshot()
        changed = True

    elif pr.op == "remove":
        target_id = pr.widget_id or (pr.widget and pr.widget.dict().get("id"))  # type: ignore
        if not target_id:
            raise HTTPException(400, "widget_id required for remove")
        before = len(_store.widgets)
        _store.widgets = [
            x for x in _store.widgets if str(x.get("id")) != str(target_id)
        ]
        if len(_store.widgets) != before:
            _store.version += 1
            _store.record_patch(
                {"op": pr.op, "widget": str(target_id), "version": _store.version}
            )
            _store.snapshot()
            changed = True

    else:
        raise HTTPException(400, "invalid op")

    # 5) Broadcast + audit on change
    if changed:
        wid = pr.widget_id or new_widget_id or (pr.widget and pr.widget.dict().get("id"))  # type: ignore
        broadcast(
            {
                "type": "dashboard.patch",
                "data": {"op": pr.op, "widget": wid, "version": _store.version},
            }
        )
        _audit(
            actor=actor,
            action="dashboard.push",
            payload={"op": pr.op, "version": _store.version, "widget": wid},
        )

    return {
        "ok": True,
        "version": _store.version,
        "count": len(_store.widgets),
        **_meta(request),
    }
