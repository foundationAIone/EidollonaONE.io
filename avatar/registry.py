"""Avatar registry loader for EidollonaONE (SE4.3 Wings/Aletheia).

Responsibilities
- Load tiered avatar definitions from ``config/avatars.yml``.
- Expand social/trading templates into concrete avatar entries per platform/strategy.
- Provide a cached registry that downstream modules (Citadel, HUD, avatar API)
  can query safely.
- Resolve wing visibility policy for presentation purposes (cognition wings remain ON).
- Emit NDJSON audit events for reloads and policy checks (logs/audit.ndjson).

SAFE posture
------------
All operations are workspace-local, deterministic, and devoid of PII storage.
The registry reads configuration only, constructs in-memory structures, and
writes audit lines for traceability.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

try:  # PyYAML is optional during constrained tests
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    from utils.audit import audit_ndjson
except Exception:  # pragma: no cover
    def audit_ndjson(event: str, **payload: Any) -> None:  # type: ignore
        return None

from types import SimpleNamespace

try:  # Prefer native SE4.3-aware wings policy when available
    from ai_core.ai_brain import AIBrain  # type: ignore
except Exception:  # pragma: no cover
    AIBrain = None  # type: ignore

__all__ = [
    "AvatarProfile",
    "AvatarRegistry",
    "get_registry",
    "resolve_wings_visibility",
]

_CONFIG_PATH = Path("config/avatars.yml")
_DEFAULT_POLICY = {
    "override": "auto",
    "show_if": {
        "readiness": "prime_ready",
        "wings_min": 1.03,
        "ra_min": 0.95,
        "risk_max": 0.06,
    },
    "hide_if": {"operator_focus": False, "risk_over": 0.08},
}


@dataclass
class AvatarProfile:
    """Materialized avatar definition exposed to the rest of the system."""

    id: str
    label: str
    tier: str
    persona: Dict[str, Any] = field(default_factory=dict)
    modules: List[str] = field(default_factory=list)
    default_room: Optional[str] = None
    readiness: Dict[str, Any] = field(default_factory=dict)
    connectors: Dict[str, Any] = field(default_factory=dict)
    wings_policy: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None
    origin: str = "tier"
    group: Optional[str] = None
    template: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "tier": self.tier,
            "persona": copy.deepcopy(self.persona),
            "modules": list(self.modules),
            "default_room": self.default_room,
            "readiness": copy.deepcopy(self.readiness),
            "connectors": copy.deepcopy(self.connectors),
            "wings_policy": copy.deepcopy(self.wings_policy),
            "notes": self.notes,
            "origin": self.origin,
            "group": self.group,
            "template": self.template,
            "metadata": copy.deepcopy(self.metadata),
        }


class AvatarRegistry:
    """Cached loader for avatar configuration with template expansion."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path or _CONFIG_PATH)
        self._mtime: Optional[float] = None
        self._avatars: Dict[str, AvatarProfile] = {}
        self._groups: Dict[str, List[str]] = {}
        self._raw: Dict[str, Any] = {}
        self.reload()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def reload(self) -> None:
        data = self._read_config()
        avatars: Dict[str, AvatarProfile] = {}
        groups: Dict[str, List[str]] = {}

        tiers = data.get("tiers") or {}
        for key, payload in tiers.items():
            profile = self._normalize_entry(payload, default_id=key, origin="tier")
            avatars[profile.id] = profile

        templates = data.get("templates") or {}
        group_cfg = data.get("groups") or {}
        for group_name, cfg in group_cfg.items():
            template_name = (cfg or {}).get("template")
            template_block = templates.get(template_name)
            if not isinstance(template_block, Mapping):
                continue
            defaults = cfg.get("defaults") or {}
            items = cfg.get("items") or []
            group_entries: List[str] = []
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                variables = self._build_variables(defaults, item)
                templated = self._format_structure(template_block, variables)
                merged = self._merge_dicts(templated, self._format_structure(defaults, variables))
                overrides = {
                    key: value
                    for key, value in item.items()
                    if isinstance(value, Mapping)
                }
                if overrides:
                    merged = self._merge_dicts(merged, overrides)
                profile = self._normalize_entry(
                    merged,
                    default_id=f"{template_name}_{len(group_entries)}",
                    origin="group",
                    group=group_name,
                    template=template_name,
                    variables=variables,
                )
                avatars[profile.id] = profile
                group_entries.append(profile.id)
            if group_entries:
                groups[group_name] = group_entries

        self._avatars = avatars
        self._groups = groups
        self._raw = data
        audit_ndjson(
            "avatar_registry_reload",
            avatars=len(avatars),
            groups=len(groups),
            path=str(self._path),
        )

    def get(self, avatar_id: str) -> Optional[AvatarProfile]:
        return self._avatars.get(str(avatar_id))

    def all(self) -> Dict[str, AvatarProfile]:
        return dict(self._avatars)

    def group_members(self, name: str) -> List[str]:
        return list(self._groups.get(name, []))

    def summary(self) -> Dict[str, Any]:
        return {
            "avatars": sorted(self._avatars.keys()),
            "groups": {k: list(v) for k, v in self._groups.items()},
            "source": str(self._path),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _read_config(self) -> Dict[str, Any]:
        if not self._path.exists():
            self._mtime = None
            return {}
        try:
            stat = self._path.stat()
            self._mtime = stat.st_mtime
        except Exception:  # pragma: no cover
            self._mtime = None
        text = self._path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        if yaml is not None:
            return dict(yaml.safe_load(text) or {})
        import json

        return dict(json.loads(text))

    @staticmethod
    def _ensure_list(values: Optional[Iterable[Any]]) -> List[Any]:
        if values is None:
            return []
        if isinstance(values, list):
            return list(values)
        return list(values)

    def _normalize_entry(
        self,
        payload: Mapping[str, Any],
        *,
        default_id: str,
        origin: str,
        group: Optional[str] = None,
        template: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> AvatarProfile:
        data = dict(payload)
        avatar_id = str(data.get("id") or default_id)
        label = str(data.get("label") or avatar_id.replace("_", " ").title())
        tier = str(data.get("tier") or "support")
        persona = dict(data.get("persona") or {})
        modules = [str(m) for m in self._ensure_list(data.get("modules"))]
        default_room = data.get("default_room")
        readiness = dict(data.get("readiness") or {})
        connectors = dict(data.get("connectors") or {})
        wings_policy = dict(data.get("wings_policy") or {})
        notes = data.get("notes")

        metadata = dict(data.get("metadata") or {})
        if variables:
            metadata.setdefault("variables", {})
            metadata["variables"].update(variables)
        metadata.setdefault("origin", origin)
        if group:
            metadata["group"] = group
        if template:
            metadata["template"] = template

        profile = AvatarProfile(
            id=avatar_id,
            label=label,
            tier=tier,
            persona=persona,
            modules=modules,
            default_room=default_room,
            readiness=readiness,
            connectors=connectors,
            wings_policy=wings_policy,
            notes=notes,
            origin=origin,
            group=group,
            template=template,
            metadata=metadata,
        )
        return profile

    @staticmethod
    def _merge_dicts(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = dict(copy.deepcopy(base))
        for key, value in overlay.items():
            if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
                result[key] = AvatarRegistry._merge_dicts(result[key], value)  # type: ignore[arg-type]
            elif isinstance(value, list) and isinstance(result.get(key), list):
                result[key] = list(result[key]) + list(value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def _build_variables(
        self,
        defaults: Mapping[str, Any],
        item: Mapping[str, Any],
    ) -> Dict[str, Any]:
        variables: Dict[str, Any] = {}
        for source in (defaults, item):
            for key, value in source.items():
                if isinstance(value, Mapping):
                    continue
                variables[key] = value
        enriched: Dict[str, Any] = {}
        for key, value in variables.items():
            if isinstance(value, str):
                slug = value.replace(" ", "_").replace("-", "_").lower()
                enriched[key] = value
                enriched[f"{key}_slug"] = slug
                enriched[f"{key}_title"] = value.replace("_", " ").title()
                enriched[f"{key}_upper"] = value.upper()
                enriched[f"{key}_lower"] = value.lower()
            else:
                enriched[key] = value
        return enriched

    def _format_structure(self, data: Any, variables: Mapping[str, Any]) -> Any:
        if isinstance(data, str):
            class _SafeDict(dict):
                def __missing__(self, key: str) -> str:
                    return "{" + key + "}"

            try:
                return data.format_map(_SafeDict(variables))
            except Exception:
                return data
        if isinstance(data, Mapping):
            return {k: self._format_structure(v, variables) for k, v in data.items()}
        if isinstance(data, list):
            return [self._format_structure(v, variables) for v in data]
        return copy.deepcopy(data)


_REGISTRY: Optional[AvatarRegistry] = None


def get_registry(force_reload: bool = False) -> AvatarRegistry:
    global _REGISTRY
    if _REGISTRY is None or force_reload:
        _REGISTRY = AvatarRegistry()
    return _REGISTRY


def resolve_wings_visibility(
    signals: Mapping[str, Any],
    policy_overrides: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Decide avatar wing visibility using SE4.3 policy thresholds."""

    policy = _merge_policy(policy_overrides)
    readiness = str(signals.get("readiness", ""))
    wings_val = float(signals.get("wings", 1.0) or 1.0)
    ra = float(signals.get("reality_alignment", 0.0) or 0.0)
    risk = float(signals.get("risk", 1.0) or 1.0)

    override = str(policy.get("override", "auto")).lower()
    show_if = policy.get("show_if", {})
    hide_if = policy.get("hide_if", {})

    def _num(key: str, default: float) -> float:
        try:
            return float(show_if.get(key, default))
        except Exception:
            return float(default)

    wings_min = _num("wings_min", _DEFAULT_POLICY["show_if"]["wings_min"]) if isinstance(show_if, Mapping) else _DEFAULT_POLICY["show_if"]["wings_min"]
    ra_min = _num("ra_min", _DEFAULT_POLICY["show_if"]["ra_min"]) if isinstance(show_if, Mapping) else _DEFAULT_POLICY["show_if"]["ra_min"]
    risk_max = _num("risk_max", _DEFAULT_POLICY["show_if"]["risk_max"]) if isinstance(show_if, Mapping) else _DEFAULT_POLICY["show_if"]["risk_max"]
    risk_over = float(hide_if.get("risk_over", _DEFAULT_POLICY["hide_if"]["risk_over"])) if isinstance(hide_if, Mapping) else 0.08
    operator_focus = bool(hide_if.get("operator_focus", False)) if isinstance(hide_if, Mapping) else False
    readiness_needed = str(show_if.get("readiness", _DEFAULT_POLICY["show_if"]["readiness"])).lower() if isinstance(show_if, Mapping) else "prime_ready"

    state = "hide"
    reason: List[str] = []

    if override == "show":
        state = "show"
        reason.append("override=show")
    elif override == "hide":
        state = "hide"
        reason.append("override=hide")
    else:
        if operator_focus:
            state = "hide"
            reason.append("operator_focus")
        elif risk > risk_over:
            state = "hide"
            reason.append("risk_over")
        elif readiness.lower() == readiness_needed:
            state = "show"
            reason.append("readiness")
        elif wings_val >= wings_min and ra >= ra_min and risk <= risk_max:
            state = "show"
            reason.append("thresholds")
        else:
            reason.append("policy_default")

    audit_ndjson(
        "avatar_wings_policy",
        state=state,
        readiness=readiness,
        wings=wings_val,
        reality_alignment=ra,
        risk=risk,
        override=override,
        readiness_needed=readiness_needed,
        wings_min=wings_min,
        ra_min=ra_min,
        risk_max=risk_max,
        risk_over=risk_over,
        operator_focus=operator_focus,
    )
    return {
        "state": state,
        "reason": reason,
        "policy": policy,
    }


def _merge_policy(overrides: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    policy = copy.deepcopy(_DEFAULT_POLICY)
    if overrides:
        for key, value in overrides.items():
            if key in {"show_if", "hide_if"} and isinstance(value, Mapping):
                merged = copy.deepcopy(policy[key])
                merged.update({k: v for k, v in value.items()})
                policy[key] = merged
            else:
                policy[key] = value
    return policy


if AIBrain is not None:
    _WINGS_ADVISOR = AIBrain()

    def resolve_wings_visibility(  # type: ignore[misc]
        signals: Mapping[str, Any],
        policy_overrides: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        policy = _merge_policy(policy_overrides)
        advisor = _WINGS_ADVISOR
        advisor._last_signals = SimpleNamespace(**signals)  # type: ignore[attr-defined]
        result = advisor.decide_wings_visibility(policy=policy)
        audit_ndjson(
            "avatar_wings_policy",
            state=result.get("state"),
            readiness=signals.get("readiness"),
            wings=signals.get("wings"),
            reality_alignment=signals.get("reality_alignment"),
            risk=signals.get("risk"),
            override=result.get("override"),
        )
        return result
