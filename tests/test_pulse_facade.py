from symbolic_core.pulse import evaluate_pulse


def test_facade_basic_shape():
    se = evaluate_pulse({
        "coherence": 0.84,
        "risk": 0.12,
        "mirror": {"consistency": 0.80},
        "RA": 0.93,
        "L": 0.90,
        "EB": 0.90,
        "IL": 0.06,
    })
    # must include these keys even in fallback mode
    for k in [
        "version","decision","impetus","readiness","L","EB","IL","gate_ok","ra_2of3","disagreement"
    ]:
        assert k in se
    assert se["decision"] in {"ALLOW","REVIEW","HOLD"}
