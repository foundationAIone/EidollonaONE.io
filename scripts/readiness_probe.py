"""Readiness probe for EidollonaONE subsystems."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"
READINESS_JSON = LOGS_DIR / "readiness.json"
PYTHON = sys.executable

MODULE_TEST_MATRIX: List[Dict[str, object]] = [
    {
        "key": "planning",
        "label": "web_planning backend",
        "state": "YELLOW",
        "tests": ["tests/test_planning_api_smoke.py"],
    },
    {
        "key": "security",
        "label": "Security / EMP / EMP Guard",
        "state": "YELLOW",
        "tests": ["tests/test_emp_smoke.py", "tests/test_security_smoke.py"],
    },
    {
        "key": "trading",
        "label": "Trading engine & options",
        "state": "YELLOW",
        "tests": ["tests/test_bs_enhanced.py", "tests/test_trading_slice.py"],
    },
    {
        "key": "ai_learning",
        "label": "ai_learning evaluation",
        "state": "GREEN",
        "tests": ["tests/ai_learning/test_eval_harness.py"],
    },
]

API_ENDPOINTS: Tuple[Tuple[str, str], ...] = (
    ("healthz", "http://127.0.0.1:8802/healthz?token=dev-token"),
    ("status_summary", "http://127.0.0.1:8802/v1/status/summary?token=dev-token"),
)


def run_subprocess(args: List[str], cwd: Path | None = None) -> Tuple[int, str, str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd or REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def run_compile_check() -> Dict[str, object]:
    script = REPO_ROOT / "scripts" / "compile_project.py"
    if not script.exists():
        return {"status": "skipped", "detail": "scripts/compile_project.py not found"}
    code, out, err = run_subprocess([PYTHON, str(script)])
    return {
        "status": "pass" if code == 0 else "fail",
        "returncode": code,
        "stdout": out,
        "stderr": err,
    }


def probe_endpoint(name: str, url: str) -> Dict[str, object]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")
            return {
                "status": "pass" if response.status == 200 else "warn",
                "http_status": response.status,
                "body": body,
            }
    except urllib.error.URLError as exc:
        return {"status": "skipped", "error": str(exc)}


def run_tests(paths: List[str]) -> Dict[str, object]:
    existing = [str(REPO_ROOT / path) for path in paths if (REPO_ROOT / path).exists()]
    if not existing:
        return {"status": "skipped", "detail": "no tests present"}
    rel_args = [str(Path(path).relative_to(REPO_ROOT)) for path in existing]
    code, out, err = run_subprocess([PYTHON, "-m", "pytest", "-q", *rel_args])
    status = "pass" if code == 0 else "fail"
    return {"status": status, "returncode": code, "stdout": out, "stderr": err, "tests": rel_args}


def ensure_logs_dir() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def generate_markdown(summary: Dict[str, object]) -> str:
    lines = ["# Readiness Probe", ""]
    compile_result = summary.get("compile")
    if isinstance(compile_result, dict):
        lines.append("## Compile step")
        lines.append(f"- Status: **{compile_result.get('status', 'unknown').upper()}**")
        if compile_result.get("stderr"):
            lines.append("- Stderr excerpt:")
            lines.append(f"  ```\n{compile_result['stderr'][:400]}\n  ```")
        lines.append("")

    api_results = summary.get("api", {})
    if isinstance(api_results, dict) and api_results:
        lines.append("## API probes")
        for key, result in api_results.items():
            if not isinstance(result, dict):
                continue
            lines.append(f"- `{key}` → **{result.get('status', 'unknown').upper()}**")
        lines.append("")

    module_results = summary.get("modules", {})
    if isinstance(module_results, dict):
        lines.append("## Module tests")
        lines.append("| Module | Declared state | Test status | Details |")
        lines.append("| --- | --- | --- | --- |")
        for key, result in module_results.items():
            if not isinstance(result, dict):
                continue
            label = result.get("label", key)
            state = result.get("state", "?")
            status = result.get("tests", {}).get("status") if isinstance(result.get("tests"), dict) else result.get("tests_status", "?")
            detail = result.get("tests", {}).get("detail", "") if isinstance(result.get("tests"), dict) else ""
            lines.append(f"| {label} | {state} | {status or 'unknown'} | {detail} |")
        lines.append("")

    overall = summary.get("overall", {})
    if isinstance(overall, dict):
        lines.append("## Overall")
        lines.append(f"- Result: **{overall.get('status', 'unknown').upper()}**")
        if overall.get("notes"):
            lines.append(f"- Notes: {overall['notes']}")

    return "\n".join(lines)


def compute_overall(module_results: Dict[str, Dict[str, object]]) -> Dict[str, object]:
    failing = []
    warnings = []
    for key, result in module_results.items():
        tests = result.get("tests")
        if isinstance(tests, dict):
            status = tests.get("status")
        else:
            status = result.get("tests_status")
        if status == "fail":
            failing.append(key)
        elif status not in ("pass", "skipped"):
            warnings.append(key)
    if failing:
        return {"status": "fail", "notes": f"Modules failing tests: {', '.join(failing)}"}
    if warnings:
        return {"status": "warn", "notes": f"Modules with warnings: {', '.join(warnings)}"}
    return {"status": "pass", "notes": "All targeted modules passed or were skipped."}


def main() -> int:
    ensure_logs_dir()

    compile_info = run_compile_check()

    api_results = {name: probe_endpoint(name, url) for name, url in API_ENDPOINTS}

    module_results: Dict[str, Dict[str, object]] = {}
    for module in MODULE_TEST_MATRIX:
        key = str(module["key"])
        module_results[key] = {
            "label": module["label"],
            "state": module["state"],
        }
        tests = module.get("tests", [])
        if isinstance(tests, list):
            module_results[key]["tests"] = run_tests([str(path) for path in tests])
        else:
            module_results[key]["tests"] = {"status": "skipped", "detail": "no tests configured"}

    overall = compute_overall(module_results)

    summary = {
        "timestamp": time.time(),
        "compile": compile_info,
        "api": api_results,
        "modules": module_results,
        "overall": overall,
    }

    READINESS_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    markdown = generate_markdown(summary)
    print(markdown)

    return 0 if overall.get("status") == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
