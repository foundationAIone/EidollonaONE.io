Param(
    [string]$Repo = (Get-Location).Path,
    [int]$Port = 8077
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$esc = [char]27
$originalLocation = Get-Location

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

function Resolve-Python {
    param([string]$RepoPath)

    $settingsPath = Join-Path $RepoPath '.vscode/settings.json'
    $candidates = @()
    if (Test-Path -LiteralPath $settingsPath) {
        try {
            $settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json -ErrorAction Stop
            $configured = $settings.'python.defaultInterpreterPath'
            if ($configured) {
                $expanded = $configured.Replace('${workspaceFolder}', $RepoPath)
                try {
                    $expanded = (Resolve-Path -LiteralPath $expanded).Path
                } catch {
                    # fall back to literal path
                }
                $candidates += [pscustomobject]@{
                    Command = $expanded
                    Args = @()
                    Display = $configured
                }
            }
        } catch {
            # ignore malformed json
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $candidates += [pscustomobject]@{
            Command = $pythonCmd.Path
            Args = @()
            Display = 'python'
        }
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $candidates += [pscustomobject]@{
            Command = $pyCmd.Path
            Args = @('-3')
            Display = 'py -3'
        }
    }

    foreach ($candidate in $candidates) {
        $testArgs = @()
        if ($candidate.Args) { $testArgs += $candidate.Args }
        $testArgs += @('-c', 'import sys')
        try {
            & $candidate.Command @testArgs *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            continue
        }
    }

    return $null
}

Write-Host "${esc}[36m=== Avatar Preview Launcher ===${esc}[0m"

$repoPath = $null
try {
    $repoPath = (Resolve-Path -LiteralPath $Repo).Path
    Add-Row -Code 'A' -Label 'repo' -Status 'PASS' -Detail "Using $repoPath"
} catch {
    Add-Row -Code 'A' -Label 'repo' -Status 'FAIL' -Detail "Repo not found: $Repo" -Hint 'Verify the workspaceFolder passed to the task.'
}

$pythonInfo = $null
if ($repoPath) {
    $pythonInfo = Resolve-Python -RepoPath $repoPath
    if ($pythonInfo) {
        Add-Row -Code 'B' -Label 'python' -Status 'PASS' -Detail "Interpreter: $($pythonInfo.Display)"
    } else {
        Add-Row -Code 'B' -Label 'python' -Status 'FAIL' -Detail 'Interpreter not found (settings → python → py -3)' -Hint 'Install Python 3 and/or set python.defaultInterpreterPath.'
    }
}

if ($pythonInfo) {
    $depsArgs = @()
    if ($pythonInfo.Args) { $depsArgs += $pythonInfo.Args }
    $depsArgs += @('-c', 'import fastapi, uvicorn')
    try {
        & $pythonInfo.Command @depsArgs *> $null
        if ($LASTEXITCODE -eq 0) {
            Add-Row -Code 'C' -Label 'deps' -Status 'PASS' -Detail 'fastapi + uvicorn present.'
        } else {
            Add-Row -Code 'C' -Label 'deps' -Status 'FAIL' -Detail 'fastapi/uvicorn missing.' -Hint 'Run: python -m pip install fastapi uvicorn'
        }
    } catch {
        Add-Row -Code 'C' -Label 'deps' -Status 'FAIL' -Detail 'fastapi/uvicorn missing.' -Hint 'Run: python -m pip install fastapi uvicorn'
    }
}

$serverScript = $null
if ($repoPath) {
    $serverScript = Join-Path $repoPath 'scripts/avatar_preview_server.py'
    if (Test-Path -LiteralPath $serverScript) {
        Add-Row -Code 'D' -Label 'server_script' -Status 'PASS' -Detail 'scripts/avatar_preview_server.py located.'
    } else {
        Add-Row -Code 'D' -Label 'server_script' -Status 'FAIL' -Detail 'scripts/avatar_preview_server.py missing.' -Hint 'Restore the preview server script from source control.'
    }
}

foreach ($row in $rows) {
    $status = Format-Status -Status $row.Status
    $line = "[{0}] {1,-3} {2,-14} {3}" -f $status, $row.Code, $row.Label, $row.Detail
    Write-Host $line
}

$finalStatus = 'PASS'
if ($rows.Status -contains 'FAIL') {
    $finalStatus = 'FAIL'
}

$finalText = Format-Status -Status $finalStatus
Write-Host ("Final Decision: {0}" -f $finalText)

Write-Host 'Next Steps:'
if ($finalStatus -eq 'PASS') {
    Write-Host '  • Browser popup launches automatically. Press Ctrl+C in this terminal to stop the server.'
} else {
    $fixes = $rows | Where-Object { $_.Status -eq 'FAIL' -and $_.Hint }
    if ($fixes) {
        foreach ($fix in $fixes | Select-Object -Unique Hint) {
            Write-Host ("  • {0}" -f $fix.Hint)
        }
    } else {
        Write-Host '  • Resolve the FAIL items above and re-run the task.'
    }
}

if ($finalStatus -eq 'FAIL') {
    exit 1
}

# Launch server and open the webview
Set-Location -LiteralPath $repoPath

$serverArgs = @()
if ($pythonInfo.Args) { $serverArgs += $pythonInfo.Args }
$serverArgs += 'scripts/avatar_preview_server.py'

Write-Host "Launching uvicorn on port $Port ..."
$proc = Start-Process -FilePath $pythonInfo.Command -ArgumentList $serverArgs -WorkingDirectory $repoPath -NoNewWindow -PassThru

Start-Sleep -Seconds 2

$url = "http://127.0.0.1:$Port/webview/avatar_popup.html"
try {
    $pingOk = $false
    for ($i = 0; $i -lt 5 -and -not $pingOk; $i++) {
        try {
            Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/api/avatar/preview" -f $Port) -UseBasicParsing -TimeoutSec 2 *> $null
            $pingOk = $true
        } catch {
            Start-Sleep -Milliseconds 700
        }
    }
    if ($pingOk) {
        Write-Host ("Launched preview server (PID {0})." -f $proc.Id)
    } else {
        Write-Host "Server ping timed out; check uvicorn logs below." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Server availability probe failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Start-Process $url | Out-Null
Write-Host "Opened popup: $url"
Write-Host 'Logs streaming below — press Ctrl+C to stop the server.'

try {
    Wait-Process -InputObject $proc
} finally {
    if (-not $proc.HasExited) {
        Stop-Process -InputObject $proc -Force
    }
    Set-Location -LiteralPath $originalLocation.Path | Out-Null
}
