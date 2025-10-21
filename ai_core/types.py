from __future__ import annotations
from enum import Enum, auto

class TradeType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP = auto()

class MarketType(Enum):
    SPOT = auto()
    FUTURES = auto()
    OPTIONS = auto()
    FOREX = auto()
    CRYPTO = auto()

class RiskLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
