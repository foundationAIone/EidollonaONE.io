from typing import Dict


class EmbodimentController:
    """Bridge SE41 signals into locomotion/look parameters.

    Maintains a small state dict that downstream (viewer, logs, etc.) can consume.
    """

    def __init__(self):
        self.current: Dict[str, float] = {
            "cadence_spm": 108.0,
            "step_len_m": 0.65,
            "phase": 0.0,
            "look_gain": 0.7,
            "impetus": 0.3,
        }

    def update_from_se41(self, signals: Dict):
        emb = signals.get("embodiment", {}) or {}
        mc = float(signals.get("mirror_consistency", 0.7))
        imp = float(signals.get("impetus", 0.3))

        self.current["cadence_spm"] = float(emb.get("cadence_spm", 108.0))
        self.current["step_len_m"] = float(emb.get("step_len_m", 0.65))
        self.current["phase"] = float(emb.get("phase", 0.0))
        self.current["look_gain"] = 0.5 + 0.45 * mc  # clamp 0.5–0.95
        self.current["impetus"] = imp

    def snapshot(self) -> Dict:
        return dict(self.current)


__all__ = ["EmbodimentController"]
