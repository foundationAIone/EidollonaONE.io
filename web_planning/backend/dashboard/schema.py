from __future__ import annotations

from typing import Literal, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, conlist, constr
from pydantic import field_validator, model_validator
import time


# -------------------------
# Common types & constants
# -------------------------

# Conservative widget-id format (compatible with existing "w_..." ids)
WIDGET_ID_RE = r"^[A-Za-z0-9_\-:.]{3,64}$"
WidgetId = constr(pattern=WIDGET_ID_RE, min_length=3, max_length=64)  # type: ignore

# Idempotency keys: simple, URL/header-safe
IdemKey = constr(pattern=r"^[A-Za-z0-9_\-:.]{1,64}$", min_length=1, max_length=64)  # type: ignore

WidgetType = Literal["kpi", "line_chart", "table", "html"]


# -------------------------
# Widget models
# -------------------------


class _BaseWidget(BaseModel):
    """Shared, optional id field so server can upsert/replace deterministically."""

    id: Optional[WidgetId] = None

    class Config:
        extra = "forbid"  # reject unknown keys early


class KPI(_BaseWidget):
    type: Literal["kpi"]
    title: constr(strip_whitespace=True, min_length=1, max_length=80)  # type: ignore
    value: float
    unit: Optional[constr(max_length=12)] = None  # type: ignore


class LineChart(_BaseWidget):
    type: Literal["line_chart"]
    title: constr(strip_whitespace=True, min_length=1, max_length=80)  # type: ignore
    # Points are lightweight dicts (e.g., {"x":"10:00","y":3.1})
    data: conlist(Dict[str, Union[float, str]], min_length=1, max_length=2000)  # type: ignore
    xKey: constr(min_length=1, max_length=24)  # type: ignore
    yKey: constr(min_length=1, max_length=24)  # type: ignore

    @field_validator("data")
    def _non_empty_points(cls, v):
        # Fast guard: ensure dict-like points
        for i, pt in enumerate(v):
            if not isinstance(pt, dict):
                raise ValueError(f"point #{i} is not an object")
        return v


class TableColumn(BaseModel):
    key: constr(strip_whitespace=True, min_length=1, max_length=48)  # type: ignore
    label: constr(strip_whitespace=True, min_length=1, max_length=80)  # type: ignore

    class Config:
        extra = "forbid"


class Table(_BaseWidget):
    type: Literal["table"]
    title: constr(strip_whitespace=True, min_length=1, max_length=80)  # type: ignore
    columns: conlist(TableColumn, min_length=1, max_length=40)  # type: ignore
    rows: conlist(Dict[str, Any], min_length=0, max_length=2000)  # type: ignore
    pageSize: Optional[int] = Field(50, ge=1, le=1000)
    total: Optional[int] = Field(None, ge=0)

    @field_validator("rows")
    def _rows_are_objects(cls, v):
        for i, r in enumerate(v):
            if not isinstance(r, dict):
                raise ValueError(f"row #{i} is not an object")
        return v


class HTML(_BaseWidget):
    type: Literal["html"]
    title: Optional[constr(max_length=80)] = None  # type: ignore
    html: constr(min_length=1, max_length=200_000)  # type: ignore


Widget = Union[KPI, LineChart, Table, HTML]


# -------------------------
# Push request
# -------------------------


class PushRequest(BaseModel):
    op: Literal["add", "remove", "clear", "replace", "upsert"]
    widget: Optional[Widget] = None
    widget_id: Optional[WidgetId] = None
    idempotency_key: Optional[IdemKey] = None
    ts: float = Field(default_factory=lambda: time.time())

    class Config:
        extra = "forbid"

    @model_validator(mode="after")
    def _op_specific_requirements(self):
        op = self.op
        widget = self.widget
        widget_id = self.widget_id

        if op in ("add", "replace", "upsert"):
            if widget is None:
                raise ValueError(f"widget required for op={op!r}")
            if op == "replace" and not (widget_id or getattr(widget, "id", None)):
                raise ValueError("widget_id or widget.id required for op='replace'")

        elif op == "remove":
            if not (widget_id or (widget and getattr(widget, "id", None))):
                raise ValueError("widget_id (or widget.id) required for op='remove'")

        elif op == "clear":
            if widget is not None:
                raise ValueError("widget must be null for op='clear'")

        return self
