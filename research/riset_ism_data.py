"""Data untuk research/riset_ism.py — daftar rilis ISM manufaktur & jasa LENGKAP, target lonjakan menit 1, kalender gabungan.

python -m research.riset_ism_data rilis          # daftar rilis & cakupan target
python -m research.riset_ism_data exness         # zip bulanan Exness (cepat) → jendela tick rilis tanpa target (≥ Sep 2015)
python -m research.riset_ism_data unduh [maks]   # unduh tick Dukascopy jam rilis yang belum punya target (2026 dulu)
python -m research.riset_ism_data target         # → data/research/eksternal/riset_ism/target.parquet
python -m research.riset_ism_data fred           # FRED rilis pertama survei jasa daerah (output_type=4)
python -m research.riset_ism_data kalshi         # Kalshi KXISMPMI / KXUSISMSERV → data/research/eksternal/riset_ism/kalshi

Kenapa perlu: lonjakan60.parquet (research/lonjakan.py) hanya memuat rilis yang punya tick di cache bersama; ISM 2010–2015
jarang (2–8/tahun), 2021 hanya 15, 2026 hanya Jan. Di sini:
- Kalender gabungan (judul dibakukan): ForexFactory spoluan (2010–2023, semua dampak, jam UTC+8 → UTC), ForexFactory
  ehsanrs2 (2020–Jan 2026, dampak tinggi saja), Nasdaq/Investing.com (2010–2026, bolong di beberapa tahun). Per (judul,
  tanggal New York) dipilih baris Nasdaq bila berisi Act & konsensus (sumber yang juga dibaca cloud), selain itu FF.
  S&P Global PMI di Nasdaq tidak membedakan flash/final → tanggal ≥ 14 = flash, ≤ 7 = final.
- Jam rilis ISM = selalu 10:00 New York (FF: 181/182 & 178/179 baris 10:00); kolom gmt Nasdaq tidak dipakai.
- Target (definisi persis research/lonjakan.satu & pra_xau_semua): p0 = mid tick terakhir ≤ t0 − 1 dtk; lonjakan
  0 < t ≤ 60 dtk, arah = naik/turun yang lebih jauh (< $0,05 = 0); gerak detik 2/3/5/10 = tanda(mid − p0). Bila t0 ada
  di lonjakan60 / pra_xau_semua_v2 → nilai itu dipakai; selain itu dihitung dari jendela tick Exness (bila ada) atau jam
  tick Dukascopy (cache bersama dibaca saja; unduhan baru di data/research/eksternal/riset_ism/duka/).
"""
from __future__ import annotations

import glob
import json
import lzma
import os
import sys
import time
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
DIR = EKS / "riset_ism"
DUKA = DIR / "duka"
SHARED = [EKS / "dukascopy" / "raw_XAUUSD_ticks", EKS / "riset_inflasi" / "duka"]   # dibaca saja
TARGET = DIR / "target.parquet"
EXN = DIR / "exness"                       # jendela tick Exness XAUUSDc (format research/exness.py) untuk rilis ISM
KAL = DIR / "kalender.parquet"
HH = (2, 3, 5, 10)
TYPES = {"M": "ISM_M", "S": "ISM_S"}

# judul baku → (judul ForexFactory, judul Nasdaq)
JUDUL = {
    "ISM_M": (["ISM Manufacturing PMI"], ["ISM Manufacturing PMI"]),
    "ISM_S": (["ISM Services PMI", "ISM Non-Manufacturing PMI"], ["ISM Non-Manufacturing PMI", "ISM Services PMI"]),
    "ISM_M_NO": ([], ["ISM Manufacturing New Orders Index"]),
    "CHI": (["Chicago PMI"], ["Chicago PMI"]),
    "EMP": (["Empire State Manufacturing Index"], ["NY Empire State Manufacturing Index"]),
    "PHI": (["Philly Fed Manufacturing Index"], ["Philadelphia Fed Manufacturing Index"]),
    "RICH": (["Richmond Manufacturing Index"], ["Richmond Manufacturing Index"]),
    "KC": ([], ["KC Fed Manufacturing Index"]),
    "RICH_S": ([], ["Richmond Services Index"]),
    "ADP": (["ADP Non-Farm Employment Change"], ["ADP Nonfarm Employment Change"]),
    "FLASH_M": (["Flash Manufacturing PMI"], []), "FINAL_M": (["Final Manufacturing PMI"], []),
    "FLASH_S": (["Flash Services PMI"], []), "FINAL_S": (["Final Services PMI"], []),
}
SPG = {"S&P Global Manufacturing PMI": ("FLASH_M", "FINAL_M"), "S&P Global Services PMI": ("FLASH_S", "FINAL_S")}


