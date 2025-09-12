from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import queue
import random
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# SE41 (v4.1+) unified interface
# ---------------------------------------------------------------------------
from symbolic_core.symbolic_equation41 import SymbolicEquation41
from trading.helpers.se41_trading_gate import (
    se41_signals,  # builds SE41Signals payload
    ethos_decision,  # allow/hold/deny with pillar breakdown
    se41_numeric,  # bounded numeric synthesis (0<|x|<1000)
)

"""
📝 EidollonaONE Trade Logger v4.1+

SE41 + Ethos + Integrity:
  • SE41 coherence for every log row
  • Optional ethos-gated persistence for sensitive classes
  • Cryptographic hashing + quantum integrity scoring
  • CSV + SQLite dual persistence (thread-safe)
  • Search + live statistics for dashboards
"""

# Optional dependencies from engine modules (kept soft)
try:
    from trading_engine.ai_trade_executor import (
        TradeType,
    )
    from trading_engine.order_management import OrderType, OrderState
    from trading_engine.position_manager import PositionType

    TRADE_COMPONENTS_AVAILABLE = True
except Exception:
    TRADE_COMPONENTS_AVAILABLE = False

    # minimal shims for smoke usage
    class TradeType(Enum):
        BUY = "buy"
        SELL = "sell"

    class OrderType(Enum):
        MARKET = "market"
        LIMIT = "limit"

    class OrderState(Enum):
        CREATED = "created"
        FILLED = "filled"

    class PositionType(Enum):
        LONG = "long"
        SHORT = "short"


# ---------------------------------------------------------------------------
# Log types & datamodel
# ---------------------------------------------------------------------------
class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    AUDIT = "audit"


class LogType(Enum):
    TRADE_EXECUTION = "trade_execution"
    ORDER_MANAGEMENT = "order_management"
    POSITION_UPDATE = "position_update"
    RISK_EVENT = "risk_event"
    COMPLIANCE_EVENT = "compliance_event"
    SYSTEM_EVENT = "system_event"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_EVENT = "error_event"
    AUDIT_TRAIL = "audit_trail"


class DataIntegrity(Enum):
    BASIC = "basic"
    ENHANCED = "enhanced"
    CRYPTOGRAPHIC = "cryptographic"
    BLOCKCHAIN = "blockchain"  # reserved for future chain anchoring


@dataclass
class TradeLogEntry:
    log_id: str
    log_type: LogType
    log_level: LogLevel
    timestamp: datetime

    # Core narrative + payload
    message: str
    event_data: Dict[str, Any] = field(default_factory=dict)

    # Related entities
    symbol: Optional[str] = None
    order_id: Optional[str] = None
    execution_id: Optional[str] = None
    position_id: Optional[str] = None
    strategy_id: Optional[str] = None

    # Financial metrics (optional)
    quantity: Optional[float] = None
    price: Optional[float] = None
    value: Optional[float] = None
    fees: Optional[float] = None
    pnl: Optional[float] = None

    # Context
    source_system: str = "EidollonaONE"
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Ordering / correlation
    sequence_number: int = 0
    parent_log_id: Optional[str] = None
    correlation_id: Optional[str] = None

    # Integrity
    data_hash: Optional[str] = None
    integrity_level: DataIntegrity = DataIntegrity.BASIC
    verification_status: str = "unverified"

    # Symbolic / quantum
    symbolic_coherence: float = 0.0
    quantum_verification: float = 0.0
    consciousness_authenticity: float = 0.0


@dataclass
class LogSearchCriteria:
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    log_types: List[LogType] = field(default_factory=list)
    log_levels: List[LogLevel] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    order_ids: List[str] = field(default_factory=list)
    text_search: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    limit: int = 1000


