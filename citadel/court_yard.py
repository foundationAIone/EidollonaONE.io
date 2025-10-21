"""Court Yard panel helper.

Creates deterministic, auditable panel transcripts for the Citadel Court Yard.
The panel does not execute live reasoning; it synthesizes succinct statements to
summarize the current topic, readiness, and gate posture.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

try:
    from utils.audit import audit_ndjson
except Exception:  # pragma: no cover
    def audit_ndjson(event: str, **payload: Any) -> None:  # type: ignore
        return None

__all__ = ["PanelEntry", "CourtYardPanel"]


@dataclass
class PanelEntry:
    panelist: str
    statement: str
    readiness: str
    wings: float
    reality_alignment: float
    gate_focus: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "panelist": self.panelist,
            "statement": self.statement,
            "readiness": self.readiness,
            "wings": round(self.wings, 4),
            "reality_alignment": round(self.reality_alignment, 4),
            "gate_focus": list(self.gate_focus),
        }


class CourtYardPanel:
    def __init__(self, log_path: str = "logs/citadel_court_yard.ndjson") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def summon_panel(
        self,
        panelists: Iterable[str],
        topic: str,
        *,
        signals: Optional[Mapping[str, Any]] = None,
        gate_focus: Optional[Iterable[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        roster = [str(p) for p in panelists if p]
        if not roster:
            raise ValueError("panelists required")
        base_signals = signals or {}
        topic = topic.strip() or "unspecified"
        gates = [str(g) for g in (gate_focus or base_signals.get("gate_focus", []))]
        timestamp = time.time()

        entries: List[PanelEntry] = []
        for idx, panelist in enumerate(roster):
            readiness = str(base_signals.get("readiness", "warming")).lower()
            wings = float(base_signals.get("wings", 1.0) or 1.0)
            ra = float(base_signals.get("reality_alignment", 0.0) or 0.0)
            statement = self._compose(panelist, topic, readiness, gates, idx)
            entry = PanelEntry(
                panelist=panelist,
                statement=statement,
                readiness=readiness,
                wings=wings,
                reality_alignment=ra,
                gate_focus=gates,
            )
            entries.append(entry)
            self._append_log(
                {
                    "ts": timestamp,
                    "panelist": panelist,
                    "topic": topic,
                    "entry": entry.to_dict(),
                    "metadata": metadata or {},
                }
            )

        payload = {
            "ts": timestamp,
            "topic": topic,
            "entries": [entry.to_dict() for entry in entries],
            "metadata": metadata or {},
        }
        audit_ndjson(
            "citadel_court_panel",
            topic=topic,
            panelists=roster,
            entries=len(entries),
            readiness=base_signals.get("readiness"),
            wings=base_signals.get("wings"),
            reality_alignment=base_signals.get("reality_alignment"),
        )
        return payload

    def _compose(
        self,
        panelist: str,
        topic: str,
        readiness: str,
        gates: List[str],
        index: int,
    ) -> str:
        gate_text = ", ".join(gates[:3]) if gates else "baseline"
        readiness_text = readiness.replace("_", " ")
        return (
            f"{panelist} notes {topic} is tracked under gates [{gate_text}] "
            f"with readiness {readiness_text}. Phase {index + 1} remains SAFE."
        )

    def _append_log(self, payload: Dict[str, Any]) -> None:
        try:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # Logging must never break SAFE posture
            pass
