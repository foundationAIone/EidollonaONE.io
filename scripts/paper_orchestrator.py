import os, sys, json, time, urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

# --- audit fallback ---
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

# --- readiness helper fallback ---
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

BASE  = os.environ.get("ALPHATAP_BASE","http://127.0.0.1:8787")
TOKEN = os.environ.get("ALPHATAP_TOKEN","change-me-now")
EVAL  = f"{BASE}/v1/se41/eval?token={TOKEN}"
CYCLES= int(os.environ.get("CYCLES","5"))
DELAY = float(os.environ.get("DELAY","2.0"))

def http_get(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent":"AlphaTap/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

allow=review=hold=0
for i in range(1, CYCLES+1):
    try:
        sig = http_get(EVAL)
        c=float(sig.get("coherence",0)); I=float(sig.get("impetus",0)); r=float(sig.get("risk",1))
        readiness = classify_readiness(c,I)
        if c>=0.75 and r<=0.20:
            gate="ALLOW"; action="paper-exec: simulate order + ledger noop"
            allow+=1
        elif c>=0.60 and r<=0.35:
            gate="REVIEW"; action="paper-review: no orders"
            review+=1
        else:
            gate="HOLD"; action="noop"
            hold+=1
        event={"cycle":i,"ts":time.time(),"readiness":readiness,"gate":gate,"action":action,"signals":sig}
        audit_ndjson("paper_tick", **event)
        print(json.dumps({"cycle":i,"readiness":readiness,"gate":gate}, separators=(",",":")))
        time.sleep(DELAY)
    except Exception as e:
        audit_ndjson("paper_tick_error", cycle=i, error=str(e))
        print(json.dumps({"cycle":i,"error":str(e)}))
        break

summary={"allow":allow,"review":review,"hold":hold,"cycles":i}
audit_ndjson("paper_summary", **summary)
print(json.dumps({"summary":summary}, indent=2))
