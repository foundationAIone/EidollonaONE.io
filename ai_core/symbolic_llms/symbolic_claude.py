"""
Minimal Anthropic Claude adapter (optional, governed use only).
Reads ANTHROPIC_API_KEY from env and calls /v1/messages.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import os
import httpx


class ClaudeAdapter:
    def __init__(
        self,
        *,
        model: str = "claude-3-5-sonnet-latest",
        endpoint: str = "https://api.anthropic.com/v1/messages",
    ):
        self.model = model
        self.endpoint = endpoint
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for ClaudeAdapter")
        self._headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def complete(
        self, user_text: str, *, system: Optional[str] = None, timeout_s: float = 12.0
    ) -> str:
        if not (user_text or "").strip():
            return ""
        messages = [{"role": "user", "content": user_text}]
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.7,
        }
        if system:
            payload["system"] = system
        try:
            with httpx.Client(timeout=timeout_s) as client:
                r = client.post(self.endpoint, headers=self._headers, json=payload)
                r.raise_for_status()
                data = r.json()
                # Anthropic messages responses: data["content"][0]["text"]
                content = data.get("content") or []
                if content and isinstance(content, list):
                    part = content[0]
                    if isinstance(part, dict):
                        return str(part.get("text") or "").strip()
                return ""
        except Exception:
            return ""
