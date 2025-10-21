Param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$esc = [char]27

$results = @()

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

function Add-Result {
	param(
		[Parameter(Mandatory = $true)][ValidateSet('PASS','WARN','FAIL')]
		[string]$Status,
		[Parameter(Mandatory = $true)][string]$Code,
		[Parameter(Mandatory = $true)][string]$Label,
		[Parameter(Mandatory = $true)][string]$Detail,
		[string]$Recommendation,
		[switch]$Required
	)
	$script:results += [pscustomobject]@{
		Status = $Status
		Code = $Code
		Label = $Label
		Detail = $Detail
		Recommendation = $Recommendation
		Required = [bool]$Required
	}
}

function Resolve-PythonInterpreter {
	$settingsPath = Join-Path $repoRoot '.vscode/settings.json'
	$candidates = @()
	if (Test-Path -LiteralPath $settingsPath) {
		try {
			$settingsContent = Get-Content -LiteralPath $settingsPath -Raw
			if ($settingsContent) {
				$settingsJson = $settingsContent | ConvertFrom-Json -ErrorAction Stop
				$rawPath = $settingsJson.'python.defaultInterpreterPath'
				if ($rawPath) {
					$expanded = $rawPath.Replace('${workspaceFolder}', $repoRoot)
					# Normalize potential relative paths
					try {
						$expandedPath = (Resolve-Path -LiteralPath $expanded).ProviderPath
					} catch {
						$expandedPath = $expanded
					}
					$candidates += [pscustomobject]@{
						Command = $expandedPath
						Args = @()
						Display = $rawPath
					}
				}
			}
		} catch {
			# ignore malformed JSON
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
		if (-not $candidate) { continue }
		$commandArgs = @()
		if ($candidate.Args) { $commandArgs += $candidate.Args }
		$commandArgs += @('-c', 'import sys')
		try {
			& $candidate.Command @commandArgs *> $null
			if ($LASTEXITCODE -eq 0) {
				return $candidate
			}
		} catch {
			continue
		}
	}

	return $null
}

Write-Host "${esc}[36m=== Avatar Quick Check ===${esc}[0m"

# A) Popup HTML present
$popupRel = 'web_interface/static/webview/avatar_popup.html'
$popupFull = Join-Path $repoRoot $popupRel
if (Test-Path -LiteralPath $popupFull) {
	Add-Result -Status 'PASS' -Code 'A' -Label 'popup_html' -Detail $popupRel -Required
} else {
	Add-Result -Status 'FAIL' -Code 'A' -Label 'popup_html' -Detail "$popupRel (missing)" -Recommendation 'Restore web_interface/static/webview/avatar_popup.html from source control.' -Required
}

# B) Preview server mounts
$serverRel = 'scripts/avatar_preview_server.py'
$serverFull = Join-Path $repoRoot $serverRel
$serverContent = $null
if (Test-Path -LiteralPath $serverFull) {
	$serverContent = Get-Content -LiteralPath $serverFull -Raw
	if ($serverContent -match 'app\.mount\(\s*"/webview"') {
	Add-Result -Status 'PASS' -Code 'B1' -Label 'server_mount_webview' -Detail $serverRel -Required
	} else {
	Add-Result -Status 'FAIL' -Code 'B1' -Label 'server_mount_webview' -Detail 'Missing app.mount("/webview", ...)' -Recommendation 'Add app.mount("/webview", ...) to scripts/avatar_preview_server.py.' -Required
	}
	if ($serverContent -match 'app\.mount\(\s*"/static"') {
	Add-Result -Status 'PASS' -Code 'B2' -Label 'server_mount_static' -Detail $serverRel -Required
	} else {
	Add-Result -Status 'FAIL' -Code 'B2' -Label 'server_mount_static' -Detail 'Missing app.mount("/static", ...)' -Recommendation 'Add app.mount("/static", ...) to scripts/avatar_preview_server.py.' -Required
	}
} else {
	Add-Result -Status 'FAIL' -Code 'B1' -Label 'server_mount_webview' -Detail "$serverRel (missing)" -Recommendation 'Restore scripts/avatar_preview_server.py with /webview mount.' -Required
	Add-Result -Status 'FAIL' -Code 'B2' -Label 'server_mount_static' -Detail "$serverRel (missing)" -Recommendation 'Restore scripts/avatar_preview_server.py with /static mount.' -Required
}

# C) Preview API file & logic
$apiRel = 'web_interface/server/avatar_preview_api.py'
$apiFull = Join-Path $repoRoot $apiRel
$apiContent = $null
if (Test-Path -LiteralPath $apiFull) {
	$apiContent = Get-Content -LiteralPath $apiFull -Raw
	if ($apiContent -match 'def\s+avatar_preview\s*\(') {
	Add-Result -Status 'PASS' -Code 'C1' -Label 'api_endpoint' -Detail $apiRel -Required
	} else {
	Add-Result -Status 'FAIL' -Code 'C1' -Label 'api_endpoint' -Detail 'avatar_preview endpoint missing' -Recommendation 'Ensure web_interface/server/avatar_preview_api.py defines avatar_preview().' -Required
	}
	if ($apiContent -match '\bmodel_url\b') {
	Add-Result -Status 'PASS' -Code 'C2' -Label 'api_model_url' -Detail 'model_url logic present' -Required
	} else {
	Add-Result -Status 'FAIL' -Code 'C2' -Label 'api_model_url' -Detail 'model_url reference missing' -Recommendation 'Add model_url handling to avatar_preview API response.' -Required
	}
} else {
	Add-Result -Status 'FAIL' -Code 'C1' -Label 'api_endpoint' -Detail "$apiRel (missing)" -Recommendation 'Restore web_interface/server/avatar_preview_api.py with avatar_preview endpoint.' -Required
	Add-Result -Status 'FAIL' -Code 'C2' -Label 'api_model_url' -Detail "$apiRel (missing)" -Recommendation 'Restore web_interface/server/avatar_preview_api.py with model_url support.' -Required
}

# D) Assets on disk
$modelCandidates = @(
	'web_interface/static/models/steward_prime.glb',
	'web_interface/static/models/avatar.glb',
	'assets/models/steward_prime.glb'
)
$knownAvailable = @()
foreach ($candidateRel in $modelCandidates) {
	$candidateFull = Join-Path $repoRoot $candidateRel
	if (Test-Path -LiteralPath $candidateFull) {
		$knownAvailable += $candidateRel
	}
}
try {
	$allModels = Get-ChildItem -Path $repoRoot -Recurse -File -Include '*.glb','*.gltf' -ErrorAction SilentlyContinue
} catch {
	$allModels = @()
}
$topModels = @()
if ($allModels) {
	$topModels = $allModels | Sort-Object Length -Descending | Select-Object -First 3
}
if ($allModels -and $allModels.Count -gt 0) {
	if ($knownAvailable -and $knownAvailable.Count -gt 0) {
		$detail = "found $($allModels.Count) model(s); includes: $([string]::Join(', ', $knownAvailable))"
	} else {
		$detail = "found $($allModels.Count) model(s)"
	}
	Add-Result -Status 'PASS' -Code 'D' -Label 'models_on_disk' -Detail $detail -Required:$false
} else {
	Add-Result -Status 'WARN' -Code 'D' -Label 'models_on_disk' -Detail '(no GLB/GLTF found)' -Recommendation 'Copy a GLB to web_interface/static/models/steward_prime.glb (or avatar.glb).' -Required:$false
}

# E) Python deps
$pythonInfo = Resolve-PythonInterpreter
if ($pythonInfo) {
	$pythonArgs = @()
	if ($pythonInfo.Args) { $pythonArgs += $pythonInfo.Args }
	$pythonArgs += @('-c', 'import fastapi, uvicorn')
	try {
		& $pythonInfo.Command @pythonArgs *> $null
		if ($LASTEXITCODE -eq 0) {
			Add-Result -Status 'PASS' -Code 'E' -Label 'python_deps' -Detail "fastapi/uvicorn OK via $($pythonInfo.Display)" -Required
		} else {
			Add-Result -Status 'WARN' -Code 'E' -Label 'python_deps' -Detail 'fastapi or uvicorn missing' -Recommendation 'Run: python -m pip install fastapi uvicorn' -Required
		}
	} catch {
	Add-Result -Status 'WARN' -Code 'E' -Label 'python_deps' -Detail 'fastapi or uvicorn missing' -Recommendation 'Run: python -m pip install fastapi uvicorn' -Required
	}
} else {
	Add-Result -Status 'FAIL' -Code 'E' -Label 'python_deps' -Detail 'Python interpreter not found (checked settings, python, py -3)' -Recommendation 'Install Python 3 or set python.defaultInterpreterPath in VS Code.' -Required
}

# F) Launcher present
$launcherRel = 'scripts/run_avatar_preview.ps1'
$launcherFull = Join-Path $repoRoot $launcherRel
if (Test-Path -LiteralPath $launcherFull) {
	Add-Result -Status 'PASS' -Code 'F' -Label 'launcher' -Detail $launcherRel -Required:$false
} else {
	Add-Result -Status 'WARN' -Code 'F' -Label 'launcher' -Detail '(launcher script missing)' -Recommendation 'Optional: add scripts/run_avatar_preview.ps1 for one-click launch.' -Required:$false
}

# Emit table
foreach ($result in $results) {
	$statusText = Format-Status -Status $result.Status
	$line = "[{0}] {1,-3} {2,-24} {3}" -f $statusText, $result.Code, $result.Label, $result.Detail
	Write-Host $line
}

# Top models output
Write-Host 'Top 3 models by size:'
if ($topModels -and $topModels.Count -gt 0) {
	foreach ($model in $topModels) {
		$relativePath = [System.IO.Path]::GetRelativePath($repoRoot, $model.FullName)
		Write-Host ("  • {0} ({1:N0} bytes)" -f $relativePath, $model.Length)
	}
} else {
	Write-Host '  • (none found)'
}

Write-Host '---'

$finalStatus = 'PASS'
$requiredResults = $results | Where-Object { $_.Required }
if ($requiredResults.Status -contains 'FAIL') {
	$finalStatus = 'FAIL'
} elseif ($requiredResults.Status -contains 'WARN') {
	$finalStatus = 'FAIL'
} else {
	$warns = $results | Where-Object { $_.Status -eq 'WARN' }
	if ($warns) {
		$nonModelWarns = $warns | Where-Object { $_.Code -ne 'D' }
		if ($nonModelWarns.Count -eq 0) {
			$finalStatus = 'WARN'
		} else {
			$finalStatus = 'FAIL'
		}
	}
}

$finalText = Format-Status -Status $finalStatus
Write-Host ("Final Decision: {0}" -f $finalText)

$actionable = $results | Where-Object { ($_.Status -ne 'PASS') -and ($_.Recommendation) }
Write-Host 'Next Steps:'
if ($actionable -and $actionable.Count -gt 0) {
	$uniqueRecommendations = $actionable | Select-Object -ExpandProperty Recommendation -Unique
	foreach ($recommendation in $uniqueRecommendations) {
		Write-Host ("  • {0}" -f $recommendation)
	}
} elseif ($finalStatus -eq 'PASS') {
	Write-Host '  • Ready to launch — run the VS Code task "Avatar: Run preview" to view the popup.'
} else {
	Write-Host '  • Review PASS/WARN/FAIL items above.'
}

if ($finalStatus -eq 'FAIL') {
	exit 1
}

exit 0
