# -*- coding: utf-8 -*-
"""
Broadcast Controller (SAFE simulated)
- Orchestrates 3-layer broadcast: symbolic -> quantum -> EM.
- Strict SAFE_MODE and two-stage approval via common.safe_mode.
"""
from __future__ import annotations
from typing import Dict, Any, List
import json
import os
import time
from common.safe_mode import require_approval
from .symbolic_packet_builder import build_symbolic_packet
from .quantum_entanglement_engine import QuantumEntanglementEngine
from .electromagnetic_sync import ElectromagneticSync
from .entity_contact_manager import EntityContactManager
from .archetype_directory import get_archetype_by_id
from .logs.broadcast_history_manager import append_event


class BroadcastController:
    """SAFE orchestrator for symbolic->quantum->EM broadcast (simulation only)."""

    def __init__(self):
        self.qengine = QuantumEntanglementEngine()
        self.emsync = ElectromagneticSync()
        self.contacts = EntityContactManager()
        # Load defaults
        try:
            cfg_path = os.path.join(
                os.path.dirname(__file__), "configs", "broadcast_config.json"
            )
            with open(cfg_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception:
            self.config = {"max_retries": 3}

    def plan_broadcast(
        self,
        target_ids: List[str],
        mandate: str,
        ethos: Dict[str, Any],
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return a plan summary and queued approval for broadcast."""
        steps: List[Dict[str, Any]] = []
        for tid in target_ids:
            tgt = self.contacts.sanitize_target(get_archetype_by_id(tid))
            valid_info = self.contacts.validate(tgt)
            if not valid_info["valid"]:
                append_event(
                    {
                        "mode": "validation",
                        "status": "invalid_target",
                        "target": tid,
                        "reasons": valid_info.get("reasons", []),
                    }
                )
                # Skip invalid targets in planning; still include a note
                continue
            steps.append({"mode": "symbolic", "target": tgt})
            steps.append({"mode": "quantum", "target": tgt})
            steps.append({"mode": "em", "target": tgt})
        packet = build_symbolic_packet(mandate, ethos, state)
        approval = require_approval(
            "broadcast", {"targets": target_ids, "packet_type": packet.get("type")}
        )
        return {"packet": packet, "steps": steps, "approval": approval}

    def execute_simulation(
        self, steps: List[Dict[str, Any]], packet: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute simulated steps without side effects; always uses approvals path."""
        results: List[Dict[str, Any]] = []
        for step in steps:
            mode = step.get("mode")
            target = step.get("target", {})
            if mode == "symbolic":
                evt = {
                    "mode": mode,
                    "status": "prepared",
                    "target": target.get("id"),
                    "ts": int(time.time() * 1000),
                }
                append_event(evt)
                results.append(evt)
            elif mode == "quantum":
                self.qengine.establish_link(packet)
                attempt = 0
                maxr = int(self.config.get("max_retries", 3))
                while True:
                    out = self.qengine.deliver(packet, target)
                    append_event(
                        {
                            "mode": mode,
                            **out,
                            "target": target.get("id"),
                            "attempt": attempt,
                        }
                    )
                    results.append(out)
                    if out.get("approved") is False or attempt >= maxr:
                        break
                    attempt += 1
            elif mode == "em":
                out = self.emsync.lock(target)
                append_event({"mode": mode, **out, "target": target.get("id")})
                results.append(out)
            else:
                results.append({"mode": mode, "status": "skipped"})
        return results
