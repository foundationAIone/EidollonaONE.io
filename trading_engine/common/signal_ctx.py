from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

try:
    import httpx
except Exception:  # pragma: no cover - optional dependency on runtime
    httpx = None  # type: ignore

try:
    from utils.audit import audit_ndjson as audit
except Exception:  # pragma: no cover - development fallback
    def audit(event: str, **payload: Any) -> None:
        return None


_BASE_URL = os.getenv("ALPHATAP_BASE", "http://127.0.0.1:8802")
_TOKEN = os.getenv("ALPHATAP_TOKEN", "dev-token")
_TIMEOUT = float(os.getenv("TRADING_SIGNAL_TIMEOUT", "3.0"))

_STATUS_CACHE: Dict[str, Any] = {}
_HMM_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0, "payload": None}
_PQRE_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}
_RETURNS_CACHE: Dict[str, Any] = {"data": [], "ts": 0.0, "window": None}


def _request(method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if httpx is None:
        return None
    url = f"{_BASE_URL}{path}"
    params = {"token": _TOKEN}
    try:
        if method == "GET":
            response = httpx.get(url, params=params, timeout=_TIMEOUT)
        else:
            response = httpx.post(url, params=params, json=json_body or {}, timeout=_TIMEOUT)
        if response.status_code >= 400:
            return None
        return response.json()
    except Exception:
        return None


def fetch_status(force: bool = False) -> Dict[str, Any]:
    if not force and _STATUS_CACHE:
        age = time.time() - float(_STATUS_CACHE.get("ts", 0.0))
        if age < 5.0:
            return _STATUS_CACHE.get("data", {})
    data = _request("GET", "/v1/status/summary")
    if not isinstance(data, dict):
        return {"gate": "HOLD", "signals": {}, "ts": None}
    payload = {
        "gate": data.get("gate", "HOLD"),
        "signals": data.get("signals") or {},
        "ts": data.get("ts"),
    }
    _STATUS_CACHE["data"] = payload
    _STATUS_CACHE["ts"] = time.time()
    audit("signal_status_fetch", gate=payload["gate"], ok=True)
    return payload


def fetch_pqre(signals: Optional[Dict[str, Any]] = None, features: Optional[Dict[str, float]] = None, force: bool = False) -> Dict[str, Any]:
    if not force and _PQRE_CACHE.get("data"):
        age = time.time() - float(_PQRE_CACHE.get("ts", 0.0))
        if age < 5.0:
            return _PQRE_CACHE.get("data", {})
    payload = {
        "signals": signals
        or {
            "coherence": 0.78,
            "impetus": 0.55,
            "risk": 0.22,
            "uncertainty": 0.28,
            "mirror_consistency": 0.71,
            "S_EM": 0.76,
            "ethos": {
                "authenticity": 0.88,
                "integrity": 0.89,
                "responsibility": 0.86,
                "enrichment": 0.87,
            },
        },
        "features": features or {"sharpness": 0.65, "noise": 0.25},
    }
    data = _request("POST", "/v1/pqre/render", payload)
    if not isinstance(data, dict):
        return {"field": {}, "strategies": [], "params": {}, "rec": "neutral"}
    _PQRE_CACHE["data"] = data
    _PQRE_CACHE["ts"] = time.time()
    audit("signal_pqre_fetch", ok=True, params=data.get("field", {}).get("params"))
    return data


def fetch_hmm(returns: Optional[Dict[str, Any]] = None, force: bool = False) -> Dict[str, Any]:
    cached_payload = _HMM_CACHE.get("payload")
    if not force and returns is None and _HMM_CACHE.get("data"):
        age = time.time() - float(_HMM_CACHE.get("ts", 0.0))
        if age < 30.0:
            return _HMM_CACHE.get("data", {})
    data = _request("POST", "/v1/regime/hmm", returns or cached_payload or {})
    if not isinstance(data, dict):
        return {"regime": 0, "confidence": 0.0}
    _HMM_CACHE["data"] = data
    _HMM_CACHE["ts"] = time.time()
    _HMM_CACHE["payload"] = returns or cached_payload
    audit("signal_hmm_fetch", ok=True, regime=data.get("regime"))
    return data


def fetch_emh(horizon: int = 252) -> Dict[str, Any]:
    data = _request("GET", f"/v1/regime/emh/runs?horizon={horizon}")
    if not isinstance(data, dict):
        return {"p_value": 1.0, "reject": False}
    audit("signal_emh_fetch", ok=True, reject=data.get("reject", False))
    return {
        "p_value": float(data.get("p_value", 1.0)),
        "reject": bool(data.get("reject", False)),
    }


def se41_gate(signals: Optional[Dict[str, Any]] = None, ouroboros: float = 0.0) -> Dict[str, Any]:
    payload = {"signals": signals or {}, "ouroboros": float(ouroboros)}
    data = _request("POST", "/v1/sovereign/gate", payload)
    if not isinstance(data, dict):
        return {"gate": "HOLD", "sovereign_gate": "HOLD"}
    gate = data.get("gate") or data.get("status") or "HOLD"
    sov_gate = data.get("sovereign_gate") or gate
    audit("signal_se41_gate", gate=gate, sovereign_gate=sov_gate)
    return {"gate": gate, "sovereign_gate": sov_gate}


def dispersion_prob(pqre_render: Optional[Dict[str, Any]]) -> float:
    if not pqre_render:
        return 0.0
    params = pqre_render.get("field", {}).get("params", {})
    sharpness = float(params.get("sharpness", 0.0))
    noise = float(params.get("noise", 0.0))
    smoothness = float(params.get("smoothness", 0.0))
    val = 0.45 * sharpness + 0.35 * (1.0 - noise) + 0.20 * smoothness
    return max(0.0, min(1.0, val))


def rolling_returns(window: int = 256, force: bool = False) -> List[float]:
    cached = _RETURNS_CACHE
    if (
        not force
        and cached.get("data")
        and cached.get("window") == window
        and time.time() - float(cached.get("ts", 0.0)) < 60.0
    ):
        return list(cached.get("data", []))
    data: Any = _request("GET", f"/v1/market/returns?window={int(window)}")
    values: List[float]
    if isinstance(data, dict):
        payload = data.get("returns")
        if isinstance(payload, list):
            values = [float(v) for v in payload if isinstance(v, (int, float))]
        else:
            values = []
    elif isinstance(data, list):
        values = [float(v) for v in data if isinstance(v, (int, float))]
    else:
        values = []
    _RETURNS_CACHE.update({"data": values, "ts": time.time(), "window": window})
    audit("signal_returns_fetch", ok=bool(values), count=len(values))
    return values


def change_point_prob(returns: Optional[List[float]] = None, hazard: float = 0.01) -> Dict[str, Any]:
    payload = {"returns": returns or rolling_returns(), "hazard": float(hazard)}
    data = _request("POST", "/v1/regime/bocpd", payload)
    if not isinstance(data, dict):
        return {"p_change": 0.0, "run_length": 0}
    audit("signal_bocpd_fetch", ok=True, p_change=data.get("p_change"))
    return {
        "p_change": float(data.get("p_change", 0.0)),
        "run_length": int(data.get("run_length", 0)),
    }


def ms_vol(returns: Optional[List[float]] = None, k: int = 2) -> Dict[str, Any]:
    payload = {"returns": returns or rolling_returns(), "k": int(k)}
    data = _request("POST", "/v1/regime/msgarch", payload)
    if not isinstance(data, dict):
        return {"sigma": 0.0, "regime_probs": []}
    audit("signal_msgarch_fetch", ok=True, sigma=data.get("sigma"))
    return {
        "sigma": float(data.get("sigma", 0.0)),
        "regime_probs": list(data.get("regime_probs", [])),
    }


__all__ = [
    "fetch_status",
    "fetch_pqre",
    "fetch_hmm",
    "fetch_emh",
    "se41_gate",
    "dispersion_prob",
    "rolling_returns",
    "change_point_prob",
    "ms_vol",
]
