#!/usr/bin/env python3
"""Update STATUS.md based on recent promotion evidence."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = ROOT / "STATUS.md"
PROMO_DIR = ROOT / "logs" / "promo"
PROMO_TTL_SECONDS = 24 * 60 * 60


@dataclass
class PromotionEvidence:
    module: str
    path: Path
    ts: float

    @property
    def rel_path(self) -> str:
        return str(self.path.relative_to(ROOT).as_posix())


def load_evidence() -> Dict[str, PromotionEvidence]:
    if not PROMO_DIR.exists():
        return {}
    now = time.time()
    latest: Dict[str, PromotionEvidence] = {}
    for file_path in PROMO_DIR.glob("*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if not payload.get("pass"):
            continue
        ts = payload.get("ts")
        module = payload.get("module")
        if not isinstance(ts, (int, float)) or not isinstance(module, str):
            continue
        if now - ts > PROMO_TTL_SECONDS:
            continue
        existing = latest.get(module)
        if existing is None or ts > existing.ts:
            latest[module] = PromotionEvidence(module, file_path, ts)
    return latest


def update_status(contents: str, promos: Dict[str, PromotionEvidence]) -> Tuple[str, List[str], List[str]]:
    if not promos:
        return contents, [], []

    lines = contents.splitlines()
    updated_modules: List[str] = []
    missing_modules: List[str] = []
    remaining = set(promos.keys())

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| Module"):
            continue
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if len(cells) < 4:
            continue
        cell_lower = cells[0].lower()
        normalized_cell = cell_lower.replace("_", "").replace(" ", "")
        match_module: Optional[str] = None
        for module in list(remaining):
            aliases = {
                module.lower(),
                module.replace("_", " ").lower(),
                module.replace("_", "").lower(),
            }
            if any(alias and alias in cell_lower for alias in aliases):
                match_module = module
                break
            if any(alias and alias.replace(" ", "") in normalized_cell for alias in aliases):
                match_module = module
                break
        if match_module is None:
            continue

        evidence = promos[match_module]
        remaining.discard(match_module)

        prev_state = cells[1]
        cells[1] = "GREEN"
        note = cells[3]
        link = f"[evidence]({evidence.rel_path})"
        if note:
            if "logs/promo" not in note:
                note = f"{note} · {link}"
        else:
            note = link
        cells[3] = note
        lines[idx] = "| " + " | ".join(cells) + " |"
        updated_modules.append(f"{match_module}:{prev_state}->GREEN")

    if remaining:
        missing_modules = sorted(remaining)

    return "\n".join(lines) + "\n", updated_modules, missing_modules


def main() -> int:
    promos = load_evidence()
    if not promos:
        print("No recent promotion evidence found.")
        return 0

    if not STATUS_PATH.exists():
        print(f"STATUS file missing: {STATUS_PATH}", file=sys.stderr)
        return 1

    original = STATUS_PATH.read_text(encoding="utf-8")
    updated, changed, missing = update_status(original, promos)

    if not changed:
        print("No STATUS rows updated.")
    else:
        STATUS_PATH.write_text(updated, encoding="utf-8")
        print("Updated STATUS rows:")
        for entry in changed:
            print(f"  - {entry}")

    if missing:
        print("Evidence without matching STATUS rows:")
        for module in missing:
            print(f"  - {module}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
