# ========================= EIDOLONALPHA+ ALL-IN BRING-UP (SE4.3 • Wings/Aletheia) =========================
$ErrorActionPreference='Stop'
$root = Get-Location

# --- Paths ---
$cfg="$root\config"; $logs="$root\logs"; $syms="$root\symbolic_core"; $avatar="$root\avatar"; $cit="$root\citadel"
$ai="$root\ai_core"; $qcore="$ai\quantum_core"; $qlogic="$ai\quantum_core\quantum_logic"
$qpir="$root\quantum_probabilistic_information_rendering_system"; $pqr="$root\probabilistic_quantum_rendering"
$web="$root\web_interface"; $websrv="$root\web_interface\server"; $scripts="$root\scripts"; $metric="$root\scripts\metrics"; $qre="$root\qre"

# --- Ensure dirs ---
New-Item -Force -ItemType Directory $cfg,$logs,$syms,$avatar,$cit,$ai,$qcore,$qlogic,$qpir,$pqr,$web,$websrv,$scripts,$metric,$qre | Out-Null

# --- Seed audit ---
$aud="$logs\audit.ndjson"; if(!(Test-Path $aud)){ New-Item -Force -ItemType File $aud | Out-Null }

# ================================= CONFIGS =================================
# se43.yml (transcendence policy + SAFE defaults)
Set-Content -Encoding UTF8 "$cfg\se43.yml" @"
se_version: 4.3
base_mode: lotus12
chakra8_online: true
audit_ndjson: true

alignment:
  gamma: 0.7
  verified_only: true

assimilation:
  sensors: consented_only
  internet: verified_only

wings:
  cognition: on
  omega_max: 0.06
  avatar_visibility: auto

transcendence:
  nature: true
  wing_use_policy:
    override: auto
    show_if: { readiness: prime_ready, wings_min: 1.03, ra_min: 0.95, risk_max: 0.06 }
    hide_if: { operator_focus: true, risk_over: 0.08 }

gate_12: [1,1,1,1,1,1,1,1,1,1,1,1]

human_compat: { smoothing_halflife_sec: 480, phi_echo: true }
quantum: { total_ms: 1200, power_cap_watts: 60 }
telemetry: { api: enabled, route: /api/hud/signals }
"@

# avatars.yml (tiers + groups: social & trading)
Set-Content -Encoding UTF8 "$cfg\avatars.yml" @"
version: 1
default_policy: { autonomy_max: AL-2, wing_visibility: inherit, hud: { show_phi_echo: true, show_gate_ring: true, show_audit_tray: true } }

