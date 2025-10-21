param(
    [switch]$StartApi,
    [string]$PythonPath = ".\\eidollona_env\\Scripts\\python.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

function Write-Section($title) {
    Write-Host "`n=== $title ===" -ForegroundColor Cyan
}

function Invoke-ApiStart {
    param([string]$Path)
    Write-Section "AlphaTap API"
    if (-not $StartApi) {
        Write-Host "Skipping API bootstrap (use -StartApi to enable)." -ForegroundColor Yellow
        return $null
    }
    if (-not (Test-Path $Path)) {
        Write-Host "Python interpreter not found at $Path" -ForegroundColor Red
        return $null
    }
    $apiArgs = "-m", "uvicorn", "web_planning.backend.main:app", "--host", "127.0.0.1", "--port", "8000"
    Write-Host "Launching API: $Path $($apiArgs -join ' ')" -ForegroundColor Green
    $process = Start-Process -FilePath $Path -ArgumentList $apiArgs -PassThru -WindowStyle Minimized
    Start-Sleep -Seconds 3
    return $process
}

function Invoke-ReadinessProbe {
    param([string]$Path)
    Write-Section "Readiness Probe"
    if (-not (Test-Path $Path)) {
        throw "Python interpreter not found at $Path"
    }
    $probeArgs = @("scripts/readiness_probe.py")
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Path
    $psi.WorkingDirectory = $repoRoot
    $psi.ArgumentList.AddRange($probeArgs)
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $proc.Start() | Out-Null
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    Write-Host $stdout
    if ($stderr) {
        Write-Host $stderr -ForegroundColor DarkYellow
    }
    return $proc.ExitCode
}

function Get-ReadinessSummary {
    $jsonPath = Join-Path $repoRoot "logs/readiness.json"
    if (-not (Test-Path $jsonPath)) {
        Write-Host "readiness.json not found; treating as failure" -ForegroundColor Red
        return @{ Status = "fail" }
    }
    $summary = Get-Content $jsonPath -Raw | ConvertFrom-Json
    $allowedYellow = @("planning", "security", "trading", "ai_learning")
    $moduleFailures = @()
    $moduleWarnings = @()
    foreach ($key in $summary.modules.PSObject.Properties.Name) {
        $module = $summary.modules.$key
        $testStatus = $module.tests.status
        Write-Host ("[{0}] {1} ⇒ {2}" -f $module.state, $module.label, $testStatus) -ForegroundColor ((if ($testStatus -eq "pass") { "Green" } elseif ($testStatus -eq "skipped") { "DarkYellow" } else { "Red" }))
        if ($testStatus -eq "fail") {
            $moduleFailures += $key
        } elseif (($testStatus -ne "pass") -and ($testStatus -ne "skipped")) {
            $moduleWarnings += $key
        }
    }
    if ($moduleFailures.Count -gt 0) {
        $labels = $moduleFailures | ForEach-Object { $summary.modules.$_.label }
        return @{ Status = "fail"; Detail = "Failures: $($labels -join ', ')" }
    }
    if ($moduleWarnings.Count -gt 0) {
        $unapproved = $moduleWarnings | Where-Object { $allowedYellow -notcontains $_ }
        if ($unapproved.Count -gt 0) {
            $warnLabels = $unapproved | ForEach-Object { $summary.modules.$_.label }
            return @{ Status = "warn"; Detail = "Warnings outside allowlist: $($warnLabels -join ', ')" }
        }
    }
    return @{ Status = "pass" }
}

$apiProcess = Invoke-ApiStart -Path $PythonPath
try {
    [void](Invoke-ReadinessProbe -Path $PythonPath)
    $summary = Get-ReadinessSummary
    if ($summary.Status -eq "pass") {
        Write-Host "`nREADINESS: PASS" -ForegroundColor Green
        exit 0
    }
    if ($summary.Status -eq "warn") {
        Write-Host "`nREADINESS: WARN - $($summary.Detail)" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "`nREADINESS: FAIL - $($summary.Detail)" -ForegroundColor Red
    exit 1
}
finally {
    if ($apiProcess -and -not $apiProcess.HasExited) {
        Write-Host "Stopping API process (PID $($apiProcess.Id))" -ForegroundColor DarkCyan
        try {
            $apiProcess.Kill()
        } catch {
            Write-Host "Unable to terminate API process: $_" -ForegroundColor DarkYellow
        }
    }
}
