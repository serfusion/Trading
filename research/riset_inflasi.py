"""🔬 PPI & PCE: petunjuk SEBELUM rilis → arah LONJAKAN TERBESAR emas di MENIT PERTAMA (putaran 2, lebih dalam).

python -m research.riset_inflasi            → docs/eksternal/hasil_riset_inflasi.txt
(data: python -m research.riset_inflasi_data unduh && python -m research.riset_inflasi_data target)

Permintaan pengguna 11 Okt 2026: "setelah data konsensus dan lain-lain ada, persentase otomatis berubah di apk? Terapkan juga
news lain dengan pengujian, riset, validasi — jika persentase tinggi pasang". Putaran 1 (research/berita_detik.py,
docs/BERITA_DETIK.md) untuk PPI & PCE: 0 lolos; grup PCE di sana baru mulai Jul 2021 (LAMA 2 rilis → tidak bisa diuji).
Putaran ini: daftar rilis LENGKAP 2014–2026 (research/riset_inflasi_data.py, tick Dukascopy tambahan), petunjuk baru
yang lebih terdefinisi, nilai "sebelumnya" dari VINTAGE ALFRED (bukan kolom previous Nasdaq yang bisa sudah direvisi).

PRA-REGISTRASI (ditulis SEBELUM evaluasi apa pun atas petunjuk di bawah; tanda = tebakan angka utama DI ATAS konsensus =
baik untuk USD → tebakan emas = kebalikannya; angka utama PPI = PPI final demand m/m, PCE = core PCE m/m):

PPI (12 aturan)
  P        kejutan PPI rilis lalu (≤ 45 hari), searah. [ulang putaran 1, pembanding]
  KONV     sebelumnya (vintage FRED PPIFIS sehari sebelum rilis, dibulatkan 0,1) > konsensus m/m → di atas. [ulang KON
           putaran 1 TANPA look-ahead revisi]
  YOY      konsistensi y/y↔m/m: m/m SA tersirat = ((1+kons y/y)·N[r−12]/N[r−1] − 1) − musiman (N = PPIFID NSA, S = PPIFIS
           SA, vintage sehari sebelum rilis; musiman = m/m NSA − m/m SA bulan yang sama tahun lalu). Tersirat − kons m/m
           ≥ +0,05 → di atas, ≤ −0,05 → di bawah. Alasan: konsensus m/m & y/y dibulatkan 0,1 dan dari panel peramal yang
           berbeda; identitas aritmetika memberi informasi angka m/m yang belum dibulatkan (analog CPI YOY 71% angka).
  CPIX     CPI bulan acuan yang sama SUDAH rilis ≤ 10 hari sebelum PPI: tanda kejutan CPI TANPA pembulatan (Nasdaq "CPI
           Index, n.s.a." Act − konsensus); cadangan tanda (kejutan CPI m/m + core CPI m/m). Searah. Alasan: guncangan
           harga bersama (energi, pangan, jasa); konsensus PPI sering disusun sebelum CPI keluar.
  IMPOR    kejutan harga impor (Nasdaq "Import Price Index") ≤ 10 hari sebelum PPI, searah (energi & dolar bersama).
  ISMP     jumlah tanda kejutan "ISM Manufacturing Prices" + "ISM Non-Manufacturing Prices" (≤ 20 hari sebelum), searah.
  WTI      rata-rata WTI (FRED DCOILWTICO) 5 hari bursa s/d tgl 13 bulan acuan vs bulan sebelumnya (tgl harga PPI = pekan
           yang memuat tgl 13): naik ≥ 5% → di atas, turun ≥ 5% → di bawah (peramal kurang bereaksi pada energi).
  BENSIN   sama dengan WTI tetapi bensin grosir Gulf Coast (FRED DGASUSGULF; lebih dekat ke item PPI bensin).
  SAHAM    rata-rata SPY (Twelve Data) bulan acuan vs bulan sebelumnya naik ≥ 2% → di atas, turun ≥ 2% → di bawah
           (biaya manajemen portofolio di PPI jasa mengikuti nilai aset).
  SUARA    tanda (YOY + CPIX + IMPOR + ISMP + BENSIN + SAHAM) — kombinasi ditetapkan sebelum melihat hasil.
  PBALIK   [PASCA-LIHAT: putaran 1 menunjukkan P angka 42%] kebalikan P (margin dagang PPI berbalik / mean reversion).
  KONBALIK [PASCA-LIHAT: putaran 1 KON angka 43%] kebalikan KONV.
PCE (11 aturan)
  P, KONV  seperti PPI (vintage PCEPILFE). [ulang putaran 1]
  NOW      nowcast core PCE m/m Cleveland Fed (TANPA pembulatan; nilai terakhir bertanggal < hari rilis) − kons m/m:
           tanda (≠ 0). Alasan: analog aturan indeks CPI — angka tak dibulatkan memberi arah pembulatan Act.
  NOW5     sama, hanya bila |selisih| ≥ 0,05.
  NOWH     nowcast PCE HEADLINE m/m Cleveland − konsensus PCE headline m/m (Nasdaq "PCE price index"), |selisih| ≥ 0,05.
  YOY5     m/m tersirat dari kons core y/y: ((1+kons y/y)·I[r−12]/I[r−1] − 1) (I = PCEPILFE vintage sehari sebelum
           rilis; PCE hanya SA → identitas tepat) − kons m/m ≥ 0,05 → di atas / ≤ −0,05 → di bawah.
  YOY3     sama dengan ambang 0,03.
  KAL      Kalshi KXPCECORE 1 jam sebelum pasar tutup (tutup ≤ t0 ≤ tutup + 1 hari): P(di atas) − P(di bawah) ≥ 0,10.
  KUART    core PCE KUARTALAN di rilis GDP (Nasdaq "Core PCE Prices", tahunan q/q) yang terbit 1–10 hari SEBELUM PCE bulan
           ke-3 kuartal itu: I3 = 3·Q·(1+q)^(1/4) − I1 − I2 (vintage sehari sebelum GDP) → m/m tersirat − kons ≥ 0,05.
           Alasan: bulan ke-3 bisa dihitung mundur dari angka kuartalan; konsensus Nasdaq bisa belum diperbarui.
  TRANS    terjemahan CPI+PPI → PCE: OLS walk-forward (hanya rilis sebelumnya, ≥ 18 baris) core PCE m/m rilis pertama
           ~ core CPI m/m rilis pertama + core PPI (PPIFES) m/m rilis pertama (ALFRED, tak dibulatkan; keduanya terbit
           sebelum PCE); prediksi − kons ≥ 0,05 → di atas / ≤ −0,05 → di bawah.
  SUARA    tanda (NOW5 + YOY5 + KUART + TRANS + KAL).
Sampel utama = SEMUA rilis (termasuk yang bersamaan dengan rilis lain, mis. GDP+PCE 2026); kepekaan = tanpa rilis
bersamaan dengan GDP / Retail Sales / CPI / NFP. Target utama = arah lonjakan menit 1 (Exness, cadangan Dukascopy);
sekunder = tanda gerak detik 2/3/5/10. Evaluasi = tutup kertas (lonjakan_uji.tutup: tahun Y memakai aturan hanya bila
rilis sebelum Y benar > 50% dengan n ≥ 10), permutasi keluarga per grup (lonjakan_uji.keluarga, 2.000×; SEMUA aturan
termasuk pasca-lihat ikut keluarga). LOLOS = tutup kertas ≥ 60% (2016–2026) & > 50% LAMA (2016–Sep 2021) & > 50% BARU
(≥ Okt 2021) dengan n ≥ 8 masing-masing & p keluarga < 0,05 (2016+ atau 2022+) & ≥ 40 rilis ditebak sejak 2016 & bisa
dihitung LIVE sebelum rilis dari sumber yang terjangkau fungsi cloud Vercel.
Tanpa look-ahead: semua petunjuk ≤ hari sebelum rilis (vintage FRED/ALFRED sehari sebelumnya, nowcast bertanggal < hari
rilis, rilis lain di tanggal lebih awal), kecuali Kalshi (≥ 1 jam sebelum tutup pasar, sebelum t0).
"""
from __future__ import annotations

