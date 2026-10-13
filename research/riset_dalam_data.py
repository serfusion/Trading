"""🗂️ Data riset MENDALAM berita lain (13 Okt 2026): jadwal lengkap SEMUA tingkat dampak + tick Exness tambahan + lonjakan.

python -m research.riset_dalam_data jadwal          → data/research/eksternal/riset_dalam/jadwal.parquet
python -m research.riset_dalam_data tick [a b]      → data/research/eksternal/exness/XAUUSDc/tambah_<YYYY-MM>.parquet
python -m research.riset_dalam_data lonjakan        → data/research/eksternal/riset_dalam/lonjakan.parquet (+ cek vs lonjakan60)

Kenapa (permintaan pengguna 13 Okt: "di sesi lain sangat lama kenapa di sini cepat? … uji keduanya"): putaran pertama
(research/riset_lain.py) memakai kalender ForexFactory BINTANG 3 saja, sehingga klaim 2018–2022, JOLTS < 2021, UoM/CB sering
hilang (dampak 'Medium'/'Non-economic' di FF) dan rilis tanpa jendela tick → n terlalu kecil untuk bisa lolos uji apa pun.
Sumber di sini:
  - arsip FF mentah spoluan (data/research/spoluan_forex-factory-scraper/datasets/*.csv): SEMUA dampak 2010–2023, dengan
    Actual/Forecast/Previous; jam = 'Combined DateTime' − 8 jam (UTC; sama dengan research/news_data.load_calendar);
  - FF ehsanrs2 (bintang 3, 2020–Jan 2026) untuk 2024+; Nasdaq (api.nasdaq.com cache, tanggal rilis NY) untuk 2024–2026
    dengan jam baku ET per grup; tanggal rilis FRED (release/dates) sebagai cadangan jadwal tanpa konsensus.
  - Tick: arsip Exness XAUUSDc per bulan (research/exness.py menyimpan jendela berita bintang 3 saja) → bulan yang punya
    rilis tanpa jendela diunduh ulang dan jendela 2 mnt sebelum s/d 16 mnt sesudah rilis itu disimpan di file `tambah_`.
Bersamaan: rilis lain (FF Medium/High, atau tanggal FRED berita besar 2024+) di MENIT yang sama dicatat di kolom `bersama`;
`sendiri` = tidak ada rilis tingkat sama/lebih tinggi di menit itu (emas bereaksi pada gabungan → dipisah saat evaluasi).
"""
from __future__ import annotations

import glob
import io
import json
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "research"
EKS = DATA / "eksternal"
DIR = EKS / "riset_dalam"
SYM = "XAUUSDc"

# grup → nama FF, nama Nasdaq, jam baku ET, id rilis FRED (cadangan jadwal)
GRUP = {
    "CLAIMS": (["Unemployment Claims"], ["Initial Jobless Claims"], "08:30", 180),
    "RETAIL": (["Retail Sales m/m"], ["Retail Sales"], "08:30", 9),
    "GDP": (["Advance GDP q/q", "Prelim GDP q/q", "Final GDP q/q"], ["GDP"], "08:30", 53),
    "ADP": (["ADP Non-Farm Employment Change"], ["ADP Nonfarm Employment Change"], "08:15", None),
    "JOLTS": (["JOLTS Job Openings"], ["JOLTS Job Openings"], "10:00", 192),
    "UOM": (["Prelim UoM Consumer Sentiment", "Revised UoM Consumer Sentiment"], ["Michigan Consumer Sentiment"], "10:00",
            None),
    "CB": (["CB Consumer Confidence"], ["CB Consumer Confidence"], "10:00", None),
    "FOMC": (["Federal Funds Rate"], ["Fed Interest Rate Decision"], "14:00", None),
}
# tingkat: rilis di menit yang sama dengan tingkat ≤ (angka lebih kecil = lebih besar) → bukan 'sendiri'
TINGKAT = {"NFP": 0, "CPI": 0, "FOMC": 0, "PCE": 1, "PPI": 1, "RETAIL": 1, "GDP": 1, "ISM": 1, "JOLTS": 2, "ADP": 2,
           "ECI": 2, "CLAIMS": 3, "UOM": 3, "CB": 3, "LAIN": 4}
