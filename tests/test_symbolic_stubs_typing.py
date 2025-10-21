"""Runtime smoke checks that mirror the symbolic_equation stub contract."""

from __future__ import annotations

import inspect
from typing import Any, Dict

import pytest

from symbolic_core import symbolic_equation as se


def test_helper_function_signatures_align() -> None:
    build_sig = inspect.signature(se.build_se41_context)
    assert "coherence_hint" in build_sig.parameters
    assert build_sig.parameters["overrides"].kind is inspect.Parameter.KEYWORD_ONLY

    assemble_sig = inspect.signature(se.assemble_se41_context_from_summaries)
    assemble_return = assemble_sig.return_annotation
    if assemble_return is not inspect.Signature.empty:
        assert str(assemble_return) in {"typing.Dict[str, typing.Any]", "Dict[str, Any]"}

    suggest_sig = inspect.signature(se.suggest_gate)
    assert "thresholds" in suggest_sig.parameters
    suggest_return = suggest_sig.return_annotation
    if suggest_return is not inspect.Signature.empty:
        assert str(suggest_return) in {"<class 'str'>", "str"}


@pytest.mark.parametrize(
    "payload",
    [
        se.build_se41_context(coherence_hint=0.9),
        se.assemble_se41_context_from_summaries([
            {"coherence_hint": 0.75, "risk_hint": 0.2},
            {"substrate": {"S_EM": 0.7}},
        ]),
    ],
)
def test_context_builders_return_dict(payload: Dict[str, Any]) -> None:
    assert isinstance(payload, dict)
    assert "coherence_hint" in payload
    assert "substrate" in payload


def test_symbolic_equation41_evaluate_from_summaries_round_trip() -> None:
    eq = se.SymbolicEquation41()
    summaries = [
        {"coherence_hint": 0.82, "mirror": {"consistency": 0.78}},
        {"risk": 0.15, "uncertainty": 0.25, "ethos_hint": {"integrity": 0.88}},
    ]
    signals = eq.evaluate_from_summaries(summaries)
    assert hasattr(signals, "coherence")
    assert hasattr(signals, "C_realize")
    assert pytest.approx(signals.C_realize, abs=1e-6) == signals.coherence
    as_dict = se.signals_to_dict(signals)
    assert isinstance(as_dict, dict)
    assert "impetus" in as_dict
    decision = se.suggest_gate(signals)
    assert decision in {"allow", "review", "hold"}
