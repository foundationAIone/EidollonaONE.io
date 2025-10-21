Param(
  [string]$Repo = (Get-Location).Path,
  [string]$Py,
  [int]$NodeHeapMB = 3072
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

function ConvertTo-Hashtable {
  param([object]$Value)
  if ($Value -is [System.Collections.IDictionary]) {
    return $Value
  }
  if ($Value -is [System.Management.Automation.PSCustomObject]) {
    $hash = @{}
    foreach ($prop in $Value.PSObject.Properties) {
      $hash[$prop.Name] = ConvertTo-Hashtable $prop.Value
    }
    return $hash
  }
  return $Value
}

function ConvertTo-OrderedJson {
  param([object]$Value)
  if ($Value -is [System.Collections.IDictionary]) {
    $ordered = [ordered]@{}
    foreach ($key in ($Value.Keys | Sort-Object)) {
      $ordered[$key] = ConvertTo-OrderedJson $Value[$key]
    }
    return $ordered
  }
  if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
    $list = @()
    foreach ($item in $Value) {
      $list += ConvertTo-OrderedJson $item
    }
    return $list
  }
  if ($Value -is [System.Management.Automation.PSCustomObject]) {
    return ConvertTo-OrderedJson (ConvertTo-Hashtable $Value)
  }
  return $Value
}

Write-Host "${esc}[36m=== VS Code OOM Fast Fix ===${esc}[0m"

$repoPath = $null
try {
  $repoPath = (Resolve-Path -LiteralPath $Repo).Path
  Add-Row -Code 'A' -Label 'repo' -Status 'PASS' -Detail "Workspace: $repoPath"
} catch {
  Add-Row -Code 'A' -Label 'repo' -Status 'FAIL' -Detail "Repo not found: $Repo" -Hint 'Provide the workspaceFolder path to the task.'
}

$settingsPath = $null
$settingsObject = $null
if ($repoPath) {
  $settingsPath = Join-Path $repoPath '.vscode/settings.json'
  if (Test-Path -LiteralPath $settingsPath) {
    $raw = Get-Content -LiteralPath $settingsPath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
      $settingsObject = [ordered]@{}
    } else {
      try {
        $settingsObject = ConvertTo-Hashtable (ConvertFrom-Json -InputObject $raw -ErrorAction Stop)
      } catch {
        Add-Row -Code 'B' -Label 'settings' -Status 'FAIL' -Detail 'Unable to parse .vscode/settings.json' -Hint 'Fix JSON syntax or delete the file and rerun.'
      }
    }
  } else {
    $settingsObject = [ordered]@{}
  }
}

if (-not $settingsObject) {
  if ($rows.Status -contains 'FAIL') {
    foreach ($row in $rows) {
      $status = Format-Status -Status $row.Status
      Write-Host ("[{0}] {1,-3} {2,-12} {3}" -f $status, $row.Code, $row.Label, $row.Detail)
    }
    Write-Host ("Final Decision: {0}" -f (Format-Status -Status 'FAIL'))
    Write-Host 'Next Steps: Resolve the failures above and re-run.'
    exit 1
  }
}

if (-not $settingsObject) {
  $settingsObject = [ordered]@{}
}

$searchExclude = @{}
$watchExclude = @{}
if ($settingsObject.ContainsKey('search.exclude')) {
  $searchExclude = ConvertTo-Hashtable $settingsObject['search.exclude']
}
if ($settingsObject.ContainsKey('files.watcherExclude')) {
  $watchExclude = ConvertTo-Hashtable $settingsObject['files.watcherExclude']
}

$patterns = @(
  '**/.git/**', '**/logs/**', '**/data/**', '**/assets/**', '**/dist/**', '**/build/**',
  '**/out/**', '**/target/**', '**/venv/**', '**/.venv/**', '**/env/**', '**/eidollona_env/**',
  '**/quantum_env/**', '**/.alpha_env/**', '**/venv_management/**'
)
foreach ($pattern in $patterns) {
  $searchExclude[$pattern] = $true
  $watchExclude[$pattern] = $true
}
$settingsObject['search.exclude'] = $searchExclude
$settingsObject['files.watcherExclude'] = $watchExclude

