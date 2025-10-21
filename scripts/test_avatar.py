"""Avatar readiness and throne room probe."""
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, cast

REPO = Path.cwd()
LOGS_DIR = REPO / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = LOGS_DIR / "avatar_test_report.json"
API_BASE = os.getenv("EID_API_BASE", "http://127.0.0.1:8000")


def safe_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore

        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
            return loaded or {}
    except Exception:
        return {}


def http_get(url: str, timeout: float = 2.0) -> Dict[str, Any]:
    started = time.time()
    try:
        try:
            import requests  # type: ignore

            response = requests.get(url, timeout=timeout)
            return {
                "ok": response.ok,
                "status": response.status_code,
                "ms": int((time.time() - started) * 1000),
                "body": response.text[:800],
            }
        except Exception:
            import urllib.error
            import urllib.request

            request = urllib.request.Request(url)
            with urllib.request.urlopen(request, timeout=timeout) as handle:  # type: ignore[attr-defined]
                body = handle.read(1024).decode("utf-8", "ignore")
                status = getattr(handle, "status", 200)
            return {
                "ok": True,
                "status": status,
                "ms": int((time.time() - started) * 1000),
                "body": body,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": None,
            "ms": int((time.time() - started) * 1000),
            "error": str(exc),
        }


def collect_required(api_base: str) -> Dict[str, Dict[str, Any]]:
    required: Dict[str, Dict[str, Any]] = {}

    settings_path = REPO / ".vscode" / "settings.json"
    try:
        if settings_path.exists():
            settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
            interpreter = settings_data.get("python.defaultInterpreterPath")
            required["A1_interpreter"] = {
                "status": "PASS" if interpreter else "WARN",
                "interpreter": interpreter,
            }
        else:
            required["A1_interpreter"] = {
                "status": "WARN",
                "why": "no .vscode/settings.json",
            }
    except Exception as exc:  # noqa: BLE001
        required["A1_interpreter"] = {"status": "WARN", "why": str(exc)}

    try:
        from symbolic_core.se_loader_ext import load_se_engine  # type: ignore

        engine = load_se_engine()
        readiness = getattr(engine, "readiness", None)
        risk = float(getattr(engine, "risk", 1.0) or 1.0)
        reality_alignment = float(getattr(engine, "reality_alignment", 0.0) or 0.0)
        wings = float(getattr(engine, "wings", 1.0) or 1.0)
        gate12 = float(getattr(engine, "gate12", 1.0) or 1.0)
        impetus = float(getattr(engine, "impetus", 0.0) or 0.0)
        ok = (
            readiness in {"ready", "prime_ready"}
            and risk <= 0.20
            and reality_alignment >= 0.90
        )
        required["A2_se43"] = {
            "status": "PASS" if ok else "WARN",
            "readiness": readiness,
            "risk": risk,
            "RA": reality_alignment,
            "wings": wings,
            "gate12": gate12,
            "impetus": impetus,
        }
    except Exception as exc:  # noqa: BLE001
        required["A2_se43"] = {
            "status": "FAIL",
            "why": "load_se_engine failed",
            "error": str(exc),
        }

    config_targets = [
        "config/se43.yml",
        "config/bots.yml",
        "config/avatars.yml",
        "config/citadel.yml",
    ]
    present = {path: (REPO / path).exists() for path in config_targets}
    bots_cfg = safe_yaml(REPO / "config" / "bots.yml")
    se_enforced = bool(bots_cfg.get("se_enforced", False))
    required["A3_configs"] = {
        "status": "PASS" if all(present.values()) and se_enforced else "FAIL",
        "present": present,
        "se_enforced": se_enforced,
    }

    try:
        from bots.registry import load_bots  # type: ignore

        bots = load_bots("config/bots.yml")
        required["B1_bots_load"] = {
            "status": "PASS",
            "count": len(bots),
            "names": [bot.__class__.__name__ for bot in bots],
        }
    except Exception as exc:  # noqa: BLE001
        required["B1_bots_load"] = {"status": "FAIL", "error": str(exc)}

    try:
        audit_path = Path(os.getenv("EIDOLLONA_AUDIT", "logs/audit.ndjson"))
        explain, total = 0, 0
        if audit_path.exists():
            recent = audit_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-1000:]
            for line in recent:
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if event.get("event") in {"q_execute", "brain_reason"}:
                    total += 1
                    if "reasons" in event:
                        explain += 1
            rate = (explain / total) if total else None
            required["B2_explainability"] = {
                "status": "PASS"
                if (rate is not None and rate >= 0.95)
                else ("WARN" if rate is not None else "UNKNOWN"),
                "rate": rate,
                "sample": total,
            }
        else:
            required["B2_explainability"] = {
                "status": "UNKNOWN",
                "why": "no audit file",
            }
    except Exception as exc:  # noqa: BLE001
        required["B2_explainability"] = {
            "status": "UNKNOWN",
            "error": str(exc),
        }

    try:
        from avatar.registry import AvatarRegistry  # type: ignore

        registry = AvatarRegistry()
        registry_any = cast(Any, registry)
        steward_prime = registry_any.get_by_id("steward_prime")
        must_have = [
            "tier",
            "autonomy_max",
            "gates_focus",
            "wing_visibility",
            "hud",
            "voice",
            "style",
        ]
        ok_fields = bool(
            steward_prime
            and all(getattr(steward_prime, field, None) is not None for field in must_have)
        )
        required["D1_steward_prime"] = {
            "status": "PASS" if (steward_prime and ok_fields) else "FAIL",
            "exists": bool(steward_prime),
            "ok_fields": ok_fields,
        }

        se43 = safe_yaml(REPO / "config" / "se43.yml")
        policy = (se43.get("transcendence") or {}).get("wing_use_policy", {})
        show_if = policy.get("show_if", {})
        hide_if = policy.get("hide_if", {})
        wings_min = float(show_if.get("wings_min", 1.03))
        ra_min = float(show_if.get("ra_min", 0.95))
        risk_max = float(show_if.get("risk_max", 0.06))
        risk_over = float(hide_if.get("risk_over", 0.08))

        current = required.get("A2_se43", {})
        global_state = {
            "readiness": current.get("readiness"),
            "wings": current.get("wings", 1.0),
            "RA": current.get("RA", 0.0),
            "risk": current.get("risk", 1.0),
            "wings_min": wings_min,
            "ra_min": ra_min,
            "risk_max": risk_max,
            "risk_over": risk_over,
        }
        visibility_now = (
            registry_any.resolve_wing_visibility("steward_prime", global_state)
            if steward_prime
            else "hide"
        )
        low_ra_state = dict(global_state)
        low_ra_state.update({"RA": ra_min - 0.1})
        high_risk_state = dict(global_state)
        high_risk_state.update({"risk": risk_over + 0.1})
        visibility_low_ra = (
            registry_any.resolve_wing_visibility("steward_prime", low_ra_state)
            if steward_prime
            else "hide"
        )
        visibility_high_risk = (
            registry_any.resolve_wing_visibility("steward_prime", high_risk_state)
            if steward_prime
            else "hide"
        )

        required["D2_wings_visibility"] = {
            "status": "PASS" if visibility_now in {"show", "hide"} else "FAIL",
            "current": visibility_now,
            "policy": {
                "wings_min": wings_min,
                "ra_min": ra_min,
                "risk_max": risk_max,
                "risk_over": risk_over,
            },
            "sim_lowRA": visibility_low_ra,
            "sim_hiRisk": visibility_high_risk,
        }

        needed_avatars = ["serve_it", "fancomp", "treasury_serplus", "markets_trading"]
        exist = {avatar_id: bool(registry_any.get_by_id(avatar_id)) for avatar_id in needed_avatars}
        required["D3_crit_avatars"] = {
            "status": "PASS" if all(exist.values()) else "FAIL",
            "exists": exist,
        }
    except Exception as exc:  # noqa: BLE001
        required["D1_steward_prime"] = {"status": "FAIL", "error": str(exc)}

    return required


