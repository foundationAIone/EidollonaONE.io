from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, cast

from utils.audit import audit_ndjson
from symbolic_core.symbolic_equation_master import MasterStateSnapshot

try:
    from symbolic_core.se_loader import SE42Loader
except Exception:  # pragma: no cover - loader optional in tooling
    SE42Loader = None  # type: ignore
_SE42_LOADER: Any = None
if SE42Loader is not None:
    try:
        _SE42_LOADER = SE42Loader()
    except Exception as exc:  # pragma: no cover - log and continue with SE4.1
        audit_ndjson("se42_loader_error", source="master_boot", error=str(exc))
        _SE42_LOADER = None


_LAST_SIGNALS: Dict[str, Any] = {}



@dataclass
class BootPolicy:
    min_coherence: float = 0.6
    min_substrate: float = 0.6
    max_risk: float = 0.6
    max_uncertainty: float = 0.7
    warn_only: bool = False

    @classmethod
    def from_env(cls) -> "BootPolicy":
        import os

        def _f(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, default))
            except Exception:
                return float(default)

        def _b(name: str, default: bool) -> bool:
            v = str(os.getenv(name, "1" if default else "0")).strip()
            return v not in {"", "0", "false", "False", "no", "No"}

        return cls(
            min_coherence=_f("BOOT_MIN_COHERENCE", 0.6),
            min_substrate=_f("BOOT_MIN_SUBSTRATE", 0.6),
            max_risk=_f("BOOT_MAX_RISK", 0.6),
            max_uncertainty=_f("BOOT_MAX_UNCERTAINTY", 0.7),
            warn_only=_b("BOOT_WARN_ONLY", False),
        )

    def evaluate(self, snap: MasterStateSnapshot) -> Tuple[bool, List[str]]:
        advisories: List[str] = []
        if snap.coherence < self.min_coherence:
            advisories.append("low_coherence")
        if snap.substrate_readiness < self.min_substrate:
            advisories.append("low_substrate")
        if snap.risk > self.max_risk:
            advisories.append("high_risk")
        if snap.uncertainty > self.max_uncertainty:
            advisories.append("high_uncertainty")
        ok = len(advisories) == 0
        return ok, advisories


def _gate_logger():
    class _L:
        def write(self, obj: Dict[str, Any]) -> None:
            audit_ndjson("boot_gate", **obj)

    return _L()


