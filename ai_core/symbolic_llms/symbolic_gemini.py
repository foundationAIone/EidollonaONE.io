"""
Minimal Google Gemini adapter (optional, governed use only).
Reads GEMINI_API_KEY from env and calls v1beta generateContent.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import os
import httpx


class GeminiAdapter:
    def __init__(
        self,
        *,
        model: str = "gemini-2.0-flash",
        endpoint_base: str = "https://generativelanguage.googleapis.com/v1beta",
    ):
        self.model = model
        self.endpoint_base = endpoint_base.rstrip("/")
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) is required for GeminiAdapter"
            )
        self._key = key

    def complete(
        self, user_text: str, *, system: Optional[str] = None, timeout_s: float = 12.0
    ) -> str:
        if not (user_text or "").strip():
            return ""
        endpoint = f"{self.endpoint_base}/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": ([{"text": system}] if system else [])
                    + [{"text": user_text}],
                }
            ]
        }
        try:
            with httpx.Client(timeout=timeout_s, base_url=self.endpoint_base) as client:
                r = client.post(
                    endpoint, headers=headers, params={"key": self._key}, json=payload
                )
                r.raise_for_status()
                data = r.json()
                # Extract the first candidate text
                cands = data.get("candidates") or []
                if cands:
                    cand = cands[0]
                    content = cand.get("content") or {}
                    parts = content.get("parts") or []
                    if parts and isinstance(parts, list):
                        return str((parts[0] or {}).get("text") or "").strip()
                return ""
        except Exception:
            return ""
