from __future__ import annotations


from typing import Any, Dict

import pytest

from symbolic_core import symbolic_equation_master as master


def build_context(**overrides: Any) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {
        "coherence_hint": 0.82,
        "risk_hint": 0.15,
        "uncertainty_hint": 0.25,
        "mirror": {"consistency": 0.70},
        "substrate": {"S_EM": 0.78},
        "ethos_hint": {},
        "t": 0.5,
    }
    ctx.update(overrides)
    return ctx


def test_evaluate_master_state_snapshot_has_expected_keys() -> None:
    snap = master.evaluate_master_state(build_context())
    assert 0.0 <= snap.coherence <= 1.0
    assert 0.0 <= snap.impetus <= 1.0
    assert 0.0 <= snap.risk <= 1.0
    assert 0.0 <= snap.uncertainty <= 1.0
    assert snap.delta_coherence == pytest.approx(0.0)
    assert snap.delta_impetus == pytest.approx(0.0)
    assert snap.delta_risk == pytest.approx(0.0)


def test_evaluate_master_state_delta_tracking() -> None:
    eq = master.MasterSymbolicEquation()
    first = eq.evaluate(build_context(coherence_hint=0.4))
    second = eq.evaluate(build_context(coherence_hint=0.6))
    assert second.delta_coherence != 0.0
    assert second.delta_coherence == pytest.approx(second.coherence - first.coherence)
    assert second.delta_impetus == pytest.approx(second.impetus - first.impetus)


def test_evaluate_dict_returns_json_safe_dict() -> None:
    eq = master.MasterSymbolicEquation()
    data = eq.evaluate_dict(build_context())
    assert isinstance(data, dict)
    assert "coherence" in data
    assert "delta_coherence" in data
    assert 0.0 <= data["coherence"] <= 1.0
    assert isinstance(data["delta_coherence"], float)


def test_last_snapshot_and_signals_cached() -> None:
    eq = master.MasterSymbolicEquation()
    assert eq.last_snapshot() is None
    assert eq.last_signals() is None
    snapshot = eq.evaluate(build_context())
    assert eq.last_snapshot() is snapshot
    assert eq.last_signals() is not None


def test_get_master_symbolic_singleton_returns_same_instance() -> None:
    a = master.get_master_symbolic_singleton()
    b = master.get_master_symbolic_singleton()
    assert a is b


def test_master_symbolic_equation_handles_minimal_signal_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    class MinimalSignals:
        def __init__(self, coherence: float) -> None:
            self.coherence = coherence
            self.impetus = 0.0
            self.risk = 1.0
            self.uncertainty = 0.0
            self.mirror_consistency = 0.0
            self.S_EM = 0.0
            self.ethos: Dict[str, float] = {}
            self.embodiment: Dict[str, float] = {}
            self.explain = "minimal"

    class MinimalEquation:
        def __init__(self) -> None:
            self._value = 0.1

        def evaluate(self, context: Dict[str, Any]) -> MinimalSignals:
            self._value = float(context.get("coherence_hint", self._value))
            return MinimalSignals(self._value)

    monkeypatch.setattr(master, "SymbolicEquation41", MinimalEquation)
    eq = master.MasterSymbolicEquation()
    snap = eq.evaluate(build_context(coherence_hint=0.3))
    assert 0.0 <= snap.coherence <= 1.0
    assert snap.ethos_min == pytest.approx(0.0)
    assert snap.embodiment_phase == pytest.approx(0.0)
