"""Project brand metadata and currency descriptors."""

from __future__ import annotations

from typing import Dict

__all__ = [
    "BRANDS",
    "BRAND_FANCOMP",
    "BRAND_SERVEIT",
    "CURRENCY_NAME",
    "CURRENCY_TICKER",
]

BRAND_SERVEIT = "Serve-itApp"
BRAND_FANCOMP = "Fancompfoundation"

CURRENCY_NAME = "SerplusCurrency"
CURRENCY_TICKER = "SER"

BRANDS: Dict[str, str] = {
    "serveit": BRAND_SERVEIT,
    "fancomp": BRAND_FANCOMP,
}
