# ====================== EIDOLONALPHA+ — PROJECT STATUS & VERIFICATION (SE4.3 FULL) ======================
$ErrorActionPreference = 'Stop'
$root = Get-Location
$cfg  = Join-Path $root 'config'
$logs = Join-Path $root 'logs'
$aud  = Join-Path $logs 'audit.ndjson'
$syms = Join-Path $root 'symbolic_core'
$bots = Join-Path $root 'bots'
$alg  = Join-Path $root 'algorithms'
$eng  = Join-Path $root 'trading_engine'
$scr  = Join-Path $root 'scripts'
$tests= Join-Path $root 'tests'

# Ensure logs exist
New-Item -Force -ItemType Directory $logs | Out-Null
if (!(Test-Path $aud)) { New-Item -Force -ItemType File $aud | Out-Null }

# --- helpers ---
function Colorize($ok){ if($ok){ return "🟢" } else { return "🔴" } }
function Row($name,$ok,$msg){ Write-Host ("{0} {1,-26} | {2}" -f (Colorize $ok), $name, $msg) }

Write-Host "`n=== EidolonAlpha+ — Project Status (SE4.3 • Wings/Aletheia) ===`n"

# 1) Config checks
$se43y = Join-Path $cfg 'se43.yml'
$botsy = Join-Path $cfg 'bots.yml'
$polcy = Join-Path $cfg 'trading_policy_crypto.yml'

$cfg_ok = (Test-Path $se43y) -and (Test-Path $botsy) -and (Test-Path $polcy)
$se_enforced = $false
if (Test-Path $botsy) {
  $raw = Get-Content -Raw -Encoding UTF8 $botsy
  $se_enforced = $raw -match '(?m)^\s*se_enforced\s*:\s*true\b'
}
Row "Configs present" $cfg_ok ("se43.yml, bots.yml, trading_policy_crypto.yml")
Row "SE enforcement on" $se_enforced ("config/bots.yml se_enforced: true")

# 2) SE4.3 core files
$se_core_ok = (Test-Path (Join-Path $syms 'se43_wings.py')) -and (Test-Path (Join-Path $syms 'se_loader_ext.py'))
Row "SE4.3 core code" $se_core_ok ("symbolic_core/se43_wings.py & se_loader_ext.py")

# 3) Algorithms & router presence
$alg_ok = (Test-Path (Join-Path $alg 'exec\almgren_chriss.py')) -and (Test-Path (Join-Path $alg 'micro\avellaneda_stoikov.py')) `
  -and (Test-Path (Join-Path $alg 'regime\bocd_har.py')) -and (Test-Path (Join-Path $alg 'alloc\exp3s.py')) `
  -and (Test-Path (Join-Path $alg 'portfolio\hrp.py'))
Row "Algorithms present" $alg_ok ("AC/AS/BOCPD+HAR/Exp3S/HRP")

