"""Validasi mendalam kandidat "beli listing baru Binance setelah turun >= 60% dari P0" — python -m research.listing_dip_porto

Aturan dasar (kandidat dari research/listing_baru.py): P0 = VWAP 60 menit pertama listing pair USDT di Binance spot;
pasang limit beli di P0 x (1 - b) yang berlaku 30 hari pertama (mulai candle 1 jam SETELAH jendela P0); jual di TP
+s, SL -l (0 = tanpa), maksimal T hari. Dasar b 0,6 / s 0,2 / l 0,5 / T 90.

Yang diuji di sini (permintaan pemimpin 8 Okt 2026, untuk bot sniper Telegram):
  1. biaya realistis: fee 0,1%/sisi (0,2% pulang-pergi) + slippage order PASAR (SL, batas waktu, entry telat) =
     setengah spread 0,1% + dampak akar-kuadrat sigma_harian x sqrt(ukuran / volume 24 jam); order LIMIT (entry, TP)
     tanpa slippage. Ukuran posisi dibatasi <= 0,5% volume quote 24 jam SEBELUM entry (tanpa look-ahead).
  2. simulasi PORTOFOLIO urut waktu: alokasi 5/10/20% ekuitas (kas + nilai pasar posisi), maks 10 posisi,
     LAMA (< Okt 2021) & BARU (>= Okt 2021) dimulai terpisah dengan modal 1 (tanpa dampak ukuran) / $1.000 / $10.000.
  3. walk-forward: tiap tahun Y pilih (b, s, l) dari trade yang SUDAH SELESAI sebelum 1 Jan Y.
  4. ketahanan: entry telat 1 jam, biaya x2/x3, P0 VWAP 30/120 mnt, pembanding acak, bootstrap, tanpa pair USDT baru
     untuk koin lama, tanpa pekan crash, kapasitas.
  5. cek look-ahead eksplisit (P0 & entry dihitung ulang dari data yang dipotong pada saat keputusan).
  6. listing baru Sep–Okt 2026 (data-api.binance.vision, hanya data pasar publik — TIDAK ada order).
Hasil: docs/eksternal/hasil_listing_dip_porto.txt. Data: data/research/eksternal/listing/ (dari listing_baru unduh),
pair_lain.parquet (hari pertama pair BTC/BNB), dip_trades.csv (rekaman trade aturan dasar, dua mode SL).

Ringkasan 8 Okt 2026: angka lama BARU +7,1%/trade berasal dari candle entry yang diabaikan (flash crash 10 Okt 2025:
harga menembus limit lalu jatuh > 50% di jam yang sama). Dihitung benar: SL order stop BARU -0,7%/trade; SL dicek di
close 1 jam +3,5%/trade (t 1,2) -> tidak lolos untuk uang nyata; LAMA +12-13%/trade (t ~5).
"""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from research.listing_baru import D1, DIR, POTONG, _keluar, muat

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_listing_dip_porto.txt"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DAPI = "https://data-api.binance.vision/api/v3"

FEE = 0.001          # per sisi (tanpa diskon BNB) -> 0,2% pulang-pergi
HALF_SPREAD = 0.001  # setengah spread untuk order pasar (koin kecil yang baru jatuh)
Y_IMPACT = 1.0       # koefisien hukum akar-kuadrat
CAP = 0.005          # ukuran posisi maks 0,5% volume quote 24 jam
MIN_ORDER = 5.0      # minimum notional Binance (USDT)
DASAR = (0.6, 0.2, 0.5, 90)
DATA_AKHIR = pd.Timestamp("2026-10-06", tz="UTC")  # data 1 jam diunduh s/d 7 Okt 2026
H = np.timedelta64(1, "h")
DAY = np.timedelta64(1, "D")


def _np(t: pd.Timestamp) -> np.datetime64:
    return np.datetime64(t.tz_convert("UTC").tz_localize(None), "ns")


# ---------------------------------------------------------------- data per listing
def vwap(m: pd.DataFrame, t: pd.Timestamp, menit: int) -> float:
    """VWAP harga tipikal candle 1 menit dengan waktu buka < t + menit (hanya data sebelum keputusan)."""
    w = m[m.index < t + pd.Timedelta(minutes=menit)]
    tp = (w.high + w.low + w.close) / 3
    return float((tp * w.qvol).sum() / w.qvol.sum()) if w.qvol.sum() > 0 else float(w.close.iloc[-1])


def siapkan() -> dict[str, dict]:
    """Array 1 jam + P0 (30/60/120 mnt) + volume 24 jam & sigma (dari candle SEBELUM i) per listing."""
    met = pd.read_parquet(DIR / "metrik.parquet")
    out = {}
    for r in met.itertuples():
        h, m = muat(r.sym)
        t = r.t
        if m is not None and len(m) >= 30:
            p0 = {w: vwap(m, t, w) for w in (30, 60, 120)}
        else:  # tidak terjadi pada data ini (semua punya 1m), cadangan: close jam pertama
            p0 = {w: float(h.close.iloc[0]) for w in (30, 60, 120)}
        tt = h.index.values.astype("datetime64[ns]")
        o, hi, lo, c, qv = (h[k].to_numpy(float) for k in ("open", "high", "low", "close", "qvol"))
        cq = np.concatenate([[0.0], np.cumsum(qv)])
        j24 = np.searchsorted(tt, tt - 24 * H)
        v24 = cq[np.arange(len(tt))] - cq[j24]          # volume 24 jam SEBELUM candle i (tidak termasuk i)
        lr = pd.Series(np.diff(np.log(np.maximum(c, 1e-12))))
        roll = lr.rolling(72, min_periods=6).std(ddof=0).to_numpy() * np.sqrt(24)
        sig = np.full(len(tt), 0.10)                    # sigma harian dari 72 return 1 jam yang SUDAH diketahui
        if len(tt) > 2:                                 # saat candle i dibuka: lr[i-73 .. i-2]
            x = roll[: len(tt) - 2]
            sig[2:] = np.where(np.isnan(x), 0.10, x)
        t0 = _np(t)
        out[r.sym] = {
            "sym": r.sym, "t": t, "periode": r.periode, "tahun": t.year, "p0": p0, "p0_lama": r.p0,
            "tt": tt, "o": o, "hi": hi, "lo": lo, "c": c, "v24": v24, "sig": sig,
            "i0": {w: int(np.searchsorted(tt, t0 + np.timedelta64(w, "m"))) for w in (30, 60, 120)},
            "W": int(np.searchsorted(tt, t0 + 30 * DAY)),
        }
    return out