# Core avatars
avatars:
  - { id: steward_prime, name: "Eidollona Prime", module: steward, tier: S, autonomy_max: AL-2,
      gates_focus: [consent,auditability,alignment,operator_override], wing_visibility: inherit,
      hud: { panels: [status, gate_ring, audit, ethos] }, voice: calm_conductor, style: throne_room,
      allowed_actions: [plan, explain, simulate], deny_actions: [live_trade, ledger_debit, raw_pii_ingest], audit_tags: [prime,overview] }

  - { id: serve_it, name: "Serve-it Avatar", module: serve_it, tier: B, autonomy_max: AL-2,
      gates_focus: [consent,privacy_pii,data_integrity,latency_compute], wing_visibility: inherit,
      hud: { panels: [quotes, jobs, comfort] }, voice: practical_guide, style: approachable,
      allowed_actions: [plan, quote_simulate, provider_match_simulate], deny_actions: [live_payment], audit_tags: [serveit] }

  - { id: fancomp, name: "FanComp Avatar", module: fancomp, tier: B, autonomy_max: AL-2,
      gates_focus: [consent,ext_policy,auditability,language_gate], wing_visibility: inherit,
      hud: { panels: [ip_vault, moneypool, policy] }, voice: curator, style: gallery,
      allowed_actions: [plan, vault_simulate, payout_simulate], deny_actions: [final_payout], audit_tags: [fancomp] }

  - { id: treasury_serplus, name: "Treasury Avatar", module: treasury_serplus, tier: A, autonomy_max: AL-2,
      gates_focus: [power_caps,auditability,data_integrity,counterparty_trust], wing_visibility: inherit,
      hud: { panels: [serplus_state, allowances, audit] }, voice: precise, style: ledger,
      allowed_actions: [credit_simulate, debit_simulate], deny_actions: [live_credit, live_debit], audit_tags: [treasury,serplus] }

  - { id: markets_trading, name: "Markets Avatar", module: markets_trading, tier: A, autonomy_max: AL-2,
      gates_focus: [tail_risk,latency_compute,alignment,auditability], wing_visibility: inherit,
      hud: { panels: [paper_plans, risk_envelopes, tails] }, voice: analyst, style: terminal,
      allowed_actions: [plan, gate_simulate, paper_execute, explain], deny_actions: [live_trade], audit_tags: [markets,paper] }

  - { id: security_emp, name: "Security/EMP Guard", module: security_emp, tier: A, autonomy_max: AL-2,
      gates_focus: [consent,privacy_pii,ext_policy,operator_override], wing_visibility: hide,
      hud: { panels: [alerts, posture, policies] }, voice: sentinel, style: minimal,
      allowed_actions: [scan, simulate_clamp], deny_actions: [disable_guardrails], audit_tags: [security] }

  - { id: sovereignty_legal, name: "Sovereignty Avatar", module: sovereignty_legal, tier: B, autonomy_max: AL-2,
      gates_focus: [alignment,ext_policy,auditability], wing_visibility: inherit,
      hud: { panels: [charters, policies] }, voice: formal, style: charter,
      allowed_actions: [explain_policy, plan_updates], deny_actions: [apply_binding_changes], audit_tags: [sovereignty] }

  - { id: compliance_audit, name: "Compliance Avatar", module: compliance_audit, tier: C, autonomy_max: AL-1,
      gates_focus: [auditability,data_integrity,language_gate], wing_visibility: hide,
      hud: { panels: [attestations, reasons, diffs] }, voice: auditor, style: ledger,
      allowed_actions: [attest_simulate, diff_reports], deny_actions: [alter_audit], audit_tags: [compliance] }

  - { id: learning_eval, name: "Learning Coach", module: learning_eval, tier: C, autonomy_max: AL-1,
      gates_focus: [alignment,data_integrity], wing_visibility: inherit,
      hud: { panels: [evals, metrics] }, voice: mentor, style: lab,
      allowed_actions: [run_evals, summarize], deny_actions: [change_policy], audit_tags: [learning] }

  - { id: quantum_bridge, name: "Quantum Research", module: quantum_bridge, tier: C, autonomy_max: AL-1,
      gates_focus: [latency_compute,tail_risk,alignment], wing_visibility: inherit,
      hud: { panels: [phase_map, budgets] }, voice: researcher, style: lab,
      allowed_actions: [phase_map, budget_simulate], deny_actions: [overclock], audit_tags: [quantum] }

  - { id: onboarding_identity, name: "Onboarding Avatar", module: onboarding_identity, tier: D, autonomy_max: AL-1,
      gates_focus: [consent,privacy_pii,alignment], wing_visibility: inherit,
      hud: { panels: [consent, identity] }, voice: friendly, style: neutral,
      allowed_actions: [consent_flow, explain], deny_actions: [raw_pii_ingest], audit_tags: [onboarding] }

  - { id: support_help, name: "Support Avatar", module: support_help, tier: D, autonomy_max: AL-1,
      gates_focus: [operator_override,auditability], wing_visibility: inherit,
      hud: { panels: [faq, status] }, voice: assistant, style: neutral,
      allowed_actions: [guide, open_docs], deny_actions: [system_change], audit_tags: [support] }

# Templates + groups to mint many avatars without duplication
templates:
  social_base: &social_base
    tier: C
    autonomy_max: AL-1
    gates_focus: [consent, privacy_pii, language_gate, auditability]
    wing_visibility: inherit
    hud: { panels: [content, schedule, policy] }
    voice: brand
    style: social
    allowed_actions: [plan, post_simulate, schedule_simulate, explain]
    deny_actions: [live_post]

  trading_base: &trading_base
    tier: A
    autonomy_max: AL-2
    gates_focus: [tail_risk, latency_compute, alignment, auditability]
    wing_visibility: inherit
    hud: { panels: [paper_plans, risk_envelopes, tails] }
    voice: analyst
    style: terminal
    allowed_actions: [plan, gate_simulate, paper_execute, explain]
    deny_actions: [live_trade]

