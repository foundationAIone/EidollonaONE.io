# Trader Avatar (Paper Mode)

The trader avatar provides SAFE-only market interactions:

- **Paper ledger only.** Every trade updates a local JSON ledger (`logs/trader_paper_ledger.json`) and the cash balance starts at 100,000 SER-equivalent credits.
- **Abilities** via `/v1/avatar/trader/intent`:
  - `status`: summarize equity, cash, and realized/unrealized PnL.
  - `positions`: return a dashboard widget of open paper positions.
  - `paper_trade`: simulate a buy or sell with bounded quantities.
- **REST API** via `/v1/trader/paper/*` for programmatic access and integration tests.
- **Dashboard widget** (`Trader Avatar Positions`) appears in SAFE Planning HUD when the avatar runs.

## Sample requests

```powershell
# Status snapshot (requires SAFE backend running locally)
iwr -UseBasicParsing -Method Get 'http://127.0.0.1:8000/v1/trader/paper/status?token=dev-token'

# Paper buy 1.5 SAFE at 12.50 SER
iwr -UseBasicParsing -Method Post -ContentType 'application/json' \
    -Body (@{ symbol = 'SAFE'; side = 'buy'; quantity = 1.5; price = 12.5 } | ConvertTo-Json) \
    'http://127.0.0.1:8000/v1/trader/paper/trade?token=dev-token'
```

Use the VS Code tasks **Trader: Status Probe** and **Trader: Paper Trade Demo** for quick local checks.
