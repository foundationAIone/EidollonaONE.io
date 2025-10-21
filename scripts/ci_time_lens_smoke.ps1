param([string]$Label='ci_smoke')

if (-not $env:EIDOLLONA_AUDIT) {
  $env:EIDOLLONA_AUDIT = 'logs\audit.ndjson'
}

python scripts/epoch_marker.py $Label

if (Test-Path 'scripts\run_cycle.py') {
  python scripts/run_cycle.py
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$replayOut = "public/reports/replay_${Label}_${timestamp}.json"
python scripts/replay_time_lens.py now $Label | Out-File -Encoding utf8 $replayOut

python scripts/check_kpis.py $replayOut
if ($LASTEXITCODE -ne 0) {
  Write-Host "KPI check: FAIL" -ForegroundColor Red
  exit 1
}

if (Test-Path 'scripts\audit_anchor.py') {
  python scripts/audit_anchor.py
}

Write-Host "CI Time-Lens smoke: PASS" -ForegroundColor Green
