import logging
import sys
import time
from pathlib import Path

import pandas as pd

from vektor_v6.config import (
    LOT, SPIKE_THRESHOLD, SL_PIPS, TP_PIPS, BREAKEVEN_PIPS, TRAIL_STEP,
    GRIEF_SECONDS, MAX_POSITIONS, ML_PROB_MIN, DAILY_PROFIT_TARGET_USD,
    DYNAMIC_LOT_ENABLED, DYNAMIC_SL_TP_ENABLED, BASE_CAPITAL, BASE_LOT,
)
from vektor_v6.bridge import read_market_data, read_positions, write_signal, read_tracker, write_order_request

from vektor_v6.direction import get_direction, check_h1_confluence, calculate_confluence_score, get_sideways_direction, _adx, _momentum_expansion
from vektor_v6.quality import compute_spike, MLQuality
from vektor_v6.risk import check_risk, set_grief, sync_position_count, reset_day

log = logging.getLogger("vektor_v6")


def setup_logger():
    log.setLevel(logging.DEBUG)
    log.handlers.clear()
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Console handler — force UTF-8 untuk Windows
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    if hasattr(console.stream, 'reconfigure'):
        try:
            console.stream.reconfigure(encoding='utf-8')
        except Exception:
            pass
    log.addHandler(console)
    # File handler
    fh = logging.FileHandler(Path("logs", "vektor_v6.log"), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    log.addHandler(fh)


PREFER_TF_ORDER = ["M5", "M15", "M30", "H1", "M1"]


def _detect_tf(data: dict):
    available = data.get("timeframes", [])
    for tf in PREFER_TF_ORDER:
        if tf in available:
            key = f"bars_{tf}"
            if key in data and isinstance(data[key], (list, pd.DataFrame)):
                n = len(data[key])
                min_req = 5 if tf == "M1" else 25
                if n >= min_req:
                    return tf
    return None


def _bar_key(ts: str, tf_minutes: int):
    try:
        parts = ts.split(" ")
        if len(parts) >= 2:
            tp = parts[-1].split(":")
            h, m = int(tp[0]), (int(tp[1]) // tf_minutes) * tf_minutes
            return f"{h:02d}:{m:02d}"
    except Exception:
        pass
    return ts


def calculate_m5_atr(bars: pd.DataFrame, period: int = 14) -> float:
    if bars.empty or len(bars) < period + 1:
        return 3.0  # Fallback range: $3.00 / 30 pips
    high_low = bars['high'] - bars['low']
    high_close_prev = (bars['high'] - bars['close'].shift(1)).abs()
    low_close_prev = (bars['low'] - bars['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean().iloc[-1]
    return float(atr)


def check_active_signals_invalidation(open_positions, bars_main, ml):
    # Fitur Panic Exit (Invalidasi) DILUMPUHKAN TOTAL.
    # Bot diinstruksikan untuk membiarkan SL (Gembok 30 Pips) bekerja penuh
    # agar tidak lagi tertipu oleh koreksi palsu (gergaji) sebelum profit.
    pass



def main():
    setup_logger()
    ml = MLQuality()

    last_bar_key = ""
    last_trade_bar_key = ""
    last_log_state_bar_key = ""
    last_log_ml_bar_key = ""
    total = 0
    tick = 0
    current_tf = None
    tf_minutes = 5

    ml_status = f"ON >= {ML_PROB_MIN}" if ml.model else "OFF (no model)"
    log.info("=" * 60)
    log.info("VEKTOR Bot v6 - Agresif Entry, Smart Exit")
    log.info(f"  Lot: {LOT}  ML filter: {ml_status}")
    log.info(f"  SL: {SL_PIPS}  TP: {TP_PIPS}  BE: {BREAKEVEN_PIPS}  Trail: {TRAIL_STEP}")
    log.info(f"  Max pos: {MAX_POSITIONS}  Grief: {GRIEF_SECONDS}s  Spike min: {SPIKE_THRESHOLD}")
    log.info(f"  Daily target: ${DAILY_PROFIT_TARGET_USD}")
    log.info("=" * 60)

    reset_day()
    last_beat = 0.0
    last_stat_hour = -1
    
    # State tracking internal untuk Dynamic Threshold
    global_last_signal_direction = None
    global_last_loss_direction = None
    init_tracker = read_tracker()
    global_last_loss_pips = float(init_tracker.get("loss_pips", 0.0)) if init_tracker else 0.0

    while True:
        try:
            tick += 1
            now = time.time()

            data = read_market_data()
            if data is None:
                if tick % 15 == 0:
                    log.debug(f"  [beat] ({tick}) waiting for market_data.json")
                time.sleep(2)
                continue

            ts = data.get("timestamp", "")

            tf = _detect_tf(data)
            if tf is None:
                if tick % 15 == 0:
                    log.debug(f"  [beat] ({tick}) no timeframe with bars")
                time.sleep(2)
                continue

            if tf != current_tf:
                current_tf = tf
                tf_minutes = int(tf.replace("M", "")) if tf.startswith("M") else 15
                log.info(f"  [switch] Using {tf} data ({tf_minutes}min bars)")
                last_bar_key = ""
                last_trade_bar_key = ""
                last_log_state_bar_key = ""
                last_log_ml_bar_key = ""

            bars_main = data.get(f"bars_{tf}", pd.DataFrame())
            bars_h1 = data.get("bars_H1", pd.DataFrame())
            if isinstance(bars_h1, list):
                bars_h1 = pd.DataFrame(bars_h1)

            if bars_main.empty or len(bars_main) < 25:
                time.sleep(2)
                continue

            bar_key = _bar_key(ts, tf_minutes)
            new_bar = bar_key != last_bar_key
            if new_bar:
                last_bar_key = bar_key
                last_beat = now
                
                # Vektor v9.7: Real-Time Analysis-Driven SL Invalidation (BUY & SELL)
                try:
                    pos_data = read_positions()
                    open_positions = pos_data.get("positions", []) if isinstance(pos_data, dict) else (pos_data if isinstance(pos_data, list) else [])
                    check_active_signals_invalidation(open_positions, bars_main, ml)
                except Exception as e:
                    log.error(f"[Active Eval Error] {e}")

            if not new_bar:
                if now - last_beat > 60:
                    last_beat = now
                    log.debug(f"  [beat] ({tick}) scanning intra-bar {tf} (current: {bar_key})")
            
            # Anti-Spam: 1 trade per bar
            if bar_key == last_trade_bar_key:
                time.sleep(2)
                continue

            # -- Real-Time Tracker Sync (Setiap Tick) --------------------------
            try:
                tracker = read_tracker()
                daily_profit = float(tracker.get("profit_usd", 0.0))
                daily_loss   = float(tracker.get("loss_pips", 0.0))
                cons_loss    = int(tracker.get("consecutive_losses", 0))
                
                # Deteksi kekalahan secara real-time dari MT4
                if daily_loss > global_last_loss_pips:
                    global_last_loss_direction = global_last_signal_direction
                    log.warning(f"  [LOSS DETECTED] MT4 lapor rugi. Arah kalah: {global_last_loss_direction}. Consec={cons_loss}")
                global_last_loss_pips = daily_loss
                
                current_hour = int(bar_key.split(":")[0])
                if current_hour != last_stat_hour:
                    last_stat_hour = current_hour
                    log.info(
                        f"  [DAILY STATS] profit=${daily_profit:.2f} | "
                        f"loss_pips={daily_loss:.0f} | consec_loss={cons_loss} | "
                        f"entries={total}"
                    )
            except Exception:
                pass

            # -- Daily Profit Target -------------------------------------------
            # DINONAKTIFKAN SESUAI PERMINTAAN AGAR BOT TERUS MENGANALISIS
            # tracker = read_tracker()
            # daily_profit = float(tracker.get("profit_usd", 0.0))
            # if daily_profit >= DAILY_PROFIT_TARGET_USD:
            #     log.info(
            #         f"  [{bar_key}] [TARGET REACHED] Daily profit "
            #         f"${daily_profit:.2f} >= ${DAILY_PROFIT_TARGET_USD}. Stop for today."
            #     )
            #     time.sleep(30)
            #     continue

            # -- ADX Calculation for Regime Switching --
            adx_series, _, _ = _adx(bars_main, 14)
            current_adx = adx_series.iloc[-1]

            # -- Direction & Regime Switch -------------------------------------
            is_sideways_mode = False
            
            # H1 Macro Trend
            current_price = bars_main["close"].iloc[-1] if not bars_main.empty else 0.0
            h1_trend = check_h1_confluence(bars_h1, current_price)
            
            # CEK MOMENTUM BREAKOUT EKSTRIM (Bypass ADX)
            bull_exp, bear_exp = _momentum_expansion(bars_main)
            
            if bull_exp or bear_exp:
                side = "BUY" if bull_exp else "SELL"
                is_aligned = (side == h1_trend) or (h1_trend == "BOTH")
                dynamic_ml_min = 0.550 if is_aligned else 0.650
                allow, prob = ml.check(bars_main, threshold=dynamic_ml_min)
                market_regime = f"BREAKOUT (Giant Candle)"
            elif current_adx <= 20:
                side = get_sideways_direction(bars_main)
                if side is None:
                    if bar_key != last_log_state_bar_key:
                        log.info(f"  [{bar_key}] 🟡 HOLD | Regime: SIDEWAYS | Volatility: LOW (ADX={current_adx:.1f})")
                        last_log_state_bar_key = bar_key
                    time.sleep(2)
                    continue
                    
                is_aligned = (side == h1_trend) or (h1_trend == "BOTH")
                dynamic_ml_min = 0.550 if is_aligned else 0.650
                allow, prob = ml.check_sideways(bars_main, threshold=dynamic_ml_min)
                market_regime = f"SIDEWAYS (ADX={current_adx:.1f})"
                is_sideways_mode = True
            else:
                side = get_direction(bars_main)
                if side is None:
                    if bar_key != last_log_state_bar_key:
                        log.info(f"  [{bar_key}] TREND (ADX={current_adx:.1f}) -> No momentum signal")
                        last_log_state_bar_key = bar_key
                    time.sleep(2)
                    continue
                    
                is_aligned = (side == h1_trend) or (h1_trend == "BOTH")
                dynamic_ml_min = 0.550 if is_aligned else 0.650
                allow, prob = ml.check(bars_main, threshold=dynamic_ml_min)
                market_regime = f"TREND (ADX={current_adx:.1f})"

            # -- Spike Score (Only for logging now) ----------------------------
            spike = compute_spike(bars_main)
            spike_score = spike["score"]

            if not allow:
                if bar_key != last_log_ml_bar_key:
                    log.info(f"  [{bar_key}] 🔎 ANALYZING {side} | Regime: {market_regime} | Win Prob: {prob*100:.1f}%")
                    log.info(f"  [{bar_key}] 🛡️ BLOCKED: Win Prob {prob*100:.1f}% < {dynamic_ml_min*100}% threshold.")
                    last_log_ml_bar_key = bar_key
                time.sleep(2)
                continue

            # -- Risk Check & Balance Extraction ------------------------------
            pos_data = read_positions()
            balance = 1000.0
            equity = 1000.0
            open_positions = []
            
            if isinstance(pos_data, dict):
                balance = float(pos_data.get("balance", 1000.0))
                equity = float(pos_data.get("equity", 1000.0))
                open_positions = pos_data.get("positions", [])
            elif isinstance(pos_data, list):
                open_positions = pos_data

            open_count = len(open_positions)
            sync_position_count(open_count)

            spread = float(
                data.get("indicators", {}).get("spread", 0)
            ) if data.get("indicators") else 0

            risk = check_risk(open_count, spread)
            if risk != "ok":
                log.info(f"  [{bar_key}] blocked by risk: {risk}")
                time.sleep(2)
                continue

            # -- Exit Strategy (Trend vs Sideways) -----------------------------
            atr = calculate_m5_atr(bars_main, period=14)
            atr_pips = int(atr * 10)
            
            # --- Perbaikan Kritis: ATR-Proportional SL ---
            # Jika kita memperketat SL saat volatilitas tinggi (Inverse SL), trade langsung tersentuh Stop Loss
            # oleh noise candle atau spread broker (spread XAUUSD bisa 20-30 pips).
            # Solusi Sehat: SL harus melebar sesuai nafas candle (1.5x ATR), tapi Maksimal 80 pips.
            dynamic_sl_pips = max(40, min(80, int(atr_pips * 1.5)))
            
            # Perlindungan Volatilitas Ekstrim: Jika ATR > 90 pips (Badai), lewati trade!
            if atr_pips > 90:
                if bar_key != last_log_ml_bar_key:
                    log.warning(f"  [{bar_key}] BADAI VOLATILITAS (ATR={atr_pips} pips). Trade diblokir untuk melindungi SL!")
                    last_log_ml_bar_key = bar_key
                time.sleep(2)
                continue
                
            if is_sideways_mode:
                # [Proteksi Rasio] Di mode sideways, jika SL melebihi 55 pips, pantulan terlalu liar & RR hancur.
                if dynamic_sl_pips > 55:
                    if bar_key != last_log_ml_bar_key:
                        log.warning(f"  [{bar_key}] SIDEWAYS BLOCKED: Risiko SL terlalu besar ({dynamic_sl_pips} pips) untuk target pendek.")
                        last_log_ml_bar_key = bar_key
                    time.sleep(2)
                    continue

                if prob >= 0.900:
                    tier_name = "Sideways A+"
                    tier_desc = "[Mode Sideways] Ultimate Bounce"
                    sl_pips_final = dynamic_sl_pips
                    tp_pips_final = 45
                    be_pips_final = 20
                    trail_pips_final = 0
                    tier_multiplier = 1.5
                else:
                    tier_name = "Sideways Reguler"
                    tier_desc = "[Mode Sideways] Pantulan Tepi"
                    sl_pips_final = dynamic_sl_pips
                    tp_pips_final = 40
                    be_pips_final = 20
                    trail_pips_final = 0
                    tier_multiplier = 1.0
            else:
                if prob >= 0.900:
                    tier_name = "Kelas A+"
                    tier_desc = "[Kelas A+] Super Volatility"
                    sl_pips_final = dynamic_sl_pips
                    tp_pips_final = int(dynamic_sl_pips * 2.0)  # TP = 2.0x SL
                    be_pips_final = int(dynamic_sl_pips * 0.5)
                    trail_pips_final = 15
                    tier_multiplier = 1.5
                elif prob >= 0.800:
                    tier_name = "Kelas A"
                    tier_desc = "[Kelas A] Solid Trend"
                    sl_pips_final = dynamic_sl_pips
                    tp_pips_final = int(dynamic_sl_pips * 1.5)  # TP = 1.5x SL
                    be_pips_final = int(dynamic_sl_pips * 0.5)
                    trail_pips_final = 15
                    tier_multiplier = 1.0
                else:
                    tier_name = "Kelas B"
                    tier_desc = "[Kelas B] Moderat"
                    sl_pips_final = dynamic_sl_pips
                    tp_pips_final = int(dynamic_sl_pips * 1.0)  # TP = 1.0x SL
                    be_pips_final = int(dynamic_sl_pips * 0.5)
                    trail_pips_final = 10
                    tier_multiplier = 0.5

            # -- Dynamic Lot Size Calculation ---------------------------------
            # Asymmetric Lot Sizing: Kurangi lot 50% jika melawan tren H1
            if not is_aligned:
                tier_multiplier *= 0.5
                
            if DYNAMIC_LOT_ENABLED:
                # Saldo compounding formula
                dynamic_lot = (balance / BASE_CAPITAL) * BASE_LOT * tier_multiplier
                dynamic_lot = round(dynamic_lot, 2)
                dynamic_lot = max(0.01, min(0.50, dynamic_lot)) # batas aman max 0.50 lot
            else:
                dynamic_lot = round(LOT * tier_multiplier, 2)
                dynamic_lot = max(0.01, dynamic_lot)

            # -- Execute Entry ------------------------------------------------
            if side == "BUY":
                lot_buy, lot_sell = dynamic_lot, 0.0
            else:
                lot_buy, lot_sell = 0.0, dynamic_lot

            write_signal(
                side,
                f"{tier_name} spike={spike_score:.0f}",
                lot_buy, lot_sell,
                sl_pips_final, tp_pips_final, be_pips_final, trail_pips_final,
                bar_time=ts,
                spike_score=spike_score,
                conf=prob,
            )
            set_grief(GRIEF_SECONDS)

            log.info(
                f"  >>> {side} #{total+1} [{bar_key}] ({tier_name}) "
                f"spike={spike_score:.0f} prob={prob:.3f} "
                f"lot={dynamic_lot:.2f} (bal=${balance:.1f} mult={tier_multiplier:.1f}x) "
                f"SL={sl_pips_final} TP={tp_pips_final} BE={be_pips_final} trail={trail_pips_final} (ATR={atr:.2f})"
            )
            
            last_trade_bar_key = bar_key
            global_last_signal_direction = side
            total += 1

        except Exception as e:
            log.error(f"Error in main loop: {e}", exc_info=True)

        time.sleep(2)


if __name__ == "__main__":
    main()