groups:
  - template: social_base
    params:
      - { platform: x,         platform_title: "X" }
      - { platform: instagram, platform_title: "Instagram" }
      - { platform: tiktok,    platform_title: "TikTok" }
      - { platform: youtube,   platform_title: "YouTube" }
      - { platform: linkedin,  platform_title: "LinkedIn" }
      - { platform: reddit,    platform_title: "Reddit" }
      - { platform: discord,   platform_title: "Discord" }
    id: "social_{platform}"
    name: "Social — {platform_title}"
    module: "social_{platform}"
    audit_tags: ["social","{platform}"]

  - template: trading_base
    params:
      - { strategy: scalper,         strategy_title: "Scalper",         risk_profile: "tight",   leverage_cap: 1 }
      - { strategy: momentum,        strategy_title: "Momentum",        risk_profile: "medium",  leverage_cap: 1 }
      - { strategy: mean_reversion,  strategy_title: "Mean Reversion",  risk_profile: "medium",  leverage_cap: 1 }
      - { strategy: pairs,           strategy_title: "Pairs/Arb",       risk_profile: "tight",   leverage_cap: 1 }
      - { strategy: options_delta,   strategy_title: "Options Δ",       risk_profile: "tight",   leverage_cap: 1 }
      - { strategy: options_gamma,   strategy_title: "Options Γ",       risk_profile: "tight",   leverage_cap: 1 }
    id: "trading_{strategy}"
    name: "Markets — {strategy_title}"
    module: "trading_{strategy}"
    audit_tags: ["markets","paper","{strategy}"]
"@

# citadel.yml (rooms + court yard)
Set-Content -Encoding UTF8 "$cfg\citadel.yml" @"
version: 1
pinnacle: { id: throne_room, name: "Eidollona — Master Chamber", avatar_id: steward_prime, route: /citadel/throne,
            panels: [status, gate_ring, audit, ethos], privacy_level: high }
courtyard: { id: court_yard, name: "Citadel Court Yard", route: /citadel/court, quorum: 2, timeout_sec: 12,
            transcript_policy: { store: true, reveal_wings: auto } }
rooms:
  - { id: room_serve_it,    name: "Serve-it Guild Hall", avatar_id: serve_it, route: /citadel/serveit,
      panels: [quotes, jobs, comfort], privacy_level: medium, gate_focus: [consent,privacy_pii,latency_compute],
      bots: [provider_matcher, quote_orchestrator] }
  - { id: room_fancomp,     name: "FanComp Hall", avatar_id: fancomp, route: /citadel/fancomp,
      panels: [ip_vault, moneypool, policy], privacy_level: medium, gate_focus: [consent,ext_policy,language_gate],
      bots: [ip_vault_mgr, moneypool_planner] }
  - { id: room_treasury,    name: "Treasury — Serplus Ledger", avatar_id: treasury_serplus, route: /citadel/treasury,
      panels: [serplus_state, allowances, audit], privacy_level: high, gate_focus: [power_caps,auditability,data_integrity],
      bots: [credit_sim, debit_sim] }
  - { id: room_markets,     name: "Markets — Paper Trading", avatar_id: markets_trading, route: /citadel/markets,
      panels: [paper_plans, risk_envelopes, tails], privacy_level: high, gate_focus: [tail_risk,latency_compute,alignment],
      bots: [scalper, momentum, mean_reversion, pairs, options_delta, options_gamma] }
  - { id: room_security,    name: "Security / EMP Guard", avatar_id: security_emp, route: /citadel/security,
      panels: [alerts, posture, policies], privacy_level: high, gate_focus: [consent,privacy_pii,ext_policy],
      bots: [guard_sentinel, posture_checker] }
  - { id: room_sovereignty, name: "Sovereignty / Legal", avatar_id: sovereignty_legal, route: /citadel/sovereignty,
      panels: [charters, policies], privacy_level: high, gate_focus: [alignment,ext_policy,auditability], bots: [policy_explainer] }
  - { id: room_compliance,  name: "Compliance / Audit", avatar_id: compliance_audit, route: /citadel/compliance,
      panels: [attestations, reasons, diffs], privacy_level: high, gate_focus: [auditability,data_integrity,language_gate],
      bots: [attestations_bot] }
  - { id: room_learning,    name: "Learning / Eval Coach", avatar_id: learning_eval, route: /citadel/learning,
      panels: [evals, metrics], privacy_level: low, gate_focus: [alignment,data_integrity], bots: [eval_runner, metrics_aggregator] }
  - { id: room_quantum,     name: "Quantum Bridge / Research", avatar_id: quantum_bridge, route: /citadel/quantum,
      panels: [phase_map, budgets], privacy_level: medium, gate_focus: [latency_compute,tail_risk], bots: [phase_scheduler, budget_allocator] }
