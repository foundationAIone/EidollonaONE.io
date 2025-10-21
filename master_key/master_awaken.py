from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, Optional

from symbolic_core.audit_bridge import audit_ndjson

try:  # Prefer unified loader extension (SE4.3→SE4.2 fallback)
    from symbolic_core.se_loader_ext import load_se_engine
except Exception:  # pragma: no cover - optional in dev shells
    load_se_engine = None  # type: ignore

try:  # Secondary fallback: SE4.2 loader
    from symbolic_core.se_loader import SE42Loader
except Exception:  # pragma: no cover - fallback for dev shells
    SE42Loader = None  # type: ignore

try:  # Fallback engine if SE4.2 loader unavailable
    from symbolic_core.symbolic_equation import SymbolicEquation41
except Exception:  # pragma: no cover
    SymbolicEquation41 = None  # type: ignore

try:  # Master key accessor for secure fingerprints
    from .master_boot import get_master_key
except Exception:  # pragma: no cover - defensive fallback
    def get_master_key() -> Any:  # type: ignore
        return {"fingerprint": "unknown", "capabilities": {}}


@dataclass
class Stability:
    """Human-friendly stability snapshot for HUDs and APIs."""

    readiness: str
    lotus_readiness: str
    gate_state: str
    base12_trace: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AwakeningReport:
    """Structured payload mirroring legacy awaken_consciousness output."""

    version: str
    readiness: str
    lotus_readiness: str
    gate_state: str
    metrics: Dict[str, Any]
    stability: Stability
    master_key: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        payload = dict(self.metrics)
        payload.update(
            {
                "version": self.version,
                "readiness": self.readiness,
                "lotus_readiness": self.lotus_readiness,
                "gate_state": self.gate_state,
                "base12": self.metrics.get("base12", {}),
                "master_key": dict(self.master_key),
                "stability": self.stability.to_dict(),
            }
        )
        # Preserve legacy flattened keys for compatibility
        payload.setdefault("coherence", self.metrics.get("coherence"))
        payload.setdefault("impetus", self.metrics.get("impetus"))
        payload.setdefault("risk", self.metrics.get("risk"))
        payload.setdefault("uncertainty", self.metrics.get("uncertainty"))
        payload.setdefault("substrate", self.metrics.get("substrate"))
        payload.setdefault("mirror", self.metrics.get("mirror_consistency"))
        payload.setdefault("ethos_min", self.metrics.get("ethos_min"))
        return payload


_SE42_LOADER: Optional[Any] = None
_SE42_LOADER_FAILED = False


def _get_se42_loader() -> Optional[Any]:
    global _SE42_LOADER, _SE42_LOADER_FAILED
    if _SE42_LOADER is not None:
        return _SE42_LOADER
    if _SE42_LOADER_FAILED or SE42Loader is None:
        return None
    try:
        _SE42_LOADER = SE42Loader()
    except Exception as exc:  # pragma: no cover - log and fall back to SE41
        audit_ndjson("se42_loader_error", source="master_awaken", error=str(exc))
        _SE42_LOADER = None
        _SE42_LOADER_FAILED = True
    return _SE42_LOADER


def _compat_readiness(lotus_readiness: str) -> str:
    mapping = {
        "lotus-prime": "prime_ready",
        "lotus-ready": "ready",
        "lotus-warming": "warming",
    }
    return mapping.get(str(lotus_readiness or ""), "baseline")


def _ethos_min(metrics: Dict[str, Any]) -> float:
    ethos = metrics.get("ethos") or {}
    try:
        values = [float(v) for v in ethos.values()]
    except Exception:
        values = []
    if not values:
        return 0.0
    return min(values)


