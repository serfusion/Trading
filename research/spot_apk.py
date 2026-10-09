"""💎 Spot dip di APK: uji JUJUR kandidat tambahan (filter / label / semesta) — python -m research.spot_apk

Permintaan pengguna (8 Okt 2026): "spot dip jika ada di Binance dengan WR dan profit yang memungkinkan, tambah saja di
apk". Riset ini TIDAK mengubah cloud/ atau android/; hasilnya usulan + angka teruji jujur untuk kartu 💎.

Dasar = skema terpasang cloud/api/_spot.py (p >= 0,93 ATAU 3 merah, lewati vol14 > P90, TP +3% / 10 hari, tanpa SL,
maks 10 posisi, tanpa filter BTC) tetapi dengan semesta JUJUR: 20 koin volume USDT terbesar SAAT ITU (rata-rata 7 hari
s.d. kemarin, termasuk koin yang kemudian delisting) = varian E research/spot_paritas.py. Kandidat:
  a) BTC > SMA200 sebagai FILTER vs LABEL (sinyal tetap tampil, statistik per rezim);
  b) filter kualitas (umur >= 1 th, belum ambruk >= 80% dari puncak 1 th, bukan volume panik >= 3x);
  c) semesta top-N volume saat itu (N 20/30/50/100) dengan 10/20 slot;
  d) label peringkat keyakinan (p model, model + 3 merah, vol rendah, ...) -> ⚡/🥈/biasa, dipilih dari LAMA;
  e) lain dari riset lama: ambang 0,95/0,97 (SPOT_JATUH), lewati vol > P70 (SPOT_PELUANG), tanpa filter vol, model
     dilatih semesta jujur (bukan 20 koin hari ini), semesta dari volume 24 jam (ticker 1 panggilan), TP harus tembus.
Model gradient boosting WALK-FORWARD per tahun (tahun Y dilatih data < Y). LAMA = Jan 2020 – Sep 2021 (model 2019 tidak
ada), BARU = Okt 2021 – Sep 2026. Biaya 0,30% (dan x2). Pembanding acak: jumlah sinyal/bulan sama, hari & koin acak di semesta yang sama.
Statistik "per sinyal" = sinyal yang MASUK SLOT (= yang benar-benar dikirim cloud, karena cloud tidak mengirim sinyal
saat posisi penuh); "semua" = sebelum batas slot (seperti spot_paritas).

VERIFIKASI adversarial 8 Okt 2026 (bagian akhir laporan): (1) 10 hari terakhir sebelum koin delisting dulu dibuang
(label NaN) -> kini dinilai dengan label terpotong (LUNA 9 Mei 2022 -100% masuk slot); (2) model 2019 tidak ada ->
LAMA efektif Jan 2020 – Sep 2021. Model tetap dilatih tanpa baris ekor (= resep model live).

Data: data/research/eksternal/spot_1d (kline 1d Binance semua pair USDT termasuk delisting). Keluaran:
docs/eksternal/hasil_spot_apk.txt, data/research/eksternal/arb/spot_apk_sinyal.parquet (sinyal semua varian utama).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .spot_paritas import DIR, END, KUALITAS, SKIP, SPLIT, muat, segs

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_spot_apk.txt"
OUT_SIG = ROOT / "data" / "research" / "eksternal" / "arb" / "spot_apk_sinyal.parquet"
OUT_JSON = ROOT / "docs" / "eksternal" / "spot_apk_teruji.json"
# VERIFIKASI 8 Okt: model walk-forward 2019 TIDAK ada (data latih 2018 < 2000 baris) -> sinyal pertama Jan 2020;
# LAMA efektif = Jan 2020 – Sep 2021 (dulu tertulis 2019, sehingga angka "/bln" LAMA terlalu kecil ±36%).
START = pd.Timestamp("2020-01-01", tz="UTC")
TP, HARI, THR, SKIP_VOL, COST = 0.03, 10, 0.93, 0.90, 0.003
SKIP_ALL = SKIP | {"BULL", "BEAR", "USDSB"}            # token leverage lama BTC 3x & stablecoin kecil
YEARS_L = (SPLIT - START).days / 365.25
YEARS_B = (END - SPLIT).days / 365.25


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ====================================================================== dataset
def _labels(d: pd.DataFrame, tp: float, n: int, margin: float = 0.0, potong: bool = False) -> pd.DataFrame:
    """= spot_peluang.labels (beli open t+1, limit +tp, keluar max(open, tp) bila kena setelah hari entry, else close
    hari ke-n), dengan opsi 'margin': limit dianggap terisi hanya bila high >= tp x (1 + margin) (antrian order).
    potong=True (VERIFIKASI 8 Okt): segmen BERHENTI sebelum akhir data (delisting / perdagangan dihentikan, mis. LUNA
    13 Mei 2022) -> 10 hari terakhir juga diberi label, keluar di close terakhir yang ada bila TP tidak kena. Dulu
    baris ini dibuang (label NaN) sehingga sinyal tepat sebelum delisting hilang (LUNA 9 Mei 2022: -100%)."""
    o, h, c = d.open.to_numpy(), d.high.to_numpy(), d.close.to_numpy()
    m = len(d)
    hit = np.full(m, np.nan)
    r = np.full(m, np.nan)
    out = np.full(m, -1)
    for t in range(m - 1 if potong else m - n - 1):
        j = t + 1
        e = o[j]
        tgt = e * (1 + tp)
        kk = -1
        for k in range(j, min(j + n, m)):
            if h[k] >= tgt * (1 + margin):
                kk = k
                break
        if kk >= 0:
            px = max(o[kk], tgt) if kk > j else tgt
            hit[t], r[t], out[t] = 1, px / e - 1 - COST, kk
        else:
            k = min(j + n, m) - 1
            hit[t], r[t], out[t] = 0, c[k] / e - 1 - COST, k
    return pd.DataFrame({"hit": hit, "r": r, "k": out}, index=d.index)


def build() -> tuple[pd.DataFrame, dict]:
    """Sama dengan spot_paritas.build (fitur, label, vr, kualitas, rank qv7) + qv1 (volume hari t = ticker 24 jam saat
    pindai 00:05 UTC), label 'TP harus tembus 0,1%', semua dalam float32 bila bisa (hemat RAM)."""
    from .spot_peluang import FEATS, features
    btc = muat("BTC")
    akhir_data = btc.index[-1]
    rows, data = [], {}
    for f in sorted(DIR.glob("*.parquet")):
        coin = f.stem
        if coin in SKIP_ALL:
            continue
        d0 = muat(coin)
        if d0 is None or len(d0) < 260:
            continue
        ss = segs(d0)
        if not ss:
            continue
        data[coin] = ss
        first = d0.index[0]
        for si, d in enumerate(ss):
            name = f"{coin}#{si}" if len(ss) > 1 else coin
            berhenti = d.index[-1] < akhir_data - pd.Timedelta(days=3)      # delisting / dihentikan sebelum akhir data
            x = features(d, btc).join(_labels(d, TP, HARI, potong=berhenti))
            ls = _labels(d, TP, HARI, margin=0.001, potong=berhenti)
            x["hit_s"], x["r_s"] = ls.hit, ls.r
            x["ekor"] = berhenti & (np.arange(len(d)) >= len(d) - HARI - 1)    # baris yang dulu dibuang
            x["vr"] = x.vol14.rolling(365, min_periods=120).rank(pct=True)
            c = d.close
            x["dd365"] = c / d.high.rolling(365, min_periods=200).max() - 1
            x["age"] = (d.index - first).days
            x["qv7"] = d.qv.shift(1).rolling(7).mean()
            x["qv1"] = d.qv
            x["qv_rel"] = d.qv / d.qv.rolling(30).mean()
            k = x.k.to_numpy()
            e = d.open.shift(-1).to_numpy()
            lo = d.low.to_numpy()
            mdd = np.full(len(d), np.nan)
            for i in range(len(d) - 1):
                if k[i] >= i + 1:
                    mdd[i] = lo[i + 1:k[i] + 1].min() / e[i] - 1
            x["mdd"] = mdd
            x["e"] = e
            x["t_in"] = pd.Series(d.index, index=d.index).shift(-1)
            x["t_out"] = [d.index[j] if j >= 0 else pd.NaT for j in k.astype(int)]
            x["coin"], x["base"] = name, coin
            rows.append(x.iloc[200:])
    df = pd.concat(rows)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS + ["hit"])
    df = df[(df.index < END) & (df.index >= pd.Timestamp("2018-01-01", tz="UTC"))]
    df["rank"] = df.groupby(level=0).qv7.rank(ascending=False, method="first")
    df["rank1"] = df.groupby(level=0).qv1.rank(ascending=False, method="first")
    keep64 = set(FEATS) | {"e", "r", "r_s", "mdd"}       # fitur tetap float64: model identik dengan spot_paritas
    for col in df.columns:
        if df[col].dtype == np.float64 and col not in keep64:
            df[col] = df[col].astype(np.float32)
    return df.sort_index(kind="stable"), data


def wf_models(train: pd.DataFrame) -> dict:
    """= spot_jatuh.wf_models: tahun Y dilatih data < 1 Jan Y - 12 hari (label 10 hari tidak bocor)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    from .spot_peluang import FEATS, GBM
    models = {}
    for y in range(2019, 2027):
        tr = train[train.index < pd.Timestamp(f"{y}-01-01", tz="UTC") - pd.Timedelta(days=HARI + 2)]
        if len(tr) >= 2000:
            models[y] = HistGradientBoostingClassifier(**GBM).fit(tr[FEATS].astype(float), tr.hit.astype(int))
    return models