"@

# ================================= CORE CODE =================================
# 1) SE4.3 engine (Wings/RA)
Set-Content -Encoding UTF8 "$syms\se43_wings.py" @"
from math import sqrt
from dataclasses import dataclass
from typing import Any, Dict, List

PHI=(1+5**0.5)/2.0; LOTUS=sqrt(2.0); NORM=LOTUS/PHI
def clamp(x,lo=0.0,hi=1.0):
    try:x=float(x)
    except:x=0.0
    return max(lo,min(hi,x))

def weighted(values:List[float],weights:List[float])->float:
    if not values or not weights or len(values)!=len(weights):
        return 0.0
    acc=0.0; wsum=0.0
    for v,w in zip(values,weights):
        acc+=v*w; wsum+=abs(w)
    return acc/wsum if wsum else 0.0

@dataclass
class SE43Signals:
    wings: float
    ra: float
    omega: float
    phi_echo: float
    readiness: str

    def as_dict(self)->Dict[str,float]:
        return {
            "wings": round(self.wings,4),
            "ra": round(self.ra,4),
            "omega": round(self.omega,4),
            "phi_echo": round(self.phi_echo,4)
        }

class WingsAletheia:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg or {}
        self.gamma = clamp(self.cfg.get("alignment",{}).get("gamma",0.7))
        self.omega_cap = clamp(self.cfg.get("wings",{}).get("omega_max",0.06),0.0,0.2)
        self.phi_bias = clamp(self.cfg.get("human_compat",{}).get("phi_echo", True))

    def _vector_norm(self, values: List[float])->float:
        return sqrt(sum(max(0.0,v)**2 for v in values))/NORM

    def _phi_echo(self, wings: float, ra: float)->float:
        base = clamp((wings+ra)/2.0)
        if self.phi_bias:
            return clamp(base*PHI/NORM)
        return base

    def evaluate(self, sample: Dict[str, float])->SE43Signals:
        wings = self._vector_norm([
            clamp(sample.get("alignment",0.0)),
            clamp(sample.get("memory_integrity",0.0)),
            clamp(sample.get("consent_delta",0.0))
        ])
        ra = weighted([
            clamp(sample.get("risk_guard",0.0)),
            clamp(sample.get("audit_fidelity",0.0)),
            clamp(sample.get("sovereignty_ratio",0.0))
        ], [0.4,0.35,0.25])
        omega_raw = clamp(sample.get("omega", wings*self.gamma))
        omega = min(omega_raw,self.omega_cap)
        phi_echo = self._phi_echo(wings,ra)

        readiness = "prime_ready"
        if wings < 0.85 or ra < 0.82:
            readiness = "hold"
        if omega > self.omega_cap*0.95:
            readiness = "watch"

        return SE43Signals(wings=wings, ra=ra, omega=omega, phi_echo=phi_echo, readiness=readiness)
"@

# 2) Loader extension (prefer SE4.3, fallback to legacy SE4)
Set-Content -Encoding UTF8 "$syms\se_loader_ext.py" @"
from importlib import import_module
from typing import Any, Dict

DEFAULT_CFG_PATH = "config/se43.yml"

class SEEngineLoaderError(RuntimeError):
    pass

def _y(engine_name: str):
    return f"symbolic_core.{engine_name}"

def load_se_engine(cfg: Dict[str, Any] | None = None):
    cfg = cfg or {}
    preferred = cfg.get("engine", "se43_wings")
    tried = []

    for name in (preferred, "se43_wings", "se4_legacy"):
        if name in tried:
            continue
        tried.append(name)
        try:
            module = import_module(_y(name))
            engine_cls = getattr(module, "WingsAletheia", None) or getattr(module, "SymbolicEngine", None)
            if not engine_cls:
                continue
            return engine_cls(cfg)
        except ModuleNotFoundError:
            continue
        except Exception as exc:
            raise SEEngineLoaderError(f"Failed to load symbolic engine '{name}': {exc}") from exc

    raise SEEngineLoaderError(f"No symbolic engine found. Tried {tried}")