import glob
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .lonjakan_uji import N_PERM, SPLIT, keluarga, sk, tutup

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
DIR = EKS / "riset_inflasi"
OUT = ROOT / "docs" / "eksternal" / "hasil_riset_inflasi.txt"
TABEL = DIR / "petunjuk.parquet"

ATURAN = {"PPI": ["P", "KONV", "YOY", "CPIX", "IMPOR", "ISMP", "WTI", "BENSIN", "SAHAM", "SUARA", "PBALIK", "KONBALIK"],
          "PCE": ["P", "KONV", "NOW", "NOW5", "NOWH", "YOY5", "YOY3", "KAL", "KUART", "TRANS", "SUARA"]}
PASCA = {"PBALIK", "KONBALIK"}
LIVE = {
    "P": "ya — Nasdaq API (Act & konsensus rilis lalu)",
    "KONV": "ya — FRED API (nilai bulan lalu sebelum rilis) + konsensus Nasdaq",
    "YOY": "ya — konsensus m/m & y/y Nasdaq + FRED PPIFID/PPIFIS (vintage terkini sebelum rilis)",
    "CPIX": "ya — Nasdaq 'CPI Index, n.s.a.' Act & konsensus (sudah dipakai _cpi_detik)",
    "IMPOR": "ya — Nasdaq 'Import Price Index'", "ISMP": "ya — Nasdaq 'ISM ... Prices'",
    "WTI": "ya — FRED DCOILWTICO", "BENSIN": "ya — FRED DGASUSGULF", "SAHAM": "ya — Twelve Data SPY harian",
    "SUARA": "ya bila semua komponen ya", "PBALIK": "ya — Nasdaq", "KONBALIK": "ya — FRED + Nasdaq",
    "NOW": "perlu dicek — JSON nowcast Cleveland Fed (clevelandfed.org; bukan sumber standar cloud, dari sesi riset 403→dibuka 10 Okt)",
    "NOW5": "perlu dicek — Cleveland Fed (lihat NOW)", "NOWH": "perlu dicek — Cleveland Fed (lihat NOW)",
    "YOY5": "ya — Nasdaq (kons m/m & y/y core PCE) + FRED PCEPILFE", "YOY3": "ya — Nasdaq + FRED PCEPILFE",
    "KAL": "ya — Kalshi API (KXPCECORE, hanya sejak Nov 2024)",
    "KUART": "ya — Nasdaq 'Core PCE Prices' (rilis GDP) + FRED PCEPILFE",
    "TRANS": "ya — FRED CPILFESL, PPIFES, PCEPILFE (vintage) + konsensus Nasdaq",
}
LIVE_PCE_SUARA = "perlu dicek — komponen NOW5 dari Cleveland Fed"
BESAR_LAIN = ("GDP", "Retail Sales", "Nonfarm Payrolls", "CPI")

