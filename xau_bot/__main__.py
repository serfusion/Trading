"""CLI: python -m xau_bot {run,check,backtest,fetch}"""
from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd

from .config import AppConfig, load_config


def setup_logging(cfg: AppConfig, console: bool) -> None:
    Path(cfg.log_file).parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(cfg.log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8")]
    if console:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _mt5_broker(cfg: AppConfig):
    from .broker.mt5 import MT5Broker
    return MT5Broker(cfg.mt5_login, cfg.mt5_password, cfg.mt5_server, cfg.broker.terminal_path,
                     cfg.broker.server_utc_offset_hours, cfg.broker.deviation_points)


def _notifier(cfg: AppConfig):
    from .telegram import Notifier, TelegramNotifier
    return TelegramNotifier(cfg.telegram) if cfg.telegram.enabled else Notifier()


def _publisher(cfg: AppConfig):
    from .publish import NtfyPublisher, Publisher, load_or_create_topic
    if not cfg.app.enabled:
        return Publisher()
    topic = cfg.app.topic or load_or_create_topic(cfg.app.topic_file)
    return NtfyPublisher(cfg.app.server, topic)


def cmd_app(args) -> int:
    cfg = load_config(args.config)
    pub = _publisher(cfg)
    print("Pengaturan aplikasi Android 'XAU Signal':")
    print(f"  Server : {cfg.app.server}")
    print(f"  Topik  : {pub.topic}")
    print("Masukkan keduanya di menu Pengaturan aplikasi. Jangan bagikan topik ke orang lain.")
    print(f"(Alternatif: aplikasi resmi 'ntfy' -> subscribe topik {pub.topic})")
    return 0


def cmd_run(args) -> int:
    from .engine import Engine
    cfg = load_config(args.config)
    if args.signals_only:
        cfg.trade_enabled = False
    if args.auto:
        cfg.trade_enabled = True
    setup_logging(cfg, console=args.no_dashboard)
    publisher = _publisher(cfg)
    if publisher.topic:
        print(f"Topik aplikasi Android: {publisher.topic}  (server {cfg.app.server})")
    engine = Engine(cfg, _mt5_broker(cfg), _notifier(cfg), publisher=publisher)
    if not engine.start():
        print("Gagal start. Cek login MT5 di .env dan pastikan terminal MT5 terbuka.")
        return 1
    try:
        if args.no_dashboard:
            engine.run()
        else:
            from .dashboard import Dashboard
            with Dashboard() as dash:
                engine.run(on_step=dash.update)
    except KeyboardInterrupt:
        engine.log("Bot dihentikan manual", notify=True)
    finally:
        engine.notifier.stop()
        engine.publisher.stop()
        engine.broker.shutdown()
    return 0


def cmd_check(args) -> int:
    from .news import NewsFilter
    cfg = load_config(args.config)
    setup_logging(cfg, console=True)
    broker = _mt5_broker(cfg)
    if not broker.connect():
        print("❌ Tidak bisa login MT5")
        return 1
    acc0 = broker.account()
    cent = cfg.broker.account_type == "cent" or (
        cfg.broker.account_type == "auto" and acc0 is not None and acc0.currency.upper() in ("USC", "USX"))
    symbol = broker.resolve_symbol(cfg.broker.symbol, cent=cent)
    if symbol is None:
        print(f"❌ Simbol {cfg.broker.symbol} tidak ada. Cek nama simbol di Market Watch MT5.")
        return 1
    spec = broker.symbol_spec(symbol)
    tick = broker.tick(symbol)
    acc = broker.account()
    print(f"✅ MT5 OK | saldo {acc.balance:.2f} {acc.currency}{' (akun CENT)' if cent else ''} | "
          f"equity {acc.equity:.2f}")
    if symbol != cfg.broker.symbol:
        print(f"ℹ️  Simbol dipakai: {symbol}")
    print(f"✅ {spec.name}: digits {spec.digits}, tick {spec.tick_size}, nilai tick {spec.tick_value}, "
          f"lot min {spec.volume_min}, step {spec.volume_step}, stop level {spec.stops_level} point")
    if tick:
        print(f"   harga {tick.bid:.2f}/{tick.ask:.2f} spread {tick.spread:.2f}")
        lag = (pd.Timestamp.now(tz="UTC") - tick.time).total_seconds() / 3600
        if abs(lag) > 0.5:
            print(f"⚠️  Waktu tick berbeda {lag:+.1f} jam dari UTC. Jika pasar sedang buka, "
                  f"atur broker.server_utc_offset_hours = {cfg.broker.server_utc_offset_hours - lag:.0f}")
        else:
            print("✅ Offset jam server sesuai")
    for item in cfg.strategy.smt_symbols:
        sym = broker.resolve_symbol(item.symbol, cent=cent)
        print(f"{'✅' if sym else '⚠️ '} SMT {item.symbol}{' -> ' + sym if sym and sym != item.symbol else ''}")
    news = NewsFilter(cfg.news)
    news.refresh(pd.Timestamp.now(tz="UTC"), force=True)
    print(f"{'⚠️ ' + news.error if news.error else '✅ Kalender berita: ' + str(len(news.events)) + ' event'}")
    if cfg.telegram.enabled:
        n = _notifier(cfg)
        n.start()
        n.send("✅ Tes koneksi bot XAUUSD berhasil")
        import time
        time.sleep(3)
        n.stop()
        print("✅ Pesan tes Telegram dikirim")
    else:
        print("⚠️  Telegram belum diisi (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID)")
    print(f"📱 Topik aplikasi Android: {_publisher(cfg).topic or '(nonaktif)'}")
    broker.shutdown()
    return 0


def cmd_backtest(args) -> int:
    from .backtest import load_csv, run_backtest
    cfg = load_config(args.config)
    entry = load_csv(args.data)
    if args.date_from:
        entry = entry[entry.index >= pd.Timestamp(args.date_from, tz="UTC")]
    if args.date_to:
        entry = entry[entry.index <= pd.Timestamp(args.date_to, tz="UTC")]
    corr = {}
    for item in args.smt or []:
        sym, _, path = item.partition("=")
        corr[sym] = load_csv(path)
    cfg.strategy.smt_symbols = [s for s in cfg.strategy.smt_symbols if s.symbol in corr]
    print(f"Backtest {len(entry)} bar {entry.index[0]} -> {entry.index[-1]}")
    result = run_backtest(cfg, entry, corr, spread=args.spread, balance=args.balance, progress=True)
    print(result.summary())
    if args.out:
        result.trades.to_csv(args.out, index=False)
        result.setups.to_csv(Path(args.out).with_suffix(".setups.csv"), index=False)
        print(f"Detail disimpan ke {args.out}")
    return 0


def cmd_fetch(args) -> int:
    cfg = load_config(args.config)
    broker = _mt5_broker(cfg)
    if not broker.connect():
        return 1
    mt5 = broker.mt5
    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=args.days)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tf = getattr(mt5, f"TIMEFRAME_{cfg.strategy.entry_tf}")
    for name in [cfg.broker.symbol] + [s.symbol for s in cfg.strategy.smt_symbols]:
        sym = broker.resolve_symbol(name)
        if sym is None:
            continue
        arr = mt5.copy_rates_range(sym, tf, start.to_pydatetime(), end.to_pydatetime())
        if arr is None or len(arr) == 0:
            print(f"⚠️  {sym}: tidak ada data ({mt5.last_error()})")
            continue
        df = pd.DataFrame(arr)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True) - broker.offset
        path = out / f"{sym}_{cfg.strategy.entry_tf}.csv"
        df[["time", "open", "high", "low", "close"]].to_csv(path, index=False)
        print(f"✅ {sym}: {len(df)} bar -> {path}")
    broker.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="xau_bot", description="Bot XAUUSD Smart Money Concepts")
    parser.add_argument("--config", default="config.yaml" if Path("config.yaml").exists() else None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="Jalankan bot 24 jam")
    run.add_argument("--signals-only", action="store_true", help="Hanya kirim sinyal, tanpa order (default)")
    run.add_argument("--auto", action="store_true", help="Aktifkan eksekusi order otomatis")
    run.add_argument("--no-dashboard", action="store_true", help="Log biasa tanpa dashboard")
    sub.add_parser("check", help="Tes koneksi MT5, simbol, berita, Telegram")
    sub.add_parser("app", help="Tampilkan server & topik untuk aplikasi Android")
    bt = sub.add_parser("backtest", help="Backtest dari CSV")
    bt.add_argument("--data", required=True)
    bt.add_argument("--smt", action="append", help="SIMBOL=path.csv (boleh berulang)")
    bt.add_argument("--spread", type=float, default=0.20)
    bt.add_argument("--balance", type=float, default=1000.0)
    bt.add_argument("--from", dest="date_from")
    bt.add_argument("--to", dest="date_to")
    bt.add_argument("--out")
    fe = sub.add_parser("fetch", help="Unduh histori dari MT5 ke CSV")
    fe.add_argument("--days", type=int, default=180)
    fe.add_argument("--out-dir", default="data")
    args = parser.parse_args(argv)
    return {"run": cmd_run, "check": cmd_check, "backtest": cmd_backtest, "fetch": cmd_fetch,
            "app": cmd_app}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