"@

# 3) ai_core/ai_brain.py (minimal orchestrator referencing SE4.3 + audit log)
Set-Content -Encoding UTF8 "$ai\ai_brain.py" @"
"""Minimal AI Brain orchestrator for SE4.3 Wings/Aletheia bring-up."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from symbolic_core.se_loader_ext import load_se_engine

AUDIT_PATH = Path("logs/audit.ndjson")
DEFAULT_CFG_PATH = Path("config/se43.yml")


def _load_cfg(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.loads(json.dumps(_yaml_like_to_dict(handle.read())))


def _yaml_like_to_dict(content: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    current: Dict[str, Any] = data
    stack: list[tuple[int, Dict[str, Any]]] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip("\"')")

        while stack and indent <= stack[-1][0]:
            stack.pop()
            current = stack[-1][1] if stack else data

        if value:
            current[key] = _parse_value(value)
        else:
            new_dict: Dict[str, Any] = {}
            current[key] = new_dict
            stack.append((indent, current))
            current = new_dict

    return data


def _parse_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("'\"")


def _log_audit(event: str, payload: Dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.utcnow().isoformat() + "Z", "event": event, "payload": payload}
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


@dataclass
class BrainSnapshot:
    wings: float = 0.0
    ra: float = 0.0
    omega: float = 0.0
    phi_echo: float = 0.0
    readiness: str = "unknown"
    raw: Dict[str, Any] = field(default_factory=dict)


class AIBrain:
    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        cfg = cfg or _load_cfg(DEFAULT_CFG_PATH)
        self.engine = load_se_engine(cfg)
        self.snapshot = BrainSnapshot()
        _log_audit("ai_brain_init", {"engine": type(self.engine).__name__, "cfg_wings": cfg.get("wings")})

    def ingest(self, sample: Dict[str, Any]) -> BrainSnapshot:
        signals = self.engine.evaluate(sample)
        self.snapshot = BrainSnapshot(
            wings=signals.wings,
            ra=signals.ra,
            omega=signals.omega,
            phi_echo=signals.phi_echo,
            readiness=signals.readiness,
            raw=signals.as_dict()
        )
        _log_audit("ai_brain_signals", self.snapshot.raw)
        return self.snapshot

    def hud_payload(self) -> Dict[str, Any]:
        return {
            "wings": self.snapshot.wings,
            "ra": self.snapshot.ra,
            "omega": self.snapshot.omega,
            "phi_echo": self.snapshot.phi_echo,
            "readiness": self.snapshot.readiness
        }
"@

# 4) quantum probabilistic interface (minimal stub for bring-up)
Set-Content -Encoding UTF8 "$qpir\__init__.py" @"
"""Quantum Probabilistic Information Rendering (QPIR) bring-up stubs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from ai_core.ai_brain import BrainSnapshot

@dataclass
class QPIRSnapshot:
    phase_map: Dict[str, float]
    budgets: Dict[str, float]
    phi_echo: float


def render(snapshot: BrainSnapshot, phases: Iterable[str] = ("alpha", "beta", "gamma")) -> QPIRSnapshot:
    base = snapshot.phi_echo
    phase_map = {phase: round(base * (idx + 1) * 0.1, 4) for idx, phase in enumerate(phases)}
    budgets = {"quantum_ms": round(snapshot.omega * 1000, 2), "power_watts": 60.0}
    return QPIRSnapshot(phase_map=phase_map, budgets=budgets, phi_echo=snapshot.phi_echo)
"@

