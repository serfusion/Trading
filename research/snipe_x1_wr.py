"""🎯 Snipe X1 dengan persentase untung tinggi (target ≥ 75% snipe untung) — python -m research.snipe_x1_wr bangun|cari

Permintaan pengguna 11 Okt 2026: "lanjut hingga persentase tinggi … riset, uji validitas … hingga di atas 75%".
Persentase = % snipe yang ditutup UNTUNG (XNT bersih diterima > modal, setelah biaya DEX + bot 1%/sisi). Syarat lolos
(ditetapkan SEBELUM mencari): WR ≥ 75% DAN rata-rata untung > 0 di paruh LATIH (s/d 14 Feb 2026) DAN paruh UJI
(15 Feb – Okt 2026), n uji ≥ 30, plus uji acak (permutasi label waktu) untuk banyaknya aturan yang dicoba.

Fitur hanya memakai transaksi ≤ saat masuk (t0 + jeda): jumlah pembeli/beli/jual, XNT masuk/keluar, kenaikan harga
sejak buka, pembuat beli/jual/tarik likuiditas, pool XNT, porsi pasokan di pool, umur & riwayat pembuat (peluncuran
SEBELUMNYA saja), wallet "penembak" yang tercatat untung di peluncuran SEBELUMNYA (tanpa melihat masa depan).
Jalur nilai jual (`v`) = simulasi sisip `snipe_x1_uji.putar` mulai titik masuk s/d akhir jendela 24 jam.
"""
from __future__ import annotations

import pickle
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from research import snipe_x1 as S
from research import snipe_x1_uji as U

MODAL = 2.0
JEDA = [0, 30, 60, 120, 300, 600, 900, 1800, 3600]
F_JALUR = S.DIR / "wr_jalur.pkl"
POTONG = pd.Timestamp("2026-02-15").timestamp()  # batas LATIH / UJI


def fitur_saat(d: pd.DataFrame, idx: int, creator: str) -> dict:
    """Fitur dari kejadian 0..idx (termasuk) — semuanya sudah terjadi saat kita masuk."""
    z = d.iloc[1:idx + 1]
    b, j = z[z.jenis == "beli"], z[z.jenis == "jual"]
    bo = b[b.w != creator]
    p0 = d.y.iloc[0] / d.x.iloc[0]
    p = d.y.iloc[idx] / d.x.iloc[idx]
    return {
        "n_beli": len(b), "n_jual": len(j), "pembeli": bo.w.nunique(), "xnt_beli": float(b.dxnt.sum()),
        "xnt_jual": float(-j.dxnt.sum()), "beli_maks": float(b.dxnt.max()) if len(b) else 0.0,
        "naik": p / p0, "y_masuk": float(d.y.iloc[idx]), "dev_beli": float(b[b.w == creator].dxnt.sum()),
        "dev_jual": bool((j.w == creator).any()), "lp_tarik": bool((z.jenis == "lp-").any()),
        "lp_tambah": bool((z.jenis == "lp+").any()), "t_akhir": float(z.t.max() - d.t.iloc[0]) if len(z) else 0.0,
        "wallets": list(dict.fromkeys(bo.w)),
    }


def bangun() -> None:
    launches = U.peluncuran()
    cad = S.muat(S.DIR / "cadangan.json.gz")["saldo"]
    pasok = S.muat(S.DIR / "pasok.json.gz")
    oto = S.muat(S.DIR / "otoritas.json.gz") if (S.DIR / "otoritas.json.gz").exists() else {}
    fp = S.DIR / "penyandang.json.gz"
    dana = S.muat(fp) if fp.exists() else {}
    out = []
    for L in launches:
        d = U.kejadian(L)
        if d is None or (d.jenis == "buat").sum() == 0:
            continue
        t0 = int(d.t.iloc[0])
        x0, y0 = float(d.x.iloc[0]), float(d.y.iloc[0])
        vt, vx, dtk, dxn = S.sisi(L)
        base = {"pool": L["pool"], "mint": L["mint"], "sym": L["sym"], "creator": L["creator"], "t0": t0,
                "y0": y0, "porsi": x0 / pasok[L["mint"]] if pasok.get(L["mint"]) else np.nan, "fee": L["fee"],
                "mint_auth": (oto.get(L["mint"]) or {}).get("mint_auth"), "freeze": (oto.get(L["mint"]) or {}).get("freeze"),
                "fee_bp": (oto.get(L["mint"]) or {}).get("fee_bp", 0),
                "creator_n": (dana.get(L["creator"]) or {}).get("n"), "creator_t1": (dana.get(L["creator"]) or {}).get("t"),
                "x_now": (cad.get(vt) or 0) / 10 ** dtk, "y_now": (cad.get(vx) or 0) / 10 ** dxn}
        jalur = {}
        for jd in JEDA:
            idx = int(np.searchsorted(d.t.values, t0 + jd, side="right") - 1)
            idx = max(idx, 0)
            tok, xs, ys = U.putar(d, L["fee"], idx, MODAL)
            v = U.nilai(tok, xs, ys, L["fee"])
            t = np.concatenate([[t0 + jd], d.t.values[idx + 1:]]).astype(float) - t0
            now = S.jual(base["x_now"], base["y_now"], tok, L["fee"]) * (1 - U.FEE_BOT) if base["x_now"] > 0 else 0.0
            jalur[jd] = {"t": t, "v": v.astype(float), "now": float(now), **fitur_saat(d, idx, L["creator"])}
        out.append({**base, "jalur": jalur})
    with open(F_JALUR, "wb") as f:
        pickle.dump(out, f)
    print(f"{len(out)} peluncuran → {F_JALUR}")


