"""Unduh & uji sinyal copy trade MQL5 (MT5 + MT4) — python -m research.mql5_signals unduh|detail|uji

Permintaan pengguna (6 Okt 2026, host www.mql5.com dibuka): cari penyedia copy trade WR & profit tinggi, uji validitas.
* unduh  : semua halaman daftar /en/signals/{mt5,mt4}/list/pageN → data/research/eksternal/mql5/list_*.csv
           (harga, growth, pelanggan, dana, saldo, minggu, % EA, trades, win %, aktivitas, PF, expected payoff, DD, leverage)
* detail : halaman sinyal (umur ≥ 26 minggu) → return bulanan (tabel growth), max deposit load, DD saldo/ekuitas, simbol
           utama, algo % → data/research/eksternal/mql5/detail/<id>.json   (jeda 1 dtk, sopan)
* uji    : persistensi — penyedia dipilih dengan data s.d. bulan M (WR, growth, profit/DD, saringan aman) → return bulanan
           sesudah M. Catatan: daftar MQL5 hanya memuat sinyal yang MASIH aktif → bias penyintas (hasil asli lebih buruk).
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from html import unescape
from pathlib import Path

import pandas as pd

from .eksternal import cache_path

BASE = "https://www.mql5.com"
DIR = cache_path("mql5")
UA = {"User-Agent": "Mozilla/5.0 (riset pribadi; 1 permintaan/detik)"}


def get(url: str, tries: int = 4) -> str:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    return ""


def num(t: str) -> float | None:
    t = unescape(t).replace("\xa0", " ").strip()
    m = re.match(r"(-?[\d ]+(?:\.\d+)?)\s*([KM]?)", t)
    if not m:
        return None
    v = float(m.group(1).replace(" ", ""))
    return v * {"": 1, "K": 1e3, "M": 1e6}[m.group(2)]


ROW = re.compile(r'<div class="row signal">(.*?)<div class="col-btns">', re.S)


def parse_list(html: str, mt: str) -> list[dict]:
    out = []
    for r in ROW.findall(html):
        g = lambda cls: (re.search(rf'class="col-{cls}[^"]*"[^>]*>(.*?)</div>', r, re.S) or [None, ""])[1]  # noqa: E731
        sid = re.search(r"/signals/(\d+)", r)
        name = re.search(r'<span class="name">(.*?)</span>', r, re.S)
        price = re.search(r'price-value">(.*?)<', r)
        real = "Real Account" in r
        out.append({"id": int(sid.group(1)) if sid else None, "mt": mt, "name": unescape(name.group(1)) if name else "",
                    "real": real, "price": num(price.group(1)) if price else 0.0,
                    "growth": num(re.sub("<[^>]+>", "", g("growth"))), "subs": num(g("subscribers")),
                    "funds": num(re.sub("<[^>]+>", " ", g("facilities"))), "balance": num(re.sub("<[^>]+>", " ", g("balance"))),
                    "weeks": num(g("weeks")), "ea": num(g("experts")), "trades": num(g("trades")), "win": num(g("plus")),
                    "activity": num(g("activity")), "pf": num(g("pf")), "dd": num(g("drawdown")),
                    "lev": (re.search(r"1:(\d+)", g("leverage")) or [None, None])[1]})
    return out


def unduh() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    for mt in ("mt5", "mt4"):
        rows, p = [], 1
        while True:
            html = get(f"{BASE}/en/signals/{mt}/list/page{p}")
            r = parse_list(html, mt)
            if not r:
                break
            rows += r
            if p % 20 == 0:
                print(mt, "halaman", p, len(rows), flush=True)
            p += 1
            time.sleep(1.0)
        df = pd.DataFrame(rows).drop_duplicates("id")
        df.to_csv(DIR / f"list_{mt}.csv", index=False)
        print(mt, len(df), "sinyal", flush=True)


def parse_detail(html: str) -> dict:
    out = {}
    m = re.search(r"table:\{years:\[(.*?)\],total", html, re.S)
    months = {}
    if m:
        for y in re.finditer(r"\{year:(\d+),yearly:[^,]*,months:\{(.*?)\}\}", m.group(1), re.S):
            for k, v in re.findall(r'"(\d+)":(-?[\d.]+)', y.group(2)):
                months[f"{y.group(1)}-{int(k) + 1:02d}"] = float(v)
    out["months"] = months

    def lab(name):
        k = re.search(rf"{re.escape(name)}:?\s*</div>\s*<div class=\"s-data-columns__value\">(.*?)</div>", html, re.S)
        return re.sub("<[^>]+>", "", k.group(1)).strip() if k else None
    for key in ("Max deposit load", "Algo trading", "Profit Trades", "Loss Trades", "Trades", "Maximum drawdown",
                "By Balance", "By Equity", "Profit Factor", "Recovery Factor", "Sharpe Ratio", "Average holding time"):
        out[key] = lab(key)
    sym = re.findall(r'<td class="col-symbol">(.*?)</td>\s*<td class="col-buy-sell col-right">(\d+)', html)
    out["symbols"] = [(s, int(n)) for s, n in sym[:5]]
    st = re.search(r"Started:</div>\s*<div class=\"s-list-info__value\">\s*([\d.]+)", html)
    out["started"] = st.group(1) if st else None
    return out


def detail(min_weeks: int = 26) -> None:
    d = DIR / "detail"
    d.mkdir(parents=True, exist_ok=True)
    lst = pd.concat([pd.read_csv(f) for f in DIR.glob("list_*.csv")])
    lst = lst[(lst.weeks >= min_weeks)].sort_values("weeks", ascending=False)
    todo = [i for i in lst.id.dropna().astype(int) if not (d / f"{i}.json").exists()]
    print(len(todo), "detail", flush=True)
    for n, i in enumerate(todo):
        html = get(f"{BASE}/en/signals/{i}")
        if html:
            (d / f"{i}.json").write_text(json.dumps(parse_detail(html)))
        if n % 100 == 0:
            print(n, i, flush=True)
        time.sleep(1.0)


def pct(x) -> float | None:
    if not x:
        return None
    m = re.search(r"(-?[\d.]+)%", x.replace(" ", ""))
    return float(m.group(1)) if m else None


def uji() -> None:
    lst = pd.concat([pd.read_csv(f) for f in DIR.glob("list_*.csv")]).drop_duplicates("id").set_index("id")
    rows = {}
    for f in (DIR / "detail").glob("*.json"):
        j = json.loads(f.read_text())
        if len(j.get("months", {})) >= 18:
            rows[int(f.stem)] = j
    R = pd.DataFrame({i: pd.Series(j["months"]) for i, j in rows.items()}).sort_index()
    R.index = pd.PeriodIndex(R.index, freq="M")
    meta = pd.DataFrame({i: {"load": pct(j.get("Max deposit load")), "algo": pct(j.get("Algo trading")),
                             "ddeq": pct(j.get("By Equity") or ""), "sym": (j.get("symbols") or [["", 0]])[0][0]}
                         for i, j in rows.items()}).T
    L = ["# Copy trade MQL5: apakah penyedia terbaik tetap terbaik? (research/mql5_signals.py)",
         f"Daftar: {len(lst)} sinyal aktif (MT5+MT4). Dengan riwayat bulanan ≥ 18 bulan: {R.shape[1]}. "
         "Bias penyintas: sinyal yang sudah mati/dihapus tidak ada di daftar → hasil nyata lebih buruk.", ""]
    L.append("## Profil daftar")
    for lab, q in (("semua", lst), ("akun real", lst[lst.real]), ("≥ 52 minggu", lst[lst.weeks >= 52])):
        L.append(f"   {lab}: n {len(q)} | median win {q.win.median():.0f}% | median DD {q.dd.median():.0f}% | "
                 f"median growth {q.growth.median():.0f}% | median pelanggan {q.subs.median():.0f}")
    # korelasi win% dengan DD
    L.append(f"   korelasi win% vs DD: {lst[['win', 'dd']].corr().iloc[0, 1]:.2f}; win ≥ 90%: median DD "
             f"{lst[lst.win >= 90].dd.median():.0f}% vs win < 60%: {lst[lst.win < 60].dd.median():.0f}%")
    # uji persistensi: tiap bulan M, pakai 12 bulan sebelumnya; ukur 6 bulan sesudahnya
    res = {k: [] for k in ("growth 12 bln tertinggi", "win% tertinggi", "profit/rugi-bulan terburuk", "aman", "semua")}
    win = lst.win
    for m in R.index[12:-6]:
        past = R.loc[m - 11:m]
        fut = R.loc[m + 1:m + 6]
        ok = past.notna().sum() >= 12
        ok &= fut.notna().sum() >= 1
        ids = ok[ok].index
        if len(ids) < 15:
            continue
        g = (1 + past[ids]).prod() - 1
        worst = past[ids].min()
        f = (1 + fut[ids].fillna(-1.0 if False else 0)).prod() - 1
        died = fut[ids].isna().any() & fut[ids].notna().any()
        sel = {"growth 12 bln tertinggi": g.nlargest(10).index,
               "win% tertinggi": win.reindex(ids).nlargest(10).index,
               "profit/rugi-bulan terburuk": (g / worst.abs().clip(lower=0.01)).nlargest(10).index,
               "aman": g[(worst > -0.10) & (meta.reindex(ids).load.fillna(100) < 30) & (g > 0)].nlargest(10).index,
               "semua": ids}
        for k, s in sel.items():
            if len(s):
                res[k].append({"m": str(m), "fut": f[s].mean(), "neg": (f[s] < 0).mean(), "n": len(s),
                               "past": g[s].mean(), "died": died[s].mean()})
    L += ["", "## Persistensi (pilih dengan 12 bulan lalu, ukur 6 bulan berikutnya, rata-rata 10 penyedia)",
          "| Cara memilih | Return 12 bln lalu | Return 6 bln ke depan (median periode) | Penyedia rugi 6 bln ke depan | Periode |",
          "|---|---|---|---|---|"]
    for k, v in res.items():
        x = pd.DataFrame(v)
        if x.empty:
            continue
        L.append(f"| {k} | {x.past.median() * 100:+.0f}% | {x.fut.median() * 100:+.1f}% | {x.neg.mean() * 100:.0f}% | {len(x)} |")
    # simbol & EA
    L += ["", "## Tanda grid/martingale di penyedia win% ≥ 90% dengan detail"]
    hi = [i for i in R.columns if (win.get(i) or 0) >= 90]
    if hi:
        sub = R[hi]
        L.append(f"   n {len(hi)} | bulan rugi > −20% pernah terjadi pada {(sub.min() < -0.2).mean() * 100:.0f}% | "
                 f"median max deposit load {meta.reindex(hi).load.median()}")
    out = DIR / "uji.txt"
    (Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_mql5.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    {"unduh": unduh, "detail": detail, "uji": uji}[sys.argv[1]]()
