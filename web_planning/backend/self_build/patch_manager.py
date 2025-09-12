from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import hashlib
import json
import re
import time


PATCH_DIR = Path(__file__).resolve().parent / "patches"
PATCH_DIR.mkdir(parents=True, exist_ok=True)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_path(p: str) -> bool:
    # No traversal or absolute
    if p.startswith("/") or p.startswith("\\"):
        return False
    if ".." in p.replace("\\", "/"):
        return False
    return True


def validate_diff(
    diff: str,
    *,
    add_only: bool = True,
    max_bytes: int = 256_000,
    max_files: int = 50,
    allowed_prefixes: List[str] | None = None,
) -> Dict[str, Any]:
    """Lightweight validation of a unified diff to keep it SAFE.

    Defaults to add-only patches (each file hunk must be a new file from /dev/null),
    limits size and file count, forbids binary/rename/delete, and constrains paths
    to allowed prefixes.
    """
    allowed_prefixes = allowed_prefixes or [
        "web_planning/backend/tests/",
        "web_planning/backend/self_build/artifacts/",
    ]

    txt = diff or ""
    ok = True
    issues: List[str] = []
    files: List[Dict[str, Any]] = []

    if len(txt.encode("utf-8")) > max_bytes:
        ok = False
        issues.append("too_large")

    if "GIT binary patch" in txt or re.search(r"^Binary files ", txt, flags=re.M):
        ok = False
        issues.append("binary_patch")

    # Parse file hunks
    file_re = re.compile(r"^diff --git a/(.+?) b/(.+)$")
    lines = txt.splitlines()
    i = 0
    count = 0
    while i < len(lines):
        m = file_re.match(lines[i])
        if not m:
            i += 1
            continue
        a_path, b_path = m.group(1), m.group(2)
        count += 1
        cur = {"a": a_path, "b": b_path, "add_only": False, "ok": True, "reasons": []}
        i += 1
        # Collect headers for this file
        new_file = False
        deleted = False
        renamed = False
        apath = None
        bpath = None
        while i < len(lines) and not lines[i].startswith("diff --git "):
            L = lines[i]
            if L.startswith("new file mode"):
                new_file = True
            if L.startswith("deleted file mode"):
                deleted = True
            if L.startswith("rename from ") or L.startswith("rename to "):
                renamed = True
            if L.startswith("--- "):
                apath = L[4:]
            if L.startswith("+++ "):
                bpath = L[4:]
            i += 1

        # Validate
        if deleted:
            cur["ok"] = False
            cur["reasons"].append("deletion_not_allowed")
        if renamed:
            cur["ok"] = False
            cur["reasons"].append("rename_not_allowed")
        if add_only:
            if not (
                new_file and apath == "/dev/null" and (bpath or "").startswith("b/")
            ):
                cur["ok"] = False
                cur["reasons"].append("not_add_only")
            else:
                cur["add_only"] = True

        # Path constraints
        target = (bpath or "")[2:] if (bpath or "").startswith("b/") else b_path
        if not _safe_path(target):
            cur["ok"] = False
            cur["reasons"].append("unsafe_path")
        if allowed_prefixes and not any(target.startswith(p) for p in allowed_prefixes):
            cur["ok"] = False
            cur["reasons"].append("disallowed_prefix")

        files.append(cur)

    if count == 0:
        ok = False
        issues.append("no_files")
    if count > max_files:
        ok = False
        issues.append("too_many_files")

    # Aggregate file statuses
    if any(not f.get("ok", False) for f in files):
        ok = False

    return {"ok": ok, "issues": issues, "files": files, "count": count}


def save_patch(patch_id: str, diff: str) -> Path:
    p = PATCH_DIR / f"{patch_id}.patch"
    p.write_text(diff, encoding="utf-8")
    # write metadata
    meta = {
        "id": patch_id,
        "sha256": _sha256(diff or ""),
        "created": time.time(),
        "size": len((diff or "").encode("utf-8")),
    }
    (PATCH_DIR / f"{patch_id}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return p


def ingest_patch(patch_id: str, diff: str, *, add_only: bool = True) -> Dict[str, Any]:
    """Validate and persist a patch. Returns {ok, path?, meta?, details}.
    Rejects unsafe diffs.
    """
    details = validate_diff(diff, add_only=add_only)
    if not details.get("ok"):
        return {"ok": False, "details": details}
    path = save_patch(patch_id, diff)
    meta = json.loads((PATCH_DIR / f"{patch_id}.json").read_text(encoding="utf-8"))
    return {"ok": True, "path": str(path), "meta": meta, "details": details}


def list_patches() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for jf in sorted(PATCH_DIR.glob("*.json")):
        try:
            meta = json.loads(jf.read_text(encoding="utf-8"))
            meta["path"] = str(PATCH_DIR / f"{meta.get('id')}.patch")
            out.append(meta)
        except Exception:
            continue
    return out


def load_patch(patch_id: str) -> str:
    return (PATCH_DIR / f"{patch_id}.patch").read_text(encoding="utf-8")


def delete_patch(patch_id: str) -> bool:
    ok = True
    try:
        (PATCH_DIR / f"{patch_id}.patch").unlink(missing_ok=True)
        (PATCH_DIR / f"{patch_id}.json").unlink(missing_ok=True)
    except Exception:
        ok = False
    return ok


__all__ = [
    "validate_diff",
    "save_patch",
    "ingest_patch",
    "list_patches",
    "load_patch",
    "delete_patch",
]
