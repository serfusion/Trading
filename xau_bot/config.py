"""Konfigurasi bot. Nilai default mengikuti docs/STRATEGY.md.

Semua jarak harga memakai satuan HARGA (bukan point MT5):
1.00 = 1 poin di chart (mis. 4348.23 -> 4349.23).
Rahasia (login MT5, token Telegram) dibaca dari environment / file .env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BrokerConfig:
    symbol: str = "XAUUSD"          # otomatis jadi XAUUSDc (Cent) / XAUUSDm (Standard) di Exness
    account_type: str = "auto"      # auto (deteksi dari mata uang akun USC) | cent | standard
    magic: int = 250925
    deviation_points: int = 30
    # Jam server Exness = UTC+0. Ubah bila broker memakai zona lain.
    server_utc_offset_hours: float = 0.0
    terminal_path: str = ""  # kosong = auto-detect terminal MT5


@dataclass
class CorrelatedSymbol:
    symbol: str
    correlation: int = 1  # +1 searah emas (XAGUSD, EURUSD), -1 berlawanan (DXY)


@dataclass
class StrategyConfig:
    # "trend" = modul tervalidasi backtest (default), "smc" = setup sweep/MSS, "both" = keduanya
    mode: str = "trend"
    entry_tf: str = "M5"
    bias_tf: str = "H1"
    bars: int = 400
    htf_bars: int = 300
    swing_len: int = 3            # swing eksternal (likuiditas)
    internal_swing_len: int = 1   # swing internal (MSS, inducement, trailing)
    htf_swing_len: int = 3
    atr_period: int = 14
    equal_tolerance_atr: float = 0.15   # toleransi equal highs/lows
    sweep_lookback: int = 24            # bar maksimum sejak sweep
    sweep_reclaim_bars: int = 2         # close kembali di dalam level dalam N bar
    mss_max_bars: int = 24              # MSS harus terjadi <= N bar setelah sweep
    setup_max_age_bars: int = 6         # setup masih valid <= N bar setelah MSS
    min_displacement_atr: float = 1.0
    sl_buffer: float = 0.30
    min_sl: float = 1.0
    max_sl: float = 12.0
    tp_buffer: float = 0.10
    tp1_min_rr: float = 1.5
    min_rr: float = 3.0
    fallback_rr: float = 4.0            # TP2 jika tidak ada likuiditas eksternal; 0 = skip setup
    ote_low: float = 0.62
    ote_high: float = 0.79
    score_threshold: int = 7
    weights: dict[str, int] = field(default_factory=lambda: {
        "sweep": 2, "mss": 2, "poi": 1, "premium_discount": 1,
        "smt": 2, "htf_bias": 1, "killzone": 1, "inducement": 1,
        "ote": 1, "external_liquidity": 1,
    })
    mandatory: list[str] = field(default_factory=lambda: [
        "sweep", "mss", "poi", "premium_discount",
    ])
    smt_symbols: list[CorrelatedSymbol] = field(default_factory=lambda: [
        CorrelatedSymbol("XAGUSD", 1),
        CorrelatedSymbol("EURUSD", 1),
    ])
    smt_window_bars: int = 2


@dataclass
class TrendConfig:
    """Donchian trend-following (lihat xau_bot/trend.py & docs/BACKTEST.md)."""
    timeframe: str = "H1"
    entry_period: int = 55
    exit_period: int = 20
    atr_period: int = 20
    stop_atr: float = 3.0
    bars: int = 200
    respect_news: bool = False  # riset: entry dekat berita justru lebih baik -> default mati
    virtual_file: str = "data/virtual_trend.json"  # (lama) tidak dipakai lagi
    magic_offset: int = 1   # magic per set = broker.magic + offset + 10 + index set
    # Skema F-ensemble (docs/BACKTEST.md): 3 set parameter, tiap sinyal dipecah jadi `legs` posisi
    ensemble: list = field(default_factory=lambda: [[40, 15], [55, 20], [80, 30]])
    legs: int = 5
    tp1_r: float = 1.0
    risk_pct_per_set: float = 0.5
    max_orders_per_minute: int = 20
    state_dir: str = "data/trend"


@dataclass
class SessionConfig:
    # Jam New York (otomatis ikut DST). Contoh WIB musim panas AS = NY + 11 jam.
    killzones: dict[str, list[str]] = field(default_factory=lambda: {
        "London": ["02:00", "05:00"],
        "NewYork": ["07:00", "10:00"],
        "SilverBullet_AM": ["10:00", "11:00"],
        "SilverBullet_PM": ["14:00", "15:00"],
    })
    asia_range: list[str] = field(default_factory=lambda: ["20:00", "00:00"])
    killzone_only: bool = False
    rollover_block: list[str] = field(default_factory=lambda: ["16:30", "17:30"])
    friday_cutoff: str = "15:00"     # tidak entry baru setelah jam ini (NY) hari Jumat
    sunday_open_block_minutes: int = 60


@dataclass
class RiskConfig:
    risk_pct: float = 1.0
    daily_loss_pct: float = 3.0
    weekly_loss_pct: float = 6.0
    max_consecutive_losses: int = 2
    max_setups_per_direction: int = 1
    allow_min_lot_over_risk: bool = False
    max_spread: float = 0.40
    partial_ratio: float = 0.5
    be_offset: float = 0.10
    trail_after_tp1: bool = True
    trail_buffer: float = 0.30
    pending_expiry_minutes: int = 120


@dataclass
class NewsConfig:
    enabled: bool = True
    url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    currencies: list[str] = field(default_factory=lambda: ["USD"])
    impacts: list[str] = field(default_factory=lambda: ["High"])
    block_before_minutes: int = 30
    block_after_minutes: int = 30
    refresh_minutes: int = 60
    block_on_error: bool = True
    protect_before_minutes: int = 10   # pindah SL ke BE bila posisi profit sebelum berita
    cache_file: str = "data/news_cache.json"


@dataclass
class TelegramConfig:
    enabled: bool = True
    token: str = ""
    chat_id: str = ""
    notify_skipped: bool = True


@dataclass
class AppPushConfig:
    """Pengiriman sinyal ke aplikasi Android (lihat xau_bot/publish.py & android/)."""
    enabled: bool = True
    server: str = "https://ntfy.sh"
    topic: str = ""                 # kosong = dibuat acak & disimpan di topic_file
    topic_file: str = "data/app_topic.txt"
    heartbeat_minutes: int = 5


@dataclass
class AppConfig:
    trade_enabled: bool = False     # False = SINYAL saja (default); aktifkan dengan run --auto
    signals_enabled: bool = True    # kirim sinyal Telegram
    poll_seconds: float = 2.0
    journal_file: str = "data/journal.sqlite"
    log_file: str = "logs/bot.log"
    broker: BrokerConfig = field(default_factory=BrokerConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    trend: TrendConfig = field(default_factory=TrendConfig)
    sessions: SessionConfig = field(default_factory=SessionConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    app: AppPushConfig = field(default_factory=AppPushConfig)
    # Diisi dari environment, tidak disimpan di YAML.
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""


def _merge(obj: Any, data: dict[str, Any]) -> Any:
    known = {f.name: f for f in fields(obj)}
    for key, value in (data or {}).items():
        if key not in known:
            raise ValueError(f"Kunci konfigurasi tidak dikenal: {key}")
        current = getattr(obj, key)
        if is_dataclass(current) and isinstance(value, dict):
            _merge(current, value)
        elif key == "smt_symbols":
            setattr(obj, key, [CorrelatedSymbol(**v) for v in value])
        elif key == "weights" and isinstance(value, dict):
            merged = dict(current)
            merged.update(value)
            setattr(obj, key, merged)
        else:
            setattr(obj, key, value)
    return obj


def _load_dotenv(path: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return
    load_dotenv(path)


def load_config(path: str | None = None, env_file: str | None = ".env") -> AppConfig:
    cfg = AppConfig()
    if path:
        with open(path, encoding="utf-8") as fh:
            _merge(cfg, yaml.safe_load(fh) or {})
    if env_file and Path(env_file).exists():
        _load_dotenv(Path(env_file))
    cfg.mt5_login = int(os.getenv("MT5_LOGIN", cfg.mt5_login) or 0)
    cfg.mt5_password = os.getenv("MT5_PASSWORD", cfg.mt5_password)
    cfg.mt5_server = os.getenv("MT5_SERVER", cfg.mt5_server)
    cfg.broker.terminal_path = os.getenv("MT5_PATH", cfg.broker.terminal_path)
    cfg.telegram.token = os.getenv("TELEGRAM_TOKEN", cfg.telegram.token)
    cfg.telegram.chat_id = os.getenv("TELEGRAM_CHAT_ID", cfg.telegram.chat_id)
    if not cfg.telegram.token or not cfg.telegram.chat_id:
        cfg.telegram.enabled = False
    return cfg
