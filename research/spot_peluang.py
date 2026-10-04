"""Peluang naik lagi untuk koin spot (semua koin besar) — python -m research.spot_peluang

Permintaan pengguna (4 Okt 2026): "bukan hanya koin jatuh — BTC, ETH, BNB, semuanya; bila kemungkinan sangat tinggi
koin itu naik lagi, infokan di aplikasi mulai dari sinyal sampai close spot".

Metode:
  * Candle harian UTC (data.binance.vision via research/spot_dip2.segments), koin besar yang masih hidup + koin yang
    ambruk/delisting (supaya peluang tidak terlalu optimistis).
  * Target: setelah close hari t, beli di open t+1; "naik" = harga menyentuh +TP% dalam N hari (limit jual di TP).
    Bila tidak tersentuh: jual di close hari ke-N. Biaya 0,30% pulang-pergi. Tanpa SL (SL -15% memperburuk, spot_dip2).
  * Fitur (hanya data s.d. close hari t): jarak dari high 20/60 hari, RSI14, RSI2, hari merah beruntun, return 1/3/7/30
    hari, z-score 20 hari, jarak SMA50/SMA200, volatilitas 14 hari, rezim BTC (di atas SMA200, return 7 hari).
  * Model regresi logistik (mudah dipasang di cloud tanpa pustaka berat), dilatih WALK-FORWARD per tahun: tahun Y
    hanya memakai data yang labelnya selesai sebelum 1 Jan Y. Pembanding: gradient boosting, aturan MERAH3, acak.
  * Laporan: kalibrasi (peluang tebakan vs kenyataan), WR & rata-rata per trade, portofolio 10 slot, LAMA/BARU.
  * --simpan: latih model akhir di semua data → cloud/api/spot_model.json (koefisien + statistik teruji).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .spot_dip import COST, SPLIT
from .spot_dip2 import MATI, portfolio, segments

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_spot_peluang.txt"
MODEL = ROOT / "cloud" / "api" / "spot_model.json"
LIVE = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "LINK", "AVAX", "DOT", "LTC", "BCH", "XLM", "ATOM",
        "ETC", "UNI", "NEAR", "AAVE", "FIL"]
# random_state: early stopping otomatis memakai validasi acak -> tanpa ini hasil berubah tiap putaran
GBM = {"max_depth": 3, "learning_rate": 0.05, "max_iter": 200, "min_samples_leaf": 200, "random_state": 0}
FEATS = ["dd20", "dd60", "rsi14", "rsi2", "red", "r1", "r3", "r7", "r30", "z20", "d50", "d200", "vol14", "btc_up",
         "btc_r7"]


def rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def features(d: pd.DataFrame, btc: pd.DataFrame) -> pd.DataFrame:
    """Fitur di close hari t (tanpa melihat masa depan). Sama persis dengan cloud/api/_spot.py."""
    c = d.close
    f = pd.DataFrame(index=d.index)
    f["dd20"] = c / d.high.rolling(20).max() - 1
    f["dd60"] = c / d.high.rolling(60).max() - 1
    f["rsi14"] = rsi(c, 14) / 100
    f["rsi2"] = rsi(c, 2) / 100
    red = (c < d.open).astype(int)
    f["red"] = red.groupby((red == 0).cumsum()).cumsum().clip(upper=6)
    for k in (1, 3, 7, 30):
        f[f"r{k}"] = c / c.shift(k) - 1
    m20, s20 = c.rolling(20).mean(), c.rolling(20).std()
    f["z20"] = (c - m20) / s20
    f["d50"] = c / c.rolling(50).mean() - 1
    f["d200"] = c / c.rolling(200).mean() - 1
    f["vol14"] = np.log(c).diff().rolling(14).std()
    b = btc.close.reindex(d.index).ffill()
    bsma = btc.close.rolling(200).mean().reindex(d.index).ffill()
    f["btc_up"] = (b > bsma).astype(float)
    f["btc_r7"] = b / b.shift(7) - 1
    return f


def labels(d: pd.DataFrame, tp: float, n: int) -> pd.DataFrame:
    """Untuk tiap hari t: beli open t+1; hit = high menyentuh +tp dalam n hari; r bersih; hari keluar."""
    o, h, c = d.open.to_numpy(), d.high.to_numpy(), d.close.to_numpy()
    m = len(d)
    hit = np.full(m, np.nan)
    r = np.full(m, np.nan)
    out = np.full(m, -1)
    for t in range(m - n - 1):
        j = t + 1
        e = o[j]
        tgt = e * (1 + tp)
        k_hit = -1
        for k in range(j, j + n):
            if h[k] >= tgt:
                k_hit = k
                break
        if k_hit >= 0:
            px = max(o[k_hit], tgt) if k_hit > j else tgt
            hit[t], r[t], out[t] = 1, px / e - 1 - COST, k_hit
        else:
            k = j + n - 1
            hit[t], r[t], out[t] = 0, c[k] / e - 1 - COST, k
    return pd.DataFrame({"hit": hit, "r": r, "k": out}, index=d.index)


def dataset(coins: list[str], tp: float, n: int) -> tuple[pd.DataFrame, dict]:
    btc = segments("BTC")[0]
    rows, data = [], {}
    for coin in coins:
        segs = segments(coin)
        if not segs:
            continue
        data[coin] = segs
        for si, d in enumerate(segs):
            name = f"{coin}#{si}" if len(segs) > 1 else coin
            f = features(d, btc)
            lab = labels(d, tp, n)
            x = f.join(lab)
            x["coin"], x["base"] = name, coin
            x["e"] = d.open.shift(-1)
            x["t_in"] = pd.Series(d.index, index=d.index).shift(-1)
            idx = x.k.astype(int)
            x["t_out"] = [d.index[k] if k >= 0 else pd.NaT for k in idx]
            rows.append(x.iloc[200:])        # SMA200 butuh 200 hari
    df = pd.concat(rows).dropna(subset=FEATS + ["hit"])
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS)
    return df, data


def walk_forward(df: pd.DataFrame, n: int, kind: str = "logit") -> pd.Series:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    p = pd.Series(np.nan, index=range(len(df)))
    df = df.reset_index(names="t")
    for y in range(2019, 2027):
        start = pd.Timestamp(f"{y}-01-01", tz="UTC")
        train = df[df.t < start - pd.Timedelta(days=n + 2)]
        test = df[(df.t >= start) & (df.t < pd.Timestamp(f"{y + 1}-01-01", tz="UTC"))]
        if len(train) < 2000 or test.empty:
            continue
        if kind == "logit":
            sc = StandardScaler().fit(train[FEATS])
            m = LogisticRegression(C=0.5, max_iter=2000).fit(sc.transform(train[FEATS]), train.hit)
            p.iloc[test.index] = m.predict_proba(sc.transform(test[FEATS]))[:, 1]
        else:
            from sklearn.ensemble import HistGradientBoostingClassifier
            m = HistGradientBoostingClassifier(**GBM)
            m.fit(train[FEATS], train.hit)
            p.iloc[test.index] = m.predict_proba(test[FEATS])[:, 1]
    return p.to_numpy()


def take(df: pd.DataFrame, mask: np.ndarray) -> pd.DataFrame:
    """Trade tidak tumpang tindih per koin: sinyal berikutnya hanya setelah posisi sebelumnya keluar."""
    out = []
    sel = df[mask].sort_index()
    for coin, g in sel.groupby("coin"):
        free = None
        for t, row in g.iterrows():
            if free is not None and row.t_in <= free:
                continue
            out.append({"coin": coin, "t": row.t_in, "t_out": row.t_out, "e": row.e, "r": row.r, "p": row.get("p")})
            free = row.t_out
    return pd.DataFrame(out)


def line(tr: pd.DataFrame) -> str:
    if tr.empty:
        return "n 0"
    parts = []
    for lab, m in (("LAMA", tr.t < SPLIT), ("BARU", tr.t >= SPLIT), ("2025+", tr.t >= pd.Timestamp("2025-01-01", tz="UTC"))):
        x = tr[m]
        if len(x):
            parts.append(f"{lab} n{len(x)} WR {(x.r > 0).mean() * 100:.0f}% rata {x.r.mean() * 100:+.2f}% "
                         f"kalah {x.r[x.r <= 0].mean() * 100 if (x.r <= 0).any() else 0:+.1f}%")
    return " | ".join(parts) + f" | terburuk {tr.r.min() * 100:+.0f}%"


def run(tp: float, n: int, L: list[str], simpan: bool = False) -> None:
    coins = LIVE + [c for c in MATI if c not in LIVE]
    df, data = dataset(coins, tp, n)
    df = df.sort_index(kind="stable")
    df["p"] = walk_forward(df, n)
    df["pg"] = walk_forward(df, n, "gbm")
    t = df.index
    L += ["", f"## TP +{tp * 100:.0f}% dalam {n} hari  (baris {len(df)}, koin {df.base.nunique()})",
          f"Peluang dasar (semua hari): LAMA {df.hit[t < SPLIT].mean() * 100:.0f}% | BARU {df.hit[t >= SPLIT].mean() * 100:.0f}%"]
    L.append("Kalibrasi walk-forward (peluang tebakan -> kenyataan naik, n hari):")
    ok = df.p.notna()
    for lo_, hi_ in ((0, .6), (.6, .7), (.7, .8), (.8, .85), (.85, .9), (.9, .95), (.95, 1.01)):
        m = ok & (df.p >= lo_) & (df.p < hi_)
        ml, mb = m & (t < SPLIT), m & (t >= SPLIT)
        if m.sum():
            L.append(f"   {lo_:.2f}-{min(hi_, 1):.2f}: LAMA {df.hit[ml].mean() * 100 if ml.sum() else float('nan'):5.1f}% "
                     f"(n{ml.sum():6})  BARU {df.hit[mb].mean() * 100 if mb.sum() else float('nan'):5.1f}% (n{mb.sum():6})")
    rng = np.random.default_rng(5)
    live = df.base.isin(LIVE).to_numpy()
    for lab, src in (("logistik", "p"), ("boosting", "pg")):
        for thr in (0.85, 0.9, 0.93, 0.95):
            for uni, um in (("semua koin", np.ones(len(df), bool)), ("20 koin live", live)):
                mask = (df[src] >= thr).to_numpy() & um
                tr = take(df, mask)
                L.append(f"   {lab} p≥{thr:.2f} {uni:12}: {line(tr)}")
                if lab == "logistik" and uni == "20 koin live" and len(tr):
                    for per, s, e in (("LAMA", pd.Timestamp("2019-01-01", tz="UTC"), SPLIT),
                                      ("BARU", SPLIT, pd.Timestamp("2026-10-01", tz="UTC"))):
                        pf = portfolio(tr, data, 10, s, e)
                        if pf:
                            L.append(f"        portofolio 10 slot {per}: CAGR {pf['cagr'] * 100:+.1f}%/th DD {pf['dd'] * 100:.0f}% "
                                     f"(diambil {pf['taken']}/{pf['n']}) per tahun "
                                     + " ".join(f"{x.year}:{v * 100:+.0f}%" for x, v in pf["tahun"].items()))
                    # acak dengan jumlah sinyal yang sama per koin
                    rm = np.zeros(len(df), bool)
                    for coin, g in df[mask].groupby("coin"):
                        pos = np.where((df.coin == coin).to_numpy() & ok.to_numpy())[0]
                        rm[rng.choice(pos, size=min(len(g), len(pos)), replace=False)] = True
                    L.append(f"        pembanding acak       : {line(take(df, rm))}")
    # aturan sederhana
    mer = ((df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0)).to_numpy() & live & ok.to_numpy()
    L.append(f"   aturan 3 merah ≥10% +SMA200 (20 koin live): {line(take(df, mer))}")
    if simpan:
        save_model(df, tp, n)


def save_model(df: pd.DataFrame, tp: float, n: int, thr: float = 0.9) -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(df[FEATS])
    m = LogisticRegression(C=0.5, max_iter=2000).fit(sc.transform(df[FEATS]), df.hit)
    live = df.base.isin(LIVE).to_numpy()
    tr = take(df, (df.p >= thr).to_numpy() & live)
    b = tr[tr.t >= SPLIT]
    lama = tr[tr.t < SPLIT]
    obj = {
        "dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "tp": tp, "hari": n, "ambang": thr,
        "fitur": FEATS, "mean": list(sc.mean_), "std": list(sc.scale_), "coef": list(m.coef_[0]),
        "intercept": float(m.intercept_[0]), "coins": LIVE,
        "teruji": {"baru": {"n": len(b), "wr": round((b.r > 0).mean() * 100, 1), "avg": round(b.r.mean() * 100, 2),
                            "kalah": round(b.r[b.r <= 0].mean() * 100, 1) if (b.r <= 0).any() else 0,
                            "terburuk": round(b.r.min() * 100, 1)},
                   "lama": {"n": len(lama), "wr": round((lama.r > 0).mean() * 100, 1),
                            "avg": round(lama.r.mean() * 100, 2)}},
    }
    MODEL.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    print("model ->", MODEL)


def main() -> None:
    L = ["# Peluang naik lagi koin spot (research/spot_peluang.py)",
         "Walk-forward per tahun (2019–2026), biaya 0,30%, tanpa SL. LAMA = 2019–Sep 2021, BARU = Okt 2021–Agu 2026."]
    if "--final" in sys.argv:
        final()
        return
    simpan = "--simpan" in sys.argv
    for tp, n in ((0.03, 10), (0.05, 10), (0.05, 20)):
        run(tp, n, L, simpan and (tp, n) == (0.03, 10))
        print("\n".join(L[-40:]), flush=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")



# ------------------------------------------------------------------ model akhir (gradient boosting, dipasang di cloud)


def export_trees(m) -> dict:
    """Pohon HistGradientBoosting -> JSON kecil; dievaluasi tanpa sklearn di cloud/api/_spot.py."""
    trees = []
    for (pred,) in m._predictors:
        nodes = []
        for nd in pred.nodes:
            nodes.append([int(nd["is_leaf"]), int(nd["feature_idx"]), float(nd["num_threshold"]),
                          int(nd["missing_go_to_left"]), int(nd["left"]), int(nd["right"]), float(nd["value"])])
        trees.append(nodes)
    return {"base": float(np.ravel(m._baseline_prediction)[0]), "trees": trees}


def gbm_prob(model: dict, x: list[float]) -> float:
    """Sama dengan cloud/api/_spot.prob (dipakai untuk memeriksa ekspor)."""
    s = model["base"]
    for nodes in model["trees"]:
        i = 0
        while not nodes[i][0]:
            leaf, f, thr, miss_left, left, right, _ = nodes[i]
            v = x[f]
            go_left = miss_left if v != v else v <= thr
            i = left if go_left else right
        s += nodes[i][6]
    return 1 / (1 + np.exp(-s))


def final(tp: float = 0.03, n: int = 10, thr: float = 0.93) -> None:
    from sklearn.ensemble import HistGradientBoostingClassifier
    coins = LIVE + [c for c in MATI if c not in LIVE]
    df, data = dataset(coins, tp, n)
    df = df.sort_index(kind="stable")
    df["pg"] = walk_forward(df, n, "gbm")
    live = df.base.isin(LIVE).to_numpy()
    t = df.index
    L = ["# Model akhir peluang naik spot (gradient boosting, walk-forward per tahun)",
         f"TP +{tp * 100:.0f}% dalam {n} hari, ambang p ≥ {thr:.2f}, 20 koin live. Biaya 0,30%, tanpa SL.",
         "Gabungan = peluang model ≥ ambang ATAU aturan 3 merah ≥10% di atas SMA200 (yang dipasang di cloud).",
         f"Peluang dasar 20 koin: LAMA {df.hit[(t < SPLIT) & live].mean() * 100:.0f}% | "
         f"BARU {df.hit[(t >= SPLIT) & live].mean() * 100:.0f}%", "Kalibrasi (tebakan -> kenyataan):"]
    ok = df.pg.notna()
    for lo_, hi_ in ((0, .8), (.8, .85), (.85, .9), (.9, .93), (.93, .95), (.95, 1.01)):
        m = ok & live & (df.pg >= lo_) & (df.pg < hi_)
        for per, pm in (("LAMA", t < SPLIT), ("BARU", t >= SPLIT)):
            x = df[m & pm]
            if len(x):
                L.append(f"   {lo_:.2f}-{min(hi_, 1):.2f} {per}: naik {x.hit.mean() * 100:5.1f}% (n {len(x)})")
    stats = {}
    rule = ((df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0)).to_numpy() & ok.to_numpy()
    for name, mask in (("gabungan", (((df.pg >= thr).to_numpy()) | rule) & live),
                       (f"boosting p≥{thr}", (df.pg >= thr).to_numpy() & live),
                       ("boosting p≥0.95", (df.pg >= 0.95).to_numpy() & live),
                       ("aturan 3 merah ≥10% +SMA200",
                        ((df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0)).to_numpy() & live & ok.to_numpy())):
        tr = take(df, mask)
        L += ["", f"## {name}", f"   per trade: {line(tr)}"]
        tr["hari"] = (tr.t_out - tr.t).dt.days + 1
        b = tr[tr.t >= SPLIT]
        L.append(f"   BARU: median tahan {b.hari.median():.0f} hari, sinyal/bulan {len(b) / 59:.1f}")
        L.append("   per tahun: " + " ".join(f"{y}:n{len(g)} WR{(g.r > 0).mean() * 100:.0f}% {g.r.mean() * 100:+.1f}%"
                                         for y, g in tr.groupby(tr.t.dt.year)))
        for per, s, e in (("LAMA", pd.Timestamp("2019-01-01", tz="UTC"), SPLIT),
                          ("BARU", SPLIT, pd.Timestamp("2026-10-01", tz="UTC"))):
            for slots in (5, 10):
                pf = portfolio(tr, data, slots, s, e)
                if pf:
                    L.append(f"   portofolio {slots} slot {per}: CAGR {pf['cagr'] * 100:+.1f}%/th DD {pf['dd'] * 100:.0f}% "
                             f"(diambil {pf['taken']}/{pf['n']}) " +
                             " ".join(f"{x.year}:{v * 100:+.0f}%" for x, v in pf["tahun"].items()))
        if name == "gabungan":
            lama = tr[tr.t < SPLIT]
            stats = {"baru": {"n": len(b), "wr": round((b.r > 0).mean() * 100, 1), "avg": round(b.r.mean() * 100, 2),
                              "kalah": round(b.r[b.r <= 0].mean() * 100, 1), "terburuk": round(b.r.min() * 100, 1),
                              "tahan": float(b.hari.median())},
                     "lama": {"n": len(lama), "wr": round((lama.r > 0).mean() * 100, 1),
                              "avg": round(lama.r.mean() * 100, 2)},
                     "dasar_baru": round(df.hit[(t >= SPLIT) & live].mean() * 100, 1),
                     "tahun": {str(y): {"n": len(g), "wr": round((g.r > 0).mean() * 100, 1),
                                        "avg": round(g.r.mean() * 100, 2)} for y, g in tr.groupby(tr.t.dt.year)}}
    # model akhir: semua data s.d. sekarang
    m = HistGradientBoostingClassifier(**GBM).fit(df[FEATS], df.hit)
    model = export_trees(m)
    xs = df[FEATS].sample(2000, random_state=1)
    diff = max(abs(gbm_prob(model, list(r)) - p) for r, p in zip(xs.to_numpy(), m.predict_proba(xs)[:, 1]))
    L.append(f"\nEkspor pohon: selisih maks vs sklearn {diff:.2e} (harus ~0)")
    obj = {"dibuat": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "data_sampai": str(df.index.max().date()),
           "tp": tp, "hari": n, "ambang": thr, "aturan_merah": True, "biaya": COST, "fitur": FEATS, "coins": LIVE, "teruji": stats, **model}
    MODEL.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")
    L.append(f"Model -> {MODEL} ({MODEL.stat().st_size / 1024:.0f} KB)")
    (ROOT / "docs" / "eksternal" / "hasil_spot_model.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
