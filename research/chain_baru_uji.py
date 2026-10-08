"""Uji selisih harga DEX vs harga acuan di chain baru (Robinhood Chain, Arc) — python -m research.chain_baru_uji <net>

Data: research/chain_onchain.py (setiap swap Uniswap v4/v3 pool resmi-resmi) + acuan 1 menit (research/chain_baru.py:
ETH/BTC Binance, saham Twelve Data jam reguler NYSE, EUR/USD Twelve Data).

Untuk setiap swap:
  untung_usd  = nilai token diterima - nilai token dibayar, dinilai dengan harga ACUAN menit itu (fee pool sudah
                termasuk; gas TIDAK). Positif = penukar membeli murah / menjual mahal dibanding harga wajar.
  dev_pra     = harga pool SEBELUM swap / harga acuan - 1 (token0 dalam USD)
  jeda_dtk    = waktu sejak kejadian terakhir di pool (swap lain / tambah likuiditas / pool dibuat) -> berapa lama
                peluang itu "terbuka" sebelum diambil. Swap untung dengan jeda >= L detik = bisa direbut bot yang
                bereaksi dalam L detik (perkiraan ATAS: pesaing juga bisa mempercepat diri).
Periode dihitung dari peluncuran publik chain: Robinhood 1 Jul 2026, Arc 16 Sep 2026.
Saham di luar jam bursa: acuan tidak ada -> swap tidak dinilai (dilaporkan terpisah).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .chain_baru import DIR
from .chain_onchain import OUT, ke_waktu, resmi

ROOT = Path(__file__).resolve().parent.parent
LAUNCH = {"robinhood": pd.Timestamp("2026-07-01", tz="UTC"), "arc": pd.Timestamp("2026-09-16", tz="UTC")}
ACUAN = DIR / "acuan"


def acuan_1m(ref: str) -> pd.Series | None:
    """Harga USD per menit (index UTC). None untuk 'USD' (=1)."""
    if ref == "USD":
        return None
    f = {"ETH": "ETHUSDT_1m", "BTC": "BTCUSDT_1m", "EUR": "EURUSDT_1m"}.get(ref, f"{ref}_1m")
    p = ACUAN / f"{f}.parquet"
    if not p.exists():
        return pd.Series(dtype=float)
    s = pd.read_parquet(p)["close"].astype(float)
    s.index = s.index.floor("min")
    return s[~s.index.duplicated(keep="last")].sort_index()


def _ref_at(s: pd.Series | None, t: pd.DatetimeIndex, tol: str) -> np.ndarray:
    if s is None:
        return np.ones(len(t))
    if not len(s):
        return np.full(len(t), np.nan)
    q = pd.DataFrame({"t": t.floor("min").astype("datetime64[ns, UTC]"), "i": np.arange(len(t))}).sort_values("t")
    r = s.rename("p").rename_axis("t").reset_index()
    r["t"] = r.t.astype("datetime64[ns, UTC]")
    m = pd.merge_asof(q, r, on="t", direction="backward", tolerance=pd.Timedelta(tol))
    return m.sort_values("i")["p"].to_numpy()


def muat(net: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    pools = pd.read_parquet(OUT / f"{net}_pools.parquet")
    sw = pd.read_parquet(OUT / f"{net}_swap.parquet")
    liq = pd.read_parquet(OUT / f"{net}_liq.parquet") if (OUT / f"{net}_liq.parquet").exists() else pd.DataFrame()
    blk = pd.read_parquet(OUT / f"{net}_blok.parquet")["ts"]
    sw["t"] = ke_waktu(sw.blok.to_numpy(), blk)
    R = resmi(net)
    pools["n0"] = pools.c0.map(lambda a: R[a][0])
    pools["n1"] = pools.c1.map(lambda a: R[a][0])
    pools["r0"] = pools.c0.map(lambda a: R[a][1])
    pools["r1"] = pools.c1.map(lambda a: R[a][1])
    pools["t_buat"] = ke_waktu(pools.blok.to_numpy(), blk)
    sw = sw.merge(pools[["id", "ver", "n0", "n1", "r0", "r1", "d0", "d1", "sqrtp0", "t_buat"]], on="id", how="left")
    if len(liq):
        liq["t"] = ke_waktu(liq.blok.to_numpy(), blk)
    return pools, sw, liq


def nilai(net: str) -> pd.DataFrame:
    pools, sw, liq = muat(net)
    refs = {}
    for r in set(pools.r0) | set(pools.r1):
        refs[r] = acuan_1m(r)
    sw = sw.sort_values(["id", "blok", "li"]).reset_index(drop=True)
    p0 = np.zeros(len(sw))
    p1 = np.zeros(len(sw))
    for r in set(sw.r0):
        m = (sw.r0 == r).to_numpy()
        p0[m] = _ref_at(refs[r], pd.DatetimeIndex(sw.t[m]), "3min")
    for r in set(sw.r1):
        m = (sw.r1 == r).to_numpy()
        p1[m] = _ref_at(refs[r], pd.DatetimeIndex(sw.t[m]), "3min")
    sw["ref0"], sw["ref1"] = p0, p1
    a0 = sw.a0 / 10.0 ** sw.d0
    a1 = sw.a1 / 10.0 ** sw.d1
    sw["v0"], sw["v1"] = a0 * sw.ref0, a1 * sw.ref1
    sw["untung_usd"] = sw.v0 + sw.v1
    sw["notional"] = np.maximum(sw.v0.abs(), sw.v1.abs())
    # harga token0 dalam token1 (manusia) setelah swap; sebelum swap = setelah swap sebelumnya di pool yg sama
    px_post = (sw.sqrtp / 2 ** 96) ** 2 * 10.0 ** (sw.d0 - sw.d1)
    first = sw.id != sw.id.shift()
    sq0 = pd.to_numeric(sw.sqrtp0.replace("", np.nan), errors="coerce")
    px_init = (sq0 / 2 ** 96) ** 2 * 10.0 ** (sw.d0 - sw.d1)
    px_pre = px_post.shift().where(~first, px_init)
    sw["dev_pra"] = px_pre * sw.ref1 / sw.ref0 - 1
    sw["dev_pasca"] = px_post * sw.ref1 / sw.ref0 - 1
    # jeda sejak kejadian terakhir di pool (swap sebelumnya / likuiditas / pembuatan)
    prev_t = sw.t.shift().where(~first, sw.t_buat)
    if len(liq):
        lq = liq[liq.dL > 0][["id", "t"]].sort_values("t")
        lq["t_liq"] = lq.t
        s2 = pd.merge_asof(sw[["id", "t"]].reset_index().sort_values("t"), lq, on="t", by="id",
                           direction="backward", allow_exact_matches=True).set_index("index").sort_index()
        prev_t = pd.concat([prev_t, s2.t_liq], axis=1).max(axis=1)
    sw["jeda_dtk"] = (sw.t - prev_t).dt.total_seconds()
    sw["hari"] = (sw.t - LAUNCH[net]).dt.total_seconds() / 86400
    sw["pair"] = sw.n0 + "/" + sw.n1
    return sw


def _tx(net: str, rows: pd.DataFrame) -> list[str]:
    """Hash transaksi dari file bagian (file gabungan tidak menyimpan tx agar hemat memori)."""
    parts = sorted((OUT / f"{net}_swap_parts").glob("swap_*.parquet"))
    want = set(zip(rows.blok, rows.li))
    found = {}
    for f in parts:
        d = pd.read_parquet(f, columns=["blok", "li", "tx"])
        d = d[d.blok.between(min(b for b, _ in want), max(b for b, _ in want))]
        for b, li, tx in zip(d.blok, d.li, d.tx):
            if (b, li) in want:
                found[(b, li)] = tx
    return [found.get((b, li), "") for b, li in zip(rows.blok, rows.li)]


def kategori(net: str, pair: str) -> str:
    """Arc: akhiran _a = alamat TIRUAN (bukan dokumen Circle; WETH_a tidak dikenal), CRCL Arc = penerbit tidak jelas."""
    if net == "arc":
        if "_a" in pair:
            return "tiruan"
        if "CRCL" in pair:
            return "CRCL Arc (penerbit?)"
    return "resmi"


BIN = [-1e9, 0, 0.25, 1, 3, 7, 14, 30, 60, 1e9]
LBL = ["pra-luncur", "jam 0-6", "jam 6-24", "hari 1-3", "hari 3-7", "hari 7-14", "hari 14-30", "hari 30-60", "> 60 hari"]


def _tabel(x: pd.DataFrame) -> pd.DataFrame:
    g = x.groupby("periode", observed=True)
    t = pd.DataFrame({
        "swap": g.size(),
        "hari": g.hari.agg(lambda h: max(h.max() - h.min(), 0.25)),
        "untung_total$": g.untung_usd.agg(lambda u: u[u > 0].sum()),
        "swap_untung>$10": g.untung_usd.agg(lambda u: (u > 10).sum()),
        "swap_untung>$100": g.untung_usd.agg(lambda u: (u > 100).sum()),
        "|dev| median": g.dev_pra.agg(lambda d: d.abs().median()),
        "|dev|>1%": g.dev_pra.agg(lambda d: (d.abs() > 0.01).mean()),
        "|dev|>5%": g.dev_pra.agg(lambda d: (d.abs() > 0.05).mean()),
    })
    t["untung$/hari"] = t["untung_total$"] / t["hari"]
    return t


def laporan(net: str) -> str:
    sw = nilai(net)
    sw["kategori"] = sw.pair.map(lambda p: kategori(net, p))
    sw.to_parquet(OUT / f"{net}_nilai.parquet")
    kecil = sw[(sw.untung_usd.abs() > 1) | (sw.dev_pra.abs() > 0.005)].drop(columns=["sqrtp0"], errors="ignore")
    kecil.to_parquet(OUT / f"{net}_nilai_ringkas.parquet", compression="zstd")  # yang di-commit (file penuh besar)
    L = []
    p = L.append
    ok = sw.untung_usd.notna()
    p(f"=== {net}: {len(sw):,} swap di {sw.id.nunique()} pool (kedua token dari daftar; v4 {int((sw.ver == 4).sum()):,}, "
      f"v3 {int((sw.ver == 3).sum()):,}); dinilai {int(ok.sum()):,} (sisanya token saham di luar jam bursa NYSE)")
    p("Untung = nilai diterima - dibayar pada harga ACUAN menit itu (fee pool termasuk, gas TIDAK). Ini untung yang "
      "SUDAH DIAMBIL penukar (arbitrase/sniping), bukan janji untuk pemain baru.")
    x = sw[ok].copy()
    x["periode"] = pd.cut(x.hari, BIN, labels=LBL)
    for kat, xk in x.groupby("kategori"):
        p(f"\n######## kategori: {kat} — pasangan: {', '.join(sorted(xk.pair.unique()))}")
        p("-- per periode sejak peluncuran publik")
        p(_tabel(xk).round(4).to_string())
    x = x[x.kategori != "tiruan"]
    p("\n######## berikut TANPA token tiruan")
    p("-- per pasangan")
    gp = x.groupby("pair")
    tp = pd.DataFrame({"swap": gp.size(), "untung_total$": gp.untung_usd.agg(lambda u: u[u > 0].sum()),
                       "untung 3 hari pertama$": gp.apply(lambda d: d[(d.hari >= 0) & (d.hari < 3) & (d.untung_usd > 0)].untung_usd.sum()),
                       "|dev| median": gp.dev_pra.agg(lambda d: d.abs().median()),
                       "|dev| median > 14 hari": gp.apply(lambda d: d[d.hari > 14].dev_pra.abs().median())})
    p(tp.sort_values("untung_total$", ascending=False).round(4).head(25).to_string())

    p("\n-- JACKPOT: 15 swap paling untung (setelah peluncuran publik)")
    pub = x[x.hari >= 0]
    top = pub.nlargest(15, "untung_usd").copy()
    if "tx" not in top:
        top["tx"] = _tx(net, top)
    top = top[["t", "hari", "pair", "notional", "untung_usd", "dev_pra", "jeda_dtk", "sender", "tx"]]
    p(top.round(4).to_string())
    p("alamat pengirim paling sering di 100 swap paling untung: " +
      ", ".join(f"{k[:10]}.. {v}" for k, v in pub.nlargest(100, "untung_usd").sender.value_counts().head(5).items()))

    p("\n-- siapa cepat dia dapat: untung dari swap yang peluangnya terbuka >= L detik (bisa direbut bot ber-jeda L dtk)")
    rows = []
    for per, d in x.groupby("periode", observed=True):
        u = d[d.untung_usd > 0]
        row = {"periode": per, "untung_total$": u.untung_usd.sum()}
        for Ls in (0.5, 2, 10, 60, 300):
            row[f">={Ls}s"] = u[u.jeda_dtk >= Ls].untung_usd.sum()
        rows.append(row)
    p(pd.DataFrame(rows).round(0).to_string(index=False))

    p("\n-- aturan bot: ambil swap untung bila |selisih| pool >= b dan peluang terbuka >= 10 dtk (perkiraan ATAS, tanpa gas)")
    rows = []
    for per, d in x.groupby("periode", observed=True):
        hari = max(d.hari.max() - d.hari.min(), 0.25)
        for b in (0.005, 0.01, 0.02, 0.05, 0.1, 0.3):
            u = d[(d.untung_usd > 0) & (d.dev_pra.abs() >= b) & (d.jeda_dtk >= 10)]
            rows.append({"periode": per, "b": b, "peluang/hari": len(u) / hari, "untung$/hari": u.untung_usd.sum() / hari,
                         "median untung$": u.untung_usd.median() if len(u) else 0,
                         "median notional$": u.notional.median() if len(u) else 0,
                         "untung/notional": (u.untung_usd.sum() / u.notional.sum()) if len(u) else 0})
    p(pd.DataFrame(rows).round(3).to_string(index=False))

    p("\n-- slippage swap yang untung > $1 (perubahan harga pool oleh swap itu sendiri)")
    u = x[(x.untung_usd > 1) & (x.hari >= 0)]
    move = ((1 + u.dev_pasca) / (1 + u.dev_pra) - 1).abs()
    p(f"median {move.median():.3%}, P75 {move.quantile(.75):.3%}, P90 {move.quantile(.9):.3%} (n {len(u):,})")
    for per, d in u.assign(m=move).groupby("periode", observed=True):
        p(f"  {per}: median {d.m.median():.3%}, P90 {d.m.quantile(.9):.3%}, untung/notional median "
          f"{(d.untung_usd / d.notional).median():.3%} (n {len(d):,})")
    out = "\n".join(L)
    (ROOT / "docs" / "eksternal").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "eksternal" / f"hasil_chain_{net}.txt").write_text(out)
    return out


if __name__ == "__main__":
    print(laporan(sys.argv[1]))
