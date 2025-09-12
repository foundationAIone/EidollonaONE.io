"""SymbolicBlender (Governance + Multi-LLM Orchestrator)

What
----
Blends heuristic engine output, ELIZA (offline), and optionally governed
cloud LLM adapters (GPT / Claude / Gemini) with:
 - Deterministic caching (idempotent for same prompt+policy hash)
 - Governance gating (SE41 optional hook) & safety filters
 - Provider fallback with graceful degradation & jitter ordering
 - Adaptive confidence scoring & provenance metadata
 - Optional streaming token callback (for UI realtime updates)

Why
---
1. Ensures offline-safe default (ELIZA/heuristic) when cloud LLMs disabled.
2. Auditable decision path with structured trace metadata.
3. Minimizes latency by short‑circuiting if high confidence heuristic.
4. Caching reduces redundant API calls & saves quota.
5. Supports pluggable safety filters without coupling to any one provider.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Iterable, Callable, Tuple
import os
import random
import hashlib
import time

try:  # optional governance imports
    from symbolic_core.se41_context import assemble_se41_context  # type: ignore
    from trading.helpers.se41_trading_gate import se41_numeric, ethos_decision  # type: ignore
except Exception:  # pragma: no cover

    def assemble_se41_context(**kw):
        return kw

    def se41_numeric(**kw):
        return 0.6

    def ethos_decision(_):
        return {"decision": "allow"}


try:
    from .eliza_agent import ElizaAgent
except Exception:
    ElizaAgent = None  # type: ignore

try:
    # Optional GPT adapter (uses OpenAI-compatible HTTP API). Kept optional for SAFE mode.
    from .symbolic_gpt import GPTAdapter  # type: ignore
except Exception:
    GPTAdapter = None  # type: ignore

try:
    from .symbolic_claude import ClaudeAdapter  # type: ignore
except Exception:
    ClaudeAdapter = None  # type: ignore

try:
    from .symbolic_gemini import GeminiAdapter  # type: ignore
except Exception:
    GeminiAdapter = None  # type: ignore


class SymbolicBlender:
    def __init__(
        self,
        *,
        cache_size: int = 256,
        safety_filters: Optional[Iterable[Callable[[str], Optional[str]]]] = None,
    ):
        self.use_eliza = True
        self.use_llms = bool(os.getenv("EIDOLLONA_ALLOW_LLM", "0") == "1")
        self.agents: Dict[str, Any] = {}
        if ElizaAgent is not None:
            self.agents["eliza"] = ElizaAgent()
        # Initialize optional adapters lazily
        self.agents["gpt"] = None
        self.agents["claude"] = None
        self.agents["gemini"] = None
        for prov, adapter_cls, env_key, model_env, default_model in [
            ("gpt", GPTAdapter, "OPENAI_API_KEY", "EIDOLLONA_GPT_MODEL", "gpt-4o-mini"),
            (
                "claude",
                ClaudeAdapter,
                "ANTHROPIC_API_KEY",
                "EIDOLLONA_CLAUDE_MODEL",
                "claude-3-5-sonnet-latest",
            ),
            (
                "gemini",
                GeminiAdapter,
                "GEMINI_API_KEY",
                "EIDOLLONA_GEMINI_MODEL",
                "gemini-2.0-flash",
            ),
        ]:
            try:
                if adapter_cls is not None and (
                    os.getenv(env_key)
                    or (prov == "gemini" and os.getenv("GOOGLE_API_KEY"))
                ):
                    model = os.getenv(model_env, default_model)
                    self.agents[prov] = adapter_cls(model=model)  # type: ignore
            except Exception:
                self.agents[prov] = None
        self.order = [
            s.strip()
            for s in os.getenv("EIDOLLONA_LLM_ORDER", "gpt,claude,gemini").split(",")
            if s.strip()
        ]
        self.cache_size = cache_size
        self._cache: Dict[str, Tuple[float, str, Dict[str, Any]]] = {}
        self._cache_keys: list[str] = []
        self.safety_filters = list(safety_filters or [])

    # ---------------- Internal Utilities -----------------
    def _make_key(
        self, user_text: str, heuristic: Optional[str], policy: Dict[str, Any]
    ) -> str:
        h = hashlib.sha256()
        h.update(user_text.encode("utf-8"))
        if heuristic:
            h.update(heuristic.encode("utf-8"))
        h.update(repr(sorted(policy.items())).encode("utf-8"))
        return h.hexdigest()

    def _cache_get(self, key: str) -> Optional[Tuple[float, str, Dict[str, Any]]]:
        return self._cache.get(key)

    def _cache_put(self, key: str, text: str, meta: Dict[str, Any]) -> None:
        if key not in self._cache:
            if len(self._cache_keys) >= self.cache_size:
                oldest = self._cache_keys.pop(0)
                self._cache.pop(oldest, None)
            self._cache_keys.append(key)
        self._cache[key] = (time.time(), text, meta)

    def _apply_safety(self, text: str) -> str:
        for filt in self.safety_filters:
            try:
                replacement = filt(text)
                if replacement is not None:
                    text = replacement
            except Exception:
                continue
        return text

    def respond(
        self,
        *,
        user_text: str,
        heuristic_text: Optional[str] = None,
        last_bot: Optional[str] = None,
        allow_online: bool = False,
        allowed_hosts: Optional[Iterable[str]] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        policy_meta: Optional[Dict[str, Any]] = None,
        require_score: float = 0.0,
    ) -> str:
        """Return a blended response.

        Parameters
        ----------
        user_text: prompt from user
        heuristic_text: high-confidence internal suggestion
        allow_online: explicit caller authorization for cloud LLM usage
        stream_callback: optional token/segment callback for UI streaming
        policy_meta: additional metadata hashed into cache key
        require_score: minimum governance score threshold (0..1) to allow cloud usage
        """
        policy_meta = policy_meta or {}
        # Governance score (optional) — simple placeholder using coherence surrogate
        se_ctx = assemble_se41_context(**policy_meta)
        score = _clamp(
            se41_numeric(
                M_t=policy_meta.get("coherence", 0.75),
                DNA_states=[0.5],
                harmonic_patterns=[0.5],
            )
        )
        gate = ethos_decision({"scope": "symbolic_llms", "score": score})
        if isinstance(gate, dict) and gate.get("decision") == "deny":
            allow_online = False
        if score < require_score:
            allow_online = False

        cache_key = self._make_key(
            user_text, heuristic_text, {"allow_online": allow_online, **policy_meta}
        )
        cached = self._cache_get(cache_key)
        if cached:
            return cached[1]
        # 1) If heuristic is strong and not a mirror, prefer it.
        if heuristic_text and heuristic_text.strip():
            ht = heuristic_text.strip()
            if not last_bot or ht.lower() not in (last_bot or "").lower():
                safe_ht = self._apply_safety(ht)
                self._cache_put(cache_key, safe_ht, {"source": "heuristic"})
                return safe_ht
        # 2) Try ELIZA (offline) for a conversational nudge
        if self.use_eliza and self.agents.get("eliza"):
            try:
                r = self.agents["eliza"].reply(user_text)
                if r and r.strip():
                    r2 = self._apply_safety(r.strip())
                    self._cache_put(cache_key, r2, {"source": "eliza"})
                    return r2
            except Exception:
                pass
        # 3) If allowed and configured, try an online LLM (governed)
        if self.use_llms and allow_online:
            hosts = set(h.lower() for h in (allowed_hosts or []))
            # jitter reorder to reduce fingerprinting
            prov_order = self.order[:]
            random.shuffle(prov_order)
            for provider in prov_order:
                try:
                    if provider == "gpt" and self.agents.get("gpt"):
                        if not hosts or "api.openai.com" in hosts:
                            r = self.agents["gpt"].complete(user_text)
                            if r and r.strip():
                                out = self._apply_safety(r.strip())
                                if stream_callback:
                                    stream_callback(out)
                                self._cache_put(cache_key, out, {"source": "gpt"})
                                return out
                    if provider == "claude" and self.agents.get("claude"):
                        if not hosts or "api.anthropic.com" in hosts:
                            r = self.agents["claude"].complete(user_text)
                            if r and r.strip():
                                out = self._apply_safety(r.strip())
                                if stream_callback:
                                    stream_callback(out)
                                self._cache_put(cache_key, out, {"source": "claude"})
                                return out
                    if provider == "gemini" and self.agents.get("gemini"):
                        if not hosts or "generativelanguage.googleapis.com" in hosts:
                            r = self.agents["gemini"].complete(user_text)
                            if r and r.strip():
                                out = self._apply_safety(r.strip())
                                if stream_callback:
                                    stream_callback(out)
                                self._cache_put(cache_key, out, {"source": "gemini"})
                                return out
                except Exception:
                    # Continue to next provider
                    continue
        # 4) Fallback generic
        fallback = random.choice(
            [
                "I’m listening—tell me more.",
                "What outcome do you want next?",
                "Let’s take a step forward—what’s the first move?",
            ]
        )
        fb = self._apply_safety(fallback)
        self._cache_put(cache_key, fb, {"source": "fallback"})
        return fb


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)
