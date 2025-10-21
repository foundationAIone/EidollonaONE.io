import json
import math
import os
import time
from pathlib import Path

AUDIT_PATH = Path(os.environ.get("EIDOLLONA_AUDIT", "logs/audit.ndjson"))


def shannon_entropy(distribution: dict[str, float]) -> float:
    entropy = 0.0
    for probability in distribution.values():
        if probability > 0.0:
            entropy -= probability * math.log2(probability)
    return entropy


def main(window_size: int = 200) -> None:
    try:
        lines = AUDIT_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()[-2000:]
    except FileNotFoundError:
        print({"ok": False, "err": "no_audit"})
        return

    decisions = []
    for line in lines:
        try:
            event = json.loads(line)
        except Exception:
            continue
        if event.get("event") in {"q_execute", "brain_reason"}:
            decisions.append(event)

    if len(decisions) < window_size:
        print({"ok": False, "err": "too_few"})
        return

    window = decisions[-window_size:]
    counts: dict[str, int] = {}
    for event in window:
        decision = event.get("decision")
        if decision:
            counts[decision] = counts.get(decision, 0) + 1

    total = sum(counts.values()) or 1
    distribution = {key: value / total for key, value in counts.items()}
    entropy_bits = shannon_entropy(distribution)

    result = {"ok": True, "entropy_bits": entropy_bits, "distribution": distribution, "N": window_size}
    print(result)

    with open(AUDIT_PATH, "a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "event": "entropy_report",
                    **result,
                    "ts": time.time(),
                },
                ensure_ascii=False,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
