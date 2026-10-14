"""👥 Sentimen ORANG (buy/sell) untuk emas — survei, posisi retail, percakapan (14 Okt 2026, docs/SENTIMEN_ORANG.md).

python -m research.sentimen_orang kitco      → cari & baca semua survei mingguan Kitco (Wall Street + Main Street)
python -m research.sentimen_orang stocktwits [jam]  → kumpulkan pesan berlabel Bullish/Bearish (GLD, XAUUSD, GC_F)
python -m research.sentimen_orang wiki       → kunjungan Wikipedia (perhatian publik) harian sejak Jul 2015
python -m research.sentimen_orang uji        → uji tutup kertas (per arah, LAMA/BARU, vs selalu-NAIK)
                                               → docs/eksternal/hasil_sentimen_orang.txt

Data di data/research/eksternal/sentimen/. Sumber yang diblokir/berbayar dicatat di docs (Myfxbook butuh login,
IG/OANDA butuh akun API, AAII 403, CNN Fear&Greed 418, Reddit 403, FXSSI riwayat berbayar — hanya potret kini).
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "sentimen"
OUT = ROOT / "docs" / "eksternal" / "hasil_sentimen_orang.txt"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
BARU = pd.Timestamp("2021-10-01")


def _get(url: str, data: bytes | None = None, headers: dict | None = None, coba: int = 4) -> bytes:
    h = {"User-Agent": UA, **(headers or {})}
    for i in range(coba):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=40) as r:
                return r.read()
        except Exception as e:                      # noqa: BLE001 — 429/5xx: tunggu lalu ulang
            if i == coba - 1:
                raise
            time.sleep(3 * (i + 1))
            print("  ulang", url[:80], e, file=sys.stderr)
    return b""


# ───────────────────────────── Kitco: survei mingguan Wall Street (analis) & Main Street (orang umum) ─────────────
GQL = "https://cms.prod.kitco.com/graphql"
Q_CARI = ("query SearchNews($query: String!, $sort: String!, $limit: Int, $offset: Int) { searchData: search(query: "
          "$query, sort: $sort, limit: $limit, offset: $offset) { total items { title urlAlias updatedAt excerpt } } }")
KATA_CARI = ["Main Street online poll gold", "Kitco gold survey", "Wall Street Main Street gold", "Main Street votes gold",
             "retail investors online poll gold next week", "Kitco weekly gold survey Main Street"]


def _survei_judul(it: dict) -> bool:
    t = html.unescape(f"{it.get('title', '')} {it.get('urlAlias', '')} {it.get('excerpt', '')}").lower().replace("’", "'")
    return any(k in t for k in ("main street", "main-street", "gold survey", "gold-survey", "gold price survey",
                                "online poll", "kitcos-gold", "kitco's gold", "wall street", "wall-street"))


def kitco_cari(maks: int = 2000) -> list[str]:
    DIR.mkdir(parents=True, exist_ok=True)
    urls: dict[str, str] = {}
    for kata in KATA_CARI:
        for off in range(0, maks, 50):
            body = json.dumps({"query": Q_CARI, "variables": {"query": kata, "sort": "relevance", "limit": 50,
                                                              "offset": off}}).encode()
            d = json.loads(_get(GQL, body, {"Content-Type": "application/json", "Origin": "https://www.kitco.com"}))
            items = ((d.get("data") or {}).get("searchData") or {}).get("items") or []
            if not items:
                break
            baru = [it for it in items if _survei_judul(it)]
            for it in baru:
                urls[it["urlAlias"]] = it.get("title", "")
            print(f"  {kata[:30]:30s} off {off:4d}: {len(items)} hasil, {len(baru)} survei, total {len(urls)}")
            if off >= 300 and not baru:              # relevansi sudah habis
                break
            time.sleep(0.4)
    (DIR / "kitco_url.json").write_text(json.dumps(urls, indent=0, ensure_ascii=False), encoding="utf-8")
    return list(urls)


def _teks(page: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace(" ", " ")
    return re.sub(r"\s+", " ", t)


NAIK = r"higher|rise|rising|gain|bullish|climb|rally|increase|go up|move up|advance|upside"
TURUN = r"lower|fall|declin|drop|lose|losing|lost|bearish|retreat|down|weak|correct|slip|slide|dip|sell"
DATAR = r"sideways|neutral|flat|range|consolidat|unchanged|sidelines|churn|couldn|undecided|unsure"


def _klas(s: str) -> str | None:
    s = s.lower()
    pos = {k: (m.start() if (m := re.search(p, s)) else 10**6) for k, p in (("up", NAIK), ("down", TURUN), ("side", DATAR))}
    k = min(pos, key=pos.get)
    return k if pos[k] < 10**6 else None


def _tiga(seg: str) -> dict:
    """Ambil 'N ..., or P%, <arah>' di segmen → {up, down, side} persen (yang pertama per arah)."""
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


def kitco_unduh() -> pd.DataFrame:
    f = DIR / "kitco_survei.json"
    lama = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    urls = json.loads((DIR / "kitco_url.json").read_text(encoding="utf-8"))
    for i, u in enumerate(sorted(urls)):
        if u in lama and lama[u].get("ms_n"):
            continue
        try:
            page = _get("https://www.kitco.com" + u).decode("utf-8", "replace")
        except Exception as e:                      # noqa: BLE001
            print("  gagal", u, e)
            continue
        lama[u] = {"judul": urls[u], **kitco_parse(page)}
        if i % 20 == 0:
            print(f"  {i}/{len(urls)} {u[:90]} {lama[u]}")
            f.write_text(json.dumps(lama, indent=0, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.5)
    f.write_text(json.dumps(lama, indent=0, ensure_ascii=False), encoding="utf-8")
    return kitco_tabel()


def kitco_tabel() -> pd.DataFrame:
    d = json.loads((DIR / "kitco_survei.json").read_text(encoding="utf-8"))
    rows = []
    for u, v in d.items():
        m = re.search(r"/(20\d\d-\d\d-\d\d)", u)
        if not m or not v.get("ms_n") or "ms_up" not in v or "ms_down" not in v:
            continue
        rows.append({"tgl": pd.Timestamp(m.group(1)), "url": u, **{k: v.get(k) for k in
                     ("ms_n", "ms_up", "ms_down", "ms_side", "ws_up", "ws_down", "ws_side")}})
    t = pd.DataFrame(rows).sort_values("tgl")
    # satu survei per pekan (Jumat); artikel tambahan di pekan sama dibuang (yang suaranya terbanyak dipakai)
    t["pekan"] = t.tgl.dt.to_period("W-SUN")
    t = t.sort_values(["pekan", "ms_n"]).drop_duplicates("pekan", keep="last").sort_values("tgl").reset_index(drop=True)
    return t


# ───────────────────────────── harga emas harian (Twelve Data, hari kerja saja) ─────────────────────────────
def emas_harian() -> pd.Series:
    f = ROOT / "data" / "research" / "eksternal" / "td_XAUUSD_1day.json"
    if not f.exists() or time.time() - f.stat().st_mtime > 6 * 3600:
        q = urllib.parse.urlencode({"symbol": "XAU/USD", "interval": "1day", "outputsize": 5000, "order": "ASC",
                                    "apikey": os.environ.get("TWELVEDATA_API_KEY", "")})
        d = json.loads(_get(f"https://api.twelvedata.com/time_series?{q}"))
        if d.get("values"):
            f.write_text(json.dumps(d), encoding="utf-8")
    v = pd.DataFrame(json.loads(f.read_text(encoding="utf-8"))["values"])
    s = pd.Series(v.close.astype(float).to_numpy(), index=pd.to_datetime(v.datetime)).sort_index()
    return s[s.index.dayofweek < 5]


# ───────────────────────────── StockTwits: pesan berlabel Bullish/Bearish ─────────────────────────────
def stocktwits(jam: float = 1.5, simbol: tuple[str, ...] = ("GLD", "XAUUSD", "GC_F", "IAU", "PHYS")) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    batas = time.time() + jam * 3600
    for s in simbol:
        f = DIR / f"stocktwits_{s}.json"
        isi = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"msg": {}, "max": None}
        mx, n0 = isi.get("max"), len(isi["msg"])
        while time.time() < batas:
            u = f"https://api.stocktwits.com/api/2/streams/symbol/{s}.json" + (f"?max={mx}" if mx else "")
            try:
                d = json.loads(_get(u, coba=2))
            except Exception as e:                  # noqa: BLE001 — batas laju: berhenti simbol ini
                print("  stop", s, e)
                time.sleep(60)
                continue
            m = d.get("messages") or []
            for x in m:
                isi["msg"][str(x["id"])] = [x["created_at"], ((x.get("entities") or {}).get("sentiment") or {}).get("basic")]
            if not m or not (d.get("cursor") or {}).get("more"):
                isi["habis"] = True
                break
            mx = d["cursor"]["max"]
            isi["max"] = mx
            if len(isi["msg"]) % 1500 < 30:
                f.write_text(json.dumps(isi), encoding="utf-8")
                print(f"  {s}: {len(isi['msg'])} pesan, sampai {m[-1]['created_at']}")
            time.sleep(1.2)
        f.write_text(json.dumps(isi), encoding="utf-8")
        print(s, "baru", len(isi["msg"]) - n0, "total", len(isi["msg"]))


def stocktwits_harian(s: str) -> pd.DataFrame:
    f = DIR / f"stocktwits_{s}.json"
    if not f.exists():
        return pd.DataFrame()
    d = pd.DataFrame(json.loads(f.read_text(encoding="utf-8"))["msg"].values(), columns=["t", "s"])
    d["t"] = pd.to_datetime(d.t).dt.tz_convert("America/New_York")
    d["hari"] = d.t.dt.tz_localize(None).dt.normalize()
    g = d.groupby("hari").agg(n=("s", "size"), bull=("s", lambda x: (x == "Bullish").sum()),
                              bear=("s", lambda x: (x == "Bearish").sum()))
    return g


# ───────────────────────────── Wikipedia: perhatian publik ─────────────────────────────
WIKI = ["Gold_as_an_investment", "Gold", "Gold_standard", "Gold_bar"]


def wiki() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for a in WIKI:
        u = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{a}/daily/"
             f"20150701/{pd.Timestamp.now('UTC'):%Y%m%d}")
        d = json.loads(_get(u, headers={"User-Agent": "TradingResearch/1.0 (riset pribadi)"}))
        out[a] = {i["timestamp"][:8]: i["views"] for i in d["items"]}
        print(a, len(out[a]))
        time.sleep(1)
    (DIR / "wiki.json").write_text(json.dumps(out), encoding="utf-8")


# ───────────────────────────── Google Trends: pencarian "buy gold" vs "sell gold" ─────────────────────────────
JENDELA = [("2004-01-01", "2008-12-31"), ("2008-06-01", "2013-05-31"), ("2013-01-01", "2017-12-31"),
           ("2017-06-01", "2022-05-31"), ("2021-10-20", None)]


def trends() -> None:
    """Mingguan per jendela ≤ 5 tahun (skala Google per jendela; rasio buy/sell di payload yang sama tetap sebanding)
    + bulanan 2004–kini (satu payload)."""
    from pytrends.request import TrendReq
    DIR.mkdir(parents=True, exist_ok=True)
    p = TrendReq(hl="en-US", tz=0, timeout=(10, 30))
    kata = ["buy gold", "sell gold", "gold price"]
    out = {"mingguan": [], "bulanan": None}
    for a, b in JENDELA:
        b = b or f"{pd.Timestamp.now('UTC'):%Y-%m-%d}"
        p.build_payload(kata, timeframe=f"{a} {b}")
        d = p.interest_over_time().drop(columns="isPartial", errors="ignore")
        out["mingguan"].append({"dari": a, "sampai": b, "data": {f"{i:%Y-%m-%d}": r.tolist() for i, r in d.iterrows()}})
        print("trends", a, b, len(d))
        time.sleep(5)
    p.build_payload(kata, timeframe=f"2004-01-01 {pd.Timestamp.now('UTC'):%Y-%m-%d}")
    d = p.interest_over_time().drop(columns="isPartial", errors="ignore")
    out["bulanan"] = {f"{i:%Y-%m-%d}": r.tolist() for i, r in d.iterrows()}
    (DIR / "trends.json").write_text(json.dumps(out), encoding="utf-8")


# ───────────────────────────── Survei konsumen (FRED): UMich & OECD keyakinan konsumen AS ─────────────────────────────
KONSUMEN = {"UMCSENT": "UMich sentimen konsumen", "CSCICP03USM665S": "OECD keyakinan konsumen AS",
            "MICH": "UMich ekspektasi inflasi 1 th"}


def konsumen() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for s in KONSUMEN:
        q = urllib.parse.urlencode({"series_id": s, "api_key": os.environ.get("FRED_API_KEY", ""), "file_type": "json"})
        d = json.loads(_get(f"https://api.stlouisfed.org/fred/series/observations?{q}"))
        out[s] = {o["date"]: float(o["value"]) for o in d.get("observations", []) if o["value"] != "."}
        print(s, len(out[s]))
    (DIR / "konsumen.json").write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "uji"
    if cmd == "kitco":
        kitco_cari()
        print(kitco_unduh().tail())
    elif cmd == "stocktwits":
        stocktwits(float(sys.argv[2]) if len(sys.argv) > 2 else 1.5)
    elif cmd == "wiki":
        wiki()
    elif cmd == "trends":
        trends()
    elif cmd == "konsumen":
        konsumen()
    elif cmd == "uji":
        from .sentimen_orang_uji import main
        main()
