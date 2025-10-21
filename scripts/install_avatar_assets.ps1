Param(
  [string]$Repo = (Get-Location).Path,
  [string]$Model,
  [string]$Portrait,
  [switch]$Force
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

$mdlExists = $false
$imgExists = $false

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

Write-Host "${esc}[36m=== Avatar Asset Installer ===${esc}[0m"

try {
  $repoPath = (Resolve-Path -LiteralPath $Repo).Path
  Set-Location -LiteralPath $repoPath
} catch {
  Add-Row -Code 'A' -Label 'repo' -Status 'FAIL' -Detail "Repo not found: $Repo" -Hint 'Double-check the workspace folder path.'
  goto Complete
}

$mdlDir = Join-Path $repoPath 'web_interface\static\models'
$imgDir = Join-Path $repoPath 'web_interface\static\images'

foreach ($dir in @($mdlDir, $imgDir)) {
  if (-not (Test-Path -LiteralPath $dir)) {
    try {
      New-Item -ItemType Directory -Force -Path $dir | Out-Null
      Add-Row -Code 'B' -Label "mkdir" -Status 'PASS' -Detail ("Created {0}" -f ([System.IO.Path]::GetRelativePath($repoPath, $dir)))
    } catch {
      Add-Row -Code 'B' -Label "mkdir" -Status 'FAIL' -Detail ("Unable to create {0}" -f $dir) -Hint 'Check write permissions for /web_interface/static.'
      goto Complete
    }
  }
}

$mdlTgt = Join-Path $mdlDir 'steward_prime.glb'
$imgTgt = Join-Path $imgDir 'steward_prime_portrait.png'

if ($Model) {
  if (Test-Path -LiteralPath $Model -PathType Leaf) {
    try {
      if ($Force) {
        Copy-Item -LiteralPath $Model -Destination $mdlTgt -Force -ErrorAction Stop
      } else {
        Copy-Item -LiteralPath $Model -Destination $mdlTgt -ErrorAction Stop
      }
      $rel = [System.IO.Path]::GetRelativePath($repoPath, $mdlTgt)
      Add-Row -Code 'C1' -Label 'model' -Status 'PASS' -Detail ("Copied to {0}" -f $rel)
    } catch {
      Add-Row -Code 'C1' -Label 'model' -Status 'FAIL' -Detail ("Copy failed: {0}" -f $_.Exception.Message) -Hint 'Verify the GLB is not open in another application.'
    }
  } else {
    Add-Row -Code 'C1' -Label 'model' -Status 'FAIL' -Detail ("Model not found: {0}" -f $Model) -Hint 'Provide a valid *.glb path via -Model.'
  }
} else {
  if (Test-Path -LiteralPath $mdlTgt) {
    Add-Row -Code 'C1' -Label 'model' -Status 'PASS' -Detail 'Existing GLB retained.'
  } else {
    Add-Row -Code 'C1' -Label 'model' -Status 'WARN' -Detail 'No model supplied; GLB not installed.' -Hint 'Run again with -Model <path\to\avatar.glb>.'
  }
}

if ($Portrait) {
  if (Test-Path -LiteralPath $Portrait -PathType Leaf) {
    try {
      if ($Force) {
        Copy-Item -LiteralPath $Portrait -Destination $imgTgt -Force -ErrorAction Stop
      } else {
        Copy-Item -LiteralPath $Portrait -Destination $imgTgt -ErrorAction Stop
      }
      $rel = [System.IO.Path]::GetRelativePath($repoPath, $imgTgt)
      Add-Row -Code 'C2' -Label 'portrait' -Status 'PASS' -Detail ("Copied to {0}" -f $rel)
    } catch {
      Add-Row -Code 'C2' -Label 'portrait' -Status 'FAIL' -Detail ("Copy failed: {0}" -f $_.Exception.Message) -Hint 'Ensure the portrait image is readable (png/jpg).'
    }
  } else {
    Add-Row -Code 'C2' -Label 'portrait' -Status 'FAIL' -Detail ("Portrait not found: {0}" -f $Portrait) -Hint 'Provide a valid *.png or *.jpg via -Portrait.'
  }
} else {
  if (Test-Path -LiteralPath $imgTgt) {
    Add-Row -Code 'C2' -Label 'portrait' -Status 'PASS' -Detail 'Existing portrait retained.'
  } else {
    Add-Row -Code 'C2' -Label 'portrait' -Status 'WARN' -Detail 'No portrait supplied; fallback image missing.' -Hint 'Run again with -Portrait <path\to\portrait.png>.'
  }
}

$mdlExists = Test-Path -LiteralPath $mdlTgt
$imgExists = Test-Path -LiteralPath $imgTgt

if ($mdlExists -and $imgExists) {
  Add-Row -Code 'D' -Label 'coverage' -Status 'PASS' -Detail 'Model + portrait ready.'
} elseif ($mdlExists -or $imgExists) {
  Add-Row -Code 'D' -Label 'coverage' -Status 'WARN' -Detail 'Only one asset present; preview will downgrade.' -Hint 'Install the missing asset for full experience.'
} else {
  Add-Row -Code 'D' -Label 'coverage' -Status 'FAIL' -Detail 'No avatar assets available.' -Hint 'Provide at least one asset via -Model or -Portrait.'
}

:Complete

foreach ($row in $rows) {
  $status = Format-Status -Status $row.Status
  $line = "[{0}] {1,-3} {2,-12} {3}" -f $status, $row.Code, $row.Label, $row.Detail
  Write-Host $line
}

$okAssets = ($mdlExists -or $imgExists)
$finalStatus = 'FAIL'
if ($mdlExists -and $imgExists) {
  $finalStatus = 'PASS'
} elseif ($okAssets) {
  $finalStatus = 'WARN'
}

$finalText = Format-Status -Status $finalStatus
Write-Host ("Final Decision: {0}" -f $finalText)

if ($finalStatus -eq 'PASS') {
  Write-Host 'Next Steps: Run "Avatar: Quick Check (show results)" to confirm the pipeline, then launch the preview.'
}elseif ($finalStatus -eq 'WARN') {
  if (-not $mdlExists) {
    Write-Host 'Next Steps: Provide a GLB to unlock the 3D preview and re-run this task.'
  } else {
    Write-Host 'Next Steps: Provide a portrait image for fallback rendering and re-run this task.'
  }
} else {
  Write-Host 'Next Steps: Supply at least one asset path (-Model or -Portrait) and re-run the installer.'
}

if ($finalStatus -eq 'FAIL') {
  exit 1
}

exit 0