def _mk_summary() -> Dict[str, Any]:
    try:
        mk = get_master_key()
    except Exception:  # pragma: no cover - defensive
        return {"fingerprint": None, "capabilities": {}}
    fingerprint = getattr(mk, "fingerprint", None)
    if isinstance(fingerprint, str):
        safe_fp = fingerprint[:12] + ("…" if len(fingerprint) > 12 else "")
    elif isinstance(fingerprint, (bytes, bytearray)):
        decoded = fingerprint.decode("utf-8", "ignore")
        safe_fp = decoded[:12] + ("…" if len(decoded) > 12 else "")
    else:
        safe_fp = None
    capabilities = getattr(mk, "capabilities", {})
    if not isinstance(capabilities, dict):
        capabilities = {}
    return {"fingerprint": safe_fp, "capabilities": capabilities}


def _signals_to_metrics(signals: Any) -> Dict[str, Any]:
    if signals is None:
        return {}
    mapping: Optional[Dict[Any, Any]] = None
    if hasattr(signals, "to_dict"):
        try:
            candidate = signals.to_dict()
        except Exception:
            candidate = None
        if isinstance(candidate, dict):
            mapping = candidate
    if mapping is None and is_dataclass(signals) and not isinstance(signals, type):
        try:
            mapping = asdict(signals)
        except Exception:
            mapping = None
    if mapping is None and isinstance(signals, dict):
        mapping = signals
    if mapping is None and hasattr(signals, "__dict__"):
        try:
            mapping = dict(vars(signals))
        except Exception:
            mapping = None
    if not mapping:
        return {}
    normalized: Dict[str, Any] = {}
    for key, value in mapping.items():
        normalized[str(key)] = value
    return normalized


def _default_base12() -> Dict[str, Any]:
    return {"vector": [0.0] * 12, "index": 0, "label": "Lotus-00", "trace": "0.000"}


def _se41_awaken(iterations: int, ctx: Dict[str, Any]) -> Dict[str, Any]:
    if SymbolicEquation41 is None:
        audit_ndjson("awaken_consciousness_error", error="No symbolic engine available")
        return {
            "version": "unknown",
            "readiness": "baseline",
            "lotus_readiness": "baseline",
            "gate_state": "HOLD",
            "metrics": {},
            "stability": Stability("baseline", "baseline", "HOLD", "0.000").to_dict(),
            "master_key": _mk_summary(),
        }
    eq = SymbolicEquation41()
    last: Dict[str, Any] = {}
    for _ in range(max(1, int(iterations))):
        result = eq.evaluate(ctx)
        payload = _signals_to_metrics(result)
        if payload:
            last = payload.copy()
    metrics = dict(last)
    metrics.setdefault("version", "4.1.0")
    metrics.setdefault("base12", _default_base12())
    metrics["ethos_min"] = _ethos_min(metrics)
    readiness = "baseline"
    report = AwakeningReport(
        version=str(metrics.get("version", "4.1.0")),
        readiness=readiness,
        lotus_readiness="baseline",
        gate_state="HOLD",
        metrics=metrics,
        stability=Stability(readiness, "baseline", "HOLD", "0.000"),
        master_key=_mk_summary(),
    )
    audit_ndjson("awaken_consciousness", readiness=report.readiness, version=report.version, gate=report.gate_state)
    return report.to_dict()


