"""Bisakah hasil berita (di atas / di bawah konsensus) ditebak SEBELUM rilis? (python -m research.news_prediksi)

Pertanyaan pengguna (30 Sep 2026): CPI, PPI, FOMC terakhir "kompak" lebih rendah seperti rumor, polling, dan
Polymarket -> kumpulkan data untuk bersiap menghadapi berita berikutnya dan simpulkan dalam persen.

Data: kalender ForexFactory 2010 - Jan 2026 (actual & forecast; spoluan semua dampak < 2020, ehsanrs2 dampak tinggi
>= 2020), bensin FRED GASREGW (dipakai sejak waktu terbit), XAU/USD M15. Polymarket/Kalshi/Cleveland Fed tidak bisa
diakses dari lingkungan riset ini, jadi tidak ikut diuji.

Aturan (ditetapkan sebelum melihat hasil):
- Target = tanda (actual - forecast) event E; 0 = "sesuai" (dilaporkan, tidak ikut hitungan tebakan).
- Petunjuk hanya memakai informasi yang SUDAH ADA sebelum rilis E:
  P1 kejutan rilis sebelumnya event yang sama (<= 45 hari; klaim <= 10 hari);
  P2 ADP -> NFP (ADP <= 7 hari sebelumnya), arah sama; ADP -> Unemployment Rate, arah terbalik;
  P3 klaim pengangguran 4 pekan sebelum NFP (jumlah tanda kejutan), arah terbalik;
  P4 PPI -> CPI (PPI m/m <= 10 hari sebelumnya, headline -> headline & core); P5 CPI -> PPI (sebaliknya);
  P6 CPI/PPI -> Core PCE (core CPI <= 25 hari sebelumnya); P7 bensin rata-rata bulan acuan vs bulan sebelumnya
     (FRED GASREGW) -> CPI m/m, arah sama.
- Nilai = % tebakan benar (hanya kasus petunjuk != 0 dan target != 0), periode LAMA (< Okt 2021) dan BARU.
  TERBUKTI bila > 50% di LAMA DAN BARU (n >= 10 masing-masing) dan p binomial (satu sisi) < 0,05 di semua data.
- Reaksi emas: % XAU naik 15 menit & 1 jam sesudah rilis per arah kejutan (harga open candle M15 saat rilis).
Keluaran: laporan di layar + cloud/api/persiapan.json (dibaca kartu "🎯 Persiapan berita" di tab Tanya).
"""
from __future__ import annotations

import glob
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .event_stats import xau_m15
from .news_data import _num
from .run_scan import DATA

NEW = pd.Timestamp("2021-10-01", tz="UTC")
OUT = Path(__file__).resolve().parent.parent / "cloud" / "api" / "persiapan.json"
EVENTS = ["CPI m/m", "Core CPI m/m", "CPI y/y", "PPI m/m", "Core PPI m/m", "Non-Farm Employment Change",
          "Unemployment Rate", "Average Hourly Earnings m/m", "ADP Non-Farm Employment Change", "Unemployment Claims",
          "Retail Sales m/m", "Core Retail Sales m/m", "Core PCE Price Index m/m", "ISM Manufacturing PMI",
          "ISM Services PMI", "JOLTS Job Openings", "Advance GDP q/q", "Federal Funds Rate"]
# emas umumnya naik bila data LEBIH LEMAH untuk USD; untuk event ini angka lebih tinggi = lebih lemah untuk USD
INVERSE = {"Unemployment Rate", "Unemployment Claims"}


def calendar() -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(DATA / "spoluan_forex-factory-scraper/datasets/*.csv"))):
        d = pd.read_csv(f)
        d = d[(d.Currency == "USD") & d.Event.isin(EVENTS)]
        t = pd.to_datetime(d["Combined DateTime"], errors="coerce") - pd.Timedelta(hours=8)   # UTC+8 -> UTC
        frames.append(pd.DataFrame({"time": t.dt.tz_localize("UTC"), "event": d.Event, "actual": d.Actual,
                                    "forecast": d.Forecast}))
    old = pd.concat(frames)
    old = old[old.time < pd.Timestamp("2020-01-01", tz="UTC")]
    e = pd.read_csv(DATA / "ehsanrs2_forexfactory-scraper/high_impact_events_calendar.csv")
    e = e[(e.Currency == "USD") & e.Event.isin(EVENTS)]
    new = pd.DataFrame({"time": pd.to_datetime(e.DateTime, utc=True), "event": e.Event, "actual": e.Actual,
                        "forecast": e.Forecast})
    cal = pd.concat([old, new[new.time >= pd.Timestamp("2020-01-01", tz="UTC")]]).dropna(subset=["time"])
    cal = cal.drop_duplicates(["time", "event"]).sort_values("time").reset_index(drop=True)
    cal["a"], cal["f"] = cal.actual.map(_num), cal.forecast.map(_num)
    cal = cal[cal.a.notna() & cal.f.notna()].copy()
    cal["s"] = np.sign(cal.a - cal.f)
    return cal.reset_index(drop=True)