def predict(models: dict, x: pd.DataFrame) -> np.ndarray:
    from .spot_peluang import FEATS
    p = np.full(len(x), np.nan)
    yrs = x.index.year.to_numpy()
    for y, m in models.items():
        sel = yrs == y
        if sel.any():
            p[sel] = m.predict_proba(x.loc[sel, FEATS].astype(float))[:, 1]
    return p


def siapkan(cache: Path | None) -> tuple[pd.DataFrame, dict]:
    if cache and cache.exists():
        log("muat cache", cache)
        df = pd.read_parquet(cache)
        if "ekor" not in df.columns:
            log("PERINGATAN: cache lama tanpa baris ekor delisting (bias penyintas) -> bangun ulang tanpa --cache")
            df["ekor"] = False
        data = {}
        for f in sorted(DIR.glob("*.parquet")):
            coin = f.stem
            if coin in SKIP_ALL:
                continue
            d0 = muat(coin)
            if d0 is None or len(d0) < 260:
                continue
            ss = segs(d0)
            if ss:
                data[coin] = ss
        return df, data
    from .spot_dip2 import MATI
    from .spot_peluang import LIVE
    log("bangun dataset")
    df, data = build()
    log(f"dataset {len(df)} baris ({int(df.ekor.sum())} baris ekor delisting), {len(data)} koin")
    # model dilatih TANPA baris ekor (= resep model live); ekor hanya ikut DINILAI
    latih = df[~df.ekor]
    # M1 = resep spot_paritas/spot_jatuh: dilatih 20 koin live (dipilih HARI INI) + koin ambruk
    df["p1"] = predict(wf_models(latih[latih.base.isin(set(LIVE) | set(MATI))]), df).astype(np.float32)
    log("model M1 selesai")
    # M2 = dilatih semesta jujur: koin 30 besar volume SAAT ITU (tanpa memilih penyintas)
    df["p2"] = predict(wf_models(latih[latih["rank"] <= 30]), df).astype(np.float32)
    log("model M2 selesai")
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache)
    return df, data


# ====================================================================== portofolio cepat (= spot_dip2.portfolio)
class Harga:
    """Matriks close harian (hari x koin/segmen), ffill (= Series.asof)."""

    def __init__(self, data: dict):
        names, ser = [], []
        for coin, ss in data.items():
            for si, d in enumerate(ss):
                names.append(f"{coin}#{si}" if len(ss) > 1 else coin)
                ser.append(d.close)
        lo = min(s.index[0] for s in ser)
        hi = max(s.index[-1] for s in ser)
        self.idx = pd.date_range(lo.normalize(), hi.normalize() + pd.Timedelta(days=30), freq="D", tz="UTC")
        m = np.full((len(self.idx), len(names)), np.nan)
        for j, s in enumerate(ser):
            pos = self.idx.get_indexer(s.index.normalize())
            m[pos, j] = s.to_numpy()
        self.m = pd.DataFrame(m).ffill().to_numpy()
        self.col = {n: j for j, n in enumerate(names)}


def portfolio(tr: pd.DataFrame, H: Harga, slots: int, start, end, extra_cost: float = 0.0) -> dict:
    """Ekuitas harian: tiap posisi 1/slots ekuitas (ekuitas tutup KEMARIN), sinyal saat slot penuh / koin sudah terbuka
    dilewati, urutan sinyal per hari = kolom 'ord' lalu nama. Sama persis dengan spot_dip2.portfolio (dicek)."""
    if tr.empty:
        return {}
    x = tr[(tr.t >= start) & (tr.t < end)].sort_values(["t", "ord", "coin"], kind="stable")
    if x.empty:
        return {}
    days = pd.date_range(x.t.min().normalize(), x.t_out.max().normalize(), freq="D", tz="UTC")
    C = H.m[H.idx.get_indexer(days)]
    dno = ((x.t.dt.normalize() - days[0]).dt.days).to_numpy()
    out_no = ((x.t_out.dt.normalize() - days[0]).dt.days).to_numpy()
    cols = np.array([H.col[c] for c in x.coin])
    e, r = x.e.to_numpy(), x.r.to_numpy() - extra_cost
    w = x.w.to_numpy() if "w" in x.columns else np.ones(len(x))
    starts = np.searchsorted(dno, np.arange(len(days) + 1))
    cash, eq = 1.0, np.empty(len(days))
    op_col, op_size, op_e, op_r, op_out, op_i = [], [], [], [], [], []
    taken = []
    for i in range(len(days)):
        if i == 0:
            equity = cash + sum(op_size)
        else:
            equity = cash + sum(s * C[i - 1, c] / ee for s, c, ee in zip(op_size, op_col, op_e))
        for j in range(starts[i], starts[i + 1]):
            if len(op_col) >= slots or cols[j] in op_col:
                continue
            size = min(equity / slots * w[j], cash)
            if size <= 0:
                continue
            cash -= size
            op_col.append(cols[j]), op_size.append(size), op_e.append(e[j]), op_r.append(r[j])
            op_out.append(out_no[j]), op_i.append(j)
            taken.append(j)
        keep = [k for k in range(len(op_col)) if op_out[k] > i]
        for k in range(len(op_col)):
            if op_out[k] <= i:
                cash += op_size[k] * (1 + op_r[k])
        op_col, op_size, op_e, op_r, op_out, op_i = ([a[k] for k in keep] for a in
                                                       (op_col, op_size, op_e, op_r, op_out, op_i))
        eq[i] = cash + sum(s * C[i, c] / ee for s, c, ee in zip(op_size, op_col, op_e))
    eqs = pd.Series(eq, index=days)
    yrs = (days[-1] - days[0]).days / 365.25
    ye = eqs.resample("YE").last()
    return {"akhir": eq[-1], "cagr": eq[-1] ** (1 / yrs) - 1 if yrs > 0 else 0.0,
            "dd": float((eqs / eqs.cummax() - 1).min()), "taken": x.iloc[taken], "n": len(x),
            "tahun": ye.pct_change().fillna(ye.iloc[0] - 1)}


# ====================================================================== sinyal
def take(sig: pd.DataFrame, rcol: str = "r", hcol: str = "hit") -> pd.DataFrame:
    """Satu posisi per koin; sinyal berikutnya hanya setelah posisi sebelumnya keluar (= spot_paritas.take), vektor
    sebagian: loop per koin dengan numpy."""
    if sig.empty:
        return pd.DataFrame()
    s = sig.sort_index(kind="stable")
    keep = np.zeros(len(s), bool)
    coins = s.coin.to_numpy()
    tin = s.t_in.to_numpy()
    tout = s.t_out.to_numpy()
    order = np.argsort(coins, kind="stable")
    last_coin, free = None, None
    for i in order:
        c = coins[i]
        if c != last_coin:
            last_coin, free = c, None
        if free is not None and tin[i] <= free:
            continue
        keep[i] = True
        free = tout[i]
    x = s[keep]
    cols = ["coin", "base", "t_in", "t_out", "e", rcol, hcol, "mdd", "ord"] + \
        [c for c in ("p", "rule", "vr", "btc_up", "rank", "rank1", "dd20", "red", "r3", "age", "dd365", "qv_rel",
                     "d200", "vol14", "ekor") if c in x.columns]
    out = x[cols].rename(columns={"t_in": "t", rcol: "r", hcol: "hit"}).copy()
    out["t_sig"] = x.index
    return out.reset_index(drop=True)


def st(x: pd.DataFrame, extra: float = 0.0) -> dict:
    if x is None or len(x) == 0:
        return {"n": 0}
    r = x.r.to_numpy() - extra
    lose = r[r <= 0]
    return {"n": len(x), "wr": float((r > 0).mean() * 100), "avg": float(r.mean() * 100),
            "kalah": float(lose.mean() * 100) if len(lose) else 0.0, "terburuk": float(r.min() * 100),
            "tp": float((x.hit == 1).mean() * 100)}


def fs(s: dict) -> str:
    if not s or s.get("n", 0) == 0:
        return "n 0"
    return (f"n {s['n']} untung {s['wr']:.1f}% rata {s['avg']:+.2f}% kalah rata {s['kalah']:+.1f}% "
            f"terburuk {s['terburuk']:+.0f}%")


def per(x: pd.DataFrame, lab: str) -> pd.DataFrame:
    if x is None or len(x) == 0:
        return x
    return x[x.t < SPLIT] if lab == "LAMA" else x[x.t >= SPLIT]


