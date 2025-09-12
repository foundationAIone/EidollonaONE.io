from symbolic_core.symbolic_equation import SymbolicEquation41


def test_se41_bounds_and_fields():
    se = SymbolicEquation41()
    ctx = {
        "mirror": {"consistency": 0.74},
        "substrate": {"S_EM": 0.83},
        "coherence_hint": 0.81,
        "risk_hint": 0.12,
        "uncertainty_hint": 0.28,
        "t": 0.42,
    }
    sig = se.evaluate(ctx)
    assert 0.0 <= sig.coherence <= 1.0
    assert 0.0 <= sig.impetus <= 1.0
    assert 0.0 <= sig.risk <= 1.0
    assert 0.0 <= sig.uncertainty <= 1.0
    assert 0.0 <= sig.mirror_consistency <= 1.0
    assert 0.0 <= sig.S_EM <= 1.0
    assert {"authenticity", "integrity", "responsibility", "enrichment"} <= set(
        sig.ethos.keys()
    )
    emb = sig.embodiment
    assert 0.0 <= emb["phase"] <= 1.0
    assert emb["cadence_spm"] > 0
    assert emb["step_len_m"] > 0