def last_before(cal: pd.DataFrame, event: str, t: pd.Timestamp, days: float) -> float:
    g = cal[(cal.event == event) & (cal.time < t) & (cal.time >= t - pd.Timedelta(days=days))]
    return float(g.s.iloc[-1]) if len(g) else np.nan


def binom_p(k: int, n: int) -> float:
    """P(X >= k), X ~ Bin(n, 0,5)."""
    return float(sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n) if n else 1.0


def gas_signal(cal: pd.DataFrame) -> pd.Series:
    """Tanda perubahan rata-rata bensin bulan acuan (bulan sebelum rilis) vs bulan sebelumnya, hanya data terbit."""
    from .eksternal_makro import fred
    g = fred("GASREGW")
    av = pd.DatetimeIndex(g.available)
    idx = pd.DatetimeIndex(g.index).tz_localize("UTC")
    out = {}
    for r in cal[cal.event == "CPI m/m"].itertuples():
        ref = (r.time - pd.DateOffset(months=1)).to_period("M")
        known = (av < r.time)
        m1 = g.value[known & (idx.to_period("M") == ref)]
        m0 = g.value[known & (idx.to_period("M") == ref - 1)]
        out[r.Index] = float(np.sign(m1.mean() - m0.mean())) if len(m1) and len(m0) else np.nan
    return pd.Series(out)


def predictors(cal: pd.DataFrame) -> dict[str, tuple[str, pd.Series]]:
    """nama -> (event target, tanda tebakan per baris kalender target)."""
    out = {}
    for ev in EVENTS:
        rows = cal[cal.event == ev]
        days = 10 if ev == "Unemployment Claims" else 45
        out[f"P1 {ev}: kejutan rilis sebelumnya"] = (ev, pd.Series(
            {i: last_before(cal, ev, r.time, days) for i, r in rows.iterrows()}))
    nfp = cal[cal.event == "Non-Farm Employment Change"]
    ur = cal[cal.event == "Unemployment Rate"]
    adp = "ADP Non-Farm Employment Change"
    out["P2 ADP -> NFP (searah)"] = ("Non-Farm Employment Change", pd.Series(
        {i: last_before(cal, adp, r.time, 7) for i, r in nfp.iterrows()}))
    out["P2 ADP -> Unemployment Rate (terbalik)"] = ("Unemployment Rate", pd.Series(
        {i: -last_before(cal, adp, r.time, 7) for i, r in ur.iterrows()}))
    claims = cal[cal.event == "Unemployment Claims"]

    def claim_sum(t):
        g = claims[(claims.time < t) & (claims.time >= t - pd.Timedelta(days=28))]
        return -float(np.sign(g.s.sum())) if len(g) else np.nan
    out["P3 klaim 4 pekan -> NFP (terbalik)"] = ("Non-Farm Employment Change", pd.Series(
        {i: claim_sum(r.time) for i, r in nfp.iterrows()}))
    for src, dst, lab in (("PPI m/m", "CPI m/m", "P4 PPI -> CPI"), ("PPI m/m", "Core CPI m/m", "P4 PPI -> Core CPI"),
                          ("Core PPI m/m", "Core CPI m/m", "P4 Core PPI -> Core CPI"),
                          ("CPI m/m", "PPI m/m", "P5 CPI -> PPI"), ("Core CPI m/m", "Core PPI m/m", "P5 Core CPI -> Core PPI"),
                          ("Core CPI m/m", "Core PCE Price Index m/m", "P6 Core CPI -> Core PCE"),
                          ("Core PPI m/m", "Core PCE Price Index m/m", "P6 Core PPI -> Core PCE")):
        rows = cal[cal.event == dst]
        days = 25 if "PCE" in dst else 10
        out[lab] = (dst, pd.Series({i: last_before(cal, src, r.time, days) for i, r in rows.iterrows()}))
    out["P7 bensin bulan acuan -> CPI m/m"] = ("CPI m/m", gas_signal(cal))
    return out