class Uji:
    def __init__(self, df: pd.DataFrame, data: dict, H: Harga):
        self.df, self.data, self.H = df, data, H
        self.cache = {}

    def run(self, name: str, mask: pd.Series, uni: pd.Series, slots: int, acak_reps: int = 0, pcol: str = "p1",
            rcol: str = "r", hcol: str = "hit", ord_col: str = "rank") -> dict:
        df = self.df
        sig = df[mask.fillna(False).to_numpy()].copy()
        sig["p"] = sig[pcol]
        sig["rule"] = (sig.red >= 3) & (sig.r3 <= -0.10) & (sig.d200 > 0)
        sig["ord"] = sig[ord_col]
        tr = take(sig, rcol, hcol)
        res = {"name": name, "slots": slots, "tr": tr}
        if tr.empty:
            return res
        for lab, (a, b) in (("LAMA", (START, SPLIT)), ("BARU", (SPLIT, END))):
            pf = portfolio(tr, self.H, slots, a, b)
            pf2 = portfolio(tr, self.H, slots, a, b, extra_cost=COST)
            res[lab] = {"semua": st(per(tr, lab)), "slot": st(pf.get("taken")), "slot_x2": st(pf.get("taken"), COST),
                        "pf": pf, "pf2": pf2}
        if acak_reps:
            res["acak"] = self.acak(tr, uni, slots, acak_reps, rcol, hcol, ord_col)
        return res

    def acak(self, tr, uni, slots, reps, rcol, hcol, ord_col):
        df = self.df
        pool = df[(uni & df[rcol].notna() & df.t_in.notna()).to_numpy()].copy()
        pool["ord"] = pool[ord_col]
        pool["m"] = pool.index.to_period("M") if pool.index.tz is None else pool.index.tz_localize(None).to_period("M")
        groups = {m: g for m, g in pool.groupby("m")}
        tsig = tr.t_sig.dt.tz_localize(None).dt.to_period("M")
        per_m = tsig.groupby(tsig).size()
        rng = np.random.default_rng(11)
        out = {"LAMA": [], "BARU": []}
        for _ in range(reps):
            picks = []
            for m, n in per_m.items():
                g = groups.get(m)
                if g is None or g.empty:
                    continue
                picks.append(g.iloc[rng.choice(len(g), size=min(len(g), int(n * 1.3)), replace=False)])
            t = take(pd.concat(picks), rcol, hcol)
            for lab, (a, b) in (("LAMA", (START, SPLIT)), ("BARU", (SPLIT, END))):
                pf = portfolio(t, self.H, slots, a, b)
                s = st(pf.get("taken"))
                if s["n"]:
                    out[lab].append((s["wr"], s["avg"], pf["cagr"] * 100, pf["dd"] * 100))
        res = {}
        for lab, v in out.items():
            if v:
                a = np.array(v)
                res[lab] = {"median": np.median(a, axis=0).tolist(), "p95": np.percentile(a, 95, axis=0).tolist()}
        return res


def baris(res: dict, L: list[str], detail: bool = True) -> None:
    L.append(f"## {res['name']}  ({res['slots']} slot)")
    if "LAMA" not in res and "BARU" not in res:
        L.append("   tidak ada sinyal")
        return
    for lab in ("LAMA", "BARU"):
        if lab not in res:
            continue
        x = res[lab]
        pf, pf2 = x["pf"], x["pf2"]
        months = (YEARS_L if lab == "LAMA" else YEARS_B) * 12
        line = f"   {lab}: masuk slot {fs(x['slot'])} ({x['slot'].get('n', 0) / months:.1f}/bln)"
        if pf:
            line += f" | portofolio {pf['cagr'] * 100:+.1f}%/th DD {pf['dd'] * 100:.0f}%"
        L.append(line)
        if detail:
            L.append(f"         semua sinyal {fs(x['semua'])} | biaya x2: untung {x['slot_x2'].get('wr', 0):.1f}% rata "
                     f"{x['slot_x2'].get('avg', 0):+.2f}%" + (f" pf {pf2['cagr'] * 100:+.1f}%/th" if pf2 else ""))
    if detail:
        pfs = [res[lab]["pf"] for lab in ("LAMA", "BARU") if lab in res and res[lab]["pf"]]
        th = " ".join(f"{t.year}{'L' if i == 0 and len(pfs) > 1 else ''}:{v * 100:+.0f}%" for i, pf in enumerate(pfs)
                      for t, v in pf["tahun"].items())
        L.append(f"   portofolio per tahun: {th}")
        tk = pd.concat([res[lab]["pf"]["taken"] for lab in ("LAMA", "BARU") if lab in res and res[lab]["pf"]])
        L.append("   per sinyal per tahun: " + " ".join(
            f"{y}:n{len(g)} {(g.r > 0).mean() * 100:.0f}% {g.r.mean() * 100:+.1f}%" for y, g in tk.groupby(tk.t.dt.year)))
    if res.get("acak"):
        a = res["acak"]
        L.append("   ACAK median: " + " | ".join(
            f"{lab} untung {a[lab]['median'][0]:.1f}% rata {a[lab]['median'][1]:+.2f}% pf {a[lab]['median'][2]:+.1f}%/th "
            f"DD {a[lab]['median'][3]:.0f}%" for lab in ("LAMA", "BARU") if lab in a))
        L.append("   ACAK p95: " + " | ".join(
            f"{lab} rata {a[lab]['p95'][1]:+.2f}% pf {a[lab]['p95'][2]:+.1f}%/th" for lab in ("LAMA", "BARU") if lab in a))


def key(res: dict, lab: str) -> tuple:
    x = res.get(lab)
    if not x or not x["slot"].get("n"):
        return (np.nan,) * 4
    return (x["slot"]["wr"], x["slot"]["avg"], x["pf"]["cagr"] * 100, x["pf"]["dd"] * 100)


def keputusan_filter(base: dict, cand: dict) -> str:
    """FILTER lolos hanya bila untung% DAN rata/sinyal DAN portofolio %/th naik di LAMA DAN BARU dan > acak p95."""
    ok, why = True, []
    for lab in ("LAMA", "BARU"):
        b, c = key(base, lab), key(cand, lab)
        for i, nm in ((0, "untung%"), (1, "rata"), (2, "pf")):
            if not (c[i] > b[i]):
                ok = False
                why.append(f"{lab} {nm} {c[i]:.2f} <= {b[i]:.2f}")
        a = cand.get("acak", {}).get(lab)
        if a and not (c[1] > a["p95"][1] and c[2] > a["p95"][2]):
            ok = False
            why.append(f"{lab} tidak > acak p95")
    return "LOLOS" if ok else "TIDAK LOLOS (" + "; ".join(why[:6]) + ")"


# ====================================================================== label / tier
def tier_tabel(tr_slot: pd.DataFrame, conds: dict, L: list[str]) -> dict:
    """Untuk tiap kriteria: statistik sinyal yang memenuhi vs tidak, LAMA & BARU, dan jumlah tahun lebih baik."""
    out = {}
    L.append("   kriteria                         | LAMA ya            | LAMA tidak         | BARU ya            | "
             "BARU tidak         | tahun ya>tidak")
    for nm, fn in conds.items():
        m = fn(tr_slot).astype(bool).to_numpy()
        row = {}
        cells = []
        for lab in ("LAMA", "BARU"):
            pm = (tr_slot.t < SPLIT).to_numpy() if lab == "LAMA" else (tr_slot.t >= SPLIT).to_numpy()
            a, b = st(tr_slot[m & pm]), st(tr_slot[~m & pm])
            row[lab] = (a, b)
            cells += [f"n{a['n']:4d} {a.get('wr', 0):5.1f}% {a.get('avg', 0):+5.2f}%",
                      f"n{b['n']:4d} {b.get('wr', 0):5.1f}% {b.get('avg', 0):+5.2f}%"]
        yb, ytot = 0, 0
        for y, g in tr_slot.groupby(tr_slot.t.dt.year):
            mm = fn(g).astype(bool).to_numpy()
            if mm.sum() >= 3 and (~mm).sum() >= 3:
                ytot += 1
                yb += int(g.r[mm].mean() > g.r[~mm].mean())
        row["tahun"] = (yb, ytot)
        out[nm] = row
        L.append(f"   {nm:32} | " + " | ".join(cells) + f" | {yb}/{ytot}")
    return out


def _ab(x: pd.DataFrame, m: np.ndarray) -> str:
    out = []
    for lab in ("LAMA", "BARU"):
        pm = (x.t < SPLIT).to_numpy() if lab == "LAMA" else (x.t >= SPLIT).to_numpy()
        a, b = st(x[m & pm]), st(x[~m & pm])
        out.append(f"{lab} ya n{a['n']} {a.get('wr', 0):.1f}% {a.get('avg', 0):+.2f}% / tidak n{b['n']} "
                   f"{b.get('wr', 0):.1f}% {b.get('avg', 0):+.2f}%")
    return " | ".join(out)


def _tahun(x: pd.DataFrame, m: np.ndarray) -> str:
    parts, yb, yt = [], 0, 0
    for y, g in x.groupby(x.t.dt.year):
        mm = m[x.t.dt.year.to_numpy() == y]
        a, b = g[mm], g[~mm]
        if len(a) >= 3 and len(b) >= 3:
            yt += 1
            yb += int(a.r.mean() > b.r.mean() and (a.r > 0).mean() >= (b.r > 0).mean())
        parts.append(f"{y}: {len(a)} {(a.r > 0).mean() * 100 if len(a) else 0:.0f}% {a.r.mean() * 100 if len(a) else 0:+.1f}%"
                     f" vs {len(b)} {(b.r > 0).mean() * 100 if len(b) else 0:.0f}% {b.r.mean() * 100 if len(b) else 0:+.1f}%")
    return f"{yb}/{yt} tahun ya lebih baik (untung% & rata) | " + " ; ".join(parts)


