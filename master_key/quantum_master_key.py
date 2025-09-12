"""quantum_master_key

Deterministic (pseudo) quantum-inspired master key abstraction used to seed
and fingerprint a running symbolic environment.  This is *not* cryptographic;
it supplies stable IDs & capability flags for coordination across subsystems.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import hashlib
import os
import time
import socket
import logging


@dataclass(frozen=True)
class MasterKey:
    fingerprint: str  # stable hash fingerprint
    seed: int  # integer seed derived from entropy mix
    created_at: float  # epoch seconds
    capabilities: Dict[str, bool]  # feature flags
    meta: Dict[str, Any]  # auxiliary descriptive metadata

    def short(self) -> str:
        return self.fingerprint[:12]


_MASTER_KEY_SINGLETON: Optional[MasterKey] = None
_LOGGER = logging.getLogger(__name__ + ".master_key")


def _entropy_mix() -> bytes:
    host = socket.gethostname()
    pid = os.getpid()
    now = int(time.time())
    monotonic = int(time.monotonic() * 1_000_000)
    payload = f"{host}|{pid}|{now}|{monotonic}".encode("utf-8")
    return hashlib.sha256(payload).digest()


def _derive_seed(entropy: bytes) -> int:
    return int.from_bytes(entropy[:8], "big") & 0x7FFF_FFFF


def _capabilities(seed: int) -> Dict[str, bool]:
    # Simple deterministic toggles; can evolve.
    return {
        "symbolic_v41": True,
        "embodiment_pipeline_ready": (seed % 3 != 0),
        "governance_signals": True,
        "finance_gate": (seed % 5 != 0),
    }


def _meta(entropy: bytes) -> Dict[str, Any]:
    return {
        "algorithm": "master-key-v1",
        "entropy_hex_prefix": entropy.hex()[:16],
        "hostname": socket.gethostname(),
    }


def generate_master_key(force: bool = False) -> MasterKey:
    global _MASTER_KEY_SINGLETON
    if _MASTER_KEY_SINGLETON is not None and not force:
        return _MASTER_KEY_SINGLETON
    entropy = _entropy_mix()
    seed = _derive_seed(entropy)
    fingerprint = hashlib.sha256(entropy + b"|MASTER").hexdigest()
    mk = MasterKey(
        fingerprint=fingerprint,
        seed=seed,
        created_at=time.time(),
        capabilities=_capabilities(seed),
        meta=_meta(entropy),
    )
    _MASTER_KEY_SINGLETON = mk
    _LOGGER.info("Generated MasterKey %s", mk.short())
    return mk


def get_master_key() -> MasterKey:
    return generate_master_key()


__all__ = ["MasterKey", "get_master_key", "generate_master_key"]
