from typing import Dict, Tuple


def ethos_gate(signals: Dict) -> Tuple[bool, str]:
    """Gate financial/SAFE actions based on SE41 signals.

    Conditions:
      - ethos_min >= 0.85
      - risk <= 0.15
      - impetus >= 0.15
    """
    ethos = signals.get("ethos", {}) or {}
    ethos_min = (
        min(
            ethos.get("authenticity", 0),
            ethos.get("integrity", 0),
            ethos.get("responsibility", 0),
            ethos.get("enrichment", 0),
        )
        if ethos
        else 0.0
    )
    risk = float(signals.get("risk", 1.0))
    imp = float(signals.get("impetus", 0.0))

    if ethos_min < 0.85:
        return False, f"ethos_min<{0.85}"
    if risk > 0.15:
        return False, f"risk>{0.15}"
    if imp < 0.15:
        return False, f"impetus<{0.15}"
    return True, "ok"


__all__ = ["ethos_gate"]
