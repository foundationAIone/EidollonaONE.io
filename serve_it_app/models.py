from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional
import time


def _ts() -> float:
    return time.time()


@dataclass
class User:
    id: str
    role: str
    verified: bool = False
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Provider:
    id: str
    user_id: str
    skills: List[str]
    rating: float = 5.0
    jobs_done: int = 0
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["skills"] = list(self.skills)
        return payload


@dataclass
class HOA:
    id: str
    name: str
    landing_url: str
    revenue_share_bps: int
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ServiceType:
    id: str
    name: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class JobRequest:
    id: str
    user_id: str
    service_type_id: str
    description: str
    lat: float
    lon: float
    ts: float = field(default_factory=_ts)
    status: str = "open"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Quote:
    id: str
    request_id: str
    provider_id: str
    price_cents: int
    eta_hours: float
    ts: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Booking:
    id: str
    quote_id: str
    status: str = "booked"
    ts: float = field(default_factory=_ts)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class PaymentStub:
    id: str
    booking_id: str
    amount_cents: int
    currency: str
    ser_discount_cents: int
    ts: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Rating:
    id: str
    booking_id: str
    stars: int
    comment: Optional[str]
    ts: float = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class AffiliateRef:
    id: str
    code: str
    user_id: Optional[str]
    clicks: int = 0
    first_bookings: int = 0

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