# nama FF lain → grup (untuk deteksi bersamaan)
FF_LAIN = [("Non-Farm Employment Change", "NFP"), ("CPI", "CPI"), ("PPI", "PPI"), ("PCE", "PCE"),
           ("Personal Spending", "PCE"), ("Personal Income", "PCE"), ("ISM", "ISM"), ("Employment Cost", "ECI"),
           ("FOMC", "FOMC"), ("Federal Funds", "FOMC"), ("Retail Sales", "RETAIL"), ("GDP", "GDP"),
           ("Unemployment Claims", "CLAIMS"), ("JOLTS", "JOLTS"), ("ADP", "ADP"), ("UoM", "UOM"),
           ("CB Consumer", "CB")]
# 2024+ (FF hanya bintang 3): tanggal FRED berita besar 08:30 ET untuk deteksi bersamaan
FRED_BESAR = {50: "NFP", 10: "CPI", 46: "PPI", 54: "PCE", 9: "RETAIL", 53: "GDP", 11: "ECI", 180: "CLAIMS",
              51: "LAIN", 27: "LAIN", 188: "LAIN", 351: "LAIN", 435: "LAIN"}


def _num(v) -> float:
    from .news_data import _num as n
    return n(v)


def _ny(tgl, hm: str) -> pd.Timestamp:
    return pd.Timestamp(f"{pd.Timestamp(tgl):%Y-%m-%d} {hm}").tz_localize("America/New_York").tz_convert("UTC")


def _fred_dates(rid: int) -> list[str]:
    from .eksternal_berita import _fred_dates as f
    try:
        return f(rid)
    except Exception:  # noqa: BLE001 - FRED tidak terjangkau → tanpa cadangan
        return []


def grup_ff(ev: str) -> str:
    for g, (ff, _, _, _) in GRUP.items():
        if ev in ff:
            return g
    return next((g for k, g in FF_LAIN if k in str(ev)), "LAIN")


def ff_mentah() -> pd.DataFrame:
    fr = []
    for f in sorted(glob.glob(str(DATA / "spoluan_forex-factory-scraper/datasets/*.csv"))):
        d = pd.read_csv(f)
        d = d[d.Currency == "USD"]
        t = pd.to_datetime(d["Combined DateTime"], errors="coerce") - pd.Timedelta(hours=8)
        fr.append(pd.DataFrame({"t0": t.dt.tz_localize("UTC"), "event": d.Event, "impact": d.Impact, "actual": d.Actual,
                                "forecast": d.Forecast, "previous": d.Previous, "src": "FF"}))
    a = pd.concat(fr)
    a = a[a.t0.notna() & (a.t0 < pd.Timestamp("2024-01-01", tz="UTC"))]
    e = pd.read_csv(DATA / "ehsanrs2_forexfactory-scraper/high_impact_events_calendar.csv")
    e = e[e.Currency == "USD"]
    b = pd.DataFrame({"t0": pd.to_datetime(e.DateTime, utc=True), "event": e.Event, "impact": e.Impact,
                      "actual": e.Actual, "forecast": e.Forecast, "previous": e.Previous, "src": "FF3"})
    b = b[b.t0 >= pd.Timestamp("2024-01-01", tz="UTC")]
    return pd.concat([a, b], ignore_index=True)


def nasdaq_baris(mulai: str = "2024-01-01") -> pd.DataFrame:
    rows = []
    nama = {n: g for g, (_, nd, _, _) in GRUP.items() for n in nd}
    for f in sorted(glob.glob(str(EKS / "nasdaq" / "*.json"))):
        tgl = Path(f).stem
        if tgl < mulai:
            continue
        seen = set()
        for r in json.loads(Path(f).read_text(encoding="utf-8")):
            g = nama.get(r.get("eventName"))
            if not g or r.get("country") != "United States" or g in seen:
                continue
            seen.add(g)                                        # baris pertama per nama (GDP: q/q tahunan dulu)
            rows.append({"t0": _ny(tgl, GRUP[g][2]), "event": r["eventName"], "grup": g, "actual": r.get("actual"),
                         "forecast": r.get("consensus"), "previous": r.get("previous"), "src": "Nasdaq"})
    return pd.DataFrame(rows)


