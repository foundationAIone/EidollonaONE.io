from __future__ import annotations

from fastapi import APIRouter

from .routes import router

__all__ = ["router", "APIRouter"]
