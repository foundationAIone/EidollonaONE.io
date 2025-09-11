<#
  Repo Hygiene Script (Phase 1 SE41 Readiness)
  - Idempotent cleanup of large installers, logs, __pycache__, and .pyc
  - CheckOnly mode: emits findings & non‑zero exit if issues
  - Analyze mode: runs PSScriptAnalyzer (if available) for stylistic/lint checks
  Approved verb helper: Initialize-Directory (replaces legacy Ensure-Dir)
#>
Param(
  [switch]$CheckOnly,
  [switch]$Analyze
)

$ErrorActionPreference = 'Stop'

function Initialize-Directory {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$Path
  )
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
  }
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$ToolsCache = Join-Path $Root 'tools/cache'
$LogsDir = Join-Path $Root 'logs'

# Findings accumulator (issues discovered when -CheckOnly is used)
$Findings = @()

Initialize-Directory -Path $ToolsCache
Initialize-Directory -Path $LogsDir

# Build tracked files set for CheckOnly comparisons
$TrackedSet = @{}
if ($CheckOnly) {
  try {
    Push-Location $Root
    $tracked = git ls-files -z 2>$null
    Pop-Location
    if ($tracked) {
      $rel = $tracked -split "`0" | Where-Object { $_ -ne '' }
      foreach ($r in $rel) {
        $Full = Join-Path $Root $r
        $TrackedSet[$Full.ToLowerInvariant()] = $true
      }
    }
  } catch { }
}
## (Removed duplicate Initialize-Directory definition)

# 1) Quarantine large binaries (installers)
$Installers = @('python-*.exe','*.zip','*.gz')
$InstallerHits = @()
foreach ($pat in $Installers) {
  # Collect matching files by wildcard name
  $InstallerHits += Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -like $pat }
}
# De-duplicate
$InstallerHits = $InstallerHits | Sort-Object FullName -Unique

foreach ($f in $InstallerHits) {
  # Skip already quarantined files
  if ($f.FullName -like "$ToolsCache*") { continue }
  if ($CheckOnly -and $TrackedSet.Count -gt 0) {
    if (-not $TrackedSet.ContainsKey($f.FullName.ToLowerInvariant())) { continue }
  }
  $dest = Join-Path $ToolsCache $f.Name
  if ($CheckOnly) {
    Write-Host "CHECK: installer outside cache -> $($f.FullName)"; $Findings += $f
  } else {
    if ($f.DirectoryName -ne $ToolsCache) {
      try {
        Move-Item -Force -LiteralPath $f.FullName -Destination $dest
        Write-Host "Moved installer -> $dest"
      } catch {
        Write-Warning "Failed moving installer: $($f.FullName) -> $dest : $($_.Exception.Message)"
      }
    }
  }
}

# 2) Logs: move to logs/ with daily rotation, remove 0-byte and >30 days
$Now = Get-Date
$Cutoff = $Now.AddDays(-30)
$LogFiles = Get-ChildItem -Path $Root -Recurse -File -Include *.log -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "*.git*" }
foreach ($lf in $LogFiles) {
  if ($CheckOnly -and $TrackedSet.Count -gt 0) {
    if (-not $TrackedSet.ContainsKey($lf.FullName.ToLowerInvariant())) { continue }
  }
  if ($lf.Length -eq 0) {
  if ($CheckOnly) { Write-Host "CHECK: 0-byte log -> $($lf.FullName)"; $Findings += $lf } else { Remove-Item -Force -LiteralPath $lf.FullName }
    continue
  }
  if ($lf.LastWriteTime -lt $Cutoff) {
  if ($CheckOnly) { Write-Host "CHECK: stale log (>30d) -> $($lf.FullName)"; $Findings += $lf } else { Remove-Item -Force -LiteralPath $lf.FullName }
    continue
  }
  # move active logs under logs/ preserving name
  $day = $lf.LastWriteTime.ToString('yyyy-MM-dd')
  $dayDir = Join-Path $LogsDir $day
  Initialize-Directory -Path $dayDir
  $dest = Join-Path $dayDir $lf.Name
  if ($CheckOnly) {
  if ($lf.DirectoryName -ne $dayDir) { Write-Host "CHECK: log not centralized -> $($lf.FullName)"; $Findings += $lf }
  } else {
    if ($lf.FullName -ne $dest) {
      try { Move-Item -Force -LiteralPath $lf.FullName -Destination $dest } catch { }
    }
  }
}

# 3) Purge __pycache__ and *.pyc (exclude known envs)
$EnvExcludes = @('eidollona_env','quantum_env','venv','env','.venv','venv_management\envs')
$PyCaches = Get-ChildItem -Path $Root -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue | Where-Object {
  $p = $_.FullName.ToLowerInvariant(); -not ($EnvExcludes | ForEach-Object { $p -like "*$_*" })
}
foreach ($d in $PyCaches) {
  if ($CheckOnly) {
    if ($TrackedSet.Count -eq 0 -or $TrackedSet.ContainsKey($d.FullName.ToLowerInvariant())) {
      Write-Host "CHECK: __pycache__ present -> $($d.FullName)"; $Findings += $d
    }
  } else { Remove-Item -Recurse -Force -LiteralPath $d.FullName }
}
$AllDirs = Get-ChildItem -Path $Root -Directory -Recurse -ErrorAction SilentlyContinue
$AllowedDirs = $AllDirs | Where-Object { $p = $_.FullName.ToLowerInvariant(); -not ($EnvExcludes | ForEach-Object { $p -like "*$_*" }) }
$PycFiles = @()
foreach ($dir in $AllowedDirs) {
  try {
    $PycFiles += Get-ChildItem -Path $dir.FullName -File -Filter *.pyc -ErrorAction SilentlyContinue
  } catch { }
}
foreach ($pf in $PycFiles) {
  if ($CheckOnly) {
    if ($TrackedSet.Count -eq 0 -or $TrackedSet.ContainsKey($pf.FullName.ToLowerInvariant())) {
      Write-Host "CHECK: stray .pyc -> $($pf.FullName)"; $Findings += $pf
    }
  } else {
    try { Remove-Item -Force -LiteralPath $pf.FullName } catch { }
  }
}

if ($Analyze) {
  Write-Host "Running PSScriptAnalyzer (if installed)..."
  try {
    if (Get-Module -ListAvailable -Name PSScriptAnalyzer) {
      Import-Module PSScriptAnalyzer -ErrorAction Stop
      $analysis = Invoke-ScriptAnalyzer -Path $MyInvocation.MyCommand.Path -Severity Warning,Error -ErrorAction Stop
      if ($analysis) {
        Write-Warning "Analyzer findings detected:"
        $analysis | ForEach-Object { Write-Host ("[{0}] {1}: {2}" -f $_.RuleSeverity,$_.RuleName,$_.Message) }
        # Distinct exit code for analyzer failures (2)
        if (-not $CheckOnly) { exit 2 }
      } else {
        Write-Host "Analyzer clean."
      }
    } else {
      Write-Host "PSScriptAnalyzer not installed; skipping."
    }
  } catch {
    Write-Warning "Analyzer execution failed: $($_.Exception.Message)"
  }
}

# 4) Summary and exit code
Write-Host "Repo hygiene completed. CheckOnly=$CheckOnly Analyze=$Analyze"
if ($CheckOnly) {
  if ($Findings.Count -gt 0) {
    Write-Error "Hygiene check found $($Findings.Count) issues."
    exit 1
  } else {
    Write-Host "No hygiene issues detected."
    exit 0
  }
}

