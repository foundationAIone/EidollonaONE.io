# ====================== EidolonAlpha+ — Time-Lens Next Step (End-to-End + KPIs + Runbook) ======================
$ErrorActionPreference = 'Stop'
$root   = Get-Location
$cfg    = Join-Path $root 'config'
$logs   = Join-Path $root 'logs'
$pub    = Join-Path $root 'public\reports'
$scr    = Join-Path $root 'scripts'
$docs   = Join-Path $root 'docs'
$anc    = Join-Path $root 'anchors'
New-Item -Force -ItemType Directory $cfg,$logs,$pub,$scr,$docs,$anc | Out-Null

# ---------- 1) KPI thresholds (tunable) ----------
Set-Content -Encoding UTF8 (Join-Path $cfg 'kpi_thresholds.yml') @"
version: 1
# Explainability fraction of decisions with reasons (target 1.0; min 0.95)
explain_rate_min: 0.95
# Near-threshold HOLD rate should be below this fraction (0.45<=impetus<0.55 & HOLD)
near_threshold_hold_rate_max: 0.30
# ALLOW<->HOLD flipping rate should be below this fraction
flap_rate_max: 0.25
# Entropy (bits) over last N decisions; warn/crit bands
entropy_warn_min: 1.10
entropy_crit_min: 0.90
"@

# ---------- 2) KPI checker (reads replay JSON or computes on the fly) ----------
Set-Content -Encoding UTF8 (Join-Path $scr 'check_kpis.py') @"
import json
import subprocess
import sys

import yaml

THRESH = yaml.safe_load(open('config/kpi_thresholds.yml', 'r', encoding='utf-8'))

def load_json(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)

def run_replay(lens: str, label: str) -> dict:
    cmd = [sys.executable, 'scripts/replay_time_lens.py', lens, label]
    output = subprocess.check_output(cmd, text=True, encoding='utf-8')
    return json.loads(output)

def run_entropy() -> dict:
    cmd = [sys.executable, 'scripts/entropy_monitor.py']
    output = subprocess.check_output(cmd, text=True, encoding='utf-8', stderr=subprocess.STDOUT)
    try:
        return json.loads(output)
    except Exception:
        return {'ok': True}

def main() -> None:
    args = sys.argv[1:]
    if len(args) >= 1 and args[0].endswith('.json'):
        replay = load_json(args[0])
        lens = replay.get('lens', 'now')
        label = replay.get('label')
    else:
        lens = args[0] if len(args) >= 1 else 'now'
        label = args[1] if len(args) >= 2 else None
        replay = run_replay(lens, label or '')

    if not replay.get('ok'):
        print({'ok': False, 'err': 'replay_failed', 'replay': replay})
        sys.exit(2)

    explain_rate = float(replay.get('explain_rate', 0.0))
    near_hold = float(replay.get('near_threshold_hold_rate', 1.0))
    flap_rate = float(replay.get('flap_rate', 1.0))

    entropy = run_entropy()
    entropy_bits = float(entropy.get('entropy_bits', 1.5)) if entropy.get('ok') else 1.5

    warnings: list[str] = []
    critical: list[str] = []

    if explain_rate < THRESH['explain_rate_min']:
        critical.append(f"explain_rate<{THRESH['explain_rate_min']} ({explain_rate:.3f})")
    if near_hold > THRESH['near_threshold_hold_rate_max']:
        warnings.append(
            f"near_threshold_hold_rate>{THRESH['near_threshold_hold_rate_max']} ({near_hold:.3f})"
        )
    if flap_rate > THRESH['flap_rate_max']:
        warnings.append(f"flap_rate>{THRESH['flap_rate_max']} ({flap_rate:.3f})")
    if entropy_bits < THRESH['entropy_crit_min']:
        critical.append(f"entropy_bits<{THRESH['entropy_crit_min']} ({entropy_bits:.3f})")
    elif entropy_bits < THRESH['entropy_warn_min']:
        warnings.append(f"entropy_bits<{THRESH['entropy_warn_min']} ({entropy_bits:.3f})")

    result = {
        'ok': len(critical) == 0,
        'warn': warnings,
        'crit': critical,
        'replay': {
            'lens': lens,
            'label': label,
            'explain_rate': explain_rate,
            'near_threshold_hold_rate': near_hold,
            'flap_rate': flap_rate,
        },
        'entropy_bits': entropy_bits,
    }

    print(json.dumps(result, indent=2))
    sys.exit(1 if critical else 0)


