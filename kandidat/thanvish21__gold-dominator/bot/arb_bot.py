#!/usr/bin/env python3
"""
Gold Dominator Crypto Arbitrage Bot
Scans BTC price across 10+ exchanges, spots mispricings in real time.
Paper trading by default — set LIVE_MODE=True + add API keys to execute real trades.

Exchange APIs used directly (no ccxt needed): Binance, Kraken, Coinbase, KuCoin,
OKX, Bybit, Bitfinex, Gemini, Bitstamp, Huobi/HTX, Gate.io, MEXC
"""

import json, time, threading, requests
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
PAPER_MODE     = True      # False = live execution (requires API keys below)
MIN_SPREAD_PCT = 0.3       # Minimum spread % to log as opportunity
SCAN_INTERVAL  = 1.0       # Seconds between full scans
MAX_TRADE_USD  = 100       # Max per trade in paper mode
LOG_FILE       = "arb_log.json"

API_KEYS = {
    # "binance":  {"key": "", "secret": ""},
    # "kucoin":   {"key": "", "secret": "", "passphrase": ""},
    # "okx":      {"key": "", "secret": "", "passphrase": ""},
}

# ─────────────────────────────────────────
# EXCHANGE PRICE FETCHERS
# ─────────────────────────────────────────

TIMEOUT = 4  # seconds per request

def _get(url: str) -> Optional[dict]:
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fetch_binance() -> Optional[tuple]:
    d = _get("https://api.binance.com/api/v3/bookTicker?symbol=BTCUSDT")
    if d: return float(d["bidPrice"]), float(d["askPrice"])

def fetch_kraken() -> Optional[tuple]:
    d = _get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD")
    if d and not d.get("error"):
        t = d["result"]["XXBTZUSD"]
        return float(t["b"][0]), float(t["a"][0])

def fetch_coinbase() -> Optional[tuple]:
    d = _get("https://api.coinbase.com/v2/prices/BTC-USD/buy")
    d2 = _get("https://api.coinbase.com/v2/prices/BTC-USD/sell")
    if d and d2:
        return float(d2["data"]["amount"]), float(d["data"]["amount"])

def fetch_kucoin() -> Optional[tuple]:
    d = _get("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT")
    if d and d.get("data"):
        return float(d["data"]["bestBid"]), float(d["data"]["bestAsk"])

def fetch_okx() -> Optional[tuple]:
    d = _get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
    if d and d.get("data"):
        t = d["data"][0]
        return float(t["bidPx"]), float(t["askPx"])

def fetch_bybit() -> Optional[tuple]:
    d = _get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT")
    if d and d.get("result", {}).get("list"):
        t = d["result"]["list"][0]
        return float(t["bid1Price"]), float(t["ask1Price"])

def fetch_bitfinex() -> Optional[tuple]:
    d = _get("https://api-pub.bitfinex.com/v2/ticker/tBTCUSD")
    if d and len(d) >= 3:
        return float(d[0]), float(d[2])  # bid, ask

def fetch_gemini() -> Optional[tuple]:
    d = _get("https://api.gemini.com/v1/pubticker/btcusd")
    if d:
        return float(d["bid"]), float(d["ask"])

def fetch_bitstamp() -> Optional[tuple]:
    d = _get("https://www.bitstamp.net/api/v2/ticker/btcusd/")
    if d:
        return float(d["bid"]), float(d["ask"])

def fetch_htx() -> Optional[tuple]:
    d = _get("https://api.huobi.pro/market/detail/merged?symbol=btcusdt")
    if d and d.get("tick"):
        t = d["tick"]
        return float(t["bid"][0]), float(t["ask"][0])

def fetch_gate() -> Optional[tuple]:
    d = _get("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT")
    if d and len(d):
        return float(d[0]["highest_bid"]), float(d[0]["lowest_ask"])

def fetch_mexc() -> Optional[tuple]:
    d = _get("https://api.mexc.com/api/v3/ticker/bookTicker?symbol=BTCUSDT")
    if d:
        return float(d["bidPrice"]), float(d["askPrice"])

EXCHANGES = {
    "Binance":   fetch_binance,
    "Kraken":    fetch_kraken,
    "Coinbase":  fetch_coinbase,
    "KuCoin":    fetch_kucoin,
    "OKX":       fetch_okx,
    "Bybit":     fetch_bybit,
    "Bitfinex":  fetch_bitfinex,
    "Gemini":    fetch_gemini,
    "Bitstamp":  fetch_bitstamp,
    "HTX":       fetch_htx,
    "Gate.io":   fetch_gate,
    "MEXC":      fetch_mexc,
}

# ─────────────────────────────────────────
# OPPORTUNITY DETECTION
# ─────────────────────────────────────────

@dataclass
class Price:
    exchange: str
    bid: float
    ask: float

@dataclass
class Opportunity:
    buy_exchange: str
    sell_exchange: str
    buy_ask: float
    sell_bid: float
    spread_pct: float
    gross_profit_usd: float
    timestamp: str

def scan_all() -> dict[str, Price]:
    results = {}
    threads = []

    def fetch_one(name, fn):
        r = fn()
        if r:
            results[name] = Price(name, r[0], r[1])

    for name, fn in EXCHANGES.items():
        t = threading.Thread(target=fetch_one, args=(name, fn))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=TIMEOUT + 1)

    return results

