"""
Cleanup report generator for EidollonaONE.

Safe by default: scans the repo and emits a JSON and Markdown summary of
potentially removable items (logs, caches, temp files, large binaries, etc.).

Usage (examples):
  python scripts/cleanup_report.py --root .
  python scripts/cleanup_report.py --root . --max-size-mb 100
  python scripts/cleanup_report.py --root . --delete   # DANGEROUS: will remove matched junk

Notes:
  - We DO NOT remove anything by default. Add --delete to actually delete.
  - We avoid touching the project venv (eidollona_env) and .git by default.
  - This script is conservative; review the JSON/MD report before deleting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "eidollona_env",
    "quantum_env",
    ".venv",
    "venv",
    ".vscode",
    ".idea",
    "node_modules",
}

LOG_EXTS = {".log"}
TMP_EXTS = {".tmp", ".bak", ".orig"}
TMP_SUFFIXES = {"~"}

CACHE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".ipynb_checkpoints",
}

JUNK_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
    ".coverage",
}

EXECUTABLE_EXTS = {".exe", ".dll"}


@dataclass
class FileInfo:
    path: str
    size: int


@dataclass
class CleanupReport:
    root: str
    generated_at: float
    max_size_mb: int
    candidates: Dict[str, List[FileInfo]]
    duplicate_groups: List[List[FileInfo]]


def human_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def walk_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def is_log_candidate(p: Path) -> bool:
    return p.suffix.lower() in LOG_EXTS or any(
        s for s in TMP_SUFFIXES if str(p).endswith(s)
    )


def is_tmp_candidate(p: Path) -> bool:
    return p.suffix.lower() in TMP_EXTS


def is_cache_dir(p: Path) -> bool:
    if p.name in CACHE_DIR_NAMES:
        return True
    # Treat self_build artifacts as cache-like (safe to clean)
    try:
        parts = set(p.parts)
    except Exception:
        parts = set()
    if p.name == "artifacts" and ("self_build" in parts or "self_build" in str(p)):
        return True
    return False


def is_executable(p: Path) -> bool:
    return p.suffix.lower() in EXECUTABLE_EXTS


def short_hash(path: Path, bytes_to_read: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            chunk = f.read(bytes_to_read)
            h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return ""


def full_hash(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def group_duplicates(
    paths: List[Path], min_size_bytes: int = 10 * 1024 * 1024
) -> List[List[Path]]:
    # First group by size
    by_size: Dict[int, List[Path]] = {}
    for p in paths:
        try:
            sz = p.stat().st_size
        except FileNotFoundError:
            continue
        if sz >= min_size_bytes:
            by_size.setdefault(sz, []).append(p)

    # For sizes with >1 file, refine by short hash then full hash
    groups: List[List[Path]] = []
    for size, files in by_size.items():
        if len(files) < 2:
            continue
        by_shorthash: Dict[str, List[Path]] = {}
        for p in files:
            by_shorthash.setdefault(short_hash(p), []).append(p)
        for sh, files2 in by_shorthash.items():
            if len(files2) < 2:
                continue
            by_fullhash: Dict[str, List[Path]] = {}
            for p in files2:
                by_fullhash.setdefault(full_hash(p), []).append(p)
            for fh, dupes in by_fullhash.items():
                if len(dupes) > 1:
                    groups.append(dupes)
    return groups


def build_report(root: Path, max_size_mb: int) -> CleanupReport:
    max_bytes = max_size_mb * 1024 * 1024
    logs: List[FileInfo] = []
    temps: List[FileInfo] = []
    caches: List[FileInfo] = []
    big_files: List[FileInfo] = []
    executables: List[FileInfo] = []
    junk_named: List[FileInfo] = []

    all_paths: List[Path] = []
    for p in walk_files(root):
        all_paths.append(p)
        try:
            size = p.stat().st_size
        except FileNotFoundError:
            continue

        if p.name in JUNK_FILE_NAMES:
            junk_named.append(FileInfo(str(p), size))
        if is_log_candidate(p):
            logs.append(FileInfo(str(p), size))
        if is_tmp_candidate(p):
            temps.append(FileInfo(str(p), size))
        if is_executable(p):
            executables.append(FileInfo(str(p), size))
        if size >= max_bytes:
            big_files.append(FileInfo(str(p), size))

    # cache dirs: record their total size
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for d in list(dirnames):
            dp = Path(dirpath) / d
            if is_cache_dir(dp):
                total = 0
                for rp, _, fns in os.walk(dp):
                    for fn in fns:
                        fp = Path(rp) / fn
                        try:
                            total += fp.stat().st_size
                        except FileNotFoundError:
                            pass
                caches.append(FileInfo(str(dp), total))

    dup_groups_paths = group_duplicates(all_paths)
    dup_groups: List[List[FileInfo]] = []
    for grp in dup_groups_paths:
        dup_groups.append([FileInfo(str(p), p.stat().st_size) for p in grp])

    cats = {
        "logs": sorted(logs, key=lambda x: x.size, reverse=True),
        "temps": sorted(temps, key=lambda x: x.size, reverse=True),
        "caches": sorted(caches, key=lambda x: x.size, reverse=True),
        "big_files": sorted(big_files, key=lambda x: x.size, reverse=True),
        "executables": sorted(executables, key=lambda x: x.size, reverse=True),
        "junk_named": sorted(junk_named, key=lambda x: x.size, reverse=True),
    }

    return CleanupReport(
        root=str(root),
        generated_at=time.time(),
        max_size_mb=max_size_mb,
        candidates=cats,
        duplicate_groups=dup_groups,
    )


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_outputs(report: CleanupReport, out_json: Path, out_md: Path) -> None:
    ensure_dir(out_json)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "root": report.root,
                "generated_at": report.generated_at,
                "max_size_mb": report.max_size_mb,
                "candidates": {
                    k: [asdict(fi) for fi in v] for k, v in report.candidates.items()
                },
                "duplicate_groups": [
                    [asdict(fi) for fi in grp] for grp in report.duplicate_groups
                ],
            },
            f,
            indent=2,
        )

    ensure_dir(out_md)
    lines: List[str] = []
    lines.append(f"Cleanup Report for {report.root}")
    lines.append("")
    lines.append(f"Generated: {time.ctime(report.generated_at)}")
    lines.append(f"Max size threshold: {report.max_size_mb} MB")
    lines.append("")

    def add_cat(title: str, items: List[FileInfo], limit: int = 50):
        lines.append(f"## {title}")
        if not items:
            lines.append("(none)")
        else:
            for fi in items[:limit]:
                lines.append(f"- {fi.path}  —  {human_size(fi.size)}")
            if len(items) > limit:
                lines.append(f"… and {len(items) - limit} more")
        lines.append("")

    add_cat("Logs", report.candidates["logs"])
    add_cat("Temp files", report.candidates["temps"])
    add_cat("Cache directories (sizes are totals)", report.candidates["caches"])
    add_cat("Large files", report.candidates["big_files"], limit=100)
    add_cat("Executables", report.candidates["executables"])
    add_cat("Known junk names", report.candidates["junk_named"])

    lines.append("## Duplicate groups (size >= 10MB)")
    if not report.duplicate_groups:
        lines.append("(none)")
    else:
        for grp in report.duplicate_groups:
            size_str = human_size(grp[0].size) if grp else "?"
            lines.append(f"- Group (~{size_str}):")
            for fi in grp:
                lines.append(f"    - {fi.path}")
    lines.append("")

    with out_md.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def delete_candidates(report: CleanupReport) -> Tuple[int, int]:
    """Delete files and cache dirs that are safe to remove.

    We delete: logs, temps, junk_named files, cache directories contents.
    We DO NOT delete: executables or large files automatically (manual review).
    Returns (files_deleted, bytes_freed).
    """
    files_deleted = 0
    bytes_freed = 0

    def try_remove_file(p: Path):
        nonlocal files_deleted, bytes_freed
        try:
            sz = p.stat().st_size
            p.unlink(missing_ok=True)
            files_deleted += 1
            bytes_freed += sz
        except Exception:
            pass

    # remove files
    for cat in ("logs", "temps", "junk_named"):
        for fi in report.candidates.get(cat, []):
            try_remove_file(Path(fi.path))

    # remove cache dirs
    for fi in report.candidates.get("caches", []):
        p = Path(fi.path)
        if p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p, topdown=False):
                for fn in filenames:
                    try_remove_file(Path(dirpath) / fn)
                for dn in dirnames:
                    dp = Path(dirpath) / dn
                    try:
                        dp.rmdir()
                    except Exception:
                        pass
            try:
                p.rmdir()
            except Exception:
                pass

    return files_deleted, bytes_freed


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a cleanup report for the repo"
    )
    parser.add_argument(
        "--root",
        type=str,
        default=str(Path(__file__).resolve().parents[1]),
        help="Root directory to scan",
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        default=50,
        help="Report files larger than this size (in MB)",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(Path("logs/cleanup_report.json")),
        help="Path to write JSON report",
    )
    parser.add_argument(
        "--md-out",
        type=str,
        default=str(Path("logs/cleanup_report.md")),
        help="Path to write Markdown summary",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete junk (logs/temps/caches/junk names)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = build_report(root, args.max_size_mb)
    out_json = Path(args.json_out)
    out_md = Path(args.md_out)
    write_outputs(report, out_json, out_md)

    if args.delete:
        files_deleted, bytes_freed = delete_candidates(report)
        print(f"Deleted {files_deleted} files; freed {human_size(bytes_freed)}")
    else:
        print(f"Report written to {out_json} and {out_md}")

    # Print a short console summary
    cats = report.candidates
    print("Summary:")
    print(f"  Logs: {len(cats['logs'])}")
    print(f"  Temp files: {len(cats['temps'])}")
    print(f"  Cache dirs: {len(cats['caches'])}")
    print(f"  Large files (>{args.max_size_mb}MB): {len(cats['big_files'])}")
    print(f"  Executables: {len(cats['executables'])}")
    print(f"  Known junk names: {len(cats['junk_named'])}")
    print(f"  Duplicate groups (>=10MB): {len(report.duplicate_groups)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
