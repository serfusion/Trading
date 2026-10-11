"""Data untuk research/riset_inflasi.py — daftar rilis PPI & PCE (core PCE bulanan) LENGKAP + target lonjakan menit 1.

python -m research.riset_inflasi_data rilis        # tampilkan daftar rilis & cakupan tick
python -m research.riset_inflasi_data unduh [maks]  # unduh tick Dukascopy jam rilis yang belum punya tick
python -m research.riset_inflasi_data target       # → data/research/eksternal/riset_inflasi/target.parquet

Kenapa perlu: lonjakan60.parquet hanya memuat rilis yang ada di events() (kalender bintang 3). Core PCE sebelum 2021
berdampak "Medium" di ForexFactory → grup PCE baru mulai Jul 2021 (LAMA hanya 2 rilis, kriteria LAMA n ≥ 8 mustahil),
PPI 2020 & 2026 juga bolong. Di sini daftar rilis disusun dari ForexFactory (jam rilis) + kalender Nasdaq (tanggal 2020 &
2026; kolom gmt Nasdaq = jam New York musim panas tetap (UTC−4) → dikonversi ke UTC; dicek cocok dengan ForexFactory).
Target per rilis (sama persis dengan research/lonjakan.satu & pra_xau_semua): p0 = mid tick terakhir ≤ t0−1 dtk;
lonjakan 0 < t ≤ 60 dtk (arah = naik/turun yang lebih jauh, < $0,05 = 0) dan gerak detik 2/3/5/10 (mid − p0).
Bila t0 sudah ada di lonjakan60 / pra_xau_semua_v2 (grup apa pun, mis. bersamaan dengan GDP/klaim) → nilai itu dipakai.
Tick baru (Dukascopy) disimpan di data/research/eksternal/riset_inflasi/duka/ (tidak mengubah cache lain).
"""
from __future__ import annotations

import json
import lzma
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
DIR = EKS / "riset_inflasi"
DUKA = DIR / "duka"
SHARED = EKS / "dukascopy" / "raw_XAUUSD_ticks"
TARGET = DIR / "target.parquet"
MULAI = pd.Timestamp("2014-01-01", tz="UTC")
NAMA = {"PCE": ("Core PCE Price Index m/m", "Core PCE Price Index"), "PPI": ("PPI m/m", "PPI")}
HH = (1, 2, 3, 5, 10)


def _nasdaq_tanggal(nama: str) -> dict[str, str]:
    """{tanggal NY: gmt} untuk judul Nasdaq yang punya konsensus."""
    out = {}
    for f in sorted((EKS / "nasdaq").glob("*.json")):
        rows = [r for r in json.loads(f.read_text(encoding="utf-8")) if r["country"] == "United States"
                and r["eventName"] == nama]
        if any(r["consensus"] for r in rows):
            # jam rilis utama = jam baris PERTAMA yang berkonsensus (2026-01-22: 10:59 Okt tanpa konsensus, 11:00 Nov)
            out[f.stem] = next(r["gmt"] for r in rows if r["consensus"])
    return out


def _gmt_utc(tgl: str, gmt: str) -> pd.Timestamp:
    """Kolom gmt Nasdaq = jam New York musim panas sepanjang tahun (UTC−4): 08:30 EDT tercatat 08:30, 08:30 EST 09:30."""
    return pd.Timestamp(f"{tgl} {gmt}") + pd.Timedelta(hours=4)


def rilis(grup: str) -> pd.DataFrame:
    """Satu baris per rilis grup (PPI / PCE): t0 UTC, d (tanggal NY), sumber jam."""
    from .news_prediksi import calendar
    cal = calendar()
    ff = cal[cal.event == NAMA[grup][0]].time.sort_values()
    rows = {}
    for t in ff:
        ny = t.tz_convert("America/New_York")
        if ny.weekday() >= 5:                                  # 2019-04-28 (Minggu) = salah scraping → Senin 08:30
            d = (ny + pd.offsets.BDay(1)).normalize()
            t = pd.Timestamp(f"{d:%Y-%m-%d} 08:30", tz="America/New_York").tz_convert("UTC")
            ny = t.tz_convert("America/New_York")
        rows[f"{ny:%Y-%m-%d}"] = (t, "FF")
    nd = _nasdaq_tanggal(NAMA[grup][1])
    cocok = []
    for tgl, gmt in nd.items():
        tn = _gmt_utc(tgl, gmt).tz_localize("UTC")
        if tgl in rows:
            cocok.append(rows[tgl][0] == tn)
        else:
            rows[tgl] = (tn, "Nasdaq")
    df = pd.DataFrame([(v[0], k, v[1]) for k, v in rows.items()], columns=["t0", "d", "sumber_jam"])
    df = df[(df.t0 >= MULAI) & (df.t0 < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=2))]
    df["grup"] = grup
    df.attrs["cocok"] = (int(sum(cocok)), len(cocok))
    return df.sort_values("t0").reset_index(drop=True)


def _jam(t0: pd.Timestamp) -> list[pd.Timestamp]:
    h = t0.floor("h")
    return ([h - pd.Timedelta(hours=1)] if t0.minute == 0 else []) + [h]


