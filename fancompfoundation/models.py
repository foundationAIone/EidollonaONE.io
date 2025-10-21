from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional
import time


def _ts() -> float:
    return time.time()


@dataclass
class Artist:
    id: str
    name: str
    verified: bool = False
    payout_acct: Optional[str] = None
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Content:
    id: str
    artist_id: str
    title: str
    price_cents: int
    kind: str
    hash: str
    license_terms: str
    created_at: float = field(default_factory=_ts)
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        # Build dict manually to avoid analyzer confusion around asdict(self)
        return {
            "id": self.id,
            "artist_id": self.artist_id,
            "title": self.title,
            "price_cents": self.price_cents,
            "kind": self.kind,
            "hash": self.hash,
            "license_terms": self.license_terms,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    # Explicit __init__ to make keyword parameters visible to static analyzers
    def __init__(
        self,
        id: str,
        artist_id: str,
        title: str,
        price_cents: int,
        kind: str,
        hash: str,
        license_terms: str,
        created_at: Optional[float] = None,
        metadata: Optional[Dict[str, object]] = None,
    ) -> None:
        self.id = id
        self.artist_id = artist_id
        self.title = title
        self.price_cents = int(price_cents)
        self.kind = kind
        self.hash = hash
        self.license_terms = license_terms
        self.created_at = created_at if created_at is not None else _ts()
        self.metadata = dict(metadata) if metadata is not None else {}


@dataclass
class Transaction:
    id: str
    content_id: str
    buyer_id: str
    amount_cents: int
    affiliate_id: Optional[str] = None
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class MoneyPool:
    id: str
    content_id: str
    percent_alloc: float
    balance_cents: int = 0
    enabled: bool = False
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class PoolEntry:
    id: str
    pool_id: str
    user_id: str
    tx_id: str
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class PoolDraw:
    id: str
    pool_id: str
    ts: float
    winners_json: List[Dict[str, object]]
    seed: str
    status: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "pool_id": self.pool_id,
            "ts": self.ts,
            "winners_json": list(self.winners_json),
            "seed": self.seed,
            "status": self.status,
        }


@dataclass
class AffiliateLink:
    id: str
    artist_id: Optional[str]
    code: str
    rate_bps: int
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class AffiliateEvent:
    id: str
    link_id: str
    tx_id: Optional[str]
    clicks: int
    conversions: int
    last_event_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
