"""Uji sistem "Muse" (unggahan pengguna 8 Okt 2026) terhadap sinyal 💰 kita — python -m research.muse_uji [filter|m5|berita|paxg]

Isi unggahan: alert XAUUSD M5 → Telegram, pemicu breakout Donchian H1 + filter tren (H4 & EMA 20/50), jurnal & review
mingguan, backtest 9 bulan PF 1,38; data Twelve Data (M5+H1), cadangan Kraken PAXGUSD, berita Finnhub (kata kunci
NFP/CPI/FOMC/Powell), kalender FRED, riset Binance PAXGUSDT M5. Inti (Donchian H1 + tren H4) SUDAH dipakai sinyal 💰
kita (_core: Donchian H1 + filter H4 EMA50 untuk XAU). Yang diuji di sini = unsur yang BERBEDA:
  filter : arah EMA20 vs EMA50 di H1 / H4 (searah sinyal) pada sinyal yang benar-benar dikirim cloud (replay kode cloud
           asli, data/research/eksternal/verifikasi/cloud_<ASET>.csv, TP1 0,7R + spread asli)
  m5     : entry saat candle M5 menutup di luar channel (lebih awal) vs entry kita di open H1 berikutnya
  berita : lewati sinyal di sekitar berita USD dampak tinggi (seperti peringatan kata kunci Finnhub)
  paxg   : PAXG (Kraken/Binance) sebagai cadangan feed XAU — seberapa sama sinyalnya
Aturan pasang (sama dengan riset lain): lebih baik di LAMA (< Okt 2021) DAN BARU, WR & profit naik, DD tidak memburuk,
mayoritas tahun searah. Selalu laporkan LAMA & BARU.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
VER = ROOT / "data" / "research" / "eksternal" / "verifikasi"
OUT = ROOT / "docs" / "eksternal" / "hasil_muse.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
KEY = {"XAU": "XAUUSD", "BTC": "BTCUSD"}


def stat(d: pd.DataFrame, col: str = "r") -> dict:
    if d.empty:
        return {"n": 0}
    d = d.sort_values("t_close")
    r = d[col].to_numpy()
    eq = np.cumsum(r)
    dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    th = d.groupby(d.t_close.dt.year)[col].sum()
    return {"n": len(r), "wr": (r > 0).mean() * 100, "avg": r.mean(), "tot": r.sum(), "pf": pos / neg if neg else np.inf,
            "dd": dd, "th": (th > 0).mean() * 100}


def fmt(s: dict) -> str:
    if not s.get("n"):
        return "n 0"
    return (f"n {s['n']:4} | WR {s['wr']:4.1f}% | {s['avg']:+.3f}R | total {s['tot']:+7.1f}R | PF {s['pf']:.2f} | "
            f"DD {s['dd']:+6.1f}R | tahun + {s['th']:.0f}%")


def load(name: str) -> pd.DataFrame:
    d = pd.read_csv(VER / f"cloud_{name}.csv", parse_dates=["t_signal", "t_close"])
    for c in ("t_signal", "t_close"):
        d[c] = pd.to_datetime(d[c], utc=True)
    return d


def h1(name: str) -> pd.DataFrame:
    from .eksternal import asset
    df = asset(KEY[name]).b.df
    return df[df.high > df.low]


def ema_cols(df: pd.DataFrame, rule: str | None) -> pd.DataFrame:
    """EMA20/50 di H1 (rule None) atau resample (mis. '4h'); index = WAKTU SELESAI candle (tanpa look-ahead)."""
    x = df if rule is None else df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    step = pd.Timedelta(hours=1) if rule is None else pd.Timedelta(rule)
    out = pd.DataFrame({"close": x.close, "e20": x.close.ewm(span=20, adjust=False).mean(),
                        "e50": x.close.ewm(span=50, adjust=False).mean()})
    out.index = out.index + step
    return out


def asof(e: pd.DataFrame, t: pd.Series) -> pd.DataFrame:
    i = e.index.searchsorted(t.to_numpy(), side="right") - 1
    v = e.iloc[np.clip(i, 0, None)].to_numpy().astype(float).copy()
    v[i < 0] = np.nan
    return pd.DataFrame(v, columns=e.columns, index=t.index)


def tambah_filter(name: str, d: pd.DataFrame) -> pd.DataFrame:
    df = h1(name)
    buy = (d.dir == "BUY").to_numpy()
    for lab, rule in (("h1", None), ("h4", "4h")):
        e = asof(ema_cols(df, rule), d.t_signal)
        up = (e.e20 > e.e50).to_numpy()
        d[f"{lab}_ema"] = np.where(buy, up, ~up)                          # EMA20 vs EMA50 searah sinyal
        above = ((e.close > e.e20) & (e.close > e.e50)).to_numpy()
        below = ((e.close < e.e20) & (e.close < e.e50)).to_numpy()
        d[f"{lab}_harga"] = np.where(buy, above, below)                   # harga di atas/bawah kedua EMA
    d["h1h4_ema"] = d.h1_ema & d.h4_ema
    return d


FILTERS = ("h1_ema", "h4_ema", "h1h4_ema", "h1_harga", "h4_harga")


def uji_filter() -> list[str]:
    L = ["## Uji 1 — filter EMA 20/50 pada sinyal yang DIKIRIM cloud (replay kode cloud asli, TP1 0,7R, spread asli)",
         "(pasca-saring: sinyal yang tidak lolos dibuang; efek 'slot kosong' diuji terpisah di replay penuh bila lolos)", ""]
    for name in ("XAU", "BTC"):
        d = tambah_filter(name, load(name))
        for lab, part in (("utama", d[~d.lapis]), ("lapisan", d[d.lapis])):
            if part.empty:
                continue
            L.append(f"### {name} — sinyal {lab}")
            for per, m in (("LAMA", part.t_signal < SPLIT), ("BARU", part.t_signal >= SPLIT)):
                x = part[m]
                L.append(f"  {per} bawaan            : {fmt(stat(x))}")
                for f in FILTERS:
                    L.append(f"  {per} + {f:15}: {fmt(stat(x[x[f]]))}")
                    L.append(f"  {per}   dibuang {f:9}: {fmt(stat(x[~x[f]]))}")
            L.append("")
    return L


def xau_intrabar() -> pd.DataFrame:
    """M5 (Agu 2020+) bila ada, selain itu M15 (2012–2022): candle di dalam jam breakout."""
    from .event_stats import dataset
    m15 = dataset("m15_2012")[0]
    m5 = pd.concat([dataset("m5_2020")[0], dataset("m5_2025")[0]])
    m5 = m5[~m5.index.duplicated()].sort_index()
    m15 = m15[m15.index < m5.index[0]]
    return pd.concat([m15, m5]).sort_index()


def uji_m5() -> list[str]:
    """Entry saat candle M5/M15 menutup di luar channel H1 (lebih awal) vs entry kita (open H1 berikutnya).
    (a) sinyal yang terkonfirmasi: entry lebih awal → R baru dengan SL & harga keluar yang sama;
    (b) breakout palsu: M5 tembus tetapi H1 menutup kembali di dalam channel → posisi ditutup di close H1 itu (rugi);
        jumlahnya diskalakan dengan rasio sinyal dikirim / breakout terkonfirmasi (kategori 💰 tidak diketahui untuk
        breakout palsu)."""
    d = load("XAU")
    d = d[~d.lapis].copy()
    df = h1("XAU")
    ib = xau_intrabar()
    hi, lo, cl = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    idx = df.index
    tr = np.maximum(hi - lo, np.maximum(abs(hi - np.r_[cl[0], cl[:-1]]), abs(lo - np.r_[cl[0], cl[:-1]])))
    atr = pd.Series(tr, index=idx).rolling(20).mean().to_numpy()
    sets = {f"T{a}/{b}": a for a, b in [(40, 15), (55, 20), (80, 30), (100, 40), (120, 50)]}
    ib_t = ib.index
    rows = []
    # (a) sinyal terkonfirmasi
    for r in d.itertuples():
        n = sets.get(r.set)
        bar = r.t_signal.floor("h") - pd.Timedelta(hours=1)
        k = idx.searchsorted(bar)
        if n is None or k >= len(idx) or idx[k] != bar or k < n + 1:
            continue
        sgn = 1 if r.dir == "BUY" else -1
        lvl = hi[k - n:k].max() if sgn > 0 else lo[k - n:k].min()
        a, b = ib_t.searchsorted(bar), ib_t.searchsorted(bar + pd.Timedelta(hours=1))
        x = ib.close.to_numpy()[a:b]
        hit = np.nonzero((x - lvl) * sgn > 0)[0]
        if not len(hit):
            continue
        e5 = x[hit[0]]
        gain = (r.entry - e5) * sgn                       # harga lebih baik (+) bila entry lebih awal
        risk_new = r.risk + gain
        if risk_new <= 0:
            continue
        r_new = -1.0 if r.r <= -0.999 else (r.r * r.risk + gain) / risk_new
        rows.append({"t": r.t_signal, "t_close": r.t_close, "r": r.r, "r_m5": r_new, "gain_r": gain / r.risk,
                     "src": "M5" if bar >= pd.Timestamp("2020-08-21", tz="UTC") else "M15"})
    a_ = pd.DataFrame(rows)
    # (b) breakout palsu untuk set yang sedang kosong (tanpa posisi set itu)
    fake, conf = [], 0
    for name, n in sets.items():
        busy = d[d.set == name][["t_signal", "t_close"]].sort_values("t_signal").to_numpy()
        bi = 0
        for k in range(n + 21, len(idx) - 1):
            t0 = idx[k]
            while bi < len(busy) and busy[bi][1] <= t0:
                bi += 1
            if bi < len(busy) and busy[bi][0] <= t0 + pd.Timedelta(hours=1) <= busy[bi][1]:
                continue
            hh, ll = hi[k - n:k].max(), lo[k - n:k].min()
            if hi[k] <= hh and lo[k] >= ll:
                continue                                   # tidak menyentuh channel sama sekali
            a0, b0 = ib_t.searchsorted(t0), ib_t.searchsorted(t0 + pd.Timedelta(hours=1))
            x = ib.close.to_numpy()[a0:b0]
            for sgn, lvl in ((1, hh), (-1, ll)):
                hit = np.nonzero((x - lvl) * sgn > 0)[0]
                if not len(hit):
                    continue
                if (cl[k] - lvl) * sgn > 0:
                    conf += 1                              # breakout terkonfirmasi H1
                else:
                    risk = 3.0 * atr[k] if atr[k] > 0 else np.nan
                    fake.append({"t": t0, "set": name, "r": (cl[k] - x[hit[0]]) * sgn / risk})
    f_ = pd.DataFrame(fake)
    send = len(d) / max(conf, 1)
    L = ["## Uji 2 — entry M5 (lebih awal, saat candle M5/M15 menutup di luar channel H1)",
         f"Sinyal utama XAU yang dikirim: {len(d)}; breakout terkonfirmasi saat set kosong: {conf}; rasio dikirim {send:.2f}",
         f"Breakout palsu (M5 tembus, H1 kembali ke dalam): {len(f_)} → perkiraan ikut terkirim {len(f_) * send:.0f}", ""]
    for per, m_a, m_f in (("LAMA", a_.t < SPLIT, f_.t < SPLIT), ("BARU", a_.t >= SPLIT, f_.t >= SPLIT)):
        x, fk = a_[m_a], f_[m_f]
        base = x.r.sum()
        new = x.r_m5.sum() + fk.r.mean() * len(fk) * send if len(fk) else x.r_m5.sum()
        n_new = len(x) + len(fk) * send
        wr_new = ((x.r_m5 > 0).sum()) / n_new * 100
        L.append(f"  {per}: sinyal {len(x)} | entry lebih awal rata {x.gain_r.mean():+.3f}R (median {x.gain_r.median():+.3f}R) "
                 f"| R sinyal sama: {base:+.1f}R → {x.r_m5.sum():+.1f}R")
        L.append(f"        breakout palsu {len(fk)} × {send:.2f} ≈ {len(fk) * send:.0f} trade, rata {fk.r.mean():+.3f}R "
                 f"(WR palsu {(fk.r > 0).mean() * 100:.0f}%) → total M5 ≈ {new:+.1f}R vs bawaan {base:+.1f}R | "
                 f"WR {(x.r > 0).mean() * 100:.1f}% → ≈{wr_new:.1f}%")
        for src in ("M15", "M5"):
            y = x[x.src == src]
            if len(y):
                L.append(f"        sumber {src}: n {len(y)} | gain {y.gain_r.mean():+.3f}R | {y.r.sum():+.1f}R → {y.r_m5.sum():+.1f}R")
    by = a_.groupby(a_.t.dt.year).apply(lambda g: g.r_m5.sum() - g.r.sum())
    fy = f_.groupby(f_.t.dt.year).r.sum() * send if len(f_) else pd.Series(dtype=float)
    net = by.add(fy, fill_value=0)
    L.append("  per tahun (selisih R, M5 − bawaan, termasuk palsu): " + " ".join(f"{y}:{v:+.0f}" for y, v in net.items()))
    return L


BESAR = {"Non-Farm Employment Change", "CPI m/m", "Core CPI m/m", "Federal Funds Rate", "PPI m/m",
         "Core PCE Price Index m/m", "Retail Sales m/m", "Advance GDP q/q", "ISM Manufacturing PMI", "ISM Services PMI",
         "JOLTS Job Openings", "ADP Non-Farm Employment Change", "Unemployment Claims"}


def uji_berita() -> list[str]:
    """Seperti peringatan kata kunci Finnhub (NFP/CPI/FOMC/Powell): lewati sinyal di sekitar rilis USD dampak tinggi.
    Kalender ForexFactory 2010–Jan 2026 (berita besar). Jendela: sebelum (sinyal ≤ X jam SEBELUM rilis) / sesudah."""
    from .news_prediksi import calendar
    cal = calendar()
    L = ["## Uji 3 — hindari sinyal di sekitar berita USD besar (pengganti peringatan berita Finnhub)",
         f"Kalender ForexFactory {cal.time.min():%Y}–{cal.time.max():%b %Y}, {len(cal)} rilis; sinyal sampai Jan 2026.", ""]
    for jenis, ev in (("utama NFP/CPI/Fed", {"Non-Farm Employment Change", "CPI m/m", "Core CPI m/m",
                                              "Federal Funds Rate"}), ("semua berita besar", BESAR)):
        t = np.sort(cal[cal.event.isin(ev)].time.drop_duplicates().to_numpy())
        for name in ("XAU", "BTC"):
            d = load(name)
            d = d[d.t_signal <= cal.time.max()]
            ts = d.t_signal.to_numpy()
            k = np.searchsorted(t, ts)
            nxt = np.where(k < len(t), (t[np.minimum(k, len(t) - 1)] - ts) / np.timedelta64(1, "h"), np.inf)
            prv = np.where(k > 0, (ts - t[np.maximum(k - 1, 0)]) / np.timedelta64(1, "h"), np.inf)
            L.append(f"### {name} — {jenis} (utama + lapisan)")
            for lab, m in (("≤ 2 jam SEBELUM rilis", nxt <= 2), ("≤ 6 jam sebelum", nxt <= 6),
                           ("≤ 2 jam SESUDAH rilis", prv <= 2), ("≤ 4 jam sesudah", prv <= 4),
                           ("−2…+2 jam (Finnhub-style)", (nxt <= 2) | (prv <= 2))):
                for per, mp in (("LAMA", d.t_signal < SPLIT), ("BARU", d.t_signal >= SPLIT)):
                    x = d[mp.to_numpy()]
                    mm = m[mp.to_numpy()]
                    L.append(f"  {per} {lab:26} kena {fmt(stat(x[mm]))}")
                    L.append(f"  {per} {'  → sisa bila dilewati':26}      {fmt(stat(x[~mm]))}")
            L.append(f"  bawaan LAMA {fmt(stat(d[d.t_signal < SPLIT]))}")
            L.append(f"  bawaan BARU {fmt(stat(d[d.t_signal >= SPLIT]))}")
            L.append("")
    return L


def jadwal_besar() -> np.ndarray:
    """Waktu rilis NFP, CPI, keputusan Fed (UTC): ForexFactory s.d. Jan 2026, lalu tanggal FRED (NFP rel 50, CPI rel 10)
    jam 08:30 ET + jadwal FOMC 2026 jam 14:00 ET (sama dengan cloud/api/jadwal.json)."""
    import json
    from zoneinfo import ZoneInfo

    from .jadwal_berita import FOMC
    from .news_prediksi import calendar
    cal = calendar()
    t = list(cal[cal.event.isin(UTAMA)].time.drop_duplicates())
    akhir = max(t)
    et = ZoneInfo("America/New_York")
    ext = ROOT / "data" / "research" / "eksternal"
    tgl = [x["date"] for r in (50, 10) for x in json.loads((ext / f"fred_release_{r}.json").read_text())["release_dates"]]
    for d, hm in [(d, (8, 30)) for d in tgl] + [(d, (14, 0)) for d in FOMC]:
        y, m, dd = map(int, d.split("-"))
        ts = pd.Timestamp(pd.Timestamp(y, m, dd, *hm).to_pydatetime().replace(tzinfo=et)).tz_convert("UTC")
        if ts > akhir:
            t.append(ts)
    return pd.DatetimeIndex(t).tz_convert("UTC").tz_localize(None).unique().sort_values().to_numpy()


UTAMA = {"Non-Farm Employment Change", "CPI m/m", "Core CPI m/m", "Federal Funds Rate"}


def jadwal_cloud() -> list:
    """Jadwal riset dalam format cloud/api/_jeda_berita (daftar (datetime UTC, nama)) — untuk replay kode cloud."""
    return [(pd.Timestamp(x).tz_localize("UTC").to_pydatetime(), "berita") for x in jadwal_besar()]


def skip_berita(jam: float = 36.0):
    t = jadwal_besar()

    def f(direction, now):
        x = np.datetime64(pd.Timestamp(now).tz_convert("UTC").tz_localize(None))
        k = np.searchsorted(t, x, side="right")
        if k < len(t) and t[k] - x <= np.timedelta64(int(jam * 60), "m"):
            return f"≤ {jam:.0f} jam sebelum NFP/CPI/Fed"
        return None
    return f


def replay_berita(jam: float = 36.0) -> list[str]:
    """Replay PENUH kode cloud XAU (konfigurasi live) dengan filter 'lewati ≤ jam sebelum NFP/CPI/Fed' (efek slot)."""
    from .verifikasi_cloud import replay
    out = replay("XAU", extra={"skip_fn": skip_berita(jam)})
    out.to_csv(VER / f"cloud_XAU_berita{int(jam)}.csv", index=False)
    base = load("XAU")
    L = [f"## Uji 3b — replay PENUH kode cloud XAU + lewati sinyal ≤ {jam:.0f} jam sebelum NFP/CPI/Fed (efek slot dihitung)"]
    for lab, x0, x1 in (("utama", base[~base.lapis], out[~out.lapis]), ("lapisan", base[base.lapis], out[out.lapis]),
                        ("semua", base, out)):
        for per, a, b in (("LAMA", x0.t_signal < SPLIT, x1.t_signal < SPLIT), ("BARU", x0.t_signal >= SPLIT,
                                                                                x1.t_signal >= SPLIT),
                          ("2026", x0.t_signal >= pd.Timestamp("2026-01-01", tz="UTC"),
                           x1.t_signal >= pd.Timestamp("2026-01-01", tz="UTC"))):
            L.append(f"  {lab:7} {per} bawaan : {fmt(stat(x0[a]))}")
            L.append(f"  {lab:7} {per} + filter: {fmt(stat(x1[b]))}")
    yb = base.groupby(base.t_close.dt.year).r.sum()
    yf = out.groupby(out.t_close.dt.year).r.sum()
    L.append("  per tahun (filter − bawaan, R): " + " ".join(f"{y}:{yf.get(y, 0) - yb.get(y, 0):+.0f}" for y in yb.index))
    return L


def paxg_binance(folder: Path) -> pd.DataFrame:
    import zipfile
    rows = []
    for f in sorted(folder.glob("PAXGUSDT-1h-*.zip")):
        with zipfile.ZipFile(f) as z:
            for name in z.namelist():
                d = pd.read_csv(z.open(name), header=None)
                if not str(d.iloc[0, 0]).isdigit():
                    d = d.iloc[1:]
                rows.append(d.iloc[:, :5].astype(float))
    d = pd.concat(rows)
    t = d[0].to_numpy()
    t = np.where(t > 1e14, t / 1000, t)                 # 2025+: mikrodetik
    out = pd.DataFrame({"open": d[1].to_numpy(), "high": d[2].to_numpy(), "low": d[3].to_numpy(),
                        "close": d[4].to_numpy()}, index=pd.to_datetime(t, unit="ms", utc=True))
    return out[~out.index.duplicated()].sort_index()


def breakouts(df: pd.DataFrame, n: int) -> pd.Series:
    hh = df.high.shift(1).rolling(n).max()
    ll = df.low.shift(1).rolling(n).min()
    return pd.Series(np.where(df.close > hh, 1, np.where(df.close < ll, -1, 0)), index=df.index)


def uji_paxg(folder: str) -> list[str]:
    """PAXG (token emas, 24/7) sebagai cadangan feed: kemiripan harga & sinyal breakout dengan XAU H1 kita."""
    import json as _json
    x = h1("XAU")
    p = paxg_binance(Path(folder))
    common = x.index.intersection(p.index)                # hanya jam pasar XAU (PAXG akhir pekan dibuang)
    xa, pa = x.loc[common], p.loc[common]
    rx, rp = xa.close.pct_change(), pa.close.pct_change()
    prem = (pa.close / xa.close - 1) * 100
    L = ["## Uji 4 — PAXG (Binance/Kraken) sebagai cadangan feed XAU",
         f"Binance PAXGUSDT 1 jam {p.index.min():%Y-%m}–{p.index.max():%Y-%m}; jam sama dengan XAU: {len(common)}",
         f"  korelasi return 1 jam {rx.corr(rp):.3f} | arah sama {(np.sign(rx) == np.sign(rp)).mean() * 100:.1f}% | "
         f"selisih harga median {prem.median():+.2f}% (P5 {prem.quantile(.05):+.2f}%, P95 {prem.quantile(.95):+.2f}%)"]
    for n in (40, 55, 80):
        bx, bp = breakouts(xa, n), breakouts(pa, n)
        ev = bx[bx != 0]
        same = (bp.reindex(ev.index) == ev).mean() * 100
        near = np.mean([(bp.loc[t - pd.Timedelta(hours=1):t + pd.Timedelta(hours=1)] == v).any() for t, v in ev.items()]) * 100
        extra = ((bp != 0) & (bx == 0)).sum()
        L.append(f"  breakout Donchian {n}: XAU {len(ev)} | PAXG sama jam {same:.0f}% | ±1 jam {near:.0f}% | "
                 f"PAXG tambahan (tidak ada di XAU) {extra}")
    try:
        k = _json.loads((ROOT / "data" / "research" / "eksternal" / "kraken_paxg.json").read_text())
        r = list(k["result"].values())[0]
        kd = pd.DataFrame(r, columns=["t", "o", "h", "l", "c", "vw", "v", "n"]).astype(float)
        kd.index = pd.to_datetime(kd.t, unit="s", utc=True)
        cm = kd.index.intersection(p.index)
        L.append(f"  Kraken vs Binance PAXG (720 jam terakhir): selisih close median "
                 f"{((kd.c.loc[cm] / p.close.loc[cm] - 1) * 100).abs().median():.3f}%")
    except Exception as e:  # noqa: BLE001
        L.append(f"  Kraken: {type(e).__name__}")
    return L


def uji_jendela() -> list[str]:
    """Sensitivitas jendela jeda (pasca-saring sinyal XAU yang dikirim, cloud_XAU.csv) + per jenis berita + p acak."""
    from .jadwal_berita import FOMC
    from .news_prediksi import calendar
    d = load("XAU").sort_values("t_signal").reset_index(drop=True)
    x = d.t_signal.dt.tz_convert(None).to_numpy()
    t_all = jadwal_besar()
    L = ["## Uji 3c — sensitivitas jendela jeda sebelum NFP/CPI/Fed (pasca-saring sinyal XAU, utama + lapisan)",
         "jam | LAMA dilewati n / total R / sisa PF | BARU dilewati n / total R / sisa PF"]

    def kena(t, jam):
        k = np.searchsorted(t, x, side="right")
        ok = k < len(t)
        m = np.zeros(len(x), bool)
        m[ok] = t[k[ok]] - x[ok] <= np.timedelta64(int(jam * 60), "m")
        return m
    for jam in (6, 12, 18, 24, 30, 36, 42, 48, 60, 72):
        m = kena(t_all, jam)
        row = f"  {jam:>3} jam"
        for per, pm in (("LAMA", d.t_signal < SPLIT), ("BARU", d.t_signal >= SPLIT)):
            a, b = stat(d[pm & m]), stat(d[pm & ~m])
            row += f" | {per} {a['n']:>4} / {a.get('tot', 0.0):+7.1f}R / PF {b.get('pf', 0.0):.2f}"
        L.append(row)
    cal = calendar()
    et = __import__("zoneinfo").ZoneInfo("America/New_York")
    jenis = {"NFP": {"Non-Farm Employment Change"}, "CPI": {"CPI m/m", "Core CPI m/m"}, "Fed": {"Federal Funds Rate"}}
    L.append("  per jenis (36 jam, hanya rilis jenis itu):")
    for nm, ev in jenis.items():
        t = cal[cal.event.isin(ev)].time.drop_duplicates()
        if nm == "Fed":
            t = pd.concat([t, pd.Series([pd.Timestamp(f"{dd} 14:00").tz_localize(et).tz_convert("UTC") for dd in FOMC])])
        t = pd.DatetimeIndex(t).tz_convert("UTC").tz_localize(None).unique().sort_values().to_numpy()
        m = kena(t, 36)
        for per, pm in (("LAMA", d.t_signal < SPLIT), ("BARU", d.t_signal >= SPLIT)):
            L.append(f"    {nm:3} {per} dilewati {fmt(stat(d[pm & m]))}")
    m = kena(t_all, 36)
    rng = np.random.default_rng(0)
    for per, pm in (("LAMA", (d.t_signal < SPLIT).to_numpy()), ("BARU", (d.t_signal >= SPLIT).to_numpy())):
        r, n = d.r.to_numpy()[pm], int((m & pm).sum())
        nyata = d.r.to_numpy()[m & pm].sum()
        acak = np.array([rng.choice(r, n, replace=False).sum() for _ in range(5000)])
        L.append(f"  36 jam {per}: dilewati {n} sinyal total {nyata:+.1f}R vs subset acak sama besar rata-rata "
                 f"{acak.mean():+.1f}R → p (acak ≤ nyata) = {(acak <= nyata).mean():.4f}")
    th = d[m].groupby(d[m].t_signal.dt.year).r.sum()
    L.append("  36 jam, R sinyal yang dilewati per tahun: " + " ".join(f"{y}:{v:+.0f}" for y, v in th.items()))
    return L


def replika(cfg: dict, spread: float = 0.20) -> pd.DataFrame:
    """Tiruan aturan repo moritakaaz/trading-alert v1.3 (ditulis ulang, kode mereka TIDAK dijalankan):
    Donchian(48) dari H1 yang sudah selesai, dicek tiap close candle intrabar (M5 sejak Agu 2020, M15 sebelumnya),
    hanya saat transisi (close sebelumnya belum tembus); SL 1,5×ATR14 H1; R per trade seperti harness mereka:
    −1 (SL sebelum TP1), 0 (TP1 lalu BE), +2 (TP3), atau tutup di 48 jam; satu posisi (bebas lagi setelah SL/TP1/48 jam);
    filter H4 (close H4 vs SMA15 H4), EMA20/50 H1 (cfg ema), jeda setelah SL (cfg cooldown jam). Biaya: spread $ per trade."""
    df = h1("XAU")
    ib = xau_intrabar()
    ib = ib[(ib.index >= df.index[0] + pd.Timedelta(days=10)) & (ib.high >= ib.low)]
    df.index, ib.index = df.index.tz_convert(None), ib.index.tz_convert(None)
    hi, lo, cl = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    pc = np.r_[cl[0], cl[:-1]]
    tr = np.maximum(hi - lo, np.maximum(abs(hi - pc), abs(lo - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    up48 = pd.Series(hi).rolling(48).max().to_numpy()
    lo48 = pd.Series(lo).rolling(48).min().to_numpy()
    e20 = pd.Series(cl).ewm(span=20, adjust=False).mean().to_numpy()
    e50 = pd.Series(cl).ewm(span=50, adjust=False).mean().to_numpy()
    h4 = df.close.resample("4h", label="left", closed="left").last().dropna()
    h4_end = (h4.index + pd.Timedelta(hours=4)).to_numpy()
    h4_sma = h4.rolling(15).mean().to_numpy()
    h4_c = h4.to_numpy()
    t_ib = ib.index.to_numpy()
    hb = ib.index.floor("h").to_numpy()
    j_of = np.searchsorted(df.index.to_numpy(), hb) - 1          # H1 terakhir yang SUDAH selesai
    k4 = np.searchsorted(h4_end, hb, side="right") - 1           # H4 terakhir yang sudah selesai
    oh, ol, oc = ib.high.to_numpy(), ib.low.to_numpy(), ib.close.to_numpy()
    trades, runners, live, last_sl = [], [], None, None
    prev_sig = None
    for i in range(1, len(ib)):
        j = j_of[i]
        if j < 60 or np.isnan(atr[j]) or atr[j] <= 0:
            continue
        ts, h, l, c = t_ib[i], oh[i], ol[i], oc[i]
        for r in runners[:]:
            sl, tp1_lama = (r["entry"] if r["tp1"] else r["sl"]), r["tp1"]
            if r["dir"] > 0:
                hit_sl, hit_tp3 = l <= sl, h >= r["tp3"]
                r["tp1"] = r["tp1"] or h >= r["tp1p"]
            else:
                hit_sl, hit_tp3 = h >= sl, l <= r["tp3"]
                r["tp1"] = r["tp1"] or l <= r["tp1p"]
            exp = ts - r["ts"] >= np.timedelta64(48, "h")
            if hit_sl or hit_tp3 or exp:
                r["r"] = (0.0 if tp1_lama else -1.0) if hit_sl else 2.0 if hit_tp3 else (c - r["entry"]) * r["dir"] / r["risk"]
                r["r"] -= spread / r["risk"]
                r["t_close"] = ts
                trades.append(r)
                runners.remove(r)
        if live is not None:
            if live["dir"] > 0:
                hit_sl, hit_tp1 = l <= live["sl"], h >= live["tp1p"]
            else:
                hit_sl, hit_tp1 = h >= live["sl"], l <= live["tp1p"]
            if hit_sl:
                last_sl, live = ts, None
            elif hit_tp1 or ts - live["ts"] >= np.timedelta64(48, "h"):
                live = None
        sig = 1 if c > up48[j] else -1 if c < lo48[j] else 0
        prev, prev_sig = prev_sig, sig
        if live is not None or sig == 0 or sig == prev:
            continue
        if cfg.get("h4", True):
            if k4[i] < 15 or np.isnan(h4_sma[k4[i]]) or (h4_c[k4[i]] > h4_sma[k4[i]]) != (sig > 0):
                continue
        if cfg.get("ema") and (e20[j] > e50[j]) != (sig > 0):
            continue
        if cfg.get("cooldown") and last_sl is not None and ts - last_sl < np.timedelta64(int(cfg["cooldown"]), "h"):
            continue
        risk = 1.5 * atr[j]
        t = {"dir": sig, "ts": ts, "entry": c, "risk": risk, "sl": c - sig * risk, "tp1p": c + sig * risk,
             "tp3": c + 2 * sig * risk, "tp1": False}
        live = {"dir": sig, "ts": ts, "sl": t["sl"], "tp1p": t["tp1p"]}
        runners.append(t)
    out = pd.DataFrame([{"t_signal": pd.Timestamp(x["ts"]).tz_localize("UTC"),
                         "t_close": pd.Timestamp(x["t_close"]).tz_localize("UTC"),
                         "dir": "BUY" if x["dir"] > 0 else "SELL", "r": x["r"]} for x in trades])
    return out


def uji_replika() -> list[str]:
    L = ["## Uji 5 — tiruan sistem repo moritakaaz/trading-alert v1.3 di data XAU kita 2012–2026 (spread $0,20)",
         "M15 sebagai pemicu s.d. Agu 2020, M5 sesudahnya. R per trade = model mereka (−1 / 0 BE / +2 / 48 jam).", ""]
    ours = load("XAU")
    for lab, cfg in (("v1.1 (H4 saja)", {"h4": True}), ("v1.2/1.3 (+EMA20/50 H1)", {"h4": True, "ema": True}),
                     ("v1.3 + jeda 12 jam setelah SL", {"h4": True, "ema": True, "cooldown": 12}),
                     ("tanpa filter", {"h4": False})):
        for sp in (0.0, 0.20):
            d = replika(cfg, sp)
            L.append(f"### {lab} — spread ${sp:.2f}")
            for per, m in (("LAMA", d.t_signal < SPLIT), ("BARU", d.t_signal >= SPLIT),
                           ("9 bln Jan–Okt 2026", d.t_signal >= pd.Timestamp("2026-01-01", tz="UTC"))):
                L.append(f"  {per:18} {fmt(stat(d[m]))}")
            th = d.groupby(d.t_close.dt.year).r.sum()
            L.append("  per tahun R: " + " ".join(f"{y}:{v:+.0f}" for y, v in th.items()))
    L.append("")
    L.append("### Pembanding: sinyal 💰 XAU kita (replay cloud, spread asli, R = risiko SL 3×ATR20)")
    for per, m in (("LAMA", ours.t_signal < SPLIT), ("BARU", ours.t_signal >= SPLIT),
                   ("9 bln Jan–Okt 2026", ours.t_signal >= pd.Timestamp("2026-01-01", tz="UTC"))):
        L.append(f"  {per:18} semua   {fmt(stat(ours[m]))}")
        L.append(f"  {per:18} utama   {fmt(stat(ours[m & ~ours.lapis]))}")
    return L


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "filter"
    if cmd in ("replika", "jendela"):
        L = uji_replika() if cmd == "replika" else uji_jendela()
        print("\n".join(L))
        with OUT.open("a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(L) + "\n")
        return
    if cmd == "paxg":
        L = uji_paxg(sys.argv[2])
        print("\n".join(L))
        with OUT.open("a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(L) + "\n")
        return
    if cmd == "replay":
        L = replay_berita(float(sys.argv[2]) if len(sys.argv) > 2 else 36.0)
        print("\n".join(L))
        with OUT.open("a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(L) + "\n")
        return
    L = {"filter": uji_filter, "m5": uji_m5, "berita": uji_berita}[cmd]()
    print("\n".join(L))
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else "# Uji sistem Muse (research/muse_uji.py)\n"
    head = L[0]
    if head in old:
        old = old.split(head)[0]
    OUT.write_text(old.rstrip() + "\n\n" + "\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
