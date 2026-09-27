import MetaTrader5 as mt5
import urllib.request
import urllib.parse
from accuracy import analyze_gold_accuracy
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import time

app = Flask(__name__)
CORS(app)

# --- Updated Configuration ---
TELEGRAM_TOKEN = "ISI_TOKEN_TELEGRAM_SENDIRI"
CHAT_ID = "ISI_CHAT_ID_SENDIRI"
SYMBOL = "XAUUSD"

live_data = {"price": 0, "signal": "Analyzing..."}

def send_telegram(msg):
    """Sending telegram message using default python libraries"""
    try:
        encoded_msg = urllib.parse.quote(msg)
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={encoded_msg}&parse_mode=HTML"
        urllib.request.urlopen(url)
        print("✅ Telegram alert sent!")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def engine():
    global live_data
    if not mt5.initialize():
        print("MT5 Initialization Failed")
        return

    mt5.symbol_select(SYMBOL, True)
    
    # Startup check
    send_telegram("🚀 <b>GILD AI:</b> System connected with new token!")

    while True:
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 100)
        if rates is not None:
            live_data = analyze_gold_accuracy(rates)
            
            # Send message if signal is found
            if "এখনই" in live_data['signal']:
                msg = (f"🔔 <b>New Signal:</b>\n"
                       f"Action: {live_data['signal']}\n"
                       f"Price: ${live_data['price']}")
                send_telegram(msg)
            
            print(f"Live Price: {live_data['price']} | Signal: {live_data['signal']}")
        
        time.sleep(10)

@app.route('/api/data')
def get_data():
    return jsonify(live_data)

if __name__ == "__main__":
    threading.Thread(target=engine, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)