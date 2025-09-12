from dataclasses import dataclass, asdict
from typing import Dict, Any
from datetime import datetime, timezone
import json
import os


@dataclass
class SelfEvidence:
    prediction_error: float
    identity_consistency: float
    sensor_coherence: float
    control_correlation: float
    explain: str
    score: float


class SERWriter:
    def __init__(self, ser_path: str = "consciousness_data/ser.log.jsonl") -> None:
        self.ser_path = ser_path
        os.makedirs(os.path.dirname(self.ser_path), exist_ok=True)

    def write(
        self,
        prediction: Dict[str, Any],
        observation: Dict[str, Any],
        env_tag: str = "WEB",
    ) -> SelfEvidence:
        err = 0.0 if prediction == observation else 0.2
        idc = 1.0 if prediction.get("id") == observation.get("id") else 0.0
        sc = 1.0 if observation.get("sensors_ok", True) else 0.5
        cc = 1.0 if prediction.get("route") == observation.get("route") else 0.7
        score = max(0.0, min(1.0, 0.35 * idc + 0.35 * sc + 0.30 * cc - err))
        ser = SelfEvidence(err, idc, sc, cc, "ok" if err == 0 else "minor-diff", score)
        line = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "env": env_tag,
            "prediction": prediction,
            "observation": observation,
            "ser": asdict(ser),
        }
        with open(self.ser_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return ser
