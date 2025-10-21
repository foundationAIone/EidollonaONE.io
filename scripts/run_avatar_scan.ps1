param(
    [string]$Repo = (Get-Location).Path,
    [int]$Top = 12
)

$ErrorActionPreference = 'Stop'
$initialLocation = Get-Location

function Get-PythonInterpreter {
    param([string]$RepoPath)

    $settingsPath = Join-Path $RepoPath '.vscode/settings.json'
    if (Test-Path -LiteralPath $settingsPath) {
        try {
            $raw = Get-Content -LiteralPath $settingsPath -Raw
            if (-not [string]::IsNullOrWhiteSpace($raw)) {
                $settings = $raw | ConvertFrom-Json
                $configured = $settings.'python.defaultInterpreterPath'
                if (-not [string]::IsNullOrWhiteSpace($configured)) {
                    return [pscustomobject]@{
                        Command = $configured
                        Args    = @()
                    }
                }
            }
        }
        catch {
            Write-Warning "Unable to parse .vscode/settings.json. Falling back to PATH lookup."
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return [pscustomobject]@{
            Command = $pythonCmd.Path
            Args    = @()
        }
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return [pscustomobject]@{
            Command = $pyCmd.Path
            Args    = @('-3')
        }
    }

    Write-Host "Python interpreter not found. Configure python.defaultInterpreterPath or install Python." -ForegroundColor Red
    return $null
}

try {
    if (-not (Test-Path -LiteralPath $Repo)) {
        throw "Repo not found: $Repo"
    }

    $resolvedRepo = (Resolve-Path -LiteralPath $Repo).Path
    Set-Location -LiteralPath $resolvedRepo

    $interpreter = Get-PythonInterpreter -RepoPath $resolvedRepo
    if (-not $interpreter) {
        exit 1
    }

    $scriptPath = Join-Path $resolvedRepo 'scripts/avatar_assets_scan.py'
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "Scanner script not found: $scriptPath"
    }

    $arguments = @()
    if ($interpreter.Args) {
        $arguments += $interpreter.Args
    }
    $arguments += @($scriptPath, '--repo', $resolvedRepo, '--top', $Top)

    & $interpreter.Command @arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        exit $exitCode
    }

    $logsPath = Join-Path $resolvedRepo 'logs'
    $latestReport = Get-ChildItem -LiteralPath $logsPath -Filter 'avatar_assets_scan_*.json' -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $latestReport) {
        Write-Host "No JSON report found in logs folder." -ForegroundColor Yellow
        exit $exitCode
    }

    Write-Host ("`nReport -> {0}" -f $latestReport.FullName)
    Get-Content -LiteralPath $latestReport.FullName -TotalCount 60 | ForEach-Object { Write-Host $_ }

    exit $exitCode
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
finally {
    Set-Location $initialLocation | Out-Null
}
