import os
import json
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from mt5_bridge import MT5Bridge
from data_pipeline import MarketFeatureBuilder
from news_fetcher import NewsFetcher
from strategy_rag import StrategyRAG
from signal_engine import SignalEngine
from risk_manager import RiskManager
import MetaTrader5 as mt5

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("pipeline.log"), logging.StreamHandler()],
)
log = logging.getLogger("xauusd_pipeline")

bridge = MT5Bridge(symbol="XAUUSD")
news = NewsFetcher(finnhub_api_key=os.getenv("FINNHUB_API_KEY"))
rag = StrategyRAG()
engine = SignalEngine(gemini_api_key=os.getenv("GEMINI_API_KEY"))
risk_manager = RiskManager(symbol="XAUUSD", risk_pct=0.01, reward_risk_ratio=2.0)


def run_cycle():
    try:
        df = bridge.get_ohlc(mt5.TIMEFRAME_M15, bars=200)
        snapshot = MarketFeatureBuilder(df).build_snapshot()

        events = news.get_upcoming_high_impact_events(hours_ahead=1)
        if events:
            log.warning(f"High-impact news within window, skipping cycle: {events}")
            return

        headlines = news.get_gold_headlines(limit=5)
        rules = rag.retrieve_relevant_rules(
            market_context=f"trend {snapshot['trend_bias']}, "
            f"distance_from_ema20_atr {snapshot['distance_from_ema20_atr']}"
        )
        signal = engine.generate(snapshot, rules, events, headlines)

        if signal is None:
            log.error("Signal parsing failed — skipping this cycle")
            return

        log.info(f"Signal: {signal.model_dump()}")

        plan = None
        if signal.direction in ("LONG", "SHORT") and not signal.news_veto:
            try:
                plan = risk_manager.build_plan(
                    direction=signal.direction,
                    ai_invalidation_price=signal.invalidation_price,
                    atr_14=snapshot["atr_14"],
                )
                log.info(f"Execution plan: {plan.model_dump()}")
            except Exception:
                log.exception("Risk plan calculation failed — writing signal without a plan")
                plan = None

        _write_signal(signal, plan)

    except Exception:
        log.exception("Cycle failed")


def _write_signal(signal, plan):
    payload = {
        **signal.model_dump(),
        "execution_plan": plan.model_dump() if plan else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open("latest_signal.json", "w") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    bridge.connect()
    scheduler = BlockingScheduler()
    scheduler.add_job(run_cycle, "interval", minutes=15)
    log.info("Pipeline started — running every 15 minutes")
    run_cycle()
    scheduler.start()