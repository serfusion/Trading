"""👥 Rangkuman posisi copy trader untuk aplikasi (GET /api/chat?copyposisi=<platform>|<id>), aplikasi 4.13.

Permintaan pengguna 6 Okt 2026: "rangkum semuanya sebelum dikirim ke apk" — cloud (bukan HP; binance.com diblokir
operator di Indonesia) membaca endpoint publik tiap situs lalu mengirim ringkasan siap tampil:
  posisi  : posisi terbuka (arah, entry, harga sekarang, TP, SL, leverage, untung %) — sejauh dibuka situsnya
  riwayat : 10 trade terakhir yang sudah ditutup (arah, entry, harga tutup, gerak harga %, TP/SL bila ada, tanggal)
  ringkas : satu kalimat (menang x/n, rata-rata gerak, arah & koin favorit, lama tahan)
Gerak harga % = (tutup − entry)/entry × arah ×100, TANPA leverage (supaya bisa ditiru di akun sendiri).
Info saja — tidak ada order. Cache 3 menit per trader di memori fungsi.
"""
from __future__ import annotations

import json
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 "
                    "Safari/537.36", "Accept": "application/json", "Content-Type": "application/json"}
_CACHE: dict[str, tuple[float, dict]] = {}
TTL = 180


def _req(url: str, body: dict | None = None, timeout: float = 12):
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=timeout) as r:
        return json.load(r)


