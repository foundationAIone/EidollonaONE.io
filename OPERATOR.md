# EidollonaONE SAFE Bring-up (SE4.3) — Wings/Aletheia

1. Run `pwsh scripts/eidolon_bringup.ps1` once to sync configs + modules.
2. Launch backend with `python scripts/serve_backend.py` (requires FastAPI + uvicorn).
3. HUD endpoint available at `http://127.0.0.1:8000/api/hud/signals`.
4. Audit log stored in `logs/audit.ndjson`; rollup via `python scripts/metrics/ndjson_rollup.py`.
5. AI Brain minimal ingest sample:

   ```python
   from ai_core.ai_brain import AIBrain
   brain = AIBrain()
   sample = {"alignment":0.92,"memory_integrity":0.88,"consent_delta":0.9,
             "risk_guard":0.87,"audit_fidelity":0.91,"sovereignty_ratio":0.9,
             "omega":0.04}
   snapshot = brain.ingest(sample)
   ```

6. Avatar/citadel configs live under `config/`.
