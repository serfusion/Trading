"""Robinhood Chain — lanjutan research/arb_cari.py (tugas B, 9 Okt 2026) — python -m research.arb_robinhood <tahap>

Agen sebelumnya berhenti di tahap swap Robinhood (tugas 6/15): satu permintaan getLogs menampung ±1 juta swap di
memori (pool WETH/USDG Slipstream/Algebra diarbitrase bot tiap blok) -> proses 3,7 GB lalu terhenti. "0 swap" di
tugas 6/15 = 3 pool v4 dari pabrik lain (0xf5b06e…) yang memang tidak pernah ada swap (bukan galat RPC).
Modul ini melanjutkan TANPA mengubah arb_cari.py (agen Arc menulis file itu):

  swap      sisa pool kandidat (v3/v2/Algebra/Slipstream/Solidly/Aerodrome) per potongan 100 jendela 100 rb blok
            (hemat RAM, bisa dilanjutkan); urutan: (1) kedua token bernilai (resmi), (2) aset resmi + quote lain,
            (3) sisanya. Pool Liquidity Book (LB, 34 pool resmi-resmi) ikut, event Swap LB didekode sendiri.
  waktu     sampel blok -> waktu s/d head (melengkapi chain_baru/onchain/robinhood_blok.parquet, file sendiri)
  acuan     ETH 1 menit Binance 8-9 Okt (melengkapi acuan lama yang berhenti 7 Okt)
  nilai     tiap swap pool kandidat + pool resmi lama dinilai thd acuan (ETH Binance; saham hanya jam NYSE)
  jendela   episode diskon >= 5% di pool BARU beraset bernilai: per pekan, lama bertahan, volume, pengambil
  pecahan   pelaku yang membeli berulang dengan jumlah input sama (pola "wetharb": 3 USDC, 3 USDC, ...)
  grup      jejak E1/E2 (pemilik bot screenshot di Arc) di Robinhood: nonce, kontrak CREATE, transfer token
  potret    potret sekarang (arb_cari.potret / potret_weth / gas_swap_usd)
  lapor     docs/eksternal/hasil_arb_cari_robinhood.txt

HANYA MEMBACA (eth_getLogs, eth_call, eth_blockNumber, eth_getBlockByNumber, eth_getTransactionByHash/Receipt,
eth_getCode, eth_getTransactionCount) + API publik Binance. Tanpa transaksi, tanpa kunci pribadi.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from . import arb_cari as A
from .chain_baru import RH_SAHAM
from .chain_onchain import OUT as ONCHAIN, PM, T3_SWAP, T_SWAP, _addr, _s, _w, rpc

NET = "robinhood"
ARB = A.ARB
SC = Path("/tmp/claude-0/-home-user-Trading/6974bf2f-503e-585e-b51e-7d713b6940e0/scratchpad")
LAP = A.ROOT / "docs" / "eksternal" / "hasil_arb_cari_robinhood.txt"
PARTS = ARB / "robinhood_swap_parts"

WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
ETH = "0x" + "0" * 40
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"
CRCL = RH_SAHAM["CRCL"]
SAHAM = {a: s for s, a in RH_SAHAM.items()}
# token bernilai: alamat -> acuan ("USD" = $1, "ETH" = ETHUSDT Binance, ticker = Twelve Data 1 mnt jam NYSE)
NILAI = {USDG: "USD", WETH: "ETH", ETH: "ETH", **{a: s for a, s in SAHAM.items()}}
T_LB_SWAP = "0xad7d6f97abf51ce18e17a38f4d70e975be9c0708474987bb3e26ad21bd93ca70"
COLS = ["id", "jenis", "blok", "li", "tx", "sender", "recipient", "a0", "a1", "sqrtp", "L"]
JENDELA_PER_FILE = 100


def _dec_lb(lg: dict) -> dict | None:
    """LB Swap(sender, to, id, amountsIn, amountsOut, ...): bytes32 = x (128 bit bawah) | y (128 bit atas)."""
    t, d = lg["topics"], lg["data"]
    try:
        ain, aout = _w(d, 1), _w(d, 2)
        m = (1 << 128) - 1
        return {"id": lg["address"].lower(), "jenis": "lb", "blok": int(lg["blockNumber"], 16),
                "li": int(lg["logIndex"], 16), "tx": lg["transactionHash"], "sender": _addr(t[1]),
                "recipient": _addr(t[2]), "a0": float(aout & m) - float(ain & m),
                "a1": float(aout >> 128) - float(ain >> 128), "sqrtp": np.nan, "L": np.nan}
    except (IndexError, ValueError):
        return None


def _rencana() -> list[tuple[str, list[str], int]]:
    """(nama, alamat pool, blok awal) — urut prioritas; v4 sudah selesai di swap_0000-0005 (agen sebelumnya)."""
    k = pd.read_parquet(ARB / "robinhood_kandidat.parquet", columns=["jenis", "blok", "pool", "c0", "c1", "kelas"])
    k = k[k.kelas.isin(("WETH/USD", "CRCL/USD", "CRCL/lain"))]
    lama = set(pd.read_parquet(ONCHAIN / "robinhood_pools.parquet").id)
    k = k[~k.pool.isin(lama) & k.jenis.isin(["v3", "alg", "slip", "algc", "v2", "solid", "aero", "lb"])]
    k = k.drop_duplicates("pool").sort_values("blok")
    v0, v1 = k.c0.isin(NILAI), k.c1.isin(NILAI)
    resmi_aset = k.c0.isin({WETH, ETH, CRCL}) | k.c1.isin({WETH, ETH, CRCL})
    k["prio"] = np.where(v0 & v1, 1, np.where(resmi_aset, 2, 3))
    out = []
    for pr, g in k.groupby("prio"):
        for jn, sub in (("lb", g[g.jenis == "lb"]), ("addr", g[g.jenis != "lb"])):
            for i in range(0, len(sub), 200):
                s = sub.iloc[i:i + 200]
                out.append((f"p{pr}{jn}{i // 200:02d}", list(s.pool), int(s.blok.min())))
    return out


def _rencana_saham() -> list[tuple[str, list[str], int, str | None]]:
    """Pool bernilai lain yang BELUM pernah diunduh: token saham resmi berpasangan USDG/WETH/ETH di DEX lain (v3 fork,
    Algebra, Slipstream, LB, v2, Solidly) + pool v4 PoolManager yang dibuat setelah riset lama (8 Okt pagi)."""
    meta = _orientasi(_meta())
    meta = meta[meta.c0.isin(NILAI) & meta.c1.isin(NILAI) & (meta.sumber == "kandidat_baru")]
    k = pd.read_parquet(ARB / "robinhood_kandidat.parquet", columns=["pool", "kelas"])
    sudah = set(k[k.kelas.isin(("WETH/USD", "CRCL/USD", "CRCL/lain"))].pool)
    m = meta[~meta.id.isin(sudah)].sort_values("blok")
    out = []
    for em, g in m[m.jenis == "v4"].groupby("emitter"):
        out.append((f"s4_{em[2:8]}", list(g.id), int(g.blok.min()), em))
    for jn, sub in (("lb", m[m.jenis == "lb"]), ("addr", m[~m.jenis.isin(["v4", "lb"])])):
        for i in range(0, len(sub), 200):
            s_ = sub.iloc[i:i + 200]
            out.append((f"s{jn}{i // 200:02d}", list(s_.id), int(s_.blok.min()), None))
    return out


BERAT = 20_000          # swap: pool "berat" (diarbitrase tiap blok) ...
BERAT_HARI = 7          # ... dan umurnya > 7 hari -> tidak diunduh lagi (yang dicari = jendela peluncuran)
BARIS_PER_FILE = 400_000
SUB = 20                # jendela per sub-batch (memori terbatas)


def _selesai(nama: str, c: int, sb: int | None = None) -> bool:
    if (PARTS / f"swap_{nama}_{c:03d}.parquet").exists() or list(PARTS.glob(f"swap_{nama}_{c:03d}_x*.parquet")):
        return True
    return sb is not None and bool(list(PARTS.glob(f"swap_{nama}_{c:03d}_{sb}*.parquet")))


def pecah_besar(maks_mb: float = 45.0) -> None:
    """File bagian > maks_mb (buatan sesi ini) dipecah per BARIS_PER_FILE baris: _<c>.parquet -> _<c>_x<k>.parquet."""
    for f in sorted(PARTS.glob("swap_p*_[0-9][0-9][0-9].parquet")) + sorted(PARTS.glob("swap_s*_[0-9][0-9][0-9].parquet")):
        if f.stat().st_size / 1e6 <= maks_mb:
            continue
        d = pd.read_parquet(f)
        for k, i in enumerate(range(0, len(d), BARIS_PER_FILE)):
            d.iloc[i:i + BARIS_PER_FILE].to_parquet(f.with_name(f.stem + f"_x{k}.parquet"), compression="zstd")
        print(f"pecah {f.name}: {len(d):,} baris -> {k + 1} file", flush=True)
        f.unlink()


def _hitung_lama(nama: str) -> pd.Series:
    fs = sorted(PARTS.glob(f"swap_{nama}_*.parquet"))
    if not fs:
        return pd.Series(dtype=float)
    return pd.concat([pd.read_parquet(f, columns=["id"]).id.value_counts() for f in fs]).groupby(level=0).sum()


def unduh_swap(saham: bool = False) -> None:
    top = A.head(NET)
    meta = PARTS / "top_lanjut.json"
    if meta.exists():
        top = json.loads(meta.read_text())["top"]
    else:
        meta.write_text(json.dumps({"top": top}))
    k = pd.read_parquet(ARB / "robinhood_semua_pool.parquet", columns=["pool", "jenis", "blok"]).drop_duplicates("pool")
    jenis_alamat = dict(zip(k.pool, k.jenis))
    lahir = dict(zip(k.pool, k.blok))
    span = A.SPAN_ALAMAT[NET]
    blok_hari = 86400 / 0.102
    rencana = _rencana_saham() if saham else [r + (None,) for r in _rencana()]
    print(f"{NET}: {len(rencana)} tugas lanjutan, {sum(len(r[1]) for r in rencana):,} pool, top {top:,}", flush=True)
    for nama, pools, b0, em in rencana:
        wins = [(c, min(c + span - 1, top)) for c in range(b0, top + 1, span)]
        t0 = time.time()
        n = 0
        cnt = _hitung_lama(nama)
        for c in range(0, len(wins), JENDELA_PER_FILE):
            ci = c // JENDELA_PER_FILE
            if _selesai(nama, ci):
                continue
            for sb, s0 in enumerate(range(c, min(c + JENDELA_PER_FILE, len(wins)), SUB)):
                if _selesai(nama, ci, sb):
                    continue
                ws = wins[s0:s0 + SUB]
                awal = ws[0][0]
                aktif = [p for p in pools if not (cnt.get(p, 0) > BERAT and awal - lahir.get(p, 0) > BERAT_HARI * blok_hari)]
                aktif = [p for p in aktif if lahir.get(p, 0) <= ws[-1][1]]
                rows = []
                if aktif:
                    if em:
                        flt, fn = {"address": em, "topics": [T_SWAP, aktif]}, (lambda x: A._dec_swap(x, jenis_alamat))
                    elif "lb" in nama:
                        flt, fn = {"address": aktif, "topics": [T_LB_SWAP]}, _dec_lb
                    else:
                        flt = {"address": aktif, "topics": [[T3_SWAP, A.T_V2_SWAP, A.T_SOLID_SWAP]]}
                        fn = (lambda x: A._dec_swap(x, jenis_alamat))
                    with ThreadPoolExecutor(A.PAR[NET]) as ex:
                        for r in ex.map(lambda w: A._logs_satu(NET, flt, w[0], w[1]), ws):
                            rows += [y for y in map(fn, r) if y]
                d = pd.DataFrame(rows, columns=COLS)
                del rows
                for kk, i in enumerate(range(0, max(len(d), 1), BARIS_PER_FILE)):
                    d.iloc[i:i + BARIS_PER_FILE].to_parquet(PARTS / f"swap_{nama}_{ci:03d}_{sb}{kk}.parquet",
                                                            compression="zstd")
                if len(d):
                    cnt = cnt.add(d.id.value_counts(), fill_value=0)
                n += len(d)
                print(f"  {nama}: jendela {s0 + len(ws)}/{len(wins)} aktif {len(aktif)}/{len(pools)} +{len(d):,} swap "
                      f"({time.time() - t0:.0f} dtk)", flush=True)
                del d
        print(f"{nama}: selesai ({len(pools)} pool, {n:,} swap baru)", flush=True)


T_ORACLE_SWAP = "0x2b2a3235899b710d8c8736a97363ef9ece6c10d7f54ef0b1090117aff3b3928b"   # pabrik 0x831880bd (non-standar)
PABRIK_ORACLE = "0x831880bd3b331249df63bacc6e21495e5e8f1eaa"


def _dec_oracle(lg: dict) -> dict | None:
    """Swap pair pabrik 0x831880bd: 6 kata (in0, in1, out0, out1, ?, ?) — harga eksekusi = harga pasar (oracle/PMM),
    BUKAN rasio cadangan getReserves (cadangan menyesatkan: MSTR tampak -37% padahal dieksekusi di harga pasar)."""
    t, d = lg["topics"], lg["data"]
    try:
        i0, i1, o0, o1 = (_w(d, k) for k in range(4))
        return {"id": lg["address"].lower(), "jenis": "v2oracle", "blok": int(lg["blockNumber"], 16),
                "li": int(lg["logIndex"], 16), "tx": lg["transactionHash"], "sender": _addr(t[1]),
                "recipient": _addr(t[2]) if len(t) > 2 else "", "a0": float(o0) - float(i0), "a1": float(o1) - float(i1),
                "sqrtp": np.nan, "L": np.nan}
    except (IndexError, ValueError):
        return None


def unduh_oracle() -> pd.DataFrame:
    f = PARTS / "swap_oracle8318_000_00.parquet"
    if f.exists():
        return pd.read_parquet(f)
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet", columns=["pool", "emitter", "blok"]).drop_duplicates("pool")
    sp = sp[sp.emitter == PABRIK_ORACLE]
    top = json.loads((PARTS / "top_lanjut.json").read_text())["top"]
    rows = A.scan(NET, {"address": list(sp.pool), "topics": [T_ORACLE_SWAP]}, int(sp.blok.min()), top,
                  A.SPAN_ALAMAT[NET], fn=_dec_oracle, label="oracle")
    d = pd.DataFrame(rows, columns=COLS)
    d.to_parquet(f, compression="zstd")
    print(f"pabrik oracle 0x831880bd: {len(sp)} pool, {len(d):,} swap", flush=True)
    return d


# ---------------------------------------------------------------- waktu & acuan
def waktu(step: int = 100_000) -> pd.Series:
    """Sampel stempel waktu blok (lama + lanjutan tiap `step` blok s/d head) -> ARB/robinhood_blok_lanjut.parquet."""
    f = ARB / "robinhood_blok_lanjut.parquet"
    lama = pd.read_parquet(ONCHAIN / "robinhood_blok.parquet")["ts"]
    old = pd.read_parquet(f)["ts"] if f.exists() else pd.Series(dtype="int64")
    top = A.head(NET)
    want = [b for b in range(int(lama.index.max()) + step, top, step)] + [top]
    want = [b for b in want if b not in set(old.index)]

    def ts(b):
        return b, int(rpc(NET, "eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)

    with ThreadPoolExecutor(6) as ex:
        new = dict(ex.map(ts, want))
    s = pd.concat([lama, old, pd.Series(new, dtype="int64")]).sort_index()
    s = s[~s.index.duplicated()]
    s.to_frame("ts").to_parquet(f)
    return s


def blok_ts() -> pd.Series:
    f = ARB / "robinhood_blok_lanjut.parquet"
    return pd.read_parquet(f)["ts"] if f.exists() else waktu()


def ts_tepat(bloks) -> dict:
    """Stempel waktu PERSIS blok-blok tertentu (eth_getBlockByNumber) — untuk jeda reaksi dalam detik."""
    f = ARB / "robinhood_blok_tepat.parquet"
    old = pd.read_parquet(f)["ts"].to_dict() if f.exists() else {}
    todo = sorted({int(b) for b in bloks} - set(old))

    def ts(b):
        try:
            return b, int(rpc(NET, "eth_getBlockByNumber", [hex(b), False], tries=4)["timestamp"], 16)
        except Exception:  # noqa: BLE001
            return b, -1

    if todo:
        with ThreadPoolExecutor(8) as ex:
            old.update(dict(ex.map(ts, todo)))
        pd.Series(old, dtype="int64").to_frame("ts").to_parquet(f)
    return old


def acuan_eth() -> pd.Series:
    """ETH 1 menit: acuan lama (s/d 7 Okt) + klines Binance (data-api.binance.vision) 7 Okt -> sekarang."""
    import urllib.request
    from .chain_baru_uji import acuan_1m
    f = ARB / "acuan_ETHUSDT_1m_lanjut.parquet"
    s = acuan_1m("ETH")
    if f.exists():
        s2 = pd.read_parquet(f)["close"]
    else:
        start = int(s.index.max().timestamp() * 1000)
        rows = []
        while True:
            url = (f"https://data-api.binance.vision/api/v3/klines?symbol=ETHUSDT&interval=1m&limit=1000"
                   f"&startTime={start}")
            with urllib.request.urlopen(url, timeout=30) as r:
                k = json.loads(r.read())
            if not k:
                break
            rows += k
            start = k[-1][0] + 60_000
            if len(k) < 1000:
                break
        d = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "v", "tc", "qv", "n", "tb", "tq", "x"])
        d.index = pd.to_datetime(d.t, unit="ms", utc=True)
        d = d[["open", "high", "low", "close"]].astype(float)
        d.to_parquet(f)
        s2 = d["close"]
    s = pd.concat([s, s2])
    return s[~s.index.duplicated(keep="last")].sort_index()


# ---------------------------------------------------------------- jejak grup E1/E2 di Robinhood
def _create_addr(sender: str, nonce: int) -> str:
    def enc_int(n):
        if n == 0:
            return b"\x80"
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return b if (len(b) == 1 and b[0] < 0x80) else bytes([0x80 + len(b)]) + b
    payload = b"\x94" + bytes.fromhex(sender[2:]) + enc_int(nonce)
    rlp = bytes([0xc0 + len(payload)]) + payload
    from eth_utils import keccak
    return "0x" + keccak(rlp).hex()[-40:]


def grup() -> dict:
    """E1/E2 di Robinhood: nonce, kontrak hasil CREATE (eth_getCode), saldo ETH, semua Transfer ERC-20."""
    out = {}
    adr = []
    for nama, e in (("E1", A.E1), ("E2", A.E2)):
        n = int(rpc(NET, "eth_getTransactionCount", [e, "latest"]), 16)
        bal = int(rpc(NET, "eth_getBalance", [e, "latest"]), 16) / 1e18
        kontrak = []
        for k in range(min(n, 400)):
            c = _create_addr(e, k)
            code = rpc(NET, "eth_getCode", [c, "latest"])
            if code and code != "0x":
                kontrak.append({"nonce": k, "alamat": c, "kode_byte": (len(code) - 2) // 2})
        out[nama] = {"alamat": e, "nonce": n, "saldo_eth": bal, "kontrak": kontrak}
        adr += [e] + [c["alamat"] for c in kontrak]
        print(nama, e, "nonce", n, "ETH", round(bal, 6), "kontrak", len(kontrak), flush=True)
    tr = A.transfer_alamat(NET, adr, 1, nama="grup_rh")
    out["transfer"] = len(tr)
    (ARB / "robinhood_grup_rh.json").write_text(json.dumps(out, indent=1))
    return out



# ---------------------------------------------------------------- nilai tiap swap thd acuan
PRIO_QUOTE = {"USD": 0, "ETH": 1}


def _meta() -> pd.DataFrame:
    """Metadata semua pool (baru + resmi lama) — id, jenis, blok, c0, c1, d0, d1, sqrtp0, aset, quote, sumber."""
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet",
                         columns=["pool", "jenis", "emitter", "blok", "c0", "c1", "d0", "d1", "sqrtp0", "fee", "s0", "s1"])
    sp = sp.drop_duplicates("pool").rename(columns={"pool": "id"})
    lama = pd.read_parquet(ONCHAIN / "robinhood_pools.parquet")
    dl = dict(zip(lama.id, zip(lama.d0, lama.d1)))
    sp["sumber"] = np.where(sp.id.isin(set(lama.id)), "resmi_lama", "kandidat_baru")
    for k in (0, 1):
        sp[f"d{k}"] = [dl[i][k] if i in dl else d for i, d in zip(sp.id, sp[f"d{k}"])]
    sp.loc[sp.c0 == ETH, "d0"] = 18
    return sp


def _orientasi(m: pd.DataFrame) -> pd.DataFrame:
    """aset = token yang dinilai TERHADAP quote (quote: USDG > ETH/WETH > saham)."""
    r0 = m.c0.map(NILAI)
    r1 = m.c1.map(NILAI)
    pr = lambda r: r.map(lambda x: PRIO_QUOTE.get(x, 2) if isinstance(x, str) else 9)  # noqa: E731
    p0, p1 = pr(r0), pr(r1)
    aset0 = (p1 < p0) | ((p1 == p0) & (m.c1 == ETH))      # quote = token1 -> aset token0
    m = m.copy()
    m["r0"], m["r1"] = r0, r1
    m["aset_is0"] = aset0
    m["aset"] = np.where(aset0, m.c0, m.c1)
    m["quote"] = np.where(aset0, m.c1, m.c0)
    m["ref_aset"] = np.where(aset0, r0, r1)
    m["ref_quote"] = np.where(aset0, r1, r0)
    sym = lambda a, r: SAHAM.get(a, {"USD": "USDG", "ETH": "WETH" if a == WETH else "ETH"}.get(r, "?"))  # noqa: E731
    m["pair"] = [f"{sym(a, ra)}/{sym(q, rq)}" for a, ra, q, rq in zip(m.aset, m.ref_aset, m.quote, m.ref_quote)]
    return m


def acuan_saham(mulai: str = "2026-10-08") -> pd.DataFrame:
    """Saham 1 menit jam reguler NYSE 8 Okt dst. (Twelve Data; acuan lama berhenti 7 Okt) -> file sendiri."""
    import os
    import urllib.parse
    import urllib.request
    f = ARB / "acuan_saham_1m_lanjut.parquet"
    if f.exists():
        return pd.read_parquet(f)
    key = os.environ.get("TWELVEDATA_API_KEY", "")
    rows = []
    for sym in sorted(SAHAM.values()):
        q = urllib.parse.urlencode({"symbol": sym, "interval": "1min", "start_date": f"{mulai} 00:00:00",
                                    "outputsize": 5000, "timezone": "UTC", "order": "ASC", "apikey": key})
        d = {}
        for k in range(4):
            try:
                with urllib.request.urlopen("https://api.twelvedata.com/time_series?" + q, timeout=60) as r:
                    d = json.loads(r.read())
            except Exception:  # noqa: BLE001
                time.sleep(10)
                continue
            if "credits" in str(d.get("message", "")).lower():
                time.sleep(61)
                continue
            break
        time.sleep(8)
        for v in d.get("values", []) or []:
            rows.append({"sym": sym, "t": pd.Timestamp(v["datetime"], tz="UTC"), "close": float(v["close"])})
        print(f"  {sym}: {len(d.get('values', []) or [])} menit ({d.get('status')})", flush=True)
    df = pd.DataFrame(rows)
    df.to_parquet(f)
    return df


def _refs() -> dict:
    from .chain_baru_uji import acuan_1m
    out = {"ETH": acuan_eth()}
    f = ARB / "acuan_saham_1m_lanjut.parquet"
    tambah = pd.read_parquet(f) if f.exists() else pd.DataFrame(columns=["sym", "t", "close"])
    for s in SAHAM.values():
        a = acuan_1m(s)
        b = tambah[tambah.sym == s].set_index("t")["close"]
        if len(b):
            b.index = pd.DatetimeIndex(b.index).floor("min")
            a = pd.concat([a, b])
            a = a[~a.index.duplicated(keep="last")].sort_index()
        out[s] = a
    return out


def _harga_ref(refs: dict, ref: np.ndarray, t: pd.DatetimeIndex) -> np.ndarray:
    from .chain_baru_uji import _ref_at
    out = np.full(len(t), np.nan)
    for r in set(ref):
        m = ref == r
        if r == "USD":
            out[m] = 1.0
        elif isinstance(r, str) and r in refs:
            out[m] = _ref_at(refs[r], pd.DatetimeIndex(t[m]), "3min")
    return out


def _nilai_df(sw: pd.DataFrame, meta: pd.DataFrame, refs: dict, blk: pd.Series, liq: pd.DataFrame | None) -> pd.DataFrame:
    """sw: id, jenis, blok, li, tx/txh, sender, a0, a1, sqrtp, L (sisi penukar: + = diterima)."""
    from .chain_onchain import ke_waktu
    m = meta.set_index("id")
    sw = sw.sort_values(["id", "blok", "li"], kind="stable").reset_index(drop=True)
    ids = sw.id.astype(str).to_numpy()
    g = lambda c: m[c].reindex(ids).to_numpy()  # noqa: E731
    d0, d1 = g("d0").astype(float), g("d1").astype(float)
    aset0 = g("aset_is0").astype(bool)
    ra, rq = g("ref_aset"), g("ref_quote")
    t = ke_waktu(sw.blok.to_numpy(), blk)
    pa, pq_ = _harga_ref(refs, ra, t), _harga_ref(refs, rq, t)
    x0 = sw.a0.to_numpy() / 10.0 ** d0
    x1 = sw.a1.to_numpy() / 10.0 ** d1
    q_aset = np.where(aset0, x0, x1)
    q_quote = np.where(aset0, x1, x0)
    # harga pool (quote per aset, satuan manusia) setelah swap; v2/LB: harga eksekusi
    sq = sw.sqrtp.to_numpy() / 2 ** 96
    p01 = sq ** 2 * 10.0 ** (d0 - d1)                      # token1 per token0
    pq_a = np.where(aset0, p01, 1 / np.where(p01 > 0, p01, np.nan))
    eks = np.abs(q_quote) / np.where(np.abs(q_aset) > 0, np.abs(q_aset), np.nan)
    tanpa_sq = ~np.isfinite(sq) | (sq <= 0)
    post = np.where(tanpa_sq, eks, pq_a)
    first = np.r_[True, ids[1:] != ids[:-1]]
    sq0 = pd.to_numeric(pd.Series(g("sqrtp0")).replace("", np.nan), errors="coerce").to_numpy(dtype=float) / 2 ** 96
    p01_0 = sq0 ** 2 * 10.0 ** (d0 - d1)
    init = np.where(aset0, p01_0, 1 / np.where(p01_0 > 0, p01_0, np.nan))
    pre = np.where(first, init, np.roll(post, 1))
    pre = np.where(first & tanpa_sq, eks, pre)
    adil = pa / pq_                                        # harga wajar quote per aset
    out = pd.DataFrame({
        "id": ids, "blok": sw.blok.to_numpy(), "li": sw.li.to_numpy().astype("int32"), "t": t,
        "sender": sw.sender.astype(str).to_numpy(),
        "jenis": g("jenis"), "pair": g("pair"), "aset": g("aset"), "sumber": g("sumber"),
        "dev_pra": pre / adil - 1, "dev_pasca": post / adil - 1, "dev_eks": eks / adil - 1,
        "q_aset": q_aset, "q_quote": q_quote, "usd_aset": q_aset * pa, "usd_quote": q_quote * pq_,
        "untung_usd": q_aset * pa + q_quote * pq_,
        "L": sw.L.to_numpy() if "L" in sw else np.nan, "sqrtp": sw.sqrtp.to_numpy(),
    })
    out["tx"] = sw["tx"].to_numpy() if "tx" in sw else ""
    out["txh"] = sw["txh"].to_numpy() if "txh" in sw else np.array([int(x[2:17], 16) for x in sw.tx], dtype="int64")
    tb = ke_waktu(g("blok").astype(float), blk)
    prev_t = pd.Series(np.roll(out.t.to_numpy(), 1)).where(~first, pd.Series(tb)).to_numpy()
    prev_b = np.where(first, g("blok"), np.roll(out.blok.to_numpy(), 1))
    if liq is not None and len(liq):
        q = pd.DataFrame({"id": ids, "blok": out.blok.to_numpy(), "i": np.arange(len(out))}).sort_values("blok")
        lq = liq[liq.id.isin(set(ids))][["id", "blok"]].rename(columns={"blok": "b_liq"}).sort_values("b_liq")
        lq["blok"] = lq.b_liq
        s2 = pd.merge_asof(q, lq, on="blok", by="id", direction="backward", allow_exact_matches=False)
        s2 = s2.sort_values("i")
        bl = s2.b_liq.to_numpy()
        prev_b = np.where(np.isfinite(bl) & (bl > prev_b), bl, prev_b)
        prev_t = ke_waktu(prev_b.astype(float), blk)
    out["blok_pra"] = prev_b.astype("int64")
    out["jeda_dtk"] = (out.t - pd.DatetimeIndex(prev_t)).dt.total_seconds().to_numpy().astype("float32")
    out["umur_jam"] = ((out.t - pd.DatetimeIndex(tb)).dt.total_seconds() / 3600).to_numpy().astype("float32")
    return out


def _swap_baru(ids: set) -> pd.DataFrame:
    parts = sorted(PARTS.glob("swap_*.parquet"))
    out = []
    for f in parts:
        d = pd.read_parquet(f, columns=["id", "jenis", "blok", "li", "tx", "sender", "recipient", "a0", "a1", "sqrtp", "L"])
        d = d[d.id.isin(ids)]
        if len(d):
            out.append(d)
    return pd.concat(out, ignore_index=True).drop_duplicates(["tx", "li"]) if out else pd.DataFrame(columns=COLS)


def _kelompok(n: pd.Series, maks: int) -> list[list[str]]:
    grp, cur, acc = [], [], 0
    for pid, c in n.items():
        if acc + c > maks and cur:
            grp.append(cur)
            cur, acc = [], 0
        cur.append(pid)
        acc += c
    if cur:
        grp.append(cur)
    return grp


def bagian():
    """Generator bagian bernilai: kandidat baru (semua riwayat) lalu resmi lama per kelompok pool <= 2,5 jt swap
    (saham: semua riwayat; ETH/WETH/USDG: hari pertama tiap pool = batas data riset lama)."""
    meta = _orientasi(_meta())
    meta = meta[meta.c0.isin(NILAI) & meta.c1.isin(NILAI)]
    meta.to_parquet(ARB / "robinhood_pool_bernilai.parquet")
    refs = _refs()
    blk = blok_ts()
    liq = pd.read_parquet(ONCHAIN / "robinhood_liq.parquet", columns=["id", "blok", "dL"])
    liq = liq[liq.dL > 0]
    liq["id"] = liq.id.astype(str)
    baru = set(meta[meta.sumber == "kandidat_baru"].id)
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq
    files = [str(f) for f in sorted(PARTS.glob("swap_*.parquet"))]
    dsb = ds.dataset(files, schema=pq.read_schema(PARTS / "swap_0000.parquet"))
    nb = dsb.to_table(columns=["id"], filter=ds.field("id").isin(list(baru))).column("id").to_pandas().value_counts()
    print(f"swap kandidat baru bernilai: {int(nb.sum()):,} ({len(nb)} pool)", flush=True)
    for k, gp in enumerate(_kelompok(nb, 1_500_000)):
        sw = dsb.to_table(columns=COLS, filter=ds.field("id").isin(gp)).to_pandas().drop_duplicates(["tx", "li"])
        print(f"  kandidat baru kelompok {k + 1}: {len(sw):,} swap", flush=True)
        yield f"baru{k:02d}", _nilai_df(sw, meta, refs, blk, None)
        del sw
    f = ONCHAIN / "robinhood_swap.parquet"
    n = pd.read_parquet(f, columns=["id"]).id.astype(str).value_counts()
    grp = _kelompok(n, 2_000_000)
    dset = ds.dataset(f)
    for k, gp in enumerate(grp):
        sw = dset.to_table(columns=["id", "blok", "li", "sender", "a0", "a1", "sqrtp", "L", "txh"],
                           filter=ds.field("id").isin(gp)).to_pandas()
        sw["id"] = sw.id.astype(str)
        print(f"  resmi lama kelompok {k + 1}/{len(grp)}: {len(sw):,} swap", flush=True)
        yield f"lama{k:02d}", _nilai_df(sw, meta, refs, blk, liq)
        del sw


def episode(x: pd.DataFrame, meta: pd.DataFrame, batas: float = -0.05) -> pd.DataFrame:
    """Episode diskon: deret swap berurutan satu pool dengan harga pool SEBELUM swap <= acuan x (1 + batas)."""
    x = x.sort_values(["id", "blok", "li"], kind="stable").reset_index(drop=True)
    d = x.dev_pra.to_numpy()
    disc = np.isfinite(d) & (d <= batas)
    ids = x.id.astype(str).to_numpy()
    newp = np.r_[True, ids[1:] != ids[:-1]]
    lastp = np.r_[ids[1:] != ids[:-1], True]
    start = disc & (newp | ~np.r_[False, disc[:-1]])
    if not start.any():
        return pd.DataFrame()
    eid = np.cumsum(start)
    eid = np.where(disc, eid, 0)
    m = meta.set_index("id")
    rows = []
    t = x.t.to_numpy()
    blok = x.blok.to_numpy()
    beli = (x.q_aset.to_numpy() > 0) & (x.usd_quote.to_numpy() < 0)
    for k in np.unique(eid[eid > 0]):
        ix = np.flatnonzero(eid == k)
        r0, r1 = ix[0], ix[-1]
        pid = ids[r0]
        if x.dev_pasca.iat[r1] > batas or not np.isfinite(x.dev_pasca.iat[r1]):
            cara, t_end = "ditutup swap", t[r1]
        elif not lastp[r1]:
            cara, t_end = "pasif (acuan/likuiditas berubah)", t[r1 + 1]
        else:
            cara, t_end = "masih terbuka (data berakhir)", np.datetime64("NaT")
        b = ix[beli[ix]]
        tb0 = x.t.iat[r0] - pd.Timedelta(seconds=float(x.jeda_dtk.iat[r0]))
        kap = np.nan
        if r0 > 0 and not newp[r0] and np.isfinite(x.L.iat[r0 - 1]) and np.isfinite(x.sqrtp.iat[r0 - 1]):
            mm = m.loc[pid]
            L, sqr = float(x.L.iat[r0 - 1]), float(x.sqrtp.iat[r0 - 1]) / 2 ** 96
            dev0 = float(d[r0])
            # harga sasaran = (1 + batas)/(1 + dev) x harga sekarang (quote per aset)
            f_ = (1 + batas) / (1 + dev0) if (1 + dev0) > 1e-9 else np.nan
            if not (sqr > 0 and np.isfinite(f_)):
                dq = np.nan
            elif mm.aset_is0:   # beli token0: P01 naik sebesar f_
                dq = L * sqr * (np.sqrt(f_) - 1) / 10.0 ** mm.d1
            else:             # beli token1: P01 turun ke P01/f_
                dq = L / sqr * (np.sqrt(f_) - 1) / 10.0 ** mm.d0
            kap = dq
        rows.append({
            "id": pid, "pair": x.pair.iat[r0], "sumber": x.sumber.iat[r0], "jenis": x.jenis.iat[r0],
            "umur_jam": float(x.umur_jam.iat[r0]), "t_mulai": tb0, "t_swap1": x.t.iat[r0], "t_tutup": t_end,
            "blok_mulai": int(x.blok_pra.iat[r0]), "blok_swap1": int(blok[r0]), "cara_tutup": cara,
            "n_swap": len(ix), "n_beli": len(b), "dev_awal": float(d[r0]), "dev_min": float(np.nanmin(d[ix])),
            "usd_beli": float(-x.usd_quote.to_numpy()[b].sum()) if len(b) else 0.0,
            "untung_beli": float(x.untung_usd.to_numpy()[b].sum()) if len(b) else 0.0,
            "untung_semua": float(np.nansum(x.untung_usd.to_numpy()[ix])),
            "t_beli1": x.t.iat[b[0]] if len(b) else pd.NaT, "blok_beli1": int(blok[b[0]]) if len(b) else -1,
            "pengirim_beli1": x.sender.iat[b[0]] if len(b) else "",
            "tx_beli1": x.tx.iat[b[0]] if len(b) else "", "txh_beli1": int(x.txh.iat[b[0]]) if len(b) else 0,
            "pengirim_terbesar": x.sender.iat[b[np.argmax(x.untung_usd.to_numpy()[b])]] if len(b) else "",
            "n_pengirim": int(pd.unique(x.sender.to_numpy()[b]).size) if len(b) else 0,
            "kap_quote": kap,
        })
    e = pd.DataFrame(rows)
    e["lama_dtk"] = (pd.to_datetime(e.t_tutup, utc=True) - e.t_mulai).dt.total_seconds()
    e["jeda_reaksi_dtk"] = (pd.to_datetime(e.t_beli1, utc=True) - e.t_mulai).dt.total_seconds()
    return e


def pecahan(x: pd.DataFrame, min_n: int = 5, maks_usd: float = 250.0) -> pd.DataFrame:
    """Kelompok beli (pengirim, pool, jumlah input quote PERSIS sama) yang berulang >= min_n kali."""
    b = x[(x.q_aset > 0) & (x.usd_quote < 0)].copy()
    if not len(b):
        return pd.DataFrame()
    b["qin"] = (-b.usd_quote).round(6)
    b["qraw"] = (-b.q_quote).round(9)
    g = b.groupby(["sender", "id", "qraw"], observed=True)
    a = g.agg(n=("qin", "size"), usd=("qin", "sum"), usd_satu=("qin", "median"), pair=("pair", "first"),
              t0=("t", "min"), t1=("t", "max"), n_blok=("blok", "nunique"), dev_med=("dev_eks", "median"),
              dev_min=("dev_eks", "min"), untung=("untung_usd", "sum"), sumber=("sumber", "first")).reset_index()
    return a[(a.n >= min_n) & (a.usd_satu <= maks_usd) & (a.n_blok >= 3)]


def proses() -> None:
    meta = None
    ep, pc, ring, ring_i, per_pool = [], [], [], 0, []
    for nama, x in bagian():
        if meta is None:
            meta = pd.read_parquet(ARB / "robinhood_pool_bernilai.parquet")
        ep.append(episode(x, meta))
        e2 = episode(x, meta, batas=-0.02)
        if len(e2):
            e2["batas"] = -0.02
            ep.append(e2)
        pc.append(pecahan(x))
        per_pool.append(x.groupby("id", observed=True).agg(
            n_swap=("blok", "size"), t_swap1=("t", "min"), t_swap_akhir=("t", "max"),
            dev_pra_min=("dev_pra", "min"), dev_pra_med_abs=("dev_pra", lambda v: v.abs().median()),
            untung_pos=("untung_usd", lambda v: v[v > 0].sum()), untung_bersih=("untung_usd", "sum"),
            notional=("usd_aset", lambda v: v.abs().sum())).reset_index())
        r = x[(x.dev_pra.abs() >= 0.005) | (x.untung_usd.abs() >= 1) | (x.dev_eks.abs() >= 0.005)]
        r = r.drop(columns=["sqrtp", "L", "q_quote"])
        for c in ("id", "sender", "jenis", "pair", "aset", "sumber", "tx"):
            r[c] = r[c].astype("category")
        fp = ARB / f"robinhood_nilai_bernilai_{ring_i:02d}.parquet"
        r.to_parquet(fp, compression="zstd")
        ring_i += 1
        print(f"  {nama}: {len(x):,} swap, ringkas {len(r):,} -> {fp.name} ({fp.stat().st_size / 1e6:.1f} MB)",
              flush=True)
        del x, r
    E = pd.concat([e for e in ep if len(e)], ignore_index=True)
    E["batas"] = E["batas"].fillna(-0.05) if "batas" in E else -0.05
    E.to_parquet(ARB / "robinhood_episode_diskon.parquet")
    P = pd.concat([p for p in pc if len(p)], ignore_index=True) if any(len(p) for p in pc) else pd.DataFrame()
    P.to_parquet(ARB / "robinhood_pecahan.parquet")
    pd.concat(per_pool, ignore_index=True).to_parquet(ARB / "robinhood_per_pool_bernilai.parquet")
    print(f"episode {len(E):,}, pecahan {len(P):,}")



# ---------------------------------------------------------------- potret token RESMI: pool tipis vs pool utama
S_FEE, S_TS = "0xddca3f43", "0xd0c93a7c"


def potret_resmi(ukuran=(3, 25, 100, 300), gas_usd: float | None = None) -> pd.DataFrame:
    """Aset resmi (WETH/ETH + 16 saham) ber-quote USDG: beli di pool termurah / jual di pool utama (terdalam) atau
    sebaliknya. Leg pool tipis dikuotasi persis (V4Quoter / simulasi v3 lintas tick dengan fee & tickSpacing asli dari
    kontrak / produk-konstan v2 fee 0,3%), leg pool utama = mid x (1 - fee) (pool utama >= 100x ukuran)."""
    g = gas_usd if gas_usd is not None else A.gas_swap_usd(NET)
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet",
                         columns=["jenis", "emitter", "blok", "pool", "c0", "c1", "fee", "ts", "hooks", "d0", "d1"])
    sp = sp.drop_duplicates("pool")
    aset_resmi = {WETH, ETH, *SAHAM}
    m = ((sp.c0 == USDG) & sp.c1.isin(aset_resmi)) | ((sp.c1 == USDG) & sp.c0.isin(aset_resmi))
    sp = sp[m & sp.jenis.isin(["v4", "v3", "slip", "alg", "algc", "v2", "solid", "aero"])]
    sp = sp[(sp.jenis != "v4") | (sp.emitter == PM)].copy()
    sp.loc[sp.c0 == ETH, "d0"] = 18
    print(f"potret resmi: {len(sp):,} pool aset resmi/USDG", flush=True)
    st = A._status_pool(NET, sp)
    # fee & tickSpacing asli untuk slip/alg/v3 fork (PoolCreated Slipstream memuat tickSpacing, bukan fee)
    nv = st[st.jenis.isin(["v3", "slip", "alg", "algc"])]
    res = A.multicall_banyak(NET, [(p, S_FEE) for p in nv.pool] + [(p, S_TS) for p in nv.pool], chunk=400)
    fee_a = {p: (int(r[2:66], 16) if r and len(r) >= 66 else np.nan) for p, r in zip(nv.pool, res[:len(nv)])}
    ts_a = {p: (A._s(int(r[2:66], 16)) if r and len(r) >= 66 else np.nan) for p, r in zip(nv.pool, res[len(nv):])}
    st["fee_asli"] = [fee_a.get(p, f) if j != "v4" else (lf if np.isfinite(lf) else f)
                      for p, j, f, lf in zip(st.pool, st.jenis, st.fee, st.lpfee)]
    st["ts"] = [ts_a.get(p, t) if j in ("slip", "alg", "algc") else t for p, j, t in zip(st.pool, st.jenis, st.ts)]
    st.loc[st.jenis.isin(["v2", "solid", "aero"]), "fee_asli"] = 3000
    v2 = st.jenis.isin(["v2", "solid", "aero"]).to_numpy()
    d0, d1 = st.d0.clip(lower=0).astype(float).to_numpy(), st.d1.clip(lower=0).astype(float).to_numpy()
    sq = st.sqrtp.to_numpy() / A.Q96
    with np.errstate(divide="ignore", invalid="ignore"):
        p01 = np.where(v2, (st.r1 / 10.0 ** d1) / (st.r0 / 10.0 ** d0), sq ** 2 * 10.0 ** (d0 - d1))
        usd0 = (st.c0 == USDG).to_numpy()
        st["harga"] = np.where(usd0, 1 / p01, p01)
        vres = np.where(v2, np.where(usd0, st.r0, st.r1), np.where(usd0, st.L / sq, st.L * sq))
        st["dalam2"] = vres / 10.0 ** np.where(usd0, d0, d1) * (np.sqrt(1.02) - 1)
    st["aset"] = np.where(usd0, st.c1, st.c0)
    st = st[np.isfinite(st.harga) & (st.harga > 0) & (st.dalam2 > 0.2)].copy()
    st["tick"] = np.where(st.jenis.isin(["v2", "solid", "aero"]), 0,
                          np.floor(np.log(np.where(st.sqrtp > 0, st.sqrtp / A.Q96, 1.0) ** 2) / np.log(1.0001))).astype(int)
    utama = st.sort_values("dalam2").groupby("aset").tail(1).set_index("aset")
    st["harga_utama"] = st.aset.map(utama.harga)
    st["fee_utama"] = st.aset.map(utama.fee_asli) / 1e6
    st["dalam2_utama"] = st.aset.map(utama.dalam2)
    st["pool_utama"] = st.aset.map(utama.pool)
    st["dev_vs_utama"] = st.harga / st.harga_utama - 1
    cal = st[(st.pool != st.pool_utama) & (st.dev_vs_utama.abs() >= 0.005)].copy()
    v3p = cal[cal.jenis.isin(["v3", "slip", "alg", "algc"])].copy()
    v3p["ts"] = v3p.ts.fillna(60).clip(lower=1).astype(int)
    ticks = A._v3_ticks(NET, v3p) if len(v3p) else {}
    rows, legs4, idx4 = [], [], []

    def leg(r, z, amt):
        f = r.fee_asli / 1e6
        if r.jenis in ("v3", "slip", "alg", "algc"):
            return A._v3_sim(amt, z, r.sqrtp, r.L, int(r.tick), f, ticks.get(r.pool, {}))
        if r.jenis in ("v2", "solid", "aero"):
            return A._v2_out(amt, r.r0 if z else r.r1, r.r1 if z else r.r0, f)
        return None

    hasil = {}
    for r in cal.itertuples():
        murah = r.dev_vs_utama < 0
        da, dq = (r.d1, r.d0) if r.c0 == USDG else (r.d0, r.d1)
        for usd in ukuran:
            if murah:   # beli aset di pool tipis dengan USDG
                z = r.c0 == USDG
                amt = usd * 10.0 ** dq
            else:       # beli aset di pool utama (mid x (1-fee)) lalu jual di pool tipis
                z = r.c0 != USDG
                amt = usd / r.harga_utama * (1 - r.fee_utama) * 10.0 ** da
            o = leg(r, z, amt)
            if o is None:
                legs4.append((r.c0, r.c1, r.fee, r.ts, r.hooks, z, amt))
                idx4.append((r.pool, usd))
            else:
                hasil[(r.pool, usd)] = o
    for k, o in zip(idx4, A._q_v4(NET, legs4)):
        hasil[k] = o
    for r in cal.itertuples():
        murah = r.dev_vs_utama < 0
        da, dq = (r.d1, r.d0) if r.c0 == USDG else (r.d0, r.d1)
        row = {"aset": r.aset, "simbol": SAHAM.get(r.aset, "WETH" if r.aset == WETH else "ETH"), "pool": r.pool,
               "jenis": r.jenis, "emitter": r.emitter, "hooks": r.hooks, "fee": r.fee_asli, "harga": r.harga,
               "harga_utama": r.harga_utama, "dev_vs_utama": r.dev_vs_utama, "dalam2": r.dalam2,
               "dalam2_utama": r.dalam2_utama, "arah": "beli di pool ini" if murah else "jual ke pool ini"}
        for usd in ukuran:
            o = hasil.get((r.pool, usd), 0.0)
            if murah:
                nilai = o / 10.0 ** da * r.harga_utama * (1 - r.fee_utama)
            else:
                nilai = o / 10.0 ** dq
            row[f"untung_{usd}"] = nilai - usd - 2 * g
        rows.append(row)
    df = pd.DataFrame(rows)
    if len(df):
        df["untung_terbaik"] = df[[f"untung_{u}" for u in ukuran]].max(axis=1)
        df = df.sort_values("untung_terbaik", ascending=False)
    df.to_parquet(ARB / "robinhood_potret_resmi.parquet")
    st.drop(columns=[c for c in ("tx", "sqrtp0") if c in st]).to_parquet(ARB / "robinhood_potret_resmi_pool.parquet")
    return df



# ---------------------------------------------------------------- cocokkan jumlah screenshot di Robinhood
def cari_ss() -> pd.DataFrame:
    """Jumlah PERSIS screenshot (arb_cari.SS) di semua swap Robinhood yang ada (kandidat baru + resmi lama):
    sisi USD 6 desimal (USDG/USDC) tampil 4 desimal, sisi aset tampil 8 (WETH) / 6 (CRCL) digit."""
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet", columns=["pool", "d0", "d1", "s0", "s1"]).drop_duplicates("pool")
    dec = sp.set_index("pool")[["d0", "d1", "s0", "s1"]]
    hits = []

    def cek(d, sumber):
        d = d.copy()
        d["id"] = d.id.astype(str)
        j = dec.reindex(d.id.to_numpy())
        v0 = d.a0.abs().to_numpy() / 10.0 ** j.d0.to_numpy().clip(0)
        v1 = d.a1.abs().to_numpy() / 10.0 ** j.d1.to_numpy().clip(0)
        for bot, arah, u, w, jam in A.SS:
            tol_w = 0.5e-8 if bot == "wetharb" else 0.5e-6
            mu0, mu1 = np.abs(v0 - u) < 0.5e-4, np.abs(v1 - u) < 0.5e-4
            mw0, mw1 = np.abs(v0 - w) <= tol_w, np.abs(v1 - w) <= tol_w
            m = (mu0 & mw1) | (mu1 & mw0)
            for r in d[m].itertuples():
                hits.append({"bot": bot, "arah": arah, "usd": u, "aset": w, "jam_wib": jam, "sumber": sumber,
                             "id": r.id, "blok": r.blok, "sender": r.sender,
                             "s0": dec.s0.get(r.id, "?"), "s1": dec.s1.get(r.id, "?")})

    for f in sorted(PARTS.glob("swap_*.parquet")):
        cek(pd.read_parquet(f, columns=["id", "blok", "sender", "a0", "a1"]), f.name)
    pf = pq.ParquetFile(ONCHAIN / "robinhood_swap.parquet")
    for rg in range(pf.num_row_groups):
        cek(pf.read_row_group(rg, columns=["id", "blok", "sender", "a0", "a1"]).to_pandas(), "resmi_lama")
    df = pd.DataFrame(hits)
    df.to_parquet(ARB / "robinhood_cari_ss.parquet")
    return df


def pecahan_semua(min_n: int = 5) -> pd.DataFrame:
    """Pola "wetharb" di SEMUA pool kandidat (termasuk quote tidak resmi): pembeli aset resmi (WETH/ETH/CRCL) dengan
    jumlah input quote PERSIS sama berulang >= min_n kali di >= 3 blok. Harga tersirat dihitung seolah quote = $1
    (hanya bermakna untuk USDG resmi)."""
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet",
                         columns=["pool", "c0", "c1", "d0", "d1", "s0", "s1", "n0", "n1", "blok"]).drop_duplicates("pool")
    sp = sp.set_index("pool")
    files = [str(f) for f in sorted(PARTS.glob("swap_*.parquet"))]
    dsb = ds.dataset(files, schema=pq.read_schema(PARTS / "swap_0000.parquet"))
    sw = dsb.to_table(columns=["id", "blok", "li", "tx", "sender", "recipient", "a0", "a1"]).to_pandas()
    sw = sw.drop_duplicates(["tx", "li"])
    j = sp.reindex(sw.id.to_numpy())
    resmi = {WETH, ETH, CRCL}
    a0 = j.c0.isin(resmi).to_numpy() & ~j.c1.isin(resmi).to_numpy()
    a1 = j.c1.isin(resmi).to_numpy() & ~j.c0.isin(resmi).to_numpy()
    m = a0 | a1
    sw, j, a0 = sw[m].reset_index(drop=True), j[m].reset_index(drop=True), a0[m]
    d0, d1 = j.d0.clip(lower=0).to_numpy(), j.d1.clip(lower=0).to_numpy()
    qa = np.where(a0, sw.a0 / 10.0 ** d0, sw.a1 / 10.0 ** d1)
    qq = np.where(a0, sw.a1 / 10.0 ** d1, sw.a0 / 10.0 ** d0)
    raw_q = np.where(a0, sw.a1, sw.a0)
    b = pd.DataFrame({"id": sw.id, "blok": sw.blok, "tx": sw.tx, "sender": sw.sender, "q_aset": qa, "q_quote": qq,
                      "raw_in": -raw_q, "aset_sym": np.where(a0, j.s0, j.s1), "quote_sym": np.where(a0, j.s1, j.s0),
                      "quote_nama": np.where(a0, j.n1, j.n0), "quote": np.where(a0, j.c1, j.c0)})
    b = b[(b.q_aset > 0) & (b.q_quote < 0)]
    b["harga_tersirat"] = -b.q_quote / b.q_aset
    g = b.groupby(["sender", "id", "raw_in"])
    a = g.agg(n=("blok", "size"), n_blok=("blok", "nunique"), blok0=("blok", "min"), blok1=("blok", "max"),
              q_in=("q_quote", lambda v: -v.iloc[0]), aset=("aset_sym", "first"), quote_sym=("quote_sym", "first"),
              quote_nama=("quote_nama", "first"), quote=("quote", "first"), harga_med=("harga_tersirat", "median"),
              harga_min=("harga_tersirat", "min"), harga_max=("harga_tersirat", "max"), tx1=("tx", "first")).reset_index()
    a = a[(a.n >= min_n) & (a.n_blok >= 3)].sort_values("n", ascending=False)
    a["quote_resmi"] = a.quote == USDG
    a.to_parquet(ARB / "robinhood_pecahan_semua.parquet")
    return a


# ---------------------------------------------------------------- kualitas token (resmi vs tiruan)
def tiruan() -> pd.DataFrame:
    """Token bersimbol sama dengan token resmi (WETH, USDG, 16 saham) atau bernama '• Robinhood Token' tetapi
    alamatnya BUKAN alamat resmi -> jumlah token & pool."""
    tok = pd.read_parquet(ARB / "robinhood_token.parquet")
    resmi = {WETH: "WETH", USDG: "USDG", **SAHAM}
    sym_resmi = set(resmi.values())
    t = tok[(tok.symbol.str.upper().isin(sym_resmi)) | tok.name.str.contains("Robinhood Token", case=False, na=False)]
    t = t.assign(resmi=t.alamat.isin(resmi))
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet", columns=["pool", "c0", "c1"]).drop_duplicates("pool")
    n = pd.concat([sp.c0, sp.c1]).value_counts()
    t = t.assign(n_pool=t.alamat.map(n).fillna(0).astype(int))
    return t


# ---------------------------------------------------------------- ringkasan & laporan
def _pekan(t: pd.Series) -> pd.Series:
    awal = pd.Timestamp("2026-07-01", tz="UTC")
    return ((pd.to_datetime(t, utc=True) - awal).dt.days // 7).astype(int)


def jendela(batas: float = -0.05, jam: float = 72.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per pekan pembuatan pool: pool BARU bernilai, berapa yang sempat diskon <= batas dalam `jam` pertama, lama
    diskon, volume beli di bawah batas, untung, jeda reaksi, pengambil."""
    from .chain_onchain import ke_waktu
    meta = pd.read_parquet(ARB / "robinhood_pool_bernilai.parquet")
    pp = pd.read_parquet(ARB / "robinhood_per_pool_bernilai.parquet")
    E = pd.read_parquet(ARB / "robinhood_episode_diskon.parquet")
    E = E[np.isclose(E.batas, batas)].copy()
    blk = blok_ts()
    meta["t_buat"] = ke_waktu(meta.blok.to_numpy().astype(float), blk)
    meta["pekan"] = _pekan(meta.t_buat)
    meta = meta.merge(pp, on="id", how="left")
    meta["ada_swap"] = meta.n_swap.fillna(0) > 0
    e = E[E.umur_jam <= jam].copy()
    e["pekan"] = e.id.map(meta.set_index("id").pekan)
    per_pool = e.groupby("id").agg(n_ep=("n_swap", "size"), usd_beli=("usd_beli", "sum"),
                                   untung=("untung_beli", "sum"), dev_min=("dev_min", "min"))
    meta["diskon"] = meta.id.isin(per_pool.index)
    w = meta.groupby("pekan").agg(pool_baru=("id", "size"), dengan_swap=("ada_swap", "sum"),
                                  sempat_diskon=("diskon", "sum"))
    ge = e.groupby("pekan")
    w["episode"] = ge.size()
    w["lama_median_dtk"] = ge.lama_dtk.median()
    w["lama_p90_dtk"] = ge.lama_dtk.quantile(0.9)
    w["reaksi_median_dtk"] = ge.jeda_reaksi_dtk.median()
    w["usd_beli_bawah_batas"] = ge.usd_beli.sum()
    w["untung_pembeli"] = ge.untung_beli.sum()
    w["kapasitas_median"] = ge.kap_quote.median()
    w["pengambil_beda"] = ge.pengirim_beli1.nunique()
    return w.fillna(0), e


def _fmt_dtk(x: float) -> str:
    if not np.isfinite(x):
        return "-"
    if x < 120:
        return f"{x:.1f} dtk"
    if x < 7200:
        return f"{x / 60:.1f} mnt"
    return f"{x / 3600:.1f} jam"


if __name__ == "__main__":
    tahap = sys.argv[1] if len(sys.argv) > 1 else ""
    if tahap == "pecah":
        pecah_besar()
    elif tahap == "swap":
        pecah_besar()
        unduh_swap()
    elif tahap == "swap_saham":
        unduh_swap(saham=True)
    elif tahap == "waktu":
        print(waktu().tail())
    elif tahap == "acuan":
        print(acuan_eth().tail())
        print(acuan_saham().groupby("sym").t.agg(["min", "max", "size"]))
    elif tahap == "pecahan":
        print(pecahan_semua().head(40).to_string())
    elif tahap == "cari":
        print(cari_ss().to_string())
    elif tahap == "proses":
        proses()
    elif tahap == "oracle":
        unduh_oracle()
    elif tahap == "potret_resmi":
        print(potret_resmi().head(30).to_string())
    elif tahap == "grup":
        print(json.dumps(grup(), indent=1)[:3000])
