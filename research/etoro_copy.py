"""eToro CopyTrader: siapa yang layak disalin & apakah bertahan? — python -m research.etoro_copy unduh|uji

Host www.etoro.com dibuka pengguna (6 Okt 2026). Endpoint publik situs (tanpa kunci):
* /sapi/rankings/rankings/?period=OneYearAgo&... → profil per investor: Gain, RiskScore, Copiers, CopiersGain (= perubahan
  JUMLAH penyalin vs BaseLineCopiers, BUKAN untung penyalin), WinRatio, PeakToValley (DD), ProfitableMonthsPct, Trades, dst.
  API hanya memberi 1.500 baris pertama per query → rankings_all memecah rentang Gain.
* /sapi/userstats/gain/cid/<cid>/history → return BULANAN sejak akun dibuka (isSimulation = bukan uang asli → dibuang).
Semesta: investor yang bisa disalin (copyblock=false) dan Popular Investor ATAU punya ≥ 1 penyalin.
Uji persistensi: tiap bulan M pilih dengan 12 bulan riwayat → ukur 6 & 12 bulan sesudahnya; LAMA (< Okt 2021) vs BARU.
Bias penyintas: akun yang ditutup / kehilangan semua penyalin tidak ada di daftar → hasil nyata lebih buruk.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "etoro"
OUT = ROOT / "docs" / "eksternal" / "hasil_etoro.txt"
BASE = "https://www.etoro.com/sapi"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 "
                    "Safari/537.36", "Accept": "application/json"}
FIELDS = ("CustomerId", "UserName", "FullName", "Verified", "PopularInvestor", "IsFund", "Gain", "FiveYearGain",
          "AnnualizedReturn", "RiskScore", "MaxDailyRiskScore", "MaxMonthlyRiskScore", "Copiers", "BaseLineCopiers",
          "CopiersGain", "AUMValue", "DailyDD", "WeeklyDD", "ProfitableWeeksPct", "ProfitableMonthsPct", "PeakToValley",
          "Trades", "WinRatio", "HighLeveragePct", "LowLeveragePct", "LongPosPct", "TopTradedAssetClassId",
          "TopTradedInstrumentPct", "TotalTradedInstruments", "ActiveWeeks", "LastActivity", "WeeksSinceRegistration",
          "Country", "Exposure", "AvgPosSize")
LAMA_AKHIR = pd.Period("2021-09", "M")


def get(url: str, tries: int = 4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    return None


def rankings(extra: str, period: str = "OneYearAgo", size: int = 500) -> list[dict]:
    rows, page, total = [], 1, None
    while total is None or (page - 1) * size < total:
        d = None
        for i in range(6):                          # halaman gagal → coba lagi (jangan berhenti diam-diam)
            d = get(f"{BASE}/rankings/rankings/?client_request_id=1&blocked=false&bonusonly=false&copyblock=false"
                    f"&istestaccount=false&period={period}{extra}&page={page}&pagesize={size}")
            if d and d.get("Items") is not None:
                break
            time.sleep(10 * (i + 1))
        if not d:
            raise RuntimeError(f"rankings eToro halaman {page} gagal")
        total = d.get("TotalRows") or 0
        items = d.get("Items") or []
        if not items:
            break
        rows += [{k: it.get(k) for k in FIELDS} for it in items]
        page += 1
        time.sleep(1.0)
    return rows


def rankings_all(extra: str, period: str = "OneYearAgo", cap: int = 1500) -> list[dict]:
    """API hanya memberi 1.500 baris pertama per query → pecah rentang Gain (bisection) sampai tiap potong ≤ 1.500."""
    out, stack = {}, [(-100.0, 0.0), (0.01, 10.0), (10.01, 25.0), (25.01, 50.0), (50.01, 100.0), (100.01, 1e6)]
    while stack:
        lo, hi = stack.pop()
        q = f"{extra}&gainmin={lo:g}&gainmax={hi:g}"
        d = get(f"{BASE}/rankings/rankings/?client_request_id=1&blocked=false&bonusonly=false&copyblock=false"
                f"&istestaccount=false&period={period}{q}&page=1&pagesize=1")
        n = (d or {}).get("TotalRows") or 0
        if n > cap and 0.02 < hi - lo and hi < 1e5:
            mid = round((lo + hi) / 2, 2)
            stack += [(lo, mid), (mid + 0.01, hi)]
            continue
        if n:
            for r in rankings(q, period):
                out[r["CustomerId"]] = r
        time.sleep(0.5)
    return list(out.values())


def history(cid: int) -> dict | None:
    return get(f"{BASE}/userstats/gain/cid/{cid}/history?IncludeSimulation=true")


def unduh() -> None:
    (DIR / "hist").mkdir(parents=True, exist_ok=True)
    rows = rankings_all("&popularinvestor=true") + rankings_all("&copiersmin=1")
    df = pd.DataFrame(rows).drop_duplicates("CustomerId")
    df.to_csv(DIR / "rankings_1y.csv", index=False)
    print("rankings", len(df), flush=True)
    todo = [int(c) for c in df.CustomerId if not (DIR / "hist" / f"{int(c)}.json").exists()]

    def one(cid: int) -> None:
        h = history(cid)
        if h is not None:
            (DIR / "hist" / f"{cid}.json").write_text(json.dumps(h))
        time.sleep(0.4)
    with ThreadPoolExecutor(3) as ex:
        for n, _ in enumerate(ex.map(one, todo)):
            if n % 500 == 0:
                print("riwayat", n, "/", len(todo), flush=True)
    pack()
    print("SELESAI", flush=True)


def pack() -> None:
    """Satukan hist/*.json → hist.json.gz (yang di-commit; folder hist/ di-gitignore)."""
    d = {f.stem: json.loads(f.read_text()).get("monthly") or [] for f in (DIR / "hist").glob("*.json")}
    (DIR / "hist.json.gz").write_bytes(gzip.compress(json.dumps(d, separators=(",", ":")).encode()))


def monthly(h: dict) -> pd.Series:
    """Return bulanan uang asli (pecahan), indeks Period bulanan; bulan pertama (sebagian) ikut."""
    m = {pd.Timestamp(x["start"]).tz_localize(None).to_period("M"): x["gain"] / 100 for x in h.get("monthly") or []
         if not x.get("isSimulation")}
    return pd.Series(m, dtype=float).sort_index()


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    rk = pd.read_csv(DIR / "rankings_1y.csv").set_index("CustomerId")
    files = list((DIR / "hist").glob("*.json"))
    raw = ({f.stem: json.loads(f.read_text()) for f in files} if files else
           {k: {"monthly": v} for k, v in json.loads(gzip.decompress((DIR / "hist.json.gz").read_bytes())).items()})
    cols = {}
    for k, h in raw.items():
        s = monthly(h)
        if len(s) >= 18:
            cols[int(k)] = s
    R = pd.DataFrame(cols).sort_index()
    return rk, R


def _mdd(r: pd.DataFrame) -> pd.Series:
    eq = (1 + r.fillna(0)).cumprod()
    return (eq / eq.cummax() - 1).min()


def _spx() -> pd.Series | None:
    """S&P 500 akhir bulan dari FRED (seri SP500, ±10 tahun) sebagai pembanding; None bila tanpa kunci/gagal."""
    import os
    f = DIR / "sp500_fred.json"
    if not f.exists():
        key = os.environ.get("FRED_API_KEY", "")
        if not key:
            return None
        d = get("https://api.stlouisfed.org/fred/series/observations?series_id=SP500&file_type=json&api_key=" + key)
        if not d:
            return None
        f.write_text(json.dumps(d["observations"]))
    o = pd.DataFrame(json.loads(f.read_text()))
    o = o[o.value != "."]
    s = pd.Series(o.value.astype(float).values, index=pd.to_datetime(o.date))
    s = s.groupby(s.index.to_period("M")).last()
    return s


def uji() -> None:
    rk, R = load()
    R = R.loc[:pd.Timestamp.now().to_period("M") - 1]          # buang bulan berjalan
    L = ["# eToro CopyTrader: siapa yang layak disalin & apakah bertahan? (research/etoro_copy.py)",
         f"{len(rk)} investor yang bisa disalin (Popular Investor atau punya penyalin), riwayat bulanan ≥ 18 bulan: "
         f"{R.shape[1]}. Data {pd.Timestamp.now():%Y-%m-%d}. Bias penyintas: akun tutup/tanpa penyalin tidak tercatat.", "",
         "## Profil 12 bulan terakhir (angka eToro)"]
    rk["cpos"] = rk.CopiersGain > 0                              # CopiersGain = % perubahan jumlah penyalin
    for lab, q in (("semua", rk), ("Popular Investor", rk[rk.PopularInvestor == True]),  # noqa: E712
                   ("≥ 100 penyalin", rk[rk.Copiers >= 100]), ("WR ≥ 80%", rk[rk.WinRatio >= 80]),
                   ("Gain ≥ 50%", rk[rk.Gain >= 50]), ("risk score ≤ 4", rk[rk.RiskScore <= 4]),
                   ("DD (peak-to-valley) ≥ −15%", rk[rk.PeakToValley >= -15])):
        L.append(f"   {lab}: n {len(q)} | median gain {q.Gain.median():+.0f}% | median DD {q.PeakToValley.median():.0f}% | "
                 f"median WR {q.WinRatio.median():.0f}% | % bulan untung {q.ProfitableMonthsPct.median():.0f}% | "
                 f"penyalin bertambah {q.cpos.mean() * 100:.0f}%")
    sp = rk[["WinRatio", "Gain", "RiskScore", "PeakToValley"]].rank().corr()
    L.append(f"   korelasi peringkat: WR vs gain {sp.loc['WinRatio', 'Gain']:+.2f}, WR vs DD {sp.loc['WinRatio', 'PeakToValley']:+.2f}, "
             f"risk score vs DD {sp.loc['RiskScore', 'PeakToValley']:+.2f}")
    kelas = rk.TopTradedAssetClassId.map({1: "forex", 2: "komoditas", 4: "indeks", 5: "saham", 6: "ETF", 10: "kripto"})
    L.append("   aset utama: " + ", ".join(f"{k} {v * 100:.0f}%" for k, v in kelas.fillna("lain").value_counts(normalize=True).items()))

    # ---- persistensi
    sel_names = ("semua", "growth 12 bln tertinggi 10", "WR proksi (% bulan untung) tertinggi 10", "aturan",
                 "aturan, 10 teratas", "aturan ketat, 10 teratas")
    res = {k: [] for k in sel_names}
    spx = _spx()
    for m in R.index[12:-6]:
        past, f6, f12 = R.loc[m - 11:m], R.loc[m + 1:m + 6], R.loc[m + 1:m + 12]
        ok = (past.notna().sum() >= 12) & (f6.notna().sum() >= 1)
        ids = ok[ok].index
        if len(ids) < 30:
            continue
        p = past[ids]
        g = (1 + p).prod() - 1
        h1, h2 = (1 + p.iloc[:6]).prod() - 1, (1 + p.iloc[6:]).prod() - 1
        worst, upm, dd = p.min(), (p > 0).mean(), _mdd(p)
        r6 = (1 + f6[ids].fillna(0)).prod() - 1
        r12 = (1 + f12[ids].fillna(0)).prod() - 1
        dd6 = _mdd(f6[ids])
        rule = (h1 > 0) & (h2 > 0) & (worst > -0.10) & (dd > -0.20) & (g <= 3.0)
        strict = rule & (worst > -0.06) & (upm >= 0.6) & (dd > -0.12)
        score = g / dd.abs().clip(lower=0.03)
        sel = {"semua": ids, "growth 12 bln tertinggi 10": g.nlargest(10).index,
               "WR proksi (% bulan untung) tertinggi 10": (upm + g * 1e-6).nlargest(10).index,
               "aturan": ids[rule.values], "aturan, 10 teratas": score[rule].nlargest(10).index,
               "aturan ketat, 10 teratas": score[strict].nlargest(10).index}
        for k, s in sel.items():
            if len(s):
                res[k].append({"m": m, "r6": r6[s].median(), "r12": r12[s].median() if len(f12) == 12 else np.nan,
                               "neg6": (r6[s] < 0).mean(), "bad6": (r6[s] < -0.3).mean(), "dd6": dd6[s].median(),
                               "n": len(s)})
        if spx is not None and m + 6 <= spx.index[-1] and m >= spx.index[0]:
            res.setdefault("S&P 500 (pembanding, FRED)", []).append(
                {"m": m, "r6": spx[m + 6] / spx[m] - 1, "r12": spx[m + 12] / spx[m] - 1 if m + 12 <= spx.index[-1] else np.nan,
                 "neg6": float(spx[m + 6] < spx[m]), "bad6": 0.0, "dd6": np.nan, "n": 1})
    L += ["", "## Persistensi (tiap bulan pilih dengan 12 bulan, ukur sesudahnya; median per periode)",
          "aturan = untung di 2 paruh, bulan terburuk > −10%, DD 12 bln > −20%, growth ≤ 300%; ketat = + bulan terburuk > −6%, "
          "≥ 60% bulan untung, DD > −12%; peringkat growth/DD.",
          "| Cara memilih | n rata | 6 bln ke depan | 12 bln ke depan | Rugi 6 bln | < −30% | DD 6 bln | LAMA 6 bln (rugi) | BARU 6 bln (rugi) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for k, v in res.items():
        x = pd.DataFrame(v)
        if x.empty:
            continue
        lama, baru = x[x.m <= LAMA_AKHIR], x[x.m > LAMA_AKHIR]
        L.append(f"| {k} | {x.n.mean():.0f} | {x.r6.median() * 100:+.1f}% | {x.r12.median() * 100:+.1f}% | "
                 f"{x.neg6.mean() * 100:.0f}% | {x.bad6.mean() * 100:.0f}% | {x.dd6.median() * 100:.0f}% | "
                 f"{lama.r6.median() * 100:+.1f}% ({lama.neg6.mean() * 100:.0f}%) | {baru.r6.median() * 100:+.1f}% "
                 f"({baru.neg6.mean() * 100:.0f}%) |")
    x0 = pd.DataFrame(res["semua"])
    L.append(f"   {len(x0)} periode {x0.m.iloc[0]}–{x0.m.iloc[-1]}; LAMA = pilih ≤ Sep 2021, BARU = sesudahnya.")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    {"unduh": unduh, "uji": uji, "pack": pack}[sys.argv[1]]()
