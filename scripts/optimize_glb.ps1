Param(
  [string]$Repo = (Get-Location).Path,
  [string]$Src = "web_interface\static\models\steward_prime.glb",
  [string]$Out = "web_interface\static\models\steward_prime_opt.glb"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$esc = [char]27

function Format-Status {
  param(
    [Parameter(Mandatory = $true)][ValidateSet('PASS','WARN','FAIL')]
    [string]$Status
  )
  switch ($Status) {
    'PASS' { return "${esc}[32mPASS${esc}[0m" }
    'WARN' { return "${esc}[33mWARN${esc}[0m" }
    'FAIL' { return "${esc}[31mFAIL${esc}[0m" }
  }
}

$rows = @()

function Add-Row {
  param(
    [Parameter(Mandatory = $true)][string]$Code,
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][ValidateSet('PASS','WARN','FAIL')]
    [string]$Status,
    [Parameter(Mandatory = $true)][string]$Detail,
    [string]$Hint
  )
  $script:rows += [pscustomobject]@{
    Code = $Code
    Label = $Label
    Status = $Status
    Detail = $Detail
    Hint = $Hint
  }
}

function Resolve-PathFlexible {
  param(
    [Parameter(Mandatory = $true)][string]$Base,
    [Parameter(Mandatory = $true)][string]$Path,
    [switch]$AllowMissing
  )
  if ([System.IO.Path]::IsPathRooted($Path)) {
    if ($AllowMissing) {
      return (Join-Path ([System.IO.Path]::GetDirectoryName($Path)) ([System.IO.Path]::GetFileName($Path)))
    }
    return (Resolve-Path -LiteralPath $Path).Path
  }
  $combined = Join-Path $Base $Path
  if ($AllowMissing) {
    return $combined
  }
  return (Resolve-Path -LiteralPath $combined).Path
}

Write-Host "${esc}[36m=== GLB Optimizer ===${esc}[0m"

$repoPath = $null
try {
  $repoPath = (Resolve-Path -LiteralPath $Repo).Path
  Add-Row -Code 'A' -Label 'repo' -Status 'PASS' -Detail "Using $repoPath"
} catch {
  Add-Row -Code 'A' -Label 'repo' -Status 'FAIL' -Detail "Repo not found: $Repo" -Hint 'Verify the workspaceFolder path.'
}

$srcPath = $null
$outPath = $null
if ($repoPath) {
  try {
    $srcPath = Resolve-PathFlexible -Base $repoPath -Path $Src
    Add-Row -Code 'B1' -Label 'source' -Status 'PASS' -Detail ([System.IO.Path]::GetRelativePath($repoPath, $srcPath))
  } catch {
    Add-Row -Code 'B1' -Label 'source' -Status 'FAIL' -Detail ("Source not found: {0}" -f $Src) -Hint 'Ensure the GLB exists before optimizing.'
  }

  $outPath = Resolve-PathFlexible -Base $repoPath -Path $Out -AllowMissing
  $outDir = Split-Path -Parent $outPath
  if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  }
  Add-Row -Code 'B2' -Label 'output' -Status 'PASS' -Detail ([System.IO.Path]::GetRelativePath($repoPath, $outPath))
}

$toolUsed = $null
$optimized = $false
$hintMissing = 'Install gltf-transform (npm install -g @gltf-transform/cli) or gltfpack (https://github.com/zeux/meshoptimizer).' 

if ($srcPath) {
  $npx = Get-Command npx -ErrorAction SilentlyContinue
  $gltfpack = Get-Command gltfpack -ErrorAction SilentlyContinue
  if ($npx) {
    Add-Row -Code 'C' -Label 'tool' -Status 'PASS' -Detail 'Using npx @gltf-transform/cli.'
    $temp1 = [System.IO.Path]::GetTempFileName()
    $temp2 = [System.IO.Path]::GetTempFileName()
    try {
      & $npx.Source -y @gltf-transform/cli weld $srcPath $temp1 *> $null
      & $npx.Source -y @gltf-transform/cli prune $temp1 $temp2 *> $null
      & $npx.Source -y @gltf-transform/cli quantize $temp2 $outPath *> $null
      $toolUsed = 'gltf-transform'
      $optimized = $true
    } catch {
      Add-Row -Code 'C' -Label 'tool' -Status 'WARN' -Detail 'gltf-transform failed; attempting gltfpack.' -Hint 'Check npm cache or reinstall @gltf-transform/cli.'
    } finally {
      Remove-Item $temp1, $temp2 -ErrorAction SilentlyContinue
    }
  }

  if (-not $optimized -and $gltfpack) {
    if (-not ($rows | Where-Object { $_.Code -eq 'C' -and $_.Status -eq 'PASS' })) {
      Add-Row -Code 'C' -Label 'tool' -Status 'PASS' -Detail 'Using gltfpack fallback.'
    }
    try {
      & $gltfpack.Source -i $srcPath -o $outPath -cc *> $null
      $toolUsed = 'gltfpack'
      $optimized = $true
    } catch {
      Add-Row -Code 'C' -Label 'tool' -Status 'FAIL' -Detail 'gltfpack execution failed.' -Hint $hintMissing
    }
  }

  if (-not $optimized -and -not $npx -and -not $gltfpack) {
    Add-Row -Code 'C' -Label 'tool' -Status 'FAIL' -Detail 'No optimizer found on PATH.' -Hint $hintMissing
  }
}

if ($optimized -and (Test-Path -LiteralPath $outPath)) {
  $bytes = (Get-Item -LiteralPath $outPath).Length
  $mb = [math]::Round($bytes / 1MB, 2)
  Add-Row -Code 'D' -Label 'result' -Status 'PASS' -Detail ("Optimized ($mb MB) via $toolUsed")
} elseif ($srcPath) {
  Add-Row -Code 'D' -Label 'result' -Status 'FAIL' -Detail 'Optimization failed; source untouched.' -Hint $hintMissing
}

foreach ($row in $rows) {
  $status = Format-Status -Status $row.Status
  $line = "[{0}] {1,-3} {2,-12} {3}" -f $status, $row.Code, $row.Label, $row.Detail
  Write-Host $line
}

$finalStatus = 'PASS'
if ($rows.Status -contains 'FAIL') {
  $finalStatus = 'FAIL'
} elseif ($rows.Status -contains 'WARN') {
  $finalStatus = 'WARN'
}

$finalText = Format-Status -Status $finalStatus
Write-Host ("Final Decision: {0}" -f $finalText)

Write-Host 'Next Steps:'
switch ($finalStatus) {
  'PASS' { Write-Host '  • Use "Avatar: Check + Run" to validate the preview with the optimized GLB.' }
  'WARN' { Write-Host '  • Review the warning above; optimization completed with fallback.' }
  'FAIL' {
    $hints = $rows | Where-Object { $_.Status -eq 'FAIL' -and $_.Hint } | Select-Object -ExpandProperty Hint -Unique
    if ($hints) {
      foreach ($hint in $hints) { Write-Host ("  • {0}" -f $hint) }
    } else {
      Write-Host '  • Install gltf-transform or gltfpack and re-run this task.'
    }
  }
}

if ($finalStatus -eq 'FAIL') {
  exit 1
}

exit 0
