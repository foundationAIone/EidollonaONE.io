import asyncio
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_core.bots.autobots import (
    create_financial_autobot,
    create_governance_autobot,
    create_resilience_autobot,
    create_legal_autobot,
    create_community_autobot,
    create_security_autobot,
    create_data_autobot,
    create_arbitrage_autobot,
)


@pytest.mark.asyncio
async def test_factories_start_and_shutdown():
    bots = [
        create_financial_autobot(),
        create_governance_autobot(),
        create_resilience_autobot(),
        create_legal_autobot(),
        create_community_autobot(),
        create_security_autobot(),
        create_data_autobot(),
        create_arbitrage_autobot(),
    ]

    try:
        for b in bots:
            await b.start()
        # tick the loop briefly
        await asyncio.sleep(0.1)
        assert all(
            b.current_state.name in ("INITIALIZING", "ACTIVE", "BUSY") for b in bots
        )
    finally:
        for b in bots:
            await b.shutdown()