def collect_optional(api_base: str) -> Dict[str, Dict[str, Any]]:
    optional: Dict[str, Dict[str, Any]] = {}

    throne_candidates = [
        REPO / "web_interface" / "static" / "webview" / "throne_room.html",
        REPO / "web" / "static" / "throne_room.html",
    ]
    exists = any(path.exists() for path in throne_candidates)
    optional["C5_throne_html"] = {
        "status": "PASS" if exists else "WARN",
        "paths": [str(path) for path in throne_candidates],
        "exists": exists,
    }

    if api_base:
        optional["C1_hud_api"] = http_get(f"{api_base}/api/hud/signals?time_lens=now", timeout=2.0)
        optional["C1_hud_api"].setdefault("status", "PASS" if optional["C1_hud_api"].get("ok") else "FAIL")

        rooms = http_get(f"{api_base}/api/citadel/rooms", timeout=2.0)
        body = rooms.get("body", "")
        has_throne = "throne" in body.lower() or "throne_room" in body.lower()
        rooms_status = "PASS" if rooms.get("ok") and has_throne else ("WARN" if rooms.get("ok") else "FAIL")
        rooms["status"] = rooms_status
        optional["C3_citadel_rooms"] = rooms

        status_banner = http_get(f"{api_base}/api/status", timeout=2.0)
        status_banner.setdefault("status", "PASS" if status_banner.get("ok") else "WARN")
        optional["C2_status_banner"] = status_banner

        qpir = http_get(f"{api_base}/api/qpir/snapshot", timeout=2.0)
        qpir.setdefault("status", "PASS" if qpir.get("ok") else "WARN")
        optional["C4_qpir_snapshot"] = qpir
    else:
        optional["C1_hud_api"] = {"status": "UNKNOWN", "why": "EID_API_BASE not set"}

    optional["E1_status_script"] = {
        "status": "PASS" if (REPO / "scripts" / "set_status_banner.py").exists() else "WARN"
    }
    optional["E2_backend_script"] = {
        "status": "PASS" if (REPO / "scripts" / "serve_backend.py").exists() else "WARN"
    }

    reserves_path = REPO / "public" / "reports" / "reserves_latest.json"
    grants_path = REPO / "public" / "reports" / "grants_latest.json"
    optional["F1_reserves"] = {
        "status": "PASS" if reserves_path.exists() else "WARN",
        "path": str(reserves_path),
    }
    optional["F2_grants"] = {
        "status": "PASS" if grants_path.exists() else "WARN",
        "path": str(grants_path),
    }
    anchors = list((REPO / "anchors").glob("anchor_*.json"))
    optional["F3_anchor"] = {
        "status": "PASS" if anchors else "WARN",
        "count": len(anchors),
    }

    return optional


