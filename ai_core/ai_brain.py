"""Minimal AI Brain orchestrator for SE4.3 Wings/Aletheia bring-up."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from symbolic_core.se_loader_ext import load_se_engine

AUDIT_PATH = Path("logs/audit.ndjson")
DEFAULT_CFG_PATH = Path("config/se43.yml")


def _load_cfg(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.loads(json.dumps(_yaml_like_to_dict(handle.read())))


def _yaml_like_to_dict(content: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    current: Dict[str, Any] = data
    stack: list[tuple[int, Dict[str, Any]]] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip("\"')")

        while stack and indent <= stack[-1][0]:
            stack.pop()
            current = stack[-1][1] if stack else data

        if value:
            current[key] = _parse_value(value)
        else:
            new_dict: Dict[str, Any] = {}
            current[key] = new_dict
            stack.append((indent, current))
            current = new_dict

    return data


def _parse_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("'\"")


def _log_audit(event: str, payload: Dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.utcnow().isoformat() + "Z", "event": event, "payload": payload}
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


@dataclass
class BrainSnapshot:
    wings: float = 0.0
    ra: float = 0.0
    omega: float = 0.0
    phi_echo: float = 0.0
    readiness: str = "unknown"
    risk: float = 1.0
    coherence: float = 0.0
    impetus: float = 0.0
    uncertainty: float = 0.0
    gate12: float = 1.0
    gamma: float = 0.0
    gate12_array: List[float] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


class AIBrain:
    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        cfg = cfg or _load_cfg(DEFAULT_CFG_PATH)
        self.engine = load_se_engine(cfg)
        self.snapshot = BrainSnapshot()
        _log_audit("ai_brain_init", {"engine": type(self.engine).__name__, "cfg_wings": cfg.get("wings")})

    def ingest(self, sample: Dict[str, Any]) -> BrainSnapshot:
        signals = self.engine.evaluate(sample)
        self.snapshot = BrainSnapshot(
            wings=signals.wings,
            ra=signals.ra,
            omega=signals.omega,
            phi_echo=signals.phi_echo,
            readiness=signals.readiness,
            risk=getattr(signals, "risk", 1.0),
            coherence=getattr(signals, "coherence", 0.0),
            impetus=getattr(signals, "impetus", 0.0),
            uncertainty=getattr(signals, "uncertainty", 0.0),
            gate12=getattr(signals, "gate12", 1.0),
            gamma=getattr(signals, "gamma", 0.0),
            gate12_array=list(getattr(signals, "gate12_array", []) or []),
            raw=signals.as_dict()
        )
        _log_audit("ai_brain_signals", self.snapshot.raw)
        return self.snapshot

    def hud_payload(self) -> Dict[str, Any]:
        return {
            "wings": self.snapshot.wings,
            "ra": self.snapshot.ra,
            "omega": self.snapshot.omega,
            "phi_echo": self.snapshot.phi_echo,
            "readiness": self.snapshot.readiness
        }

    def decide_wings_visibility(
        self,
        policy: Mapping[str, Any],
        *,
        signals: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate the avatar wings policy using the latest signals."""

        policy_dict = {"override": "auto", "show_if": {}, "hide_if": {}}
        if policy:
            policy_dict.update({k: v for k, v in policy.items()})
        show_if = dict(policy_dict.get("show_if") or {})
        hide_if = dict(policy_dict.get("hide_if") or {})
        policy_dict["show_if"] = show_if
        policy_dict["hide_if"] = hide_if
        override = str(policy_dict.get("override", "auto")).lower()

        if signals is not None:
            tgt = dict(signals)
        else:
            last = getattr(self, "_last_signals", None)
            if last is not None and hasattr(last, "__dict__"):
                tgt = dict(last.__dict__)
            elif isinstance(last, Mapping):
                tgt = dict(last)
            else:
                tgt = dict(self.snapshot.raw)

        tgt.setdefault("wings", self.snapshot.wings)
        tgt.setdefault("reality_alignment", self.snapshot.ra)
        tgt.setdefault("risk", self.snapshot.risk)
        tgt.setdefault("readiness", self.snapshot.readiness)

        readiness = str(tgt.get("readiness", "unknown"))
        wings_val = float(tgt.get("wings", 0.0))
        ra_val = float(tgt.get("reality_alignment", tgt.get("ra", 0.0)))
        risk_val = float(tgt.get("risk", 1.0))
        operator_focus = bool(tgt.get("operator_focus", True))

        reasons: List[str] = []
        state = "hidden"

        if override == "always":
            return {"state": "visible", "reason": ["override_always"], "policy": policy_dict, "override": override}
        if override == "never":
            return {"state": "hidden", "reason": ["override_never"], "policy": policy_dict, "override": override}

        hide_triggered = False
        risk_over = hide_if.get("risk_over")
        if risk_over is not None and risk_val > float(risk_over):
            reasons.append("risk_over")
            hide_triggered = True
        if hide_if.get("operator_focus") is False and not operator_focus:
            reasons.append("operator_focus_off")
            hide_triggered = True

        readiness_needed = str(show_if.get("readiness", "prime_ready"))
        wings_min = float(show_if.get("wings_min", 1.0))
        ra_min = float(show_if.get("ra_min", 0.0))
        risk_max = float(show_if.get("risk_max", 1.0))

        readiness_ok = readiness_needed in {"any", "*"} or readiness == readiness_needed
        wings_ok = wings_val >= wings_min
        ra_ok = ra_val >= ra_min
        risk_ok = risk_val <= risk_max

        if readiness_ok:
            reasons.append("readiness_ok")
        if wings_ok:
            reasons.append("wings_ok")
        if ra_ok:
            reasons.append("ra_ok")
        if risk_ok:
            reasons.append("risk_ok")

        if not hide_triggered and readiness_ok and wings_ok and ra_ok and risk_ok:
            state = "visible"
        else:
            state = "hidden"
        if not reasons:
            reasons.append("policy_default")

        return {"state": state, "reason": reasons, "policy": policy_dict, "override": override}
