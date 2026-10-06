"""Binance Copy Trading (futures): siapa lead trader terbaik & apakah bertahan? — python -m research.binance_copy unduh|uji

Endpoint publik /bapi/futures/v1/friendly/future/copy-trade/home-page/query-list (dibuka pengguna 6 Okt 2026): tiap lead
portfolio publik → ROI, PnL, AUM, MDD, win rate, PnL PENGIKUT (copierPnl), jumlah pengikut, grafik ROI harian 365 hari.
Uji persistensi: pilih dengan 180 hari pertama grafik (ROI, MDD, % hari naik sebagai proksi WR), ukur 185 hari sesudahnya.
Hanya portfolio yang MASIH publik → bias penyintas (yang ditutup karena rugi tidak tercatat), hasil nyata lebih buruk.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .eksternal import cache_path

URL = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/home-page/query-list"
DIR = cache_path("binance_copy")
OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_binance_copy.txt"


def page(n: int, tr: str = "365D", size: int = 50) -> dict:
    body = json.dumps({"pageNumber": n, "pageSize": size, "timeRange": tr, "dataType": "ROI", "favoriteOnly": False,
                       "hideFull": False, "nickname": "", "order": "DESC", "userAsset": 0,
                       "portfolioType": "PUBLIC"}).encode()
    for i in range(4):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json",
                                                                   "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)["data"]
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    return {"list": []}


def unduh() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    for tr in ("365D", "90D", "30D"):
        rows, n = [], 1
        while True:
            d = page(n, tr)
            lst = d.get("list") or []
            if not lst:
                break
            rows += lst
            n += 1
            time.sleep(0.4)
        (DIR / f"list_{tr}.json").write_text(json.dumps(rows))
        print(tr, len(rows), flush=True)


def load(tr: str) -> pd.DataFrame:
    rows = json.loads((DIR / f"list_{tr}.json").read_text())
    df = pd.DataFrame([{k: r.get(k) for k in ("leadPortfolioId", "nickname", "currentCopyCount", "roi", "pnl", "aum", "mdd",
                                                "winRate", "copierPnl", "startTime", "badgeName")} for r in rows])
    df["chart"] = [[c["value"] for c in r.get("chartItems") or []] for r in rows]
    return df.drop_duplicates("leadPortfolioId").set_index("leadPortfolioId")


def mdd(eq: np.ndarray) -> float:
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def uji() -> None:
    d = load("365D")
    L = ["# Binance Copy Trading: lead trader terbaik & persistensi (research/binance_copy.py)",
         f"{len(d)} lead portfolio publik (data {pd.Timestamp.now():%Y-%m-%d}). Bias penyintas: portfolio yang sudah ditutup "
         "tidak tercatat.", "", "## Profil 365 hari"]
    d["copier_pos"] = d.copierPnl > 0
    for lab, q in (("semua", d), ("≥ 50 pengikut", d[d.currentCopyCount >= 50]), ("WR ≥ 80%", d[d.winRate >= 80]),
                   ("ROI ≥ 100%", d[d.roi >= 100]), ("MDD ≤ 20%", d[d.mdd <= 20])):
        L.append(f"   {lab}: n {len(q)} | median ROI {q.roi.median():+.0f}% | median MDD {q.mdd.median():.0f}% | "
                 f"median WR {q.winRate.median():.0f}% | PnL pengikut positif {q.copier_pos.mean() * 100:.0f}% | "
                 f"total PnL pengikut {q.copierPnl.sum() / 1e6:+.1f} jt USDT")
    L.append(f"   korelasi WR vs MDD {d[['winRate', 'mdd']].corr().iloc[0, 1]:+.2f}; WR vs PnL pengikut (rank) "
             f"{d[['winRate', 'copierPnl']].rank().corr().iloc[0, 1]:+.2f}; ROI vs PnL pengikut (rank) "
             f"{d[['roi', 'copierPnl']].rank().corr().iloc[0, 1]:+.2f}")
    # persistensi dari grafik ROI harian
    rows = []
    for pid, r in d.iterrows():
        c = np.array(r.chart, float)
        if len(c) < 360:
            continue
        eq = 1 + c / 100
        if (eq <= 0).any():
            eq = np.clip(eq, 1e-3, None)
        a, b = eq[:180], eq[180:]
        dr = np.diff(a) / a[:-1]
        rows.append({"id": pid, "past": a[-1] / a[0] - 1, "past_mdd": mdd(a), "upday": (dr > 0).sum() / max((dr != 0).sum(), 1),
                     "active": (dr != 0).mean(), "fut": b[-1] / a[-1] - 1, "fut_mdd": mdd(np.r_[a[-1], b]),
                     "wr_now": r.winRate, "copiers": r.currentCopyCount, "copier_pnl": r.copierPnl})
    p = pd.DataFrame(rows).set_index("id")
    p = p[p.active > 0.3]                       # aktif berdagang di 180 hari pertama
    L += ["", f"## Persistensi: pilih dengan hari 1–180, ukur hari 181–365 (n {len(p)} portfolio aktif penuh 365 hari)",
          "| Cara memilih (20 teratas) | Return 180 hari lalu | Return 185 hari berikutnya (median / rata) | Rugi ke depan | MDD ke depan (median) |",
          "|---|---|---|---|---|"]
    picks = {"ROI tertinggi": p.past.nlargest(20).index,
             "% hari naik tertinggi (proksi WR)": p.upday.nlargest(20).index,
             "ROI / MDD": (p.past / p.past_mdd.abs().clip(lower=0.02)).nlargest(20).index,
             "aman: ROI > 0, MDD ≤ 15%": p[(p.past > 0) & (p.past_mdd >= -0.15)].past.nlargest(20).index,
             "semua (rata-rata)": p.index}
    for k, s in picks.items():
        x = p.loc[s]
        L.append(f"| {k} | {x.past.median() * 100:+.0f}% | {x.fut.median() * 100:+.1f}% / {x.fut.mean() * 100:+.1f}% | "
                 f"{(x.fut < 0).mean() * 100:.0f}% | {x.fut_mdd.median() * 100:.0f}% |")
    q = p.copy()
    q["dec"] = pd.qcut(q.past.rank(method="first"), 10, labels=False)
    L.append("   Desil ROI 180 hari pertama → median return berikutnya: " +
             " ".join(f"D{i + 1}:{v * 100:+.0f}%" for i, v in q.groupby("dec").fut.median().items()))
    L.append(f"   korelasi rank return lalu vs berikutnya: {p[['past', 'fut']].rank().corr().iloc[0, 1]:+.2f}; "
             f"% hari naik lalu vs return berikutnya: {p[['upday', 'fut']].rank().corr().iloc[0, 1]:+.2f}")
    # kandidat sekarang dengan saringan aman
    cand = d[(d.mdd <= 20) & (d.roi > 0) & (d.copierPnl > 0) & (d.currentCopyCount >= 20)]
    cand = cand.assign(skor=cand.roi / cand.mdd.clip(lower=3)).sort_values("skor", ascending=False)
    L += ["", f"## Kandidat sekarang (365 hari: MDD ≤ 20%, ROI > 0, PnL pengikut > 0, ≥ 20 pengikut): {len(cand)}"]
    for pid, r in cand.head(15).iterrows():
        L.append(f"   {r.nickname} ({pid}) ROI {r.roi:+.0f}% MDD {r.mdd:.0f}% WR {r.winRate:.0f}% pengikut "
                 f"{r.currentCopyCount} PnL pengikut {r.copierPnl:+,.0f}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    cand.head(30).drop(columns=["chart"]).to_csv(DIR / "kandidat.csv")
    print("\n".join(L))


if __name__ == "__main__":
    {"unduh": unduh, "uji": uji}[sys.argv[1]]()
