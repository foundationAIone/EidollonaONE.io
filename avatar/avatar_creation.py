"""
Avatar Creation - Enhanced

Purpose:
- Provide a simple API and CLI to create an avatar deterministically using the
  rpm_ecosystem components (CharacterCustomizer and MultiPlatformRenderer).
- Support exporting minimal assets per platform to a target directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Local ecosystem imports (updated to canonical path)
from avatar.rpm_ecosystem.ecosystem_manager import EcosystemManager, AvatarConfig
from avatar.rpm_ecosystem.utilities import (
    get_logger,
    load_config,
    ensure_dir,
    atomic_write_json,
)


async def _create_avatar_data(
    *,
    name: str,
    avatar_id: str,
    customization: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create avatar data via CharacterCustomizer (async)."""
    eco = EcosystemManager()
    cfg = AvatarConfig(
        avatar_id=avatar_id,
        name=name,
        customization_params=dict(customization or {}),
    )
    # Character customizer may be a stub; both paths return a deterministic dict
    avatar = await eco.character_customizer.generate_avatar(cfg)
    return avatar


async def _export_for_platforms(
    *,
    eco: EcosystemManager,
    avatar: Dict[str, Any],
    platforms: List[str],
    quality: str,
    out_dir: Path,
) -> List[str]:
    """Export minimal assets for requested platforms and save to disk."""
    written: List[str] = []
    for p in platforms:
        pkg = await eco.renderer.export_for_platform(avatar, p, quality)
        out_file = await eco.renderer.save_avatar_asset(pkg, str(out_dir), p)
        written.append(out_file)
    return written


async def create_and_save_avatar(
    *,
    name: str,
    avatar_id: str,
    platforms: Optional[List[str]] = None,
    quality: str = "high",
    customization: Optional[Dict[str, Any]] = None,
    output_dir: str = "outputs/avatars",
) -> Tuple[Dict[str, Any], List[str]]:
    """Create an avatar and export assets.

    Returns (avatar_data, list_of_written_files).
    """
    logger = get_logger("Eidollona.AvatarCreation")
    cfg = load_config()
    logger.info(
        "Starting avatar creation | safe_mode=%s, quality=%s, out=%s",
        cfg.safe_mode,
        quality,
        output_dir,
    )

    eco = EcosystemManager()
    ensure_dir(output_dir)

    # Generate avatar data
    avatar = await _create_avatar_data(
        name=name, avatar_id=avatar_id, customization=customization
    )

    # Export assets
    plats = list(platforms or ["webxr"])  # defaults
    written = await _export_for_platforms(
        eco=eco,
        avatar=avatar,
        platforms=plats,
        quality=quality,
        out_dir=Path(output_dir),
    )

    # Save a summary manifest next to assets
    summary = {
        "avatar": {
            "id": avatar.get("id") or avatar.get("name") or avatar_id,
            "name": avatar.get("name", name),
        },
        "platforms": plats,
        "quality": quality,
        "files": written,
    }
    manifest_path = str(Path(output_dir) / f"avatar_{avatar_id}_summary.json")
    atomic_write_json(manifest_path, summary)
    logger.info("Avatar created and saved | files=%d", len(written))
    return avatar, written


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Create and export an avatar")
    ap.add_argument("--name", default="Eidollona", help="Avatar name")
    ap.add_argument("--id", dest="avatar_id", default="eidollona_001", help="Avatar ID")
    ap.add_argument(
        "--platforms",
        default="webxr",
        help="Comma-separated platforms (webxr,unity,unreal)",
    )
    ap.add_argument(
        "--quality",
        default="high",
        choices=["low", "medium", "high", "ultra"],
        help="Export quality",
    )
    ap.add_argument(
        "--out",
        dest="output_dir",
        default="outputs/avatars",
        help="Output directory",
    )
    ap.add_argument(
        "--custom",
        dest="custom_json",
        default=None,
        help="Custom JSON string for customization_params",
    )
    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    ns = _parse_args(argv)
    platforms = [p.strip() for p in (ns.platforms or "").split(",") if p.strip()]
    customization = None
    if ns.custom_json:
        try:
            customization = json.loads(ns.custom_json)
        except Exception:
            customization = None
    avatar, files = asyncio.run(
        create_and_save_avatar(
            name=ns.name,
            avatar_id=ns.avatar_id,
            platforms=platforms,
            quality=ns.quality,
            customization=customization,
            output_dir=ns.output_dir,
        )
    )
    # Print a concise summary to stdout
    print(json.dumps({"avatar": avatar.get("name"), "files": files}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
