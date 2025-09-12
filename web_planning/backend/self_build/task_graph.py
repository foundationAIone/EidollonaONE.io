from __future__ import annotations

from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict, deque
import re


# Lightweight, dependency-free task graph builder for self_build.
# Inputs: backlog_loader-style task dicts with keys:
#   id, title, impact, effort, priority, source, line, tags, path_hint?
# Outputs: task dicts annotated with deps (list[str]), kind, cluster, score, and layer.


_PREC = {
    "code": 0,
    "refactor": 1,
    "style": 1,
    "test": 2,
    "doc": 2,
}


def _norm_text(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("\\", "/")
    s = re.sub(r"[^a-z0-9_./\- ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _infer_kind(title: str, path_hint: str | None) -> str:
    t = _norm_text(title)
    p = _norm_text(path_hint or "")
    if any(k in t for k in ("test", "tests", "unit", "pytest")) or "test" in p:
        return "test"
    if any(k in t for k in ("doc", "docs", "readme", "guide")) or "docs" in p:
        return "doc"
    if any(k in t for k in ("refactor", "cleanup", "rewrite", "migrate")):
        return "refactor"
    if any(k in t for k in ("lint", "format", "formatter", "style")):
        return "style"
    return "code"


def _cluster_key(task: Dict[str, Any]) -> str:
    # Prefer path-based clustering; normalize away tests/docs segments and extensions
    p = str(task.get("path_hint") or "").strip()
    if p:
        p = _norm_text(p)
        # Remove leading tests/ or docs/
        p = re.sub(r"^(tests?|docs?)/", "", p)
        # Remove any '/tests/' segments
        p = re.sub(r"/tests?/(?!$)", "/", p)
        # Split and clean filename patterns like test_*.py, *_test.py
        parts = [seg for seg in p.split("/") if seg]
        if parts:
            fname = parts[-1]
            # strip extensions
            fname = re.sub(r"\.(?:py|ts|js|md|rst|txt|json|yaml|yml)$", "", fname)
            # remove common test markers
            fname = re.sub(r"^test_", "", fname)
            fname = re.sub(r"_test$", "", fname)
            parts[-1] = fname
        # Use the last two segments to make clusters consistent across deep trees
        tail = parts[-2:] if len(parts) >= 2 else parts
        if tail:
            return "/".join(tail)
    # Fallback to a title-derived base, dropping typical suffix words
    t = _norm_text(task.get("title", ""))
    t = re.sub(
        r"\b(test|tests|doc|docs|readme|guide|lint|format|refactor|cleanup|rewrite|migrate)\b",
        " ",
        t,
    )
    t = re.sub(r"\s+", " ", t).strip()
    return t or task.get("id", "")


def _explicit_mentions(title: str, known_ids: Set[str]) -> Set[str]:
    """Very small parser for explicit dependency mentions in the title.

    Supports patterns like: "depends on XYZ", "after XYZ", or "#task-id".
    Only returns ids that exist in known_ids.
    """
    t = _norm_text(title)
    out: Set[str] = set()
    for pat in (
        r"\bdepends on ([a-z0-9][a-z0-9_\-]*)",
        r"\bafter ([a-z0-9][a-z0-9_\-]*)",
        r"#([a-z0-9][a-z0-9_\-]*)",
    ):
        for m in re.finditer(pat, t):
            cand = m.group(1)
            if cand in known_ids:
                out.add(cand)
    return out


def infer_dependencies(tasks: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """Infer a conservative dependency set using heuristics.

    Heuristics:
    - Cluster tasks by path/title; within a cluster, earlier precedence kinds
      (code -> refactor/style -> test/doc) must precede later ones.
    - Parse explicit mentions like "depends on <id>", "after <id>", or "#<id>".
    Returns: mapping id -> set(dependency_ids)
    """
    id_set: Set[str] = {str(t.get("id")) for t in tasks if t.get("id")}
    kinds: Dict[str, str] = {}
    clusters: Dict[str, List[str]] = defaultdict(list)
    by_id: Dict[str, Dict[str, Any]] = {}
    for t in tasks:
        tid = str(t.get("id"))
        if not tid:
            continue
        kind = _infer_kind(str(t.get("title", "")), str(t.get("path_hint", "")))
        kinds[tid] = kind
        ckey = _cluster_key(t)
        clusters[ckey].append(tid)
        by_id[tid] = t

    deps: Dict[str, Set[str]] = {tid: set() for tid in id_set}

    # Cluster ordering edges
    for ckey, ids in clusters.items():
        # Collect ids per kind
        per_kind: Dict[str, List[str]] = defaultdict(list)
        for tid in ids:
            per_kind[kinds.get(tid, "code")].append(tid)
        # For each later kind, depend on all earlier kinds in this cluster
        for later_kind, later_ids in per_kind.items():
            later_prec = _PREC.get(later_kind, 0)
            earlier_ids: List[str] = []
            for ek, eids in per_kind.items():
                if _PREC.get(ek, 0) < later_prec:
                    earlier_ids.extend(eids)
            if not earlier_ids:
                continue
            for lid in later_ids:
                deps[lid].update(earlier_ids)

    # Explicit mentions
    for t in tasks:
        tid = str(t.get("id"))
        if not tid:
            continue
        mentions = _explicit_mentions(str(t.get("title", "")), id_set)
        if mentions:
            deps[tid].update(mentions)

    return deps


def to_dag(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Annotate tasks into a DAG with inferred dependencies and scheduling hints.

    Adds fields:
    - deps: list[str]
    - kind: str in {code, test, doc, refactor, style}
    - cluster: str (grouping key)
    - score: float (impact / (effort+1e-3))
    - layer: int (0-based topological layer; best-effort if cycles exist)
    """
    deps_map = infer_dependencies(tasks)
    out: List[Dict[str, Any]] = []
    for t in tasks:
        tid = str(t.get("id"))
        kind = _infer_kind(str(t.get("title", "")), str(t.get("path_hint", "")))
        cluster = _cluster_key(t)
        impact = float(t.get("impact", 0.0) or 0.0)
        effort = float(t.get("effort", 0.0) or 0.0)
        score = impact / (effort + 1e-3)
        node = {
            **t,
            "deps": sorted(deps_map.get(tid, set())),
            "kind": kind,
            "cluster": cluster,
            "score": round(score, 4),
        }
        out.append(node)

    # Assign layers using Kahn's algorithm
    layers = topological_layers(out)
    layer_index: Dict[str, int] = {}
    for i, layer in enumerate(layers):
        for tid in layer:
            layer_index[tid] = i
    for n in out:
        n["layer"] = int(layer_index.get(str(n.get("id")), 0))
    return out


def topological_order(dag: List[Dict[str, Any]]) -> List[str]:
    """Return a topologically sorted list of task ids. Falls back to stable order."""
    layers = topological_layers(dag)
    if not layers:
        return [str(n.get("id")) for n in dag]
    return [tid for layer in layers for tid in layer]


def topological_layers(dag: List[Dict[str, Any]]) -> List[List[str]]:
    """Return layered Kahn topological ordering. On cycles, leftover nodes go to the last layer."""
    # Build graph
    nodes = [str(n.get("id")) for n in dag if n.get("id")]
    deps_of: Dict[str, Set[str]] = {
        str(n.get("id")): set(map(str, n.get("deps", []))) for n in dag if n.get("id")
    }
    children: Dict[str, Set[str]] = {nid: set() for nid in nodes}
    for nid, ds in deps_of.items():
        for d in ds:
            if d in children:
                children[d].add(nid)

    # Kahn
    indeg: Dict[str, int] = {nid: len(deps_of.get(nid, set())) for nid in nodes}
    q = deque(sorted([nid for nid, k in indeg.items() if k == 0]))
    layers: List[List[str]] = []
    visited: Set[str] = set()
    while q:
        level: List[str] = []
        # Process current frontier, but collect next frontier
        next_q: List[str] = []
        while q:
            u = q.popleft()
            if u in visited:
                continue
            visited.add(u)
            level.append(u)
            for v in sorted(children.get(u, set())):
                if v in visited:
                    continue
                indeg[v] = max(0, indeg.get(v, 0) - 1)
                if indeg[v] == 0:
                    next_q.append(v)
        if level:
            layers.append(level)
        q = deque(sorted(next_q))

    # Any nodes left (cycle or unreachable) go to a final layer in stable order
    rem = [nid for nid in nodes if nid not in visited]
    if rem:
        # Sort by priority-ish: layer last, then by id
        layers.append(sorted(rem))
    return layers


def critical_path(
    dag: List[Dict[str, Any]], weight_key: str = "effort"
) -> Tuple[float, List[str]]:
    """Compute a critical path length and one of the longest paths by weight.

    Assumes non-negative weights. If cycles exist, nodes in the last layer are skipped from the path.
    Returns (total_weight, path_ids).
    """
    # Map id to node and deps
    nodes = {str(n.get("id")): n for n in dag if n.get("id")}
    order = topological_order(dag)
    # If we had a cycle, nodes in the final layer after cycles are present too; dp will just ignore back-edges.
    dist: Dict[str, float] = {
        nid: float(nodes[nid].get(weight_key, 0.0) or 0.0)
        for nid in order
        if nid in nodes
    }
    prev: Dict[str, str | None] = {nid: None for nid in order if nid in nodes}
    for nid in order:
        n = nodes.get(nid)
        if not n:
            continue
        w = float(n.get(weight_key, 0.0) or 0.0)
        for v in [str(c) for c in n.get("deps", [])]:
            # Ensure v is before nid; otherwise skip
            if v not in dist:
                continue
            if dist[v] + w > dist[nid]:
                dist[nid] = dist[v] + w
                prev[nid] = v
    # Find best end
    if not dist:
        return 0.0, []
    end = max(dist, key=lambda k: dist[k])
    total = float(dist[end])
    path: List[str] = []
    cur = end
    seen: Set[str] = set()
    while cur and cur not in seen:
        path.append(cur)
        seen.add(cur)
        cur = prev.get(cur) or None
    path.reverse()
    return total, path


__all__ = [
    "to_dag",
    "infer_dependencies",
    "topological_order",
    "topological_layers",
    "critical_path",
]
