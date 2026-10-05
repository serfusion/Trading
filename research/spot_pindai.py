"""Pindai spot tiap jam (candle harian masih berjalan) & lebih banyak koin — python -m research.spot_pindai

Permintaan pengguna (5 Okt 2026, URGENT): "Spot Binance seharusnya dipindai beberapa menit bukan per hari dan koinnya
bukan hanya 20, masih banyak koin lain".

Pertanyaan yang diuji (model & ambang SAMA dengan yang terpasang, research/spot_peluang.final):
  1. Pindai tiap jam: di akhir tiap jam, candle harian hari ini yang BELUM tutup dianggap candle terakhir (open hari ini,
     high sejauh ini, close = harga sekarang) -> fitur -> peluang. Entry di open jam berikutnya, limit jual +3%, batas 10
     hari (240 jam), TP dicek dengan high per jam SETELAH entry. Pembanding: pindai harian (hanya jam terakhir hari =
     yang terpasang sekarang) di mesin per jam yang sama.
  2. Koin lain: 20 koin lama vs koin lain yang masih diperdagangkan (sebagian TIDAK pernah ikut pelatihan: ALGO, SHIB,
     SUI, TON, MATIC, XMR, EOS) vs koin yang sudah delisting.
Model walk-forward per tahun (tahun Y dilatih hanya dengan data sebelum Y), pelatihan = semesta yang terpasang (20 koin
lama + koin ambruk/delisting). Biaya 0,30% pulang-pergi. Data 1 jam data.binance.vision (data/research/eksternal/pair_h1).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .pair_data import _dir
from .spot_dip import COST, SPLIT
from .spot_dip2 import MATI, portfolio, segments
from .spot_peluang import FEATS, GBM, LIVE, features, labels

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_spot_pindai.txt"
EXTRA = ["ALGO", "SHIB", "SUI", "TON", "MATIC", "XMR", "EOS"]     # tidak pernah ikut pelatihan
TP, N, THR = 0.03, 10, 0.93
HOURS = N * 24
PASANG = "tiap jam BTC > SMA200"          # skema yang dipasang di cloud (izin/permintaan pengguna 5 Okt 2026)
SLOTS = 20


def hourly(sym: str) -> pd.DataFrame | None:
    if sym == "BTC":
        from .eksternal import asset
        return asset("BTCUSD").b.df[["open", "high", "low", "close"]]
    f = _dir() / f"{sym}USD.parquet"
    return pd.read_parquet(f)[["open", "high", "low", "close"]] if f.exists() else None


def provisional(d: pd.DataFrame, hh: pd.DataFrame, btc_d: pd.DataFrame, btc_h: pd.Series) -> pd.DataFrame:
    """Fitur di akhir TIAP jam: hari-hari yang sudah tutup + candle hari ini yang masih berjalan (sama dengan
    cloud/api/_spot.features bila candle berjalan ditempel sebagai candle terakhir). Jam terakhir hari = fitur harian."""
    C, H, O = d.close, d.high, d.open
    day = hh.index.floor("D")
    pos = pd.Series(np.arange(len(d)), index=d.index)
    k = pos.reindex(day).to_numpy()
    ok = ~np.isnan(k)
    hh, day, k = hh[ok], day[ok], k[ok].astype(int)
    g = hh.groupby(day)
    o_p = g.open.transform("first").to_numpy()
    h_p = g.high.cummax().to_numpy()
    c_p = hh.close.to_numpy()

    def prev(s: pd.Series) -> np.ndarray:            # nilai s di hari k-1 (hari tutup terakhir)
        return s.shift(1).to_numpy()[k]

    f = {}
    f["dd20"] = c_p / np.maximum(prev(H.rolling(19).max()), h_p) - 1
    f["dd60"] = c_p / np.maximum(prev(H.rolling(59).max()), h_p) - 1
    dlt = C.diff()
    for n_, name in ((14, "rsi14"), (2, "rsi2")):
        a = 1 / n_
        up = (1 - a) * prev(dlt.clip(lower=0).ewm(alpha=a, adjust=False).mean()) + a * np.maximum(c_p - prev(C), 0)
        dn = (1 - a) * prev((-dlt.clip(upper=0)).ewm(alpha=a, adjust=False).mean()) + a * np.maximum(prev(C) - c_p, 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            f[name] = np.where(dn > 0, 1 - 1 / (1 + up / np.where(dn > 0, dn, 1)), np.nan)
    red = (C < O).astype(int)
    red_run = red.groupby((red == 0).cumsum()).cumsum()
    f["red"] = np.minimum(np.where(c_p < o_p, prev(red_run) + 1, 0), 6).astype(float)
    for n_ in (1, 3, 7, 30):
        f[f"r{n_}"] = c_p / C.shift(n_ - 1).shift(1).to_numpy()[k] - 1
    s19, q19 = prev(C.rolling(19).sum()), prev((C ** 2).rolling(19).sum())
    m20 = (s19 + c_p) / 20
    v20 = np.maximum((q19 + c_p ** 2 - 20 * m20 ** 2) / 19, 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        f["z20"] = np.where(v20 > 0, (c_p - m20) / np.sqrt(v20), 0.0)
    f["d50"] = c_p / ((prev(C.rolling(49).sum()) + c_p) / 50) - 1
    f["d200"] = c_p / ((prev(C.rolling(199).sum()) + c_p) / 200) - 1
    lr = np.log(C).diff()
    lp = np.log(c_p / prev(C))
    m14 = (prev(lr.rolling(13).sum()) + lp) / 14
    f["vol14"] = np.sqrt(np.maximum((prev((lr ** 2).rolling(13).sum()) + lp ** 2 - 14 * m14 ** 2) / 13, 0))
    # rezim BTC dengan harga BTC jam yang sama
    b_p = btc_h.reindex(hh.index).ffill().to_numpy()
    bc = btc_d.close
    bsum = bc.rolling(199).sum().shift(1).reindex(day).to_numpy()
    f["btc_up"] = (b_p > (bsum + b_p) / 200).astype(float)
    b_al = bc.reindex(d.index).ffill()
    f["btc_r7"] = b_p / b_al.shift(6).shift(1).to_numpy()[k] - 1
    out = pd.DataFrame(f, index=hh.index)[FEATS]
    out["k"] = k
    out["last"] = np.r_[day[1:] != day[:-1], True]       # jam terakhir hari itu (= pindai harian)
    return out


def train_models(df: pd.DataFrame) -> dict[int, object]:
    from sklearn.ensemble import HistGradientBoostingClassifier
    models = {}
    t = df.index
    for y in range(2019, 2027):
        start = pd.Timestamp(f"{y}-01-01", tz="UTC")
        train = df[t < start - pd.Timedelta(days=N + 2)]
        if len(train) < 2000:
            continue
        models[y] = HistGradientBoostingClassifier(**GBM).fit(train[FEATS], train.hit)
    return models


def predict(models: dict, x: pd.DataFrame) -> np.ndarray:
    p = np.full(len(x), np.nan)
    yrs = x.index.year.to_numpy()
    for y, m in models.items():
        sel = yrs == y
        if sel.any():
            p[sel] = m.predict_proba(x.loc[sel, FEATS])[:, 1]
    return p


def sim(hh: pd.DataFrame, sig: np.ndarray, coin: str) -> list[dict]:
    """Satu posisi per koin. Sinyal di akhir jam j -> beli open jam j+1; TP = high jam setelah entry >= +3%."""
    o, h, c = hh.open.to_numpy(), hh.high.to_numpy(), hh.close.to_numpy()
    t = hh.index
    idx = np.flatnonzero(sig)
    out, free = [], -1
    for j in idx:
        if j < free or j + 1 >= len(hh):
            continue
        e = o[j + 1]
        end = min(j + HOURS, len(hh) - 1)
        if t[end] - t[j + 1] < pd.Timedelta(hours=HOURS - 1) and end == len(hh) - 1:
            break                                       # data habis sebelum batas waktu
        w = h[j + 1:end + 1]
        hit = np.flatnonzero(w >= e * (1 + TP))
        if hit.size:
            kk = j + 1 + hit[0]
            px = max(o[kk], e * (1 + TP)) if kk > j + 1 else e * (1 + TP)
        else:
            kk = end
            px = c[kk]
        out.append({"coin": coin, "t": t[j + 1], "t_out": t[kk], "e": e, "r": px / e - 1 - COST,
                    "jam": t[j].hour})
        free = kk                                       # sinyal berikutnya paling cepat di jam keluar
    return out


def stat(tr: pd.DataFrame) -> str:
    if tr.empty:
        return "n 0"
    parts = []
    for lab, m in (("LAMA", tr.t < SPLIT), ("BARU", tr.t >= SPLIT), ("2025+", tr.t >= pd.Timestamp("2025-01-01", tz="UTC"))):
        x = tr[m]
        if len(x):
            parts.append(f"{lab} n{len(x)} naik {(x.r > 0).mean() * 100:.0f}% rata {x.r.mean() * 100:+.2f}% "
                         f"kalah {x.r[x.r <= 0].mean() * 100 if (x.r <= 0).any() else 0:+.1f}%")
    return " | ".join(parts) + f" | terburuk {tr.r.min() * 100:+.0f}%"


def main() -> None:
    train_coins = LIVE + [c for c in MATI if c not in LIVE]
    all_coins = train_coins + [c for c in EXTRA if c not in train_coins]
    btc_d = segments("BTC")[0]
    btc_hh = hourly("BTC")
    rows, data, hseg = [], {}, {}
    for coin in all_coins:
        segs = segments(coin)
        h = hourly(coin)
        if not segs or h is None:
            continue
        data[coin] = segs
        for si, d in enumerate(segs):
            name = f"{coin}#{si}" if len(segs) > 1 else coin
            x = features(d, btc_d).join(labels(d, TP, N))
            x["coin"], x["base"] = name, coin
            rows.append(x.iloc[200:])
            hseg[name] = (coin, d, h[(h.index >= d.index[0]) & (h.index < d.index[-1] + pd.Timedelta(days=1))])
    df = pd.concat(rows).dropna(subset=FEATS + ["hit"]).replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS)
    df = df.sort_index(kind="stable")
    models = train_models(df[df.base.isin(train_coins)])
    alive = {c for c, segs in data.items() if segs[-1].index[-1] >= pd.Timestamp("2026-08-30", tz="UTC")}
    groups = {"20 koin lama": set(LIVE), "koin lain masih hidup": alive - set(LIVE),
              "  di antaranya tidak pernah dilatih": alive & set(EXTRA), "koin delisting": set(data) - alive}
    L = ["# Pindai spot tiap jam & lebih banyak koin (research/spot_pindai.py)",
         f"Model terpasang (gradient boosting, ambang {THR}, + aturan 3 merah), walk-forward per tahun. TP +{TP * 100:.0f}%"
         f" / {N} hari, biaya 0,30%. LAMA < Okt 2021, BARU >= Okt 2021. Data s.d. 31 Agu 2026.",
         "Grup: " + "; ".join(f"{g} ({len(s & set(data))}): {', '.join(sorted(s & set(data)))}" for g, s in groups.items())]
    trades = {"harian": [], "tiap jam": [], "tiap jam p≥0.95": [], "tiap jam bertahan 2 jam": [],
              "tiap jam bertahan 3 jam": [], "tiap jam BTC > SMA200": [], "harian BTC > SMA200": []}
    check = []
    for name, (coin, d, hh) in hseg.items():
        x = provisional(d, hh, btc_d, btc_hh.close)
        x = x[x.k >= 200].replace([np.inf, -np.inf], np.nan)
        good = x[FEATS].notna().all(axis=1).to_numpy()
        p = predict(models, x)
        p[~good] = np.nan
        rule = ((x.red >= 3) & (x.r3 <= -0.10) & (x.d200 > 0)).to_numpy() & good
        last = x["last"].to_numpy()
        hx = hh.loc[x.index]
        # cek: fitur jam terakhir hari == fitur harian riset
        ref = df[df.coin == name][FEATS]
        lx = x[last & good].iloc[:, :len(FEATS)]
        both = ref.index.intersection(lx.index.floor("D"))
        if len(both):
            a = lx.set_axis(lx.index.floor("D")).loc[both].to_numpy(float)
            check.append(np.nanmax(np.abs(a - ref.loc[both].to_numpy(float)) / (1e-9 + np.abs(ref.loc[both].to_numpy(float)))))
        trades["harian"] += sim(hx, ((p >= THR) | rule) & last, name)
        trades["tiap jam"] += sim(hx, (p >= THR) | rule, name)
        trades["tiap jam p≥0.95"] += sim(hx, (p >= 0.95) | rule, name)
        s1 = (p >= THR) | rule
        s2 = s1 & np.r_[False, s1[:-1]]
        trades["tiap jam bertahan 2 jam"] += sim(hx, s2, name)
        trades["tiap jam bertahan 3 jam"] += sim(hx, s2 & np.r_[False, s2[:-1]], name)
        trades["tiap jam BTC > SMA200"] += sim(hx, s1 & (x.btc_up == 1).to_numpy(), name)
        trades["harian BTC > SMA200"] += sim(hx, s1 & last & (x.btc_up == 1).to_numpy(), name)
    L.append(f"Cek fitur jam terakhir = fitur harian riset: selisih relatif maks median {np.median(check):.1e}, "
             f"maks {np.max(check):.1e} (koin dengan celah data)")
    hourly_tr = pd.DataFrame(trades["tiap jam"]).sort_values(["t", "coin"])
    for k_ in (2, 3, 5):                                  # maks k entry baru per hari (semua koin) -> kurangi gerombol
        trades[f"tiap jam maks {k_} baru/hari"] = hourly_tr[hourly_tr.groupby(hourly_tr.t.dt.floor("D")).cumcount() < k_]
    for mode, tr in trades.items():
        tr = pd.DataFrame(tr)
        tr["base"] = tr.coin.str.split("#").str[0]
        L += ["", f"## Pindai {mode}"]
        for g, s in groups.items():
            L.append(f"   {g:36}: {stat(tr[tr.base.isin(s)])}")
        for uni_name, s in (("20 koin lama", set(LIVE)), ("semua koin hidup", alive)):
            sub = tr[tr.base.isin(s)]
            b = sub[sub.t >= SPLIT]
            L.append(f"   {uni_name}: sinyal BARU per bulan {len(b) / 59:.1f}; per tahun " +
                     " ".join(f"{y}:n{len(gg)} {(gg.r > 0).mean() * 100:.0f}% {gg.r.mean() * 100:+.1f}%"
                              for y, gg in sub.groupby(sub.t.dt.year)))
            for slots in (10, 20):
                for per, s0, e0 in (("LAMA", pd.Timestamp("2019-01-01", tz="UTC"), SPLIT),
                                    ("BARU", SPLIT, pd.Timestamp("2026-09-01", tz="UTC"))):
                    pf = portfolio(sub, data, slots, s0, e0)
                    if pf:
                        L.append(f"      portofolio {slots} slot {per}: {pf['cagr'] * 100:+.1f}%/th DD {pf['dd'] * 100:.0f}% "
                                 f"(diambil {pf['taken']}/{pf['n']}) " +
                                 " ".join(f"{t_.year}:{v * 100:+.0f}%" for t_, v in pf["tahun"].items()))
        if mode == "tiap jam":
            b = tr[(tr.t >= SPLIT) & tr.base.isin(alive)]
            L.append("   BARU semua koin hidup per jam sinyal (UTC): " +
                     " ".join(f"{hr}:{(g_.r > 0).mean() * 100:.0f}%/{g_.r.mean() * 100:+.1f}%"
                              for hr, g_ in b.groupby((b.jam // 4) * 4)))
    if "--simpan" in sys.argv:
        L.append(save_stats(pd.DataFrame(trades[PASANG]), df, data, alive))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def save_stats(tr: pd.DataFrame, df: pd.DataFrame, data: dict, alive: set) -> str:
    """Angka 'teruji' skema terpasang (pindai tiap jam, semua koin hidup, BTC > SMA200, 20 slot) -> spot_model.json.
    Pohon model TIDAK berubah (model sama dengan research/spot_peluang.final)."""
    import json
    path = ROOT / "cloud" / "api" / "spot_model.json"
    model = json.loads(path.read_text(encoding="utf-8"))
    tr["base"] = tr.coin.str.split("#").str[0]
    tr = tr[tr.base.isin(alive)]
    tr["hari"] = (tr.t_out - tr.t).dt.total_seconds() / 86400
    b, lama = tr[tr.t >= SPLIT], tr[tr.t < SPLIT]
    pf = portfolio(b, data, SLOTS, SPLIT, pd.Timestamp("2026-09-01", tz="UTC"))
    pl = portfolio(lama, data, SLOTS, pd.Timestamp("2019-01-01", tz="UTC"), SPLIT)
    bulan = (pd.Timestamp("2026-09-01", tz="UTC") - SPLIT).days / 30.44
    model["teruji"] = {
        "skema": f"pindai tiap 10 menit, {len(alive)} koin uji, BTC > SMA200, maks {SLOTS} posisi",
        "baru": {"n": len(b), "wr": round((b.r > 0).mean() * 100, 1), "avg": round(b.r.mean() * 100, 2),
                 "kalah": round(b.r[b.r <= 0].mean() * 100, 1), "terburuk": round(b.r.min() * 100, 1),
                 "tahan": round(float(b.hari.median()), 1), "per_bulan": round(len(b) / bulan, 1),
                 "cagr": round(pf["cagr"] * 100, 1), "dd": round(pf["dd"] * 100, 1)},
        "lama": {"n": len(lama), "wr": round((lama.r > 0).mean() * 100, 1), "avg": round(lama.r.mean() * 100, 2),
                 "cagr": round(pl["cagr"] * 100, 1), "dd": round(pl["dd"] * 100, 1)},
        "dasar_baru": round(df.hit[(df.index >= SPLIT) & df.base.isin(alive)].mean() * 100, 1),
        "tahun": {str(y): {"n": len(g), "wr": round((g.r > 0).mean() * 100, 1), "avg": round(g.r.mean() * 100, 2)}
                  for y, g in tr.groupby(tr.t.dt.year)},
    }
    model["btc_filter"] = True
    path.write_text(json.dumps(model, separators=(",", ":")), encoding="utf-8")
    return f"\nteruji -> {path.name}: " + json.dumps(model["teruji"], ensure_ascii=False)


if __name__ == "__main__":
    main()
