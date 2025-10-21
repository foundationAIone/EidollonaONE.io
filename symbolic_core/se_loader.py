"""Symbolic Equation 4.2 loader utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

from symbolic_core.audit_bridge import audit_ndjson

from .se42_duodecimal import SE42Signals, SE42_VERSION, SymbolicEquation42Lotus

try:  # Optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback when PyYAML absent
    yaml = None  # type: ignore

__all__ = ["SE42Loader", "load_se42_config", "SymbolicEquation42Lotus", "SE42Signals"]

_DEFAULT_CONFIG_PATH = Path("config/se42.yml")


def load_se42_config(path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """Load the SE4.2 configuration from YAML/JSON.

    The loader degrades gracefully when PyYAML is unavailable by expecting the
    file to contain JSON (valid YAML subset).
    """

    cfg_path = Path(path or _DEFAULT_CONFIG_PATH)
    if not cfg_path.exists():
        raise FileNotFoundError(f"SE4.2 config missing at {cfg_path}")
    text = cfg_path.read_text(encoding="utf-8")
    data: Dict[str, Any]
    if yaml is not None:
        parsed = yaml.safe_load(text)
        data = dict(parsed or {})
    else:
        data = json.loads(text or "{}")
    data.setdefault("version", SE42_VERSION)
    return data


class SE42Loader:
    """Convenience wrapper that owns the SE4.2 Lotus engine and config."""

    def __init__(self, *, config_path: Optional[Union[Path, str]] = None, audit_event: Optional[str] = None) -> None:
        self.config_path = Path(config_path or _DEFAULT_CONFIG_PATH)
        self.config = load_se42_config(self.config_path)
        event = audit_event or self.config.get("audit", {}).get("event", "se42_eval")
        self.engine = SymbolicEquation42Lotus(self.config, audit_event=event)
        audit_ndjson(
            "se42_loader_init",
            config_path=str(self.config_path),
            version=self.config.get("version", SE42_VERSION),
            audit_event=event,
        )
        audit_ndjson(
            "se_upgrade",
            stage="loader",
            version=self.config.get("version", SE42_VERSION),
        )

    def evaluate(self, ctx: Optional[Mapping[str, Any]] = None) -> SE42Signals:
        return self.engine.evaluate(ctx)

    def evaluate_dict(self, ctx: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        return self.engine.evaluate_dict(ctx)

    def reload(self) -> None:
        """Reload configuration from disk and reset the engine."""

        self.config = load_se42_config(self.config_path)
        event = self.config.get("audit", {}).get("event", "se42_eval")
        self.engine = SymbolicEquation42Lotus(self.config, audit_event=event)
        audit_ndjson(
            "se42_loader_reload",
            config_path=str(self.config_path),
            version=self.config.get("version", SE42_VERSION),
            audit_event=event,
        )

    def phase_map(self) -> Dict[str, Any]:
        """Return a map of phase labels and the latest base-12 vector."""

        signals = self.engine.evaluate_dict({})
        base12 = signals.get("base12", {})
        return {
            "labels": self.engine.phase_labels(),
            "vector": list(base12.get("vector", [])),
            "index": base12.get("index", 0),
            "trace": base12.get("trace", "0.000"),
        }