$settingsObject['search.followSymlinks'] = $false
$settingsObject['files.maxMemoryForLargeFilesMB'] = 256
$settingsObject['typescript.tsserver.experimental.enableProjectDiagnostics'] = $false
$settingsObject['typescript.tsserver.maxTsServerMemory'] = 2048
$settingsObject['python.analysis.indexing'] = $false
$settingsObject['python.analysis.userFileIndexingLimit'] = 1000
$settingsObject['python.analysis.typeCheckingMode'] = 'off'

$interpreterPath = $null
$interpreterHint = $null
if ($Py) {
  try {
    $interpreterPath = (Resolve-Path -LiteralPath $Py).Path
  } catch {
    $interpreterPath = $Py
    $interpreterHint = 'Interpreter path not found; double-check -Py value.'
  }
} elseif ($settingsObject.ContainsKey('python.defaultInterpreterPath')) {
  $configured = [string]$settingsObject['python.defaultInterpreterPath']
  if ($configured) {
    $candidate = $configured.Replace('${workspaceFolder}', $repoPath)
    try {
      $interpreterPath = (Resolve-Path -LiteralPath $candidate).Path
    } catch {
      $interpreterPath = $candidate
      $interpreterHint = 'Configured interpreter missing on disk; update the path.'
    }
  }
}

if (-not $interpreterPath -and (Test-Path -LiteralPath 'E:\.venvs')) {
  $venv = Get-ChildItem -Path 'E:\.venvs' -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($venv) {
    $candidate = Join-Path $venv.FullName 'Scripts\python.exe'
    if (Test-Path -LiteralPath $candidate) {
      $interpreterPath = $candidate
    }
  }
}

if ($interpreterPath) {
  $settingsObject['python.defaultInterpreterPath'] = $interpreterPath
  if (Test-Path -LiteralPath $interpreterPath) {
    Add-Row -Code 'C' -Label 'interpreter' -Status 'PASS' -Detail $interpreterPath
  } else {
    Add-Row -Code 'C' -Label 'interpreter' -Status 'WARN' -Detail $interpreterPath -Hint ($interpreterHint ?? 'Interpreter path not found; update python.defaultInterpreterPath.')
  }
} else {
  Add-Row -Code 'C' -Label 'interpreter' -Status 'WARN' -Detail 'Interpreter not resolved.' -Hint 'Provide -Py <path\python.exe> or create E:\.venvs\<env> first.'
}

$missingWatch = @($patterns | Where-Object { -not $watchExclude.ContainsKey($_) -or -not $watchExclude[$_] })
if ($missingWatch.Count -eq 0) {
  Add-Row -Code 'D' -Label 'watchers' -Status 'PASS' -Detail 'Watcher excludes applied.'
} else {
  Add-Row -Code 'D' -Label 'watchers' -Status 'WARN' -Detail 'Some watcher excludes missing.' -Hint 'Re-run task to enforce watcher excludes.'
}

$missingSearch = @($patterns | Where-Object { -not $searchExclude.ContainsKey($_) -or -not $searchExclude[$_] })
if ($missingSearch.Count -eq 0) {
  Add-Row -Code 'E' -Label 'search' -Status 'PASS' -Detail 'Search excludes applied.'
} else {
  Add-Row -Code 'E' -Label 'search' -Status 'WARN' -Detail 'Search excludes incomplete.' -Hint 'Re-run task to enforce search excludes.'
}

if ($settingsObject['python.analysis.indexing'] -eq $false -and $settingsObject['python.analysis.userFileIndexingLimit'] -le 1000) {
  Add-Row -Code 'F' -Label 'pylance' -Status 'PASS' -Detail 'Indexing limited/off.'
} else {
  Add-Row -Code 'F' -Label 'pylance' -Status 'WARN' -Detail 'Pylance indexing still high.' -Hint 'Set python.analysis.indexing=false and userFileIndexingLimit=1000.'
}

