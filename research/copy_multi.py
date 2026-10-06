"""👥 Copy trader dari situs lain: OKX, Bitget, Hyperliquid (vault) — python -m research.copy_multi unduh <situs>|uji

Network penuh dibuka pengguna (6 Okt 2026). Semua endpoint publik tanpa kunci:
* OKX      : /api/v5/copytrading/public-lead-traders (resmi) + public-pnl lastDays=4 (ROI kumulatif harian 365 hari) +
             public-stats lastDays=4 (win rate HARIAN = hari untung / hari aktif, untung penyalin sekarang).
* Bitget   : /v1/trigger/trace/public/traderView (457 trader yang ditampilkan) + cycleData cycleTime=180 (ROI harian
             180 hari, win rate trade, untung penyalin 180 hari, MDD).
* Hyperliquid: stats-data.hyperliquid.xyz/Mainnet/vaults (SEMUA vault termasuk yang sudah tutup → bias penyintas kecil)
             + api.hyperliquid.xyz/info vaultDetails (riwayat nilai akun & PnL; return dihitung time-weighted).
Uji: kurva dibelah dua — pilih dengan paruh pertama (untung di 2 kuartal, DD ≤ 20%, aktif), ukur paruh kedua; pembanding
semua penyedia & beli-tahan BTC di jendela yang sama. Bybit diblokir (Akamai, IP AS); BingX butuh tanda tangan waktu.
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
DIR = ROOT / "data" / "research" / "eksternal" / "copy_multi"
OUT = ROOT / "docs" / "eksternal" / "hasil_copy_multi.txt"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 "
                    "Safari/537.36", "Accept": "application/json", "Content-Type": "application/json"}


def req(url: str, body: dict | None = None, tries: int = 4):
    for i in range(tries):
        try:
            data = json.dumps(body).encode() if body is not None else None
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=40) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    return None


def _save(name: str, obj) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / f"{name}.json.gz").write_bytes(gzip.compress(json.dumps(obj, separators=(",", ":")).encode()))


def load(name: str):
    return json.loads(gzip.decompress((DIR / f"{name}.json.gz").read_bytes()))


# ------------------------------------------------------------------ OKX
OKX = "https://www.okx.com/api/v5/copytrading"


def okx_list(min_lead: int = 4) -> list[dict]:
    rows, page, total = [], 1, None
    while total is None or page <= total:
        d = req(f"{OKX}/public-lead-traders?instType=SWAP&sortType=overview&minLeadDays={min_lead}&limit=20&page={page}")
        if not d or d.get("code") != "0" or not d.get("data"):
            break
        x = d["data"][0]
        total = int(x.get("totalPage") or 0)
        for r in x.get("ranks") or []:
            r.pop("traderInsts", None)
            rows.append(r)
        page += 1
        time.sleep(0.45)                        # batas 5 permintaan / 2 detik
    return rows


def okx_detail(code: str) -> dict:
    pnl = req(f"{OKX}/public-pnl?instType=SWAP&uniqueCode={code}&lastDays=4")
    time.sleep(0.45)
    st = req(f"{OKX}/public-stats?instType=SWAP&uniqueCode={code}&lastDays=4")
    time.sleep(0.45)
    return {"pnl": (pnl or {}).get("data") or [], "stats": ((st or {}).get("data") or [{}])[0]}


def unduh_okx() -> None:
    rows = okx_list()
    print("OKX lead trader ≥ 180 hari:", len(rows), flush=True)
    det = {}
    for n, r in enumerate(rows):
        det[r["uniqueCode"]] = okx_detail(r["uniqueCode"])
        if n % 200 == 0:
            print("  detail", n, flush=True)
    _save("okx", {"list": rows, "detail": det, "waktu": pd.Timestamp.now(tz="UTC").isoformat()})


# ------------------------------------------------------------------ Bitget
BG = "https://www.bitget.com/v1/trigger/trace/public"


def bitget_list() -> list[dict]:
    rows, page = {}, 1
    while True:
        d = req(f"{BG}/traderView", {"pageNo": page, "pageSize": 50, "languageType": 0})
        x = (d or {}).get("data") or {}
        for r in x.get("rows") or []:
            items = {i["showColumnCode"]: i.get("comparedValue") for i in r.get("itemVoList") or []}
            rows[r["traderUid"]] = {"uid": r["traderUid"], "name": r.get("traderNickName") or r.get("displayName"),
                                    "follow": r.get("followCount"), "max_follow": r.get("maxFollowCount"),
                                    "days": (r.get("viewDataVO") or {}).get("enterDay"), **items}
        if not x.get("nextFlag") or not x.get("rows"):
            break
        page += 1
        time.sleep(0.6)
    return list(rows.values())


def bitget_detail(uid: str) -> dict:
    d = req(f"{BG}/cycleData", {"languageType": 0, "triggerUserId": uid, "cycleTime": 180})
    x = (d or {}).get("data") or {}
    time.sleep(0.6)
    return {"roi": [(r["dataTime"], r["amount"]) for r in (x.get("roiRows") or {}).get("rows") or []],
            "follow": [(r["dataTime"], r["amount"]) for r in (x.get("followNetProfitKlineDTO") or {}).get("rows") or []],
            "stats": x.get("statisticsDTO") or {}, "score": x.get("pageScoreDTO") or {}}


def unduh_bitget() -> None:
    rows = bitget_list()
    print("Bitget trader:", len(rows), flush=True)
    det = {}
    for n, r in enumerate(rows):
        det[r["uid"]] = bitget_detail(r["uid"])
        if n % 100 == 0:
            print("  detail", n, flush=True)
    _save("bitget", {"list": rows, "detail": det, "waktu": pd.Timestamp.now(tz="UTC").isoformat()})


# ------------------------------------------------------------------ Hyperliquid
HL_LIST = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
HL_INFO = "https://api.hyperliquid.xyz/info"


def unduh_hl(min_tvl: float = 10_000, min_hari: int = 120) -> None:
    vs = req(HL_LIST) or []
    now = time.time() * 1000
    # semua vault yang pernah berumur ≥ min_hari & cukup besar (pakai PnL allTime maks sebagai proksi ukuran), termasuk tutup
    pick = []
    for v in vs:
        s = v["summary"]
        age = (now - (s.get("createTimeMillis") or now)) / 86_400_000
        allt = dict(v.get("pnls") or []).get("allTime") or ["0"]
        size = max(float(s.get("tvl") or 0), max(abs(float(p)) for p in allt) * 5)
        if age >= min_hari and size >= min_tvl:
            pick.append(s["vaultAddress"])
    print("Hyperliquid vault:", len(vs), "dipilih", len(pick), flush=True)

    def one(a: str):
        x = req(HL_INFO, {"type": "vaultDetails", "vaultAddress": a})
        time.sleep(0.3)
        if not x:
            return a, None
        p = dict(x.get("portfolio") or []).get("allTime") or {}
        return a, {"name": x.get("name"), "leader": x.get("leader"), "apr": x.get("apr"), "closed": x.get("isClosed"),
                   "deposits": x.get("allowDeposits"), "commission": x.get("leaderCommission"),
                   "followers": len(x.get("followers") or []), "av": p.get("accountValueHistory"),
                   "pnl": p.get("pnlHistory")}
    det = {}
    with ThreadPoolExecutor(3) as ex:
        for n, (a, d) in enumerate(ex.map(one, pick)):
            if d:
                det[a] = d
            if n % 200 == 0:
                print("  detail", n, flush=True)
    _save("hyperliquid", {"list": [v["summary"] for v in vs], "detail": det,
                          "waktu": pd.Timestamp.now(tz="UTC").isoformat()})


# ------------------------------------------------------------------ kurva → uji
def curve_okx(d: dict) -> pd.Series:
    p = sorted(d.get("pnl") or [], key=lambda r: int(r["beginTs"]))
    return pd.Series([1 + float(r["pnlRatio"]) for r in p], index=pd.to_datetime([int(r["beginTs"]) for r in p], unit="ms"))


def curve_bitget(d: dict) -> pd.Series:
    r = d.get("roi") or []
    return pd.Series([1 + float(a) / 100 for _, a in r], index=pd.to_datetime([t for t, _ in r], unit="ms"))


def curve_hl(d: dict) -> pd.Series:
    av = pd.Series({int(t): float(v) for t, v in d.get("av") or []}).sort_index()
    pn = pd.Series({int(t): float(v) for t, v in d.get("pnl") or []}).sort_index()
    j = pd.concat([av, pn], axis=1, keys=["av", "pnl"]).dropna()
    if len(j) < 3:
        return pd.Series(dtype=float)
    dp = j.pnl.diff().iloc[1:]
    base = j.av.shift(1).iloc[1:]
    r = (dp / base.where(base > 1)).fillna(0).clip(-0.95, 5)        # time-weighted: PnL periode / nilai awal periode
    eq = (1 + r).cumprod()
    s = pd.concat([pd.Series([1.0], index=[j.index[0]]), eq])
    s.index = pd.to_datetime(s.index, unit="ms")
    return s


def _mdd(e: np.ndarray) -> float:
    e = np.clip(np.asarray(e, float), 1e-6, None)
    return float((e / np.maximum.accumulate(e) - 1).min())


def split_test(curves: dict[str, pd.Series], min_len_days: int) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    """Belah tiap kurva harian di tanggal tengah bersama; pilih dengan paruh 1, ukur paruh 2."""
    ok = {k: c for k, c in curves.items() if len(c) >= 2 and (c.index[-1] - c.index[0]).days >= min_len_days}
    if not ok:
        return pd.DataFrame(), pd.NaT, pd.NaT
    end = max(c.index[-1] for c in ok.values())
    mid = end - pd.Timedelta(days=min_len_days // 2)
    rows = []
    for k, c in ok.items():
        a, b = c[c.index <= mid], c[c.index >= mid]
        if len(a) < 4 or len(b) < 2 or a.index[0] > mid - pd.Timedelta(days=min_len_days // 2 - 5):
            continue
        q = a.index[0] + (mid - a.index[0]) / 2
        a1, a2 = a[a.index <= q], a[a.index >= q]
        da = np.diff(a.values)
        rows.append({"id": k, "past": a.iloc[-1] / a.iloc[0] - 1, "h1": a1.iloc[-1] / a1.iloc[0] - 1,
                     "h2": a2.iloc[-1] / a2.iloc[0] - 1, "pm": _mdd(a.values), "act": float((da != 0).mean()),
                     "up": (da > 0).sum() / max((da != 0).sum(), 1), "fut": b.iloc[-1] / b.iloc[0] - 1, "fm": _mdd(b.values)})
    return pd.DataFrame(rows).set_index("id") if rows else pd.DataFrame(), mid, end


def btc_ret(t0: pd.Timestamp, t1: pd.Timestamp) -> tuple[float, float] | None:
    f = ROOT / "data" / "research" / "eksternal" / "spot_1d" / "BTC.parquet"
    if not f.exists():
        return None
    c = pd.read_parquet(f).close
    c.index = c.index.tz_localize(None)
    c = c[(c.index >= t0) & (c.index <= t1)]
    return (c.iloc[-1] / c.iloc[0] - 1, _mdd(c.values)) if len(c) > 5 else None


def table(lab: str, p: pd.DataFrame, mid, end) -> list[str]:
    p = p[p.act > 0.2]
    rule = p[(p.past > 0) & (p.h1 > 0) & (p.h2 > 0) & (p.pm >= -0.20)]
    sc = rule.past / rule.pm.abs().clip(lower=0.03)
    L = [f"## {lab}: pilih s.d. {mid:%Y-%m-%d}, ukur {mid:%Y-%m-%d}–{end:%Y-%m-%d} ({len(p)} penyedia aktif)",
         "| Pilihan | n | Median | Rata-rata | Rugi | Hancur < −50% | DD median |", "|---|---|---|---|---|---|---|"]
    for name, x in (("semua", p), ("lolos aturan", rule), ("aturan, 10 teratas ROI/DD", rule.loc[sc.nlargest(10).index]),
                    ("ROI tertinggi 10", p.nlargest(10, "past")), ("% hari untung tertinggi 10 (proksi WR)", p.nlargest(10, "up"))):
        if len(x):
            L.append(f"| {name} | {len(x)} | {x.fut.median() * 100:+.1f}% | {x.fut.mean() * 100:+.1f}% | "
                     f"{(x.fut < 0).mean() * 100:.0f}% | {(x.fut < -0.5).mean() * 100:.0f}% | {x.fm.median() * 100:.0f}% |")
    b = btc_ret(mid, end)
    if b:
        L.append(f"| beli-tahan BTC | 1 | {b[0] * 100:+.1f}% | {b[0] * 100:+.1f}% | - | - | {b[1] * 100:.0f}% |")
    return L + [""]


def uji() -> None:
    L = ["# 👥 Copy trader OKX, Bitget, Hyperliquid: apakah yang terbaik tetap terbaik? (research/copy_multi.py)", ""]
    if (DIR / "okx.json.gz").exists():
        o = load("okx")
        p, mid, end = split_test({k: curve_okx(v) for k, v in o["detail"].items()}, 360)
        if len(p):
            L += table(f"OKX ({len(o['list'])} lead trader ≥ 180 hari)", p, mid, end)
    if (DIR / "bitget.json.gz").exists():
        g = load("bitget")
        p, mid, end = split_test({k: curve_bitget(v) for k, v in g["detail"].items()}, 178)
        if len(p):
            L += table(f"Bitget ({len(g['list'])} trader yang ditampilkan, riwayat 180 hari)", p, mid, end)
        fol = pd.Series({k: float((v.get("stats") or {}).get("totalFollowProfit") or 0) for k, v in g["detail"].items()})
        L.append(f"   Bitget: untung penyalin 180 hari positif pada {(fol > 0).mean() * 100:.0f}% trader "
                 f"(total {fol.sum() / 1e6:+.2f} jt USDT)")
        L.append("")
    if (DIR / "hyperliquid.json.gz").exists():
        h = load("hyperliquid")
        curves = {k: curve_hl(v) for k, v in h["detail"].items()}
        p, mid, end = split_test(curves, 360)
        if len(p):
            ncl = sum(1 for v in h["detail"].values() if v.get("closed"))
            L += table(f"Hyperliquid vault ({len(h['detail'])} vault, {ncl} sudah tutup — ikut dihitung)", p, mid, end)
    L.append("Bias penyintas: OKX/Bitget hanya memuat trader yang masih tampil; Hyperliquid memuat vault yang sudah tutup.")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "unduh":
        {"okx": unduh_okx, "bitget": unduh_bitget, "hl": unduh_hl}[sys.argv[2]]()
    else:
        uji()
