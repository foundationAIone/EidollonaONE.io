from __future__ import annotations

from pathlib import Path

from serve_it_app import services
from serve_it_app import state as serve_state


def _prepare_temp(monkeypatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    state_path = log_dir / "serveit_state.json"
    log_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(serve_state, "LOG_DIR", log_dir)
    monkeypatch.setattr(serve_state, "STATE_PATH", state_path)


def test_request_quote_book(monkeypatch, tmp_path):
    _prepare_temp(monkeypatch, tmp_path)
    receiver = services.create_user("receiver")
    provider_user = services.create_user("provider")
    provider = services.register_provider(provider_user.id, ["general"], rating=4.8)
    services.ensure_service_type("general")

    request = services.create_request(receiver.id, "general", "Clean", 37.7, -122.4)
    quote = services.add_quote(request.id, provider.id, 3200, 2.0)
    booking = services.create_booking(quote.id)
    services.complete_booking(booking.id, proof="photo")
    receipt = services.payout_paper(booking.id, "paper-acct", 3200)

    metrics = services.metrics()
    assert metrics["bookings"] == 1
    assert metrics["completed"] == 1
    assert receipt["booking_id"] == booking.id
    assert "stub" in receipt
