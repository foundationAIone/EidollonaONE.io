from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Optional
from fastapi import Depends, FastAPI

from security.deps import require_token
from utils.audit import audit_ndjson
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from cluster.cluster_control import (
    quote_job as _quote_job,
    submit_job as _submit_job,
    get_status as _cluster_status,
    cancel_job as _cancel_job,
)

OP = os.getenv("OPERATOR", "programmerONE")
_Optional = Optional
AI_LEARNING_SUMMARY_PATH = Path("outputs/ai_learning_eval/summary.json")

# ---- try real core; otherwise shim ----------------------------------------------------------
try:
    from symbolic_core.context_builder import assemble_se41_context
    from symbolic_core.symbolic_equation import SymbolicEquation41 as _CoreSymbolicEquation41
    from symbolic_core.symbolic_equation import classify_readiness as _core_classify_readiness
    HAVE_CORE = True
    SymbolicEquation41 = _CoreSymbolicEquation41  # type: ignore[assignment]
    classify_readiness = _core_classify_readiness  # type: ignore[assignment]
except Exception:
    HAVE_CORE = False

    def _clamp01(value: float) -> float:
        try:
            value = float(value)
        except Exception:
            return 0.0
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    def assemble_se41_context(
        coherence_hint: float = 0.82,
        risk_hint: float = 0.15,
        uncertainty_hint: float = 0.25,
        mirror_consistency: float = 0.70,
        s_em: float = 0.78,
        t: float = 0.0,
        ethos_hint: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        return {
            "coherence_hint": float(coherence_hint),
            "risk_hint": float(risk_hint),
            "uncertainty_hint": float(uncertainty_hint),
            "mirror": {"consistency": float(mirror_consistency)},
            "substrate": {"S_EM": float(s_em)},
            "ethos_hint": ethos_hint or {},
            "t": float(t) % 1.0,
        }

    def classify_readiness(coherence_value: float, impetus_value: float) -> str:
        coherence_value = _clamp01(coherence_value)
        impetus_value = _clamp01(impetus_value)
        if coherence_value >= 0.85 and impetus_value >= 0.50:
            return "prime_ready"
        if coherence_value >= 0.75:
            return "ready"
        if coherence_value >= 0.60:
            return "warming"
        return "baseline"

    class SymbolicEquation41:
        def __init__(self, default_coherence: float = 0.8) -> None:
            self._coherence = _clamp01(default_coherence)

        def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
            coherence_value = _clamp01(float(ctx.get("coherence_hint", self._coherence)))
            risk_value = _clamp01(float(ctx.get("risk_hint", 0.2)))
            uncertainty_value = _clamp01(float(ctx.get("uncertainty_hint", 0.25)))
            mirror_value = _clamp01(float((ctx.get("mirror", {}) or {}).get("consistency", 0.7)))
            substrate_value = _clamp01(float((ctx.get("substrate", {}) or {}).get("S_EM", 0.78)))
            ethos_value = ctx.get("ethos_hint") or {
                "authenticity": 0.9,
                "integrity": 0.9,
                "responsibility": 0.88,
                "enrichment": 0.9,
            }
            self._coherence = coherence_value
            impetus_value = _clamp01(coherence_value * mirror_value * (1.0 - risk_value))
            return {
                "coherence": coherence_value,
                "impetus": impetus_value,
                "risk": risk_value,
                "uncertainty": uncertainty_value,
                "mirror_consistency": mirror_value,
                "S_EM": substrate_value,
                "ethos": ethos_value,
                "embodiment": {"phase": float(ctx.get("t", 0.0)) % 1.0},
            }

# ---- app, then CORS (order matters) ---------------------------------------------------------
app = FastAPI(title="AlphaTap", version="0.1", docs_url=None, redoc_url=None)

try:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
except Exception:
    CORSMiddleware = None  # Optional for constrained environments

try:
    from observability.otel_boot import init_otel, set_span_attributes
except Exception:
    init_otel = None

    def set_span_attributes(attributes: Optional[Dict[str, Any]] = None) -> None:  # type: ignore[redefinition]
        return None

_OTEL_ENABLED = False
if init_otel is not None:
    try:
        _OTEL_ENABLED = bool(init_otel(app))
    except Exception:
        _OTEL_ENABLED = False

def _span_attrs(**attrs: Any) -> None:
    if not attrs:
        return
    try:
        set_span_attributes(attrs)
    except Exception:
        return

ENGINE = SymbolicEquation41()
CTX: Dict[str, Any] = assemble_se41_context()

try:  # Mount EMP routes under /v1/sim
    from emp.api.routes import router as emp_router

    app.include_router(emp_router, prefix="/v1/sim")
except Exception:
    pass

try:  # Mount EMP Guard routes under /v1/emp-guard
    from emp_guard.api.routes import router as emp_guard_router

    app.include_router(emp_guard_router, prefix="/v1/emp-guard")
except Exception:
    pass
try:  # Mount Security routes under /v1/sec
    from security.api.routes import router as sec_router

    app.include_router(sec_router, prefix="/v1/sec")
except Exception:
    pass

try:  # Mount Internet allowlist routes under /v1/internet
    from internet_access.api.routes import router as internet_router

    app.include_router(internet_router, prefix="/v1/internet")
except Exception:
    pass

try:  # Mount Sovereignty charter routes under /v1/sovereign
    from sovereignty.api.routes import router as sov_router

    app.include_router(sov_router, prefix="/v1/sovereign")
except Exception:
    pass

try:  # Mount Node dialogue routes under /v1/nodes
    from nodes.api.routes import router as node_router

    app.include_router(node_router, prefix="/v1/nodes")
except Exception:
    pass

try:  # Mount Resonance routes under /v1/resonance
    from resonance.api.routes import router as res_router

    app.include_router(res_router, prefix="/v1/resonance")
except Exception:
    pass

try:  # Mount Serplus routes under /v1/ser
    from serplus.api import router as ser_router

    app.include_router(ser_router, prefix="/v1")
except Exception:
    pass

try:  # Mount Black-Scholes analytics under /v1/bs
    from black_scholes.api import router as bs_router

    app.include_router(bs_router, prefix="/v1/bs")
except Exception:
    pass

try:  # Mount enhanced trading options routes under /v1/opt
    from trading_engine.options.api.routes import router as opt_router

    app.include_router(opt_router, prefix="/v1/opt")
except Exception:
    pass

try:  # Mount regime analytics under /v1/regime
    from market_analysis.regime.api.routes import router as regime_router

    app.include_router(regime_router, prefix="/v1/regime")
except Exception:
    pass

try:  # Mount Stewardship routes under /v1/stewardship
    from stewardship.api.routes import router as stew_router

    app.include_router(stew_router, prefix="/v1/stewardship")
except Exception:
    pass

try:  # Mount PQRE routes under /v1/pqre
    from pqre.api.routes import router as pqre_router

    app.include_router(pqre_router, prefix="/v1/pqre")
except Exception:
    pass

try:  # Mount Avatar orchestrator routes under /v1/avatar
    from avatars.orchestrator.api import router as avatar_router

    app.include_router(avatar_router)
except Exception:
    pass

try:  # Mount FanComp Foundation routes under /v1/fancomp
    from fancompfoundation import router as fancomp_router

    app.include_router(fancomp_router)
except Exception:
    pass

try:  # Mount Serve-it routes under /v1/serveit
    from serve_it_app import router as serveit_router

    app.include_router(serveit_router)
except Exception:
    pass

try:  # Mount Trader avatar routes under /v1/trader
    from trading.api.routes import router as trader_router

    app.include_router(trader_router, prefix="/v1")
except Exception:
    pass

try:
    from symbolic_core.se41_service import sovereign_gate as _sov_gate

    @app.post("/v1/sovereign/gate")
    def sovereign_gate_api(payload: Dict[str, Any], token: str = Depends(require_token)):
        signals = dict(payload.get("signals") or {})
        ouro = float(payload.get("ouroboros", 0.0))
        response = _sov_gate(signals, ouro)
        audit_ndjson("sovereign_gate", token=token, signals=signals, ouroboros=ouro, result=response)
        return response
except Exception:
    pass

class ContextIn(BaseModel):
    coherence_hint: Optional[float] = None
    risk_hint: Optional[float] = None
    uncertainty_hint: Optional[float] = None
    mirror_consistency: Optional[float] = None
    s_em: Optional[float] = None
    ethos_hint: Optional[Dict[str, float]] = None
    alpha: Optional[float] = None
    impetus_mode: Optional[str] = None


class JobSpecIn(BaseModel):
    job: str
    provider: str
    resources: dict
    data: dict
    output: dict
    caps: dict
    audit: dict

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": time.time(), "operator": OP, "have_core": HAVE_CORE}

@app.get("/v1/se41/context")
def get_context(_: str = Depends(require_token)):
    return CTX


@app.post("/v1/se41/context")
def set_context(payload: ContextIn, _: str = Depends(require_token)):
    args = {k: v for k, v in payload.dict().items() if v is not None}
    new_ctx = assemble_se41_context(
        coherence_hint=args.get("coherence_hint", CTX["coherence_hint"]),
        risk_hint=args.get("risk_hint", CTX["risk_hint"]),
        uncertainty_hint=args.get("uncertainty_hint", CTX["uncertainty_hint"]),
        mirror_consistency=args.get("mirror_consistency", CTX["mirror"]["consistency"]),
        s_em=args.get("s_em", CTX["substrate"]["S_EM"]),
        ethos_hint=args.get("ethos_hint", CTX.get("ethos_hint", {})),
    )
    if "alpha" in args:
        new_ctx["alpha"] = args["alpha"]
    if "impetus_mode" in args:
        new_ctx["impetus_mode"] = str(args["impetus_mode"]).lower()
    CTX.update(new_ctx)
    return {"ok": True, "context": CTX}


def _normalize_signal(data: Any) -> Dict[str, Any]:
    if hasattr(data, "to_dict"):
        try:
            return data.to_dict()  # type: ignore[return-value]
        except Exception:
            pass
    if hasattr(data, "__dict__"):
        try:
            return dict(data.__dict__)
        except Exception:
            pass
    if isinstance(data, dict):
        return dict(data)
    return {
        "coherence": 0.0,
        "impetus": 0.0,
        "risk": 1.0,
        "uncertainty": 1.0,
        "mirror_consistency": 0.0,
        "S_EM": 0.0,
        "ethos": {},
    }

@app.get("/v1/se41/eval")
def eval_se41(token: str = Depends(require_token)):
    sig_data = _normalize_signal(ENGINE.evaluate(CTX))
    sig_data["readiness"] = classify_readiness(sig_data.get("coherence", 0.0), sig_data.get("impetus", 0.0))
    return sig_data


@app.post("/v1/cluster/quote")
def cluster_quote(payload: JobSpecIn, token: str = Depends(require_token)):
    spec = payload.dict()
    quote = _quote_job(spec)
    audit_ndjson("cluster_quote", token=token, spec=spec)
    _span_attrs(
        eidollona_cluster_provider=spec.get("provider"),
        eidollona_cluster_job=spec.get("job"),
    )
    return {"ok": True, "quote": quote}


@app.post("/v1/cluster/submit")
def cluster_submit(payload: JobSpecIn, token: str = Depends(require_token)):
    spec = payload.dict()
    result = _submit_job(spec)
    audit_ndjson("cluster_submit", token=token, spec=spec, result=result)
    _span_attrs(
        eidollona_cluster_provider=spec.get("provider"),
        eidollona_cluster_job=spec.get("job"),
        eidollona_cluster_job_id=result.get("job_id"),
    )
    return {"ok": True, **result}


@app.get("/v1/cluster/status")
def cluster_status(provider: str, job_id: str, token: str = Depends(require_token)):
    status = _cluster_status(provider, job_id)
    audit_ndjson("cluster_status", token=token, provider=provider, job_id=job_id, status=status)
    _span_attrs(
        eidollona_cluster_provider=provider,
        eidollona_cluster_job_id=job_id,
        eidollona_cluster_state=status.get("status") if isinstance(status, dict) else None,
    )
    return {"ok": True, **status}


@app.post("/v1/cluster/cancel")
def cluster_cancel(provider: str, job_id: str, token: str = Depends(require_token)):
    status = _cancel_job(provider, job_id)
    audit_ndjson("cluster_cancel", token=token, provider=provider, job_id=job_id, status=status)
    _span_attrs(
        eidollona_cluster_provider=provider,
        eidollona_cluster_job_id=job_id,
        eidollona_cluster_state=status.get("status") if isinstance(status, dict) else None,
    )
    return {"ok": True, **status}

@app.get("/v1/audit/tail")
def audit_tail(limit: int = 50, _: str = Depends(require_token)):
    path = os.path.join("logs", "audit.ndjson")
    out = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f.readlines()[-int(abs(limit)):]:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return JSONResponse(out)


def _audit_tail_lines(path: Path, limit: int = 50) -> Iterator[str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()[-int(abs(limit)) :]
    except Exception:
        return iter(())
    filtered = [line.strip() for line in lines if line.strip()]
    return iter(filtered)


def _stream_audit(path: Path, heartbeat_seconds: float = 5.0) -> Iterator[str]:
    last_pos = 0
    last_heartbeat = time.time()
    sent_initial = False
    while True:
        try:
            if path.exists():
                size = path.stat().st_size
                if last_pos > size:
                    last_pos = 0
                if not sent_initial:
                    for line in _audit_tail_lines(path, limit=50):
                        yield f"data: {line}\n\n"
                    last_pos = size
                    sent_initial = True
                else:
                    with path.open("r", encoding="utf-8") as handle:
                        handle.seek(last_pos)
                        for line in handle:
                            stripped = line.strip()
                            if stripped:
                                yield f"data: {stripped}\n\n"
                        last_pos = handle.tell()
            elif not sent_initial:
                yield "data: {\"heartbeat\": true}\n\n"
                sent_initial = True

            now = time.time()
            if now - last_heartbeat >= heartbeat_seconds:
                yield "data: {\"heartbeat\": true}\n\n"
                last_heartbeat = now
            time.sleep(1.0)
        except GeneratorExit:
            break
        except Exception as exc:
            payload = json.dumps({"error": str(exc)}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            time.sleep(2.0)


@app.get("/v1/audit/tail/stream")
def audit_tail_stream(token: str = Depends(require_token)):
    path = Path("logs") / "audit.ndjson"
    audit_ndjson("audit_stream_open", token=token, exists=path.exists())
    return StreamingResponse(_stream_audit(path), media_type="text/event-stream")


@app.get("/v1/status/summary")
def status_summary(token: str = Depends(require_token)):
    sig = _normalize_signal(ENGINE.evaluate(CTX))
    coherence_value = float(sig.get("coherence", 0.0))
    risk_value = float(sig.get("risk", 1.0))
    impetus_value = float(sig.get("impetus", 0.0))
    gate = "ALLOW" if (coherence_value >= 0.75 and risk_value <= 0.20) else (
        "REVIEW" if (coherence_value >= 0.60 and risk_value <= 0.35) else "HOLD"
    )
    audit_ndjson("status_summary", token=token, gate=gate, signals=sig)
    _span_attrs(
        eidollona_gate=gate,
        eidollona_readiness=classify_readiness(coherence_value, impetus_value),
        eidollona_coherence=coherence_value,
        eidollona_risk=risk_value,
    )
    return {"readiness": classify_readiness(coherence_value, impetus_value), "gate": gate, "signals": sig}


def _load_ai_learning_summary() -> Optional[Dict[str, Any]]:
    if not AI_LEARNING_SUMMARY_PATH.exists():
        return None
    try:
        with AI_LEARNING_SUMMARY_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


@app.get("/v1/ai-learning/eval-status")
def ai_learning_eval_status(token: str = Depends(require_token)):
    summary = _load_ai_learning_summary()
    if summary is None:
        audit_ndjson("ai_learning_eval_status", token=token, available=False)
        return JSONResponse(
            {"available": False, "detail": "No evaluation summary present."},
            status_code=404,
        )

    aggregate_thresholds = summary.get("aggregate_thresholds", {}) or {}
    passed_cases = int(summary.get("passed_cases", 0))
    pass_rate = float(summary.get("pass_rate", 0.0))
    minimum_cases = int(aggregate_thresholds.get("minimum_cases_passed", 0))
    minimum_pass_rate = float(aggregate_thresholds.get("minimum_pass_rate", 0.0))

    response = {
        "available": True,
        "passed": bool(passed_cases >= minimum_cases and pass_rate >= minimum_pass_rate),
        "total_cases": summary.get("total_cases"),
        "passed_cases": passed_cases,
        "pass_rate": pass_rate,
        "per_metric": summary.get("per_metric", {}),
        "metric_thresholds": summary.get("metric_thresholds", {}),
        "aggregate_thresholds": aggregate_thresholds,
        "completed_at": summary.get("completed_at"),
        "started_at": summary.get("started_at"),
    }
    audit_ndjson("ai_learning_eval_status", token=token, available=True, summary=response)
    return response

@app.get("/v1/next")
def next_action(token: str = Depends(require_token)):
    sig = _normalize_signal(ENGINE.evaluate(CTX))
    coherence_value = float(sig.get("coherence", 0.0))
    risk_value = float(sig.get("risk", 1.0))
    impetus_value = float(sig.get("impetus", 0.0))
    readiness = classify_readiness(coherence_value, impetus_value)

    if coherence_value >= 0.75 and risk_value <= 0.20:
        gate = "ALLOW"
        next_cmd = (
            "powershell -NoLogo -NoProfile -Command "
            "\"$env:ALPHATAP_BASE='http://127.0.0.1:8802'; "
            "$env:ALPHATAP_TOKEN='dev-token'; "
            "& '.\\.alpha_env\\Scripts\\python.exe' '.\\scripts\\paper_orchestrator.py'\""
        )
        reason = "Gate=ALLOW (paper). Run a short, audited dry-run loop."
    elif coherence_value >= 0.60 and risk_value <= 0.35:
        gate = "REVIEW"
        next_cmd = (
            "powershell -NoLogo -NoProfile -Command "
            "\"& '.\\.alpha_env\\Scripts\\python.exe' '.\\scripts\\dry_run_plan.py'\""
        )
        reason = "Gate=REVIEW. Plan-only; no execution."
    else:
        gate = "HOLD"
        next_cmd = "powershell -NoLogo -NoProfile -Command \"Write-Host 'HOLD: lower risk / raise coherence'\""
        reason = "Gate=HOLD. Improve signals before acting."

    response = {"readiness": readiness, "gate": gate, "next_command": next_cmd, "reason": reason, "signals": sig}
    audit_ndjson("next_preview", token=token, **response)
    _span_attrs(eidollona_gate=gate, eidollona_readiness=readiness)
    return response


@app.post("/v1/next/run")
def next_run(token: str = Depends(require_token)):
    sig = _normalize_signal(ENGINE.evaluate(CTX))
    coherence_value = float(sig.get("coherence", 0.0))
    risk_value = float(sig.get("risk", 1.0))
    impetus_value = float(sig.get("impetus", 0.0))
    readiness = classify_readiness(coherence_value, impetus_value)

    if not (coherence_value >= 0.75 and risk_value <= 0.20):
        gate = "REVIEW" if (coherence_value >= 0.60 and risk_value <= 0.35) else "HOLD"
        result = {"ok": False, "readiness": readiness, "gate": gate, "reason": "Gate not ALLOW", "signals": sig}
        audit_ndjson("next_run_blocked", token=token, **result)
        return result

    env = os.environ.copy()
    env["ALPHATAP_BASE"] = "http://127.0.0.1:8802"
    env["ALPHATAP_TOKEN"] = os.getenv("ALPHATAP_TOKEN", "dev-token")
    cmd = [sys.executable, os.path.join(".", "scripts", "paper_orchestrator.py")]

    try:
        proc = subprocess.run(cmd, cwd=os.getcwd(), env=env, capture_output=True, text=True, timeout=60)
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "readiness": readiness, "gate": "ALLOW"}
        audit_ndjson("next_run_error", token=token, **result)
        return result

    tail = (proc.stdout or "").splitlines()[-8:]
    result = {
        "ok": proc.returncode == 0,
        "readiness": readiness,
        "gate": "ALLOW",
        "stdout_tail": tail,
        "stderr": proc.stderr,
    }
    audit_ndjson("next_run", token=token, **result)
    _span_attrs(eidollona_gate="ALLOW", eidollona_next_ok=result.get("ok", False))
    return result
