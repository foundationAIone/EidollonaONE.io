from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from social.bridge import BridgeConfig, proxy_intent

API_TIMEOUT = 10
POLL_INTERVAL = 2.5


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value else None


def _telegram_api(bot_token: str, method: str, **params: object) -> Dict[str, Any]:
    normalized_params = {key: value if isinstance(value, (str, bytes)) else str(value) for key, value in params.items()}
    query = urlencode(normalized_params)
    url = f"https://api.telegram.org/bot{bot_token}/{method}?{query}"
    req = Request(url)
    with urlopen(req, timeout=API_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_orchestrator(config: BridgeConfig, chat_id: str, text: str) -> Optional[str]:
    result = proxy_intent(config, text=text, session_id=f"telegram_{chat_id}")
    speech = result.speech()
    if not result.ok:
        if result.moderated:
            return speech or "I'm keeping things safe and can't process that."
        return speech or f"Orchestrator error: {result.error or 'unavailable'}"
    if result.moderated and speech:
        return f"[caution] {speech}"
    if speech:
        return speech
    if isinstance(result.response, dict):
        return json.dumps(result.response)
    return None


def main() -> int:
    bot_token = _env("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN env var required.")
        return 1

    avatar_id = os.getenv("AVATAR_ID", "fancomp")
    orchestrator_base = _env("ORCHESTRATOR_BASE") or "http://127.0.0.1:8000"
    orchestrator_token = _env("ORCHESTRATOR_TOKEN") or "dev-token"
    bridge_config = BridgeConfig(
        base_url=orchestrator_base,
        token=orchestrator_token,
        avatar_id=avatar_id,
        session_prefix="telegram",
        timeout=API_TIMEOUT,
    )

    offset = 0
    print(f"Telegram adapter ready. Proxying to {orchestrator_base} as avatar '{avatar_id}'. Press Ctrl+C to exit.")

    while True:
        try:
            updates = _telegram_api(bot_token, "getUpdates", timeout=int(API_TIMEOUT), offset=offset)
        except URLError as exc:
            print(f"Telegram poll failed: {exc}")
            time.sleep(POLL_INTERVAL)
            continue

        for update in updates.get("result", []):
            offset = max(offset, int(update.get("update_id", 0)) + 1)
            message = update.get("message") or {}
            chat = message.get("chat") or {}
            chat_id = str(chat.get("id"))
            text = message.get("text")
            if not text:
                continue
            response_text = _call_orchestrator(bridge_config, chat_id, text)
            if response_text:
                send_payload = {
                    "chat_id": chat_id,
                    "text": response_text,
                }
                try:
                    _telegram_api(bot_token, "sendMessage", **send_payload)
                except URLError as exc:
                    print(f"Telegram send failed: {exc}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
