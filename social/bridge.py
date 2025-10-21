from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from utils.audit import audit_ndjson

from .moderation import ModerationVerdict, moderate, redact

__all__ = ["BridgeConfig", "BridgeResult", "proxy_intent"]


@dataclass(frozen=True)
class BridgeConfig:
    base_url: str
    token: str
    avatar_id: str
    session_prefix: str = "social"
    timeout: float = 10.0


@dataclass(frozen=True)
class BridgeResult:
    ok: bool
    response: Dict[str, Any]
    verdict: ModerationVerdict
    error: Optional[str] = None
    moderated: bool = False

    def speech(self) -> Optional[str]:
        speech = self.response.get("speech") if isinstance(self.response, dict) else None
        return str(speech) if speech is not None else None


def _open(request: Request, *, timeout: float):
    return urlopen(request, timeout=timeout)


def _safe_session_id(config: BridgeConfig, session_id: Optional[str]) -> str:
    if session_id:
        return session_id
    stamp = int(time.time() * 1000)
    return f"{config.session_prefix}_{stamp}"


def proxy_intent(
    config: BridgeConfig,
    *,
    text: Optional[str],
    session_id: Optional[str] = None,
    intent: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
    opener: Optional[Callable[[Request], Any]] = None,
) -> BridgeResult:
    verdict = moderate(text)
    if not verdict.allowed:
        fallback = {
            "speech": "I'm staying cautious and can't help with that request.",
            "moderation": verdict.to_dict(),
        }
        audit_ndjson(
            "social_moderation_block",
            avatar_id=config.avatar_id,
            reason=verdict.reason,
            actions=verdict.actions,
            sample=redact(text or ""),
        )
        return BridgeResult(ok=False, response=fallback, verdict=verdict, error=verdict.reason, moderated=True)

    payload: Dict[str, Any] = {
        "session_id": _safe_session_id(config, session_id),
        "text": text,
        "args": args or {},
    }
    if intent:
        payload["intent"] = intent

    effective_opener: Callable[[Request], Any]
    if opener is not None:
        effective_opener = opener
    else:
        def _default_opener(request_obj: Request) -> Any:
            return _open(request_obj, timeout=config.timeout)

        effective_opener = _default_opener

    endpoint = f"{config.base_url.rstrip('/')}/v1/avatar/{config.avatar_id}/intent?{urlencode({'token': config.token})}"
    request = Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})

    try:
        with effective_opener(request) as resp:
            raw = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    body: Dict[str, Any] = parsed
                else:
                    body = {"speech": str(parsed)}
            except json.JSONDecodeError:
                body = {"speech": raw}
    except URLError as exc:
        fallback = {
            "speech": "The avatar service is momentarily unavailable. Please try again soon.",
            "error": str(exc.reason if hasattr(exc, "reason") else exc),
        }
        audit_ndjson(
            "social_bridge_error",
            avatar_id=config.avatar_id,
            error=str(exc),
            sample=redact(text or ""),
        )
        return BridgeResult(ok=False, response=fallback, verdict=verdict, error=str(exc), moderated=False)

    audit_ndjson(
        "social_bridge_forward",
        avatar_id=config.avatar_id,
        sample=redact(text or ""),
        intent=payload.get("intent"),
    )
    moderated = "caution" in verdict.actions
    if moderated:
        body.setdefault("moderation", verdict.to_dict())
    return BridgeResult(ok=True, response=body, verdict=verdict, moderated=moderated)
