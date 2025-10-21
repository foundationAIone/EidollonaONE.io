# Quantum Probabilistic Information Rendering (QPIR)

SAFE, SE4.3-aligned probability and HUD rendering utilities for EidollonaONE.

## Quick start

```python
from quantum_probabilistic_information_rendering_system import hud_payload

payload = hud_payload()
print(payload["probability"]["p50"])  # deterministic percentile snapshot
```

The convenience helpers also expose the full snapshot object:

```python
from quantum_probabilistic_information_rendering_system import render_snapshot

snapshot = render_snapshot()
print(snapshot.signals["reality_alignment"])
```

## FastAPI integration

```python
from fastapi import FastAPI
from quantum_probabilistic_information_rendering_system import fastapi_router

app = FastAPI()
app.include_router(fastapi_router(), prefix="")  # /api/qpir/snapshot
```

## Auditing

Each snapshot emits an NDJSON record to the path specified by `$EIDOLLONA_AUDIT`
(or `logs/audit.ndjson` by default).  The payload contains the raw signals, ring
weights, percentile highlights, and human-readable reasons.

## Requirements

- Python 3.9+
- Symbolic Equation stack (SE4.3 preferred, SE4.1 fallback)
- Optional: `fastapi` for the router helper
