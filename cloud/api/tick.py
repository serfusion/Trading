"""Endpoint Vercel: GET /api/tick?key=<CRON_SECRET>  (dipanggil Supabase pg_cron)."""
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(__file__))

import _core  # noqa: E402


def executor_from_env():
    """MetaApi hanya aktif bila token & account id diisi. Auto order tetap OFF sampai dinyalakan dari aplikasi."""
    env = os.environ
    if env.get("METAAPI_TOKEN") and env.get("METAAPI_ACCOUNT_ID"):
        return _core.MetaApi(env["METAAPI_TOKEN"], env["METAAPI_ACCOUNT_ID"],
                             env.get("METAAPI_REGION", "new-york"), env.get("BROKER_SYMBOL", "XAUUSDc"))
    return None


def btc_skip_fn(store, now: datetime, result: dict):
    """Filter BTC 💰 dari riset data eksternal (env BTC_FUNDING_FILTER=0 / BTC_SEPT_FILTER=0 untuk mematikan).
    Cache funding di baris Supabase 'funding'; gagal unduh tidak menghentikan sinyal (filter funding dilewati)."""
    import _funding
    env = os.environ
    use_funding = env.get("BTC_FUNDING_FILTER", "1") == "1"
    cache = {}
    if use_funding:
        try:
            old = store.get_state("funding") or {}
            cache = _funding.refresh(old, now)
            if cache != old:
                store.save_state(cache, "funding")
            f = cache.get("f") or []
            result["funding"] = {"day": cache.get("day"), "n": len(f),
                                 "pct": _funding.percentile_last([v for _, v in f])}
        except Exception as exc:  # noqa: BLE001
            result["funding_error"] = str(exc)
    return lambda direction, t: _funding.skip_reason(direction, t, cache, use_funding,
                                                     env.get("BTC_SEPT_FILTER", "1") == "1", _core.new_york)


def signal_extras(asset: str, store) -> dict:
    """Sinyal berlapis (cloud/api/sinyal_lapis.json, env LAYER_SIGNALS=0 untuk mematikan) & tanda 📰 sinyal setelah
    berita (env NEWS_TAG=0 untuk mematikan) — research/sinyal_lapis.py & sinyal_berita.py, izin pengguna 2 Okt 2026."""
    import _berita_sinyal
    env = os.environ
    out = {}
    path = os.path.join(os.path.dirname(__file__), "sinyal_lapis.json")
    if env.get("LAYER_SIGNALS", "1") == "1" and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            lay = json.load(f).get(asset)
        if lay:
            out["layer"] = lay
    # 🎯 label WR tinggi pada lapisan BTC saat volatilitas ≥ 1,5× normal (izin pengguna 3 Okt 2026); WR_TINGGI=0 mematikan
    if env.get("WR_TINGGI", "1") == "1" and asset in _core.WR_TINGGI:
        out["wr_tinggi"] = _core.WR_TINGGI[asset]
    # 📰 BTC dimatikan 3 Okt 2026 (replay: sejak 2021 −0,06R/sin, tidak lebih baik); NEWS_TAG_BTC=1 menyalakan lagi
    if env.get("NEWS_TAG", "1") == "1" and (asset != "BTC" or env.get("NEWS_TAG_BTC", "0") == "1"):
        def rows():
            import _arsip
            import _chat
            return _arsip.calendar_cached(store, datetime.now(timezone.utc), _chat.fetch_calendar)
        out["news_fn"] = _berita_sinyal.news_fn(asset, store, rows)
    return out


class Keep:
    """Pembungkus feed: simpan candle terakhir supaya 🌊 ikut arus memakai ulang data (tanpa kredit Twelve Data lagi)."""

    def __init__(self, feed):
        self.feed, self.bars = feed, None

    def candles(self, n, interval="1h"):
        out = self.feed.candles(n, interval)
        if interval == "1h":
            self.bars = out
        return out


