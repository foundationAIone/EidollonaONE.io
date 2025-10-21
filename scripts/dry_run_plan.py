import os, sys, json, time, urllib.request
# Ensure repo root is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

# Safe imports with fallbacks
try:
    from utils.audit import audit_ndjson
except Exception:
    def audit_ndjson(event, **payload):
        try:
            os.makedirs(os.path.join(ROOT,"logs"), exist_ok=True)
            with open(os.path.join(ROOT,"logs","audit.ndjson"),"a",encoding="utf-8") as f:
                f.write(json.dumps({"ts":time.time(),"event":event,**payload})+"\n")
        except Exception:
            pass

try:
    from symbolic_core.symbolic_equation import classify_readiness
except Exception:
    def _clamp01(x): 
        try: x=float(x)
        except Exception: return 0.0
        return 0.0 if x<0 else (1.0 if x>1 else x)
    def classify_readiness(c,I):
        c=_clamp01(c); I=_clamp01(I)
        return "prime_ready" if (c>=0.85 and I>=0.50) else ("ready" if c>=0.75 else ("warming" if c>=0.60 else "baseline"))

BASE = os.environ.get("ALPHATAP_BASE","http://127.0.0.1:8787")
TOKEN= os.environ.get("ALPHATAP_TOKEN","change-me-now")
EVAL = f"{BASE}/v1/se41/eval?token={TOKEN}"

def http_get(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))

sig = http_get(EVAL)
coh = float(sig.get("coherence",0.0))
imp = float(sig.get("impetus",0.0))
risk= float(sig.get("risk",1.0))
ready = classify_readiness(coh, imp)

# SAFE gate (paper-mode)
effective_risk = risk
if coh >= 0.75 and effective_risk <= 0.20:
    gate = "ALLOW"
elif coh >= 0.60 and effective_risk <= 0.35:
    gate = "REVIEW"
else:
    gate = "HOLD"

audit_ndjson("plan_dry_run", readiness=ready, gate=gate, signals=sig)
print(json.dumps({"readiness": ready, "gate": gate, "signals": sig}, indent=2))
