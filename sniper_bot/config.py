"""Konfigurasi: config.yaml (pengaturan) + .env / variabel lingkungan (rahasia: token Telegram, kunci API bursa)."""
from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

BAWAAN: dict = {
    "mode": "kertas",                    # kertas (simulasi) | live
    "modal_kertas_usd": 500.0,           # saldo awal mode kertas
    "data_dir": str(HERE / "data"),      # state disimpan di <data_dir>/<mode>/ (kertas & live TERPISAH)
    "telegram": {"aktif": True, "interval_poll": 25},
    "bursa": {
        "ccxt_id": "binance",            # binance | tokocrypto | bybit | okx | gate | mexc | kucoin (lihat tutorial)
        "quote": "USDT",                 # USDT (atau USDC/FDUSD). IDR TIDAK didukung: sinyal memakai harga Binance USDT
        "slippage_kertas": 0.001,        # 0,1% hanya untuk order pasar simulasi (limit/TP terisi di harga limit)
        "biaya_kertas": 0.001,           # 0,1% per sisi (fee taker Binance)
    },
    "risiko": {                          # batas KERAS untuk semua strategi; sesuaikan dengan modal (tutorial langkah 6)
        "maks_usd_per_trade": 50.0,      # ≈ 10% modal
        "maks_total_usd": 500.0,         # ≈ modal (💎 teruji: 10 slot × 10%)
        "maks_posisi": 12,
        "stop_rugi_harian_usd": 60.0,    # rugi tertutup + perubahan nilai posisi sejak 07:00 WIB <= -X -> jeda entry
        "maks_trade_per_hari": 20,
    },
    "listing_dip": {
        "aktif": True,
        "turun": 0.60,                   # beli bila harga <= P0 x (1 - 0,60)
        "tp": 0.20,
        "sl": 0.50,
        "hari_jendela": 30,              # sinyal hanya dalam 30 hari sejak listing
        "hari_maks": 90,                 # jual paksa setelah 90 hari
        "persen_modal": 0.05,            # 5% ekuitas per trade (portofolio riset research/listing_dip_porto.py)
        "min_persen_target": 0.5,        # lewati bila ukuran yang diizinkan < 50% target (seperti portofolio riset)
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
        # volume20 = 20 pair USDT dengan rata-rata volume 7 hari terbesar SAAT ITU (varian JUJUR D, tanpa bias
        # penyintas, dikoreksi 9 Okt: BARU naik 90,6%, +0,73%/sinyal, portofolio +7,7%/th DD -14%). tetap20 = 20 koin spot_model.json
        # (= cloud; angka uji lebih tinggi karena koin dipilih hari ini). koin: [..] = daftar sendiri (belum diuji).
        "semesta": "volume20",
        "koin": [],
        "pra_pilih": 60,                 # volume20: ambil kline 1d hanya untuk 60 pair volume 24 jam terbesar
        "filter_btc_sma200": True,       # teruji: DD BARU -40% -> -14% (tanpa filter LAMA lebih untung)
        "filter_kualitas": False,        # teruji netral (D2); boleh dinyalakan
        "persen_modal": 0.10,            # 10% ekuitas per koin (portofolio teruji 10 slot)
        "min_persen_target": 0.5,
        "maks_posisi": 10,
        "peringatan_turun": [0.10, 0.20],
        "jendela_jam": 1,                # beli otomatis hanya 00:05–01:00 UTC (07:05–08:00 WIB); di luar itu hanya kabar
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
    try:
        if os.name != "nt" and path.stat().st_mode & 0o077:
            print(f"⚠️ {path} bisa dibaca pengguna lain. Jalankan: chmod 600 {path}", flush=True)
    except OSError:
        pass
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
    sp = cfg["spot_dip"]
    if sp.get("semesta") not in ("volume20", "tetap20"):
        raise ValueError("spot_dip.semesta harus volume20 atau tetap20")
    for nama in ("listing_dip", "spot_dip"):
        if not 0 < float(cfg[nama]["persen_modal"]) <= 0.5:
            raise ValueError(f"{nama}.persen_modal harus 0..0,5")
    q = str(cfg["bursa"].get("quote", "USDT")).upper()
    if q not in ("USDT", "USDC", "FDUSD"):
        raise ValueError("bursa.quote harus USDT/USDC/FDUSD (IDR tidak didukung: sinyal memakai harga Binance USDT)")


def rahasia(nama: str) -> str:
    return os.environ.get(nama, "").strip()
