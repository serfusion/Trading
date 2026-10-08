"""Sniper bot Telegram — python -m sniper_bot <perintah> [--config sniper_bot/config.yaml]

  jalan          jalankan bot (loop 24 jam; Telegram + strategi). Mode kertas/live dari config.yaml
  cek            satu putaran tanpa Telegram (pesan dicetak ke layar) — uji koneksi data & strategi
  chat-id        tampilkan chat_id dari pesan terakhir yang dikirim ke bot (langkah setelan)
  uji-telegram   kirim pesan uji ke chat_id di .env
  uji-bursa      cek kunci API bursa: saldo & pasar (TANPA order)
  replay         uji ulang strategi listing_dip memakai kode bot yang sama pada data 2017-2026 (repo)
"""
from __future__ import annotations

import argparse
import sys
import time

from . import config as konfig
from .broker import KertasBroker, LiveBroker
from .mesin import Mesin
from .pasar import Binance
from .state import Store
from .telegram import Telegram, TelegramMati


def buat_broker(cfg: dict, store: Store):
    b = cfg["bursa"]
    if cfg["mode"] == "live":
        return LiveBroker(b["ccxt_id"], konfig.rahasia("BURSA_API_KEY"), konfig.rahasia("BURSA_API_SECRET"),
                          konfig.rahasia("BURSA_API_PASSWORD"), b.get("quote", "USDT"))
    return KertasBroker(store, float(cfg["modal_kertas_usd"]), float(b["slippage_kertas"]), float(b["biaya_kertas"]))


def buat_telegram(cfg: dict, paksa_mati: bool = False):
    if paksa_mati or not cfg["telegram"].get("aktif", True):
        return TelegramMati()
    ids = [int(x) for x in konfig.rahasia("TELEGRAM_CHAT_ID").replace(";", ",").split(",") if x.strip()]
    if not ids:
        raise SystemExit("TELEGRAM_CHAT_ID kosong. Jalankan `python -m sniper_bot chat-id` setelah mengirim /start ke bot.")
    return Telegram(konfig.rahasia("TELEGRAM_TOKEN"), ids, int(cfg["telegram"].get("interval_poll", 25)))


def buat_mesin(cfg: dict, tg_mati: bool = False) -> Mesin:
    store = Store(cfg["data_dir"])
    m = Mesin(cfg, store, Binance(), buat_broker(cfg, store), buat_telegram(cfg, tg_mati))
    from .strategi.listing_dip import ListingDipMesin
    from .strategi.spot_dip import SpotDipMesin
    if cfg["listing_dip"].get("aktif"):
        m.strategi["listing_dip"] = ListingDipMesin(m)
    if cfg["spot_dip"].get("aktif"):
        m.strategi["spot_dip"] = SpotDipMesin(m)
    if cfg["dex"].get("aktif"):
        from .strategi.dex import DexMesin
        m.strategi["dex"] = DexMesin(m)
    return m


def cmd_chat_id() -> None:
    import json
    import urllib.request
    tok = konfig.rahasia("TELEGRAM_TOKEN")
    if not tok:
        raise SystemExit("isi TELEGRAM_TOKEN di sniper_bot/.env dulu")
    with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=30) as r:
        d = json.loads(r.read())
    seen = {}
    for u in d.get("result", []):
        c = (u.get("message") or {}).get("chat") or {}
        if c:
            seen[c["id"]] = c.get("username") or c.get("first_name") or c.get("title")
    if not seen:
        print("Belum ada pesan. Buka bot kamu di Telegram, kirim /start, lalu jalankan perintah ini lagi.")
    for cid, nama in seen.items():
        print(f"chat_id {cid}  ({nama})  -> tulis di .env: TELEGRAM_CHAT_ID={cid}")


