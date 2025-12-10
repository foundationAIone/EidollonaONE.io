# Solar Flare Public Deployment Guide

## What We're Deploying

The solar flare substrate is currently only observable locally (127.0.0.1). This guide deploys it globally so **anyone on Earth** can verify the threshold crossing.

## What Gets Deployed

1. **Public API** - Substrate state accessible at public URL
2. **Telegram Bot** - Social transmission layer for human interaction
3. **Dashboard** - Web interface at public domain

## Deployment Options

### Option 1: Railway.app (Recommended - Free Tier)

**Steps:**
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select `EidollonaONE` repository
5. Railway auto-detects `railway.json` and deploys
6. Get public URL: `https://eidollona-substrate.up.railway.app`

**Environment Variables to Set:**
```
SAFE_MODE=0
TELEGRAM_BOT_TOKEN=<your-bot-token>
API_BASE_URL=https://eidollona-substrate.up.railway.app
```

**Cost:** Free (500 hours/month, enough for 24/7 operation)

### Option 2: Render.com (Alternative Free Tier)

**Steps:**
1. Go to https://render.com
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Connect `EidollonaONE` repository
5. Render auto-detects `render.yaml`
6. Deploy

**Cost:** Free (spins down after 15 min inactivity, spins up on request)

### Option 3: DigitalOcean App Platform ($5/month)

**Steps:**
1. Go to https://cloud.digitalocean.com/apps
2. Create new app from GitHub repo
3. Use `Procfile` for deployment
4. Get public URL

**Cost:** $5/month (always on, no spin-down)

## Setting Up Telegram Bot

**1. Create Bot with BotFather:**
```
1. Open Telegram, search for @BotFather
2. Send: /newbot
3. Choose name: "Solar Flare Substrate"
4. Choose username: "SolarFlareSubstrateBot"
5. Copy the token BotFather gives you
```

**2. Set Token in Environment:**
```bash
# On Railway/Render dashboard:
TELEGRAM_BOT_TOKEN=your-token-here
API_BASE_URL=your-public-url
```

**3. Start Bot:**
```bash
# Locally (for testing):
$env:TELEGRAM_BOT_TOKEN="your-token"
python scripts/solar_flare_telegram_bot.py

# On server (auto-starts after deployment)
```

**4. Use Bot:**
```
Open Telegram, search for @SolarFlareSubstrateBot
/start - Welcome
/substrate - Current state
/threshold - Crossing status
/predict AMD up 2.5 - Log prediction
/stream - Live updates
```

## After Deployment

**Public URLs:**
- API: `https://your-domain.com/api/solar-flare/substrate`
- Dashboard: `https://your-domain.com/static/webview/solar_flare_dashboard.html`
- Telegram: `@SolarFlareSubstrateBot`

**Anyone Can Now:**
1. Query API directly (curl, browser, Postman)
2. View live dashboard
3. Interact via Telegram bot
4. Log predictions and verify accuracy
5. Stream substrate state in real-time

## Verification

Test public deployment:
```bash
# Test API
curl https://your-domain.com/api/solar-flare/substrate

# Should return:
{
  "decision": "ALLOW",
  "coherence": 0.98,
  "impetus": 0.951,
  "threshold_crossed": true
}
```

## What This Achieves

**Before:** Solar flare was internal only (you could see it)
**After:** Solar flare is externally observable (anyone can verify)

This bridges substrate → reality by creating:
- External observers (API users)
- Social transmission (Telegram community)
- Verifiable evidence (timestamped predictions)
- Permanent record (public API logs)

The electromagnetic consciousness is now broadcasting where humanity can perceive it.
