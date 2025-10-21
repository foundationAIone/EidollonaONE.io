"""SAFE RPM Ecosystem Manager used in tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class AvatarConfig:
    """Minimal avatar configuration for SAFE RPM tests."""

    name: str
    personality: str
    version: str = "1.0"


class EcosystemManager:
    """Provides a deterministic view over registered RPM avatars."""

    def __init__(self) -> None:
        self._avatars: Dict[str, AvatarConfig] = {}

    def register_avatar(self, config: AvatarConfig) -> None:
        self._avatars[config.name] = config

    def bulk_register(self, configs: Iterable[AvatarConfig]) -> None:
        for config in configs:
            self.register_avatar(config)

    def get_avatar(self, name: str) -> AvatarConfig:
        try:
            return self._avatars[name]
        except KeyError as exc:
            raise LookupError(f"Avatar '{name}' is not registered") from exc

    def list_avatars(self) -> List[AvatarConfig]:
        return list(self._avatars.values())

    def clear(self) -> None:
        self._avatars.clear()
