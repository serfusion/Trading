"""🎯 Petunjuk KHUSUS per berita (data yang terbit lebih dulu) → arah XAU 1–10 detik setelah rilis.

python -m research.pra_per_berita        → docs/eksternal/hasil_pra_per_berita.txt + cloud/api/pra_aset.json["per_berita"]

Permintaan pengguna 10 Okt 2026: "coba cari metode lain untuk masing-masing news, saya yakin pasti ada di atas 65%".
Semua aturan DITETAPKAN SEBELUM melihat hasil. Data FRED memakai NILAI RILIS PERTAMA dan tanggal terbitnya
(output_type=4 → tanpa revisi & tanpa look-ahead). Tanda = tebakan angka DI ATAS (+1) / DI BAWAH (−1) konsensus.
  Retail Sales & core:  AUTO  penjualan mobil unit (TOTALSA, terbit awal bulan) bulan acuan naik → di atas
                        BBM   rata-rata harga bensin (GASREGW) bulan acuan naik → di atas (penjualan SPBU ikut naik)
  ISM Manufaktur:       FLASH PMI manufaktur S&P (rilis ±1 pekan sebelumnya) naik dari bulan lalu → di atas
                        REG   survei Fed daerah Empire + Philly + Dallas (aktivitas umum) bulan acuan naik → di atas
  ISM Jasa:             FLASH PMI jasa S&P naik → di atas
  Core PCE:             CPIC  kejutan core CPI bulan acuan (rilis ±2 pekan sebelumnya) searah
                        PPIC  kejutan core PPI bulan acuan searah;  GAB  gabungan keduanya
  Upah per jam (AHE):   K12   tanggal 12 bulan acuan jatuh Minggu–Rabu (tanggal 15 masuk pekan survei) → di atas
                        PK5   5 pekan antar pekan survei (bukan 4) → arah dipilih dari LAMA
  NFP:                  PK5, K12 (arah dipilih dari LAMA)
  Klaim pengangguran:   P / −P  kejutan pekan lalu searah / berbalik
  UMich & CB:           SAHAM S&P 500 (SPY) naik 20 hari bursa terakhir → di atas;  BBM naik → di bawah
                        UM    (khusus CB) kejutan UMich bulan itu searah
  ADP:                  P / −P / KLM (klaim 4 pekan naik → di bawah)
  Core CPI & CPI m/m:   Q1    data Jan–Mar ("efek Januari" residual musiman) → di atas
  Semua judul:          P, −P, ANK (konsensus di atas angka lalu → di atas; anchoring Campbell–Sharpe)
Arah emas: angka di atas konsensus → emas TURUN (pengangguran & klaim terbalik). Dinilai pada harga XAU tengah
t0−1 → t0+2/3/5/10 dtk (tick Exness, cadangan Dukascopy; research/pra_xau_semua.py). Arah aturan dipilih di LAMA
(< Okt 2021) bila LAMA n ≥ 15, selain itu sesuai teori. LOLOS = emas benar ≥ 60% (rata-rata 2–10 dtk), LAMA & BARU
≥ 55% (n ≥ 10 masing-masing; bila LAMA < 10 maka BARU n ≥ 20), p < 0,05, Dukascopy searah — lalu uji acak permutasi.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

from .news_detik import DATA, NEW
from .news_data import INVERSE, _num, load_calendar

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_pra_per_berita.txt"
JSON = ROOT / "cloud" / "api" / "pra_aset.json"
EKS = ROOT / "data" / "research" / "eksternal"
HH = (2, 3, 5, 10)


def fred_awal(series: str) -> pd.DataFrame:
    """Nilai RILIS PERTAMA per observasi + waktu terbit (realtime_start + 1 hari, UTC)."""
    f = EKS / f"fred_{series}_awal.json"
    if not f.exists():
        url = ("https://api.stlouisfed.org/fred/series/observations?series_id=" + series + "&output_type=4"
               "&realtime_start=1776-07-04&realtime_end=9999-12-31&observation_start=2003-01-01&file_type=json"
               "&api_key=" + os.environ["FRED_API_KEY"])
        with urllib.request.urlopen(url, timeout=90) as r:
            f.write_bytes(r.read())
    obs = [o for o in json.loads(f.read_text())["observations"] if o["value"] != "."]
    df = pd.DataFrame({"value": [float(o["value"]) for o in obs],
                       "available": pd.to_datetime([o["realtime_start"] for o in obs]).tz_localize("UTC")
                       + pd.Timedelta(days=1)}, index=pd.DatetimeIndex([o["date"] for o in obs]))
    return df[~df.index.duplicated()].sort_index()


def spy() -> pd.Series:
    f = EKS / "td_SPY_1day.json"
    if not f.exists():
        url = ("https://api.twelvedata.com/time_series?symbol=SPY&interval=1day&outputsize=5000&order=ASC&timezone=UTC"
               "&apikey=" + os.environ["TWELVEDATA_API_KEY"])
        with urllib.request.urlopen(url, timeout=90) as r:
            f.write_bytes(r.read())
    v = json.loads(f.read_text())["values"]
    return pd.Series([float(x["close"]) for x in v], index=pd.DatetimeIndex([x["datetime"] for x in v]).tz_localize("UTC"))


def kalender() -> pd.DataFrame:
    cal = load_calendar(DATA)
    cal = cal[cal.time >= pd.Timestamp("2009-06-01", tz="UTC")].copy()
    cal["a"], cal["f"], cal["p"] = cal.actual.map(_num), cal.forecast.map(_num), cal.previous.map(_num)
    cal["s"] = np.sign(cal.a - cal.f)
    return cal.reset_index(drop=True)


def sg(v) -> float:
    return 0.0 if v is None or v != v or v == 0 else float(np.sign(v))


def bulan_acuan(t: pd.Timestamp, mundur: int = 1) -> pd.Timestamp:
    return (t.tz_convert(None).to_period("M") - mundur).to_timestamp()


def nilai_bulan(df: pd.DataFrame, t: pd.Timestamp, bulan: pd.Timestamp) -> float:
    s = df[(df.available < t)]
    return float(s.value.get(bulan, np.nan))


def ubah_bulan(df: pd.DataFrame, t: pd.Timestamp, bulan: pd.Timestamp) -> float:
    a = nilai_bulan(df, t, bulan)
    b = nilai_bulan(df, t, (bulan.to_period("M") - 1).to_timestamp())
    return sg(a - b)


def rata_mingguan(df: pd.DataFrame, t: pd.Timestamp, bulan: pd.Timestamp) -> float:
    s = df[df.available < t].value
    cur = s[(s.index >= bulan) & (s.index < bulan + pd.offsets.MonthBegin(1))]
    prev_b = (bulan.to_period("M") - 1).to_timestamp()
    prv = s[(s.index >= prev_b) & (s.index < bulan)]
    return sg(cur.mean() - prv.mean()) if len(cur) >= 2 and len(prv) >= 2 else 0.0


def terakhir(cal: pd.DataFrame, judul: str, t: pd.Timestamp, hari: float) -> pd.Series | None:
    g = cal[(cal.event == judul) & (cal.time < t) & (cal.time >= t - pd.Timedelta(days=hari))]
    return g.iloc[-1] if len(g) else None


def pekan_survei(bulan: pd.Timestamp) -> pd.Timestamp:
    d12 = bulan + pd.Timedelta(days=11)
    return d12 - pd.Timedelta(days=(d12.weekday() + 1) % 7)        # Minggu awal pekan yang memuat tgl 12


FITUR = {
    "Retail Sales m/m": ["AUTO", "BBM"], "Core Retail Sales m/m": ["AUTO", "BBM"],
    "ISM Manufacturing PMI": ["FLASH", "REG"], "ISM Services PMI": ["FLASH"],
    "Core PCE Price Index m/m": ["CPIC", "PPIC", "GAB"],
    "Average Hourly Earnings m/m": ["K12", "PK5"], "Non-Farm Employment Change": ["K12", "PK5"],
    "Unemployment Claims": [], "Prelim UoM Consumer Sentiment": ["SAHAM", "BBM"],
    "CB Consumer Confidence": ["SAHAM", "BBM", "UM"], "ADP Non-Farm Employment Change": ["KLM"],
    "Core CPI m/m": ["Q1"], "CPI m/m": ["Q1"], "PPI m/m": [], "Core PPI m/m": [], "Unemployment Rate": ["K12", "PK5"],
    "JOLTS Job Openings": [], "Advance GDP q/q": [], "CPI y/y": [],
}


def fitur(cal: pd.DataFrame) -> pd.DataFrame:
    auto, bbm = fred_awal("TOTALSA"), fred_awal("GASREGW")
    reg = [fred_awal(s) for s in ("GACDISA066MSFRBNY", "GACDFSA066MSFRBPHI", "BACTSAMFRBDAL")]
    sp = spy()
    rows = []
    for r in cal[cal.event.isin(FITUR)].itertuples():
        t, ev = r.time, r.event
        x = {"time": t, "event": ev, "s": r.s}
        prev = cal[(cal.event == ev) & (cal.time < t - pd.Timedelta(hours=1))].tail(1)
        if len(prev) and (t - prev.time.iloc[0]).days <= (10 if ev == "Unemployment Claims" else 45):
            x["P"] = sg(prev.s.iloc[0])
            x["-P"] = -x["P"]
        x["ANK"] = sg(r.f - r.p) if r.p == r.p and r.f == r.f else 0.0
        m1 = bulan_acuan(t)
        for nm in FITUR[ev]:
            v = 0.0
            if nm == "AUTO":
                v = ubah_bulan(auto, t, m1)
            elif nm == "BBM":
                bm = bulan_acuan(t, 0) if ev in ("Prelim UoM Consumer Sentiment", "CB Consumer Confidence") else m1
                v = rata_mingguan(bbm, t, bm)
                if ev in ("Prelim UoM Consumer Sentiment", "CB Consumer Confidence"):
                    v = -v
            elif nm == "FLASH":
                j = "Flash Manufacturing PMI" if ev.startswith("ISM Manu") else "Flash Services PMI"
                g = terakhir(cal, j, t, 20)
                v = sg(g.a - g.p) if g is not None and g.a == g.a and g.p == g.p else 0.0
            elif nm == "REG":
                v = sg(sum(ubah_bulan(d, t, m1) for d in reg))
            elif nm in ("CPIC", "PPIC", "GAB"):
                c = terakhir(cal, "Core CPI m/m", t, 25)
                p = terakhir(cal, "Core PPI m/m", t, 25)
                cs = sg(c.s) if c is not None else 0.0
                ps = sg(p.s) if p is not None else 0.0
                v = cs if nm == "CPIC" else ps if nm == "PPIC" else sg(cs + ps)
            elif nm == "K12":
                v = 1.0 if (m1 + pd.Timedelta(days=11)).weekday() in (6, 0, 1, 2) else -1.0
            elif nm == "PK5":
                gap = (pekan_survei(m1) - pekan_survei((m1.to_period("M") - 1).to_timestamp())).days
                v = 1.0 if gap >= 35 else -1.0
            elif nm == "SAHAM":
                s = sp[sp.index < t.normalize()]
                v = sg(s.iloc[-1] - s.iloc[-21]) if len(s) > 21 else 0.0
            elif nm == "UM":
                g = terakhir(cal, "Prelim UoM Consumer Sentiment", t, 20)
                v = sg(g.s) if g is not None else 0.0
            elif nm == "KLM":
                cl = cal[(cal.event == "Unemployment Claims") & (cal.time < t) & (cal.time >= t - pd.Timedelta(days=28))]
                v = -sg(cl.s.sum()) if len(cl) else 0.0
            elif nm == "Q1":
                v = 1.0 if m1.month in (1, 2, 3) else 0.0
            x[nm] = v
        rows.append(x)
    return pd.DataFrame(rows)


def target(fx: pd.DataFrame) -> pd.DataFrame:
    from .pra_xau_semua import bangun
    d = bangun()
    keep = ["t0", "H4"] + [f"y{h}_{f}" for h in HH for f in ("XAU_EXNESS", "XAU")]
    return fx.merge(d[keep], left_on="time", right_on="t0", how="left")


def skor(pred: np.ndarray, y: np.ndarray, t: pd.DatetimeIndex) -> dict:
    m = (pred != 0) & ~np.isnan(y) & (y != 0)
    ok = np.sign(pred[m]) == np.sign(y[m])
    tt = t[m]
    lama, baru = ok[tt < NEW], ok[tt >= NEW]
    k, n = int(ok.sum()), int(m.sum())
    return {"n": n, "benar": k / n * 100 if n else np.nan, "p": float(binom.sf(k - 1, n, .5)) if n else 1.0,
            "lama": lama.mean() * 100 if len(lama) else np.nan, "n_lama": int(len(lama)),
            "baru": baru.mean() * 100 if len(baru) else np.nan, "n_baru": int(len(baru))}


def emas(df: pd.DataFrame, pred: np.ndarray, feed: str = "XAU_EXNESS") -> dict:
    """Rata-rata ketepatan arah emas di detik 2/3/5/10 (Exness, cadangan Dukascopy bila feed Exness)."""
    t = pd.DatetimeIndex(df.time)
    hasil = {}
    for h in HH:
        y = df[f"y{h}_{feed}"].to_numpy()
        if feed == "XAU_EXNESS":
            y = np.where(np.isnan(y), df[f"y{h}_XAU"].to_numpy(), y)
        hasil[h] = skor(pred, y, t)
    return hasil


def kutub(ev: str) -> float:
    return 1.0 if ev in INVERSE else -1.0       # arah emas = kutub × tanda kejutan


def uji(df: pd.DataFrame, acak: np.random.Generator | None = None) -> list[dict]:
    out = []
    for ev in FITUR:
        x = df[df.event == ev].reset_index(drop=True)
        if len(x) < 20:
            continue
        if acak is not None:                      # uji permutasi: hasil diacak di dalam judul
            perm = acak.permutation(len(x))
            for c in [c for c in x.columns if c.startswith("y")] + ["s"]:
                x[c] = x[c].to_numpy()[perm]
        t = pd.DatetimeIndex(x.time)
        for nm in ["P", "-P", "ANK"] + FITUR[ev]:
            if nm not in x or (x[nm].fillna(0) == 0).all():
                continue
            v = x[nm].fillna(0).to_numpy()
            lama = t < NEW
            sk = skor(v[lama], x.s.to_numpy()[lama], t[lama])
            if sk["n"] >= 15:
                arah = 1.0 if sk["benar"] >= 50 else -1.0
            else:
                arah = 1.0
            pred_s = arah * v
            ks = skor(pred_s, x.s.to_numpy(), t)
            g = emas(x, kutub(ev) * pred_s)
            gd = emas(x, kutub(ev) * pred_s, "XAU")
            rata = float(np.nanmean([g[h]["benar"] for h in HH]))
            rl = float(np.nanmean([g[h]["lama"] for h in HH]))
            rb = float(np.nanmean([g[h]["baru"] for h in HH]))
            rd = float(np.nanmean([gd[h]["benar"] for h in HH]))
            nl, nb, n = g[5]["n_lama"], g[5]["n_baru"], g[5]["n"]
            cukup = (nl >= 10 and nb >= 10) or (nl < 10 and nb >= 20)
            ok = (rata >= 60 and cukup and (rl >= 55 or nl < 10) and rb >= 55 and g[5]["p"] < 0.05
                  and (rd != rd or rd > 50))
            out.append({"judul": ev, "fitur": nm, "arah": arah, "kejutan": ks, "emas": g, "rata": rata, "lama": rl,
                        "baru": rb, "duka": rd, "n": n, "n_lama": nl, "n_baru": nb, "lolos": bool(ok)})
    return out


def main() -> None:
    cal = kalender()
    fx = fitur(cal)
    df = target(fx)
    hasil = uji(df)
    L = ["# 🎯 Petunjuk khusus per berita → arah XAU 2–10 detik setelah rilis", __doc__.split("\n\n")[1], ""]
    for ev in FITUR:
        rs = [r for r in hasil if r["judul"] == ev]
        if not rs:
            continue
        L.append(f"\n## {ev}")
        for r in rs:
            k = r["kejutan"]
            L.append(f"   {'✅' if r['lolos'] else '  '} {r['fitur']:5s} ({'searah' if r['arah'] > 0 else 'dibalik'}) "
                     f"kejutan {k['benar']:.0f}% (n {k['n']}, LAMA {k['lama']:.0f} BARU {k['baru']:.0f}) → EMAS 2–10 dtk "
                     f"{r['rata']:.1f}% (n {r['n']}; LAMA {r['lama']:.0f}% n {r['n_lama']}, BARU {r['baru']:.0f}% n "
                     f"{r['n_baru']}; p {r['emas'][5]['p']:.3f}; Duka {r['duka']:.0f}%)")
    lolos = [r for r in hasil if r["lolos"]]
    rng = np.random.default_rng(11)
    ac = [sum(r["lolos"] for r in uji(df, rng)) for _ in range(200)]
    L += ["", f"## LOLOS: {len(lolos)} dari {len(hasil)} aturan"]
    L += [f"   {r['judul']} • {r['fitur']}: emas {r['rata']:.1f}% (LAMA {r['lama']:.0f}%, BARU {r['baru']:.0f}%, n {r['n']})"
          for r in lolos] or ["   TIDAK ADA"]
    L.append(f"\n## UJI ACAK (permutasi {len(ac)}×): lolos karena kebetulan rata-rata {np.mean(ac):.2f}, 95% ≤ "
             f"{np.percentile(ac, 95):.0f}; sungguhan {len(lolos)} → peluang kebetulan ≥ {len(lolos)}: "
             f"{np.mean(np.array(ac) >= len(lolos)) * 100:.0f}%")
    # aturan "konsisten lemah" (LAMA & BARU ≥ 55%, p < 0,05, tebakan ANGKA ≥ 54% — tanpa itu tidak ada mekanisme)
    # + gabungan dengan tren emas 4 jam searah → cloud
    simpan = {}
    for r in hasil:
        if not (r["n_lama"] >= 10 and r["n_baru"] >= 10 and r["lama"] >= 55 and r["baru"] >= 55
                and r["emas"][5]["p"] < 0.05 and r["kejutan"]["benar"] >= 54) or r["fitur"] == "P" and r["arah"] < 0:
            continue
        x = df[df.event == r["judul"]]
        g = kutub(r["judul"]) * r["arah"] * x[r["fitur"]].fillna(0).to_numpy()
        h4 = x.H4.fillna(0).to_numpy()
        tr = emas(x, np.where(g == h4, g, 0.0))
        lw = emas(x, np.where((g != h4) & (h4 != 0), g, 0.0))
        rata = lambda e, k="benar": round(float(np.nanmean([e[h][k] for h in HH])), 1)  # noqa: E731
        simpan[f"{r['judul']}|{r['fitur']}"] = {
            "arah": r["arah"], "benar": round(r["rata"], 1), "lama": round(r["lama"], 1), "baru": round(r["baru"], 1),
            "n": r["n"], "p": round(r["emas"][5]["p"], 4), "lolos": r["lolos"],
            "kejutan": round(r["kejutan"]["benar"], 1),
            "tren_searah": {"benar": rata(tr), "lama": rata(tr, "lama"), "baru": rata(tr, "baru"), "n": tr[5]["n"]},
            "tren_lawan": {"benar": rata(lw), "lama": rata(lw, "lama"), "baru": rata(lw, "baru"), "n": lw[5]["n"]}}
        kunci = f"{r['judul']}|{r['fitur']}"
        L.append(f"   → disimpan {kunci}: {simpan[kunci]}")
    d = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    d["per_berita"] = simpan
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    df.to_parquet(EKS / "pra_per_berita.parquet")
    print("\n".join(L))


if __name__ == "__main__":
    main()