def awaken_consciousness(iterations: int, context: Dict[str, Any]) -> Dict[str, Any]:
    ctx = dict(context or {})
    steps = max(1, int(iterations or 1))

    signals: Any = None
    source: Optional[str] = None

    if load_se_engine is not None:
        try:
            signals = load_se_engine(context=ctx, iterations=steps)
        except TypeError:
            # Legacy signature without kwargs support
            try:
                signals = load_se_engine()  # type: ignore[misc]
            except Exception as exc:  # pragma: no cover
                audit_ndjson("awaken_loader_error", error=str(exc))
                signals = None
        except Exception as exc:  # pragma: no cover
            audit_ndjson("awaken_loader_error", error=str(exc))
            signals = None
        if signals is not None:
            version_hint = str(getattr(signals, "version", ""))
            if version_hint.startswith("4.3"):
                source = "se43"

    if signals is None:
        loader = _get_se42_loader()
        if loader is not None:
            try:
                signals = loader.evaluate(ctx)
                source = "se42"
            except Exception as exc:  # pragma: no cover
                audit_ndjson("se42_awaken_fallback", error=str(exc))
                signals = None

    if signals is None:
        return _se41_awaken(steps, ctx)

    metrics = _signals_to_metrics(signals)
    metrics.setdefault("version", getattr(signals, "version", "4.x"))
    metrics.setdefault("coherence", getattr(signals, "coherence", None))
    metrics.setdefault("impetus", getattr(signals, "impetus", None))
    metrics.setdefault("risk", getattr(signals, "risk", None))
    metrics.setdefault("uncertainty", getattr(signals, "uncertainty", None))
    metrics.setdefault("mirror_consistency", getattr(signals, "mirror_consistency", None))
    substrate_val = metrics.get("substrate", getattr(signals, "substrate", getattr(signals, "substrate_readiness", 0.0)))
    metrics["substrate"] = substrate_val if substrate_val is not None else 0.0
    metrics.setdefault("base12", metrics.get("base12") or getattr(signals, "base12", _default_base12()))
    metrics.setdefault("gate_state", getattr(signals, "gate_state", "HOLD"))
    metrics.setdefault("readiness", getattr(signals, "readiness", "baseline"))
    metrics.setdefault("wings", getattr(signals, "wings", None))
    metrics.setdefault("reality_alignment", getattr(signals, "reality_alignment", None))
    metrics.setdefault("gamma", getattr(signals, "gamma", None))
    metrics.setdefault("gate12", getattr(signals, "gate12", None))
    metrics.setdefault("gate12_array", getattr(signals, "gate12_array", None))
    metrics["ethos_min"] = _ethos_min(metrics)

    version = str(metrics.get("version", ""))
    base12 = metrics.get("base12") or {}

    if source == "se43" or version.startswith("4.3") or metrics.get("wings") is not None:
        readiness = str(metrics.get("readiness", "baseline"))
        gate_state = str(metrics.get("gate_state", "HOLD"))
        report = AwakeningReport(
            version=version or "4.3.0",
            readiness=readiness,
            lotus_readiness=readiness,
            gate_state=gate_state,
            metrics=metrics,
            stability=Stability(
                readiness=readiness,
                lotus_readiness=readiness,
                gate_state=gate_state,
                base12_trace=str((base12 or {}).get("trace", "0.000")),
            ),
            master_key=_mk_summary(),
        )
        audit_ndjson(
            "awaken_consciousness",
            version=report.version,
            readiness=report.readiness,
            lotus_readiness=report.lotus_readiness,
            gate=report.gate_state,
            wings=metrics.get("wings"),
            reality_alignment=metrics.get("reality_alignment"),
            master_key=report.master_key.get("fingerprint"),
        )
        return report.to_dict()

    lotus_native = str(metrics.get("readiness", "baseline"))
    readiness = _compat_readiness(lotus_native)
    gate_state = str(metrics.get("gate_state", "HOLD"))
    report = AwakeningReport(
        version=version or "4.2.0",
        readiness=readiness,
        lotus_readiness=lotus_native,
        gate_state=gate_state,
        metrics=metrics,
        stability=Stability(
            readiness=readiness,
            lotus_readiness=lotus_native,
            gate_state=gate_state,
            base12_trace=str((base12 or {}).get("trace", "0.000")),
        ),
        master_key=_mk_summary(),
    )
    audit_ndjson(
        "awaken_consciousness",
        version=report.version,
        readiness=report.readiness,
        lotus_readiness=report.lotus_readiness,
        gate=report.gate_state,
        master_key=report.master_key.get("fingerprint"),
    )
    return report.to_dict()
