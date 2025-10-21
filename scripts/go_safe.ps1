param(
	[string]$Base  = "http://127.0.0.1:8802",
	[string]$Token = "dev-token"
)

$ErrorActionPreference = 'Stop'

$ROOT = $PWD.Path
$py   = Join-Path $ROOT ".alpha_env\Scripts\python.exe"
$orc  = Join-Path $ROOT "scripts\paper_orchestrator.py"
$plan = Join-Path $ROOT "scripts\dry_run_plan.py"

function Get-Json {
	param(
		[string]$Url,
		[ValidateSet('GET','POST')][string]$Method = 'GET',
		$Body = $null
	)

	try {
		if ($Method -eq 'GET') {
			return Invoke-RestMethod -Uri $Url -Method GET -TimeoutSec 15 -ErrorAction Stop
		}
		return Invoke-RestMethod -Uri $Url -Method POST -Body $Body -ContentType 'application/json' -TimeoutSec 30 -ErrorAction Stop
	} catch {
		throw "HTTP error calling $Url : $($_.Exception.Message)"
	}
}

Write-Host "SE41 summary → $Base/v1/status/summary"

try {
	$sum = Get-Json "$Base/v1/status/summary?token=$Token"
} catch {
	Write-Error "Cannot reach $Base : $_"
	exit 1
}

if (-not $sum -or -not $sum.gate -or -not $sum.readiness) {
	Write-Error "Malformed response from /v1/status/summary"
	exit 1
}

$gate  = [string]$sum.gate
$ready = [string]$sum.readiness
Write-Host ("Readiness: {0}  Gate: {1}" -f $ready, $gate)

$env:ALPHATAP_BASE  = $Base
$env:ALPHATAP_TOKEN = $Token

try {
	if ($gate -eq 'ALLOW') {
		& $py $orc
	} else {
		& $py $plan
	}
} catch {
	Write-Error "Failed to run action: $($_.Exception.Message)"
}

Write-Host "`nAudit tail:"
try {
	$tail = Get-Json "$Base/v1/audit/tail?limit=50&token=$Token"
	$tail | ConvertTo-Json -Depth 10
} catch {
	Write-Warning "Could not read audit tail: $($_.Exception.Message)"
}
