#!/usr/bin/env python3
"""Promotion sweep utility.

Runs lightweight verification for selected modules, stores evidence, and
emits audit events so Capstone can display promotion readiness.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Iterable as IterableABC
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import md5
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
LOG_DIR = ROOT / "logs"
PROMO_DIR = LOG_DIR / "promo"
AUDIT_LOG = LOG_DIR / "audit.ndjson"
DEFAULT_MATRIX = SCRIPTS_DIR / "promo_matrix.json"
PYTEST_TIMEOUT = int(os.getenv("PROMO_PYTEST_TIMEOUT", "600"))
DIR_CHECK_FILE_LIMIT = int(os.getenv("PROMO_DIR_FILE_LIMIT", "5"))
DIR_CHECK_TAIL_BYTES = int(os.getenv("PROMO_DIR_TAIL_BYTES", "1024"))


@dataclass
class SmokeResult:
    name: str
    status: str
    detail: Optional[str] = None


@dataclass
class EndpointResult:
    route: str
    status: str
    code: Optional[int] = None
    detail: Optional[str] = None


@dataclass
class ArtifactResult:
    path: str
    status: str
    detail: Optional[str] = None
    checksum: Optional[str] = None


@dataclass
class ModuleResult:
    name: str
    passed: bool
    smokes: List[SmokeResult]
    endpoints: List[EndpointResult]
    artifacts: List[ArtifactResult]
    errors: List[str]
    timestamp: float

    def to_json(self) -> Dict[str, object]:
        return {
            "module": self.name,
            "pass": self.passed,
            "ts": self.timestamp,
            "smokes": [sr.__dict__ for sr in self.smokes],
            "endpoints": [er.__dict__ for er in self.endpoints],
            "artifacts": [ar.__dict__ for ar in self.artifacts],
            "errors": self.errors,
        }


def load_matrix(path: Path) -> Dict[str, Dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def coerce_str_list(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, IterableABC):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def run_compile_probe() -> Tuple[bool, str]:
    compile_script = SCRIPTS_DIR / "compile_project.py"
    if not compile_script.exists():
        return True, "compile_project.py missing; skipping compile probe"
    cmd = [sys.executable, str(compile_script)]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"compile probe failed to launch: {exc}"
    success = completed.returncode == 0
    summary = (completed.stdout or "").strip().splitlines()
    tail = summary[-1] if summary else "compile_project.py executed"
    if not success:
        detail = (completed.stderr or "").strip()
        tail = f"compile_project.py failed: {detail or 'unknown error'}"
    return success, tail


def run_pytest(path: str) -> SmokeResult:
    cmd = [sys.executable, "-m", "pytest", "-q", path]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=PYTEST_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SmokeResult(path, "fail", "timeout")
    except Exception as exc:  # pragma: no cover - defensive
        return SmokeResult(path, "fail", f"error launching pytest: {exc}")

    if completed.returncode == 0:
        return SmokeResult(path, "pass")
    detail = (completed.stdout or "") + "\n" + (completed.stderr or "")
    detail = detail.strip()[-4000:]
    return SmokeResult(path, "fail", detail or "pytest reported failures")


def normalize_endpoint(base: str, route: str, token: str) -> str:
    parsed = urlparse(base)
    route_parsed = urlparse(route)
    if route_parsed.scheme and route_parsed.netloc:
        merged = route_parsed
    else:
        path = route_parsed.path if route_parsed.path.startswith("/") else f"/{route_parsed.path}"
        merged = parsed._replace(path=path, query=route_parsed.query)
    query = dict()
    if merged.query:
        query.update({kv.split("=", 1)[0]: kv.split("=", 1)[1] for kv in merged.query.split("&") if kv})
    query.setdefault("token", token)
    merged = merged._replace(query=urlencode(query))
    return urlunparse(merged)


def ping_endpoint(url: str) -> EndpointResult:
    req = Request(url, headers={"User-Agent": "promo-sweep/1.0"})
    try:
        with urlopen(req, timeout=10) as resp:
            status = resp.status
            return EndpointResult(url, "pass" if 200 <= status < 400 else "fail", code=status)
    except HTTPError as err:
        return EndpointResult(url, "fail", code=err.code, detail=str(err))
    except URLError as err:
        return EndpointResult(url, "fail", detail=str(err.reason))
    except Exception as exc:  # pragma: no cover - defensive
        return EndpointResult(url, "fail", detail=str(exc))


def newest_files(directory: Path, limit: int) -> List[Path]:
    files: List[Tuple[float, Path]] = []
    for item in directory.rglob("*"):
        if item.is_file():
            try:
                files.append((item.stat().st_mtime, item))
            except OSError:
                continue
    files.sort(key=lambda entry: entry[0], reverse=True)
    return [entry[1] for entry in files[:limit]]


def checksum_tail(files: Iterable[Path], tail_bytes: int) -> str:
    digest = md5()
    for file_path in files:
        try:
            with file_path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                seek_pos = max(0, size - tail_bytes)
                handle.seek(seek_pos)
                digest.update(handle.read())
        except OSError:
            continue
    return digest.hexdigest()


def check_artifact(root: Path, relative: str) -> ArtifactResult:
    target = root / relative
    if not target.exists():
        return ArtifactResult(relative, "fail", "missing")
    if target.is_file():
        try:
            size = target.stat().st_size
            detail = f"file {size} bytes"
            checksum = checksum_tail([target], DIR_CHECK_TAIL_BYTES)
            return ArtifactResult(relative, "pass", detail=detail, checksum=checksum)
        except OSError as exc:
            return ArtifactResult(relative, "fail", f"unreadable: {exc}")
    if target.is_dir():
        newest = newest_files(target, DIR_CHECK_FILE_LIMIT)
        if not newest:
            return ArtifactResult(relative, "warn", "directory empty")
        checksum = checksum_tail(newest, DIR_CHECK_TAIL_BYTES)
        detail = f"dir files={len(newest)}"
        return ArtifactResult(relative, "pass", detail=detail, checksum=checksum)
    return ArtifactResult(relative, "warn", "unknown file type")


def append_audit_event(module: str, ts: float) -> None:
    ensure_dir(AUDIT_LOG.parent)
    event = {
        "event": "promo_green",
        "module": module,
        "ts": ts,
        "when": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")


def sweep_module(
    name: str,
    spec: Dict[str, object],
    base: str,
    token: str,
) -> ModuleResult:
    errors: List[str] = []
    smokes: List[SmokeResult] = []
    endpoints: List[EndpointResult] = []
    artifacts: List[ArtifactResult] = []

    smoke_paths = coerce_str_list(spec.get("smoke"))
    for path in smoke_paths:
        smokes.append(run_pytest(path))

    endpoint_routes = coerce_str_list(spec.get("endpoints"))
    for route in endpoint_routes:
        url = normalize_endpoint(base, route, token)
        endpoints.append(ping_endpoint(url))

    artifact_entries = coerce_str_list(spec.get("artifacts"))
    for rel in artifact_entries:
        artifacts.append(check_artifact(ROOT, rel))

    passed = True
    for smoke in smokes:
        if smoke.status != "pass":
            passed = False
            if smoke.detail:
                errors.append(f"smoke {smoke.name}: {smoke.detail}")
    for endpoint in endpoints:
        if endpoint.status != "pass":
            passed = False
            detail = endpoint.detail or ""
            errors.append(f"endpoint {endpoint.route}: {endpoint.code or ''} {detail}".strip())
    for artifact in artifacts:
        if artifact.status == "fail":
            passed = False
            if artifact.detail:
                errors.append(f"artifact {artifact.path}: {artifact.detail}")

    timestamp = time.time()
    result = ModuleResult(name, passed, smokes, endpoints, artifacts, errors, timestamp)

    ensure_dir(PROMO_DIR)
    evidence_path = PROMO_DIR / f"{name}.json"
    with evidence_path.open("w", encoding="utf-8") as handle:
        json.dump(result.to_json(), handle, indent=2, sort_keys=True)

    if passed:
        append_audit_event(name, timestamp)

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run promotion sweep for selected modules.")
    parser.add_argument("--modules", help="Comma-separated list of modules to sweep")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX), help="Path to promo matrix JSON")
    parser.add_argument("--base", default=os.getenv("BASE", "http://127.0.0.1:8802"), help="Base URL for endpoint checks")
    parser.add_argument("--token", default=os.getenv("TOKEN", "dev-token"), help="Token to append to endpoint requests")
    return parser.parse_args()


def print_summary(results: List[ModuleResult]) -> None:
    print("| Module | Pass | Timestamp | Notes |")
    print("| --- | --- | --- | --- |")
    for res in results:
        status = "✅" if res.passed else "⚠️"
        dt = datetime.fromtimestamp(res.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        note = "; ".join(res.errors) if res.errors else "" if res.passed else "check evidence"
        evidence_link = f"logs/promo/{res.name}.json"
        note = f"{note} ({evidence_link})" if note else evidence_link
        print(f"| {res.name} | {status} | {dt} | {note} |")


def main() -> int:
    args = parse_args()
    matrix_path = Path(args.matrix).resolve()
    if not matrix_path.exists():
        print(f"Matrix file not found: {matrix_path}", file=sys.stderr)
        return 2

    matrix = load_matrix(matrix_path)

    selected_modules: List[str]
    if args.modules:
        requested = [item.strip() for item in args.modules.split(",") if item.strip()]
        selected_modules = [item for item in requested if item in matrix]
        missing = [item for item in requested if item not in matrix]
        if missing:
            print(f"Warning: unknown modules skipped: {', '.join(missing)}", file=sys.stderr)
    else:
        selected_modules = sorted(matrix.keys())

    if not selected_modules:
        print("No modules selected", file=sys.stderr)
        return 2

    compile_ok, compile_msg = run_compile_probe()
    print(f"Compile probe: {'PASS' if compile_ok else 'FAIL'} — {compile_msg}")

    results: List[ModuleResult] = []
    for module in selected_modules:
        spec = matrix[module]
        results.append(sweep_module(module, spec, args.base, args.token))

    print_summary(results)

    overall_pass = all(res.passed for res in results) and compile_ok
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
