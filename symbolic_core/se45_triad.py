from __future__ import annotations

from dataclasses import dataclass
from math import sqrt, prod
from statistics import median
from typing import Dict, List, Optional, Tuple

PHI = (1.0 + 5.0 ** 0.5) / 2.0
NORM = sqrt(2.0) / PHI
EPS = 1e-9


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        v = float(x)
    except Exception:
        v = lo
    if v != v:  # NaN guard
        v = lo
    return max(lo, min(hi, v))


def _readiness(coherence: float, impetus: float) -> str:
    c = _clamp(coherence)
    i = _clamp(impetus)
    if c >= 0.85 and i >= 0.50:
        return "prime_ready"
    if c >= 0.75:
        return "ready"
    if c >= 0.60:
        return "warming"
    return "baseline"


@dataclass
class SE44Inputs:
    # Core signals
    coherence: float
    risk: float
    mirror: float
    gate12: float = 1.0  # ethics/consent/caps product in [0,1]
    RA: float = 0.9  # Reality Alignment
    wings: float = 1.0  # stability multiplier [1.0 .. ~1.06]
    # Awareness extensions
    L: float = 0.80  # Lucidity
    EB: float = 0.85  # Evidence Balance
    IL: float = 0.10  # Illusion Load (higher is worse)
    # Softness weights
    gamma: float = 0.7  # RA softness
    delta: float = 0.6  # L softness
    eta: float = 0.5  # EB softness
    # Optional precomputed readiness
    pre_readiness: Optional[str] = None


@dataclass
class SE44Output:
    impetus: float
    readiness: str
    coherence: float
    risk: float
    mirror: float
    gate12: float
    RA: float
    wings: float
    L: float
    EB: float
    IL: float
    explain: Dict[str, float]


def evaluate_se44(inp: SE44Inputs) -> SE44Output:
    """Single-instance SE4.4 pulse with L / EB / IL."""
    c_coh = _clamp(inp.coherence)
    c_risk = _clamp(inp.risk)
    c_mir = _clamp(inp.mirror)
    c_gate = _clamp(inp.gate12)
    c_RA = _clamp(inp.RA)
    wings = max(1.0, float(inp.wings))

    c_L = _clamp(inp.L)
    c_EB = _clamp(inp.EB)
    c_IL = _clamp(inp.IL)

    core = c_coh * c_mir * (1.0 - c_risk)
    pulse = (
        core
        * c_gate
        * NORM
        * wings
        * (c_RA ** float(inp.gamma))
        * (c_L ** float(inp.delta))
        * (c_EB ** float(inp.eta))
        * (1.0 - c_IL)
    )

    impetus = _clamp(pulse)
    readiness = inp.pre_readiness or _readiness(c_coh, impetus)

    return SE44Output(
        impetus=impetus,
        readiness=readiness,
        coherence=c_coh,
        risk=c_risk,
        mirror=c_mir,
        gate12=c_gate,
        RA=c_RA,
        wings=wings,
        L=c_L,
        EB=c_EB,
        IL=c_IL,
        explain={
            "core": round(core, 6),
            "ethics_gate": round(c_gate, 6),
            "stability": round(NORM * wings, 6),
            "ra_gamma": float(inp.gamma),
            "lucidity_delta": float(inp.delta),
            "evidence_eta": float(inp.eta),
        },
    )


@dataclass
class SE45ConsensusCfg:
    ra_min: float = 0.90  # two-of-three RA must exceed this
    allow_threshold: float = 0.50
    review_band: Tuple[float, float] = (0.40, 0.50)  # inclusive lower bound
    il_alpha: float = 0.50  # disagreement → increased IL*
    l_beta: float = 0.50  # disagreement → decreased L*
    lucidity_min: float = 0.85  # require L* ≥ this for ALLOW
    evidence_min: float = 0.85  # require EB ≥ this for ALLOW
    illusion_max: float = 0.10  # require IL* ≤ this for ALLOW
    gate12_pass_value: float = 0.999  # treat gate12 >= this as pass (boolean)


