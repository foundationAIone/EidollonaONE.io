# ===================== EIDOLONALPHA+ — ETHOS ENHANCEMENTS (TRUST • PROOF • COMMUNITY) =====================
$ErrorActionPreference='Stop'
$root = Get-Location

# --- Paths ---
$cfg="$root\config"; $logs="$root\logs"; $docs="$root\docs"
$tre="$root\treasury"; $pub="$root\public\reports"; $anc="$root\anchors"
$web="$root\web_interface\server"; $scripts="$root\scripts"; $comm="$root\community\pods"; $tests="$root\tests"
New-Item -Force -ItemType Directory $cfg,$logs,$docs,$tre,$pub,$anc,$web,$scripts,$comm,$tests | Out-Null

# ===================== 1) ANTI-COERCION & PRIVACY POLICY =====================
Set-Content -Encoding UTF8 "$docs\ANTI_COERCION_POLICY.md" @"
# Anti-Coercion & Privacy Policy (EidollonaONE)

## Non-negotiables
- **Consent-first**: Participation is voluntary. No biometric mandates. No dark patterns. Revocable scopes at any time.
- **Minimal data**: We log only what we must for risk, audit integrity, and law. No third-party ad/analytics trackers.
- **No single off-switch**: Multi-venue routing + circuit breakers; switchover to **paper mode** on incidents; users informed via signed banner.
- **No leverage (early phases)**: Risk/trade ≤ 0.5% equity, order ≤ 1–2% equity, max daily loss ≤ 2.5%; kill-switch enforced.
- **Explainability**: ≥ 95–99% decisions include reasons; Court Yard transcripts on demand.

See also: docs/COMMUNITY_PODS.md, config/policies.yml
"@

Set-Content -Encoding UTF8 "$cfg\policies.yml" @"
version: 1
consent:
  biometric_required: false
  scopes:
    treasury: opt_in
    trading: opt_in
privacy:
  log_minimum: true
  external_trackers: false
operations:
  allow_leverage: false
  risk_per_trade_max: 0.005
  max_order_notional_pct: 0.02
  max_daily_loss_pct: 0.025
"@

# ===================== 2) VALUE TAGS (NINE STREAMS) =====================
Set-Content -Encoding UTF8 "$cfg\value_tags.yml" @"
version: 1
tags:
  - love_compassion
  - time_stewardship
  - service
  - creativity
  - earth_care
  - consciousness_grid
  - unity_commerce
  - clear_exchange
  - healing_energy
"@

# ===================== 3) PROOF-OF-RESERVES (RESERVES + ATTESTATION HASH) =====================
Set-Content -Encoding UTF8 "$cfg\reserves.yml" @"
version: 1
assets:
  - { symbol: USD_CASH_EQ, amount: 100000.00, custodian: 'Bank/PF', attestation: 'docs/CUSTODIAN_LETTER.txt' }
  - { symbol: XAU_PILOT,   amount: 5.000,     custodian: 'GoldVault', unit: 'troy_oz', attestation: 'docs/CUSTODIAN_LETTER.txt' }
settings:
  output: 'public/reports/reserves_latest.json'
"@

Set-Content -Encoding UTF8 "$tre\proof_of_reserves.py" @"
import os, json, yaml, hashlib, time
from pathlib import Path

def sha256_file(p: Path) -> str:
    if not p.exists(): return ''
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            h.update(chunk)
    return h.hexdigest()

def main(cfg_path='config/reserves.yml'):
    cfg=yaml.safe_load(open(cfg_path,'r',encoding='utf-8')) or {}
    out_path=Path(cfg.get('settings',{}).get('output','public/reports/reserves_latest.json'))
    data={'timestamp': time.time(), 'assets': [], 'totals': {}, 'attestations': []}
    totals={}
    for a in cfg.get('assets',[]):
        att=Path(a.get('attestation',''))
        rec=dict(a)
        rec['attestation_sha256']=sha256_file(att) if att else ''
        data['assets'].append(rec)
        sym=a.get('symbol','?'); amt=float(a.get('amount',0.0))
        totals[sym]=totals.get(sym,0.0)+amt
        if rec['attestation_sha256']:
            data['attestations'].append({'symbol':sym,'sha256':rec['attestation_sha256'],'file':str(att)})
    data['totals']=totals
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path,'w',encoding='utf-8') as f: json.dump(data,f,indent=2,ensure_ascii=False)
    print(json.dumps({'ok':True,'output':str(out_path),'assets':len(data['assets'])}))
if __name__=='__main__': main()
"@