# Ditulis di sesi 2 (11 Okt, setelah restart kontainer) SEBELUM evaluasi apa pun dijalankan; aturan tidak diubah.
CATATAN_DATA = """CATATAN DATA (sesi 2, ditulis sebelum evaluasi; aturan pra-registrasi TIDAK diubah):
- Konsensus INDEKS PPI/PCE tanpa pembulatan (analog aturan IDX|K CPI) TIDAK ada di kalender Nasdaq: judul yang ada hanya
  "PPI", "Core PPI", "PPI ex. Food/Energy/Transport" (15 berkonsensus), "Core PCE Price Index", "PCE price index",
  "Core PCE Prices" (kuartalan, rilis GDP), "PCE Deflator" (6). → ide itu tidak bisa diuji; pengganti terdekat = YOY
  (identitas y/y↔m/m) dan NOW (nowcast Cleveland tak dibulatkan).
- Nowcast Cleveland Fed = berkas statis https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/
  nowcast_month.json (7,6 MB; HTTP 200 tanpa User-Agent dari sesi riset 11 Okt; BELUM dites dari Vercel → status live
  tetap "perlu dicek" sesuai pra-registrasi). Riwayat mulai 2013-07; tidak bisa dipastikan apakah nilai lama = nowcast
  real-time asli atau rekonstruksi (model dipasang dengan data belakangan) → kemungkinan bias optimistis untuk tahun awal.
- Jam rilis: ForexFactory, cadangan Nasdaq (kolom gmt = jam New York musim panas tetap; dicek cocok 79/79 PCE, 159/159 PPI).
- Sesi 1 terputus (restart kontainer) setelah mengunduh 16 jam tick Dukascopy; sesi 2 mengunduh 82 jam sisanya (PCE
  2014–2020 + 11 PPI), lalu menghitung ulang target. Tidak ada evaluasi yang dijalankan di sesi 1 (berkas hasil belum ada)."""


# ───────────────────────── sumber data ─────────────────────────
def us(d) -> tuple:
    from .berita_detik import us as _us
    return _us(d)


def _num(s) -> float:
    from .nasdaq_kalender import angka
    return angka(s)


@lru_cache(maxsize=None)
def _alfred(seri: str) -> pd.DataFrame:
    obs = json.loads((DIR / f"alfred_{seri}.json").read_text(encoding="utf-8"))["observations"]
    df = pd.DataFrame(obs)
    df = df[df.value != "."].copy()
    df["value"] = df.value.astype(float)
    df["date"] = pd.to_datetime(df.date)
    df["rs"] = pd.to_datetime(df.realtime_start)
    df["re"] = pd.to_datetime(df.realtime_end.replace("9999-12-31", "2262-01-01"))
    return df[["date", "rs", "re", "value"]]


@lru_cache(maxsize=None)
def vintage(seri: str, tgl: pd.Timestamp) -> pd.Series:
    """Nilai seri seperti yang diketahui pada tanggal tgl (realtime_start ≤ tgl ≤ realtime_end)."""
    a = _alfred(seri)
    v = a[(a.rs <= tgl) & (a.re >= tgl)]
    return pd.Series(v.value.to_numpy(), index=pd.DatetimeIndex(v.date)).sort_index()


def ref_bulan(seri: str, d: pd.Timestamp) -> pd.Timestamp:
    """Bulan acuan rilis tanggal d: observasi terbaru yang PERTAMA muncul pada d (cadangan: bulan sebelum d)."""
    a = _alfred(seri)
    first = a.groupby("date").rs.min()
    baru = first[first == d]
    if len(baru):
        return baru.index.max()
    return (d - pd.DateOffset(months=1)).to_period("M").to_timestamp()


def mm(s: pd.Series, r: pd.Timestamp, k: int = 1) -> float:
    try:
        return float((s[r] / s[r - pd.DateOffset(months=k)] - 1) * 100)
    except KeyError:
        return np.nan


@lru_cache(maxsize=None)
def rilis_pertama_mm(seri: str) -> pd.DataFrame:
    """m/m RILIS PERTAMA per bulan acuan (tak dibulatkan) + tanggal terbit."""
    a = _alfred(seri)
    first = a.groupby("date").rs.min()
    rows = []
    for r, t in first.items():
        if t <= pd.Timestamp("2014-02-19") and seri in ("PPIFIS", "PPIFES", "PPIFID"):
            continue                                       # vintage awal seri final demand = sejarah, bukan rilis
        v = vintage(seri, t)
        rows.append((r, t, mm(v, r)))
    return pd.DataFrame(rows, columns=["ref", "terbit", "mm"]).set_index("ref")