def dalam(U: Uji, R: dict, tk: pd.DataFrame, L: list[str], thr_dd: float = -0.15) -> None:
    """Uji mendalam label '⚡ dip ringan' (dd20 > -15%: harga masih <= 15% di bawah high 20 hari saat sinyal).
    Kriteria ini ada di daftar awal (kebalikan 'jatuh dalam'), tetapi arah 'ringan' baru dipertimbangkan setelah melihat
    BARU -> butuh cek tambahan: ember, ambang lain, semesta/koin lain, model lain, bootstrap per bulan, ukuran posisi."""
    L.append(f"# 4b. Uji mendalam label '⚡ dip ringan' = dd20 > {thr_dd * 100:.0f}% (harga <= {-thr_dd * 100:.0f}% di "
             "bawah high 20 hari)")
    L.append("   Ember dd20 (sinyal E masuk slot):")
    for lo, hi in ((-9, -0.30), (-0.30, -0.20), (-0.20, -0.15), (-0.15, -0.10), (-0.10, 1)):
        m = ((tk.dd20 > lo) & (tk.dd20 <= hi)).to_numpy()
        L.append(f"     dd20 {lo * 100 if lo > -9 else -100:.0f}%..{min(hi, 0) * 100:.0f}%: LAMA "
                 f"{fs(st(per(tk[m], 'LAMA')))} | BARU {fs(st(per(tk[m], 'BARU')))}")
    L.append("   Ambang lain (ya = dd20 > ambang):")
    for th in (-0.10, -0.12, -0.15, -0.20, -0.25):
        m = (tk.dd20 > th).to_numpy()
        L.append(f"     {th * 100:.0f}%: {_ab(tk, m)}")
    m = (tk.dd20 > thr_dd).to_numpy()
    L.append("   Per tahun (E): " + _tahun(tk, m))
    # set lain
    sets = {
        "E semua sinyal (sebelum batas slot)": R["E"]["tr"],
        "a1 E + BTC>SMA200": pd.concat([R["D"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU")]),
        "e5 model M2 (dilatih semesta jujur)": pd.concat([R["M2"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU")]),
        "e7 TP harus tembus 0,1%": pd.concat([R["strict"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU")]),
        "e4 tanpa filter vol": pd.concat([R["novol"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU")]),
        "KOIN LAIN: peringkat 21-100 (top-100, semua sinyal)": R["N100s20"]["tr"][R["N100s20"]["tr"]["rank"] > 20],
        "KOIN LAIN: peringkat 21-50 (semua sinyal)": R["N100s20"]["tr"][(R["N100s20"]["tr"]["rank"] > 20) &
                                                                       (R["N100s20"]["tr"]["rank"] <= 50)],
        "e6 semesta volume 24 jam": pd.concat([R["rank1"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU")]),
    }
    L.append("   Set lain (ya = dip ringan):")
    for nm, x in sets.items():
        x = x[x.t >= START]
        mm = (x.dd20 > thr_dd).to_numpy()
        L.append(f"     {nm}: {_ab(x, mm)}")
        L.append(f"        {_tahun(x, mm).split(' | ')[0]}")
    ekstra = {"boot": {}, "dasar": {}, "pf": {}}
    x = tk[(tk.t >= SPLIT) & (tk.t.dt.year != 2022)]
    mm = (x.dd20 > thr_dd).to_numpy()
    L.append(f"   BARU TANPA 2022 (tahun turun): ya {fs(st(x[mm]))} | tidak {fs(st(x[~mm]))}")
    x = tk[tk.t.dt.year.isin([2023, 2024, 2025])]
    mm = (x.dd20 > thr_dd).to_numpy()
    ekstra["2325"] = (st(x[mm]), st(x[~mm]))
    L.append(f"   Hanya 2023-2025 (pasar naik): ya {fs(st(x[mm]))} | tidak {fs(st(x[~mm]))}")
    # angka dasar: SEMUA hari di semesta top-20 (tanpa sinyal) dengan dd20 > ambang vs <= ambang
    u = U.df[(U.df["rank"] <= 20).to_numpy() & U.df.p1.notna().to_numpy() & (U.df.index >= START)]
    for lab in ("LAMA", "BARU"):
        x = u[u.index < SPLIT] if lab == "LAMA" else u[u.index >= SPLIT]
        a, b = x[x.dd20 > thr_dd], x[x.dd20 <= thr_dd]
        ekstra["dasar"][lab] = ((a.r > 0).mean() * 100, (b.r > 0).mean() * 100)
        L.append(f"   Angka dasar semua hari top-20 {lab}: dd20 > {thr_dd * 100:.0f}% n {len(a)} untung "
                 f"{(a.r > 0).mean() * 100:.1f}% rata {a.r.mean() * 100:+.2f}% | dd20 <= {thr_dd * 100:.0f}% n {len(b)} "
                 f"untung {(b.r > 0).mean() * 100:.1f}% rata {b.r.mean() * 100:+.2f}%")
    # BTC rezim silang
    for up in (1, 0):
        x = tk[tk.btc_up == up]
        L.append(f"   BTC {'atas' if up else 'bawah'} SMA200: {_ab(x, (x.dd20 > thr_dd).to_numpy())}")
    # bootstrap blok per bulan: selisih rata (ya - tidak) dan selisih untung%
    rng = np.random.default_rng(5)
    for lab in ("LAMA", "BARU"):
        x = per(tk, lab)
        mon = x.t.dt.tz_localize(None).dt.to_period("M").to_numpy()
        months = np.unique(mon)
        idx = {mo: np.where(mon == mo)[0] for mo in months}
        ya = (x.dd20 > thr_dd).to_numpy()
        r = x.r.to_numpy()
        d_avg, d_wr = [], []
        for _ in range(2000):
            pick = np.concatenate([idx[mo] for mo in rng.choice(months, size=len(months), replace=True)])
            a, b = r[pick][ya[pick]], r[pick][~ya[pick]]
            if len(a) and len(b):
                d_avg.append((a.mean() - b.mean()) * 100)
                d_wr.append(((a > 0).mean() - (b > 0).mean()) * 100)
        d_avg, d_wr = np.array(d_avg), np.array(d_wr)
        ekstra["boot"][lab] = {"avg": [float(np.median(d_avg)), float(np.percentile(d_avg, 2.5)),
                                       float(np.percentile(d_avg, 97.5)), float((d_avg <= 0).mean() * 100)],
                               "wr": [float(np.median(d_wr)), float(np.percentile(d_wr, 2.5)),
                                      float(np.percentile(d_wr, 97.5)), float((d_wr <= 0).mean() * 100)]}
        L.append(f"   Bootstrap blok bulan {lab} (2000x): selisih rata {np.median(d_avg):+.2f} poin "
                 f"[CI95 {np.percentile(d_avg, 2.5):+.2f}..{np.percentile(d_avg, 97.5):+.2f}], P(<=0) "
                 f"{(d_avg <= 0).mean() * 100:.1f}% | selisih untung% {np.median(d_wr):+.1f} "
                 f"[{np.percentile(d_wr, 2.5):+.1f}..{np.percentile(d_wr, 97.5):+.1f}]")
    # angka tampilan per tier (sinyal E masuk slot) + susunan alasan + lama tahan
    L.append("   Angka tampilan per tier (E, sinyal masuk slot):")
    out = {}
    hold = (tk.t_out - tk.t).dt.days + 1
    for nm, m in (("⚡ dip ringan", tk.dd20 > thr_dd), ("biasa", ~(tk.dd20 > thr_dd))):
        m = m.to_numpy()
        out[nm] = {}
        for lab in ("LAMA", "BARU"):
            pm = (tk.t < SPLIT).to_numpy() if lab == "LAMA" else (tk.t >= SPLIT).to_numpy()
            s = st(tk[m & pm])
            s["tahan_median_hari"] = float(hold[m & pm].median())
            s["per_bulan"] = s["n"] / ((YEARS_L if lab == "LAMA" else YEARS_B) * 12)
            s["turun10"] = float((tk[m & pm].mdd <= -0.10).mean() * 100)
            s["rugi20"] = float((tk[m & pm].r <= -0.20).mean() * 100)      # porsi sinyal rugi >= 20%
            out[nm][lab] = s
            L.append(f"     {nm} {lab}: {fs(s)} | {s['per_bulan']:.1f}/bln | tahan median {s['tahan_median_hari']:.0f} hari | "
                     f"sempat turun >= 10%: {s['turun10']:.0f}% | rugi >= 20%: {s['rugi20']:.1f}%")
        rr = tk[m]
        L.append(f"       alasan: model {((rr.p >= THR) & ~rr.rule).mean() * 100:.0f}% | model + 3 merah "
                 f"{((rr.p >= THR) & rr.rule).mean() * 100:.0f}% | 3 merah {((rr.p < THR) & rr.rule).mean() * 100:.0f}%")
    # daftar 20 koin TETAP aplikasi (bias penyintas) — untuk perbandingan saja
    xa = pd.concat([R["A"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU")])
    L.append(f"   (Pembanding bias penyintas) A 20 koin tetap: {_ab(xa, (xa.dd20 > thr_dd).to_numpy())}")
    # ukuran posisi per label (bukan membuang sinyal): ⚡ 10% modal, biasa 5%
    tr = R["E"]["tr"].copy()
    for nm, wb in (("semua 10% (terpasang)", 1.0), ("⚡ 10% / biasa 5%", 0.5), ("hanya ⚡ (= filter)", 0.0)):
        tr["w"] = np.where(tr.dd20 > thr_dd, 1.0, wb)
        parts = []
        ekstra["pf"][nm] = {}
        for lab, (a0, b0) in (("LAMA", (START, SPLIT)), ("BARU", (SPLIT, END))):
            pf = portfolio(tr[tr.w > 0], U.H, 10, a0, b0)
            pf2 = portfolio(tr[tr.w > 0], U.H, 10, a0, b0, extra_cost=COST)
            s = st(pf["taken"])
            ekstra["pf"][nm][lab] = (pf["cagr"] * 100, pf["dd"] * 100, pf2["cagr"] * 100)
            parts.append(f"{lab} {pf['cagr'] * 100:+.1f}%/th DD {pf['dd'] * 100:.0f}% (x2 {pf2['cagr'] * 100:+.1f}%) "
                         f"n {s['n']} {s['wr']:.1f}% {s['avg']:+.2f}%")
        L.append(f"   Portofolio 10 slot, {nm}: " + " | ".join(parts))
        out[f"pf {nm}"] = parts
    L.append("")
    out["_ekstra"] = ekstra
    return out


# ====================================================================== utama
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=None, help="parquet dataset+prediksi (opsional, mempercepat ulang)")
    ap.add_argument("--reps", type=int, default=20, help="ulangan acak")
    a = ap.parse_args()
    t0 = time.time()
    df, data = siapkan(a.cache)
    H = Harga(data)
    U = Uji(df, data, H)
    log(f"siap: {len(df)} baris, {len(data)} koin, {time.time() - t0:.0f} dtk")

    rule3 = (df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0)
    vol_ok = ~(df.vr > SKIP_VOL)
    btc_ok = df.btc_up == 1
    kual = (df.age >= KUALITAS["umur_min"]) & ~(df.dd365 <= KUALITAS["ambruk"]) & ~(df.qv_rel >= KUALITAS["vol_panik"])
    sig1 = ((df.p1 >= THR) | rule3) & df.p1.notna()
    sig2 = ((df.p2 >= THR) | rule3) & df.p2.notna()
    top = {n: df["rank"] <= n for n in (20, 30, 50, 100)}
    from .spot_peluang import LIVE
    live = df.base.isin(LIVE)
    E = sig1 & top[20] & vol_ok
    L: list[str] = []
    R: dict = {}
    ek = df[(E & df.ekor).fillna(False).to_numpy()]
    L.append(f"# 0a. Baris ekor delisting (10 hari terakhir sebelum koin berhenti diperdagangkan, dulu dibuang): "
             f"{int(df.ekor.sum())} baris; sinyal E (sebelum batas slot) di ekor: " +
             ", ".join(f"{bs} {t:%Y-%m-%d} r {r * 100:+.0f}%" for t, bs, r in zip(ek.index, ek.base, ek.r)))
    L.append("")

    # ---------------------------------------------------------------- 0. cek mesin cepat = spot_paritas (D & E)
    L.append("# 0. Cek mesin: portofolio cepat vs spot_dip2.portfolio (spot_paritas varian D & E, urutan koin model)")
    from .spot_paritas import portfolio as pf_lama
    order = {c: i for i, c in enumerate(LIVE)}
    R0 = {}
    for nm, m in (("D", E & btc_ok), ("E", E)):
        s = df[m.fillna(False).to_numpy()].copy()
        s["p"] = s.p1
        s["ord"] = s.base.map(order).fillna(999)
        tr = take(s)
        for lab, (a0, b0) in (("LAMA", (START, SPLIT)), ("BARU", (SPLIT, END))):
            new = portfolio(tr, H, 10, a0, b0)
            old_tr = tr.assign(ord=tr.ord.astype(int))
            old = pf_lama(old_tr, data, 10, a0, b0)
            R0[(nm, lab)] = old["cagr"] * 100
            L.append(f"   {nm} {lab}: cepat {new['cagr'] * 100:+.2f}%/th DD {new['dd'] * 100:.1f}% | lama "
                     f"{old['cagr'] * 100:+.2f}%/th DD {old['dd'] * 100:.1f}% | semua sinyal {fs(st(per(tr, lab)))}")
    log("cek mesin selesai")
    L.append("")
    R["_cek0"] = R0

    # ---------------------------------------------------------------- 1. dasar & a) BTC filter
    log("varian dasar")
    R["A"] = U.run("A. TERPASANG (20 koin TETAP hari ini, vol>P90, tanpa BTC) — BIAS PENYINTAS", sig1 & live & vol_ok,
                   live, 10, 0)
    R["E"] = U.run("E. DASAR JUJUR: 20 koin volume terbesar SAAT ITU, vol>P90, tanpa BTC (= terpasang tanpa bias)", E,
                   top[20], 10, a.reps)
    R["D"] = U.run("a1. FILTER BTC>SMA200 (= E + BTC)", E & btc_ok, top[20], 10, a.reps)
    R["b"] = U.run("b1. FILTER kualitas (= E + kualitas)", E & kual, top[20], 10, a.reps)
    R["D2"] = U.run("b2. BTC + kualitas (= E + BTC + kualitas)", E & btc_ok & kual, top[20], 10, a.reps)
    log("varian semesta")
    for n in (30, 50, 100):
        for sl in (10, 20):
            R[f"N{n}s{sl}"] = U.run(f"c. top-{n} volume saat itu, vol>P90, tanpa BTC, {sl} slot",
                                    sig1 & top[n] & vol_ok, top[n], sl, a.reps if sl == 10 else 0)
            R[f"N{n}s{sl}b"] = U.run(f"c. top-{n} + BTC>SMA200, {sl} slot", sig1 & top[n] & vol_ok & btc_ok, top[n], sl,
                                     0)
    R["N20s20"] = U.run("c. top-20, 20 slot", E, top[20], 20, 0)
    log("varian lain")
    R["thr95"] = U.run("e1. ambang 0,95 (filter)", ((df.p1 >= 0.95) | rule3) & df.p1.notna() & top[20] & vol_ok,
                       top[20], 10, a.reps)
    R["thr97"] = U.run("e2. ambang 0,97 (filter)", ((df.p1 >= 0.97) | rule3) & df.p1.notna() & top[20] & vol_ok,
                       top[20], 10, a.reps)
    R["vol70"] = U.run("e3. lewati vol > P70 (filter)", sig1 & top[20] & ~(df.vr > 0.70), top[20], 10, a.reps)
    R["novol"] = U.run("e4. TANPA filter vol (cek filter terpasang)", sig1 & top[20], top[20], 10, a.reps)
    R["M2"] = U.run("e5. model dilatih semesta jujur (top-30 saat itu), selain itu = E", sig2 & top[20] & vol_ok,
                    top[20], 10, a.reps, pcol="p2")
    top1 = df["rank1"] <= 20
    R["rank1"] = U.run("e6. semesta dari volume 24 jam terakhir (1 panggilan ticker), selain itu = E",
                       sig1 & top1 & vol_ok, top1, 10, 0)
    R["strict"] = U.run("e7. E dengan TP harus tembus +0,1% di atas limit (antrian order)", E, top[20], 10, 0,
                        rcol="r_s", hcol="hit_s")
    R["noskipvol_M2"] = U.run("e8. model M2 + BTC (= a1 dengan model jujur)", sig2 & top[20] & vol_ok & btc_ok,
                              top[20], 10, 0, pcol="p2")

    # ---------------------------------------------------------------- tulis bagian varian
    L.append("# 1. Varian (statistik per sinyal = sinyal MASUK SLOT; portofolio = tiap posisi 1/slot modal)")
    for k in ("A", "E", "D", "b", "D2"):
        baris(R[k], L)
        if k not in ("A", "E"):
            L.append(f"   KEPUTUSAN filter vs E: {keputusan_filter(R['E'], R[k])}")
        L.append("")
    L.append("# 2. Semesta lebih luas (dibanding E: top-20, 10 slot)")
    for k in ["N20s20"] + [f"N{n}s{sl}{b}" for n in (30, 50, 100) for sl in (10, 20) for b in ("", "b")]:
        baris(R[k], L, detail=k in ("N30s10", "N50s10", "N100s10", "N100s20"))
        if not k.endswith("b"):
            L.append(f"   KEPUTUSAN vs E: {keputusan_filter(R['E'], R[k])}")
        L.append("")
    L.append("# 3. Lain dari riset lama (dibanding E)")
    for k in ("thr95", "thr97", "vol70", "novol", "M2", "rank1", "strict", "noskipvol_M2"):
        baris(R[k], L)
        if k in ("thr95", "thr97", "vol70"):
            L.append(f"   KEPUTUSAN filter vs E: {keputusan_filter(R['E'], R[k])}")
        elif k == "novol":
            L.append(f"   KEPUTUSAN filter vol terpasang (E vs tanpa vol): {keputusan_filter(R['novol'], R['E'])}")
        L.append("")

    # ---------------------------------------------------------------- 4. label
    log("label")
    L.append("# 4. LABEL pada sinyal E yang masuk slot (sinyal tidak dibuang). ya = memenuhi kriteria.")
    L.append("   Format sel: n, untung%, rata/sinyal. 'tahun ya>tidak' = tahun (n>=3 di tiap sisi) rata 'ya' > 'tidak'.")
    tk = pd.concat([R["E"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU")])
    conds = {
        "BTC > SMA200": lambda x: x.btc_up == 1,
        "p >= 0,97": lambda x: x.p >= 0.97,
        "p >= 0,95": lambda x: x.p >= 0.95,
        "model + 3 merah": lambda x: (x.p >= THR) & x.rule,
        "hanya 3 merah (p < 0,93)": lambda x: (x.p < THR) & x.rule,
        "vol rendah (vr <= 0,5)": lambda x: x.vr <= 0.5,
        "koin 10 terbesar (rank <= 10)": lambda x: x["rank"] <= 10,
        "jatuh dalam (dd20 <= -15%)": lambda x: x.dd20 <= -0.15,
        "kualitas lolos": lambda x: (x.age >= 365) & ~(x.dd365 <= -0.8) & ~(x.qv_rel >= 3),
        "di atas SMA200 koin (d200 > 0)": lambda x: x.d200 > 0,
    }
    tt = tier_tabel(tk, conds, L)
    # pilih 2 kriteria terbaik dari LAMA saja (selisih rata ya - tidak, n ya >= 30 di LAMA)
    cand = []
    for nm, row in tt.items():
        a_, b_ = row["LAMA"]
        if a_["n"] >= 30 and b_["n"] >= 30:
            cand.append((a_["avg"] - b_["avg"], nm))
    cand.sort(reverse=True)
    best = [nm for d, nm in cand[:2] if d > 0]
    L.append(f"   Dipilih dari LAMA (selisih rata terbesar, n >= 30): {best} (selisih {[round(d, 2) for d, _ in cand[:2]]})")
    if best:
        def score(x):
            return sum(conds[nm](x).astype(int) for nm in best)
        tk = tk.assign(sk=score(tk).to_numpy())
        L.append("   Tier dari kriteria LAMA: ⚡ = memenuhi semua, 🥈 = sebagian, biasa = tidak ada")
        for lab in ("LAMA", "BARU"):
            x = per(tk, lab)
            parts = []
            for nm, m in (("⚡", x.sk == len(best)), ("🥈", (x.sk > 0) & (x.sk < len(best))), ("biasa", x.sk == 0)):
                parts.append(f"{nm} {fs(st(x[m]))}")
            L.append(f"   {lab}: " + " | ".join(parts))
        tahun = []
        for y, g in tk.groupby(tk.t.dt.year):
            a1, b1 = g[g.sk == len(best)], g[g.sk == 0]
            if len(a1) >= 3 and len(b1) >= 3:
                tahun.append(f"{y}: ⚡ {a1.r.mean() * 100:+.1f}% vs biasa {b1.r.mean() * 100:+.1f}%")
        L.append("   per tahun: " + " | ".join(tahun))
    # kalibrasi peluang model (angka cincin "peluang" di aplikasi)
    L.append("   Kalibrasi peluang model (sinyal E masuk slot): ember p -> untung% LAMA | BARU")
    tk2 = pd.concat([R["E"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU")])
    for lo, hi in ((0.0, 0.93), (0.93, 0.95), (0.95, 0.97), (0.97, 0.99), (0.99, 1.01)):
        m = (tk2.p >= lo) & (tk2.p < hi)
        a1, b1 = st(per(tk2[m], "LAMA")), st(per(tk2[m], "BARU"))
        L.append(f"     p {lo:.2f}-{min(hi, 1):.2f}: LAMA {fs(a1)} | BARU {fs(b1)}")
    # transparansi: peringkat LAMA bila kebalikan tiap kriteria juga dihitung (ditambahkan SETELAH melihat BARU)
    both = []
    for nm, row in tt.items():
        a_, b_ = row["LAMA"]
        if a_["n"] >= 30 and b_["n"] >= 30:
            both.append((round(a_["avg"] - b_["avg"], 2), nm))
            both.append((round(b_["avg"] - a_["avg"], 2), "BUKAN " + nm))
    both.sort(reverse=True)
    L.append("   Peringkat LAMA dua arah (kebalikan ikut dihitung; DITAMBAHKAN setelah melihat BARU): " +
             ", ".join(f"{nm} {d:+.2f}" for d, nm in both[:5]))
    L.append("")
    tier = dalam(U, R, tk2, L)

    # ---------------------------------------------------------------- 5. label BTC: rezim
    L.append("# 5. BTC>SMA200 sebagai LABEL (E): statistik per rezim, per tahun")
    for y, g in tk2.groupby(tk2.t.dt.year):
        up, dn = g[g.btc_up == 1], g[g.btc_up == 0]
        L.append(f"   {y}: BTC atas {fs(st(up))} | BTC bawah {fs(st(dn))}")
    L.append("")

    # ---------------------------------------------------------------- 6. pembanding BTC & semua hari
    c = data["BTC"][0].close
    for lab, (a0, b0) in (("LAMA", (START, SPLIT)), ("BARU", (SPLIT, END))):
        x = c[(c.index >= a0) & (c.index < b0)]
        yrs = (x.index[-1] - x.index[0]).days / 365.25
        L.append(f"BTC beli-tahan {lab}: {((x.iloc[-1] / x.iloc[0]) ** (1 / yrs) - 1) * 100:+.1f}%/th DD "
                 f"{(x / x.cummax() - 1).min() * 100:.0f}%")
    u = df[top[20].to_numpy() & df.p1.notna().to_numpy()]
    for lab in ("LAMA", "BARU"):
        x = u[u.index < SPLIT] if lab == "LAMA" else u[u.index >= SPLIT]
        x = x[x.index >= START]
        L.append(f"Semua hari semesta top-20 {lab}: untung {(x.r > 0).mean() * 100:.1f}% rata {x.r.mean() * 100:+.2f}% "
                 f"(TP kena {(x.hit == 1).mean() * 100:.1f}%)")
    # semesta saat ini vs daftar 20 koin aplikasi
    last = df.index.max()
    cur = df[(df.index == last) & (df["rank"] <= 20)].sort_values("rank").base.tolist()
    L.append(f"Top-20 volume (rata 7 hari) per {last:%Y-%m-%d}: {' '.join(cur)}")
    L.append(f"   sama dengan daftar aplikasi: {len(set(cur) & set(LIVE))}/20; tidak ada di aplikasi: "
             f"{sorted(set(cur) - set(LIVE))}; di aplikasi tetapi bukan top-20: {sorted(set(LIVE) - set(cur))}")
    hist = df[(df["rank"] <= 20) & (df.index >= START)]
    share = hist.base.isin(LIVE).groupby(level=0).mean()
    for k in (20, 30, 40, 60):
        inc = hist["rank1"] <= k
        L.append(f"   cara pindai cloud: top-20 (rata 7 hari) yang juga masuk top-{k} volume 24 jam (ticker): "
                 f"{inc.mean() * 100:.1f}%")
    L.append("   porsi koin aplikasi di top-20 historis per tahun: " + " ".join(
        f"{y}:{v * 100:.0f}%" for y, v in share.groupby(share.index.year).mean().items()))
    L.append("")

    # ---------------------------------------------------------------- simpan
    keep_keys = ["A", "E", "D", "b", "D2", "N30s10", "N50s10", "N100s20", "thr97", "vol70", "M2", "strict"]
    sigs = []
    for k in keep_keys:
        for lab in ("LAMA", "BARU"):
            if lab in R[k] and R[k][lab]["pf"]:
                x = R[k][lab]["pf"]["taken"].copy()
                x["varian"] = k
                sigs.append(x)
    if sigs:
        s = pd.concat(sigs)
        for col in s.columns:
            if s[col].dtype == object and col != "varian":
                s[col] = s[col].astype(str)
        OUT_SIG.parent.mkdir(parents=True, exist_ok=True)
        s.to_parquet(OUT_SIG, index=False)
    js = {}
    for k in ("E", "D", "b", "D2"):
        js[k] = {lab: {**{kk: round(v, 2) for kk, v in R[k][lab]["slot"].items()},
                       "pf_th": round(R[k][lab]["pf"]["cagr"] * 100, 1), "dd": round(R[k][lab]["pf"]["dd"] * 100, 1)}
                 for lab in ("LAMA", "BARU") if lab in R[k]}
    def _r(o):
        if isinstance(o, dict):
            return {k: _r(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_r(v) for v in o]
        return round(float(o), 2) if isinstance(o, (float, np.floating)) else o
    js["tier_dip_ringan_E"] = _r(tier)
    js["acak_E"] = _r(R["E"].get("acak"))
    K, us = ringkasan(R, tier)
    js["usulan_spot_model"] = us
    js = _r(js)
    OUT_JSON.write_text(json.dumps(js, ensure_ascii=False, indent=1, default=float), encoding="utf-8")

    head = [
        "# 💎 Spot dip untuk APK: uji JUJUR kandidat tambahan (research/spot_apk.py, 8 Okt 2026)",
        f"Data: kline 1d Binance {len(data)} pair USDT (termasuk delisting) s.d. {df.index.max():%Y-%m-%d}. "
        f"LAMA = {START:%Y-%m-%d} – Sep 2021, BARU = Okt 2021 – Sep 2026.",
        "Sinyal: p >= 0,93 ATAU 3 merah (red>=3, r3<=-10%, di atas SMA200) di close hari t; beli open t+1; limit jual +3%;"
        " maks 10 hari; biaya 0,30% pulang-pergi (x2 = 0,60%); satu posisi per koin; sinyal saat slot penuh tidak dikirim.",
        "Model gradient boosting WALK-FORWARD per tahun. M1 = resep riset lama (dilatih 20 koin hari ini + koin ambruk);"
        " M2 = dilatih 30 koin volume terbesar SAAT ITU (lebih jujur).",
        "Semesta jujur = N koin volume USDT terbesar (rata-rata 7 hari s.d. kemarin) di antara koin yang punya >= 200 hari"
        " riwayat, termasuk yang kemudian delisting. Urutan pindai = peringkat volume.",
        "Aturan: FILTER lolos hanya bila untung%, rata/sinyal, dan portofolio %/th naik di LAMA DAN BARU serta di atas "
        "acak p95. LABEL lolos bila tier atas lebih baik di kedua periode (dipilih dari LAMA).",
        f"Waktu jalan {time.time() - t0:.0f} dtk.", ""]
    # bagian VERIFIKASI (ditulis verifikator, bukan dihitung skrip ini) dipertahankan saat laporan dibuat ulang
    lama = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    verif = lama[lama.index("\n# VERIFIKASI"):] if "\n# VERIFIKASI" in lama else ""
    teks = "\n".join(head + K + L) + "\n"
    if verif:
        teks += "\n" + verif.lstrip("\n")
    OUT.write_text(teks, encoding="utf-8")
    print("\n".join(head + K + L))


def ringkasan(R: dict, tier: dict) -> tuple[list[str], dict]:
    """Kesimpulan + usulan implementasi (teks dari angka yang baru dihitung) dan usulan isi spot_model.json."""
    def g(k, lab, f):
        x = R[k].get(lab)
        if not x:
            return float("nan")
        if f in ("pf", "dd"):
            return x["pf"]["cagr" if f == "pf" else "dd"] * 100
        if f == "pf2":
            return x["pf2"]["cagr"] * 100
        return x["slot"][f]

    def p(v, d=1):
        return f"{v:+.{d}f}".replace(".", ",")

    def q(v, d=1):
        return f"{v:.{d}f}".replace(".", ",")

    kt, bs = tier["⚡ dip ringan"], tier["biasa"]
    ek = tier.get("_ekstra", {})
    ac = R["E"].get("acak", {})
    tk = pd.concat([R["E"][lab]["pf"]["taken"] for lab in ("LAMA", "BARU") if lab in R["E"]])
    kal = tk[(tk.t >= SPLIT) & (tk.p >= 0.97) & (tk.p < 0.99)]
    kal_wr = (kal.r > 0).mean() * 100 if len(kal) else float("nan")
    eks = tk[tk.ekor.astype(bool)] if "ekor" in tk.columns else tk.iloc[:0]
    eks_txt = ", ".join(f"{b} masuk {t:%d %b %Y} {r * 100:+.0f}%" for b, t, r in zip(eks.base, eks.t, eks.r)) or "tidak ada"
    bo = ek.get("boot", {})
    y2325 = ek.get("2325")
    pfk = ek.get("pf", {})
    c0 = R.get("_cek0", {}).get(("E", "BARU"), float("nan"))

    def pfs(nm, lab, i):
        return pfk.get(nm, {}).get(lab, (float("nan"),) * 3)[i]

    K = [
        "# RINGKASAN & KEPUTUSAN (angka = sinyal yang masuk slot; LAMA Jan 2020–Sep 2021 / BARU Okt 2021–Sep 2026)",
        "   (Versi setelah VERIFIKASI 8 Okt: baris 10 hari terakhir sebelum koin DELISTING kini ikut dinilai, LAMA",
        "   efektif mulai 2020 karena model 2019 tidak ada. Lihat bagian VERIFIKASI di akhir file.)",
        "1. Angka 'teruji' di aplikasi sekarang (spot_model.json: 'naik 92% sinyal, rata +1,37%, rugi rata -13,3%,",
        "   terburuk -58%', dasar acak 75,8%) berasal dari 20 koin yang DIPILIH HARI INI (research/spot_vol.py, bias",
        "   penyintas). Di mesin ini 20 koin tetap itu: BARU " +
        f"{q(g('A', 'BARU', 'wr'))}% / {p(g('A', 'BARU', 'avg'), 2)}%/sinyal, portofolio {p(g('A', 'BARU', 'pf'))}%/th.",
        "   Angka JUJUR (E: 20 koin volume terbesar SAAT ITU, termasuk yang kemudian delisting, model walk-forward):",
        f"   LAMA untung di {q(g('E', 'LAMA', 'wr'))}% sinyal, rata {p(g('E', 'LAMA', 'avg'), 2)}%, rugi rata "
        f"{p(g('E', 'LAMA', 'kalah'))}%, terburuk {p(g('E', 'LAMA', 'terburuk'), 0)}%, portofolio {p(g('E', 'LAMA', 'pf'))}%/th "
        f"DD {q(g('E', 'LAMA', 'dd'), 0)}%;",
        f"   BARU untung di {q(g('E', 'BARU', 'wr'))}% sinyal, rata {p(g('E', 'BARU', 'avg'), 2)}%, rugi rata "
        f"{p(g('E', 'BARU', 'kalah'))}%, terburuk {p(g('E', 'BARU', 'terburuk'), 0)}%, portofolio {p(g('E', 'BARU', 'pf'))}%/th "
        f"DD {q(g('E', 'BARU', 'dd'), 0)}% (biaya x2 {p(g('E', 'BARU', 'pf2'))}%/th).",
        f"   Sinyal tepat sebelum delisting yang masuk slot: {eks_txt}.",
        (f"   Acak di semesta sama BARU: untung {q(ac['BARU']['median'][0])}%, rata {p(ac['BARU']['median'][1], 2)}%, "
         f"portofolio {p(ac['BARU']['median'][2])}%/th -> sinyal tetap jauh di atas acak." if ac.get("BARU") else ""),
        f"   Model dilatih semesta jujur (M2): BARU {q(g('M2', 'BARU', 'wr'))}% / "
        f"{p(g('M2', 'BARU', 'avg'), 2)}%/sinyal, {p(g('M2', 'BARU', 'pf'))}%/th DD {q(g('M2', 'BARU', 'dd'), 0)}% "
        f"(LAMA {p(g('M2', 'LAMA', 'avg'), 2)}%/sinyal). TP harus tembus 0,1%: "
        f"{p(g('strict', 'BARU', 'avg'), 2)}%/sinyal, {p(g('strict', 'BARU', 'pf'))}%/th.",
        "   Portofolio sensitif terhadap detail kecil (urutan koin saat slot penuh, cara memilih semesta): BARU E "
        f"{p(g('E', 'BARU', 'pf'))}%/th (urutan volume) vs {p(c0)}%/th (urutan daftar model, bagian 0), semesta volume "
        f"24 jam {p(g('rank1', 'BARU', 'pf'))}%/th. Angka per sinyal lebih stabil.",
        "2. FILTER tambahan (harus naik untung%, rata, DAN portofolio di LAMA & BARU, di atas acak): TIDAK ADA yang lolos.",
        f"   a) BTC>SMA200: BARU {q(g('D', 'BARU', 'wr'))}% / {p(g('D', 'BARU', 'avg'), 2)}% / {p(g('D', 'BARU', 'pf'))}%/th DD "
        f"{q(g('D', 'BARU', 'dd'), 0)}% (risiko turun), tetapi LAMA {p(g('D', 'LAMA', 'pf'))}%/th vs {p(g('E', 'LAMA', 'pf'))}%/th "
        "dan untung%/rata LAMA turun. Sebagai LABEL juga tidak konsisten (LAMA: sinyal saat BTC di bawah SMA200 justru "
        "lebih baik; BARU kebalikannya).",
        f"   b) kualitas: portofolio LAMA {p(g('b', 'LAMA', 'pf'))}, BARU {p(g('b', 'BARU', 'pf'))}%/th (E "
        f"{p(g('E', 'LAMA', 'pf'))} / {p(g('E', 'BARU', 'pf'))}) -> lihat KEPUTUSAN di bagian 1.",
        f"   c) top-30/50/100 (10/20 slot): untung% & rata/sinyal LEBIH RENDAH di LAMA dan BARU; DD lebih dalam "
        f"(top-100 20 slot BARU DD {q(g('N100s20', 'BARU', 'dd'), 0)}%). 'Semua koin Binance' tidak menaikkan WR/profit.",
        f"   e) ambang 0,95/0,97, lewati vol > P70: tidak lolos. Kalibrasi BARU datar: p 0,97–0,99 hanya "
        f"{q(kal_wr)}% untung ->",
        "      angka 'peluang 9x%' di cincin aplikasi BUKAN peluang nyata.",
        "3. LABEL yang lolos: '⚡ Dip ringan' = harga saat sinyal masih <= 15% di bawah high 20 hari (fitur dd20 > -0,15,",
        "   sudah dihitung cloud). Sinyal TIDAK dibuang; hanya diberi label & angka teruji per label.",
        f"   ⚡  LAMA n {kt['LAMA']['n']} untung {q(kt['LAMA']['wr'])}% rata {p(kt['LAMA']['avg'], 2)}% rugi rata "
        f"{p(kt['LAMA']['kalah'])}% terburuk {p(kt['LAMA']['terburuk'], 0)}% | BARU n {kt['BARU']['n']} untung "
        f"{q(kt['BARU']['wr'])}% rata {p(kt['BARU']['avg'], 2)}% rugi rata {p(kt['BARU']['kalah'])}% terburuk "
        f"{p(kt['BARU']['terburuk'], 0)}% (±{q(kt['BARU']['per_bulan'])}/bln; rugi >= 20%: {q(kt['BARU']['rugi20'])}% sinyal)",
        f"   biasa LAMA n {bs['LAMA']['n']} untung {q(bs['LAMA']['wr'])}% rata {p(bs['LAMA']['avg'], 2)}% rugi rata "
        f"{p(bs['LAMA']['kalah'])}% terburuk {p(bs['LAMA']['terburuk'], 0)}% | BARU n {bs['BARU']['n']} untung "
        f"{q(bs['BARU']['wr'])}% rata {p(bs['BARU']['avg'], 2)}% rugi rata {p(bs['BARU']['kalah'])}% terburuk "
        f"{p(bs['BARU']['terburuk'], 0)}% (rugi >= 20%: {q(bs['BARU']['rugi20'])}% sinyal)",
        ("   Bukti tambahan (bagian 4b): bootstrap blok bulan selisih rata ⚡-biasa BARU "
         f"{p(bo['BARU']['avg'][0], 2)} poin [CI95 {p(bo['BARU']['avg'][1], 2)}..{p(bo['BARU']['avg'][2], 2)}], LAMA "
         f"{p(bo['LAMA']['avg'][0], 2)} [{p(bo['LAMA']['avg'][1], 2)}..{p(bo['LAMA']['avg'][2], 2)}]; selisih untung% "
         f"BARU {p(bo['BARU']['wr'][0])} [{p(bo['BARU']['wr'][1])}..{p(bo['BARU']['wr'][2])}] (CI melewati 0 = belum "
         "signifikan);" if bo.get("BARU") and bo.get("LAMA") else "   Bukti tambahan: lihat bagian 4b;"),
        "   ambang -10/-12/-15/-18% searah di kedua periode (-25% berbalik di LAMA); searah di model M2, semesta volume",
        "   24 jam, tanpa filter vol, TP ketat, BTC naik & turun; angka dasar hari 'dekat high' tanpa sinyal justru",
        (f"   lebih buruk (BARU {q(ek['dasar']['BARU'][0])}% vs {q(ek['dasar']['BARU'][1])}%)." if ek.get("dasar") else
         "   lebih buruk."),
        "   JUJUR: (i) arah 'ringan' baru dipertimbangkan setelah melihat BARU (daftar awal memuat 'jatuh dalam'; dari",
        "   20 kriteria dua arah hanya ini yang lebih baik di kedua periode); (ii) keunggulan terutama di tahun turun/datar",
        "   (2020, 2022, 2026)" + (f"; 2023–2025 untung% ⚡ {q(y2325[0]['wr'])}% vs biasa {q(y2325[1]['wr'])}% (rata "
                                  f"{p(y2325[0]['avg'], 2)}% vs {p(y2325[1]['avg'], 2)}%)" if y2325 else "") +
        "; (iii) di koin peringkat 21–100 hanya terlihat di BARU. -> pasang sebagai LABEL + uji maju, bukan filter.",
        f"   Ukuran opsional (BUKAN bawaan): ⚡ 10% modal / biasa 5% -> BARU {p(pfs('⚡ 10% / biasa 5%', 'BARU', 0))}%/th DD "
        f"{q(pfs('⚡ 10% / biasa 5%', 'BARU', 1), 0)}% (biaya x2 {p(pfs('⚡ 10% / biasa 5%', 'BARU', 2))}%) vs semua 10% "
        f"{p(pfs('semua 10% (terpasang)', 'BARU', 0))}%/th DD {q(pfs('semua 10% (terpasang)', 'BARU', 1), 0)}% (x2 "
        f"{p(pfs('semua 10% (terpasang)', 'BARU', 2))}%); LAMA {p(pfs('⚡ 10% / biasa 5%', 'LAMA', 0))}% vs "
        f"{p(pfs('semua 10% (terpasang)', 'LAMA', 0))}%/th -> mengurangi risiko, bukan menambah profit LAMA.",
        "",
        "# USULAN IMPLEMENTASI (JANGAN dipasang tanpa izin; file cloud/ & android/ tidak diubah riset ini)",
        "A. Angka teruji + label (isi lengkap di docs/eksternal/spot_apk_teruji.json 'usulan_spot_model'):",
        "   - JANGAN tulis ke cloud/api/spot_model.json: tests/test_spot_paritas.py mengunci sha256 file itu (sama dengan",
        "     sniper_bot/strategi/spot_model.json & fixture). Taruh di file baru cloud/api/spot_teruji.json (dibaca _spot.py,",
        "     menimpa MODEL['teruji'] bila ada), ATAU buat ulang fixture + salinan sniper_bot sekaligus.",
        "   - 'teruji' DIGANTI angka jujur E (bukan 20 koin penyintas); kunci baru wr/avg/kalah/terburuk tetap (SpotCard &",
        "     research/peringkat.py membaca kunci itu + 'lama' + 'dasar_baru'); tambah 'teruji_metode'.",
        "   - 'tier': {'dd20_min': -0.15, 'kilat': {nama '⚡ Dip ringan', lama, baru}, 'biasa': {nama 'Biasa', lama, baru}}.",
        "B. cloud/api/_spot.py (label saja; keputusan BELI/CLOSE TIDAK berubah, tanpa panggilan data tambahan):",
        "   - tier = 'kilat' bila dict(zip(MODEL['fitur'], x))['dd20'] > tier['dd20_min'] else 'biasa' (tier tidak ada ->",
        "     tanpa label, jangan KeyError); env SPOT_TIER (bawaan '1'; '0' = tanpa label, event tetap seperti sekarang).",
        "   - pos & event spot_signal: + 'tier', 'tier_nama', 'dd20' (persen, 1 desimal), 'teruji_tier' {lama, baru};",
        "     spot_close & closed[]: + 'tier'; spot_status: 'teruji' jujur + 'tier' (angka per label).",
        "   - Judul ntfy: '💎 BELI SPOT {KOIN}/USDT • ⚡ Dip ringan' / '💎 BELI SPOT {KOIN}/USDT • biasa' (ganti 'peluang naik p%').",
        f"   - Teks: '⚡ Dip ringan: harga masih ≤15% di bawah puncak 20 hari. Teruji Okt 2021–2026: untung di "
        f"{kt['BARU']['wr']:.0f}% sinyal,",
        f"     rata {p(kt['BARU']['avg'])}%, rugi terburuk {p(kt['BARU']['terburuk'], 0)}%.' / biasa: 'Teruji Okt 2021–2026: "
        f"untung di {bs['BARU']['wr']:.0f}% sinyal, rata {p(bs['BARU']['avg'])}%",
        f"     (hampir impas setelah biaya), rugi terburuk {p(bs['BARU']['terburuk'], 0)}% (koin bisa delisting).' (angka "
        "dari file teruji, dibulatkan).",
        "   - tests/test_cloud_spot.py: tier kilat/biasa dari dd20, SPOT_TIER=0, tanpa blok tier, angka teruji dibaca dari file.",
        "C. android SpotCard.kt + Notifications.kt (aplikasi 4.24):",
        "   - Pill '⚡ Dip ringan' (Gold) di samping 'BELI SPOT' bila tier = kilat; tanpa pill untuk biasa.",
        "   - Cincin: ganti 'p% peluang' -> untung% teruji label (mis. '92%' + 'teruji'); p model kecil 'skor model 95'.",
        f"   - Baris bawah kartu: 'Teruji Okt 2021–2026 (20 koin volume terbesar saat itu, termasuk delisting): ⚡ untung di "
        f"{kt['BARU']['wr']:.0f}% sinyal,",
        f"     rata {p(kt['BARU']['avg'])}% • biasa {bs['BARU']['wr']:.0f}%, {p(bs['BARU']['avg'])}% • rugi terburuk "
        f"{p(bs['BARU']['terburuk'], 0)}% • acak " + (f"{ac['BARU']['median'][0]:.0f}%'." if ac.get("BARU") else "-'."),
        f"   - NoteBox: 'Maks 10% modal per koin. Tanpa SL: sesekali rugi besar (⚡ terburuk {p(kt['BARU']['terburuk'], 0)}%, "
        f"biasa {p(bs['BARU']['terburuk'], 0)}%).'",
        "   - Close terakhir: tampilkan ⚡ di depan koin bila tier kilat. SignalRepository tidak berubah (spot_status apa adanya).",
        "D. research/peringkat.py: baris 💎 memakai angka jujur + baris '💎 ⚡ Dip ringan (label)' (status 'label').",
        "E. Semesta (opsional, BUKAN penambah WR/profit, hanya menyamakan dengan uji jujur): env SPOT_SEMESTA=volume (bawaan",
        "   'tetap' = 20 koin sekarang). Cara pindai: 1x GET data-api.binance.vision/api/v3/ticker/24hr?type=MINI (semua",
        "   pair) -> 40 pair USDT volume 24 jam terbesar (tanpa stablecoin/emas/token pembungkus/leverage/token saham",
        "   '...B') -> kline 1d 420 bar (field quote volume r[7]) -> rata-rata volume 7 hari s.d. kemarin -> 20 teratas yang",
        "   punya >= 201 candle tutup; daftar hari itu DISIMPAN di state (scan.todo) agar tick lanjutan tidak menghitung",
        "   ulang. Top-40 24 jam memuat 98% top-20 rata-rata 7 hari (bagian 6). Panggilan 1 + 40 (sekarang 20): pakai",
        "   batas waktu tick (deadline_s 20 dtk) + lanjut tick berikutnya. Posisi terbuka tetap dipantau walau keluar daftar.",
        "",
    ]
    us = {
        "teruji_metode": "20 koin volume USDT terbesar SAAT ITU (rata 7 hari), termasuk delisting (10 hari terakhir "
                         "sebelum delisting ikut dinilai, keluar di close terakhir); model walk-forward; biaya 0,30%; "
                         "sinyal masuk slot 10; LAMA Jan 2020–Sep 2021, BARU Okt 2021–Sep 2026; research/spot_apk.py",
        "teruji": {
            "baru": {"n": g("E", "BARU", "n"), "wr": g("E", "BARU", "wr"), "avg": g("E", "BARU", "avg"),
                     "kalah": g("E", "BARU", "kalah"), "terburuk": g("E", "BARU", "terburuk"),
                     "pf_th": g("E", "BARU", "pf"), "dd": g("E", "BARU", "dd")},
            "lama": {"n": g("E", "LAMA", "n"), "wr": g("E", "LAMA", "wr"), "avg": g("E", "LAMA", "avg"),
                     "kalah": g("E", "LAMA", "kalah"), "terburuk": g("E", "LAMA", "terburuk"),
                     "pf_th": g("E", "LAMA", "pf"), "dd": g("E", "LAMA", "dd")},
            "dasar_baru": ac["BARU"]["median"][0] if ac.get("BARU") else None,
            "catatan": "angka jujur tanpa bias penyintas (bukan 20 koin yang dipilih hari ini)",
        },
        "tier": {
            "dd20_min": -0.15,
            "kilat": {"nama": "⚡ Dip ringan", "syarat": "harga <= 15% di bawah high 20 hari",
                      **{lab.lower(): {k: kt[lab][k] for k in ("n", "wr", "avg", "kalah", "terburuk")}
                         for lab in ("LAMA", "BARU")}},
            "biasa": {"nama": "Biasa",
                      **{lab.lower(): {k: bs[lab][k] for k in ("n", "wr", "avg", "kalah", "terburuk")}
                         for lab in ("LAMA", "BARU")}},
        },
    }
    return K, us


if __name__ == "__main__":
    sys.exit(main())
