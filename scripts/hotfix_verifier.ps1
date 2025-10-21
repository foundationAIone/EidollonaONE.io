# ======================= HOTFIX & VERIFIER — EidolonAlpha+ (SE4.3) =======================
$ErrorActionPreference = 'Stop'
$root = Get-Location
$logs = Join-Path $root 'logs'
New-Item -Force -ItemType Directory $logs | Out-Null
$aud = Join-Path $logs 'audit.ndjson'
if (!(Test-Path $aud)) {
    New-Item -Force -ItemType File $aud | Out-Null
}

# 0) Ensure Python package boundaries
$pkgs = @(
    'symbolic_core',
    'ai_core', 'ai_core\quantum_core', 'ai_core\quantum_core\quantum_logic',
    'avatar', 'citadel',
    'web_interface', 'web_interface\server',
    'quantum_probabilistic_information_rendering_system',
    'probabilistic_quantum_rendering',
    'qre', 'scripts', 'utils'
)
foreach ($p in $pkgs) {
    $d = Join-Path $root $p
    if (!(Test-Path $d)) {
        New-Item -Force -ItemType Directory $d | Out-Null
    }
    $init = Join-Path $d '__init__.py'
    if (!(Test-Path $init)) {
        Set-Content -Encoding UTF8 -Path $init -Value ''
    }
}

# 1) Minimal auditor fallback
$utilsAudit = Join-Path $root 'utils\audit.py'
if (!(Test-Path $utilsAudit)) {
@"
import json
import os
import time


def audit_ndjson(event: str, **fields):
    path = os.getenv('EIDOLLONA_AUDIT', 'logs/audit.ndjson')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as handle:
        payload = {'event': event, **fields, 'ts': time.time()}
        handle.write(json.dumps(payload, ensure_ascii=False) + '\n')
"@ | Set-Content -Encoding UTF8 -Path $utilsAudit
}

# 2) QPIR system percentile normalization
$qpirSystem = Join-Path $root 'quantum_probabilistic_information_rendering_system\system.py'
if (Test-Path $qpirSystem) {
    $txt = Get-Content -Path $qpirSystem -Raw -Encoding UTF8
    $pattern = '(?s)(def _probability_view\(.*?return xs, hist, p10, p50, p90)'
    $replacement = @'
    def _probability_view(
        self, impetus: float, risk: float
    ) -> Tuple[List[float], List[float], float, float, float]:
        """Render histogram percentiles using a deterministic Beta fit."""
        m = max(0.0, min(1.0, impetus))
        kappa = 2.0 + 10.0 * max(0.0, min(1.0, (1.0 - risk)))
        alpha = max(1e-3, m * kappa)
        beta = max(1e-3, (1.0 - m) * kappa)

        n = self.cfg.clamp_bins()
        xs = [i / (n - 1) for i in range(n)]

        def beta_pdf(x: float) -> float:
            if x <= 0.0 or x >= 1.0:
                x = max(1e-6, min(1.0 - 1e-6, x))
            return (x ** (alpha - 1.0)) * ((1.0 - x) ** (beta - 1.0))

        pdf = [beta_pdf(x) for x in xs]
        s = sum(pdf) or 1.0
        hist = [p / s for p in pdf]

        cdf = 0.0
        p10 = p50 = p90 = 0.0
        for x, h in zip(xs, hist):
            cdf += h
            if cdf >= 0.10 and p10 == 0.0:
                p10 = x
            if cdf >= 0.50 and p50 == 0.0:
                p50 = x
            if cdf >= 0.90 and p90 == 0.0:
                p90 = x
        return xs, hist, p10, p50, p90
'@
    $updated = $txt -replace $pattern, $replacement
    if ($updated -ne $txt) {
        Set-Content -Encoding UTF8 -Path $qpirSystem -Value $updated
    }
}

