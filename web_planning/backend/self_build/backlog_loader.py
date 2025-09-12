from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Tuple
import os
import re


ROOT = Path(__file__).resolve().parents[3]
TREE = ROOT / "PROJECT_TREE.md"
MANIFEST = ROOT / "PROJECT_MANIFEST.md"


_TREE_CHARS = str.maketrans(
    {
        "\u2502": " ",  # │
        "\u251c": " ",  # ├
        "\u2514": " ",  # └
        "\u2500": " ",  # ─
    }
)


def _clean_line(line: str) -> str:
    s = line.translate(_TREE_CHARS)
    s = s.strip()
    s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*", "", s)
    s = re.sub(r"^\s*\[(?: |x|X)\]\s*", "", s)
    return s.strip()


def _priority_weights(prio: str) -> Tuple[float, float]:
    pr = (prio or "").upper()
    if pr == "P1":
        return 0.9, 0.6
    if pr == "P2":
        return 0.7, 0.5
    if pr == "P3":
        return 0.55, 0.45
    return 0.5, 0.5


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\-_. /]+", "-", s)
    s = s.replace(" ", "-")
    s = s.replace("/", "_")
    s = re.sub(r"-+", "-", s)
    return s.strip("-") or "task"


def parse_backlog_text(text: str, source: str) -> List[Dict[str, Any]]:
    """Pure parser for backlog-like markdown text.

    Recognizes lines containing [P], [P1], [P2], [P3]. Returns task dicts with:
    id, title, impact, effort, priority, source, line, tags, path_hint (optional).
    """
    tasks: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for idx, raw in enumerate((text or "").splitlines(), start=1):
        body = _clean_line(raw)
        if not body:
            continue
        m = re.search(r"\[(P[123]?)\]", body)
        if not m:
            continue
        prio = m.group(1) or "P"
        title = body[m.end() :].strip() or body
        title = re.sub(r"^\[(?:P[123]?)\]\s*", "", title).strip()
        impact, effort = _priority_weights(prio if prio != "P" else "")
        t_low = title.lower()
        if any(tok in t_low for tok in ("doc", "readme")):
            impact = min(impact, 0.6)
        if any(tok in t_low for tok in ("test", "lint", "format")):
            effort = min(effort, 0.5)

        tid_base = _slug(title) or _slug(prio)
        tid = tid_base
        dedupe_i = 1
        while tid in seen:
            dedupe_i += 1
            tid = f"{tid_base}-{dedupe_i}"
        seen.add(tid)

        path_hint = title if ("/" in title or "\\" in title) else None
        task = {
            "id": tid,
            "title": title,
            "impact": round(float(impact), 3),
            "effort": round(float(effort), 3),
            "priority": prio,
            "source": source,
            "line": idx,
            "tags": [],
        }
        if path_hint:
            task["path_hint"] = path_hint
        tasks.append(task)
    return tasks


def load_backlog() -> List[Dict[str, Any]]:
    """Aggregate backlog from known project docs.

    Sources (if present): PROJECT_TREE.md, PROJECT_MANIFEST.md.
    Honors BACKLOG_MAX environment variable to limit returned items.
    """
    out: List[Dict[str, Any]] = []
    try:
        if TREE.exists():
            out.extend(
                parse_backlog_text(
                    TREE.read_text(encoding="utf-8"), source="PROJECT_TREE.md"
                )
            )
        if MANIFEST.exists():
            out.extend(
                parse_backlog_text(
                    MANIFEST.read_text(encoding="utf-8"), source="PROJECT_MANIFEST.md"
                )
            )
    except Exception:
        pass

    pr_order = {"P1": 1, "P2": 2, "P3": 3, "P": 9}
    out.sort(
        key=lambda t: (pr_order.get(str(t.get("priority")), 9), str(t.get("title", "")))
    )

    try:
        limit = int(os.getenv("BACKLOG_MAX", "0") or "0")
    except Exception:
        limit = 0
    if limit > 0:
        out = out[:limit]
    return out


__all__ = ["load_backlog", "parse_backlog_text"]
