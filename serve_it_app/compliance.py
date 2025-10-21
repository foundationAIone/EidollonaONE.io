from __future__ import annotations

from typing import Dict


TERMS_URL = "https://serveit.example.com/terms"
PRIVACY_URL = "https://serveit.example.com/privacy"
DISPUTE_WINDOW_DAYS = 14


def tos_url() -> str:
    return TERMS_URL


def privacy_url() -> str:
    return PRIVACY_URL


def dispute_policy() -> Dict[str, object]:
    return {
        "window_days": DISPUTE_WINDOW_DAYS,
        "evidence_required": ["before photo", "after photo", "service receipt"],
    }
