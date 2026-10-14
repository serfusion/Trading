"""Uji 👥 sentimen orang → arah emas (dipanggil `python -m research.sentimen_orang uji`).

Aturan penilaian (ditetapkan SEBELUM melihat hasil):
- Keputusan pada waktu data terbit; target = arah emas (close) k hari kerja SESUDAHNYA. Kitco: survei terbit Jumat
  sore AS → target close Jumat berikutnya (5 hari) & Senin (1 hari). StockTwits/Wikipedia: hari h (jam NY) → close h+1 / h+5.
- Setiap aturan dilaporkan PER ARAH tebakan + pembanding SELALU-NAIK pada periode yang sama.
- Tutup kertas: tiap tahun, versi "ikut" atau "lawan" dipilih HANYA dari tahun-tahun sebelumnya (minimal 1 tahun).
- Lolos bila tutup kertas > selalu-NAIK, kedua paruh waktu searah, dan p (binomial vs laju dasar) < 0,05.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from .sentimen_orang import BARU, DIR, OUT, emas_harian, kitco_tabel, stocktwits_harian

L: list[str] = []


def say(s: str = "") -> None:
    print(s)
    L.append(s)


def p_binom(k: int, n: int, p: float) -> float:
    """P(X ≥ k), X ~ Bin(n, p) (satu sisi)."""
    if n == 0:
        return 1.0
    return float(sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def target(px: pd.Series, hari: pd.Series, k: int) -> pd.Series:
    """Arah close k hari kerja sesudah `hari` vs close `hari` (hari tanpa harga → hari kerja sebelumnya)."""
    idx = px.index
    out = []
    for h in hari:
        i = idx.searchsorted(h, side="right") - 1
        out.append(np.nan if i < 0 or i + k >= len(idx) else float(np.sign(px.iloc[i + k] - px.iloc[i])))
    return pd.Series(out, index=hari.index)


def nilai(df: pd.DataFrame, tebak: str, y: str, nama: str) -> dict:
    d = df[(df[tebak] != 0) & df[y].notna() & (df[y] != 0)]
    if len(d) < 8:
        say(f"  {nama:46s} n {len(d)} (terlalu sedikit)")
        return {}
    hit = (np.sign(d[tebak]) == d[y])
    base = (d[y] > 0).mean()
    up, dn = d[d[tebak] > 0], d[d[tebak] < 0]
    hu = (up[y] > 0).mean() if len(up) else np.nan
    hd = (dn[y] < 0).mean() if len(dn) else np.nan
    p = p_binom(int(hit.sum()), len(d), max(base, 1 - base))
    tengah = d.index[len(d) // 2]
    a, b = hit.loc[:tengah], hit.loc[tengah:].iloc[1:]
    say(f"  {nama:46s} n {len(d):3d} benar {100 * hit.mean():5.1f}% | tebak NAIK {100 * hu:5.1f}% (n {len(up)}) "
        f"TURUN {100 * hd:5.1f}% (n {len(dn)}) | selalu-NAIK {100 * base:5.1f}% | paruh {100 * a.mean():.0f}/"
        f"{100 * b.mean():.0f}% | p {p:.3f}")
    return {"n": len(d), "benar": float(hit.mean()), "naik": hu, "turun": hd, "dasar": float(base), "p": p,
            "paruh": [float(a.mean()), float(b.mean())]}


def tutup_kertas(df: pd.DataFrame, sinyal: str, y: str, nama: str) -> dict:
    """Per tahun: pilih tanda (+1 ikut / −1 lawan) dari tahun-tahun sebelumnya saja."""
    d = df[(df[sinyal] != 0) & df[y].notna() & (df[y] != 0)].copy()
    d["th"] = d.index.year if isinstance(d.index, pd.DatetimeIndex) else pd.to_datetime(d["tgl"]).dt.year
    hasil, rows = [], []
    for th in sorted(d.th.unique()):
        lalu, kini = d[d.th < th], d[d.th == th]
        if len(lalu) < 20:
            continue
        tanda = 1 if (np.sign(lalu[sinyal]) == lalu[y]).mean() >= 0.5 else -1
        h = (np.sign(kini[sinyal]) * tanda == kini[y])
        hasil.append(h)
        rows.append(f"{th}:{'ikut' if tanda > 0 else 'lawan'} {100 * h.mean():.0f}% (n {len(h)}, naik {100 * (kini[y] > 0).mean():.0f}%)")
    if not hasil:
        return {}
    h = pd.concat(hasil)
    base = (d.loc[h.index, y] > 0).mean()
    say(f"  ⤷ tutup kertas {nama}: {100 * h.mean():.1f}% (n {len(h)}) vs selalu-NAIK {100 * base:.1f}% • " + " | ".join(rows))
    return {"benar": float(h.mean()), "n": len(h), "dasar": float(base)}


def uji_kitco(px: pd.Series) -> dict:
    say("=" * 110)
    say("A. KITCO — survei mingguan: Main Street (orang umum, voting online) & Wall Street (analis)")
    t = kitco_tabel().set_index("tgl")
    say(f"   {len(t)} pekan ({t.index.min():%d %b %Y} – {t.index.max():%d %b %Y}); suara Main Street median "
        f"{t.ms_n.median():.0f} (min {t.ms_n.min()}, maks {t.ms_n.max()}); total {t.ms_n.sum():,} suara")
    say(f"   rata-rata Main Street: naik {t.ms_up.mean():.0f}% / turun {t.ms_down.mean():.0f}% / datar {t.ms_side.mean():.0f}% "
        f"— mayoritas NAIK di {100 * (t.ms_up > t.ms_down).mean():.0f}% pekan")
    t["y5"], t["y1"] = target(px, t.index.to_series(), 5), target(px, t.index.to_series(), 1)
    t["ms"] = np.sign(t.ms_up - t.ms_down)
    t["ws"] = np.sign(t.ws_up.fillna(0) - t.ws_down.fillna(0))
    t["ms_lawan"] = -t.ms
    t["ms_ekstrem"] = np.where(t.ms_up >= t.ms_up.expanding().quantile(0.8).shift(1), 1,
                               np.where(t.ms_down >= t.ms_down.expanding().quantile(0.8).shift(1), -1, 0))
    t["beda"] = np.where((t.ms != 0) & (t.ws != 0) & (t.ms != t.ws), t.ws, 0)   # orang vs analis berbeda → ikut analis
    t["sepakat"] = np.where((t.ms == t.ws), t.ms, 0)
    d_ms = t.ms_up - t.ms_down
    t["ms_berubah"] = np.sign(d_ms.diff())                                          # orang makin optimis pekan ini
    res = {"n_pekan": len(t), "mayoritas_naik": round(100 * (t.ms_up > t.ms_down).mean()), "suara": int(t.ms_n.sum())}
    for y, jk in (("y5", "1 pekan"), ("y1", "1 hari")):
        say(f" — target {jk}:")
        for c, nm in (("ms", "Main Street ikut mayoritas"), ("ms_lawan", "Main Street LAWAN mayoritas"),
                      ("ms_ekstrem", "Main Street ekstrem (P80) ikut"), ("ws", "Wall Street (analis) ikut"),
                      ("sepakat", "orang & analis sepakat"), ("beda", "beda → ikut analis"),
                      ("ms_berubah", "orang makin optimis → naik")):
            res[f"{c}_{y}"] = nilai(t, c, y, nm)
        res[f"tk_ms_{y}"] = tutup_kertas(t, "ms", y, "Main Street")
        res[f"tk_ws_{y}"] = tutup_kertas(t, "ws", y, "Wall Street")
    akhir = t.iloc[-1]
    res["terakhir"] = {"tgl": f"{t.index[-1]:%Y-%m-%d}", "n": int(akhir.ms_n), "naik": akhir.ms_up, "turun": akhir.ms_down,
                       "datar": akhir.ms_side, "ws_naik": akhir.ws_up, "ws_turun": akhir.ws_down, "ws_datar": akhir.ws_side}
    return res


def uji_stocktwits(px: pd.Series) -> dict:
    say("=" * 110)
    say("B. STOCKTWITS — pesan berlabel Bullish/Bearish (percakapan trader)")
    res = {}
    for s in ("GLD", "XAUUSD", "GC_F", "IAU", "PHYS"):
        g = stocktwits_harian(s)
        if g.empty:
            continue
        lab = g.bull + g.bear
        say(f"   {s}: {int(g.n.sum()):,} pesan ({int(lab.sum()):,} berlabel, bull {100 * g.bull.sum() / max(lab.sum(), 1):.0f}%), "
            f"{g.index.min():%d %b %Y} – {g.index.max():%d %b %Y}")
        res[s] = g
    if not res:
        return {}
    g = sum(res.values()).fillna(0) if len(res) > 1 else next(iter(res.values()))
    g = pd.concat(res.values()).groupby(level=0).sum()
    g = g[(g.bull + g.bear) >= 5]
    g["rasio"] = g.bull / (g.bull + g.bear)
    g["z"] = (g.rasio - g.rasio.rolling(20, min_periods=10).mean().shift(1)) / g.rasio.rolling(20, min_periods=10).std().shift(1)
    g["y1"], g["y5"] = target(px, g.index.to_series(), 1), target(px, g.index.to_series(), 5)
    g["ikut"] = np.sign(g.rasio - 0.5) * (abs(g.rasio - 0.5) > 0.0)
    g["lawan_z"] = np.where(g.z >= 1, -1, np.where(g.z <= -1, 1, 0))
    g["ikut_z"] = -g.lawan_z
    say(f"   gabungan: {len(g)} hari dengan ≥ 5 pesan berlabel, rasio bull median {100 * g.rasio.median():.0f}%")
    out = {"hari": len(g)}
    for y, jk in (("y1", "1 hari"), ("y5", "1 pekan")):
        say(f" — target {jk}:")
        for c, nm in (("ikut", "mayoritas bull → naik"), ("ikut_z", "lonjakan bull (z ≥ 1) → naik"),
                      ("lawan_z", "lonjakan bull (z ≥ 1) → TURUN (kontrarian)")):
            out[f"{c}_{y}"] = nilai(g, c, y, nm)
    return out


def uji_wiki(px: pd.Series) -> dict:
    say("=" * 110)
    say("C. WIKIPEDIA — perhatian publik (kunjungan harian artikel emas)")
    f = DIR / "wiki.json"
    if not f.exists():
        return {}
    w = json.loads(f.read_text(encoding="utf-8"))
    df = pd.DataFrame({a: pd.Series({pd.Timestamp(k): v for k, v in s.items()}) for a, s in w.items()}).sort_index()
    v = df.sum(axis=1)
    z = (np.log(v) - np.log(v).rolling(60, min_periods=30).mean().shift(1)) / np.log(v).rolling(60, min_periods=30).std().shift(1)
    d = pd.DataFrame({"z": z})
    d = d[d.index.dayofweek < 5]
    r5 = np.log(px).diff(5).reindex(d.index, method="ffill")
    d["arah_lalu"] = np.sign(r5)
    d["y1"], d["y5"] = target(px, d.index.to_series(), 1), target(px, d.index.to_series(), 5)
    d["ramai_lawan"] = np.where(d.z >= 2, -d.arah_lalu, 0)      # perhatian melonjak → balik arah 5 hari terakhir
    d["ramai_ikut"] = -d.ramai_lawan
    say(f"   {len(d)} hari kerja, lonjakan perhatian (z ≥ 2) {int((d.z >= 2).sum())} hari")
    out = {}
    for y, jk in (("y1", "1 hari"), ("y5", "1 pekan")):
        say(f" — target {jk}:")
        out[f"lawan_{y}"] = nilai(d, "ramai_lawan", y, "perhatian melonjak → balik arah")
        out[f"ikut_{y}"] = nilai(d, "ramai_ikut", y, "perhatian melonjak → lanjut arah")
        d["lama"] = d.index < pd.Timestamp("2021-10-01")
        for nm, m in (("LAMA <Okt21", d.lama), ("BARU", ~d.lama)):
            nilai(d[m], "ramai_lawan", y, f"   {nm}: balik arah")
    return out


def uji_cot(px: pd.Series) -> dict:
    say("=" * 110)
    say("D. COT CFTC — posisi TRADER KECIL (non-reportable = ritel futures emas) vs managed money; mingguan sejak 2006")
    from .sentimen_orang import ROOT
    c = pd.DataFrame(json.loads((ROOT / "data" / "research" / "eksternal" / "cot_XAUUSD.json").read_text(encoding="utf-8")))
    from .eksternal_cot import SHUTDOWN
    rep = pd.to_datetime(c.report_date_as_yyyy_mm_dd)
    c["tgl"] = rep + pd.Timedelta(days=3)                                                # terbit Jumat sore
    for a, b, rel in SHUTDOWN:                                                           # shutdown: terbit terlambat
        c.loc[(rep >= a) & (rep <= b), "tgl"] = pd.Timestamp(rel)
    c = c.sort_values("tgl").drop_duplicates("tgl", keep="last")
    f = lambda a: c[a].astype(float)                                                     # noqa: E731
    c["kecil"] = (f("nonrept_positions_long_all") - f("nonrept_positions_short_all")) / (
        f("nonrept_positions_long_all") + f("nonrept_positions_short_all"))
    c["mm"] = (f("m_money_positions_long_all") - f("m_money_positions_short_all")) / (
        f("m_money_positions_long_all") + f("m_money_positions_short_all"))
    c = c.set_index("tgl").sort_index()
    out = {"terakhir": {"tgl": f"{c.index[-1]:%Y-%m-%d}", "kecil_long": float(
        100 * c.nonrept_positions_long_all.astype(float).iloc[-1] / (c.nonrept_positions_long_all.astype(float).iloc[-1]
                                                                      + c.nonrept_positions_short_all.astype(float).iloc[-1]))}}
    say(f"   {len(c)} pekan {c.index.min():%Y}–{c.index.max():%d %b %Y}; trader kecil kini {out['terakhir']['kecil_long']:.0f}% long")
    for k in ("kecil", "mm"):
        z = (c[k] - c[k].rolling(52, min_periods=26).mean().shift(1)) / c[k].rolling(52, min_periods=26).std().shift(1)
        c[f"{k}_lawan"] = np.where(z >= 1.5, -1, np.where(z <= -1.5, 1, 0))
        c[f"{k}_ikut"] = np.sign(c[k].diff())
    c["y5"], c["y20"] = target(px, c.index.to_series(), 5), target(px, c.index.to_series(), 20)
    lama = c.index < BARU
    for y, jk in (("y5", "1 pekan"), ("y20", "1 bulan")):
        say(f" — target {jk}:")
        for col, nm in (("kecil_lawan", "trader kecil ekstrem (z ±1,5) → LAWAN"), ("kecil_ikut", "trader kecil menambah long → naik"),
                        ("mm_lawan", "managed money ekstrem → LAWAN"), ("mm_ikut", "managed money menambah long → naik")):
            out[f"{col}_{y}"] = nilai(c, col, y, nm)
            nilai(c[lama], col, y, "   LAMA < Okt 2021")
            nilai(c[~lama], col, y, "   BARU")
        out[f"tk_kecil_{y}"] = tutup_kertas(c, "kecil_lawan", y, "trader kecil ekstrem")
    return out


def uji_trends(px: pd.Series) -> dict:
    say("=" * 110)
    say("E. GOOGLE TRENDS — pencarian 'buy gold' vs 'sell gold' (niat orang sedunia), mingguan 2004–2026")
    t = json.loads((DIR / "trends.json").read_text(encoding="utf-8"))
    rows = {}
    for w in t["mingguan"]:                                      # jendela berikutnya menimpa yang tumpang tindih
        d = pd.DataFrame(w["data"], index=["buy", "sell", "harga"]).T
        d.index = pd.to_datetime(d.index)
        d = d.astype(float)
        d["rasio"] = d.buy / (d.buy + d.sell).replace(0, np.nan)
        d["zr"] = (d.rasio - d.rasio.rolling(26, min_periods=13).mean().shift(1)) / d.rasio.rolling(26, min_periods=13).std().shift(1)
        d["zh"] = (np.log1p(d.harga) - np.log1p(d.harga).rolling(26, min_periods=13).mean().shift(1)) / \
            np.log1p(d.harga).rolling(26, min_periods=13).std().shift(1)
        for i, r in d.iterrows():
            rows[i] = r
    d = pd.DataFrame(rows).T.sort_index()
    d.index = d.index + pd.Timedelta(days=8)                     # minggu Minggu–Sabtu → keputusan close Senin sesudahnya
    say(f"   {len(d)} pekan; rata-rata rasio buy/(buy+sell) {100 * d.rasio.mean():.0f}% (orang lebih sering mencari 'buy')")
    r4 = np.log(px).diff(20).reindex(d.index, method="ffill")
    d["y5"], d["y20"] = target(px, d.index.to_series(), 5), target(px, d.index.to_series(), 20)
    d["buy_lawan"] = np.where(d.zr >= 1.5, -1, np.where(d.zr <= -1.5, 1, 0))
    d["buy_ikut"] = -d.buy_lawan
    d["ramai_balik"] = np.where(d.zh >= 2, -np.sign(r4), 0)
    lama = d.index < BARU
    out = {}
    for y, jk in (("y5", "1 pekan"), ("y20", "1 bulan")):
        say(f" — target {jk}:")
        for col, nm in (("buy_lawan", "'buy gold' melonjak → LAWAN (turun)"), ("buy_ikut", "'buy gold' melonjak → ikut (naik)"),
                        ("ramai_balik", "'gold price' melonjak → balik arah 1 bln")):
            out[f"{col}_{y}"] = nilai(d, col, y, nm)
            nilai(d[lama], col, y, "   LAMA < Okt 2021")
            nilai(d[~lama], col, y, "   BARU")
        out[f"tk_buy_{y}"] = tutup_kertas(d, "buy_lawan", y, "'buy gold'")
    akhir = d.iloc[-1]
    out["terakhir"] = {"rasio": float(akhir.rasio), "z": float(akhir.zr) if pd.notna(akhir.zr) else None}
    return out


def uji_konsumen(px: pd.Series) -> dict:
    say("=" * 110)
    say("F. SURVEI KONSUMEN (kepuasan/keyakinan konsumen AS, bulanan) → emas 1 bulan")
    k = json.loads((DIR / "konsumen.json").read_text(encoding="utf-8"))
    out = {}
    for s, nm in (("UMCSENT", "UMich sentimen konsumen"), ("CSCICP03USM665S", "OECD keyakinan konsumen AS"),
                  ("MICH", "UMich ekspektasi inflasi")):
        v = pd.Series({pd.Timestamp(a): b for a, b in k[s].items()}).sort_index()
        d = pd.DataFrame({"v": v})
        d.index = d.index + pd.offsets.MonthBegin(1) + pd.Timedelta(days=1)   # angka bulan M final → awal bulan M+1
        d = d[d.index >= "2004-01-01"]
        d["y20"] = target(px, d.index.to_series(), 20)
        d["turun_naik"] = -np.sign(d.v.diff())            # konsumen makin pesimis → emas naik
        lama = d.index < BARU
        say(f" {nm} ({s}): {len(d)} bulan")
        out[s] = nilai(d, "turun_naik", "y20", f"{nm} turun → emas naik")
        nilai(d[lama], "turun_naik", "y20", "   LAMA < Okt 2021")
        nilai(d[~lama], "turun_naik", "y20", "   BARU")
        tutup_kertas(d, "turun_naik", "y20", nm)
    return out


def _pc(x) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.0f}%"


def simpan_cloud(h: dict) -> None:
    """cloud/api/sentimen.json — ringkasan uji untuk poin 👥 di bawah XAU (_sentimen.py). INFO saja."""
    from .sentimen_orang import ROOT
    k, c, t = h.get("kitco") or {}, h.get("cot") or {}, h.get("trends") or {}
    ms, kl = k.get("ms_y5") or {}, c.get("kecil_lawan_y20") or {}
    ringkas = [
        f"Kitco Main Street {k.get('n_pekan', '?')} pekan: mayoritas orang memilih NAIK di {k.get('mayoritas_naik', '?')}% pekan → "
        f"sama dengan selalu-NAIK (benar {_pc(ms.get('benar'))} vs selalu-NAIK {_pc(ms.get('dasar'))})",
        f"COT trader kecil ekstrem → lawan arah 1 bulan: {_pc(kl.get('benar'))} (n {kl.get('n', '?')}) — hanya bekerja sebelum "
        f"Okt 2021, sejak itu kalah dari selalu-NAIK",
        "Google Trends 'buy/sell gold', StockTwits, Wikipedia, survei konsumen UMich/OECD: 48–56%, tidak lolos",
    ]
    out = {"dibuat": f"{pd.Timestamp.now('UTC'):%Y-%m-%d}", "putusan_singkat": "info (diuji: tidak menambah ketepatan)",
           "ringkas": ringkas, "docs": "docs/SENTIMEN_ORANG.md"}
    (ROOT / "cloud" / "api" / "sentimen.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                                                          encoding="utf-8")


def main() -> None:
    L.clear()
    px = emas_harian()
    say(f"👥 SENTIMEN ORANG → ARAH EMAS (dibuat {pd.Timestamp.utcnow():%d %b %Y %H:%M} UTC; emas harian Twelve Data "
        f"{px.index.min():%Y}–{px.index.max():%d %b %Y})")
    say("Benar = arah close emas k hari kerja sesudah data terbit sama dengan tebakan. p = binomial vs laju dasar terbesar.")
    hasil = {"kitco": uji_kitco(px), "stocktwits": uji_stocktwits(px), "wiki": uji_wiki(px), "cot": uji_cot(px),
             "trends": uji_trends(px), "konsumen": uji_konsumen(px)}
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    simpan_cloud(hasil)
    (DIR / "hasil.json").write_text(json.dumps(hasil, default=lambda o: None if isinstance(o, float) and math.isnan(o)
                                               else (o.tolist() if hasattr(o, "tolist") else str(o)), indent=1),
                                    encoding="utf-8")


if __name__ == "__main__":
    main()