# Stub attestation file (replace with real letter later)
if (!(Test-Path "$docs\CUSTODIAN_LETTER.txt")) {
  Set-Content -Encoding UTF8 "$docs\CUSTODIAN_LETTER.txt" "Custodian attestation placeholder — replace with signed letter or auditor report."
}

# ===================== 4) GRANT VAULTS (TAGGED DISBURSEMENTS + PUBLIC REPORT) =====================
Set-Content -Encoding UTF8 "$cfg\grants.yml" @"
version: 1
mode: paper               # live writes only when policy allows
vaults:
  - id: community_pilot
    description: Seed grants for earth_care + healing_energy pods
    disbursements:
      - { to: 'pod_alpha',  amount_usd: 500,  tags: [earth_care, unity_commerce],  reason: 'soil remediation pilot' }
      - { to: 'pod_beta',   amount_usd: 300,  tags: [healing_energy, love_compassion], reason: 'community care circle' }
settings:
  report: 'public/reports/grants_latest.json'
"@

Set-Content -Encoding UTF8 "$tre\grant_vaults.py" @"
import os, json, time, yaml
from pathlib import Path

def audit(ev, **kw):
    path=Path(os.environ.get('EIDOLLONA_AUDIT','logs/audit.ndjson'))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path,'a',encoding='utf-8') as f:
        f.write(json.dumps({'event':ev,**kw,'ts':time.time()},ensure_ascii=False)+'\n')

def main(cfg='config/grants.yml', tags_cfg='config/value_tags.yml'):
    c=yaml.safe_load(open(cfg,'r',encoding='utf-8')) or {}
    tags=yaml.safe_load(open(tags_cfg,'r',encoding='utf-8')) or {}
    allowed=set(tags.get('tags',[]))
    report=Path(c.get('settings',{}).get('report','public/reports/grants_latest.json'))
    mode=c.get('mode','paper'); out=[]
    by_tag={}
    for v in c.get('vaults',[]):
        vid=v.get('id'); desc=v.get('description','')
        for d in v.get('disbursements',[]):
            d_tags=[t for t in d.get('tags',[]) if t in allowed]
            rec={'vault':vid,'desc':desc,'to':d.get('to'),'amount_usd':float(d.get('amount_usd',0)),'tags':d_tags,'reason':d.get('reason')}
            out.append(rec)
            for t in d_tags: by_tag[t]=by_tag.get(t,0.0)+rec['amount_usd']
            # Paper-mode: only audit the plan
            audit('grant_disburse', decision=('ALLOW' if mode!='paper' else 'PAPER'), reasons=['se_ready','clear_exchange'], grant=rec, mode=mode)
    report.parent.mkdir(parents=True, exist_ok=True)
    with open(report,'w',encoding='utf-8') as f:
        json.dump({'ts':time.time(),'mode':mode,'items':out,'totals_by_tag':by_tag}, f, indent=2, ensure_ascii=False)
    print(json.dumps({'ok':True,'report':str(report),'items':len(out)}))

if __name__=='__main__': main()
"@

