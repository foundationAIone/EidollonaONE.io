import base64
import gzip
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Settings
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".pytest_cache",
    "eidollona_env",
    "quantum_env",
    "env",
    "envs",
}
INCLUDE_LINE_COUNTS = True
MAX_TEXT_BYTES = 1_048_576  # 1MB
TEXT_EXTS = {
    ".py",
    ".ps1",
    ".psm1",
    ".js",
    ".ts",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".toml",
    ".ini",
    ".cfg",
    ".rs",
    ".go",
    ".java",
    ".cs",
    ".cpp",
    ".c",
    ".hpp",
    ".h",
    ".glsl",
    ".frag",
    ".vert",
    ".sql",
    ".sh",
    ".bat",
    ".zsh",
    ".rb",
    ".php",
    ".lua",
}

ROOT = Path.cwd()


def rel_path(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def is_text_ext(ext: str) -> bool:
    return ext.lower() in TEXT_EXTS


def sha256_file_hex(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def to_base64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def count_lines_if_small_text(path: Path, size: int):
    if not INCLUDE_LINE_COUNTS or size > MAX_TEXT_BYTES:
        return None
    if not is_text_ext(path.suffix):
        return None
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return None


def build_file_list():
    entries = []
    leaf_hashes = []
    total_bytes = 0

    for dirpath, dirnames, filenames in os.walk(ROOT):
        # prune excluded directories in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            # skip if any segment is in EXCLUDE_DIRS (safety for nested)
            if any(seg in EXCLUDE_DIRS for seg in p.relative_to(ROOT).parts):
                continue
            rel = rel_path(p)
            try:
                size = p.stat().st_size
            except FileNotFoundError:
                # transient file removed, skip
                continue
            total_bytes += size
            sha = sha256_file_hex(p)
            mtime_utc = (
                datetime.utcfromtimestamp(p.stat().st_mtime)
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
            lines = count_lines_if_small_text(p, size)

            entries.append(
                {
                    "path": rel,
                    "size": size,
                    "sha256": sha,
                    "mtime_utc": mtime_utc,
                    "lines": lines,
                }
            )

            leaf_str = f"F|{rel}|{size}|{sha}".encode("utf-8")
            leaf_hash = sha256_hex(leaf_str)
            leaf_hashes.append(leaf_hash)

    return entries, leaf_hashes, total_bytes


def merkle_root_from_leaves(leaf_hashes):
    if not leaf_hashes:
        return sha256_hex(b"")
    layer = sorted(leaf_hashes)
    while len(layer) > 1:
        next_layer = []
        i = 0
        while i < len(layer):
            if i == len(layer) - 1:
                pair = (layer[i] + layer[i]).encode("utf-8")
            else:
                pair = (layer[i] + layer[i + 1]).encode("utf-8")
            next_layer.append(sha256_hex(pair))
            i += 2
        layer = next_layer
    return layer[0]


def write_gzip_json(data, out_path: Path):
    js = json.dumps(
        data, ensure_ascii=False, separators=(",", ":"), sort_keys=False
    ).encode("utf-8")
    out_path.write_bytes(gzip.compress(js))
    return js


def main():
    entries, leaf_hashes, total_bytes = build_file_list()
    root = ROOT.name
    created_utc = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    merkle_root = merkle_root_from_leaves(leaf_hashes)

    manifest = {
        "root": root,
        "created_utc": created_utc,
        "files": entries,
        "file_count": len(entries),
        "merkle_root": merkle_root,
        "excludes": sorted(EXCLUDE_DIRS),
        "host": {
            "os": os.name,
            "python": sys.version.split()[0],
        },
    }

    gz_path = ROOT / "eid_manifest.json.gz"
    write_gzip_json(manifest, gz_path)

    manifest_hash_hex = hashlib.sha256(gz_path.read_bytes()).hexdigest()
    manifest_hash16 = manifest_hash_hex[:16]

    root_b64 = to_base64url(merkle_root.encode("utf-8"))
    epoch = int(time.time())

    master = f"MASTER_CODE: EID1:{root_b64}.MH:{manifest_hash16}.FC:{len(entries)}.BY:{total_bytes}.EP:{epoch}"

    # persist and print
    (ROOT / "eid_master_code.txt").write_text(master + "\n", encoding="utf-8")
    print(master)


if __name__ == "__main__":
    main()
