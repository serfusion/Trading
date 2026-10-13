"""🏭 ISM Manufaktur & ISM Jasa → petunjuk SEBELUM rilis untuk ARAH LONJAKAN TERBESAR emas di MENIT PERTAMA.

python -m research.riset_ism            → docs/eksternal/hasil_riset_ism.txt (+ data/research/eksternal/riset_ism/)
Data & target: research/riset_ism_data.py (daftar rilis lengkap 10:00 ET, tick tambahan Dukascopy, kalender gabungan).

Permintaan pengguna 11 Okt 2026: cari petunjuk pra-rilis per berita yang menebak arah lonjakan menit pertama, uji jujur
(tutup kertas + permutasi keluarga), pasang hanya yang tinggi & dapat dipercaya. Putaran 1 (research/berita_detik.py,
lonjakan_uji.py) menggabung ISM manufaktur + jasa dan GAGAL (FED 57%, CHI 49%, SPG 45%; P/P3/KON tidak pernah dipakai
karena < 50%). Di sini keduanya DIPISAH (jam & penggeraknya beda) dan petunjuk diperdalam.

=== PRA-REGISTRASI (ditulis 11 Okt 2026 SEBELUM evaluasi apa pun di skrip ini) ===
Notasi per rilis: A = Act, K = konsensus (Nasdaq/Investing.com; cadangan ForexFactory), V = angka bulan lalu (seperti
tercetak di hari rilis), s = tanda(A − K). Setiap petunjuk = tebakan tanda s (+1 = ISM DI ATAS konsensus). ISM di atas =
baik untuk USD → tebakan emas = −petunjuk. "Bulan acuan" = bulan sebelum bulan rilis. Hanya data terbit < t0 − 1 dtk.
Aturan "_D" memakai satu definisi seragam: regresi OLS walk-forward (hanya rilis sebelumnya, ≥ 24 titik, dengan
intersep) ΔISM = A − V terhadap fitur x → Δ̂; petunjuk = tanda(Δ̂ − (K − V)) ("informasi menyiratkan perubahan lebih
besar/kecil daripada perubahan yang diperkirakan ekonom"). Tanpa ambang kecuali disebut.

ISM MANUFAKTUR (rilis hari kerja pertama, 10:00 ET):
 M01 -P        berbalik dari kejutan ISM manufaktur bulan lalu (≤ 45 hari). Alasan: survei bising, ekonom menambatkan
               perkiraan pada angka terakhir → kejutan cenderung berbalik. [PASCA-LIHAT: putaran 1 gabungan P 43%
               angka; pra_per_berita manufaktur 50%]
 M02 -KON      tanda(K − V): ekonom kurang mengekstrapolasi arah perubahan → angka melampaui arah konsensus.
               [PASCA-LIHAT: putaran 1 gabungan KON 43,6% angka = kebalikannya 56%]
 M03 FLASH_K   kejutan S&P Global FLASH Manufacturing PMI bulan acuan (terbit ±1 pekan sebelumnya, 09:45 ET) vs
               konsensusnya, searah. Alasan: informasi baru bulan yang sama.
 M04 FLASH_D   aturan _D dengan x = flash − PMI S&P final bulan lalu.
 M05 FINAL_R   revisi S&P Global FINAL Manufacturing PMI terhadap flash (terbit 09:45 ET HARI YANG SAMA, 15 mnt
               sebelum ISM; 2012–2014 pukul 08:58–09:00), searah. Alasan: jawaban akhir bulan juga tertangkap ISM;
               konsensus ISM sudah dikumpulkan sebelumnya.
 M06 CHI_K     kejutan Chicago PMI (hari kerja terakhir bulan acuan, 09:45 ET) vs konsensus, searah. [versi data lebih
               lengkap dari CHI putaran 1: ForexFactory + Nasdaq]
 M07 CHI_D     aturan _D, x = Chicago A − V.
 M08 REG_K     tanda jumlah tanda kejutan survei Fed daerah manufaktur BULAN ACUAN (Empire, Philly, Richmond, KC;
               terbit sebelum t0), searah. [versi rapi dari FED putaran 1: jendela = bulan acuan, data FF + Nasdaq]
 M09 REG_D     aturan _D, x = rata-rata z(Δ) survei daerah bulan acuan (Empire, Philly, Richmond, KC dari kalender
               A − V; Dallas dari FRED rilis pertama BACTSAMFRBDAL), z = Δ / simpangan baku Δ masa lalu (≥ 12),
               minimal 2 survei.
 M10 REG_D+    seperti M09 tetapi hanya bila |Δ̂ − (K − V)| ≥ 0,5 poin (sinyal kuat).
 M11 NOG       aturan _D, x = New Orders ISM bulan lalu − PMI bulan lalu (pesanan memimpin produksi).
 M12 MR6       tanda(rata-rata 6 angka ISM terakhir − K): pembalikan ke rata-rata (survei bising, konsensus menempel V).
 M13 SEAS      tanda rata-rata kejutan bulan kalender acuan yang sama di tahun-tahun lalu (≥ 4 tahun): sisa musiman.
 M14 VOTE_INFO tanda(FLASH_D + FINAL_R + CHI_D + REG_D).
 M15 VOTE_ALL  tanda(-P + -KON + FLASH_D + FINAL_R + CHI_D + REG_D + NOG).

ISM JASA (rilis hari kerja ketiga, 10:00 ET):
 S01 -P        berbalik dari kejutan ISM jasa bulan lalu. [DIKETAHUI SEBELUMNYA: pra_per_berita kejutan 65%, emas 2–10
               dtk 62% → diuji ulang dengan target lonjakan; dihitung PASCA-LIHAT]
 S02 -KON      tanda(K − V). [PASCA-LIHAT seperti M02]
 S03 FLASH_K   kejutan S&P Global FLASH Services PMI vs konsensusnya, searah.
 S04 FLASH_D   aturan _D, x = flash jasa − PMI jasa S&P final bulan lalu.
 S05 FINAL_R   revisi S&P Global FINAL Services PMI terhadap flash (09:45 ET hari yang sama / sebelumnya), searah.
 S06 MFG_K     kejutan ISM MANUFAKTUR bulan acuan yang sama (2 hari kerja sebelumnya), searah. Alasan: guncangan siklus
               bersama; konsensus jasa sering dikumpulkan sebelum ISM manufaktur terbit.
 S07 MFG_D     aturan _D, x = ISM manufaktur A − V bulan acuan.
 S08 REGS_D    aturan _D, x = rata-rata z(Δ) survei Fed daerah JASA bulan acuan: Philly nonmanufaktur
               (GARBNDIF066MSFRBPHI) & Dallas TSSOS (TSSOSBACTSAMFRBDAL) dari FRED rilis pertama, Richmond Services
               (kalender Nasdaq A − V); minimal 1 survei.
 S09 ADP_K     kejutan ADP pekan yang sama bila terbit sebelum t0 (08:15 ET), searah (ketenagakerjaan = 1 dari 4
               komponen ISM jasa).
 S10 MR6       seperti M12.
 S11 SEAS      seperti M13.
 S12 -P&MFG    -P hanya bila sepakat dengan MFG_K (selain itu 0).
 S13 VOTE_INFO tanda(FLASH_D + FINAL_R + MFG_D + REGS_D).
 S14 VOTE_ALL  tanda(-P + -KON + FLASH_D + FINAL_R + MFG_D + REGS_D).
 S15 REG_K     seperti M08 (survei Fed daerah MANUFAKTUR bulan acuan) — replikasi FED putaran 1 untuk jasa.

Info tambahan (bukan aturan keluarga; n terlalu kecil): Kalshi KXISMPMI (sejak Apr 2025) & KXUSISMSERV (2026).

Evaluasi (identik dengan CPI, research/lonjakan_uji): target utama = arah lonjakan terbesar 0–60 dtk (Exness, cadangan
Dukascopy); tutup kertas per tahun mulai 2013 (aturan dipakai di tahun Y hanya bila rilis < Y benar > 50%, n ≥ 10);
laporan 2016–2026, LAMA (2016..Sep 2021), BARU (≥ Okt 2021), 2022+, 2026, per tahun, pembanding "selalu naik", plafon
(kejutan sebenarnya), target kedua = arah detik 2/3/5/10. Permutasi keluarga 2.000× per jenis (M01–M15; S01–S15)
dan gabungan 30 aturan. LOLOS = tutup kertas ≥ 60% (2016–2026), > 50% di LAMA & BARU (n ≥ 8 masing-masing), p keluarga
< 0,05 (2016+ atau 2022+), ≥ 40 rilis ditebak sejak 2016, dan bisa dihitung LIVE sebelum rilis dari sumber yang bisa
dijangkau Vercel.
=== AKHIR PRA-REGISTRASI ===

=== TAMBAHAN PASCA-LIHAT (ditulis 11 Okt 2026 SETELAH putaran pertama 30 aturan di atas; semua masuk keluarga) ===
Temuan putaran pertama: semua aturan "_D" justru BERLAWANAN (angka 38–48%). Sebabnya rancangan: tanda(Δ̂ − (K − V))
didominasi suku −(K − V), padahal perubahan sebenarnya cenderung MELAMPAUI arah perubahan konsensus (-KON angka 53–58%)
— ekonom kurang bereaksi. Perbaikan yang secara ekonomi benar: regresi kejutan langsung. Aturan "_S": OLS walk-forward
(≥ 24 titik sebelumnya, intersep) kejutan e = A − K terhadap [x, K − V] → petunjuk = tanda(ê).
 M16 FLASH_S  x = flash − final bulan lalu     M17 CHI_S  x = Chicago A − V
 M18 REG_S    x = rata-rata z(Δ) Fed daerah     M19 NOG_S  x = New Orders lalu − PMI lalu
 S16 FLASH_S  x = flash jasa − final lalu       S17 MFG_S  x = ISM manufaktur A − V
 S18 REGS_S   x = rata-rata z(Δ) Fed daerah jasa
 S19 -P&REGK  -P hanya bila sepakat dengan REG_K (dipilih karena -P & REG_K dua yang tertinggi → data-snooping;
              hanya sah bila lolos permutasi keluarga yang memuat SEMUA aturan).
Aturan pra-registrasi dinilai dengan keluarga pra-registrasi (15 per jenis); aturan pasca-lihat dengan keluarga
diperluas (19 per jenis) & gabungan 38 aturan. Keduanya dilaporkan. Karena S19 DIBANGUN dari hasil, LOLOS-nya juga
mensyaratkan uji SADAR-SELEKSI (uji_seleksi): di tiap acakan diambil yang terbaik dari semua aturan + SEMUA pasangan
"sepakat" dua aturan tunggal (p < 0,05); nol "templat -P & X" ikut dilaporkan sebagai pembanding.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .lonjakan_uji import N_PERM, SPLIT, keluarga, pct, sk, tutup
from .riset_ism_data import DIR, fred_awal, kalender, target

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_ism.txt"
FITUR = DIR / "fitur.parquet"
HH = (2, 3, 5, 10)
MIN_OLS, MIN_SD = 24, 12

ATURAN_PRA = {
    "M": ["-P", "-KON", "FLASH_K", "FLASH_D", "FINAL_R", "CHI_K", "CHI_D", "REG_K", "REG_D", "REG_D+", "NOG", "MR6",
          "SEAS", "VOTE_INFO", "VOTE_ALL"],
    "S": ["-P", "-KON", "FLASH_K", "FLASH_D", "FINAL_R", "MFG_K", "MFG_D", "REGS_D", "ADP_K", "MR6", "SEAS", "-P&MFG",
          "VOTE_INFO", "VOTE_ALL", "REG_K"],
}
ATURAN_PL = {"M": ["FLASH_S", "CHI_S", "REG_S", "NOG_S"], "S": ["FLASH_S", "MFG_S", "REGS_S", "-P&REGK"]}
ATURAN = {j: ATURAN_PRA[j] + ATURAN_PL[j] for j in ATURAN_PRA}
KODE = {"M": {c: f"M{i + 1:02d}" for i, c in enumerate(ATURAN["M"])},
        "S": {c: f"S{i + 1:02d}" for i, c in enumerate(ATURAN["S"])}}
PASCA = {"M": {"-P", "-KON"} | set(ATURAN_PL["M"]), "S": {"-P", "-KON", "-P&MFG"} | set(ATURAN_PL["S"])}
NAMA = {"M": "ISM Manufaktur (ISM Manufacturing PMI)", "S": "ISM Jasa (ISM Services / Non-Manufacturing PMI)"}
LIVE = {
    "-P": "Nasdaq API: Act & konsensus ISM bulan lalu (GET api.nasdaq.com/api/calendar/economicevents?date=<tgl+1>)",
    "-KON": "Nasdaq API hari rilis: konsensus & 'previous' ISM",
    "FLASH_K": "Nasdaq API ±1 pekan sebelumnya: baris 'S&P Global ... PMI' (tanggal ≥ 14) Act vs konsensus",
    "FLASH_D": "Nasdaq API: flash S&P (Act − previous) + koefisien OLS tersimpan + konsensus ISM",
    "FINAL_R": "Nasdaq API hari rilis 09:45 ET: 'S&P Global ... PMI' final vs flash",
    "CHI_K": "Nasdaq API hari kerja terakhir bulan acuan: 'Chicago PMI' Act vs konsensus",
    "CHI_D": "Nasdaq API: Chicago PMI Act − previous + koefisien OLS",
    "REG_K": "Nasdaq API: Empire/Philly/Richmond/KC bulan acuan Act vs konsensus",
    "REG_D": "Nasdaq API (Empire, Philly, Richmond, KC Act − previous) + FRED API BACTSAMFRBDAL + koefisien OLS",
    "REG_D+": "seperti REG_D",
    "NOG": "Nasdaq API hari rilis: 'ISM Manufacturing New Orders Index' previous & PMI previous + koefisien OLS",
    "MR6": "Nasdaq API: 6 Act ISM terakhir (atau riwayat tersimpan) vs konsensus",
    "SEAS": "riwayat kejutan tersimpan (file JSON) per bulan kalender",
    "MFG_K": "Nasdaq API 2 hari kerja sebelumnya: ISM manufaktur Act vs konsensus",
    "MFG_D": "Nasdaq API: ISM manufaktur Act − previous + koefisien OLS",
    "REGS_D": "FRED API GARBNDIF066MSFRBPHI & TSSOSBACTSAMFRBDAL + Nasdaq 'Richmond Services Index' + koefisien OLS",
    "ADP_K": "Nasdaq API pekan rilis 08:15 ET: ADP Act vs konsensus",
    "-P&MFG": "Nasdaq API (lihat -P & MFG_K)",
    "VOTE_INFO": "gabungan komponen di atas", "VOTE_ALL": "gabungan komponen di atas",
    "FLASH_S": "seperti FLASH_D (koefisien OLS kejutan tersimpan)", "CHI_S": "seperti CHI_D", "REG_S": "seperti REG_D",
    "NOG_S": "seperti NOG", "MFG_S": "seperti MFG_D", "REGS_S": "seperti REGS_D", "-P&REGK": "Nasdaq API (-P & REG_K)",
}


def sg(v) -> float:
    return 0.0 if v is None or v != v or v == 0 else float(np.sign(v))


# ---------------------------------------------------------------- fitur
class Kal:
    def __init__(self) -> None:
        k = kalender()
        self.k = {key: g.sort_values("d").reset_index(drop=True) for key, g in k.groupby("key")}

    def bulan(self, key: str, ref: pd.Period, sebelum: pd.Timestamp, t0: pd.Timestamp, hari_sama: bool = False):
        """Baris terakhir judul `key` bertanggal di bulan acuan `ref` & terbit sebelum t0."""
        g = self.k.get(key)
        if g is None:
            return None
        x = g[(g.d.dt.to_period("M") == ref) & ((g.d < sebelum) | (hari_sama & (g.d == sebelum)))]
        x = x[x.t.isna() | (x.t < t0 - pd.Timedelta(seconds=1))]
        return x.iloc[-1] if len(x) else None

    def rentang(self, key: str, a: pd.Timestamp, b: pd.Timestamp, t0: pd.Timestamp):
        g = self.k.get(key)
        if g is None:
            return None
        x = g[(g.d >= a) & (g.d <= b)]
        x = x[x.t.isna() | (x.t < t0 - pd.Timedelta(seconds=1))]
        return x.iloc[-1] if len(x) else None


def _fred_delta(df: pd.DataFrame, ref: pd.Period, t0: pd.Timestamp) -> float:
    s = df[df.available < t0].value
    a, b = s.get(ref.to_timestamp(), np.nan), s.get((ref - 1).to_timestamp(), np.nan)
    return float(a - b) if a == a and b == b else np.nan


def bangun(segar: bool = False) -> pd.DataFrame:
    if FITUR.exists() and not segar:
        return pd.read_parquet(FITUR)
    K = Kal()
    tg = target()
    dal = fred_awal("BACTSAMFRBDAL")
    phn, tss = fred_awal("GARBNDIF066MSFRBPHI"), fred_awal("TSSOSBACTSAMFRBDAL")
    rows = []
    for x in tg.sort_values("t0").itertuples():
        key = "ISM_M" if x.jenis == "M" else "ISM_S"
        h = K.k[key]
        h = h[h.d == x.d].iloc[0]
        d, t0 = x.d, x.t0
        ref = d.to_period("M") - 1
        o = {"t0": t0, "d": d, "jenis": x.jenis, "A": h.a, "K": h.f, "V": h.p, "src": h.src, "ref": str(ref),
             "L": x.L, "besar": x.besar, "detik": x.detik, "ex_L": x.ex_L, "du_L": x.du_L, "sumber": x.sumber}
        for hh in HH:
            o[f"g{hh}"] = getattr(x, f"g{hh}")
        o["s"] = sg(round(h.a - h.f, 9)) if h.f == h.f and h.a == h.a else np.nan
        sfx = "M" if x.jenis == "M" else "S"
        fl = K.bulan(f"FLASH_{sfx}", ref, d, t0)
        o["flash_k"] = sg(fl.a - fl.f) if fl is not None and fl.f == fl.f else 0.0
        o["x_flash"] = fl.a - fl.p if fl is not None and fl.p == fl.p else np.nan
        fi = K.rentang(f"FINAL_{sfx}", ref.to_timestamp(how="end").normalize() + pd.Timedelta(days=1), d, t0)
        if fi is not None:
            acuan = fl.a if fl is not None else fi.f
            o["final_r"] = sg(round(fi.a - acuan, 9)) if acuan == acuan else 0.0
        else:
            o["final_r"] = 0.0
        if x.jenis == "M":
            ch = K.bulan("CHI", ref, d, t0)
            o["chi_k"] = sg(ch.a - ch.f) if ch is not None and ch.f == ch.f else 0.0
            o["x_chi"] = ch.a - ch.p if ch is not None and ch.p == ch.p else np.nan
            no = K.rentang("ISM_M_NO", d, d, t0 + pd.Timedelta(hours=1))        # 'previous' hari ini = bulan lalu
            o["x_nog"] = (no.p - h.p) if no is not None and no.p == no.p and h.p == h.p else np.nan
        # survei daerah manufaktur (bulan acuan)
        sk_, dz = [], {}
        for kk in ("EMP", "PHI", "RICH", "KC"):
            r = K.bulan(kk, ref, d, t0)
            if r is not None:
                if r.f == r.f:
                    sk_.append(sg(r.a - r.f))
                if r.p == r.p:
                    dz[kk] = r.a - r.p
        dv = _fred_delta(dal, ref, t0)
        if dv == dv:
            dz["DAL"] = dv
        o["reg_k"] = sg(sum(sk_)) if sk_ else 0.0
        for kk, v in dz.items():
            o[f"dz_{kk}"] = v
        if x.jenis == "S":
            for kk, df_ in (("PHN", phn), ("TSS", tss)):
                v = _fred_delta(df_, ref, t0)
                if v == v:
                    o[f"dz_{kk}"] = v
            r = K.bulan("RICH_S", ref, d, t0)
            if r is not None and r.p == r.p and r.a == r.a:
                o["dz_RIS"] = r.a - r.p
            m = K.rentang("ISM_M", d - pd.Timedelta(days=8), d - pd.Timedelta(days=1), t0)
            if m is not None and m.d.to_period("M") == d.to_period("M"):
                o["mfg_k"] = sg(round(m.a - m.f, 9)) if m.f == m.f else 0.0
                o["x_mfg"] = m.a - m.p if m.p == m.p else np.nan
            else:
                o["mfg_k"], o["x_mfg"] = 0.0, np.nan
            ad = K.rentang("ADP", d - pd.Timedelta(days=6), d, t0)
            o["adp_k"] = sg(ad.a - ad.f) if ad is not None and ad.f == ad.f else 0.0
        rows.append(o)
    df = pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)
    df.to_parquet(FITUR)
    return df


def _z(df: pd.DataFrame, cols: list[str], i: int, minimal: int) -> float:
    """Rata-rata z(Δ) survei untuk baris i; simpangan baku dari baris sebelumnya (≥ MIN_SD)."""
    zs = []
    for c in cols:
        if c not in df or df[c].iloc[i] != df[c].iloc[i]:
            continue
        lalu = df[c].iloc[:i].dropna()
        if len(lalu) >= MIN_SD and lalu.std() > 0:
            zs.append(df[c].iloc[i] / lalu.std())
    return float(np.mean(zs)) if len(zs) >= minimal else np.nan


def _ols_d(x: np.ndarray, dy: np.ndarray, kv: np.ndarray, ambang: float = 0.0) -> np.ndarray:
    """Aturan _D: OLS walk-forward ΔISM = a + b·x (≥ MIN_OLS titik sebelumnya) → tanda(Δ̂ − (K − V))."""
    out = np.zeros(len(x))
    for i in range(len(x)):
        if x[i] != x[i] or kv[i] != kv[i]:
            continue
        m = ~np.isnan(x[:i]) & ~np.isnan(dy[:i])
        if m.sum() < MIN_OLS:
            continue
        b, a = np.polyfit(x[:i][m], dy[:i][m], 1)
        e = a + b * x[i] - kv[i]
        out[i] = 0.0 if abs(e) < max(ambang, 1e-9) else np.sign(e)
    return out


def _ols_s(x: np.ndarray, e: np.ndarray, kv: np.ndarray) -> np.ndarray:
    """Aturan _S (pasca-lihat): OLS walk-forward kejutan e = A − K terhadap [x, K − V] (≥ MIN_OLS) → tanda(ê)."""
    out = np.zeros(len(x))
    for i in range(len(x)):
        if x[i] != x[i] or kv[i] != kv[i]:
            continue
        m = ~np.isnan(x[:i]) & ~np.isnan(e[:i]) & ~np.isnan(kv[:i])
        if m.sum() < MIN_OLS:
            continue
        X = np.c_[np.ones(m.sum()), x[:i][m], kv[:i][m]]
        b = np.linalg.lstsq(X, e[:i][m], rcond=None)[0]
        out[i] = sg(round(float(b[0] + b[1] * x[i] + b[2] * kv[i]), 9))
    return out


def petunjuk(df: pd.DataFrame) -> pd.DataFrame:
    """Kolom aturan (tebakan tanda kejutan ISM = arah USD) per jenis, sesuai pra-registrasi."""
    out = []
    for j, x in df.groupby("jenis"):
        x = x.sort_values("t0").reset_index(drop=True)
        n = len(x)
        dy = (x.A - x.V).to_numpy(float)
        kv = (x.K - x.V).to_numpy(float)
        s = x.s.fillna(0).to_numpy()
        c = {}
        dekat = (x.t0 - x.t0.shift(1)).dt.days.fillna(999).to_numpy() <= 45
        c["-P"] = np.where(dekat, -np.r_[0, s[:-1]], 0.0)
        c["-KON"] = np.sign(np.nan_to_num(kv))
        c["FLASH_K"] = x.flash_k.fillna(0).to_numpy()
        c["FLASH_D"] = _ols_d(x.x_flash.to_numpy(float), dy, kv)
        c["FINAL_R"] = x.final_r.fillna(0).to_numpy()
        e = (x.A - x.K).to_numpy(float)
        c["FLASH_S"] = _ols_s(x.x_flash.to_numpy(float), e, kv)
        mr, se = np.zeros(n), np.zeros(n)
        bl = x.d.dt.month.to_numpy()
        A = x.A.to_numpy(float)
        for i in range(n):
            if i >= 6 and not np.isnan(A[i - 6:i]).any() and x.K.iloc[i] == x.K.iloc[i]:
                mr[i] = sg(round(A[i - 6:i].mean() - x.K.iloc[i], 9))
            lalu = s[:i][(bl[:i] == bl[i]) & (s[:i] != 0)]
            if len(lalu) >= 4:
                se[i] = sg(lalu.mean())
        c["MR6"], c["SEAS"] = mr, se
        if j == "M":
            c["CHI_K"] = x.chi_k.fillna(0).to_numpy()
            c["CHI_D"] = _ols_d(x.x_chi.to_numpy(float), dy, kv)
            c["REG_K"] = x.reg_k.fillna(0).to_numpy()
            zr = np.array([_z(x, ["dz_EMP", "dz_PHI", "dz_RICH", "dz_KC", "dz_DAL"], i, 2) for i in range(n)])
            x["z_reg"] = zr
            c["REG_D"] = _ols_d(zr, dy, kv)
            c["REG_D+"] = _ols_d(zr, dy, kv, ambang=0.5)
            c["NOG"] = _ols_d(x.x_nog.to_numpy(float), dy, kv)
            c["CHI_S"] = _ols_s(x.x_chi.to_numpy(float), e, kv)
            c["REG_S"] = _ols_s(zr, e, kv)
            c["NOG_S"] = _ols_s(x.x_nog.to_numpy(float), e, kv)
            c["VOTE_INFO"] = np.sign(c["FLASH_D"] + c["FINAL_R"] + c["CHI_D"] + c["REG_D"])
            c["VOTE_ALL"] = np.sign(c["-P"] + c["-KON"] + c["FLASH_D"] + c["FINAL_R"] + c["CHI_D"] + c["REG_D"]
                                    + c["NOG"])
        else:
            c["MFG_K"] = x.mfg_k.fillna(0).to_numpy()
            c["MFG_D"] = _ols_d(x.x_mfg.to_numpy(float), dy, kv)
            zr = np.array([_z(x, ["dz_PHN", "dz_TSS", "dz_RIS"], i, 1) for i in range(n)])
            x["z_regs"] = zr
            c["REGS_D"] = _ols_d(zr, dy, kv)
            c["ADP_K"] = x.adp_k.fillna(0).to_numpy()
            c["-P&MFG"] = np.where((c["-P"] == c["MFG_K"]) & (c["-P"] != 0), c["-P"], 0.0)
            c["VOTE_INFO"] = np.sign(c["FLASH_D"] + c["FINAL_R"] + c["MFG_D"] + c["REGS_D"])
            c["VOTE_ALL"] = np.sign(c["-P"] + c["-KON"] + c["FLASH_D"] + c["FINAL_R"] + c["MFG_D"] + c["REGS_D"])
            c["REG_K"] = x.reg_k.fillna(0).to_numpy()
            c["MFG_S"] = _ols_s(x.x_mfg.to_numpy(float), e, kv)
            c["REGS_S"] = _ols_s(zr, e, kv)
            c["-P&REGK"] = np.where((c["-P"] == c["REG_K"]) & (c["-P"] != 0), c["-P"], 0.0)
        for k_, v in c.items():
            x[k_] = v
        out.append(x)
    return pd.concat(out).sort_values("t0").reset_index(drop=True)


# ---------------------------------------------------------------- evaluasi
def _periode(tb: np.ndarray, y: np.ndarray, t0: pd.Series, th: np.ndarray) -> dict:
    m = {"semua": th >= 2016, "LAMA": (th >= 2016) & (t0 < SPLIT).to_numpy(), "BARU": (t0 >= SPLIT).to_numpy(),
         "2022+": th >= 2022, "2026": th == 2026}
    return {k: sk(tb, y, v) for k, v in m.items()}


def _fmt(r: dict) -> str:
    return " | ".join(f"{k} {pct(*v)}" for k, v in r.items())


def _detik(tbs: dict, x: pd.DataFrame, th: np.ndarray) -> dict:
    """Target kedua: gabungan detik 2/3/5/10, aturan tutup kertas dihitung per target detik."""
    out = {"semua": [0, 0], "LAMA": [0, 0], "BARU": [0, 0]}
    for h in HH:
        y = x[f"g{h}"].fillna(0).to_numpy()
        r = _periode(tbs[h], y, x.t0, th)
        for k in out:
            out[k][0] += r[k][0]
            out[k][1] += r[k][1]
    return {k: tuple(v) for k, v in out.items()}


def keluarga_gabung(C: dict, Y: dict, TH: dict, rng) -> dict:
    """Permutasi gabungan semua aturan kedua jenis: hasil emas diacak DI DALAM jenisnya; dibanding aturan terbaik."""
    cukup = [(j, c) for j in C for c, v in C[j].items()
             if ((v != 0) & (TH[j] >= 2016)).sum() >= 40 and ((v != 0) & (TH[j] >= 2022)).sum() >= 20]

    def h(v, yy, m):
        g = -v
        ok = m & (g != 0) & (yy != 0)
        return (g[ok] == yy[ok]).mean() if ok.any() else np.nan
    obs = {(j, c): (h(C[j][c], Y[j], TH[j] >= 2016), h(C[j][c], Y[j], TH[j] >= 2022)) for j, c in cukup}
    m16, m22 = [], []
    for _ in range(N_PERM):
        yp = {j: Y[j][rng.permutation(len(Y[j]))] for j in Y}
        m16.append(np.nanmax([h(C[j][c], yp[j], TH[j] >= 2016) for j, c in cukup]))
        m22.append(np.nanmax([h(C[j][c], yp[j], TH[j] >= 2022) for j, c in cukup]))
    m16, m22 = np.array(m16), np.array(m22)
    return {k: (float((m16 >= o[0]).mean()), float((m22 >= o[1]).mean())) for k, o in obs.items()}


SELEKSI = {("S", "-P&REGK"): ("S", "-P&REG_K")}      # aturan gabungan pasca-lihat → kunci uji sadar-seleksi


def evaluasi(df: pd.DataFrame, rng, sel: dict | None = None) -> tuple[list[str], list[dict], dict]:
    """rng dipakai persis seperti putaran pertama untuk keluarga pra-registrasi (gabungan, lalu M, lalu S);
    keluarga diperluas (+ pasca-lihat) memakai rng tersendiri (seed 12)."""
    L, hasil = [], []
    C, CP, Y, TH = {}, {}, {}, {}
    for j in ("M", "S"):
        x = df[(df.jenis == j) & df.L.notna()].sort_values("t0").reset_index(drop=True)
        y, th = x.L.to_numpy(float), x.t0.dt.year.to_numpy()
        C[j] = {c: x[c].fillna(0).to_numpy() for c in ATURAN[j]}
        CP[j] = {c: C[j][c] for c in ATURAN_PRA[j]}
        Y[j], TH[j] = y, th
    kg_pra = keluarga_gabung(CP, Y, TH, rng)
    kel_pra = {j: keluarga(CP[j], Y[j], TH[j], rng) for j in ("M", "S")}
    rng2 = np.random.default_rng(12)
    kg = keluarga_gabung(C, Y, TH, rng2)
    kel_all = {j: keluarga(C[j], Y[j], TH[j], rng2) for j in ("M", "S")}
    for j in ("M", "S"):
        x = df[(df.jenis == j) & df.L.notna()].sort_values("t0").reset_index(drop=True)
        y, th, t0 = Y[j], TH[j], x.t0
        s = x.s.fillna(0).to_numpy()
        thn = sorted(set(th))
        L.append(f"\n## {NAMA[j]} — {len(x)} rilis bertarget {t0.min():%Y-%m}–{t0.max():%Y-%m}; lonjakan naik "
                 f"{(y > 0).sum() / max((y != 0).sum(), 1) * 100:.0f}%; rilis per tahun "
                 + " ".join(f"{Y_}:{(th == Y_).sum()}" for Y_ in thn))
        L.append("   selalu NAIK   " + _fmt(_periode(np.ones(len(x)), y, t0, th)))
        L.append("   PLAFON        " + _fmt(_periode(-s, y, t0, th)) + "   (emas = −kejutan sebenarnya)")
        L.append(f"   (permutasi keluarga {j}: pra-registrasi {len(kel_pra[j])}/{len(CP[j])} aturan cukup n, diperluas "
                 f"{len(kel_all[j])}/{len(C[j])}; {N_PERM}× acak)")
        L.append(f"   {'kode':4s} {'aturan':10s} {'angka':>14s} | tutup kertas lonjakan menit 1 → semua (2016–2026) | LAMA | "
                 "BARU | 2022+ | 2026 | p keluarga pra-reg 2016+/2022+ | p diperluas | p gabungan diperluas | "
                 "detik 2–10 (semua/LAMA/BARU)")
        for c in ATURAN[j]:
            v = C[j][c]
            ma = (v != 0) & (s != 0)
            ang = (int((v[ma] == s[ma]).sum()), int(ma.sum()))
            tb = tutup(v, y, th)
            r = _periode(tb, y, t0, th)
            tbs = {h: tutup(v, x[f"g{h}"].fillna(0).to_numpy(), th) for h in HH}
            dt = _detik(tbs, x, th)
            pp = kel_pra[j].get(c)
            pa = kel_all[j].get(c)
            pg = kg.get((j, c))
            p = pa if c in ATURAN_PL[j] else pp                     # p yang menentukan LOLOS
            (k, n), (kl, nl), (kb, nb) = r["semua"], r["LAMA"], r["BARU"]
            n_rilis = n
            ok = bool(n and k / n >= 0.6 and nl >= 8 and kl / nl > 0.5 and nb >= 8 and kb / nb > 0.5
                      and p and min(p[0], p[1]) < 0.05 and n_rilis >= 40)
            formal, ps = ok, None
            if (j, c) in SELEKSI and sel is not None:
                ps = sel.get(SELEKSI[(j, c)])
                ok = bool(formal and ps and min(ps) < 0.05)
            tag = (" [pasca-lihat]" if c in PASCA[j] else "") + ("  ✅ LOLOS" if ok else "") + (
                f"  ⚠️ lolos formal (keluarga diperluas) tetapi GAGAL uji sadar-seleksi semua pasangan p {ps[0]:.3f}/"
                f"{ps[1]:.3f}" if formal and not ok and ps else "")
            L.append(f"   {KODE[j][c]} {c:10s} {pct(*ang):>14s} | " + _fmt(r)
                     + (f" | p {pp[0]:.3f}/{pp[1]:.3f}" if pp else " | p –")
                     + (f" | pd {pa[0]:.3f}/{pa[1]:.3f}" if pa else " | pd –")
                     + (f" | pg {pg[0]:.3f}/{pg[1]:.3f}" if pg else " | pg –")
                     + " | dtk " + " / ".join(pct(*dt[k_]) for k_ in ("semua", "LAMA", "BARU")) + tag)
            per = {str(Y_): list(sk(tb, y, th == Y_)) for Y_ in range(2013, int(th.max()) + 1) if sk(tb, y, th == Y_)[1]}
            mentah = (keluarga_obs(v, y, th))
            hasil.append({"jenis": j, "kode": KODE[j][c], "aturan": c, "angka": ang, "r": r, "p": p, "p_pra": pp,
                          "p_diperluas": pa, "pg": pg, "pg_pra": kg_pra.get((j, c)), "dt": dt,
                          "per_tahun": per, "mentah": mentah, "lolos": ok, "lolos_formal": formal, "p_seleksi": ps,
                          "pasca": c in PASCA[j], "n_rilis": n_rilis})
        L.append("   per tahun (tutup kertas, benar/ditebak):")
        for hsl in [h_ for h_ in hasil if h_["jenis"] == j]:
            L.append(f"     {hsl['kode']} {hsl['aturan']:10s} " + " ".join(f"{k_[2:]}:{v_[0]}/{v_[1]}"
                                                                      for k_, v_ in hsl["per_tahun"].items()))
    return L, hasil, kg


GABUNGAN = {"-P&MFG", "-P&REGK", "VOTE_INFO", "VOTE_ALL"}


def uji_seleksi(df: pd.DataFrame, rng) -> tuple[list[str], dict]:
    """Permutasi SADAR-SELEKSI (pasca-lihat): S19 dibuat dari dua aturan tunggal teratas → nol = di setiap acakan
    diambil yang TERBAIK dari (a) semua aturan keluarga diperluas dan (b) SEMUA pasangan "sepakat" dua aturan tunggal
    (A bila A = B ≠ 0). Statistik = ketepatan mentah 2016+ (dan 2022+), syarat n sama dengan keluarga."""
    L = ["\n## Uji sadar-seleksi untuk aturan gabungan pasca-lihat (nol = terbaik dari semua aturan + semua pasangan)"]
    out = {}
    for j in ("M", "S"):
        x = df[(df.jenis == j) & df.L.notna()].sort_values("t0").reset_index(drop=True)
        y, th = x.L.to_numpy(float), x.t0.dt.year.to_numpy()
        tunggal = [c for c in ATURAN[j] if c not in GABUNGAN]
        V = {c: x[c].fillna(0).to_numpy() for c in ATURAN[j]}
        for a_ in range(len(tunggal)):
            for b_ in range(a_ + 1, len(tunggal)):
                A, B = V[tunggal[a_]], V[tunggal[b_]]
                V[f"{tunggal[a_]}&{tunggal[b_]}"] = np.where((A == B) & (A != 0), A, 0.0)
        s16, b22 = th >= 2016, th >= 2022
        cukup = [c for c, v in V.items() if ((v != 0) & s16).sum() >= 40 and ((v != 0) & b22).sum() >= 20]
        G = np.array([-V[c] for c in cukup])                       # tebakan emas, baris = aturan

        def hit(yy, m):
            ok = (G != 0) & (yy != 0)[None, :] & m[None, :]
            return np.where(ok.sum(1) > 0, ((G == yy[None, :]) & ok).sum(1) / np.maximum(ok.sum(1), 1), np.nan)
        o16, o22 = hit(y, s16), hit(y, b22)
        # nol "templat": hanya aturan keluarga + pasangan "-P & X" (cara S19 benar-benar dibuat: -P diketahui dari riset
        # sebelumnya, templat -P&MFG sudah pra-registrasi, X = aturan tunggal terbaik)
        tpl = np.array([("&" not in c) or c.startswith("-P&") or c.endswith("&-P") for c in cukup])
        m16, m22, t16, t22 = [], [], [], []
        for _ in range(N_PERM):
            yp = y[rng.permutation(len(y))]
            h16, h22 = hit(yp, s16), hit(yp, b22)
            m16.append(np.nanmax(h16))
            m22.append(np.nanmax(h22))
            t16.append(np.nanmax(h16[tpl]))
            t22.append(np.nanmax(h22[tpl]))
        m16, m22, t16, t22 = np.array(m16), np.array(m22), np.array(t16), np.array(t22)
        urut = np.argsort(-o16)[:5]
        L.append(f"   {NAMA[j]}: {len(cukup)} aturan+pasangan memenuhi n; acak terbaik persentil 95 "
                 f"{np.percentile(m16, 95) * 100:.1f}% (2016+) / {np.percentile(m22, 95) * 100:.1f}% (2022+)")
        for i in urut:
            p16, p22 = float((m16 >= o16[i]).mean()), float((m22 >= o22[i]).mean())
            L.append(f"     {cukup[i]:18s} mentah 2016+ {o16[i] * 100:.1f}% | 2022+ {o22[i] * 100:.1f}% → "
                     f"p sadar-seleksi {p16:.3f} / {p22:.3f}")
            out[(j, cukup[i])] = (p16, p22)
        for nm in ("-P&REG_K", "-P&MFG_K"):
            if nm in cukup:
                i = cukup.index(nm)
                p16, p22 = float((m16 >= o16[i]).mean()), float((m22 >= o22[i]).mean())
                q16, q22 = float((t16 >= o16[i]).mean()), float((t22 >= o22[i]).mean())
                out[(j, nm)] = (p16, p22)
                out[(j, nm, "templat")] = (q16, q22)
                L.append(f"     → {nm}: p sadar-seleksi SEMUA pasangan {p16:.3f} / {p22:.3f}; nol templat '-P & X' "
                         f"{q16:.3f} / {q22:.3f}")
    return L, out


def ketahanan(df: pd.DataFrame) -> list[str]:
    """Ketahanan S19 -P&REGK (pasca-lihat) & komponennya: feed, sumber konsensus, varian survei (tanpa memilih ulang)."""
    L = ["\n## Ketahanan S19 -P&REGK (hanya pemeriksaan; aturan tidak diubah)"]
    x = df[(df.jenis == "S") & df.L.notna()].sort_values("t0").reset_index(drop=True)
    th, t0 = x.t0.dt.year.to_numpy(), x.t0
    v = x["-P&REGK"].to_numpy()

    def satu(nama, y, vv=v):
        tb = tutup(vv, y, th)
        L.append(f"   {nama:34s} " + _fmt(_periode(tb, y, t0, th)))
    satu("target utama (Exness, cadangan Duka)", x.L.to_numpy(float))
    satu("feed Exness saja", x.ex_L.fillna(0).to_numpy())
    satu("feed Dukascopy saja", x.du_L.fillna(0).to_numpy())
    for h in HH:
        satu(f"arah detik {h}", x[f"g{h}"].fillna(0).to_numpy())
    m_nq = (x.src == "NQ").to_numpy()
    satu("hanya rilis berkonsensus Nasdaq", np.where(m_nq, x.L.to_numpy(float), 0))
    k, n = sk(-v, x.L.to_numpy(float), th >= 2016)
    L.append(f"   tanpa saringan tutup kertas (mentah) 2016+: {pct(k, n)}")
    L.append("   Live (bila kelak diuji maju): -P = Nasdaq API rilis ISM jasa bulan lalu (Act vs konsensus); REG_K = Nasdaq API")
    L.append("   Empire (±tgl 15), Philly (Kamis ke-3), Richmond (Selasa ke-4), KC (akhir bulan) bulan acuan, Act vs konsensus;")
    L.append("   semuanya terbit ≥ 4 hari sebelum ISM jasa (hari kerja ke-3, 10:00 ET).")
    return L


def keluarga_obs(v: np.ndarray, y: np.ndarray, th: np.ndarray) -> tuple:
    """Ketepatan mentah (tanpa saringan tahun lalu) 2016+ & 2022+ dan n."""
    out = []
    for m in (th >= 2016, th >= 2022):
        g = -v
        ok = m & (g != 0) & (y != 0)
        out.append((int((g[ok] == y[ok]).sum()), int(ok.sum())))
    return tuple(out)


def cakupan(df: pd.DataFrame) -> list[str]:
    L = ["\n## Cakupan petunjuk (rilis dengan petunjuk ≠ 0, per tahun)"]
    for j in ("M", "S"):
        x = df[df.jenis == j]
        th = x.t0.dt.year
        L.append(f"   {NAMA[j]}")
        for c in ATURAN[j]:
            n = (x[c] != 0).groupby(th).sum()
            L.append(f"     {KODE[j][c]} {c:10s} " + " ".join(f"{int(k) % 100:02d}:{int(v)}" for k, v in n.items()))
    return L


def kalshi_info(df: pd.DataFrame) -> list[str]:
    """Info tambahan: Kalshi KXISMPMI (manufaktur, strike bulat "at least X") & KXUSISMSERV (jasa, "above X"):
    peluang di atas / di bawah konsensus 1 jam sebelum pasar tutup (interpolasi linear antar strike)."""
    import re

    from .kalshi_uji import p_above, prob_at
    bln = {b: i + 1 for i, b in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                           "Nov", "Dec"])}
    L = ["\n## Info tambahan: Kalshi (bukan aturan keluarga; n kecil, pasar tipis)"]
    for j, seri in (("M", "KXISMPMI"), ("S", "KXUSISMSERV")):
        x = df[df.jenis == j].set_index("ref")
        rows = []
        for f in sorted((DIR / "kalshi" / seri).glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            mm = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{4})", d.get("judul") or "")
            if not mm:
                continue
            ref = f"{mm.group(2)}-{bln[mm.group(1)]:02d}"
            if ref not in x.index:
                continue
            r = x.loc[ref]
            ms = d["pasar"]
            close = min(pd.Timestamp(m["tutup"]) for m in ms)
            ts = (close - pd.Timedelta(hours=1)).timestamp()
            pts = sorted((float(m["strike"]), prob_at(m, ts)) for m in ms
                         if m.get("strike") is not None and prob_at(m, ts) is not None)
            if r.K != r.K or len(pts) < 2:
                continue
            up, lo = p_above(pts, r.K + 0.05), p_above(pts, r.K - 0.05)
            if up is None or lo is None:
                continue
            bawah = 1 - lo
            tebak = sg(up - bawah) if abs(up - bawah) >= 0.10 else 0.0
            rows.append((r.d, tebak, r.s, r.L, round(up, 2), round(bawah, 2)))
        if not rows:
            L.append(f"   {seri}: tidak ada event yang cocok")
            continue
        t = pd.DataFrame(rows, columns=["d", "tebak", "s", "L", "p_atas", "p_bawah"])
        m = (t.tebak != 0) & (t.s != 0)
        mg = (t.tebak != 0) & t.L.notna() & (t.L != 0)
        L.append(f"   {seri}: {len(t)} rilis {t.d.min():%Y-%m}–{t.d.max():%Y-%m}; tebakan (selisih ≥ 10 poin) angka "
                 f"{pct(int((t.tebak[m] == t.s[m]).sum()), int(m.sum()))}, emas lonjakan "
                 f"{pct(int((-t.tebak[mg] == t.L[mg]).sum()), int(mg.sum()))}")
        for rr in t.itertuples():
            L.append(f"     {rr.d:%Y-%m-%d} P(atas) {rr.p_atas:.2f} P(bawah) {rr.p_bawah:.2f} tebak {rr.tebak:+.0f} "
                     f"kejutan {rr.s:+.0f} lonjakan " + (f"{rr.L:+.0f}" if rr.L == rr.L else "–"))
    return L


def mutu(df: pd.DataFrame) -> list[str]:
    """Catatan mutu data: sumber konsensus, sumber target, kesepakatan feed."""
    L = ["\n## Mutu data"]
    for j in ("M", "S"):
        x = df[df.jenis == j]
        L.append(f"   {NAMA[j]}: {len(x)} rilis di kalender; konsensus dari {x.src.value_counts().to_dict()}; "
                 f"target {x.sumber.value_counts().to_dict()}; kejutan 0 (Act = konsensus) {int((x.s == 0).sum())}")
        b = x[x.ex_L.notna() & x.du_L.notna()]
        if len(b):
            L.append(f"     arah lonjakan Exness = Dukascopy: {pct(int((b.ex_L == b.du_L).sum()), len(b))}")
    # kesepakatan tanda kejutan Nasdaq vs ForexFactory (konsensus berbeda tipis)
    from .riset_ism_data import _ff
    ff = _ff()
    for j, key in (("M", "ISM_M"), ("S", "ISM_S")):
        a = df[(df.jenis == j) & (df.src == "NQ")].merge(ff[ff.key == key][["d", "a", "f"]], on="d", how="inner")
        sf = np.sign((a.a - a.f).round(9))
        m = a.s.notna() & sf.notna()
        L.append(f"   {key}: tanda kejutan Nasdaq = ForexFactory pada {pct(int((a.s[m] == sf[m]).sum()), int(m.sum()))}")
    return L


def kesimpulan(hasil: list[dict], sel: dict) -> list[str]:
    H = {(h["jenis"], h["aturan"]): h for h in hasil}

    def ring(j, c):
        h = H[(j, c)]
        r = h["r"]
        return (f"{pct(*r['semua']).strip()} (LAMA {pct(*r['LAMA']).strip()}, BARU {pct(*r['BARU']).strip()}, "
                f"2026 {pct(*r['2026']).strip()})")
    s19, tp = H[("S", "-P&REGK")], sel.get(("S", "-P&REG_K", "templat"), (np.nan, np.nan))
    ps = s19["p_seleksi"] or (np.nan, np.nan)
    pd_ = s19["p_diperluas"] or (np.nan, np.nan)
    return [
        "\n## Kesimpulan (jujur)",
        "1. ISM MANUFAKTUR: tidak ada petunjuk yang bekerja. Flash S&P, final S&P 09:45, Chicago PMI, survei Fed daerah,",
        "   New Orders, musiman, pembalikan: 36–54% tutup kertas (n ≥ 40), atau 62–64% hanya pada n 28–34 sejak 2024",
        "   (CHI_D, VOTE_INFO; p 0,94/0,18–0,99/0,40), VOTE_ALL 57% (LAMA 47%). Tebakan ANGKA kejutan pun 40–54%.",
        "   Aturan '_D' (perubahan tersirat vs perubahan konsensus) malah berlawanan karena ekonom KURANG bereaksi",
        "   (angka melampaui arah perubahan konsensus); versi perbaikan '_S' (regresi kejutan) juga gagal.",
        f"2. ISM JASA, aturan pra-registrasi terbaik: S15 REG_K {ring('S', 'REG_K')}, p keluarga "
        f"{H[('S', 'REG_K')]['p'][0]:.2f}/{H[('S', 'REG_K')]['p'][1]:.2f}; S12 -P&MFG {ring('S', '-P&MFG')}, p "
        f"{H[('S', '-P&MFG')]['p'][0]:.2f}/{H[('S', '-P&MFG')]['p'][1]:.2f}; S01 -P {ring('S', '-P')} → TIDAK lolos.",
        f"3. S19 -P&REGK (PASCA-LIHAT: berbalik dari kejutan ISM jasa bulan lalu DAN survei Fed daerah manufaktur bulan",
        f"   acuan sepakat): {ring('S', '-P&REGK')}, n {s19['n_rilis']} rilis, keluarga diperluas p {pd_[0]:.3f}/{pd_[1]:.3f},",
        f"   nol templat '-P & X' p {tp[0]:.3f}/{tp[1]:.3f}, tetapi uji sadar-seleksi SEMUA pasangan p {ps[0]:.3f}/{ps[1]:.3f}",
        "   (≥ 0,05) dan 2026 hanya 3/7. Secara mekanisme masuk akal (dua sinyal lemah ±61% yang independen → saat sepakat",
        "   ±71%), tetapi DITEMUKAN SETELAH MELIHAT DATA → BELUM TERBUKTI. Saran: uji maju (catat tiap rilis ISM jasa) tanpa",
        "   dipasang di aplikasi sampai ≥ 12 rilis baru ≥ 65%.",
        "4. Kalshi ISM: n 10–12 (sejak Apr 2025), pasar tipis → belum bisa dinilai.",
        "5. Temuan data: file ForexFactory spoluan memuat baris Januari tahun berikutnya bertanda tahun berjalan (contoh",
        "   '2023-01-03 ISM 47,4' = 3 Jan 2024) dan Nasdaq kadang mundur 1 hari (2019-07-31, 2025-09-01, 2026-01-06) —",
        "   diperbaiki di research/riset_ism_data.kalender; lonjakan60 memuat satu baris ISM palsu (2016-01-05 15:00 UTC).",
    ]


def main() -> None:
    rng = np.random.default_rng(11)
    df = petunjuk(bangun(segar=True))
    L = ["# 🏭 ISM manufaktur & jasa → arah lonjakan emas menit pertama (tutup kertas + permutasi keluarga)",
         "Dibuat oleh `python -m research.riset_ism` (11 Okt 2026). Pra-registrasi lengkap = docstring research/riset_ism.py.",
         "Format sel: persen benar (benar/ditebak). 'angka' = tebakan TANDA KEJUTAN ISM (tanpa saringan tahun lalu);",
         "tutup kertas = tahun Y hanya memakai aturan bila rilis sebelum Y benar > 50% (n ≥ 10); tebakan emas = −petunjuk.",
         "p = permutasi keluarga pra-registrasi per jenis (15 aturan; terbaik acakan, 2.000×); pd = keluarga diperluas",
         "(+ 4 aturan pasca-lihat per jenis = 19); pg = gabungan diperluas 38 aturan kedua jenis. LOLOS memakai p untuk",
         "aturan pra-registrasi, pd untuk aturan pasca-lihat, dan untuk gabungan pasca-lihat (S19) juga p sadar-seleksi.",
         "Rilis 2010–2015 bertarget sedikit (tick hanya 10–11 rilis per jenis; unduhan Dukascopy ±60 dtk/file terlalu lambat)",
         "→ syarat tutup kertas (≥ 10 tebakan sebelumnya) membuat kebanyakan aturan baru dipakai mulai 2016–2018.",
         "detik 2–10 = target kedua (arah mid t0−1 → t0+2/3/5/10 dtk, dijumlah keempatnya)."]
    L += mutu(df)
    L += cakupan(df)
    S, sel = uji_seleksi(df, np.random.default_rng(13))
    E, hasil, _kg = evaluasi(df, rng, sel)
    L += E
    L += S
    L += ketahanan(df)
    L += kalshi_info(df)
    L += kesimpulan(hasil, sel)
    lolos = [h for h in hasil if h["lolos"]]
    L.append("\n## LOLOS (semua kriteria): " + (", ".join(f"{h['kode']} {h['aturan']}" for h in lolos) or "TIDAK ADA"))
    terbaik = sorted(hasil, key=lambda h: -(h["r"]["semua"][0] / h["r"]["semua"][1] if h["r"]["semua"][1] else 0))[:6]
    L.append("   Teratas menurut tutup kertas 2016–2026: " + "; ".join(
        f"{h['kode']} {h['aturan']} {pct(*h['r']['semua'])} (p {h['p'][0]:.2f}/{h['p'][1]:.2f})" if h["p"] else
        f"{h['kode']} {h['aturan']} {pct(*h['r']['semua'])} (p –)" for h in terbaik))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    (DIR / "hasil.json").write_text(json.dumps(hasil, ensure_ascii=False, default=str, indent=0), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
