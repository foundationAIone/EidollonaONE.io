from __future__ import annotations
from typing import Any

def se41_to_dict(sig: Any) -> dict:
    if hasattr(sig, "to_dict"):
        return sig.to_dict()
    if hasattr(sig, "__dict__"):
        return dict(sig.__dict__)
    return dict(sig)