def jadwal(segar: bool = False) -> pd.DataFrame:
    f = DIR / "jadwal.parquet"
    if f.exists() and not segar:
        return pd.read_parquet(f)
    DIR.mkdir(parents=True, exist_ok=True)
    ff = ff_mentah()
    ff["grup"] = ff.event.map(grup_ff)
    utama = ff[ff.event.isin(sum((v[0] for v in GRUP.values()), []))].copy()
    nd = nasdaq_baris()
    # 2024+: FF bintang 3 dulu (jam tepat), Nasdaq mengisi yang tidak ada / konsensus kosong
    utama["ny"] = utama.t0.dt.tz_convert("America/New_York").dt.date
    nd["ny"] = nd.t0.dt.tz_convert("America/New_York").dt.date
    kunci = set(zip(utama.grup, utama.ny))
    tambah = nd[[(g, d) not in kunci for g, d in zip(nd.grup, nd.ny)]]
    x = pd.concat([utama, tambah], ignore_index=True)
    # FRED: tanggal rilis tanpa baris kalender (konsensus kosong) tetap masuk supaya target lengkap
    ada = set(zip(x.grup, x.ny))
    ekstra = []
    for g, (_, _, jam, rid) in GRUP.items():
        for d in _fred_dates(rid) if rid else []:
            dd = pd.Timestamp(d).date()
            if dd >= pd.Timestamp("2015-01-01").date() and (g, dd) not in ada and pd.Timestamp(d) < pd.Timestamp.now():
                ekstra.append({"t0": _ny(d, jam), "event": GRUP[g][0][0], "grup": g, "src": "FRED", "ny": dd})
    x = pd.concat([x, pd.DataFrame(ekstra)], ignore_index=True)
    x = x.sort_values(["grup", "t0"]).drop_duplicates(["grup", "ny"]).reset_index(drop=True)
    x["sub"] = x.event.map(lambda e: {"Advance GDP q/q": "adv", "Prelim GDP q/q": "prelim", "Final GDP q/q": "final",
                                      "Prelim UoM Consumer Sentiment": "prelim",
                                      "Revised UoM Consumer Sentiment": "final"}.get(e, ""))
    # Nasdaq/FRED tanpa label: GDP = urutan dalam kuartal; UoM = rilis pertama di bulan itu = prelim
    m = (x.grup == "GDP") & (x["sub"] == "")
    x.loc[m, "sub"] = x[m].t0.dt.month.map(lambda k: {1: "adv", 2: "prelim", 0: "final"}[k % 3])
    m = (x.grup == "UOM") & (x["sub"] == "")
    x.loc[m, "sub"] = np.where(x[m].t0.dt.day <= 17, "prelim", "final")
    for c in ("actual", "forecast", "previous"):
        x[f"{c[0]}"] = x[c].map(_num)
    # bersamaan di menit yang sama
    lain = ff[ff.impact.isin(["High", "Medium"]) | ff.event.isin(sum((v[0] for v in GRUP.values()), []))]
    per_menit: dict = {}
    for t, g in zip(lain.t0.dt.floor("min"), lain.grup):
        per_menit.setdefault(t, set()).add(g)
    for rid, g in FRED_BESAR.items():
        for d in _fred_dates(rid):
            t = _ny(d, "08:30")
            if t >= pd.Timestamp("2024-01-01", tz="UTC"):
                per_menit.setdefault(t, set()).add(g)
    for g, (_, _, jam, _) in GRUP.items():                      # Nasdaq 2024+ (ISM/UoM/CB/JOLTS jam 10:00)
        for t in nd[nd.grup == g].t0:
            per_menit.setdefault(t, set()).add(g)
    for t in nasdaq_ism():
        per_menit.setdefault(t, set()).add("ISM")
    bers, sendiri = [], []
    for t, g in zip(x.t0.dt.floor("min"), x.grup):
        o = sorted(per_menit.get(t, set()) - {g})
        bers.append(",".join(o))
        sendiri.append(all(TINGKAT.get(k, 4) > TINGKAT[g] for k in o))
    x["bersama"], x["sendiri"] = bers, sendiri
    x = x.drop(columns=["ny"])
    x.to_parquet(f)
    return x


