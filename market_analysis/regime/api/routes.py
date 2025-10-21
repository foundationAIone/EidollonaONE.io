from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from market_analysis.regime.bocpd import bocpd_posterior
from market_analysis.regime.emh_tests import runs_test
from market_analysis.regime.ms_garch import fit_ms_garch, forecast_vol
from market_analysis.regime.hmm_regime import SimpleHMM
from security.deps import require_token
from utils.audit import audit_ndjson

router = APIRouter()
_model = SimpleHMM()


class ReturnsIn(BaseModel):
    returns: List[float] = []


class BocpdIn(ReturnsIn):
    hazard: float = 0.01


class MSGARCHIn(ReturnsIn):
    k: int = 2


@router.post("/hmm")
def api_hmm(body: ReturnsIn, _: str = Depends(require_token)) -> Dict[str, object]:
    _model.fit(body.returns, iters=5)
    regime = _model.infer(body.returns)
    audit_ndjson("regime_hmm", size=len(body.returns), out=regime)
    return {"ok": True, "regime": regime}


@router.post("/bocpd")
def api_bocpd(body: BocpdIn, _: str = Depends(require_token)) -> Dict[str, object]:
    result = bocpd_posterior(body.returns, hazard=body.hazard)
    audit_ndjson("regime_bocpd", size=len(body.returns), out=result)
    return {"ok": True, **result}


@router.post("/msgarch")
def api_msgarch(body: MSGARCHIn, _: str = Depends(require_token)) -> Dict[str, object]:
    model = fit_ms_garch(body.returns, k=body.k)
    sigma_next = forecast_vol(model)
    payload = {
        "sigma": sigma_next,
        "regime_probs": model.regime_probs,
        "stub": model.stub,
        "meta": model.meta,
    }
    audit_ndjson("regime_msgarch", size=len(body.returns), out=payload)
    return {"ok": True, **payload}


@router.post("/emh/runs")
def api_runs(body: ReturnsIn, _: str = Depends(require_token)) -> Dict[str, object]:
    result = runs_test(body.returns)
    audit_ndjson("emh_runs", size=len(body.returns), out=result)
    return {"ok": True, "runs_test": result}


__all__ = ["router"]