def pasangan(d, nama: tuple[str, ...], p_mm: float, p_yy: float) -> dict:
    """Baris Nasdaq m/m & y/y (berkonsensus) judul `nama` pada tanggal d; urutan dipilih dengan 'previous' terdekat ke
    vintage FRED (m/m & y/y bulan lalu)."""
    rows = [r for r in us(d) if r["eventName"] in nama and r["consensus"]]
    if not rows:
        return {}
    v = [(_num(r["actual"]), _num(r["consensus"]), _num(r["previous"])) for r in rows[:2]]

    def e(x, ref):
        return abs(x[2] - ref) if x[2] == x[2] and ref == ref else 9.0
    if len(v) == 1:
        jenis = "mm" if e(v[0], p_mm) <= e(v[0], p_yy) else "yy"
        return dict(zip((f"a_{jenis}", f"f_{jenis}", f"p_{jenis}"), v[0]))
    a, b = v
    if e(b, p_mm) + e(a, p_yy) < e(a, p_mm) + e(b, p_yy):
        a, b = b, a
    return {"a_mm": a[0], "f_mm": a[1], "p_mm": a[2], "a_yy": b[0], "f_yy": b[1], "p_yy": b[2]}


def kejutan_hari(d, nama: str) -> float:
    for r in us(d):
        if r["eventName"] == nama and r["consensus"]:
            a, f = _num(r["actual"]), _num(r["consensus"])
            if a == a and f == f:
                return float(np.sign(round(a - f, 9)))
    return np.nan


def cari_sebelum(d: pd.Timestamp, nama: str, hari: int) -> list[pd.Timestamp]:
    """Tanggal kerja (d − hari, d) yang memuat judul `nama` berkonsensus (terlama → terbaru)."""
    out = []
    for x in pd.bdate_range(d - pd.Timedelta(days=hari), d - pd.Timedelta(days=1)):
        if any(r["eventName"] == nama and r["consensus"] for r in us(x)):
            out.append(x)
    return out


@lru_cache(maxsize=None)
def harian(seri: str) -> pd.Series:
    f = DIR / f"fred_{seri}.json"
    if not f.exists():
        f = EKS / f"fred_{seri}.json"
    obs = [o for o in json.loads(f.read_text(encoding="utf-8"))["observations"] if o["value"] != "."]
    return pd.Series([float(o["value"]) for o in obs], index=pd.DatetimeIndex([o["date"] for o in obs])).sort_index()


@lru_cache(maxsize=None)
def spy() -> pd.Series:
    v = json.loads((EKS / "td_SPY_1day.json").read_text(encoding="utf-8"))["values"]
    return pd.Series([float(x["close"]) for x in v], index=pd.DatetimeIndex([x["datetime"] for x in v])).sort_index()


def jendela13(s: pd.Series, r: pd.Timestamp) -> float:
    """Rata-rata 5 observasi terakhir s/d tanggal 13 bulan r."""
    x = s[s.index <= r + pd.Timedelta(days=12)].tail(5)
    return float(x.mean()) if len(x) == 5 and (r + pd.Timedelta(days=12) - x.index[-1]).days < 7 else np.nan


def ubah_energi(s: pd.Series, r: pd.Timestamp, ambang: float = 5.0) -> float:
    a, b = jendela13(s, r), jendela13(s, r - pd.DateOffset(months=1))
    if not (a == a and b == b):
        return 0.0
    d = (a / b - 1) * 100
    return float(np.sign(d)) if abs(d) >= ambang else 0.0


def ubah_bulan(s: pd.Series, r: pd.Timestamp, ambang: float) -> float:
    a = s[(s.index >= r) & (s.index < r + pd.DateOffset(months=1))]
    b = s[(s.index >= r - pd.DateOffset(months=1)) & (s.index < r)]
    if len(a) < 10 or len(b) < 10:
        return 0.0
    d = (a.mean() / b.mean() - 1) * 100
    return float(np.sign(d)) if abs(d) >= ambang else 0.0


@lru_cache(maxsize=None)
def cleveland() -> pd.DataFrame:
    rows = []
    for ch in json.loads((EKS / "cleveland" / "nowcast_month.json").read_text(encoding="utf-8")):
        y, m = map(int, ch["chart"]["subcaption"].split("-"))
        labels = [c["label"] for c in ch["categories"][0]["category"] if not c.get("vline")]
        for ds in ch["dataset"]:
            if ds["seriesname"] not in ("Core PCE Inflation", "PCE Inflation"):
                continue
            for lab, v in zip(labels, ds["data"]):
                val = v.get("value")
                if not val or "/" not in lab:
                    continue
                mm_, dd = map(int, lab.split("/"))
                rows.append((ds["seriesname"], pd.Timestamp(y, m, 1),
                             pd.Timestamp(y + (1 if mm_ < m else 0), mm_, dd), float(val)))
    return pd.DataFrame(rows, columns=["seri", "ref", "tgl", "now"])


def nowcast(seri: str, r: pd.Timestamp, d: pd.Timestamp) -> float:
    c = cleveland()
    g = c[(c.seri == seri) & (c.ref == r) & (c.tgl < d)]
    return float(g.sort_values("tgl").now.iloc[-1]) if len(g) else np.nan