def nasdaq_ism() -> list[pd.Timestamp]:
    out = []
    for f in sorted(glob.glob(str(EKS / "nasdaq" / "*.json"))):
        if Path(f).stem < "2024-01-01":
            continue
        for r in json.loads(Path(f).read_text(encoding="utf-8")):
            if r.get("eventName") in ("ISM Manufacturing PMI", "ISM Non-Manufacturing PMI") and \
                    r.get("country") == "United States":
                out.append(_ny(Path(f).stem, "10:00"))
    return out


# ---------------------------------------------------------------- tick Exness tambahan
def _tercakup() -> pd.DatetimeIndex:
    from .news_detik import events
    return pd.DatetimeIndex(events().time)


def butuh(x: pd.DataFrame) -> dict[str, list[pd.Timestamp]]:
    """Bulan → waktu rilis yang tidak punya jendela tick Exness (jendela bintang 3 = [e − 2 mnt, e + 16 mnt])."""
    ev = np.sort(_tercakup().asi8)
    out: dict[str, list] = {}
    for t in x.t0[x.t0 >= pd.Timestamp("2015-09-01", tz="UTC")]:
        i = np.searchsorted(ev, (t - pd.Timedelta(minutes=14)).value, side="left")
        if i < len(ev) and ev[i] <= t.value:
            continue
        out.setdefault(t.strftime("%Y-%m"), []).append(t)
    return out


def tambah_bulan(arg) -> str:
    from .exness import AFTER, BEFORE, SCALE, URL, _get, out_dir
    bln, times = arg
    f = out_dir(SYM) / f"tambah_{bln}.parquet"
    if f.exists():
        old = pd.read_parquet(f)
        times = [t for t in times if not ((old.index >= t - BEFORE) & (old.index <= t)).any()]
        if not times:
            return f"{bln}: ada"
    y, m = bln.split("-")
    raw = _get(f"{URL}/{SYM}/{y}/{m}/Exness_{SYM}_{y}_{m}.zip")
    if raw is None:
        return f"{bln}: tidak ada arsip"
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), usecols=["Timestamp", "Bid", "Ask"])
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("Timestamp"), utc=True, format="ISO8601")).as_unit("ns")
    df.columns = ["bid", "ask"]
    df = df[~df.index.duplicated()].sort_index()
    t = df.index.asi8
    keep = np.zeros(len(df), bool)
    for e in times:
        a, b = np.searchsorted(t, [(e - BEFORE).value, (e + AFTER).value])
        keep[a:b] = True
    k = SCALE["XAU"]
    w = df[keep]
    baru = pd.DataFrame({"bid": np.round(w.bid * k).astype("int64"), "spread": np.round((w.ask - w.bid) * k).astype("int32")},
                        index=w.index)
    if f.exists():
        baru = pd.concat([pd.read_parquet(f), baru]).sort_index()
        baru = baru[~baru.index.duplicated()]
    baru.to_parquet(f, compression="zstd")
    return f"{bln}: {len(times)} rilis, {keep.sum()} tick"


def unduh(a: str = "2015-09", b: str = "2026-10", pekerja: int = 3) -> None:
    x = jadwal()
    need = {k: v for k, v in butuh(x).items() if a <= k <= b}
    print(f"{sum(len(v) for v in need.values())} rilis tanpa tick di {len(need)} bulan", flush=True)
    with ProcessPoolExecutor(pekerja) as ex:
        for s in ex.map(tambah_bulan, sorted(need.items())):
            print(s, flush=True)


def ticks(t0: pd.Timestamp) -> pd.DataFrame | None:
    """Tick Exness (jendela bintang 3 + jendela tambahan) 2 mnt sebelum s/d 16 mnt sesudah t0."""
    from .exness import AFTER, BEFORE, SCALE, out_dir
    fr = []
    for p in {t0.to_period("M"), (t0 - BEFORE).to_period("M"), (t0 + AFTER).to_period("M")}:
        for nm in (f"{p.strftime('%Y-%m')}.parquet", f"tambah_{p.strftime('%Y-%m')}.parquet"):
            f = out_dir(SYM) / nm
            if f.exists():
                fr.append(pd.read_parquet(f))
    if not fr:
        return None
    df = pd.concat(fr).sort_index()
    df = df[~df.index.duplicated()]
    df = df[(df.index >= t0 - BEFORE) & (df.index <= t0 + AFTER)]
    if not len(df):
        return None
    k = SCALE["XAU"]
    return pd.DataFrame({"bid": df.bid / k, "ask": (df.bid + df.spread) / k}, index=df.index)


