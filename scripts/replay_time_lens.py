import json
import os
import sys
from pathlib import Path

A = Path(os.environ.get("EIDOLLONA_AUDIT", "logs/audit.ndjson"))
lens = sys.argv[1] if len(sys.argv) > 1 else "now"
label = sys.argv[2] if len(sys.argv) > 2 else None

try:
    lines = A.read_text(encoding="utf-8", errors="ignore").splitlines()
except FileNotFoundError:
    print({"ok": False, "err": "no_audit"})
    sys.exit(0)

start_ts = None
for line in reversed(lines):
    try:
        event = json.loads(line)
    except Exception:
        continue
    if event.get("event") == "epoch_marker" and (label is None or event.get("label") == label):
        start_ts = event.get("ts")
        break

events = []
for line in lines:
    try:
        event = json.loads(line)
    except Exception:
        continue
    if start_ts and event.get("ts", 0) < start_ts:
        continue
    events.append(event)

decisions = [e for e in events if e.get("event") in ("q_execute", "brain_reason")]
reasons = [e for e in decisions if e.get("reasons")]
explain_rate = (len(reasons) / len(decisions)) if decisions else 0.0

holds = 0
sampled = 0
for event in decisions:
    impetus = None
    if "impetus" in event:
        impetus = event["impetus"]
    elif isinstance(event.get("signals"), dict):
        impetus = event["signals"].get("impetus")
    if impetus is None:
        continue
    sampled += 1
    if 0.45 <= float(impetus) < 0.55 and event.get("decision") == "HOLD":
        holds += 1
near_hold = (holds / sampled) if sampled else 0.0

previous = None
flips = 0
for event in decisions:
    decision = event.get("decision")
    if previous and decision and decision != previous:
        flips += 1
    if decision:
        previous = decision
flap_rate = (flips / len(decisions)) if decisions else 0.0

print(
    {
        "ok": True,
        "lens": lens,
        "label": label,
        "explain_rate": explain_rate,
        "near_threshold_hold_rate": near_hold,
        "flap_rate": flap_rate,
        "events": len(events),
    }
)