def _num(s) -> float:
    from .nasdaq_kalender import angka
    if s is None or (isinstance(s, float) and s != s):
        return float("nan")
    return angka(str(s))


def _ff() -> pd.DataFrame:
    peta = {n: k for k, (ff, _) in JUDUL.items() for n in ff}
    fr = []
    for f in sorted(glob.glob(str(ROOT / "data/research/spoluan_forex-factory-scraper/datasets/*.csv"))):
        d = pd.read_csv(f)
        t = pd.to_datetime(d["Combined DateTime"], errors="coerce")
        # BUG data spoluan: baris SETELAH baris Desember terakhir di file tahun Y = Januari Y+1 tetapi bertanda tahun Y
        # (mis. "2010-01-03" ISM 57,0 = 3 Jan 2011; "2023-01-03" ISM 47,4 = 3 Jan 2024) → tahun +1
        akhir_des = int(np.flatnonzero((t.dt.month == 12).to_numpy()).max())
        salah = (np.arange(len(d)) > akhir_des) & (t.dt.month == 1).to_numpy()
        t = t.where(~salah, t + pd.DateOffset(years=1))
        m = ((d.Currency == "USD") & d.Event.isin(peta)).to_numpy()
        d, t = d[m], t[m]
        t = (t - pd.Timedelta(hours=8)).dt.tz_localize("UTC")
        fr.append(pd.DataFrame({"t": t, "key": d.Event.map(peta), "a": d.Actual, "f": d.Forecast, "p": d.Previous,
                                "src": "FF"}))
    old = pd.concat(fr)
    old = old[old.t < pd.Timestamp("2024-01-01", tz="UTC")]
    e = pd.read_csv(ROOT / "data/research/ehsanrs2_forexfactory-scraper/high_impact_events_calendar.csv")
    e = e[(e.Currency == "USD") & e.Event.isin(peta)]
    new = pd.DataFrame({"t": pd.to_datetime(e.DateTime, utc=True), "key": e.Event.map(peta), "a": e.Actual,
                        "f": e.Forecast, "p": e.Previous, "src": "FF2"})
    x = pd.concat([old, new]).dropna(subset=["t"])
    x["d"] = x.t.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    for c in ("a", "f", "p"):
        x[c] = x[c].map(_num)
    # spoluan (semua dampak) diutamakan atas ehsanrs2 untuk tanggal yang sama
    x["_o"] = x.src.map({"FF": 0, "FF2": 1})
    return x.sort_values("_o").drop_duplicates(["key", "d"]).drop(columns="_o")


def _nasdaq() -> pd.DataFrame:
    peta = {n: k for k, (_, nd) in JUDUL.items() for n in nd}
    rows = []
    for f in sorted((EKS / "nasdaq").glob("*.json")):
        d = pd.Timestamp(f.stem)
        seen = set()
        for r in json.loads(f.read_text(encoding="utf-8")):
            if r["country"] != "United States":
                continue
            n = r["eventName"]
            if n in SPG:
                k = SPG[n][0] if d.day >= 14 else SPG[n][1] if d.day <= 7 else None
            else:
                k = peta.get(n)
            if k is None or k in seen:                       # baris PERTAMA judul itu
                continue
            seen.add(k)
            rows.append({"t": pd.NaT, "key": k, "a": _num(r["actual"]), "f": _num(r["consensus"]),
                         "p": _num(r["previous"]), "src": "NQ", "d": d})
    return pd.DataFrame(rows)


