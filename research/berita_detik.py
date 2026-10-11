"""⏱️ Semua berita USD → arah emas 1–10 DETIK setelah rilis, uji TUTUP KERTAS + uji validitas (seperti CPI).

python -m research.berita_detik           → docs/eksternal/hasil_berita_detik.txt (+ data/research/eksternal/berita_detik.pkl)

Permintaan pengguna 11 Okt 2026: "setelah selesai menemukan persentase tinggi yang dapat dipercaya validitasnya, uji juga
news lainnya" dan "setelah persentase tinggi dan uji validitas dapat dipercaya PASANG". Metode sama dengan research/cpi_detik
& cpi_validitas: target = tanda harga tengah XAU t0−1 dtk → t0+2/3/5/10 dtk (tick Exness, cadangan Dukascopy; 1 dtk
dilaporkan terpisah); tahun Y hanya melihat rilis < Y; aturan dipakai di tahun Y hanya bila tahun-tahun lalu > 50%.
Konsensus/Act: kalender Nasdaq/Investing.com (research/nasdaq_kalender, semua hari kerja 2010–2026) → juga rilis 2026.

Petunjuk (tanda = tebakan angka utama DI ATAS konsensus; disimpan dalam arah "baik untuk USD" sehingga emas = kebalikannya;
pengangguran & klaim terbalik). Semua ditetapkan SEBELUM melihat hasil; hanya data yang terbit sebelum rilis:
  UMUM   P   kejutan rilis lalu judul sama • P3  jumlah tanda 3 kejutan terakhir • KON konsensus < angka lalu → di atas
  NFP    ADP kejutan ADP pekan itu • KLAIM klaim awal 4 pekan terakhir di atas konsensus → NFP di bawah • ISME indeks
         ketenagakerjaan ISM manufaktur naik (≤ 7 hari) • KAL Kalshi payrolls • KALUR Kalshi pengangguran (terbalik)
  ADP    KLAIM
  PPI    CPI kejutan CPI headline ≤ 10 hari sebelumnya
  RETAIL MOBIL penjualan kendaraan bulan acuan naik • CPI kejutan CPI headline bulan itu
  PCE    CPIC kejutan core CPI bulan itu • PPIC kejutan core PPI bulan itu • KALPCE Kalshi core PCE
  ISM    CHI kejutan Chicago PMI ≤ 3 hari • FED rata tanda kejutan survei Fed daerah 30 hari (Empire, Philly, Richmond, KC)
         • SPG S&P Global PMI final hari yang sama (terbit 15 mnt sebelum ISM) vs konsensus
  GDP    NOW GDPNow Atlanta Fed terakhir − konsensus ≥ 0,2
  JOLTS  IND lowongan Indeed bulan acuan naik
  CLAIMS KONT kejutan klaim lanjutan pekan lalu
  KONSUMEN SPX S&P 500 naik 4 pekan • BENSIN bensin naik → sentimen di bawah
Lolos (sama dengan CPI): tutup kertas 2–10 dtk ≥ 60% (2016–2026), > 50% LAMA & BARU, dan permutasi keluarga (aturan
≥ 40 rilis 2016+ & ≥ 20 rilis 2022+, 2.000×) p < 0,05 untuk seluruh periode ATAU sejak 2022.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .cpi_detik import DET, JAUH, per_periode, tepat, tetap
from .cpi_validitas import N_PERM, hit_mentah
from .nasdaq_kalender import angka, hari

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_berita_detik.txt"
EKS = ROOT / "data" / "research" / "eksternal"
CACHE = EKS / "berita_detik.pkl"
# grup → (judul utama Nasdaq, arah USD), judul pendamping (untuk plafon)
UTAMA = {"NFP": [("Nonfarm Payrolls", 1)], "ADP": [("ADP Nonfarm Employment Change", 1)],
         "PPI": [("PPI", 1)], "RETAIL": [("Retail Sales", 1)], "PCE": [("Core PCE Price Index", 1)],
         "ISM": [("ISM Manufacturing PMI", 1), ("ISM Non-Manufacturing PMI", 1)], "GDP": [("GDP", 1)],
         "JOLTS": [("JOLTS Job Openings", 1)], "CLAIMS": [("Initial Jobless Claims", -1)],
         "KONSUMEN": [("Michigan Consumer Sentiment", 1), ("CB Consumer Confidence", 1)]}
IKUT = {"NFP": [("Unemployment Rate", -1), ("Average Hourly Earnings", 1)], "PPI": [("Core PPI", 1)],
        "RETAIL": [("Core Retail Sales", 1)], "PCE": [("PCE price index", 1)]}
JENDELA = {"CLAIMS": 10}


@lru_cache(maxsize=None)
def _us(tgl: str) -> tuple:
    return tuple(r for r in hari(tgl, ambil=False) if r["country"] == "United States")


def us(d) -> tuple:
    return _us(f"{pd.Timestamp(d):%Y-%m-%d}")


def ambil(d, nama: str) -> tuple[float, float, float] | None:
    """(Act, konsensus, sebelumnya) baris PERTAMA judul itu pada tanggal d (m/m untuk judul ganda m/m–y/y)."""
    for r in us(d):
        if r["eventName"] == nama:
            a, f, p = angka(r["actual"]), angka(r["consensus"]), angka(r["previous"])
            if f == f:
                return a, f, p
    return None


def kejutan(d, nama: str) -> float:
    v = ambil(d, nama)
    return float(np.sign(round(v[0] - v[1], 9))) if v and v[0] == v[0] else np.nan


def riwayat(nama: str, sampai: pd.Timestamp, hari_: int) -> list[tuple[pd.Timestamp, float]]:
    """Kejutan judul `nama` di hari kerja (sampai − hari_, sampai) — data yang terbit SEBELUM tanggal `sampai`."""
    out = []
    for d in pd.bdate_range(sampai - pd.Timedelta(days=hari_), sampai - pd.Timedelta(days=1)):
        s = kejutan(d, nama)
        if s == s:
            out.append((d, s))
    return out


def rilis() -> pd.DataFrame:
    v = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    v = v[v.grup.isin(UTAMA)].copy()
    for h in DET:
        v[f"g{h}"] = v[f"y{h}_XAU_EXNESS"].fillna(v[f"y{h}_XAU"])
        v[f"ex{h}"], v[f"du{h}"] = v[f"y{h}_XAU_EXNESS"], v[f"y{h}_XAU"]
    ny = v.t0.dt.tz_convert("America/New_York")
    v["d"], v["menit"] = ny.dt.normalize().dt.tz_localize(None), ny.dt.hour * 60 + ny.dt.minute
    # rilis ganda (zona waktu salah di sumber, mis. 07:30 vs 08:30 New York): simpan jam yang paling umum per grup
    modus = v.groupby("grup").menit.agg(lambda s: s.mode().iloc[0])
    v["_jarak"] = (v.menit - v.grup.map(modus)).abs()
    v = v.sort_values("_jarak").drop_duplicates(["grup", "d"]).sort_values("t0")
    return v[["t0", "grup", "d", "menit"] + [f"{p}{h}" for p in ("g", "ex", "du") for h in DET]].reset_index(drop=True)


def sp500() -> pd.DataFrame:
    """S&P 500 harian (FRED SP500, tanpa tanggal vintage) — dianggap terbit 1 hari bursa setelah tanggal data."""
    import json
    d = json.loads((EKS / "fred_SP500.json").read_text(encoding="utf-8"))["observations"]
    d = [(o["date"], float(o["value"])) for o in d if o["value"] != "."]
    idx = pd.DatetimeIndex([x for x, _ in d])
    return pd.DataFrame({"value": [v for _, v in d], "available": (idx + pd.offsets.BDay(1)).tz_localize("UTC")},
                        index=idx)


def kalshi_lean(seri: str, step, t0: pd.Timestamp, kons: float) -> float:
    """Kalshi 1 jam sebelum tutup pasar (event yang tutup ≤ 15 mnt sebelum rilis) vs konsensus → tanda atas−bawah."""
    import glob
    import json

    from .kalshi_uji import curve, lean
    for f in glob.glob(str(EKS / "kalshi" / seri / "*.json")):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        ms = d["pasar"]
        close = min(pd.Timestamp(m["tutup"]) for m in ms)
        if close <= t0 <= close + pd.Timedelta(minutes=15):
            lp = lean(curve(ms, (close - pd.Timedelta(hours=1)).timestamp()), kons, step)
            if lp and abs(lp[0] - lp[1]) >= 0.10:
                return float(np.sign(lp[0] - lp[1]))
            return 0.0
    return 0.0


def tabel() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_pickle(CACHE)
    from .berita_gabung import gdpnow
    from .eksternal_makro import fred
    from .sumber_lain import indeed, ubah, ubah_bulan
    df = rilis()
    gn = gdpnow()
    ind, spx, gas = indeed(), sp500(), fred("GASREGW")
    rows = []
    for _, r in df.iterrows():
        g, d, t0 = r.grup, r.d, r.t0
        nama = next((n for n, _ in UTAMA[g] if ambil(d, n)), None)
        o = {"t0": t0, "nama": nama}
        if nama is None:
            rows.append(o)
            continue
        arah = dict(UTAMA[g])[nama]
        a, f, p = ambil(d, nama)
        s = float(np.sign(round(a - f, 9))) if a == a else 0.0
        o.update(arah=arah, s=s, kons=f, prev=p)
        net = 2 * arah * s
        for n2, a2 in IKUT.get(g, []):
            s2 = kejutan(d, n2)
            net += a2 * (s2 if s2 == s2 else 0)
        o["PLAFON"] = float(np.sign(net))                          # arah USD dari kejutan sebenarnya
        c = {}                                                     # petunjuk = tebakan kejutan angka utama
        c["KON"] = float(np.sign(p - f)) if p == p and p != f else 0.0
        if g == "NFP":
            adp = riwayat("ADP Nonfarm Employment Change", d, 7)
            c["ADP"] = adp[-1][1] if adp else 0.0
            kl = riwayat("Initial Jobless Claims", d, 28)
            c["KLAIM"] = -float(np.sign(sum(x for _, x in kl))) if kl else 0.0
            ism = [ambil(x, "ISM Manufacturing Employment") for x in pd.bdate_range(d - pd.Timedelta(days=7), d - pd.Timedelta(days=1))]
            ism = [x for x in ism if x and x[0] == x[0] and x[2] == x[2]]
            c["ISME"] = float(np.sign(ism[-1][0] - ism[-1][2])) if ism else 0.0
            c["KAL"] = kalshi_lean("KXPAYROLLS", None, t0, f)
            ur = ambil(d, "Unemployment Rate")
            c["KALUR"] = -kalshi_lean("KXU3", 0.1, t0, ur[1]) if ur else 0.0      # pengangguran di atas → NFP lemah
        if g == "ADP":
            kl = riwayat("Initial Jobless Claims", d, 28)
            c["KLAIM"] = -float(np.sign(sum(x for _, x in kl))) if kl else 0.0
        if g in ("PPI", "RETAIL"):
            cp = riwayat("CPI", d, 10 if g == "PPI" else 25)
            c["CPI"] = cp[-1][1] if cp else 0.0
        if g == "RETAIL":
            mb = [ambil(x, "Total Vehicle Sales") for x in pd.bdate_range(d - pd.Timedelta(days=20), d - pd.Timedelta(days=1))]
            mb = [x for x in mb if x and x[0] == x[0] and x[2] == x[2]]
            c["MOBIL"] = float(np.sign(mb[-1][0] - mb[-1][2])) if mb else 0.0
        if g == "PCE":
            cc = riwayat("Core CPI", d, 25)
            c["CPIC"] = cc[-1][1] if cc else 0.0
            pp = riwayat("Core PPI", d, 25)
            c["PPIC"] = pp[-1][1] if pp else 0.0
            c["KALPCE"] = kalshi_lean("KXPCECORE", 0.1, t0, f)
        if g == "ISM":
            ch = riwayat("Chicago PMI", d, 4)
            c["CHI"] = ch[-1][1] if ch else 0.0
            fed = [x for n2 in ("NY Empire State Manufacturing Index", "Philadelphia Fed Manufacturing Index",
                                "Richmond Manufacturing Index", "KC Fed Composite Index") for _, x in riwayat(n2, d, 30)]
            c["FED"] = float(np.sign(sum(fed))) if fed else 0.0
            sp = "S&P Global Manufacturing PMI" if nama == "ISM Manufacturing PMI" else "S&P Global Services PMI"
            c["SPG"] = kejutan(d, sp) if kejutan(d, sp) == kejutan(d, sp) else 0.0   # 09:45, sebelum ISM 10:00
        if g == "GDP":
            q = gn[(gn.rilis - t0).abs() <= pd.Timedelta(days=2)]
            c["NOW"] = float(np.sign(q.now.iloc[0] - f)) if len(q) and abs(q.now.iloc[0] - f) >= 0.2 else 0.0
        if g == "JOLTS":
            v_ = ubah_bulan(ind, t0)
            c["IND"] = float(np.sign(v_)) if v_ == v_ else 0.0
        if g == "CLAIMS":
            kt = riwayat("Continuing Jobless Claims", d, 9)
            c["KONT"] = kt[-1][1] if kt else 0.0
        if g == "KONSUMEN":
            v_ = ubah(spx, t0, 20)
            c["SPX"] = float(np.sign(v_)) if v_ == v_ else 0.0
            v_ = ubah_bulan(gas, t0)
            c["BENSIN"] = -float(np.sign(v_)) if v_ == v_ else 0.0
        for k, v in c.items():
            o[k] = arah * v                                         # → arah "baik untuk USD"
        rows.append(o)
    x = pd.DataFrame(rows)
    df = df.merge(x, on="t0", how="left")
    df = df[df.nama.notna()].sort_values("t0").reset_index(drop=True)
    # kejutan lalu (judul sama) → P, P3 (arah USD)
    df["P"] = df["P3"] = 0.0
    for (_g, _n), x in df.groupby(["grup", "nama"]):
        batas = pd.Timedelta(days=JENDELA.get(_g, 45))
        us_ = x.arah * x.s
        dekat = (x.t0 - x.t0.shift(1)) <= batas
        df.loc[x.index, "P"] = np.where(dekat, us_.shift(1).fillna(0), 0.0)
        df.loc[x.index, "P3"] = np.sign(us_.shift(1).rolling(3, min_periods=3).sum().fillna(0))
    df["th"] = df.t0.dt.year
    df.to_pickle(CACHE)
    return df


ATURAN = {"NFP": ["P", "P3", "KON", "ADP", "KLAIM", "ISME", "KAL", "KALUR"], "ADP": ["P", "P3", "KON", "KLAIM"],
          "PPI": ["P", "P3", "KON", "CPI"], "RETAIL": ["P", "P3", "KON", "CPI", "MOBIL"],
          "PCE": ["P", "P3", "KON", "CPIC", "PPIC", "KALPCE"], "ISM": ["P", "P3", "KON", "CHI", "FED", "SPG"],
          "GDP": ["P", "P3", "KON", "NOW"], "JOLTS": ["P", "P3", "KON", "IND"], "CLAIMS": ["P", "P3", "KON", "KONT"],
          "KONSUMEN": ["P", "P3", "KON", "SPX", "BENSIN"]}


def main() -> None:
    df = tabel()
    L = ["# ⏱️ Semua berita USD → arah emas 1–10 detik, tutup kertas + validitas", __doc__.split("\n\n")[1], ""]
    lolos, rng = [], np.random.default_rng(5)
    for g in ATURAN:
        x = df[df.grup == g].reset_index(drop=True)
        if x.empty:
            continue
        for c in ATURAN[g]:
            if c not in x:
                x[c] = 0.0
            x[c] = x[c].fillna(0.0)
        # turunan ditetapkan sebelum melihat hasil: suara semua petunjuk khusus + P
        khusus = [c for c in ATURAN[g] if c not in ("P", "P3", "KON")]
        x["SUARA"] = np.sign(x[khusus + ["P"]].sum(axis=1))
        semua = ATURAN[g] + ["SUARA"]
        L.append(f"\n## {g} ({len(x)} rilis {x.t0.min():%Y-%m}–{x.t0.max():%Y-%m}; Nasdaq: {x.nama.value_counts().to_dict()})")
        # per_periode menerima tebakan EMAS langsung (+1 naik); PLAFON = arah USD → emas kebalikannya
        L.append("   selalu NAIK   " + per_periode(x, pd.Series(1.0, index=x.index)))
        L.append("   PLAFON        " + per_periode(x, -x.PLAFON))
        L.append("   PLAFON 1 dtk  " + per_periode(x, -x.PLAFON, (1,)))
        G = x[[f"g{h}" for h in JAUH]].fillna(0).to_numpy()
        s16, b22 = (x.th >= 2016).to_numpy(), (x.th >= 2022).to_numpy()
        hasil = {}
        for c in semua:
            tb = tetap(x, c)
            k, n = tepat(x[x.th >= 2016], tb[x.th >= 2016])
            hasil[c] = (k / n if n else 0, n)
            L.append(f"   {c:6s} angka {pct_angka(x, c)} | emas 2–10 {per_periode(x, tb)}")
        # permutasi keluarga
        cukup = [c for c in semua if ((x[c] != 0) & s16).sum() >= 40 and ((x[c] != 0) & b22).sum() >= 20]
        if cukup:
            C = {c: x[c].to_numpy() for c in cukup}
            m16, m22 = [], []
            for _ in range(N_PERM):
                Gp = G[rng.permutation(len(x))]
                m16.append(np.nanmax([hit_mentah(C[c], Gp, s16) for c in cukup]))
                m22.append(np.nanmax([hit_mentah(C[c], Gp, b22) for c in cukup]))
            m16, m22 = np.array(m16), np.array(m22)
            L.append(f"   keluarga ({len(cukup)} aturan): acak terbaik persentil 95 {np.percentile(m16, 95) * 100:.1f}% / "
                     f"{np.percentile(m22, 95) * 100:.1f}%")
            for c in cukup:
                o16, o22 = hit_mentah(C[c], G, s16), hit_mentah(C[c], G, b22)
                p16, p22 = float((m16 >= o16).mean()), float((m22 >= o22).mean())
                tb = tetap(x, c)
                k, n = tepat(x[x.th >= 2016], tb[x.th >= 2016])
                kl, nl = tepat(x[(x.th >= 2016) & (x.t0 < "2021-10-01")], tb[(x.th >= 2016) & (x.t0 < "2021-10-01")])
                kb, nb = tepat(x[x.t0 >= "2021-10-01"], tb[x.t0 >= "2021-10-01"])
                ok = n and k / n >= 0.60 and nl and kl / nl > 0.5 and nb and kb / nb > 0.5 and min(p16, p22) < 0.05
                L.append(f"     {c:6s} mentah {o16 * 100:.1f}% / {o22 * 100:.1f}% → p {p16:.3f} / {p22:.3f}"
                         f"{'  ✅ LOLOS' if ok else ''}")
                if ok:
                    lolos.append(f"{g} {c}")
    L.append("\nLOLOS (layak dipasang): " + (", ".join(lolos) or "TIDAK ADA"))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def pct_angka(x: pd.DataFrame, c: str) -> str:
    """Ketepatan tebakan ANGKA (arah kejutan utama) — untuk konteks."""
    us_ = x.arah * x.s
    m = (x[c] != 0) & (us_ != 0)
    k, n = int((x[c][m] == us_[m]).sum()), int(m.sum())
    return f"{k / n * 100:5.1f}% (n {n:3d})" if n else "    – (n   0)"


if __name__ == "__main__":
    main()