def judge(cal: pd.DataFrame, target: str, pred: pd.Series) -> dict:
    rows = cal.loc[pred.index]
    ok = (pred != 0) & pred.notna() & (rows.s != 0)
    hit = (pred[ok] == rows.s[ok])
    old = rows.time[ok] < NEW
    res = {"n": int(ok.sum())}
    for lab, m in (("lama", old), ("baru", ~old)):
        res[lab] = {"n": int(m.sum()), "benar": round(100 * float(hit[m].mean()), 1) if m.sum() else None}
    res["benar"] = round(100 * float(hit.mean()), 1) if len(hit) else None
    res["p"] = round(binom_p(int(hit.sum()), len(hit)), 4)
    res["terbukti"] = bool(res["lama"]["n"] >= 10 and res["baru"]["n"] >= 10 and res["lama"]["benar"] > 50
                           and res["baru"]["benar"] > 50 and res["p"] < 0.05)
    return res


def gold_reaction(cal: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    """% perubahan XAU 15 menit & 1 jam dari open candle M15 saat rilis."""
    o, c, idx = px.open.to_numpy(), px.close.to_numpy(), px.index
    out = []
    for r in cal.itertuples():
        i = idx.searchsorted(r.time, side="right") - 1
        if i < 1 or not (idx[i] <= r.time < idx[i] + pd.Timedelta(minutes=15)) or i + 4 >= len(px):
            out.append((np.nan, np.nan))
            continue
        out.append(((c[i] / o[i] - 1) * 100, (c[i + 3] / o[i] - 1) * 100))
    cal = cal.copy()
    cal["x15"], cal["x1j"] = [a for a, _ in out], [b for _, b in out]
    return cal


def base_rates(cal: pd.DataFrame) -> dict:
    out = {}
    for ev in EVENTS:
        g = cal[cal.event == ev]
        if len(g) < 20:
            continue
        cell = {}
        for lab, m in (("semua", g.time.notna()), ("lama", g.time < NEW), ("baru", g.time >= NEW)):
            x = g[m]
            cell[lab] = {"n": int(len(x)), "bawah": round(100 * float((x.s < 0).mean())),
                         "sesuai": round(100 * float((x.s == 0).mean())), "atas": round(100 * float((x.s > 0).mean()))}
        rx = {}
        for tag, m in (("bawah", g.s < 0), ("atas", g.s > 0), ("sesuai", g.s == 0)):
            x = g[m & g.x1j.notna()]
            if len(x) >= 8:
                rx[tag] = {"n": int(len(x)), "naik15m": round(100 * float((x.x15 > 0).mean())),
                           "naik1j": round(100 * float((x.x1j > 0).mean())),
                           "rata1j": round(float(x.x1j.mean()), 3),
                           "baru_naik1j": round(100 * float((x[x.time >= NEW].x1j > 0).mean()))
                           if (x.time >= NEW).sum() >= 5 else None,
                           "tahun": f"{x.time.min():%Y}–{x.time.max():%Y}"}
        cell["emas"] = rx
        x = g[g.x1j.notna()]                      # tanpa tahu hasil = tebakan sebelum rilis
        cell["emas_sebelum"] = {"n": int(len(x)), "naik1j": round(100 * float((x.x1j > 0).mean())),
                                "baru_naik1j": round(100 * float((x[x.time >= NEW].x1j > 0).mean()))}
        cell["kebalikan"] = ev in INVERSE
        out[ev] = cell
    return out


def conditional(cal: pd.DataFrame, target: str, pred: pd.Series) -> dict:
    """Per kondisi petunjuk (bawah/atas): sebaran hasil target (termasuk 'sesuai') & % emas naik 1 jam."""
    out = {}
    for tag, v in (("bawah", -1.0), ("atas", 1.0)):
        rows = cal.loc[pred.index[pred == v]]
        if len(rows) < 8:
            continue
        cell = {}
        for lab, m in (("semua", rows.time.notna()), ("lama", rows.time < NEW), ("baru", rows.time >= NEW)):
            x = rows[m]
            gx = x[x.x1j.notna()]
            cell[lab] = {"n": int(len(x)), "bawah": round(100 * float((x.s < 0).mean())) if len(x) else None,
                         "sesuai": round(100 * float((x.s == 0).mean())) if len(x) else None,
                         "atas": round(100 * float((x.s > 0).mean())) if len(x) else None,
                         "emas_naik1j": round(100 * float((gx.x1j > 0).mean())) if len(gx) else None,
                         "n_emas": int(len(gx))}
        out[tag] = cell
    return out


def main() -> None:
    cal = calendar()
    print(f"# Prediksi hasil berita sebelum rilis (research/news_prediksi.py)\n\nkalender {cal.time.min():%Y-%m-%d} .. "
          f"{cal.time.max():%Y-%m-%d}, {len(cal)} rilis bernilai\n")
    cal = gold_reaction(cal, xau_m15())
    br = base_rates(cal)
    print("## Peluang dasar (bawah / sesuai / atas konsensus) dan reaksi emas 1 jam")
    for ev, c in br.items():
        s, lo, ne = c["semua"], c["lama"], c["baru"]
        rx = " | ".join(f"{k}: naik1j {v['naik1j']}% (n={v['n']}, rata {v['rata1j']:+.2f}%, BARU {v['baru_naik1j']}%)"
                        for k, v in c["emas"].items())
        print(f"- {ev}: {s['bawah']}/{s['sesuai']}/{s['atas']}% (n={s['n']}; LAMA {lo['bawah']}/{lo['sesuai']}/"
              f"{lo['atas']}, BARU {ne['bawah']}/{ne['sesuai']}/{ne['atas']})\n    emas: {rx}")
    print("\n## Petunjuk sebelum rilis -> arah kejutan (% tebakan benar)")
    res = {}
    for name, (target, pred) in predictors(cal).items():
        j = judge(cal, target, pred)
        res[name] = {"target": target, **j}
        if j["n"] >= 10:
            print(f"- {name}: {j['benar']}% (n={j['n']}) | LAMA {j['lama']['benar']}% ({j['lama']['n']}) | BARU "
                  f"{j['baru']['benar']}% ({j['baru']['n']}) | p={j['p']}{'  TERBUKTI' if j['terbukti'] else ''}")
    ok = [k for k, v in res.items() if v["terbukti"]]
    print(f"\n-> terbukti: {len(ok)} dari {sum(1 for v in res.values() if v['n'] >= 10)} petunjuk: {ok}")
    print("\n## Kondisi petunjuk -> hasil (bawah/sesuai/atas) & emas naik 1 jam")
    preds = predictors(cal)
    for name in ok + [k for k in preds if k.startswith("P5")]:
        target, pred = preds[name]
        res[name]["kondisi"] = conditional(cal, target, pred)
        for tag, c in res[name]["kondisi"].items():
            print(f"- {name} | petunjuk {tag}: " + " | ".join(
                f"{p.upper()} n={c[p]['n']} {c[p]['bawah']}/{c[p]['sesuai']}/{c[p]['atas']}% emas naik1j "
                f"{c[p]['emas_naik1j']}%" for p in ("semua", "lama", "baru") if c[p]["n"]))
    for name, v in res.items():                   # ringkasan per event untuk kartu aplikasi
        ev = v["target"]
        if ev not in br or v["n"] < 10:
            continue
        naik = [c["semua"]["emas_naik1j"] for c in v.get("kondisi", {}).values() if c["semua"]["emas_naik1j"] is not None]
        br[ev].setdefault("petunjuk", []).append({
            "nama": name.split(": ", 1)[-1] if name.startswith("P1") else name[3:], "benar": v["benar"],
            "lama": v["lama"]["benar"], "baru": v["baru"]["benar"], "n": v["n"], "terbukti": v["terbukti"],
            "emas_naik1j": [min(naik), max(naik)] if naik else None})
    tested = [v for v in res.values() if v["n"] >= 10]
    naik = [x for k in ok for c in res[k].get("kondisi", {}).values() for x in [c["semua"]["emas_naik1j"]] if x is not None]
    benar = [res[k]["benar"] for k in ok]
    cpi = br["CPI m/m"]["emas"]
    kesimpulan = (
        f"Diuji {len(tested)} petunjuk yang sudah ada SEBELUM rilis (kejutan bulan lalu, ADP, klaim, PPI↔CPI, bensin) "
        f"di data {cal.time.min():%Y}–{cal.time.max():%Y}: {len(ok)} terbukti, semuanya untuk CPI (arah benar "
        f"{min(benar):.0f}–{max(benar):.0f}%). Tetapi peluang emas naik 1 jam sesudah rilis tetap {min(naik)}–{max(naik)}% "
        f"(≈ lempar koin), karena ±1/3 CPI keluar sesuai perkiraan. Emas baru bereaksi jelas SETELAH angka keluar "
        f"(CPI di bawah perkiraan → emas naik 1 jam {cpi['bawah']['naik1j']}%, di atas → {cpi['atas']['naik1j']}%), "
        f"dan entry sesudah rilis sudah diuji 36 cara dan rugi (spread & slippage). Polymarket/Kalshi belum diuji.")
    print("\n" + kesimpulan)
    OUT.write_text(json.dumps({"dibuat": "research/news_prediksi.py", "periode": f"{cal.time.min():%Y-%m} .. "
                               f"{cal.time.max():%Y-%m}", "kesimpulan": kesimpulan, "dasar": br, "petunjuk": res},
                              ensure_ascii=False,
                              indent=1) + "\n", encoding="utf-8")
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
