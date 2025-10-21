"""Citadel room routing for SE4.3 (Wings/Aletheia).

The router maps avatars to their canonical Citadel rooms and exposes helpers to
fetch metadata for HUD/web surfaces. All configuration lives in
``config/citadel.yml`` and is loaded lazily with caching.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

try:  # PyYAML optional in minimal shells
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    from utils.audit import audit_ndjson
except Exception:  # pragma: no cover
    def audit_ndjson(event: str, **payload: Any) -> None:  # type: ignore
        return None

from avatar.registry import AvatarProfile, AvatarRegistry, get_registry

__all__ = ["CitadelRoom", "CitadelRouter", "get_router"]


@dataclass
class CitadelRoom:
    id: str
    label: str
    avatar: str
    modules: List[str] = field(default_factory=list)
    routes: List[str] = field(default_factory=list)
    gate_focus: List[str] = field(default_factory=list)
    bots: List[str] = field(default_factory=list)
    tier: str = "support"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "avatar": self.avatar,
            "modules": list(self.modules),
            "routes": list(self.routes),
            "gate_focus": list(self.gate_focus),
            "bots": list(self.bots),
            "tier": self.tier,
            "metadata": copy.deepcopy(self.metadata),
        }


class CitadelRouter:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path or "config/citadel.yml")
        self._meta: Dict[str, Any] = {}
        self._rooms: Dict[str, CitadelRoom] = {}
        self._pinnacle: Optional[CitadelRoom] = None
        self._courtyard: Optional[Dict[str, Any]] = None
        self.reload()

    # ------------------------------------------------------------------
    def reload(self) -> None:
        data = self._read_config()
        registry = get_registry()
        self._meta = data.get("meta", {})
        self._rooms = {}

        pinnacle_cfg = data.get("pinnacle") or {}
        if pinnacle_cfg:
            self._pinnacle = self._normalize_room(pinnacle_cfg, registry, origin="pinnacle")
        else:
            self._pinnacle = None

        courtyard_cfg = data.get("courtyard") or {}
        self._courtyard = copy.deepcopy(courtyard_cfg) if courtyard_cfg else None

        for entry in data.get("rooms", []) or []:
            if not isinstance(entry, dict):
                continue
            room = self._normalize_room(entry, registry, origin="room")
            self._rooms[room.id] = room

        audit_ndjson(
            "citadel_router_reload",
            rooms=len(self._rooms),
            pinnacle=self._pinnacle.id if self._pinnacle else None,
            courtyard=bool(self._courtyard),
            path=str(self._path),
        )

    # ------------------------------------------------------------------
    def pinnacle(self) -> Optional[CitadelRoom]:
        return self._pinnacle

    def courtyard(self) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._courtyard) if self._courtyard else None

    def room(self, room_id: str) -> Optional[CitadelRoom]:
        return self._rooms.get(str(room_id))

    def by_avatar(self, avatar_id: str) -> Optional[CitadelRoom]:
        avatar_id = str(avatar_id)
        if self._pinnacle and self._pinnacle.avatar == avatar_id:
            return self._pinnacle
        for room in self._rooms.values():
            if room.avatar == avatar_id or avatar_id in room.bots:
                return room
        return None

    def summary(self) -> Dict[str, Any]:
        return {
            "pinnacle": self._pinnacle.to_dict() if self._pinnacle else None,
            "courtyard": copy.deepcopy(self._courtyard),
            "rooms": {rid: room.to_dict() for rid, room in self._rooms.items()},
            "meta": copy.deepcopy(self._meta),
        }

    # ------------------------------------------------------------------
    def _read_config(self) -> Dict[str, Any]:
        if not self._path.exists():
            return {}
        text = self._path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        if yaml is not None:
            return dict(yaml.safe_load(text) or {})
        import json

        return dict(json.loads(text))

    def _normalize_room(
        self,
        cfg: Mapping[str, Any],
        registry: AvatarRegistry,
        *,
        origin: str,
    ) -> CitadelRoom:
        avatar_id = str(cfg.get("avatar") or cfg.get("id") or "")
        profile: Optional[AvatarProfile] = registry.get(avatar_id)
        tier = profile.tier if profile else str(cfg.get("tier") or "support")
        modules = list(cfg.get("modules") or (profile.modules if profile else []))
        routes = [str(r) for r in cfg.get("routes", [])]
        gate_focus = [str(g) for g in cfg.get("gate_focus", [])]
        bots = [str(b) for b in cfg.get("bots", [])]
        metadata = {
            "origin": origin,
            "audit_stream": cfg.get("audit_stream") or self._meta.get("audit_stream"),
        }
        if profile:
            metadata.setdefault("avatar_label", profile.label)
            metadata.setdefault("avatar_origin", profile.origin)
            if profile.group:
                metadata.setdefault("avatar_group", profile.group)
            metadata.setdefault("avatar_modules", list(profile.modules))
        return CitadelRoom(
            id=str(cfg.get("id") or avatar_id or origin),
            label=str(cfg.get("label") or (profile.label if profile else avatar_id.title())),
            avatar=avatar_id,
            modules=modules,
            routes=routes,
            gate_focus=gate_focus,
            bots=bots,
            tier=tier,
            metadata=metadata,
        )


_ROUTER: Optional[CitadelRouter] = None


def get_router(force_reload: bool = False) -> CitadelRouter:
    global _ROUTER
    if _ROUTER is None or force_reload:
        _ROUTER = CitadelRouter()
    return _ROUTER
