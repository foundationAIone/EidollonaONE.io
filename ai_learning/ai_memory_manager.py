"""
AI Memory Manager: episodic/semantic/procedural/symbolic memory with retrieval and consolidation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta


@dataclass
class MemoryRecord:
    data: Any
    timestamp: datetime
    access_count: int = 0
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)


class AIMemoryManager:
    def __init__(self):
        self.memory_banks: Dict[str, Dict[str, MemoryRecord]] = {
            "episodic": {},
            "semantic": {},
            "procedural": {},
            "symbolic": {},
        }
        self.memory_importance: Dict[str, float] = {}

    def store_memory(
        self,
        memory_type: str,
        key: str,
        data: Any,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> None:
        if memory_type not in self.memory_banks:
            raise ValueError(f"Unknown memory type: {memory_type}")
        rec = MemoryRecord(
            data=data, timestamp=datetime.now(), importance=importance, tags=tags or []
        )
        self.memory_banks[memory_type][key] = rec
        self.memory_importance[f"{memory_type}:{key}"] = importance

    def has_memory(self, memory_type: str, key: str) -> bool:
        return key in self.memory_banks.get(memory_type, {})

    def retrieve_memory(
        self, memory_type: str, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        if memory_type not in self.memory_banks:
            return []
        query_l = query.lower()
        results: List[Tuple[float, str, MemoryRecord]] = []
        for key, rec in self.memory_banks[memory_type].items():
            score = self._relevance_score(query_l, key, rec)
            if score > 0:
                results.append((score, key, rec))
        results.sort(key=lambda x: x[0], reverse=True)
        out: List[Dict[str, Any]] = []
        for score, key, rec in results[:limit]:
            rec.access_count += 1
            out.append(
                {
                    "key": key,
                    "memory": {
                        "data": rec.data,
                        "timestamp": rec.timestamp,
                        "access_count": rec.access_count,
                        "importance": rec.importance,
                        "tags": rec.tags,
                    },
                    "relevance": score,
                }
            )
        return out

    def _relevance_score(self, query_l: str, key: str, rec: MemoryRecord) -> float:
        key_l = key.lower()
        data_l = str(rec.data).lower()
        tag_hit = (
            any(q in (t.lower()) for t in rec.tags for q in query_l.split())
            if rec.tags
            else 0
        )
        key_hit = sum(1 for q in query_l.split() if q in key_l)
        data_hit = sum(1 for q in query_l.split() if q in data_l)
        raw = key_hit * 0.7 + data_hit * 0.3 + (0.5 if tag_hit else 0)
        # Weight by importance and recency (simple decay after 30 days)
        age_days = (datetime.now() - rec.timestamp).days
        recency = max(0.2, 1.0 - age_days / 180.0)
        return raw * (0.5 + rec.importance * 0.5) * recency

    def consolidate_memories(
        self, max_age_days: int = 30, min_importance: float = 0.1, min_access: int = 2
    ) -> int:
        removed = 0
        cutoff = datetime.now() - timedelta(days=max_age_days)
        for mtype, bank in self.memory_banks.items():
            to_delete = []
            for key, rec in bank.items():
                if (
                    rec.importance < min_importance
                    and rec.access_count < min_access
                    and rec.timestamp < cutoff
                ):
                    to_delete.append(key)
            for key in to_delete:
                del bank[key]
                self.memory_importance.pop(f"{mtype}:{key}", None)
                removed += 1
        return removed

    def forget(self, memory_type: str, key: str) -> bool:
        bank = self.memory_banks.get(memory_type)
        if not bank or key not in bank:
            return False
        del bank[key]
        self.memory_importance.pop(f"{memory_type}:{key}", None)
        return True

    def stats(self) -> Dict[str, Any]:
        return {
            mtype: {
                "count": len(bank),
                "avg_importance": (
                    (sum(rec.importance for rec in bank.values()) / len(bank))
                    if bank
                    else 0.0
                ),
            }
            for mtype, bank in self.memory_banks.items()
        }


# Module-level instance
ai_memory_manager = AIMemoryManager()

__all__ = ["AIMemoryManager", "ai_memory_manager", "MemoryRecord"]