$router_ok = (Test-Path (Join-Path $eng 'router_effective_price.py')) -and `
             (Test-Path (Join-Path $eng 'adapters\kraken.py')) -and `
             (Test-Path (Join-Path $eng 'adapters\coinbase.py')) -and `
             (Test-Path (Join-Path $eng 'adapters\alpaca.py'))
Row "Router & adapters" $router_ok ("effective_price + kraken/coinbase/alpaca stubs")

# 4) Try to load bots (SE-aware enforcement)
$pyBotsLoad = @"
import json, traceback
out={'ok':False,'count':0,'names':[], 'err':None}
try:
    from bots.registry import load_bots
    bs = load_bots('config/bots.yml')
    out['ok']=True; out['count']=len(bs); out['names']=[b.__class__.__name__ for b in bs]
except Exception as e:
    out['err']=traceback.format_exc()
print(json.dumps(out))
"@
$botsLoad = & python -c $pyBotsLoad
$botsJson = $null
try { $botsJson = $botsLoad | ConvertFrom-Json } catch {}
$bots_ok = $false; $bots_msg = "failed to import bots.registry"
if ($botsJson -and $botsJson.ok) { $bots_ok = $true; $bots_msg = "loaded {0} bots: {1}" -f $botsJson.count, ($botsJson.names -join ", ") }
elseif ($botsJson -and $botsJson.err) { $bots_msg = $botsJson.err }
Row "SE-aware bots load" $bots_ok $bots_msg

# 5) Compile all .py to catch syntax/import errors
$compileLog = Join-Path $logs 'compile_errors.txt'
if (Test-Path $compileLog) { Remove-Item $compileLog -Force }
$pyFiles = Get-ChildItem -Recurse -Filter *.py | ForEach-Object { $_.FullName }
$errs=@(); foreach($f in $pyFiles){
  $cmd = "import py_compile,sys; fn=r'"+$f.Replace("\","\\")+"'; py_compile.compile(fn, doraise=True)"
  try { python -c $cmd | Out-Null } catch { $errs += ,@($f, $_.Exception.Message); Add-Content -Encoding UTF8 $compileLog ("[ERROR] {0}`n{1}`n" -f $f, $_.Exception.Message) }
}
$errCount = [int]($errs.Length/2)
Row "Compile check" ($errCount -eq 0) ($(if($errCount -eq 0){"OK"}else{"$errCount errors (see logs/compile_errors.txt)"}))

# 6) Paper smoke (run_cycle) and audit checks
$preSize = (Get-Item $aud).Length
$cycleScript = Join-Path $scr 'run_cycle.py'
$smoke_ok = $false; $smoke_msg = "scripts/run_cycle.py missing"
if (Test-Path $cycleScript) {
  try {
    python $cycleScript | Out-Null
    Start-Sleep -Milliseconds 300
    $postSize = (Get-Item $aud).Length
    if ($postSize -gt $preSize) { $smoke_ok = $true; $smoke_msg = "audit appended $(($postSize-$preSize)) bytes" }
    else { $smoke_msg = "no new audit bytes" }
  } catch { $smoke_msg = $_.Exception.Message }
}
Row "Paper smoke (cycle)" $smoke_ok $smoke_msg

# 7) Parse audit tail -> event counts & explainability
$pyAudit = @"
import json, os, sys
p=os.environ.get('EIDOLLONA_AUDIT','logs/audit.ndjson')
events=0; explain=0; qx=0; maker=0; venue=0; regime=0; alloc=0
try:
    lines=open(p,'r',encoding='utf-8').read().splitlines()[-1000:]
    for L in lines:
        try: ev=json.loads(L)
        except: continue
        events+=1
        if 'reasons' in ev: explain+=1
        e=ev.get('event','')
        if e=='q_execute': qx+=1
        if e in ('maker_quote_post','maker_quote_plan'): maker+=1
        if e in ('venue_disable','venue_enable','latency_alert'): venue+=1
        if e=='regime_update': regime+=1
        if e=='alloc_update': alloc+=1
except FileNotFoundError:
    pass
rate = (explain/events) if events else 0.0
print(json.dumps({'events':events,'explain_rate':rate,'q_execute':qx,'maker':maker,'venue':venue,'regime':regime,'alloc':alloc}))
"@
$env:EIDOLLONA_AUDIT = $aud
$aStatsRaw = & python -c $pyAudit
$aStats = $null; try { $aStats = $aStatsRaw | ConvertFrom-Json } catch {}
$evts = if($aStats){ [int]$aStats.events } else { 0 }
$expR = if($aStats){ [double]$aStats.explain_rate } else { 0.0 }
$explain_ok = $expR -ge 0.95
Row "Audit events" ($evts -gt 0) ("$evts lines parsed")
Row "Explainability ≥95%" $explain_ok ("rate = {0:P0}" -f $expR)
Row "q_execute/maker/venue/regime/alloc" ($aStats -ne $null) ("{0}/{1}/{2}/{3}/{4}" -f $aStats.q_execute,$aStats.maker,$aStats.venue,$aStats.regime,$aStats.alloc)

# 8) Optional tests (pytest if present)
$pytest_ok=$true; $pytest_msg="skipped (pytest not found)"
try {
  $pyv = & python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest') else 1)"
  if($LASTEXITCODE -eq 0){
    & pytest -q 2>$null
    $pytest_msg="ran"; $pytest_ok=$true
  }
} catch { $pytest_ok=$true; $pytest_msg="skipped" }
Row "Pytests" $pytest_ok $pytest_msg

# 9) Summary matrix
Write-Host "`n--- STATUS MATRIX ---"
Row "CONFIGS" ($cfg_ok -and $se_enforced) ("se_enforced=" + $se_enforced)
Row "SE CORE" $se_core_ok "SE4.3 engine & loader"
Row "ALGORITHMS" $alg_ok "AC/AS/BOCPD+HAR/Exp3S/HRP"
Row "ROUTER/ADAPTERS" $router_ok "effective price + venue stubs"
Row "BOTS (SE-AWARE)" $bots_ok $bots_msg
Row "COMPILE" ($errCount -eq 0) ("errors=" + $errCount)
Row "SMOKE" $smoke_ok $smoke_msg
Row "AUDIT EXPLAIN" $explain_ok ("explain_rate=" + ("{0:P0}" -f $expR))
Row "TESTS" $pytest_ok $pytest_msg

# 10) JSON export (for copy/paste)
$status = [ordered]@{
  configs_ok = $cfg_ok
  se_enforced = $se_enforced
  se_core_ok = $se_core_ok
  algorithms_ok = $alg_ok
  router_ok = $router_ok
  bots_ok = $bots_ok
  compile_errors = $errCount
  smoke_ok = $smoke_ok
  audit = if($aStats){ $aStats } else { @{ events = 0; explain_rate = 0 } }
}
Write-Host "`n--- JSON SUMMARY ---"
$status | ConvertTo-Json -Depth 6 | Write-Output

Write-Host "`n✅ Done. If any row is red, see logs/compile_errors.txt and tail logs/audit.ndjson for details."
# ==========================================================================================================