@dataclass
class BootReport:
    ok: bool
    advisories: List[str]
    details: Dict[str, Any]
    gate: str
    lotus_readiness: str

    def summary(self) -> Dict[str, Any]:
        mk = get_master_key()
        fingerprint = getattr(mk, "fingerprint", "")
        safe_fp = fingerprint[:12] if isinstance(fingerprint, str) else ""
        return {
            "ok": self.ok,
            "fingerprint": safe_fp,
            "gate": self.gate,
            "lotus_readiness": self.lotus_readiness,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {"summary": self.summary(), "details": self.details}


def get_master_key():
    class _MK:
        fingerprint = "ABCDEF0123456789"
        capabilities: Dict[str, Any] = {}

    return _MK()


def evaluate_master_state(context: Dict[str, Any] | None = None) -> MasterStateSnapshot:
    ctx = context or {}
    metrics: Dict[str, Any] | None = None

    global _LAST_SIGNALS

    if _SE42_LOADER is not None:
        try:
            signals = _SE42_LOADER.evaluate(ctx)
            metrics_candidate = signals.to_dict()
            metrics = dict(metrics_candidate) if isinstance(metrics_candidate, dict) else dict(metrics_candidate or {})
            base12 = metrics.get("base12", {}) or {}
            ethos = metrics.get("ethos") if isinstance(metrics.get("ethos"), dict) else {}
            ethos_vals = []
            if isinstance(ethos, dict):
                try:
                    ethos_vals = [float(v) for v in ethos.values()]
                except Exception:
                    ethos_vals = []
            metrics["ethos_min"] = min(ethos_vals) if ethos_vals else 0.0
            _LAST_SIGNALS = dict(metrics)
            audit_ndjson(
                "se42_boot_metrics",
                version=metrics.get("version"),
                readiness=metrics.get("readiness"),
                gate=metrics.get("gate_state"),
                base12_trace=base12.get("trace"),
                context_label=base12.get("label"),
            )
        except Exception as exc:  # pragma: no cover
            audit_ndjson("se42_boot_fallback", error=str(exc))
            metrics = None

    if metrics is None:  # Fallback to SE4.1 heuristics for legacy shells
        coh = float(ctx.get("coherence_hint", 0.8))
        s_em = float((ctx.get("substrate", {}) or {}).get("S_EM", 0.8))
        risk = float(ctx.get("risk_hint", 0.2))
        unc = float(ctx.get("uncertainty_hint", 0.25))
        metrics = {
            "version": "4.1.0",
            "coherence": coh,
            "impetus": max(0.0, min(1.0, coh * (1.0 - risk))),
            "risk": risk,
            "uncertainty": unc,
            "mirror_consistency": 0.75,
            "substrate": s_em,
            "ethos_min": 0.8,
            "base12": {"index": 0, "label": "Lotus-00", "trace": "0.000"},
        }
        _LAST_SIGNALS = dict(metrics)
        audit_ndjson("se41_boot_metrics", coherence=coh, substrate=s_em, risk=risk, uncertainty=unc)

    metrics = cast(Dict[str, Any], metrics)
    base12 = metrics.get("base12", {}) or {}
    if not isinstance(base12, dict):
        base12 = {}
    substrate_val = metrics.get("substrate", metrics.get("substrate_readiness", 0.0))
    return MasterStateSnapshot(
        coherence=float(metrics.get("coherence", 0.0)),
        impetus=float(metrics.get("impetus", 0.0)),
        risk=float(metrics.get("risk", 1.0)),
        uncertainty=float(metrics.get("uncertainty", 1.0)),
        mirror_consistency=float(metrics.get("mirror_consistency", 0.0)),
    substrate_readiness=float(substrate_val if substrate_val is not None else 0.0),
        ethos_min=float(metrics.get("ethos_min", 0.0)),
        embodiment_phase=float(base12.get("index", 0.0)),
        delta_coherence=0.0,
        delta_impetus=0.0,
        delta_risk=0.0,
        timestamp=float(metrics.get("timestamp", 0.0)),
        explain=base12.get("label", "boot_eval"),
    )


def boot_system(ctx: Dict[str, Any] | None = None, policy: BootPolicy | None = None) -> Any:
    pol = policy or BootPolicy()
    snap = evaluate_master_state(ctx or {})
    ok, advisories = pol.evaluate(snap)
    # Tests expect HOLD for non-ok decisions (even when warn_only=True)
    se42_meta = {
        "version": _LAST_SIGNALS.get("version"),
        "lotus_readiness": _LAST_SIGNALS.get("readiness", "baseline"),
        "gate": _LAST_SIGNALS.get("gate_state", "HOLD"),
        "base12": {
            "index": (_LAST_SIGNALS.get("base12") or {}).get("index"),
            "label": (_LAST_SIGNALS.get("base12") or {}).get("label"),
            "trace": (_LAST_SIGNALS.get("base12") or {}).get("trace"),
        },
    }
    gate_state = se42_meta.get("gate")
    if gate_state not in {"ALLOW", "HOLD"}:
        gate_state = "ALLOW" if ok else "HOLD"
    se42_meta["gate"] = gate_state
    decision = "ALLOW" if ok else "HOLD"
    evt = {
        "decision": decision,
        "snapshot": {
            "coherence": snap.coherence,
            "impetus": snap.impetus,
            "risk": snap.risk,
            "uncertainty": snap.uncertainty,
            "substrate_readiness": snap.substrate_readiness,
        },
        "policy": {
            "min_coherence": pol.min_coherence,
            "min_substrate": pol.min_substrate,
            "max_risk": pol.max_risk,
            "max_uncertainty": pol.max_uncertainty,
            "warn_only": pol.warn_only,
        },
        "advisories": advisories,
        "reason": advisories[0] if advisories else "",
        "se42": se42_meta,
    }
    _gate_logger().write(evt)
    # Maintain audit
    audit_ndjson("boot_system", ok=ok, gate=se42_meta["gate"], lotus_readiness=se42_meta["lotus_readiness"], **evt)
    return BootReport(
        ok=ok,
        advisories=advisories,
        details=evt,
        gate=se42_meta["gate"],
        lotus_readiness=se42_meta["lotus_readiness"],
    )
