"""
ai_core/probabilistic_quantum_rendering/ascii.py

SE4.3 (Wings/Aletheia) ASCII renderer for EidollonaONE.

Responsibilities
- Pull a QPIR snapshot (Base-12 lotus + Wings W(t) + Reality Alignment RA(t)).
- Render the snapshot as plain-text:
  * Signals (coherence, impetus, risk, readiness, wings, RA, gate12)
  * 12-gate ring (bars)
  * Probability ribbon (condensed histogram with p10|p50|p90 markers)
  * Uncertainty cone (near/medium/far), RA-damped
- Emit NDJSON audit events to $EIDOLLONA_AUDIT or logs/audit.ndjson.

SAFE posture
- Read-only rendering. No PII. Consent/verified-net surface indirectly via RA
  provided by the symbolic engine.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Audit helpers (fallback-safe)
# ---------------------------------------------------------------------------
def _audit_ndjson(event: str, **fields: Any) -> None:
	path = os.getenv("EIDOLLONA_AUDIT", "logs/audit.ndjson")
	try:
		os.makedirs(os.path.dirname(path), exist_ok=True)
		payload = {"event": event, **fields, "ts": time.time()}
		with open(path, "a", encoding="utf-8") as f:
			f.write(json.dumps(payload, ensure_ascii=False) + "\n")
	except Exception:
		# Renderer should never raise simply because the audit sink failed.
		pass


try:
	from utils.audit import audit_ndjson as audit_ndjson  # type: ignore
except Exception:  # pragma: no cover - utils.audit optional in some envs
	audit_ndjson = _audit_ndjson


# ---------------------------------------------------------------------------
# Snapshot sourcing (prefers QPIR system, falls back to symbolic engine)
# ---------------------------------------------------------------------------
def _load_qpir_snapshot() -> Dict[str, Any]:
	"""
	Obtain a deterministic QPIR snapshot in dictionary form.

	Preference order:
	1. Use the published QPIRSystem (SE4.3 with Wings/RA and uncertainty cone)
	2. Fall back to the Symbolic Equation stack to synthesize a minimal snapshot
	"""

	# Primary: packaged QPIRSystem
	try:
		module = importlib.import_module(
			"quantum_probabilistic_information_rendering_system"
		)
		QPIRSystem = getattr(module, "QPIRSystem")  # type: ignore
		system = QPIRSystem()  # type: ignore[call-arg]
		snap = system.render_snapshot()
		return {
			"ts": snap.timestamp,
			"signals": snap.signals,
			"ring": snap.ring,
			"probability": snap.probability,
			"cone": snap.cone,
			"reasons": snap.reasons,
		}
	except Exception:
		pass

	# Fallback: Symbolic Equation evaluation
	try:
		loader_mod = importlib.import_module("symbolic_core.se_loader_ext")
		load_se_engine = getattr(loader_mod, "load_se_engine")
		sig = load_se_engine()
	except Exception:
		ctx_mod = importlib.import_module("symbolic_core.context_builder")
		eq_mod = importlib.import_module("symbolic_core.symbolic_equation")
		assemble_ctx = getattr(ctx_mod, "assemble_se41_context")
		SymbolicEquation41 = getattr(eq_mod, "SymbolicEquation41")
		sig = SymbolicEquation41().evaluate(assemble_ctx())

	def _get(attr: str, default: Any = None) -> Any:
		return getattr(sig, attr, default)

	signals = {
		"coherence": _get("coherence", 0.0),
		"impetus": _get("impetus", 0.0),
		"risk": _get("risk", 0.0),
		"uncertainty": _get("uncertainty", 0.0),
		"mirror_consistency": _get("mirror_consistency", 0.0),
		"readiness": _get("readiness", "warming"),
		"gate12": _get("gate12", 1.0),
		"wings": _get("wings", 1.0),
		"reality_alignment": _get("reality_alignment", 0.0),
		"gamma": _get("gamma", 0.7),
	}

	arr = getattr(sig, "gate12_array", None)
	if not isinstance(arr, list) or not arr:
		arr = [1.0] * 12
	coh = float(signals["coherence"])
	risk = float(signals["risk"])
	base = max(1e-6, coh * (1.0 - risk))
	raw = [max(0.0, min(1.0, float(x))) * base for x in arr[:12]]
	total = sum(raw) or 1.0
	ring_weights = [x / total for x in raw]
	labels = [
		"consent",
		"privacy_pii",
		"power_caps",
		"auditability",
		"alignment",
		"data_integrity",
		"ext_policy",
		"counterparty_trust",
		"latency_compute",
		"tail_risk",
		"operator_override",
		"language_gate",
	]

	xs, hist, p10, p50, p90 = _quick_pdf(
		float(signals["impetus"]), float(signals["risk"])
	)

	return {
		"ts": time.time(),
		"signals": signals,
		"ring": {"weights": ring_weights, "labels": labels},
		"probability": {"bins": xs, "hist": hist, "p10": p10, "p50": p50, "p90": p90},
		"cone": _uncertainty_cone(
			uncertainty=float(signals["uncertainty"]),
			ra=float(signals["reality_alignment"]),
		),
		"reasons": _basic_reasons(signals, ring_weights, (p10, p50, p90), labels),
	}


# ---------------------------------------------------------------------------
# ASCII renderer configuration
# ---------------------------------------------------------------------------
@dataclass
class AsciiConfig:
	ring_bar_width: int = 24
	max_gate_rows: int = 12
	ribbon_width: int = 64
	charset: str = "block"  # 'block' or 'hash'
	show_ansi: bool = False  # placeholder for future coloring support


# ---------------------------------------------------------------------------
# Renderer Implementation
# ---------------------------------------------------------------------------
class AsciiRenderer:
	BLOCKS = (" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█")
	DENSITY = " .:-=+*#%@"

	def __init__(self, cfg: Optional[AsciiConfig] = None) -> None:
		self.cfg = cfg or AsciiConfig()
		try:
			cols = shutil.get_terminal_size().columns
			self.cfg.ribbon_width = max(48, min(self.cfg.ribbon_width, cols - 16))
		except Exception:
			pass

	# -- public API ---------------------------------------------------------
	def render_snapshot(self, snap: Dict[str, Any]) -> str:
		sig = snap.get("signals", {})
		ring = snap.get("ring", {})
		prob = snap.get("probability", {})
		cone = snap.get("cone", {})
		reasons = snap.get("reasons", {})

		sections = [
			self._hdr(sig, snap.get("ts")),
			self._signals(sig),
			self._ring(ring),
			self._ribbon(prob),
			self._cone(cone),
			self._why(reasons),
		]
		return "\n".join(sections)

	def print_snapshot(self, snap: Dict[str, Any]) -> None:
		out = self.render_snapshot(snap)
		print(out)
		audit_ndjson(
			"qpir_ascii_render",
			readiness=snap.get("signals", {}).get("readiness"),
			impetus=snap.get("signals", {}).get("impetus"),
			risk=snap.get("signals", {}).get("risk"),
		)

	# -- sections -----------------------------------------------------------
	def _hdr(self, sig: Dict[str, Any], ts: Optional[float]) -> str:
		t = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts or time.time()))
		readiness = str(sig.get("readiness", "warming")).upper()
		return f"QPIR ASCII Snapshot — {t}  |  READINESS: {readiness}"

	def _signals(self, sig: Dict[str, Any]) -> str:
		coh = float(sig.get("coherence", 0.0))
		imp = float(sig.get("impetus", 0.0))
		risk = float(sig.get("risk", 0.0))
		ra = float(sig.get("reality_alignment", 0.0))
		wings = float(sig.get("wings", 1.0))
		gate12 = float(sig.get("gate12", 1.0))
		return (
			"Signals  "
			f"coh={coh:0.3f}  imp={imp:0.3f}  risk={risk:0.3f}  RA={ra:0.3f}  "
			f"W={wings:0.3f}  Gate₁₂={gate12:0.3f}"
		)

	def _ring(self, ring: Dict[str, Any]) -> str:
		weights: List[float] = list(ring.get("weights") or [])
		labels: List[str] = list(ring.get("labels") or [])
		if not weights:
			return "Ring     (no ring data)"
		rows = min(self.cfg.max_gate_rows, len(weights))
		lines = ["Ring     "]
		for idx in range(rows):
			label = (labels[idx] if idx < len(labels) else f"gate_{idx + 1}")
			label = label[:18].ljust(18)
			bar = self._bar(weights[idx], self.cfg.ring_bar_width)
			pct = f"{weights[idx] * 100:5.1f}%"
			lines.append(f"  {label} {bar} {pct}")
		return "\n".join(lines)

	def _ribbon(self, prob: Dict[str, Any]) -> str:
		xs: List[float] = list(prob.get("bins") or [])
		hist: List[float] = list(prob.get("hist") or [])
		p10 = float(prob.get("p10", 0.10))
		p50 = float(prob.get("p50", 0.50))
		p90 = float(prob.get("p90", 0.90))
		if not xs or not hist:
			return "Probability  (no ribbon data)"

		width = self.cfg.ribbon_width
		cols = _resample(xs, hist, width)
		idx10 = max(0, min(width - 1, int(round(p10 * (width - 1)))))
		idx50 = max(0, min(width - 1, int(round(p50 * (width - 1)))))
		idx90 = max(0, min(width - 1, int(round(p90 * (width - 1)))))

		chars = list(cols)
		chars[idx10] = "|"
		chars[idx50] = "│" if self.cfg.charset == "block" else "|"
		chars[idx90] = "|"

		return f"Probability [{p10:0.2f} | {p50:0.2f} | {p90:0.2f}]\n  {''.join(chars)}"

	def _cone(self, cone: Dict[str, Any]) -> str:
		near = float(cone.get("near", 0.0))
		medium = float(cone.get("medium", 0.0))
		far = float(cone.get("far", 0.0))
		return (
			"Uncertainty Cone (RA-damped)\n"
			f"  near  {self._bar(near, 20)} {near:0.3f}\n"
			f"  med   {self._bar(medium, 20)} {medium:0.3f}\n"
			f"  far   {self._bar(far, 20)} {far:0.3f}"
		)

	def _why(self, reasons: Dict[str, Any]) -> str:
		wings_active = bool(reasons.get("wings_active", False))
		ra = reasons.get("reality_alignment")
		gate = reasons.get("gate12")
		dominant = reasons.get("dominant_gates", [])
		top = ", ".join(
			f"{item.get('label')}:{item.get('weight')}" for item in dominant
		) or "n/a"
		wing_icon = "⟠" if wings_active else "-"
		return f"Reasons  wings={wing_icon}  RA={ra}  Gate₁₂={gate}  top=[{top}]"

	# -- primitives --------------------------------------------------------
	def _bar(self, value: float, width: int) -> str:
		value = max(0.0, min(1.0, float(value)))
		filled = int(value * width)
		remainder = value * width - filled
		if self.cfg.charset == "block":
			partial = self.BLOCKS[min(8, int(round(remainder * 8)))]
			base = "█" * filled
			tail_needed = width - filled - 1
			if filled >= width:
				return base
			return base + partial + " " * max(0, tail_needed)
		return "#" * filled + "-" * (width - filled)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _resample(xs: List[float], ys: List[float], width: int) -> str:
	if width <= 1:
		return "#"
	n = len(xs)
	if n == 0:
		return "-" * width
	buckets = [0.0] * width
	counts = [0] * width
	for x, y in zip(xs, ys):
		idx = max(0, min(width - 1, int(round(x * (width - 1)))))
		buckets[idx] += float(y)
		counts[idx] += 1
	vals = [buckets[i] / counts[i] if counts[i] else 0.0 for i in range(width)]
	maximum = max(vals) or 1.0
	density = " .:-=+*#%@"
	chars = []
	for v in vals:
		spot = int(round((len(density) - 1) * (v / maximum)))
		chars.append(density[spot])
	return "".join(chars)


def _uncertainty_cone(*, uncertainty: float, ra: float) -> Dict[str, Any]:
	u = max(0.0, min(1.0, float(uncertainty)))
	ra_adj = max(0.0, min(1.0, float(ra)))
	damp = 1.0 - 0.35 * ra_adj
	near = max(0.0, min(1.0, u * 0.85 * damp))
	medium = max(0.0, min(1.0, u * 1.00 * damp))
	far = max(0.0, min(1.0, u * 1.15 * damp))
	return {
		"near": round(near, 4),
		"medium": round(medium, 4),
		"far": round(far, 4),
		"ra_damping": round(damp, 4),
	}


def _beta_pdf_series(xs: Iterable[float], a: float, b: float) -> List[float]:
	def beta_pdf(x: float) -> float:
		if x <= 0.0 or x >= 1.0:
			x = max(1e-6, min(1.0 - 1e-6, x))
		return (x ** (a - 1.0)) * ((1.0 - x) ** (b - 1.0))

	vals = [beta_pdf(float(x)) for x in xs]
	total = sum(vals) or 1.0
	return [v / total for v in vals]


def _quick_pdf(impetus: float, risk: float, bins: int = 41) -> Tuple[List[float], List[float], float, float, float]:
	m = max(0.0, min(1.0, float(impetus)))
	kappa = 2.0 + 10.0 * max(0.0, min(1.0, 1.0 - float(risk)))
	alpha = max(1e-3, m * kappa)
	beta = max(1e-3, (1.0 - m) * kappa)
	xs = [i / (bins - 1) for i in range(bins)]
	hist = _beta_pdf_series(xs, alpha, beta)
	cumulative = 0.0
	p10 = p50 = p90 = 0.0
	for x, h in zip(xs, hist):
		cumulative += h
		if cumulative >= 0.10 and p10 == 0.0:
			p10 = x
		if cumulative >= 0.50 and p50 == 0.0:
			p50 = x
		if cumulative >= 0.90 and p90 == 0.0:
			p90 = x
	return xs, hist, p10, p50, p90


def _basic_reasons(
	signals: Dict[str, Any],
	ring_weights: List[float],
	pct: Tuple[float, float, float],
	labels: List[str],
) -> Dict[str, Any]:
	wings = float(signals.get("wings", 1.0) or 1.0)
	ra = float(signals.get("reality_alignment", 0.0) or 0.0)
	gate = float(signals.get("gate12", 1.0) or 1.0)
	top = sorted(
		[(idx, wt) for idx, wt in enumerate(ring_weights)],
		key=lambda item: item[1],
		reverse=True,
	)[:3]
	dominant = [
		{"label": labels[idx], "weight": round(weight, 4)} for idx, weight in top
	]
	return {
		"wings_active": wings >= 1.03,
		"wings_value": round(wings, 4),
		"reality_alignment": round(ra, 4),
		"gate12": round(gate, 4),
		"dominant_gates": dominant,
		"percentiles": {
			"p10": round(pct[0], 4),
			"p50": round(pct[1], 4),
			"p90": round(pct[2], 4),
		},
	}


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
	snapshot = _load_qpir_snapshot()
	AsciiRenderer().print_snapshot(snapshot)
	return 0


if __name__ == "__main__":  # pragma: no cover
	sys.exit(main(sys.argv[1:]))

