from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .se45_triad import (
    SE44Inputs,
    SE45ConsensusCfg,
    evaluate_se44,
    fuse_trinity,
)


def _load_config() -> Dict[str, Any]:
    # YAML is optional; we support a minimal subset via naive parsing if no PyYAML
    cfg_path = Path("config/se.yml")
    if not cfg_path.exists():
        # default: triad enabled with sane consensus
        return {
            "se": {
                "version": 4.5,
                "triad": {
                    "enabled": True,
                    "consensus": {
                        "ra_min": 0.90,
                        "allow_threshold": 0.50,
                        "review_band": [0.40, 0.50],
                        "il_alpha": 0.5,
                        "l_beta": 0.5,
                        "lucidity_min": 0.85,
                        "evidence_min": 0.85,
                        "illusion_max": 0.10,
                    },
                    "instances": {
                        "mind": {"gamma": 0.8, "delta": 0.8, "eta": 0.7},
                        "heart": {"gamma": 0.6, "delta": 0.9, "eta": 0.8},
                        "body": {"gamma": 0.7, "delta": 0.6, "eta": 0.5},
                    },
                },
            }
        }
    try:
        import yaml  # type: ignore

        with cfg_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)  # type: ignore[no-any-return]
    except Exception:
        # ultra-naive parser: treat as JSON if possible
        try:
            with cfg_path.open("r", encoding="utf-8") as f:
                return json.load(f)  # type: ignore[no-any-return]
        except Exception:
            return {}


def _mk_inputs(context: Dict[str, Any], role_cfg: Dict[str, Any]) -> SE44Inputs:
    coh = float(context.get("coherence", context.get("coherence_hint", 0.82)))
    risk = float(context.get("risk", context.get("risk_hint", 0.15)))
    mirror = float((context.get("mirror") or {}).get("consistency", 0.78))
    gate12 = float(context.get("gate12", 1.0))
    RA = float(context.get("RA", 0.93))
    wings = float(context.get("wings", 1.02))
    L = float(context.get("L", 0.90))
    EB = float(context.get("EB", 0.90))
    IL = float(context.get("IL", 0.06))
    gamma = float(role_cfg.get("gamma", 0.7))
    delta = float(role_cfg.get("delta", 0.6))
    eta = float(role_cfg.get("eta", 0.5))
    return SE44Inputs(
        coherence=coh,
        risk=risk,
        mirror=mirror,
        gate12=gate12,
        RA=RA,
        wings=wings,
        L=L,
        EB=EB,
        IL=IL,
        gamma=gamma,
        delta=delta,
        eta=eta,
    )


def evaluate_pulse(context: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _load_config() or {}
    se_cfg = cfg.get("se") or {}
    version = se_cfg.get("version", 4.4)
    triad = (se_cfg.get("triad") or {}) if isinstance(se_cfg, dict) else {}
    enabled = bool((triad.get("enabled") if isinstance(triad, dict) else False))

    if float(version) >= 4.5 and enabled:
        cons_cfg = triad.get("consensus", {})
        inst_cfg = triad.get("instances", {})
        mind_in = _mk_inputs(context, inst_cfg.get("mind", {}))
        heart_in = _mk_inputs(context, inst_cfg.get("heart", {}))
        body_in = _mk_inputs(context, inst_cfg.get("body", {}))
        A = evaluate_se44(mind_in)
        B = evaluate_se44(heart_in)
        C = evaluate_se44(body_in)
        fcfg = SE45ConsensusCfg(
            ra_min=float(cons_cfg.get("ra_min", 0.90)),
            allow_threshold=float(cons_cfg.get("allow_threshold", 0.50)),
            review_band=tuple(cons_cfg.get("review_band", [0.40, 0.50])),
            il_alpha=float(cons_cfg.get("il_alpha", 0.5)),
            l_beta=float(cons_cfg.get("l_beta", 0.5)),
            lucidity_min=float(cons_cfg.get("lucidity_min", 0.85)),
            evidence_min=float(cons_cfg.get("evidence_min", 0.85)),
            illusion_max=float(cons_cfg.get("illusion_max", 0.10)),
            gate12_pass_value=float(cons_cfg.get("gate12_pass_value", 0.999)),
        )
        fused = fuse_trinity(A, B, C, fcfg)
        # Map to unified dict
        return {
            **fused,
        }

    # Fallback: mimic single-pulse result into compatible dict
    single = evaluate_se44(_mk_inputs(context, {}))
    decision = (
        "ALLOW"
        if (single.impetus >= 0.5 and single.L >= 0.85 and single.EB >= 0.85 and single.IL <= 0.10)
        else ("REVIEW" if 0.40 <= single.impetus < 0.50 else "HOLD")
    )
    return {
        "version": f"SE-{float(version):.1f}",
        "decision": decision,
        "reasons": [],
        "impetus": single.impetus,
        "readiness": single.readiness,
        "L": single.L,
        "EB": single.EB,
        "IL": single.IL,
        "gate_ok": single.gate12 >= 0.999,
        "ra_2of3": True,
        "disagreement": 0.0,
        "votes": {},
        "explain": single.explain,
    }
