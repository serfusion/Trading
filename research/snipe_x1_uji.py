"""Analisis snipe X1 (lihat research/snipe_x1.py) — python -m research.snipe_x1 uji|kmn

Simulasi "sisip": transaksi kita (beli B XNT) DISISIPKAN ke urutan transaksi asli pool, lalu semua transaksi orang lain
diputar ulang dengan jumlah masuk yang sama (beli = XNT masuk, jual = token masuk; tambah/tarik likuiditas = proporsi
pool) → cadangan berubah karena kehadiran kita (penting: pool X1 sering hanya 10–50 XNT, 2 XNT = 4–20% pool).
Nilai jual = rumus x·y=k pada cadangan saat itu dikurangi biaya DEX (0,28–0,30%) & biaya bot (asumsi 1%/sisi).
Aturan keluar ditetapkan SEBELUM melihat hasil: TP m× (nilai jual nyata ≥ m × modal), keluar waktu T, tahan s/d
sekarang; "jual di puncak" (tahu masa depan) hanya batas atas. Jendela putar ulang = 24 jam pertama tiap pool.
"""
from __future__ import annotations

import datetime as dt
import numpy as np
import pandas as pd

from research import snipe_x1 as S

FEE_BOT = 0.01
JEDA = {"pertama (sebelum siapa pun)": 0, "10 dtk": 10, "30 dtk": 30, "1 mnt": 60, "5 mnt": 300, "30 mnt": 1800}
TP = [2, 3, 5, 10, 20, 50, 100, 200]
WAKTU = {"5 mnt": 300, "15 mnt": 900, "1 jam": 3600, "6 jam": 21600, "24 jam": 86400}
BUKAN_MEME = ("USDC", "USDT", "WSOL", "SOL", "ETH", "BTC", "XNM", "XBLK", "XUNI", "RXNT", "PXNT", "SXNT")


def kejadian(p: dict) -> pd.DataFrame | None:
    """Transaksi pool (24 jam pertama) → jenis & perubahan cadangan. Kolom: t, w, jenis, dtok, dxnt, x, y."""
    s = S.sisi(p)
    f = S.DIR / "swap" / f"{p['pool']}.json.gz"
    if s is None or not f.exists():
        return None
    vt, vx, dtk, dxn = s
    rows = []
    for r in S.muat(f):
        if r.get("err") or vt not in r or vx not in r:
            continue
        (a0, a1), (b0, b1) = r[vt], r[vx]
        if a1 is None or b1 is None:
            continue
        rows.append({"t": r["t"], "slot": r["slot"], "w": r["payer"], "x0": (a0 or 0) / 10 ** dtk,
                     "y0": (b0 or 0) / 10 ** dxn, "x": a1 / 10 ** dtk, "y": b1 / 10 ** dxn})
    if not rows:
        return None
    d = pd.DataFrame(rows).sort_values("slot", kind="stable").reset_index(drop=True)
    d["dtok"], d["dxnt"] = d.x - d.x0, d.y - d.y0
    j = np.where((d.dxnt > 0) & (d.dtok < 0), "beli", np.where((d.dxnt < 0) & (d.dtok > 0), "jual",
                 np.where((d.dxnt > 0) & (d.dtok > 0), "lp+", np.where((d.dxnt < 0) & (d.dtok < 0), "lp-", "lain"))))
    d["jenis"] = j
    if d.x0.iloc[0] == 0 and d.y0.iloc[0] == 0:
        d.loc[0, "jenis"] = "buat"
    return d