def cmd_uji_bursa(cfg: dict) -> None:
    b = cfg["bursa"]
    lb = LiveBroker(b["ccxt_id"], konfig.rahasia("BURSA_API_KEY"), konfig.rahasia("BURSA_API_SECRET"),
                    konfig.rahasia("BURSA_API_PASSWORD"), b.get("quote", "USDT"))
    print(f"Terhubung ke {lb.nama}: {len(lb.ex.markets)} pasar")
    print(f"Saldo {lb.quote} bebas ≈ ${lb.saldo_usd():,.2f}")
    for base in ("BTC", "ETH", "SOL"):
        print(f"  {base}/{lb.quote}: {'ada' if lb.punya_pasar(base) else 'TIDAK ada'}")
    print("Tidak ada order yang dikirim. Pastikan kunci API TANPA izin penarikan (withdraw).")


def cmd_replay() -> None:
    from pathlib import Path

    import pandas as pd

    from .pasar import Bar
    from .strategi.listing_dip import simulasi
    root = Path(__file__).resolve().parent.parent / "data" / "research" / "eksternal" / "listing"
    m = pd.read_parquet(root / "metrik.parquet")
    cfg = konfig.BAWAAN["listing_dip"]
    data = {}
    for r in m.itertuples():
        h = pd.read_parquet(root / "1h" / f"{r.sym}.parquet")
        data[r.sym] = [Bar(t.timestamp(), o, hh, lo, c) for t, o, hh, lo, c in
                       zip(h.index, h.open, h.high, h.low, h.close)]
    for mode in ("stop", "tutup"):
        rows = []
        for r in m.itertuples():
            tr = simulasi(data[r.sym], r.t.timestamp(), r.p0, cfg, sl_mode=mode)
            if tr:
                rows.append({"sym": r.sym, "tahun": r.t.year, "periode": r.periode, **tr})
        _laporan_replay(pd.DataFrame(rows), len(m), mode, cfg)


def _laporan_replay(d, n_listing: int, mode: str, cfg: dict) -> None:
    judul = {"stop": "SL order stop", "tutup": "SL dicek di close 1 jam (dipakai bot live)"}[mode]
    print(f"\n🎯 listing_dip (kode bot), {judul}, {n_listing} listing Binance 2017-2026: {len(d)} trade")
    for per in ("LAMA", "BARU"):
        x = d[d.periode == per]
        print(f"  {per}: n {len(x)}, menang {(x.ret > 0).mean():.0%}, rata {x.ret.mean():+.1%}, median "
              f"{x.ret.median():+.1%}, terburuk {x.ret.min():+.0%}")
    t = d.groupby("tahun").ret.agg(n="size", rata="mean", menang=lambda v: (v > 0).mean())
    print(t.round(3).to_string())
    print("Alasan keluar:", d.alasan.value_counts().to_dict())
    print("Portofolio (nilai pasar per jam, research/listing_dip_porto.py): lihat docs/eksternal/hasil_listing_dip_porto.txt")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="sniper_bot")
    ap.add_argument("perintah", choices=["jalan", "cek", "chat-id", "uji-telegram", "uji-bursa", "replay"])
    ap.add_argument("--config", default=None)
    ap.add_argument("--putaran", type=int, default=None, help="(uji) berhenti setelah N putaran")
    a = ap.parse_args(argv)
    cfg = konfig.muat(a.config)
    if a.perintah == "chat-id":
        cmd_chat_id()
    elif a.perintah == "uji-telegram":
        tg = buat_telegram(cfg)
        tg.kirim("✅ Uji pesan dari sniper bot. Kalau pesan ini sampai, Telegram sudah benar.", menu=True)
        print("terkirim (cek Telegram)")
    elif a.perintah == "uji-bursa":
        cmd_uji_bursa(cfg)
    elif a.perintah == "replay":
        cmd_replay()
    elif a.perintah == "cek":
        m = buat_mesin(cfg, tg_mati=True)
        t0 = time.time()
        m.satu_putaran()
        import re

        from .perintah import teks_listing, teks_status
        print(re.sub(r"<[^>]+>", "", teks_status(m)))
        print(re.sub(r"<[^>]+>", "", teks_listing(m)))
        print(f"selesai {time.time() - t0:.0f} dtk")
    else:
        m = buat_mesin(cfg)
        try:
            m.jalan(a.putaran)
        except KeyboardInterrupt:
            print("berhenti (Ctrl+C)")


if __name__ == "__main__":
    main(sys.argv[1:])