class KlineFeed:
    """Candle 1 jam koin dari Binance (data-api.binance.vision → api.binance.us; tanpa kredit Twelve Data, sumber sama
    dengan riset research/pair_kripto.py), cadangan Twelve Data. Candle terakhir = yang masih berjalan (seperti TD)."""

    def __init__(self, coin: str, td_key: str):
        self.coin, self.td_key = coin, td_key

    def candles(self, n, interval="1h"):
        for base in ("https://data-api.binance.vision", "https://api.binance.us"):
            try:
                out, end = [], None
                while len(out) < n:
                    q = f"symbol={self.coin}USDT&interval=1h&limit={min(1000, n - len(out))}"
                    rows = _core.http("GET", f"{base}/api/v3/klines?{q}" + (f"&endTime={end}" if end else ""),
                                      timeout=10) or []
                    if not rows:
                        break
                    out = [_core.Bar(datetime.fromtimestamp(r[0] / 1000, timezone.utc), float(r[1]), float(r[2]),
                                     float(r[3]), float(r[4])) for r in rows] + out
                    end = int(rows[0][0]) - 1
                    if len(rows) < 1000:
                        break
                if len(out) >= 500:
                    return out
            except Exception:  # noqa: BLE001 - coba sumber berikutnya
                pass
        return _core.TwelveData(self.td_key, f"{self.coin}/USD").candles(n, interval)


