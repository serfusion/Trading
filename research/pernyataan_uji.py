"""🗣️ Pernyataan orang penting SEBELUM rilis berita → arah XAU 1–10 detik setelah rilis.

python -m research.pernyataan_uji         → docs/eksternal/hasil_pernyataan_uji.txt

Permintaan pengguna 10 Okt 2026: "cari juga statement orang penting / petinggi supaya bisa meningkatkan persentase".
Sumber dengan ARSIP lengkap (tanpa arsip tidak bisa diuji):
  • Tweet @realDonaldTrump masa jabatan 1 (20 Jan 2017 – 8 Jan 2021; MarkHershey/CompleteTrumpTweetsArchive, waktu
    persis dari ID tweet)  • Truth Social @realDonaldTrump 14 Feb 2022 – kini (arsip CNN ix.cnn.io).
  Dasar: Presiden/Dewan Penasihat Ekonomi menerima angka resmi (mis. laporan kerja) SEHARI sebelum rilis (OMB Directive
  No. 3) → unggahan pagi/malam sebelum rilis bisa membocorkan arah (contoh terkenal 1 Jun 2018 "Looking forward to seeing
  the employment numbers at 8:30"). 2022–2024 Trump BUKAN presiden (tidak menerima angka) = PEMBANDING (plasebo).
ATURAN (ditetapkan sebelum melihat hasil), unggahan di jendela t0−16 jam … t0−1 menit:
  EKON   berita aktivitas/kerja (NFP, Retail, GDP, ISM, ADP, JOLTS, klaim, konsumen, durable): unggahan bertopik ekonomi/
         lapangan kerja, skor = kata positif − kata negatif; > 0 → angka LEBIH BAIK dari konsensus → emas TURUN
  HARGA  berita inflasi (CPI, PPI, PCE): unggahan bertopik harga/inflasi, nada positif ("harga turun", "inflasi hilang")
         → angka DI BAWAH konsensus → emas NAIK
  ANGKA  unggahan yang menyebut angka/laporan/"looking forward"/"8:30"/"this morning" + topik ekonomi: positif → emas TURUN
  FED    unggahan menyerang Fed/Powell/suku bunga: arah dipilih dari masa jabatan 1, dinilai masa jabatan 2
Dinilai: ketepatan arah emas detik 2/3/5/10 (tick Exness, cadangan Dukascopy) dan ketepatan arah kejutan angka.
Periode: JABATAN-1 (2017–2020), PLASEBO (2022–2024, bukan presiden), JABATAN-2 (2025–2026).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "research" / "eksternal" / "pernyataan"
OUT = ROOT / "docs" / "eksternal" / "hasil_pernyataan_uji.txt"
HH = (2, 3, 5, 10)

EKON = r"\b(jobs?|employment|unemployment|hiring|workers?|economy|economic|gdp|growth|manufacturing|retail|consumers?|" \
       r"stock market|dow|nasdaq|s&p|payrolls?|wages?)\b"
HARGA = r"\b(inflation|prices?|cpi|cost of living|gas|gasoline|eggs|groceries|grocery|affordab\w*)\b"
POS = r"\b(great|greatest|record|records|best|strong|strongest|booming|boom|incredible|fantastic|tremendous|highest|" \
      r"historic|amazing|beautiful|looking forward|winning|soaring|success|thriving|way up|way down|lowest|down)\b"
NEG = r"\b(bad|terrible|disaster|weak|slow|slowing|recession|rigged|fake|fraud|manipulated|too late|crash|collapse|" \
      r"inherited|biden|sleepy joe|worst|failing|high)\b"
ANGKA = r"(numbers|jobs report|employment numbers|looking forward|8:30|this morning|report today|today's report)"
FED = r"\b(fed|federal reserve|powell|too late|interest rates?|rate cuts?|cut rates|lower rates)\b"
AKTIF = {"NFP", "RETAIL", "GDP", "ISM", "ADP", "JOLTS", "CLAIMS", "KONSUMEN", "DURABLE", "MANUFAKTUR", "PMI"}
INFLASI = {"CPI", "PPI", "PCE"}


def _bersih(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')


def unggahan() -> pd.DataFrame:
    t = pd.read_csv(D / "trump_tweets_in_office.csv", skipinitialspace=True, quotechar='"', engine="python")
    ids = t["Tweet URL"].str.extract(r"status/(\d+)")[0].astype("int64")
    waktu = pd.to_datetime(ids.map(lambda i: (int(i) >> 22) + 1288834974657), unit="ms", utc=True)   # dari ID (snowflake)
    a = pd.DataFrame({"waktu": waktu, "teks": t["Tweet Text"].astype(str), "sumber": "twitter"})
    s = pd.read_parquet(D / "truth_archive.parquet")
    b = pd.DataFrame({"waktu": pd.to_datetime(s.created_at, utc=True), "teks": s.content.map(_bersih),
                      "sumber": "truth"})
    x = pd.concat([a, b], ignore_index=True).sort_values("waktu").reset_index(drop=True)
    x["low"] = x.teks.str.lower()
    for nm, pat in (("ekon", EKON), ("harga", HARGA), ("angka", ANGKA), ("fed", FED)):
        x[nm] = x.low.str.contains(pat, regex=True)
    x["pos"] = x.low.str.count(POS)
    x["neg"] = x.low.str.count(NEG)
    return x


def periode(t: pd.Timestamp) -> str:
    if pd.Timestamp("2017-01-20", tz="UTC") <= t < pd.Timestamp("2021-01-09", tz="UTC"):
        return "JABATAN-1"
    if pd.Timestamp("2022-02-14", tz="UTC") <= t < pd.Timestamp("2025-01-20", tz="UTC"):
        return "PLASEBO"
    if t >= pd.Timestamp("2025-01-20", tz="UTC"):
        return "JABATAN-2"
    return ""


def fitur(df: pd.DataFrame, u: pd.DataFrame) -> pd.DataFrame:
    rows = []
    wt = u.waktu.dt.tz_convert(None).to_numpy()
    for r in df.itertuples():
        t = r.t0
        per = periode(t)
        if not per:
            continue
        i0 = np.searchsorted(wt, np.datetime64((t - pd.Timedelta(hours=16)).tz_convert(None)), side="left")
        i1 = np.searchsorted(wt, np.datetime64((t - pd.Timedelta(minutes=1)).tz_convert(None)), side="right")
        w = u.iloc[i0:i1]
        x = {"t0": t, "grup": r.grup, "periode": per, "n_post": len(w)}
        e = w[w.ekon]
        h = w[w.harga]
        x["EKON"] = -np.sign((e.pos - e.neg).sum()) if r.grup in AKTIF and len(e) else 0.0
        x["HARGA"] = np.sign((h.pos - h.neg).sum()) if r.grup in INFLASI and len(h) else 0.0
        a = w[w.angka & (w.ekon | w.harga)]
        if len(a):
            sk = np.sign((a.pos - a.neg).sum())
            x["ANGKA"] = (sk if r.grup in INFLASI else -sk) if (r.grup in INFLASI or r.grup in AKTIF) else 0.0
        else:
            x["ANGKA"] = 0.0
        x["FED"] = 1.0 if w.fed.any() else 0.0
        rows.append(x)
    return pd.DataFrame(rows)


def nilai(pred: np.ndarray, x: pd.DataFrame) -> dict:
    out = {}
    for h in HH:
        y = x[f"y{h}_XAU_EXNESS"].to_numpy()
        y = np.where(np.isnan(y), x[f"y{h}_XAU"].to_numpy(), y)
        m = (pred != 0) & ~np.isnan(y) & (y != 0)
        ok = np.sign(pred[m]) == np.sign(y[m])
        out[h] = (int(ok.sum()), int(m.sum()))
    k = sum(v[0] for v in out.values())
    n = sum(v[1] for v in out.values())
    n5 = out[5][1]
    return {"benar": k / n * 100 if n else np.nan, "n": n5, "p": float(binom.sf(out[5][0] - 1, n5, .5)) if n5 else 1.0}


def main() -> None:
    from .news_detik import events
    from .pra_xau_semua import bangun
    u = unggahan()
    d = bangun()
    ev = events()[["time", "bias"]].rename(columns={"time": "t0"})
    d = d.merge(ev, on="t0", how="left")
    fx = fitur(d, u)
    x = fx.merge(d[["t0", "bias"] + [c for c in d.columns if c.startswith("y")]], on="t0", how="left")
    L = ["# 🗣️ Pernyataan Trump sebelum rilis → arah XAU 2–10 dtk", __doc__.split("\n\n")[1], "",
         f"Unggahan: {len(u)} ({(u.sumber == 'twitter').sum()} tweet 2017–2021, {(u.sumber == 'truth').sum()} Truth Social "
         f"{u[u.sumber == 'truth'].waktu.min():%Y-%m-%d} … {u.waktu.max():%Y-%m-%d})",
         "Rilis dengan data emas per periode: " + ", ".join(f"{k} {v}" for k, v in x.periode.value_counts().items())]
    for f in ("EKON", "HARGA", "ANGKA"):
        L.append(f"\n## {f}")
        for per in ("JABATAN-1", "PLASEBO", "JABATAN-2"):
            z = x[x.periode == per]
            pred = z[f].fillna(0).to_numpy()
            e = nilai(pred, z)
            m = (pred != 0) & z.bias.notna() & (z.bias != 0)
            ang = (np.sign(pred[m]) == np.sign(z.bias[m])).mean() * 100 if m.sum() else np.nan
            L.append(f"   {per:10s} emas 2–10 dtk {e['benar']:.1f}% (n {e['n']}, p {e['p']:.3f}) • arah kejutan cocok "
                     f"{ang:.0f}% (n {int(m.sum())})")
    # FED: arah dari JABATAN-1, dinilai JABATAN-2 & PLASEBO
    L.append("\n## FED (ada unggahan menyerang Fed/suku bunga di jendela) → arah emas dipilih dari JABATAN-1")
    z1 = x[x.periode == "JABATAN-1"]
    naik = []
    for h in HH:
        y = z1[f"y{h}_XAU_EXNESS"].where(z1[f"y{h}_XAU_EXNESS"].notna(), z1[f"y{h}_XAU"])
        m = (z1.FED == 1) & y.notna() & (y != 0)
        naik.append((y[m] > 0).mean())
    arah = 1.0 if np.nanmean(naik) >= 0.5 else -1.0
    for per in ("JABATAN-1", "PLASEBO", "JABATAN-2"):
        z = x[x.periode == per]
        e = nilai(z.FED.to_numpy() * arah, z)
        L.append(f"   {per:10s} emas {'NAIK' if arah > 0 else 'TURUN'} benar {e['benar']:.1f}% (n {e['n']}, p {e['p']:.3f})")
    # contoh unggahan ANGKA (bukti)
    L.append("\n## Contoh unggahan ANGKA di jendela sebelum rilis")
    ua = u[u.angka & (u.ekon | u.harga)]
    for r in x[x.ANGKA != 0].itertuples():
        w = ua[(ua.waktu >= r.t0 - pd.Timedelta(hours=16)) & (ua.waktu < r.t0 - pd.Timedelta(minutes=1))]
        for p in w.itertuples():
            y5 = getattr(r, "y5_XAU_EXNESS")
            y5 = y5 if y5 == y5 else getattr(r, "y5_XAU")
            L.append(f"   {r.t0:%Y-%m-%d %H:%M} {r.grup:8s} tebak emas {'NAIK' if r.ANGKA > 0 else 'TURUN'} | emas 5 dtk "
                     f"{y5:+.2f} | {p.waktu:%H:%M} UTC: {p.teks[:110]}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    x.to_parquet(D / "pernyataan_fitur.parquet")
    print("\n".join(L))


# ---------------------------------------------------------------- pidato pejabat Fed (Dewan Gubernur, 2006–2026)
HAWK = r"(inflation pressures?|upside risks? to inflation|tighten\w*|raise rates|rate increases?|higher rates|restrictive|" \
       r"further increases|overheat\w*|elevated inflation|persistent inflation|price pressures?|hikes?|vigilant|" \
       r"inflation (?:remains|is) (?:too )?high|reduce (?:the )?balance sheet)"
DOVE = r"(accommodative|accommodation|rate cuts?|cut rates|lower rates|easing|downside risks?|patient|patience|slack|" \
       r"weakness|support the economy|gradual\w*|below (?:our )?(?:2 percent )?target|too low|softening|labor market " \
       r"(?:has )?(?:weakened|cooled))"


def unduh_fed() -> None:
    """Teks pidato Dewan Gubernur Fed (federalreserve.gov/json/ne-speeches.json). File .txt tidak di-commit (.gitignore)
    → diunduh ulang bila belum ada. Situs menolak User-Agent bawaan urllib (403), jadi memakai User-Agent curl."""
    import json
    import time
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    fd = D / "fed"
    fd.mkdir(parents=True, exist_ok=True)
    hdr = {"User-Agent": "curl/8.5.0", "Accept": "*/*"}

    def ambil(url: str) -> bytes:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=40) as r:
            return r.read()
    if not (fd / "daftar.json").exists():
        src = json.loads(ambil("https://www.federalreserve.gov/json/ne-speeches.json").decode("utf-8-sig"))
        (fd / "daftar.json").write_text(json.dumps([x for x in src if isinstance(x, dict) and x.get("l")],
                                                   ensure_ascii=False), encoding="utf-8")

    def satu(x: dict) -> None:
        f = fd / x["l"].rsplit("/", 1)[-1].replace(".htm", ".txt")
        for k in range(3):
            if f.exists():
                return
            try:
                html = ambil("https://www.federalreserve.gov" + x["l"]).decode("utf-8", "ignore")
                m = re.search(r'<div[^>]*id="article"[^>]*>(.*?)<div[^>]*id="lastUpdate"', html, re.S)
                f.write_text(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1) if m else html)), encoding="utf-8")
            except Exception:  # noqa: BLE001
                time.sleep(2 * (k + 1))
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(satu, json.loads((fd / "daftar.json").read_text(encoding="utf-8"))))


def pidato_fed() -> pd.DataFrame:
    import json
    fd = D / "fed"
    unduh_fed()
    rows = []
    for x in json.loads((fd / "daftar.json").read_text(encoding="utf-8")):
        f = fd / x["l"].rsplit("/", 1)[-1].replace(".htm", ".txt")
        if not f.exists():
            continue
        teks = f.read_text(encoding="utf-8").lower()
        h, d = len(re.findall(HAWK, teks)), len(re.findall(DOVE, teks))
        tgl = x["d"] if ":" in x["d"] else x["d"] + " 11:59:00 PM"     # tanpa jam → akhir hari (tanpa look-ahead)
        t = pd.Timestamp(pd.to_datetime(tgl, format="%m/%d/%Y %I:%M:%S %p")).tz_localize(
            "America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")
        rows.append({"waktu": t, "siapa": x.get("s", ""), "hawk": h, "dove": d, "skor": (h - d) / (h + d + 1)})
    return pd.DataFrame(rows).dropna(subset=["waktu"]).sort_values("waktu").reset_index(drop=True)


def fed() -> list[str]:
    """Nada pidato Fed 7 hari sebelum rilis (rata-rata skor hawkish−dovish, |x| ≥ 0,1) → arah emas; arah dipilih di
    LAMA (< Okt 2021), dinilai BARU; per grup berita (SEMUA, CPI, NFP, PPI, RETAIL, ISM, PCE)."""
    from .news_detik import NEW
    from .pra_xau_semua import bangun
    p = pidato_fed()
    d = bangun()
    wt = p.waktu.dt.tz_convert(None).to_numpy()
    nada = []
    for t in d.t0:
        i0 = np.searchsorted(wt, np.datetime64((t - pd.Timedelta(days=7)).tz_convert(None)))
        i1 = np.searchsorted(wt, np.datetime64((t - pd.Timedelta(minutes=1)).tz_convert(None)))
        sk = p.skor.iloc[i0:i1]
        nada.append(float(np.sign(sk.mean())) if len(sk) and abs(sk.mean()) >= 0.1 else 0.0)
    d["NADA"] = nada
    L = [f"\n## Pidato pejabat Fed ({len(p)} pidato {p.waktu.min():%Y}–{p.waktu.max():%Y}): nada 7 hari sebelum rilis",
         f"   terisi {int((d.NADA != 0).sum())} rilis (hawkish {int((d.NADA > 0).sum())}, dovish {int((d.NADA < 0).sum())})"]
    t = pd.DatetimeIndex(d.t0.to_numpy())
    for g in ("SEMUA", "CPI", "NFP", "PPI", "RETAIL", "ISM", "PCE", "CLAIMS"):
        x = d if g == "SEMUA" else d[d.grup == g]
        tt = pd.DatetimeIndex(x.t0.to_numpy())
        v = x.NADA.to_numpy()
        hasil = []
        for h in HH:
            y = x[f"y{h}_XAU_EXNESS"].to_numpy()
            y = np.where(np.isnan(y), x[f"y{h}_XAU"].to_numpy(), y)
            m = (v != 0) & ~np.isnan(y) & (y != 0)
            hasil.append((np.sign(v[m]) == np.sign(y[m]), tt[m]))
        ok_l = np.concatenate([o[tm < NEW] for o, tm in hasil])
        arah = 1.0 if (ok_l.mean() if len(ok_l) else 0.5) >= 0.5 else -1.0      # hawkish → emas naik (+1) / turun (−1)
        lama = np.concatenate([(o if arah > 0 else ~o)[tm < NEW] for o, tm in hasil])
        baru = np.concatenate([(o if arah > 0 else ~o)[tm >= NEW] for o, tm in hasil])
        n5 = int((hasil[2][1] >= NEW).sum())
        kb = int(((hasil[2][0] if arah > 0 else ~hasil[2][0])[hasil[2][1] >= NEW]).sum())
        L.append(f"   {g:7s} hawkish → emas {'NAIK' if arah > 0 else 'TURUN'}: LAMA {lama.mean() * 100 if len(lama) else float('nan'):.1f}% "
                 f"(n {int((hasil[2][1] < NEW).sum())}) → BARU {baru.mean() * 100 if len(baru) else float('nan'):.1f}% (n {n5}, "
                 f"p {binom.sf(kb - 1, n5, .5) if n5 else 1:.3f})")
    return L


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["fed"]:
        L = fed()
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(L) + "\n")
        print("\n".join(L))
    else:
        main()
