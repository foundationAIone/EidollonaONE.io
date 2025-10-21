from __future__ import annotations
import os
from typing import Dict

def get_master_key() -> Dict[str, str]:
    return {"key": os.getenv("EID_QUANTUM_MASTER_KEY", "dev-local"), "version": "0.1"}
