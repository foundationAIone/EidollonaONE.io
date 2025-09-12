"""Black–Scholes / Black '76 pricing & Greeks (SE41 aligned).

Exports two tiers of Greeks:
- Base set from ``black_scholes_model`` (Greeks, B76Greeks)
- Extended higher‑order set from ``greeks_calculator`` (AdvancedGreeks)
"""

from .black_scholes_model import (
    price_bsm,
    greeks_bsm,
    parity_residual_bsm,
    implied_vol_bsm,
    price_black76,
    greeks_black76,
    Greeks,
    B76Greeks,
    se41_price_coherence,
)
from .greeks_calculator import (
    Greeks as AdvancedGreeks,
    greeks_black_scholes,
    greeks_black76 as greeks_black76_forward,
    finite_diff_greeks_bsm,
)
from .implied_volatility import (
    implied_volatility,
    IVResult as ImpliedVolResult,
)

__all__ = [
    "price_bsm",
    "greeks_bsm",
    "parity_residual_bsm",
    "implied_vol_bsm",
    "price_black76",
    "greeks_black76",
    "Greeks",
    "B76Greeks",
    "se41_price_coherence",
    # Extended
    "AdvancedGreeks",
    "greeks_black_scholes",
    "greeks_black76_forward",
    "finite_diff_greeks_bsm",
    "implied_volatility",
    "ImpliedVolResult",
]
