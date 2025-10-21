# Social Adapters

The social adapter layer keeps SAFE posture when forwarding community messages into the avatar orchestrator. It provides:

- Deterministic moderation (`social.moderation`) that blocks risky phrases and marks cautionary language.
- A bridge helper (`social.bridge`) that applies moderation, records audit events, and proxies requests to `/v1/avatar/{avatar_id}/intent` with token-gated access.
- Channel adapters (for example Telegram) that consume updates and call the bridge so every message shares the same safeguards.

## Running the Telegram adapter

1. Export the required environment variables:
   - `TELEGRAM_BOT_TOKEN`: Bot token from BotFather.
   - `ORCHESTRATOR_BASE`: Base URL for the avatar orchestrator (defaults to `http://127.0.0.1:8000`).
   - `ORCHESTRATOR_TOKEN`: SAFE token with analyzer visibility (defaults to `dev-token`).
   - `AVATAR_ID`: Target avatar identifier (`fancomp`, `serveit`, `trader`, etc.).
2. Start the SAFE backend (for example via the "Run Backend (SAFE)" task).
3. Launch the new VS Code task **Social: Telegram Bridge** or run `python -m social.telegram.adapter` manually.

The bridge writes NDJSON audit events (`social_moderation_block`, `social_bridge_forward`, and `social_bridge_error`) so the analyzer can track activity without relying on external logs.
