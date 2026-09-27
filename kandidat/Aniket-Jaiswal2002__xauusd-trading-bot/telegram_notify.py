"""
Telegram Notifier for XAUUSD Bot
Sends alerts to your phone for every trade event.
"""

import requests
import logging

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  ⚠️  PUT YOUR DETAILS HERE
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = "YOUR_TELEGRAM_BOT_TOKEN"    # from @BotFather
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"      # from @userinfobot
# ─────────────────────────────────────────────

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def send(message: str):
    """Send a Telegram message. Silently logs if it fails."""
    try:
        resp = requests.post(BASE_URL, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        if not resp.ok:
            log.warning(f"Telegram send failed: {resp.text}")
    except Exception as e:
        log.warning(f"Telegram error: {e}")


# ── Alert Templates ───────────────────────────

def alert_start():
    send(
        "🤖 <b>XAUUSD Bot Started</b>\n"
        "Scanning every 60 seconds.\n"
        "Symbol: XAUUSD | Timeframe: H4"
    )

def alert_trade_open(signal, price, sl, tp, lot, atr):
    emoji = "🟢" if signal == "BUY" else "🔴"
    send(
        f"{emoji} <b>Trade Opened — {signal}</b>\n"
        f"────────────────\n"
        f"Symbol  : XAUUSD\n"
        f"Price   : {price:.2f}\n"
        f"Lot     : {lot}\n"
        f"SL      : {sl:.2f}\n"
        f"TP      : {tp:.2f}\n"
        f"ATR     : {atr:.2f}\n"
        f"────────────────\n"
        f"R:R ~1:1.67 | Risk 1%"
    )

def alert_trade_close(ticket, profit, symbol="XAUUSD"):
    emoji = "✅" if profit >= 0 else "❌"
    result = "WIN" if profit >= 0 else "LOSS"
    send(
        f"{emoji} <b>Trade Closed — {result}</b>\n"
        f"────────────────\n"
        f"Symbol  : {symbol}\n"
        f"Ticket  : #{ticket}\n"
        f"P&L     : {'+'if profit>=0 else ''}{profit:.2f} USD\n"
        f"────────────────"
    )

def alert_daily_loss_limit(loss_amount):
    send(
        f"⛔ <b>Daily Loss Limit Hit</b>\n"
        f"Loss today: ${abs(loss_amount):.2f}\n"
        f"Bot paused for the rest of today."
    )

def alert_spread_too_wide(spread):
    send(
        f"⚠️ <b>Spread Warning</b>\n"
        f"Current spread: {spread:.1f} pts\n"
        f"Trade skipped — waiting for tighter spread."
    )

def alert_trailing_stop_updated(ticket, new_sl):
    send(
        f"🔒 <b>Trailing Stop Updated</b>\n"
        f"Ticket : #{ticket}\n"
        f"New SL : {new_sl:.2f}"
    )

def alert_error(error_msg):
    send(
        f"🆘 <b>Bot Error</b>\n"
        f"{error_msg}"
    )
