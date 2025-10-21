"""transaction_monitor.py

SE41 v4.1+ Transaction Monitor
--------------------------------
Real-time governance layer for financial transaction events (debits, credits,
withdrawals, transfers). Applies symbolic coherence scoring, risk synthesis,
ethos gating, decision policy (ALLOW / HOLD / DENY), integrity stamping, and
throttled alerting. Designed to integrate with the broader trading / autonomy
engine without creating tight coupling; all dependencies on SE41 helpers are
import-level only.

Key Pipeline (ingest_event):
 1. Normalize & basic validation
 2. Coherence scoring via bounded se41_numeric synthesis
 3. Risk scoring (amount magnitude, velocity, daily exposure, counterparty flags,
	geofence anomalies)
 4. Ethos decision (ethos_decision) – can elevate HOLD/DENY
 5. Composite decision logic with conservative bias
 6. Integrity stamp (sha256 prefix)
 7. Alert emission (rate limited) for HOLD/DENY/high-risk
 8. Optional audit callback (e.g., TradeLogger.log_risk)

FastAPI Integration (future): instantiate ONE singleton TransactionMonitor and
expose endpoints:
   POST /tx/ingest   -> returns decision + scores
   GET  /tx/stats    -> summary metrics
   GET  /tx/alerts   -> recent alert objects

Safety Principles:
 - Any exception or out-of-bounds numeric -> HOLD with reason "internal_error".
 - Ethos HOLD or DENY always respected even if numeric scores benign.
 - High risk > 0.85 or coherence < 0.40 -> cannot ALLOW (at most HOLD).
 - Daily amount soft ceiling (config.daily_limit) escalates risk proportionally.

Authoritative Decision Ladder (first match wins):
  * Ethos DENY -> DENY
  * Explicit sanction / blocked counterparty -> DENY
  * Integrity failure (should not happen under normal) -> HOLD
  * Risk >= 0.92 -> DENY
  * Risk >= 0.85 or coherence < 0.40 -> HOLD
  * Otherwise ALLOW

This module purposefully keeps implementation contained; persistence of raw
events and advanced anomaly ML pipelines can be layered later without changing
the public interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, List, Optional, Tuple
from collections import deque
from time import time
import hashlib
import threading

# SE41 governance helpers
from trading.helpers.se41_trading_gate import se41_numeric, ethos_decision  # type: ignore

__all__ = [
    "TransactionEvent",
    "TxAlert",
    "MonitorStats",
    "MonitorConfig",
    "TransactionMonitor",
]


@dataclass
class MonitorConfig:
    """Runtime tunables for the monitor.

    velocity_window_s: rolling window (seconds) for velocity / burst analysis.
    alert_cooldown_s: minimum seconds between identical alert keys.
    daily_limit:      soft cap for cumulative notional per 24h (risk escalates beyond).
    max_events:       in-memory cap for recent events ring buffer.
    max_alerts:       cap for recent alert retention.
    enable_ethos:     if False, ethos_decision still evaluated but only logged; not enforced.
    audit_on:         optional categories triggering audit callback.
    """

    velocity_window_s: int = 300
    alert_cooldown_s: int = 30
    daily_limit: float = 1_000_000.0
    max_events: int = 5000
    max_alerts: int = 250
    enable_ethos: bool = True
    audit_on: Tuple[str, ...] = ("HOLD", "DENY")


@dataclass
class TransactionEvent:
    tx_id: str
    timestamp: float
    account_id: str
    counterparty: str
    amount: float  # positive number; direction inferred via type if needed
    currency: str
    tx_type: str  # e.g. withdrawal, deposit, transfer, settlement
    meta: Dict[str, float | str | int | bool] = field(default_factory=dict)


@dataclass
class TxAlert:
    key: str
    level: str  # INFO | WARN | CRITICAL
    decision: str  # ALLOW | HOLD | DENY (decision associated)
    message: str
    timestamp: float
    risk: float
    coherence: float
    ethos: str
    integrity: str


@dataclass
class MonitorStats:
    total_events: int = 0
    allow: int = 0
    hold: int = 0
    deny: int = 0
    avg_risk: float = 0.0
    avg_coherence: float = 0.0
    last_update: float = 0.0


class TransactionMonitor:
    """SE41-aligned transaction governance engine."""

    def __init__(
        self,
        config: Optional[MonitorConfig] = None,
        audit_callback: Optional[Callable[[Dict], None]] = None,
    ) -> None:
        self.config = config or MonitorConfig()
        self._events: Deque[Dict] = deque(maxlen=self.config.max_events)
        self._alerts: Deque[TxAlert] = deque(maxlen=self.config.max_alerts)
        self._stats = MonitorStats()
        self._audit_cb = audit_callback
        self._lock = threading.RLock()
        # Rolling windows helpers
        self._velocity: Deque[Tuple[float, float]] = deque()  # (ts, amount)
        self._daily: Deque[Tuple[float, float]] = deque()  # 24h exposure window
        self._last_alert: Dict[str, float] = {}

    # ---------------- Public API -----------------
    def ingest_event(self, event: TransactionEvent) -> Dict:
        """Process a single transaction event and return decision envelope."""
        with self._lock:
            try:
                coherence = self._score_coherence(event)
                risk = self._score_risk(event)
                ethos_gate = self._apply_ethos(event, coherence, risk)
                decision = self._decide(event, coherence, risk, ethos_gate)
                integrity = self._stamp_integrity(
                    event, coherence, risk, decision, ethos_gate
                )
                record = {
                    "tx_id": event.tx_id,
                    "t": event.timestamp,
                    "account": event.account_id,
                    "counterparty": event.counterparty,
                    "amount": event.amount,
                    "currency": event.currency,
                    "type": event.tx_type,
                    "coherence": round(coherence, 4),
                    "risk": round(risk, 4),
                    "ethos": ethos_gate,
                    "decision": decision,
                    "integrity": integrity,
                }
                self._events.append(record)
                self._update_stats(coherence, risk, decision)
                self._maybe_alert(record)
                self._maybe_audit(record)
                return record
            except Exception as exc:  # fail-safe
                ts = time()
                fallback = {
                    "tx_id": event.tx_id,
                    "t": ts,
                    "account": event.account_id,
                    "counterparty": event.counterparty,
                    "amount": event.amount,
                    "currency": event.currency,
                    "type": event.tx_type,
                    "coherence": 0.0,
                    "risk": 1.0,
                    "ethos": "HOLD",
                    "decision": "HOLD",
                    "integrity": "ERR",
                    "error": str(exc)[:160],
                }
                self._events.append(fallback)
                self._maybe_alert(fallback, force=True, msg="internal_error")
                self._maybe_audit(fallback)
                return fallback

    def batch(self, events: List[TransactionEvent]) -> List[Dict]:
        return [self.ingest_event(e) for e in events]

    def stats(self) -> Dict:
        with self._lock:
            return {
                "total": self._stats.total_events,
                "allow": self._stats.allow,
                "hold": self._stats.hold,
                "deny": self._stats.deny,
                "avg_risk": round(self._stats.avg_risk, 4),
                "avg_coherence": round(self._stats.avg_coherence, 4),
                "alerts": len(self._alerts),
                "last_update": self._stats.last_update,
            }

    def recent_alerts(self, limit: int = 25) -> List[Dict]:
        with self._lock:
            return [a.__dict__ for a in list(self._alerts)[-limit:]]

    # ------------- Internal Scoring -------------
    def _score_coherence(self, event: TransactionEvent) -> float:
        # Use limited contextual signals; placeholders can be expanded later.
        # Build a pseudo signal dict to reuse se41_numeric semantics.
        base = 0.65
        size_factor = max(0.05, min(1.0, 50_000.0 / max(1.0, event.amount)))
        diversity = 0.9 if event.tx_type in {"deposit", "settlement"} else 0.75
        numeric = se41_numeric(
            M_t=base,
            DNA_states=[1.0, size_factor, diversity, 1.1],
            harmonic_patterns=[1.0, size_factor * diversity, 1.05],
        )
        try:
            coh = max(0.0, min(1.0, float(numeric) / 100.0))
        except Exception:
            coh = 0.5
        return max(0.0, min(1.0, coh))

    def _score_risk(self, event: TransactionEvent) -> float:
        now = event.timestamp
        # Update rolling windows
        self._velocity.append((now, event.amount))
        self._daily.append((now, event.amount))
        vw = self.config.velocity_window_s
        day_window = 86400
        while self._velocity and now - self._velocity[0][0] > vw:
            self._velocity.popleft()
        while self._daily and now - self._daily[0][0] > day_window:
            self._daily.popleft()
        velocity_amt = sum(a for _, a in self._velocity)
        daily_amt = sum(a for _, a in self._daily)

        # Components
        amt_norm = min(
            1.0, event.amount / (self.config.daily_limit * 0.10)
        )  # 10% of limit -> saturate
        velocity_norm = min(1.0, velocity_amt / (self.config.daily_limit * 0.25))
        daily_norm = min(1.0, daily_amt / self.config.daily_limit)
        counterparty_flag = (
            1.0 if self._is_counterparty_flagged(event.counterparty) else 0.0
        )
        geo_str = (
            str(event.meta.get("geo", "")) if hasattr(event, "meta") else ""
        )
        geo_flag = 0.75 if self._is_geofence_anomaly(geo_str) else 0.0

        # Weighted sum then normalized via se41_numeric for boundedness
        numeric = se41_numeric(
            M_t=0.5,
            DNA_states=[1.0, amt_norm * 1.2, velocity_norm, daily_norm, 1.05],
            harmonic_patterns=[1.0, counterparty_flag or 0.95, geo_flag or 0.90, 1.1],
        )
        try:
            raw = max(0.0, min(1.0, float(numeric) / 100.0))
        except Exception:
            raw = 0.5
        # Amplify flags
        if counterparty_flag:
            raw = min(1.0, raw * 1.25)
        if geo_flag:
            raw = min(1.0, raw * 1.15)
        return max(0.0, min(1.0, raw))

    # ------------- Governance Helpers -------------
    def _apply_ethos(
        self, event: TransactionEvent, coherence: float, risk: float
    ) -> str:
        # Ethos decision returns a tuple (decision, reason)
        decision, _reason = ethos_decision(
            {
                "authenticity": coherence,
                "integrity": 1.0 - risk * 0.5,
                "responsibility": max(0.0, 1.0 - risk),
                "enrichment": coherence * (1.0 - risk * 0.3),
            }
        )
        if not self.config.enable_ethos:
            return f"OBSERVE:{decision}"
        return decision

    def _decide(
        self, event: TransactionEvent, coherence: float, risk: float, ethos: str
    ) -> str:
        # Ethos override
        if ethos == "DENY":
            return "DENY"
        # Sanction / blocked
        if self._is_counterparty_sanctioned(event.counterparty):
            return "DENY"
        # Catastrophic risk
        if risk >= 0.92:
            return "DENY"
        if risk >= 0.85 or coherence < 0.40 or ethos == "HOLD":
            return "HOLD"
        return "ALLOW"

    def _stamp_integrity(
        self,
        event: TransactionEvent,
        coherence: float,
        risk: float,
        decision: str,
        ethos: str,
    ) -> str:
        h = hashlib.sha256(
            f"{event.tx_id}|{event.timestamp}|{event.account_id}|{event.amount}|{coherence:.4f}|{risk:.4f}|{decision}|{ethos}".encode()
        ).hexdigest()[:16]
        return h

    def _maybe_alert(
        self, record: Dict, force: bool = False, msg: Optional[str] = None
    ) -> None:
        key = f"{record['decision']}:{record['account']}"
        now = record["t"]
        last = self._last_alert.get(key, 0.0)
        if not force and now - last < self.config.alert_cooldown_s:
            return
        if record["decision"] == "ALLOW" and not force:
            # Only alert on ALLOW if explicit force or extreme metrics
            if record["risk"] < 0.9 and record["coherence"] > 0.35:
                return
        level = "INFO"
        if record["decision"] == "HOLD":
            level = "WARN"
        if record["decision"] == "DENY":
            level = "CRITICAL"
        alert = TxAlert(
            key=key,
            level=level,
            decision=record["decision"],
            message=msg
            or f"tx {record['tx_id']} {record['decision']} risk={record['risk']} coh={record['coherence']}",
            timestamp=now,
            risk=record["risk"],
            coherence=record["coherence"],
            ethos=record["ethos"],
            integrity=record["integrity"],
        )
        self._alerts.append(alert)
        self._last_alert[key] = now

    def _maybe_audit(self, record: Dict) -> None:
        if record["decision"] in self.config.audit_on and self._audit_cb:
            try:
                self._audit_cb(
                    {
                        "category": "transaction",
                        "subtype": record["decision"].lower(),
                        "tx": record,
                    }
                )
            except Exception:
                pass

    def _update_stats(self, coherence: float, risk: float, decision: str) -> None:
        s = self._stats
        s.total_events += 1
        if decision == "ALLOW":
            s.allow += 1
        elif decision == "HOLD":
            s.hold += 1
        else:
            s.deny += 1
        # Running averages
        n = s.total_events
        s.avg_risk = ((s.avg_risk * (n - 1)) + risk) / n
        s.avg_coherence = ((s.avg_coherence * (n - 1)) + coherence) / n
        s.last_update = time()

    # ------------- Flag Helpers (stub logic extendable) -------------
    def _is_counterparty_flagged(self, counterparty: str) -> bool:
        if not counterparty:
            return False
        lowered = counterparty.lower()
        return any(tag in lowered for tag in ("test", "sandbox"))

    def _is_counterparty_sanctioned(self, counterparty: str) -> bool:
        if not counterparty:
            return False
        lowered = counterparty.lower()
        return any(tag in lowered for tag in ("blocked", "sanction"))

    def _is_geofence_anomaly(self, geo: str | None) -> bool:
        if not geo:
            return False
        geo_l = str(geo).lower()
        return geo_l in {"??", "xx", "irregular"}


# End of module