if ($settingsObject['typescript.tsserver.maxTsServerMemory'] -ge 2048) {
  Add-Row -Code 'G' -Label 'tsserver' -Status 'PASS' -Detail 'tsserver memory boosted.'
} else {
  Add-Row -Code 'G' -Label 'tsserver' -Status 'WARN' -Detail 'tsserver memory low.' -Hint 'Set typescript.tsserver.maxTsServerMemory to 2048.'
}

$orderedSettings = ConvertTo-OrderedJson $settingsObject
$settingsJson = ($orderedSettings | ConvertTo-Json -Depth 12)
if ($settingsPath) {
  $settingsDir = Split-Path -Parent $settingsPath
  if (-not (Test-Path -LiteralPath $settingsDir)) {
    New-Item -ItemType Directory -Force -Path $settingsDir | Out-Null
  }
  Set-Content -LiteralPath $settingsPath -Value $settingsJson -Encoding UTF8
  Add-Row -Code 'H' -Label 'settings' -Status 'PASS' -Detail '.vscode/settings.json updated.'
}

# Apply session clamps
$env:NODE_OPTIONS = "--max-old-space-size=$NodeHeapMB"
$env:ELECTRON_DISABLE_GPU = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:BLIS_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
$env:PYTHONMALLOC = 'malloc'
Add-Row -Code 'I' -Label 'session' -Status 'PASS' -Detail "NODE_OPTIONS set to ${NodeHeapMB} MB; CPU threads pinned."

$codeCmd = $null
foreach ($candidate in @('code.cmd','code.exe','code')) {
  $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
  if ($cmd) {
    $codeCmd = $cmd
    break
  }
}

if ($codeCmd) {
  try {
    Start-Process -FilePath $codeCmd.Source -ArgumentList @('--disable-extensions','--disable-gpu',$repoPath) | Out-Null
    Add-Row -Code 'J' -Label 'relaunch' -Status 'PASS' -Detail 'VS Code relaunched (--disable-extensions --disable-gpu).'
  } catch {
    Add-Row -Code 'J' -Label 'relaunch' -Status 'WARN' -Detail 'VS Code relaunch failed.' -Hint 'Run: code --disable-extensions --disable-gpu .' 
  }
} else {
  Add-Row -Code 'J' -Label 'relaunch' -Status 'WARN' -Detail 'code command not found.' -Hint 'Add VS Code to PATH or run "Shell Command: Install `code` command".'
}

foreach ($row in $rows) {
  $status = Format-Status -Status $row.Status
  Write-Host ("[{0}] {1,-3} {2,-12} {3}" -f $status, $row.Code, $row.Label, $row.Detail)
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
if ($finalStatus -eq 'PASS') {
  Write-Host '  • Close unused VS Code windows and continue working in the relaunched session.'
} elseif ($finalStatus -eq 'WARN') {
  $hints = $rows | Where-Object { $_.Status -eq 'WARN' -and $_.Hint } | Select-Object -ExpandProperty Hint -Unique
  if ($hints) {
    foreach ($hint in $hints) { Write-Host ("  • {0}" -f $hint) }
  } else {
    Write-Host '  • Review WARN items above and address as needed.'
  }
} else {
  $hints = $rows | Where-Object { $_.Status -eq 'FAIL' -and $_.Hint } | Select-Object -ExpandProperty Hint -Unique
  if ($hints) {
    foreach ($hint in $hints) { Write-Host ("  • {0}" -f $hint) }
  } else {
    Write-Host '  • Resolve configuration issues and re-run the fast fix.'
  }
}

Write-Host 'Done. Keep only essential extensions (Python, Pylance) enabled.'

if ($finalStatus -eq 'FAIL') {
  exit 1
}

exit 0
