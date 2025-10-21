from __future__ import annotations

from pathlib import Path
from typing import Dict, cast

from fancompfoundation import compliance, services


def _prepare_temp(monkeypatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    vault_dir = tmp_path / "vault"
    state_path = log_dir / "fancomp_state.json"
    log_dir.mkdir(parents=True, exist_ok=True)
    vault_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(services, "LOG_DIR", log_dir)
    monkeypatch.setattr(services, "VAULT_DIR", vault_dir)
    monkeypatch.setattr(services, "STATE_PATH", state_path)


def test_pool_accrues_and_draw(monkeypatch, tmp_path):
    _prepare_temp(monkeypatch, tmp_path)
    artist = services.create_artist("Alice")
    content = services.ingest_content(
        artist_id=artist.id,
        title="Liminal Echo",
        price_cents=500,
        kind="audio",
        license_terms="non-exclusive",
        metadata={"genre": "ambient"},
        file_bytes=b"sample",
        filename="sample.txt",
        percent_alloc=10.0,
    )
    services.record_purchase(content.id, buyer_id="fan1", amount_cents=1000)
    state = services.pool_state(content.id)
    pool_obj = state["pool"]
    assert pool_obj is not None
    pool = cast(Dict[str, object], pool_obj)
    assert pool["balance_cents"] == 100
    assert state["entries"], "pool entry should be recorded"

    compliance.enable_sweepstakes(True)
    pool_id = cast(str, pool["id"])
    draw = services.run_pool_draw(pool_id=pool_id, sample_size=1)
    assert draw.winners_json, "draw should select a winner"
    compliance.enable_sweepstakes(False)
