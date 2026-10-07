"""👁 Trader Hyperliquid dengan posisi SELALU terlihat (leaderboard 47 ribu akun) — python -m research.hl_trader unduh|uji

Permintaan pengguna 7 Okt 2026: "cari di seluruh market/broker dunia trader WR & profit tinggi, terutama yang terlihat open
posisinya" (untuk fitur follow). Di Hyperliquid (bursa perp on-chain) SEMUA posisi, TP/SL, dan riwayat transaksi setiap
akun publik — tidak bisa disembunyikan seperti di Binance/OKX/Bitget — jadi cocok untuk follow (cloud/api/_ikuti.py).

Kumpulan kandidat dipilih TANPA melihat kinerja (supaya uji maju jujur): akun ≥ $20 rb, bukan market maker (volume
bulanan ≤ 150× modal), 1.000 akun terbesar. Kurva = time-weighted dari riwayat nilai akun & PnL (portfolio "allTime").
Uji maju: pilih dengan data s.d. 90 hari lalu, ukur 90 hari terakhir (CM.split_test), banding BTC beli-tahan.
WR = % transaksi tutup yang untung dari 2.000 fill terakhir (userFills, digabung per koin+waktu).
Bias penyintas: akun yang menarik dana/meledak bisa hilang dari leaderboard → hasil uji cenderung terlalu bagus.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from research import copy_multi as CM

ROOT = Path(__file__).resolve().parent.parent
DIR = CM.DIR
HL = "https://api.hyperliquid.xyz/info"
LB = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"


def q(body: dict, tries: int = 6):
    for i in range(tries):
        try:
            r = urllib.request.Request(HL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=30) as f:
                return json.load(f)
        except Exception as exc:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1) if "429" in str(exc) else 2)


def _wp(row: dict) -> dict:
    return {k: {kk: float(vv) for kk, vv in v.items()} for k, v in row.get("windowPerformances") or []}


def kandidat(rows: list[dict], n: int = 1000, min_av: float = 20_000, max_turn: float = 150) -> list[dict]:
    """Kandidat tanpa melihat untung/rugi: modal ≥ min_av, bukan market maker, n akun terbesar."""
    out = []
    for r in rows:
        av = float(r.get("accountValue") or 0)
        w = _wp(r)
        vm = (w.get("month") or {}).get("vlm", 0)
        if av >= min_av and 0 < vm <= max_turn * av and (w.get("allTime") or {}).get("vlm", 0) > 0:
            out.append(r)
    return sorted(out, key=lambda r: -float(r["accountValue"]))[:n]


def kandidat_acak(rows: list[dict], n: int = 400, min_vlm: float = 5e6, seed: int = 7) -> list[dict]:
    """Pembanding yang lebih jujur: acak dari akun dengan volume seumur hidup ≥ min_vlm, BERAPA PUN modalnya sekarang
    (akun yang sudah meledak/ditarik ikut) — 1.000 terbesar hari ini bias ke pemenang terbaru."""
    pool = []
    for r in rows:
        w, av = _wp(r), float(r.get("accountValue") or 0)
        vm = (w.get("month") or {}).get("vlm", 0)
        if (w.get("allTime") or {}).get("vlm", 0) >= min_vlm and not (vm > 1e9 and vm > 150 * max(av, 1.0)):
            pool.append(r)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(pool), size=min(n, len(pool)), replace=False)
    return [pool[i] for i in sorted(idx)]


def unduh(n: int = 1000, jeda: float = 0.35, n_acak: int = 400) -> None:
    with urllib.request.urlopen(urllib.request.Request(LB, headers={"User-Agent": "Mozilla/5.0"}), timeout=120) as f:
        rows = json.load(f)["leaderboardRows"]
    CM._save("hl_leaderboard", rows)
    besar, acak = kandidat(rows, n), kandidat_acak(rows, n_acak)
    CM._save("hl_pool", {"besar": [r["ethAddress"] for r in besar], "acak": [r["ethAddress"] for r in acak]})
    cand = besar + [r for r in acak if r["ethAddress"] not in {b["ethAddress"] for b in besar}]
    old = CM.load("hl_portfolio") if (DIR / "hl_portfolio.json.gz").exists() else {}
    port = dict(old)
    print(f"leaderboard {len(rows)} akun → kandidat {len(cand)}", flush=True)
    for i, r in enumerate(cand):
        a = r["ethAddress"]
        if a in port and port[a].get("t", 0) > time.time() - 3 * 86400:
            continue
        try:
            p = dict(q({"type": "portfolio", "user": a}))
            al = p.get("allTime") or {}
            port[a] = {"t": time.time(), "av": al.get("accountValueHistory") or [], "pnl": al.get("pnlHistory") or []}
        except Exception as exc:  # noqa: BLE001
            print("gagal", a, exc, flush=True)
        if i % 100 == 99:
            CM._save("hl_portfolio", port)
            print(i + 1, flush=True)
        time.sleep(jeda)
    CM._save("hl_portfolio", port)


def wr_fills(fills: list[dict]) -> tuple[float | None, int, int]:
    """(WR %, jumlah transaksi tutup, waktu fill terakhir ms) — fill penutupan digabung per (koin, waktu, arah)."""
    agg: dict[tuple, float] = {}
    for f in fills:
        if str(f.get("dir", "")).startswith("Close"):
            k = (f.get("coin"), f.get("time"), f.get("dir"))
            agg[k] = agg.get(k, 0.0) + float(f.get("closedPnl") or 0) - float(f.get("fee") or 0)
    n = len(agg)
    last = max((int(f.get("time") or 0) for f in fills), default=0)
    return (sum(1 for v in agg.values() if v > 0) / n * 100 if n else None), n, last


def curves() -> dict[str, pd.Series]:
    port = CM.load("hl_portfolio")
    return {a: CM.curve_hl(d) for a, d in port.items()}


def uji() -> list[str]:
    cs = curves()
    pool = CM.load("hl_pool") if (DIR / "hl_pool.json.gz").exists() else {"besar": list(cs), "acak": []}
    L = ["# 👁 Trader Hyperliquid (posisi selalu terlihat) — uji maju", "",
         "Aturan sama dengan copy_pilih: untung di kedua paruh, DD ≤ 20%, aktif. Dua kumpulan kandidat:",
         "- **besar** = 1.000 akun terbesar HARI INI (≥ $20 rb, bukan market maker) — bias ke pemenang terbaru "
         "(akun yang tumbuh besar karena untung 90 hari terakhir ikut terpilih) → angka 'semua' terlalu bagus;",
         "- **acak** = 400 akun acak dengan volume seumur hidup ≥ $5 jt berapa pun modalnya sekarang (akun meledak ikut) "
         "→ pembanding yang lebih jujur.", ""]
    for lab, ids in (("besar", pool.get("besar") or []), ("acak", pool.get("acak") or [])):
        sub = {a: cs[a] for a in ids if a in cs and len(cs[a])}
        p, mid, end = CM.split_test(sub, 180)
        if len(p):
            L += CM.table(f"Hyperliquid trader — kumpulan {lab}", p, mid, end)
    out = ROOT / "docs" / "eksternal" / "hasil_hl_trader.txt"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return L


def pilih(maks_wr: int = 120) -> list[dict]:
    """Daftar sekarang (365 hari terakhir, aturan copy_pilih) + WR dari fill + posisi terbuka → hl_trader_pilih."""
    from research import copy_pilih as CP
    rows = {r["ethAddress"]: r for r in CM.load("hl_leaderboard")}
    cs = curves()
    cand = []
    for a, c in cs.items():
        if not len(c):
            continue
        c = c[c.index >= c.index[-1] - pd.Timedelta(days=365)]
        k = CP._kurva(c)
        if not CP._lolos(k, 180):
            continue
        cand.append((k["roi"] / max(abs(k["dd"]), 0.03), a, k))
    cand.sort(reverse=True)
    out = []
    for _, a, k in cand[:maks_wr]:
        try:
            fills = q({"type": "userFills", "user": a}) or []
            st = q({"type": "clearinghouseState", "user": a}) or {}
        except Exception as exc:  # noqa: BLE001
            print("gagal", a, exc)
            continue
        wr, n, last = wr_fills(fills)
        npos = len(st.get("assetPositions") or [])
        r = rows.get(a, {})
        av = float(r.get("accountValue") or 0)
        aktif = last > (time.time() - 14 * 86400) * 1000
        name = r.get("displayName") or f"{a[:6]}…{a[-4:]}"
        if wr is None or n < 20 or not aktif:
            continue
        out.append(CP._row("Hyperliquid", a, name, f"https://app.hyperliquid.xyz/explorer/address/{a}", k, wr,
                           0, "kripto perp", modal=round(av), transaksi=n, posisi_buka=npos, terlihat=True,
                           jenis="trader"))
        time.sleep(1.0)
    CM._save("hl_trader_pilih", out)
    print(f"{len(cand)} lolos kurva → {len(out)} dengan WR & aktif ≤ 14 hari")
    for x in sorted(out, key=lambda x: -x["skor"])[:25]:
        print(f"  {x['name'][:18]:18} ROI {x['roi']:+7.1f}% DD {x['mdd']:5.1f}% WR {x['wr']:5.1f}% n {x['transaksi']:4} "
              f"modal ${x['modal']:,} posisi {x['posisi_buka']}")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "uji"
    {"unduh": unduh, "uji": uji, "pilih": pilih}[cmd]()
