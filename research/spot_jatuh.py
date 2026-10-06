"""Spot: semua koin Binance + deteksi "akan turun jauh" — python -m research.spot_jatuh

Permintaan pengguna (5 Okt 2026): "cek seluruhnya, supaya WR dan profit tinggi dan bisa deteksi apabila ingin turun jauh".

Data: candle harian SEMUA pair USDT Binance termasuk yang sudah delisting (research/spot_semua.py). Semesta tiap hari =
100 koin dengan volume USDT rata-rata 7 hari terbesar s.d. KEMARIN (tanpa melihat masa depan), riwayat >= 201 hari —
sama dengan cloud (100 koin volume terbesar). Sinyal = model terpasang (walk-forward, p >= 0,93 atau 3 merah) + BTC >
SMA200, beli open besok, limit jual +3%, maks 10 hari, biaya 0,30%.

"Turun jauh" = sebelum TP kena, harga sempat turun >= 10% dari harga beli (atau hasil akhir rugi). Pendeteksi diuji:
  A. aturan sederhana (dipilih di LAMA, dilihat di BARU): koin baru (< 365 hari), koin sudah ambruk dari puncak 1 tahun,
     volume panik, hari crash pasar (median koin turun), banyak sinyal bersamaan, BTC turun tajam;
  B. model "risiko jatuh" (gradient boosting walk-forward, dilatih hanya dari sinyal tahun-tahun sebelumnya);
  C. keluar lebih awal saat posisi berjalan bila pasar crash / BTC jatuh ke bawah SMA200.
LAMA = 2019 – Sep 2021, BARU = Okt 2021 – Sep 2026.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .spot_dip import COST, SPLIT
from .spot_dip2 import MATI, portfolio
from .spot_peluang import FEATS, GBM, LIVE, features, labels
from .spot_semua import load_all

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_spot_jatuh.txt"
TP, N, THR = 0.03, 10, 0.93
TOP = 100
END = pd.Timestamp("2026-10-01", tz="UTC")
# filter kualitas yang dipasang (5 Okt 2026): koin umur >= 1 tahun, bukan volume panik >= 3x rata 30 hari,
# belum ambruk >= 80% dari puncak 1 tahun
KUALITAS = {"umur_min": 365, "vol_panik": 3.0, "ambruk": -0.80}
EXTRA = ["dd365", "age", "qv_rel", "lqv", "rank", "b_med_r1", "b_below50", "b_red", "btc_r1", "btc_r3", "btc_dd20",
         "n_sig"]


def segs(d: pd.DataFrame) -> list[pd.DataFrame]:
    d = d[(d.close > 0) & (d.low > 0)]
    cut = np.where(d.index.to_series().diff() > pd.Timedelta(days=3))[0]
    out, a = [], 0
    for b in list(cut) + [len(d)]:
        if b - a >= 120:
            out.append(d.iloc[a:b])
        a = b
    return out


def build() -> tuple[pd.DataFrame, dict]:
    raw = load_all()
    btc = raw["BTC"]
    rows, data = [], {}
    for coin, d0 in raw.items():
        ss = segs(d0)
        if not ss:
            continue
        data[coin] = ss
        first = d0.index[0]
        for si, d in enumerate(ss):
            name = f"{coin}#{si}" if len(ss) > 1 else coin
            x = features(d, btc).join(labels(d, TP, N))
            c = d.close
            x["dd365"] = c / d.high.rolling(365, min_periods=200).max() - 1
            x["age"] = (d.index - first).days
            q = d.qv.shift(1)                                    # volume s.d. kemarin (pemilihan semesta)
            x["qv7"] = q.rolling(7).mean()
            x["qv_rel"] = d.qv / d.qv.rolling(30).mean()          # volume hari sinyal vs 30 hari (panik?)
            x["lqv"] = np.log10(d.qv.rolling(30).mean() + 1)
            # turun jauh sebelum TP: low terendah dari entry s.d. keluar
            lo = d.low.to_numpy()
            k = x.k.to_numpy()
            e = d.open.shift(-1).to_numpy()
            mdd = np.full(len(d), np.nan)
            for i in range(len(d) - 1):
                if k[i] >= 0:
                    mdd[i] = lo[i + 1:k[i] + 1].min() / e[i] - 1 if k[i] >= i + 1 else np.nan
            x["mdd"] = mdd
            x["e"] = e
            x["t_in"] = pd.Series(d.index, index=d.index).shift(-1)
            x["t_out"] = [d.index[j] if j >= 0 else pd.NaT for j in k.astype(int)]
            x["coin"], x["base"] = name, coin
            rows.append(x.iloc[200:])
    df = pd.concat(rows)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS + ["hit"])
    df = df[df.index < END]
    # semesta harian: 100 koin volume terbesar (rata-rata 7 hari s.d. kemarin)
    df["rank"] = df.groupby(level=0).qv7.rank(ascending=False, method="first")
    # kondisi pasar (semua koin dalam semesta hari itu)
    uni = df[df["rank"] <= TOP]
    g = uni.groupby(level=0)
    mkt = pd.DataFrame({"b_med_r1": g.r1.median(), "b_below50": g.d50.apply(lambda s: (s < 0).mean()),
                        "b_red": g.red.apply(lambda s: (s >= 1).mean())})
    df = df.join(mkt)
    bf = features(btc, btc)
    bt = pd.DataFrame({"btc_r1": bf.r1, "btc_r3": bf.r3, "btc_dd20": bf.dd20})
    df = df.join(bt)
    return df.sort_index(kind="stable"), data


def wf_models(train: pd.DataFrame) -> dict:
    from sklearn.ensemble import HistGradientBoostingClassifier
    models = {}
    for y in range(2019, 2027):
        tr = train[train.index < pd.Timestamp(f"{y}-01-01", tz="UTC") - pd.Timedelta(days=N + 2)]
        if len(tr) >= 2000:
            models[y] = HistGradientBoostingClassifier(**GBM).fit(tr[FEATS], tr.hit)
    return models


def predict(models: dict, x: pd.DataFrame, cols=FEATS) -> np.ndarray:
    p = np.full(len(x), np.nan)
    yrs = x.index.year.to_numpy()
    for y, m in models.items():
        sel = yrs == y
        if sel.any():
            p[sel] = m.predict_proba(x.loc[sel, cols])[:, 1]
    return p


def take(sig: pd.DataFrame) -> pd.DataFrame:
    """Satu posisi per koin (sinyal berikutnya setelah keluar)."""
    out = []
    for coin, g in sig.sort_index().groupby("coin"):
        free = None
        for t, r in g.iterrows():
            if free is not None and r.t_in <= free:
                continue
            out.append({"coin": coin, "t": r.t_in, "t_out": r.t_out, "e": r.e, "r": r.r, "mdd": r.mdd, "row": t,
                        **{c: r[c] for c in ("p", "risk") if c in r}})
            free = r.t_out
    return pd.DataFrame(out)


def stat(tr: pd.DataFrame) -> str:
    if tr.empty:
        return "n 0"
    parts = []
    for lab, m in (("LAMA", tr.t < SPLIT), ("BARU", tr.t >= SPLIT)):
        x = tr[m]
        if len(x):
            parts.append(f"{lab} n{len(x)} naik {(x.r > 0).mean() * 100:.1f}% rata {x.r.mean() * 100:+.2f}% "
                         f"jatuh≥10% {(x.mdd <= -0.10).mean() * 100:.0f}%")
    return " | ".join(parts) + f" | terburuk {tr.r.min() * 100:+.0f}%"


def pf_line(tr: pd.DataFrame, data: dict, slots: int = 20) -> str:
    out = []
    for per, s, e in (("LAMA", pd.Timestamp("2019-01-01", tz="UTC"), SPLIT), ("BARU", SPLIT, END)):
        pf = portfolio(tr, data, slots, s, e)
        if pf:
            out.append(f"{per} {pf['cagr'] * 100:+.1f}%/th DD {pf['dd'] * 100:.0f}%")
    return " | ".join(out)


def main() -> None:
    df, data = build()
    train_coins = set(LIVE) | set(MATI)
    models = wf_models(df[df.base.isin(train_coins)])
    df["p"] = predict(models, df)
    sig_mask = ((df.p >= THR) | ((df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0))) & (df.btc_up == 1) & \
        (df["rank"] <= TOP) & df.p.notna()
    df["n_sig"] = sig_mask.groupby(level=0).transform("sum")
    sig = df[sig_mask].copy()
    base = take(sig)
    L = ["# Spot: semua koin Binance + deteksi turun jauh (research/spot_jatuh.py)",
         f"Koin dengan data: {len(data)}; semesta harian = {TOP} volume terbesar (7 hari s.d. kemarin), riwayat >= 201 hari.",
         f"Sinyal model terpasang (walk-forward) + BTC > SMA200, pindai harian (pindai tiap 10 menit: lihat SPOT_PINDAI).",
         "", "## Dasar (yang terpasang)", f"   per trade: {stat(base)}", f"   portofolio 20 slot: {pf_line(base, data)}"]
    sb = base[base.t >= SPLIT]
    L.append(f"   BARU per bulan {len(sb) / 60:.1f}; rata kalah {sb.r[sb.r <= 0].mean() * 100:+.1f}%; "
             f"per tahun: " + " ".join(f"{y}:n{len(g)} {(g.r > 0).mean() * 100:.0f}% {g.r.mean() * 100:+.1f}%"
                                       for y, g in base.groupby(base.t.dt.year)))
    for lvl in (0.10, 0.20):
        for per, pm in (("LAMA", base.t < SPLIT), ("BARU", base.t >= SPLIT)):
            x = base[pm & (base.mdd <= -lvl)]
            L.append(f"   sempat turun >= {lvl * 100:.0f}% dari beli: {per} {len(x) / max(pm.sum(), 1) * 100:.0f}% posisi, "
                     f"tetap kena TP {(x.r > 0).mean() * 100:.0f}%, rata akhir {x.r.mean() * 100:+.1f}%")
    # A. aturan sederhana: pilih ambang di LAMA
    L += ["", "## A. Aturan sederhana (dilewati bila ...): LAMA -> BARU"]
    sx = sig.copy()
    sx["row"] = sx.index
    bx = base.merge(sx.reset_index(drop=True)[["coin", "row"] + FEATS + EXTRA], on=["coin", "row"], how="left")
    rules = {
        "koin umur < 365 hari": bx.age < 365,
        "koin umur < 730 hari": bx.age < 730,
        "ambruk >= 80% dari puncak 1 th": bx.dd365 <= -0.80,
        "ambruk >= 60% dari puncak 1 th": bx.dd365 <= -0.60,
        "volume panik >= 3x": bx.qv_rel >= 3,
        "volume panik >= 2x": bx.qv_rel >= 2,
        "pasar crash (median koin <= -5%)": bx.b_med_r1 <= -0.05,
        "pasar crash (median koin <= -3%)": bx.b_med_r1 <= -0.03,
        ">= 70% koin di bawah SMA50": bx.b_below50 >= 0.70,
        ">= 10 sinyal bersamaan": bx.n_sig >= 10,
        ">= 5 sinyal bersamaan": bx.n_sig >= 5,
        "BTC turun >= 5% 3 hari": bx.btc_r3 <= -0.05,
        "BTC -10% dari high 20 hari": bx.btc_dd20 <= -0.10,
        "volatilitas koin tinggi (vol14 >= 8%)": bx.vol14 >= 0.08,
        "rank volume 51-100": bx["rank"] > 50,
        "turun 30 hari >= 30%": bx.r30 <= -0.30,
    }
    for name, m in rules.items():
        m = m.fillna(False).to_numpy()
        keep = base[~m]
        lama_gain = keep[keep.t < SPLIT].r.mean() - base[base.t < SPLIT].r.mean()
        L.append(f"   {name:38} dilewati {m.mean() * 100:4.1f}% | sisa {stat(keep)} | LAMA rata {lama_gain * 100:+.2f}% "
                 f"| pf {pf_line(keep, data)}")
    # B. model risiko jatuh (meta-label) walk-forward pada sinyal
    from sklearn.ensemble import HistGradientBoostingClassifier
    cols = FEATS + EXTRA
    bx["jatuh"] = ((bx.mdd <= -0.10) | (bx.r <= 0)).astype(int)
    bx["risk"] = np.nan
    for y in range(2020, 2027):
        start = pd.Timestamp(f"{y}-01-01", tz="UTC")
        tr = bx[bx.t_out < start]
        te = (bx.t >= start) & (bx.t < pd.Timestamp(f"{y + 1}-01-01", tz="UTC"))
        if len(tr) < 300 or tr.jatuh.nunique() < 2 or not te.any():
            continue
        m = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=50,
                                           random_state=0).fit(tr[cols], tr.jatuh)
        bx.loc[te, "risk"] = m.predict_proba(bx.loc[te, cols])[:, 1]
    from sklearn.metrics import roc_auc_score
    ok = bx.risk.notna()
    L += ["", "## B. Model risiko jatuh (walk-forward, dilatih dari sinyal tahun-tahun sebelumnya)"]
    for per, pm in (("LAMA", bx.t < SPLIT), ("BARU", bx.t >= SPLIT)):
        mm = ok & pm
        if mm.sum() > 50 and bx.jatuh[mm].nunique() == 2:
            L.append(f"   AUC {per}: {roc_auc_score(bx.jatuh[mm], bx.risk[mm]):.3f} (0,5 = tebak acak) n {mm.sum()}")
    for q in (0.9, 0.8, 0.7):
        thr_lama = bx.risk[ok & (bx.t < SPLIT)].quantile(q) if (ok & (bx.t < SPLIT)).sum() > 50 else np.nan
        if np.isnan(thr_lama):
            continue
        m = (bx.risk >= thr_lama).fillna(False).to_numpy()
        keep = base[~m]
        L.append(f"   lewati risiko >= persentil {q * 100:.0f} LAMA ({thr_lama:.2f}): dilewati {m.mean() * 100:.0f}% | "
                 f"sisa {stat(keep)} | pf {pf_line(keep, data)}")
        x = bx[m & (bx.t >= SPLIT).to_numpy()]
        L.append(f"      yang dilewati BARU: n{len(x)} naik {(x.r > 0).mean() * 100:.0f}% rata {x.r.mean() * 100:+.2f}%")
    # D. definisi sinyal lain (ambang, tanpa aturan 3 merah, model dilatih semua koin, gabungan aturan)
    L += ["", "## D. Varian sinyal (dipilih bila LAMA dan BARU sama-sama lebih baik)"]
    all_models = wf_models(df[df["rank"] <= TOP])
    df["p_all"] = predict(all_models, df)
    rule3 = (df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0)
    gate = (df.btc_up == 1) & (df["rank"] <= TOP) & df.p.notna()
    good = (df.age >= KUALITAS["umur_min"]) & ~(df.qv_rel >= KUALITAS["vol_panik"]) & \
        ~(df.dd365 <= KUALITAS["ambruk"])
    variants = {
        "p>=0.95 + 3 merah": ((df.p >= 0.95) | rule3) & gate,
        "p>=0.97 + 3 merah": ((df.p >= 0.97) | rule3) & gate,
        "p>=0.93 tanpa 3 merah": (df.p >= THR) & gate,
        "hanya 3 merah": rule3 & gate,
        "model dilatih 100 koin teratas": ((df.p_all >= THR) | rule3) & gate & df.p_all.notna(),
        "umur>=1th, tanpa volume panik, tanpa ambruk 80%": ((df.p >= THR) | rule3) & gate & good,
        "  + p>=0.95": ((df.p >= 0.95) | rule3) & gate & good,
        "semesta 50 koin teratas": ((df.p >= THR) | rule3) & gate & (df["rank"] <= 50),
        "semesta 200 koin teratas": ((df.p >= THR) | rule3) & (df.btc_up == 1) & (df["rank"] <= 200) & df.p.notna(),
    }
    for name, m in variants.items():
        tr = take(df[m.fillna(False)])
        L.append(f"   {name:46}: {stat(tr)} | pf {pf_line(tr, data)}")
        if name.startswith("umur>=1th") and "--simpan" in sys.argv:
            L.append(save(tr, data))

    # C. keluar lebih awal saat posisi berjalan (dicek di close harian, jual open besok)
    L += ["", "## C. Keluar lebih awal saat pasar/koin jatuh (dicek tiap close harian, jual di open besok)"]
    day = df.groupby(level=0).first()[["b_med_r1", "btc_up", "btc_r1"]]
    conds = {"pasar crash (median koin <= -5%)": day.b_med_r1 <= -0.05,
             "BTC turun ke bawah SMA200": day.btc_up < 1,
             "BTC turun >= 5% sehari": day.btc_r1 <= -0.05}
    for name, cond in conds.items():
        L.append(f"   {name:34}: {stat(early(base, data, cond))} | pf {pf_line(early(base, data, cond), data)}")
    for lvl in (0.10, 0.15, 0.20):
        tr = early(base, data, None, stop=lvl)
        L.append(f"   {'koin turun >= %d%% dari beli (close)' % (lvl * 100):34}: {stat(tr)} | pf {pf_line(tr, data)}")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def save(tr: pd.DataFrame, data: dict) -> str:
    """Filter kualitas (KUALITAS) + angka teruji semua koin Binance -> cloud/api/spot_model.json (pohon tidak berubah)."""
    import json
    path = ROOT / "cloud" / "api" / "spot_model.json"
    model = json.loads(path.read_text(encoding="utf-8"))
    b, lama = tr[tr.t >= SPLIT], tr[tr.t < SPLIT]
    pb = portfolio(b, data, 20, SPLIT, END)
    pl = portfolio(lama, data, 20, pd.Timestamp("2019-01-01", tz="UTC"), SPLIT)
    jatuh = {}
    for lvl in (10, 20):
        x = b[b.mdd <= -lvl / 100]
        jatuh[str(lvl)] = {"porsi": round(len(x) / len(b) * 100, 1), "tetap_tp": round((x.r > 0).mean() * 100, 1),
                           "akhir": round(x.r.mean() * 100, 1)}
    model["kualitas"] = KUALITAS
    model["teruji"] = {
        "skema": "semua koin Binance (100 volume terbesar), BTC > SMA200, filter kualitas, maks 20 posisi",
        "baru": {"n": len(b), "wr": round((b.r > 0).mean() * 100, 1), "avg": round(b.r.mean() * 100, 2),
                 "kalah": round(b.r[b.r <= 0].mean() * 100, 1), "terburuk": round(b.r.min() * 100, 1),
                 "per_bulan": round(len(b) / 60, 1), "cagr": round(pb["cagr"] * 100, 1), "dd": round(pb["dd"] * 100, 1)},
        "lama": {"n": len(lama), "wr": round((lama.r > 0).mean() * 100, 1), "avg": round(lama.r.mean() * 100, 2),
                 "cagr": round(pl["cagr"] * 100, 1), "dd": round(pl["dd"] * 100, 1)},
        "jatuh": jatuh,
        "tahun": {str(y): {"n": len(g), "wr": round((g.r > 0).mean() * 100, 1), "avg": round(g.r.mean() * 100, 2)}
                  for y, g in tr.groupby(tr.t.dt.year)},
    }
    path.write_text(json.dumps(model, separators=(",", ":")), encoding="utf-8")
    return "      teruji -> spot_model.json: " + json.dumps(model["teruji"], ensure_ascii=False)


def early(base: pd.DataFrame, data: dict, cond: pd.Series | None, stop: float | None = None) -> pd.DataFrame:
    """Trade dengan aturan keluar lebih awal: kondisi pasar `cond` (per hari) atau close koin <= beli x (1-stop).
    Hanya hari SEBELUM TP/keluar asli; jual di open hari berikutnya."""
    frames = {}
    for coin, ss in data.items():
        for si, d in enumerate(ss):
            frames[f"{coin}#{si}" if len(ss) > 1 else coin] = d
    out = []
    cset = set(cond[cond].index) if cond is not None else set()
    for r in base.itertuples(index=False):
        d = frames[r.coin]
        o, c = d.open, d.close
        days = d.index[(d.index >= r.t) & (d.index < r.t_out)]
        new = r._asdict()
        for dd in days:
            hit_stop = stop is not None and c.loc[dd] <= r.e * (1 - stop)
            if dd in cset or hit_stop:
                nxt = d.index[d.index > dd]
                if len(nxt) and nxt[0] <= r.t_out:
                    new.update(r=o.loc[nxt[0]] / r.e - 1 - COST, t_out=nxt[0])
                break
        out.append(new)
    return pd.DataFrame(out)


if __name__ == "__main__":
    main()
