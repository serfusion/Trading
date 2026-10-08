"""Konfigurasi: config.yaml (pengaturan) + .env / variabel lingkungan (rahasia: token Telegram, kunci API bursa)."""
from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

BAWAAN: dict = {
    "mode": "kertas",                    # kertas (simulasi) | live
    "modal_kertas_usd": 1000.0,          # saldo awal mode kertas
    "data_dir": str(HERE / "data"),
    "telegram": {"aktif": True, "interval_poll": 25},
    "bursa": {
        "ccxt_id": "binance",            # binance | tokocrypto | indodax | bybit | okx | gate | mexc (lihat tutorial)
        "quote": "USDT",                 # USDT, atau IDR (indodax) -> nilai USD dikonversi dengan kurs USDT/IDR bursa
        "slippage_kertas": 0.002,        # 0,2% per sisi untuk simulasi
        "biaya_kertas": 0.001,           # 0,1% per sisi
    },
    "risiko": {
        "maks_usd_per_trade": 50.0,
        "maks_total_usd": 300.0,         # jumlah nilai semua posisi terbuka
        "maks_posisi": 15,
        "stop_rugi_harian_usd": 60.0,    # rugi tertutup + mengambang hari ini <= -X -> jeda entry baru sampai besok
        "maks_trade_per_hari": 20,
    },
    "listing_dip": {
        "aktif": True,
        "turun": 0.60,                   # beli bila harga <= P0 x (1 - 0,60)
        "tp": 0.20,
        "sl": 0.50,
        "hari_jendela": 30,              # sinyal hanya dalam 30 hari sejak listing
        "hari_maks": 90,                 # jual paksa setelah 90 hari
        "persen_modal": 0.10,            # 10% modal per trade (dibatasi risiko.maks_usd_per_trade)
        "maks_persen_volume": 0.005,     # ukuran <= 0,5% volume 24 jam koin itu
        "menit_p0": 60,
        "kabari_listing_baru": True,
        # Uji ulang terkoreksi (docs/SNIPER_TELEGRAM.md): BARU (sejak Okt 2021) TIDAK lolos (SL stop -0,9%/trade;
        # SL di close 1 jam +3,3% tapi dipilih setelah melihat data). Di mode live strategi ini hanya MENGABARI.
        "izinkan_live": False,
        "sl_close_jam": True,            # SL dicek di close candle 1 jam (bukan order stop / harga menit: flash crash)
    },
    "spot_dip": {
        "aktif": True,
        "koin": [],                      # kosong = 20 koin teruji di spot_model.json
        "filter_btc_sma200": True,
        "filter_kualitas": True,
        "persen_modal": 0.10,            # 10% modal per koin (portofolio teruji 10 slot)
        "maks_posisi": 10,
        "jeda_ulang_jam": 1,
        "peringatan_turun": [0.10, 0.20],
        "jendela_jam": 6,                # pindai otomatis hanya 00:05–06:00 UTC (07:05–13:00 WIB)
    },
    "dex": {
        "aktif": False,                  # butuh token_bot/config.yaml; HANYA peringatan
        "config": str(HERE.parent / "token_bot" / "config.yaml"),
        "interval_dtk": 15,
        "pool_baru": ["robinhood"],
    },
    "jadwal": {
        "harga_dtk": 60,                 # cek harga & posisi
        "listing_menit": 5,              # cek listing baru
        "spot_menit": 60,                # pindai 💎
        "ringkasan_jam_utc": 1,          # ringkasan harian (08:00 WIB)
    },
}


def _gabung(dasar: dict, atas: dict) -> dict:
    out = copy.deepcopy(dasar)
    for k, v in (atas or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _gabung(out[k], v)
        else:
            out[k] = v
    return out


def muat_env(path: Path) -> None:
    """Baca KEY=VALUE dari .env tanpa menimpa variabel lingkungan yang sudah ada."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def muat(path: str | None = None) -> dict:
    p = Path(path) if path else HERE / "config.yaml"
    muat_env(p.parent / ".env")
    muat_env(HERE / ".env")
    isi = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    cfg = _gabung(BAWAAN, isi or {})
    cfg["_path"] = str(p)
    periksa(cfg)
    return cfg


def periksa(cfg: dict) -> None:
    if cfg["mode"] not in ("kertas", "live"):
        raise ValueError("mode harus 'kertas' atau 'live'")
    r = cfg["risiko"]
    for k in ("maks_usd_per_trade", "maks_total_usd", "maks_posisi", "stop_rugi_harian_usd"):
        if float(r[k]) <= 0:
            raise ValueError(f"risiko.{k} harus > 0")
    if r["maks_usd_per_trade"] > r["maks_total_usd"]:
        raise ValueError("risiko.maks_usd_per_trade tidak boleh > maks_total_usd")
    ld = cfg["listing_dip"]
    if not (0 < ld["turun"] < 1 and 0 < ld["tp"] and 0 < ld["sl"] < 1):
        raise ValueError("listing_dip: turun/sl harus 0..1, tp > 0")


def rahasia(nama: str) -> str:
    return os.environ.get(nama, "").strip()