def muat() -> list[dict]:
    with open(F_JALUR, "rb") as f:
        return pickle.load(f)


# ------------------------------------------------------------------------------------------------- aturan keluar
def keluar(t: np.ndarray, v: np.ndarray, now: float, aturan: tuple) -> float:
    """XNT bersih diterima. aturan = (jenis, ...):
    ("tp", k, T, telat)        jual semua saat v ≥ k·modal, bila tak kena jual di T detik (T None = 24 jam)
    ("tpsl", k, s, T, telat)   + jual saat v ≤ s·modal
    ("parsial", f, k1, k2, T)  jual f bagian saat v ≥ k1·modal, sisa saat ≥ k2·modal atau di T
    ("modal", k, T)            saat v ≥ k·modal jual bagian senilai modal (1/k), sisa ikut sampai T (gratis)"""
    jenis = aturan[0]
    T = None
    if jenis == "tp":
        _, k, T, telat = aturan
        akhir = len(v) - 1 if T is None else max(int(np.searchsorted(t, T, side="right") - 1), 0)
        hit = np.nonzero(v[:akhir + 1] >= k * MODAL)[0]
        if len(hit):
            return float(v[min(hit[0] + telat, len(v) - 1)])
        return float(v[akhir])
    if jenis == "tpsl":
        _, k, s, T, telat = aturan
        akhir = len(v) - 1 if T is None else max(int(np.searchsorted(t, T, side="right") - 1), 0)
        w = v[:akhir + 1]
        hit = np.nonzero((w >= k * MODAL) | (w <= s * MODAL))[0]
        hit = hit[hit > 0] if len(hit) and hit[0] == 0 and w[0] <= s * MODAL else hit  # titik masuk sendiri bukan SL
        if len(hit):
            return float(v[min(hit[0] + telat, len(v) - 1)])
        return float(v[akhir])
    if jenis == "parsial":
        _, f, k1, k2, T = aturan
        akhir = len(v) - 1 if T is None else max(int(np.searchsorted(t, T, side="right") - 1), 0)
        w = v[:akhir + 1]
        h1 = np.nonzero(w >= k1 * MODAL)[0]
        if not len(h1):
            return float(w[-1])
        a = f * w[h1[0]]  # nilai jual sebagian ≈ proporsional (pool jauh lebih besar dari sisa kecil kita: aproksimasi)
        rest = w[h1[0]:]
        h2 = np.nonzero(rest >= k2 * MODAL)[0]
        return float(a + (1 - f) * (rest[h2[0]] if len(h2) else rest[-1]))
    if jenis == "modal":
        _, k, T = aturan
        akhir = len(v) - 1 if T is None else max(int(np.searchsorted(t, T, side="right") - 1), 0)
        w = v[:akhir + 1]
        h = np.nonzero(w >= k * MODAL)[0]
        if not len(h):
            return float(w[-1])
        f = 1.0 / k
        return float(f * w[h[0]] + (1 - f) * w[-1])
    raise ValueError(jenis)


ATURAN = (
    [("tp", k, T, 0) for k in (1.05, 1.1, 1.15, 1.2, 1.3, 1.5, 2, 3, 5, 10) for T in (600, 3600, 6 * 3600, None)]
    + [("tpsl", k, s, T, 0) for k in (1.2, 1.5, 2, 3) for s in (0.5, 0.7, 0.85) for T in (3600, None)]
    + [("parsial", f, k1, k2, None) for f in (0.5, 0.7) for k1 in (1.3, 1.5, 2) for k2 in (3, 5, 10)]
    + [("modal", k, None) for k in (1.5, 2, 3)]
)


