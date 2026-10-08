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


# ------------------------------------------------------------------ platform lain (permintaan 8 Okt: "cari seluruh broker")
# Riwayat posisi TUTUP per trader dari API publik yang sama dengan cloud/api/_copyposisi.py. Kandidat dipilih TANPA
# melihat kinerja: semua lead trader OKX & Bitget yang tercatat, Binance & eToro = sampel acak + paling banyak disalin.
# Biaya salin (masuk+keluar+jeda): futures 0,15%; eToro kripto 1% (spread), aset lain 0,2%.
TRADES = CM.DIR / "trades"


def _get(url: str, body: dict | None = None, tries: int = 4):
    sys.path.insert(0, str(ROOT / "cloud" / "api"))
    import _copyposisi as C
    for i in range(tries):
        try:
            return C._req(url, body, timeout=20)
        except Exception as exc:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(10 * (i + 1) if "429" in str(exc) else 3)


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def riwayat_okx(code: str, maks: int = 10) -> list[dict]:
    out, after = [], None
    for _ in range(maks):
        u = ("https://www.okx.com/api/v5/copytrading/public-subpositions-history?instType=SWAP"
             f"&uniqueCode={code}&limit=100" + (f"&after={after}" if after else ""))
        d = (_get(u) or {}).get("data") or []
        for h in d:
            side = h.get("posSide")
            buy = side == "long" if side in ("long", "short") else (_f(h.get("subPos")) or 0) > 0
            out.append({"sym": (h.get("instId") or "").replace("-SWAP", ""), "dir": 1 if buy else -1,
                        "t0": int(h.get("openTime") or 0), "t1": int(h.get("closeTime") or 0),
                        "p_in": _f(h.get("openAvgPx")), "p_out": _f(h.get("closeAvgPx")), "lev": _f(h.get("lever"))})
        if len(d) < 100:
            break
        after = d[-1].get("subPosId")
        time.sleep(0.4)
    return out


def riwayat_bitget(uid: str, maks: int = 10) -> list[dict]:
    out = []
    for page in range(1, maks + 1):
        body = {"languageType": 0, "traderUid": uid, "triggerUserId": uid, "pageNo": page, "pageSize": 50}
        d = (_get("https://www.bitget.com/v1/trigger/trace/order/newHistoryList", body) or {}).get("data") or {}
        for h in d.get("rows") or []:
            out.append({"sym": h.get("symbolDisplayName"), "dir": 1 if h.get("position") == 1 else -1,
                        "t0": int(h.get("openTime") or 0), "t1": int(h.get("closeTime") or 0),
                        "p_in": _f(h.get("openAvgPrice")), "p_out": _f(h.get("closeAvgPrice")),
                        "lev": _f(h.get("openLevel"))})
        if not d.get("nextFlag"):
            break
        time.sleep(0.4)
    return out


def riwayat_binance(pid: str, maks: int = 10) -> list[dict]:
    out = []
    for page in range(1, maks + 1):
        body = {"pageNumber": page, "pageSize": 100, "portfolioId": str(pid)}
        d = (_get("https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/lead-portfolio/position-history",
                  body) or {}).get("data") or {}
        rows = d.get("list") or []
        for h in rows:
            out.append({"sym": h.get("symbol"), "dir": 1 if h.get("side") == "Long" else -1,
                        "t0": int(h.get("opened") or 0), "t1": int(h.get("closed") or 0),
                        "p_in": _f(h.get("avgCost")), "p_out": _f(h.get("avgClosePrice")), "lev": _f(h.get("leverage"))})
        if len(rows) < 100 or page * 100 >= int(d.get("total") or 0):
            break
        time.sleep(0.4)
    return out


def riwayat_etoro(cid: str, hari: int = 400, maks: int = 10) -> list[dict]:
    start = pd.Timestamp.now("UTC") - pd.Timedelta(days=hari)
    out = []
    for page in range(1, maks + 1):
        u = ("https://www.etoro.com/sapi/trade-data-real/history/public/credit/flat?"
             f"CID={cid}&ItemsPerPage=100&PageNumber={page}&StartTime={start:%Y-%m-%dT00:00:00.000Z}")
        rows = (_get(u) or {}).get("PublicHistoryPositions") or []
        for h in rows:
            out.append({"sym": str(h.get("InstrumentID")), "dir": 1 if h.get("IsBuy") else -1,
                        "t0": int(pd.Timestamp(h["OpenDateTime"]).timestamp() * 1000),
                        "t1": int(pd.Timestamp(h["CloseDateTime"]).timestamp() * 1000),
                        "p_in": _f(h.get("OpenRate")), "p_out": _f(h.get("CloseRate")), "lev": _f(h.get("Leverage")),
                        "kripto": int(h.get("InstrumentID") or 0) >= 100000, "induk": h.get("ParentCID") or 0})
        if len(rows) < 100:
            break
        time.sleep(0.4)
    return out