def kalshi(t0: pd.Timestamp, kons: float) -> float:
    from .kalshi_uji import curve, lean
    for f in glob.glob(str(EKS / "kalshi" / "KXPCECORE" / "*.json")):
        ms = json.loads(Path(f).read_text(encoding="utf-8"))["pasar"]
        close = min(pd.Timestamp(m["tutup"]) for m in ms)
        if close <= t0 <= close + pd.Timedelta(days=1):
            lp = lean(curve(ms, (close - pd.Timedelta(hours=1)).timestamp()), kons, 0.1)
            if lp and abs(lp[0] - lp[1]) >= 0.10:
                return float(np.sign(lp[0] - lp[1]))
            return 0.0
    return 0.0


def sgn(v: float, ambang: float = 0.0) -> float:
    return float(np.sign(v)) if v == v and v != 0 and abs(v) >= ambang - 1e-9 else 0.0


# ───────────────────────── tabel petunjuk ─────────────────────────
def _ff() -> pd.DataFrame:
    from .news_prediksi import calendar
    c = calendar()
    c["d"] = c.time.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
    return c


def tabel(segar: bool = False) -> pd.DataFrame:
    if TABEL.exists() and not segar:
        return pd.read_pickle(TABEL)
    from .riset_inflasi_data import target
    from .nasdaq_kalender import cpi as cpi_nasdaq
    tg = target()
    ff = _ff()
    rows = []
    for x in tg.itertuples():
        g, t0 = x.grup, x.t0
        d = pd.Timestamp(x.d)
        d1 = d - pd.Timedelta(days=1)
        o = {"t0": t0, "grup": g, "d": x.d, "L": x.arah, "besar": x.besar, "ex": x.ex_arah, "du": x.du_arah,
             "sumber_target": x.sumber_target, "grup_lj": x.grup_lj}
        for h in (2, 3, 5, 10):
            o[f"g{h}"] = getattr(x, f"g{h}")
        seri = "PPIFIS" if g == "PPI" else "PCEPILFE"
        r = ref_bulan(seri, d)
        o["ref"] = r
        v = vintage(seri, d1)
        p_mm = mm(v, r - pd.DateOffset(months=1))
        if g == "PPI":
            n_ = vintage("PPIFID", d1)
            p_yy = mm(n_, r - pd.DateOffset(months=1), 12)
            pr = pasangan(d, ("PPI",), p_mm, p_yy)
            fe = "PPI m/m"
        else:
            p_yy = mm(v, r - pd.DateOffset(months=1), 12)
            pr = pasangan(d, ("Core PCE Price Index",), p_mm, p_yy)
            fe = "Core PCE Price Index m/m"
        f_ff = ff[(ff.event == fe) & (ff.d == x.d)]
        o["f_ff"] = float(f_ff.f.iloc[0]) if len(f_ff) else np.nan
        am, cm = pr.get("a_mm", np.nan), pr.get("f_mm", np.nan)
        if not (cm == cm) and len(f_ff):
            am, cm = float(f_ff.a.iloc[0]), float(f_ff.f.iloc[0])
            o["sumber_kons"] = "FF"
        else:
            o["sumber_kons"] = "Nasdaq" if cm == cm else None
        o.update(am=am, cm=cm, ay=pr.get("a_yy", np.nan), cy=pr.get("f_yy", np.nan), p_mm_v=p_mm, p_yy_v=p_yy)
        o["s"] = float(np.sign(round(am - cm, 9))) if am == am and cm == cm else np.nan
        # rilis lain yang bersamaan (jam Nasdaq sama, hari sama)
        jam = next((rr["gmt"] for rr in us(d) if rr["eventName"] in (("PPI",) if g == "PPI" else ("Core PCE Price Index",))
                    and rr["consensus"]), None)
        o["bersama"] = ",".join(sorted({rr["eventName"] for rr in us(d) if rr["eventName"] in BESAR_LAIN
                                        and rr["gmt"] == jam and rr["consensus"]}))
        # pendamping untuk plafon (arah USD dari kejutan sebenarnya)
        if g == "PPI":
            vc = vintage("PPIFES", d1)
            pc = pasangan(d, ("Core PPI",), mm(vc, r - pd.DateOffset(months=1)), mm(vc, r - pd.DateOffset(months=1), 12))
        else:
            vh = vintage("PCEPI", d1)
            pc = pasangan(d, ("PCE price index", "PCE Price index"), mm(vh, r - pd.DateOffset(months=1)),
                          mm(vh, r - pd.DateOffset(months=1), 12))
        o["ch_f"] = pc.get("f_mm", np.nan)
        s2 = float(np.sign(round(pc["a_mm"] - pc["f_mm"], 9))) if pc.get("a_mm", np.nan) == pc.get("a_mm", np.nan) \
            and pc.get("f_mm", np.nan) == pc.get("f_mm", np.nan) else 0.0
        o["PLAFON"] = float(np.sign(2 * np.nan_to_num(o["s"]) + s2))
        c = {}
        c["KONV"] = sgn(round(p_mm, 1) - cm) if p_mm == p_mm and cm == cm else 0.0
        if g == "PPI":
            c.update(_ppi(d, d1, r, cm, o["cy"], cpi_nasdaq))
        else:
            c.update(_pce(d, d1, r, t0, cm, o["cy"], o["ch_f"]))
        o.update(c)
        rows.append(o)
    df = pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)
    df["th"] = df.t0.dt.year
    for g, xg in df.groupby("grup"):
        s_ = xg.s.fillna(0)
        dekat = (xg.t0 - xg.t0.shift(1)) <= pd.Timedelta(days=45)
        df.loc[xg.index, "P"] = np.where(dekat, s_.shift(1).fillna(0), 0.0)
    df["PBALIK"] = np.where(df.grup == "PPI", -df.P, 0.0)
    df["KONBALIK"] = np.where(df.grup == "PPI", -df.KONV, 0.0)
    df = trans(df)
    df["SUARA"] = 0.0
    m = df.grup == "PPI"
    df.loc[m, "SUARA"] = np.sign(df.loc[m, ["YOY", "CPIX", "IMPOR", "ISMP", "BENSIN", "SAHAM"]].fillna(0).sum(axis=1))
    m = df.grup == "PCE"
    df.loc[m, "SUARA"] = np.sign(df.loc[m, ["NOW5", "YOY5", "KUART", "TRANS", "KAL"]].fillna(0).sum(axis=1))
    df.to_pickle(TABEL)
    return df