# ---------------------------------------------------------------- satu trade
def trade(L: dict, b: float, s: float, l: float, T: int = 90, w: int = 60, telat: bool = False,
          idx_acak: int | None = None, sl_mode: str = "intra") -> dict | None:
    """Entry & exit satu listing. Kembalikan rekaman trade (harga kotor; biaya dihitung di net()).
    sl_mode: "intra" = order stop di bursa (terisi di SL atau open bila gap), "rendah" = stop terisi di low candle
    (terburuk, mis. flash crash), "tutup" = SL hanya dicek di close candle 1 jam lalu jual pasar di close."""
    tt, o, hi, lo, c = L["tt"], L["o"], L["hi"], L["lo"], L["c"]
    i0, W = L["i0"][w], L["W"]
    if idx_acak is not None:                       # pembanding: beli pasar di open jam acak
        i, e, pasar_in, penuh = idx_acak, o[idx_acak], True, True
    else:
        lim = L["p0"][w] * (1 - b)
        hit = np.flatnonzero(lo[i0:W] <= lim)
        if not len(hit):
            return None
        i = i0 + int(hit[0])
        if telat:                                  # bot cek per jam: beli pasar di open candle berikutnya
            i += 1
            if i >= len(tt):
                return None
            e, pasar_in, penuh = o[i], True, True
        else:                                      # limit beli yang menunggu: isi di limit (atau open bila lebih rendah)
            e, pasar_in, penuh = min(o[i], lim), False, False
    tp, sl = e * (1 + s), (e * (1 - l) if l else -1.0)
    j = int(np.searchsorted(tt, tt[i] + T * DAY))  # candle dengan waktu buka < entry + T hari
    rec = {"sym": L["sym"], "t": L["t"], "periode": L["periode"], "tahun": L["tahun"], "i": i, "e": e,
           "t_in": tt[i] + (np.timedelta64(30, "m") if not penuh else np.timedelta64(0, "m")),
           "pasar_in": pasar_in, "v_in": L["v24"][i], "sig_in": L["sig"][i]}

    def selesai(k, x, jenis):
        rec.update(k=k, x=x, jenis=jenis, t_out=tt[k] + H, v_out=L["v24"][k], sig_out=L["sig"][k],
                   pasar_out=jenis != "TP", hari=float((tt[k] + H - tt[i]) / DAY))
        return rec

    def pertama(a):
        return int(a[0]) if len(a) else 10**9

    if not penuh:                                  # candle entry limit: TP sebelum terisi tidak dihitung
        if sl_mode == "tutup":                     # SL dicek di close 1 jam; close >= TP berarti TP tersentuh SETELAH terisi
            if c[i] >= tp:
                return selesai(i, tp, "TP")
            if l and c[i] <= sl:
                return selesai(i, c[i], "SL")
        else:                                      # SL order stop: low <= SL di candle entry pasti SETELAH terisi
            if l and lo[i] <= sl:
                return selesai(i, sl if sl_mode == "intra" else lo[i], "SL")
            if c[i] >= tp:
                return selesai(i, tp, "TP")
        k0 = i + 1
    else:
        k0 = i
    k_tp = pertama(np.flatnonzero(hi[k0:j] >= tp))
    if sl_mode == "tutup":                         # TP (limit menunggu) lebih dulu dari SL yang baru dicek di close
        k_sl = pertama(np.flatnonzero(c[k0:j] <= sl)) if l else 10**9
        if k_tp < 10**9 and k_tp <= k_sl:
            return selesai(k0 + k_tp, max(o[k0 + k_tp], tp), "TP")
        if k_sl < 10**9:
            return selesai(k0 + k_sl, c[k0 + k_sl], "SL")
    else:                                          # SL dulu bila TP & SL di candle sama (konservatif)
        k_sl = pertama(np.flatnonzero(lo[k0:j] <= sl)) if l else 10**9
        if k_sl < 10**9 and k_sl <= k_tp:
            k = k0 + k_sl
            return selesai(k, min(o[k], sl) if sl_mode == "intra" else lo[k], "SL")
        if k_tp < 10**9:
            return selesai(k0 + k_tp, max(o[k0 + k_tp], tp), "TP")
    if tt[-1] + H >= tt[i] + T * DAY and j - 1 >= i:
        return selesai(j - 1, c[j - 1], "WAKTU")
    k = len(tt) - 1
    return selesai(k, c[k], "TERBUKA" if tt[k] >= _np(DATA_AKHIR) else "PUTUS")


def net(r: dict | pd.Series, q: float = 0.0, kb: float = 1.0) -> float:
    """Return bersih untuk posisi q USDT (q = 0 -> tanpa dampak ukuran). kb = pengali biaya (x2, x3)."""
    s_in = (HALF_SPREAD + Y_IMPACT * r["sig_in"] * np.sqrt(q / max(r["v_in"], 1.0))) * kb if r["pasar_in"] else 0.0
    qx = q * r["x"] / r["e"]
    s_out = (HALF_SPREAD + Y_IMPACT * r["sig_out"] * np.sqrt(qx / max(r["v_out"], 1.0))) * kb if r["pasar_out"] else 0.0
    return r["x"] / r["e"] * (1 - FEE * kb - s_out) / (1 + FEE * kb + s_in) - 1


def semua(D: dict, b, s, l, T=90, w=60, telat=False, sl_mode="intra") -> pd.DataFrame:
    rows = [x for L in D.values() if (x := trade(L, b, s, l, T, w, telat, sl_mode=sl_mode)) is not None]
    return pd.DataFrame(rows).sort_values("t_in").reset_index(drop=True)


def stat(df: pd.DataFrame, q: float = 0.0, kb: float = 1.0) -> dict:
    if not len(df):
        return {"n": 0}
    v = np.array([net(r, q, kb) for _, r in df.iterrows()])
    return {"n": len(v), "wr": (v > 0).mean(), "rata": v.mean(), "median": np.median(v), "terburuk": v.min(),
            "terbaik": v.max(), "v": v}


def fmt(st: dict) -> str:
    if not st.get("n"):
        return "n 0"
    return (f"n {st['n']:3d}  WR {st['wr']:4.0%}  rata {st['rata']:+6.1%}  median {st['median']:+6.1%}  "
            f"terburuk {st['terburuk']:+5.0%}")


