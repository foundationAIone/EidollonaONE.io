"""Avatar preview readiness probe."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

CHECKS: Dict[str, Dict[str, Any]] = {}
NEXT_STEPS: List[str] = []


def _add_check(name: str, status: str, info: Dict[str, Any], next_step: str | None = None) -> None:
    entry = {"status": status}
    entry.update(info)
    CHECKS[name] = entry
    if next_step:
        NEXT_STEPS.append(next_step)


def check_popup() -> None:
    path = ROOT / "web_interface" / "static" / "webview" / "avatar_popup.html"
    if path.exists():
        _add_check("popup_html", "PASS", {"path": str(path)})
    else:
        _add_check(
            "popup_html",
            "FAIL",
            {"path": str(path)},
            "Create web_interface/static/webview/avatar_popup.html",
        )


def check_server_mounts() -> None:
    path = ROOT / "scripts" / "avatar_preview_server.py"
    if not path.exists():
        _add_check(
            "server_mounts",
            "FAIL",
            {"path": str(path)},
            "Ensure scripts/avatar_preview_server.py exists with /webview and /static mounts",
        )
        return

    content = path.read_text(encoding="utf-8", errors="ignore")
    has_webview = 'app.mount("/webview"' in content or "app.mount(\"/webview\"" in content
    has_static = 'app.mount("/static"' in content or "app.mount(\"/static\"" in content
    if has_webview and has_static:
        _add_check("server_mounts", "PASS", {"path": str(path)})
    else:
        missing = []
        if not has_webview:
            missing.append("/webview")
        if not has_static:
            missing.append("/static")
        _add_check(
            "server_mounts",
            "FAIL",
            {"path": str(path), "missing": missing},
            "Update scripts/avatar_preview_server.py to mount both /webview and /static",
        )


def check_api_model_url() -> None:
    path = ROOT / "web_interface" / "server" / "avatar_preview_api.py"
    if not path.exists():
        _add_check(
            "preview_api",
            "FAIL",
            {"path": str(path)},
            "Ensure web_interface/server/avatar_preview_api.py exists and returns model_url",
        )
        return

    content = path.read_text(encoding="utf-8", errors="ignore")
    has_function = "def avatar_preview" in content
    has_model_url = "model_url" in content and '"model_url"' in content
    if has_function and has_model_url:
        _add_check("preview_api", "PASS", {"path": str(path)})
    else:
        missing = []
        if not has_function:
            missing.append("avatar_preview function")
        if not has_model_url:
            missing.append("model_url")
        _add_check(
            "preview_api",
            "FAIL",
            {"path": str(path), "missing": missing},
            "Update web_interface/server/avatar_preview_api.py to expose model_url",
        )


def check_models() -> None:
    candidates = [
        ROOT / "web_interface/static/models/steward_prime.glb",
        ROOT / "web_interface/static/models/avatar.glb",
        ROOT / "assets/models/steward_prime.glb",
    ]
    found_primary = None
    for candidate in candidates:
        if candidate.exists():
            found_primary = candidate
            break

    glb_files: List[Path] = []
    for pattern in ("*.glb", "*.gltf"):
        glb_files.extend(ROOT.rglob(pattern))

    glb_data = []
    for file_path in glb_files:
        try:
            size = file_path.stat().st_size
        except OSError:
            continue
        glb_data.append((file_path, size))

    glb_data.sort(key=lambda item: item[1], reverse=True)
    top_entries = [
        {"path": str(path), "bytes": size}
        for path, size in glb_data[:10]
    ]

    if found_primary is not None:
        _add_check(
            "models",
            "PASS",
            {
                "primary": str(found_primary),
                "top": top_entries,
            },
        )
    elif top_entries:
        _add_check(
            "models",
            "WARN",
            {
                "primary": None,
                "top": top_entries,
            },
            "Place a GLB at web_interface/static/models/steward_prime.glb for the preview",
        )
    else:
        _add_check(
            "models",
            "WARN",
            {"primary": None, "top": []},
            "Add a GLB model under web_interface/static/models/ to enable 3D preview",
        )


def check_python_runtime() -> None:
    settings_path = ROOT / ".vscode" / "settings.json"
    configured = None
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            configured = data.get("python.defaultInterpreterPath")
        except Exception:
            configured = None

    interpreter = None
    args: List[str] = []
    source = "settings"

    if configured:
        interpreter = configured
    else:
        source = "python"
        python_cmd = shutil.which("python")
        if python_cmd:
            interpreter = python_cmd
        else:
            py_cmd = shutil.which("py")
            if py_cmd:
                interpreter = py_cmd
                args = ["-3"]
                source = "py"

    if not interpreter:
        _add_check(
            "python",
            "FAIL",
            {"detail": "Interpreter not found"},
            "Install Python or set python.defaultInterpreterPath in .vscode/settings.json",
        )
        return

    check_cmd = [interpreter, *args, "-c", "import fastapi, uvicorn"]
    try:
        subprocess.run(
            check_cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        _add_check("python", "PASS", {"interpreter": interpreter, "source": source, "args": args})
    except subprocess.CalledProcessError as exc:
        suggestion = (
            f"{interpreter} {' '.join(args)} -m pip install fastapi uvicorn".strip()
        )
        detail = exc.stderr.strip() if exc.stderr else exc.stdout.strip()
        _add_check(
            "python",
            "WARN",
            {
                "interpreter": interpreter,
                "source": source,
                "args": args,
                "error": detail,
            },
            f"Install FastAPI/Uvicorn via: {suggestion}",
        )


def check_launcher() -> None:
    path = ROOT / "scripts" / "run_avatar_preview.ps1"
    if path.exists():
        _add_check("launcher", "PASS", {"path": str(path)})
    else:
        _add_check(
            "launcher",
            "FAIL",
            {"path": str(path)},
            "Add scripts/run_avatar_preview.ps1 or run the preview manually",
        )


def build_decision() -> str:
    if any(entry["status"] == "FAIL" for entry in CHECKS.values()):
        return "FAIL"
    if any(entry["status"] == "WARN" for entry in CHECKS.values()):
        return "WARN"
    return "PASS"


def emit_console(decision: str) -> None:
    print("=== Avatar Preview Readiness ===")
    for name, data in CHECKS.items():
        status = data.get("status", "UNKNOWN")
        payload = {k: v for k, v in data.items() if k != "status"}
        preview = json.dumps(payload, ensure_ascii=False)[:200]
        print(f"[{status}] {name} — {preview}")
    print(f"\nDecision: {decision}")
    if NEXT_STEPS:
        for step in NEXT_STEPS:
            print(f" - Next: {step}")


def write_report(decision: str) -> None:
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "decision": decision,
        "checks": CHECKS,
        "next_steps": NEXT_STEPS,
    }
    out_path = LOGS_DIR / "avatar_preview_ready.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report: {out_path}")


def main() -> None:
    check_popup()
    check_server_mounts()
    check_api_model_url()
    check_models()
    check_python_runtime()
    check_launcher()

    decision = build_decision()
    emit_console(decision)
    write_report(decision)

    if decision == "FAIL":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
