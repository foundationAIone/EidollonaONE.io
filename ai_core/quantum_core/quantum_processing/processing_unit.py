"""High level orchestration of quantum jobs using the sovereign-aligned bridge."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from ..quantum_logic import QuantumSymbolicBridge
from .job_queue import QuantumJob, QuantumJobQueue
from .monitor import ProcessingMonitor

__all__ = ["QuantumProcessingUnit"]


class QuantumProcessingUnit:
    """Coordinate queued jobs with the quantum symbolic bridge."""

    def __init__(
        self,
        *,
        bridge: Optional[QuantumSymbolicBridge] = None,
        monitor: Optional[ProcessingMonitor] = None,
    ) -> None:
        self.bridge = bridge or QuantumSymbolicBridge()
        self.queue = QuantumJobQueue()
        self.monitor = monitor or ProcessingMonitor()

    def submit(self, payload: Mapping[str, Any], *, metadata: Optional[Mapping[str, Any]] = None) -> QuantumJob:
        job = self.queue.enqueue(dict(payload), metadata=dict(metadata or {}))
        self.monitor.record_submission(job)
        return job

    def process_next(self) -> Optional[Dict[str, Any]]:
        job = self.queue.dequeue()
        if job is None:
            return None

        payload = job.payload
        signals = self._resolve_signals(payload)
        ouroboros = float(payload.get("ouroboros", payload.get("ouro", 0.0)))
        explain = bool(payload.get("explain", True))

        report = self.bridge.align(signals, ouroboros=ouroboros, explain=explain)
        result = {
            "job": job.summary(),
            "report": {
                "sovereign_gate": report.sovereign_gate,
                "gate": report.gate,
                "ready": report.ready,
                "fidelity_est": report.fidelity_est,
                "recommendation": report.rec,
                "params": dict(report.params),
                "config": asdict(report.config),
                "signals": dict(signals),
                "metadata": dict(payload.get("metadata", {})),
            },
        }
        self.monitor.record_completion(job, result)
        return result

    def drain(self) -> Iterable[Dict[str, Any]]:
        results = []
        while True:
            record = self.process_next()
            if record is None:
                break
            results.append(record)
        return tuple(results)

    # ------------------------------------------------------------------
    # Helpers

    @staticmethod
    def _clamp01(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    def _resolve_signals(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        raw_signals = payload.get("signals")
        if isinstance(raw_signals, Mapping):
            signals: Dict[str, Any] = dict(raw_signals)
        else:
            signals = self._infer_signals_from_sequence(payload.get("sequence"))

        ethos = payload.get("ethos")
        if isinstance(ethos, Mapping):
            signals["ethos"] = dict(ethos)
        else:
            signals.setdefault("ethos", {})

        overrides = payload.get("signals_overrides")
        if isinstance(overrides, Mapping):
            for key, value in overrides.items():
                signals[str(key)] = value
        return signals

    def _infer_signals_from_sequence(self, sequence: Any) -> Dict[str, Any]:
        if not isinstance(sequence, Sequence) or isinstance(sequence, (str, bytes)):
            return self._default_signals()

        seq_list = list(sequence)
        length = len(seq_list)
        entangling = sum(1 for gate in seq_list if self._is_entangling_gate(gate))
        length_factor = min(1.0, length / 8.0)
        entangle_factor = min(1.0, entangling / max(1, length))

        return {
            "coherence": self._clamp01(0.55 + 0.15 * (1.0 - length_factor)),
            "impetus": self._clamp01(0.35 + 0.25 * length_factor),
            "risk": self._clamp01(0.25 + 0.5 * (0.6 * entangle_factor + 0.4 * length_factor)),
            "uncertainty": self._clamp01(0.30 + 0.40 * length_factor),
            "mirror_consistency": self._clamp01(0.55 - 0.25 * entangle_factor),
            "S_EM": self._clamp01(0.45 + 0.10 * (1.0 - length_factor)),
            "ethos": {},
        }

    def _default_signals(self) -> Dict[str, Any]:
        return {
            "coherence": 0.55,
            "impetus": 0.40,
            "risk": 0.35,
            "uncertainty": 0.45,
            "mirror_consistency": 0.50,
            "S_EM": 0.50,
            "ethos": {},
        }

    def _is_entangling_gate(self, gate: Any) -> bool:
        name: str = ""
        targets: Optional[Sequence[Any]] = None

        if isinstance(gate, Mapping):
            name = str(gate.get("name", "")).upper()
            raw_targets = gate.get("targets")
            if isinstance(raw_targets, Sequence) and not isinstance(raw_targets, (str, bytes)):
                targets = list(raw_targets)
        elif hasattr(gate, "name"):
            name = str(getattr(gate, "name", "")).upper()
            raw_targets = getattr(gate, "targets", None)
            if isinstance(raw_targets, Sequence) and not isinstance(raw_targets, (str, bytes)):
                targets = list(raw_targets)
        elif isinstance(gate, str):
            name = gate.upper()

        if targets is not None and len(targets) > 1:
            return True

        entangling_names = {"CX", "CZ", "SWAP", "CNOT", "CRX", "CRY", "CRZ"}
        return name in entangling_names