def boot(v: np.ndarray, n: int = 5000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    bs = rng.choice(v, (n, len(v))).mean(1)
    return float(np.percentile(bs, 5)), float(np.percentile(bs, 95))


# ---------------------------------------------------------------- portofolio
def porto(tr: pd.DataFrame, D: dict, alloc: float = 0.10, maxpos: int = 10, modal: float | None = None,
          kb: float = 1.0, mulai: pd.Timestamp | None = None, akhir: pd.Timestamp | None = None) -> dict:
    """Simulasi urut waktu. modal None = ekuitas 1 tanpa dampak ukuran & tanpa batas volume;
    modal $ = slippage akar-kuadrat + batas 0,5% volume 24 jam + minimum order $5.
    Ukuran = alokasi x ekuitas (kas + nilai pasar posisi terbuka di close 1 jam terakhir), maks = kas;
    sinyal dilewati bila posisi sudah maks atau kas < setengah target."""
    usd = modal is not None
    modal0 = float(modal if usd else 1.0)
    tr = tr.sort_values("t_in").reset_index(drop=True)
    n = len(tr)
    tin = tr.t_in.values.astype("datetime64[ns]")
    tout = tr.t_out.values.astype("datetime64[ns]")
    e, x, ii = tr.e.to_numpy(float), tr.x.to_numpy(float), tr.i.to_numpy(int)
    v_in, v_out = tr.v_in.to_numpy(float), tr.v_out.to_numpy(float)
    s_in_, s_out_ = tr.sig_in.to_numpy(float), tr.sig_out.to_numpy(float)
    p_in, p_out = tr.pasar_in.to_numpy(bool), tr.pasar_out.to_numpy(bool)
    Ls = [D[s] for s in tr.sym]
    kas = modal0
    buka: dict[int, float] = {}            # idx -> unit
    biaya, uang = np.zeros(n), np.zeros(n)
    unit, porsi, dipakai = np.zeros(n), np.zeros(n), np.zeros(n, bool)
    lewat_penuh = lewat_kas = dipotong = kecil = 0
    maks_buka = 0

    def harga(j, t):
        L = Ls[j]
        k = int(np.searchsorted(L["tt"], t - H, "right")) - 1   # candle yang sudah tutup sebelum t
        return L["c"][k] if k >= ii[j] else e[j]

    def tutup_sampai(t):
        nonlocal kas
        for j in sorted([j for j in buka if tout[j] <= t], key=lambda j: tout[j]):
            u = buka.pop(j)
            q = u * x[j]
            if p_out[j]:
                so = (HALF_SPREAD + (Y_IMPACT * s_out_[j] * np.sqrt(q / max(v_out[j], 1.0)) if usd else 0.0)) * kb
            else:
                so = 0.0
            uang[j] = q * (1 - FEE * kb - so)
            kas += uang[j]

    for j in range(n):
        t = tin[j]
        tutup_sampai(t)
        if len(buka) >= maxpos:
            lewat_penuh += 1
            continue
        ekuitas = kas + sum(u * harga(k, t) for k, u in buka.items())
        target = alloc * ekuitas
        ukuran = min(target, kas)
        if ukuran < 0.5 * target:
            lewat_kas += 1
            continue
        if usd:
            if ukuran > CAP * v_in[j]:
                dipotong += 1
                ukuran = CAP * v_in[j]
            if ukuran < MIN_ORDER:
                kecil += 1
                continue
        si = (HALF_SPREAD + (Y_IMPACT * s_in_[j] * np.sqrt(ukuran / max(v_in[j], 1.0)) if usd else 0.0)) * kb \
            if p_in[j] else 0.0
        unit[j] = ukuran / (e[j] * (1 + FEE * kb + si))
        biaya[j], porsi[j], dipakai[j] = ukuran, ukuran / ekuitas, True
        kas -= ukuran
        buka[j] = unit[j]
        maks_buka = max(maks_buka, len(buka))
    tutup_sampai(np.datetime64("2100-01-01"))
    # kurva ekuitas harian (nilai pasar, akhir hari UTC)
    t_mulai = _np(mulai) if mulai is not None else tin.min() - DAY
    t_akhir = _np(akhir) if akhir is not None else (tout[dipakai].max() if dipakai.any() else t_mulai + DAY)
    hari = (np.arange(t_mulai.astype("datetime64[D]"), t_akhir.astype("datetime64[D]") + 2) + 1).astype("datetime64[ns]")
    eq = np.full(len(hari), modal0)
    for j in np.flatnonzero(dipakai):
        a = int(np.searchsorted(hari, tin[j]))
        z = int(np.searchsorted(hari, tout[j]))
        eq[a:] -= biaya[j]
        eq[z:] += uang[j]
        if z > a:
            L = Ls[j]
            k = np.searchsorted(L["tt"], hari[a:z] - H, "right") - 1
            eq[a:z] += unit[j] * np.where(k >= ii[j], L["c"][np.clip(k, 0, None)], e[j])
    s = pd.Series(eq, index=pd.to_datetime(hari - DAY, utc=True))   # label = tanggal hari itu
    dd = float((s / s.cummax() - 1).min())
    th = (s.index[-1] - s.index[0]).days / 365.25
    cagr = float((s.iloc[-1] / s.iloc[0]) ** (1 / th) - 1) if th > 0 else np.nan
    akhir_th = s.groupby(s.index.year).last()
    awal = np.concatenate([[s.iloc[0]], akhir_th.values[:-1]])
    per_th = pd.Series(akhir_th.values / awal - 1, index=akhir_th.index)
    h = tr[dipakai].assign(biaya=biaya[dipakai], uang=uang[dipakai], unit=unit[dipakai], porsi=porsi[dipakai])
    h["ret"] = h.uang / h.biaya - 1
    n_th = h.groupby(pd.to_datetime(h.t_in).dt.year).size() if len(h) else pd.Series(dtype=int)
    return {"kurva": s, "cagr": cagr, "dd": dd, "akhir": float(s.iloc[-1] / s.iloc[0]), "per_th": per_th,
            "n_th": n_th, "h": h, "lewat_penuh": lewat_penuh, "lewat_kas": lewat_kas, "dipotong": dipotong,
            "kecil": kecil, "maks_buka": maks_buka}


def ringkas_porto(p: dict, judul: str) -> list[str]:
    h = p["h"]
    L = [f"{judul}: akhir x{p['akhir']:.2f}, CAGR {p['cagr']:+.1%}, DD maks {p['dd']:+.1%}, trade {len(h)}"
         f" (lewat: posisi penuh {p['lewat_penuh']}, kas kurang {p['lewat_kas']}, < $5 {p['kecil']};"
         f" dipotong batas 0,5% vol {p['dipotong']}; posisi bersamaan maks {p['maks_buka']})"]
    if len(h):
        v = h.ret.to_numpy()
        L.append(f"    per trade: WR {(v > 0).mean():.0%}, rata {v.mean():+.1%}, median {np.median(v):+.1%}, "
                 f"terburuk {v.min():+.0%}; porsi ekuitas rata {h.porsi.mean():.1%}")
    L.append("    per tahun: " + ", ".join(f"{y} {r:+.0%} ({p['n_th'].get(y, 0)} tr)" for y, r in p["per_th"].items()))
    return L


def btc_tahan(mulai: pd.Timestamp, akhir: pd.Timestamp) -> str:
    d = pd.read_parquet(D1 / "BTC.parquet").close
    d = d[(d.index >= mulai.normalize()) & (d.index <= akhir)]
    th = (d.index[-1] - d.index[0]).days / 365.25
    dd = (d / d.cummax() - 1).min()
    return f"BTC beli-tahan {d.index[0]:%Y-%m-%d}..{d.index[-1]:%Y-%m-%d}: x{d.iloc[-1] / d.iloc[0]:.2f}, " \
           f"CAGR {(d.iloc[-1] / d.iloc[0]) ** (1 / th) - 1:+.1%}, DD maks {dd:+.1%}"


# ---------------------------------------------------------------- pembanding acak
def acak_trades(D: dict, syms, s, l, T, seed: int, w: int = 60, sl_mode: str = "intra") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for sym in syms:
        L = D[sym]
        i0, W = L["i0"][w], L["W"]
        if W - i0 < 2:
            continue
        x = trade(L, 0, s, l, T, w, idx_acak=int(rng.integers(i0, W)), sl_mode=sl_mode)
        if x is not None:
            rows.append(x)
    return pd.DataFrame(rows).sort_values("t_in").reset_index(drop=True)


# ---------------------------------------------------------------- cek look-ahead
def cek_lookahead(D: dict, tr: pd.DataFrame) -> list[str]:
    """Hitung ulang P0 & entry dari data yang DIPOTONG pada saat keputusan; harus identik."""
    beda_p0 = beda_entry = 0
    for r in tr.itertuples():
        L = D[r.sym]
        _, m = muat(r.sym)
        m_pot = m[m.index < r.t + pd.Timedelta(minutes=60)]        # hanya 60 menit pertama yang tersedia
        if abs(vwap(m_pot, r.t, 60) - L["p0"][60]) > 1e-12 * L["p0"][60]:
            beda_p0 += 1
        # potong data 1 jam sampai candle entry (inklusif) -> deteksi ulang
        Lp = {**L, **{k: L[k][: r.i + 1] for k in ("tt", "o", "hi", "lo", "c", "v24", "sig")}}
        Lp["W"] = min(L["W"], r.i + 1)
        lim = L["p0"][60] * (1 - DASAR[0])
        hit = np.flatnonzero(Lp["lo"][L["i0"][60]:Lp["W"]] <= lim)
        if not len(hit) or L["i0"][60] + int(hit[0]) != r.i or min(Lp["o"][r.i], lim) != r.e:
            beda_entry += 1
    n_awal = sum(1 for r in tr.itertuples() if D[r.sym]["tt"][r.i] < _np(r.t + pd.Timedelta(minutes=60)))
    v_bocor = 0
    for r in tr.itertuples():                                       # volume 24 jam dari DataFrame mentah, < candle entry
        h, _ = muat(r.sym)
        te = pd.Timestamp(D[r.sym]["tt"][r.i], tz="UTC")
        v = h[(h.index >= te - pd.Timedelta(hours=24)) & (h.index < te)].qvol.sum()
        v_bocor += not np.isclose(v, r.v_in, rtol=1e-9)
    return [f"P0 dihitung ulang dari 60 menit pertama saja: beda {beda_p0}/{len(tr)}",
            f"entry dihitung ulang dari data yang dipotong di candle entry: beda {beda_entry}/{len(tr)}",
            f"candle entry yang dimulai sebelum P0 selesai (t+60 mnt): {n_awal}",
            f"volume 24 jam saat entry dihitung ulang dari candle < candle entry: beda {v_bocor}/{len(tr)}; sigma memakai "
            "return 1 jam yang sudah tutup (lr[i-73..i-2])"]


# ---------------------------------------------------------------- pair lain (listing sungguhan?)
def _s3_keys(prefix: str) -> list[str]:
    with urllib.request.urlopen(f"{S3}?prefix={prefix}", timeout=60) as r:
        return re.findall(r"<Key>([^<]*)</Key>", r.read().decode())


def _hari_pertama(sym: str) -> pd.Timestamp | None:
    keys = sorted(k for k in _s3_keys(f"data/spot/monthly/klines/{sym}/1d/") if k.endswith(".zip"))
    if not keys:
        return None
    with urllib.request.urlopen("https://data.binance.vision/" + keys[0], timeout=60) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    t = int(pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0]).iloc[0, 0])
    return pd.to_datetime(t, unit="us" if t > 1e14 else "ms", utc=True)


