"""Entry SEBELUM rilis (t0-1 dtk), tutup 1 dtk s.d. 3 menit: semua cara menebak arah + cara tanpa tebakan arah.

python -m research.news_pra2        # -> docs/eksternal/hasil_news_pra2.txt

Lanjutan research/news_pra.py. Permintaan pengguna (30 Sep 2026): "1-60 detik kedepan akan saya close atau 1-3
menit boleh, tapi saya memprioritaskan sebelum 1 detik news keluar saya akan entry ... silahkan cari uji metodenya".

Aturan (ditetapkan sebelum melihat hasil):
- Tick XAU Exness Cent (XAUUSDc 2015-2026, broker pengguna) dan Dukascopy (2010-2026) pembanding; semua rilis USD
  bintang 3 (research/news_detik.events()); t0 = waktu rilis resmi.
- Skenario eksekusi: CEPAT (terisi di kutipan saat keputusan, tanpa slippage), REALISTIS (terisi 0,5 dtk kemudian +
  slippage $0,30 saat masuk DAN keluar), STRES (0,5 dtk + $1,00). BUY di ASK, SELL di BID.
- Keluar: WAKTU h (tutup h dtk setelah entry, h = 1,2,3,5,10,20,30,45,60,90,120,180) atau KUNCI x/W (tutup begitu
  untung >= $x, x = 0,5/1/2/3, dicek tiap tick; bila tak tercapai tutup di W = 60/180 dtk), dengan/tanpa SL $3 (dicek
  tiap tick). REALISTIS/STRES: order tutup terisi 0,5 dtk setelah syarat terpenuhi.
- Arah sebelum rilis (hanya informasi yang sudah ada sebelum t0-1):
  literatur: ANCHOR (Campbell & Sharpe 2009: konsensus terlalu dekat ke angka sebelumnya -> kejutan searah Cons - Prev);
  MOMENTUM KEJUTAN (jumlah arah kejutan semua data AS 30 hari terakhir berlanjut, seperti indeks kejutan Citi);
  DRIFT 15/30/60 mnt (Kurov dkk. 2019: futures mulai bergerak ke arah benar +/-30 menit sebelum rilis) + LAWAN;
  ADP BESAR -> NFP (kejutan ADP >= 2x median sebelumnya diikuti kejutan NFP searah);
  riset sebelumnya: ULANG, ACT->PREV, P1/P7 CPI, DRIFT/LAWAN 10-110 dtk (tick), SELALU BUY/SELL;
  MODEL = regresi logistik walk-forward (dilatih hanya dengan tahun-tahun sebelumnya) dari semua fitur di atas,
  target = arah harga t0-1 -> t0+30 dtk; MODEL YAKIN = hanya bila peluang >= 55% / <= 45%.
  ORAKEL = arah kejutan sebenarnya (tidak mungkin diketahui) -> batas atas & akurasi minimal agar impas.
- Tanpa tebakan arah (disiapkan sebelum rilis): STRADDLE k (Buy Stop & Sell Stop dipasang t0-1 di mid +/- $k,
  k = 0,5/1/2/3, OCO, terisi di tick pertama yang melewati level -> gap = slippage nyata; + slippage skenario; tidak
  tersentuh 60 dtk -> batal); HEDGE d (BUY & SELL di t0-1; di t0+d dtk (d = 1/2/3/5) sisi yang rugi ditutup bila gerak
  >= $0,5, sisi untung ditahan dengan cara keluar di atas dihitung dari saat itu; gerak < $0,5 -> keduanya ditutup).
- Lolos: news_detik.judge (n >= 30, LAMA & BARU > 0, >= 60% tahun positif, t > 2) pada CEPAT dengan REALISTIS > 0, di
  KEDUA feed. STRES dilaporkan. Jumlah kombinasi yang diuji dilaporkan: dengan ribuan uji, beberapa "lolos" bisa
  kebetulan -> hanya yang lolos di kedua feed yang dianggap.
- Hasil dalam $ per ons = $ per 0,01 lot (akun Cent: sen).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .event_stats import xau_m15
from .news_data import _num, load_calendar
from .news_detik import EXNESS, NEW, events, fmt, judge, prepare, stats
from .news_pra import clues
from .run_scan import DATA

FIXED = [1, 2, 3, 5, 10, 20, 30, 45, 60, 90, 120, 180]
LOCK = [(x, w, sl) for x in (0.5, 1.0, 2.0, 3.0) for w in (60, 180) for sl in (None, 3.0)]
EXITS = [f"tutup {h}s" for h in FIXED] + [f"untung>=${x:g} maks {w}s" + (" SL$3" if sl else "") for x, w, sl in LOCK]
SCEN = {"CEPAT": (0.0, 0.0), "REALISTIS": (0.5, 0.3), "STRES": (0.5, 1.0)}
STRADDLE = [0.5, 1.0, 2.0, 3.0]
GAP_SEDANG = 0.5          # asumsi "gap sedang" untuk perlindungan gap Exness (tidak disebut angkanya oleh broker)
HEDGE = [1, 2, 3, 5]
HEDGE_MIN = 0.5
TICK_DRIFT = [10, 30, 60, 110]
BAR_DRIFT = {"15m": 1, "30m": 2, "60m": 4}
FEEDS = {"XAU_EXNESS": "Exness", "XAU": "Dukascopy"}
GROUPS = ["SEMUA", "NFP", "CPI", "PPI", "ADP", "RETAIL", "GDP", "PCE", "ISM", "CLAIMS", "FOMC", "JOLTS", "KONSUMEN"]
SHOW = ["tutup 1s", "tutup 3s", "tutup 10s", "tutup 30s", "tutup 60s", "tutup 180s", "untung>=$1 maks 60s",
        "untung>=$1 maks 180s SL$3", "untung>=$2 maks 180s"]
OUT = Path(__file__).resolve().parent.parent / "docs" / "eksternal" / "hasil_news_pra2.txt"


# ---------------------------------------------------------------- mesin keluar
def exit_all(p, i: int, price: float, d: int, lat: float, slip: float, start: float) -> np.ndarray:
    """P&L tiap cara keluar (urutan EXITS) untuk posisi arah d yang harga masuknya `price` (sudah termasuk slippage
    masuk), memakai tick mulai indeks i. Jam keluar dihitung dari `start` (detik relatif t0)."""
    end = int(np.searchsorted(p.T, start + max(FIXED) + lat + 1, side="right"))
    T = p.T[i:end]
    pnl = (p.bid[i:end] - price) if d > 0 else (price - p.ask[i:end])

    def at(sec: float) -> float:
        k = int(np.searchsorted(T, sec, side="right")) - 1
        return float(pnl[max(k, 0)])

    out = [at(start + h + lat) - slip for h in FIXED]
    for x, w, sl in LOCK:
        idx = np.flatnonzero((T >= start) & (T <= start + w))
        cand = [a[0] for a in (idx[pnl[idx] >= x], idx[pnl[idx] <= -sl] if sl else idx[:0]) if len(a)]
        if not cand:
            out.append(at(start + w + lat) - slip)
        else:
            k = min(cand)
            out.append((float(pnl[k]) if lat == 0 else at(T[k] + lat)) - slip)
    return np.array(out)


def entry(p, lat: float, slip: float) -> tuple[int, float, float] | None:
    """(indeks kutipan, harga BUY, harga SELL) untuk keputusan di t0-1 yang terisi lat dtk kemudian."""
    i = p.at(-1 + lat)
    if i < 0 or p.T[i] < -60:
        return None
    return i, float(p.ask[i]) + slip, float(p.bid[i]) - slip


def directional(p) -> np.ndarray | None:
    """[skenario, arah (0 = BUY, 1 = SELL), cara keluar]."""
    out = np.full((len(SCEN), 2, len(EXITS)), np.nan)
    for s, (lat, slip) in enumerate(SCEN.values()):
        e = entry(p, lat, slip)
        if e is None:
            return None
        i, pb, ps = e
        out[s, 0] = exit_all(p, i, pb, 1, lat, slip, -1 + lat)
        out[s, 1] = exit_all(p, i, ps, -1, lat, slip, -1 + lat)
    return out


def straddle(p) -> np.ndarray:
    """[isi (0 = di tick lonjakan/gap, 1 = di level), k, skenario, cara keluar]; NaN bila tidak tersentuh 60 dtk.
    Isi di level = klaim "perlindungan gap" Exness (±90% order stop diisi di harga yang diminta walau ada gap
    sedang); di sini hanya bila gap <= GAP_SEDANG, gap lebih besar tetap diisi di tick. Isi di tick = pesimistis."""
    out = np.full((2, len(STRADDLE), len(SCEN), len(EXITS)), np.nan)
    i0 = p.at(-1)
    if i0 < 0:
        return out
    ref = p.mid[i0]
    w = np.flatnonzero((p.T > -1) & (p.T <= 60))
    for a, k in enumerate(STRADDLE):
        up, dn = w[p.ask[w] >= ref + k], w[p.bid[w] <= ref - k]
        iu, idn = (int(up[0]) if len(up) else None), (int(dn[0]) if len(dn) else None)
        if iu is None and idn is None or iu == idn:
            continue
        d = 1 if idn is None or (iu is not None and iu < idn) else -1
        j = iu if d > 0 else idn
        level = ref + k if d > 0 else ref - k
        for s, (lat, slip) in enumerate(SCEN.values()):
            gap = p.ask[j] if d > 0 else p.bid[j]
            protect = level if abs(gap - level) <= GAP_SEDANG else gap      # hanya gap "sedang" yang dilindungi
            for f, fill in enumerate((gap, protect)):
                price = fill + slip if d > 0 else fill - slip
                out[f, a, s] = exit_all(p, j, float(price), d, lat, slip, float(p.T[j]))
    return out


def hedge(p) -> np.ndarray:
    """[d, skenario, cara keluar]: BUY + SELL di t0-1, sisi rugi ditutup di t0+d."""
    out = np.full((len(HEDGE), len(SCEN), len(EXITS)), np.nan)
    i0 = p.at(-1)
    if i0 < 0:
        return out
    for a, d in enumerate(HEDGE):
        move = p.mid[p.at(d)] - p.mid[i0]
        for s, (lat, slip) in enumerate(SCEN.values()):
            e = entry(p, lat, slip)
            if e is None:
                continue
            i, pb, ps = e
            j = p.at(d + lat)
            if abs(move) < HEDGE_MIN:                          # tidak ada gerak berarti: tutup keduanya
                out[a, s] = (p.bid[j] - pb) + (ps - p.ask[j]) - 2 * slip
                continue
            win = 1 if move > 0 else -1
            loser = (ps - p.ask[j]) if win > 0 else (p.bid[j] - pb)
            out[a, s] = loser - slip + exit_all(p, i, pb if win > 0 else ps, win, lat, slip, float(d))
    return out


# ---------------------------------------------------------------- arah sebelum rilis
def momentum(ev: pd.DataFrame, cal: pd.DataFrame, days: int = 30) -> pd.Series:
    """Tanda jumlah arah kejutan (untuk emas) semua berita USD berdampak tinggi dalam `days` hari sebelum t0."""
    c = cal[cal.gold_bias.notna()].sort_values("time")
    t = c.time.values                                   # datetime64[ns] UTC
    cs = np.concatenate([[0.0], np.cumsum(c.gold_bias.to_numpy())])
    out = {}
    for i, r in ev.iterrows():
        a = np.searchsorted(t, (r.time - pd.Timedelta(days=days)).to_datetime64(), side="left")
        b = np.searchsorted(t, r.time.to_datetime64(), side="left")         # sebelum t0 (rilis yang sama tidak ikut)
        s = cs[b] - cs[a]
        if s != 0:
            out[i] = float(np.sign(s))
    return pd.Series(out, dtype=float).reindex(ev.index)


def adp_besar(ev: pd.DataFrame, cal: pd.DataFrame) -> pd.Series:
    """NFP: arah kejutan ADP (<= 7 hari sebelumnya) bila |kejutan| >= 2x median |kejutan| ADP SEBELUMNYA."""
    adp = cal[cal.event == "ADP Non-Farm Employment Change"].sort_values("time").copy()
    adp["surp"] = adp.actual.map(_num) - adp.forecast.map(_num)
    adp = adp[adp.surp.notna() & adp.gold_bias.notna()]
    med = adp.surp.abs().replace(0, np.nan).expanding().median().shift(1)
    adp = adp[(adp.surp.abs() >= 2 * med) & med.notna()]
    out = {}
    for i, r in ev[ev.group == "NFP"].iterrows():
        g = adp[(adp.time < r.time) & (adp.time >= r.time - pd.Timedelta(days=7))]
        if len(g):
            out[i] = float(g.gold_bias.iloc[-1])
    return pd.Series(out, dtype=float).reindex(ev.index)


def bar_features(ev: pd.DataFrame) -> pd.DataFrame:
    """Drift M15 sebelum t0 (%, hanya bar yang sudah tutup sebelum t0) + tren 1 hari + cek jam (bar rilis)."""
    px = xau_m15()
    idx, o, c = px.index, px.open.to_numpy(), px.close.to_numpy()
    rows = {}
    for i, r in ev.iterrows():
        k = int(idx.searchsorted(r.time))
        if k < 97 or k >= len(idx) or idx[k] != r.time:
            continue
        row = {f"bar{lab}": (c[k - 1] / o[k - n] - 1) * 100 for lab, n in BAR_DRIFT.items()}
        row["tren1h"] = (c[k - 1] / c[k - 97] - 1) * 100
        row["bar_rilis"] = (c[k] / o[k] - 1) * 100                      # HANYA untuk cek jam, bukan fitur
        rows[i] = row
    return pd.DataFrame.from_dict(rows, orient="index").reindex(ev.index)


def all_clues(ev: pd.DataFrame, bars: pd.DataFrame) -> dict[str, pd.Series]:
    cl = clues(ev)
    cal = load_calendar(DATA)
    cl["ANCHOR (Campbell-Sharpe)"] = -cl["ACT->PREV"]
    cl["MOMENTUM KEJUTAN 30 hari"] = momentum(ev, cal)
    cl["ADP BESAR -> NFP"] = adp_besar(ev, cal)
    for lab in BAR_DRIFT:
        s = np.sign(bars[f"bar{lab}"]).replace(0, np.nan)
        cl[f"DRIFT {lab} (Kurov)"] = s
        cl[f"LAWAN DRIFT {lab}"] = -s
    return cl


def drift(p, m1: float, n: int) -> float:
    """Gerak mid n dtk terakhir sebelum t0-1; NaN bila belum ada tick (p.at = -1 akan menunjuk tick TERAKHIR)."""
    j = p.at(-1 - n)
    return float(m1 - p.mid[j]) if j >= 0 else np.nan


# ---------------------------------------------------------------- walk-forward
FEATS = ["ULANG kejutan sebelumnya", "ACT->PREV", "MOMENTUM KEJUTAN 30 hari", "ADP BESAR -> NFP", "bar15m", "bar30m",
         "bar60m", "tren1h", "tick10", "tick30", "tick60", "tick110"]


def walk_forward(tab: pd.DataFrame) -> pd.Series:
    """Peluang harga naik t0-1 -> t0+30 dtk dari model yang dilatih HANYA dengan tahun-tahun sebelumnya."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    grp = pd.get_dummies(tab.group.where(tab.group.isin(GROUPS[1:]), "LAIN"), prefix="g", dtype=float)
    X = pd.concat([tab[FEATS].astype(float).fillna(0.0), grp], axis=1)
    y = np.sign(tab.target)
    prob = pd.Series(np.nan, index=tab.index)
    for yr in sorted(tab.time.dt.year.unique()):
        tr = (tab.time.dt.year < yr) & (y != 0) & y.notna()
        te = tab.time.dt.year == yr
        if tr.sum() < 300 or len(set(y[tr])) < 2:
            continue
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=1000)).fit(X[tr], y[tr])
        prob[te] = m.predict_proba(X[te])[:, list(m.classes_).index(1.0)]
    return prob


