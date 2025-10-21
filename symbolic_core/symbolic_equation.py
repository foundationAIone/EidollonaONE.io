from __future__ import annotations

from dataclasses import dataclass, asdict
from math import isfinite
from typing import Any, Dict, Optional, Iterable, List, Tuple

__all__ = [
    "SE41_VERSION",
    "SE41Signals",
    "SymbolicEquation41",
    "classify_readiness",
    "Reality",
    # Helper utilities for tests and callers
    "build_se41_context",
    "assemble_se41_context_from_summaries",
    "compute_verification_score",
    "suggest_gate",
    "signals_to_dict",
]

SE41_VERSION = "4.1.0"


def _clamp01(x: float) -> float:
    """Clamp a number to [0, 1], treating non-finite values as 0."""
    try:
        xf = float(x)
    except Exception:
        return 0.0
    if not isfinite(xf):
        return 0.0
    return 0.0 if xf < 0.0 else (1.0 if xf > 1.0 else xf)


def _num(value: Any, default: float) -> float:
    """Coerce to float safely; return default when not parsable."""
    try:
        v = float(value)
        return v if isfinite(v) else default
    except Exception:
        return default


def _merge_ethos(hint: Optional[Dict[str, float]]) -> Dict[str, float]:
    """
    Merge user-provided ethos with SAFE defaults.
    Values are clamped to [0, 1] for stability.
    """
    base = {
        "authenticity": 0.90,
        "integrity": 0.90,
        "responsibility": 0.88,
        "enrichment": 0.90,
    }
    if not hint:
        return base
    out: Dict[str, float] = dict(base)
    for k, v in hint.items():
        out[k] = _clamp01(v)
    return out


def classify_readiness(coherence: float, impetus: float) -> str:
    """
    Readiness classification that mirrors MasterSymbolicEquation logic.
    Keep here for convenience and testability.
    """
    c, i = _clamp01(coherence), _clamp01(impetus)
    if c >= 0.85 and i >= 0.50:
        return "prime_ready"
    if c >= 0.75:
        return "ready"
    if c >= 0.60:
        return "warming"
    return "baseline"


@dataclass
class SE41Signals:
    coherence: float
    impetus: float
    risk: float
    uncertainty: float
    mirror_consistency: float
    S_EM: float
    ethos: Dict[str, float]
    embodiment: Dict[str, float]
    explain: str = "SymbolicEquation41"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # Back-compat alias used in some tests/utilities
    @property
    def C_realize(self) -> float:  # noqa: N802 (legacy alias)
        return float(self.coherence)