def run() -> tuple[int, dict]:
    started = time.monotonic()           # batas Vercel 60 dtk (vercel.json): spot memakai sisa waktu saja
    env = os.environ
    missing = [k for k in ("TWELVEDATA_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "NTFY_TOPIC")
               if not env.get(k)]
    if missing:
        return 500, {"ok": False, "error": f"Environment variable belum diisi: {', '.join(missing)}"}
    cfg = {**_core.CFG, "legs": int(env.get("LEGS", _core.CFG["legs"])),
           "leg_lot": float(env.get("LEG_LOT", _core.CFG["leg_lot"])),
           "max_leg_lot": float(env.get("MAX_LEG_LOT", 0.10)),
           "star_only": env.get("STAR_ONLY", "0") == "1",   # 1 = hanya kirim sinyal ⭐
           # validasi arah H4 EMA50 untuk 💰 XAU (research/alchemist.py; XAU_H4_FILTER=0 untuk mematikan)
           "h4_filter": env.get("XAU_H4_FILTER", "1") == "1",
           # 🛑 BATAL saat guncangan ekstrem ≥ 4 ATR melawan posisi (research/batal_guncang.py; GUNCANG_BATAL=0 mati)
           "guncang": env.get("GUNCANG_BATAL", "1") == "1"}
    if env.get("XAU_EXTRA_SETS", "1") == "1":   # set 100/40 & 120/50 (research/sinyal_tambahan.py, izin 3 Okt 2026)
        cfg["sets"] = list(_core.CFG["sets"]) + [(100, 40), (120, 50)]
    if env.get("WAR_MODE", "1") == "1":    # ⚠️ mode perang (label saja, XAU tidak dijeda)
        try:
            import _perang
            now = datetime.now(timezone.utc)
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            backup = (lambda: _perang.uso_rows(env["TWELVEDATA_API_KEY"], store, now)) \
                if env.get("WAR_BACKUP", "1") == "1" else None    # cadangan USO bila FRED gagal/basi
            cfg["war"] = _perang.current(now, backup)
        except Exception as exc:  # noqa: BLE001 - FRED gagal tidak boleh menghentikan sinyal
            cfg["war"] = None
            war_error = str(exc)
    main_store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
    if env.get("XAU_NEWS_SKIP", "1") == "1":   # ⏸️ jeda ≤ 60 jam sebelum NFP/CPI/Fed (research/muse_uji.py, izin 7 Okt 2026)
        try:
            import _arsip
            import _chat
            import _jeda_berita
            now = datetime.now(timezone.utc)
            cfg["skip_fn"], cfg["jeda"] = _jeda_berita.siapkan(
                lambda: _arsip.calendar_cached(main_store, now, _chat.fetch_calendar), now, env)
        except Exception as exc:  # noqa: BLE001 - jadwal gagal tidak boleh menghentikan sinyal
            jeda_error = str(exc)
    try:
        cfg.update(signal_extras("XAU", main_store))
    except Exception as exc:  # noqa: BLE001 - tambahan opsional tidak boleh menghentikan sinyal
        result_extra_error = str(exc)
    feeds = {"XAU": Keep(_core.TwelveData(env["TWELVEDATA_API_KEY"], env.get("SYMBOL", "XAU/USD"))),
             "BTC": Keep(_core.TwelveData(env["TWELVEDATA_API_KEY"], "BTC/USD")),
             "ETH": Keep(_core.TwelveData(env["TWELVEDATA_API_KEY"], "ETH/USD"))}
    result = _core.tick(
        datetime.now(timezone.utc),
        feeds["XAU"],
        main_store,
        _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
        cfg,
        symbol=env.get("SYMBOL", "XAU/USD"),
        executor=executor_from_env(),
    )
    result["war"] = cfg.get("war")
    if "result_extra_error" in locals():
        result["extra_error"] = result_extra_error
    if "war_error" in locals():
        result["war_error"] = war_error
    result["jeda"] = cfg.get("jeda")
    if "jeda_error" in locals():
        result["jeda_error"] = jeda_error
    try:                                   # sinyal BTC/USD (24 jam, state di baris 'btc', tanpa auto order)
        if env.get("BTC_SIGNALS", "1") == "1":
            now = datetime.now(timezone.utc)
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            btc = _core.tick(now, feeds["BTC"],
                             _core.RowStore(store, "btc"),
                             _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
                             {**_core.BTC_CFG, "skip_fn": btc_skip_fn(store, now, result), "guncang": cfg["guncang"],
                              # BTC konf dimatikan (research/tanpa_konf.py); BTC_SKIP_KONF=0 untuk menyalakan lagi
                              "skip_cats": ("konf",) if env.get("BTC_SKIP_KONF", "1") == "1" else (),
                              **signal_extras("BTC", store)}, symbol="BTC/USD")
            result["btc"] = {k: btc.get(k) for k in ("ok", "price", "events", "error")}
    except Exception as exc:  # noqa: BLE001 - BTC tidak boleh mengganggu sinyal XAU
        result["btc_error"] = str(exc)
    try:                                   # sinyal ETH/USD: hanya saat sinyal 💰 BTC searah sedang terbuka (izin 3 Okt)
        if env.get("ETH_SIGNALS", "1") == "1":
            now = datetime.now(timezone.utc)
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            bstate = _core.RowStore(store, "btc").get_state() or {}
            btc_dirs = {x["dir"] for s_ in (bstate.get("systems") or {}).values()
                        for x in [s_.get("virtual")] + list(s_.get("layers") or []) if x}
            eth = _core.tick(now, feeds["ETH"],
                             _core.RowStore(store, "eth"),
                             _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
                             {**_core.BTC_CFG, "asset": "ETH", "id_prefix": "ETH-", "skip_cats": ("konf", "biasa"),
                              "guncang": False,          # 13 Okt 2026: 🛑 batal tidak menolong ETH/DOGE/ADA (diuji)
                              "skip_fn": lambda d, t: None if d in btc_dirs else "tidak ada 💰 BTC searah terbuka"},
                             symbol="ETH/USD")
            result["eth"] = {k: eth.get(k) for k in ("ok", "price", "events", "error")}
    except Exception as exc:  # noqa: BLE001 - ETH tidak boleh mengganggu sinyal lain
        result["eth_error"] = str(exc)
    try:                                   # sinyal DOGE/ADA: semua kategori, hanya saat 💰 BTC searah terbuka
        if env.get("KRIPTO_SIGNALS", "1") == "1":     # (izin "pasang semua WR & profit tinggi" 6 Okt 2026)
            now = datetime.now(timezone.utc)
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            bstate = _core.RowStore(store, "btc").get_state() or {}
            btc_dirs = {x["dir"] for s_ in (bstate.get("systems") or {}).values()
                        for x in [s_.get("virtual")] + list(s_.get("layers") or []) if x}
            for sym in [c.strip() for c in env.get("KRIPTO_COINS", "DOGE,ADA").split(",") if c.strip()]:
                feeds[sym] = Keep(KlineFeed(sym, env["TWELVEDATA_API_KEY"]))
                kr = _core.tick(now, feeds[sym], _core.RowStore(store, sym.lower()),
                                _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
                                {**_core.KRIPTO_CFG, "asset": sym, "id_prefix": f"{sym}-", "guncang": False,
                                 "skip_fn": lambda d, t: None if d in btc_dirs else "tidak ada 💰 BTC searah terbuka"},
                                symbol=f"{sym}/USD")
                result[sym.lower()] = {k: kr.get(k) for k in ("ok", "price", "events", "error")}
    except Exception as exc:  # noqa: BLE001 - DOGE/ADA tidak boleh mengganggu sinyal lain
        result["kripto_error"] = str(exc)
    try:                                   # sinyal gap pekan forex (hanya ambil data saat perlu)
        import _gap
        now = datetime.now(timezone.utc)
        store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
        if env.get("GAP_SIGNALS", "1") == "1" and _gap.needs_data(now, store):
            gap_feeds = {p: _core.TwelveData(env["TWELVEDATA_API_KEY"], p) for p in _gap.PAIRS}   # jangan timpa feeds
            usdchf = lambda: _core.TwelveData(env["TWELVEDATA_API_KEY"], "USD/CHF").candles(2)[-1].c  # noqa: E731
            result["gap"] = _gap.gap_tick(now, gap_feeds, store,
                                          _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
                                          usdchf)
    except Exception as exc:  # noqa: BLE001 - gap tidak boleh mengganggu sinyal XAU
        result["gap_error"] = str(exc)
    try:                                   # 🌊 ikut arus (izin pengguna 6 Okt 2026; ARUS_SIGNALS=0 mati)
        if env.get("ARUS_SIGNALS", "1") == "1":
            import _arus
            _arus.GUNCANG_ON = cfg["guncang"]
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            result["arus"] = _arus.arus_tick(datetime.now(timezone.utc),
                                             {k: f.bars for k, f in feeds.items() if f.bars},
                                             _core.RowStore(store, "arus"),
                                             _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")))
    except Exception as exc:  # noqa: BLE001 - ikut arus tidak boleh mengganggu sinyal lain
        result["arus_error"] = str(exc)
    try:                                   # 🔗 emas pulih → kripto ikut naik (izin pengguna 9 Okt 2026; PULIH_SIGNALS=0 mati)
        if env.get("PULIH_SIGNALS", "1") == "1":
            import _pulih
            _pulih.GUNCANG_ON = cfg["guncang"]
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            result["pulih"] = _pulih.pulih_tick(datetime.now(timezone.utc), feeds["XAU"].bars or [],
                                                _core.RowStore(store, "pulih"),
                                                _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")))
    except Exception as exc:  # noqa: BLE001 - pulih tidak boleh mengganggu sinyal lain
        result["pulih_error"] = str(exc)
    try:                                   # 📝 rekam hasil berita tiap jam (15 Okt 2026; _rekam.py, REKAM_HASIL=0 mati)
        import _arsip
        import _chat
        import _rekam
        now = datetime.now(timezone.utc)
        result["rekam"] = _rekam.jalankan(main_store, now, env,
                                          lambda: _arsip.calendar_cached(main_store, now, _chat.fetch_calendar))
    except Exception as exc:  # noqa: BLE001 - rekam hasil berita tidak boleh mengganggu sinyal
        result["rekam_error"] = str(exc)[:200]
    try:                                   # 💎 sinyal spot Binance harian (izin pengguna 4 Okt 2026; SPOT_SIGNALS=0 mati)
        if env.get("SPOT_SIGNALS", "1") == "1":
            import _spot
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            result["spot"] = _spot.spot_tick(datetime.now(timezone.utc), _core.RowStore(store, "spot"),
                                             _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
                                             env.get("TWELVEDATA_API_KEY"), max_open=int(env.get("SPOT_MAX", "10")),
                                             deadline_s=max(3.0, 45.0 - (time.monotonic() - started)),
                                             # ⚠️ guncangan spot = peringatan; SPOT_BATAL=1 paksa jual (tidak disarankan)
                                             paksa_jual=env.get("SPOT_BATAL", "0") == "1")
    except Exception as exc:  # noqa: BLE001 - spot tidak boleh mengganggu sinyal lain
        result["spot_error"] = str(exc)
    return 200, result


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        secret = os.environ.get("CRON_SECRET", "")
        key = parse_qs(urlparse(self.path).query).get("key", [""])[0]
        auth = self.headers.get("Authorization", "")
        if not secret or (key != secret and auth != f"Bearer {secret}"):
            self._send(401, {"ok": False, "error": "kunci salah atau CRON_SECRET belum diisi"})
            return
        try:
            code, body = run()
        except Exception as exc:  # noqa: BLE001
            code, body = 500, {"ok": False, "error": str(exc), "trace": traceback.format_exc()[-800:]}
        self._send(code, body)

    do_POST = do_GET