@dataclass
class LogStatistics:
    total_entries: int = 0
    entries_by_type: Dict[str, int] = field(default_factory=dict)
    entries_by_level: Dict[str, int] = field(default_factory=dict)
    entries_by_symbol: Dict[str, int] = field(default_factory=dict)
    entries_last_hour: int = 0
    entries_last_day: int = 0
    entries_last_week: int = 0
    verified_entries: int = 0
    integrity_score: float = 0.0
    average_log_latency_ms: float = 0.0
    storage_size_mb: float = 0.0
    average_symbolic_coherence: float = 0.0
    quantum_verification_rate: float = 0.0


# ---------------------------------------------------------------------------
# SE41 coherence validator for logs
# ---------------------------------------------------------------------------
class SymbolicLogValidator:
    def __init__(self):
        self.log = logging.getLogger(f"{__name__}.SymbolicLogValidator")
        self._se41 = SymbolicEquation41()

    def validate_log_coherence(
        self, entry: TradeLogEntry, ctx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Produce a bounded SE41 numeric → coherence in [0..1]; hash & status.
        """
        try:
            importance = self._importance(entry.log_level, entry.log_type)
            value_factor = self._norm_value(entry.value or 0.0)
            t_factor = self._time_factor(entry.timestamp)
            completeness = self._completeness(entry)

            vol = float(ctx.get("volatility", 0.2))
            volf = min(max(vol, 0.0), 1.0)
            vfac = float(ctx.get("volume_factor", 0.5))
            load = float(ctx.get("system_load", 0.3))

            numeric = se41_numeric(
                M_t=max(0.05, (importance * 0.5 + completeness * 0.5)),
                DNA_states=[
                    1.0,
                    importance,
                    value_factor,
                    t_factor,
                    completeness,
                    (1.0 - volf),
                    (1.0 - min(load, 1.0)),
                    1.07,
                ],
                harmonic_patterns=[
                    1.0,
                    1.1,
                    importance,
                    completeness,
                    value_factor,
                    max(0.0, 1.0 - volf),
                    vfac,
                    0.98,
                ],
            )
            ok = (
                isinstance(numeric, (int, float))
                and math.isfinite(numeric)
                and 0.001 < abs(numeric) < 1000.0
            )
            coherence = min(abs(float(numeric)) / 80.0, 1.0) if ok else 0.5
            entry.symbolic_coherence = coherence

            # Hash & verification label
            dhash = self._data_hash(entry, coherence)
            entry.data_hash = dhash
            entry.verification_status = (
                "highly_verified"
                if coherence >= 0.9
                else (
                    "verified"
                    if coherence >= 0.7
                    else "partially_verified" if coherence >= 0.5 else "unverified"
                )
            )

            return {
                "valid": True,
                "coherence_score": coherence,
                "symbolic_result": float(numeric) if ok else 0.0,
                "integrity_hash": dhash,
                "verification_status": entry.verification_status,
                "validation_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.log.error(f"Log coherence failed: {e}")
            return {"valid": False, "coherence_score": 0.0, "error": str(e)}

    # ---- helpers
    def _importance(self, level: LogLevel, ltype: LogType) -> float:
        lw = {
            LogLevel.DEBUG: 0.2,
            LogLevel.INFO: 0.4,
            LogLevel.WARNING: 0.6,
            LogLevel.ERROR: 0.8,
            LogLevel.CRITICAL: 1.0,
            LogLevel.AUDIT: 1.0,
        }.get(level, 0.5)
        tw = {
            LogType.TRADE_EXECUTION: 1.0,
            LogType.ORDER_MANAGEMENT: 0.9,
            LogType.POSITION_UPDATE: 0.8,
            LogType.RISK_EVENT: 0.9,
            LogType.COMPLIANCE_EVENT: 1.0,
            LogType.SYSTEM_EVENT: 0.6,
            LogType.PERFORMANCE_METRIC: 0.7,
            LogType.ERROR_EVENT: 0.8,
            LogType.AUDIT_TRAIL: 1.0,
        }.get(ltype, 0.5)
        return (lw + tw) / 2.0

    def _norm_value(self, v: float) -> float:
        if v == 0:
            return 0.1
        return max(0.1, min(abs(v) / 100_000.0, 1.0))

    def _time_factor(self, ts: datetime) -> float:
        diff = (datetime.now() - ts).total_seconds()
        if diff < 60:
            return 1.0
        if diff < 3600:
            return 0.9
        if diff < 86_400:
            return 0.7
        return 0.5

    def _completeness(self, e: TradeLogEntry) -> float:
        req = ["log_id", "log_type", "log_level", "timestamp", "message"]
        opt = [
            "symbol",
            "order_id",
            "execution_id",
            "position_id",
            "quantity",
            "price",
            "value",
            "fees",
        ]
        rq = sum(1 for f in req if getattr(e, f) is not None) / len(req)
        op = sum(1 for f in opt if getattr(e, f) is not None) / len(opt)
        return rq * 0.7 + op * 0.3

    def _data_hash(self, e: TradeLogEntry, coherence: float) -> str:
        critical = {
            "log_id": e.log_id,
            "ts": e.timestamp.isoformat(),
            "type": e.log_type.value,
            "msg": e.message,
            "sym": e.symbol,
            "qty": e.quantity,
            "px": e.price,
            "val": e.value,
            "coh": round(coherence, 6),
        }
        blob = json.dumps(critical, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Quantum integrity verifier (soft heuristic)
# ---------------------------------------------------------------------------
class QuantumLogIntegrity:
    def __init__(self):
        self.log = logging.getLogger(f"{__name__}.QuantumLogIntegrity")
        self._cache: Dict[str, Any] = {}

    def verify(self, entry: TradeLogEntry, ctx: Dict[str, Any]) -> Dict[str, Any]:
        try:
            qrnd = random.uniform(0.95, 1.05)
            coh = random.uniform(0.9, 1.0)
            hash_ok = 1.0 if entry.data_hash and len(entry.data_hash) == 16 else 0.6
            seq_ok = self._seq_check(entry, ctx)
            data_ok = self._data_check(entry)
            time_ok = self._time_check(entry)

            base = hash_ok * 0.3 + seq_ok * 0.2 + data_ok * 0.3 + time_ok * 0.2
            qscore = min(base * qrnd * coh, 1.0)
            entry.quantum_verification = qscore
            cls = (
                "perfect"
                if qscore >= 0.95
                else (
                    "excellent"
                    if qscore >= 0.9
                    else (
                        "good"
                        if qscore >= 0.8
                        else (
                            "acceptable"
                            if qscore >= 0.7
                            else "questionable" if qscore >= 0.5 else "poor"
                        )
                    )
                )
            )
            return {
                "quantum_integrity_score": qscore,
                "integrity_class": cls,
                "verification_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.log.error(f"Quantum verify failed: {e}")
            return {"quantum_integrity_score": 0.5, "integrity_class": "unknown"}

    def _seq_check(self, e: TradeLogEntry, ctx: Dict[str, Any]) -> float:
        last = float(ctx.get("last_sequence_number", 0))
        if e.sequence_number == 0:
            return 0.8
        if e.sequence_number > last:
            return 1.0
        if e.sequence_number == last:
            return 0.6
        return 0.4

    def _data_check(self, e: TradeLogEntry) -> float:
        score = 0.0
        checks = 0
        if e.quantity is not None and e.price is not None and e.value is not None:
            exp = e.quantity * e.price
            score += 1.0 if abs((e.value or 0) - exp) < 0.01 else 0.5
            checks += 1
        if e.message and len(e.message) > 5:
            score += 1.0
            checks += 1
        if e.log_id and len(e.log_id) > 10:
            score += 1.0
            checks += 1
        return score / max(checks, 1)

    def _time_check(self, e: TradeLogEntry) -> float:
        now = datetime.now()
        if e.timestamp > now:
            return 0.2
        delta = (now - e.timestamp).total_seconds()
        if delta < 3600:
            return 1.0
        if delta < 86400:
            return 0.9
        if delta < 604800:
            return 0.8
        return 0.7


# ---------------------------------------------------------------------------
# Trade Logger: CSV + SQLite + in-memory queue
# ---------------------------------------------------------------------------
class TradeLogger:
    def __init__(
        self, logger_directory: Optional[str] = None, use_ethos_gate: bool = True
    ):
        self.log = logging.getLogger(f"{__name__}.TradeLogger")

        self.dir = Path(logger_directory or "trade_logger_data")
        self.dir.mkdir(exist_ok=True)

        self.validator = SymbolicLogValidator()
        self.integrity = QuantumLogIntegrity()

        self.sequence = 0
        self.session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        self.csv_path = self.dir / "trade_logs.csv"
        self.db_path = self.dir / "trade_logs.sqlite"
        self._init_storage()

        self._queue: "queue.Queue[TradeLogEntry]" = queue.Queue()
        self._lock = threading.Lock()
        self._bg = None
        self._run_bg = False

        self.max_memory_logs = 10000
        self.auto_flush_interval = 300  # seconds
        self.compression_enabled = False
        self.encryption_enabled = False
        self.use_ethos_gate = use_ethos_gate

        self.log.info(f"Trade Logger v4.1+ ready | session={self.session_id}")

    # -------------------------- public API -----------------------------------

    def start_background_flush(self) -> None:
        if self._bg and self._bg.is_alive():  # already running
            return
        self._run_bg = True
        self._bg = threading.Thread(
            target=self._flush_daemon, name="trade-log-flusher", daemon=True
        )
        self._bg.start()

    def stop_background_flush(self) -> None:
        self._run_bg = False
        if self._bg:
            self._bg.join(timeout=5)

    def log_generic(
        self,
        log_type: LogType,
        log_level: LogLevel,
        message: str,
        event_data: Optional[Dict[str, Any]] = None,
        *,
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        position_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        value: Optional[float] = None,
        fees: Optional[float] = None,
        pnl: Optional[float] = None,
        integrity_level: DataIntegrity = DataIntegrity.BASIC,
        trading_context: Optional[Dict[str, Any]] = None,
    ) -> TradeLogEntry:
        """
        Create, validate, (optionally ethos-gate), queue and persist the entry.
        """
        eid = f"log_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        self.sequence += 1

        e = TradeLogEntry(
            log_id=eid,
            log_type=log_type,
            log_level=log_level,
            timestamp=datetime.now(),
            message=message,
            event_data=event_data or {},
            symbol=symbol,
            order_id=order_id,
            execution_id=execution_id,
            position_id=position_id,
            strategy_id=strategy_id,
            quantity=quantity,
            price=price,
            value=value,
            fees=fees,
            pnl=pnl,
            source_system="EidollonaONE",
            user_id=None,
            session_id=self.session_id,
            sequence_number=self.sequence,
            integrity_level=integrity_level,
        )

        # 1) SE41 validation
        ctx = trading_context or {}
        _ = self.validator.validate_log_coherence(e, ctx)

        # 2) (Optional) ethos gate for sensitive classes
        if self.use_ethos_gate and log_type in (
            LogType.RISK_EVENT,
            LogType.COMPLIANCE_EVENT,
            LogType.AUDIT_TRAIL,
        ):
            if not self._ethos_allows_log(e, ctx):
                self.log.warning(
                    f"Ethos gate HOLD/DENY for log {e.log_id} ({log_type.value}); not persisted."
                )
                return e  # return, but don't persist

        # 3) Quantum integrity mark
        _ = self.integrity.verify(e, {"last_sequence_number": self.sequence - 1})

        # 4) Enqueue & persist
        self._queue.put(e)
        self._persist_entry(e)
        return e

    # Convenience typed helpers
    def log_execution(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.TRADE_EXECUTION, LogLevel.AUDIT, **kwargs)

    def log_order(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.ORDER_MANAGEMENT, LogLevel.INFO, **kwargs)

    def log_position(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.POSITION_UPDATE, LogLevel.INFO, **kwargs)

    def log_risk(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.RISK_EVENT, LogLevel.WARNING, **kwargs)

    def log_compliance(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.COMPLIANCE_EVENT, LogLevel.AUDIT, **kwargs)

    def log_system(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.SYSTEM_EVENT, LogLevel.INFO, **kwargs)

    def log_performance(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.PERFORMANCE_METRIC, LogLevel.INFO, **kwargs)

    def log_error(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.ERROR_EVENT, LogLevel.ERROR, **kwargs)

    def log_audit(self, **kwargs) -> TradeLogEntry:
        return self.log_generic(LogType.AUDIT_TRAIL, LogLevel.AUDIT, **kwargs)

    # --------------------------- queries & stats -----------------------------

    def search(self, criteria: LogSearchCriteria) -> List[TradeLogEntry]:
        """
        Simple in-memory scan (backed by CSV/SQLite persisted store).
        """
        items: List[TradeLogEntry] = list(self._snapshot_queue())
        out: List[TradeLogEntry] = []
        for e in items:
            if criteria.start_time and e.timestamp < criteria.start_time:
                continue
            if criteria.end_time and e.timestamp > criteria.end_time:
                continue
            if criteria.log_types and e.log_type not in criteria.log_types:
                continue
            if criteria.log_levels and e.log_level not in criteria.log_levels:
                continue
            if criteria.symbols and (e.symbol or "") not in criteria.symbols:
                continue
            if criteria.order_ids and (e.order_id or "") not in criteria.order_ids:
                continue
            if (
                criteria.text_search
                and criteria.text_search.lower() not in (e.message or "").lower()
            ):
                continue
            if criteria.min_value is not None and (e.value or 0.0) < criteria.min_value:
                continue
            if criteria.max_value is not None and (e.value or 0.0) > criteria.max_value:
                continue
            out.append(e)
            if len(out) >= criteria.limit:
                break
        return out

    def statistics(self) -> LogStatistics:
        items: List[TradeLogEntry] = list(self._snapshot_queue())
        stats = LogStatistics()
        stats.total_entries = len(items)
        now = datetime.now()

        by_type = defaultdict(int)
        by_level = defaultdict(int)
        by_symbol = defaultdict(int)
        ver = 0
        coh_sum = 0.0
        q_ok = 0

        for e in items:
            by_type[e.log_type.value] += 1
            by_level[e.log_level.value] += 1
            if e.symbol:
                by_symbol[e.symbol] += 1
            if e.verification_status in ("verified", "highly_verified"):
                ver += 1
            coh_sum += float(e.symbolic_coherence or 0.0)
            if (e.quantum_verification or 0.0) >= 0.7:
                q_ok += 1

        stats.entries_by_type = dict(by_type)
        stats.entries_by_level = dict(by_level)
        stats.entries_by_symbol = dict(by_symbol)
        stats.verified_entries = ver
        stats.average_symbolic_coherence = coh_sum / max(1, len(items))
        stats.quantum_verification_rate = q_ok / max(1, len(items))

        # time windows
        stats.entries_last_hour = sum(
            (now - e.timestamp) <= timedelta(hours=1) for e in items
        )
        stats.entries_last_day = sum(
            (now - e.timestamp) <= timedelta(days=1) for e in items
        )
        stats.entries_last_week = sum(
            (now - e.timestamp) <= timedelta(days=7) for e in items
        )

        # storage size (approx)
        try:
            sz = 0
            if self.csv_path.exists():
                sz += self.csv_path.stat().st_size
            if self.db_path.exists():
                sz += self.db_path.stat().st_size
            stats.storage_size_mb = round(sz / (1024 * 1024), 3)
        except Exception:
            stats.storage_size_mb = 0.0

        return stats

    # --------------------------- internals -----------------------------------

    def _ethos_allows_log(self, entry: TradeLogEntry, ctx: Dict[str, Any]) -> bool:
        """
        Optional: apply ethos gate (A/I/R/E) for sensitive logs before persistence.
        """
        sig = se41_signals(
            {
                "coherence": max(0.0, min(entry.symbolic_coherence, 1.0)),
                "risk": max(0.0, min(float(ctx.get("risk_hint", 0.4)), 1.0)),
                "impetus": max(0.0, min(float(ctx.get("impetus", 0.5)), 1.0)),
                "ethos": {
                    "authenticity": 0.92,
                    "integrity": 0.90,
                    "responsibility": 0.88,
                    "enrichment": 0.90,
                },
                "explain": f"log.{entry.log_type.value}",
            }
        )
        decision = ethos_decision(sig)
        d = decision.get("decision", "hold")
        self.log.info(
            f"Ethos(log): {d} | type={entry.log_type.value} reason={decision.get('reason','')}"
        )
        return d == "allow"

    def _snapshot_queue(self) -> List[TradeLogEntry]:
        # In-memory view (recent rows). For full history, query SQLite if desired.
        with self._lock:
            # Copy current queue content snapshot (plus not-yet-flushed file is already written by _persist_entry)
            return (
                list(getattr(self, "_mem_cache", []))
                if hasattr(self, "_mem_cache")
                else []
            )

    def _persist_entry(self, e: TradeLogEntry) -> None:
        # append to memory cache too (bounded)
        with self._lock:
            cache = getattr(self, "_mem_cache", [])
            cache.append(e)
            if len(cache) > self.max_memory_logs:
                cache = cache[-self.max_memory_logs :]
            self._mem_cache = cache

        # CSV
        self._append_csv(e)
        # SQLite
        self._insert_sqlite(e)

    def _append_csv(self, e: TradeLogEntry) -> None:
        hdr = [
            "log_id",
            "timestamp",
            "type",
            "level",
            "message",
            "symbol",
            "order_id",
            "execution_id",
            "position_id",
            "strategy_id",
            "quantity",
            "price",
            "value",
            "fees",
            "pnl",
            "sequence_number",
            "session_id",
            "data_hash",
            "verification_status",
            "symbolic_coherence",
            "quantum_verification",
        ]
        row = [
            e.log_id,
            e.timestamp.isoformat(),
            e.log_type.value,
            e.log_level.value,
            e.message,
            e.symbol,
            e.order_id,
            e.execution_id,
            e.position_id,
            e.strategy_id,
            e.quantity,
            e.price,
            e.value,
            e.fees,
            e.pnl,
            e.sequence_number,
            e.session_id,
            e.data_hash,
            e.verification_status,
            round(e.symbolic_coherence or 0.0, 6),
            round(e.quantum_verification or 0.0, 6),
        ]
        try:
            new = not self.csv_path.exists()
            with self.csv_path.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(hdr)
                w.writerow(row)
        except Exception as ex:
            self.log.error(f"CSV append failed: {ex}")

    def _insert_sqlite(self, e: TradeLogEntry) -> None:
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_logs(
                    log_id TEXT PRIMARY KEY,
                    ts TEXT,
                    type TEXT,
                    level TEXT,
                    message TEXT,
                    symbol TEXT,
                    order_id TEXT,
                    execution_id TEXT,
                    position_id TEXT,
                    strategy_id TEXT,
                    quantity REAL,
                    price REAL,
                    value REAL,
                    fees REAL,
                    pnl REAL,
                    sequence_number INTEGER,
                    session_id TEXT,
                    data_hash TEXT,
                    verification_status TEXT,
                    symbolic_coherence REAL,
                    quantum_verification REAL,
                    event_json TEXT
                )
            """
            )
            cur.execute(
                """
                INSERT OR REPLACE INTO trade_logs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
                (
                    e.log_id,
                    e.timestamp.isoformat(),
                    e.log_type.value,
                    e.log_level.value,
                    e.message,
                    e.symbol,
                    e.order_id,
                    e.execution_id,
                    e.position_id,
                    e.strategy_id,
                    e.quantity,
                    e.price,
                    e.value,
                    e.fees,
                    e.pnl,
                    e.sequence_number,
                    e.session_id,
                    e.data_hash,
                    e.verification_status,
                    float(e.symbolic_coherence or 0.0),
                    float(e.quantum_verification or 0.0),
                    json.dumps(e.event_data, sort_keys=True),
                ),
            )
            con.commit()
            con.close()
        except Exception as ex:
            self.log.error(f"SQLite insert failed: {ex}")

    def _flush_daemon(self) -> None:
        last = time.time()
        while self._run_bg:
            try:
                # Backoff flush interval
                if time.time() - last >= self.auto_flush_interval:
                    last = time.time()
                time.sleep(0.5)
            except Exception:
                pass

    def _init_storage(self) -> None:
        # ensure CSV header and SQLite schema
        if not self.csv_path.exists():
            try:
                with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(
                        [
                            "log_id",
                            "timestamp",
                            "type",
                            "level",
                            "message",
                            "symbol",
                            "order_id",
                            "execution_id",
                            "position_id",
                            "strategy_id",
                            "quantity",
                            "price",
                            "value",
                            "fees",
                            "pnl",
                            "sequence_number",
                            "session_id",
                            "data_hash",
                            "verification_status",
                            "symbolic_coherence",
                            "quantum_verification",
                        ]
                    )
            except Exception as ex:
                self.log.error(f"CSV init failed: {ex}")
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_logs(
                    log_id TEXT PRIMARY KEY,
                    ts TEXT,
                    type TEXT,
                    level TEXT,
                    message TEXT,
                    symbol TEXT,
                    order_id TEXT,
                    execution_id TEXT,
                    position_id TEXT,
                    strategy_id TEXT,
                    quantity REAL,
                    price REAL,
                    value REAL,
                    fees REAL,
                    pnl REAL,
                    sequence_number INTEGER,
                    session_id TEXT,
                    data_hash TEXT,
                    verification_status TEXT,
                    symbolic_coherence REAL,
                    quantum_verification REAL,
                    event_json TEXT
                )
            """
            )
            con.commit()
            con.close()
        except Exception as ex:
            self.log.error(f"SQLite init failed: {ex}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_trade_logger(**kwargs) -> TradeLogger:
    return TradeLogger(**kwargs)


# ---------------------------------------------------------------------------
# Smoke (local)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import math

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    tl = create_trade_logger()
    tl.start_background_flush()

    # demo entries
    tl.log_execution(
        message="Filled market order",
        event_data={"side": "buy"},
        symbol="AAPL",
        order_id="ord_123",
        execution_id="exec_456",
        quantity=100,
        price=195.25,
        value=19525.0,
        fees=1.95,
        pnl=None,
        trading_context={"volatility": 0.22, "volume_factor": 0.65, "system_load": 0.3},
    )

    tl.log_compliance(
        message="Rule check OK: position limits",
        event_data={"rule_id": "PL-01", "status": "pass"},
        symbol="AAPL",
        value=0.0,
        trading_context={"risk_hint": 0.3, "impetus": 0.6},
    )

    stats = tl.statistics()
    print("STATS:", stats)

# How to use it right away
# Create once via create_trade_logger() (or inject directory, enable/disable ethos gate).
# Use typed helpers to log:
# logger.log_execution(...), logger.log_order(...), logger.log_risk(...), logger.log_compliance(...), ...
# Query recent logs with logger.search(LogSearchCriteria(...)).
# Feed a dashboard from logger.statistics().
