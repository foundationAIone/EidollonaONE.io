"""quick_assimilation.py

Rapid SAFE consciousness assimilation runner for the EidollonaONE stack.

This utility awakens the global consciousness core (if required), applies
optional sensing hints, and executes a single deterministic assimilation run.
It prints the resulting diagnostics as JSON and can optionally write the
payload to disk for auditing pipelines.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from consciousness_core import (
    assimilate_consciousness,
    awaken_eidollona,
    get_consciousness_status,
    ingest_consciousness_hints,
)

HintValue = Optional[float]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trigger a quick SAFE consciousness assimilation cycle",
    )
    parser.add_argument(
        "--comfort-index",
        type=float,
        help="Optional SAFE comfort index hint in [0.0, 1.0]",
    )
    parser.add_argument(
        "--audio-rms",
        type=float,
        help="Optional normalized audio RMS hint in [0.0, 1.0]",
    )
    parser.add_argument(
        "--risk-bias",
        type=float,
        help="Optional risk bias hint in [-0.25, 0.25]",
    )
    parser.add_argument(
        "--force-awaken",
        action="store_true",
        help="Force re-awakening even if the core is already active",
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Skip assimilation and only report current status",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the JSON payload",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=None,
        help="Pretty-print JSON with the given indentation",
    )
    return parser.parse_args(argv)


async def run_assimilation(args: argparse.Namespace) -> Dict[str, Any]:
    timestamp = datetime.utcnow().isoformat() + "Z"
    response: Dict[str, Any] = {
        "timestamp": timestamp,
        "hints_applied": {},
        "awakened": False,
        "status_only": bool(args.status_only),
    }

    hints: Dict[str, float] = {}
    if args.comfort_index is not None:
        hints["comfort_index"] = _clamp(float(args.comfort_index), 0.0, 1.0)
    if args.audio_rms is not None:
        hints["audio_rms"] = _clamp(float(args.audio_rms), 0.0, 1.0)
    if args.risk_bias is not None:
        hints["risk_bias"] = _clamp(float(args.risk_bias), -0.25, 0.25)

    if hints:
        ingest_consciousness_hints(**hints)
        response["hints_applied"] = hints

    response["awakened"] = await awaken_eidollona(force=bool(args.force_awaken))

    if args.status_only:
        response["status"] = get_consciousness_status()
        return response

    assimilation_report = await assimilate_consciousness()
    response.update(assimilation_report)
    return response


def emit_payload(payload: Dict[str, Any], *, indent: Optional[int], output: Optional[Path]) -> None:
    json_payload = json.dumps(payload, indent=indent)
    print(json_payload)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_payload + "\n", encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    try:
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        payload = asyncio.run(run_assimilation(args))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover - defensive logging
        error_payload: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(exc),
            "type": exc.__class__.__name__,
        }
        print(json.dumps(error_payload, indent=args.indent), file=sys.stderr)
        return 1

    emit_payload(payload, indent=args.indent, output=args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