class SymbolicEquation41:
    """
    Minimal, SAFE SE41 signal engine.

    Compatibility:
    - By default, computes impetus as `coherence * mirror_consistency * (1 - risk)`
      to preserve existing behavior and tests.
    - Optional features (advanced impetus & smoothing) are opt-in via context keys.

    Context keys (all optional):
      coherence_hint: float in [0,1]
      risk_hint: float in [0,1]
      uncertainty_hint: float in [0,1]
      mirror.consistency: float in [0,1]
      substrate.S_EM: float in [0,1]
      ethos_hint: Dict[str, float] (values in [0,1])
      t: float (phase; wrapped to [0,1))
      alpha: float in (0,1] — smoothing factor for stateful coherence (default 1.0)
      impetus_mode: "compat" (default) or "advanced"
    """

    def __init__(self, default_coherence: float = 0.8) -> None:
        self._coh = _clamp01(default_coherence)

    # ---- public API ---------------------------------------------------------

    def evaluate(self, ctx: Dict[str, Any]) -> SE41Signals:
        """
        Evaluate SE41 signals from a (possibly sparse) context dict.

        Returns:
          SE41Signals dataclass (typed and analyzer-friendly).
        """
        # Pull and sanitize inputs
        c_hint = _clamp01(_num(ctx.get("coherence_hint", self._coh), self._coh))
        r = _clamp01(_num(ctx.get("risk_hint", 0.2), 0.2))
        u = _clamp01(_num(ctx.get("uncertainty_hint", 0.25), 0.25))

        mirror = ctx.get("mirror", {}) or {}
        m = _clamp01(_num(mirror.get("consistency", 0.7), 0.7))

        substrate = ctx.get("substrate", {}) or {}
        s = _clamp01(_num(substrate.get("S_EM", 0.78), 0.78))

        ethos = _merge_ethos(ctx.get("ethos_hint"))

        # Optional stateful smoothing for coherence
        alpha = _clamp01(_num(ctx.get("alpha", 1.0), 1.0)) or 1.0
        self._coh = _clamp01((1.0 - alpha) * self._coh + alpha * c_hint)

        # Impetus calculation (compat by default)
        mode = str(ctx.get("impetus_mode", "compat")).lower()
        if mode == "advanced":
            # Advanced (opt-in): gently incorporate uncertainty, ethos, and S_EM.
            # Tuned to keep outputs within prior expectations.
            ethos_score = sum(ethos.values()) / max(1, len(ethos))
            imp = self._coh * m * (1.0 - r)
            imp *= (0.85 + 0.15 * s)          # substrate lifts a little
            imp *= (0.5 + 0.5 * ethos_score)  # ethical alignment multiplier
            imp *= (1.0 - 0.35 * u)           # uncertainty dampener (mild)
            imp = _clamp01(imp)
            explain = "SymbolicEquation41:advanced"
        else:
            # Compatibility path (preserves your current outputs)
            imp = _clamp01(self._coh * m * (1.0 - r))
            explain = "SymbolicEquation41:compat"

        # Embodiment fields expected by tests
        phase = _clamp01(_num(ctx.get("t", 0.0), 0.0)) % 1.0
        # simple gait parameters derived from impetus (always positive)
        cadence_spm = 30.0 + 90.0 * max(0.0, imp)  # steps per minute (>0)
        step_len_m = 0.15 + 0.35 * max(0.0, imp)   # meters per step (>0)
        emb = {"phase": phase, "cadence_spm": cadence_spm, "step_len_m": step_len_m}

        return SE41Signals(
            coherence=self._coh,
            impetus=imp,
            risk=r,
            uncertainty=u,
            mirror_consistency=m,
            S_EM=s,
            ethos=ethos,
            embodiment=emb,
            explain=explain,
        )

    # Convenience for callers that want plain dicts
    def evaluate_dict(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return self.evaluate(ctx).to_dict()

    # Convenience used by tests: evaluate from blended summaries
    def evaluate_from_summaries(self, summaries: Iterable[Dict[str, Any]]) -> SE41Signals:
        ctx = assemble_se41_context_from_summaries(list(summaries))
        return self.evaluate(ctx)

    # ---- legacy shims used in tests/utilities --------------------------------
    def reality_manifestation(self, Q: float = 0.0) -> float:
        """Back-compat helper: map Q in [0,1] to [0,1] (identity clamp)."""
        return _clamp01(_num(Q, 0.0))

    def validate_update_coherence(self, ctx: Dict[str, Any]) -> float:
        """Back-compat: update internal coherence with provided hint; return level."""
        c_hint = _clamp01(_num(ctx.get("coherence_hint", self._coh), self._coh))
        self._coh = c_hint
        return float(self._coh)

    def get_coherence_level(self) -> float:
        """Back-compat accessor for current coherence level."""
        return float(self._coh)

    def post_update_recalibration(self) -> None:
        """Back-compat no-op hook."""
        return None

    # Additional legacy conveniences used by higher-level IO modules
    def get_current_state_summary(self) -> Dict[str, Any]:
        """Return a current summary dict of signals.

        Some legacy modules call this without context; provide a stable
        summary derived from the current internal state with a minimal
        default context.
        """
        ctx = build_se41_context(coherence_hint=self._coh)
        return self.evaluate_dict(ctx)

    def consciousness_shift(self, delta: float) -> None:
        """Legacy hook to nudge internal coherence state by a small delta."""
        try:
            self._coh = _clamp01(float(self._coh) + float(delta))
        except Exception:
            # SAFE posture: ignore bad inputs
            self._coh = _clamp01(self._coh)


class Reality:
    """Adapter that maps a symbolic 'Reality(t)' measure to a bounded scalar in [0,1].

    The measure is derived from SE41 signals and a phase `t` following the intent:

      Reality(t) = [ Node_Consciousness
                      × Π_{i=2..9} ( Angle_i × ( Vibration(f(Q, M(t)), DNA_i)
                                       × Σ_{k=1..12} Evolve(Harmonic_Pattern_k) ) )
                   ] + ΔConsciousness(t) + Ethos

    Practical mapping:
    - Node_Consciousness := coherence
    - Angle_i := 0.5 * (1 + cos(2π i phase)) ∈ [0,1]
    - M(t) := impetus
    - Q := coherence_hint (or current coherence if missing)
    - Vibration(f(Q, M), DNA_i) := σ(2(Q·M − 0.5) + 0.1 cos(2π i phase)) · DNA_i,
      with σ the logistic sigmoid and DNA_i ∈ [0.7, 1.0] derived from ethos
    - Σ Evolve(Harmonic_Pattern_k) := average over k=1..12 of 0.5(1+cos(2π k phase)) ∈ [0,1]
    - ΔConsciousness(t) := 0.05·sin(2π phase)
    - Ethos := 0.1·mean(ethos.values())

    The product is aggregated via a geometric mean to avoid underflow across factors.
    """

    def __init__(self, engine: Optional["SymbolicEquation41"] = None) -> None:
        self.engine = engine or SymbolicEquation41()

    @staticmethod
    def _cos01(x: float) -> float:
        from math import cos, tau

        return 0.5 * (1.0 + cos(tau * x))

    @staticmethod
    def _sigmoid(x: float) -> float:
        try:
            from math import exp

            # numerically stable sigmoid for moderate x
            if x >= 0:
                z = exp(-x)
                return 1.0 / (1.0 + z)
            else:
                z = exp(x)
                return z / (1.0 + z)
        except Exception:
            # SAFE fallback linear clamp
            return _clamp01(0.5 + 0.25 * x)

    def __call__(self, t: Optional[float] = None, ctx: Optional[Dict[str, Any]] = None) -> float:
        """Callable form: merge `t` into `ctx` and return the measure."""
        data = dict(ctx or {})
        if t is not None:
            data["t"] = t
        return self.measure(data)

    def measure(self, ctx: Dict[str, Any]) -> float:
        from math import log, exp

        # Evaluate SE41 signals first (source of coherence, impetus, ethos, phase)
        sig = self.engine.evaluate(ctx)
        node = _clamp01(sig.coherence)
        phase = _clamp01(float(sig.embodiment.get("phase", 0.0)))
        M_t = _clamp01(sig.impetus)
        Q = _clamp01(_num(ctx.get("coherence_hint", node), node))
        ethos_vals = list((sig.ethos or {}).values())
        ethos_score = _clamp01(sum(ethos_vals) / max(1, len(ethos_vals))) if ethos_vals else 0.9

        # Harmonic evolution term: average over k=1..12 of a phase-based cosine
        evol_sum = 0.0
        for k in range(1, 13):
            evol_sum += 0.5 * (1.0 + __import__("math").cos(__import__("math").tau * k * phase))
        evol_avg = evol_sum / 12.0  # ∈ [0,1]

        # Construct 8 multiplicative factors (i=2..9)
        factors = []
        for i in range(2, 10):
            angle_i = self._cos01(i * phase)  # ∈ [0,1]
            # DNA_i: ethos-influenced weight in [0.7, 1.0]
            dna_i = _clamp01(0.7 + 0.3 * ethos_score * (1.0 - 0.05 * (i - 2)))
            vib_arg = 2.0 * (Q * M_t - 0.5) + 0.1 * __import__("math").cos(__import__("math").tau * i * phase)
            vibration = self._sigmoid(vib_arg) * dna_i  # ∈ [0,1]
            factor = angle_i * (vibration * evol_avg)
            # keep within [1e-6,1] to avoid log(0)
            factors.append(max(1e-6, min(1.0, factor)))

        # Geometric mean of factors to avoid underflow and keep the magnitude meaningful
        gm = exp(sum(log(f) for f in factors) / len(factors)) if factors else 1.0
        base = _clamp01(node * gm)

        # ΔConsciousness(t): gentle oscillation; bounded small addend
        d_conscious = 0.05 * __import__("math").sin(__import__("math").tau * phase)

        # Ethos additive component
        ethos_add = 0.1 * ethos_score

        return _clamp01(base + d_conscious + ethos_add)


# -------- Helper utilities expected by tests --------

def _blend(values: List[float], default: float) -> float:
    if not values:
        return float(default)
    try:
        return float(sum(values) / len(values))
    except Exception:
        return float(default)


def build_se41_context(
    coherence_hint: float = 0.8,
    *,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Minimal context builder with keyword-only overrides for analyzer-friendly API."""
    base = {
        "coherence_hint": _clamp01(_num(coherence_hint, 0.8)),
        "risk_hint": 0.2,
        "uncertainty_hint": 0.25,
        "mirror": {"consistency": 0.7},
        "substrate": {"S_EM": 0.78},
        "ethos_hint": _merge_ethos(None),
        "t": 0.0,
    }
    if overrides:
        # Shallow merge is sufficient for tests; keys can override nested dicts wholly
        merged = dict(base)
        merged.update(overrides)
        base = merged
    return base


def assemble_se41_context_from_summaries(
    summaries: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Blend multiple summary dicts into a single context.

    Accepts flexible keys used across the codebase and tests:
    - risk or risk_hint; uncertainty or uncertainty_hint
    - mirror.consistency or mirror_consistency
    - substrate.S_EM or S_EM
    - ethos or ethos_hint
    """
    s_list = list(summaries or [])
    if not s_list:
        return build_se41_context()

    coh_vals: List[float] = []
    risk_vals: List[float] = []
    unc_vals: List[float] = []
    mir_vals: List[float] = []
    sem_vals: List[float] = []
    t_vals: List[float] = []
    ethos_merge: Dict[str, float] = {}

    for s in s_list:
        try:
            if "coherence_hint" in s:
                coh_vals.append(_num(s.get("coherence_hint"), 0.8))
            if "coherence_level" in s:  # alternate name in tests
                coh_vals.append(_num(s.get("coherence_level"), 0.8))

            # risk / uncertainty can appear under alternate keys
            if "risk_hint" in s:
                risk_vals.append(_num(s.get("risk_hint"), 0.2))
            if "risk" in s:
                risk_vals.append(_num(s.get("risk"), 0.2))

            if "uncertainty_hint" in s:
                unc_vals.append(_num(s.get("uncertainty_hint"), 0.25))
            if "uncertainty" in s:
                unc_vals.append(_num(s.get("uncertainty"), 0.25))

            # mirror
            if "mirror" in s and isinstance(s.get("mirror"), dict):
                mir_vals.append(_num(s["mirror"].get("consistency"), 0.7))
            if "mirror_consistency" in s:
                mir_vals.append(_num(s.get("mirror_consistency"), 0.7))

            # substrate
            if "substrate" in s and isinstance(s.get("substrate"), dict):
                sem_vals.append(_num(s["substrate"].get("S_EM"), 0.78))
            if "S_EM" in s:
                sem_vals.append(_num(s.get("S_EM"), 0.78))

            # ethos
            e = s.get("ethos_hint") or s.get("ethos")
            if isinstance(e, dict):
                for k, v in e.items():
                    ethos_merge[k] = _clamp01(_num(v, ethos_merge.get(k, 0.9)))

            # time/phase
            if "t" in s:
                t_vals.append(_num(s.get("t"), 0.0))
        except Exception:
            continue

    ctx = build_se41_context(
        coherence_hint=_blend(coh_vals, 0.8),
        overrides={
            "risk_hint": _clamp01(_blend(risk_vals, 0.2)),
            "uncertainty_hint": _clamp01(_blend(unc_vals, 0.25)),
            "mirror": {"consistency": _clamp01(_blend(mir_vals, 0.7))},
            "substrate": {"S_EM": _clamp01(_blend(sem_vals, 0.78))},
            "ethos_hint": _merge_ethos(ethos_merge if ethos_merge else None),
            "t": _clamp01(_blend(t_vals, 0.0)),
        },
    )
    return ctx


def signals_to_dict(sig: Any) -> Dict[str, Any]:
    """Best-effort conversion of signals object/dict into a plain dict."""
    if sig is None:
        return {}
    if isinstance(sig, dict):
        return dict(sig)
    if hasattr(sig, "to_dict"):
        try:
            return sig.to_dict()  # type: ignore[no-any-return]
        except Exception:
            pass
    if hasattr(sig, "__dict__"):
        try:
            return dict(getattr(sig, "__dict__"))
        except Exception:
            pass
    try:
        return dict(sig)  # type: ignore[arg-type]
    except Exception:
        return {}


def compute_verification_score(payload: Any) -> float:
    """Compute a verification score in [0,1] from signals-like input.

    Heuristic, but stable across inputs used in tests. Weighs coherence/impetus
    positively and risk/uncertainty negatively. Includes mirror/substrate softly.
    """
    data = signals_to_dict(payload)
    c = _clamp01(_num(data.get("coherence", 0.0), 0.0))
    i = _clamp01(_num(data.get("impetus", 0.0), 0.0))
    r = _clamp01(_num(data.get("risk", 0.5), 0.5))
    u = _clamp01(_num(data.get("uncertainty", 0.5), 0.5))
    m = _clamp01(_num(data.get("mirror_consistency", 0.7), 0.7))
    s = _clamp01(_num(data.get("S_EM", 0.78), 0.78))
    # simple weighted sum
    score = 0.35 * c + 0.30 * i + 0.10 * m + 0.10 * s + 0.075 * (1.0 - r) + 0.075 * (1.0 - u)
    return _clamp01(score)


def suggest_gate(payload: Any, thresholds: Tuple[float, float] = (0.8, 0.6)) -> str:
    """Return 'allow' | 'review' | 'hold' based on score.

    Accepts a float score or a signals-like object.
    """
    if isinstance(payload, (int, float)):
        score = _clamp01(float(payload))
    else:
        score = compute_verification_score(payload)
    hi, lo = float(thresholds[0]), float(thresholds[1])
    if score >= hi:
        return "allow"
    if score >= lo:
        return "review"
    return "hold"
