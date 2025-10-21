"""Scan repo for avatar model assets and references."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence, TypedDict

MODEL_EXTENSIONS = {".glb", ".gltf", ".fbx", ".obj", ".mtl", ".dae"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}
TEXT_EXTENSIONS = {
    ".yml",
    ".yaml",
    ".json",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".html",
    ".css",
}
KEYWORDS = ("steward_prime", "glb", "gltf", "model", "mesh", "throne")


class InventoryEntry(TypedDict):
    path: str
    bytes: int
    bytes_h: str


class DirectoryCount(TypedDict):
    dir: str
    count: int


class ReferenceEntry(TypedDict):
    file: str
    hits: int


class ReportCounts(TypedDict):
    models: int
    images: int
    refs: int


class Report(TypedDict):
    timestamp: str
    repo: str
    counts: ReportCounts
    top_models: list[InventoryEntry]
    top_images: list[InventoryEntry]
    model_dirs: list[DirectoryCount]
    image_dirs: list[DirectoryCount]
    references: list[ReferenceEntry]


def human_bytes(num: int) -> str:
    if num >= 1024**3:
        return f"{num / 1024**3:.2f} GB"
    if num >= 1024**2:
        return f"{num / 1024**2:.2f} MB"
    if num >= 1024:
        return f"{num / 1024:.2f} KB"
    return f"{num} B"


def iter_matching_files(root: Path, extensions: set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in extensions:
            yield path


def collect_file_inventory(paths: Iterable[Path]) -> list[InventoryEntry]:
    inventory: list[InventoryEntry] = []
    for path in paths:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        inventory.append(
            {
                "path": str(path),
                "bytes": int(size),
                "bytes_h": human_bytes(size),
            }
        )
    return inventory


def top_entries(items: Sequence[InventoryEntry], limit: int) -> list[InventoryEntry]:
    return sorted(items, key=lambda item: item["bytes"], reverse=True)[:limit]


def dir_counts(items: Sequence[InventoryEntry]) -> list[DirectoryCount]:
    counter: Counter[str] = Counter()
    for item in items:
        path = Path(item["path"])
        counter[str(path.parent)] += 1
    return [
        {"dir": directory, "count": count}
        for directory, count in counter.most_common(10)
    ]


def scan_references(root: Path) -> list[ReferenceEntry]:
    totals: Counter[str] = Counter()
    keyword_pattern = re.compile("|".join(re.escape(word) for word in KEYWORDS), re.IGNORECASE)
    for path in iter_matching_files(root, TEXT_EXTENSIONS):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matches = keyword_pattern.findall(content)
        if matches:
            totals[str(path)] = len(matches)
    return [{"file": file_path, "hits": hits} for file_path, hits in totals.most_common()]


def build_report(repo: Path, top_n: int) -> Report:
    models = collect_file_inventory(iter_matching_files(repo, MODEL_EXTENSIONS))
    images = collect_file_inventory(iter_matching_files(repo, IMAGE_EXTENSIONS))
    references = scan_references(repo)

    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "timestamp": timestamp,
        "repo": str(repo),
        "counts": {
            "models": len(models),
            "images": len(images),
            "refs": sum(item["hits"] for item in references),
        },
        "top_models": top_entries(models, top_n),
        "top_images": top_entries(images, top_n),
        "model_dirs": dir_counts(models),
        "image_dirs": dir_counts(images),
        "references": references,
    }


def write_report(report: Report, repo: Path) -> Path:
    logs_dir = repo / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    filename = f"avatar_assets_scan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out_path = logs_dir / filename
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out_path


def print_summary(report: Report, top_n: int) -> None:
    counts = report["counts"]
    print("\n=== Avatar Asset Scan (report-only) ===")
    print(
        "Models found: {models} | Images: {images} | Text refs: {refs}".format(
            models=counts["models"], images=counts["images"], refs=counts["refs"]
        )
    )

    top_models = report["top_models"][:top_n]
    if top_models:
        print("\nTop model files:")
        for item in top_models:
            print(f" - {item['path']}  {item['bytes_h']}")
    else:
        print("\nNo model files (*.glb|*.gltf|*.fbx|*.obj|*.mtl|*.dae) found.")

    top_images = report["top_images"][:top_n]
    if top_images:
        print("\nTop images:")
        for item in top_images:
            print(f" - {item['path']}  {item['bytes_h']}")

    references = report["references"][:10]
    if references:
        print("\nFiles with most avatar/model refs:")
        for item in references:
            print(f" - {item['file']}  ({item['hits']} hits)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report avatar asset files and references.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Repository root to scan (default: current directory)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=12,
        help="Maximum number of top model/image files to list (default: 12)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    if not repo.exists():
        raise SystemExit(f"Repo not found: {repo}")

    report = build_report(repo, args.top)
    out_path = write_report(report, repo)
    print_summary(report, args.top)
    print(f"\nSaved JSON report -> {out_path}")


if __name__ == "__main__":
    main()