# ---------------------------------------------------------------- jalankan
def collect(aset: str, ev: pd.DataFrame, cl: dict[str, pd.Series], bars: pd.DataFrame):
    if aset in EXNESS:
        ev = ev[ev.time >= EXNESS[aset][1]]
    keep, dirn, strd, hedg, extra = [], [], [], [], []
    for i, r in ev.iterrows():
        p = prepare(r.time, aset)
        if p is None:
            continue
        dr = directional(p)
        if dr is None:
            continue
        keep.append(i)
        dirn.append(dr)
        strd.append(straddle(p))
        hedg.append(hedge(p))
        m1 = p.mid[p.at(-1)]
        x = {f"tick{n}": drift(p, m1, n) for n in TICK_DRIFT}
        x["target"] = float(p.mid[p.at(30)] - m1)
        x["cek_t0-5"] = float(m1 - p.mid[p.at(-5)])
        extra.append(x)
    tab = ev.loc[keep, ["time", "group", "bias"]].copy()
    tab = pd.concat([tab, pd.DataFrame(extra, index=keep), bars.loc[keep]], axis=1)
    for name, s in cl.items():
        tab[name] = s.reindex(keep)
    for n in TICK_DRIFT:
        s = np.sign(tab[f"tick{n}"]).where(tab[f"tick{n}"].abs() >= 0.01)
        tab[f"DRIFT {n}s"], tab[f"LAWAN {n}s"] = s, -s
    tab["ORAKEL (kejutan diketahui)"] = tab.bias.where(tab.bias.isin([1.0, -1.0]))
    prob = walk_forward(tab)
    tab["MODEL walk-forward"] = np.sign(prob - 0.5).replace(0, np.nan)
    tab["MODEL YAKIN (>=55%)"] = tab["MODEL walk-forward"].where((prob - 0.5).abs() >= 0.05)
    tab["_prob"] = prob
    return tab.reset_index(drop=True), np.array(dirn), np.array(strd), np.array(hedg)