def _mad(vals: List[float]) -> float:
    """Median Absolute Deviation (robust disagreement proxy)."""
    if not vals:
        return 0.0
    m = median(vals)
    return median([abs(x - m) for x in vals])


def fuse_trinity(A: SE44Output, B: SE44Output, C: SE44Output, cfg: SE45ConsensusCfg) -> Dict:
    """Fuse three SE4.4 outputs into a single, safety-first SE4.5 consensus."""
    trio = [A, B, C]

    # Gate OR — any red gate forces HOLD posture later
    gate_ok = all(t.gate12 >= cfg.gate12_pass_value for t in trio)

    # Two-of-three RA
    ra_2of3 = sum(1 for t in trio if t.RA >= cfg.ra_min) >= 2

    # Impetus robust fusion: conservative
    imp_vals = [t.impetus for t in trio]
    imp_med = median(imp_vals)
    imp_geo = prod(max(EPS, x) for x in imp_vals) ** (1 / 3)
    imp_star = min(imp_med, imp_geo)

    # Disagreement-based adjustment for L/IL
    d = 0.33 * (
        _mad([t.impetus for t in trio]) + _mad([t.RA for t in trio]) + _mad([t.L for t in trio])
    )
    L_star = max(0.0, min(1.0, median([t.L for t in trio]) - cfg.l_beta * d))
    EB_star = max(0.0, min(1.0, median([t.EB for t in trio])))
    IL_star = max(0.0, min(1.0, median([t.IL for t in trio]) + cfg.il_alpha * d))

    # Majority readiness (ties bias downwards)
    order = ["baseline", "warming", "ready", "prime_ready"]
    idx: List[int] = []
    for t in trio:
        try:
            idx.append(order.index(t.readiness))
        except ValueError:
            idx.append(0)
    idx.sort()  # lowest first
    rd_star = order[idx[1]] if len(idx) == 3 else order[min(idx) if idx else 0]

    # Decision logic
    reasons: List[str] = []
    decision = "HOLD"

    if not gate_ok:
        reasons.append("gate12_red")
    if not ra_2of3:
        reasons.append("ra_2of3_fail")

    allow_ok = (
        gate_ok
        and ra_2of3
        and (imp_star >= cfg.allow_threshold)
        and (L_star >= cfg.lucidity_min)
        and (EB_star >= cfg.evidence_min)
        and (IL_star <= cfg.illusion_max)
    )

    low, high = cfg.review_band
    if allow_ok:
        decision = "ALLOW"
    elif (imp_star >= low and imp_star < high) and gate_ok:
        decision = "REVIEW"
        reasons.append("impetus_near_threshold")
    else:
        decision = "HOLD"
        if not reasons:
            reasons.append("impetus_low_or_quality_low")

    # Package votes for audit / HUD
    votes = {
        "Mind": {
            "impetus": A.impetus,
            "readiness": A.readiness,
            "RA": A.RA,
            "L": A.L,
            "EB": A.EB,
            "IL": A.IL,
            "gate12": A.gate12,
        },
        "Heart": {
            "impetus": B.impetus,
            "readiness": B.readiness,
            "RA": B.RA,
            "L": B.L,
            "EB": B.EB,
            "IL": B.IL,
            "gate12": B.gate12,
        },
        "Body": {
            "impetus": C.impetus,
            "readiness": C.readiness,
            "RA": C.RA,
            "L": C.L,
            "EB": C.EB,
            "IL": C.IL,
            "gate12": C.gate12,
        },
    }

    return {
        "version": "SE-4.5",
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "impetus": imp_star,
        "readiness": rd_star,
        "L": L_star,
        "EB": EB_star,
        "IL": IL_star,
        "gate_ok": gate_ok,
        "ra_2of3": ra_2of3,
        "disagreement": d,
        "votes": votes,
        "explain": {
            "fuse": "min(median(impetus), geometric-mean(impetus))",
            "review_band": cfg.review_band,
            "allow_threshold": cfg.allow_threshold,
            "lucidity_min": cfg.lucidity_min,
            "evidence_min": cfg.evidence_min,
            "illusion_max": cfg.illusion_max,
            "ra_min": cfg.ra_min,
        },
    }