def kandidat_platform(nama: str, n_acak: int = 500, n_atas: int = 200) -> list[str]:
    rng = np.random.default_rng(11)
    if nama == "okx":
        return [x["uniqueCode"] for x in CM.load("okx")["list"] if x.get("uniqueCode")]
    if nama == "bitget":
        return [x["uid"] for x in CM.load("bitget")["list"] if x.get("uid")]
    if nama == "binance":
        rows = json.loads((CM.DIR.parent / "binance_copy" / "list_365D.json").read_text())
        ids = [str(r["leadPortfolioId"]) for r in rows]
        atas = [str(r["leadPortfolioId"]) for r in sorted(rows, key=lambda r: -float(r.get("currentCopyCount") or 0))[:n_atas]]
        return list(dict.fromkeys(atas + list(rng.choice(ids, size=min(n_acak, len(ids)), replace=False))))
    if nama == "etoro":
        e = pd.read_csv(CM.DIR.parent / "etoro" / "rankings_1y.csv")
        e = e[e.Trades >= 20]
        atas = e.sort_values("Copiers", ascending=False).CustomerId.astype(str).head(n_atas).tolist()
        acak = rng.choice(e.CustomerId.astype(str).to_numpy(), size=min(n_acak, len(e)), replace=False).tolist()
        return list(dict.fromkeys(atas + acak))
    raise ValueError(nama)


AMBIL = {"okx": riwayat_okx, "bitget": riwayat_bitget, "binance": riwayat_binance, "etoro": riwayat_etoro}


def unduh_platform(nama: str, jeda: float = 0.6, ulang_hari: float = 7) -> None:
    d = TRADES / nama
    d.mkdir(parents=True, exist_ok=True)
    ids = kandidat_platform(nama)
    print(f"{nama}: {len(ids)} kandidat", flush=True)
    baru = 0
    for i, x in enumerate(ids):
        p = d / f"{x}.json.gz"
        if p.exists():
            try:
                if json.loads(gzip.decompress(p.read_bytes()))["t"] > time.time() - ulang_hari * 86400:
                    continue
            except Exception:  # noqa: BLE001
                pass
        try:
            rows = AMBIL[nama](x)
        except Exception as exc:  # noqa: BLE001
            print(nama, "gagal", x, str(exc)[:120], flush=True)
            time.sleep(20)
            continue
        p.write_bytes(gzip.compress(json.dumps({"t": time.time(), "trades": rows}, separators=(",", ":")).encode()))
        baru += 1
        if baru % 25 == 0:
            print(f"{nama} {i + 1}/{len(ids)}", flush=True)
        time.sleep(jeda)
    print(nama, "selesai", flush=True)


def episode_platform(nama: str) -> pd.DataFrame:
    rows = []
    for p in sorted((TRADES / nama).glob("*.json.gz")):
        a = p.name.split(".")[0]
        for t in json.loads(gzip.decompress(p.read_bytes()))["trades"]:
            if not (t.get("p_in") and t.get("p_out") and t.get("t0") and t.get("t1")) or t["t1"] < t["t0"]:
                continue
            if t.get("induk"):                         # eToro: posisi hasil menyalin orang lain → bukan keputusan sendiri
                continue
            biaya = (0.01 if t.get("kripto") else 0.002) if nama == "etoro" else BIAYA
            rows.append({"akun": f"{nama}:{a}", "platform": nama, "coin": t.get("sym"), "dir": t["dir"],
                         "t0": t["t0"], "t1": t["t1"], "salin": t["dir"] * (t["p_out"] / t["p_in"] - 1) - biaya,
                         "acak": True})
    return pd.DataFrame(rows)


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


def semua_episode(platform: tuple = ("hyperliquid", "okx", "bitget", "binance", "etoro")) -> pd.DataFrame:
    frames = []
    if "hyperliquid" in platform:
        frames.append(_episode_hl())
    for nama in platform:
        if nama != "hyperliquid" and (TRADES / nama).exists():
            frames.append(episode_platform(nama))
    df = pd.concat([f for f in frames if len(f)], ignore_index=True) if any(len(f) for f in frames) else pd.DataFrame()
    if df.empty:
        return df
    df["t0"] = pd.to_datetime(df.t0, unit="ms", utc=True)
    df["t1"] = pd.to_datetime(df.t1, unit="ms", utc=True)
    df["jam"] = (df.t1 - df.t0).dt.total_seconds() / 3600
    return df


def _episode_hl() -> pd.DataFrame:
    rows = []
    pool = CM.load("hl_pool")
    acak = {a.lower() for a in pool["acak"]}
    for p in sorted(FILLS.glob("*.json.gz")):
        d = json.loads(gzip.decompress(p.read_bytes()))
        a = p.name.split(".")[0]
        if d.get("bot"):
            continue
        for e in episodes(d["fills"]):
            e["akun"] = f"hyperliquid:{a}"
            e["platform"] = "hyperliquid"
            e["acak"] = a in acak
            rows.append(e)
    return pd.DataFrame(rows)


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


