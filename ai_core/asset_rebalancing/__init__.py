"""Asset Rebalancing Toolkit (SE41 v4.1+ aligned)

Provides three complementary allocation engines:
	* mean_variance        – classical Markowitz / efficient frontier utilities
	* risk_parity          – volatility / marginal risk balanced weighting
	* black_litterman      – market equilibrium + subjective views fusion

Each module integrates light SE41 governance hooks (numeric synthesis + ethos
gate) without taking a hard runtime dependency: if SE41 helpers are absent the
optimizers still work with a safe fallback (no gate enforcement).

Design Notes:
	- No external heavy solvers; relies on numpy if available, else degraded
		approximate routines (uniform fallback or simple scaling).
	- All covariance matrices are softly regularized if near singular.
	- Ethos gate (ethos_decision) only blocks returning new weights when it
		explicitly denies; on hold it returns prior/current weights if supplied.
"""

from .mean_variance import (
    mean_variance_optimize,
    efficient_frontier,
    rebalance_threshold,
)
from .risk_parity import risk_parity_weights, risk_parity_iterative
from .black_litterman import (
    black_litterman_posterior,
    black_litterman_weights,
)

__all__ = [
    # mean-variance
    "mean_variance_optimize",
    "efficient_frontier",
    "rebalance_threshold",
    # risk parity
    "risk_parity_weights",
    "risk_parity_iterative",
    # black-litterman
    "black_litterman_posterior",
    "black_litterman_weights",
]
