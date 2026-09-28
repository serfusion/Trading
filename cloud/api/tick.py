"""Endpoint Vercel: GET /api/tick?key=<CRON_SECRET>  (dipanggil Supabase pg_cron)."""
import json
import os
import sys
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


def run() -> tuple[int, dict]:
    env = os.environ
    missing = [k for k in ("TWELVEDATA_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "NTFY_TOPIC")
               if not env.get(k)]
    if missing:
        return 500, {"ok": False, "error": f"Environment variable belum diisi: {', '.join(missing)}"}
    cfg = {**_core.CFG, "legs": int(env.get("LEGS", _core.CFG["legs"])),
           "leg_lot": float(env.get("LEG_LOT", _core.CFG["leg_lot"])),
           "max_leg_lot": float(env.get("MAX_LEG_LOT", 0.10)),
           "star_only": env.get("STAR_ONLY", "0") == "1"}   # 1 = hanya kirim sinyal ⭐
    result = _core.tick(
        datetime.now(timezone.utc),
        _core.TwelveData(env["TWELVEDATA_API_KEY"], env.get("SYMBOL", "XAU/USD")),
        _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"]),
        _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
        cfg,
        symbol=env.get("SYMBOL", "XAU/USD"),
        executor=executor_from_env(),
    )
    try:                                   # sinyal BTC/USD (24 jam, state di baris 'btc', tanpa auto order)
        if env.get("BTC_SIGNALS", "1") == "1":
            now = datetime.now(timezone.utc)
            store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
            btc = _core.tick(now, _core.TwelveData(env["TWELVEDATA_API_KEY"], "BTC/USD"),
                             _core.RowStore(store, "btc"),
                             _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
                             {**_core.BTC_CFG, "skip_fn": btc_skip_fn(store, now, result)}, symbol="BTC/USD")
            result["btc"] = {k: btc.get(k) for k in ("ok", "price", "events", "error")}
    except Exception as exc:  # noqa: BLE001 - BTC tidak boleh mengganggu sinyal XAU
        result["btc_error"] = str(exc)
    try:                                   # sinyal gap pekan forex (hanya ambil data saat perlu)
        import _gap
        now = datetime.now(timezone.utc)
        store = _core.Supabase(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
        if env.get("GAP_SIGNALS", "1") == "1" and _gap.needs_data(now, store):
            feeds = {p: _core.TwelveData(env["TWELVEDATA_API_KEY"], p) for p in _gap.PAIRS}
            usdchf = lambda: _core.TwelveData(env["TWELVEDATA_API_KEY"], "USD/CHF").candles(2)[-1].c  # noqa: E731
            result["gap"] = _gap.gap_tick(now, feeds, store,
                                          _core.Ntfy(env["NTFY_TOPIC"], env.get("NTFY_SERVER", "https://ntfy.sh")),
                                          usdchf)
    except Exception as exc:  # noqa: BLE001 - gap tidak boleh mengganggu sinyal XAU
        result["gap_error"] = str(exc)
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
