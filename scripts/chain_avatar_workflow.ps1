Param(
  [string]$Repo = (Get-Location).Path,
  [int]$Port = 8077
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

try {
  $repoPath = (Resolve-Path -LiteralPath $Repo).Path
} catch {
  Write-Host "Repository not found: $Repo" -ForegroundColor Red
  exit 1
}

Set-Location -LiteralPath $repoPath
Write-Host "=== Avatar Chain: Install -> Check -> Run ==="

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)][string]$Command,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )
  pwsh -NoProfile -ExecutionPolicy Bypass -File $Command @Arguments
  return $LASTEXITCODE
}

# Step 1: Install assets
$installArgs = @(
  '-Repo', $repoPath,
  '-Model', 'C:\Users\weare\Downloads\eidollona(5).glb',
  '-Portrait', 'C:\Users\weare\Downloads\eidollona_avatar.png',
  '-Force'
)
$exitCode = Invoke-Step -Command 'scripts/install_avatar_assets.ps1' -Arguments $installArgs
if ($exitCode -ne 0) {
  Write-Host 'Install FAILED' -ForegroundColor Red
  exit 1
}

# Step 2: Run quick check
$exitCode = Invoke-Step -Command 'scripts/avatar_quick_check.ps1' -Arguments @()
if ($exitCode -ne 0) {
  Write-Host 'Readiness FAIL: not launching preview.' -ForegroundColor Red
  exit 1
}

# Step 3: Launch preview
$previewArgs = @(
  '-Repo', $repoPath,
  '-Port', $Port
)
$exitCode = Invoke-Step -Command 'scripts/run_avatar_preview.ps1' -Arguments $previewArgs
if ($exitCode -ne 0) {
  Write-Host 'Preview launch FAILED' -ForegroundColor Red
  exit 1
}

Write-Host ("Launched preview -> http://127.0.0.1:{0}/webview/avatar_popup.html" -f $Port) -ForegroundColor Green
exit 0
