"""Deprecation shim for historical mis-spelling imports.

Use: from ai_core.serplus.policy_engine import compute_policy
This module exists only to prevent hard import failures and will be
removed after refactor stabilization.
"""

import warnings
from ai_core.serplus.policy_engine import (
    PolicyInputs,
    PolicyDecision,
    compute_policy,
)  # re-export

warnings.warn(
    "Importing ai_core.currency.serplus_alias is deprecated; use ai_core.serplus.policy_engine instead",
    DeprecationWarning,
)

__all__ = ["PolicyInputs", "PolicyDecision", "compute_policy"]