def _ppi(d, d1, r, cm, cy, cpi_nasdaq) -> dict:
    c = {}
    # YOY: m/m SA tersirat dari konsensus y/y (NSA) & musiman tahun lalu
    N, S = vintage("PPIFID", d1), vintage("PPIFIS", d1)
    c["YOY"] = 0.0
    try:
        imp_nsa = ((1 + cy / 100) * N[r - pd.DateOffset(months=12)] / N[r - pd.DateOffset(months=1)] - 1) * 100
        seas = mm(N, r - pd.DateOffset(months=12)) - mm(S, r - pd.DateOffset(months=12))
        imp = imp_nsa - seas
        c["yoy_imp"] = imp
        if cm == cm and imp == imp:
            c["YOY"] = sgn(imp - cm, 0.05)
    except (KeyError, TypeError):
        pass
    # CPIX: CPI bulan yang sama sudah rilis ≤ 10 hari sebelumnya
    c["CPIX"] = 0.0
    tc = cari_sebelum(d, "CPI", 10)
    if tc:
        t = tc[-1]
        idx = [rr for rr in us(t) if rr["eventName"] == "CPI Index, n.s.a." and rr["consensus"] and rr["actual"]]
        if idx:
            c["CPIX"] = sgn(_num(idx[0]["actual"]) - _num(idx[0]["consensus"]))
        else:
            k = cpi_nasdaq(t)
            s1 = np.sign(round(k.get("mm_a", np.nan) - k.get("mm_f", np.nan), 9))
            s2 = np.sign(round(k.get("core_a", np.nan) - k.get("core_f", np.nan), 9))
            c["CPIX"] = sgn(np.nan_to_num(s1) + np.nan_to_num(s2))
    ti = cari_sebelum(d, "Import Price Index", 10)
    c["IMPOR"] = sgn(kejutan_hari(ti[-1], "Import Price Index")) if ti else 0.0
    tot = 0.0
    for nm in ("ISM Manufacturing Prices", "ISM Non-Manufacturing Prices"):
        tt = cari_sebelum(d, nm, 20)
        if tt:
            tot += np.nan_to_num(kejutan_hari(tt[-1], nm))
    c["ISMP"] = sgn(tot)
    c["WTI"] = ubah_energi(harian("DCOILWTICO"), r)
    c["BENSIN"] = ubah_energi(harian("DGASUSGULF"), r)
    c["SAHAM"] = ubah_bulan(spy(), r, 2.0)
    return c


def _pce(d, d1, r, t0, cm, cy, ch_f) -> dict:
    c = {}
    nc, nh = nowcast("Core PCE Inflation", r, d), nowcast("PCE Inflation", r, d)
    c["now_c"], c["now_h"] = nc, nh
    c["NOW"] = sgn(nc - cm) if cm == cm else 0.0
    c["NOW5"] = sgn(nc - cm, 0.05) if cm == cm else 0.0
    c["NOWH"] = sgn(nh - ch_f, 0.05) if ch_f == ch_f else 0.0
    I = vintage("PCEPILFE", d1)
    c["YOY5"] = c["YOY3"] = 0.0
    try:
        imp = ((1 + cy / 100) * I[r - pd.DateOffset(months=12)] / I[r - pd.DateOffset(months=1)] - 1) * 100
        c["yoy_imp"] = imp
        if cm == cm and imp == imp:
            c["YOY5"], c["YOY3"] = sgn(imp - cm, 0.05), sgn(imp - cm, 0.03)
    except (KeyError, TypeError):
        pass
    c["KAL"] = kalshi(t0, cm) if cm == cm else 0.0
    c["KUART"] = 0.0
    if r.month in (3, 6, 9, 12) and cm == cm:
        for gd in cari_gdp(d):
            q = [rr for rr in us(gd) if rr["eventName"] == "Core PCE Prices" and rr["actual"]]
            if not q:
                continue
            qv = _num(q[0]["actual"])
            V = vintage("PCEPILFE", gd - pd.Timedelta(days=1))
            try:
                m1, m2 = V[r - pd.DateOffset(months=2)], V[r - pd.DateOffset(months=1)]
                qp = np.mean([V[r - pd.DateOffset(months=k)] for k in (3, 4, 5)])
            except KeyError:
                continue
            i3 = 3 * qp * (1 + qv / 100) ** 0.25 - m1 - m2
            c["kuart_imp"] = (i3 / m2 - 1) * 100
            c["KUART"] = sgn(c["kuart_imp"] - cm, 0.05)
            break
    return c