def putar(d: pd.DataFrame, fee: float, sisip: int, modal: float) -> tuple[float, np.ndarray, np.ndarray]:
    """Sisipkan beli `modal` XNT SETELAH kejadian ke-`sisip`; kembalikan (token kita, x[], y[]) mulai titik sisip."""
    x, y = float(d.x.iloc[sisip]), float(d.y.iloc[sisip])
    tok = S.beli(x, y, modal * (1 - FEE_BOT), fee)
    x, y = x - tok, y + modal * (1 - FEE_BOT)
    xs, ys = [x], [y]
    for r in d.iloc[sisip + 1:].itertuples():
        if r.jenis == "beli":
            a = r.dxnt
            out = x * a * (1 - fee) / (y + a * (1 - fee))
            x, y = x - out, y + a
        elif r.jenis == "jual":
            a = r.dtok
            out = y * a * (1 - fee) / (x + a * (1 - fee))
            x, y = x + a, y - out
        elif r.jenis in ("lp+", "lp-"):
            k = r.y / r.y0 if r.y0 > 0 else 1.0
            x, y = x * k, y * k
        else:
            x = x * (r.x / r.x0) if r.x0 > 0 else x
            y = y * (r.y / r.y0) if r.y0 > 0 else y
        xs.append(max(x, 1e-12))
        ys.append(max(y, 1e-12))
    return tok, np.array(xs), np.array(ys)


def nilai(tok: float, xs: np.ndarray, ys: np.ndarray, fee: float) -> np.ndarray:
    """XNT bersih bila semua token dijual pada tiap titik (biaya DEX + bot)."""
    a = tok * (1 - fee)
    return ys * a / (xs + a) * (1 - FEE_BOT)


def peluncuran() -> list[dict]:
    """Pool pertama tiap token (berpasangan WXNT), bukan aset jembatan/stabil."""
    pools = S.muat_pools()
    tanda = {}
    for p in pools:
        f = S.DIR / "tanda" / f"{p['pool']}.json.gz"
        if f.exists():
            tanda[p["pool"]] = S.muat(f)
    pertama: dict[str, tuple[int, dict]] = {}
    for p in pools:
        tg = tanda.get(p["pool"])
        if not tg or not tg["t0"]:
            continue
        for m in (p["mint0"], p["mint1"]):
            if m != S.WXNT and (m not in pertama or tg["t0"] < pertama[m][0]):
                pertama[m] = (tg["t0"], p)
    out = []
    for m, (t0, p) in pertama.items():
        sym = (p["sym1"] if p["mint1"] == m else p["sym0"]) or ""
        if S.sisi(p) is None or sym.upper().endswith(".X") or sym.upper() in BUKAN_MEME:
            continue
        out.append({**p, "mint": m, "sym": sym, "t0": t0, "tanda": tanda[p["pool"]]})
    return sorted(out, key=lambda q: q["t0"])


def harga_xnt() -> pd.Series:
    b = S.muat(S.DIR / "xnt_usd.json.gz")
    return pd.Series({pd.Timestamp(int(x["t"]), unit="s").normalize(): float(x["c"]) for x in b}).sort_index()


def ringkas_pool(L: dict, d: pd.DataFrame, cad: dict, pasok: dict) -> dict:
    s = S.sisi(L)
    vt, vx, dtk, dxn = s
    x_now, y_now = (cad.get(vt) or 0) / 10 ** dtk, (cad.get(vx) or 0) / 10 ** dxn
    c = d[d.jenis == "buat"]
    x0, y0 = (float(c.x.iloc[0]), float(c.y.iloc[0])) if len(c) else (float(d.x.iloc[0]), float(d.y.iloc[0]))
    t0 = int(d.t.iloc[0])
    beli_ = d[d.jenis == "beli"]
    pembeli = beli_[beli_.w != L["creator"]]
    sup = pasok.get(L["mint"])
    return {
        "pool": L["pool"], "sym": L["sym"], "t0": t0, "y0": y0, "x0": x0, "y_maks24": float(d.y.max()),
        "y_akhir24": float(d.y.iloc[-1]), "y_now": y_now, "x_now": x_now,
        "harga0": y0 / x0 if x0 else np.nan, "harga_maks24": float((d.y / d.x).max()),
        "harga_now": y_now / x_now if x_now else 0.0,
        "n24": int(len(d)), "n_total": L["tanda"]["n"] - L["tanda"]["n_err"], "n_beli24": int(len(beli_)),
        "pembeli24": int(pembeli.w.nunique()),
        "dtk_beli1": float(pembeli.t.iloc[0] - t0) if len(pembeli) else np.nan,
        "dev_jual24": bool(((d.jenis == "jual") & (d.w == L["creator"])).any()),
        "dev_tarik24": bool(((d.jenis == "lp-") & (d.w == L["creator"])).any()),
        "tarik24": bool((d.jenis == "lp-").any()),
        "porsi_pool": x0 / sup if sup else np.nan, "creator": L["creator"], "fee": L["fee"],
        "aktif_hari": int(sum(1 for v in L["tanda"].get("jam_hari", []) if v > 0)),
    }


