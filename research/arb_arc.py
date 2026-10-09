"""Bot screenshot "wetharb"/"circarb" di Arc: bukti, untung-rugi grup, jalur keluar (redeem), pihak lawan, jendela diskon.

    python -m research.arb_arc <tahap>

Lanjutan research/arb_cari.py (tahap pabrik/token/kandidat/swap_kandidat/cari/transfer_alamat/perdagangan_grup/fifo/potret).
Modul terpisah supaya tidak bentrok dengan pekerjaan Robinhood di arb_cari.py. HANYA MEMBACA: eth_getLogs, eth_call,
eth_getBlockByNumber, eth_getTransactionReceipt, eth_getCode, eth_getTransactionCount (Arc, Ethereum, Base, Arbitrum
publik) + API harga publik (data.binance.vision, Twelve Data bila kunci tersedia). Tanpa transaksi, tanpa kunci pribadi.

Tahap:
  log_token    semua event kontrak token "• Arc Token" (WETH/CRCL/NVDA, kode identik: mint(address,uint256,bytes32)
               oleh keeper, redeem(uint256,address) oleh pemegang, maxSupply, pause) -> arc_token_log.parquet
  layar        tabel pencocokan screenshot (jam UTC/WIB tepat dari stempel blok) -> arc_layar.parquet
  acuan        harga acuan menit: ETH Binance 1m, CRCL/NVDA NYSE (Twelve Data 1 mnt/harian) -> arc_acuan_*.parquet
  pnl          untung-rugi FIFO grup per bot & token + nilai sisa + nilai yang ditebus/dibakar
  lawan        pihak lawan di pool bot: siapa yang menjual murah (tx.from), rugi vs acuan
  jendela      sejak 16 Sep: swap pool aset bernilai dengan diskon >= 5% vs acuan (durasi, volume)
  blok         stempel waktu Arc tiap 1.000 blok (interpolasi blok->waktu galat < 1 dtk) -> arc_blok_rapat.parquet
  swap_nvda    swap semua pool NVDA•Arc (tidak masuk kandidat WETH/CRCL arb_cari) -> arc_swap_nvda.parquet
  jembatan     event Deposit/Release vault Robinhood (jembatan kustodian RH<->Arc) -> robinhood_jembatan_log.parquet
  cocok        pasangkan Minted/Redeemed Arc dengan Deposit/Release Robinhood (id sama): jeda, fee, alamat
  lawan2       pelaku tiap swap 3 pool bot (log Transfer pada tx yang sama), penjual murah & pemenang
  laporan      tulis bagian Arc di docs/eksternal/hasil_arb_cari.txt (di antara penanda MULAI/SELESAI)
Data: data/research/eksternal/arb/arc_*.parquet. Laporan: bagian Arc di docs/eksternal/hasil_arb_cari.txt
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from . import arb_cari as A
from .chain_onchain import OUT as ONCHAIN, _addr, ke_waktu, rpc

ARB = A.ARB
SCR = Path(os.environ.get("ARB_SCRATCH", "/tmp"))
TOKEN3 = list(A.TOK_ARC)            # WETH, CRCL, NVDA "• Arc Token"
KEEPER = "0x0d8e72ec76d44aab959b4156f29a3bfe50f5671a"   # keeper() ketiga token (EOA, nonce 13.468 pada 9 Okt 2026)
OWNER = A.ARC_TOKEN_PENERBIT                             # owner() ketiga token (EOA)
DIST = "0x7821f1d95173f214f0ef23069f3a95a29de3f311"     # EOA yang mengirim USDC/NVDA/CRCL ke E1 & menerima balik
BUAT = {"0xd02d2b38d9ccf08044f0a493350a2339fe8d708b": 19_948_946,   # blok pertama kode ada (pencarian biner getCode)
        "0x2ba0f44bdfc17fba30eda9cdbecb908ca45b043b": 19_729_553,
        "0x6505506540dc99f7366316b10e9cf1a584cbd42a": 18_671_508}
POOL_BOT = {"0x7a5de3edaab5780dbcc9a84a3dd9a25a5f4b5d8c": "WETH", "0x2e8180fa3967caf9abf57bbaeab9ae9063bcd7ba": "CRCL",
            "0x4268ad801dc449b12341add14d61119d470959f0": "NVDA"}
MAINNET_PUBLIK = pd.Timestamp("2026-09-16", tz="UTC")


def blok_rapat(langkah: int = 1000, b0: int = 18_400_000) -> pd.Series:
    """Stempel waktu tiap `langkah` blok sejak b0 (+ sampel lama) -> interpolasi blok->waktu galat < 1 dtk."""
    f = ARB / "arc_blok_rapat.parquet"
    old = pd.read_parquet(f)["ts"] if f.exists() else pd.Series(dtype="int64")
    top = A.head("arc")
    want = [b for b in range(b0, top + 1, langkah) if b not in set(old.index)] + [top]

    def satu(b):
        for k in range(5):
            try:
                return b, int(rpc("arc", "eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
            except Exception:  # noqa: BLE001
                time.sleep(1 + k)
        return b, None

    with ThreadPoolExecutor(8) as ex:
        new = {b: t for b, t in ex.map(satu, want) if t}
    lama = pd.read_parquet(ONCHAIN / "arc_blok.parquet")["ts"]
    s = pd.concat([lama, old, pd.Series(new, dtype="int64")]).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.to_frame("ts").to_parquet(f)
    return s


def _blk() -> pd.Series:
    f = ARB / "arc_blok_rapat.parquet"
    return pd.read_parquet(f)["ts"] if f.exists() else pd.read_parquet(ONCHAIN / "arc_blok.parquet")["ts"]


# ---------------------------------------------------------------- acuan harga
def acuan_kripto(sym: str = "ETHUSDT", start: str = "2026-09-01", end: str = "2026-10-08") -> pd.Series:
    """Close 1 menit Binance spot (data.binance.vision zip harian) -> arb/acuan_<sym>_1m.parquet."""
    from .chain_baru import _zip_1m
    f = ARB / f"acuan_{sym}_1m.parquet"
    old = pd.read_parquet(f) if f.exists() else pd.DataFrame()
    have = set(old.index.strftime("%Y-%m-%d")) if len(old) else set()
    parts = [old] if len(old) else []
    baru = 0
    for d in pd.date_range(start, end):
        if d.strftime("%Y-%m-%d") in have:
            continue
        x = _zip_1m(f"https://data.binance.vision/data/spot/daily/klines/{sym}/1m/{sym}-1m-{d:%Y-%m-%d}.zip")
        if x is not None:
            parts.append(x)
            baru += 1
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    if baru:
        df.to_parquet(f)
    return df["close"]


def acuan_saham(sym: str) -> pd.Series:
    """Close 1 menit NYSE (cache riset lama chain_baru/acuan, Twelve Data) — hanya jam bursa reguler."""
    from .chain_baru import DIR
    return pd.read_parquet(DIR / "acuan" / f"{sym}_1m.parquet")["close"]


def harga_acuan(sym: str, t: pd.Series | pd.DatetimeIndex, basi_maks: str | None = None) -> np.ndarray:
    """Harga acuan terakhir <= t (asof, tanpa look-ahead). Saham di luar jam bursa = close terakhir (Jumat utk akhir
    pekan); basi_maks membatasi umur harga (NaN bila lebih tua)."""
    s = acuan_kripto(sym) if sym.endswith("USDT") else acuan_saham(sym)
    s = s.sort_index()
    s.index = pd.DatetimeIndex(s.index).as_unit("ns")
    t = pd.DatetimeIndex(t).as_unit("ns")
    i = s.index.searchsorted(t, side="right") - 1
    v = np.where(i >= 0, s.to_numpy()[np.clip(i, 0, None)], np.nan)
    if basi_maks:
        umur = t - s.index[np.clip(i, 0, None)]
        v = np.where(umur <= pd.Timedelta(basi_maks), v, np.nan)
    return v


# ---------------------------------------------------------------- log token
def log_token() -> pd.DataFrame:
    """Semua log yang dipancarkan 3 kontrak token (semua topik), sejak blok pembuatan. Disimpan per bagian."""
    f = ARB / "arc_token_log.parquet"
    if f.exists():
        return pd.read_parquet(f)
    top = A.head("arc")
    parts = ARB / "arc_token_log_parts"
    parts.mkdir(exist_ok=True)
    b0 = min(BUAT.values())
    B = 400_000
    for k, c in enumerate(range(b0, top + 1, B)):
        fp = parts / f"p_{k:04d}.parquet"
        if fp.exists():
            continue
        c1 = min(c + B - 1, top)

        def dek(x):
            t = x["topics"]
            return {"token": x["address"].lower(), "blok": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16),
                    "tx": x["transactionHash"], "t0": t[0] if t else "", "t1": t[1] if len(t) > 1 else "",
                    "t2": t[2] if len(t) > 2 else "", "t3": t[3] if len(t) > 3 else "", "data": x["data"]}

        rows = A.scan("arc", {"address": TOKEN3}, c, c1, A.SPAN_ALAMAT["arc"], label=f"log token {k}", fn=dek)
        pd.DataFrame(rows, columns=["token", "blok", "li", "tx", "t0", "t1", "t2", "t3", "data"]).to_parquet(
            fp, compression="zstd")
        print(f"  log token bagian {k}: blok {c:,}-{c1:,}: {len(rows):,} log", flush=True)
    df = pd.concat([pd.read_parquet(p) for p in sorted(parts.glob("p_*.parquet"))], ignore_index=True)
    df = df.drop_duplicates(["tx", "li"]).sort_values(["blok", "li"]).reset_index(drop=True)
    df["t"] = ke_waktu(df.blok.to_numpy(), _blk())
    df.to_parquet(f, compression="zstd")
    print(f"log token: {len(df):,} -> {f} ({f.stat().st_size / 1e6:.1f} MB)")
    print(df.groupby(["token", "t0"]).size().to_string())
    return df


# ---------------------------------------------------------------- screenshot
def _ts_tepat(net: str, bloks) -> dict:
    out = {}
    for b in sorted(set(int(x) for x in bloks)):
        out[b] = int(rpc(net, "eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
    return out


def _batas_bot() -> pd.DataFrame:
    """Argumen buy(usdcIn, minOut) / sell(amountIn, minUsdcOut) tiap tx bot -> harga batas (USDC per token)."""
    b = pd.read_parquet(ARB / "arc_bot_tx.parquet")
    a = b.input.str[10:]
    x = np.array([int(v[:64], 16) for v in a], dtype=float)
    y = np.array([int(v[64:128], 16) for v in a], dtype=float)
    beli = b.input.str[:10] == "0xd6febde8"
    out = pd.DataFrame({"tx": b.tx, "arah": np.where(beli, "BUY", "SELL"),
                        "arg_usdc": np.where(beli, x / 1e6, y / 1e6), "arg_aset": np.where(beli, y / 1e18, x / 1e18)})
    out["batas"] = np.where(out.arg_aset > 0, out.arg_usdc / out.arg_aset, np.nan)   # BUY: maks; SELL: min
    out.loc[(out.arah == "BUY") & (out.arg_aset == 0), "batas"] = np.inf          # minOut 0 = tanpa batas
    return out


def layar() -> pd.DataFrame:
    """Swap screenshot yang cocok PERSIS (jumlah USDC 4 desimal & aset 8/6 digit) + jam blok tepat + acuan."""
    h = A.cari("arc")
    h = h[h.cocok == "pasangan"].copy()
    ts = _ts_tepat("arc", h.blok)
    h["utc"] = pd.to_datetime(h.blok.map(ts), unit="s", utc=True)
    h["wib"] = h.utc.dt.tz_convert("Asia/Jakarta")
    h["jam_cocok"] = h.wib.dt.strftime("%H:%M") == h.jam_wib
    h["harga"] = h.usd / h.aset
    ref = np.where(h.bot == "wetharb", "ETHUSDT", "CRCL")
    h["acuan_sym"] = ref
    h["acuan"] = np.nan
    for r_ in set(ref):
        m = h.acuan_sym == r_
        h.loc[m, "acuan"] = harga_acuan(r_, h.loc[m, "utc"])
    h["vs_acuan"] = h.harga / h.acuan - 1
    lim = _batas_bot().set_index("tx")
    h["batas"] = h.tx.map(lim.batas)
    cols = ["bot", "arah", "usd", "aset", "harga", "jam_wib", "utc", "wib", "jam_cocok", "blok", "tx", "id", "sender",
            "acuan_sym", "acuan", "vs_acuan", "batas"]
    h = h[cols].sort_values("blok").reset_index(drop=True)
    h.to_parquet(ARB / "arc_layar.parquet")
    return h


# ---------------------------------------------------------------- untung-rugi grup
ACUAN = {"WETH•Arc": "ETHUSDT", "CRCL•Arc": "CRCL", "NVDA•Arc": "NVDA"}
FEE_JEMBATAN = 0.01      # 1% tiap arah (Deposit/Release vault Robinhood; dicek dari event fee)
PANGGUNG = {"E1": "E1", "E2": "E2", **{v[0]: ("E1" if v[1] == A.E1 else "E2") for v in A.BOT.values()}}


def waktu(blok) -> pd.DatetimeIndex:
    return ke_waktu(np.asarray(blok, dtype=float), _blk())


def _acuan_kolom(df: pd.DataFrame, kol_sym: str = "sym", kol_t: str = "t") -> np.ndarray:
    out = np.full(len(df), np.nan)
    for sym, ref in ACUAN.items():
        m = (df[kol_sym] == sym).to_numpy()
        if m.any():
            out[m] = harga_acuan(ref, df.loc[m, kol_t])
    return out


def _fifo_putaran(tr: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """FIFO per transaksi jual: untung = hasil jual - biaya lot beli terdahulu (bagian yang tertutup)."""
    from collections import deque
    q: deque = deque()
    out = []
    for r in tr.itertuples():
        if r.qty > 0:
            q.append([r.qty, r.harga, r.t])
            continue
        amt, biaya, tutup, t_beli = -r.qty, 0.0, 0.0, None
        while amt > 1e-12 and q:
            lot = q[0]
            m = min(lot[0], amt)
            biaya += m * lot[1]
            tutup += m
            t_beli = t_beli or lot[2]
            lot[0] -= m
            amt -= m
            if lot[0] <= 1e-12:
                q.popleft()
        out.append({"t_jual": r.t, "t_beli_awal": t_beli, "qty": -r.qty, "qty_tertutup": tutup,
                    "hasil": tutup * r.harga, "biaya": biaya, "untung": tutup * r.harga - biaya,
                    "qty_tanpa_beli": amt, "hasil_tanpa_beli": amt * r.harga, "harga_jual": r.harga})
    return pd.DataFrame(out), [x for x in q]


def _saldo_sekarang(alamat: list[str]) -> pd.DataFrame:
    calls = [(tk, "0x70a08231" + "0" * 24 + a[2:]) for a in alamat for tk in TOKEN3]
    res = A.multicall("arc", calls)
    rows = []
    for (tk, data), r in zip(calls, res):
        rows.append({"alamat": "0x" + data[-40:], "token": tk, "sym": A.TOK_ARC[tk][0],
                     "saldo": int(r, 16) / 1e18 if r and r != "0x" else 0.0})
    return pd.DataFrame(rows)


def pnl() -> dict:
    """Untung-rugi grup E1/E2 + 8 kontrak bot (Arc): putaran FIFO per bot & token, buku besar per token."""
    g = pd.read_parquet(ARB / "arc_grup_perdagangan.parquet")
    g["t"] = waktu(g.blok)
    g["jenis"] = np.where(g.usdc * g.qty < 0, "swap", "lp")
    g["acuan"] = _acuan_kolom(g)
    g["vs_acuan"] = g.harga / g.acuan - 1
    g["sisi"] = g.nama.map(PANGGUNG)
    g.to_parquet(ARB / "arc_grup_perdagangan_t.parquet")
    sw = g[(g.jenis == "swap") & g.sym.isin(ACUAN)].sort_values(["blok", "tx"])
    # ---- per bot x token
    bot_rows, put_all = [], []
    for (nama, sym), tr in sw.groupby(["nama", "sym"]):
        put, sisa = _fifo_putaran(tr)
        put["nama"], put["sym"] = nama, sym
        put_all.append(put)
        cash = tr.usdc.cumsum()
        beli, jual = tr[tr.qty > 0], tr[tr.qty < 0]
        real = put[put.qty_tertutup > 0]
        cum = real.set_index("t_jual").untung.cumsum() if len(real) else pd.Series(dtype=float)
        ref_now = harga_acuan(ACUAN[sym], pd.DatetimeIndex([pd.Timestamp("2026-10-08 22:41", tz="UTC")]))[0]
        sisa_qty = sum(x[0] for x in sisa)
        sisa_biaya = sum(x[0] * x[1] for x in sisa)
        hari = max((tr.t.max() - tr.t.min()).total_seconds() / 86400, 1 / 24)
        bot_rows.append({
            "bot": nama, "sym": sym, "n_beli": len(beli), "n_jual": len(jual), "usdc_beli": -beli.usdc.sum(),
            "usdc_jual": jual.usdc.sum(), "qty_beli": beli.qty.sum(), "qty_jual": -jual.qty.sum(),
            "ukuran_beli_median": -beli.usdc.median() if len(beli) else np.nan,
            "harga_beli_med": beli.harga.median() if len(beli) else np.nan,
            "beli_vs_acuan_med": beli.vs_acuan.median() if len(beli) else np.nan,
            "harga_jual_med": jual.harga.median() if len(jual) else np.nan,
            "jual_vs_acuan_med": jual.vs_acuan.median() if len(jual) else np.nan,
            "putaran": len(real), "wr_putaran": (real.untung > 0).mean() if len(real) else np.nan,
            "untung_fifo": real.untung.sum(), "jual_tanpa_beli_qty": put.qty_tanpa_beli.sum() if len(put) else 0,
            "jual_tanpa_beli_usdc": put.hasil_tanpa_beli.sum() if len(put) else 0,
            "sisa_qty": sisa_qty, "sisa_biaya": sisa_biaya, "sisa_nilai_acuan_8okt": sisa_qty * ref_now * (1 - FEE_JEMBATAN),
            "kas_bersih": tr.usdc.sum(), "modal_maks": max(0.0, float((-cash).max())),
            "mulai": tr.t.min(), "selesai": tr.t.max(), "hari_aktif": hari,
            "untung_per_hari": real.untung.sum() / hari,
            "pertama_positif": cum[cum > 0].index.min() if len(cum) and (cum > 0).any() else pd.NaT,
            "puncak": cum.idxmax() if len(cum) else pd.NaT, "puncak_nilai": cum.max() if len(cum) else np.nan,
            "untung_sebelum_16sep": real[real.t_jual < MAINNET_PUBLIK].untung.sum(),
            "untung_sejak_16sep": real[real.t_jual >= MAINNET_PUBLIK].untung.sum(),
        })
    per_bot = pd.DataFrame(bot_rows)
    putaran = pd.concat(put_all, ignore_index=True)
    putaran.to_parquet(ARB / "arc_grup_putaran.parquet")
    per_bot.to_parquet(ARB / "arc_grup_pnl_bot.parquet")
    # ---- buku besar per token (seluruh grup: E1+E2+bot; transfer antar anggota grup diabaikan)
    t = A._transfer_grup()
    t = t[t.token.isin(TOKEN3)].copy()
    t["t"] = waktu(t.blok)
    G = set(A.GRUP)
    pools = set(pd.read_parquet(ARB / "arc_semua_pool.parquet", columns=["pool"]).pool) | {A.PM}
    gi, go = t.ke.isin(G), t.dari.isin(G)
    t = t[gi ^ go].copy()
    t["lawan"] = np.where(t.ke.isin(G), t.dari, t.ke)
    t["d"] = np.where(t.ke.isin(G), t.v, -t.v)
    t["kelas"] = np.select([t.lawan.isin(pools), t.lawan == "0x" + "0" * 40, t.lawan == DIST],
                           ["pool", "tebus(bakar)", "DIST"], "lain")
    t["acuan"] = _acuan_kolom(t)
    t["nilai_acuan"] = t.d * t.acuan
    t.to_parquet(ARB / "arc_grup_token_buku.parquet")
    sal = _saldo_sekarang(list(G))
    ref_now = {s_: harga_acuan(r_, pd.DatetimeIndex([pd.Timestamp("2026-10-08 22:41", tz="UTC")]))[0]
               for s_, r_ in ACUAN.items()}
    buku = []
    for sym in ACUAN:
        x = t[t.sym == sym]
        s_ = sw[sw.sym == sym]
        lp = g[(g.jenis == "lp") & (g.sym == sym)]
        tebus = x[x.kelas == "tebus(bakar)"]
        masuk = x[(x.kelas.isin(["DIST", "lain"])) & (x.d > 0)]
        keluar = x[(x.kelas.isin(["DIST", "lain"])) & (x.d < 0)]
        saldo = sal[sal.sym == sym].saldo.sum()
        r = {"sym": sym, "kas_pool": s_.usdc.sum(), "kas_lp": lp.usdc.sum(), "qty_pool_bersih": s_.qty.sum(),
             "qty_lp": lp.qty.sum(), "qty_masuk_luar": masuk.d.sum(),
             "nilai_masuk_luar": masuk.nilai_acuan.sum() / (1 - FEE_JEMBATAN),      # biaya menjembatani masuk
             "qty_keluar_luar": -keluar.d.sum(), "nilai_keluar_luar": -keluar.nilai_acuan.sum() * (1 - FEE_JEMBATAN),
             "qty_ditebus": -tebus.d.sum(), "nilai_ditebus_net": -(tebus.nilai_acuan.sum()) * (1 - FEE_JEMBATAN),
             "saldo_sekarang": saldo, "nilai_saldo_8okt": saldo * ref_now[sym] * (1 - FEE_JEMBATAN)}
        r["selisih_cek_qty"] = r["qty_pool_bersih"] + r["qty_lp"] + r["qty_masuk_luar"] - r["qty_keluar_luar"] - \
            r["qty_ditebus"] - saldo
        r["untung_termasuk_aset"] = r["kas_pool"] + r["kas_lp"] - r["nilai_masuk_luar"] + r["nilai_keluar_luar"] + \
            r["nilai_ditebus_net"] + r["nilai_saldo_8okt"]
        buku.append(r)
    buku = pd.DataFrame(buku)
    buku.to_parquet(ARB / "arc_grup_buku.parquet")
    # ---- harian grup (kas pool + tebus + transfer, nilai acuan) per tanggal UTC
    ev = pd.concat([sw.assign(nilai=sw.usdc, kind="kas_pool")[["t", "sym", "nilai", "kind"]],
                    t[t.kelas != "pool"].assign(nilai=-t.nilai_acuan * np.where(
                        t.kelas == "tebus(bakar)", 1 - FEE_JEMBATAN, np.where(t.d > 0, 1 / (1 - FEE_JEMBATAN),
                                                                              1 - FEE_JEMBATAN)),
                        kind=t.kelas)[["t", "sym", "nilai", "kind"]]])
    # nilai: token keluar (d<0) -> +nilai; masuk (d>0) -> -nilai
    harian = ev.assign(tgl=ev.t.dt.strftime("%Y-%m-%d")).pivot_table(index="tgl", columns="sym", values="nilai",
                                                                      aggfunc="sum").fillna(0.0)
    # modal grup: kas USDC kumulatif seluruh swap bot (urut waktu) -> uang maksimum yang pernah tertanam
    kas = sw.sort_values("t").usdc.cumsum()
    buku.attrs["modal_maks_grup"] = float(max(0.0, (-kas).max()))
    per_bot.attrs["modal_maks_grup"] = buku.attrs["modal_maks_grup"]
    return {"per_bot": per_bot, "putaran": putaran, "buku": buku, "harian": harian, "saldo": sal, "transfer": t,
            "trades": g}


# ---------------------------------------------------------------- swap pool NVDA•Arc (tidak masuk kandidat WETH/CRCL)
def swap_nvda() -> pd.DataFrame:
    f = ARB / "arc_swap_nvda.parquet"
    if f.exists():
        return pd.read_parquet(f)
    p = pd.read_parquet(ARB / "arc_semua_pool.parquet", columns=["jenis", "emitter", "blok", "pool", "c0", "c1"])
    nv = "0x6505506540dc99f7366316b10e9cf1a584cbd42a"
    p = p[(p.c0 == nv) | (p.c1 == nv)].drop_duplicates("pool")
    top = A.head("arc")
    jen = dict(zip(p.pool, p.jenis))
    rows = []
    v3 = p[p.jenis.isin(["v3", "v2"])]
    for i in range(0, len(v3), 20):
        part = v3.iloc[i:i + 20]
        rows += A.scan("arc", {"address": list(part.pool), "topics": [[A.T3_SWAP, A.T_V2_SWAP]]}, int(part.blok.min()),
                       top, A.SPAN_ALAMAT["arc"], label="nvda v3", fn=lambda x: A._dec_swap(x, jen))
    v4 = p[(p.jenis == "v4") & (p.emitter == A.PM)]
    if len(v4):
        rows += A.scan("arc", {"address": A.PM, "topics": [A.T_SWAP, list(v4.pool)]}, int(v4.blok.min()), top,
                       A.SPAN_ALAMAT["arc"], label="nvda v4", fn=lambda x: A._dec_swap(x, jen))
    df = pd.DataFrame(rows, columns=A.SWAP_COLS).sort_values(["blok", "li"]).reset_index(drop=True)
    df.to_parquet(f, compression="zstd")
    print(f"swap NVDA•Arc: {len(df):,} dari {len(p)} pool")
    return df


# ---------------------------------------------------------------- jendela diskon sejak mainnet publik
ASET_NILAI = {  # aset bernilai di Arc -> (nama, acuan, desimal, biaya tebus)
    "0xd02d2b38d9ccf08044f0a493350a2339fe8d708b": ("WETH•Arc (jembatan RH)", "ETHUSDT", 18, 0.01),
    "0x2ba0f44bdfc17fba30eda9cdbecb908ca45b043b": ("CRCL•Arc (jembatan RH)", "CRCL", 18, 0.01),
    "0x6505506540dc99f7366316b10e9cf1a584cbd42a": ("NVDA•Arc (jembatan RH)", "NVDA", 18, 0.01),
    "0x128cc466b61f542da60c70e3aa11c10e19b84edb": ("WETH_b (penerbit tdk jelas)", "ETHUSDT", 18, 0.0),
    "0x171a4217b86a807a64eb94757db6849fb4bdbaa0": ("cirBTC resmi", "BTCUSDT", 8, 0.0),
    "0xbef5f6d51cb62b58e6a8f77868681825c6fe21c1": ("EURC resmi", "EURUSDT", 6, 0.0),
}
USD_ARC = {"0x3600000000000000000000000000000000000000": 6, "0x0000000000000000000000000000000000000000": 18}


def swap_aset() -> pd.DataFrame:
    """Semua swap pool <aset bernilai>/USDC di Arc dari 3 sumber (kandidat, riset lama v4 resmi, NVDA)."""
    f = ARB / "arc_swap_aset.parquet"
    if f.exists():
        return pd.read_parquet(f)
    cols = ["id", "blok", "li", "tx", "sender", "a0", "a1", "sqrtp"]
    s1 = pd.read_parquet(ARB / "arc_swap_kandidat.parquet", columns=cols + ["recipient"])
    s2 = pd.read_parquet(ONCHAIN / "arc_swap.parquet", columns=cols)
    s3 = swap_nvda()[cols + ["recipient"]]
    sw = pd.concat([s1, s2.assign(recipient=""), s3], ignore_index=True).drop_duplicates(["tx", "li"])
    p1 = pd.read_parquet(ARB / "arc_semua_pool.parquet", columns=["pool", "jenis", "c0", "c1", "fee"]).drop_duplicates(
        "pool")
    p2 = pd.read_parquet(ONCHAIN / "arc_pools.parquet", columns=["id", "c0", "c1", "fee"]).rename(columns={"id": "pool"})
    pools = pd.concat([p1, p2.assign(jenis="v4")]).drop_duplicates("pool").set_index("pool")
    sw = sw.join(pools, on="id", how="inner")
    u0, u1 = sw.c0.isin(USD_ARC), sw.c1.isin(USD_ARC)
    a0, a1 = sw.c0.isin(ASET_NILAI), sw.c1.isin(ASET_NILAI)
    sw = sw[(u0 & a1) | (u1 & a0)].copy()
    usd0 = sw.c0.isin(USD_ARC).to_numpy()
    sw["aset"] = np.where(usd0, sw.c1, sw.c0)
    dq = np.where(usd0, sw.c0.map(USD_ARC), sw.c1.map(USD_ARC)).astype(float)
    da = sw.aset.map(lambda a: ASET_NILAI[a][2]).astype(float).to_numpy()
    sw["usd"] = np.where(usd0, sw.a0, sw.a1) / 10.0 ** dq          # sisi penukar: <0 = membayar USDC (BELI aset)
    sw["qty"] = np.where(usd0, sw.a1, sw.a0) / 10.0 ** da
    sw["harga"] = (sw.usd / sw.qty).abs()
    sq = sw.sqrtp.to_numpy() / Q96
    d0 = np.where(usd0, dq, da)
    d1 = np.where(usd0, da, dq)
    p01 = sq ** 2 * 10.0 ** (d0 - d1)
    sw["mid"] = np.where(usd0, 1 / p01, p01)
    sw = sw[np.isfinite(sw.harga) & (sw.qty != 0)]
    sw["t"] = waktu(sw.blok)
    sw["nama"] = sw.aset.map(lambda a: ASET_NILAI[a][0])
    sw["ref"] = sw.aset.map(lambda a: ASET_NILAI[a][1])
    sw["acuan"] = np.nan
    sw["acuan_umur_mnt"] = np.nan
    for r_ in sw.ref.unique():
        m = (sw.ref == r_).to_numpy()
        sw.loc[m, "acuan"] = harga_acuan(r_, sw.loc[m, "t"])
        segar = harga_acuan(r_, sw.loc[m, "t"], basi_maks="3min")
        sw.loc[m, "acuan_segar"] = np.isfinite(segar)
    sw["vs_acuan"] = sw.harga / sw.acuan - 1
    sw["mid_vs_acuan"] = sw.mid / sw.acuan - 1
    sw = sw.sort_values(["blok", "li"]).reset_index(drop=True)
    sw.drop(columns=["sqrtp"]).to_parquet(f, compression="zstd")
    print(f"swap aset bernilai: {len(sw):,}")
    return sw


Q96 = 2.0 ** 96


def jendela(ambang: float = 0.05, mulai: str = "2026-09-16") -> dict:
    """Sejak mainnet publik: menit-menit dengan harga mid pool <= (1-ambang) x acuan (diskon) atau >= (1+ambang)
    (premi), lama episode, volume swap yang mengambil selisih itu, untung kasar setelah biaya tebus 1%."""
    sw = swap_aset()
    sw = sw[sw.jenis.isin(["v3", "v4"])]
    t0 = pd.Timestamp(mulai, tz="UTC")
    t1 = pd.Timestamp("2026-10-08 13:00", tz="UTC")
    grid = pd.date_range(t0, t1, freq="1min")
    ep_rows, ring = [], []
    for (aset, pool), g in sw.groupby(["aset", "id"]):
        nama, ref, _, fee_t = ASET_NILAI[aset]
        g = g.sort_values(["blok", "li"])
        # harga mid terakhir per menit (asof) — hanya bila pool pernah di-swap sebelum menit itu
        i = pd.DatetimeIndex(g.t).as_unit("ns").searchsorted(grid.as_unit("ns"), side="right") - 1
        ok = i >= 0
        if not ok.any():
            continue
        mid = np.where(ok, g.mid.to_numpy()[np.clip(i, 0, None)], np.nan)
        acu = harga_acuan(ref, grid)
        segar = np.isfinite(harga_acuan(ref, grid, basi_maks="3min"))
        dev = mid / acu - 1
        g1 = g[g.t >= t0]
        beli = g1[g1.usd < 0]
        jual = g1[g1.usd > 0]
        bd = beli[beli.vs_acuan <= -ambang]
        jp = jual[jual.vs_acuan >= ambang]
        ring.append({
            "aset": nama, "pool": pool, "jenis": g.jenis.iloc[0], "fee": g.fee.iloc[0], "swap_sejak": len(g1),
            "vol_usd_sejak": g1.usd.abs().sum(), "menit_ada_harga": int(np.isfinite(dev[grid >= t0]).sum()),
            "menit_diskon": int((dev <= -ambang).sum()), "menit_diskon_segar": int(((dev <= -ambang) & segar).sum()),
            "menit_premi": int((dev >= ambang).sum()),
            "beli_diskon_n": len(bd), "beli_diskon_usd": -bd.usd.sum(),
            "beli_diskon_untung": (bd.qty * bd.acuan * (1 - fee_t) + bd.usd).sum(),
            "jual_premi_n": len(jp), "jual_premi_usd": jp.usd.sum(),
            "jual_premi_untung": (jp.usd + jp.qty * jp.acuan / (1 - fee_t)).sum(),
            "dev_med": float(np.nanmedian(dev)) if np.isfinite(dev).any() else np.nan,
        })
        # episode diskon berurutan
        m = dev <= -ambang
        if m.any():
            idx = np.flatnonzero(m)
            pecah = np.flatnonzero(np.diff(idx) > 1)
            awal = np.r_[idx[0], idx[pecah + 1]]
            akhir = np.r_[idx[pecah], idx[-1]]
            for a_, b_ in zip(awal, akhir):
                ta, tb = grid[a_], grid[b_] + pd.Timedelta(minutes=1)
                x = g1[(g1.t >= ta) & (g1.t < tb)]
                xb = x[(x.usd < 0) & (x.vs_acuan <= -ambang)]
                ep_rows.append({"aset": nama, "pool": pool, "mulai": ta, "selesai": tb,
                                "menit": int(b_ - a_ + 1), "dev_min": float(np.nanmin(dev[a_:b_ + 1])),
                                "dev_med": float(np.nanmedian(dev[a_:b_ + 1])), "segar_frac": float(segar[a_:b_ + 1].mean()),
                                "swap": len(x), "beli_diskon_n": len(xb), "beli_diskon_usd": -xb.usd.sum(),
                                "untung_kasar": (xb.qty * xb.acuan * (1 - fee_t) + xb.usd).sum()})
    ring = pd.DataFrame(ring).sort_values("beli_diskon_untung", ascending=False)
    ep = pd.DataFrame(ep_rows)
    ring.to_parquet(ARB / "arc_jendela_pool.parquet")
    ep.to_parquet(ARB / "arc_jendela_episode.parquet")
    # harian per aset (pool paling ramai per aset): median selisih eksekusi swap
    s2 = sw[sw.t >= pd.Timestamp("2026-09-01", tz="UTC")]
    hari = s2.assign(tgl=s2.t.dt.strftime("%m-%d")).groupby(["nama", "tgl"]).agg(
        n=("vs_acuan", "size"), med=("vs_acuan", "median"), vol=("usd", lambda v: v.abs().sum())).reset_index()
    hari.to_parquet(ARB / "arc_jendela_harian.parquet")
    return {"pool": ring, "episode": ep, "harian": hari}


# ---------------------------------------------------------------- pihak lawan
def lawan(sampai: str = "2026-09-16 01:00") -> dict:
    """Siapa yang MENJUAL murah di 3 pool bot (sebelum mainnet publik): penerima USDC (recipient swap v3 = dompet
    penjual bila lewat router), jumlah, rugi vs acuan (qty x acuan x 0,99 - USDC diterima), asal token penjual
    (mint jembatan = deposit sendiri di Robinhood / transfer / beli di pool)."""
    sw = swap_aset()
    sw = sw[sw.id.isin(POOL_BOT) & (sw.t < pd.Timestamp(sampai, tz="UTC"))].copy()
    G = set(A.GRUP)
    sw["grup"] = sw.sender.isin(G) | sw.recipient.isin(G)
    sw["pelaku"] = np.where(sw.recipient.str.len() == 42, sw.recipient, sw.sender)
    fee = 0.01
    sw["rugi_vs_acuan"] = np.where(sw.usd > 0, -sw.qty * sw.acuan * (1 - fee) - sw.usd, np.nan)   # penjual
    sw["untung_vs_acuan"] = np.where(sw.usd < 0, sw.qty * sw.acuan * (1 - fee) + sw.usd, np.nan)  # pembeli
    jual = sw[(sw.usd > 0) & ~sw.grup]
    beli = sw[(sw.usd < 0)]
    top_jual = jual.groupby(["nama", "pelaku"]).agg(
        n=("usd", "size"), usdc=("usd", "sum"), qty=("qty", lambda v: -v.sum()), rugi=("rugi_vs_acuan", "sum"),
        harga_med=("harga", "median"), vs_acuan_med=("vs_acuan", "median"), t0=("t", "min"), t1=("t", "max")
    ).reset_index().sort_values("rugi", ascending=False)
    # asal token para penjual teratas: Minted (jembatan), Transfer masuk non-pool, beli di pool
    lg = log_token()
    mint = lg[lg.t0 == T_MINT].assign(ke="0x" + lg.t2.str[-40:], v=lambda d: d.data.map(lambda h: int(h, 16) / 1e18))
    tr = lg[lg.t0 == A.T_TRANSFER].assign(dari="0x" + lg.t1.str[-40:], ke="0x" + lg.t2.str[-40:],
                                           v=lambda d: d.data.map(lambda h: int(h[:66], 16) / 1e18))
    pools = set(pd.read_parquet(ARB / "arc_semua_pool.parquet", columns=["pool"]).pool) | {A.PM}
    nol = "0x" + "0" * 40
    asal = []
    for r in top_jual.head(40).itertuples():
        tok = [a for a, v in ASET_NILAI.items() if v[0] == r.nama][0]
        x = tr[(tr.token == tok) & (tr.ke == r.pelaku)]
        asal.append({"nama": r.nama, "pelaku": r.pelaku,
                     "mint_jembatan": mint[(mint.token == tok) & (mint.ke == r.pelaku)].v.sum(),
                     "dari_pool": x[x.dari.isin(pools)].v.sum(), "dari_lain": x[~x.dari.isin(pools) & (x.dari != nol)].v.sum(),
                     "pengirim_lain_utama": x[~x.dari.isin(pools) & (x.dari != nol)].groupby("dari").v.sum().idxmax()
                     if (~x.dari.isin(pools) & (x.dari != nol)).any() else ""})
    asal = pd.DataFrame(asal)
    top_jual = top_jual.merge(asal, on=["nama", "pelaku"], how="left")
    top_beli = beli.groupby(["nama", "pelaku", "grup"]).agg(
        n=("usd", "size"), usdc=("usd", lambda v: -v.sum()), qty=("qty", "sum"), untung=("untung_vs_acuan", "sum"),
        harga_med=("harga", "median"), vs_acuan_med=("vs_acuan", "median")).reset_index().sort_values(
        "untung", ascending=False)
    ringkas = sw.groupby(["nama", sw.usd > 0]).agg(n=("usd", "size"), usdc=("usd", lambda v: v.abs().sum()),
                                                   pelaku=("pelaku", "nunique")).reset_index()
    top_jual.to_parquet(ARB / "arc_lawan_penjual.parquet")
    top_beli.to_parquet(ARB / "arc_lawan_pembeli.parquet")
    return {"penjual": top_jual, "pembeli": top_beli, "ringkas": ringkas, "swap": sw}


ROUTER_ARC = {"0x53bf6b0684ec7ef91e1387da3d1a1769bc5a6f77", "0x919c548ea8a779e0e551ef35f6aba65565b140a7",
              "0x00000000e91fc5bad977c0cc4ad60557c06886a2"}   # router/agregator (kontrak `to` tx, multi-hop & fee)


def pelaku_tx(sampai: str = "2026-09-16 06:00") -> pd.DataFrame:
    """Pelaku tiap swap di 3 pool bot dari log Transfer token pada tx yang sama (RPC Arc tidak melayani
    eth_getTransactionByHash untuk sebagian besar tx lama): penjual = pengirim Transfer PERTAMA yang bukan pool,
    pembeli = penerima Transfer TERAKHIR yang bukan pool. Bila hasilnya router/agregator (ROUTER_ARC) = rute
    multi-hop (pelaku asli tidak terlihat dari log token ini)."""
    sw = swap_aset()
    sw = sw[sw.id.isin(POOL_BOT) & (sw.t < pd.Timestamp(sampai, tz="UTC"))].copy()
    lg = log_token()
    tr = lg[(lg.t0 == A.T_TRANSFER) & lg.tx.isin(set(sw.tx))].copy()
    tr["dari"] = "0x" + tr.t1.str[-40:]
    tr["ke"] = "0x" + tr.t2.str[-40:]
    pools = set(pd.read_parquet(ARB / "arc_semua_pool.parquet", columns=["pool"]).pool) | {A.PM}
    lewat = pools | {"0x" + "0" * 40}
    G = set(A.GRUP)
    pel = {}
    tr = tr.sort_values(["tx", "li"])
    for (txh, tok), d in tr.groupby(["tx", "token"], sort=False):
        jual = [a for a in d.dari if a not in lewat]          # Transfer PERTAMA dari bukan-pool = penjual
        beli = [a for a in d.ke if a not in lewat]            # Transfer TERAKHIR ke bukan-pool = pembeli
        pel[(txh, tok)] = (jual[0] if jual else "", beli[-1] if beli else "")
    sw["penjual_tx"] = [pel.get((a, b), ("", ""))[0] for a, b in zip(sw.tx, sw.aset)]
    sw["pembeli_tx"] = [pel.get((a, b), ("", ""))[1] for a, b in zip(sw.tx, sw.aset)]
    sw["pelaku"] = np.where(sw.usd > 0, sw.penjual_tx, sw.pembeli_tx)
    sw["pelaku"] = np.where(sw.pelaku == "", sw.recipient, sw.pelaku)
    sw["grup"] = sw.pelaku.isin(G) | sw.sender.isin(G) | sw.recipient.isin(G)
    sw["pnl_vs_tebus"] = sw.usd + sw.qty * sw.acuan * 0.99
    sw["via_router"] = sw.pelaku.isin(ROUTER_ARC)
    return sw


def lawan2(sampai: str = "2026-09-16 06:00") -> dict:
    sw = pelaku_tx(sampai)
    pra = sw[sw.t < pd.Timestamp("2026-09-15 22:00", tz="UTC")]
    agg = pra.groupby(["nama", "pelaku"]).agg(
        grup=("grup", "max"), router=("via_router", "max"), n=("usd", "size"), n_jual=("usd", lambda v: (v > 0).sum()),
        usdc_bersih=("usd", "sum"), qty_bersih=("qty", "sum"), pnl_vs_tebus=("pnl_vs_tebus", "sum"),
        vol=("usd", lambda v: v.abs().sum()), t0=("t", "min"), t1=("t", "max")).reset_index()
    lg = log_token()
    mint = lg[lg.t0 == T_MINT].assign(ke="0x" + lg.t2.str[-40:], v=lambda d: d.data.map(lambda h: int(h[:66], 16) / 1e18))
    red = lg[lg.t0 == T_REDEEM].assign(dari="0x" + lg.t2.str[-40:], v=lambda d: d.data.map(lambda h: int(h[:66], 16) / 1e18))
    nm2tok = {v[0]: a for a, v in ASET_NILAI.items()}
    agg["mint"] = [mint[(mint.token == nm2tok[n]) & (mint.ke == a)].v.sum() for n, a in zip(agg.nama, agg.pelaku)]
    agg["tebus"] = [red[(red.token == nm2tok[n]) & (red.dari == a)].v.sum() for n, a in zip(agg.nama, agg.pelaku)]
    agg = agg.sort_values("pnl_vs_tebus")
    agg.to_parquet(ARB / "arc_lawan_pelaku.parquet")
    return {"pelaku": agg, "swap": sw, "perantara": sorted(ROUTER_ARC)}


# ---------------------------------------------------------------- jembatan Robinhood Chain <-> Arc
# Ditemukan 9 Okt 2026: "• Arc Token" = jembatan KUSTODIAN milik OWNER 0xb053c334 (keeper 0x0d8e72ec di KEDUA chain).
# Robinhood: user deposit(uint256) token resmi Robinhood ke vault -> event Deposit(id, user, net, fee 1%, nonce) ->
# keeper mint(user, net, id) di Arc (event Minted(id, to, amount)). Arc: redeem(amount, to) membakar -> Redeemed(id,
# from, to, amount) -> keeper memanggil vault.release(to, amount, id) di Robinhood -> Release(id, to, net, fee 1%).
T_DEP = "0x5fc9fc2f3a33277b43b33ac226b81a5f87f8e5f2e3b36aef009852b310ddd37e"
T_REL = "0xbaa21fb6000fbb6d014fac9cd1b0726799e6f352a967157a59f4b2da8ef32211"
T_MINT = "0x1a49076e0e8c733171c5360d78c9ae8e19fef5a0720b926e72f78b7cc37618cd"
T_REDEEM = "0xaa7dc873a7d37b94883eae5b185beafe0223de340014bc7a1690496363d5bb28"
VAULT_RH = ["0x98529fe38feaf705bc692ac5808d4620c11c7c21", "0x0365a1b0443af59bc137d0c12695b96b5a11aaa8",
            "0x4824f0a37bdf7cc4867b91ea4cb4cb8c8d4cfc55", "0xa6a0e713a311b6ddb31c92949e87cf6ddf27c9fd",
            "0x304f455664fe6c58fca02f86600ec9c0deaba135", "0xf24b3e387b545874763298122d6bd57a26ddde50",
            "0x64fc24b117f0a8f9dc718951ab6eaf34f92b7a0b", "0x7972373c3ee70551d65baef8f55a2ad9a20afcf4",
            "0xaeb17c341262565d285eaed0d4974836ad548eda", "0x4d1efa7f5629f89fbdd7950b5ef73403a350ad59",
            "0x3943a8a80c85602f255fb8ebde7f213ea2873d8a", "0xe5f79c5ec5566fd10b5179203084c699b01d0985",
            "0x4a8d7dadc03b6b907e42cc2149428a47d902a555", "0xfc7521d54c4028cbb2959762f303570aa70d56df"]
RH_MULAI = 50_000_000   # ±31 Agu 2026 (blok Robinhood ±0,102 dtk); token Arc pertama (NVDA) dibuat ±1 Sep


def jembatan_rh() -> pd.DataFrame:
    """Event Deposit/Release semua vault Robinhood (filter alamat, 100 rb blok/permintaan), disimpan per bagian."""
    f = ARB / "robinhood_jembatan_log.parquet"
    if f.exists():
        return pd.read_parquet(f)
    top = A.head("robinhood")
    parts = ARB / "robinhood_jembatan_parts"
    parts.mkdir(exist_ok=True)
    B = 2_000_000

    def dek(x):
        t = x["topics"]
        return {"vault": x["address"].lower(), "blok": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16),
                "tx": x["transactionHash"], "t0": t[0], "id": t[1] if len(t) > 1 else "",
                "user": _addr(t[2]) if len(t) > 2 else "", "data": x["data"]}

    for k, c in enumerate(range(RH_MULAI, top + 1, B)):
        fp = parts / f"p_{k:04d}.parquet"
        if fp.exists():
            continue
        c1 = min(c + B - 1, top)
        rows = A.scan("robinhood", {"address": VAULT_RH}, c, c1, 100_000, par=4, label=f"jembatan {k}", fn=dek)
        pd.DataFrame(rows, columns=["vault", "blok", "li", "tx", "t0", "id", "user", "data"]).to_parquet(
            fp, compression="zstd")
        print(f"  jembatan bagian {k}: blok {c:,}-{c1:,}: {len(rows):,} log", flush=True)
    df = pd.concat([pd.read_parquet(p) for p in sorted(parts.glob("p_*.parquet"))], ignore_index=True)
    df = df.drop_duplicates(["tx", "li"]).sort_values(["blok", "li"]).reset_index(drop=True)
    w = df.data.str[2:]
    df["net"] = [int(x[0:64], 16) / 1e18 if len(x) >= 64 else np.nan for x in w]
    df["fee"] = [int(x[64:128], 16) / 1e18 if len(x) >= 128 else np.nan for x in w]
    df["jenis"] = df.t0.map({T_DEP: "deposit", T_REL: "release"}).fillna("lain")
    df.to_parquet(f, compression="zstd")
    print(f"jembatan: {len(df):,} log -> {f}")
    print(df.groupby(["vault", "jenis"]).agg(n=("net", "size"), net=("net", "sum")).to_string())
    return df


VAULT_TOKEN = {"0xaeb17c341262565d285eaed0d4974836ad548eda": "CRCL•Arc", "0xf24b3e387b545874763298122d6bd57a26ddde50":
               "WETH•Arc", "0x3943a8a80c85602f255fb8ebde7f213ea2873d8a": "NVDA•Arc"}   # dicocokkan via id event


def _rh_waktu(bloks) -> pd.DatetimeIndex:
    f = ARB / "robinhood_blok_sampel.parquet"
    if f.exists():
        s_ = pd.read_parquet(f)["ts"]
    else:
        want = list(range(RH_MULAI, A.head("robinhood"), 250_000))
        with ThreadPoolExecutor(4) as ex:
            ts = list(ex.map(lambda b: int(rpc("robinhood", "eth_getBlockByNumber", [hex(b), False])["timestamp"], 16),
                             want))
        s_ = pd.Series(ts, index=want, dtype="int64")
        s_.to_frame("ts").to_parquet(f)
    return ke_waktu(np.asarray(bloks, dtype=float), s_)


def jembatan_cocok() -> dict:
    """Pasangkan Minted(Arc)<->Deposit(RH) dan Redeemed(Arc)<->Release(RH) lewat id; jeda, biaya, saldo vault."""
    rh = jembatan_rh()
    rh = rh[rh.vault.isin(VAULT_TOKEN)].copy()
    rh["sym"] = rh.vault.map(VAULT_TOKEN)
    rh["t_rh"] = _rh_waktu(rh.blok)
    lg = log_token()
    lg = lg[lg.t0.isin([T_MINT, T_REDEEM])].copy()
    lg["sym"] = lg.token.map(lambda a: A.TOK_ARC[a][0])
    lg["t_arc"] = waktu(lg.blok)
    lg["jumlah"] = lg.data.map(lambda h: int(h[2:66], 16) / 1e18)
    lg["alamat"] = np.where(lg.t0 == T_MINT, "0x" + lg.t2.str[-40:], "0x" + lg.t2.str[-40:])
    lg["tujuan"] = np.where(lg.t0 == T_REDEEM, "0x" + lg.t3.str[-40:], "")
    mint = lg[lg.t0 == T_MINT].merge(rh[rh.jenis == "deposit"][["id", "t_rh", "user", "net", "fee", "blok"]],
                                     left_on="t1", right_on="id", how="left", suffixes=("", "_rh"))
    mint["jeda_dtk"] = (mint.t_arc - mint.t_rh).dt.total_seconds()
    red = lg[lg.t0 == T_REDEEM].merge(rh[rh.jenis == "release"][["id", "t_rh", "user", "net", "fee", "blok", "tx"]],
                                      left_on="t1", right_on="id", how="left", suffixes=("", "_rh"))
    red["jeda_dtk"] = (red.t_rh - red.t_arc).dt.total_seconds()
    ring = []
    for nm, d in (("mint<-deposit RH", mint), ("redeem->release RH", red)):
        for sym, x in d.groupby("sym"):
            ring.append({"arah": nm, "sym": sym, "n_arc": len(x), "cocok_rh": int(x.net.notna().sum()),
                         "jumlah_arc": x.jumlah.sum(), "net_rh": x.net.sum(), "fee_rh": x.fee.sum(),
                         "fee_pct_med": float(np.nanmedian(x.fee / (x.net + x.fee))) if x.net.notna().any() else np.nan,
                         "jeda_med_dtk": float(np.nanmedian(x.jeda_dtk)), "jeda_p90_dtk": float(np.nanpercentile(
                             x.jeda_dtk.dropna(), 90)) if x.jeda_dtk.notna().any() else np.nan,
                         "alamat_unik": x.alamat.nunique(), "t0": x.t_arc.min(), "t1": x.t_arc.max()})
    ring = pd.DataFrame(ring)
    mint.drop(columns=["data"]).to_parquet(ARB / "arc_jembatan_mint.parquet")
    red.drop(columns=["data"]).to_parquet(ARB / "arc_jembatan_tebus.parquet")
    return {"ringkas": ring, "mint": mint, "tebus": red}


# ---------------------------------------------------------------- laporan
def _f(x, d: int = 0) -> str:
    """Format angka gaya Indonesia: 1.234,5"""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "-"
    t = f"{x:,.{d}f}"
    return t.replace(",", "_").replace(".", ",").replace("_", ".")


def _pct(x, d: int = 0) -> str:
    return "-" if x is None or not np.isfinite(x) else _f(100 * x, d) + "%"


MULAI_TANDA, AKHIR_TANDA = "=== ARC (TUGAS A): MULAI ===", "=== ARC (TUGAS A): SELESAI ==="


def laporan() -> str:
    L: list[str] = []
    w = L.append
    w(MULAI_TANDA)
    w("Bot screenshot 'wetharb' & 'circarb' di Arc — dibuat 9 Okt 2026 oleh research/arb_arc.py (lanjutan arb_cari.py)")
    w("Periode data: blok Arc s.d. 25.007.986 (±9 Okt 2026 03:30 UTC); acuan ETH/BTC/EUR = Binance 1 mnt s.d. 8 Okt;")
    w("CRCL/NVDA = NYSE 1 mnt (Twelve Data) s.d. 7 Okt, di luar jam bursa dipakai close terakhir (ditandai 'basi').")
    w("Pembagian waktu: PRA-PUBLIK (1-15 Sep 2026, Arc masih izin terbatas) vs PASCA-PUBLIK (16 Sep - 8 Okt).")
    w("Semua angka USD = USDC. Hanya baca RPC (eth_getLogs/eth_call/getBlock/receipt) — tanpa transaksi.")
    w("")
    # ---- A1
    ly = pd.read_parquet(ARB / "arc_layar.parquet")
    w("A1. PENCOCOKAN SCREENSHOT — 21/21 baris cocok PERSIS (jumlah USDC 4 desimal + aset 8/6 digit), 20/21 menit sama;")
    w("    1 baris (SELL 0,573879 CRCL) on-chain 19:16:40 WIB vs layar 19:17 (notifikasi Telegram terkirim setelah blok).")
    lay_c = ly[ly.bot == "circarb"]
    lay_w = ly[ly.bot == "wetharb"]
    w(f"    => circarb = SABTU 12 Sep 2026 ({lay_c.wib.min():%H:%M}-{lay_c.wib.max():%H:%M} WIB = "
      f"{lay_c.utc.min():%H:%M}-{lay_c.utc.max():%H:%M} UTC); wetharb = MINGGU 13 Sep 2026 "
      f"({lay_w.wib.min():%H:%M}-{lay_w.wib.max():%H:%M} WIB). Keduanya 3-4 hari SEBELUM mainnet publik.")
    w("    Pool: WETH = v3-fork 0x7a5de3ed…5d8c (USDC/WETH•Arc, fee 1%, pabrik 0xf0db7b58); CRCL = 0x2e8180fa…ba (CRCL•Arc/USDC,")
    w("    fee 1%). Kontrak bot: wetharb 0xa25790ec…62b1 (owner E1 0x673250c6…6886), circarb 0xcdfe8dab…8551 (owner E2")
    w("    0x7cff8a2b…87db). Fungsi bot: buy(usdcIn,minOut) 0xd6febde8 / sell(amountIn,minUsdcOut) 0xd79875eb langsung ke pool.")
    w("    Acuan: ETH Binance menit yg sama; CRCL = close NYSE Jumat 11 Sep $90,63 (akhir pekan, bursa tutup).")
    w(f"    {'tgl':5} {'WIB':8} {'UTC':8} {'bot':7} {'arah':4} {'USDC':>8} {'aset':>11} {'harga':>8} {'acuan':>8} {'vs':>6} "
      f"{'batas':>8} tx")
    for r in ly.itertuples():
        w(f"    {r.wib:%d-%m} {r.wib:%H:%M:%S} {r.utc:%H:%M:%S} {r.bot:7} {r.arah:4} {_f(r.usd, 4):>8} {_f(r.aset, 6 if r.bot == 'circarb' else 8):>11} "
          f"{_f(r.harga, 2):>8} {_f(r.acuan, 2):>8} {_pct(r.vs_acuan):>6} {(_f(r.batas, 1) if np.isfinite(r.batas) else 'tanpa'):>8} {r.tx[:14]}…")
    w("    'batas' = harga maksimum (BUY, dari minOut) / minimum (SELL, dari minUsdcOut) yang dikirim bot pada tx itu.")
    w("")
    # ---- A2
    pb = pd.read_parquet(ARB / "arc_grup_pnl_bot.parquet")
    bk = pd.read_parquet(ARB / "arc_grup_buku.parquet")
    w("A2. UNTUNG-RUGI GRUP (E1 + E2 + 8 kontrak bot), 6-16 Sep 2026 — SELURUHNYA PRA-PUBLIK; 0 trade token ini sejak")
    w("    16 Sep 00:52 UTC. Putaran = satu tx jual dipasangkan FIFO dengan beli terdahulu bot yang sama (USDC).")
    w(f"    {'bot':17} {'token':9} {'beli':>4} {'jual':>4} {'putaran':>7} {'WR':>5} {'untung FIFO':>11} {'sisa qty':>9} "
      f"{'biaya sisa':>10} {'nilai sisa*':>11} {'modal maks':>10} {'beli vs acuan':>13} {'jual vs acuan':>13} aktif (UTC)")
    for r in pb.itertuples():
        w(f"    {r.bot:17} {r.sym:9} {r.n_beli:>4} {r.n_jual:>4} {r.putaran:>7} {_pct(r.wr_putaran):>5} {_f(r.untung_fifo, 0):>11} "
          f"{_f(r.sisa_qty, 4):>9} {_f(r.sisa_biaya, 0):>10} {_f(r.sisa_nilai_acuan_8okt, 0):>11} {_f(r.modal_maks, 0):>10} "
          f"{_pct(r.beli_vs_acuan_med):>13} {_pct(r.jual_vs_acuan_med):>13} {r.mulai:%d/%m %H:%M}-{r.selesai:%d/%m %H:%M}")
    w("    * nilai sisa = sisa lot FIFO x acuan 8 Okt x 0,99 (biaya tebus 1%). Sisa itu TIDAK disimpan: lihat buku besar.")
    w(f"    Total untung FIFO (putaran tertutup): ${_f(pb.untung_fifo.sum(), 0)}; WR putaran gabungan "
      f"{_pct((pd.read_parquet(ARB / 'arc_grup_putaran.parquet').query('qty_tertutup > 0').untung > 0).mean())}; "
      f"modal USDC per bot maks ${_f(pb.modal_maks.max(), 0)} (jumlah semua bot ${_f(pb.modal_maks.sum(), 0)}).")
    w("    Dompet induk 0x7821f1d9 (EOA; nonce Arc 602, Base 2.509, BSC 963, Robinhood 654, Ethereum 110) mendanai E1 (blok")
    w("    19.447.015: 4 USDC + 0,045 NVDA) lalu E2 (lewat E1). Kemungkinan satu operator; cerita pengguna (0,45 ETH, $1.100) cocok")
    w("    persis dengan E1 — tetapi kepemilikan dompet TIDAK bisa dibuktikan dari data chain.")
    w("    Bot NVDA menjual stok NVDA•Arc yang DIKIRIM dompet induk 0x7821f1d9 (hasil deposit jembatan) — 'jual tanpa beli'")
    w(f"    {_f(pb.jual_tanpa_beli_qty.sum(), 2)} token = ${_f(pb.jual_tanpa_beli_usdc.sum(), 0)}, dihitung di buku besar pada nilai acuan.")
    w("")
    w("    Buku besar per token (seluruh grup; transfer antar-anggota diabaikan; token dinilai acuan saat kejadian):")
    w(f"    {'token':9} {'kas pool':>9} {'kas LP':>7} {'masuk luar':>10} {'keluar luar':>11} {'ditebus net':>11} {'saldo 8/10':>10} {'UNTUNG':>8}")
    for r in bk.itertuples():
        w(f"    {r.sym:9} {_f(r.kas_pool):>9} {_f(r.kas_lp):>7} {_f(-r.nilai_masuk_luar):>10} {_f(r.nilai_keluar_luar):>11} "
          f"{_f(r.nilai_ditebus_net):>11} {_f(r.nilai_saldo_8okt):>10} {_f(r.untung_termasuk_aset):>8}")
    tot = bk.untung_termasuk_aset.sum()
    w(f"    TOTAL grup ≈ ${_f(tot)} dalam 10 hari aktif (6-16 Sep) ≈ ${_f(tot / 10)}/hari; kas USDC murni ${_f((bk.kas_pool + bk.kas_lp).sum())}.")
    w("    masuk luar = token diterima dari luar grup (hampir semua dari 0x7821f1d9) dinilai acuan/0,99 (biaya jembatan);")
    w("    keluar luar = dikirim ke luar grup (ke 0x7821f1d9) dinilai acuan x 0,99; ditebus = redeem x acuan x 0,99.")
    w("    Cek jumlah token: pool + LP + masuk - keluar - ditebus - saldo = 0 (selisih < 0,003 token).")
    w("    Harian (USD, kumulatif): 6 Sep -162 | 7 Sep -108 | 8 Sep +917 | 9 Sep +1.085 | 10 Sep +994 | 11 Sep +1.878 | 12 Sep +2.399")
    w("    | 13 Sep +3.059 | 14 Sep +6.624 (tebus 0,45+0,275 WETH) | 15 Sep +7.196 | 16 Sep +7.502 (+LP $98 = total di atas).")
    w("    Mulai untung: bot NVDA E1 awal 6 Sep 15:17 UTC; wetharb 13 Sep 12:46; puncak & berhenti 15-16 Sep. Setelah 16 Sep")
    w("    tidak ada trade lagi (lihat A5). Junk token E1 (DUM, ARCT, bunfi; bikin/tarik LP sendiri) ±$52 — diabaikan.")
    w("")
    # ---- A3
    jb = jembatan_cocok_cache()
    w("A3. JALUR KELUAR = JEMBATAN KUSTODIAN ROBINHOOD CHAIN <-> ARC (TERBUKTI on-chain)")
    w("    Token 'WETH' 0xd02d2b38, 'CRCL • Arc Token' 0x2ba0f44b, 'NVIDIA • Arc Token' 0x65055065: kode identik, owner EOA")
    w("    0xb053c334…dfd8, keeper EOA 0x0d8e72ec…671a (nonce Arc 13.468, Robinhood 10.870). Fungsi: mint(address,uint256,")
    w("    bytes32) hanya keeper; redeem(uint256 jumlah, address tujuan) oleh pemegang = BAKAR + event Redeemed(id, dari, tujuan,")
    w("    jumlah); maxSupply, pause. Pasangannya di Robinhood: vault per token (CRCL 0xaeb17c34…, WETH 0xf24b3e38…, NVDA")
    w("    0x3943a8a8…; owner & keeper SAMA) — deposit(uint256) token resmi Robinhood -> event Deposit(id, user, net, fee 1%)")
    w("    -> keeper mint di Arc dengan id yang sama; redeem di Arc -> keeper memanggil release(tujuan, jumlah, id) di vault ->")
    w("    event Release(id, tujuan, net, fee 1%) dan token resmi Robinhood (CRCL 0xdf0992e4, NVDA 0xd0601ce1, WETH->ETH) dikirim.")
    w(f"    {'arah':20} {'token':9} {'n Arc':>6} {'cocok RH':>8} {'jumlah':>10} {'fee':>7} {'fee%':>5} {'jeda med':>8} {'p90':>8} alamat")
    for r in jb.itertuples():
        w(f"    {r.arah:20} {r.sym:9} {r.n_arc:>6} {r.cocok_rh:>8} {_f(r.jumlah_arc, 2):>10} {_f(r.fee_rh, 2):>7} {_pct(r.fee_pct_med, 1):>5} "
          f"{_f(r.jeda_med_dtk):>6} s {_f(r.jeda_p90_dtk):>6} s {r.alamat_unik}")
    w("    100% event Arc punya pasangan di Robinhood (id sama). Jadi token ini DAPAT DITEBUS 1:1 dikurangi 1% (+gas, ±2 mnt).")
    w("    Bukti grup: E1 redeem 0,45 WETH•Arc 14 Sep 00:48:55 UTC (Arc blok 20.737.658, id 0x4849670c…) -> Robinhood blok")
    w("    62.395.685 00:51:03 UTC: vault 0xf24b3e38 release 0,4455 ETH (+fee 0,0045) ke E1 (tx 0x58f93cbf…; WETH dibakar/unwrap,")
    w("    ETH asli dikirim). ETH saat itu $2.484,91 -> 0,4455 ETH ≈ $1.107 = COCOK dengan cerita pengguna 'WETH modal $6 dapat")
    w("    0,45 ETH (untung $1.100)'. Sumbernya: 14 Sep 00:34:32 UTC (07:34 WIB) wetharb membeli 0,441213 WETH•Arc seharga 3 USDC")
    w("    (tx 0x1c691152…, harga $6,80/WETH = -99,7% vs ETH), 1 blok (0,5 dtk) setelah 0xed65d422 menjual 0,999 WETH•Arc seharga")
    w("    $76,56. Total tebusan E1: 6x = 0,94168 WETH -> 0,93226 ETH di Robinhood; E2 1x 3,6725 CRCL•Arc -> 3,6358 CRCL Robinhood")
    w("    (15 Sep 23:24 UTC, release 23 mnt kemudian). Dompet induk 0x7821f1d9 (pendana E1/E2) juga memakai jembatan: 20x deposit")
    w("    NVDA/CRCL/WETH ke Arc (stok yang dijual bot NVDA) dan 13x tebus. Saldo token Robinhood E1/E2 kini 0 (sudah dipindah;")
    w("    tujuan akhir tidak bisa dilacak: RPC Robinhood tanpa arsip, tanpa indeks alamat). Ethereum/Base/Arbitrum/OP: E1/E2 nonce")
    w("    0 (Base E1 2) — tidak ada jejak jembatan ke sana. RISIKO: kustodian satu EOA (owner/keeper) — bisa pause/tidak membayar.")
    w("")
    # ---- A4
    w("A4. PIHAK LAWAN (pra-publik, 3 pool bot; pelaku dari log Transfer token pada tx yang sama)")
    ll = pd.read_parquet(ARB / "arc_lawan_langsung.parquet")
    w(f"    Penjual tepat SEBELUM beli grup (<= 120 blok): {len(ll)} jualan, rugi mereka vs nilai tebus (qty x acuan x 0,99 - USDC):")
    for nm, x in ll.groupby("nama"):
        w(f"      {nm:24} {len(x):>4} jualan, rugi ${_f(x.rugi_penjual.sum())}, jeda median {_f(x.jeda_blok.median())} blok, "
          f"{_pct(x.router.mean())} lewat router/agregator (pelaku asli tak terlihat)")
    w("    Contoh (WETH): 0xed65d422 (EOA, deposit 4,5 WETH lewat jembatan) jual 0,999 WETH = $76,56 (-96,9%); 0x69c4deaa jual")
    w("    1,26 WETH = $110,86 (-96,5%); 0xa144ca08 (deposit 1,782 WETH) jual 1,782 WETH = $120,25 (-97,2%) 16 Sep 00:50 UTC.")
    lp = pd.read_parquet(ARB / "arc_lawan_pelaku.parquet")
    jual = lp[~lp.router & ~lp.grup].sort_values("pnl_vs_tebus").head(8)
    w("    Penjual bersih terbesar (bukan router), rugi vs tebus:")
    for r in jual.itertuples():
        w(f"      {r.pelaku[:10]}… {r.nama[:8]} jual bersih {_f(-r.qty_bersih, 2)} token -> ${_f(r.usdc_bersih)}; rugi ${_f(-r.pnl_vs_tebus)}; "
          f"mint jembatan sendiri {_f(r.mint, 1)}")
    beli = lp[~lp.router & ~lp.grup].sort_values("pnl_vs_tebus", ascending=False).head(5)
    w("    Pemenang terbesar (pesaing grup — beli murah lalu redeem):")
    for r in beli.itertuples():
        w(f"      {r.pelaku[:10]}… {r.nama[:8]} beli bersih {_f(r.qty_bersih, 1)} token, untung vs tebus ${_f(r.pnl_vs_tebus)}, ditebus {_f(r.tebus, 1)}")
    g_ = lp[lp.grup].pnl_vs_tebus.sum()
    w(f"    Bagian grup di pasar pra-publik ±${_f(g_)} (vs tebus) dari volume CRCL $2,54 jt / NVDA $165 rb / WETH $29 rb —")
    w("    grup KECIL; pemain terbesar 0x4663f735 (EOA, +$90 rb vs tebus, 1.496 CRCL ditebus).")
    w("    POLA: (1) penjual 'naif' yang menjembatani WETH/CRCL dari Robinhood lalu market-sell sekaligus di pool tipis (USDC")
    w("    ±$1-100 per 2% gerak) -> rugi 50-97%; (2) dompet distributor: 0x5107a9bc deposit 3.241 CRCL, kirim 1.539 ke 0x47ae7042")
    w("    yang menjual 1.146 CRCL @ ±$40 (-58%, rugi ±$61 rb); (3) banyak alamat kecil (4.142 penerima mint CRCL, mint 0,0099)")
    w("    = pola pemburu airdrop/aktivitas pra-publik yang butuh USDC (gas Arc = USDC). Tidak ada bukti faucet/airdrop token")
    w("    dari penerbit: semua pasokan = mint jembatan yang dibayar deposit token asli di Robinhood.")
    w("")
    # ---- A5
    w("A5. STRATEGI PERSIS (dari argumen tx bot + jejak swap)")
    w("    Inti: 'beli diskon, tebus penuh' — beli token jembatan di pool Arc saat harga jauh di bawah acuan, tebus 1:1 (-1%)")
    w("    ke Robinhood (aset asli bernilai penuh); sisi lain: jual stok (hasil deposit jembatan) saat harga Arc ≈/di atas acuan.")
    w("    wetharb (E1): BUY 3 USDC per tx; bila 3 USDC berikutnya melewati batas, pecahan DIBAGI DUA (1,5 / 0,75 / 0,375) supaya")
    w("    berhenti tepat di batas. Batas beli median $795/WETH (5-95%: $562-1.000; tertinggi $1.000 ≈ 40% harga ETH), slippage")
    w("    ±1,7% dari kuotasi. SELL kecil (8x) hanya bila harga ≥ $1.500-2.000 (≈ 61-81% ETH). 137 beli, jeda dalam burst ±11 dtk.")
    w("    circarb (E2): BUY 20 USDC (juga 25/30/10/12,5), batas $40-45/CRCL (≈ 44-50% NYSE), 27 beli TANPA batas (minOut 0);")
    w("    SELL ≥ $52-65 (median $59 ≈ 65% NYSE), ukuran ±0,3-0,7 CRCL. 165 beli / 84 jual, jeda dalam burst ±6 dtk.")
    w("    Bot lain: NVDA E1/E2 beli 10 USDC (5/15) di -49…-55% dan jual stok di ≈ acuan (median +1% / -17%); CRCL E1 10 USDC;")
    w("    E2 #3 WETH 2,5 USDC. Semua swap langsung ke pool v3 (callback), tanpa router; owner EOA memanggil buy/sell.")
    w("    Kenapa berhenti 16 Sep: mainnet publik dibuka ±15 Sep 22:00 UTC; per jam volume CRCL naik $1-20 rb -> $230-600 rb,")
    w("    pelaku 5-10 -> 100+; harga melonjak dari -50% ke premi (+40% CRCL, +135% NVDA jam 00 UTC 16 Sep) lalu ±3% dari acuan")
    w("    sejak ±05:00 UTC. Sejak 16 Sep 06:00 hanya 5 swap WETH ($58) & 5 swap CRCL ($0,02) yang di bawah batas beli bot; NVDA 0")
    w("    -> aturan bot tidak pernah terpicu lagi; E1 menebus sisa WETH 16 Sep 00:55.")
    w("")
    # ---- A6
    jp = pd.read_parquet(ARB / "arc_jendela_pool.parquet")
    ep = pd.read_parquet(ARB / "arc_jendela_episode.parquet")
    w("A6. JENDELA LAIN DI ARC SEJAK PUBLIK (16 Sep - 8 Okt): swap BELI yang tereksekusi ≥ 5% di bawah acuan (harga eksekusi,")
    w("    sudah termasuk fee pool), untung kasar = qty x acuan x (1 - biaya tebus 1% utk token jembatan) - USDC dibayar.")
    w("    Aset: WETH•Arc/CRCL•Arc/NVDA•Arc (jembatan), WETH_b (penerbit tdk jelas), cirBTC & EURC resmi Circle.")
    w("    Hasil per periode (n swap, USDC, untung kasar SEMUA pelaku):")
    w("      sejak 16 Sep 00:00: WETH•Arc 1.534 / $28,3 rb / $15,3 rb; NVDA•Arc 435 / $10,6 rb / $6,0 rb; CRCL•Arc 259 / $16,2 rb")
    w("                          / $1,8 rb (acuan saham BASI di luar jam bursa); cirBTC 3 / $2,5 / $0,6; WETH_b 3 / $10 / $22.")
    w("      sejak 17 Sep:       WETH•Arc 305 / $5,4 rb / $769; CRCL 81 / $9,4 rb / $552 (25 Sep 23:27 UTC, setelah bursa tutup);")
    w("                          NVDA 30 / $1,3 rb / $109.")
    w("      sejak 20 Sep:       WETH•Arc 111 / $958 / $391 (11 hari); NVDA 30 / $1,3 rb / $109; CRCL ≈ $551 (episode 25 Sep).")
    w("      sejak 1 Okt:        WETH•Arc 36 / $134 / $62; NVDA 28 / $1,2 rb / $103 (2 Okt 16:15 UTC jam bursa, 26 swap $1.005 -> $65).")
    w("    Hari pertama publik saja (16 Sep) = 70-98% dari seluruh peluang pasca-publik (WETH 95%, NVDA 98%, CRCL 70%);")
    w("    diambil oleh ≥ 45-60 alamat penerima per token (sebagian router) — persaingan bot sangat ramai.")
    w("    Arah sebaliknya (JUAL ≥ 5% DI ATAS acuan; deposit jembatan lalu jual): 16 Sep 00-06 UTC CRCL $840 rb (untung vs acuan")
    w("    basi ±$151 rb), NVDA $179 rb (±$52 rb) — FOMO pembukaan; setelah 16 Sep 06:00: CRCL $1,1 rb (+$85), NVDA $75 rb (+$9 rb,")
    w("    hampir semua 16 Sep), sejak 17 Sep ≈ $0-0,1 rb.")
    w("    Pool masih aktif (≥ 10 swap sejak 16 Sep, swap terakhir ≥ 1 Okt) dengan harga MID ≤ -5% paling lama. Pool WETH•Arc")
    w("    utama 0x7a5de3 memang sering diskon, tetapi kedalamannya ±$1 per 2% gerak harga (potret 8 Okt, arc_potret_weth) ->")
    w("    hanya receh yang bisa diambil. Pool fee tinggi/dinamis tidak bisa diarbitrase. (Pool yang tidak di-swap lagi,")
    w("    mis. cirBTC sejak 16 Sep, tampak 'diskon' hanya karena harga mid basi -> diabaikan.) Angka swap/untung di bawah =")
    w("    sejak 16 Sep 00:00, sebagian besar terjadi di hari pembukaan.")
    akhir = pd.read_parquet(ARB / "arc_swap_aset.parquet", columns=["id", "t"]).groupby("id").t.max()
    jp = jp.assign(swap_terakhir=jp.pool.map(akhir))
    top = jp[(jp.swap_sejak >= 10) & (jp.swap_terakhir >= pd.Timestamp("2026-10-01", tz="UTC"))]
    top = top.sort_values("menit_diskon", ascending=False).head(5)
    for r in top.itertuples():
        fee_s = "dinamis" if r.fee >= 0x800000 else _f(r.fee / 1e4, 2) + "%"
        w(f"      {r.aset[:26]:26} {r.pool[:12]}… fee {fee_s} menit diskon {_f(r.menit_diskon)} / {_f(r.menit_ada_harga)}, "
          f"swap beli diskon {r.beli_diskon_n} = ${_f(r.beli_diskon_usd)} (untung ${_f(r.beli_diskon_untung)})")
    big = ep.sort_values("untung_kasar", ascending=False)
    big = big[big.mulai >= pd.Timestamp("2026-09-17", tz="UTC")].head(5)
    w("    Episode terbesar sejak 17 Sep (durasi, untung kasar semua pelaku):")
    for r in big.itertuples():
        w(f"      {r.aset[:22]:22} {r.mulai:%d/%m %H:%M}-{r.selesai:%d/%m %H:%M} UTC {r.menit} mnt, beli diskon {r.beli_diskon_n} = "
          f"${_f(r.beli_diskon_usd)}, untung ${_f(r.untung_kasar)} (dev median {_pct(r.dev_med)})")
    w("    Harian median selisih eksekusi vs acuan (semua pool): WETH•Arc -1,6…-9,5% (pool kecil fee tinggi), CRCL/NVDA ±2%,")
    w("    cirBTC/EURC/WETH_b ±0,2%. Tidak ada pool aset bernilai yang diperdagangkan dengan diskon ≥ 5% DAN likuid sejak 17 Sep.")
    w("")
    w("KESIMPULAN ARC: screenshot = 12-13 Sep 2026 (pra-publik). Untung grup ±$7,6 rb (dinilai acuan) / 10 hari dengan modal USDC")
    w("±$40-180 per bot + stok NVDA/CRCL ±$5 rb dari dompet induk; sumber untung = token jembatan dijual 50-97% di bawah nilai")
    w("tebus oleh penjual naif di pool sangat tipis + tebus 1:1 lewat jembatan kustodian. Jendela itu TUTUP saat mainnet publik")
    w("(±15 Sep 22:00 UTC - 16 Sep 05:00 UTC); sesudahnya sisa peluang ≈ $20-65/hari untuk SEMUA pelaku (17 Sep-8 Okt $65/hari,")
    w("sejak 1 Okt $21/hari), dibagi banyak bot. Mengulang strategi ini")
    w("hanya masuk akal di chain/jembatan BARU yang masih pra-publik — dengan risiko kustodian (EOA tunggal), tebusan bisa dihentikan,")
    w("pool tanpa likuiditas, dan persaingan bot (pesaing terbesar mengambil ±13x untung grup).")
    w(AKHIR_TANDA)
    return "\n".join(L)


def jembatan_cocok_cache() -> pd.DataFrame:
    mint = pd.read_parquet(ARB / "arc_jembatan_mint.parquet")
    red = pd.read_parquet(ARB / "arc_jembatan_tebus.parquet")
    ring = []
    for nm, d in (("mint<-deposit RH", mint), ("redeem->release RH", red)):
        for sym, x in d.groupby("sym"):
            ring.append({"arah": nm, "sym": sym, "n_arc": len(x), "cocok_rh": int(x.net.notna().sum()),
                         "jumlah_arc": x.jumlah.sum(), "fee_rh": x.fee.sum(),
                         "fee_pct_med": float(np.nanmedian(x.fee / (x.net + x.fee))),
                         "jeda_med_dtk": float(np.nanmedian(x.jeda_dtk)),
                         "jeda_p90_dtk": float(np.nanpercentile(x.jeda_dtk.dropna(), 90)), "alamat_unik": x.alamat.nunique()})
    return pd.DataFrame(ring)


def tulis_laporan() -> None:
    teks = laporan()
    LAP = A.LAP
    lama = LAP.read_text() if LAP.exists() else ""
    if MULAI_TANDA in lama and AKHIR_TANDA in lama:
        a = lama.index(MULAI_TANDA)
        b = lama.index(AKHIR_TANDA) + len(AKHIR_TANDA)
        baru = lama[:a] + teks + lama[b:]
    else:
        baru = (lama.rstrip() + "\n\n" if lama.strip() else "") + teks + "\n"
    LAP.write_text(baru)
    print(teks)


if __name__ == "__main__":
    tahap = sys.argv[1] if len(sys.argv) > 1 else ""
    if tahap == "log_token":
        log_token()
    elif tahap == "layar":
        pd.set_option("display.width", 250)
        print(layar().to_string())
    elif tahap == "pnl":
        pd.set_option("display.width", 250)
        pd.set_option("display.max_columns", 50)
        r_ = pnl()
        print(r_["per_bot"].T.to_string())
        print(r_["buku"].T.to_string())
        print("modal maks grup (kas USDC kumulatif terdalam):", r_["buku"].attrs.get("modal_maks_grup"))
        print(r_["harian"].round(1).to_string())
    elif tahap == "swap_nvda":
        swap_nvda()
    elif tahap == "jendela":
        pd.set_option("display.width", 250)
        pd.set_option("display.max_columns", 40)
        r_ = jendela()
        print(r_["pool"].head(40).to_string())
        e_ = r_["episode"]
        print(e_.sort_values("untung_kasar", ascending=False).head(30).to_string())
        print(r_["harian"].pivot(index="tgl", columns="nama", values="med").round(3).to_string())
    elif tahap == "lawan":
        pd.set_option("display.width", 250)
        pd.set_option("display.max_columns", 40)
        r_ = lawan()
        print(r_["ringkas"].to_string())
        print(r_["penjual"].head(30).to_string())
        print(r_["pembeli"].head(30).to_string())
    elif tahap == "cocok":
        pd.set_option("display.width", 250)
        pd.set_option("display.max_columns", 40)
        r_ = jembatan_cocok()
        print(r_["ringkas"].to_string())
        G_ = set(A.GRUP) | {DIST}
        for k_ in ("mint", "tebus"):
            x_ = r_[k_]
            print(k_, "grup/DIST:")
            print(x_[x_.alamat.isin(G_)][["sym", "t_arc", "t_rh", "alamat", "jumlah", "net", "fee", "jeda_dtk"]].to_string())
    elif tahap == "lawan2":
        pd.set_option("display.width", 250)
        pd.set_option("display.max_columns", 40)
        r_ = lawan2()
        a_ = r_["pelaku"]
        print("perantara:", r_["perantara"])
        print(a_.head(25).to_string())
        print(a_.tail(25).to_string())
        print(a_.groupby(["nama", "grup"]).agg(n=("pelaku", "size"), pnl=("pnl_vs_tebus", "sum"),
                                               vol=("vol", "sum")).to_string())
    elif tahap == "laporan":
        tulis_laporan()
    elif tahap == "jembatan":
        jembatan_rh()
    elif tahap == "acuan":
        for s_ in ("ETHUSDT", "BTCUSDT", "EURUSDT"):
            print(s_, len(acuan_kripto(s_)))
    elif tahap == "blok":
        s_ = blok_rapat()
        print(len(s_), s_.index.max())
