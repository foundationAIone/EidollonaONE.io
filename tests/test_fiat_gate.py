from finance.policy.fiat_gate import FiatGate


def test_fiat_gate_thresholds_hold_then_allow(tmp_path):
    journal = tmp_path / "fiat_gate_journal.jsonl"
    policy = {
        "thresholds": {
            "coherence_min": 0.75,
            "ethos_min": 0.85,
            "risk_max": 0.15,
            "uncertainty_max": 0.30,
            "ser_min": 0.70,
        },
        "actions": {
            "hold_seconds": 10,
            "redirect_reserve_account": "SERPLUS_RESERVE",
            "categories": [],
        },
        "logging": {"journal_path": str(journal)},
    }
    gate = FiatGate(policy)
    tx = {
        "id": "t1",
        "amount": 100,
        "currency": "USD",
        "purpose": "test",
        "tags": ["service"],
        "meta": {},
    }
    v41 = {
        "coherence": 0.70,
        "risk": 0.10,
        "uncertainty": 0.20,
        "ethos": {
            "authenticity": 0.9,
            "integrity": 0.9,
            "responsibility": 0.9,
            "enrichment": 0.9,
        },
    }
    dec = gate.evaluate(tx, v41, ser_score=0.80)  # coherence below min
    assert dec.decision == "hold"
    assert any("coherence<" in r for r in dec.reasons)

    v41["coherence"] = 0.80
    dec2 = gate.evaluate(tx, v41, ser_score=0.80)
    assert dec2.decision == "allow"
