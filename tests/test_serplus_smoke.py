from __future__ import annotations

import sys

import pytest


def _reload_serplus_modules() -> None:
    to_drop = [name for name in sys.modules if name.startswith("serplus")]
    for name in to_drop:
        sys.modules.pop(name, None)


@pytest.fixture(autouse=True)
def serplus_tmpdir(monkeypatch, tmp_path):
    monkeypatch.setenv("SERPLUS_DATA_DIR", str(tmp_path))
    _reload_serplus_modules()
    yield
    _reload_serplus_modules()


def test_serplus_currency_lifecycle():
    from serplus import allocation_health, ledger_snapshot, plan_allocation, ser_burn, ser_mint, ser_transfer
    from serplus.accounts import all_accounts
    from serplus.compcoin import burn_comp, comp_state, mint_comp, transfer_comp
    from serplus.ledger import ndjson_ledger as ledger
    from serplus.nft import all_tokens, register_token, reset_registry, tokens_by_owner

    # Seed treasury and perform lifecycle operations
    ser_mint(to="treasury", amount=500, actor="programmerONE", meta={"label": "Treasury"})
    ser_transfer(source="treasury", target="ops", amount=125, actor="treasury")
    ser_burn(account="ops", amount=25, actor="ops")

    balances = ledger.balances("SER")
    assert balances["treasury"] == pytest.approx(375.0)
    assert balances["ops"] == pytest.approx(100.0)
    assert ledger.total_supply("SER") == pytest.approx(475.0)

    plan = plan_allocation(250)
    assert pytest.approx(sum(plan.values()), rel=1e-3) == 250

    snapshot = ledger_snapshot(limit=5)
    assert snapshot["asset"] == "SER"
    assert snapshot["holders"] and any(h["account"] == "treasury" for h in snapshot["holders"])

    health = allocation_health()
    assert health["supply"] == pytest.approx(475.0)
    assert health["holder_count"] >= 2

    accounts = all_accounts()
    assert set(accounts.keys()) == {"treasury", "ops"}

    # NFT registry basics
    reset_registry()
    register_token("nft-1", "ops", {"rarity": "gold"})
    register_token("nft-2", "treasury")
    assert len(all_tokens()) == 2
    assert len(tokens_by_owner("ops")) == 1

    # CompCoin mirrors the same ledger infrastructure
    mint_comp("treasury", 300, actor="programmerONE")
    transfer_comp("treasury", "ops", 50, actor="treasury")
    burn_comp("ops", 10, actor="ops")
    comp_snapshot = comp_state(limit=5)
    assert comp_snapshot["supply"] == pytest.approx(290.0)
    assert any(holder["account"] == "ops" for holder in comp_snapshot["holders"])

    entries = ledger.iter_entries(limit=20)
    assert len(entries) >= 6  # mint + transfer + burn + comp ops + nft audits

    # Authorization guard
    with pytest.raises(PermissionError):
        ser_mint(to="hacker", amount=10, actor="unauthorized")


def test_transfer_validation_errors():
    from serplus import ser_mint
    from serplus.transfers import ser_transfer

    ser_mint(to="wallet", amount=10, actor="programmerONE")
    with pytest.raises(ValueError):
        ser_transfer(source="wallet", target="wallet", amount=1, actor="wallet")
    with pytest.raises(ValueError):
        ser_transfer(source="wallet", target="ops", amount=50, actor="wallet")