def pair_lain(syms) -> pd.DataFrame:
    """Hari pertama pair XXX/BTC & XXX/BNB (bila ada). Bila jauh sebelum pair USDT -> bukan listing token baru."""
    f = DIR / "pair_lain.parquet"
    if f.exists():
        return pd.read_parquet(f)

    def satu(sym):
        out = {"sym": sym}
        for q in ("BTC", "BNB"):
            try:
                out[q] = _hari_pertama(sym + q)
            except Exception:  # noqa: BLE001
                out[q] = None
        return out

    with ThreadPoolExecutor(12) as ex:
        df = pd.DataFrame(list(ex.map(satu, syms)))
    for q in ("BTC", "BNB"):
        df[q] = pd.to_datetime(df[q], utc=True)
    df.to_parquet(f)
    return df


# ---------------------------------------------------------------- listing terbaru (Sep-Okt 2026)
def _get(url: str):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())


def listing_terbaru(D: dict) -> list[str]:
    """Pair USDT yang sedang TRADING tetapi belum ada di data harian bulanan -> listing baru. Hanya data pasar."""
    L = []
    try:
        info = _get(f"{DAPI}/exchangeInfo?permissions=SPOT&symbolStatus=TRADING")
    except Exception as exc:  # noqa: BLE001
        return [f"exchangeInfo gagal: {exc}"]
    ada = {f.stem for f in D1.glob("*.parquet")}
    kand = [s for s in info["symbols"] if s["quoteAsset"] == "USDT" and s["baseAsset"] not in ada]
    rows = []
    for s in kand:
        try:
            k = _get(f"{DAPI}/klines?symbol={s['symbol']}&interval=1d&startTime=0&limit=1")
        except Exception:  # noqa: BLE001
            continue
        if k:
            rows.append((s["symbol"], pd.to_datetime(k[0][0], unit="ms", utc=True)))
    rows.sort(key=lambda x: x[1])
    L.append(f"pair USDT TRADING di exchangeInfo: {sum(1 for s in info['symbols'] if s['quoteAsset'] == 'USDT')}; "
             f"belum ada di data harian bulanan: {len(kand)}")
    baru = [(s, t) for s, t in rows if t >= pd.Timestamp("2026-08-01", tz="UTC")]
    lama = [(s, t) for s, t in rows if t < pd.Timestamp("2026-08-01", tz="UTC")]
    L.append(f"  di antaranya hari pertama < Agu 2026 (bukan listing baru / pair stablecoin/fiat dsb.): {len(lama)} "
             f"(contoh {', '.join(s for s, _ in lama[:8])})")
    L.append(f"  listing pertama >= Agu 2026: {len(baru)}")
    # status pantauan sekarang untuk listing <= 30 hari terakhir (termasuk dari data kita)
    now = pd.Timestamp.now(tz="UTC")
    pantau = [(s, t) for s, t in baru]
    for sym, Lx in D.items():
        if Lx["t"] >= now - pd.Timedelta(days=45):
            pantau.append((sym + "USDT", Lx["t"]))
    seen = set()
    for s, t in pantau:
        if s in seen:
            continue
        seen.add(s)
        try:
            m1 = _get(f"{DAPI}/klines?symbol={s}&interval=1m&startTime={int(t.timestamp() * 1000)}&limit=120")
            m1 = pd.DataFrame(m1).iloc[:, :8].astype(float)
            m1.columns = ["t", "open", "high", "low", "close", "vol", "tc", "qvol"]
            m1.index = pd.to_datetime(m1.t, unit="ms", utc=True)
            tl = m1.index[0]
            p0 = vwap(m1, tl, 60)
            hari = _get(f"{DAPI}/klines?symbol={s}&interval=1h&startTime={int((tl + pd.Timedelta(hours=1)).timestamp() * 1000)}"
                        f"&limit=1000")
            hh = pd.DataFrame(hari).iloc[:, :5].astype(float)
            hh = hh[hh[0] < (tl + pd.Timedelta(days=30)).timestamp() * 1000]      # hanya jendela 30 hari
            low = hh[3].min() if len(hh) else np.nan
            last = hh[4].iloc[-1] if len(hh) else np.nan
            umur = (now - tl).days
            saham = s.endswith("BUSDT") and tl >= pd.Timestamp("2026-06-01", tz="UTC")
            L.append(("  [token saham, dikecualikan] " if saham else "  ") + f"{s:14s} listing {tl:%Y-%m-%d %H:%M} UTC, P0 {p0:.6g}, limit 60% {p0 * 0.4:.6g}, terendah sejak "
                     f"jam ke-2 (30 hari) {low / p0 - 1:+.0%}, sekarang {last / p0 - 1:+.0%}, umur {umur} hari -> "
                     + ("SINYAL SUDAH TERJADI" if low <= p0 * 0.4 else
                        ("jendela 30 hari habis" if umur > 30 else "masih dipantau")))
        except Exception as exc:  # noqa: BLE001
            L.append(f"  {s}: gagal {exc}")
    return L