def find_opportunities(prices: dict[str, Price]) -> list[Opportunity]:
    opps = []
    names = list(prices.keys())
    for i, buy_name in enumerate(names):
        for sell_name in names[i+1:]:
            buy = prices[buy_name]
            sell = prices[sell_name]

            # Buy on buy_name (ask), sell on sell_name (bid)
            if sell.bid > buy.ask:
                spread = (sell.bid - buy.ask) / buy.ask * 100
                if spread >= MIN_SPREAD_PCT:
                    gross = (sell.bid - buy.ask) * (MAX_TRADE_USD / buy.ask)
                    opps.append(Opportunity(
                        buy_exchange=buy_name,
                        sell_exchange=sell_name,
                        buy_ask=buy.ask,
                        sell_bid=sell.bid,
                        spread_pct=round(spread, 4),
                        gross_profit_usd=round(gross, 2),
                        timestamp=datetime.now(timezone.utc).isoformat()
                    ))

            # Reverse direction
            if buy.bid > sell.ask:
                spread = (buy.bid - sell.ask) / sell.ask * 100
                if spread >= MIN_SPREAD_PCT:
                    gross = (buy.bid - sell.ask) * (MAX_TRADE_USD / sell.ask)
                    opps.append(Opportunity(
                        buy_exchange=sell_name,
                        sell_exchange=buy_name,
                        buy_ask=sell.ask,
                        sell_bid=buy.bid,
                        spread_pct=round(spread, 4),
                        gross_profit_usd=round(gross, 2),
                        timestamp=datetime.now(timezone.utc).isoformat()
                    ))

    return sorted(opps, key=lambda x: x.spread_pct, reverse=True)

# ─────────────────────────────────────────
# PAPER EXECUTION LOG
# ─────────────────────────────────────────

trade_log = []
total_paper_profit = 0.0

def log_opportunity(opp: Opportunity):
    global total_paper_profit
    total_paper_profit += opp.gross_profit_usd
    entry = {
        "time": opp.timestamp,
        "buy": opp.buy_exchange,
        "sell": opp.sell_exchange,
        "buy_ask": opp.buy_ask,
        "sell_bid": opp.sell_bid,
        "spread_pct": opp.spread_pct,
        "gross_usd": opp.gross_profit_usd,
        "cumulative_usd": round(total_paper_profit, 2),
        "mode": "PAPER"
    }
    trade_log.append(entry)
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(trade_log, f, indent=2)
    except Exception:
        pass
    return entry

# ─────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────

def display_prices(prices: dict[str, Price]):
    print(f"\n{'─'*60}")
    print(f"  BTC/USD LIVE PRICES  [{datetime.now().strftime('%H:%M:%S')}]")
    print(f"{'─'*60}")
    for name, p in sorted(prices.items(), key=lambda x: x[1].ask):
        mid = (p.bid + p.ask) / 2
        print(f"  {name:<12} bid={p.bid:>10,.2f}  ask={p.ask:>10,.2f}  mid={mid:>10,.2f}")

def display_opportunities(opps: list[Opportunity]):
    if not opps:
        print("\n  No arbitrage opportunities ≥ {:.1f}%".format(MIN_SPREAD_PCT))
        return
    print(f"\n  {'★ ARBITRAGE OPPORTUNITIES':}")
    for o in opps[:5]:
        print(f"  BUY {o.buy_exchange:<10} @ {o.buy_ask:,.2f}  →  "
              f"SELL {o.sell_exchange:<10} @ {o.sell_bid:,.2f}  "
              f"│ {o.spread_pct:.3f}%  ≈ ${o.gross_profit_usd:.2f}")
    print(f"\n  Total paper P&L: ${total_paper_profit:,.2f}")

# ─────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────

def main():
    print("=" * 60)
    print("  GOLD DOMINATOR ARBITRAGE BOT v1.0")
    print(f"  Mode: {'⚠️  PAPER TRADING (simulation)' if PAPER_MODE else '🔴 LIVE TRADING'}")
    print(f"  Scanning {len(EXCHANGES)} exchanges for BTC/USD")
    print(f"  Min spread: {MIN_SPREAD_PCT}%  |  Max trade: ${MAX_TRADE_USD}")
    print("=" * 60)
    print("\nStarting scan... (Ctrl+C to stop)\n")

    scan_count = 0
    try:
        while True:
            scan_count += 1
            prices = scan_all()

            if not prices:
                print("  No prices retrieved — check network")
                time.sleep(SCAN_INTERVAL)
                continue

            opps = find_opportunities(prices)

            display_prices(prices)
            display_opportunities(opps)

            for opp in opps:
                entry = log_opportunity(opp)
                if not PAPER_MODE:
                    # Placeholder for live execution
                    print(f"  [LIVE] Would execute: {entry}")

            print(f"\n  Scan #{scan_count} | {len(prices)}/{len(EXCHANGES)} exchanges online")
            time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\nBot stopped. Total paper P&L: ${total_paper_profit:,.2f}")
        print(f"Trade log saved to: {LOG_FILE}")

if __name__ == "__main__":
    main()
