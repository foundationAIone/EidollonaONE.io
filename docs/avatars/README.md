# Avatar Layer Overview

This document explains how the multi-avatar layer is structured, how to extend it with new personas, and what sovereignty safeguards are in place.

## Architecture

- **Avatar Orchestrator** (`avatars/orchestrator/api.py`): FastAPI router mounted under `/v1/avatar/*`. It token-gates every interaction, writes NDJSON audit events, and loads module adapters lazily.
- **Module Abilities** (`avatars/<module>/abilities.py`): Each module implements `get_module_adapter()` returning handlers for intents, state snapshots, dashboards, and optional streams.
- **Persona Metadata** (`avatars/<module>/persona.json`): Declares avatar name, tone, and sovereign channel flags (attention/economy/pqre/trading).
- **Micro-frontend** (`web_interface/static/webview/avatars/runner.html` + `js/avatar_runner.js`): Shared VRM runner with dashboard frame and action controls. Query parameters:
  - `id` (default `fancomp`)
  - `token` (default `dev-token`)
  - `base` (API origin, defaults to same host)
  - `vrmUrl` optional VRM asset

## Sovereignty & Safety

- Gate tokens validated via `security.deps.require_token`.
- Every action audited (`avatar_intent`, `avatar_state_read`, module-specific events like `fancomp_avatar_intent`).
- Persona channel flags enforce SE41 constraints in front-end expression routing (trading channel stays off).
- Uploads routed through `fancompfoundation.services.ingest_content`; files land in `ip_vault/` with SHA-256 hash.
- Serve-it payouts emit paper-mode receipts only; no fiat custody.

## Adding a New Avatar

1. Create `avatars/<module>/persona.json` with name, tone, and channel toggles.
2. Implement `avatars/<module>/abilities.py` exposing `get_module_adapter()`.
3. Provide service APIs under `<module>/api.py` and mount them in `bridge/alpha_tap.py`.
4. Update docs/tests and optionally extend the front-end action list in `avatar_runner.js`.

## Social Adapters

- `social/telegram/adapter.py` proxies Telegram chats to the orchestrator. Supply `TELEGRAM_BOT_TOKEN`, `ORCHESTRATOR_BASE`, and `ORCHESTRATOR_TOKEN` environment variables before running.
- Additional adapters (Discord, YouTube) can follow the same pattern: poll platform API → POST to `/v1/avatar/{id}/intent` → relay the speech response.

## Development Notes

- Run the AlphaTap API, then open `http://127.0.0.1:7860/static/webview/avatars/runner.html?id=fancomp` for FanComp, or `...id=serveit` for Serve-it.
- Tests covering FanComp pools and Serve-it flows live in `tests/test_fancomp_pool.py` and `tests/test_serveit_flow.py`.
- All code is Python 3.9 compatible and idempotent; state is stored in `logs/*.json` for easy inspection.
