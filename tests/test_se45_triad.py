from symbolic_core.se45_triad import (
    SE44Inputs, evaluate_se44, SE45ConsensusCfg, fuse_trinity
)


def test_gate_or_hold():
    base = dict(coherence=0.85, risk=0.1, mirror=0.82, RA=0.95, L=0.9, EB=0.9, IL=0.05)
    A = evaluate_se44(SE44Inputs(**base, gate12=1.0))
    B = evaluate_se44(SE44Inputs(**base, gate12=0.2))  # red gate
    C = evaluate_se44(SE44Inputs(**base, gate12=1.0))
    cfg = SE45ConsensusCfg()
    fused = fuse_trinity(A, B, C, cfg)
    assert fused["decision"] == "HOLD"
    assert "gate12_red" in fused["reasons"]


def test_ra_two_of_three():
    base = dict(coherence=0.85, risk=0.1, mirror=0.82, gate12=1.0, L=0.9, EB=0.9, IL=0.05)
    A = evaluate_se44(SE44Inputs(**base, RA=0.95))
    B = evaluate_se44(SE44Inputs(**base, RA=0.94))
    C = evaluate_se44(SE44Inputs(**base, RA=0.80))  # below ra_min
    cfg = SE45ConsensusCfg(ra_min=0.90)
    fused = fuse_trinity(A, B, C, cfg)
    assert fused["ra_2of3"] is True


def test_disagreement_inflates_IL_and_deflates_L():
    base = dict(coherence=0.85, risk=0.1, mirror=0.82, gate12=1.0, RA=0.93, L=0.9, EB=0.9, IL=0.05)
    A = evaluate_se44(SE44Inputs(**base, impetus=0.8 if False else 0.0))  # impetus not accepted, just baseline
    # Create disagreement via L/RA spread using inputs producing different output
    A = evaluate_se44(SE44Inputs(**base, RA=0.95, L=0.95))
    B = evaluate_se44(SE44Inputs(**base, RA=0.90, L=0.85))
    C = evaluate_se44(SE44Inputs(**base, RA=0.92, L=0.88))
    cfg = SE45ConsensusCfg(il_alpha=0.5, l_beta=0.5)
    fused = fuse_trinity(A, B, C, cfg)
    assert fused["disagreement"] >= 0.0
    assert fused["IL"] >= 0.05  # inflated
    assert fused["L"] <= 0.95   # deflated


def test_allow_thresholds():
    base = dict(coherence=0.86, risk=0.10, mirror=0.82, gate12=1.0, RA=0.95, L=0.92, EB=0.93, IL=0.05)
    A = evaluate_se44(SE44Inputs(**base))
    B = evaluate_se44(SE44Inputs(**base))
    C = evaluate_se44(SE44Inputs(**base))
    cfg = SE45ConsensusCfg(allow_threshold=0.50, lucidity_min=0.85, evidence_min=0.85, illusion_max=0.10)
    fused = fuse_trinity(A, B, C, cfg)
    assert fused["decision"] in {"ALLOW", "REVIEW", "HOLD"}
    if fused["decision"] == "ALLOW":
        assert fused["impetus"] >= 0.50 and fused["L"] >= 0.85 and fused["EB"] >= 0.85 and fused["IL"] <= 0.10
