"""Performance Smoke Script (Phase 1)

Outputs JSON with:
  - encryption_chacha_ops_per_sec (approx)
  - encryption_payload_size
  - symbolic_eval_latency_ms (if symbolic_core available)
  - timestamp

Lightweight, no external deps beyond stdlib & existing project modules.
"""

from __future__ import annotations
import json
import time
import statistics
import os
import sys
from datetime import datetime

# Encryption performance
try:
    from connection.encryption_layer import EncryptionLayer
except Exception:
    EncryptionLayer = None  # type: ignore

# Symbolic equation (optional)
try:
    from symbolic_core.symbolic_equation import SymbolicEquation
except Exception:
    SymbolicEquation = None  # type: ignore

RESULT = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "encryption_chacha_ops_per_sec": None,
    "encryption_payload_size": 256,
    "symbolic_eval_latency_ms": None,
}

# Encryption benchmark
if EncryptionLayer:
    enc = EncryptionLayer()
    kid = enc.create_encryption_key()
    key = enc.encryption_keys[kid]
    payload = os.urandom(RESULT["encryption_payload_size"])
    # Warmup
    for _ in range(10):
        ed_w = enc.encryption_engine.encrypt_data(payload, key, compression=False)
        enc.encryption_engine.decrypt_data(ed_w, key)
    iters = 200
    times = []
    for _ in range(iters):
        t0 = time.perf_counter()
        ed = enc.encryption_engine.encrypt_data(payload, key, compression=False)
        enc.encryption_engine.decrypt_data(ed, key)
        times.append(time.perf_counter() - t0)
    if times:
        median = statistics.median(times)
        if median > 0:
            RESULT["encryption_chacha_ops_per_sec"] = round(1.0 / median, 2)

# Symbolic evaluation latency
if SymbolicEquation:
    try:
        se = SymbolicEquation()
        t0 = time.perf_counter()
        se.evaluate({"risk_hint": 0.4, "uncertainty_hint": 0.3, "coherence_hint": 0.6})
        RESULT["symbolic_eval_latency_ms"] = round(
            (time.perf_counter() - t0) * 1000.0, 3
        )
    except Exception:
        pass

print(json.dumps(RESULT, indent=2))

# Optional regression comparison (non-fatal warnings)
base_path = os.path.join(os.path.dirname(__file__), "perf_baseline.json")
try:
    if os.path.exists(base_path):
        with open(base_path, "r", encoding="utf-8") as fh:
            base = json.load(fh)
        warn = []
        cur_enc = RESULT.get("encryption_chacha_ops_per_sec")
        base_enc = base.get("encryption_chacha_ops_per_sec")
        if base_enc and cur_enc and cur_enc < base_enc * 0.75:
            warn.append(
                f"enc_ops_sec regression: {cur_enc:.0f} < {base_enc:.0f} * 0.75"
            )
        cur_sym = RESULT.get("symbolic_eval_latency_ms")
        base_sym = base.get("symbolic_eval_latency_ms")
        if base_sym and cur_sym and cur_sym > base_sym * 1.5:
            warn.append(f"se41_eval_ms slower: {cur_sym:.2f} > {base_sym:.2f} * 1.5")
        if warn:
            print("PERF WARNING: " + "; ".join(warn), file=sys.stderr)
except Exception as e:  # non-fatal
    print(f"perf regression check error: {e}", file=sys.stderr)