# ---------------------------------------------------------------------------------------- reputasi tanpa masa depan
def reputasi(data: list[dict]) -> None:
    """Untuk tiap peluncuran: berapa kali pembuat sudah meluncurkan token sebelumnya & hasilnya, dan apakah wallet awal
    (sebelum kita masuk) termasuk "penembak untung" menurut peluncuran SEBELUMNYA. Disimpan di r['rep'][jeda]."""
    pembuat_hist: dict[str, list[float]] = defaultdict(list)   # pembuat → kelipatan puncak 24 jam token sebelumnya
    wallet_hist: dict[str, list[float]] = defaultdict(list)    # wallet → hasil (XNT) sebagai pembeli awal sebelumnya
    W = pd.read_csv(S.DIR / "pemain.csv")
    W = W[~W.pembuat & (W.modal > 0)]
    W["roi"] = W.pnl / W.modal
    hasil_pool = {k: g[["w", "roi", "urut"]].values.tolist() for k, g in W.groupby("pool")}
    for r in data:  # hasil tiap peluncuran (baru diketahui ±24 jam setelah t0)
        r["_rekam"] = (r["creator"], float(r["jalur"][0]["v"].max() / MODAL), hasil_pool.get(r["pool"], []))
    # hanya catat hasil yang sudah tersedia ≥ 24 jam sebelum t0 peluncuran yang dinilai (tanpa bocor masa depan)
    data_s = sorted(data, key=lambda q: q["t0"])
    j = 0
    for r in data_s:
        while j < len(data_s) and data_s[j]["t0"] + 86400 <= r["t0"]:
            c, pk, hp = data_s[j]["_rekam"]
            pembuat_hist[c].append(pk)
            for w, roi, urut in hp:
                if urut <= 5:
                    wallet_hist[w].append(roi)
            j += 1
        prev = pembuat_hist[r["creator"]]
        r["creator_prev"] = len(prev)
        r["creator_prev_bagus"] = float(np.mean([p >= 2 for p in prev])) if prev else np.nan
        for jd, J in r["jalur"].items():
            sk = [np.mean(wallet_hist[w]) for w in J["wallets"] if len(wallet_hist[w]) >= 3]
            J["penembak_n"] = int(sum(1 for s in sk if s > 0))
            J["penembak_rugi"] = int(sum(1 for s in sk if s <= 0))
            J["wallet_dikenal"] = int(sum(1 for w in J["wallets"] if len(wallet_hist[w]) >= 1))


def tabel(data: list[dict], jd: int) -> pd.DataFrame:
    rows = []
    for r in data:
        J = r["jalur"][jd]
        rows.append({k: v for k, v in r.items() if k not in ("jalur", "_rekam")} |
                    {k: v for k, v in J.items() if k not in ("t", "v", "wallets")} | {"jeda": jd})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------- alat uji standar
SYARAT = {"wr": 0.75, "n_min": 30, "telat": 1}  # dikunci 11 Okt 2026 sebelum pencarian aturan


def muat_siap() -> list[dict]:
    """Data jalur + reputasi tanpa bocor (cache wr_siap.pkl)."""
    f = S.DIR / "wr_siap.pkl"
    if f.exists() and f.stat().st_mtime >= F_JALUR.stat().st_mtime:
        with open(f, "rb") as h:
            return pickle.load(h)
    data = muat()
    reputasi(data)
    for r in data:
        r["latih"] = r["t0"] < POTONG
        r["umur_pembuat"] = (r["t0"] - r["creator_t1"]) / 86400 if r.get("creator_t1") else np.nan
    with open(f, "wb") as h:
        pickle.dump(data, h)
    return data


def hasil(data: list[dict], jd: int, aturan: tuple, saring=None) -> pd.DataFrame:
    """Satu baris per snipe yang lolos saringan: t0, latih, out (XNT bersih), untung (out > modal)."""
    rows = []
    for r in data:
        J = r["jalur"][jd]
        if saring is not None and not saring(r, J):
            continue
        out = keluar(J["t"], J["v"], J["now"], aturan)
        rows.append({"pool": r["pool"], "t0": r["t0"], "latih": r["latih"], "out": out, "untung": out > MODAL})
    return pd.DataFrame(rows)


def ringkas(h: pd.DataFrame) -> dict:
    o = {}
    for nama, z in (("latih", h[h.latih]), ("uji", h[~h.latih]), ("semua", h)):
        o[f"n_{nama}"] = len(z)
        o[f"wr_{nama}"] = float(z.untung.mean()) if len(z) else np.nan
        o[f"roi_{nama}"] = float(z.out.mean() / MODAL - 1) if len(z) else np.nan
    return o


def p_acak(data: list[dict], jd: int, aturan: tuple, h: pd.DataFrame, n_iter: int = 20000, seed: int = 7) -> float:
    """Peluang subset ACAK berukuran sama dari paruh UJI mencapai WR ≥ WR uji kandidat (tanpa koreksi banyak uji)."""
    semua = hasil(data, jd, aturan)
    u = semua[~semua.latih].untung.values
    k = int((~h.latih).sum())
    if k == 0:
        return 1.0
    wr = h[~h.latih].untung.mean()
    rng = np.random.default_rng(seed)
    sim = np.array([rng.choice(u, k, replace=False).mean() for _ in range(n_iter)])
    return float((sim >= wr - 1e-12).mean())


def lolos(o: dict) -> bool:
    return (o["n_latih"] >= SYARAT["n_min"] and o["n_uji"] >= SYARAT["n_min"] and o["wr_latih"] >= SYARAT["wr"]
            and o["wr_uji"] >= SYARAT["wr"] and o["roi_latih"] > 0 and o["roi_uji"] > 0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "bangun"
    if cmd == "bangun":
        bangun()