def kalender(segar: bool = False) -> pd.DataFrame:
    """Satu baris per (judul baku, tanggal New York): a, f, p, src, t (jam UTC bila dari FF)."""
    if KAL.exists() and not segar:
        return pd.read_parquet(KAL)
    ff, nq = _ff(), _nasdaq()
    # tanggal Nasdaq kadang mundur 1 hari (2019-07-31 = ISM 1 Agu, 2025-09-01 = 2 Sep, 2026-01-06 = 7 Jan): bila nilai
    # (Act & konsensus) sama dengan baris FF ≤ 3 hari di tanggal lain → pakai tanggal FF
    ffi = {(k, d) for k, d in zip(ff.key, ff.d)}
    for i, x in nq.iterrows():
        if (x.key, x.d) in ffi or x.a != x.a:
            continue
        c = ff[(ff.key == x.key) & ((ff.d - x.d).abs() <= pd.Timedelta(days=3)) & (ff.a == x.a) & (ff.f == x.f)]
        if len(c):
            nq.at[i, "d"] = c.d.iloc[0]
    nq_ok =nq[nq.a.notna() & (nq.f.notna() | nq.key.isin(["ISM_M_NO", "KC", "RICH_S"]))]
    x = pd.concat([nq_ok.assign(_o=0), ff.assign(_o=1), nq[~nq.index.isin(nq_ok.index)].assign(_o=2)])
    x = x.sort_values("_o").drop_duplicates(["key", "d"]).drop(columns="_o").sort_values(["key", "d"])
    # jam FF dipakai bila sumber terpilih Nasdaq tetapi FF punya baris tanggal yang sama
    jam = ff.set_index(["key", "d"]).t
    x["t"] = [jam.get((k, d), t) for k, d, t in zip(x.key, x.d, x.t)]
    x = x.reset_index(drop=True)
    DIR.mkdir(parents=True, exist_ok=True)
    x.to_parquet(KAL)
    return x


def rilis() -> pd.DataFrame:
    """Satu baris per rilis ISM (jenis M/S): t0 UTC (10:00 New York), d (tanggal NY)."""
    k = kalender()
    out = []
    for jenis, key in TYPES.items():
        x = k[(k.key == key) & k.a.notna()]
        for d in x.d:
            t0 = pd.Timestamp(f"{d:%Y-%m-%d} 10:00", tz="America/New_York").tz_convert("UTC")
            out.append({"t0": t0, "d": d, "jenis": jenis})
    df = pd.DataFrame(out)
    df = df[(df.t0 >= pd.Timestamp("2010-01-01", tz="UTC")) & (df.t0 < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=2))]
    return df.sort_values("t0").reset_index(drop=True)


def _jam(t0: pd.Timestamp) -> list[pd.Timestamp]:
    h = t0.floor("h")
    return ([h - pd.Timedelta(hours=1)] if t0.minute == 0 else []) + [h]


def _file(h: pd.Timestamp) -> Path | None:
    for d in SHARED + [DUKA]:
        f = d / f"{h:%Y%m%d_%H}.bi5"
        if f.exists():
            return f
    return None


@lru_cache(maxsize=1)
def _lj() -> pd.DataFrame:
    return pd.read_parquet(EKS / "lonjakan60.parquet").drop_duplicates("t0").set_index("t0")


@lru_cache(maxsize=1)
def _pv() -> pd.DataFrame:
    return pd.read_parquet(EKS / "pra_xau_semua_v2.parquet").sort_values("t0").drop_duplicates("t0").set_index("t0")


def _ex_ok(t0: pd.Timestamp) -> bool:
    if t0.year < 2015:
        return False
    return _ukur(t0, _ex_ticks(t0)) != {}


