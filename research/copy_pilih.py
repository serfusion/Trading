"""👥 Pilih copy trader teruji (eToro CopyTrader + Binance Copy Trading + MQL5 Signals) → cloud/api/copytrader.json

python -m research.copy_pilih [--segar]     (--segar: unduh ulang daftar; dipakai GitHub Actions mingguan)
python -m research.copy_pilih uji           (uji maju aturan ini → docs/eksternal/hasil_copy_pilih.txt; angka "uji" di JSON)
Izin pengguna 6 Okt 2026 ("pasang copy trader dengan WR dan profit tinggi yang sudah teruji"). Aturan dari uji
research/copy_trade.py, binance_copy.py, mql5_signals.py — memilih WR/ROI tertinggi saja TIDAK bertahan; yang paling
tahan: umur ≥ 12 bulan, untung di DUA paruh tahun (konsisten), drawdown kecil, WR ≥ 60–65%, pengikut nyata.
  Binance: umur ≥ 365 hari, ROI 365 hari > 0 dan positif di paruh 1 & 2 grafik, MDD ≤ 20%, WR ≥ 60%, PnL pengikut > 0,
           ≥ 30 pengikut, masih aktif (grafik berubah ≥ 30% hari dalam 30 hari terakhir). Peringkat: ROI / MDD.
           WR ≥ 95% diberi tanda ⚠️ (biasanya posisi rugi ditahan/floating, bukan keahlian).
  MQL5   : akun real, ≥ 52 minggu, DD ≤ 20%, win ≥ 65%, ≥ 100 trade, riwayat ≥ 12 bulan, tiap 6 bulan terakhir positif,
           bulan terburuk > −10%, max deposit load ≤ 30% (anti grid/martingale), ≥ 5 pelanggan, saldo ≥ $1.000, growth
           12 bulan ≤ 300% (lebih dari itu = akun kecil sangat agresif). Peringkat: growth 12 bulan / DD.
  eToro  : terverifikasi, ≥ 30 penyalin, bukan fund, ≥ 52 minggu, gain 12 bln > 0, DD (peak-to-valley) ≤ 20%,
           WR ≥ 60%, risk score ≤ 6; riwayat bulanan: 12 bulan penuh terakhir positif di kedua paruh, bulan
           terburuk > −10%, DD bulanan > −20%, growth ≤ 300%. Peringkat: growth 12 bulan / DD.
Info saja: aplikasi menampilkan nama + angka + link langganan; tidak ada order otomatis.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import binance_copy as B
from . import copy_multi as CM
from . import etoro_copy as E
from . import mql5_signals as M

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cloud" / "api" / "copytrader.json"
NOW = pd.Timestamp.now(tz="UTC")


def binance(segar: bool) -> list[dict]:
    f = B.DIR / "list_365D.json"
    if segar or not (f.exists() or f.with_suffix(".json.gz").exists()):
        B.DIR.mkdir(parents=True, exist_ok=True)
        rows, n = [], 1
        while True:
            lst = B.page(n, "365D").get("list") or []
            if not lst:
                break
            rows += lst
            n += 1
            time.sleep(0.4)
        if not rows:
            raise RuntimeError("daftar Binance kosong (diblokir/galat jaringan)")
        f.write_text(json.dumps(rows))
    rows = json.loads(f.read_text() if f.exists() else gzip.decompress(f.with_suffix(".json.gz").read_bytes()))
    out = []
    for r in rows:
        c = np.array([x["value"] for x in r.get("chartItems") or []], float)
        start = pd.Timestamp(r.get("startTime") or 0, unit="ms", tz="UTC")
        if len(c) < 360 or (NOW - start).days < 365:
            continue
        eq = np.clip(1 + c / 100, 1e-3, None)
        h1, h2 = float(eq[180] / eq[0] - 1), float(eq[-1] / eq[180] - 1)
        aktif = float((np.diff(eq)[-30:] != 0).mean())          # masih berdagang 30 hari terakhir
        ok = (r["roi"] > 0 and h1 > 0 and h2 > 0 and (r["mdd"] or 99) <= 20 and (r["winRate"] or 0) >= 60
              and (r["copierPnl"] or 0) > 0 and (r["currentCopyCount"] or 0) >= 30 and aktif >= 0.3)
        if not ok:
            continue
        out.append({"platform": "Binance", "id": r["leadPortfolioId"], "name": r["nickname"],
                    "url": f"https://www.binance.com/en/copy-trading/lead-details/{r['leadPortfolioId']}",
                    "roi": round(r["roi"], 1), "mdd": round(r["mdd"], 1), "wr": round(r["winRate"], 1),
                    "pengikut": int(r["currentCopyCount"]), "penuh": r["currentCopyCount"] >= (r.get("maxCopyCount") or 1e9),
                    "pnl_pengikut": round(r["copierPnl"]), "paruh": [round(h1 * 100, 1), round(h2 * 100, 1)],
                    "r90": round(float(eq[-1] / eq[-91] - 1) * 100, 1),
                    "wr_curiga": r["winRate"] >= 95,     # WR ≈ 100% biasanya = posisi rugi ditahan (floating)
                    "aset": "kripto futures", "skor": r["roi"] / max(r["mdd"], 3)})
    return sorted(out, key=lambda x: -x["skor"])


def mql5(segar: bool) -> list[dict]:
    if segar or not list(M.DIR.glob("list_*.csv")):
        M.unduh()                                   # galat bila daftar kosong (DataFrame tanpa kolom id)
    lst = pd.concat([pd.read_csv(f) for f in M.DIR.glob("list_*.csv")]).drop_duplicates("id")
    cand = lst[lst.real & (lst.weeks >= 52) & (lst.dd <= 20) & (lst.win >= 65) & (lst.trades >= 100) & (lst.growth > 0)
               & (lst.subs >= 5) & (lst.balance >= 1000)]
    d = M.DIR / "detail"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for _, r in cand.iterrows():
        f = d / f"{int(r.id)}.json"
        if segar or not f.exists():
            html = M.get(f"{M.BASE}/en/signals/{int(r.id)}")
            if not html:
                continue
            f.write_text(json.dumps(M.parse_detail(html)))
            time.sleep(1.0)
        j = json.loads(f.read_text())
        mo = pd.Series(j.get("months") or {}).sort_index()
        if len(mo) < 12:
            continue
        last = mo.iloc[-13:-1] if len(mo) >= 13 else mo.iloc[-12:]       # 12 bulan penuh terakhir
        h1, h2 = float((1 + last.iloc[:6]).prod() - 1), float((1 + last.iloc[6:]).prod() - 1)
        load = M.pct(j.get("Max deposit load"))
        g12 = float((1 + last).prod() - 1)
        if h1 <= 0 or h2 <= 0 or last.min() <= -0.10 or load is None or load > 30 or g12 > 3.0:
            continue
        sym = (j.get("symbols") or [["", 0]])[0][0]
        out.append({"platform": "MQL5 " + r.mt.upper(), "id": int(r.id), "name": r["name"],
                    "url": f"https://www.mql5.com/en/signals/{int(r.id)}", "roi": round(g12 * 100, 1),
                    "mdd": float(r.dd), "wr": float(r.win), "pengikut": int(r.subs or 0), "harga": float(r.price or 0),
                    "minggu": int(r.weeks), "paruh": [round(h1 * 100, 1), round(h2 * 100, 1)],
                    "bulan_terburuk": round(float(last.min()) * 100, 1), "beban": load,
                    "r90": round(float((1 + last.iloc[-3:]).prod() - 1) * 100, 1), "wr_curiga": float(r.win) >= 95,
                    "aset": re.sub(r"[._].*$", "", sym) or "-", "emas": "XAU" in sym.upper(),
                    "skor": g12 / max(float(r.dd), 3) * 100})
    return sorted(out, key=lambda x: -x["skor"])


ASET_ETORO = {1: "forex", 2: "komoditas", 4: "indeks", 5: "saham", 6: "ETF", 10: "kripto"}


def etoro(segar: bool) -> list[dict]:
    f = E.DIR / "pilih_rankings.json"
    if segar or not f.exists():
        rows = E.rankings_all("&copiersmin=30&verified=true")
        if not rows:
            raise RuntimeError("daftar eToro kosong (diblokir/galat jaringan)")
        E.DIR.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(rows))
    (E.DIR / "hist").mkdir(parents=True, exist_ok=True)
    now = NOW.tz_localize(None).to_period("M")
    out = []
    for r in json.loads(f.read_text()):
        if not (r.get("Verified") and not r.get("IsFund") and (r.get("Copiers") or 0) >= 30
                and (r.get("WeeksSinceRegistration") or 0) >= 52 and (r.get("Gain") or 0) > 0
                and (r.get("PeakToValley") or -99) >= -20 and (r.get("WinRatio") or 0) >= 60 and (r.get("RiskScore") or 10) <= 6):
            continue
        cid = int(r["CustomerId"])
        hf = E.DIR / "hist" / f"{cid}.json"
        if segar or not hf.exists():
            h = E.history(cid)
            if h is None:
                continue
            hf.write_text(json.dumps(h))
            time.sleep(0.4)
        mo = E.monthly(json.loads(hf.read_text()))
        mo = mo[mo.index < now]                                     # bulan berjalan dibuang
        if len(mo) < 13:
            continue
        last = mo.iloc[-12:]
        h1, h2 = float((1 + last.iloc[:6]).prod() - 1), float((1 + last.iloc[6:]).prod() - 1)
        eq = (1 + last).cumprod()
        dd = float((eq / eq.cummax() - 1).min())
        g12 = float((1 + last).prod() - 1)
        if h1 <= 0 or h2 <= 0 or last.min() <= -0.10 or dd <= -0.20 or g12 > 3.0:
            continue
        out.append({"platform": "eToro", "id": cid, "name": r["UserName"],
                    "url": f"https://www.etoro.com/people/{str(r['UserName']).lower()}",
                    "roi": round(g12 * 100, 1), "mdd": round(abs(float(r["PeakToValley"])), 1), "wr": round(float(r["WinRatio"]), 1),
                    "pengikut": int(r["Copiers"]),
                    "risiko": int(r["RiskScore"]), "paruh": [round(h1 * 100, 1), round(h2 * 100, 1)],
                    "bulan_terburuk": round(float(last.min()) * 100, 1),
                    "r90": round(float((1 + last.iloc[-3:]).prod() - 1) * 100, 1), "wr_curiga": float(r["WinRatio"]) >= 95,
                    "aset": ASET_ETORO.get(r.get("TopTradedAssetClassId"), "campuran"),
                    "tahun": round((r.get("WeeksSinceRegistration") or 0) / 52, 1),
                    "skor": g12 / max(abs(dd), 0.03)})
    return sorted(out, key=lambda x: -x["skor"])


def _kurva(c: pd.Series) -> dict | None:
    """Ringkas kurva ekuitas (indeks waktu): ROI, ROI 2 paruh, DD, aktif 30 hari, % periode untung."""
    c = c.dropna()
    if len(c) < 8:
        return None
    mid = c.index[0] + (c.index[-1] - c.index[0]) / 2
    a, b = c[c.index <= mid], c[c.index >= mid]
    d = np.diff(c.values)
    last30 = c.iloc[-max(4, int((c.index >= c.index[-1] - pd.Timedelta(days=30)).sum())):]   # kurva jarang: ≥ 4 titik
    return {"roi": float(c.iloc[-1] / c.iloc[0] - 1), "h1": float(a.iloc[-1] / a.iloc[0] - 1),
            "h2": float(b.iloc[-1] / b.iloc[0] - 1), "dd": _mdd(c.values),
            "aktif": float((np.diff(last30.values) != 0).mean()) if len(last30) > 2 else 0.0,
            "up": float((d > 0).sum() / max((d != 0).sum(), 1)), "hari": int((c.index[-1] - c.index[0]).days)}


def _lolos(k: dict | None, min_hari: int) -> bool:
    return bool(k and k["hari"] >= min_hari and k["roi"] > 0 and k["h1"] > 0 and k["h2"] > 0 and k["dd"] >= -0.20
                and k["aktif"] >= 0.3)


def _row(platform: str, id_, name: str, url: str, k: dict, wr: float, pengikut: int, aset: str, **extra) -> dict:
    return {"platform": platform, "id": id_, "name": name, "url": url, "roi": round(k["roi"] * 100, 1),
            "periode": "1 th" if k["hari"] >= 300 else f"{round(k['hari'] / 30)} bln", "mdd": round(abs(k["dd"]) * 100, 1),
            "wr": round(wr, 1), "pengikut": int(pengikut), "paruh": [round(k["h1"] * 100, 1), round(k["h2"] * 100, 1)],
            "wr_curiga": wr >= 95, "aset": aset, "hari": k["hari"], **extra,
            "skor": (1 + k["roi"]) ** (365 / max(k["hari"], 180)) / max(abs(k["dd"]), 0.03)}


def okx(segar: bool) -> list[dict]:
    if segar:
        rows = CM.okx_list()
        if not rows:
            raise RuntimeError("daftar OKX kosong")
        det = {r["uniqueCode"]: CM.okx_detail(r["uniqueCode"]) for r in rows
               if int(r.get("leadDays") or 0) >= 365 and int(r.get("copyTraderNum") or 0) >= 30}
        CM._save("okx_pilih", {"list": rows, "detail": det})
        data = {"list": rows, "detail": det}
    else:
        data = CM.load("okx_pilih" if (CM.DIR / "okx_pilih.json.gz").exists() else "okx")
    out = []
    for r in data["list"]:
        d = data["detail"].get(r["uniqueCode"])
        if not d or int(r.get("leadDays") or 0) < 365 or int(r.get("copyTraderNum") or 0) < 30:
            continue
        k = _kurva(CM.curve_okx(d))
        st = d.get("stats") or {}
        wr = float(st.get("winRatio") or r.get("winRatio") or 0) * 100
        if not _lolos(k, 300) or wr < 60 or float(st.get("curCopyTraderPnl") or 0) <= 0:
            continue
        out.append(_row("OKX", r["uniqueCode"], r["nickName"],
                        f"https://www.okx.com/copy-trading/account/{r['uniqueCode']}?tab=swap", k, wr,
                        int(r["copyTraderNum"]), "kripto futures", penuh=r.get("copyTraderNum") == r.get("maxCopyTraderNum")))
    return sorted(out, key=lambda x: -x["skor"])


def bitget(segar: bool) -> list[dict]:
    if segar:
        rows = CM.bitget_list()
        if not rows:
            raise RuntimeError("daftar Bitget kosong")
        det = {r["uid"]: CM.bitget_detail(r["uid"]) for r in rows
               if int(r.get("days") or 0) >= 180 and int(r.get("follow") or 0) >= 30}
        CM._save("bitget_pilih", {"list": rows, "detail": det})
        data = {"list": rows, "detail": det}
    else:
        data = CM.load("bitget_pilih" if (CM.DIR / "bitget_pilih.json.gz").exists() else "bitget")
    out = []
    for r in data["list"]:
        d = data["detail"].get(r["uid"])
        if not d or int(r.get("days") or 0) < 180 or int(r.get("follow") or 0) < 30:
            continue
        k = _kurva(CM.curve_bitget(d))
        st = d.get("stats") or {}
        wr = float(st.get("winningRate") or 0)
        if not _lolos(k, 170) or wr < 60 or float(st.get("totalFollowProfit") or 0) <= 0:
            continue
        out.append(_row("Bitget", r["uid"], r["name"], f"https://www.bitget.com/copy-trading/trader/{r['uid']}/futures",
                        k, wr, int(r["follow"]), "kripto futures",
                        penuh=bool(r.get("max_follow")) and r.get("follow") == r.get("max_follow")))
    return sorted(out, key=lambda x: -x["skor"])


def hyperliquid(segar: bool) -> list[dict]:
    if segar:
        vs = CM.req(CM.HL_LIST) or []
        if not vs:
            raise RuntimeError("daftar Hyperliquid kosong")
        now = time.time() * 1000
        det = {}
        for v in vs:
            sm = v["summary"]
            if sm.get("isClosed") or float(sm.get("tvl") or 0) < 50_000 or \
                    (now - (sm.get("createTimeMillis") or now)) / 86_400_000 < 365:
                continue
            x = CM.req(CM.HL_INFO, {"type": "vaultDetails", "vaultAddress": sm["vaultAddress"]})
            time.sleep(0.3)
            if x:
                pf = dict(x.get("portfolio") or []).get("allTime") or {}
                det[sm["vaultAddress"]] = {"name": x.get("name"), "closed": x.get("isClosed"),
                                           "deposits": x.get("allowDeposits"), "followers": len(x.get("followers") or []),
                                           "av": pf.get("accountValueHistory"), "pnl": pf.get("pnlHistory"),
                                           "tvl": float(sm.get("tvl") or 0)}
        CM._save("hyperliquid_pilih", {"detail": det})
    else:
        f = "hyperliquid_pilih" if (CM.DIR / "hyperliquid_pilih.json.gz").exists() else "hyperliquid"
        det = CM.load(f)["detail"]
    out = []
    for a, d in det.items():
        if d.get("closed") or d.get("deposits") is False or (d.get("followers") or 0) < 30:
            continue
        c = CM.curve_hl(d)
        c = c[c.index >= c.index[-1] - pd.Timedelta(days=365)] if len(c) else c
        k = _kurva(c)
        if not _lolos(k, 300) or k["up"] < 0.6:
            continue
        out.append(_row("Hyperliquid", a, d.get("name") or a[:10], f"https://app.hyperliquid.xyz/vaults/{a}", k,
                        k["up"] * 100, int(d.get("followers") or 0), "vault kripto", wr_proksi=True))
    return sorted(out, key=lambda x: -x["skor"])


def _mdd(e: np.ndarray) -> float:
    return float((e / np.maximum.accumulate(e) - 1).min())


def uji() -> None:
    """Uji maju aturan pemilih: Binance pilih dengan hari 1–180 grafik ROI → ukur hari 181–365; MQL5 tiap bulan M pilih
    dengan 12 bulan → ukur 6 bulan. WR/pengikut/DD daftar hanya angka SEKARANG (tidak dipakai saat memilih, hindari
    look-ahead); max deposit load MQL5 = angka sekarang (sedikit look-ahead). Bias penyintas di kedua sumber."""
    L = ["# 👥 Uji maju aturan pemilih copy trader (research/copy_pilih.py uji)", ""]
    rows = json.loads(gzip.decompress((B.DIR / "list_365D.json.gz").read_bytes()))
    R = []
    for r in rows:
        c = np.array([x["value"] for x in r.get("chartItems") or []], float)
        if len(c) < 360:
            continue
        eq = np.clip(1 + c / 100, 1e-3, None)
        a, b = eq[:181], eq[180:]
        da = np.diff(a)
        if (da != 0).mean() < 0.3:
            continue
        t180 = pd.Timestamp(r["chartItems"][180]["dateTime"], unit="ms", tz="UTC")
        R.append({"past": a[-1] / a[0] - 1, "h1": a[90] / a[0] - 1, "h2": a[-1] / a[90] - 1, "pm": _mdd(a),
                  "act30": (da[-30:] != 0).mean(), "up": (da > 0).sum() / max((da != 0).sum(), 1),
                  "fut": b[-1] / b[0] - 1, "fm": _mdd(b)})
    p = pd.DataFrame(R)
    btc_f = ROOT / "data" / "research" / "eksternal" / "spot_1d" / "BTC.parquet"
    btc = None
    if btc_f.exists():                               # pembanding: beli-tahan BTC spot di jendela yang sama
        c = pd.read_parquet(btc_f).close
        c = c[c.index >= t180]
        btc = (c.iloc[-1] / c.iloc[0] - 1, _mdd(c.values), f"{c.index[0]:%Y-%m-%d}–{c.index[-1]:%Y-%m-%d}")
    rule = p[(p.past > 0) & (p.h1 > 0) & (p.h2 > 0) & (p.pm >= -0.20) & (p.act30 >= 0.3)]
    sc = rule.past / rule.pm.abs().clip(lower=0.03)
    L += [f"## Binance (pilih hari 1–180, ukur hari 181–365; {len(p)} portfolio aktif yang MASIH publik)",
          "| Pilihan | n | Median 185 hari | Rata-rata | Rugi | Hancur < −50% | DD median |", "|---|---|---|---|---|---|---|"]
    for lab, x in (("semua", p), ("lolos aturan", rule), ("aturan, 20 teratas ROI/DD", rule.loc[sc.nlargest(20).index]),
                   ("aturan, 6 teratas ROI/DD", rule.loc[sc.nlargest(6).index]), ("ROI tertinggi 20", p.nlargest(20, "past")),
                   ("% hari naik tertinggi 20 (proksi WR)", p.nlargest(20, "up"))):
        L.append(f"| {lab} | {len(x)} | {x.fut.median() * 100:+.1f}% | {x.fut.mean() * 100:+.1f}% | {(x.fut < 0).mean() * 100:.0f}% | "
                 f"{(x.fut < -0.5).mean() * 100:.0f}% | {x.fm.median() * 100:.0f}% |")
    if btc:
        L.append(f"| beli-tahan BTC spot ({btc[2]}) | 1 | {btc[0] * 100:+.1f}% | {btc[0] * 100:+.1f}% | - | - | {btc[1] * 100:.0f}% |")
    det = {}
    for f in (M.DIR / "detail").glob("*.json"):
        j = json.loads(f.read_text())
        if len(j.get("months", {})) >= 18:
            det[int(f.stem)] = j
    lst = pd.concat([pd.read_csv(f) for f in M.DIR.glob("list_*.csv")]).drop_duplicates("id").set_index("id")
    Rm = pd.DataFrame({i: pd.Series(j["months"]) for i, j in det.items()}).sort_index()
    Rm.index = pd.PeriodIndex(Rm.index, freq="M")
    load = pd.Series({i: M.pct(j.get("Max deposit load")) for i, j in det.items()}, dtype=float)
    real = lst.real.reindex(Rm.columns).fillna(False).astype(bool)
    res = {k: [] for k in ("semua", "lolos aturan", "aturan, 6 teratas", "growth 12 bln tertinggi 6")}
    xf = M.DIR / "xau_1month_twelvedata.json"               # pembanding: beli-tahan emas (Twelve Data bulanan)
    xau = None
    if xf.exists():
        v = pd.DataFrame(json.loads(xf.read_text()))
        xau = pd.Series(v.close.astype(float).values, index=pd.PeriodIndex(pd.to_datetime(v.datetime), freq="M")).sort_index()
    for m in Rm.index[12:-6]:
        past, fut = Rm.loc[m - 11:m], Rm.loc[m + 1:m + 6]
        ok = (past.notna().sum() >= 12) & (fut.notna().sum() >= 1)
        ids = ok[ok].index
        if len(ids) < 15:
            continue
        g = (1 + past[ids]).prod() - 1
        h1, h2 = (1 + past[ids].iloc[:6]).prod() - 1, (1 + past[ids].iloc[6:]).prod() - 1
        worst, f = past[ids].min(), (1 + fut[ids].fillna(0)).prod() - 1
        mask = (h1 > 0) & (h2 > 0) & (worst > -0.10) & (g <= 3.0) & (load.reindex(ids).fillna(100) <= 30) & real.reindex(ids)
        rule_m = ids[mask.values]
        sc_m = g[rule_m] / worst[rule_m].abs().clip(lower=0.01)
        for k, sel in (("semua", ids), ("lolos aturan", rule_m), ("aturan, 6 teratas", sc_m.nlargest(6).index),
                       ("growth 12 bln tertinggi 6", g.nlargest(6).index)):
            if len(sel):
                res[k].append({"m": str(m), "fut": f[sel].median(), "neg": (f[sel] < 0).mean(), "bad": (f[sel] < -0.3).mean(),
                               "n": len(sel)})
        if xau is not None and m in xau.index and m + 6 in xau.index:
            g6 = xau[m + 6] / xau[m] - 1
            res.setdefault("beli-tahan emas (pembanding)", []).append({"m": str(m), "fut": g6, "neg": float(g6 < 0),
                                                                     "bad": float(g6 < -0.3), "n": 1})
    x0 = pd.DataFrame(res["semua"])
    L += ["", f"## MQL5 (tiap bulan pilih dengan 12 bulan, ukur 6 bulan; {len(x0)} periode {x0.m.iloc[0]}–{x0.m.iloc[-1]}, "
          f"{Rm.shape[1]} sinyal yang MASIH aktif)",
          "| Pilihan | n rata | Median 6 bln | Rugi | < −30% |", "|---|---|---|---|---|"]
    for k, v in res.items():
        x = pd.DataFrame(v)
        L.append(f"| {k} | {x.n.mean():.0f} | {x.fut.median() * 100:+.1f}% | {x.neg.mean() * 100:.0f}% | {x.bad.mean() * 100:.0f}% |")
    L += ["", "Kesimpulan: aturan ini terutama MENGURANGI risiko (rugi & hancur), bukan menjamin profit lebih besar. "
          "Bias penyintas: penyedia yang sudah tutup/dihapus tidak ada di data → angka nyata lebih rendah."]
    out = ROOT / "docs" / "eksternal" / "hasil_copy_pilih.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def main() -> None:
    if "uji" in sys.argv:
        uji()
        return
    segar = "--segar" in sys.argv
    lama = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    hasil, galat = {}, {}
    for key, fn in (("okx", okx), ("bitget", bitget), ("hyperliquid", hyperliquid), ("etoro", etoro),
                    ("binance", binance), ("mql5", mql5)):
        try:
            hasil[key] = fn(segar)
        except Exception as exc:  # noqa: BLE001 - satu sumber gagal → pakai daftar minggu lalu, sumber lain tetap
            galat[key] = f"{type(exc).__name__}: {str(exc)[:120]}"
            hasil[key] = None
            print(f"{key} gagal ({galat[key]}) → daftar lama dipakai (invalid)", flush=True)
    if all(v is None for v in hasil.values()):
        sys.exit("semua sumber gagal — copytrader.json tidak diubah")
    for v in hasil.values():
        for x in v or []:
            x.pop("skor", None)
    obj = {"dibuat": NOW.strftime("%Y-%m-%d"),
           "aturan": "umur ≥ 12 bln • untung di 2 paruh tahun • DD ≤ 20% • WR ≥ 60–65% • pengikut nyata • tanpa grid",
           # angka dari `python -m research.copy_pilih uji` (docs/eksternal/hasil_copy_pilih.txt) & `research.etoro_copy uji`
           # (docs/eksternal/hasil_etoro.txt), 6 Okt 2026
           "uji": {"okx": "pilih dgn Okt–Apr → Apr–Okt 2026: lolos aturan median +8%, 25% rugi, DD 11% • semua +6%, 28% rugi, "
                          "DD 18% • beli-tahan BTC +17%",
                   "bitget": "pilih dgn 90 hr → 90 hr: lolos aturan +1%, 44% rugi, 0% hancur • ROI tertinggi 10: −17%, 40% "
                             "hancur • untung penyalin positif hanya 12% trader",
                   "hyperliquid": "termasuk 1.395 vault tutup; lolos aturan +1,5%/6 bln, 27% rugi • beli-tahan BTC +15%",
                   "etoro": "159 periode 2013–2026, pilih dgn 12 bln → 6 bln: 10 teratas median +4%, 39% rugi • lolos aturan "
                            "+5%, 34% rugi • semua +0%, 38% rugi • beli indeks S&P 500 +8%, 21% rugi (lebih baik)",
                   "binance": "pilih dgn 180 hr → 185 hr berikutnya: 20 teratas median +9%, 25% rugi, DD 13%, 0% hancur "
                              "• semua penyedia +6%, 38% rugi, DD 34%, 10% hancur • beli-tahan BTC +21%, DD 29% (1 periode)",
                   "mql5": "72 periode 2020–2026, pilih dgn 12 bln → 6 bln: 6 teratas median +19%, 4% rugi "
                           "• semua +12%, 19% rugi • beli-tahan emas +6% (bias penyintas besar: nyata lebih rendah)"},
           "kesimpulan": "Saringan ini terutama MENGURANGI risiko rugi & hancur, bukan menjamin profit. eToro kalah dari "
                         "beli indeks S&P 500; Binance kalah dari beli-tahan BTC tetapi DD jauh lebih kecil. Jangan pilih "
                         "karena WR; mulai modal kecil.",
           "singkat": "Saringan: untung di 2 paruh, DD ≤ 20%, WR ≥ 60%, ≥ 30 pengikut. Teruji menekan rugi & hancur, "
                      "profit tidak dijamin (sering kalah dari beli-tahan BTC/indeks). Mulai modal kecil.",
           "n": {}}
    for key, v in hasil.items():
        obj[key] = v[:6] if v is not None else lama.get(key, [])
        obj["n"][key] = len(v) if v is not None else (lama.get("n") or {}).get(key, 0)
    # 👥 gabungan semua situs: WR ≥ 60%, profit > 0, ≥ 30 pengikut (sudah disaring per situs); peringkat profit / DD
    # (profit periode apa adanya, tanpa disetahunkan → riwayat 6 bulan Bitget tidak dibesar-besarkan)
    gab = []
    for key in hasil:
        for x in obj[key]:
            if x["wr"] >= 60 and x["roi"] > 0 and x.get("pengikut", 0) >= 30:
                gab.append(dict(x, sumber=key, periode=x.get("periode", "1 th"), skor_gab=x["roi"] / max(x["mdd"], 3)))
    gab.sort(key=lambda x: -x["skor_gab"])
    per, top = {}, []
    for x in gab:                                   # maks 4 per situs supaya daftar benar-benar gabungan
        if per.get(x["sumber"], 0) < 4:
            per[x["sumber"]] = per.get(x["sumber"], 0) + 1
            top.append({k: v for k, v in x.items() if k != "skor_gab"})
    obj["gabungan"] = top[:20]
    if galat:
        obj["invalid"] = sorted(galat)              # sumber yang gagal diunduh → daftar minggu lalu (aplikasi menandai)
    OUT.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(", ".join(f"{k} lolos {v}" for k, v in obj["n"].items()))
    for x in obj["gabungan"]:
        print(f"  {x['platform']:11} {x['name'][:24]:24} ROI {x['roi']:+.0f}% ({x.get('periode', '1 th')}) DD {x['mdd']:.0f}% "
              f"WR {x['wr']:.0f}% pengikut {x['pengikut']} paruh {x['paruh']}")


if __name__ == "__main__":
    main()