METHODS_SKIP = {"time", "group", "bias", "target", "cek_t0-5", "bar_rilis", "tren1h", "_prob"} | \
    {f"tick{n}" for n in TICK_DRIFT} | {f"bar{lab}" for lab in BAR_DRIFT}


def series(res, method: str, s: int, e: int) -> pd.DataFrame:
    """pnl per rilis untuk satu cara (arah / STRADDLE k / HEDGE d), skenario s, cara keluar e."""
    tab, dirn, strd, hedg = res
    if method.startswith("STRADDLE "):
        k = STRADDLE.index(float(method.split("$")[1].split()[0]))
        v = strd[:, 1 if method.endswith("di level") else 0, k, s, e]
    elif method.startswith("HEDGE "):
        v = hedg[:, HEDGE.index(int(method.split()[1].rstrip("s"))), s, e]
    else:
        d = tab[method].to_numpy(dtype=float)
        v = np.where(d == 1, dirn[:, s, 0, e], np.where(d == -1, dirn[:, s, 1, e], np.nan))
    x = pd.DataFrame({"time": tab.time, "group": tab.group, "pnl": v})
    return x[x.pnl.notna()]


def methods(tab: pd.DataFrame) -> list[str]:
    arah = [c for c in tab.columns if c not in METHODS_SKIP]
    return (arah + [f"STRADDLE ${k:g}" for k in STRADDLE] + [f"STRADDLE ${k:g} di level" for k in STRADDLE]
            + [f"HEDGE {d}s" for d in HEDGE])


