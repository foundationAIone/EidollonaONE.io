"""Unified exports for SE41 bot collection (canonical namespace).

All bot families (trading bots, social_bots, autobots) live under this package.
"""

from importlib import import_module
from .arbitrage_bot import create_bot as create_arbitrage_bot, ArbitrageBot  # type: ignore
from .crypto_bot import create_bot as create_crypto_bot, CryptoBot  # type: ignore
from .forex_bot import create_bot as create_forex_bot, ForexBot  # type: ignore
from .futures_bot import create_bot as create_futures_bot, FuturesBot  # type: ignore
from .options_bot import create_bot as create_options_bot, OptionsBot  # type: ignore
from .stock_bot import create_bot as create_stock_bot, StockBot  # type: ignore
from .dca_bot import create_bot as create_dca_bot, DCABot  # type: ignore
from .grid_trading_bot import create_bot as create_grid_trading_bot, GridTradingBot  # type: ignore
from .volatility_bot import create_bot as create_volatility_bot, VolatilityBot  # type: ignore
from .black_scholes_bot import create_bot as create_black_scholes_bot, BlackScholesBot  # type: ignore
from .sentiment_bot import create_bot as create_sentiment_bot, SentimentBot  # type: ignore

# Re-export commonly used Autobots symbols at the package root for convenience
try:
    _autobots = import_module(".autobots", __name__)
    TaskExecutorBot = getattr(_autobots, "TaskExecutorBot", None)
    AutobotCoordinator = getattr(_autobots, "AutobotCoordinator", None)
    GovernanceGate = getattr(_autobots, "GovernanceGate", None)
    BotCapabilities = getattr(_autobots, "BotCapabilities", None)
    Task = getattr(_autobots, "Task", None)
    TaskPriority = getattr(_autobots, "TaskPriority", None)
except Exception:  # keep imports light if optional
    TaskExecutorBot = AutobotCoordinator = GovernanceGate = None
    BotCapabilities = Task = TaskPriority = None

__all__ = [
    "create_arbitrage_bot",
    "ArbitrageBot",
    "create_crypto_bot",
    "CryptoBot",
    "create_forex_bot",
    "ForexBot",
    "create_futures_bot",
    "FuturesBot",
    "create_options_bot",
    "OptionsBot",
    "create_stock_bot",
    "StockBot",
    "create_dca_bot",
    "DCABot",
    "create_grid_trading_bot",
    "GridTradingBot",
    "create_volatility_bot",
    "VolatilityBot",
    "create_black_scholes_bot",
    "BlackScholesBot",
    "create_sentiment_bot",
    "SentimentBot",
    # Autobots convenience exports
    "TaskExecutorBot",
    "AutobotCoordinator",
    "GovernanceGate",
    "BotCapabilities",
    "Task",
    "TaskPriority",
]
