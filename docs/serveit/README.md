# Serve-it Module

Serve-it powers the local service marketplace: capturing requests, ranking providers, booking jobs, and issuing paper-mode payouts. This guide walks through the major pieces and safety rails.

## Core Files

- **API** (`serve_it_app/api.py`): Token-gated FastAPI routes for request creation, quotes, bookings, completion proofs, paper payouts, and HOA dashboards.
- **Services** (`serve_it_app/services.py`): Maintains state in `logs/serveit_state.json`, wraps business operations (request lifecycle, metrics, payouts), and emits NDJSON audits for every action.
- **Match Heuristics** (`serve_it_app/match.py`): Simple scoring stub combining skills, rating, and jobs-done counts. Swap with ML ranking later.
- **Compliance & Verification** (`serve_it_app/compliance.py`, `serve_it_app/verification.py`): Provide ToS/Privacy links, dispute policies, and placeholders for KYC/background checks.
- **Avatar Abilities** (`avatars/serveit/abilities.py`): Implements `explain_state`, `quote_task`, `accept_task`, and `payout_paper` abilities consumed by the orchestrator.

## Request → Quote → Book Flow

1. `/v1/serveit/request` stores a new request (lat/lon optional). Avatar helper `quote_task` auto-creates a receiver user if needed.
2. Providers are ranked via `match.rank_providers`; quotes recorded with `serveit_quote` audit events.
3. Booking via `/v1/serveit/book` locks a quote (`serveit_book` audit).
4. Completion `/v1/serveit/complete` records proof metadata and emits `serveit_complete`.
5. Payout `/v1/serveit/payout_paper` writes a paper stub and reuses Serplus paper ledger semantics via `serve_it_app.payouts.payout_paper_ser`.

## Sovereign Safeguards

- No fiat custody: payouts emit paper receipts only (`currency: SER-paper`).
- Disputes default to a 14-day window; capture before/after evidence in `serve_it_app/compliance.py`.
- Roles: when avatars create requests/quotes, helper functions automatically provision verified users/providers.
- Audit tags include `serveit_avatar_intent`, `serveit_request`, `serveit_quote`, `serveit_book`, `serveit_complete`, and `serveit_payout_paper`.

## Extending Serve-it

- Add more KPIs or charts by editing `services.dashboard()`.
- Integrate real ranking data by replacing `match.rank_providers` with a call out to your ML service.
- Hook in actual payouts (ACH, card) by swapping `payouts.payout_paper_ser` once compliance approves non-paper flows.
- Build HOA landing experiences through `/v1/serveit/hoa/{hoa_id}` and surface them inside the avatar dashboard or micro-frontends.
