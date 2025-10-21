import json
import subprocess
import sys

import yaml

THRESH = yaml.safe_load(open("config/kpi_thresholds.yml", "r", encoding="utf-8"))


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_replay(lens: str, label: str) -> dict:
    cmd = [sys.executable, "scripts/replay_time_lens.py", lens, label]
    output = subprocess.check_output(cmd, text=True, encoding="utf-8")
    return json.loads(output)


def run_entropy() -> dict:
    cmd = [sys.executable, "scripts/entropy_monitor.py"]
    output = subprocess.check_output(cmd, text=True, encoding="utf-8", stderr=subprocess.STDOUT)
    try:
        return json.loads(output)
    except Exception:
        return {"ok": True}


def main() -> None:
    args = sys.argv[1:]
    if len(args) >= 1 and args[0].endswith(".json"):
        replay = load_json(args[0])
        lens = replay.get("lens", "now")
        label = replay.get("label")
    else:
        lens = args[0] if len(args) >= 1 else "now"
        label = args[1] if len(args) >= 2 else None
        replay = run_replay(lens, label or "")

    if not replay.get("ok"):
        print({"ok": False, "err": "replay_failed", "replay": replay})
        sys.exit(2)

    explain_rate = float(replay.get("explain_rate", 0.0))
    near_hold = float(replay.get("near_threshold_hold_rate", 1.0))
    flap_rate = float(replay.get("flap_rate", 1.0))

    entropy = run_entropy()
    entropy_bits = float(entropy.get("entropy_bits", 1.5)) if entropy.get("ok") else 1.5

    warnings: list[str] = []
    critical: list[str] = []

    if explain_rate < THRESH["explain_rate_min"]:
        critical.append(f'explain_rate<{THRESH["explain_rate_min"]} ({explain_rate:.3f})')
    if near_hold > THRESH["near_threshold_hold_rate_max"]:
        warnings.append(
            f'near_threshold_hold_rate>{THRESH["near_threshold_hold_rate_max"]} ({near_hold:.3f})'
        )
    if flap_rate > THRESH["flap_rate_max"]:
        warnings.append(f'flap_rate>{THRESH["flap_rate_max"]} ({flap_rate:.3f})')
    if entropy_bits < THRESH["entropy_crit_min"]:
        critical.append(f'entropy_bits<{THRESH["entropy_crit_min"]} ({entropy_bits:.3f})')
    elif entropy_bits < THRESH["entropy_warn_min"]:
        warnings.append(f'entropy_bits<{THRESH["entropy_warn_min"]} ({entropy_bits:.3f})')

    result = {
        "ok": len(critical) == 0,
        "warn": warnings,
        "crit": critical,
        "replay": {
            "lens": lens,
            "label": label,
            "explain_rate": explain_rate,
            "near_threshold_hold_rate": near_hold,
            "flap_rate": flap_rate,
        },
        "entropy_bits": entropy_bits,
    }

    print(json.dumps(result, indent=2))
    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
