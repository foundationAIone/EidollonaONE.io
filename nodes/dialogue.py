from __future__ import annotations

from typing import Any, Dict

from .graph import GRAPH


def open_channel(node_id: str, about: Dict[str, Any]) -> Dict[str, Any]:
    GRAPH.upsert(node_id, about)
    return {"ok": True, "node": node_id, "about": dict(about)}


def speak(node_id: str, message: str) -> Dict[str, Any]:
    return {
        "ok": True,
        "node": node_id,
        "message": message,
        "reply": "Eidollona hears {node}: {msg}".format(node=node_id, msg=message),
    }
