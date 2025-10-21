from __future__ import annotations

from typing import Any, Dict, List


class NodeGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}

    def upsert(self, node_id: str, attrs: Dict[str, Any]) -> None:
        self.nodes[node_id] = dict(attrs)

    def get(self, node_id: str) -> Dict[str, Any]:
        return dict(self.nodes.get(node_id, {}))

    def all(self) -> List[str]:
        return list(self.nodes.keys())


GRAPH = NodeGraph()
