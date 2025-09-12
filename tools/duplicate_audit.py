#!/usr/bin/env python
"""Duplicate & collision audit.

Generates a JSON report listing:
 1. filename_collisions: basenames that appear more than once (filtered & ranked)
 2. exact_content_duplicates: groups of files with identical content hash (sha256)
 3. stats: counts & summary

Usage:
  python tools/duplicate_audit.py [--root .] [--limit 40]

Exclusions (by default):
  - __pycache__ directories
  - .git, virtual envs (heuristic: folders containing Scripts/python.exe or site-packages)
  - Filenames: __init__.py
  - Patterns: test_*.py (can still be listed under exact content duplicates if byte-identical)

Exit code 0 on success; writes duplicate_audit_report.json at repo root.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

DEFAULT_EXTS = {".py", ".js", ".ts", ".json", ".html", ".css", ".md"}
IGNORE_BASENAMES = {"__init__.py", "avatar_controller.py"}
# Unified ignore parts (directory name tokens) to suppress environment & vendor noise.
# NOTE: We treat each path segment independently; compound entries like 'webview/vendor'
# are replaced by plain 'vendor' which covers both trees.
IGNORE_DIR_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "site-packages",
    "dist-info",
    "Scripts",
    "bin",
    "vendor",
    "eidollona_env",
    "quantum_env",
}
TEST_PREFIXES = ("test_",)
VENV_HINTS = {"site-packages", "Scripts"}


def should_skip(path: str) -> bool:
    """Return True if this file path should be skipped from auditing.

    Rules:
      - Any directory segment in IGNORE_DIR_PARTS
      - Zero-length files (often placeholders / type markers)
      - Inaccessible paths (treated as skip)
    """
    norm = path.replace("\\", "/")
    parts = set(norm.split("/"))
    if parts & IGNORE_DIR_PARTS:
        return True
    try:
        if os.path.getsize(path) == 0:
            return True
    except OSError:
        return True
    return False


def is_probably_venv(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    # Fast skip if obvious virtual env markers present
    if any(h.lower() in parts for h in VENV_HINTS):
        return True
    # Skip top-level env folders by conventional names
    for candidate in ("eidollona_env", "quantum_env", ".env", ".venv"):
        if candidate in parts:
            return True
    return False


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        p = Path(dirpath)
        # prune ignored dirs in-place for efficiency
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIR_PARTS]
        if is_probably_venv(p):
            continue
        for fn in filenames:
            if fn.endswith(".pyc"):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext not in DEFAULT_EXTS:
                continue
            yield Path(dirpath) / fn


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Root directory (repo)")
    ap.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Limit of largest collision groups to include in summary",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    filename_map: dict[str, list[str]] = defaultdict(list)
    content_map: dict[str, list[str]] = defaultdict(list)

    for fp in iter_files(root):
        # Apply new skip logic early
        if should_skip(str(fp)):
            continue
        rel = str(fp.relative_to(root))
        base = fp.name
        filename_map[base].append(rel)
        try:
            digest = sha256_file(fp)
        except Exception as e:  # pragma: no cover - defensive
            print(f"WARN: unable to hash {rel}: {e}")
            continue
        content_map[digest].append(rel)

    # Filter filename collisions (exclude trivial & test duplicates unless widely duplicated)
    filename_collisions = []
    for base, paths in filename_map.items():
        if len(paths) < 2:
            continue
        if base in IGNORE_BASENAMES:
            continue
        is_test = any(p.split("/")[-1].startswith(TEST_PREFIXES) for p in paths)
        if is_test and len(paths) <= 2:
            # ignore small duplicate test name collisions
            continue
        filename_collisions.append(
            {
                "basename": base,
                "count": len(paths),
                "paths": paths,
            }
        )

    filename_collisions.sort(key=lambda d: d["count"], reverse=True)

    exact_content_duplicates = [
        {"hash": h, "count": len(paths), "paths": paths}
        for h, paths in content_map.items()
        if len(paths) > 1
    ]
    exact_content_duplicates.sort(key=lambda d: d["count"], reverse=True)

    stats = {
        "total_files_scanned": sum(len(v) for v in filename_map.values()),
        "unique_basenames": len(filename_map),
        "collision_basenames": len(filename_collisions),
        "exact_content_duplicate_groups": len(exact_content_duplicates),
        "largest_filename_collision": (
            filename_collisions[0]["count"] if filename_collisions else 0
        ),
        "largest_content_duplicate_group": (
            exact_content_duplicates[0]["count"] if exact_content_duplicates else 0
        ),
    }

    report = {
        "stats": stats,
        "filename_collisions": filename_collisions,
        "exact_content_duplicates": exact_content_duplicates,
    }

    out_path = root / "duplicate_audit_report.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Human summary
    print("[DuplicateAudit] Stats:")
    for k, v in stats.items():
        print(f"  - {k}: {v}")
    print(
        f"[DuplicateAudit] Top {min(args.limit, len(filename_collisions))} filename collisions (by count):"
    )
    for entry in filename_collisions[: args.limit]:
        print(f"  * {entry['basename']} x{entry['count']}")
    print(
        f"[DuplicateAudit] Top {min(args.limit, len(exact_content_duplicates))} exact content duplicate groups:"
    )
    for entry in exact_content_duplicates[: args.limit]:
        print(f"  * hash={entry['hash'][:10]}.. x{entry['count']}")
    print(f"Report written: {out_path}")


if __name__ == "__main__":
    main()