if __name__ == '__main__':
    main()
"@

# ---------- 3) End-to-end runner (epoch -> cycle -> replay -> entropy -> anchor -> check) ----------
Set-Content -Encoding UTF8 (Join-Path $scr 'run_time_lens_workflow.ps1') @"
param(
  [string]$Label = 'policy_v3_start',
  [string]$Lens  = 'loop'  # now | line | loop
)
# Ensure audit var
if (-not $env:EIDOLLONA_AUDIT) { $env:EIDOLLONA_AUDIT = 'logs\audit.ndjson' }
# Mark epoch
python scripts/epoch_marker.py $Label | Write-Host
# Run one paper cycle (adjust to your normal cycle runner if different)
if (Test-Path 'scripts\run_cycle.py') {
  python scripts/run_cycle.py | Write-Host
}
# Replay from epoch
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$replayOut = "public/reports/replay_$($Label)_$($ts).json"
$replayJson = python scripts/replay_time_lens.py $Lens $Label
$replayJson | Out-File -Encoding utf8 $replayOut
Write-Host "Saved replay KPIs -> $replayOut"
# Entropy monitor (also appends to audit)
$entropyJson = python scripts/entropy_monitor.py
# Save entropy snapshot if JSON-like
try {
  [void]($entropyJson | ConvertFrom-Json)
  $entropyOut = "public/reports/entropy_$($ts).json"
  $entropyJson | Out-File -Encoding utf8 $entropyOut
  Write-Host "Saved entropy snapshot -> $entropyOut"
} catch { }
# Anchor today's audit (if anchor script exists)
if (Test-Path 'scripts/audit_anchor.py') {
  python scripts/audit_anchor.py | Write-Host
}
# KPI gate check (CI-friendly)
Write-Host "`n=== KPI CHECK ==="
if (Test-Path 'scripts/check_kpis.py') {
  python scripts/check_kpis.py $replayOut
  if ($LASTEXITCODE -ne 0) {
    Write-Host "KPI check: FAIL" -ForegroundColor Red
    exit 1
  } else {
    Write-Host "KPI check: PASS" -ForegroundColor Green
  }
} else {
  Write-Host "checker not found; skipping"
}
"@

# ---------- 4) CI smoke wrapper (optional) ----------
Set-Content -Encoding UTF8 (Join-Path $scr 'ci_time_lens_smoke.ps1') @"
# Minimal CI smoke: epoch -> cycle -> replay(now) -> check -> anchor
param([string]$Label='ci_smoke')
if (-not $env:EIDOLLONA_AUDIT) { $env:EIDOLLONA_AUDIT = 'logs\audit.ndjson' }
python scripts/epoch_marker.py $Label
if (Test-Path 'scripts/run_cycle.py') { python scripts/run_cycle.py }
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$replayOut = "public/reports/replay_$($Label)_$($ts).json"
python scripts/replay_time_lens.py now $Label | Out-File -Encoding utf8 $replayOut
python scripts/check_kpis.py $replayOut
if ($LASTEXITCODE -ne 0) { Write-Host "KPI check: FAIL" -ForegroundColor Red; exit 1 }
if (Test-Path 'scripts/audit_anchor.py') { python scripts/audit_anchor.py }
Write-Host "CI Time-Lens smoke: PASS" -ForegroundColor Green
"@

# ---------- 5) Runbook for operators ----------
Set-Content -Encoding UTF8 (Join-Path $docs 'RUNBOOK_TIME_LENS.md') @"
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
"@

# ---------- 6) Print next-step instructions ----------
Write-Host "`n=== Next Step: Execute the Time-Lens workflow ==="
Write-Host "1) Tag an epoch and run the end-to-end:"
Write-Host "   pwsh -File scripts/run_time_lens_workflow.ps1 -Label 'policy_v3_start' -Lens loop"
Write-Host "2) Inspect reports:"
Write-Host "   public/reports/replay_policy_v3_start_<timestamp>.json"
Write-Host "   public/reports/entropy_<timestamp>.json"
Write-Host "3) (Optional) CI smoke:"
Write-Host "   pwsh -File scripts/ci_time_lens_smoke.ps1 -Label ci_smoke"
Write-Host "`nWorkspace-only: no OS scheduling changes applied."