def _file(h: pd.Timestamp) -> Path | None:
    for d in (SHARED, DUKA):
        f = d / f"{h:%Y%m%d_%H}.bi5"
        if f.exists():
            return f
    return None


def perlu() -> list[pd.Timestamp]:
    lj = set(pd.read_parquet(EKS / "lonjakan60.parquet").t0)
    hs = []
    for g in ("PCE", "PPI"):
        for t0 in rilis(g).t0:
            if t0 in lj:
                continue
            hs += [h for h in _jam(t0) if _file(h) is None]
    return sorted(set(hs), key=lambda h: (h.year < 2026, h))     # 2026 dulu (paling berharga), lalu urut waktu


def unduh(maks: int | None = None, mundur: bool = False) -> None:
    """mundur=True: dari jam terakhir ke awal (pekerja kedua); jam yang sudah ada (pekerja lain) dilewati."""
    from .dukascopy import URL
    DUKA.mkdir(parents=True, exist_ok=True)
    todo = perlu()[:maks] if maks else perlu()
    if mundur:
        todo = todo[::-1]
    print(f"{len(todo)} jam tick perlu diunduh", flush=True)
    wait, t_a = 15.0, time.time()
    for i, h in enumerate(todo, 1):
        if _file(h) is not None:
            continue
        url = f"{URL}/XAUUSD/{h.year}/{h.month - 1:02d}/{h.day:02d}/{h.hour:02d}h_ticks.bi5"
        for _ in range(12):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    raw = r.read()
                if raw:
                    lzma.decompress(raw)
                tmp = DUKA / f"{h:%Y%m%d_%H}.bi5.tmp"
                tmp.write_bytes(raw)
                tmp.replace(DUKA / f"{h:%Y%m%d_%H}.bi5")
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
    """Lonjakan & gerak detik (definisi lonjakan.satu / pra_xau_semua)."""
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
    m = p.mid[w]
    up, dn = float(m.max() - p0), float(p0 - m.min())
    o = {"arah": 0.0 if max(up, dn) < 0.05 else (1.0 if up > dn else -1.0), "besar": max(up, dn)}
    for h in HH:
        k = p.at(h)
        o[f"y{h}"] = float(p.mid[k] - p0) if k >= 0 else np.nan
    return o


def target(segar: bool = False) -> pd.DataFrame:
    if TARGET.exists() and not segar:
        return pd.read_parquet(TARGET)
    from .exness import ticks_around as ex_ticks
    lj = pd.read_parquet(EKS / "lonjakan60.parquet").set_index("t0")
    pv = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    pv = pv.sort_values("t0").drop_duplicates("t0").set_index("t0")
    rows = []
    for g in ("PCE", "PPI"):
        r = rilis(g)
        for x in r.itertuples():
            t0 = x.t0
            o = {"t0": t0, "grup": g, "d": x.d, "sumber_jam": x.sumber_jam}
            if t0 in lj.index:
                a = lj.loc[t0]
                o.update(arah=float(a.arah) if a.arah == a.arah else np.nan, besar=a.besar,
                         grup_lj=a.grup, ex_arah=a.ex_arah, du_arah=a.du_arah, sumber_target="lonjakan60")
            else:
                ex = _ukur(t0, ex_ticks("XAUUSDc", t0)) if t0.year >= 2015 else {}
                du = _ukur(t0, _duka_ticks(t0))
                b = ex if ex else du
                o.update(arah=b.get("arah", np.nan), besar=b.get("besar", np.nan), grup_lj=None,
                         ex_arah=ex.get("arah", np.nan), du_arah=du.get("arah", np.nan),
                         sumber_target="hitung" if b else "tidak ada tick")
            for h in (2, 3, 5, 10):
                v = np.nan
                if t0 in pv.index:
                    e, dk = pv.loc[t0, f"y{h}_XAU_EXNESS"], pv.loc[t0, f"y{h}_XAU"]
                    v = e if e == e else dk
                elif o["sumber_target"] == "hitung":
                    v = b.get(f"y{h}", np.nan)
                o[f"g{h}"] = float(np.sign(v)) if v == v else np.nan
            rows.append(o)
    df = pd.DataFrame(rows)
    DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(TARGET)
    return df


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "rilis"
    if cmd == "rilis":
        for g in ("PCE", "PPI"):
            r = rilis(g)
            print(g, len(r), "rilis", r.t0.min(), r.t0.max(), "| jam Nasdaq = FF:", r.attrs["cocok"],
                  r.sumber_jam.value_counts().to_dict())
        print("jam tick perlu:", len(perlu()))
    elif cmd == "unduh":
        unduh(int(sys.argv[2]) or None if len(sys.argv) > 2 else None, mundur="mundur" in sys.argv[3:])
    elif cmd == "target":
        df = target(segar=True)
        print(df.groupby(["grup", "sumber_target"]).size())
        df["th"] = df.t0.dt.year
        print(df[df.arah.notna()].groupby(["grup", "th"]).size().unstack(0).T.to_string())


if __name__ == "__main__":
    main()