def _f(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x not in (0.0, -1.0) else None


def _lev(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _move(entry, close, buy) -> float | None:
    if not entry or not close or buy is None:
        return None
    return round((close - entry) / entry * (1 if buy else -1) * 100, 2)


def _iso(ms) -> str | None:
    try:
        return datetime.fromtimestamp(float(ms) / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    except (TypeError, ValueError, OSError):
        return None


def _pos(symbol, buy, entry, now, tp=None, sl=None, lev=None, pnl=None) -> dict:
    return {"symbol": symbol, "arah": None if buy is None else ("BUY" if buy else "SELL"), "entry": entry, "now": now,
            "tp": tp, "sl": sl, "lev": _lev(lev), "untung": None if pnl is None else round(pnl, 2)}


def _trade(symbol, buy, entry, close, t_open=None, t_close=None, tp=None, sl=None, lev=None) -> dict:
    return {"symbol": symbol, "arah": None if buy is None else ("BUY" if buy else "SELL"), "entry": entry,
            "tutup": close, "gerak": _move(entry, close, buy), "tp": tp, "sl": sl, "lev": _lev(lev),
            "buka": _iso(t_open), "waktu": _iso(t_close)}


# ------------------------------------------------------------------ per situs
def binance(pid: str) -> tuple[list, list, str]:
    base = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade"
    with ThreadPoolExecutor(2) as ex:
        fp = ex.submit(_req, f"{base}/lead-data/positions?portfolioId={pid}")
        fh = ex.submit(_req, f"{base}/lead-portfolio/position-history",
                       {"pageNumber": 1, "pageSize": 10, "portfolioId": str(pid)})
        pos_raw = (fp.result().get("data") or [])
        hist_raw = ((fh.result().get("data") or {}).get("list") or [])
    pos = []
    for p in pos_raw:
        amt = _f(p.get("positionAmount"))
        if not amt:
            continue
        entry, lev = _f(p.get("entryPrice")), int(p.get("leverage") or 1)
        pnl, margin = _f(p.get("unrealizedProfit")), (abs(amt) * entry / lev if entry else None)
        pos.append(_pos(p.get("symbol"), amt > 0, entry, _f(p.get("markPrice")), lev=lev,
                        pnl=pnl / margin * 100 if pnl is not None and margin else None))
    hist = [_trade(h.get("symbol"), h.get("side") == "Long", _f(h.get("avgCost")), _f(h.get("avgClosePrice")),
                   h.get("opened"), h.get("closed"), lev=int(float(h.get("leverage") or 1))) for h in hist_raw]
    note = "" if pos else "Trader menyembunyikan posisi terbuka (atau sedang tidak ada posisi). TP/SL tidak dibuka Binance."
    return pos, hist, note


def okx_side(p: dict) -> bool | None:
    """Arah posisi OKX: posSide long/short; mode 'net' → tanda subPos (positif = BUY)."""
    side = p.get("posSide")
    if side in ("long", "short"):
        return side == "long"
    v = _f(p.get("subPos")) or _f(p.get("pos"))
    return None if v is None else v > 0


def okx(code: str) -> tuple[list, list, str]:
    base = "https://www.okx.com/api/v5/copytrading"
    with ThreadPoolExecutor(2) as ex:
        fp = ex.submit(_req, f"{base}/public-current-subpositions?instType=SWAP&uniqueCode={code}&limit=20")
        fh = ex.submit(_req, f"{base}/public-subpositions-history?instType=SWAP&uniqueCode={code}&limit=10")
        pos_raw, hist_raw = fp.result().get("data") or [], fh.result().get("data") or []
    pos = [_pos((p.get("instId") or "(disembunyikan)").replace("-SWAP", ""), okx_side(p),
                _f(p.get("openAvgPx")), _f(p.get("markPx")), lev=p.get("lever"),
                pnl=(_f(p.get("uplRatio")) or 0) * 100) for p in pos_raw[:10]]
    hist = [_trade((h.get("instId") or "?").replace("-SWAP", ""), okx_side(h), _f(h.get("openAvgPx")),
                   _f(h.get("closeAvgPx")), h.get("openTime"), h.get("closeTime") or None, lev=h.get("lever"))
            for h in hist_raw]
    hidden = any(not p.get("instId") for p in pos_raw)
    note = ("Koin & harga posisi terbuka disembunyikan trader. " if hidden else "") + "TP/SL tidak dibuka OKX."
    return pos, hist, note


def bitget(uid: str) -> tuple[list, list, str]:
    base = "https://www.bitget.com/v1/trigger/trace"
    body = {"languageType": 0, "traderUid": uid, "triggerUserId": uid, "pageNo": 1, "pageSize": 10}
    with ThreadPoolExecutor(2) as ex:
        fp = ex.submit(_req, f"{base}/public/traderPosition", {"languageType": 0, "traderUid": uid})
        fh = ex.submit(_req, f"{base}/order/newHistoryList", body)
        pos_raw = fp.result().get("data") or []
        hist_raw = ((fh.result().get("data") or {}).get("rows") or [])
    side = {1: True, 2: False}
    pos = []
    for p in pos_raw[:10]:
        if not isinstance(p, dict):
            continue
        sym, buy, entry = p.get("symbolDisplayName"), side.get(p.get("holdSide")), _f(p.get("openAvgPrice"))
        now = None
        try:                                    # harga sekarang dari ticker publik Bitget
            t = _req(f"https://api.bitget.com/api/v2/mix/market/ticker?productType=USDT-FUTURES&symbol={sym}", timeout=6)
            now = _f((t.get("data") or [{}])[0].get("lastPr"))
        except Exception:  # noqa: BLE001
            pass
        lev = _lev(p.get("openLevel"))
        mv = _move(entry, now, buy)
        pos.append(_pos(sym, buy, entry, now, lev=lev, pnl=mv * lev if mv is not None and lev else None))
    hist = [_trade(h.get("symbolDisplayName"), side.get(h.get("position")), _f(h.get("openAvgPrice")),
                   _f(h.get("closeAvgPrice")), h.get("openTime"), h.get("closeTime"), _f(h.get("stopProfitPrice")),
                   _f(h.get("stopLossPrice")), h.get("openLevel")) for h in hist_raw]
    note = "" if pos else "Tidak ada posisi terbuka atau trader mengaktifkan perlindungan posisi."
    return pos, hist, note


def hyperliquid(addr: str) -> tuple[list, list, str]:
    url = "https://api.hyperliquid.xyz/info"
    with ThreadPoolExecutor(3) as ex:
        fs = ex.submit(_req, url, {"type": "clearinghouseState", "user": addr})
        fo = ex.submit(_req, url, {"type": "frontendOpenOrders", "user": addr})
        ff = ex.submit(_req, url, {"type": "userFills", "user": addr})
        st, orders, fills = fs.result(), fo.result() or [], ff.result() or []
    tp, sl = {}, {}
    for o in orders:
        px, t = _f(o.get("triggerPx")), str(o.get("orderType") or "")
        if px and "Take Profit" in t:
            tp[o.get("coin")] = px
        elif px and "Stop" in t:
            sl[o.get("coin")] = px
    aps = [a["position"] for a in st.get("assetPositions") or []]
    aps.sort(key=lambda p: -abs(_f(p.get("positionValue")) or 0))
    pos = []
    for p in aps[:10]:
        szi, val = _f(p.get("szi")) or 0, _f(p.get("positionValue"))
        pos.append(_pos(p.get("coin"), szi > 0, _f(p.get("entryPx")), abs(val / szi) if val and szi else None,
                        tp.get(p.get("coin")), sl.get(p.get("coin")), (p.get("leverage") or {}).get("value"),
                        (_f(p.get("returnOnEquity")) or 0) * 100))
    # riwayat: gabung fill penutupan per (koin, waktu) → harga tutup rata-rata; entry = tutup ∓ PnL/ukuran
    agg: dict[tuple, dict] = {}
    for f in fills:
        if not str(f.get("dir", "")).startswith("Close") or _f(f.get("closedPnl")) is None:
            continue
        k = (f.get("coin"), f.get("time"), f.get("dir"))
        a = agg.setdefault(k, {"sz": 0.0, "pxsz": 0.0, "pnl": 0.0})
        sz, px = float(f.get("sz") or 0), float(f.get("px") or 0)
        a["sz"] += sz
        a["pxsz"] += px * sz
        a["pnl"] += float(f.get("closedPnl") or 0)
    hist = []
    for (coin, t, d), a in sorted(agg.items(), key=lambda kv: -kv[0][1])[:10]:
        if a["sz"] <= 0:
            continue
        close = a["pxsz"] / a["sz"]
        buy = "Long" in d
        entry = close - a["pnl"] / a["sz"] if buy else close + a["pnl"] / a["sz"]
        hist.append(_trade(coin, buy, round(entry, 6), round(close, 6), None, t))
    return pos, hist, "" if pos else "Tidak ada posisi terbuka."


def etoro(cid: str) -> tuple[list, list, str]:
    base = "https://www.etoro.com/sapi/trade-data-real"
    start = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%dT00:00:00.000Z")
    with ThreadPoolExecutor(2) as ex:
        fp = ex.submit(_req, f"{base}/live/public/portfolios?cid={cid}&format=json")
        fh = ex.submit(_req, f"{base}/history/public/credit/flat?CID={cid}&ItemsPerPage=10&PageNumber=1&StartTime={start}")
        pf, hs = fp.result(), fh.result()
    agg = sorted(pf.get("AggregatedPositions") or [], key=lambda a: -(a.get("Invested") or 0))[:6]
    hist_raw = (hs.get("PublicHistoryPositions") or [])[:10]
    ids = sorted({a["InstrumentID"] for a in agg} | {h["InstrumentID"] for h in hist_raw})
    names = {}
    if ids:
        try:
            m = _req("https://api.etorostatic.com/sapi/instrumentsmetadata/V1.1/instruments?InstrumentIds="
                     + ",".join(map(str, ids)))
            names = {x["InstrumentID"]: x.get("SymbolFull") or x.get("InstrumentDisplayName") for x in
                     m.get("InstrumentDisplayDatas") or []}
        except Exception:  # noqa: BLE001
            pass

    def detail(a):
        iid = a["InstrumentID"]
        entry = now = tp = sl = None
        lev = 1
        try:
            p = _req(f"{base}/live/public/positions?cid={cid}&InstrumentID={iid}&format=json")
            entry = _f(p.get("AverageOpen"))
            ps = p.get("PublicPositions") or []
            last = max(ps, key=lambda q: q.get("OpenDateTime") or "") if ps else None
            if last:
                now, lev = _f(last.get("CurrentRate")), last.get("Leverage") or 1
                e = entry or _f(last.get("OpenRate")) or 0
                # TP/SL "kosong" eToro = nilai ekstrem (±10× harga, 0,0001) → dianggap tidak ada
                tpv, slv = _f(last.get("TakeProfitRate")), _f(last.get("StopLossRate"))
                tp = tpv if tpv is not None and e > 0 and 0.2 <= tpv / e <= 3.0 else None
                sl = slv if slv is not None and e > 0 and 0.2 <= slv / e <= 3.0 else None
        except Exception:  # noqa: BLE001
            pass
        return _pos(names.get(iid, f"ID {iid}"), a.get("Direction") != "Sell", entry, now, tp, sl, lev, a.get("NetProfit"))
    with ThreadPoolExecutor(6) as ex:
        pos = list(ex.map(detail, agg))
    hist = [_trade(names.get(h["InstrumentID"], f"ID {h['InstrumentID']}"), bool(h.get("IsBuy")), _f(h.get("OpenRate")),
                   _f(h.get("CloseRate")), None, None, lev=h.get("Leverage"))
            | {"buka": (h.get("OpenDateTime") or "")[:16] + "Z", "waktu": (h.get("CloseDateTime") or "")[:16] + "Z"}
            for h in hist_raw]
    return pos, hist, "" if pos else "Tidak ada posisi terbuka."


SITUS = {"Binance": binance, "OKX": okx, "Bitget": bitget, "Hyperliquid": hyperliquid, "eToro": etoro}


def ringkas(hist: list[dict]) -> str:
    g = [h["gerak"] for h in hist if h.get("gerak") is not None]
    if not g:
        return ""
    win = sum(1 for x in g if x > 0)
    arah = Counter(h["arah"] for h in hist if h.get("arah"))
    koin = Counter(h["symbol"] for h in hist if h.get("symbol"))
    s = f"{len(g)} trade terakhir: untung {win}/{len(g)}, rata-rata gerak harga {sum(g) / len(g):+.2f}%"
    if arah:
        a, n = arah.most_common(1)[0]
        s += f", lebih sering {a} ({n}/{sum(arah.values())})"
    if koin:
        s += f", paling sering {koin.most_common(1)[0][0]}"
    lama = []
    for h in hist:
        try:
            lama.append((datetime.fromisoformat(h["waktu"].replace("Z", "+00:00"))
                         - datetime.fromisoformat(h["buka"].replace("Z", "+00:00"))).total_seconds() / 3600)
        except (TypeError, ValueError, AttributeError, KeyError):
            pass
    if lama:
        med = sorted(lama)[len(lama) // 2]
        s += f", tahan ±{med:.0f} jam" if med < 48 else f", tahan ±{med / 24:.0f} hari"
    return s + "."


def copyposisi(platform: str, id_: str, now: float | None = None) -> dict:
    now = now or time.time()
    key = f"{platform}|{id_}"
    if key in _CACHE and now - _CACHE[key][0] < TTL:
        return _CACHE[key][1]
    fn = SITUS.get(platform)
    if fn is None:
        out = {"ok": True, "posisi": [], "riwayat": [], "ringkas": "",
               "catatan": "MQL5 hanya membuka posisi & riwayat untuk pelanggan sinyal."}
    else:
        try:
            pos, hist, note = fn(id_)
            out = {"ok": True, "posisi": pos, "riwayat": hist, "ringkas": ringkas(hist), "catatan": note,
                   "waktu": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "posisi": [], "riwayat": [], "ringkas": "",
                    "catatan": f"Gagal membaca {platform}: {type(exc).__name__}"}
    _CACHE[key] = (now, out)
    return out
