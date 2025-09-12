"""
Minimal OpenAI-compatible GPT adapter (optional, governed use only).
Reads OPENAI_API_KEY from env. Designed to be called only when internet is authorized.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import os
import httpx


class GPTAdapter:
    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        endpoint: str = "https://api.openai.com/v1/chat/completions",
    ):
        self.model = model
        self.endpoint = endpoint
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for GPTAdapter")
        self._headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def complete(
        self, user_text: str, *, system: Optional[str] = None, timeout_s: float = 12.0
    ) -> str:
        if not (user_text or "").strip():
            return ""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_text})
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 200,
        }
        try:
            with httpx.Client(timeout=timeout_s) as client:
                r = client.post(self.endpoint, headers=self._headers, json=payload)
                r.raise_for_status()
                data = r.json()
                choice = (data.get("choices") or [{}])[0]
                msg = (choice.get("message") or {}).get("content") or ""
                return str(msg).strip()
        except Exception:
            return ""