def simulasi(d: pd.DataFrame, fee: float, modal: float, jeda: int, y_now: float, x_now: float) -> dict | None:
    t0 = d.t.iloc[0]
    idx = int(np.searchsorted(d.t.values, t0 + jeda, side="right") - 1) if jeda else 0
    idx = max(idx, 0)
    if idx >= len(d) - 0 and len(d) == 0:
        return None
    tok, xs, ys = putar(d, fee, idx, modal)
    if tok <= 0:
        return None
    v = nilai(tok, xs, ys, fee)
    t = np.concatenate([[d.t.iloc[idx]], d.t.values[idx + 1:]])
    te = t[0]
    out = {"jeda_nyata": float(te - t0), "puncak": float(v.max()), "24j": float(v[-1]),
           "now": float(S.jual(x_now, y_now, tok, fee) * (1 - FEE_BOT)) if x_now > 0 else 0.0}
    for m in TP:
        hit = np.nonzero(v >= m * modal)[0]
        out[f"tp{m}"] = float(v[hit[0]]) if len(hit) else float(v[-1])
        out[f"tp{m}_telat"] = float(v[min(hit[0] + 1, len(v) - 1)]) if len(hit) else float(v[-1])
        out[f"tp{m}_kena"] = bool(len(hit))
        out[f"tp{m}_now"] = float(v[hit[0]]) if len(hit) else out["now"]
    for k, sec in WAKTU.items():
        j = int(np.searchsorted(t, te + sec, side="right") - 1)
        out[f"w{k}"] = float(v[max(j, 0)])
    # TP 2× separuh lalu sisa ikut jalan (bebas modal) s/d 24 jam
    hit = np.nonzero(v >= 2 * modal)[0]
    out["separuh2"] = float(v[hit[0]] / 2 + v[-1] / 2) if len(hit) else float(v[-1])
    return out


def pnl_wallet(d: pd.DataFrame, fee: float) -> pd.DataFrame:
    """Untung/rugi NYATA tiap wallet dalam 24 jam pertama (swap saja): XNT keluar-masuk + sisa token dinilai harga jual
    nyata di akhir jendela. Token yang dikirim antar-wallet tidak terlihat → wallet penerima tampak 'menjual tanpa beli'."""
    sw = d[d.jenis.isin(["beli", "jual"])]
    if sw.empty:
        return pd.DataFrame()
    x, y = float(d.x.iloc[-1]), float(d.y.iloc[-1])
    g = sw.groupby("w").agg(xnt=("dxnt", "sum"), tok=("dtok", lambda s: -s.sum()), t1=("t", "min"),
                            modal=("dxnt", lambda s: s[s > 0].sum()))
    g["sisa"] = [S.jual(x, y, t, fee) if t > 0 else 0.0 for t in g.tok]
    g["pnl"] = -g.xnt + g.sisa
    g["urut"] = g.t1.rank(method="first")
    return g


def _fmt_pct(a) -> str:
    return f"{100 * np.mean(a):.0f}%"


