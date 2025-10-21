"""Lightweight accessors for symbolic helpers."""

from .se41_ext import clamp01, ethos_avg, ouroboros_score, road_map
from .se_loader import SE42Loader, load_se42_config

try:  # Optional Wings/Aletheia helpers
	from .se43_wings import (
		SE43Signals,
		SymbolicEquation43,
		WingsAletheia,
		assemble_se43_context,
	)
except Exception:  # pragma: no cover - keep optional
	SE43Signals = None  # type: ignore[assignment]
	SymbolicEquation43 = None  # type: ignore[assignment]
	WingsAletheia = None  # type: ignore[assignment]
	assemble_se43_context = None  # type: ignore[assignment]

try:
	from .se_loader_ext import load_se_engine
except Exception:  # pragma: no cover
	load_se_engine = None  # type: ignore[assignment]

__all__ = [
	"clamp01",
	"ethos_avg",
	"ouroboros_score",
	"road_map",
	"SE42Loader",
	"load_se42_config",
	"SymbolicEquation43",
	"SE43Signals",
	"WingsAletheia",
	"assemble_se43_context",
	"load_se_engine",
]

