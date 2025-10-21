"""Decorator utilities enforcing SE gating for bot decisions."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from .se_contract import get_se_context, se_guard
from utils.audit import audit_ndjson


def se_required(decision_event: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorate bot methods so they only run when the SE contract passes."""

    def _wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def inner(self, *args: Any, **kwargs: Any) -> Any:
            context = get_se_context()
            ok, reasons = se_guard(context, getattr(self, "policy", {}))
            if not ok:
                audit_ndjson(
                    decision_event,
                    bot=getattr(self, "name", func.__name__),
                    decision="HOLD",
                    reasons=reasons,
                    se=context.__dict__,
                )
                return None
            return func(self, context, *args, **kwargs)

        return inner

    return _wrap
