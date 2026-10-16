"""🧩 Uji JUJUR dokumen "ARSITEKTUR konfluensi_85" (unggahan pengguna 16 Okt 2026) dengan DATA ASLI.

python -m research.konfluensi_85        → cloud/api/konfluensi_85.json + docs/eksternal/hasil_konfluensi_85.txt

Dokumen menjanjikan win rate 85–89% bila ≥ 4 dari 5 "metode dunia" searah, dengan angka JSON yang TIDAK pernah dihitung dari
repo ini (skrip risetnya hanya berisi fungsi, tanpa data). Di sini kelima vektor dihitung per rilis dari data asli dan aturan
rezim dokumen dipakai APA ADANYA (ambang tetap 0,6 / 0,7 / 65% / bobot 1,1 — tidak di-fit ke data, jadi seluruh periode adalah
uji luar sampel untuk aturan itu). Standar uji = standar dokumen sendiri: tanpa look-ahead (≤ t0−1 dtk), untung SETELAH spread
asli Exness, LAMA (< Okt 2021) vs BARU, Wilson lower bound (z 1,28), uji permutasi 5.000× (+ pembanding selalu-NAIK).

Vektor (+1 = emas NAIK, −1 = TURUN, 0 = netral), semua dari data yang sudah ada SEBELUM rilis:
  v_bar    palang perkiraan: Z = (Forecast − Previous) / MAD 12 rilis sebelumnya (|Act_t − Act_t−1|, hanya rilis lama);
           Z ≥ +0,6 → +1, Z ≤ −0,6 → −1 (pengangguran/klaim dibalik karena angka tinggi = buruk bagi USD)
  v_kalshi Kalshi 1 jam sebelum tutup: P(di atas konsensus) ≥ 65% → −1, P(di bawah) ≥ 65% → +1 (pengangguran dibalik);
           hanya CPI, NFP, pengangguran, core PCE (pasar Kalshi ada sejak ±2021)
  v_lead   petunjuk rantai pasok yang SUDAH teruji di aplikasi (research/live_kurva.tebakan: CPI indeks/Kalshi, PPI ← minyak,
           lainnya petunjuk KEJ)
  v_sweep  D = (harga t0−1 dtk − EMA 4 jam M15) / ATR20 M15; D ≥ +0,7 → −1 (disapu turun), D ≤ −0,7 → +1
  ko_rilis rilis bersamaan: varian A (dokumen harfiah) ≥ 2 berita High di jam sama; varian B ≥ 2 KELOMPOK berbeda (PPI+Retail)
Target: arah harga tengah tick Exness detik d vs t0−1 dtk (0 = salah, konservatif) + untung bersih posisi masuk t−1 searah.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
CACHE = EKS / "konfluensi_85_vektor.parquet"
OUT_JSON = ROOT / "cloud" / "api" / "konfluensi_85.json"
OUT_TXT = ROOT / "docs" / "eksternal" / "hasil_konfluensi_85.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
DETIK = (1, 2, 3, 5, 10, 30, 60)
UTAMA = {"CPI": ["CPI m/m"], "PPI": ["PPI m/m"], "NFP": ["Non-Farm Employment Change"], "RETAIL": ["Retail Sales m/m"],
         "ISM": ["ISM Manufacturing PMI", "ISM Services PMI"], "FOMC": ["Federal Funds Rate"],
         "PCE": ["Core PCE Price Index m/m"], "GDP": ["Advance GDP q/q"], "CLAIMS": ["Unemployment Claims"]}
KALSHI = {"CPI": "KXCPI", "NFP": "KXPAYROLLS", "PCE": "KXPCECORE"}
REZIM = ("KONFLUENSI_PENUH_NAIK", "KONFLUENSI_PENUH_TURUN", "SAPUAN_PUCUK_V_SHAPE_NAIK", "SAPUAN_DASAR_V_SHAPE_TURUN",
         "KONFLUENSI_MENENGAH_NAIK", "KONFLUENSI_MENENGAH_TURUN")
ARAH = {"KONFLUENSI_PENUH_NAIK": 1, "KONFLUENSI_PENUH_TURUN": -1, "SAPUAN_PUCUK_V_SHAPE_NAIK": -1,
        "SAPUAN_DASAR_V_SHAPE_TURUN": 1, "KONFLUENSI_MENENGAH_NAIK": 1, "KONFLUENSI_MENENGAH_TURUN": -1}
KLAIM = {"KONFLUENSI_PENUH_NAIK": 87.5, "KONFLUENSI_PENUH_TURUN": 86.7, "SAPUAN_PUCUK_V_SHAPE_NAIK": 85.7,
         "SAPUAN_DASAR_V_SHAPE_TURUN": 85.0, "KONFLUENSI_MENENGAH_NAIK": 77.8, "KONFLUENSI_MENENGAH_TURUN": 76.9}


AMBANG = {"persen": 75.0, "wilson": 70.0, "p": 0.01, "periode_n": 5, "periode_persen": 60.0}


def status(o: dict) -> str:
    """Status rezim menurut standar dokumen SENDIRI (≥ 75%, Wilson lower bound, permutasi p ≤ 0,01) + standar repo (LAMA &
    BARU masing-masing ≥ 5 rilis dan ≥ 60%). Hanya "teruji" yang boleh menimpa arah di cloud (_konfluensi_85.boleh_timpa)."""
    if not o.get("n"):
        return "tidak pernah terjadi"
    a = AMBANG
    if (o["d3"] >= a["persen"] and o["wilson_d3"] >= a["wilson"] and o.get("p_acak_rilis", 1.0) <= a["p"]
            and o["n_lama"] >= a["periode_n"] and o["n_baru"] >= a["periode_n"]
            and o.get("d3_lama", 0) >= a["periode_persen"] and o.get("d3_baru", 0) >= a["periode_persen"]):
        return "teruji"
    if o["d3"] >= a["periode_persen"] and o["n"] >= 10:
        return "belum terbukti"
    return "tidak lolos"


def mad_terakhir() -> dict:
    """MAD 12 rilis terakhir per judul (|Act_t − Act_t−1|) = pembagi Z palang untuk rilis BERIKUTNYA di cloud (live)."""
    from .news_data import _num, load_calendar
    from .run_scan import DATA
    cal = load_calendar(DATA)
    out = {}
    for ev in sorted({e for v in UTAMA.values() for e in v}):
        g = cal[cal.event == ev].sort_values("time")
        a = g.actual.map(_num)
        m = a.diff().abs().rolling(12, min_periods=6).median()
        if len(m) and m.iloc[-1] == m.iloc[-1] and m.iloc[-1] > 0:
            out[ev] = {"mad": round(float(m.iloc[-1]), 4), "sampai": g.time.iloc[-1].strftime("%Y-%m-%d")}
    return out


def wilson_lb(benar: int, n: int, z: float = 1.28155) -> float:
    if n <= 0:
        return 0.0
    p = benar / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return round((c - s) / den * 100, 1)


def rezim(v_bar: float, v_kalshi: float, v_lead: float, v_sweep: float, ko: bool) -> str | None:
    """Aturan dokumen apa adanya (research/konfluensi_85.py & _konfluensi_85.py versi dokumen)."""
    if ko and v_sweep <= -1 and v_lead <= -1 and v_bar >= 1:
        return "SAPUAN_PUCUK_V_SHAPE_NAIK"
    if ko and v_sweep >= 1 and v_lead >= 1 and v_bar <= -1:
        return "SAPUAN_DASAR_V_SHAPE_TURUN"
    skor = 1.1 * v_bar + 1.0 * v_kalshi + 1.1 * v_lead + 1.0 * v_sweep
    if not ko and skor >= 3.2:
        return "KONFLUENSI_PENUH_NAIK"
    if not ko and skor <= -3.2:
        return "KONFLUENSI_PENUH_TURUN"
    if skor >= 2.0:
        return "KONFLUENSI_MENENGAH_NAIK"
    if skor <= -2.0:
        return "KONFLUENSI_MENENGAH_TURUN"
    return None


def vektor() -> pd.DataFrame:
    """Satu baris per (rilis, kelompok) bertick Exness: kutipan masuk_pra + 5 vektor + rilis bersamaan."""
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from .event_stats import xau_m15
    from .kalshi_uji import rows as kalshi_rows
    from .live_kurva import tebakan
    from .masuk_pra import kutipan
    from .news_data import INVERSE, _num, load_calendar
    from .run_scan import DATA
    q = kutipan()
    q["t0"] = pd.to_datetime(q.t0, utc=True)
    q["v_lead"] = np.sign(tebakan(q).to_numpy())
    cal = load_calendar(DATA)
    cal["f"], cal["p"], cal["a"] = cal.forecast.map(_num), cal.previous.map(_num), cal.actual.map(_num)
    # MAD 12 rilis SEBELUMNYA per judul (|Act_t − Act_t−1|), hanya angka yang sudah keluar sebelum rilis ini
    mad = {}
    for ev, g in cal.sort_values("time").groupby("event"):
        d = g.a.diff().abs()
        m = d.rolling(12, min_periods=6).median().shift(1)
        for t, v in zip(g.time, m):
            mad[(ev, t)] = v
    per_t = {t: g for t, g in cal.groupby("time")}
    # Kalshi 1 jam sebelum tutup
    kr = kalshi_rows()
    kr["t0"] = pd.to_datetime(kr.t0, utc=True)
    kal = {}
    for _, r in kr.iterrows():
        kal[(r.seri, r.t0)] = (r.get("atas 1 jam"), r.get("bawah 1 jam"))
    m15 = xau_m15()
    close, high, low = m15.close.to_numpy(), m15.high.to_numpy(), m15.low.to_numpy()
    ema = m15.close.ewm(span=16, adjust=False).mean().to_numpy()            # 16 × 15 mnt = 4 jam
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    atr = pd.Series(tr).rolling(20).mean().to_numpy()
    idx = m15.index
    rows = []
    for r in q.itertuples(index=False):
        t0 = r.t0
        o = {"t0": t0, "grup": r.grup}
        g = per_t.get(t0)
        # rilis bersamaan
        if g is not None:
            o["n_event"] = int(len(g))
            o["n_grup"] = int(g.group.dropna().nunique())
        else:
            o["n_event"], o["n_grup"] = 0, 0
        # v_bar
        vb, z = 0.0, np.nan
        if g is not None and r.grup in UTAMA:
            e = g[g.event.isin(UTAMA[r.grup])]
            if len(e):
                e = e.iloc[0]
                md = mad.get((e.event, t0))
                if e.f == e.f and e.p == e.p and md and md == md and md > 0:
                    z = (e.f - e.p) / md
                    s = -1.0 if e.event in INVERSE else 1.0
                    vb = s * (1.0 if z >= 0.6 else -1.0 if z <= -0.6 else 0.0)
        o["z_bar"], o["v_bar"] = z, vb
        # v_kalshi
        vk = 0.0
        seri = KALSHI.get(r.grup)
        if seri and (seri, t0) in kal:
            atas, bawah = kal[(seri, t0)]
            if atas == atas and atas is not None and bawah == bawah and bawah is not None:
                if atas >= 0.65:
                    vk = -1.0
                elif bawah >= 0.65 or (1 - atas) >= 0.65:
                    vk = 1.0
        o["v_kalshi"] = vk
        # v_sweep: bar M15 yang SUDAH tutup sebelum t0
        k = int(idx.searchsorted(t0 - pd.Timedelta(minutes=15), side="right")) - 1
        vs, dd = 0.0, np.nan
        if k >= 25 and atr[k] == atr[k] and atr[k] > 0 and abs((idx[k] + pd.Timedelta(minutes=15) - t0).total_seconds()) <= 900:
            m0 = (r.bid_in + r.ask_in) / 2
            dd = (m0 - ema[k]) / atr[k]
            vs = -1.0 if dd >= 0.7 else 1.0 if dd <= -0.7 else 0.0
        o["d_xau"], o["v_sweep"] = dd, vs
        rows.append(o)
    v = pd.DataFrame(rows)
    df = q.merge(v, on=["t0", "grup"], how="left")
    df.to_parquet(CACHE)
    return df


def hasil(df: pd.DataFrame, arah: np.ndarray, m: np.ndarray) -> dict:
    """Akurasi arah per detik (harga tengah; 0 = salah) + untung bersih masuk t−1 tutup detik 3/10/60."""
    from .masuk_pra import mid, pnl
    x, d = df[m], arah[m]
    if len(x) == 0:
        return {"n": 0}
    m0 = ((x.bid_in + x.ask_in) / 2).to_numpy()
    lama = (x.t0 < SPLIT).to_numpy()
    o = {"n": int(len(x)), "n_lama": int(lama.sum()), "n_baru": int((~lama).sum())}
    for s in DETIK:
        g = d * (mid(x, s) - m0)
        ok = g > 0
        o[f"d{s}"] = round(float(ok.mean() * 100), 1)
        if lama.sum():
            o[f"d{s}_lama"] = round(float(ok[lama].mean() * 100), 1)
        if (~lama).sum():
            o[f"d{s}_baru"] = round(float(ok[~lama].mean() * 100), 1)
    for h in (3, 10, 60):
        v = pnl(x, d, h)
        o[f"untung{h}"] = round(float((v > 0).mean() * 100), 1)
        o[f"rata{h}"] = round(float(v.mean()), 2)
    ok3 = (d * (mid(x, 3) - m0)) > 0
    o["wilson_d3"] = wilson_lb(int(ok3.sum()), len(x))
    # V-shape: arah detik 3 searah, lalu detik 10 berbalik melewati harga t−1
    g3, g10 = d * (mid(x, 3) - m0), d * (mid(x, 10) - m0)
    o["v_shape"] = round(float(((g3 > 0) & (g10 < 0)).mean() * 100), 1)
    return o


def permutasi(df: pd.DataFrame, arah: np.ndarray, m: np.ndarray, s: int = 3, n_iter: int = 5000, seed: int = 42) -> dict:
    """p vs 50% (binomial acak, cara dokumen) dan p vs pilihan rilis ACAK dengan arah sama (mengontrol tren emas)."""
    from .masuk_pra import mid
    m0 = ((df.bid_in + df.ask_in) / 2).to_numpy()
    g = mid(df, s) - m0
    obs = float(((arah[m] * g[m]) > 0).mean()) if m.sum() else 0.0
    rng = np.random.default_rng(seed)
    k = int(m.sum())
    if k == 0:
        return {"p_binomial": 1.0, "p_acak_rilis": 1.0}
    acak = rng.binomial(1, 0.5, size=(n_iter, k)).mean(axis=1)
    p1 = float((acak >= obs).mean())
    d_all = np.where(arah[m] > 0, 1, -1)
    pool = np.arange(len(df))
    hits = []
    for _ in range(n_iter):
        j = rng.choice(pool, size=k, replace=False)
        hits.append(((d_all * g[j]) > 0).mean())
    p2 = float((np.array(hits) >= obs).mean())
    return {"p_binomial": round(p1, 4), "p_acak_rilis": round(p2, 4)}


def main() -> None:
    df = vektor()
    df = df.dropna(subset=["v_lead"]).reset_index(drop=True)
    L = ["# 🧩 Uji dokumen konfluensi_85 dengan data asli (research/konfluensi_85.py)", __doc__.split("\n\n")[1],
         f"rilis bertick Exness: {df.t0.nunique()} jam rilis, {len(df)} baris (rilis × kelompok)"]
    for c in ("v_bar", "v_kalshi", "v_lead", "v_sweep"):
        L.append(f"   {c}: +1 {int((df[c] > 0).sum())} • −1 {int((df[c] < 0).sum())} • 0 {int((df[c] == 0).sum())}")
    out = {"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "sumber": "research/konfluensi_85.py",
           "catatan": "angka HASIL UJI data asli (tick Exness 2016–2026), bukan angka dokumen unggahan",
           "n_rilis": int(df.t0.nunique()), "tahun": f"{df.t0.min().year}–{df.t0.max().year}", "ambang": AMBANG,
           "mad": mad_terakhir(), "varian": {}}
    from .masuk_pra import mid
    m0 = ((df.bid_in + df.ask_in) / 2).to_numpy()
    naik3 = (mid(df, 3) - m0) > 0
    out["selalu_naik_d3"] = round(float(naik3.mean() * 100), 1)
    L.append(f"pembanding: emas naik di detik 3 pada {naik3.mean() * 100:.1f}% rilis (selalu-NAIK); acak = 50%")
    for var, kolom in (("A_berita", "n_event"), ("B_kelompok", "n_grup")):
        ko = (df[kolom] >= 2).to_numpy()
        lab = np.array([rezim(a, b, c, d, k) for a, b, c, d, k in
                        zip(df.v_bar, df.v_kalshi, df.v_lead, df.v_sweep, ko)], dtype=object)
        arah = np.array([ARAH.get(x, 0) for x in lab], dtype=float)
        L.append(f"\n## Varian rilis bersamaan {var} (ko_rilis = {kolom} ≥ 2: {int(ko.sum())} baris)")
        L.append("   rezim | n (LAMA/BARU) | klaim dokumen | arah benar detik 1 • 2 • 3 • 5 • 10 • 30 • 60 | LAMA / BARU detik 3 | "
                 "untung bersih t−1 tutup 3 dtk / 10 dtk / 1 mnt | Wilson LB d3 | V-shape | p (acak 50% / acak rilis) | status")
        res = {}
        for rz in REZIM:
            m = lab == rz
            o = hasil(df, arah, m)
            if o["n"]:
                o.update(permutasi(df, arah, m))
                o["arah"] = "naik" if ARAH[rz] > 0 else "turun"
                o["klaim_dokumen"] = KLAIM[rz]
            o["status"] = status(o)
            res[rz] = o
            if not o["n"]:
                L.append(f"   {rz:28s} | n 0 — tidak pernah terjadi")
                continue
            L.append(f"   {rz:28s} | n {o['n']} ({o['n_lama']}/{o['n_baru']}) | {KLAIM[rz]}% | " +
                     " • ".join(f"{o[f'd{s}']:.0f}" for s in DETIK) + f" | {o.get('d3_lama', '–')} / {o.get('d3_baru', '–')} | "
                     f"{o['untung3']:.0f}% {o['rata3']:+.2f} / {o['untung10']:.0f}% {o['rata10']:+.2f} / {o['untung60']:.0f}% "
                     f"{o['rata60']:+.2f} | {o['wilson_d3']} | {o['v_shape']}% | {o['p_binomial']} / {o['p_acak_rilis']} | "
                     f"{o['status']}")
        # klaim utama dokumen: semakin banyak metode searah → semakin akurat
        L.append("   Jumlah metode searah (dari 4 vektor arah; mayoritas tanpa lawan) → arah benar detik 3 / 10 / 60:")
        V = df[["v_bar", "v_kalshi", "v_lead", "v_sweep"]].to_numpy()
        pos, neg = (V > 0).sum(axis=1), (V < 0).sum(axis=1)
        res["per_jumlah"] = {}
        for kk in (1, 2, 3, 4):
            for nm, sel, dr in (("naik", (pos == kk) & (neg == 0), 1.0), ("turun", (neg == kk) & (pos == 0), -1.0)):
                if sel.sum() == 0:
                    continue
                o = hasil(df, np.full(len(df), dr), sel)
                res["per_jumlah"][f"{kk}_{nm}"] = o
                L.append(f"     {kk} metode → {nm.upper():5s} n {o['n']:4d} ({o['n_lama']}/{o['n_baru']}): detik 3 {o['d3']:.0f}% "
                         f"(LAMA {o.get('d3_lama', '–')} / BARU {o.get('d3_baru', '–')}) • 10 dtk {o['d10']:.0f}% • 1 mnt {o['d60']:.0f}% "
                         f"• untung bersih 1 mnt {o['untung60']:.0f}% ({o['rata60']:+.2f} $/oz)")
        out["varian"][var] = res
    # masing-masing vektor sendirian (apakah tiap "metode dunia" punya keunggulan?)
    L.append("\n## Tiap metode sendirian: arah benar detik 3 / 1 mnt bila vektor ≠ 0 (LAMA | BARU)")
    out["tunggal"] = {}
    for c in ("v_bar", "v_kalshi", "v_lead", "v_sweep"):
        m = (df[c] != 0).to_numpy()
        o = hasil(df, df[c].to_numpy(), m)
        if o["n"]:
            o.update(permutasi(df, df[c].to_numpy(), m))
        out["tunggal"][c] = o
        if o["n"]:
            L.append(f"   {c:8s} n {o['n']:4d}: detik 3 {o['d3']:.1f}% (LAMA {o.get('d3_lama', '–')} | BARU {o.get('d3_baru', '–')}) • "
                     f"1 mnt {o['d60']:.1f}% • untung bersih 1 mnt {o['untung60']:.0f}% ({o['rata60']:+.2f}) • p acak rilis {o['p_acak_rilis']}")
    a = AMBANG
    lolos = [f"{v}:{r}" for v, res in out["varian"].items() for r, o in res.items() if r in REZIM and o.get("status") == "teruji"]
    L.append(f"\n## Kesimpulan (syarat teruji: arah benar detik 3 ≥ {a['persen']:.0f}%, Wilson LB ≥ {a['wilson']:.0f}%, p acak rilis "
             f"≤ {a['p']}, LAMA & BARU masing-masing ≥ {a['periode_n']} rilis dan ≥ {a['periode_persen']:.0f}%)")
    L.append("   rezim teruji: " + (", ".join(lolos) if lolos else "TIDAK ADA → cloud tidak menimpa arah (hanya info 🧩)"))
    L.append("   MAD terakhir (pembagi Z palang live): " + " • ".join(f"{k} {v['mad']:g} (s/d {v['sampai']})"
                                                               for k, v in out["mad"].items()))
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    OUT_TXT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
