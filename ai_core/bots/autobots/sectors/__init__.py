"""
Sectors package: organizational layer for domain-specific adapters/constraints.

Exports a lightweight SectorConfig so autobots can request domain policy hints.
"""

from .sector_config import SectorConfig, get_default_sector_config

__all__ = ["SectorConfig", "get_default_sector_config"]