def perlu() -> list[pd.Timestamp]:
    lj = _lj()
    hs = []
    for t0 in rilis().t0:
        if t0 in lj.index or _ex_ok(t0):
            continue
        hs += [h for h in _jam(t0) if _file(h) is None]
    # prioritas: 2026, lalu periode LAMA 2016–2021 (bolong), lalu sisanya
    return sorted(set(hs), key=lambda h: (0 if h.year >= 2026 else 1 if 2016 <= h.year <= 2021 else 2, h))


def unduh(maks: int | None = None) -> None:
    from .dukascopy import URL
    DUKA.mkdir(parents=True, exist_ok=True)
    todo = perlu()
    todo = todo[:maks] if maks else todo
    print(f"{len(todo)} jam tick perlu diunduh", flush=True)
    wait, t_a = 15.0, time.time()
    for i, h in enumerate(todo, 1):
        url = f"{URL}/XAUUSD/{h.year}/{h.month - 1:02d}/{h.day:02d}/{h.hour:02d}h_ticks.bi5"
        for _ in range(12):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    raw = r.read()
                if raw:
                    lzma.decompress(raw)
                (DUKA / f"{h:%Y%m%d_%H}.bi5").write_bytes(raw)
                wait = max(12.0, wait * 0.8)
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    (DUKA / f"{h:%Y%m%d_%H}.bi5").write_bytes(b"")
                    break
            except Exception:  # noqa: BLE001 - diputus server / terpotong
                pass
            time.sleep(wait)
            wait = min(wait * 1.5, 120.0)
        if i % 5 == 0 or i == len(todo):
            print(f"{i}/{len(todo)} {h:%Y-%m-%d %H}h {(time.time() - t_a) / i:.0f} dtk/file", flush=True)
        time.sleep(3.0)


def _ex_ticks(t0: pd.Timestamp) -> pd.DataFrame | None:
    """Tick Exness: jendela milik riset ini dulu, lalu cache bersama research/exness."""
    from .exness import AFTER, BEFORE, SCALE, ticks_around
    f = EXN / f"{t0:%Y-%m}.parquet"
    if f.exists():
        df = pd.read_parquet(f)
        df = df[(df.index >= t0 - BEFORE) & (df.index <= t0 + AFTER)]
        if len(df):
            k = SCALE["XAU"]
            return pd.DataFrame({"bid": df.bid / k, "ask": (df.bid + df.spread) / k}, index=df.index)
    return ticks_around("XAUUSDc", t0)


def unduh_exness() -> None:
    """Zip bulanan Exness XAUUSDc (±100 MB, cepat) untuk bulan yang punya rilis ISM tanpa target → jendela 2/16 menit.
    Zip diproses di memori (CSV dibaca sebagai data saja), tidak disimpan."""
    import io
    import zipfile

    from .exness import AFTER, BEFORE, SCALE, URL, _get
    lj = _lj()
    perlu_t = [t0 for t0 in rilis().t0 if t0 not in lj.index and t0 >= pd.Timestamp("2015-09-01", tz="UTC")
               and _ukur(t0, _ex_ticks(t0)) == {}]
    bulan = sorted({t.to_period("M") for t in perlu_t})
    print(f"{len(perlu_t)} rilis tanpa target → {len(bulan)} bulan Exness", flush=True)
    EXN.mkdir(parents=True, exist_ok=True)
    for p in bulan:
        t_a = time.time()
        raw = _get(f"{URL}/XAUUSDc/{p.year}/{p.month:02d}/Exness_XAUUSDc_{p.year}_{p.month:02d}.zip")
        if raw is None:
            print(p, "tidak ada", flush=True)
            continue
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            df = pd.read_csv(z.open(z.namelist()[0]), usecols=["Timestamp", "Bid", "Ask"])
        del raw
        df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("Timestamp"), utc=True, format="ISO8601")).as_unit("ns")
        df.columns = ["bid", "ask"]
        df = df[~df.index.duplicated()].sort_index()
        t = df.index.asi8
        keep = np.zeros(len(df), bool)
        semua = [x for x in rilis().t0 if x.to_period("M") == p]
        for e in semua:
            a, b = np.searchsorted(t, [(e - BEFORE).value, (e + AFTER).value])
            keep[a:b] = True
        k = SCALE["XAU"]
        w = df[keep]
        pd.DataFrame({"bid": np.round(w.bid * k).astype("int64"), "spread": np.round((w.ask - w.bid) * k).astype("int32")},
                     index=w.index).to_parquet(EXN / f"{p.strftime('%Y-%m')}.parquet", compression="zstd")
        print(f"{p}: {keep.sum()} tick di {len(semua)} jendela ({time.time() - t_a:.0f} dtk)", flush=True)


