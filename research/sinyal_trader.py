"""🧪 Sinyal trader: apakah posisi baru trader Hyperliquid yang "bagus menurut riwayatnya" untung bila disalin?
python -m research.sinyal_trader unduh|uji|pilih

Permintaan pengguna 8 Okt 2026: "apabila salah satu copy trader open posisi bagus dengan kemungkinan WR dan profit
tinggi, deteksi sekaligus uji validitas otomatis dan masuk di apk sebagai 🧪 sinyal trader".

Data: Hyperliquid (bursa perp on-chain) — SEMUA fill tiap akun publik (`userFillsByTime`, maks 10.000 fill terbaru per
akun, 2.000 per halaman). Kumpulan akun dari research/hl_trader.py (hl_pool): "besar" = 1.000 akun terbesar hari ini
(bias pemenang) dan "acak" = 400 akun acak volume ≥ $5 jt berapa pun modalnya sekarang (akun meledak ikut).

Posisi (episode) per koin: dari posisi 0 → buka → kembali 0 (atau berbalik arah). Penyalin = masuk di harga fill
PERTAMA trader (+ jeda salin), keluar di rata-rata harga penutupan trader. Return salin (tanpa leverage) =
arah × (keluar / masuk − 1) − biaya taker 2 × 0,045% − jeda/slip 0,05%. Episode yang sudah terbuka sebelum data mulai
atau belum tutup diabaikan.

Uji maju bulanan (tanpa melihat masa depan): tiap awal bulan M, trader dipilih HANYA dari episode yang TUTUP dalam
180 hari sebelum M (WR, rata-rata return salin, jumlah trade, lama tahan), lalu diukur episode yang mereka BUKA dalam
bulan M. Pembanding: semua trader yang bisa disalin (lama tahan wajar) dan pilihan acak dengan jumlah sama.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from research import copy_multi as CM
from research.hl_trader import q

ROOT = Path(__file__).resolve().parent.parent
FILLS = CM.DIR / "hl_fills"
OUT = ROOT / "docs" / "eksternal" / "hasil_sinyal_trader.txt"
BIAYA = 2 * 0.00045 + 0.0005          # taker masuk + keluar + jeda salin/slip
HARI = 86400_000
KEEP = ("coin", "px", "sz", "side", "time", "startPosition", "dir", "closedPnl", "fee")


# ------------------------------------------------------------------ unduh
def _path(a: str) -> Path:
    return FILLS / f"{a.lower()}.json.gz"


def fills_akun(a: str, hari: int = 400, maks_hal: int = 5) -> dict:
    """Fill seumur 'hari' terakhir (atau s.d. 10.000 terbaru). Akun sangat aktif (2.000 fill < 3 hari) dicatat 'bot'."""
    start = int((time.time() - hari * 86400) * 1000)
    out, hal, bot = [], 0, False
    while hal < maks_hal:
        rows = q({"type": "userFillsByTime", "user": a, "startTime": start, "aggregateByTime": True}) or []
        hal += 1
        out += [{k: r.get(k) for k in KEEP} for r in rows]
        if len(rows) < 2000:
            break
        span = rows[-1]["time"] - rows[0]["time"]
        if hal == 1 and span < 3 * HARI:
            bot = True
            break
        start = rows[-1]["time"] + 1
    return {"t": time.time(), "bot": bot, "fills": out}


def unduh(jeda: float = 1.0, ulang_hari: float = 7) -> None:
    FILLS.mkdir(parents=True, exist_ok=True)
    pool = CM.load("hl_pool")
    ids = list(dict.fromkeys([a.lower() for a in pool["acak"]] + [a.lower() for a in pool["besar"]]))
    print(f"{len(ids)} akun", flush=True)
    done = 0
    for i, a in enumerate(ids):
        p = _path(a)
        if p.exists():
            try:
                if json.loads(gzip.decompress(p.read_bytes()))["t"] > time.time() - ulang_hari * 86400:
                    continue
            except Exception:  # noqa: BLE001 - file rusak: unduh ulang
                pass
        try:
            d = fills_akun(a)
        except Exception as exc:  # noqa: BLE001
            print("gagal", a, exc, flush=True)
            time.sleep(30)
            continue
        p.write_bytes(gzip.compress(json.dumps(d, separators=(",", ":")).encode()))
        done += 1
        if done % 25 == 0:
            print(f"{i + 1}/{len(ids)} ({done} baru)", flush=True)
        time.sleep(jeda)
    print("selesai", flush=True)


# ------------------------------------------------------------------ episode
def episodes(fills: list[dict]) -> list[dict]:
    """Posisi per koin dari 0 → buka → 0 (atau berbalik). Return salin & trader dalam pecahan (0,01 = 1%)."""
    out = []
    by: dict[str, list] = {}
    for f in sorted(fills, key=lambda x: (x["time"], x.get("dir") or "")):
        by.setdefault(f["coin"], []).append(f)
    for coin, fs in by.items():
        if coin.startswith("@") or "/" in coin:          # spot Hyperliquid: lewati (perp saja)
            continue
        ep = None
        for f in fs:
            sz, px = float(f["sz"]), float(f["px"])
            start = float(f["startPosition"])
            sgn = 1 if f["side"] == "B" else -1
            end = start + sgn * sz
            if ep is None:
                if abs(start) > 1e-12:                   # posisi sudah terbuka sebelum data → tunggu sampai 0
                    if abs(end) <= 1e-12 * max(1.0, abs(start)) or start * end < 0:
                        if start * end < 0:              # berbalik: sisa jadi posisi baru
                            ep = {"coin": coin, "dir": 1 if end > 0 else -1, "t0": f["time"], "p0": px,
                                  "q_in": abs(end), "v_in": abs(end) * px, "q_out": 0.0, "v_out": 0.0,
                                  "pnl": 0.0, "fee": 0.0, "n_fill": 1}
                    continue
                if abs(end) > 1e-12:
                    ep = {"coin": coin, "dir": 1 if end > 0 else -1, "t0": f["time"], "p0": px, "q_in": abs(end),
                          "v_in": abs(end) * px, "q_out": 0.0, "v_out": 0.0, "pnl": 0.0,
                          "fee": float(f.get("fee") or 0), "n_fill": 1}
                continue
            ep["n_fill"] += 1
            ep["fee"] += float(f.get("fee") or 0)
            ep["pnl"] += float(f.get("closedPnl") or 0)
            if sgn == ep["dir"]:                          # menambah posisi
                ep["q_in"] += sz
                ep["v_in"] += sz * px
                continue
            close = min(sz, abs(start))                   # mengurangi / menutup
            ep["q_out"] += close
            ep["v_out"] += close * px
            if abs(end) <= 1e-9 * max(1.0, ep["q_in"]) or start * end < 0:
                d = ep["dir"]
                p_out = ep["v_out"] / ep["q_out"]
                p_in = ep["v_in"] / ep["q_in"]
                out.append({"coin": coin, "dir": d, "t0": ep["t0"], "t1": f["time"],
                            "salin": d * (p_out / ep["p0"] - 1) - BIAYA, "trader": d * (p_out / p_in - 1),
                            "pnl": ep["pnl"] - ep["fee"], "notional": ep["v_in"], "n_fill": ep["n_fill"]})
                ep = None
                if start * end < 0:                       # sisa berbalik arah = episode baru
                    ep = {"coin": coin, "dir": 1 if end > 0 else -1, "t0": f["time"], "p0": px, "q_in": abs(end),
                          "v_in": abs(end) * px, "q_out": 0.0, "v_out": 0.0, "pnl": 0.0, "fee": 0.0, "n_fill": 1}
    return out


def semua_episode() -> pd.DataFrame:
    rows = []
    pool = CM.load("hl_pool")
    acak = {a.lower() for a in pool["acak"]}
    for p in sorted(FILLS.glob("*.json.gz")):
        d = json.loads(gzip.decompress(p.read_bytes()))
        a = p.name.split(".")[0]
        if d.get("bot"):
            continue
        for e in episodes(d["fills"]):
            e["akun"] = a
            e["acak"] = a in acak
            rows.append(e)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["t0"] = pd.to_datetime(df.t0, unit="ms", utc=True)
    df["t1"] = pd.to_datetime(df.t1, unit="ms", utc=True)
    df["jam"] = (df.t1 - df.t0).dt.total_seconds() / 3600
    return df


# ------------------------------------------------------------------ uji
def ringkas(x: pd.Series) -> str:
    if len(x) == 0:
        return "n 0"
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    return (f"n {len(x):5} | WR {(x > 0).mean() * 100:5.1f}% | rata {x.mean() * 100:+6.2f}% | median {x.median() * 100:+6.2f}%"
            f" | PF {pos / neg if neg else float('inf'):4.2f}")


def pilih_trader(hist: pd.DataFrame, aturan: dict) -> list[str]:
    g = hist.groupby("akun").salin
    st = pd.DataFrame({"n": g.size(), "wr": g.apply(lambda x: (x > 0).mean() * 100), "avg": g.mean(),
                       "pf": g.apply(lambda x: x[x > 0].sum() / max(-x[x < 0].sum(), 1e-9)),
                       "jam": hist.groupby("akun").jam.median()})
    m = (st.n >= aturan["n"]) & (st.wr >= aturan["wr"]) & (st.avg > aturan.get("avg", 0)) & \
        (st.pf >= aturan.get("pf", 0)) & (st.jam >= aturan.get("jam", 1))
    return list(st[m].index)


ATURAN = {
    "A WR≥60 n≥30 untung": {"n": 30, "wr": 60, "avg": 0.0},
    "B WR≥65 n≥30 PF≥1,5": {"n": 30, "wr": 65, "avg": 0.0, "pf": 1.5},
    "C WR≥70 n≥20 untung": {"n": 20, "wr": 70, "avg": 0.0},
    "D PF≥2 n≥30 (tanpa WR)": {"n": 30, "wr": 0, "avg": 0.0, "pf": 2.0},
    "E WR≥55 n≥50 rata ≥0,3%": {"n": 50, "wr": 55, "avg": 0.003},
}


def uji(hari_hist: int = 180) -> list[str]:
    df = semua_episode()
    L = ["# 🧪 Sinyal trader Hyperliquid — uji maju bulanan (research/sinyal_trader.py)", "",
         f"Episode tertutup: {len(df)} dari {df.akun.nunique()} akun (bukan bot), "
         f"{df.t0.min():%Y-%m-%d} s.d. {df.t1.max():%Y-%m-%d}.",
         "Return salin = arah × (keluar rata-rata trader / harga fill pertama − 1) − 0,14% biaya & jeda; tanpa leverage.",
         "Bisa disalin = tahan ≥ 1 jam (posisi lebih singkat mustahil disalin manual / notifikasi 15 detik).", ""]
    df = df[df.jam >= 1].copy()
    akhir = df.t1.max()
    bulan = pd.date_range(df.t0.min().normalize() + pd.Timedelta(days=hari_hist), akhir, freq="MS", tz="UTC")
    rng = np.random.default_rng(0)
    for nama, aturan in ATURAN.items():
        for kump, sub in (("semua", df), ("acak", df[df.acak])):
            sel, base, rnd, per_bulan = [], [], [], []
            for m in bulan:
                m1 = m + pd.offsets.MonthBegin(1)
                hist = sub[(sub.t1 < m) & (sub.t1 >= m - pd.Timedelta(days=hari_hist))]
                nxt = sub[(sub.t0 >= m) & (sub.t0 < m1) & (sub.t1 <= akhir)]
                if nxt.empty:
                    continue
                ids = pilih_trader(hist, aturan)
                s = nxt[nxt.akun.isin(ids)]
                aktif = list(set(hist.akun) & set(nxt.akun))
                r_ids = rng.choice(aktif, size=min(len(ids), len(aktif)), replace=False) if ids and aktif else []
                sel.append(s.salin)
                base.append(nxt[nxt.akun.isin(aktif)].salin)
                rnd.append(nxt[nxt.akun.isin(r_ids)].salin)
                if len(s):
                    per_bulan.append((m, len(ids), len(s), s.salin.mean()))
            s_all = pd.concat(sel) if sel else pd.Series(dtype=float)
            L.append(f"## {nama} — kumpulan {kump}")
            L.append(f"  terpilih : {ringkas(s_all)}")
            L.append(f"  acak     : {ringkas(pd.concat(rnd) if rnd else pd.Series(dtype=float))}")
            L.append(f"  semua    : {ringkas(pd.concat(base) if base else pd.Series(dtype=float))}")
            if per_bulan:
                pos = sum(1 for x in per_bulan if x[3] > 0)
                L.append(f"  bulan untung {pos}/{len(per_bulan)}: " + " ".join(
                    f"{m:%y-%m}:{n_t}t/{n_e}e/{avg * 100:+.2f}%" for m, n_t, n_e, avg in per_bulan))
            L.append("")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return L


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "uji"
    {"unduh": unduh, "uji": uji}[cmd]()