def cari_gdp(d: pd.Timestamp) -> list[pd.Timestamp]:
    return [x for x in pd.bdate_range(d - pd.Timedelta(days=10), d - pd.Timedelta(days=1))
            if any(rr["eventName"] == "Core PCE Prices" and rr["actual"] for rr in us(x))][::-1]


def trans(df: pd.DataFrame) -> pd.DataFrame:
    """TRANS: OLS walk-forward core PCE m/m rilis pertama ~ core CPI + core PPI m/m rilis pertama (bulan acuan sama)."""
    pce, cpi, ppi = rilis_pertama_mm("PCEPILFE"), rilis_pertama_mm("CPILFESL"), rilis_pertama_mm("PPIFES")
    df["TRANS"] = 0.0
    df["trans_pred"] = np.nan
    x = df[df.grup == "PCE"]
    for i, row in x.iterrows():
        d = pd.Timestamp(row.d)
        r = row.ref
        if r not in cpi.index or r not in ppi.index or not (cpi.terbit[r] < d and ppi.terbit[r] < d):
            continue
        ok = pce[(pce.terbit < d) & pce.index.isin(cpi.index) & pce.index.isin(ppi.index)]
        ok = ok[(cpi.terbit.reindex(ok.index) < ok.terbit) & (ppi.terbit.reindex(ok.index) < ok.terbit)]
        ok = ok[ok.index >= pd.Timestamp("2014-01-01")]
        if len(ok) < 18:
            continue
        X = np.column_stack([np.ones(len(ok)), cpi.mm.reindex(ok.index), ppi.mm.reindex(ok.index)])
        yy = ok.mm.to_numpy()
        bersih = ~np.isnan(X).any(axis=1) & ~np.isnan(yy)
        if bersih.sum() < 18 or not (cpi.mm[r] == cpi.mm[r] and ppi.mm[r] == ppi.mm[r]):
            continue
        b = np.linalg.lstsq(X[bersih], yy[bersih], rcond=None)[0]
        pred = float(b @ [1, cpi.mm[r], ppi.mm[r]])
        df.loc[i, "trans_pred"] = pred
        if row.cm == row.cm:
            df.loc[i, "TRANS"] = sgn(pred - row.cm, 0.05)
    return df


# ───────────────────────── evaluasi ─────────────────────────
def pct(k: int, n: int) -> str:
    return f"{k / n * 100:5.1f}% ({k}/{n})" if n else "    – (0/0)"


MASK = {"2016-26": lambda th, t0: th >= 2016, "LAMA": lambda th, t0: (th >= 2016) & (t0 < SPLIT),
        "BARU": lambda th, t0: t0 >= SPLIT, "2022+": lambda th, t0: th >= 2022, "2026": lambda th, t0: th == 2026}


def ringkas(tb, y, th, t0) -> dict:
    return {k: sk(tb, y, np.asarray(f(th, t0), bool)) for k, f in MASK.items()}


def tutup_detik(usd: np.ndarray, G: np.ndarray, th: np.ndarray) -> np.ndarray:
    """Tutup kertas untuk target sekunder (detik 2/3/5/10 digabung): tahun Y dipakai bila sebelum Y > 50%, n ≥ 40."""
    g = -np.asarray(usd, float)
    out = np.zeros(len(g))
    for Y in range(2013, int(th.max()) + 1):
        lalu = (th < Y) & (g != 0)
        c, gg = g[lalu][:, None], G[lalu]
        ok = (gg != 0) & ~np.isnan(gg)
        n = int(ok.sum())
        if n >= 40 and (np.broadcast_to(c, gg.shape)[ok] == gg[ok]).mean() > 0.5:
            out[th == Y] = g[th == Y]
    return out


def sk_detik(tb, G, m) -> tuple[int, int]:
    c, gg = tb[m][:, None], G[m]
    ok = (gg != 0) & ~np.isnan(gg) & (c != 0)
    return int((np.broadcast_to(c, gg.shape)[ok] == gg[ok]).sum()), int(ok.sum())


