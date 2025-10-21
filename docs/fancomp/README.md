# FanComp Foundation Module

FanComp handles creator uploads, the IP vault, affiliate tracking, and paper-mode reward pools. This document summarizes the flows and compliance guardrails.

## Key Components

- **API** (`fancompfoundation/api.py`): Token-gated endpoints for artist creation, content uploads, paper purchases, pool draws, and affiliate analytics.
- **Services** (`fancompfoundation/services.py`): Stores state under `logs/fancomp_state.json`, manages SHA-256 hashes for IP uploads in `ip_vault/`, tracks pool balances, and emits NDJSON audits.
- **Compliance** (`fancompfoundation/compliance.py`): Sweepstakes are OFF by default. Call `enable_sweepstakes(True)` only after publishing official rules and verifying jurisdiction controls.
- **Avatar Abilities** (`avatars/fancomp/abilities.py`): Implements `explain_state`, `upload_ip`, and `join_pool`, returning dashboard widgets and plain-language speech.

## Upload & Vault Flow

1. Avatar or API call POSTs `/v1/fancomp/content/upload` with metadata and optional file.
2. File stored under `ip_vault/` with SHA-256 hash; metadata recorded in the state ledger.
3. Audit entry `fancomp_upload_ip` recorded with hash + artist ID.
4. Avatar can immediately explain current state (`explain_state`) and show updated dashboard widgets.

## Paper Money Pool

- Pools attach to content when `percent_alloc > 0` at upload time. Balances accrue on every paper purchase (`fancomp_purchase_paper`).
- Pool draws are blocked until `sweepstakes_enabled()` returns `True`. Tests provide a context where compliance is temporarily enabled.
- Draws output winners, seed, and status (`paper_pending`) for audit trails.

## Affiliate Tracking

- Affiliates created via `/v1/fancomp/affiliate/create`; each purchase updates click/conversion counters and emits `fancomp_affiliate_create` and `fancomp_purchase_paper` entries.
- `/v1/fancomp/affiliate/{code}/stats` returns aggregated metrics for dashboards or persona explanations.

## Operational Checklist

- Provide official sweepstakes rules and jurisdiction gating before enabling draws.
- Keep `ip_vault/` backed up and monitor for duplicate hashes.
- Ensure audit log ingestion covers `fancomp_avatar_intent`, `fancomp_pool_draw`, `fancomp_affiliate_create`, etc.
- Extend `services.dashboard()` to surface any new KPIs you need in the avatar UI.
