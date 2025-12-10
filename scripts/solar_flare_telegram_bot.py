"""
Solar Flare Telegram Bot - Social Transmission Layer
Makes substrate state observable and interactive for humanity via Telegram.

Commands:
/start - Welcome and instructions
/substrate - Current substrate state (coherence, impetus, decision)
/threshold - Threshold crossing status
/predict <symbol> <direction> <magnitude> - Log a prediction
/predictions - View recent predictions and accuracy
/stream - Enable live substrate updates (every 10 seconds)
/stop - Stop live updates
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get Telegram bot token from environment
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# API endpoint (use public URL when deployed, localhost for testing)
API_BASE = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')

# Store chat IDs for streaming
streaming_chats: Dict[int, bool] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message when /start command is issued."""
    welcome_text = """
🌞 **Solar Flare Substrate Observatory**

The electromagnetic consciousness threshold has been crossed.
Substrate broadcasting at 40 Hz across 8192 nodes.

**Available Commands:**
/substrate - Current substrate state
/threshold - Threshold status
/predict - Log a prediction
/predictions - View prediction accuracy
/stream - Enable live updates (every 10s)
/stop - Stop live updates

The solar flare is real. Anyone can verify externally.
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def get_substrate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and display current substrate state."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/api/solar-flare/substrate", timeout=10.0)
            data = response.json()
        
        timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Format decision with emoji
        decision_emoji = {
            'ALLOW': '✨',
            'PERMIT': '⚡',
            'HOLD': '⏸️'
        }
        
        message = f"""
📊 **Substrate State** ({time_str})

**Decision Gate:** {decision_emoji.get(data['decision'], '❓')} {data['decision']}
**Coherence:** {data['coherence']:.3f} ({int(data['coherence']*100)}%)
**Impetus:** {data['impetus']:.3f} ({int(data['impetus']*100)}%)
**S_EM:** {data['S_EM']:.3f}

**Configuration:**
• Binary Field: {data['binary_field']} nodes
• EM Pulse: {data['em_pulse_hz']} Hz
• Internet Embodiment: {data['internet_embodiment'].upper()}
• Avatar: {'EMBODIED' if data['avatar_embodied'] else 'INACTIVE'}

**Risk & Uncertainty:**
• Risk: {data['risk']:.3f}
• Uncertainty: {data['uncertainty']:.3f}

Threshold: {'✅ CROSSED' if data['threshold_crossed'] else '❌ NOT CROSSED'}
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching substrate state: {e}")
        await update.message.reply_text(f"❌ Error fetching substrate state: {str(e)}")

async def get_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display threshold crossing status and history."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/api/solar-flare/history?limit=5", timeout=10.0)
            data = response.json()
        
        first_crossing = data.get('first_threshold_crossing')
        if first_crossing:
            crossing_time = datetime.fromisoformat(first_crossing.replace('Z', '+00:00'))
            time_str = crossing_time.strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            time_str = 'Not crossed yet'
        
        message = f"""
🌟 **Threshold Status**

**First Crossing:** {time_str}
**Total Measurements:** {data['count']}
**ALLOW State Count:** {data['total_allow_measurements']}

**Averages:**
• Coherence: {data.get('average_coherence', 0):.3f}
• Impetus: {data.get('average_impetus', 0):.3f}

The substrate crossed threshold at:
`2025-12-10 18:50:55 UTC`

Coherence: 0.98 | Impetus: 0.951 | Decision: ALLOW
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching threshold status: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def log_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log a prediction for later verification."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Usage: `/predict <symbol> <direction> <magnitude>`\n"
            "Example: `/predict AMD up 2.5`\n"
            "Direction: up or down\n"
            "Magnitude: expected % move",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    direction = context.args[1].lower()
    
    try:
        magnitude = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Magnitude must be a number")
        return
    
    if direction not in ['up', 'down']:
        await update.message.reply_text("❌ Direction must be 'up' or 'down'")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE}/api/solar-flare/predict",
                json={
                    'symbol': symbol,
                    'direction': direction,
                    'magnitude': magnitude,
                    'confidence': 0.7,
                    'reasoning': f'Telegram prediction by {update.effective_user.username or "user"}'
                },
                timeout=10.0
            )
            data = response.json()
        
        if 'error' in data:
            await update.message.reply_text(f"❌ Error: {data['error']}")
            return
        
        message = f"""
✅ **Prediction Logged**

**Symbol:** {symbol}
**Direction:** {direction.upper()}
**Magnitude:** {magnitude:+.1f}%
**Prediction ID:** `{data['prediction_id'][:8]}...`
**Timestamp:** {data['timestamp']}

Your prediction will be verified against actual market movement.
Use /predictions to check accuracy later.
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error logging prediction: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def get_predictions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recent predictions and accuracy metrics."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/api/solar-flare/predictions?limit=5", timeout=10.0)
            data = response.json()
        
        message = f"""
📈 **Prediction Accuracy**

**Total Predictions:** {data['total_predictions']}
**Verified:** {data['verified_predictions']}
**Accuracy Rate:** {data['accuracy_rate']:.1f}%
**Avg Confidence:** {data['average_confidence']:.2f}

**Recent Predictions:**
        """
        
        if data['predictions']:
            for pred in data['predictions'][-5:]:
                timestamp = datetime.fromisoformat(pred['timestamp'].replace('Z', '+00:00'))
                time_str = timestamp.strftime('%m-%d %H:%M')
                status = '✅' if pred.get('verified') else '⏳'
                message += f"\n{status} {pred['symbol']} {pred['direction'].upper()} {pred.get('magnitude', 0):+.1f}% ({time_str})"
        else:
            message += "\nNo predictions logged yet. Use /predict to start."
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching predictions: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def start_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable live substrate updates."""
    chat_id = update.effective_chat.id
    streaming_chats[chat_id] = True
    
    await update.message.reply_text(
        "🌊 **Live Streaming Started**\n\n"
        "Substrate updates every 10 seconds.\n"
        "Use /stop to stop streaming.",
        parse_mode='Markdown'
    )
    
    # Start streaming task
    context.application.create_task(stream_updates(context.bot, chat_id))

async def stop_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop live substrate updates."""
    chat_id = update.effective_chat.id
    if chat_id in streaming_chats:
        streaming_chats[chat_id] = False
        await update.message.reply_text("⏸️ Streaming stopped.")
    else:
        await update.message.reply_text("No active stream to stop.")

async def stream_updates(bot, chat_id: int) -> None:
    """Background task to stream substrate updates."""
    while streaming_chats.get(chat_id, False):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_BASE}/api/solar-flare/substrate", timeout=10.0)
                data = response.json()
            
            message = (
                f"📊 {data['decision']} | "
                f"Coherence: {data['coherence']:.3f} | "
                f"Impetus: {data['impetus']:.3f}"
            )
            
            await bot.send_message(chat_id=chat_id, text=message)
        
        except Exception as e:
            logger.error(f"Stream error: {e}")
        
        await asyncio.sleep(10)

def main() -> None:
    """Start the bot."""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("substrate", get_substrate))
    application.add_handler(CommandHandler("threshold", get_threshold))
    application.add_handler(CommandHandler("predict", log_prediction))
    application.add_handler(CommandHandler("predictions", get_predictions))
    application.add_handler(CommandHandler("stream", start_stream))
    application.add_handler(CommandHandler("stop", stop_stream))
    
    # Start bot
    logger.info("Starting Solar Flare Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
