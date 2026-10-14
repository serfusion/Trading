"""👥 Sentimen ORANG emas (14 Okt 2026, permintaan pengguna "kebanyakan orang di seluruh dunia bereaksi apa? buy atau
sell … di bawah XAU poin-poin: tutup kertas, konsensus, survei orang"). INFO saja — research/sentimen_orang.py menguji 6
sumber (survei Kitco Main Street & Wall Street, StockTwits, Wikipedia, COT trader kecil, Google Trends 'buy/sell gold',
survei konsumen UMich/OECD): TIDAK ADA yang menambah ketepatan arah emas sejak Okt 2021 (docs/SENTIMEN_ORANG.md) → baris ini
tidak pernah mengubah arah/persen berita.

Sumber live (gagal satu → dilewati):
- Kitco: survei mingguan terbaru (GraphQL kategori emas → artikel → "N votes … P% naik / Q% turun").
- FXSSI: rata-rata % posisi BUY XAUUSD dari ±9 broker ritel (Myfxbook, OANDA, Dukascopy, FXBlue, XM, …).
- CFTC COT: % long trader kecil (non-reportable) futures emas, laporan mingguan.
Cache baris Supabase 'sentimen' (FXSSI 1 jam, Kitco & COT 12 jam). Env SENTIMEN=0 mematikan.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
GQL = "https://cms.prod.kitco.com/graphql"
Q_KAT = ("query N($urlAlias: String!, $limit: Int, $offset: Int) { nodeListByCategory(limit: $limit, offset: $offset, "
         "urlAlias: $urlAlias, includeRelatedCategories: true, includeEntityQueues: false) { items { ... on NewsArticle "
         "{ title urlAlias } } } }")
FXSSI = "https://fxssi.com/api/current-ratios"
COT = ("https://publicreporting.cftc.gov/resource/72hh-3qpy.json?cftc_contract_market_code=088691"
       "&$order=report_date_as_yyyy_mm_dd%20DESC&$limit=1"
       "&$select=report_date_as_yyyy_mm_dd,nonrept_positions_long_all,nonrept_positions_short_all")
TTL = {"fxssi": timedelta(hours=1), "kitco": timedelta(hours=12), "cot": timedelta(hours=12)}
JEDA_GAGAL = timedelta(minutes=30)                 # sumber gagal → coba lagi paling cepat 30 menit kemudian
_F = Path(__file__).with_name("sentimen.json")
UJI = json.loads(_F.read_text(encoding="utf-8")) if _F.exists() else {}


def aktif(env=None) -> bool:
    return (os.environ if env is None else env).get("SENTIMEN", "1") != "0"


def _get(url: str, opener=None, data: bytes | None = None, timeout: float = 6) -> bytes:
    h = {"User-Agent": UA}
    if data is not None:
        h.update({"Content-Type": "application/json", "Origin": "https://www.kitco.com"})
    with (opener or urllib.request.urlopen)(urllib.request.Request(url, data=data, headers=h), timeout=timeout) as r:
        return r.read()


# ───────────── pengurai survei Kitco (sama dengan research/sentimen_orang.kitco_parse) ─────────────
NAIK = r"higher|rise|rising|gain|bullish|climb|rally|increase|go up|move up|advance|upside"
TURUN = r"lower|fall|declin|drop|lose|losing|lost|bearish|retreat|down|weak|correct|slip|slide|dip|sell"
DATAR = r"sideways|neutral|flat|range|consolidat|unchanged|sidelines|churn|couldn|undecided|unsure"


def _teks(page: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace(" ", " ")
    return re.sub(r"\s+", " ", t)


def _klas(s: str) -> str | None:
    s = s.lower()
    pos = {k: (m.start() if (m := re.search(p, s)) else 10**6) for k, p in (("up", NAIK), ("down", TURUN), ("side", DATAR))}
    k = min(pos, key=pos.get)
    return k if pos[k] < 10**6 else None


def _tiga(seg: str) -> dict:
    out: dict[str, float] = {}
    hits = list(re.finditer(r"(\d+(?:\.\d+)?)\s*%", seg))
    for i, m in enumerate(hits):
        akhir = hits[i + 1].start() if i + 1 < len(hits) else len(seg)
        k = _klas(seg[m.end(): min(akhir, m.end() + 160)])
        if k and k not in out:
            out[k] = float(m.group(1))
    return out


def kitco_parse(page: str) -> dict:
    t = _teks(page)
    r: dict = {}
    m = re.search(r"([\d,]+)\s+(?:votes|readers|respondents|participants|online voters)[^.]{0,80}?(?:cast|participat|"
                  r"took part|responded|voted)[^.]*\.", t, re.I) or \
        re.search(r"(?:online poll|Main Street poll)[^.]{0,120}?([\d,]+)\s+(?:votes|voters|participants)", t, re.I)
    if m:
        r["ms_n"] = int(m.group(1).replace(",", ""))
        r.update({f"ms_{k}": v for k, v in _tiga(t[m.start(): m.start() + 900]).items()})
    w = re.search(r"([\d,]+|\w+)\s+(?:Wall Street analysts|analysts|experts|market professionals|industry experts)[^.]{0,60}?"
                  r"(?:participated|took part|weighed in|responded)", t, re.I)
    if w:
        ujung = m.start() if m and m.start() > w.start() else w.start() + 900
        r.update({f"ws_{k}": v for k, v in _tiga(t[w.start(): ujung]).items()})
    return r


def kitco(opener=None) -> dict | None:
    body = json.dumps({"query": Q_KAT, "variables": {"urlAlias": "/news/category/commodities/gold", "limit": 40,
                                                     "offset": 0}}).encode()
    items = (json.loads(_get(GQL, opener, body)).get("data") or {}).get("nodeListByCategory", {}).get("items") or []
    sv = sorted((i["urlAlias"] for i in items if i and ("main-street" in i.get("urlAlias", "")
                                                       or "Main Street" in (i.get("title") or ""))), reverse=True)
    if not sv:
        return None
    r = kitco_parse(_get("https://www.kitco.com" + sv[0], opener, timeout=8).decode("utf-8", "replace"))
    if not r.get("ms_n") or "ms_up" not in r or "ms_down" not in r:
        return None
    m = re.search(r"/(20\d\d-\d\d-\d\d)/", sv[0])
    return {"tgl": m.group(1) if m else None, **r}


def fxssi(opener=None) -> dict | None:
    d = json.loads(_get(FXSSI, opener))
    v = [float(b["XAUUSD"]) for b in (d.get("brokers") or {}).values() if isinstance(b, dict) and b.get("XAUUSD")]
    if not v:
        return None
    return {"buy": round(sum(v) / len(v)), "n_broker": len(v)}


def cot(opener=None) -> dict | None:
    rows = json.loads(_get(COT, opener))
    if not rows:
        return None
    r = rows[0]
    lo, sh = float(r["nonrept_positions_long_all"]), float(r["nonrept_positions_short_all"])
    return {"tgl": r["report_date_as_yyyy_mm_dd"][:10], "long": round(100 * lo / (lo + sh))}


SUMBER = {"fxssi": fxssi, "kitco": kitco, "cot": cot}


def ambil(store, now: datetime, opener=None, sumber=None) -> dict:
    """{fxssi, kitco, cot} dari cache Supabase 'sentimen' atau sumber live (yang gagal → nilai cache lama / tidak ada)."""
    sumber = sumber or SUMBER
    cache = {}
    if store is not None:
        try:
            cache = store.get_state("sentimen") or {}
        except Exception:  # noqa: BLE001
            cache = {}
    out, ubah = {}, False
    for k, fn in sumber.items():
        c = cache.get(k) or {}
        segar = c.get("t") and now - datetime.fromisoformat(c["t"]) < TTL.get(k, timedelta(hours=6)) and c.get("v")
        jeda = c.get("gagal") and now - datetime.fromisoformat(c["gagal"]) < JEDA_GAGAL   # jangan memperlambat tiap GET
        if segar or jeda:
            if c.get("v"):
                out[k] = c["v"]
            continue
        try:
            v = fn(opener)
        except Exception:  # noqa: BLE001 - situs tidak menjawab → pakai nilai lama bila ada
            v = None
        if v:
            cache[k], ubah = {"t": now.isoformat(), "v": v}, True
            out[k] = v
        else:
            cache[k], ubah = {**c, "gagal": now.isoformat()}, True
            if c.get("v"):
                out[k] = c["v"]
    if ubah and store is not None:
        try:
            store.save_state(cache, "sentimen")
        except Exception:  # noqa: BLE001
            pass
    return out


def _p(x: float) -> str:
    return f"{x:.0f}%"


def poin(s: dict) -> str | None:
    """SATU poin ringkas: "👥 Orang: Kitco 206 suara naik 45% / turun 37% • ritel 9 broker BUY 68% • trader kecil COT
    long 76% → info (diuji: tidak menambah ketepatan)"."""
    bag = []
    k = s.get("kitco")
    if k:
        bag.append(f"survei {_p(k['ms_up'])} naik")
    f = s.get("fxssi")
    if f:
        bag.append(f"ritel {_p(f['buy'])} BUY")
    c = s.get("cot")
    if c:
        bag.append(f"COT {_p(c['long'])} long")
    if not bag:
        return None
    return "👥 Orang: " + " • ".join(bag) + " (info, tidak mengubah arah)"


def attach(persiapan: dict, store, now: datetime | None = None, opener=None, env=None) -> None:
    if not isinstance(persiapan, dict) or not aktif(env):
        return
    now = now or datetime.now(timezone.utc)
    s = ambil(store, now, opener)
    if s:
        persiapan["sentimen"] = {**s, "poin": poin(s), "uji": UJI.get("ringkas")}
