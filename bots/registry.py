"""Loader that instantiates all enabled SE-aware bots."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List

try:  # PyYAML is optional in minimal bring-up environments
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

from .base_se_bot import SEAwareBot


def load_bots(cfg_path: str = "config/bots.yml") -> List[SEAwareBot]:
    path = Path(cfg_path)
    if not path.exists():
        raise FileNotFoundError(f"Bot config not found: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        config = {}
    elif yaml is not None:
        config = yaml.safe_load(text) or {}
    else:
        import json

        config = json.loads(text)
    if not config.get("se_enforced", False):
        raise RuntimeError("SE enforcement must be enabled (config/bots.yml se_enforced: true)")
    bots_cfg: Dict[str, Any] = config.get("bots", {})
    policy_defaults: Dict[str, Any] = config.get("policy_defaults", {})
    instances: List[SEAwareBot] = []
    for name, settings in bots_cfg.items():
        if not isinstance(settings, dict) or not settings.get("enabled", False):
            continue
        module = importlib.import_module(f"bots.{name}")
        klass = None
        for attr in dir(module):
            candidate = getattr(module, attr)
            if inspect.isclass(candidate) and issubclass(candidate, SEAwareBot) and candidate is not SEAwareBot:
                klass = candidate
                break
        if klass is None:
            raise TypeError(f"Bot {name} must subclass SEAwareBot")
        policy = dict(policy_defaults)
        policy.update(settings)
        signature = inspect.signature(klass)
        if "name" in signature.parameters and "policy" in signature.parameters:
            instances.append(klass(name=name, policy=policy))
        else:
            instances.append(klass(policy=policy))  # type: ignore[call-arg]
    return instances
