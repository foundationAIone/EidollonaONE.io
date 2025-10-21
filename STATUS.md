# Project Readiness Overview

This page tracks the current live readiness posture across the major EidollonaONE subsystems. Status values reflect the latest operator verification and nightly checks.

| Module | State | Key Checks | Notes |
| --- | --- | --- | --- |
| web_interface HUD & tools | GREEN | VS Code task **Start HUD (7860)** → manual smoke | UI flows stable but Capstone rollout pending full rehearsal. · [evidence](logs/promo/web_interface.json) |
| web_planning backend | YELLOW | **Smoke: Planning** task | Planner APIs healthy; automation pass required before GREEN. |
| bridge / AlphaTap API | GREEN | GET `http://127.0.0.1:8802/healthz?token=dev-token` | Core endpoints pass smoke; enabling OpenTelemetry in progress. · [evidence](logs/promo/bridge.json) |
| Avatar assets & docs | YELLOW | Manual VRM load in Throne Room; **pytest: avatar reactive layer** | Multi-avatar orchestrator, FanComp & Serve-it docs live; run Throne Room VRM smoke before promote. |
| ai_core orchestration | YELLOW | `scripts/ai_brain_reasoning.py` (manual run) | Needs nightly automation; logic cold start OK. |
| ai_learning evaluation | GREEN | **AI Learning: Eval** task | Deterministic harness + CI precheck in place. |
| Sovereignty stack | YELLOW | **pytest: sovereignty preferences** | Charter endpoints pass; policy sync doc refresh pending. |
| Security / EMP / EMP Guard | YELLOW | **Tests: EMP + Security** task | Smoke coverage passing; broader audit queued. |
| Trading engine & options | YELLOW | **Tests: Fast Suite (ad-hoc)** or focused trading tasks | Paper trading verified; live gating deferred. |
| Symbolic core / IO / alignment | YELLOW | `tools/enforce_symbolic_v41.py` | Alignment checks green; symbol-graph diffs still under review. |

## Module readiness snapshot — completed checks

- **web_interface HUD & tools** — GREEN  
  Completed: VS Code task **Start HUD (7860)** executed with manual smoke validation; UI flows confirmed stable. Pending: Capstone rollout rehearsal.
- **web_planning backend** — YELLOW  
  Completed: **Smoke: Planning** task run verifies planner APIs; automation pass still required before promotion.
- **bridge / AlphaTap API** — GREEN  
  Completed: `GET http://127.0.0.1:8802/healthz?token=dev-token` returns healthy; OpenTelemetry enablement remains in progress.
- **Avatar assets & docs** — YELLOW  
  Completed: FanComp & Serve-it documentation aligned with multi-avatar orchestrator; Throne Room VRM smoke pending for GREEN.
- **ai_core orchestration** — YELLOW  
  Completed: Manual execution of `scripts/ai_brain_reasoning.py` validates cold start; nightly automation still outstanding.
- **ai_learning evaluation** — GREEN  
  Completed: **AI Learning: Eval** task runs deterministic harness and CI precheck.
- **Sovereignty stack** — YELLOW  
  Completed: **pytest: sovereignty preferences** passes for charter endpoints; policy sync documentation refresh pending.
- **Security / EMP / EMP Guard** — YELLOW  
  Completed: **Tests: EMP + Security** smoke suite succeeds; broader audit queued before GREEN.
- **Trading engine & options** — YELLOW  
  Completed: Paper trading flow validated via focused trading tasks; live gating deferred.
- **Symbolic core / IO / alignment** — YELLOW  
  Completed: `tools/enforce_symbolic_v41.py` alignment checks pass; symbol-graph diff review in progress.

## Status definitions

- **GREEN** — Deployable. Smoke tests and readiness probe pass with no actionable warnings.
- **YELLOW** — Deployable with caution. Known follow-ups exist; operator acknowledgement required before Engage.
- **ORANGE** — Hold. Significant gaps or outstanding migrations; additional remediation needed before Arm/Engage.

Promotion checklist to move a component to GREEN:

1. Latest smoke task(s) in this table pass in CI and on operator workstation.
2. Readiness probe (`Readiness: Probe`) reports PASS for the module.
3. STATUS.md updated with evidence link or log artifact in `logs/`.
4. Operator dry-run recorded in audit NDJSON within the last 24h.

## Useful tasks & references

- Readiness probe: VS Code task **Readiness: Probe** or `pwsh -File .\scripts\preflight.ps1`.
- Focused GREEN sweep: task **Tests: GREEN Sweep**.
- Nightly follow-ups: **Nightly: SVI QA**, **Nightly: PQRE Sanity**, **Nightly: Cluster Null**.
- Capstone dashboard: `web_interface/static/webview/capstone.html` (token required).
