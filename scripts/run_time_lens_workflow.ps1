param(
  [string]$Label = 'policy_v3_start',
  [string]$Lens  = 'loop'
)

if (-not $env:EIDOLLONA_AUDIT) {
  $env:EIDOLLONA_AUDIT = 'logs\audit.ndjson'
}

python scripts/epoch_marker.py $Label | Write-Host

if (Test-Path 'scripts\run_cycle.py') {
  python scripts/run_cycle.py | Write-Host
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$replayOut = "public/reports/replay_${Label}_${timestamp}.json"
$replayJson = python scripts/replay_time_lens.py $Lens $Label
$replayJson | Out-File -Encoding utf8 $replayOut
Write-Host "Saved replay KPIs -> $replayOut"

$entropyJson = python scripts/entropy_monitor.py
try {
  [void]($entropyJson | ConvertFrom-Json)
  $entropyOut = "public/reports/entropy_${timestamp}.json"
  $entropyJson | Out-File -Encoding utf8 $entropyOut
  Write-Host "Saved entropy snapshot -> $entropyOut"
} catch {
}

if (Test-Path 'scripts\audit_anchor.py') {
  python scripts/audit_anchor.py | Write-Host
}

Write-Host "`n=== KPI CHECK ==="
if (Test-Path 'scripts\check_kpis.py') {
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