def uji(x: pd.DataFrame, nama: str, aturan: list[str], L: list, hasil: list, rng, tag: str = "") -> None:
    x = x[x.L.notna()].reset_index(drop=True)
    y, th, t0 = x.L.to_numpy(), x.th.to_numpy(), x.t0
    G = x[["g2", "g3", "g5", "g10"]].to_numpy(float)
    us_ = x.s.fillna(0).to_numpy()
    L.append(f"\n## {nama}{tag} — {len(x)} rilis {t0.min():%Y-%m}–{t0.max():%Y-%m} (target ada), lonjakan naik "
             f"{(y > 0).sum() / max((y != 0).sum(), 1) * 100:.0f}%")
    for lab, v in (("selalu NAIK", -np.ones(len(x))), ("PLAFON", x.PLAFON.fillna(0).to_numpy())):
        r = ringkas(-v, y, th, t0)
        L.append(f"   {lab:12s} " + " | ".join(f"{k} {pct(*r[k])}" for k in MASK))
    C = {c: x[c].fillna(0).to_numpy() for c in aturan}
    kel = keluarga(C, y, th, rng)
    L.append(f"   (permutasi keluarga {len(kel)} aturan cukup data dari {len(C)}; {N_PERM}×)")
    L.append("   aturan     angka(n)        | " + " | ".join(f"{k:>16s}" for k in MASK) + " | p16/p22 | detik2–10 2016-26 / LAMA / BARU")
    for c, v in C.items():
        tb = tutup(v, y, th)
        r = ringkas(tb, y, th, t0)
        m = (v != 0) & (us_ != 0)
        angka = pct(int((v[m] == us_[m]).sum()), int(m.sum()))
        p = kel.get(c)
        td = tutup_detik(v, G, th)
        dd = [sk_detik(td, G, np.asarray(f(th, t0), bool)) for f in (MASK["2016-26"], MASK["LAMA"], MASK["BARU"])]
        (k, n), (kl, nl), (kb, nb) = r["2016-26"], r["LAMA"], r["BARU"]
        live = LIVE_PCE_SUARA if (nama == "PCE" and c == "SUARA") else LIVE.get(c, "-")
        ok = bool(n >= 40 and k / n >= 0.6 and nl >= 8 and kl / nl > 0.5 and nb >= 8 and kb / nb > 0.5
                  and p and min(p[0], p[1]) < 0.05 and live.startswith("ya"))
        L.append(f"   {c + ('*' if c in PASCA else ''):9s} {angka:15s} | " + " | ".join(f"{pct(*r[kk]):>16s}" for kk in MASK)
                 + (f" | {p[0]:.3f}/{p[1]:.3f}" if p else " |   –  ") + " | "
                 + " / ".join(pct(*z) for z in dd) + ("  ✅ LOLOS" if ok else ""))
        per = {str(Y): sk(tb, y, th == Y) for Y in range(2014, int(th.max()) + 1)}
        L.append("             per tahun: " + " ".join(f"{Y[2:]}:{a}/{b}" for Y, (a, b) in per.items() if b))
        if not tag:
            hasil.append({"berita": nama, "kode_aturan": c, "lolos": ok, "n_rilis": n,
                          "semua": round(k / n * 100, 1) if n else 0.0,
                          "lama": round(kl / nl * 100, 1) if nl else None, "baru": round(kb / nb * 100, 1) if nb else None,
                          "s2022": round(r["2022+"][0] / r["2022+"][1] * 100, 1) if r["2022+"][1] else None,
                          "p16": p[0] if p else None, "p22": p[1] if p else None,
                          "uraian": ("PASCA-LIHAT; " if c in PASCA else "") + f"angka {angka.strip()}; live: {live}"})


def main() -> None:
    df = tabel()
    L = ["# 🔬 PPI & PCE → arah lonjakan terbesar emas menit pertama (riset putaran 2, tutup kertas + validitas)",
         __doc__.split("\n\n")[2], "", "(disalin apa adanya dari docstring research/riset_inflasi.py)",
         "\n\n".join(__doc__.split("\n\n")[3:]).rstrip(), "", CATATAN_DATA]
    hasil, rng = [], np.random.default_rng(11)
    for g in ("PPI", "PCE"):
        x = df[df.grup == g]
        L.append(f"\n# {g}: {len(x)} rilis 2014–2026 | target dari lonjakan60 {int((x.sumber_target == 'lonjakan60').sum())}, "
                 f"hitung tick baru {int((x.sumber_target == 'hitung').sum())}, tanpa tick {int((x.sumber_target == 'tidak ada tick').sum())}"
                 f" | konsensus Nasdaq {int((x.sumber_kons == 'Nasdaq').sum())}, FF {int((x.sumber_kons == 'FF').sum())}"
                 f" | bersamaan rilis besar lain {int((x.bersama != '').sum())}")
        both = x[x.f_ff.notna() & (x.sumber_kons == "Nasdaq")]
        L.append(f"   konsensus Nasdaq = ForexFactory: {(both.f_ff == both.cm).mean() * 100:.0f}% ({len(both)} rilis); "
                 f"kejutan ≠ 0: {(x.s.fillna(0) != 0).mean() * 100:.0f}%; Exness=Dukascopy arah "
                 f"{(x.ex == x.du)[x.ex.notna() & x.du.notna()].mean() * 100:.0f}%")
        L.append("   cakupan petunjuk (≠ 0, 2016+): " + ", ".join(
            f"{c} {int(((x[c].fillna(0) != 0) & (x.th >= 2016)).sum())}" for c in ATURAN[g]))
        uji(x, g, ATURAN[g], L, hasil, rng)
        uji(x[x.bersama == ""], g, ATURAN[g], L, [], np.random.default_rng(12), tag=" [kepekaan: tanpa rilis bersamaan]")
        xd = x.assign(L=x.du)
        uji(xd, g, ATURAN[g], L, [], np.random.default_rng(13), tag=" [kepekaan: target feed Dukascopy saja]")
    lolos = [f"{h['berita']} {h['kode_aturan']}" for h in hasil if h["lolos"]]
    L.append("\nLOLOS (semua kriteria): " + (", ".join(lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    (DIR / "hasil.json").write_text(json.dumps(hasil, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
