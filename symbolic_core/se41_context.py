"""Legacy import shim for SE41 context assembly.

Preferred modern imports:
  - from eidollona_core.se41_interface import assemble_se41_context
  - from symbolic_core.context_builder import assemble_se41_context

This module keeps older import paths working while providing the same behavior.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, Mapping, Optional, cast

try:  # Canonical dual-surface package
	from eidollona_core.se41_interface import (  # type: ignore
		assemble_se41_context as __ASSEMBLE_IMPL,
	)
	__IMPL_SRC = "eidollona_core.se41_interface"
except Exception:  # pragma: no cover - optional dependency
	try:
		from symbolic_core.context_builder import (  # type: ignore
			assemble_se41_context as __ASSEMBLE_IMPL,
		)
		__IMPL_SRC = "symbolic_core.context_builder"
	except Exception:  # pragma: no cover - optional dependency
		__ASSEMBLE_IMPL = None
		__IMPL_SRC = "fallback"

if "__ASSEMBLE_IMPL" not in globals():
	__ASSEMBLE_IMPL = None  # type: ignore[assignment]
if "__IMPL_SRC" not in globals():
	__IMPL_SRC = "fallback"


def _clip01(x: float) -> float:
	return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _f(x: Any, default: float) -> float:
	"""Float coercion with a safe default."""
	try:
		return float(x)
	except (TypeError, ValueError):
		return float(default)


def _deep_update(dst: Dict[str, Any], src: Mapping[str, Any]) -> Dict[str, Any]:
	"""Deep merge: nested dicts are merged recursively."""
	for key, value in src.items():
		if isinstance(value, Mapping) and isinstance(dst.get(key), dict):
			_deep_update(dst[key], value)  # type: ignore[index]
		else:
			dst[key] = value
	return dst


def assemble_se41_context(
	coherence_hint: float = 0.81,
	risk_hint: float = 0.12,
	uncertainty_hint: float = 0.28,
	mirror_consistency: float = 0.74,
	s_em: float = 0.83,
	*args: Any,
	t: Optional[float] = None,
	phase: Optional[float] = 0.0,
	cadence_spm: float = 108.0,
	step_len_m: float = 0.65,
	ethos_hint: Optional[Mapping[str, Any]] = None,
	authenticity: Optional[float] = None,
	integrity: Optional[float] = None,
	responsibility: Optional[float] = None,
	enrichment: Optional[float] = None,
	extras: Optional[Mapping[str, Any]] = None,
	clamp: bool = True,
	legacy_aliases: bool = False,
	**context: Any,
) -> Dict[str, Any]:
	"""Build a normalized dict context for SymbolicEquation41.evaluate.

	Prefers the canonical builder; if unavailable, uses a local safe fallback.
	"""

	# Prefer using module-level imports directly; no mutation of module globals here.

	if __ASSEMBLE_IMPL is not None:
		merged_extras: Optional[Dict[str, Any]] = None
		if context:
			inline = dict(context)
			merged_extras = (
				_deep_update(dict(extras or {}), inline)
				if extras is not None
				else inline
			)
		elif extras is not None:
			merged_extras = dict(extras)
		warnings.filterwarnings("once", category=DeprecationWarning)
		warnings.warn(
			f"assemble_se41_context imported via legacy shim; prefer `{__IMPL_SRC}`.",
			DeprecationWarning,
			stacklevel=2,
		)
		try:
			impl = cast(Any, __ASSEMBLE_IMPL)
			return impl(  # type: ignore[call-arg]
				coherence_hint=coherence_hint,
				risk_hint=risk_hint,
				uncertainty_hint=uncertainty_hint,
				mirror_consistency=mirror_consistency,
				s_em=s_em,
				t=t,
				phase=phase,
				cadence_spm=cadence_spm,
				step_len_m=step_len_m,
				ethos_hint=ethos_hint,
				authenticity=authenticity,
				integrity=integrity,
				responsibility=responsibility,
				enrichment=enrichment,
				extras=merged_extras,
				clamp=clamp,
				legacy_aliases=legacy_aliases,
			)
		except TypeError as exc:
			message = str(exc)
			if not any(
				keyword in message
				for keyword in ("phase", "cadence_spm", "step_len_m", "authenticity")
			):
				raise
			warnings.warn(
				(
					f"{__IMPL_SRC} signature rejected legacy parameters; "
					f"falling back to local builder."
				),
				RuntimeWarning,
				stacklevel=2,
			)
			# Fall back to local builder without mutating module-level globals.
			pass

	c01 = _clip01 if clamp else (lambda value: float(value))

	if ethos_hint is None:
		e_auth = c01(_f(authenticity, 0.92)) if authenticity is not None else 0.92
		e_integ = c01(_f(integrity, 0.90)) if integrity is not None else 0.90
		e_resp = c01(_f(responsibility, 0.89)) if responsibility is not None else 0.89
		e_enri = c01(_f(enrichment, 0.91)) if enrichment is not None else 0.91
		ethos: Dict[str, float] = {
			"authenticity": float(e_auth),
			"integrity": float(e_integ),
			"responsibility": float(e_resp),
			"enrichment": float(e_enri),
		}
	else:
		ethos = {
			"authenticity": c01(_f(ethos_hint.get("authenticity"), 0.92)),
			"integrity": c01(_f(ethos_hint.get("integrity"), 0.90)),
			"responsibility": c01(_f(ethos_hint.get("responsibility"), 0.89)),
			"enrichment": c01(_f(ethos_hint.get("enrichment"), 0.91)),
		}

	base: Dict[str, Any] = {
		"coherence_hint": c01(_f(coherence_hint, 0.81)),
		"risk_hint": c01(_f(risk_hint, 0.12)),
		"uncertainty_hint": c01(_f(uncertainty_hint, 0.28)),
		"mirror": {"consistency": c01(_f(mirror_consistency, 0.74))},
		"substrate": {"S_EM": c01(_f(s_em, 0.83))},
		"ethos_hint": ethos,
		"embodiment": {
			"phase": float(phase or 0.0),
			"cadence_spm": float(cadence_spm),
			"step_len_m": float(step_len_m),
		},
		"t": float(t if t is not None else (phase if phase is not None else 0.0)),
	}

	if context:
		inline_context = dict(context)
		mirror_ctx = inline_context.pop("mirror", None)
		if isinstance(mirror_ctx, Mapping):
			_deep_update(base.setdefault("mirror", {}), mirror_ctx)
		substrate_ctx = inline_context.pop("substrate", None)
		if isinstance(substrate_ctx, Mapping):
			_deep_update(base.setdefault("substrate", {}), substrate_ctx)
		perception = inline_context.pop("perception", None)
		if perception is not None:
			base["perception"] = perception
		memory = inline_context.pop("memory", None)
		if memory is not None:
			base["memory"] = memory
		intent_ctx = inline_context.pop("intent", None)
		if intent_ctx is not None:
			base["intent"] = intent_ctx
		extra_ctx = inline_context.pop("extra", None)
		if isinstance(extra_ctx, Mapping):
			_deep_update(base, extra_ctx)
		if inline_context:
			_deep_update(base, inline_context)

	if legacy_aliases:
		base["C_realize"] = base["coherence_hint"]
		try:
			ethos_min = min(float(value) for value in ethos.values()) if ethos else 0.0
		except Exception:
			ethos_min = 0.0
		base["FZ1"] = float(
			base["coherence_hint"]
			* base["mirror"]["consistency"]
			* base["substrate"]["S_EM"]
			* (1.0 - base["risk_hint"])
			* ethos_min
		)
		base["S_EM"] = base["substrate"]["S_EM"]

	if extras:
		_deep_update(base, extras)

	return base


assemble_se41_context_dict = assemble_se41_context


__all__ = ["assemble_se41_context", "assemble_se41_context_dict"]