# ---------------------------------------------------------------- laporan
MODE = {"intra": "SL = order stop di bursa (dasar)", "tutup": "SL dicek di close 1 jam (jual pasar)"}
AKHIR_BARU = pd.Timestamp("2026-10-07", tz="UTC")
BATAS = {"LAMA": (pd.Timestamp("2017-09-01", tz="UTC"), None), "BARU": (POTONG, AKHIR_BARU)}


def _ret(df: pd.DataFrame, q: float = 0.0, kb: float = 1.0) -> pd.DataFrame:
    return df.assign(ret=[net(r, q, kb) for _, r in df.iterrows()])


def laporan() -> str:
    D = siapkan()
    out: list[str] = []
    p = out.append
    b0, s0, l0, T0 = DASAR
    basis = {m: _ret(semua(D, b0, s0, l0, T0, sl_mode=m)) for m in MODE}
    base = basis["intra"]
    p("=== Validasi: beli listing baru Binance setelah turun >= 60% dari P0, TP +20%, SL -50%, maks 90 hari")
    p(f"Universe: {len(D)} listing pair USDT Binance spot 2017-09..2026-09 (termasuk yang sudah delisting).")
    p("P0 = VWAP 60 menit pertama (1m); limit beli P0 x 0,4 berlaku untuk candle 1 jam yang DIMULAI >= t+60 mnt s/d t+30 hari.")
    p(f"Biaya: fee {FEE:.1%}/sisi (pulang-pergi {2 * FEE:.1%}); order pasar (SL, batas waktu, entry telat) + setengah "
      f"spread {HALF_SPREAD:.1%} + dampak {Y_IMPACT:g} x sigma_harian x sqrt(ukuran/volume 24 jam); order limit (entry, TP)"
      " tanpa slippage.")
    p("Urutan dalam candle: candle entry -> SL (low <= SL) pasti SETELAH terisi (harga turun melewati limit) jadi dihitung;"
      " TP hanya bila close >= TP (pasti setelah terisi). Candle berikutnya: SL dulu bila TP & SL di candle sama.")
    p("LAMA = listing < Okt 2021, BARU = >= Okt 2021. 'modal 1' = tanpa dampak ukuran; $1.000/$10.000 = dengan dampak & batas"
      " 0,5% volume 24 jam.\n")

    p("--- 0. Cek look-ahead & reproduksi angka lama")
    for x in cek_lookahead(D, base):
        p("  " + x)
    g = pd.read_parquet(DIR / "grid.parquet")
    g0 = g[(g["mode"] == "dip") & (g.b == b0) & (g.s == s0) & (g.l == l0) & (g["T"] == T0)]
    rep = []
    for _, r in base.iterrows():
        L = D[r.sym]
        j = int(np.searchsorted(L["tt"], L["tt"][r.i] + T0 * DAY))
        sl_ = slice(r.i + 1, max(j, r.i + 2))
        rep.append(_keluar(L["hi"][sl_], L["lo"][sl_], L["c"][sl_], L["o"][sl_], r.e, s0, l0, 0.004))
    rep = np.array(rep)
    for per in ("LAMA", "BARU"):
        mk = (base.periode == per).to_numpy()
        p(f"  {per}: listing_baru._keluar (candle entry diabaikan, biaya 0,4%) pada entry yang sama: n {mk.sum()}, "
          f"rata {rep[mk].mean():+.2%} (grid.parquet {g0[g0.periode == per].ret.mean():+.2%}, n {len(g0[g0.periode == per])})"
          f" -> dengan candle entry dihitung: {base[mk].ret.mean():+.2%}")
    ce = base[base.k == base.i]
    p(f"  trade yang selesai di candle entry: {len(ce)} (SL {int((ce.jenis == 'SL').sum())}, TP {int((ce.jenis == 'TP').sum())});"
      " SL di candle entry: " + ", ".join(f"{r.sym} {pd.Timestamp(r.t_in):%Y-%m-%d %H:%M}" for r in
                                          ce[ce.jenis == 'SL'].itertuples()))
    p("  -> angka lama (+7,1% BARU) terlalu optimistis: 6 dari 8 SL candle entry terjadi saat flash crash 10 Okt 2025"
      " 21:00 UTC (harga menembus limit lalu terus jatuh > 50% dalam jam yang sama, lalu pulih).\n")

    # ------------------------------------------------ 1. per trade
    p("--- 1. Per trade (aturan 0,6 / 0,2 / 0,5 / 90)")
    for m, judul in MODE.items():
        d = basis[m]
        p(f"  [{judul}]")
        for nama, q in (("modal 1 (tanpa dampak)", 0.0), ("$1.000 x 10% = $100/trade", 100.0),
                        ("$10.000 x 10% = $1.000/trade", 1000.0)):
            for per in ("LAMA", "BARU"):
                st = stat(d[d.periode == per], q)
                ci = boot(st["v"])
                p(f"    {nama:30s} {per}: {fmt(st)}  CI90 rata [{ci[0]:+.1%}, {ci[1]:+.1%}]")
        for per in ("LAMA", "BARU"):
            x = d[d.periode == per]
            j = x.jenis.value_counts()
            p(f"    {per} cara keluar: " + ", ".join(f"{k} {v}" for k, v in j.items())
              + f"; lama tahan median {x.hari.median():.1f} hari (TP {x[x.jenis == 'TP'].hari.median():.1f}, "
                f"SL {x[x.jenis == 'SL'].hari.median():.1f})")
        th = d.groupby("tahun").ret.agg(n="size", wr=lambda v: (v > 0).mean(), rata="mean", median="median",
                                        terburuk="min", jumlah="sum")
        p("    per tahun listing (modal 1):")
        p("    " + th.round(3).to_string().replace("\n", "\n    "))
    bln = pd.to_datetime(base.t_in).dt.strftime("%Y-%m")
    kl = bln.value_counts().head(6)
    p("  bulan dengan entry terbanyak (kluster crash): " + ", ".join(f"{k} {v}" for k, v in kl.items()))
    for m in MODE:
        d = basis[m].sort_values("ret", ascending=False)
        p(f"  [{m}] 5 trade terbaik menyumbang {d.ret.head(5).sum() / d.ret.sum():.0%} dari jumlah return; tanpa 5 terbaik:"
          f" rata LAMA {d.iloc[5:][d.iloc[5:].periode == 'LAMA'].ret.mean():+.1%}, BARU "
          f"{d.iloc[5:][d.iloc[5:].periode == 'BARU'].ret.mean():+.1%}")
    p("\n  Kapasitas: volume quote 24 jam SEBELUM entry (USDT):")
    for per in ("LAMA", "BARU"):
        vv = base[base.periode == per].v_in
        p(f"    {per}: median ${vv.median():,.0f}, P10 ${vv.quantile(.1):,.0f}, P90 ${vv.quantile(.9):,.0f}, "
          f"minimum ${vv.min():,.0f}")
    for modal in (1000, 10000, 100000):
        s_ = []
        for a in (0.05, 0.10, 0.20):
            for per in ("LAMA", "BARU"):
                x = base[base.periode == per]
                s_.append(f"{a:.0%} {per} {(x.v_in * CAP < a * modal).sum()}/{len(x)}")
        p(f"    posisi > 0,5% vol 24 jam (modal ${modal:,} x alokasi, tanpa compounding): " + "; ".join(s_))
    for q in (100, 1000, 10000):
        sl = np.array([(HALF_SPREAD + Y_IMPACT * r.sig_out * np.sqrt(q * r.x / r.e / max(r.v_out, 1))) for r in
                       base[base.jenis == "SL"].itertuples()])
        p(f"    perkiraan slippage SL untuk posisi ${q:,}: median {np.median(sl):.2%}, P90 {np.percentile(sl, 90):.2%}"
          f" (sigma harian median saat SL {base[base.jenis == 'SL'].sig_out.median():.0%})")

    # ------------------------------------------------ 2. portofolio
    p("\n--- 2. Portofolio (urut waktu, maks 10 posisi, alokasi % dari ekuitas nilai pasar, kurva harian)")
    hasil_porto = {}
    for m, judul in MODE.items():
        d = basis[m]
        p(f"\n  ===== {judul}")
        for per in ("LAMA", "BARU"):
            m0, m1 = BATAS[per]
            x = d[d.periode == per]
            p(f"  [{per}] {len(x)} sinyal")
            for a in (0.05, 0.10, 0.20):
                for modal in (None, 1000.0, 10000.0):
                    pr = porto(x, D, a, 10, modal, mulai=m0, akhir=m1)
                    hasil_porto[(m, per, a, modal)] = pr
                    nm = f"alokasi {a:.0%}, " + ("modal 1" if modal is None else f"${modal:,.0f}")
                    for y in ringkas_porto(pr, nm):
                        p("  " + y)
            pr = hasil_porto[(m, per, 0.10, None)]
            p("  " + btc_tahan(pr["kurva"].index[0], pr["kurva"].index[-1]))
    pr_l = hasil_porto[("intra", "LAMA", 0.10, None)]
    p(f"\n  Catatan: periode LAMA dari 2017-09-01 s/d exit trade LAMA terakhir ({pr_l['kurva'].index[-1]:%Y-%m-%d}); BARU "
      "2021-10-01 s/d 2026-10-07; tahun tanpa trade = 0% (kas menganggur, tanpa bunga).")

    # ------------------------------------------------ 3. walk-forward
    p("\n--- 3. Walk-forward (pilih b,s,l dari trade yang SELESAI sebelum 1 Jan tahun uji; T 90; modal 1)")
    B, S, Ls = (0.5, 0.6, 0.7), (0.1, 0.2, 0.3), (0, 0.3, 0.5)
    for m, judul in MODE.items():
        kom = {(b, s, l): _ret(semua(D, b, s, l, 90, sl_mode=m)) for b in B for s in S for l in Ls}
        p(f"\n  ===== {judul}")
        tetap_tr = []
        for kriteria in ("rata", "rata-1SE"):
            rows, pilih_tr = [], []
            for Y in range(2019, 2027):
                tY = np.datetime64(f"{Y}-01-01")
                best, skor_b = None, -9.0
                for k, d in kom.items():
                    x = d[d.t_out <= tY].ret
                    if len(x) < 15:
                        continue
                    sk = x.mean() if kriteria == "rata" else x.mean() - x.std(ddof=1) / np.sqrt(len(x))
                    if sk > skor_b:
                        best, skor_b = k, sk
                if best is None:
                    best = (b0, s0, l0)
                uji = kom[best][kom[best].tahun == Y]
                ref = kom[(b0, s0, l0)][kom[(b0, s0, l0)].tahun == Y]
                rows.append((Y, best, len(uji), uji.ret.mean(), (uji.ret > 0).mean(), len(ref), ref.ret.mean(),
                             (ref.ret > 0).mean()))
                pilih_tr.append(uji)
                if kriteria == "rata":
                    tetap_tr.append(ref)
            allw = pd.concat(pilih_tr)
            p(f"  kriteria '{kriteria}' (n latih >= 15; tahun 2019 = latih 2017-2018):")
            p("   tahun  pilihan(b,s,l)    n    rata    WR  | tetap 0,6/0,2/0,5:  n    rata    WR")
            for Y, bst, n, rt, wr, nr, rr, wrr in rows:
                p(f"   {Y}   {str(bst):16s} {n:3d} {rt:+7.1%} {wr:4.0%}  |                   {nr:3d} {rr:+7.1%} {wrr:4.0%}")
            for per in ("LAMA", "BARU"):
                a = allw[allw.periode == per].ret
                p(f"   total {per}: walk-forward n {len(a)}, WR {(a > 0).mean():.0%}, rata {a.mean():+.1%}, "
                  f"jumlah {a.sum():+.2f}")
            for per in ("LAMA", "BARU"):
                m0, m1 = BATAS[per]
                m0 = pd.Timestamp("2019-01-01", tz="UTC") if per == "LAMA" else m0
                a = porto(allw[allw.periode == per], D, 0.10, 10, None, mulai=m0, akhir=m1)
                p(f"   portofolio 10% {per}: walk-forward x{a['akhir']:.2f} CAGR {a['cagr']:+.1%} DD {a['dd']:+.1%}")
        tetap_all = pd.concat(tetap_tr)
        for per in ("LAMA", "BARU"):
            a = tetap_all[tetap_all.periode == per].ret
            m0, m1 = BATAS[per]
            m0 = pd.Timestamp("2019-01-01", tz="UTC") if per == "LAMA" else m0
            pb = porto(tetap_all[tetap_all.periode == per], D, 0.10, 10, None, mulai=m0, akhir=m1)
            p(f"   pembanding aturan tetap {per} (tahun uji 2019+): n {len(a)}, WR {(a > 0).mean():.0%}, rata "
              f"{a.mean():+.1%}, jumlah {a.sum():+.2f}; portofolio 10% x{pb['akhir']:.2f} CAGR {pb['cagr']:+.1%} "
              f"DD {pb['dd']:+.1%}")
        p("  Peta 27 kombinasi (rata %/trade, modal 1) LAMA | BARU:")
        for k, d in kom.items():
            a, c = d[d.periode == "LAMA"].ret, d[d.periode == "BARU"].ret
            p(f"   b {k[0]} s {k[1]} l {k[2]}: LAMA n {len(a):3d} WR {(a > 0).mean():4.0%} {a.mean():+6.1%} | BARU n "
              f"{len(c):3d} WR {(c > 0).mean():4.0%} {c.mean():+6.1%}")
        lolos = [k for k, d in kom.items() if d[d.periode == "LAMA"].ret.mean() > 0 and d[d.periode == "BARU"].ret.mean() > 0]
        p(f"  kombinasi positif di KEDUA periode: {len(lolos)}/27: " + ", ".join(map(str, lolos)))

    # ------------------------------------------------ 4. ketahanan
    p("\n--- 4. Ketahanan (per trade modal 1 | portofolio 10% modal 1 BARU)")

    def baris(nama, df, kb=1.0, q=0.0):
        l_, b_ = df[df.periode == "LAMA"], df[df.periode == "BARU"]
        sl_, sb = stat(l_, q, kb), stat(b_, q, kb)
        ci = boot(sb["v"]) if sb.get("n") else (np.nan, np.nan)
        pb = porto(b_, D, 0.10, 10, None, kb=kb, mulai=POTONG, akhir=AKHIR_BARU) if len(b_) else None
        p(f"  {nama:40s} LAMA {fmt(sl_)}")
        p(f"  {'':40s} BARU {fmt(sb)}  CI90 [{ci[0]:+.1%}, {ci[1]:+.1%}]"
          + (f"  porto CAGR {pb['cagr']:+.1%} DD {pb['dd']:+.1%}" if pb else ""))

    pl = pair_lain([L["sym"] for L in D.values()]).set_index("sym")
    tl = pd.Series({k: L["t"] for k, L in D.items()})
    awal_lain = pl[["BTC", "BNB"]].min(axis=1)
    lama_koin = set(awal_lain[awal_lain < tl.reindex(awal_lain.index) - pd.Timedelta(days=7)].index)
    for m, judul in MODE.items():
        d = basis[m]
        p(f"\n  ===== {judul}")
        baris("dasar (limit, P0 60 mnt)", d)
        dt = semua(D, b0, s0, l0, T0, telat=True, sl_mode=m)
        baris("entry telat 1 jam (pasar di open)", dt)
        baris("biaya x2", d, kb=2.0)
        baris("biaya x3", d, kb=3.0)
        baris("telat 1 jam + biaya x2", dt, kb=2.0)
        baris("P0 = VWAP 30 menit", semua(D, b0, s0, l0, T0, w=30, sl_mode=m))
        baris("P0 = VWAP 120 menit", semua(D, b0, s0, l0, T0, w=120, sl_mode=m))
        baris("$1.000 x10% ($100) + slippage", d, q=100.0)
        baris("$10.000 x10% ($1.000) + slippage", d, q=1000.0)
        baris("hanya listing token sungguhan", d[~d.sym.isin(lama_koin)])
        tgl = pd.to_datetime(d.t_in).dt.strftime("%Y-%m-%d")
        crash = tgl.isin(["2020-03-12", "2020-03-13", "2021-05-19", "2022-06-13", "2022-11-09", "2025-10-10",
                          "2025-10-11"]).to_numpy()
        p(f"  entry pada hari crash besar (12-13 Mar 2020, 19 Mei 2021, 13 Jun 2022, 9 Nov 2022, 10-11 Okt 2025): "
          f"{crash.sum()} trade, rata {d[crash].ret.mean():+.1%}")
        baris("tanpa hari crash besar", d[~crash])
        for vmin in (100_000, 1_000_000):
            baris(f"hanya volume 24j sebelum entry >= ${vmin:,}", d[d.v_in >= vmin])
    baris("SL stop terisi di LOW candle (terburuk)", semua(D, b0, s0, l0, T0, sl_mode="rendah"))
    baris("tanpa SL (l = 0), maks 90 hari", semua(D, b0, s0, 0, T0))
    p(f"\n  Pair USDT baru untuk koin yang SUDAH listing di Binance (pair BTC/BNB > 7 hari lebih dulu): {len(lama_koin)}"
      f" dari {len(D)} listing (LAMA {sum(D[s]['periode'] == 'LAMA' for s in lama_koin)}, BARU "
      f"{sum(D[s]['periode'] == 'BARU' for s in lama_koin)}); di antara sinyal: {base.sym.isin(lama_koin).sum()}")

    # ------------------------------------------------ 5. pembanding acak
    p("\n--- 5. Pembanding ACAK (token yang SAMA dengan sinyal, beli pasar di open jam acak dalam 30 hari, TP/SL/T sama)")
    for m, judul in MODE.items():
        d = basis[m]
        p(f"  ===== {judul}")
        for per in ("LAMA", "BARU"):
            x = d[d.periode == per]
            m0, m1 = BATAS[per]
            rata_ac, cagr_ac, dd_ac = [], [], []
            for sd in range(200):
                ac = acak_trades(D, x.sym.unique(), s0, l0, T0, seed=sd, sl_mode=m)
                rata_ac.append(np.mean([net(r) for _, r in ac.iterrows()]))
                if sd < 20:
                    pa = porto(ac, D, 0.10, 10, None, mulai=m0, akhir=m1)
                    cagr_ac.append(pa["cagr"])
                    dd_ac.append(pa["dd"])
            rata_ac = np.array(rata_ac)
            ps = hasil_porto[(m, per, 0.10, None)]
            p(f"  {per}: sinyal rata {x.ret.mean():+.1%} vs acak rata {rata_ac.mean():+.1%} (P5..P95 "
              f"{np.percentile(rata_ac, 5):+.1%}..{np.percentile(rata_ac, 95):+.1%}); p-acak "
              f"{(rata_ac >= x.ret.mean()).mean():.3f} (200 undian)")
            p(f"        portofolio 10%: sinyal CAGR {ps['cagr']:+.1%} DD {ps['dd']:+.1%} vs acak (20 undian) CAGR median "
              f"{np.median(cagr_ac):+.1%} [{min(cagr_ac):+.1%}..{max(cagr_ac):+.1%}], DD median {np.median(dd_ac):+.1%}")
        for per in ("LAMA", "BARU"):
            syms = [k for k, L in D.items() if L["periode"] == per]
            rr = [np.mean([net(r) for _, r in acak_trades(D, syms, s0, l0, T0, seed=1000 + sd, sl_mode=m).iterrows()])
                  for sd in range(20)]
            p(f"  {per}: acak dari SEMUA listing ({len(syms)} token, 20 undian): rata {np.mean(rr):+.1%}")
        tv = d[d.periode == "BARU"].ret
        tl_ = d[d.periode == "LAMA"].ret
        p(f"  t-stat rata vs 0: LAMA {tl_.mean() / (tl_.std(ddof=1) / np.sqrt(len(tl_))):.2f}, BARU "
          f"{tv.mean() / (tv.std(ddof=1) / np.sqrt(len(tv))):.2f}")

    # ------------------------------------------------ 6. listing terbaru
    p("\n--- 6. Listing baru Sep-Okt 2026 (data-api.binance.vision exchangeInfo + klines, data pasar publik)")
    for x in listing_terbaru(D):
        p(x)

    # ------------------------------------------------ 7. kesimpulan (angka diambil dari hasil di atas)
    p("\n--- 7. Kesimpulan")
    st = {(m, per): basis[m][basis[m].periode == per].ret for m in MODE for per in ("LAMA", "BARU")}
    tst = {k: v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) for k, v in st.items()}
    pi, pt = hasil_porto[("intra", "BARU", 0.10, None)], hasil_porto[("tutup", "BARU", 0.10, None)]
    li, lt = hasil_porto[("intra", "LAMA", 0.10, None)], hasil_porto[("tutup", "LAMA", 0.10, None)]
    p(f"  * Angka lama BARU +7,1%/trade TIDAK bertahan: dengan SL & TP di candle entry dihitung benar, aturan dasar (SL order"
      f" stop) BARU {st[('intra', 'BARU')].mean():+.1%}/trade (t {tst[('intra', 'BARU')]:.2f}), portofolio 10% CAGR "
      f"{pi['cagr']:+.1%} DD {pi['dd']:+.1%}. LAMA tetap kuat {st[('intra', 'LAMA')].mean():+.1%} (t "
      f"{tst[('intra', 'LAMA')]:.2f}), CAGR {li['cagr']:+.1%} DD {li['dd']:+.1%}.")
    p(f"  * Varian SL dicek di close 1 jam (dipilih SETELAH melihat flash crash 10 Okt 2025 -> belum terbukti): LAMA "
      f"{st[('tutup', 'LAMA')].mean():+.1%} (t {tst[('tutup', 'LAMA')]:.2f}), BARU {st[('tutup', 'BARU')].mean():+.1%} "
      f"(t {tst[('tutup', 'BARU')]:.2f}, CI90 mencakup 0); portofolio 10% BARU CAGR {pt['cagr']:+.1%} DD {pt['dd']:+.1%}"
      f" (LAMA CAGR {lt['cagr']:+.1%}).")
    p("  * Walk-forward TIDAK lebih baik dari aturan tetap (memilih tanpa SL / TP 30% yang gagal di 2024-2025).")
    p("  * Mengalahkan beli ACAK pada token yang sama (p < 0,005) karena listing baru cenderung terus turun; tetapi nilai"
      " absolut BARU ~0 s/d +3,5%/trade dan portofolio BARU kalah dari BTC beli-tahan (CAGR +11,7%, walau DD BTC -77%).")
    p("  * Rapuh terhadap eksekusi: entry telat 1 jam (cek per jam, beli pasar) -> BARU ~0%. 2025 (46 sinyal, kluster Sep-Okt)"
      " negatif. Kapasitas bukan masalah untuk modal $1.000-$10.000.")
    p("  => TIDAK LOLOS untuk uang nyata (BARU tidak signifikan). Bila dipasang di bot: mode KERTAS/uji maju dengan aturan"
      " tetap 0,6/0,2/0,5/90 + SL di close 1 jam, alokasi <= 5%.")

    text = "\n".join(out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text + "\n")
    pd.concat([basis[m].assign(sl_mode=m) for m in MODE]).to_csv(DIR / "dip_trades.csv", index=False)
    return text


if __name__ == "__main__":
    print(laporan())
