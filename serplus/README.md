# Serplus Currency Stack

The Serplus package provides a SAFE-friendly currency sandbox built around an append-only NDJSON ledger. It supports:

- Account registry with lightweight metadata.
- Mint, burn, and transfer flows for the Serplus (`SER`) asset, including supply-cap enforcement.
- Companion CompCoin (`COMP`) helpers that reuse the same ledger.
- Allocation utilities for planning distributions and monitoring holder concentration.
- A simple NFT registry for paper collectibles tied to ledger activity.
- FastAPI routes mounted under `/v1/ser` (see `serplus/api/routes.py`).

## Data directory

All files live under the directory pointed to `SERPLUS_DATA_DIR` (defaults to `logs/`). The ledger (`serplus_ledger.ndjson`), account registry, and NFT registry files are created on demand.

## Quick start

```python
from serplus import ser_mint, ser_transfer, ser_burn

ser_mint(to="treasury", amount=1_000, actor="programmerONE")
ser_transfer(source="treasury", target="community", amount=120, actor="treasury")
ser_burn(account="community", amount=10, actor="community")
```

Audit entries are written to `logs/audit.ndjson` for every state mutation, and the FastAPI router exposes read/write endpoints secured by the existing token gate.
