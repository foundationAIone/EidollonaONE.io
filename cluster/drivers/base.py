from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseDriver(ABC):
    name: str = "base"

    @abstractmethod
    def quote(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def submit(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def status(self, job_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def cancel(self, job_id: str) -> Dict[str, Any]:
        raise NotImplementedError


__all__ = ["BaseDriver"]
