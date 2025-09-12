from avatar.embodiment.embodiment_controller import EmbodimentController


def test_embodiment_from_se41():
    c = EmbodimentController()
    signals = {
        "embodiment": {"phase": 0.25, "cadence_spm": 110.0, "step_len_m": 0.66},
        "mirror_consistency": 0.8,
        "impetus": 0.32,
    }
    c.update_from_se41(signals)
    s = c.snapshot()
    assert s["cadence_spm"] == 110.0
    assert abs(s["look_gain"] - (0.5 + 0.45 * 0.8)) < 1e-6