def decide(required: Dict[str, Dict[str, Any]]) -> str:
    hard_requirements = ["A1_interpreter", "A2_se43", "A3_configs", "B1_bots_load", "D1_steward_prime"]
    hard_fail = any(required.get(key, {}).get("status") == "FAIL" for key in hard_requirements)
    if hard_fail:
        return "FAIL"

    se_ready = required.get("A2_se43", {}).get("status") != "WARN"
    bots_ok = required.get("B1_bots_load", {}).get("status") == "PASS"
    steward_ok = required.get("D1_steward_prime", {}).get("status") == "PASS"
    if se_ready and bots_ok and steward_ok:
        return "PASS"
    return "WARN"


def emit_console_section(section: Dict[str, Dict[str, Any]]) -> None:
    for key, value in section.items():
        status = value.get("status", "")
        payload = {k: v for k, v in value.items() if k != "status"}
        print(f"[{status}] {key} — {json.dumps(payload)[:200]}")


def main() -> None:
    report: Dict[str, Any] = {
        "ts": time.time(),
        "api_base": API_BASE,
        "required": {},
        "optional": {},
        "summary": {},
        "errors": [],
    }

    required = collect_required(API_BASE)
    optional = collect_optional(API_BASE)
    decision = decide(required)

    report["required"].update(required)
    report["optional"].update(optional)
    report["summary"]["awaken_decision"] = decision

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== Avatar / Throne Room Readiness ===")
    emit_console_section(report["required"])
    emit_console_section(report["optional"])
    print(f"\nDecision: AWAKEN = {decision}")
    print(f"Report: {REPORT_PATH}")

    if decision == "FAIL":
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        crash_path = LOGS_DIR / "avatar_test_error.json"
        crash_payload = {
            "status": "CRASH",
            "error": str(exc),
            "trace": traceback.format_exc(),
        }
        crash_path.write_text(json.dumps(crash_payload, indent=2), encoding="utf-8")
        print("Probe crashed — see logs/avatar_test_error.json")
        sys.exit(2)
