from symbolic_core.symbolic_equation import SymbolicEquation41


def test_v41_evaluate_bounded():
    se = SymbolicEquation41()
    ctx = {
        "mirror": {"consistency": 0.7},
        "substrate": {"S_EM": 0.8},
        "coherence_hint": 0.82,
        "risk_hint": 0.12,
        "uncertainty_hint": 0.28,
        "t": 0.37,
        "ethos_hint": {
            "authenticity": 0.93,
            "integrity": 0.91,
            "responsibility": 0.90,
            "enrichment": 0.92,
        },
    }
    s = se.evaluate(ctx)
    assert 0 <= s.coherence <= 1
    assert 0 <= s.impetus <= 1
    assert 0 <= s.ethos["authenticity"] <= 1
    assert "phase" in s.embodiment


def test_legacy_shims_exist():
    se = SymbolicEquation41()
    v = se.reality_manifestation(Q=0.77)
    assert 0 <= v <= 1
    assert se.validate_update_coherence({}) >= 0.0
    lvl = se.get_coherence_level()
    assert 0 <= lvl <= 1
    se.post_update_recalibration()