def _duka_ticks(t0: pd.Timestamp) -> pd.DataFrame | None:
    from .dukascopy import POINT, _decode_ticks
    fr = []
    for h in _jam(t0):
        f = _file(h)
        if f is None:
            return None
        fr.append(_decode_ticks(f.read_bytes(), h, POINT["XAUUSD"]))
    fr = [x for x in fr if len(x)]
    if not fr:
        return None
    df = pd.concat(fr)
    df = df[(df.index >= t0 - pd.Timedelta(minutes=2)) & (df.index <= t0 + pd.Timedelta(minutes=16))]
    return df if len(df) else None


def _ukur(t0: pd.Timestamp, df: pd.DataFrame | None) -> dict:
    """Lonjakan & gerak detik (definisi lonjakan.satu / pra_xau_semua; syarat data = news_detik.prepare)."""
    from .news_detik import Tick
    if df is None:
        return {}
    p = Tick(t0, df)
    if not ((p.T >= -60) & (p.T < 0)).any() or not ((p.T >= 0) & (p.T < 5)).any() or p.T[-1] < 14.5 * 60:
        return {}
    i0 = p.at(-1)
    if i0 < 0:
        return {}
    p0 = p.mid[i0]
    w = (p.T > 0) & (p.T <= 60)
    if not w.any():
        return {}
    m, t = p.mid[w], p.T[w]
    up, dn = float(m.max() - p0), float(p0 - m.min())
    o = {"arah": 0.0 if max(up, dn) < 0.05 else (1.0 if up > dn else -1.0), "besar": max(up, dn),
         "detik": float(t[int(m.argmax())] if up > dn else t[int(m.argmin())])}
    for h in HH:
        k = p.at(h)
        o[f"y{h}"] = float(np.sign(p.mid[k] - p0)) if k >= 0 else np.nan
    return o


def target(segar: bool = False) -> pd.DataFrame:
    if TARGET.exists() and not segar:
        return pd.read_parquet(TARGET)
    lj, pv = _lj(), _pv()
    rows = []
    for x in rilis().itertuples():
        t0 = x.t0
        o = {"t0": t0, "d": x.d, "jenis": x.jenis}
        ex = du = {}
        if t0 in lj.index:
            a = lj.loc[t0]
            o.update(L=float(a.arah) if a.arah == a.arah else np.nan, besar=a.besar, detik=a.detik,
                     ex_L=a.ex_arah, du_L=a.du_arah, sumber="lonjakan60", grup_lj=a.grup)
        else:
            ex = _ukur(t0, _ex_ticks(t0)) if t0.year >= 2015 else {}
            du = _ukur(t0, _duka_ticks(t0))
            b = ex or du
            o.update(L=b.get("arah", np.nan), besar=b.get("besar", np.nan), detik=b.get("detik", np.nan),
                     ex_L=ex.get("arah", np.nan), du_L=du.get("arah", np.nan),
                     sumber=("exness" if ex else "dukascopy") if b else "tanpa tick", grup_lj=None)
        for h in HH:
            v = np.nan
            if t0 in pv.index:
                e, dk = pv.loc[t0, f"y{h}_XAU_EXNESS"], pv.loc[t0, f"y{h}_XAU"]
                v = np.sign(e) if e == e else np.sign(dk)
            elif ex or du:
                v = (ex or du).get(f"y{h}", np.nan)
            o[f"g{h}"] = float(v) if v == v else np.nan
        rows.append(o)
    df = pd.DataFrame(rows)
    DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(TARGET)
    return df


