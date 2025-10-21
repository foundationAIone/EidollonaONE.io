from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
	from fastapi import APIRouter

	router: APIRouter


def __getattr__(name: str):
	if name == "router":
		from .api import router as _router

		return _router
	raise AttributeError(name)


__all__ = ("router",)