def summary(xs: dict[str, pd.DataFrame], grp: str) -> dict:
    """xs: skenario -> series(); statistik satu grup per skenario."""
    return {sc: stats(x if grp == "SEMUA" else x[x.group == grp]) for sc, x in xs.items()}


def surprise_accuracy(tab: pd.DataFrame, method: str) -> tuple[int, float, float, float]:
    """(n, % benar menebak arah kejutan, LAMA, BARU) untuk rilis yang punya kejutan."""
    k = tab[tab.bias.isin([1.0, -1.0]) & tab[method].isin([1.0, -1.0])]
    hit = k[method] == k.bias
    old = k.time < NEW
    pct = lambda m: float(hit[m].mean() * 100) if m.sum() else np.nan  # noqa: E731
    return len(k), pct(k.time.notna()), pct(old), pct(~old)


def report() -> str:
    ev = events()
    bars = bar_features(ev)
    cl = all_clues(ev, bars)
    res = {a: collect(a, ev, cl, bars) for a in FEEDS}
    L = ["# Entry sebelum rilis (t0-1 dtk), tutup 1 dtk s.d. 3 menit (research/news_pra2.py)", ""]
    # 1. cek jam & ke mana emas
    for a, lab in FEEDS.items():
        tab = res[a][0]
        k = tab[tab.bias.isin([1.0, -1.0])]
        L.append(f"== {lab}: {len(tab)} rilis ({tab.time.min():%Y-%m}..{tab.time.max():%Y-%m}), {len(k)} dengan kejutan ==")
        chk = (np.sign(k["cek_t0-5"]) * k.bias > 0).mean() * 100
        b = k[k.bar_rilis.notna()]
        L.append(f"Cek jam: gerak t0-5->t0-1 searah kejutan {chk:.0f}% (50% = tidak bocor); bar M15 rilis searah "
                 f"{(np.sign(b.bar_rilis) * b.bias > 0).mean() * 100:.0f}%, bar sebelum rilis (15m) "
                 f"{(np.sign(b.bar15m) * b.bias > 0).mean() * 100:.0f}% (n={len(b)})")
    L.append("")
    # 2. seberapa tepat tiap petunjuk menebak arah kejutan
    L.append("== Akurasi menebak ARAH KEJUTAN sebelum rilis (hanya rilis dengan kejutan; 50% = lempar koin) ==")
    tab = res["XAU_EXNESS"][0]
    for m in methods(tab):
        if m.startswith(("STRADDLE", "HEDGE", "ORAKEL", "SELALU")):
            continue
        for a, lab in FEEDS.items():
            n, allp, lo, hi = surprise_accuracy(res[a][0], m)
            if n >= 30:
                L.append(f"  {lab:9} {m:34} n={n:4} benar {allp:4.1f}% | LAMA {lo:4.1f}% | BARU {hi:4.1f}%")
    L.append("")
    # 3. ORAKEL: akurasi minimal agar impas per cara keluar
    L.append("== ORAKEL (arah kejutan diketahui 100%) dan akurasi tebakan minimal agar impas ==")
    for a, lab in FEEDS.items():
        tab, dirn = res[a][0], res[a][1]
        o = tab["ORAKEL (kejutan diketahui)"].to_numpy(dtype=float)
        for e, ex in enumerate(EXITS):
            cells = []
            for s, sc in enumerate(SCEN):
                ok = np.where(o == 1, dirn[:, s, 0, e], np.where(o == -1, dirn[:, s, 1, e], np.nan))
                bad = np.where(o == 1, dirn[:, s, 1, e], np.where(o == -1, dirn[:, s, 0, e], np.nan))
                g, b = np.nanmean(ok), np.nanmean(bad)
                be = -b / (g - b) * 100 if g > b else np.nan
                cells.append(f"{sc} {g:+.2f} (impas >= {be:.0f}%)" if be == be else f"{sc} {g:+.2f} (tidak mungkin)")
            L.append(f"  {lab:9} {ex:28} " + " | ".join(cells))
    L.append("")
    # 4. semua cara x keluar x grup
    L.append("== Semua cara (SEMUA grup, cara keluar pilihan): CEPAT | REALISTIS | STRES ==")
    lolos, n_uji = [], 0
    for m in methods(res["XAU_EXNESS"][0]):
        for e, ex in enumerate(EXITS):
            xs = {a: {sc: series(res[a], m, s, e) for s, sc in enumerate(SCEN)} for a in FEEDS}
            for grp in GROUPS:
                sm = {a: summary(xs[a], grp) for a in FEEDS}
                if grp == "SEMUA" and ex in SHOW:
                    for a, lab in FEEDS.items():
                        c, r, st = sm[a]["CEPAT"], sm[a]["REALISTIS"], sm[a]["STRES"]
                        if c.get("n", 0) >= 30:
                            L.append(fmt(f"  {lab:9} {m} | {ex}", c) + f" | REAL {r['avg']:+.2f} | STRES {st['avg']:+.2f}")
                if all(sm[a]["CEPAT"].get("n", 0) >= 30 for a in FEEDS):
                    n_uji += 1
                    if all(judge(sm[a]["CEPAT"], sm[a]["REALISTIS"]) for a in FEEDS):
                        lolos.append((m, ex, grp, sm))
    L.append("")
    L.append(f"== LOLOS di KEDUA feed: {len(lolos)} dari {n_uji} kombinasi (cara x keluar x grup) yang diuji ==")
    for m, ex, grp, sm in lolos:
        if m.startswith("ORAKEL"):
            continue
        for a, lab in FEEDS.items():
            c, r, st = sm[a]["CEPAT"], sm[a]["REALISTIS"], sm[a]["STRES"]
            L.append(fmt(f"  {lab:9} {m} | {ex} | {grp}", c) + f" | REAL {r['avg']:+.2f} | STRES {st['avg']:+.2f}")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = report()
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"ditulis {OUT}")


if __name__ == "__main__":
    main()