# ---------------------------------------------------------------- target: lonjakan menit 1 + arah detik
def satu(t0: pd.Timestamp) -> dict:
    o = {"t0": t0}
    df = ticks(t0)
    if df is None:
        return o
    T = (df.index - t0).total_seconds().to_numpy()
    mid = ((df.bid + df.ask) / 2).to_numpy()
    i0 = int(np.searchsorted(T, -1.0, side="right")) - 1
    if i0 < 0 or T[i0] < -60 or not ((T > 0) & (T <= 5)).any() or T[-1] < 60:
        return o                                               # pasar tutup / data bolong (sama dengan news_detik.prepare)
    p0 = mid[i0]
    w = (T > 0) & (T <= 60)
    m, t = mid[w], T[w]
    up, dn = float(m.max() - p0), float(p0 - m.min())
    o["naik"], o["turun"], o["besar"] = up, dn, max(up, dn)
    o["arah"] = 0.0 if max(up, dn) < 0.05 else (1.0 if up > dn else -1.0)
    o["detik"] = float(t[int(m.argmax())] if up > dn else t[int(m.argmin())])
    for h in (1, 2, 3, 5, 10, 60):
        j = int(np.searchsorted(T, h, side="right")) - 1
        o[f"d{h}"] = float(np.sign(mid[j] - p0)) if j > i0 else 0.0
    o["spread0"] = float(df.ask.iloc[i0] - df.bid.iloc[i0])
    return o


def lonjakan(segar: bool = False) -> pd.DataFrame:
    f = DIR / "lonjakan.parquet"
    if f.exists() and not segar:
        return pd.read_parquet(f)
    x = jadwal()
    x = x[x.t0 >= pd.Timestamp("2015-09-01", tz="UTC")]
    waktu = sorted(set(x.t0))                                   # satu hitungan per waktu (rilis bersamaan = waktu sama)
    with ProcessPoolExecutor(4) as ex:
        rows = list(ex.map(satu, waktu, chunksize=16))
    y = x.merge(pd.DataFrame(rows), on="t0", how="left")
    assert len(y) == len(x)
    y.to_parquet(f)
    return y


def cek() -> None:
    """Hasil lonjakan di sini vs lonjakan60.parquet (ex_arah) untuk rilis yang sama → harus ≈ 100% sama."""
    y = lonjakan()
    l60 = pd.read_parquet(EKS / "lonjakan60.parquet")[["t0", "ex_arah"]]
    z = y.merge(l60, on="t0").dropna(subset=["arah", "ex_arah"])
    print(f"cek vs lonjakan60: {len(z)} rilis sama, arah sama {(z.arah == z.ex_arah).mean() * 100:.1f}%")
    y["th"] = y.t0.dt.year
    ok = y[y.arah.notna()]
    print(ok.groupby(["grup", "th"]).size().unstack(fill_value=0).loc[:, 2015:].to_string())
    print("sendiri:", ok[ok.sendiri].groupby("grup").size().to_dict())


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "jadwal"
    if mode == "jadwal":
        x = jadwal(segar=True)
        x["th"] = x.t0.dt.year
        print(x.groupby(["grup", "th"]).size().unstack(fill_value=0).to_string())
        print("konsensus ada:", x.groupby("grup").f.apply(lambda s: f"{s.notna().mean() * 100:.0f}%").to_dict())
        print("sendiri:", x.groupby("grup").sendiri.mean().round(2).to_dict())
    elif mode == "tick":
        unduh(*(sys.argv[2:4] if len(sys.argv) >= 4 else ()))
    elif mode == "lonjakan":
        lonjakan(segar=True)
        cek()


if __name__ == "__main__":
    main()
