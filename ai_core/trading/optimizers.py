"""SymbolicEquation-guided portfolio optimizers."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, MutableMapping, Sequence, Tuple

from symbolic_core.symbolic_equation import SymbolicEquation41

__all__ = ["build_portfolio_qubo"]

_EQ = SymbolicEquation41()


def _mean(values: Iterable[float]) -> float:
	vals = list(values)
	if not vals:
		return 0.0
	return sum(vals) / float(len(vals))


def build_portfolio_qubo(
	prices: Mapping[str, float],
	covariance: Mapping[Tuple[str, str], float],
	constraints: Mapping[str, Mapping[str, float] | float],
) -> Tuple[Dict[Tuple[int, int], float], Sequence[str]]:
	"""Construct a basic QUBO matrix for binary asset selection.

	The construction leans on SymbolicEquation41 signals to balance coherence
	(rewarding expected return), risk, liquidity, and turnover penalties. The
	returned tuple contains the upper-triangular QUBO and the asset ordering
	used for indexing.
	"""

	if not prices:
		return {}, []

	ordering = list(dict.fromkeys(prices.keys()))

	raw_expected = constraints.get("expected_returns")
	expected_returns = dict(raw_expected) if isinstance(raw_expected, Mapping) else {}

	raw_liquidity = constraints.get("liquidity")
	liquidity = dict(raw_liquidity) if isinstance(raw_liquidity, Mapping) else {}

	raw_turnover = constraints.get("turnover")
	turnover = dict(raw_turnover) if isinstance(raw_turnover, Mapping) else {}

	raw_budget = constraints.get("budget")
	if isinstance(raw_budget, Mapping):
		budget = max(1.0, _mean(float(v) for v in raw_budget.values()))
	elif raw_budget is None:
		budget = float(max(1, len(ordering) // 2 or 1))
	else:
		budget = max(1.0, float(raw_budget))

	context = {
		"coherence_hint": _mean(expected_returns.values()) or 0.02,
		"risk_hint": _mean(v for k, v in covariance.items() if k[0] == k[1]) or 0.05,
		"uncertainty_hint": _mean(turnover.values()) or 0.1,
		"mirror": {"consistency": max(0.5, min(1.0, _mean(liquidity.values()) or 0.8))},
		"metadata": {"assets": len(ordering), "budget": budget},
	}
	signals = _EQ.evaluate(context).to_dict()

	# Strength parameters derived from symbolic signals
	reward_scale = max(0.1, signals.get("coherence", 0.5))
	risk_scale = max(0.1, signals.get("risk", 0.2))
	uncertainty_scale = max(0.1, signals.get("uncertainty", 0.3))
	liquidity_scale = signals.get("mirror_consistency", 0.75)

	qubo: MutableMapping[Tuple[int, int], float] = {}

	def cov_lookup(i: str, j: str) -> float:
		if (i, j) in covariance:
			return float(covariance[(i, j)])
		if (j, i) in covariance:
			return float(covariance[(j, i)])
		return 0.0

	for idx, sym_i in enumerate(ordering):
		ret_i = float(expected_returns.get(sym_i, 0.01))
		liq_i = float(liquidity.get(sym_i, 1.0))
		turn_i = float(turnover.get(sym_i, 0.0))
		risk_i = abs(cov_lookup(sym_i, sym_i))

		# Diagonal rewards (negative energy encourages selection)
		diag = (
			-reward_scale * ret_i
			- liquidity_scale * 0.05 * liq_i
			+ risk_scale * risk_i
			+ uncertainty_scale * abs(turn_i)
		)
		qubo[(idx, idx)] = diag

		for jdx in range(idx + 1, len(ordering)):
			sym_j = ordering[jdx]
			cov = cov_lookup(sym_i, sym_j)
			turn_j = float(turnover.get(sym_j, 0.0))
			# Coupling penalizes selecting pairs with high covariance/turnover
			coupling = risk_scale * cov + uncertainty_scale * 0.5 * (abs(turn_i) + abs(turn_j))
			qubo[(idx, jdx)] = coupling

	# Soft budget constraint: encourage exactly `budget` picks.
	penalty = max(0.1, risk_scale) * 2.0
	target = max(1.0, budget)
	for idx in range(len(ordering)):
		qubo[(idx, idx)] = qubo.get((idx, idx), 0.0) + penalty
		for jdx in range(idx + 1, len(ordering)):
			qubo[(idx, jdx)] = qubo.get((idx, jdx), 0.0) - (penalty / target)

	return dict(qubo), ordering