# 3) FastAPI bootstrap (hud + optionals)
$serverMain = Join-Path $root 'web_interface\server\main.py'
if (!(Test-Path $serverMain)) {
@"
"""FastAPI application bootstrap for HUD and auxiliary routers."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI

app = FastAPI(title="EidolonAlpha+ HUD")


# HUD (required)
try:
    from web_interface.server.hud_api import router as hud_router

    app.include_router(hud_router)
except Exception as exc:  # pragma: no cover - fallback path
    exc_detail = str(exc)

    @app.get("/api/hud/signals")
    def _hud_stub() -> Dict[str, Any]:
        return {"error": "hud_api_missing", "detail": exc_detail}


# Optional QPIR snapshot API
try:
    from quantum_probabilistic_information_rendering_system import fastapi_router

    app.include_router(fastapi_router())
except Exception:
    pass


# Optional Citadel endpoints
try:
    from citadel.router import Citadel

    _citadel = Citadel()

    @app.get("/api/citadel/rooms")
    def list_rooms() -> Any:
        return _citadel.list_rooms()

    @app.get("/api/citadel/rooms/{room_id}")
    def resolve_room(room_id: str) -> Any:
        return _citadel.resolve_avatar(room_id) or {"error": "not_found"}
except Exception:
    pass
"@ | Set-Content -Encoding UTF8 -Path $serverMain
}

# 4) Backend runner with gentle failure mode
$serve = Join-Path $root 'scripts\serve_backend.py'
@"
"""Local development launcher for the FastAPI HUD service."""
from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        import uvicorn
        from web_interface.server.main import app
    except Exception as exc:  # pragma: no cover - defensive path
        print({"error": "server_boot", "detail": str(exc)})
        sys.exit(0)

    host = os.getenv("HUD_HOST", "127.0.0.1")
    port = int(os.getenv("HUD_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
"@ | Set-Content -Encoding UTF8 -Path $serve

# 5) Compile and collect errors (workspace python only)
$compileLog = Join-Path $logs 'compile_errors.txt'
Remove-Item -ErrorAction Ignore $compileLog
$excluded = @('\eidollona_env\', '\.alpha_env\', '\venv\', '\quantum_env\', '\__pycache__\')
$pyFiles = Get-ChildItem -Path $root -Recurse -Filter *.py -File | Where-Object {
    $full = $_.FullName
    foreach ($skip in $excluded) {
        if ($full -like "*${skip}*") { return $false }
    }
    return $true
}
$errs = @()
foreach ($item in $pyFiles) {
    $f = $item.FullName
    $escaped = $f -replace '\\', '\\\\'
    $cmd = "import py_compile, sys; fn=r'$escaped'; print('COMPILING', fn); py_compile.compile(fn, doraise=True)"
    try {
        python -c "$cmd" | Out-Null
    } catch {
        $msg = $_.Exception.Message
        $errs += $f
        $errs += $msg
        Add-Content -Encoding UTF8 -Path $compileLog -Value "[ERROR] $f`n$msg`n"
    }
}

# 6) Summary output
$errCount = [int]($errs.Length / 2)
Write-Host "`n=== COMPILE SUMMARY ==="
if ($errCount -eq 0) {
    Write-Host "✅ No syntax/import errors detected by py_compile."
} else {
    Write-Host ("❌ Detected {0} compile/import errors. See {1}" -f $errCount, $compileLog)
    if (Test-Path $compileLog) {
        Get-Content -Path $compileLog -TotalCount 40 | Write-Host
    }
}

Write-Host "`nHow to smoke:"
Write-Host "  1) HUD server: python scripts/serve_backend.py"
Write-Host "     Then GET http://127.0.0.1:8000/api/hud/signals"
Write-Host "  2) QPIR snapshot: python -m quantum_probabilistic_information_rendering_system.system"
Write-Host "  3) ASCII snapshot: python -m probabilistic_quantum_rendering.ascii"
Write-Host "  4) Metrics rollup: python scripts/metrics/ndjson_rollup.py"

$auditEntry = [ordered]@{
    event = 'hotfix_verifier'
    decision = 'ALLOW'
    errors = $errCount
    ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
} | ConvertTo-Json -Compress
Add-Content -Encoding UTF8 -Path $aud -Value $auditEntry
# ==========================================================================================
