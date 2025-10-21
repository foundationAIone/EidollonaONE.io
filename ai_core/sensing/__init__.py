"""SAFE-mode sensing shims used by the test suite.

The original sensing subsystem is unavailable in this workspace, so we provide
deterministic fallbacks that satisfy the public APIs consumed by our tests and
other SAFE-mode utilities.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Dict, Mapping, MutableMapping, Optional, Tuple


@dataclass
class GateDecision:
	"""Structured outcome from the gatekeeper."""

	decision: str
	reason: str
	score: float
	details: Dict[str, Any] = field(default_factory=dict)


class Gatekeeper:
	"""Policy-oriented SAFE sensing gatekeeper."""

	def __init__(
		self,
		*,
		fz1_min: float = 0.70,
		coherence_min: float = 0.75,
		ethos_min: float = 0.80,
		verification_slack: float = 0.15,
	) -> None:
		self.thresholds = {
			"fz1_min": float(fz1_min),
			"coherence_min": float(coherence_min),
			"ethos_min": float(ethos_min),
			"verification_slack": max(0.0, min(1.0, float(verification_slack))),
		}
		self._overrides: MutableMapping[Tuple[str, str], str] = {}

	# ------------------------------------------------------------------
	# Override management
	# ------------------------------------------------------------------
	def set_override(self, node_id: str, purpose: str, decision: str) -> None:
		self._overrides[(node_id, purpose)] = decision.upper()

	def clear_override(self, node_id: str, purpose: str) -> None:
		self._overrides.pop((node_id, purpose), None)

	def clear_overrides(self) -> None:
		self._overrides.clear()

	# ------------------------------------------------------------------
	# Decision flow
	# ------------------------------------------------------------------
	def decide(
		self,
		node: Mapping[str, Any],
		*,
		purpose: str,
		ctx: Optional[Mapping[str, Any]] = None,
	) -> GateDecision:
		ctx = ctx or {}
		node_id = str(node.get("id", "unknown"))

		override = self._overrides.get((node_id, purpose))
		if override:
			return GateDecision(
				decision=override,
				reason="override",
				score=1.0,
				details={"node": node_id, "purpose": purpose},
			)

		consent = str(node.get("consent", "summary")).lower()
		if consent == "deny":
			return self._deny("no_consent")
		if consent == "hold":
			return self._hold("awaiting_consent")

		if ctx.get("safe_mode") and str(node.get("redaction", "edge")) != "edge":
			return self._hold("redaction_required")

		signals = self._synth_signals(node, ctx)
		verification_min = max(
			0.0,
			min(
				self.thresholds["fz1_min"],
				self.thresholds["coherence_min"],
			)
			- self.thresholds["verification_slack"],
		)
		meets = (
			signals["fz1"] >= self.thresholds["fz1_min"]
			and signals["coherence"] >= self.thresholds["coherence_min"]
			and signals["ethos"] >= self.thresholds["ethos_min"]
			and signals["verification"] >= verification_min
		)

		details = {
			"signals": signals,
			"thresholds": {**self.thresholds, "verification_min": verification_min},
			"node": node_id,
			"purpose": purpose,
		}

		if not meets:
			score = min(1.0, max(0.0, (signals["fz1"] + signals["coherence"]) / 2.0))
			return GateDecision(
				decision="HOLD",
				reason="insufficient_signals",
				score=score,
				details=details,
			)

		score = min(1.0, max(0.0, sum(signals.values()) / (len(signals) * 1.0)))
		return GateDecision(
			decision="ALLOW",
			reason="ok_safe",
			score=score,
			details=details,
		)

	# ------------------------------------------------------------------
	# Helpers
	# ------------------------------------------------------------------
	def _synth_signals(
		self, node: Mapping[str, Any], ctx: Mapping[str, Any]
	) -> Dict[str, float]:
		modality = str(node.get("modality", "vision")).lower()
		base = 0.68 if modality == "audio" else 0.72
		safe_bonus = 0.05 if ctx.get("safe_mode") else 0.0
		redaction = str(node.get("redaction", "edge")).lower()
		redaction_bonus = 0.04 if redaction == "edge" else -0.08

		fz1 = max(0.0, min(1.0, base + safe_bonus + redaction_bonus))
		coherence = max(0.0, min(1.0, base + safe_bonus))
		ethos = 0.88
		verification = max(0.0, min(1.0, 0.70 + safe_bonus - 0.02))

		return {
			"fz1": round(fz1, 3),
			"coherence": round(coherence, 3),
			"ethos": round(ethos, 3),
			"verification": round(verification, 3),
		}

	def _deny(self, reason: str) -> GateDecision:
		return GateDecision(
			decision="DENY",
			reason=reason,
			score=0.0,
			details={"thresholds": self.thresholds},
		)

	def _hold(self, reason: str) -> GateDecision:
		return GateDecision(
			decision="HOLD",
			reason=reason,
			score=0.0,
			details={"thresholds": self.thresholds},
		)


# ----------------------------------------------------------------------
# Virtual submodule export
# ----------------------------------------------------------------------
_gatekeeper_module = ModuleType(__name__ + ".gatekeeper")
setattr(_gatekeeper_module, "GateDecision", GateDecision)
setattr(_gatekeeper_module, "Gatekeeper", Gatekeeper)
setattr(_gatekeeper_module, "__all__", ["GateDecision", "Gatekeeper"])
sys.modules[_gatekeeper_module.__name__] = _gatekeeper_module


__all__ = ["GateDecision", "Gatekeeper"]