# 5) probabilistic quantum rendering support
Set-Content -Encoding UTF8 "$pqr\__init__.py" @"
"""Probabilistic quantum rendering bring-up surfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ai_core.ai_brain import BrainSnapshot
from quantum_probabilistic_information_rendering_system import render

@dataclass
class RenderingEnvelope:
    readiness: str
    wings_signal: float
    phi_echo: float
    phase_map: Dict[str, float]


def make_envelope(snapshot: BrainSnapshot) -> RenderingEnvelope:
    qpir_snapshot = render(snapshot)
    return RenderingEnvelope(
        readiness=snapshot.readiness,
        wings_signal=snapshot.wings,
        phi_echo=qpir_snapshot.phi_echo,
        phase_map=qpir_snapshot.phase_map
    )
"@

# 6) Web interface HUD endpoint (fastapi)
Set-Content -Encoding UTF8 "$websrv\hud.py" @"
"""HUD API for SE4.3 bring-up."""
from __future__ import annotations

from fastapi import APIRouter

from ai_core.ai_brain import AIBrain
from probabilistic_quantum_rendering import make_envelope

router = APIRouter(prefix="/api/hud", tags=["hud"])
_brain = AIBrain()


@router.get("/signals")
def get_signals():
    envelope = make_envelope(_brain.snapshot)
    payload = _brain.hud_payload()
    payload.update({"phase_map": envelope.phase_map, "phi_echo": envelope.phi_echo})
    return payload
"@

# 7) Metrics roll-up (audit ndjson to simple summary)
Set-Content -Encoding UTF8 "$metric\ndjson_rollup.py" @"
"""Derive minimal metrics from audit.ndjson."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict

AUDIT_PATH = Path("logs/audit.ndjson")


def rollup() -> Dict[str, int]:
    counter = Counter()
    if not AUDIT_PATH.exists():
        return {}
    with AUDIT_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
                counter[payload.get("event", "unknown")] += 1
            except json.JSONDecodeError:
                continue
    return dict(counter)


if __name__ == "__main__":
    print(json.dumps(rollup(), indent=2))
"@

# 8) QRE stubs (placeholder reinforcement engine)
Set-Content -Encoding UTF8 "$qre\__init__.py" @"
"""Quantum Reinforcement Engine placeholder"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ai_core.ai_brain import BrainSnapshot


@dataclass
class QREReport:
    decision: str
    risk_score: float
    notes: Dict[str, str]


def evaluate(snapshot: BrainSnapshot) -> QREReport:
    if snapshot.wings < 0.9:
        decision = "deny"
        risk_score = 0.8
    elif snapshot.readiness != "prime_ready":
        decision = "hold"
        risk_score = 0.4
    else:
        decision = "allow"
        risk_score = 0.1
    return QREReport(
        decision=decision,
        risk_score=risk_score,
        notes={"readiness": snapshot.readiness}
    )
"@

# 9) Web planning backend main adjustments (ensure router mounted)
Set-Content -Encoding UTF8 "$websrv\__init__.py" @"
from fastapi import FastAPI

from . import hud

app = FastAPI()
app.include_router(hud.router)
"@

# 10) Minimal web interface entry (uvicorn app)
Set-Content -Encoding UTF8 "$web\__init__.py" ""
Set-Content -Encoding UTF8 "$web\main.py" @"
from fastapi import FastAPI

from web_interface.server import app as server_app

app = FastAPI()
app.mount("/api", server_app)
"@

# 11) Serve script for local dev
Set-Content -Encoding UTF8 "$scripts\serve_backend.py" @"
from uvicorn import run

from web_interface.server import app

if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8000)
"@

# 12) README/OPERATOR entry
Set-Content -Encoding UTF8 "$root\OPERATOR.md" @"
# EidollonaONE SAFE Bring-up (SE4.3) — Wings/Aletheia

1. Run `pwsh scripts/eidolon_bringup.ps1` once to sync configs + modules.
2. Launch backend with `python scripts/serve_backend.py` (requires FastAPI + uvicorn).
3. HUD endpoint available at `http://127.0.0.1:8000/api/hud/signals`.
4. Audit log stored in `logs/audit.ndjson`; rollup via `python scripts/metrics/ndjson_rollup.py`.
5. AI Brain minimal ingest sample:
   ```python
   from ai_core.ai_brain import AIBrain
   brain = AIBrain()
   sample = {"alignment":0.92,"memory_integrity":0.88,"consent_delta":0.9,
             "risk_guard":0.87,"audit_fidelity":0.91,"sovereignty_ratio":0.9,
             "omega":0.04}
   snapshot = brain.ingest(sample)
   ```
6. Avatar/citadel configs live under `config/`.
"@

Write-Host "EIDOLONALPHA+ bring-up complete."