# ===================== 5) TAMPER-EVIDENT AUDIT ANCHORING (DAILY ROOT HASH) =====================
Set-Content -Encoding UTF8 "$scripts\audit_anchor.py" @"
import os, json, time, hashlib
from pathlib import Path
A=Path(os.environ.get('EIDOLLONA_AUDIT','logs/audit.ndjson'))
C=Path('logs/audit.chain')
D=Path('anchors')
def sha256(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def chain():
    if not A.exists(): return ''
    prev=b''
    with open(A,'rb') as f:
        for line in f:
            prev=hashlib.sha256(prev + line.rstrip(b'\n')).digest()
    return prev.hex()
def main():
    D.mkdir(parents=True, exist_ok=True)
    root=chain(); ts=time.time()
    out={'root_sha256':root,'ts':ts,'file':str(A)}
    fn=D/f'anchor_{time.strftime("%Y%m%d",time.gmtime(ts))}.json'
    with open(fn,'w',encoding='utf-8') as f: json.dump(out,f,indent=2,ensure_ascii=False)
    print(json.dumps({'ok':True,'anchor':str(fn),'root':root}))
if __name__=='__main__': main()
"@

# ===================== 6) INCIDENT COMMS BANNER (SIGNED STATUS) =====================
Set-Content -Encoding UTF8 "$cfg\status_banner.yml" @"
enabled: false
message: ""
mode_hint: paper    # paper | live
"@

Set-Content -Encoding UTF8 "$web\status_api.py" @"
from fastapi import APIRouter
import os, json, hmac, hashlib, yaml
router = APIRouter()

def sign(msg:str)->str:
    key=os.environ.get('EID_STATUS_SIGNING_KEY','')
    return hmac.new(key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest() if key else ''

@router.get('/api/status')
def status():
    cfg=yaml.safe_load(open('config/status_banner.yml','r',encoding='utf-8')) or {}
    pol=yaml.safe_load(open('config/trading_policy_crypto.yml','r',encoding='utf-8')) or {}
    mode=(cfg.get('mode_hint') or pol.get('mode') or 'paper')
    msg=str(cfg.get('message','') or '')
    enabled=bool(cfg.get('enabled',False))
    sig=sign(msg if enabled else 'disabled')
    return {'enabled':enabled,'message':msg,'mode':mode,'signature':sig}
"@

Set-Content -Encoding UTF8 "$scripts\set_status_banner.py" @"
import sys, yaml
cfg='config/status_banner.yml'
d=yaml.safe_load(open(cfg,'r',encoding='utf-8')) or {}
if len(sys.argv)>=2:
    d['enabled']=True; d['message']=' '.join(sys.argv[1:]); d.setdefault('mode_hint','paper')
else:
    d['enabled']=False; d['message']=''
yaml.safe_dump(d, open(cfg,'w',encoding='utf-8'))
print(d)
"@

# ===================== 7) COMMUNITY PODS (TEMPLATES) =====================
Set-Content -Encoding UTF8 "$docs\COMMUNITY_PODS.md" @"
# Community Pods / Time-Bank Templates

- **Goal**: small, transparent, consent-first exchange circles (skills, time, micro-grants).
- **Principles**: transparency, goodwill, mutual upliftment, opt-in privacy.
- **How**: start from templates in community/pods/. Tag flows with value_tags; publish simple monthly rollups.

"@

Set-Content -Encoding UTF8 "$comm\timebank_pod.yml" @"
pod_id: timebank_alpha
members:
  - { id: alice, skills: [design, healing], hours_bank: 5 }
  - { id: bob,   skills: [repairs, transport], hours_bank: 3 }
exchanges:
  - { from: alice, to: bob,   hours: 1, note: 'design consult' }
  - { from: bob,   to: alice, hours: 1, note: 'bike tune' }
policies:
  privacy_min_logs: true
  publish_monthly_rollup: true
"@

Set-Content -Encoding UTF8 "$comm\unity_pod.yml" @"
pod_id: unity_alpha
purpose: 'earth_care + healing_energy pilot'
grants:
  - { to: seed_garden, amount_usd: 250, tags: [earth_care, unity_commerce], reason: 'soil remediation' }
  - { to: care_circle, amount_usd: 150, tags: [healing_energy, love_compassion], reason: 'community care' }
"@

# ===================== 8) OPTIONAL TESTS (LIGHTWEIGHT) =====================
Set-Content -Encoding UTF8 "$tests\test_policies_present.py" @"
from pathlib import Path
def test_policy_files_present():
    assert Path('config/policies.yml').exists()
    assert Path('docs/ANTI_COERCION_POLICY.md').exists()
    assert Path('config/value_tags.yml').exists()
"@

# ===================== 9) RUN ENHANCEMENT SCRIPTS (PAPER SAFE) =====================
$env:EIDOLLONA_AUDIT = 'logs\audit.ndjson'
# Proof-of-Reserves report
python "$tre\proof_of_reserves.py" | Write-Host
# Grant vault rollup (paper)
python "$tre\grant_vaults.py" | Write-Host
# Anchor today’s audit file
python "$scripts\audit_anchor.py" | Write-Host
# Set a sample status banner (clear with no args)
python "$scripts\set_status_banner.py" "Paper cycle healthy • KPIs steady" | Write-Host

Write-Host "`n=== Enhancement Outputs ==="
Write-Host ("• Proof-of-Reserves:   " + (Resolve-Path 'public/reports/reserves_latest.json'))
Write-Host ("• Grants report:       " + (Resolve-Path 'public/reports/grants_latest.json'))
Write-Host ("• Audit anchor (today):" + (Resolve-Path (Join-Path $anc ('anchor_{0}.json' -f (Get-Date -UFormat %Y%m%d)))))
Write-Host ("• Status banner cfg:   " + (Resolve-Path 'config/status_banner.yml'))
Write-Host "• Policies + tags installed. Community pods templates ready."

Write-Host "`n✅ Done. Next:"
Write-Host "  1) Mount status API router in your FastAPI app: app.include_router(status_api.router)"
Write-Host "  2) Publish reserves/grants reports (public/reports/*) and anchors/ for tamper-evidence."
Write-Host "  3) Replace docs/CUSTODIAN_LETTER.txt with a real attestation and re-run proof_of_reserves.py."
Write-Host "  4) Keep mode=paper; verify explainability stays 1.0; then consider micro-live promotion rules."
# ==========================================================================================================
