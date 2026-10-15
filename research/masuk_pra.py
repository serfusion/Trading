"""⏱️ Gaya pengguna: MASUK 1 detik SEBELUM rilis, tahan 1 detik s/d 3 menit (15 Okt 2026).

python -m research.masuk_pra            → cloud/api/masuk_pra.json + docs/eksternal/hasil_masuk_pra.txt

Pengguna 15 Okt: "style trading saya entry 1 detik sebelum release news dan bertahan 1 detik hingga 1–3 menit ke depan, karena
entry pada detik ke 2 pasti delay dan pasti tertinggal jauh". Tick asli Exness XAUUSDc (bid/ask = spread asli saat berita), semua
rilis bertick 2016–2026 (daftar research/live_kurva). Masuk BUY di ask / SELL di bid kutipan terakhir ≤ t0−1 dtk; tutup BUY di bid /
SELL di ask pada detik h (kutipan terakhir ≤ h). Arah = tebakan aplikasi SEBELUM rilis (research/live_kurva.tebakan: CPI IDX|K,
PPI minyak WTI, lainnya petunjuk KEJ). Pembanding: selalu BUY (rilis yang sama) dan arah acak (rata-rata BUY & SELL = −spread).
Bagian B: setelah masuk t−1, keputusan di detik 1/2 menurut gerak LIVE (harga tengah vs t0−1): searah ≥ $X → tahan s/d H,
berlawanan ≥ $X → tutup (eksekusi detik d + reaksi L), sisanya tahan/tutup; bagian C: TP/SL. Aturan B/C dipilih di LAMA
(< Okt 2021), diuji di BARU. Hasil dalam $/ons = USD per 0,01 lot standar (= USC per 0,01 lot akun Cent).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
CACHE = EKS / "masuk_pra_kutipan.parquet"
OUT_JSON = ROOT / "cloud" / "api" / "masuk_pra.json"          # ringkas untuk cloud (_masuk_pra.py)
OUT_FULL = ROOT / "docs" / "eksternal" / "hasil_masuk_pra.json"   # lengkap (semua tabel)
OUT_TXT = ROOT / "docs" / "eksternal" / "hasil_masuk_pra.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
GRID = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5] + list(range(6, 181))
TAHAN = (1, 2, 3, 5, 10, 20, 30, 60, 90, 120, 180)
# satu baris per jam rilis untuk SEMUA (jam yang sama = satu posisi): judul utama mengikuti urutan aplikasi (_persiapan.UTAMA_RILIS)
PRIORITAS = ("NFP", "CPI", "PPI", "FOMC", "PCE", "RETAIL", "GDP", "ISM", "JOLTS", "ADP", "KONSUMEN", "PMI", "DURABLE",
             "MANUFAKTUR", "RUMAH", "ECI", "NERACA", "MINYAK", "CLAIMS")
UTAMA = ("CPI", "PPI", "NFP", "FOMC", "PCE", "RETAIL", "GDP", "ISM", "JOLTS", "ADP", "KONSUMEN", "CLAIMS")


def k(g: float) -> str:
    return str(int(round(g * 10)))


def kutipan() -> pd.DataFrame:
    """Satu baris per (rilis, grup): bid/ask masuk (≤ t0−1 dtk) + bid/ask setiap titik GRID (detik setelah rilis)."""
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from .live_kurva import gerak
    from .news_detik import prepare
    daftar = gerak()[["t0", "grup"]].copy()
    daftar["t0"] = pd.to_datetime(daftar.t0, utc=True)
    rows, siap = [], {}
    for r in daftar.itertuples():
        if r.t0 not in siap:
            try:
                siap[r.t0] = prepare(r.t0, "XAU_EXNESS")
            except Exception:  # noqa: BLE001
                siap[r.t0] = None
        p = siap[r.t0]
        if p is None:
            continue
        i0 = p.at(-1.0)
        if i0 < 0 or p.T[i0] < -60:
            continue
        o = {"t0": r.t0, "grup": r.grup, "t_in": float(p.T[i0]), "bid_in": float(p.bid[i0]), "ask_in": float(p.ask[i0])}
        i2 = p.at(-2.0)
        o["mid_m2"] = float(p.mid[i2]) if i2 >= 0 else np.nan
        for g in GRID:
            j = p.at(g)
            o["b" + k(g)], o["a" + k(g)] = float(p.bid[j]), float(p.ask[j])
        rows.append(o)
    df = pd.DataFrame(rows)
    df.to_parquet(CACHE)
    return df


def pnl(df: pd.DataFrame, arah: np.ndarray, g: float) -> np.ndarray:
    """P&L $/ons posisi arah (+1 BUY / −1 SELL) yang dibuka t0−1 dan ditutup pada detik g."""
    b, a = df["b" + k(g)].to_numpy(), df["a" + k(g)].to_numpy()
    return np.where(arah > 0, b - df.ask_in.to_numpy(), df.bid_in.to_numpy() - a)


def mid(df: pd.DataFrame, g: float) -> np.ndarray:
    return (df["b" + k(g)].to_numpy() + df["a" + k(g)].to_numpy()) / 2


def ringkas(v: np.ndarray) -> dict | None:
    v = v[~np.isnan(v)]
    if len(v) < 5:
        return None
    t = float(v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))) if len(v) > 2 and v.std(ddof=1) > 0 else 0.0
    return {"n": int(len(v)), "wr": round(float((v > 0).mean() * 100)), "rata": round(float(v.mean()), 2),
            "med": round(float(np.median(v)), 2), "t": round(t, 1)}


def semua_satu(df: pd.DataFrame) -> pd.DataFrame:
    """Satu baris per jam rilis (grup utama mengikuti PRIORITAS; yang bertebakan didahulukan)."""
    x = df.copy()
    x["_p"] = x.grup.map({g: i for i, g in enumerate(PRIORITAS)}).fillna(99) + np.where(x.tebak != 0, 0, 100)
    return x.sort_values(["t0", "_p"]).drop_duplicates("t0").drop(columns="_p")


def bagian_a(x: pd.DataFrame, nama: str, L: list) -> dict:
    """Tahan tetap: tebakan (per arah) vs selalu BUY vs acak, per periode."""
    out = {}
    q = x[x.tebak != 0]
    for per, m in (("semua", np.ones(len(q), bool)), ("lama", (q.t0 < SPLIT).to_numpy()), ("baru", (q.t0 >= SPLIT).to_numpy())):
        qq = q[m]
        if len(qq) < 5:
            continue
        d = np.sign(qq.tebak.to_numpy())
        for h in TAHAN:
            r = ringkas(pnl(qq, d, h))
            buy = ringkas(pnl(qq, np.ones(len(qq)), h))
            acak = ringkas((pnl(qq, np.ones(len(qq)), h) + pnl(qq, -np.ones(len(qq)), h)) / 2)
            if r:
                out.setdefault(per, {})[str(h)] = {"tebak": r, "buy": buy, "acak_rata": acak["rata"] if acak else None}
        for nm, s in (("naik", 1), ("turun", -1)):
            qs = qq[np.sign(qq.tebak) == s]
            if len(qs) < 5:
                continue
            for h in TAHAN:
                r = ringkas(pnl(qs, np.full(len(qs), s), h))
                if r:
                    out.setdefault(per + "_" + nm, {})[str(h)] = r
    if out.get("semua"):
        L.append(f"\n## {nama}: masuk t−1 searah tebakan, tahan tetap (n {out['semua']['60']['tebak']['n'] if '60' in out['semua'] else '?'})")
        L.append("   tahan | tebakan untung% rata $ (t) | selalu BUY untung% rata $ | acak rata $ | LAMA tebakan | BARU tebakan "
                 "| tebakan NAIK | tebakan TURUN")
        for h in TAHAN:
            a = out["semua"].get(str(h))
            if not a:
                continue
            f = lambda r: "–" if not r else f"{r['wr']}% {r['rata']:+.2f} (n {r['n']})"  # noqa: E731
            L.append(f"   {h:>4}s | {a['tebak']['wr']}% {a['tebak']['rata']:+.2f} (t {a['tebak']['t']}) | {a['buy']['wr']}% "
                     f"{a['buy']['rata']:+.2f} | {a['acak_rata']:+.2f} | {f((out.get('lama') or {}).get(str(h), {}).get('tebak'))} | "
                     f"{f((out.get('baru') or {}).get(str(h), {}).get('tebak'))} | {f((out.get('semua_naik') or {}).get(str(h)))} | "
                     f"{f((out.get('semua_turun') or {}).get(str(h)))}")
    return out


def dinamis(q: pd.DataFrame, d: float, lat: float, amb: float, H: int, tengah: str) -> np.ndarray:
    """Masuk t−1 searah tebakan; di detik d lihat gerak LIVE (harga tengah vs t0−1): searah ≥ amb → tahan s/d H; berlawanan ≥ amb →
    tutup di detik d+lat; sisanya 'tahan' (s/d H) atau 'tutup' (d+lat)."""
    D = np.sign(q.tebak.to_numpy())
    m0 = (q.bid_in.to_numpy() + q.ask_in.to_numpy()) / 2
    g = D * (mid(q, d) - m0)
    tutup_cepat = pnl(q, D, min(GRID, key=lambda z: abs(z - (d + lat))))
    tahan = pnl(q, D, H)
    if tengah == "tahan":
        return np.where(g <= -amb, tutup_cepat, tahan)
    return np.where(g >= amb, tahan, tutup_cepat)


def bracket(q: pd.DataFrame, tp: float, sl: float | None, H: int) -> np.ndarray:
    """TP (limit, terisi tepat di TP) / SL (stop, terisi di kutipan saat terdeteksi) diperiksa tiap titik GRID s/d H."""
    D = np.sign(q.tebak.to_numpy())
    gs = [g for g in GRID if g <= H]
    P = np.column_stack([pnl(q, D, g) for g in gs])
    out = P[:, -1].copy()
    selesai = np.zeros(len(q), bool)
    for j in range(P.shape[1]):
        kena_tp = ~selesai & (P[:, j] >= tp)
        out[kena_tp] = tp
        selesai |= kena_tp
        if sl is not None:
            kena_sl = ~selesai & (P[:, j] <= -sl)
            out[kena_sl] = P[kena_sl, j]
            selesai |= kena_sl
    return out


def bagian_bc(x: pd.DataFrame, nama: str, L: list) -> dict:
    q = x[x.tebak != 0]
    lama, baru = q[q.t0 < SPLIT], q[q.t0 >= SPLIT]
    if len(lama) < 10 or len(baru) < 10:
        return {}
    kand = []
    for d in (1, 2):
        for lat in (0.5, 1.0):
            for amb in (0.3, 0.5, 1.0):
                for H in (30, 60, 120, 180):
                    for tengah in ("tahan", "tutup"):
                        f = lambda z, d=d, lat=lat, amb=amb, H=H, tengah=tengah: dinamis(z, d, lat, amb, H, tengah)  # noqa: E731
                        kand.append((f"B d{d} reaksi {lat}s ≥${amb} tahan {H}s sisanya {tengah}", f))
    for tp in (1, 2, 3, 5):
        for sl in (1, 2, 3, None):
            for H in (60, 120, 180):
                f = lambda z, tp=tp, sl=sl, H=H: bracket(z, tp, sl, H)  # noqa: E731
                kand.append((f"C TP ${tp} SL {'$' + str(sl) if sl else 'tanpa'} maks {H}s", f))
    tetap = [(f"tahan tetap {h}s", (lambda z, h=h: pnl(z, np.sign(z.tebak.to_numpy()), h))) for h in TAHAN]
    hasil = []
    for nm, f in kand + tetap:
        a, b = ringkas(f(lama)), ringkas(f(baru))
        if a and b:
            hasil.append((nm, a, b))
    hasil.sort(key=lambda z: -z[1]["rata"])
    L.append(f"\n## {nama}: aturan keluar setelah masuk t−1 (dipilih LAMA n {len(lama)}, diuji BARU n {len(baru)}; {len(kand)} aturan)")
    for nm, a, b in hasil[:8]:
        L.append(f"   {nm:45s} LAMA {a['wr']}% {a['rata']:+.2f} | BARU {b['wr']}% {b['rata']:+.2f} (t {b['t']})")
    best_tetap = max((h for h in hasil if h[0].startswith("tahan tetap")), key=lambda z: z[1]["rata"])
    L.append(f"   pembanding tahan tetap terbaik LAMA: {best_tetap[0]} → BARU {best_tetap[2]['wr']}% {best_tetap[2]['rata']:+.2f}")
    top = hasil[0]
    return {"aturan": top[0], "lama": top[1], "baru": top[2], "tetap": best_tetap[0], "tetap_baru": best_tetap[2],
            "n_aturan": len(kand)}


def kelola(q: pd.DataFrame, D: np.ndarray, H: int, d: int | None = 2, amb: float = 0.5, reaksi: float = 1.0) -> np.ndarray:
    """Aturan kelola setelah masuk t−1 (dipilih SEBELUM melihat hasil, sesuai ⚡LIVE): di detik d gerak LIVE (harga tengah vs t0−1)
    BERLAWANAN posisi ≥ amb → tutup di detik d+reaksi; selain itu tahan s/d H. d None = tahan tetap H."""
    tahan = pnl(q, D, H)
    if d is None:
        return tahan
    m0 = (q.bid_in.to_numpy() + q.ask_in.to_numpy()) / 2
    g = D * (mid(q, d) - m0)
    return np.where(g <= -amb, pnl(q, D, d + reaksi), tahan)


ATURAN = (("tahan tetap", None), ("R1 tutup bila detik 2 berlawanan ≥ $0,50", 2), ("R2 tutup bila detik 1 berlawanan ≥ $0,50", 1))
H_KELOLA = (10, 30, 60, 120, 180)


def bagian_kelola(x: pd.DataFrame, nama: str, L: list) -> dict:
    """Masuk t−1 searah tebakan + aturan kelola, per arah tebakan & periode; pembanding selalu BUY & acak dengan aturan sama."""
    q = x[x.tebak != 0]
    if len(q) < 10:
        return {}
    out = {}
    L.append(f"\n## {nama}: masuk t−1 + aturan kelola (untung% rata $/ons; LAMA / BARU; NAIK / TURUN = arah tebakan)")
    for an, d in ATURAN:
        for H in H_KELOLA:
            sel = {}
            for per, m in (("semua", np.ones(len(q), bool)), ("lama", (q.t0 < SPLIT).to_numpy()),
                           ("baru", (q.t0 >= SPLIT).to_numpy())):
                qq = q[m]
                if len(qq) < 5:
                    continue
                D = np.sign(qq.tebak.to_numpy())
                one = np.ones(len(qq))
                sel[per] = {"tebak": ringkas(kelola(qq, D, H, d)), "buy": ringkas(kelola(qq, one, H, d)),
                            "acak": round(float(np.nanmean((kelola(qq, one, H, d) + kelola(qq, -one, H, d)) / 2)), 2)}
                for nm, s in (("naik", 1), ("turun", -1)):
                    qs = qq[np.sign(qq.tebak) == s]
                    if len(qs) >= 5:
                        sel[per][nm] = ringkas(kelola(qs, np.full(len(qs), s), H, d))
            out[f"{an.split()[0]}|{H}"] = sel
            f = lambda r: "–" if not r else f"{r['wr']}% {r['rata']:+.2f}"  # noqa: E731
            a = sel.get("semua", {})
            L.append(f"   {an[:40]:40s} s/d {H:>3}s | tebakan {f(a.get('tebak'))} (n {a.get('tebak', {}).get('n')}) | LAMA "
                     f"{f(sel.get('lama', {}).get('tebak'))} / BARU {f(sel.get('baru', {}).get('tebak'))} | NAIK {f(a.get('naik'))} / "
                     f"TURUN {f(a.get('turun'))} | selalu BUY LAMA {f(sel.get('lama', {}).get('buy'))} / BARU "
                     f"{f(sel.get('baru', {}).get('buy'))} | acak {a.get('acak')}")
    return out


def live_posisi(x: pd.DataFrame) -> dict:
    """⚡LIVE untuk posisi APA PUN yang dibuka t−1 (BUY atau SELL; semua rilis, tanpa syarat tebakan): gerak detik d ≥ $X SEARAH
    posisi → untung% bila tahan s/d H; BERLAWANAN → untung% & rata-rata bila tahan vs tutup di detik d+1."""
    m0 = (x.bid_in.to_numpy() + x.ask_in.to_numpy()) / 2
    lama = (x.t0 < SPLIT).to_numpy()
    out = {}
    for d in (1, 2):
        mv = mid(x, d) - m0
        for amb in (0.3, 0.5, 1.0, 2.0):
            for sisi in ("searah", "lawan"):
                m = np.abs(mv) >= amb
                if m.sum() < 10:
                    continue
                D = np.sign(mv) * (1 if sisi == "searah" else -1)
                o = {"n": int(m.sum()), "n_lama": int((m & lama).sum()), "n_baru": int((m & ~lama).sum())}
                for H in (5, 10, 30, 60, 120, 180):
                    v = pnl(x, D, H)
                    o[str(H)] = {"wr": round(float((v[m] > 0).mean() * 100)), "rata": round(float(v[m].mean()), 2),
                                 "wr_lama": round(float((v[m & lama] > 0).mean() * 100)) if (m & lama).sum() >= 5 else None,
                                 "wr_baru": round(float((v[m & ~lama] > 0).mean() * 100)) if (m & ~lama).sum() >= 5 else None}
                c = pnl(x, D, d + 1.0)
                o["tutup"] = {"wr": round(float((c[m] > 0).mean() * 100)), "rata": round(float(c[m].mean()), 2)}
                out.setdefault(str(d), {})[f"{sisi}|{amb}"] = o
        # emas hampir diam (< $0,30) di detik d: posisi BUY & SELL dirata-rata (arah belum terlihat)
        m = np.abs(mv) < 0.3
        if m.sum() >= 10:
            o = {"n": int(m.sum())}
            one = np.ones(len(x))
            for H in (5, 10, 30, 60, 120, 180):
                b, s_ = pnl(x, one, H)[m], pnl(x, -one, H)[m]
                o[str(H)] = {"wr": round(float(((b > 0).mean() + (s_ > 0).mean()) * 50)), "rata": round(float((b + s_).mean() / 2), 2)}
            b, s_ = pnl(x, one, d + 1.0)[m], pnl(x, -one, d + 1.0)[m]
            o["tutup"] = {"wr": round(float(((b > 0).mean() + (s_ > 0).mean()) * 50)), "rata": round(float((b + s_).mean() / 2), 2)}
            out.setdefault(str(d), {})["kecil"] = o
    return out


def ringkas_cloud(hasil: dict, acak: dict) -> dict:
    """Bagian yang dipakai cloud (_masuk_pra.py): t1[grup][arah] (masuk t−1 searah tebakan, tahan H) & posisi[grup] (⚡LIVE)."""
    t1 = {}
    for g, a in hasil["grup"].items():
        for arah in ("naik", "turun"):
            s = a.get(f"semua_{arah}") or {}
            if not s.get("60"):
                continue
            o = {"n": s["60"]["n"], "H": {h: [s[h]["wr"], s[h]["rata"]] for h in ("1", "2", "5", "10", "30", "60", "120", "180") if h in s}}
            for per in ("lama", "baru"):
                x = (a.get(f"{per}_{arah}") or {}).get("60")
                if x:
                    o[per] = [x["wr"], x["rata"], x["n"]]
                bq = ((a.get(per) or {}).get("60") or {}).get("buy")
                if bq:
                    o[f"buy_{per}"] = [bq["wr"], bq["rata"], bq["n"]]
            t1.setdefault(g, {})[arah] = o
    pos = {}
    for g, lv in hasil["live"].items():
        for d, isi in lv.items():
            for key, o in isi.items():
                sisi, _, amb = key.partition("|")
                ent = {"n": o["n"], **{h: [o[h]["wr"], o[h]["rata"]] for h in ("10", "30", "60", "180") if h in o},
                       "tutup": [o["tutup"]["wr"], o["tutup"]["rata"]]}
                if "n_lama" in o:
                    ent.update(n_lama=o["n_lama"], n_baru=o["n_baru"], wr60=[(o.get("60") or {}).get("wr_lama"),
                                                                           (o.get("60") or {}).get("wr_baru")])
                pos.setdefault(g, {}).setdefault(d, {})[key if sisi == "kecil" else f"{'s' if sisi == 'searah' else 'l'}|{amb}"] = ent
    return {"dibuat": hasil["dibuat"], "sumber": hasil["sumber"], "spread": hasil["spread"], "acak": acak, "t1": t1, "posisi": pos}


def main() -> None:
    from .live_kurva import tebakan
    df = kutipan()
    df["t0"] = pd.to_datetime(df.t0, utc=True)
    df["tebak"] = tebakan(df)
    sp = (df.ask_in - df.bid_in)
    L = ["# ⏱️ Masuk 1 detik SEBELUM rilis, tahan 1 detik s/d 3 menit (research/masuk_pra.py)", __doc__.split("\n\n")[1],
         f"rilis bertick Exness: {df.t0.nunique()} jam rilis, {len(df)} baris (rilis × grup); bertebakan {int((df.tebak != 0).sum())} "
         f"({df[df.tebak != 0].groupby('grup').size().to_dict()}) — berita lain tanpa tebakan (aplikasi: ≈ 50:50)",
         f"spread saat masuk (t0−1): median ${sp.median():.2f}, P90 ${sp.quantile(.9):.2f}, maks ${sp.max():.2f}"]
    one = semua_satu(df)
    for nm, x in (("semua rilis", one), ("bertebakan", one[one.tebak != 0])):
        for per, m in (("LAMA", x.t0 < SPLIT), ("BARU", x.t0 >= SPLIT)):
            q = x[m]
            L.append(f"pembanding selalu BUY t−1, {nm} {per} (n {len(q)}): " + " • ".join(
                f"{h}s {ringkas(pnl(q, np.ones(len(q)), h))['wr']}% {ringkas(pnl(q, np.ones(len(q)), h))['rata']:+.2f}"
                for h in (1, 2, 5, 10, 30, 60, 180)))
    # tanpa tebakan (≈ 50:50): masuk t−1 arah acak = rata-rata BUY & SELL (semua jam rilis)
    o1 = np.ones(len(one))
    acak = {str(h): round(float(np.nanmean((pnl(one, o1, h) + pnl(one, -o1, h)) / 2)), 2) for h in (5, 30, 60, 180)}
    L.append("tanpa tebakan, masuk t−1 arah acak (semua jam rilis): " + " • ".join(f"{h}s {v:+.2f}" for h, v in acak.items()))
    hasil = {"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "sumber": "research/masuk_pra.py",
             "spread": {"median": round(float(sp.median()), 2), "p90": round(float(sp.quantile(.9)), 2)},
             "tahan": list(TAHAN), "grup": {}, "kelola": {}, "aturan": {}, "live": {}}
    for nm, x in [("SEMUA", one)] + [(g, df[df.grup == g]) for g in UTAMA]:
        a = bagian_a(x, nm, L)
        if a:
            hasil["grup"][nm] = a
        kl = bagian_kelola(x, nm, L)
        if kl:
            hasil["kelola"][nm] = kl
        bc = bagian_bc(x, nm, L)
        if bc:
            hasil["aturan"][nm] = bc
        lv = live_posisi(x)
        if lv:
            hasil["live"][nm] = lv
    L.append("\n## ⚡LIVE posisi APA PUN dibuka t−1 (semua rilis): gerak detik d ≥ $X SEARAH / BERLAWANAN posisi → untung% & rata $ bila "
             "tahan s/d H; 'tutup' = tutup di detik d+1")
    for nm in ("SEMUA",) + UTAMA:
        for d in ("1", "2"):
            for key in ("searah|0.3", "lawan|0.3", "searah|0.5", "lawan|0.5", "searah|1.0", "lawan|1.0", "searah|2.0", "lawan|2.0"):
                o = ((hasil["live"].get(nm) or {}).get(d) or {}).get(key)
                if not o:
                    continue
                L.append(f"   {nm:8s} detik {d} {key.replace('|', ' ≥ $'):14s} (n {o['n']}; lama {o['n_lama']} / baru {o['n_baru']}): "
                         + " • ".join(f"{H}s {o[str(H)]['wr']}% {o[str(H)]['rata']:+.2f}" for H in (5, 10, 30, 60, 120, 180))
                         + f" | tutup d+1 {o['tutup']['wr']}% {o['tutup']['rata']:+.2f}")
    for nm in ("SEMUA",) + UTAMA:
        for d in ("1", "2"):
            o = ((hasil["live"].get(nm) or {}).get(d) or {}).get("kecil")
            if o:
                L.append(f"   {nm:8s} detik {d} gerak < $0,30 (n {o['n']}, BUY & SELL dirata-rata): "
                         + " • ".join(f"{H}s {o[str(H)]['wr']}% {o[str(H)]['rata']:+.2f}" for H in (5, 10, 30, 60, 120, 180))
                         + f" | tutup d+1 {o['tutup']['wr']}% {o['tutup']['rata']:+.2f}")
    OUT_FULL.write_text(json.dumps(hasil, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(ringkas_cloud(hasil, acak), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    OUT_TXT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ulang":
        CACHE.unlink(missing_ok=True)
    main()