# ---------- FRED rilis pertama (survei jasa daerah) ----------
FRED_SERI = ["GACDISA066MSFRBNY", "GACDFSA066MSFRBPHI", "BACTSAMFRBDAL", "GARBNDIF066MSFRBPHI", "TSSOSBACTSAMFRBDAL"]


def fred_awal(seri: str) -> pd.DataFrame:
    """Nilai rilis pertama + waktu tersedia (realtime_start + 1 hari, UTC — konservatif, sama dengan pra_per_berita)."""
    f = EKS / f"fred_{seri}_awal.json"
    if not f.exists():
        f = DIR / f"fred_{seri}_awal.json"
    if not f.exists():
        url = ("https://api.stlouisfed.org/fred/series/observations?series_id=" + seri + "&output_type=4"
               "&realtime_start=1776-07-04&realtime_end=9999-12-31&observation_start=2003-01-01&file_type=json"
               "&api_key=" + os.environ["FRED_API_KEY"])
        with urllib.request.urlopen(url, timeout=90) as r:
            raw = r.read()
        DIR.mkdir(parents=True, exist_ok=True)
        f.write_bytes(raw)
    obs = [o for o in json.loads(f.read_text())["observations"] if o["value"] != "."]
    df = pd.DataFrame({"value": [float(o["value"]) for o in obs],
                       "available": pd.to_datetime([o["realtime_start"] for o in obs]).tz_localize("UTC")
                       + pd.Timedelta(days=1)}, index=pd.DatetimeIndex([o["date"] for o in obs]))
    return df[~df.index.duplicated()].sort_index()


# ---------- Kalshi (info tambahan) ----------
def kalshi() -> None:
    from .kalshi import candles, events, markets
    for s in ("KXISMPMI", "KXUSISMSERV"):
        d = DIR / "kalshi" / s
        d.mkdir(parents=True, exist_ok=True)
        for e in sorted(events(s), key=lambda x: x["event_ticker"]):
            f = d / f"{e['event_ticker']}.json"
            if f.exists():
                continue
            ms, arsip = markets(e["event_ticker"])
            if not ms or not all(m.get("result") in ("yes", "no") for m in ms):
                continue
            rows = [{"ticker": m["ticker"], "judul": m.get("yes_sub_title") or m.get("subtitle"),
                     "strike": m.get("floor_strike"), "hasil": m.get("result"), "nilai": m.get("expiration_value"),
                     "tutup": m["close_time"], "volume": m.get("volume_fp", m.get("volume")),
                     "candle": candles(s, m, arsip)} for m in ms]
            f.write_text(json.dumps({"event": e["event_ticker"], "judul": e.get("title"), "pasar": rows},
                                    ensure_ascii=False), encoding="utf-8")
            print(f"  {e['event_ticker']}: {len(rows)} pasar", flush=True)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "rilis"
    if cmd == "rilis":
        kalender(segar=True)
        r = rilis()
        lj = _lj()
        r["di_lj"] = r.t0.isin(lj.index)
        print(r.groupby([r.t0.dt.year, "jenis"]).di_lj.agg(["size", "sum"]).unstack().to_string())
        ism_lj = lj[lj.grup == "ISM"].index
        print("lonjakan60 ISM yang tidak ada di daftar:", sorted(set(ism_lj) - set(r.t0)))
        print("jam tick perlu:", len(perlu()))
    elif cmd == "unduh":
        unduh(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "exness":
        unduh_exness()
    elif cmd == "target":
        df = target(segar=True)
        print(df.groupby(["jenis", "sumber"]).size())
        print(df[df.L.notna()].groupby([df.t0.dt.year, "jenis"]).size().unstack().T.to_string())
    elif cmd == "fred":
        for s in FRED_SERI:
            x = fred_awal(s)
            print(s, len(x), x.index.min(), x.index.max())
    elif cmd == "kalshi":
        kalshi()


if __name__ == "__main__":
    main()
