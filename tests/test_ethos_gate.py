from finance.policy.ethos_gate import ethos_gate


def test_ethos_gate_ok():
    sig = {
        "risk": 0.12,
        "impetus": 0.3,
        "ethos": {
            "authenticity": 0.9,
            "integrity": 0.9,
            "responsibility": 0.9,
            "enrichment": 0.9,
        },
    }
    ok, why = ethos_gate(sig)
    assert ok and why == "ok"


def test_ethos_gate_block():
    sig = {
        "risk": 0.2,
        "impetus": 0.1,
        "ethos": {
            "authenticity": 0.8,
            "integrity": 0.9,
            "responsibility": 0.9,
            "enrichment": 0.9,
        },
    }
    ok, why = ethos_gate(sig)
    assert not ok