def uji() -> None:
    launches = peluncuran()
    cad = S.muat(S.DIR / "cadangan.json.gz")["saldo"]
    pasok = S.muat(S.DIR / "pasok.json.gz") if (S.DIR / "pasok.json.gz").exists() else {}
    hx = harga_xnt()
    rows, sims, pemain = [], [], []
    for L in launches:
        d = kejadian(L)
        if d is None or len(d) < 1 or (d.jenis == "buat").sum() == 0:
            continue
        r = ringkas_pool(L, d, cad, pasok)
        rows.append(r)
        g = pnl_wallet(d, L["fee"])
        if not g.empty:
            g = g.reset_index()
            g["pool"], g["dtk"], g["pembuat"] = L["pool"], g.t1 - r["t0"], g.w == L["creator"]
            pemain.append(g)
        for nama, j in JEDA.items():
            for modal in (2.0, 10.0):
                s = simulasi(d, L["fee"], modal, j, r["y_now"], r["x_now"])
                if s:
                    sims.append({"pool": L["pool"], "jeda": nama, "modal": modal, "t0": r["t0"], **s})
    P, M = pd.DataFrame(rows), pd.DataFrame(sims)
    P.to_csv(S.DIR / "ringkas_pool.csv", index=False)
    M.to_csv(S.DIR / "simulasi.csv", index=False)
    P["bulan"] = pd.to_datetime(P.t0, unit="s").dt.to_period("M").astype(str)
    usd0 = [hx.asof(pd.Timestamp(t, unit="s")) for t in P.t0]
    P["usd_xnt"] = usd0

    L = []
    w = L.append
    w("🎯 SNIPE TOKEN BARU DI X1 (XDEX) — data on-chain rpc.mainnet.x1.xyz, diunduh "
      f"{dt.datetime.fromtimestamp(S.muat(S.DIR / 'cadangan.json.gz')['waktu'], dt.UTC):%d %b %Y %H:%M} UTC")
    w(f"Pool XDEX: {len(S.muat_pools())}; peluncuran token (pool pertama, pasangan WXNT, bukan aset jembatan): {len(P)}")
    w(f"Periode: {pd.to_datetime(P.t0.min(), unit='s'):%d %b %Y} – {pd.to_datetime(P.t0.max(), unit='s'):%d %b %Y}")
    w("")
    w("== 1. Seberapa besar 'pasar'-nya ==")
    q = P[["y0", "y_maks24", "y_now", "n24", "pembeli24", "dtk_beli1"]].describe(percentiles=[.25, .5, .75, .9, .99])
    w(q.round(2).to_string())
    P["usd_maks24"] = P.y_maks24 * P.usd_xnt
    w(f"Likuiditas XNT di pool saat puncak 24 jam (≈ uang maksimum yang bisa ditarik SEMUA penjual): median "
      f"{P.y_maks24.median():.1f} XNT (≈ ${P.usd_maks24.median():.1f}); ≥ 1.000 XNT hanya {(P.y_maks24 >= 1000).mean():.1%}")
    w(f"Peluncuran tanpa pembeli lain dalam 24 jam: {(P.pembeli24 == 0).mean():.0%}; ≤ 3 pembeli: "
      f"{(P.pembeli24 <= 3).mean():.0%}")
    w(f"Pembeli pertama (bukan pembuat) masuk: median {P.dtk_beli1.median():.0f} dtk setelah pool dibuat; "
      f"≤ 10 dtk {(P.dtk_beli1 <= 10).mean():.0%}, ≤ 60 dtk {(P.dtk_beli1 <= 60).mean():.0%}")
    w(f"Pembuat menjual token di 24 jam pertama: {P.dev_jual24.mean():.0%}; pembuat menarik likuiditas 24 jam: "
      f"{P.dev_tarik24.mean():.0%}; siapa pun menarik likuiditas 24 jam: {P.tarik24.mean():.0%}")
    if P.porsi_pool.notna().any():
        w(f"Porsi pasokan yang dimasukkan ke pool saat dibuat: median {P.porsi_pool.median():.0%}; < 50% (sisa di "
          f"tangan pembuat → bisa dibuang) {(P.porsi_pool < 0.5).mean():.0%}")
    P["mati"] = P.y_now <= 0.1 * P.y_maks24
    w(f"Likuiditas sekarang ≤ 10% dari puncak 24 jam ('mati'): {P.mati.mean():.0%}; harga sekarang < harga awal: "
      f"{(P.harga_now < P.harga0).mean():.0%}")
    w("")
    w("== 2. Klaim '$1 jadi $200' — simulasi beli 2 XNT (≈ $1 saat XNT $0,45) disisipkan ke transaksi asli ==")
    w("Biaya: DEX 0,28–0,30% + bot 1% per sisi. Kelipatan = XNT bersih diterima / modal.")
    for modal in (2.0, 10.0):
        w(f"-- modal {modal:g} XNT --")
        hdr = f"{'masuk':28s} {'n':>4s} {'puncak≥2×':>9s} {'≥10×':>6s} {'≥100×':>6s} {'≥200×':>6s} | " \
              f"{'tahan→now':>9s} {'24 jam':>7s} {'TP2×':>6s} {'TP5×':>6s} {'TP10×':>6s} {'TP2×½':>6s}"
        w(hdr)
        for nama in JEDA:
            m = M[(M.jeda == nama) & (M.modal == modal)]
            if m.empty:
                continue
            pk = m.puncak / modal
            roi = lambda c: f"{m[c].sum() / (modal * len(m)) - 1:+.0%}"  # noqa: E731
            w(f"{nama:28s} {len(m):4d} {_fmt_pct(pk >= 2):>9s} {_fmt_pct(pk >= 10):>6s} {_fmt_pct(pk >= 100):>6s} "
              f"{_fmt_pct(pk >= 200):>6s} | {roi('now'):>9s} {roi('24j'):>7s} {roi('tp2'):>6s} {roi('tp5'):>6s} "
              f"{roi('tp10'):>6s} {roi('separuh2'):>6s}")
    w("Kolom kiri = peluang nilai jual NYATA pernah mencapai k× (jual tepat di puncak = tahu masa depan).")
    w("Kolom kanan = hasil total bila snipe SEMUA peluncuran dengan aturan itu (ROI gabungan, + = untung).")
    w("")
    w("== 3. Semua aturan TP & waktu (modal 2 XNT) ==")
    kol = [f"tp{m}" for m in TP] + [f"tp{m}_telat" for m in (2, 5, 10)] + [f"tp{m}_now" for m in (2, 10, 100)] + \
          [f"w{k}" for k in WAKTU] + ["puncak", "now"]
    tab = []
    for nama in JEDA:
        m = M[(M.jeda == nama) & (M.modal == 2.0)]
        if m.empty:
            continue
        tab.append({"masuk": nama, **{c: m[c].sum() / (2.0 * len(m)) - 1 for c in kol}})
    w((pd.DataFrame(tab).set_index("masuk").T * 100).round(0).to_string())
    w("(angka = ROI % gabungan; tpM = jual saat nilai ≥ M×, bila tak kena jual di jam ke-24; _telat = jual 1 transaksi "
      "setelah sinyal; _now = bila tak kena tahan s/d sekarang; wT = jual setelah T)")
    w("")
    w("== 4. Per bulan (masuk 30 dtk, modal 2 XNT) ==")
    m = M[(M.jeda == "30 dtk") & (M.modal == 2.0)].merge(P[["pool", "bulan", "usd_xnt"]], on="pool")
    g = m.groupby("bulan").apply(lambda z: pd.Series({
        "n": len(z), "puncak≥10×": (z.puncak >= 20).mean(), "puncak≥200×": (z.puncak >= 400).mean(),
        "ROI_TP2": z.tp2.sum() / (2 * len(z)) - 1, "ROI_TP10": z.tp10.sum() / (2 * len(z)) - 1,
        "ROI_24j": z["24j"].sum() / (2 * len(z)) - 1, "XNT_usd": z.usd_xnt.mean()}), include_groups=False)
    w(g.round(2).to_string())
    w("")
    w("== 5. Peluncuran terbaik bagi penyisip 'pertama' (modal 2 XNT, jual di puncak = batas atas) ==")
    m = M[(M.jeda == "pertama (sebelum siapa pun)") & (M.modal == 2.0)].merge(P, on="pool", suffixes=("", "_p"))
    m = m.sort_values("puncak", ascending=False).head(15)
    for r in m.itertuples():
        w(f"{r.sym[:12]:12s} {pd.to_datetime(r.t0, unit='s'):%Y-%m-%d} puncak {r.puncak:8.1f} XNT ({r.puncak / 2:5.0f}×) "
          f"30dtk-TP10 {r.tp10:6.1f} | pool awal {r.y0:7.1f} → maks {r.y_maks24:8.1f} → now {r.y_now:8.1f} XNT, "
          f"pembeli24 {r.pembeli24}")
    w("")
    w("== 6. Pemain NYATA (bukan simulasi): untung/rugi wallet di 24 jam pertama ==")
    W = pd.concat(pemain, ignore_index=True)
    W = W[~W.pembuat & (W.modal > 0)]
    W.to_csv(S.DIR / "pemain.csv", index=False)
    W["kel"] = pd.cut(W.dtk, [-1, 60, 300, 3600, 6 * 3600, 1e9], labels=["≤ 1 mnt", "1–5 mnt", "5–60 mnt", "1–6 jam",
                                                                         "> 6 jam"])
    for k, z in W.groupby("kel", observed=True):
        w(f"masuk {k:9s}: {len(z):5d} posisi, modal {z.modal.sum():9.0f} XNT, untung bersih {z.pnl.sum():+9.0f} XNT "
          f"({z.pnl.sum() / z.modal.sum():+.0%}), wallet untung {(z.pnl > 0).mean():.0%}, ≥ 10× {(z.pnl >= 9 * z.modal).mean():.1%}, "
          f"≥ 100× {(z.pnl >= 99 * z.modal).mean():.2%}")
    ser = W[W.urut <= 3].groupby("w").agg(n=("pool", "nunique"), modal=("modal", "sum"), pnl=("pnl", "sum"),
                                         untung=("pnl", lambda s: (s > 0).mean()))
    ser = ser[ser.n >= 5].sort_values("n", ascending=False)
    w(f"Wallet yang ≥ 5 kali jadi 3 pembeli pertama (penembak/bot snipe): {len(ser)}; gabungan modal "
      f"{ser.modal.sum():.0f} XNT, untung {ser.pnl.sum():+.0f} XNT ({ser.pnl.sum() / max(ser.modal.sum(), 1e-9):+.0%})")
    for r in ser.head(12).itertuples():
        w(f"  {r.Index[:6]}… {r.n:3d} peluncuran, modal {r.modal:8.1f}, untung {r.pnl:+8.1f} XNT, untung di {r.untung:.0%}")
    fp = S.DIR / "penyandang.json.gz"
    if fp.exists():
        F = S.muat(fp)
        dari = {k: (v or {}).get("dari") for k, v in F.items()}
        terkait = []
        for r in P.itertuples():
            z = W[(W.pool == r.pool) & (W.urut <= 5)]
            c = r.creator
            link = [b for b in z.w if dari.get(b) == c or dari.get(c) == b or
                    (dari.get(b) and dari.get(b) == dari.get(c))]
            terkait.append(bool(link))
        P["orang_dalam"] = terkait
        w(f"Peluncuran yang salah satu dari 5 pembeli pertamanya TERHUBUNG ke pembuat (didanai pembuat / mendanai "
          f"pembuat / penyandang sama): {P.orang_dalam.mean():.0%} dari {len(P)}")
        z = W.merge(P[["pool", "creator"]], on="pool")
        z["terkait"] = [dari.get(b) == c or dari.get(c) == b or (dari.get(b) is not None and dari.get(b) == dari.get(c))
                        for b, c in zip(z.w, z.creator)]
        for k, q in z[z.urut <= 5].groupby("terkait"):
            w(f"  pembeli awal {'TERKAIT pembuat' if k else 'tidak terkait   '}: {len(q):4d} posisi, untung "
              f"{q.pnl.sum():+8.0f} XNT ({q.pnl.sum() / q.modal.sum():+.0%}), wallet untung {(q.pnl > 0).mean():.0%}")
    S.OUT.parent.mkdir(parents=True, exist_ok=True)
    S.OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def dana() -> None:
    """Unduh penyandang (pengirim XNT pertama) untuk pembuat + 5 pembeli pertama tiap peluncuran."""
    ws = []
    for L in peluncuran():
        d = kejadian(L)
        if d is None:
            continue
        ws.append(L["creator"])
        b = d[(d.jenis == "beli") & (d.w != L["creator"])].drop_duplicates("w")
        ws += list(b.w.head(5))
    S.penyandang(ws)


def kmn() -> None:
    p = next(p for p in S.muat_pools() if S.KMN in (p["mint0"], p["mint1"]))
    d = kejadian(p)
    print(d[["t", "w", "jenis", "dtok", "dxnt", "x", "y"]].head(40).to_string())


if __name__ == "__main__":
    uji()
