# RUNBOOK — Time-Lens Workflow (line · loop · now)

## Go/No-Go thresholds (default in `config/kpi_thresholds.yml`)

- explain_rate ≥ 0.95 (target 1.0)
- near_threshold_hold_rate ≤ 0.30
- flap_rate ≤ 0.25
- entropy_bits: WARN < 1.10, CRIT < 0.90 (investigate sustained drops)

## Daily Ops

1. Tag the beginning of any meaningful change: `python scripts/epoch_marker.py "policy_vX_start"`
2. Run normal paper cycle(s)
3. Replay KPIs from the marker: `python scripts/replay_time_lens.py loop policy_vX_start`
4. Check entropy: `python scripts/entropy_monitor.py`
5. Anchor audit (if enabled): `python scripts/audit_anchor.py`

## One-shot end-to-end

`pwsh -File scripts/run_time_lens_workflow.ps1 -Label "policy_vX_start" -Lens loop`

## CI smoke (optional)

`pwsh -File scripts/ci_time_lens_smoke.ps1 -Label ci_smoke`

## HUD

- `GET /api/hud/signals?time_lens={now|line|loop}`
  - **now**: emphasize readiness/impetus/risk/RA/Wings
  - **loop**: 12-phase ring + daily KPIs
  - **line**: 7-day trends and pre/post-epoch deltas