def uji_kumpulan(sub: pd.DataFrame, aturan: dict, hari_hist: int, langkah: int, akhir, rng) -> dict:
    """Uji maju bergulir: tiap 'langkah' hari pilih trader dari episode TUTUP dalam 'hari_hist' hari sebelumnya, ukur
    episode yang mereka BUKA dalam 'langkah' hari berikutnya. Jendela uji harus selesai ≥ 14 hari sebelum data berakhir
    (posisi rugi yang masih ditahan tidak membuat hasil terlalu bagus)."""
    sel, base, rnd, per, draws = [], [], [], [], []
    mulai = sub.t1.min().normalize() + pd.Timedelta(days=hari_hist)
    batas = akhir - pd.Timedelta(days=14)
    m = mulai
    while m + pd.Timedelta(days=langkah) <= batas:
        m1 = m + pd.Timedelta(days=langkah)
        hist = sub[(sub.t1 < m) & (sub.t1 >= m - pd.Timedelta(days=hari_hist))]
        nxt = sub[(sub.t0 >= m) & (sub.t0 < m1) & (sub.t1 <= akhir)]
        m = m1
        if nxt.empty or hist.empty:
            continue
        ids = pilih_trader(hist, aturan)
        aktif = list(set(hist.akun) & set(nxt.akun))
        s_ = nxt[nxt.akun.isin(ids)]
        r_ids = rng.choice(aktif, size=min(len(set(ids) & set(aktif)), len(aktif)), replace=False) if aktif else []
        sel.append(s_.salin)
        base.append(nxt[nxt.akun.isin(aktif)].salin)
        rnd.append(nxt[nxt.akun.isin(r_ids)].salin)
        k = len(set(ids) & set(aktif))
        if k:                                          # 200 undian trader acak (jumlah sama) → p-acak
            g = nxt[nxt.akun.isin(aktif)].groupby("akun").salin
            sums, cnts = g.sum(), g.size()
            idx = np.array([rng.choice(len(sums), size=k, replace=False) for _ in range(200)])
            draws.append((sums.to_numpy()[idx].sum(1), cnts.to_numpy()[idx].sum(1)))
        if len(s_):
            per.append((m1 - pd.Timedelta(days=langkah), len(set(s_.akun)), len(s_), s_.salin.mean()))
    cat = lambda xs: pd.concat(xs) if xs else pd.Series(dtype=float)  # noqa: E731
    p_acak = None
    if draws:
        tot = sum(d[0] for d in draws)
        cnt = sum(d[1] for d in draws)
        acak_mean = tot / np.maximum(cnt, 1)
        p_acak = float((acak_mean >= cat(sel).mean()).mean()) if len(cat(sel)) else None
    return {"terpilih": cat(sel), "acak": cat(rnd), "semua": cat(base), "per": per, "p_acak": p_acak}


def uji(hari_hist: int = 90, langkah: int = 14) -> list[str]:
    df = semua_episode()
    L = ["# 🧪 Sinyal trader — uji maju bergulir semua platform (research/sinyal_trader.py)", "",
         f"Pilih trader dari posisi TUTUP {hari_hist} hari terakhir, ukur posisi yang mereka BUKA {langkah} hari "
         "berikutnya (tanpa melihat masa depan). Return salin = arah × (harga tutup / harga buka − 1) − biaya "
         "(futures 0,14–0,15%, eToro kripto 1%, eToro lain 0,2%); TANPA leverage (leverage memperbesar untung & rugi).",
         "Bisa disalin = tahan ≥ 1 jam. Pembanding: 'acak' = trader acak aktif sejumlah sama, 'semua' = semua trader aktif.",
         ""]
    df = df[df.jam >= 1].copy()
    akhir = df.t1.max()
    for plat, g in df.groupby("platform"):
        L.append(f"- {plat}: {len(g)} posisi dari {g.akun.nunique()} trader, {g.t0.min():%Y-%m-%d} s.d. {g.t1.max():%Y-%m-%d}")
    L.append("")
    rng = np.random.default_rng(0)
    kump = [(p, df[df.platform == p]) for p in sorted(df.platform.unique())]
    kump.append(("gabungan futures (tanpa eToro)", df[df.platform != "etoro"]))
    ringkasan = {}
    for nama, aturan in ATURAN.items():
        L.append(f"## Aturan {nama}")
        for k, sub in kump:
            if sub.empty:
                continue
            r = uji_kumpulan(sub, aturan, hari_hist, langkah, akhir, rng)
            per = r["per"]
            pos = sum(1 for x in per if x[3] > 0)
            L.append(f"  {k}")
            p_ = "" if r["p_acak"] is None else f" | p-acak {r['p_acak']:.3f}"
            L.append(f"    terpilih : {ringkas(r['terpilih'])} | periode untung {pos}/{len(per)}{p_}")
            L.append(f"    acak     : {ringkas(r['acak'])}")
            L.append(f"    semua    : {ringkas(r['semua'])}")
            ringkasan[(nama, k)] = r
        L.append("")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return L


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "uji"
    if cmd == "unduh" and len(sys.argv) > 2:
        unduh_platform(sys.argv[2])
    else:
        {"unduh": unduh, "uji": uji}[cmd]()
