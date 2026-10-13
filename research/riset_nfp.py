"""🧑‍💼 Riset NFP mendalam: petunjuk SEBELUM rilis → arah LONJAKAN TERBESAR MENIT PERTAMA emas (tutup kertas + permutasi).

python -m research.riset_nfp            → docs/eksternal/hasil_riset_nfp.txt (+ cache data/research/eksternal/riset_nfp.pkl)

Permintaan pengguna 11 Okt 2026: "setelah data konsensus dan lain-lain ada, otomatis persentase berubah di apk? Jika iya
terapkan juga news lain dengan pengujian, riset, validasi; jika persentase tinggi pasang". Putaran pertama NFP (ADP, klaim
4 pekan, ISM ketenagakerjaan, Kalshi, P/P3/KON — research/berita_detik.py) GAGAL. Putaran ini memakai sumber & definisi baru.

PRA-REGISTRASI (ditulis 11 Okt 2026 SEBELUM evaluasi apa pun dijalankan; tidak ada aturan yang ditambah setelah melihat hasil
kecuali ditandai "pasca-lihat"). Bulan acuan M = bulan terakhir yang pertama kali terbit pada tanggal rilis (ALFRED PAYEMS;
rilis tertunda 2025 tetap benar). Nilai "diketahui sebelum rilis" = vintage ALFRED yang berlaku H−1 (tanggal New York) atau
baris kalender Nasdaq yang terbit pada tanggal < tanggal NFP (Challenger 07:30 ET boleh hari yang sama). Semua petunjuk
disimpan dalam ARAH "BAIK UNTUK USD" (+1) → tebakan emas = kebalikannya. Nol = tidak menebak.

A. Angka utama NFP (tebakan kejutan payrolls; USD = +tebakan)
  1  ADPG    ADP bulan M (terbit < H) − konsensus payrolls SWASTA Nasdaq (cadangan: konsensus utama) → tanda.
             Alasan: ADP = ukuran independen ketenagakerjaan swasta; bila ADP di atas yang diharapkan ekonom untuk swasta BLS,
             BLS cenderung di atas. Harapan +.
  2  ADPG50  idem, hanya bila |selisih| ≥ 50 rb (varian peredam derau).
  3  KLSW    klaim awal pekan survei (pekan Minggu–Sabtu yang memuat tgl 12) bulan M vs pekan survei bulan M−1 (nilai rilis
             pertama): turun → payrolls kuat (+). Alasan: klaim pekan survei = PHK pada pekan yang diukur BLS.
  4  KL4SW   idem dengan rata-rata 4 pekan klaim awal (varian lebih halus).
  5  ISMJ    indeks ketenagakerjaan ISM JASA (Act − sebelumnya) bulan M, terbit pada tanggal < H → naik = +.
  6  ISM2    tanda (Δ ketenagakerjaan ISM manufaktur + Δ ISM jasa), yang sudah terbit < H.
  7  PHIL    Philly Fed Employment bulan M (terbit pekan ke-3 bulan M) Act − sebelumnya → naik = +.
  8  CHAL    Challenger job cuts bulan M, perubahan y/y (%) > 0 → PHK naik → payrolls lemah (−); < 0 → +.
  9  IND     indeks lowongan Indeed (SA) tgl ≤ 12 bulan M vs tgl ≤ 12 bulan M−1 (terbit +7 hari) → naik = +.
 10  REV     revisi bersih 2 bulan pada rilis NFP SEBELUMNYA (ALFRED PAYEMS) → positif = + (revisi berautokorelasi; revisi
             rilis ini ikut terlihat pasar).
 11  FFNQ    perkiraan ForexFactory − konsensus Nasdaq (|selisih| ≥ 5 rb) → FF lebih tinggi = + (konsensus yang lebih
             baru/“bisikan” lebih tinggi).
 12  KON3    rata-rata perubahan payrolls 3 bulan terakhir (vintage H−1) − konsensus → konsensus di bawah tren = + .
B. Tingkat pengangguran (tebakan kejutan UR; USD = −tebakan)
 13  URU     UR tanpa pembulatan bulan M−1 = UNEMPLOY/CLF16OV (vintage H−1) − konsensus UR; |selisih| ≥ 0,02 → tanda.
             Alasan mekanis: UR acak-berjalan; bila angka tanpa pembulatan sudah dekat batas pembulatan atas, peluang dibulatkan
             ke atas konsensus lebih besar. Harapan: selisih + → UR di atas → USD −.
 14  URU0    idem tanpa ambang (varian).
 15  KLLSW   klaim LANJUTAN pekan survei bulan M vs pekan survei M−1: naik → UR di atas → USD −.
 16  PK5U    5 pekan antar pekan survei (bukan 4) → UR di atas → USD − (aturan lama research/pra_per_berita, arah dari studi
             itu; sudah pernah diuji dengan target 2–10 dtk — dicatat, bukan petunjuk baru).
C. Upah per jam (AHE m/m; USD = +tebakan)
 17  AHEM    konsistensi y/y tanpa pembulatan (seperti CPI YOY): m/m tersirat = (1+konsensus y/y)·L(M−12)/L(M−1) − 1 dari
             CES0500000003 vintage H−1; tersirat − konsensus m/m ≥ +0,05 → m/m di atas (+), ≤ −0,05 → di bawah (−).
             Alasan: kedua konsensus dibulatkan 0,1; irisan keduanya menunjukkan harapan m/m tanpa pembulatan berada di sisi
             atas/bawah konsensusnya. Hanya 2018+ (konsensus y/y Nasdaq).
 18  AHEY    kebalikan yang sama untuk y/y: y/y tersirat = L(M−1)·(1+konsensus m/m)/L(M−12) − 1; − konsensus y/y ≥ +0,05 →
             y/y di atas (+). (Hampir selalu = −AHEM; dua-duanya dihitung karena pasar bisa membaca m/m atau y/y.)
 19  K12A    tgl 12 bulan M jatuh Minggu–Rabu (tgl 15 masuk pekan survei) → AHE di atas (+), selain itu (−). Aturan lama
             research/pra_per_berita (sudah pernah diuji untuk angka/2–10 dtk) — dicatat.
D. Gabungan (ditetapkan sebelum melihat hasil; bobot seperti plafon NFP 2 : UR 1 : AHE 1)
 20  KOMP    tanda(2·ADPG + URU + AHEM)   (nilai arah USD)
 21  RND     tanda(URU + AHEM)            (dua petunjuk mekanis pembulatan)
 22  SUARA   tanda(jumlah ADPG, KLSW, ISM2, PHIL, CHAL, IND, REV, FFNQ, KON3, URU, KLLSW, PK5U, AHEM, K12A)
E. PASCA-LIHAT (ditambah 11 Okt 2026 SETELAH melihat hasil 22 aturan di atas — 0 lolos, terbaik KLLSW 58,5% p 0,54; tetap
   dimasukkan ke keluarga yang sama, jadi p-nya ikut dihukum):
 23  KOLEKSI masa pengumpulan data BLS: jumlah Jumat sesudah pekan survei s/d hari rilis = 2 (pendek, tingkat respons
             awal rendah) → payrolls di bawah (−); ≥ 4 (panjang) → (+); 3 (normal) → tidak menebak. Alasan dari literatur
             analis (cetak awal bulan pengumpulan pendek cenderung lemah & direvisi naik).
 24  MODEL   regresi logistik walk-forward (tahun Y dilatih hanya rilis < Y, ≥ 30 rilis) memakai 14 petunjuk SUARA sebagai
             fitur, target arah lonjakan. CATATAN: permutasi keluarga tidak melatih ulang model → p MODEL terlalu optimistis.
 25  UR2     tanda(KLLSW + PK5U) — gabungan dua petunjuk UR yang "terbaik" di hasil putaran ini (DATA-MINING, pasca-lihat).
Total keluarga = 25 aturan (22 pra-registrasi + 3 pasca-lihat; semua ikut uji permutasi bila cukup rilis). Tidak diuji: Conference Board "jobs plentiful −
hard to get" (berlisensi, tidak ada di Nasdaq/FRED), NFIB rencana rekrut (tidak ada di kalender), Kalshi/Polymarket (sejak
2023 → < 40 rilis; putaran pertama KAL/KALUR), ADP mingguan & Revelio (sejak 2025).

TARGET utama: arah lonjakan terbesar 0–60 dtk (research/lonjakan.py; Exness, cadangan Dukascopy). Sekunder: arah t0+2/3/5/10
dtk (pra_xau_semua_v2, Exness → Dukascopy). Evaluasi: research/lonjakan_uji.tutup (tahun Y dipakai bila tahun-tahun lalu
> 50% n ≥ 10), permutasi keluarga 2.000× (lonjakan_uji.keluarga). LOLOS = tutup kertas ≥ 60% 2016–2026, > 50% LAMA & BARU
(n ≥ 8 masing-masing), p keluarga < 0,05 (2016+ atau 2022+), ≥ 40 rilis ditebak sejak 2016, dan bisa dihitung LIVE.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .berita_detik import us
from .lonjakan_uji import N_PERM, SPLIT, keluarga, sk, tutup
from .nasdaq_kalender import DIR as NQ_DIR
from .nasdaq_kalender import angka

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_nfp.txt"
CACHE = EKS / "riset_nfp.pkl"
HH = (2, 3, 5, 10)

GRUP_A = ["ADPG", "ADPG50", "KLSW", "KL4SW", "ISMJ", "ISM2", "PHIL", "CHAL", "IND", "REV", "FFNQ", "KON3"]
GRUP_B = ["URU", "URU0", "KLLSW", "PK5U"]
GRUP_C = ["AHEM", "AHEY", "K12A"]
GRUP_D = ["KOMP", "RND", "SUARA"]
GRUP_E = ["KOLEKSI", "MODEL", "UR2"]                      # pasca-lihat
ATURAN = GRUP_A + GRUP_B + GRUP_C + GRUP_D + GRUP_E
SUARA_IKUT = ["ADPG", "KLSW", "ISM2", "PHIL", "CHAL", "IND", "REV", "FFNQ", "KON3", "URU", "KLLSW", "PK5U", "AHEM", "K12A"]
LIVE = {
    "ADPG": "Nasdaq API: baris 'ADP Nonfarm Employment Change' (Rabu) + konsensus 'Private Nonfarm Payrolls' hari NFP",
    "ADPG50": "idem ADPG",
    "KLSW": "FRED API ICSA (atau Nasdaq API 'Initial Jobless Claims'): pekan survei bulan ini & bulan lalu",
    "KL4SW": "FRED API ICSA: rata 4 pekan s/d pekan survei",
    "ISMJ": "Nasdaq API 'ISM Non-Manufacturing Employment'",
    "ISM2": "Nasdaq API 'ISM Manufacturing Employment' + 'ISM Non-Manufacturing Employment'",
    "PHIL": "Nasdaq API 'Philly Fed Employment'",
    "CHAL": "Nasdaq API 'Challenger Job Cuts' (baris %)",
    "IND": "CSV Indeed Hiring Lab di GitHub (raw.githubusercontent.com)",
    "REV": "FRED API PAYEMS dengan realtime_start/realtime_end (vintage ALFRED)",
    "FFNQ": "JSON mingguan ForexFactory (nfs.faireconomy.media) + Nasdaq API",
    "KON3": "FRED API PAYEMS (nilai terbaru) + konsensus Nasdaq",
    "URU": "FRED API UNEMPLOY & CLF16OV (nilai terbaru) + konsensus UR Nasdaq",
    "URU0": "idem URU",
    "KLLSW": "FRED API CCSA (atau Nasdaq API 'Continuing Jobless Claims'): pekan survei",
    "PK5U": "kalender (tanggal saja)",
    "AHEM": "FRED API CES0500000003 + konsensus AHE m/m & y/y Nasdaq",
    "AHEY": "idem AHEM",
    "K12A": "kalender (tanggal saja)",
    "KOMP": "gabungan ADPG + URU + AHEM", "RND": "gabungan URU + AHEM", "SUARA": "gabungan 14 petunjuk",
    "KOLEKSI": "kalender (tanggal saja)", "MODEL": "gabungan 14 petunjuk + koefisien tersimpan",
    "UR2": "FRED CCSA + kalender",
}


def sg(v: float, batas: float = 0.0) -> float:
    return float(np.sign(v)) if v == v and v != 0 and abs(v) >= batas else 0.0


# ───────────────────────────── data ─────────────────────────────
@lru_cache(maxsize=None)
def kumpul() -> dict[str, list[tuple[pd.Timestamp, dict]]]:
    """Semua baris kalender Nasdaq (AS) untuk judul yang dibutuhkan → {judul: [(tanggal NY, baris), ...]}."""
    nama = {"ADP Nonfarm Employment Change", "ISM Manufacturing Employment", "ISM Non-Manufacturing Employment",
            "Philly Fed Employment", "Challenger Job Cuts"}
    out: dict = {n: [] for n in nama}
    for f in sorted(NQ_DIR.glob("*.json")):
        d = pd.Timestamp(f.stem)
        for r in us(d):
            if r["eventName"] in nama:
                out[r["eventName"]].append((d, r))
    return out


def nq(d, nama: str, pilih=None) -> tuple[float, float, float] | None:
    """(Act, konsensus, sebelumnya) baris pertama judul `nama` pada tanggal d (pilih: filter tambahan atas baris)."""
    for r in us(d):
        if r["eventName"] == nama and (pilih is None or pilih(r)):
            return angka(r["actual"]), angka(r["consensus"]), angka(r["previous"])
    return None


def acuan(d: pd.Timestamp, geser: int = 12) -> pd.Timestamp:
    """Bulan acuan rilis bulanan yang terbit ±awal bulan berikutnya (tanggal rilis − 12 hari)."""
    return (d - pd.Timedelta(days=geser)).to_period("M").to_timestamp()


def cari(nama: str, M: pd.Timestamp, sebelum: pd.Timestamp, bulan_rilis: bool = False, boleh_sama: bool = False):
    """Baris terakhir judul `nama` untuk bulan acuan M yang terbit sebelum `sebelum`."""
    hasil = None
    for d, r in kumpul()[nama]:
        if d > sebelum or (d == sebelum and not boleh_sama):
            continue
        ref = d.to_period("M").to_timestamp() if bulan_rilis else acuan(d)
        if ref == M:
            hasil = (d, r)
    return hasil


def sabtu_survei(M: pd.Timestamp) -> pd.Timestamp:
    d12 = M + pd.Timedelta(days=11)
    return d12 + pd.Timedelta(days=(5 - d12.weekday()) % 7)


def alfred(sid: str) -> pd.DataFrame:
    from .nfp_mean import fred
    return fred(sid)


def asof(d: pd.DataFrame, obs: pd.Timestamp, when: pd.Timestamp) -> float:
    """Nilai observasi `obs` menurut vintage ALFRED yang berlaku pada tanggal `when` (realtime_end INKLUSIF)."""
    x = d[(d.date == obs) & (d.rs <= when) & (d.re >= when)]
    return float(x.value.iloc[0]) if len(x) else np.nan


@lru_cache(maxsize=None)
def rilis_pertama(sid: str) -> pd.DataFrame:
    """Nilai rilis pertama + tanggal terbit per observasi (ALFRED) — dipakai untuk klaim mingguan ICSA/CCSA."""
    d = alfred(sid)
    return d.loc[d.groupby("date").rs.idxmin()].set_index("date")[["value", "rs"]]


@lru_cache(maxsize=None)
def peta_acuan() -> dict:
    p = alfred("PAYEMS")
    first = p.groupby("date").rs.min()
    return first.reset_index().groupby("rs").date.max().to_dict()


def ff_nfp() -> pd.DataFrame:
    from .news_prediksi import calendar
    c = calendar()
    return c[c.event == "Non-Farm Employment Change"][["time", "f"]].reset_index(drop=True)


def indeed_df() -> pd.DataFrame:
    from .sumber_lain import indeed
    return indeed()


def tabel(segar: bool = False) -> pd.DataFrame:
    if CACHE.exists() and not segar:
        return pd.read_pickle(CACHE)
    from .berita_detik import rilis as rilis_detik
    from .lonjakan import tabel as lj_tabel
    lj = lj_tabel()
    lj = lj[lj.grup == "NFP"][["t0", "arah", "ex_arah", "du_arah", "detik", "besar"]].copy()
    det = rilis_detik()
    det = det[det.grup == "NFP"][["t0"] + [f"g{h}" for h in HH] + [f"ex{h}" for h in HH] + [f"du{h}" for h in HH]]
    df = lj.merge(det, on="t0", how="left")
    peta, P, U, CL, AH = peta_acuan(), alfred("PAYEMS"), alfred("UNEMPLOY"), alfred("CLF16OV"), alfred("CES0500000003")
    UR = alfred("UNRATE")
    ind, ff = indeed_df(), ff_nfp()
    rows = []
    for r in df.itertuples():
        t0 = r.t0
        d = t0.tz_convert("America/New_York").normalize().tz_localize(None)
        o = {"t0": t0, "d": d}
        nfp = nq(d, "Nonfarm Payrolls")
        if nfp is None or nfp[1] != nfp[1]:
            rows.append(o)
            continue
        M = peta.get(d, (d.to_period("M") - 1).to_timestamp())
        M1 = (M.to_period("M") - 1).to_timestamp()
        h1 = d - pd.Timedelta(days=1)                                       # vintage yang berlaku sebelum hari rilis
        o.update(M=M, nfp_a=nfp[0] / 1e3, nfp_f=nfp[1] / 1e3)
        ur = nq(d, "Unemployment Rate")
        ahe = nq(d, "Average Hourly Earnings", lambda x: (angka(x["consensus"]) == angka(x["consensus"]) and
                                                         abs(angka(x["consensus"])) < 1.5))
        ahey = nq(d, "Average Hourly Earnings (YoY)")
        prv = nq(d, "Private Nonfarm Payrolls")
        o["s_nfp"] = sg(round(nfp[0] - nfp[1], 6))
        o["s_ur"] = sg(round(ur[0] - ur[1], 6)) if ur and ur[1] == ur[1] else 0.0
        o["s_ahe"] = sg(round(ahe[0] - ahe[1], 6)) if ahe and ahe[1] == ahe[1] else 0.0
        o["s_ahey"] = sg(round(ahey[0] - ahey[1], 6)) if ahey and ahey[1] == ahey[1] else 0.0
        o["PLAFON"] = sg(2 * o["s_nfp"] - o["s_ur"] + o["s_ahe"])          # arah USD dari kejutan sebenarnya
        c = {}
        # 1–2 ADP vs konsensus payrolls swasta
        a = cari("ADP Nonfarm Employment Change", M, d)
        kons_sw = prv[1] / 1e3 if prv and prv[1] == prv[1] else nfp[1] / 1e3
        if a:
            gap = angka(a[1]["actual"]) / 1e3 - kons_sw
            o["adp_gap"] = gap
            c["ADPG"], c["ADPG50"] = sg(gap), sg(gap, 50)
        # 3–4, 15 klaim pekan survei
        s0, s1 = sabtu_survei(M), sabtu_survei(M1)
        for sid, nama, lebar in (("ICSA", "KLSW", 1), ("ICSA", "KL4SW", 4), ("CCSA", "KLLSW", 1)):
            f_ = rilis_pertama(sid)
            pk0 = [s0 - pd.Timedelta(weeks=k) for k in range(lebar)]
            pk1 = [s1 - pd.Timedelta(weeks=k) for k in range(lebar)]
            if all(w in f_.index for w in pk0 + pk1) and f_.at[s0, "rs"] < d:
                v = sg(f_.loc[pk0, "value"].mean() - f_.loc[pk1, "value"].mean())
                c[nama] = -v        # klaim awal turun → payrolls kuat (+); klaim lanjutan naik → UR di atas → USD −
        # 5–6 ISM ketenagakerjaan
        dj = []
        for nama in ("ISM Manufacturing Employment", "ISM Non-Manufacturing Employment"):
            x = cari(nama, M, d)
            if x:
                a_, p_ = angka(x[1]["actual"]), angka(x[1]["previous"])
                if a_ == a_ and p_ == p_:
                    dj.append(a_ - p_)
                    if nama.startswith("ISM Non"):
                        c["ISMJ"] = sg(a_ - p_)
        if dj:
            c["ISM2"] = sg(sum(dj))
        # 7 Philly Fed Employment (terbit bulan M)
        x = cari("Philly Fed Employment", M, d, bulan_rilis=True)
        if x:
            a_, p_ = angka(x[1]["actual"]), angka(x[1]["previous"])
            c["PHIL"] = sg(a_ - p_)
        # 8 Challenger (baris %), 07:30 ET → boleh hari yang sama
        ch = [r_ for d_, r_ in kumpul()["Challenger Job Cuts"] if d_ <= d and acuan(d_) == M and "%" in r_["actual"]]
        if ch:
            c["CHAL"] = -sg(angka(ch[-1]["actual"]))
        # 9 Indeed
        s = ind[ind.available < t0].value
        a_, b_ = s[s.index <= M + pd.Timedelta(days=11)], s[s.index <= M1 + pd.Timedelta(days=11)]
        if len(a_) and len(b_) and a_.index[-1] >= M and b_.index[-1] >= M1:
            c["IND"] = sg(a_.iloc[-1] - b_.iloc[-1])
        # 10 revisi rilis sebelumnya, 12 KON3 (ALFRED PAYEMS)
        dprev = P[P.date == M1].rs.min()
        if dprev == dprev and dprev < d:
            m2, m4 = (M.to_period("M") - 2).to_timestamp(), (M.to_period("M") - 4).to_timestamp()
            new = asof(P, m2, dprev) - asof(P, m4, dprev)
            old = asof(P, m2, dprev - pd.Timedelta(days=1)) - asof(P, m4, dprev - pd.Timedelta(days=1))
            o["rev"] = new - old
            c["REV"] = sg(new - old)
        lv = [asof(P, (M.to_period("M") - k).to_timestamp(), h1) for k in range(1, 5)]
        if all(v == v for v in lv):
            o["tren3"] = (lv[0] - lv[3]) / 3
            c["KON3"] = sg(o["tren3"] - nfp[1] / 1e3)
        # 11 ForexFactory vs Nasdaq
        g = ff[(ff.time - t0).abs() <= pd.Timedelta(hours=26)]
        if len(g):
            o["ff_gap"] = g.f.iloc[0] / 1e3 - nfp[1] / 1e3
            c["FFNQ"] = sg(o["ff_gap"], 5)
        # 13–14 UR tanpa pembulatan
        if ur and ur[1] == ur[1]:
            u_, l_ = asof(U, M1, h1), asof(CL, M1, h1)
            if u_ == u_ and l_ == l_:
                uu = 100 * u_ / l_
                o["ur_u"], o["ur_cek"] = uu, abs(round(uu + 1e-9, 1) - asof(UR, M1, h1)) < 1e-6
                c["URU"], c["URU0"] = -sg(round(uu - ur[1], 9), 0.02), -sg(round(uu - ur[1], 9))
        # 16 PK5, 19 K12
        gap = ((s0 - pd.Timedelta(days=6)) - (s1 - pd.Timedelta(days=6))).days
        c["PK5U"] = -1.0 if gap >= 35 else 1.0
        c["K12A"] = 1.0 if (M + pd.Timedelta(days=11)).weekday() in (6, 0, 1, 2) else -1.0
        jumat = sum(1 for k in range(1, (d - s0).days + 1) if (s0 + pd.Timedelta(days=k)).weekday() == 4)
        o["jumat"] = jumat
        c["KOLEKSI"] = -1.0 if jumat <= 2 else (1.0 if jumat >= 4 else 0.0)
        # 17–18 konsistensi y/y AHE
        if ahe and ahey and ahe[1] == ahe[1] and ahey[1] == ahey[1]:
            L1, L12 = asof(AH, M1, h1), asof(AH, (M.to_period("M") - 12).to_timestamp(), h1)
            if L1 == L1 and L12 == L12:
                mm_i = ((1 + ahey[1] / 100) * L12 / L1 - 1) * 100
                yy_i = (L1 * (1 + ahe[1] / 100) / L12 - 1) * 100
                o["ahe_mm_i"], o["ahe_yy_i"] = mm_i, yy_i
                c["AHEM"] = sg(round(mm_i - ahe[1], 9), 0.05)
                c["AHEY"] = sg(round(yy_i - ahey[1], 9), 0.05)
        o.update(c)
        rows.append(o)
    x = pd.DataFrame(rows)
    x = df.merge(x, on="t0", how="left")
    x = x[x.nfp_f.notna()].sort_values("t0").reset_index(drop=True)
    for col in GRUP_A + GRUP_B + GRUP_C + ["KOLEKSI"]:
        if col not in x:
            x[col] = 0.0
        x[col] = x[col].fillna(0.0)
    x["KOMP"] = np.sign(2 * x.ADPG + x.URU + x.AHEM)
    x["RND"] = np.sign(x.URU + x.AHEM)
    x["SUARA"] = np.sign(x[SUARA_IKUT].sum(axis=1))
    x["th"] = x.t0.dt.year
    x["MODEL"] = model_wf(x)
    x["UR2"] = np.sign(x.KLLSW + x.PK5U)
    x.to_pickle(CACHE)
    return x


def model_wf(x: pd.DataFrame) -> np.ndarray:
    """Logistik walk-forward per tahun (pasca-lihat): fitur = 14 petunjuk SUARA, target = arah USD lonjakan (−arah emas)."""
    from sklearn.linear_model import LogisticRegression
    X = x[SUARA_IKUT].to_numpy(float)
    yy = -x.arah.fillna(0).to_numpy()
    th = x.th.to_numpy()
    out = np.zeros(len(x))
    for Y in range(2013, int(th.max()) + 1):
        tr = (th < Y) & (yy != 0)
        if tr.sum() < 30:
            continue
        m = LogisticRegression(C=1.0).fit(X[tr], yy[tr])
        out[th == Y] = np.sign(m.decision_function(X[th == Y]))
    return out


# ───────────────────────────── evaluasi ─────────────────────────────
def pct(k: int, n: int) -> str:
    return f"{k / n * 100:5.1f}% ({k}/{n})" if n else "   –   (0/0)"


def periode(tb, y, x) -> dict:
    th, t0 = x.th.to_numpy(), x.t0
    m = {"2016–26": th >= 2016, "LAMA": (th >= 2016) & (t0 < SPLIT).to_numpy(), "BARU": (t0 >= SPLIT).to_numpy(),
         "2022+": th >= 2022, "2026": th == 2026}
    return {k: sk(tb, y, v) for k, v in m.items()}


def teks(r: dict) -> str:
    return " | ".join(f"{k} {pct(*v)}" for k, v in r.items())


def angka_tepat(x: pd.DataFrame, c: str) -> str:
    """Ketepatan petunjuk menebak komponen kejutan yang dituju (dalam arah USD)."""
    if c in GRUP_A:
        ref = x.s_nfp
    elif c in GRUP_B:
        ref = -x.s_ur
    elif c == "AHEY":
        ref = x.s_ahey
    elif c in GRUP_C:
        ref = x.s_ahe
    else:
        ref = x.PLAFON
    out = []
    for nm, m in (("semua", x.th >= 2010), ("2016+", x.th >= 2016)):
        ok = m & (x[c] != 0) & (ref != 0)
        k, n = int((x[c][ok] == ref[ok]).sum()), int(ok.sum())
        out.append(f"{nm} {pct(k, n)}")
    return " ; ".join(out)


def per_tahun(tb, y, th) -> str:
    out = []
    for Y in range(2013, int(th.max()) + 1):
        k, n = sk(tb, y, th == Y)
        if n:
            out.append(f"{Y} {k}/{n}")
    return ", ".join(out) or "–"


def p_seleksi(x: pd.DataFrame, rng, n_perm: int = N_PERM) -> dict:
    """Permutasi SADAR-SELEKSI untuk aturan pasca-lihat UR2: tiap acakan MENGULANG langkah yang benar-benar dilakukan —
    (1) hitung tutup kertas 2016–26 ke-19 aturan tunggal (grup A–C), (2) pilih 2 terbaik (n ≥ 40), gabungkan tanda(r1 + r2),
    (3) latih ulang MODEL, lalu statistik = ketepatan mentah TERBAIK seluruh keluarga (22 + KOLEKSI + MODEL + gabungan)."""
    y = x.arah.fillna(0).to_numpy()
    th = x.th.to_numpy()
    s16, b22 = th >= 2016, th >= 2022
    tunggal = GRUP_A + GRUP_B + GRUP_C
    tetap_ = {c: x[c].to_numpy(float) for c in GRUP_A + GRUP_B + GRUP_C + GRUP_D + ["KOLEKSI"]}

    def h(v, yy, m):
        ok = m & (v != 0) & (yy != 0)
        return ((-v[ok]) == yy[ok]).mean() if ok.sum() else np.nan

    def cukup(v):
        return ((v != 0) & s16).sum() >= 40 and ((v != 0) & b22).sum() >= 20

    def stat(yy, model):
        skor = []
        for c in tunggal:
            k, n = sk(tutup(tetap_[c], yy, th), yy, s16)
            if n >= 40:
                skor.append((k / n, c))
        skor.sort(reverse=True)
        gab = np.sign(tetap_[skor[0][1]] + tetap_[skor[1][1]])
        fam = [v for v in tetap_.values() if cukup(v)] + [model] + ([gab] if cukup(gab) else [])
        return (np.nanmax([h(v, yy, s16) for v in fam]), np.nanmax([h(v, yy, b22) for v in fam]),
                (skor[0][1], skor[1][1]))
    o16, o22, pas = stat(y, x.MODEL.to_numpy(float))
    ur2 = x.UR2.to_numpy(float)
    u16, u22 = h(ur2, y, s16), h(ur2, y, b22)
    m16, m22 = [], []
    for _ in range(n_perm):
        yp = y[rng.permutation(len(y))]
        xp = x.assign(arah=yp)
        a, b, _ = stat(yp, model_wf(xp))
        m16.append(a)
        m22.append(b)
    m16, m22 = np.array(m16), np.array(m22)
    return {"pasangan_asli": pas, "ur2": (u16, u22), "p16": float((m16 >= u16).mean()), "p22": float((m22 >= u22).mean()),
            "q95": (float(np.percentile(m16, 95)), float(np.percentile(m22, 95))), "n_perm": n_perm}


def keluarga_detik(C: dict, x: pd.DataFrame, rng) -> dict:
    """Permutasi keluarga untuk target SEKUNDER (gabungan detik 2/3/5/10, seperti research/berita_detik)."""
    from .cpi_validitas import hit_mentah
    G = x[[f"g{h}" for h in HH]].fillna(0).to_numpy()
    s16, b22 = (x.th >= 2016).to_numpy(), (x.th >= 2022).to_numpy()
    cukup = [c for c, v in C.items() if ((v != 0) & s16).sum() >= 40 and ((v != 0) & b22).sum() >= 20]
    m16, m22 = [], []
    for _ in range(N_PERM):
        Gp = G[rng.permutation(len(x))]
        m16.append(np.nanmax([hit_mentah(C[c], Gp, s16) for c in cukup]))
        m22.append(np.nanmax([hit_mentah(C[c], Gp, b22) for c in cukup]))
    m16, m22 = np.array(m16), np.array(m22)
    out = {}
    for c in cukup:
        o16, o22 = hit_mentah(C[c], G, s16), hit_mentah(C[c], G, b22)
        out[c] = (float((m16 >= o16).mean()), float((m22 >= o22).mean()), (o16, o22))
    return out


def sekunder(x: pd.DataFrame, c: str) -> tuple[str, dict]:
    """Tutup kertas gabungan detik 2–10 (cpi_detik.tetap/tepat: dipakai bila gabungan tahun lalu > 50%)."""
    from .cpi_detik import tepat, tetap
    tb = tetap(x, c)
    r = {}
    th, t0 = x.th, x.t0
    for nm, m in (("2016–26", th >= 2016), ("LAMA", (th >= 2016) & (t0 < SPLIT)), ("BARU", t0 >= SPLIT),
                  ("2022+", th >= 2022)):
        r[nm] = tepat(x[m], tb[m], HH)
    return " | ".join(f"{k} {pct(*v)}" for k, v in r.items()), r


def main() -> None:
    segar = "segar" in sys.argv
    x = tabel(segar)
    y = x.arah.fillna(0).to_numpy()
    th = x.th.to_numpy()
    rng = np.random.default_rng(11)
    L = ["# 🧑‍💼 Riset NFP mendalam → arah lonjakan terbesar menit pertama (tutup kertas + permutasi keluarga)",
         "", __doc__.split("\n\n", 2)[2].split("TARGET utama")[0].strip(), ""]
    L.append(f"Data: {len(x)} rilis NFP {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m} (ada tick & baris Nasdaq); "
             f"bulan acuan dari ALFRED PAYEMS. Cek UR tanpa pembulatan = UNRATE vintage: "
             f"{int(x.ur_cek.fillna(False).sum())}/{int(x.ur_cek.notna().sum())} cocok.")
    L.append("Cakupan petunjuk (rilis ≠ 0 sejak 2016 / sejak 2022): " +
             ", ".join(f"{c} {int(((x[c] != 0) & (x.th >= 2016)).sum())}/{int(((x[c] != 0) & (x.th >= 2022)).sum())}"
                       for c in ATURAN))
    L.append("Kolom: tutup kertas (tahun Y dipakai hanya bila rilis < Y benar > 50%, n ≥ 10) | 'mentah' = semua rilis tanpa "
             "saringan, 2016+/2022+, dengan p permutasi keluarga | 'angka' = ketepatan menebak kejutan komponen yang dituju "
             "(NFP / UR / AHE; gabungan → plafon) dalam arah USD.")
    L.append("\n## Pembanding (target lonjakan menit pertama; arah emas)")
    L.append("   selalu NAIK  " + teks(periode(np.ones(len(x)), y, x)))
    L.append("   selalu TURUN " + teks(periode(-np.ones(len(x)), y, x)))
    L.append("   PLAFON       " + teks(periode(-x.PLAFON.to_numpy(), y, x)) + "   (kejutan sebenarnya NFP×2 − UR + AHE)")
    from .cpi_detik import tepat
    naik = pd.Series(1.0, index=x.index)
    L.append("   sekunder detik 2–10 gabungan, selalu NAIK: " + " | ".join(
        f"{nm} {pct(*tepat(x[m], naik[m], HH))}" for nm, m in
        (("2016–26", x.th >= 2016), ("LAMA", (x.th >= 2016) & (x.t0 < SPLIT)), ("BARU", x.t0 >= SPLIT))))
    L.append("   sekunder detik 2–10 gabungan, PLAFON:      " + " | ".join(
        f"{nm} {pct(*tepat(x[m], -x.PLAFON[m], HH))}" for nm, m in
        (("2016–26", x.th >= 2016), ("LAMA", (x.th >= 2016) & (x.t0 < SPLIT)), ("BARU", x.t0 >= SPLIT))))
    C = {c: x[c].to_numpy(float) for c in ATURAN}
    kel = keluarga(C, y, th, rng)
    kd = keluarga_detik(C, x, rng)
    L.append(f"\n## Hasil per aturan — tutup kertas, target LONJAKAN (keluarga {len(kel)} aturan cukup rilis, 2.000×)")
    hasil, kandidat = [], []
    for c in ATURAN:
        tb = tutup(C[c], y, th)
        r = periode(tb, y, x)
        p = kel.get(c)
        (k, n), (kl, nl), (kb, nb) = r["2016–26"], r["LAMA"], r["BARU"]
        ok = bool(p and n >= 40 and k / n >= 0.6 and nl >= 8 and kl / nl > 0.5 and nb >= 8 and kb / nb > 0.5
                  and min(p[0], p[1]) < 0.05)
        mentah = f"mentah {p[2][0] * 100:.1f}%/{p[2][1] * 100:.1f}% p {p[0]:.3f}/{p[1]:.3f}" if p else \
            "di luar keluarga (rilis kurang)"
        tag = " [pasca-lihat]" if c in GRUP_E else ""
        L.append(f"   {c:7s} {teks(r)}{tag}")
        L.append(f"           {mentah} | angka {angka_tepat(x, c)}{'  ✅ LOLOS' if ok else ''}")
        L.append(f"           per tahun: {per_tahun(tb, y, th)}")
        sek = []
        for h in HH:
            yh = np.sign(x[f"g{h}"].fillna(0).to_numpy())
            sek.append(f"{h}d {pct(*sk(tutup(C[c], yh, th), yh, th >= 2016))}")
        st, sr = sekunder(x, c)
        q = kd.get(c)
        L.append("           sekunder per detik (2016–26): " + " | ".join(sek))
        L.append(f"           sekunder gabungan 2–10: {st}" +
                 (f" | mentah {q[2][0] * 100:.1f}%/{q[2][1] * 100:.1f}% p {q[0]:.3f}/{q[1]:.3f}" if q else ""))
        if n:
            fe = []
            for f_ in ("ex_arah", "du_arah"):
                yf = x[f_].fillna(0).to_numpy()
                fe.append(f"{f_[:2]} {pct(*sk(tutup(C[c], yf, th), yf, th >= 2016))}")
            L.append("           per feed (2016–26): " + " | ".join(fe))
        h_ = {"kode_aturan": c, "uraian": c + tag, "semua": round(k / n * 100, 1) if n else 0.0, "n_rilis": n,
              "lolos": ok, "lama": round(kl / nl * 100, 1) if nl else None,
              "baru": round(kb / nb * 100, 1) if nb else None,
              "s2022": round(r["2022+"][0] / r["2022+"][1] * 100, 1) if r["2022+"][1] else None,
              "p16": p[0] if p else None, "p22": p[1] if p else None,
              "detik_semua": round(sr["2016–26"][0] / sr["2016–26"][1] * 100, 1) if sr["2016–26"][1] else None,
              "detik_p16": q[0] if q else None, "detik_p22": q[1] if q else None}
        hasil.append(h_)
        if ok:
            kandidat.append(c)
    L.append("\n## Rangkuman (diurutkan menurut tutup kertas 2016–26, target lonjakan)")
    L.append("   aturan    2016–26        LAMA    BARU    2022+   p16    p22   | detik 2–10 gabungan (p16/p22)")
    for h_ in sorted(hasil, key=lambda v: -(v["semua"] or 0)):
        f = lambda v, d=1: "  –  " if v is None else (f"{v:5.1f}" if d else f"{v:.3f}")  # noqa: E731
        L.append(f"   {h_['kode_aturan']:8s} {f(h_['semua'])}% n {h_['n_rilis']:3d}  {f(h_['lama'])}  {f(h_['baru'])}  "
                 f"{f(h_['s2022'])}  {f(h_['p16'], 0)}  {f(h_['p22'], 0)} | {f(h_['detik_semua'])}% "
                 f"({f(h_['detik_p16'], 0)}/{f(h_['detik_p22'], 0)})")
    L.append("\nLOLOS menurut kriteria baku: " + (", ".join(kandidat) or "TIDAK ADA"))
    ps = p_seleksi(x, np.random.default_rng(23))
    L.append(f"\n## Uji sadar-seleksi untuk UR2 (pasca-lihat) — {ps['n_perm']} acakan, langkah pemilihan diulang di tiap acakan")
    L.append(f"   pasangan terbaik pada data asli: {ps['pasangan_asli']} (= KLLSW + PK5U, sesuai yang dipilih)")
    L.append(f"   UR2 mentah {ps['ur2'][0] * 100:.1f}% (2016+) / {ps['ur2'][1] * 100:.1f}% (2022+); persentil 95 acakan "
             f"terbaik-keluarga {ps['q95'][0] * 100:.1f}% / {ps['q95'][1] * 100:.1f}% → p sadar-seleksi "
             f"{ps['p16']:.3f} / {ps['p22']:.3f}")
    for h_ in hasil:
        if h_["kode_aturan"] == "UR2":
            h_["p16_seleksi"], h_["p22_seleksi"] = ps["p16"], ps["p22"]
    lolos2 = [c for c in kandidat if c not in GRUP_E or min(ps["p16"], ps["p22"]) < 0.05]
    L.append("\nLOLOS setelah koreksi seleksi (aturan pasca-lihat wajib lolos uji sadar-seleksi): " +
             (", ".join(lolos2) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    import json
    (EKS / "riset_nfp_hasil.json").write_text(json.dumps(hasil, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
