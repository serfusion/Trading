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


def muat_pool(net: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    pools = pd.read_parquet(OUT / f"{net}_pools.parquet")
    liq = pd.read_parquet(OUT / f"{net}_liq.parquet") if (OUT / f"{net}_liq.parquet").exists() else pd.DataFrame()
    blk = pd.read_parquet(OUT / f"{net}_blok.parquet")["ts"]
    R = resmi(net)
    pools["n0"] = pools.c0.map(lambda a: R[a][0])
    pools["n1"] = pools.c1.map(lambda a: R[a][0])
    pools["r0"] = pools.c0.map(lambda a: R[a][1])
    pools["r1"] = pools.c1.map(lambda a: R[a][1])
    pools["t_buat"] = ke_waktu(pools.blok.to_numpy(), blk)
    pools["pair"] = pools.n0 + "/" + pools.n1
    if len(liq):
        liq["t"] = ke_waktu(liq.blok.to_numpy(), blk)
    return pools, liq, blk


def _nilai_bagian(sw: pd.DataFrame, pools: pd.DataFrame, liq: pd.DataFrame, blk: pd.Series, refs: dict,
                  net: str) -> pd.DataFrame:
    sw = sw.merge(pools[["id", "ver", "pair", "r0", "r1", "d0", "d1", "sqrtp0", "t_buat"]], on="id", how="left")
    sw = sw.sort_values(["id", "blok", "li"]).reset_index(drop=True)
    sw["t"] = ke_waktu(sw.blok.to_numpy(), blk)
    p0 = np.zeros(len(sw))
    p1 = np.zeros(len(sw))
    for col, arr in (("r0", p0), ("r1", p1)):
        for r in set(sw[col]):
            m = (sw[col] == r).to_numpy()
            arr[m] = _ref_at(refs[r], pd.DatetimeIndex(sw.t[m]), "3min")
    v0 = sw.a0.to_numpy() / 10.0 ** sw.d0.to_numpy() * p0
    v1 = sw.a1.to_numpy() / 10.0 ** sw.d1.to_numpy() * p1
    dd = (sw.d0 - sw.d1).to_numpy().astype(float)
    # harga token0 dalam token1 (manusia) setelah swap; sebelum swap = setelah swap sebelumnya di pool yang sama
    px_post = (sw.sqrtp.to_numpy() / 2 ** 96) ** 2 * 10.0 ** dd
    first = (sw.id != sw.id.shift()).to_numpy()
    sq0 = pd.to_numeric(sw.sqrtp0.replace("", np.nan), errors="coerce").to_numpy(dtype=float)
    px_init = (sq0 / 2 ** 96) ** 2 * 10.0 ** dd
    px_pre = np.where(first, px_init, np.roll(px_post, 1))
    prev_t = sw.t.shift().where(~first, sw.t_buat)
    if len(liq):
        lq = liq[(liq.dL > 0) & liq.id.isin(set(sw.id))][["id", "t"]].sort_values("t")
        if len(lq):
            lq["t_liq"] = lq.t
            q = sw[["id", "t"]].reset_index().sort_values("t")
            q["id"] = q.id.astype(str)
            lq["id"] = lq.id.astype(str)
            s2 = pd.merge_asof(q, lq, on="t", by="id", direction="backward").set_index("index").sort_index()
            prev_t = pd.concat([prev_t, s2.t_liq], axis=1).max(axis=1)
    out = pd.DataFrame({
        "id": sw.id.astype(str), "blok": sw.blok.to_numpy(), "li": sw.li.to_numpy().astype("int32"),
        "txh": sw.txh.to_numpy(),
        "sender": sw.sender.astype(str), "t": sw.t, "ver": sw.ver.to_numpy().astype("int8"), "pair": sw.pair,
        "untung_usd": v0 + v1, "notional": np.maximum(np.abs(v0), np.abs(v1)).astype("float32"),
        "dev_pra": (px_pre * p1 / p0 - 1), "dev_pasca": (px_post * p1 / p0 - 1),
        "jeda_dtk": (sw.t - prev_t).dt.total_seconds().to_numpy().astype("float32"),
    })
    out["hari"] = ((out.t - LAUNCH[net]).dt.total_seconds() / 86400).astype("float32")
    return out


def nilai(net: str, maks_baris: int = 2_500_000) -> pd.DataFrame:
    """Dinilai per kelompok pool (hemat memori: swap Robinhood > 10 juta baris)."""
    pools, liq, blk = muat_pool(net)
    refs = {r: acuan_1m(r) for r in set(pools.r0) | set(pools.r1)}
    f = OUT / f"{net}_swap.parquet"
    import pyarrow.parquet as pq
    kol = pq.read_schema(f).names
    sw = pd.read_parquet(f, columns=["id", "blok", "li", "sender", "a0", "a1", "sqrtp"] + (["txh"] if "txh" in kol else ["tx"]))
    if "txh" not in sw:
        sw["txh"] = sw.pop("tx").map(lambda x: int(x[2:17], 16)).astype("int64")
    sw["id"] = sw.id.astype(str)
    n = sw.id.value_counts()
    grp, cur, acc = [], [], 0
    for pid, c in n.items():
        if acc + c > maks_baris and cur:
            grp.append(cur)
            cur, acc = [], 0
        cur.append(pid)
        acc += c
    if cur:
        grp.append(cur)
    parts = []
    for g in grp:
        parts.append(_nilai_bagian(sw[sw.id.isin(set(g))], pools, liq, blk, refs, net))
    out = pd.concat(parts, ignore_index=True)
    for c in ("id", "sender", "pair"):
        out[c] = out[c].astype("category")
    return out.sort_values(["blok", "li"]).reset_index(drop=True)


def _tx(net: str, rows: pd.DataFrame) -> list[str]:
    """Hash transaksi dari file bagian (file gabungan tidak menyimpan tx agar hemat memori)."""
    parts = sorted((OUT / f"{net}_swap_parts").glob("swap_*.parquet"))
    if not parts:
        import pyarrow.parquet as pq
        if "tx" in pq.read_schema(OUT / f"{net}_swap.parquet").names:
            parts = [OUT / f"{net}_swap.parquet"]
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


def aksi(x: pd.DataFrame) -> pd.DataFrame:
    """Swap digabung per (transaksi, pengirim): rute multi-hop & manuver bolak-balik dalam satu transaksi dinetto
    (contoh: bot meminjam 50 WETH, jatuhkan harga, swap balik -> per swap tampak +/-$83 ribu, bersih +$317)."""
    g = x.groupby(["txh", "sender"], observed=True, sort=False)
    a = g.agg(t=("t", "first"), hari=("hari", "first"), periode=("periode", "first"), pair=("pair", "first"),
              kategori=("kategori", "first"), untung_usd=("untung_usd", "sum"), notional=("notional", "max"),
              dev_pra=("dev_pra", "first"), dev_pasca=("dev_pasca", "last"), jeda_dtk=("jeda_dtk", "first"),
              n_swap=("untung_usd", "size"), blok=("blok", "first"), li=("li", "first"))
    return a.reset_index()


def _tabel(x: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    g = x.groupby("periode", observed=True)
    ga = a.groupby("periode", observed=True)
    t = pd.DataFrame({
        "swap": g.size(),
        "hari": g.hari.agg(lambda h: max(h.max() - h.min(), 0.25)),
        "untung_total$": ga.untung_usd.agg(lambda u: u[u > 0].sum()),
        "aksi_untung>$10": ga.untung_usd.agg(lambda u: (u > 10).sum()),
        "aksi_untung>$100": ga.untung_usd.agg(lambda u: (u > 100).sum()),
        "rugi_penukar$": ga.apply(lambda d: d[d.untung_usd < -0.05 * d.notional].untung_usd.sum()),
        "|dev| median": g.dev_pra.agg(lambda d: d.abs().median()),
        "|dev|>1%": g.dev_pra.agg(lambda d: (d.abs() > 0.01).mean()),
        "|dev|>5%": g.dev_pra.agg(lambda d: (d.abs() > 0.05).mean()),
    })
    t["untung$/hari"] = t["untung_total$"] / t["hari"]
    return t


def laporan(net: str) -> str:
    sw = nilai(net)
    sw["kategori"] = sw.pair.astype(str).map(lambda p: kategori(net, p))
    sw.to_parquet(OUT / f"{net}_nilai.parquet")
    kecil = sw[(sw.untung_usd.abs() > 1) | (sw.dev_pra.abs() > 0.005)]
    kecil.to_parquet(OUT / f"{net}_nilai_ringkas.parquet", compression="zstd")  # yang di-commit (file penuh besar)
    L = []
    p = L.append
    ok = sw.untung_usd.notna()
    p(f"=== {net}: {len(sw):,} swap di {sw.id.nunique()} pool (kedua token dari daftar; v4 {int((sw.ver == 4).sum()):,}, "
      f"v3 {int((sw.ver == 3).sum()):,}); dinilai {int(ok.sum()):,} (sisanya token saham di luar jam bursa NYSE)")
    p("Untung = nilai diterima - dibayar pada harga ACUAN menit itu (fee pool termasuk, gas TIDAK), dijumlah per "
      "(transaksi, pengirim) = 'aksi'. Ini untung yang SUDAH DIAMBIL pelaku (arbitrase/sniping/bot), bukan janji.")
    p("rugi_penukar$ = jumlah aksi yang rugi > 5% dari nilainya (slippage tanpa batas / jadi korban sandwich).")
    x = sw[ok].copy()
    x["periode"] = pd.cut(x.hari, BIN, labels=LBL)
    A = aksi(x)
    for kat in sorted(x.kategori.unique()):
        xk, ak = x[x.kategori == kat], A[A.kategori == kat]
        p(f"\n######## kategori: {kat} — pasangan: {', '.join(sorted(map(str, xk.pair.unique())))[:600]}")
        p("-- per periode sejak peluncuran publik")
        p(_tabel(xk, ak).round(4).to_string())
    x = x[x.kategori != "tiruan"]
    A = A[A.kategori != "tiruan"]
    p("\n######## berikut TANPA token tiruan")
    p("-- per pasangan (aksi)")
    gp = A.groupby("pair", observed=True)
    tp = pd.DataFrame({"aksi": gp.size(), "untung_total$": gp.untung_usd.agg(lambda u: u[u > 0].sum()),
                       "untung 3 hari pertama$": gp.apply(lambda d: d[(d.hari >= 0) & (d.hari < 3) & (d.untung_usd > 0)].untung_usd.sum()),
                       "rugi_penukar$": gp.apply(lambda d: d[d.untung_usd < -0.05 * d.notional].untung_usd.sum())})
    gs = x.groupby("pair", observed=True)
    tp["|dev| median"] = gs.dev_pra.agg(lambda d: d.abs().median())
    tp["|dev| median > 14 hari"] = gs.apply(lambda d: d[d.hari > 14].dev_pra.abs().median())
    p(tp.sort_values("untung_total$", ascending=False).round(4).head(25).to_string())

    p("\n-- JACKPOT: 15 aksi paling untung (setelah peluncuran publik)")
    pub = A[A.hari >= 0]
    top = pub.nlargest(15, "untung_usd").copy()
    top["tx"] = _tx(net, top)
    p(top[["t", "hari", "pair", "n_swap", "notional", "untung_usd", "dev_pra", "jeda_dtk", "sender", "tx"]].round(4).to_string())
    p("pengirim paling sering di 100 aksi paling untung: " +
      ", ".join(f"{str(k)[:10]}.. {v}" for k, v in pub.nlargest(100, "untung_usd").sender.astype(str).value_counts().head(5).items()))
    p("\n-- 10 aksi paling RUGI (pelajaran batas slippage)")
    bot = pub.nsmallest(10, "untung_usd").copy()
    bot["tx"] = _tx(net, bot)
    p(bot[["t", "pair", "n_swap", "notional", "untung_usd", "dev_pra", "dev_pasca", "sender", "tx"]].round(4).to_string())

    p("\n-- siapa cepat dia dapat: untung aksi yang peluangnya terbuka >= L detik (bisa direbut bot ber-jeda L dtk)")
    rows = []
    for per, d in A.groupby("periode", observed=True):
        u = d[d.untung_usd > 0]
        row = {"periode": per, "untung_total$": u.untung_usd.sum()}
        for Ls in (0.5, 2, 10, 60, 300):
            row[f">={Ls}s"] = u[u.jeda_dtk >= Ls].untung_usd.sum()
        rows.append(row)
    p(pd.DataFrame(rows).round(0).to_string(index=False))

    p("\n-- aturan bot: ambil aksi untung bila |selisih| pool >= b dan peluang terbuka >= 10 dtk (perkiraan ATAS, tanpa gas)")
    rows = []
    for per, d in A.groupby("periode", observed=True):
        hari = max(d.hari.max() - d.hari.min(), 0.25)
        for b in (0.005, 0.01, 0.02, 0.05, 0.1, 0.3):
            u = d[(d.untung_usd > 0) & (d.dev_pra.abs() >= b) & (d.jeda_dtk >= 10)]
            rows.append({"periode": per, "b": b, "peluang/hari": len(u) / hari, "untung$/hari": u.untung_usd.sum() / hari,
                         "median untung$": u.untung_usd.median() if len(u) else 0,
                         "median notional$": u.notional.median() if len(u) else 0,
                         "untung/notional": (u.untung_usd.sum() / u.notional.sum()) if len(u) else 0})
    p(pd.DataFrame(rows).round(3).to_string(index=False))

    p("\n-- slippage aksi satu-swap yang untung > $1 (perubahan harga pool oleh swap itu sendiri)")
    u = A[(A.untung_usd > 1) & (A.hari >= 0) & (A.n_swap == 1)]
    move = ((1 + u.dev_pasca) / (1 + u.dev_pra) - 1).abs()
    p(f"median {move.median():.3%}, P75 {move.quantile(.75):.3%}, P90 {move.quantile(.9):.3%} (n {len(u):,})")
    for per, d in u.assign(m=move).groupby("periode", observed=True):
        p(f"  {per}: median {d.m.median():.3%}, P90 {d.m.quantile(.9):.3%}, untung/notional median "
          f"{(d.untung_usd / d.notional).median():.3%} (n {len(d):,})")
    out = "\n".join(L)
    (ROOT / "docs" / "eksternal").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "eksternal" / f"hasil_chain_{net}.txt").write_text(out)
    return out


def tambahan(net: str, token: list[str]) -> str:
    """Per token: untung aksi |selisih| >= 1% sejak swap pertama token; untung BERSIH per pelaku; CRCL per minggu."""
    x = pd.read_parquet(OUT / f"{net}_nilai.parquet")
    x = x[x.untung_usd.notna() & (x.kategori != "tiruan")].copy()
    x["periode"] = pd.cut(x.hari, BIN, labels=LBL)
    A = aksi(x)
    A["pair"] = A.pair.astype(str)
    L = []
    p = L.append
    rows = []
    for s_ in token:
        a = A[A.pair.str.split("/").map(lambda q, s_=s_: s_ in q)]
        if not len(a):
            continue
        t0 = a.t.min()
        a = a.assign(dt=(a.t - t0).dt.total_seconds() / 3600)
        g = a[(a.untung_usd > 0) & (a.dev_pra.abs() >= 0.01)]
        rest = max((a.dt.max() - 168) / 24, 1)
        rows.append({"token": s_, "swap_pertama": t0.strftime("%Y-%m-%d %H:%M"),
                     "jam_1$": g[g.dt < 1].untung_usd.sum(), "jam_1-24$": g[(g.dt >= 1) & (g.dt < 24)].untung_usd.sum(),
                     "hari_1-7$": g[(g.dt >= 24) & (g.dt < 168)].untung_usd.sum(),
                     "$/hari sesudah 7 hari": g[g.dt >= 168].untung_usd.sum() / rest,
                     "hari terbaik": g.groupby(g.t.dt.date).untung_usd.sum().idxmax() if len(g) else None,
                     "untung hari terbaik$": g.groupby(g.t.dt.date).untung_usd.sum().max() if len(g) else 0,
                     "jeda median 100 aksi teratas (dtk)": g.nlargest(100, "untung_usd").jeda_dtk.median()})
    p("-- per token: untung aksi dengan |selisih| >= 1% (sebelum gas) sejak swap pertama token itu")
    p(pd.DataFrame(rows).set_index("token").round(2).to_string())
    N = A.groupby("sender", observed=True).agg(aksi=("untung_usd", "size"), bersih=("untung_usd", "sum"),
                                               kotor=("untung_usd", lambda u: u[u > 0].sum()))
    N = N.sort_values("bersih", ascending=False)
    p("\n-- untung BERSIH per pengirim (semua aksi + dan -); pengirim = kontrak bot/router, bukan selalu satu orang")
    p(N.head(10).round(0).to_string())
    p(f"pengirim {len(N):,}; bersih > $1.000: {(N.bersih > 1000).sum()}; bersih < -$1.000: {(N.bersih < -1000).sum()}; "
      f"bersih total semua pelaku ${N.bersih.sum():,.0f} (fee LP + derau acuan)")
    for tk in ("CRCL",):
        c = A[A.pair.str.contains(tk)].copy()
        if not len(c):
            continue
        c["minggu"] = c.t.dt.to_period("W").astype(str)
        dev1 = (c.untung_usd > 0) & (c.dev_pra.abs() >= 0.01)
        t = c.groupby("minggu").agg(aksi=("untung_usd", "size"), bersih_semua=("untung_usd", "sum"),
                                    dev_median=("dev_pra", lambda d: d.abs().median()))
        t["untung |dev|>=1%"] = c[dev1].groupby("minggu").untung_usd.sum()
        p(f"\n-- {tk} per minggu (jam bursa NYSE saja)")
        p(t.fillna(0).round(4).to_string())
    out = "\n".join(L)
    f = ROOT / "docs" / "eksternal" / f"hasil_chain_{net}.txt"
    f.write_text(f.read_text() + "\n\n" + out)
    return out


SAHAM_RH = ["CRCL", "NVDA", "SPY", "TSLA", "AAPL", "COIN", "MSTR", "PLTR", "GOOGL", "AMZN", "META", "QQQ", "AMD", "MSFT",
            "GME", "HIMS"]


if __name__ == "__main__":
    print(laporan(sys.argv[1]))
    if sys.argv[1] == "robinhood":
        print(tambahan("robinhood", SAHAM_RH))
