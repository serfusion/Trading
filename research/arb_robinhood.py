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


TOL_SAHAM = "3min"   # toleransi acuan saham: "3min" = hanya jam bursa; "4D" = close terakhir ('basi') di luar jam bursa


def _harga_ref(refs: dict, ref: np.ndarray, t: pd.DatetimeIndex) -> np.ndarray:
    from .chain_baru_uji import _ref_at
    out = np.full(len(t), np.nan)
    for r in set(ref):
        m = ref == r
        if r == "USD":
            out[m] = 1.0
        elif isinstance(r, str) and r in refs:
            out[m] = _ref_at(refs[r], pd.DatetimeIndex(t[m]), "3min" if r == "ETH" else TOL_SAHAM)
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
    (saham: semua riwayat; ETH/WETH/USDG: hari pertama tiap pool = batas data riset lama).
    Menghasilkan (nama, fungsi) — data baru dihitung saat fungsi dipanggil (bagian yang sudah tersimpan dilewati)."""
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
    def baru_k(k, gp):
        sw = dsb.to_table(columns=COLS, filter=ds.field("id").isin(gp)).to_pandas().drop_duplicates(["tx", "li"])
        print(f"  kandidat baru kelompok {k + 1}: {len(sw):,} swap", flush=True)
        return _nilai_df(sw, meta, refs, blk, None)

    for k, gp in enumerate(_kelompok(nb, 1_500_000)):
        yield f"baru{k:02d}", (lambda k=k, gp=gp: baru_k(k, gp))
    f = ONCHAIN / "robinhood_swap.parquet"
    n = pd.read_parquet(f, columns=["id"]).id.astype(str).value_counts()
    grp = _kelompok(n, 2_000_000)
    dset = ds.dataset(f)

    def lama_k(k, gp, rentang=None):
        flt = ds.field("id").isin(gp)
        if rentang:   # potongan waktu satu pool besar: baris blok < b_mulai = pemanasan (harga pra), dibuang
            bw, b_mulai, b_akhir = rentang
            flt = flt & (ds.field("blok") >= bw) & (ds.field("blok") < b_akhir)
        sw = dset.to_table(columns=["id", "blok", "li", "sender", "a0", "a1", "sqrtp", "L", "txh"],
                           filter=flt).to_pandas()
        sw["id"] = sw.id.astype(str)
        print(f"  resmi lama kelompok {k + 1}/{len(grp)}{' potongan ' + str(rentang) if rentang else ''}: "
              f"{len(sw):,} swap", flush=True)
        x = _nilai_df(sw, meta, refs, blk, liq)
        del sw
        if rentang:
            x = x[x.blok >= rentang[1]].reset_index(drop=True)
        return x

    POTONG = 1_200_000   # RAM: pool tunggal > 2 jt swap dipotong per waktu (episode yang melintasi potongan terbelah)
    for k, gp in enumerate(grp):
        if len(gp) == 1 and n[gp[0]] > 2_000_000:
            b = np.sort(dset.to_table(columns=["blok"], filter=ds.field("id").isin(gp)).column("blok").to_numpy())
            cuts = [0]
            for i in range(POTONG, len(b), POTONG):
                j = int(np.searchsorted(b, b[i], "left"))      # potong di awal blok
                if j > cuts[-1]:
                    cuts.append(j)
            cuts.append(len(b))
            for h in range(len(cuts) - 1):
                i0, i1 = cuts[h], cuts[h + 1]
                bw = int(b[i0 - 1]) if i0 > 0 else int(b[0])
                ren = (bw, int(b[i0]), int(b[i1]) if i1 < len(b) else int(b[-1]) + 1)
                yield f"lama{k:02d}{chr(97 + h)}", (lambda k=k, gp=gp, ren=ren: lama_k(k, gp, ren))
            continue
        yield f"lama{k:02d}", (lambda k=k, gp=gp: lama_k(k, gp))


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
    m = meta.set_index("id")
    rows = []
    t = x.t.to_numpy()
    blok = x.blok.to_numpy()
    beli = (x.q_aset.to_numpy() > 0) & (x.usd_quote.to_numpy() < 0)
    # episode = run berurutan disc (dipotong di batas pool); awal = start, akhir = sebelum disc putus / pool ganti
    st_ix = np.flatnonzero(start)
    end = disc & (lastp | ~np.r_[disc[1:], False] | np.r_[start[1:], False])
    en_ix = np.flatnonzero(end)
    assert len(st_ix) == len(en_ix)
    for r0, r1 in zip(st_ix, en_ix):
        ix = np.arange(r0, r1 + 1)
        pid = ids[r0]
        if x.dev_pasca.iat[r1] > batas or not np.isfinite(x.dev_pasca.iat[r1]):
            cara, t_end = "ditutup swap", t[r1]
        elif not lastp[r1]:
            cara, t_end = "pasif (acuan/likuiditas berubah)", t[r1 + 1]
        else:
            cara, t_end = "masih terbuka (data berakhir)", pd.NaT
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
    e["t_tutup"] = pd.to_datetime(e.t_tutup, utc=True)
    e["t_beli1"] = pd.to_datetime(e.t_beli1, utc=True)
    e["lama_dtk"] = (e.t_tutup - e.t_mulai).dt.total_seconds()
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


PROSES_PARTS = ARB / "robinhood_proses_parts"


def _rss_gb() -> float:
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def proses() -> None:
    """Per bagian: episode diskon (-5% & -2%), pecahan, ringkasan per pool, swap ringkas -> disimpan per bagian di
    robinhood_proses_parts/ (bisa dilanjutkan), lalu digabung."""
    PROSES_PARTS.mkdir(exist_ok=True)
    meta = None
    for ring_i, (nama, buat) in enumerate(bagian()):
        fe, fc, fpp = (PROSES_PARTS / f"{nama}_{s}.parquet" for s in ("ep", "pc", "pp"))
        fp = ARB / f"robinhood_nilai_bernilai_{ring_i:02d}.parquet"
        if fe.exists() and fc.exists() and fpp.exists() and fp.exists():
            print(f"  {nama}: sudah ada, dilewati", flush=True)
            continue
        if meta is None:
            meta = pd.read_parquet(ARB / "robinhood_pool_bernilai.parquet")
        x = buat()
        e5 = episode(x, meta)
        e2 = episode(x, meta, batas=-0.02)
        for e, b in ((e5, -0.05), (e2, -0.02)):
            if len(e):
                e["batas"] = b
        pd.concat([e for e in (e5, e2) if len(e)] or [pd.DataFrame()], ignore_index=True).to_parquet(fe)
        pecahan(x).to_parquet(fc)
        x.groupby("id", observed=True).agg(
            n_swap=("blok", "size"), t_swap1=("t", "min"), t_swap_akhir=("t", "max"),
            dev_pra_min=("dev_pra", "min"), dev_pra_med_abs=("dev_pra", lambda v: v.abs().median()),
            untung_pos=("untung_usd", lambda v: v[v > 0].sum()), untung_bersih=("untung_usd", "sum"),
            notional=("usd_aset", lambda v: v.abs().sum())).reset_index().to_parquet(fpp)
        r = x[(x.dev_pra.abs() >= 0.005) | (x.untung_usd.abs() >= 1) | (x.dev_eks.abs() >= 0.005)]
        r = r.drop(columns=["sqrtp", "L", "q_quote"])
        for c in ("id", "sender", "jenis", "pair", "aset", "sumber", "tx"):
            r[c] = r[c].astype("category")
        r.to_parquet(fp, compression="zstd")
        print(f"  {nama}: {len(x):,} swap, ringkas {len(r):,} -> {fp.name} ({fp.stat().st_size / 1e6:.1f} MB), "
              f"episode {len(e5):,}/{len(e2):,}, RSS maks {_rss_gb():.2f} GB", flush=True)
        del x, r, e5, e2
    gab = lambda s: [pd.read_parquet(f) for f in sorted(PROSES_PARTS.glob(f"*_{s}.parquet"))]  # noqa: E731
    E = pd.concat([e for e in gab("ep") if len(e)], ignore_index=True)
    E.to_parquet(ARB / "robinhood_episode_diskon.parquet")
    P = [p for p in gab("pc") if len(p)]
    P = pd.concat(P, ignore_index=True) if P else pd.DataFrame()
    P.to_parquet(ARB / "robinhood_pecahan.parquet")
    pp = pd.concat(gab("pp"), ignore_index=True)
    pp = pp.groupby("id", as_index=False).agg(        # pool besar yang dipotong waktu muncul di > 1 bagian
        n_swap=("n_swap", "sum"), t_swap1=("t_swap1", "min"), t_swap_akhir=("t_swap_akhir", "max"),
        dev_pra_min=("dev_pra_min", "min"), dev_pra_med_abs=("dev_pra_med_abs", "median"),
        untung_pos=("untung_pos", "sum"), untung_bersih=("untung_bersih", "sum"), notional=("notional", "sum"))
    pp.to_parquet(ARB / "robinhood_per_pool_bernilai.parquet")
    print(f"episode {len(E):,}, pecahan {len(P):,}")



# ---------------------------------------------------------------- potret token RESMI: pool tipis vs pool utama
S_FEE, S_TS = "0xddca3f43", "0xd0c93a7c"


def potret_resmi(ukuran=(3, 25, 100, 300), gas_usd: float | None = None, semua: bool = False) -> pd.DataFrame:
    """Aset resmi (WETH/ETH + 16 saham) ber-quote USDG: beli di pool termurah / jual di pool utama (terdalam) atau
    sebaliknya. Leg pool tipis dikuotasi persis (V4Quoter / simulasi v3 lintas tick dengan fee & tickSpacing asli dari
    kontrak / produk-konstan v2 fee 0,3%), leg pool utama = mid x (1 - fee) (pool utama >= 100x ukuran)."""
    g = gas_usd if gas_usd is not None else A.gas_swap_usd(NET)
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet",
                         columns=["jenis", "emitter", "blok", "pool", "c0", "c1", "fee", "ts", "hooks", "d0", "d1"])
    sp = sp.drop_duplicates("pool")
    if semua:
        _pakai_saham_semua()
    aset_resmi = {WETH, ETH, *SAHAM}
    m = ((sp.c0 == USDG) & sp.c1.isin(aset_resmi)) | ((sp.c1 == USDG) & sp.c0.isin(aset_resmi))
    sp = sp[m & sp.jenis.isin(["v4", "v3", "slip", "alg", "algc", "v2", "solid", "aero"])]
    sp = sp[(sp.jenis != "v4") | (sp.emitter == PM)].copy()
    # pabrik 0x831880bd = pair "oracle/PMM": eksekusi di harga pasar, cadangan getReserves menyesatkan -> dikeluarkan
    n_or = int((sp.emitter == PABRIK_ORACLE).sum())
    sp = sp[sp.emitter != PABRIK_ORACLE]
    sp.loc[sp.c0 == ETH, "d0"] = 18
    print(f"potret resmi: {len(sp):,} pool aset resmi/USDG (+{n_or} pool oracle 0x831880bd dikeluarkan)", flush=True)
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
    utm = st.set_index("pool", drop=False)
    v3p = st[st.pool.isin(set(cal.pool) | set(cal.pool_utama)) & st.jenis.isin(["v3", "slip", "alg", "algc"])].copy()
    v3p["ts"] = v3p.ts.fillna(60).clip(lower=1).astype(int)
    ticks = A._v3_ticks(NET, v3p) if len(v3p) else {}

    def leg(r, z, amt):
        f = r.fee_asli / 1e6
        if r.jenis in ("v3", "slip", "alg", "algc"):
            return A._v3_sim(amt, z, r.sqrtp, r.L, int(r.tick), f, ticks.get(r.pool, {}))
        if r.jenis in ("v2", "solid", "aero"):
            return A._v2_out(amt, r.r0 if z else r.r1, r.r1 if z else r.r0, f)
        return None

    def kuot(daftar):
        """Kuotasi PERSIS banyak leg: v3/v2 disimulasikan, v4 lewat V4Quoter (revert = 0)."""
        hasil, legs4, idx4 = {}, [], []
        for r, z, amt, k in daftar:
            if not amt or amt <= 0:
                hasil[k] = 0.0
                continue
            o = leg(r, z, amt)
            if o is None:
                legs4.append((r.c0, r.c1, r.fee, r.ts, r.hooks, z, amt))
                idx4.append(k)
            else:
                hasil[k] = o
        for k, o in zip(idx4, A._q_v4(NET, legs4)):
            hasil[k] = o
        return hasil

    dq = lambda r: r.d0 if r.c0 == USDG else r.d1   # noqa: E731  desimal USDG
    da = lambda r: r.d1 if r.c0 == USDG else r.d0   # noqa: E731  desimal aset
    # leg 1: murah -> USDG ke aset di pool tipis; mahal -> USDG ke aset di pool utama
    l1 = []
    for r in cal.itertuples():
        u = utm.loc[r.pool_utama]
        p1 = r if r.dev_vs_utama < 0 else u
        for usd in ukuran:
            l1.append((p1, p1.c0 == USDG, usd * 10.0 ** dq(p1), (r.pool, usd)))
    h1 = kuot(l1)
    # leg 2: jual aset hasil leg 1 (murah -> di pool utama; mahal -> di pool tipis) — PERSIS, bukan harga mid
    l2 = []
    for r in cal.itertuples():
        u = utm.loc[r.pool_utama]
        p2 = u if r.dev_vs_utama < 0 else r
        for usd in ukuran:
            l2.append((p2, p2.c0 != USDG, h1.get((r.pool, usd), 0.0), (r.pool, usd)))
    h2 = kuot(l2)
    rows = []
    for r in cal.itertuples():
        murah = r.dev_vs_utama < 0
        u = utm.loc[r.pool_utama]
        p1, p2 = (r, u) if murah else (u, r)
        row = {"aset": r.aset, "simbol": SAHAM.get(r.aset, "WETH" if r.aset == WETH else "ETH"), "pool": r.pool,
               "jenis": r.jenis, "emitter": r.emitter, "hooks": r.hooks, "fee": r.fee_asli, "harga": r.harga,
               "harga_utama": r.harga_utama, "dev_vs_utama": r.dev_vs_utama, "dalam2": r.dalam2,
               "dalam2_utama": r.dalam2_utama, "pool_utama": r.pool_utama, "jenis_utama": u.jenis,
               "arah": "beli di pool ini" if murah else "jual ke pool ini"}
        for usd in ukuran:
            o1 = h1.get((r.pool, usd), 0.0)
            o2 = h2.get((r.pool, usd), 0.0)
            row[f"aset_{usd}"] = o1 / 10.0 ** da(p1)
            row[f"untung_{usd}"] = o2 / 10.0 ** dq(p2) - usd - 2 * g
            # pembanding lama: leg pool utama = harga mid x (1 - fee) (menyesatkan bila pool utama satu sisi)
            row[f"untung_mid_{usd}"] = (o1 / 10.0 ** da(p1) * r.harga_utama * (1 - r.fee_utama) if murah
                                        else o2 / 10.0 ** dq(p2)) - usd - 2 * g
            row[f"leg2_nol_{usd}"] = bool(o1 > 0 and o2 <= 0)
        rows.append(row)
    df = pd.DataFrame(rows)
    if len(df):
        df["untung_terbaik"] = df[[f"untung_{u}" for u in ukuran]].max(axis=1)
        df = df.sort_values("untung_terbaik", ascending=False)
    suf = "_semua" if semua else ""
    df.to_parquet(ARB / f"robinhood_potret_resmi{suf}.parquet")
    st.drop(columns=[c for c in ("tx", "sqrtp0") if c in st]).to_parquet(ARB / f"robinhood_potret_resmi{suf}_pool.parquet")
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
    (hanya bermakna untuk USDG resmi). Dibaca per file (hemat RAM): hanya baris BELI, kolom string jadi kategori."""
    import pyarrow.parquet as pq
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet",
                         columns=["pool", "c0", "c1", "d0", "d1", "s0", "s1", "n0", "n1", "blok"]).drop_duplicates("pool")
    resmi = {WETH, ETH, CRCL}
    a0p = sp.c0.isin(resmi) & ~sp.c1.isin(resmi)
    a1p = sp.c1.isin(resmi) & ~sp.c0.isin(resmi)
    sp = sp[a0p | a1p].set_index("pool")
    sp["aset0"] = sp.c0.isin(resmi)
    idx = pd.Index(sp.index)          # mesin hash dibangun sekali (isin(set) 1,4 jt alamat = 14 dtk per file)
    keep = []
    for f in sorted(PARTS.glob("swap_*.parquet")):
        if pq.ParquetFile(f).metadata.num_rows == 0:
            continue
        sw = pd.read_parquet(f, columns=["id", "blok", "li", "tx", "sender", "a0", "a1"])
        sw = sw[idx.get_indexer(sw.id.to_numpy()) >= 0]
        if not len(sw):
            continue
        j = sp.reindex(sw.id.to_numpy())
        a0 = j.aset0.to_numpy(dtype=bool)
        d0, d1 = j.d0.clip(lower=0).to_numpy(), j.d1.clip(lower=0).to_numpy()
        qa = np.where(a0, sw.a0 / 10.0 ** d0, sw.a1 / 10.0 ** d1)
        qq = np.where(a0, sw.a1 / 10.0 ** d1, sw.a0 / 10.0 ** d0)
        raw_q = np.where(a0, sw.a1, sw.a0)
        b = pd.DataFrame({"id": sw.id.to_numpy(), "blok": sw.blok.to_numpy(), "li": sw.li.to_numpy(),
                          "tx": sw.tx.to_numpy(), "sender": sw.sender.to_numpy(), "q_aset": qa, "q_quote": qq,
                          "raw_in": -raw_q})
        b = b[(b.q_aset > 0) & (b.q_quote < 0)]
        for c in ("id", "sender"):
            b[c] = b[c].astype("category")
        keep.append(b)
        del sw, j
    b = pd.concat(keep, ignore_index=True)
    for c in ("id", "sender"):
        b[c] = b[c].astype(str).astype("category")
    b = b.drop_duplicates(["tx", "li"])
    b["harga_tersirat"] = -b.q_quote / b.q_aset
    # selisih PER SWAP thd ETH Binance (bermakna hanya bila quote = USDG resmi & aset WETH/ETH)
    from .chain_baru_uji import _ref_at
    from .chain_onchain import ke_waktu
    jj = sp.reindex(b.id.astype(str).to_numpy())
    asetw = np.where(jj.aset0.to_numpy(dtype=bool), jj.c0, jj.c1)
    quote = np.where(jj.aset0.to_numpy(dtype=bool), jj.c1, jj.c0)
    ok = (quote == USDG) & np.isin(asetw, [WETH, ETH])
    b["dev"] = np.nan
    if ok.any():
        tt = ke_waktu(b.blok.to_numpy()[ok].astype(float), blok_ts())
        b.loc[ok, "dev"] = b.harga_tersirat.to_numpy()[ok] / _ref_at(acuan_eth(), pd.DatetimeIndex(tt), "3min") - 1
    g = b.groupby(["sender", "id", "raw_in"], observed=True)
    a = g.agg(n=("blok", "size"), n_blok=("blok", "nunique"), blok0=("blok", "min"), blok1=("blok", "max"),
              q_in=("q_quote", "first"), harga_med=("harga_tersirat", "median"),
              harga_min=("harga_tersirat", "min"), harga_max=("harga_tersirat", "max"), tx1=("tx", "first"),
              dev_med=("dev", "median"), dev_min=("dev", "min")).reset_index()
    a["q_in"] = -a.q_in
    a = a[(a.n >= min_n) & (a.n_blok >= 3)].sort_values("n", ascending=False)
    a["id"] = a.id.astype(str)
    j = sp.reindex(a.id.to_numpy())
    a0 = j.aset0.to_numpy(dtype=bool)
    a["aset"] = np.where(a0, j.s0, j.s1)
    a["quote_sym"] = np.where(a0, j.s1, j.s0)
    a["quote_nama"] = np.where(a0, j.n1, j.n0)
    a["quote"] = np.where(a0, j.c1, j.c0)
    a["quote_resmi"] = a.quote == USDG
    a["sender"] = a.sender.astype(str)
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


# ---------------------------------------------------------------- SEMUA token saham resmi (bukan hanya 16)
MINTER_SAHAM = "0x2b94105fff37630f98e1f24811dad588fc5c3a87"   # EOA yang mengirim tx mint CRCL/NVDA/... resmi


def resmi_semua() -> pd.DataFrame:
    """Token '• Robinhood Token' dengan kode proxy IDENTIK dengan CRCL resmi dan mint pertama dikirim MINTER_SAHAM
    (minter yang sama dengan 16 token daftar putih lama). Hasil: robinhood_token_resmi_semua.parquet."""
    import hashlib
    f = ARB / "robinhood_token_resmi_semua.parquet"
    if f.exists():
        return pd.read_parquet(f)
    tok = pd.read_parquet(ARB / "robinhood_token.parquet")
    c = tok[tok.name.str.contains("Robinhood Token", case=False, na=False)].copy()
    with ThreadPoolExecutor(8) as ex:
        codes = list(ex.map(lambda a: rpc(NET, "eth_getCode", [a, "latest"]), c.alamat))
    c["code_md5"] = [hashlib.md5(x.encode()).hexdigest()[:8] for x in codes]
    c = c[c.code_md5 == c.set_index("alamat").code_md5.get(CRCL)].copy()
    top, z, first = A.head(NET), "0x" + "0" * 64, {}
    adr = list(c.alamat)
    for i in range(0, len(adr), 200):
        lg = A.scan(NET, {"address": adr[i:i + 200], "topics": [A.T_TRANSFER, z]}, 1, top, 100_000, label=f"mint {i}",
                    fn=lambda x: (x["address"].lower(), int(x["blockNumber"], 16), x["transactionHash"]))
        for a, b, h in sorted(lg, key=lambda q: q[1]):
            first.setdefault(a, (b, h))
    with ThreadPoolExecutor(8) as ex:
        frm = dict(zip(first, ex.map(lambda a: rpc(NET, "eth_getTransactionByHash", [first[a][1]])["from"].lower(), first)))
    c["mint1_blok"] = c.alamat.map(lambda a: first.get(a, (np.nan,))[0])
    c["mint1_dari"] = c.alamat.map(frm)
    c["resmi_minter"] = c.mint1_dari == MINTER_SAHAM
    c.to_parquet(f)
    return c


def saham_semua() -> dict:
    """alamat -> ticker untuk SEMUA token saham resmi (192 per 9 Okt 2026)."""
    c = resmi_semua()
    c = c[c.resmi_minter]
    return dict(zip(c.alamat, c.symbol.str.upper()))


def _pakai_saham_semua() -> None:
    """Perluas NILAI/SAHAM modul ini ke semua token saham resmi (acuan = ticker NYSE/Nasdaq)."""
    for a, t in saham_semua().items():
        SAHAM.setdefault(a, t)
        NILAI.setdefault(a, t)


PELUNCURAN = ARB / "robinhood_peluncuran_parts"
BLOK_JAM = 3600 / 0.1004          # blok Robinhood ±0,1004 dtk (sampel 100 rb blok)


def _pool_peluncuran(hari_token: float = 7.0) -> pd.DataFrame:
    """Pool token saham resmi TAMBAHAN (di luar 16) x USDG/WETH/ETH yang dibuat <= hari_token hari setelah mint
    pertama token itu (= gelombang peluncuran)."""
    c = resmi_semua()
    c = c[c.resmi_minter & ~c.alamat.isin(set(RH_SAHAM.values()))]
    m1 = dict(zip(c.alamat, c.mint1_blok))
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet",
                         columns=["pool", "jenis", "emitter", "blok", "c0", "c1", "d0", "d1", "fee", "ts", "hooks",
                                  "sqrtp0"]).drop_duplicates("pool")
    q = {USDG, WETH, ETH}
    ex = set(c.alamat)
    m = (sp.c0.isin(ex) & sp.c1.isin(q)) | (sp.c1.isin(ex) & sp.c0.isin(q))
    sp = sp[m & sp.jenis.isin(["v4", "v3", "slip", "alg", "algc", "v2", "solid", "aero", "lb"])].copy()
    sp = sp[(sp.jenis != "v4") | (sp.emitter == PM)]
    sp["token"] = np.where(sp.c0.isin(ex), sp.c0, sp.c1)
    sp["mint1"] = sp.token.map(m1)
    sp = sp[sp.blok <= sp.mint1 + hari_token * 24 * BLOK_JAM]
    return sp


def unduh_peluncuran(jam: float = 72.0, ember: int = 500_000) -> None:
    """Swap pool peluncuran (lihat _pool_peluncuran) dalam `jam` pertama sejak pool dibuat. Pool dikelompokkan per
    `ember` blok pembuatan; tiap kelompok satu rentang blok (bisa dilanjutkan: file per kelompok)."""
    PELUNCURAN.mkdir(exist_ok=True)
    sp = _pool_peluncuran()
    jenis_alamat = dict(zip(sp.pool, sp.jenis))
    span = A.SPAN_ALAMAT[NET]
    top = A.head(NET)
    sp["ember"] = sp.blok // ember
    print(f"peluncuran: {len(sp):,} pool, {sp.token.nunique()} token, {sp.ember.nunique()} kelompok", flush=True)
    for e, g in sp.groupby("ember"):
        f = PELUNCURAN / f"swap_{e:04d}.parquet"
        if f.exists():
            continue
        b0, b1 = int(g.blok.min()), min(int(g.blok.max() + jam * BLOK_JAM), top)
        rows = []
        v4 = list(g[g.jenis == "v4"].pool)
        lb = list(g[g.jenis == "lb"].pool)
        lain = list(g[~g.jenis.isin(["v4", "lb"])].pool)
        filt = [({"address": PM, "topics": [T_SWAP, v4[i:i + 500]]}, lambda x: A._dec_swap(x, jenis_alamat))
                for i in range(0, len(v4), 500)]
        filt += [({"address": lain[i:i + 200], "topics": [[T3_SWAP, A.T_V2_SWAP, A.T_SOLID_SWAP]]},
                  lambda x: A._dec_swap(x, jenis_alamat)) for i in range(0, len(lain), 200)]
        filt += [({"address": lb[i:i + 200], "topics": [T_LB_SWAP]}, _dec_lb) for i in range(0, len(lb), 200)]
        for flt, fn in filt:
            rows += A.scan(NET, flt, b0, b1, span, fn=fn, label=f"peluncuran {e}")
        d = pd.DataFrame(rows, columns=COLS)
        lahir = dict(zip(g.pool, g.blok))
        d = d[d.blok <= d.id.map(lahir) + jam * BLOK_JAM]
        d.to_parquet(f, compression="zstd")
        print(f"  kelompok {e}: {len(g)} pool, blok {b0:,}-{b1:,}, {len(d):,} swap", flush=True)


def acuan_peluncuran(hari: int = 11) -> pd.DataFrame:
    """Twelve Data 1 menit tiap ticker token tambahan: [hari mint pertama, + hari] (jam bursa AS). Bisa dilanjutkan."""
    import os
    import urllib.parse
    import urllib.request
    from .chain_onchain import ke_waktu
    f = ARB / "robinhood_acuan_peluncuran_1m.parquet"
    old = pd.read_parquet(f) if f.exists() else pd.DataFrame(columns=["sym", "t", "close"])
    sp = _pool_peluncuran()
    c = resmi_semua()
    c = c[c.alamat.isin(set(sp.token))]
    c["t1"] = ke_waktu(c.mint1_blok.to_numpy().astype(float), blok_ts())
    key = os.environ.get("TWELVEDATA_API_KEY", "")
    sudah = set(old.sym) | set(json.loads((ARB / "robinhood_acuan_peluncuran_gagal.json").read_text())
                               if (ARB / "robinhood_acuan_peluncuran_gagal.json").exists() else [])
    gagal = []
    rows = []
    for r in c.sort_values("t1").itertuples():
        sym = r.symbol.upper()
        if sym in sudah:
            continue
        a = pd.Timestamp(r.t1).floor("D")
        q = urllib.parse.urlencode({"symbol": sym, "interval": "1min", "start_date": f"{a:%Y-%m-%d} 00:00:00",
                                    "end_date": f"{a + pd.Timedelta(days=hari):%Y-%m-%d} 00:00:00", "outputsize": 5000,
                                    "timezone": "UTC", "order": "ASC", "apikey": key})
        d = {}
        for k in range(4):
            try:
                with urllib.request.urlopen("https://api.twelvedata.com/time_series?" + q, timeout=60) as rr:
                    d = json.loads(rr.read())
            except Exception:  # noqa: BLE001
                time.sleep(10)
                continue
            if "credits" in str(d.get("message", "")).lower():
                time.sleep(61)
                continue
            break
        time.sleep(7.6)
        v = d.get("values", []) or []
        if not v:
            gagal.append(sym)
        rows += [{"sym": sym, "t": pd.Timestamp(x["datetime"], tz="UTC"), "close": float(x["close"])} for x in v]
        print(f"  {sym}: {len(v)} menit ({d.get('status')} {str(d.get('message', ''))[:60]})", flush=True)
        out = pd.concat([old, pd.DataFrame(rows)], ignore_index=True) if rows else old
        out.to_parquet(f)
        (ARB / "robinhood_acuan_peluncuran_gagal.json").write_text(json.dumps(sorted(set(gagal) | (sudah - set(old.sym)))))
    return pd.read_parquet(f) if f.exists() else old


def proses_peluncuran(batas: float = -0.05, basi: bool = False) -> pd.DataFrame:
    """Nilai swap pool peluncuran thd acuan saham Twelve Data (jam bursa, toleransi 3 mnt) / ETH Binance, episode
    diskon, untung per aksi (netting per tx). Hasil: robinhood_peluncuran_{nilai,episode}.parquet."""
    global TOL_SAHAM
    TOL_SAHAM = "4D" if basi else "3min"
    suf = "_basi" if basi else ""
    _pakai_saham_semua()
    sp = _pool_peluncuran()
    meta = _orientasi(_meta())
    meta = meta[meta.id.isin(set(sp.pool))].copy()
    sw = pd.concat([pd.read_parquet(f) for f in sorted(PELUNCURAN.glob("swap_*.parquet"))], ignore_index=True)
    sw = sw.drop_duplicates(["tx", "li"])
    for c in ("a0", "a1", "sqrtp", "L"):
        sw[c] = pd.to_numeric(sw[c], errors="coerce").astype(float)
    sw["blok"] = sw.blok.astype("int64")
    sw["li"] = sw.li.astype("int64")
    refs = _refs()
    ac = pd.read_parquet(ARB / "robinhood_acuan_peluncuran_1m.parquet")
    for sym, g in ac.groupby("sym"):
        s_ = g.set_index("t")["close"]
        s_.index = pd.DatetimeIndex(s_.index).floor("min")
        refs[sym] = s_[~s_.index.duplicated(keep="last")].sort_index()
    x = _nilai_df(sw, meta, refs, blok_ts(), None)
    x.drop(columns=["sqrtp", "L"]).to_parquet(ARB / f"robinhood_peluncuran_nilai{suf}.parquet", compression="zstd")
    e = episode(x, meta, batas)
    if len(e):
        nol = "0x" + "0" * 40
        hk = dict(zip(sp.pool, sp.hooks.fillna("")))
        e["hook"] = e.id.map(lambda i: bool(hk.get(i, "")) and hk.get(i, "") != nol)
        per_tx = x.groupby("txh").untung_usd.sum()
        b = x[(x.dev_pra <= batas) & (x.q_aset > 0) & (x.usd_quote < 0)][["id", "blok", "li", "txh"]].sort_values("blok")
        e = e.reset_index(drop=True)
        e["eid"] = np.arange(len(e))
        ep = e[["id", "blok_swap1", "eid"]].rename(columns={"blok_swap1": "blok"}).sort_values("blok")
        b = pd.merge_asof(b, ep, on="blok", by="id", direction="backward").dropna(subset=["eid"])
        b = b.sort_values(["blok", "li"]).drop_duplicates("txh")
        b["untung_tx"] = b.txh.map(per_tx)
        g = b.groupby("eid").agg(n_aksi=("txh", "size"), untung_aksi=("untung_tx", "sum"))
        e = e.join(g, on="eid").fillna({"n_aksi": 0, "untung_aksi": 0})
        e["jeda_blok"] = e.blok_beli1 - e.blok_mulai
    e.to_parquet(ARB / f"robinhood_peluncuran_episode{suf}.parquet")
    hk = dict(zip(sp.pool, sp.hooks.fillna("")))
    y = _cermin(x)
    ep2 = episode(y, meta, batas)
    if len(ep2):
        ep2 = _aksi_dari(y, ep2, batas, hk)
        ep2["dev_awal"], ep2["dev_min"] = -ep2.dev_awal, -ep2.dev_min
        ep2 = ep2.rename(columns={"usd_beli": "usd_jual", "n_beli": "n_jual"})
    ep2.to_parquet(ARB / f"robinhood_peluncuran_premi{suf}.parquet")
    meta.to_parquet(ARB / "robinhood_peluncuran_pool.parquet")
    TOL_SAHAM = "3min"
    return e


# ---------------------------------------------------------------- untung per AKSI (netting per transaksi)
def _ringkas() -> pd.DataFrame:
    """Gabungan robinhood_nilai_bernilai_*.parquet (swap |dev| >= 0,5% atau |untung| >= $1 — sisanya ±0)."""
    cols = ["id", "blok", "li", "t", "sender", "jenis", "pair", "sumber", "dev_pra", "dev_pasca", "dev_eks", "q_aset", "usd_aset",
            "usd_quote", "untung_usd", "txh", "blok_pra", "jeda_dtk", "umur_jam"]
    fs = sorted(ARB.glob("robinhood_nilai_bernilai_*.parquet"))
    x = pd.concat([pd.read_parquet(f, columns=cols) for f in fs], ignore_index=True)
    for c in ("id", "sender", "jenis", "pair", "sumber"):
        x[c] = x[c].astype(str).astype("category")
    x = x.drop_duplicates(["txh", "id", "li", "blok"])
    return x


def aksi(batas: float = -0.05) -> pd.DataFrame:
    """Episode diskon (batas -5%) + untung BERSIH per aksi: semua swap pool bernilai dalam tx yang sama dijumlahkan
    (jual-lalu-beli-balik dalam satu tx = ±0; arbitrase dua pool = untung sebenarnya). Pool v4 ber-hook ditandai:
    angka event Swap v4 tidak memuat delta hook (biaya/kurva kustom) -> bisa menyimpang dari transfer nyata."""
    x = _ringkas()
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet", columns=["pool", "hooks", "emitter"]).drop_duplicates("pool")
    hook = dict(zip(sp.pool, sp.hooks.fillna("")))
    nol = "0x" + "0" * 40
    x["hook"] = [bool(hook.get(i, "")) and hook.get(i, "") != nol for i in x.id.astype(str)]
    per_tx = x.groupby("txh").agg(untung_tx=("untung_usd", "sum"), n_swap_tx=("blok", "size"),
                                  n_pool_tx=("id", "nunique"), hook_tx=("hook", "any"))
    E = pd.read_parquet(ARB / "robinhood_episode_diskon.parquet")
    E = E[np.isclose(E.batas, batas)].copy().reset_index(drop=True)
    E["eid"] = np.arange(len(E))
    b = x[(x.dev_pra <= batas) & (x.q_aset > 0) & (x.usd_quote < 0)][["id", "blok", "li", "txh", "sender"]].copy()
    b["id"] = b.id.astype(str)
    b = b.sort_values("blok")
    ep = E[["id", "blok_swap1", "eid"]].rename(columns={"blok_swap1": "blok"}).sort_values("blok")
    b = pd.merge_asof(b, ep, on="blok", by="id", direction="backward")
    b = b.dropna(subset=["eid"])
    b["eid"] = b.eid.astype(int)
    b = b.sort_values(["blok", "li"]).drop_duplicates("txh")          # satu aksi dihitung sekali (episode pertama)
    b = b.join(per_tx, on="txh")
    g = b.groupby("eid").agg(n_aksi=("txh", "size"), untung_aksi=("untung_tx", "sum"),
                             aksi_hook=("hook_tx", "sum"), pengambil=("sender", "nunique"))
    E = E.join(g, on="eid")
    E[["n_aksi", "untung_aksi", "aksi_hook", "pengambil"]] = E[["n_aksi", "untung_aksi", "aksi_hook", "pengambil"]].fillna(0)
    E["hook"] = E.id.map(lambda i: bool(hook.get(i, "")) and hook.get(i, "") != nol)
    E["kelas"] = np.where(E.pair.str.match(r"^(WETH|ETH)/"), "ETH/WETH",
                          np.where(E.pair.str.endswith("/USDG"), "saham/USDG", "saham/ETH"))
    E["jeda_blok"] = E.blok_beli1 - E.blok_mulai
    E.to_parquet(ARB / "robinhood_episode_aksi.parquet")
    b.to_parquet(ARB / "robinhood_episode_aksi_tx.parquet")
    return E


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


def _cermin(x: pd.DataFrame) -> pd.DataFrame:
    """Balik arah: premi aset (harga pool >= acuan x 1,05) diperlakukan sebagai 'diskon' cermin; 'beli' = JUAL aset."""
    y = x.copy()
    for c in ("dev_pra", "dev_pasca", "dev_eks", "q_aset", "usd_quote", "usd_aset"):
        if c in y:
            y[c] = -y[c]
    for c in ("L", "sqrtp"):
        y[c] = np.nan
    return y


def _aksi_dari(x: pd.DataFrame, E: pd.DataFrame, batas: float, hook: dict) -> pd.DataFrame:
    """Tempel untung per aksi (netting per tx atas SEMUA swap x) ke episode E (kolom id, blok_swap1)."""
    nol = "0x" + "0" * 40
    per_tx = x.groupby("txh").untung_usd.sum()
    E = E.reset_index(drop=True).copy()
    E["eid"] = np.arange(len(E))
    b = x[(x.dev_pra <= batas) & (x.q_aset > 0) & (x.usd_quote < 0)][["id", "blok", "li", "txh", "sender"]].copy()
    b["id"] = b.id.astype(str)
    b = b.sort_values("blok")
    ep = E[["id", "blok_swap1", "eid"]].rename(columns={"blok_swap1": "blok"}).sort_values("blok")
    b = pd.merge_asof(b, ep, on="blok", by="id", direction="backward").dropna(subset=["eid"])
    b["eid"] = b.eid.astype(int)
    b = b.sort_values(["blok", "li"]).drop_duplicates("txh")
    b["untung_tx"] = b.txh.map(per_tx)
    g = b.groupby("eid").agg(n_aksi=("txh", "size"), untung_aksi=("untung_tx", "sum"), pengambil=("sender", "nunique"))
    E = E.join(g, on="eid")
    E[["n_aksi", "untung_aksi", "pengambil"]] = E[["n_aksi", "untung_aksi", "pengambil"]].fillna(0)
    E["hook"] = E.id.map(lambda i: bool(hook.get(i, "")) and hook.get(i, "") != nol)
    E["jeda_blok"] = E.blok_beli1 - E.blok_mulai
    return E


def aksi_premi(batas: float = -0.05) -> pd.DataFrame:
    """Arah sebaliknya: pool beraset bernilai yang harganya >= 5% DI ATAS acuan (aset dijual mahal ke pool). Dihitung
    dari swap ringkas (semua swap |dev| >= 0,5% atau |untung| >= $1 tersimpan -> deret episode hampir persis)."""
    x = _ringkas()
    x["id"] = x.id.astype(str)
    x["sender"] = x.sender.astype(str)
    x["tx"] = ""
    meta = pd.read_parquet(ARB / "robinhood_pool_bernilai.parquet")
    y = _cermin(x)
    E = episode(y, meta, batas)
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet", columns=["pool", "hooks"]).drop_duplicates("pool")
    hook = dict(zip(sp.pool, sp.hooks.fillna("")))
    E = _aksi_dari(y, E, batas, hook)
    E["dev_awal"], E["dev_min"] = -E.dev_awal, -E.dev_min
    E = E.rename(columns={"usd_beli": "usd_jual", "n_beli": "n_jual"})
    E["kelas"] = np.where(E.pair.str.match(r"^(WETH|ETH)/"), "ETH/WETH",
                          np.where(E.pair.str.endswith("/USDG"), "saham/USDG", "saham/ETH"))
    E.to_parquet(ARB / "robinhood_episode_premi.parquet")
    return E


def verif_hook(min_usd: float = 20.0) -> pd.DataFrame:
    """Aksi di pool v4 ber-hook dengan |untung event| >= min_usd dicek lewat receipt: arus ERC-20 bersih 'sisi
    pedagang' (semua alamat kecuali PoolManager, pool yang memancarkan Swap, hook, 0x0, kontrak WETH) dinilai acuan.
    ETH asli tidak terlihat (tanpa trace) -> hanya batas bawah bila ETH tidak di-wrap. Token tak bernilai dicatat."""
    from .chain_onchain import ke_waktu
    E = pd.read_parquet(ARB / "robinhood_episode_aksi.parquet")
    B = pd.read_parquet(ARB / "robinhood_episode_aksi_tx.parquet")
    B = B.join(E.set_index("eid")[["pair"]], on="eid")
    B = B[B.hook_tx & (B.untung_tx.abs() >= min_usd)].copy()
    sp = pd.read_parquet(ARB / "robinhood_semua_pool.parquet", columns=["pool", "hooks"]).drop_duplicates("pool")
    hooks = set(sp.hooks.dropna()) - {"", "0x" + "0" * 40}
    tok = pd.read_parquet(ARB / "robinhood_token.parquet").set_index("alamat")
    refs, blk = _refs(), blok_ts()

    def satu(r):
        b = rpc(NET, "eth_getBlockByNumber", [hex(int(r.blok)), False])
        pre = format(int(r.txh), "x").rjust(15, "0")
        c = [h for h in b["transactions"] if h[2:17] == pre]
        if not c:
            return None, {}
        rc = rpc(NET, "eth_getTransactionReceipt", [c[0]])
        pools = {lg["address"].lower() for lg in rc["logs"] if lg["topics"] and lg["topics"][0] in (T3_SWAP, A.T_V2_SWAP)}
        skip = {PM, "0x" + "0" * 40, WETH} | pools | hooks
        net = {}
        for lg in rc["logs"]:
            if not lg["topics"] or lg["topics"][0] != A.T_TRANSFER or len(lg["topics"]) != 3:
                continue
            t = lg["address"].lower()
            f, to = "0x" + lg["topics"][1][-40:], "0x" + lg["topics"][2][-40:]
            v = int(lg["data"][2:66] or "0", 16) / 10 ** int(tok.decimals.get(t, 18))
            if f not in skip:
                net[t] = net.get(t, 0) - v
            if to not in skip:
                net[t] = net.get(t, 0) + v
        return c[0], net

    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(satu, B.itertuples()))
    rows = []
    for r, (h, net), tt in zip(B.itertuples(), res, ke_waktu(B.blok.to_numpy(), blk)):
        usd, tak = 0.0, []
        for tk, v in net.items():
            ref = NILAI.get(tk)
            if ref is None:
                if abs(v) > 0:
                    tak.append(tok.symbol.get(tk, tk[:8]))
                continue
            usd += v * (1.0 if ref == "USD" else float(_harga_ref(refs, np.array([ref]), pd.DatetimeIndex([tt]))[0]))
        rows.append({"txh": r.txh, "tx": h, "pair": r.pair, "t": tt, "untung_event": r.untung_tx,
                     "untung_receipt": usd if h else np.nan, "token_tak_dinilai": ",".join(tak)})
    d = pd.DataFrame(rows)
    d.to_parquet(ARB / "robinhood_verif_hook.parquet")
    return d


def tabel_pekan(E: pd.DataFrame, pools: pd.DataFrame, jam: float = 72.0) -> pd.DataFrame:
    """Per pekan pembuatan pool (pekan 0 = 1-7 Jul 2026): pool baru bernilai, yang punya swap, yang sempat diskon
    >= 5% dalam `jam` pertama, episode, lama diskon, jeda reaksi (blok & detik), volume beli di bawah batas, untung
    per aksi (tanpa / dengan pool ber-hook), kapasitas median (USD), pengambil berbeda.
    E: episode (kolom id, umur_jam, lama_dtk, jeda_blok, n_aksi, usd_beli, untung_aksi, hook, kap_usd, pengirim_beli1)
    pools: id, t_buat, n_swap."""
    pools = pools.copy()
    pools["pekan"] = _pekan(pools.t_buat)
    e = E[(E.umur_jam <= jam) & E.id.isin(set(pools.id))].copy()
    e["pekan"] = e.id.map(pools.set_index("id").pekan)
    gp = pools.groupby("pekan")
    w = pd.DataFrame({"pool_baru": gp.size(), "dengan_swap": gp.n_swap.apply(lambda v: int((v.fillna(0) > 0).sum()))})
    w["sempat_diskon"] = e.groupby("pekan").id.nunique()
    ge = e.groupby("pekan")
    w["episode"] = ge.size()
    tutup = e[np.isfinite(e.lama_dtk)]
    w["lama_med_dtk"] = tutup.groupby("pekan").lama_dtk.median()
    w["lama_p90_dtk"] = tutup.groupby("pekan").lama_dtk.quantile(0.9)
    ada = e[(e.n_aksi > 0) & (e.jeda_blok >= 0)]
    w["reaksi_med_blok"] = ada.groupby("pekan").jeda_blok.median()
    w["reaksi_blok1_pct"] = ada.groupby("pekan").jeda_blok.apply(lambda v: float((v <= 1).mean()))
    w["usd_beli_tanpa_hook"] = e[~e.hook].groupby("pekan").usd_beli.sum()
    w["untung_tanpa_hook"] = e[~e.hook].groupby("pekan").untung_aksi.sum()
    w["untung_hook"] = e[e.hook].groupby("pekan").untung_aksi.sum()
    if "kap_usd" in e:
        w["kap_med_usd"] = ge.kap_usd.median()
    w["pengambil"] = e[e.n_aksi > 0].groupby("pekan").pengirim_beli1.nunique()
    return w.fillna(0).sort_index()


def _kap_usd(E: pd.DataFrame, meta: pd.DataFrame) -> pd.Series:
    """kap_quote (satuan token quote) -> USD (quote USDG = $1; ETH/WETH x ETH Binance saat episode mulai)."""
    from .chain_baru_uji import _ref_at
    rq = E.id.map(meta.set_index("id").ref_quote)
    eth = _ref_at(acuan_eth(), pd.DatetimeIndex(pd.to_datetime(E.t_mulai, utc=True)), "3min")
    return pd.Series(np.where(rq == "USD", E.kap_quote, np.where(rq == "ETH", E.kap_quote * eth, np.nan)), index=E.index)


def _fmt_dtk(x: float) -> str:
    if not np.isfinite(x):
        return "-"
    if x < 120:
        t = f"{x:.1f} dtk"
    elif x < 7200:
        t = f"{x / 60:.1f} mnt"
    else:
        t = f"{x / 3600:.1f} jam"
    return t.replace(".", ",")


def _rp(x: float) -> str:
    """USD gaya Indonesia: 1.234 / 12,3 / 0,05."""
    if not np.isfinite(x):
        return "-"
    a = abs(x)
    t = f"{x:,.0f}" if a >= 100 else (f"{x:,.1f}" if a >= 10 else f"{x:,.2f}")
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def _n(x) -> str:
    return f"{int(x):,}".replace(",", ".")


BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _tgl(t, jam: bool = True) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {BULAN[t.month - 1]}" + (f" {t:%H:%M}" if jam else "")


def _pct(x: float, d: int = 1) -> str:
    return "-" if not np.isfinite(x) else f"{x * 100:.{d}f}%".replace(".", ",")


def _tabel_teks(w: pd.DataFrame, judul_pekan=True) -> list[str]:
    awal = pd.Timestamp("2026-07-01")
    out = ["    pekan (mulai)    pool  swap diskon  ep  lama med   lama p90  reaksi med  <=1 blok  beli<-5% USD  untung(tanpa hook)  "
           "untung hook  kap med  pengambil"]
    for k, r in w.iterrows():
        tgl = (awal + pd.Timedelta(days=7 * int(k))).strftime("%d/%m")
        out.append(f"    {int(k):>3} ({tgl})     {int(r.pool_baru):>5} {int(r.dengan_swap):>5} {int(r.sempat_diskon):>6} {int(r.episode):>3}"
                   f"  {_fmt_dtk(r.lama_med_dtk) if r.episode else '-':>9}  {_fmt_dtk(r.lama_p90_dtk) if r.episode else '-':>9}"
                   f"  {(str(int(r.reaksi_med_blok)) + ' blok') if r.episode else '-':>10}  {_pct(r.reaksi_blok1_pct, 0) if r.episode else '-':>8}"
                   f"  {_rp(r.usd_beli_tanpa_hook):>12}  {_rp(r.untung_tanpa_hook):>18}  {_rp(r.untung_hook):>11}"
                   f"  {_rp(r.get('kap_med_usd', np.nan)) if r.episode else '-':>7}  {int(r.pengambil):>9}")
    return out


def _bagian_b1() -> list[str]:
    import pyarrow.parquet as pq
    from .chain_onchain import ke_waktu
    blk = blok_ts()
    top = json.loads((PARTS / "top_lanjut.json").read_text())["top"]
    t_top = ke_waktu(np.array([float(top)]), blk)[0]
    n = {}
    for f in PARTS.glob("swap_*.parquet"):
        k = f.stem.split("_")[1]
        k = "v4 PoolManager (tugas 1-6)" if k.isdigit() else ("pabrik oracle 0x831880bd" if k.startswith("oracle")
             else ("saham lain (DEX lain + v4 baru)" if k.startswith("s") else "WETH/CRCL kandidat (v3/v2/Algebra/LB/...)"))
        n[k] = n.get(k, 0) + pq.ParquetFile(f).metadata.num_rows
    nf = len(list(PARTS.glob("swap_*.parquet")))
    npl = sum(pq.ParquetFile(f).metadata.num_rows for f in PELUNCURAN.glob("swap_*.parquet"))
    lama = pq.ParquetFile(ONCHAIN / "robinhood_swap.parquet").metadata.num_rows
    L = ["B1. UNDUHAN SWAP POOL KANDIDAT — SELESAI",
         f"    robinhood_swap_parts/: {nf} file, {_n(sum(n.values()))} swap (s.d. blok {_n(top)} = {_tgl(t_top)} UTC 2026):",
         *[f"      {k:<42} {_n(v):>10}" for k, v in sorted(n.items(), key=lambda z: -z[1])],
         "    Semua 17 tugas lanjutan (12 tugas WETH/CRCL + 5 tugas saham di DEX lain) lengkap; tidak ada sub-jendela hilang.",
         "    Kenapa agen sebelumnya berhenti & '0 swap' di tugas 6/15:",
         "      - '0 swap' BUKAN galat RPC: tugas 6/15 = 3 pool v4 milik PoolManager KEDUA 0xf5b06ef9… (bukan Uniswap",
         "        resmi). Pindai penuh semua log alamat itu (blok 55,0 jt - head): 46 Initialize, hanya 2 Swap seumur hidup",
         "        (bukan di 3 pool itu) -> memang tidak pernah diperdagangkan. 18 pool v4 resmi baru (8 Okt) juga hanya 2 swap.",
         "      - Yang menghentikan proses: tugas 7/15 menampung ±1 juta swap pool WETH/USDG (diarbitrase bot tiap blok) di",
         "        memori (3,7 GB). Perbaikan: per 20 jendela x 100 rb blok, file <= 400 rb baris, bisa dilanjutkan; pool",
         "        'berat' (> 20 rb swap) berhenti diunduh setelah umur 7 hari (yang dicari = jendela peluncuran).",
         "      - Swap pabrik 0x831880bd (13 pool, 56 rb swap) memakai event Swap non-standar; harga eksekusinya = harga pasar",
         "        (oracle/PMM). Rasio cadangan getReserves menyesatkan (MSTR tampak -37%, NVDA -27%, SPY -40%, padahal",
         "        swap terakhir dieksekusi ±0% dari NYSE/Binance) -> dikeluarkan dari potret.",
         f"    Data lama (riset 8 Okt): {_n(lama)} swap pool resmi-resmi (16 saham seluruh riwayat; pool ETH/WETH/USDG hanya",
         "      hari PERTAMA tiap pool) s.d. blok 83.365.924 (8 Okt 13:57 UTC).",
         f"    BARU (sesi ini): token saham resmi ternyata 192, bukan 16 (lihat B3). Pool 175 token tambahan x USDG/WETH/ETH",
         f"      yang dibuat <= 7 hari setelah mint pertama token: 822 pool, {_n(npl)} swap dalam 72 jam pertama",
         "      (robinhood_peluncuran_parts/).",
         "    Batasan: pool ETH/WETH/USDG resmi lama hanya 24 jam pertama; acuan saham hanya jam bursa AS (±3 mnt),",
         "      di luar jam bursa swap saham TIDAK dinilai; acuan ETH = Binance ETHUSDT 1 mnt (24 jam)."]
    return L


def _bagian_b2() -> list[str]:
    from .chain_onchain import ke_waktu
    blk = blok_ts()
    ss = pd.read_parquet(ARB / "robinhood_cari_ss.parquet")
    P = pd.read_parquet(ARB / "robinhood_pecahan.parquet")
    Pw = P[P.dev_med <= -0.05]
    S = pd.read_parquet(ARB / "robinhood_pecahan_semua.parquet")
    Sw = S[S.quote_resmi & S.aset.str.upper().isin(["WETH", "ETH"])]
    Sx = Sw[Sw.dev_med <= -0.05]
    g = json.loads((ARB / "robinhood_grup_rh.json").read_text())
    tok = pd.read_parquet(ARB / "robinhood_token.parquet").set_index("alamat")
    tg = pd.read_parquet(ARB / "robinhood_transfer_grup_rh.parquet")
    tg["t"] = ke_waktu(tg.blok.to_numpy().astype(float), blk)
    ind = pd.read_parquet(ARB / "robinhood_transfer_induk_rh.parquet")
    I = "0x7821f1d95173f214f0ef23069f3a95a29de3f311"
    ind["sym"] = ind.token.map(tok.symbol)
    ind["v"] = ind.nilai / 10.0 ** ind.token.map(tok.decimals).fillna(18)
    ind["t"] = ke_waktu(ind.blok.to_numpy().astype(float), blk)
    usdg = ind[ind.token == USDG]
    L = ["B2. POLA SCREENSHOT DI ROBINHOOD (beli pecahan kecil sampai batas, seperti wetharb) + JEJAK GRUP E1/E2",
         f"    Cocokkan jumlah PERSIS 21 baris screenshot di SEMUA swap Robinhood (5,67 jt baru + 19,3 jt lama): {len(ss)} cocok",
         "      -> screenshot BUKAN dari Robinhood (sudah terbukti di Arc, lihat hasil_arb_cari.txt bagian A1).",
         f"    Pola 'pecahan' (pengirim sama, pool sama, input quote PERSIS sama >= 5x, <= $250, >= 3 blok) di pool bernilai",
         f"      (kedua token resmi, dinilai per swap thd acuan): {_n(len(P))} kelompok; median selisih eksekusi "
         f"{_pct(P.dev_med.median(), 2)} (P10 {_pct(P.dev_med.quantile(.1), 2)}, P90 {_pct(P.dev_med.quantile(.9), 2)}).",
         f"      Yang membeli <= -5% di bawah acuan: {len(Pw)} kelompok, untung total ${_rp(Pw.untung.sum())}. Bukan bot pecahan:",
         "      sebagian besar = SATU tx yang menyapu banyak 'bin' pool Liquidity Book WETH/USDG 0xcc8e5ada (4 Sep 16:30-16:32",
         "      UTC; tiap bin = 1 event Swap berjumlah sama ±1,05-1,12 USDG). Kejadiannya: 0x8f10b468 menjual WETH senilai",
         "      ±$14 rb ke pool LB tipis (harga turun s/d -35%, ia rugi ±$1,2 rb); 3 kontrak bot (0x0b8c2b82, 0xd526fb7b,",
         "      0x2b5f704a) membeli balik dalam 1-3 detik, untung ±$1,1 rb. Sisanya: META/WETH v2 18 Sep (5 beli, +$222).",
         "      Pembeli 'pecahan' terbanyak justru membayar DI ATAS acuan (+0,15…+0,19%): mis. 0x65050a9b 26 rb x 0,0099 WETH",
         "      ke SPY/WETH, 0xcaf681a6 SPY/WETH & NVDA/WETH x 0,099 WETH = router/pembuat pasar, bukan pemburu diskon.",
         f"    Semua pool kandidat (termasuk quote tiruan): {_n(len(S))} kelompok; WETH/ETH ber-quote USDG resmi {_n(len(Sw))} kelompok,",
         f"      median selisih per swap {_pct(Sw.dev_med.median(), 2)}; <= -5%: {len(Sx)} kelompok (input ${_rp((Sx.q_in * Sx.n).sum())}) —",
         "      lagi-lagi sapuan bin LB 4 Sep + 0x7a31dd32 (v2 0x8803c117, 1-2 Jul, 6 x 226 USDG di -5%, +$87).",
         f"      {_n(len(S) - S.quote_resmi.sum())} kelompok ber-quote token TIRUAN (USDG/USDC/USDT palsu) tidak bisa dinilai (quote tak bernilai).",
         "    => TIDAK ada bot gaya wetharb/circarb di Robinhood. Bedanya dengan Arc: di Robinhood token resmi dicetak",
         "       langsung oleh penerbit (bukan jembatan dengan pasokan tipis) dan pool utamanya dalam (ETH/USDG ±$2,5-5 jt per",
         "       2% gerak), sehingga diskon besar hanya muncul sesaat di pool kecil dan langsung ditutup bot.",
         f"    Jejak grup di Robinhood: E1 0x673250c6 nonce {g['E1']['nonce']}, saldo {str(round(g['E1']['saldo_eth'], 6)).replace('.', ',')} ETH; "
         f"E2 0x7cff8a2b nonce {g['E2']['nonce']}, saldo {str(round(g['E2']['saldo_eth'], 6)).replace('.', ',')} ETH;",
         "      tidak ada kontrak hasil CREATE dari nonce mereka. Seluruh Transfer ERC-20 E1/E2 sejak blok 1:"]
    for r in tg.itertuples():
        sym = tok.symbol.get(r.token, r.token[:8])
        v = r.nilai / 10.0 ** int(tok.decimals.get(r.token, 18))
        dari = {"0xaeb17c341262565d285eaed0d4974836ad548eda": "vault jembatan CRCL", A.E1: "E1", A.E2: "E2",
                I: "induk 0x7821f1d9"}.get(r.dari, r.dari[:10])
        ke = {A.E1: "E1", A.E2: "E2", I: "induk 0x7821f1d9"}.get(r.ke, r.ke[:10])
        L.append(f"      {_tgl(r.t)} UTC  {sym:<7} {v:>12.6f}  {dari} -> {ke}".replace(".", ","))
    L += ["      (ETH asli 0,4455 dari vault WETH ke E1 14 Sep tidak muncul sebagai Transfer — lihat A3). E1/E2 TIDAK pernah",
          "      berdagang di DEX Robinhood; Robinhood hanya tempat tebus & kirim hasil ke dompet induk.",
          f"    Dompet induk 0x7821f1d9 di Robinhood: EOA dengan delegasi EIP-7702 (kode 23 byte), {_n(len(ind))} Transfer ERC-20",
          f"      {_tgl(ind.t.min(), False)}-{_tgl(ind.t.max(), False)} 2026: USDG masuk ${_rp(usdg[usdg.ke == I].v.sum())} / keluar "
          f"${_rp(usdg[usdg.dari == I].v.sum())}; NVDA/CRCL resmi bolak-balik ke vault jembatan",
          "      (0x3943a8a8 NVDA, 0xaeb17c34 CRCL) = setoran ke Arc; WETH resmi hanya receh (<= 0,006); sisanya puluhan token",
          "      meme (FARTCLUB, BEAV, XHAMSTER, ...). Tidak ada pola beli-diskon berulang di Robinhood."]
    return L


def _bagian_b3() -> list[str]:
    import os
    gas = json.loads((ARB / "robinhood_gas_sekarang.json").read_text())["robinhood"]
    tm = lambda f: pd.Timestamp(os.path.getmtime(ARB / f), unit="s")  # noqa: E731
    d = pd.read_parquet(ARB / "robinhood_potret_resmi_semua.parquet")
    st = pd.read_parquet(ARB / "robinhood_potret_resmi_semua_pool.parquet")
    pos = d[d.untung_terbaik > 0]
    semu = d[d.leg2_nol_100 & (d.untung_mid_100 > 0)]
    pu = pd.read_parquet(ARB / "robinhood_potret.parquet")
    w = pd.read_parquet(ARB / "robinhood_potret_weth.parquet")
    w["wr"] = w.weth.isin([WETH, ETH])
    w["ur"] = w.usd == USDG
    wr = w[w.wr & w.ur & (w.dalam2 > 1)]
    wf = w[w.wr & ~w.ur & (w.dalam2 > 1) & (w.selisih <= -0.05)]
    wd = wr[wr.selisih <= -0.05]
    c = resmi_semua()
    n_rt = len(c)
    n_resmi = int(c.resmi_minter.sum())
    tok = pd.read_parquet(ARB / "robinhood_token.parquet")
    nama_rt = tok.name.str.contains("Robinhood Token", case=False, na=False)
    palsu_nama = int(nama_rt.sum() - c.resmi_minter.sum())
    sym = tok.symbol.str.upper()
    res_alamat = set(c[c.resmi_minter].alamat) | {WETH, USDG}
    simbol_resmi = set(c[c.resmi_minter].symbol.str.upper()) | {"WETH", "USDG"}
    tiru = tok[sym.isin(simbol_resmi) & ~tok.alamat.isin(res_alamat)]
    s18 = set(RH_SAHAM) | {"WETH", "USDG"}
    tiru18 = tiru[tiru.symbol.str.upper().isin(s18)]
    top_tiru = tiru18.symbol.str.upper().value_counts().head(8)
    L = ["B3. POTRET SEKARANG (9 Okt 2026, ±08:50-09:35 UTC = bursa AS TUTUP, harga token saham diam) — hanya eth_call",
         f"    Gas 1 swap: median {_n(gas['gas_used_median'])} gas x {gas['gas_price_wei'] / 1e9:.4f} gwei x ETH ±$2.503 = "
         f"${gas['usd_per_swap']:.4f} (2 swap ±$0,017) — gas BUKAN penghalang.".replace("0.0", "0,0"),
         f"    Kualitas token: token saham RESMI = {n_resmi} (bukan 16): nama '... • Robinhood Token', kode proxy identik dengan",
         "      CRCL resmi, dan tx mint pertamanya dikirim minter yang SAMA 0x2b94105f… (EOA penerbit). 16 token daftar putih lama",
         f"      hanya sebagian; 176 lainnya (DJT, AMC, RDDT, GLD, SGOV, NFLX, SNDK, MU, INTC, ...) juga resmi. Dari {_n(n_rt)}",
         f"      kontrak berkode sama, {n_rt - n_resmi} belum pernah mint. Tiruan: {_n(palsu_nama)} token lain bernama '• Robinhood Token'",
         f"      dengan kode berbeda; {_n(len(tiru18))} token memakai simbol 16 saham lama/WETH/USDG tetapi alamat lain: "
         + ", ".join(f"{k} {_n(v)}" for k, v in top_tiru.items()) + f" (dengan 192 simbol: {_n(len(tiru))},",
         "      sebagian simbol umum seperti BULL/FLY/ON).",
         "      => daftar putih HARUS berdasarkan alamat (atau minter 0x2b94105f), bukan simbol/nama.",
         f"    (a) Aset resmi (192 saham + WETH/ETH) ber-quote USDG resmi: {_n(len(st))} pool hidup di {st.aset.nunique()} aset;",
         f"        {_n(len(d))} pool menyimpang >= 0,5% dari pool terdalam asetnya (median |selisih| {_pct(d.dev_vs_utama.abs().median())}).",
         "        Untung pulang-pergi dihitung PERSIS dua kaki (V4Quoter resmi / simulasi v3 lintas tick dengan fee & tickSpacing",
         f"        dibaca dari kontrak / v2), dikurangi gas 2 swap: positif hanya {len(pos)} pool:"]
    for r in pos.head(6).itertuples():
        hk = "hook" if (isinstance(r.hooks, str) and r.hooks not in ("", "0x" + "0" * 40)) else "    "
        L.append(f"          {r.simbol:<6} {r.jenis:<4} {hk} fee {_pct(r.fee / 1e6, 2):>6} selisih {_pct(r.dev_vs_utama, 2):>7}  "
                 f"$3 -> {_rp(r.untung_3):>6}  $25 -> {_rp(r.untung_25):>6}  $100 -> {_rp(r.untung_100):>6}  $300 -> {_rp(r.untung_300):>6}")
    nol = d[d.leg2_nol_100]
    L += [f"        Untung maks ${_rp(pos.untung_terbaik.max())} per transaksi (modal $300) = receh; antre dengan bot lain.",
          f"        'Selisih semu': {len(nol)} pool ({nol.aset.nunique()} aset) kaki keduanya = 0 / revert. {len(semu)} di antaranya tampak "
          "untung bila dinilai",
          "        di harga MID pool utama (cara lama): " + ", ".join(
              f"{r.simbol} {_pct(r.dev_vs_utama, 0)}" for r in semu.sort_values("dev_vs_utama").head(6).itertuples())
          + ". Pool utama token baru",
          "        hanya berisi TOKEN (dinding jual satu sisi, tanpa USDG untuk membeli balik) -> tidak bisa diarbitrase.",
          f"    (b) Semua aset (termasuk meme) dengan >= 2 pool ber-quote USDG resmi ({tm('robinhood_potret.parquet'):%H:%M} UTC): 158.609 pool,",
          f"        33.194 aset; 400 selisih terbesar dikuotasi; positif {int((pu.untung_terbaik > 0).sum())}: STONKBROKER & ROBIN (token meme).",
          "        Dicek ulang dengan fee/tickSpacing asli kontrak Slipstream (0,25%/1%, bukan angka event): kaki jual STONKBROKER",
          "        = 0 (likuiditas satu sisi) -> untung semu. Tidak ada peluang nyata.",
          f"    (c) WETH/ETH vs ETH Binance ({tm('robinhood_potret_weth.parquet'):%H:%M} UTC, ETH ${_rp(float(w.eth_binance.iloc[0]))}): "
          f"{_n(len(w))} pool token bersimbol WETH/ETH ber-quote 'USD'.",
          f"        WETH/ETH resmi x USDG resmi (kedalaman > $1 per 2%): {len(wr)} pool, median selisih {_pct(wr.selisih.median(), 2)};",
          f"        <= -5%: {len(wd)} pool, kedalaman ${_rp(wd.dalam2.min())}-{_rp(wd.dalam2.max())} per 2% (mis. Slipstream 0x2ab9f3b0 -28%:",
          "        harga di TEPI rentang likuiditas — WETH sudah habis terjual; 8 Okt 17:24 UTC ada yang menjual 0,0011 WETH di",
          "        -28% dan bot 0x0970ca94 membeli balik 0,2 dtk kemudian).",
          f"        WETH resmi x stablecoin TIRUAN tampak -16…-60% di {len(wf)} pool 'dalam' — kedalamannya dalam token palsu (USDT/",
          "        USDC/DAI/USDe/PYUSD tiruan), bukan uang. Jebakan bagi bot yang memfilter simbol."]
    return L


UMUR = [(0, 1, "0-1 jam"), (1, 24, "1-24 jam"), (24, 72, "1-3 hari"), (72, 168, "3-7 hari"), (168, 720, "7-30 hari"),
        (720, 1e9, "> 30 hari")]


def _ringkas_umur(E: pd.DataFrame) -> list[str]:
    out = ["      umur pool      ep  untung tanpa hook  untung hook  aksi untung>$1  reaksi med (blok)  <=1 blok"]
    for a, b, nm in UMUR:
        e = E[(E.umur_jam >= a) & (E.umur_jam < b)]
        ok = e[(e.n_aksi > 0) & (e.untung_aksi > 1) & (e.jeda_blok >= 0)]
        out.append(f"      {nm:<11} {len(e):>5}  {_rp(e[~e.hook].untung_aksi.sum()):>17}  {_rp(e[e.hook].untung_aksi.sum()):>11}"
                   f"  {len(ok):>14}  {(str(int(ok.jeda_blok.median())) if len(ok) else '-'):>17}  "
                   f"{_pct((ok.jeda_blok <= 1).mean(), 0) if len(ok) else '-':>8}")
    return out


def _bagian_b4() -> list[str]:
    from .chain_onchain import ke_waktu
    blk = blok_ts()
    meta = pd.read_parquet(ARB / "robinhood_pool_bernilai.parquet")
    pp = pd.read_parquet(ARB / "robinhood_per_pool_bernilai.parquet")
    E = pd.read_parquet(ARB / "robinhood_episode_aksi.parquet")
    E["kap_usd"] = _kap_usd(E, meta)
    pools = meta[["id", "blok"]].copy()
    pools["t_buat"] = ke_waktu(pools.blok.to_numpy().astype(float), blk)
    pools = pools.merge(pp[["id", "n_swap"]], on="id", how="left")
    w72 = tabel_pekan(E, pools, 72)
    vh = pd.read_parquet(ARB / "robinhood_verif_hook.parquet") if (ARB / "robinhood_verif_hook.parquet").exists() else None
    nh = E[~E.hook]
    bulan = nh.groupby(pd.to_datetime(nh.t_mulai, utc=True).dt.strftime("%Y-%m")).agg(
        ep=("id", "size"), untung=("untung_aksi", "sum"), usd=("usd_beli", "sum"))
    ok = E[(E.n_aksi > 0) & (E.untung_aksi > 1) & (E.jeda_blok >= 0) & ~E.hook]
    tutup = E[np.isfinite(E.lama_dtk) & (E.n_aksi > 0)]
    tk = nh[nh.n_aksi > 0].groupby("pengirim_beli1").untung_aksi.sum().sort_values(ascending=False)
    L = ["B4. JENDELA PELUNCURAN SEJAK 1 JUL 2026 — episode diskon >= 5% vs acuan di pool BARU beraset bernilai",
         "    Definisi: episode = deret swap berurutan satu pool dengan harga pool SEBELUM swap <= acuan x 0,95 (ETH Binance;",
         "    saham = Twelve Data 1 mnt, hanya jam bursa). 'lama' = sejak kejadian yang membuka diskon (swap/likuiditas",
         "    sebelumnya) sampai harga kembali > -5% (ditutup swap) atau acuan bergeser. 'reaksi' = blok antara kejadian",
         "    pembuka dan beli pertama di diskon (1 blok = 0,1 dtk). Untung = per AKSI: SEMUA swap pool bernilai dalam tx yang",
         "    sama dijumlahkan & dinilai acuan (jual-lalu-beli-balik sendiri = 0; arbitrase 2 pool = untung sebenarnya).",
         "    Pool v4 ber-hook dipisah: event Swap v4 tidak memuat delta hook -> angka bisa menyimpang (dicek lewat receipt).",
         "",
         "    (1) 16 saham lama + WETH/ETH/USDG (pool kedua token bernilai; ETH/WETH/USDG resmi lama hanya 24 jam pertama).",
         "        Per pekan PEMBUATAN pool, diskon dalam 72 jam pertama pool:"]
    L += ["    " + x for x in _tabel_teks(w72)]
    tot = w72.sum()
    L += [f"        Total 72 jam pertama: {int(tot.episode)} episode di {int(tot.sempat_diskon)} dari {_n(tot.pool_baru)} pool baru; untung semua "
          f"pelaku ${_rp(tot.untung_tanpa_hook)} (tanpa hook) + ${_rp(tot.untung_hook)} (pool ber-hook).",
          "        Semua umur pool (tidak hanya 72 jam), per umur saat episode:"]
    L += ["    " + x for x in _ringkas_umur(E)]
    L += ["        Per bulan (semua umur, tanpa hook): " + "; ".join(
        f"{BULAN[int(k[5:]) - 1]} {int(r.ep)} ep ${_rp(r.untung)}" for k, r in bulan.iterrows())]
    L += [f"        Reaksi (episode untung > $1, tanpa hook, n {len(ok)}): median {int(ok.jeda_blok.median())} blok, "
          f"{_pct((ok.jeda_blok <= 1).mean(), 0)} diambil <= 1 blok (0,1 dtk), {_pct((ok.jeda_blok <= 10).mean(), 0)} <= 10 blok (1 dtk).",
          f"        Lama diskon (episode tertutup dgn pembeli, n {len(tutup)}): median {_fmt_dtk(tutup.lama_dtk.median())}, "
          f"P75 {_fmt_dtk(tutup.lama_dtk.quantile(.75))}, P90 {_fmt_dtk(tutup.lama_dtk.quantile(.9))}.",
          f"        Pengambil (pengirim swap = kontrak pemanggil pool): {tk.size} alamat = 336 kontrak + 34 EOA ber-delegasi EIP-7702,",
          f"        0 EOA biasa; 5 teratas = {_pct(tk.head(5).sum() / tk[tk > 0].sum(), 0)} untung positif. Tidak ada satu pemain dominan.",
          "        Episode terbesar (tanpa hook):"]
    for r in nh.sort_values("untung_aksi", ascending=False).head(8).itertuples():
        L.append(f"          {_tgl(r.t_mulai)} {r.pair:<10} {r.jenis:<4} umur {r.umur_jam:7.1f} j  dev {_pct(r.dev_awal, 0):>5}  "
                 f"beli ${_rp(r.usd_beli):>7}  untung ${_rp(r.untung_aksi):>6}  reaksi {int(r.jeda_blok)} blok  {r.pengirim_beli1[:10]}")
    L += ["        Pool ber-hook (dicek receipt):"]
    if vh is not None:
        for r in vh.sort_values("untung_event", ascending=False).head(3).itertuples():
            L.append(f"          {_tgl(r.t)} {r.pair:<9} event ${_rp(r.untung_event):>7} -> receipt ${_rp(r.untung_receipt):>7}  tx {r.tx[:14]}…")
        L += [f"          Total {len(vh)} aksi hook |untung| >= $20: event ${_rp(vh.untung_event.sum())}, receipt ${_rp(vh.untung_receipt.sum())}"
              " (receipt = arus ERC-20 sisi pedagang; ETH asli tak terlihat).",
              "          Terbesar = 27 Agu 10:25 UTC pool ETH/USDG ber-hook 0x19d4c7dd (umur 44 mnt): 1 blok setelah LP menaruh",
              "          likuiditas di rentang harga ~0, bot (EOA 0x6113eece, nonce 93.891) mengambil 39,65 ETH (±$99,7 rb) dengan",
              "          1e-6 USDG; WETH berakhir di EOA 0x33eabd63. = KESALAHAN KONFIGURASI LP/hook yang 'dipanen' dalam 0,1 dtk,",
              "          bukan pola yang bisa diulang. 11 Sep 17:16-20:44: 12 'beli $50-450 rb di -5%' di pool hook 0xd986deca",
              "          ternyata jual-lalu-beli-balik dalam SATU tx (180 ETH bolak-balik, tanpa Transfer ERC-20) -> untung 0."]
    return L


def _bagian_b4b() -> list[str]:
    """Gelombang peluncuran 175 token saham tambahan (Jun-Sep 2026)."""
    from .chain_onchain import ke_waktu
    blk = blok_ts()
    sp = _pool_peluncuran()
    sp["t_buat"] = ke_waktu(sp.blok.to_numpy().astype(float), blk)
    c = resmi_semua()
    c = c[c.resmi_minter & c.alamat.isin(set(sp.token))].copy()
    c["t1"] = ke_waktu(c.mint1_blok.to_numpy().astype(float), blk)
    x = pd.read_parquet(ARB / "robinhood_peluncuran_nilai.parquet", columns=["id", "dev_pra", "usd_aset", "untung_usd", "txh"])
    xb = pd.read_parquet(ARB / "robinhood_peluncuran_nilai_basi.parquet", columns=["id", "dev_pra", "usd_aset", "untung_usd"])
    ac = pd.read_parquet(ARB / "robinhood_acuan_peluncuran_1m.parquet")
    nsw = x.groupby("id").size()
    pools = sp[["pool", "t_buat"]].rename(columns={"pool": "id"})
    pools["n_swap"] = pools.id.map(nsw)
    gel = c.groupby(c.t1.dt.strftime("%Y-%m-%d")).symbol.size()
    L = ["    (2) GELOMBANG PELUNCURAN 175 token saham resmi TAMBAHAN (di luar 16) — pool x USDG/WETH/ETH yang dibuat <= 7 hari",
         "        setelah mint pertama token, swap 72 jam pertama tiap pool. Mint pertama per hari: "
         + ", ".join(f"{_tgl(pd.Timestamp(k), False)} {v}" for k, v in gel.items() if v >= 2) + " (+ beberapa tunggal).",
         f"        {len(sp)} pool, {_n(len(x))} swap, acuan Twelve Data 1 mnt untuk {ac.sym.nunique()} ticker; swap yang punya acuan:",
         f"        jam bursa saja {_pct(x.dev_pra.notna().mean(), 0)} (volume {_pct(x[x.dev_pra.notna()].usd_aset.abs().sum() / max(xb.usd_aset.abs().sum(), 1), 0)}"
         " dari yang ternilai versi 'basi');",
         f"        versi 'basi' (di luar jam bursa pakai close terakhir) {_pct(xb.dev_pra.notna().mean(), 0)}."]
    for suf, nama in (("", "jam bursa"), ("_basi", "acuan basi")):
        f = ARB / f"robinhood_peluncuran_episode{suf}.parquet"
        if not f.exists():
            continue
        E = pd.read_parquet(f)
        if not len(E):
            L.append(f"        [{nama}] 0 episode diskon >= 5%.")
            continue
        E["kap_usd"] = np.nan
        w = tabel_pekan(E, pools, 72)
        w = w[w.pool_baru > 0]
        L.append(f"        [{nama}] per pekan pembuatan pool:")
        L += ["    " + q for q in _tabel_teks(w)]
        nh = E[~E.hook]
        ok = nh[(nh.n_aksi > 0) & (nh.untung_aksi > 1) & (nh.jeda_blok >= 0)]
        L.append(f"        [{nama}] total: {len(E)} episode di {E.id.nunique()} pool; beli di bawah -5% ${_rp(nh.usd_beli.sum())}, untung semua pelaku "
                 f"${_rp(nh.untung_aksi.sum())} (tanpa hook) + ${_rp(E[E.hook].untung_aksi.sum())} (hook); episode untung > $1: {len(ok)}"
                 + (f", reaksi median {int(ok.jeda_blok.median())} blok" if len(ok) else "") + ".")
        for r in nh.sort_values("untung_aksi", ascending=False).head(5).itertuples():
            L.append(f"          {_tgl(r.t_mulai)} {r.pair:<10} {r.jenis:<4} umur {r.umur_jam:5.1f} j  dev {_pct(r.dev_awal, 0):>5}  "
                     f"beli ${_rp(r.usd_beli):>7}  untung ${_rp(r.untung_aksi):>6}  reaksi {int(r.jeda_blok)} blok")
    return L


def _kesimpulan() -> list[str]:
    E = pd.read_parquet(ARB / "robinhood_episode_aksi.parquet")
    e72 = E[E.umur_jam <= 72]
    nh72 = e72[~e72.hook]
    ok = E[(E.n_aksi > 0) & (E.untung_aksi > 1) & (E.jeda_blok >= 0) & ~E.hook]
    tutup = E[np.isfinite(E.lama_dtk) & (E.n_aksi > 0)]
    d = pd.read_parquet(ARB / "robinhood_potret_resmi_semua.parquet")
    fp = ARB / "robinhood_peluncuran_episode.parquet"
    fb = ARB / "robinhood_peluncuran_episode_basi.parquet"
    Ep = pd.read_parquet(fp) if fp.exists() else pd.DataFrame(columns=["untung_aksi", "hook"])
    Eb = pd.read_parquet(fb) if fb.exists() else pd.DataFrame(columns=["untung_aksi", "hook"])
    up = Ep[~Ep.hook.astype(bool)].untung_aksi.sum() if len(Ep) else 0.0
    ub = Eb[~Eb.hook.astype(bool)].untung_aksi.sum() if len(Eb) else 0.0
    pek = (pd.Timestamp("2026-10-09") - pd.Timestamp("2026-07-01")).days / 7
    return [
        "KESIMPULAN ROBINHOOD (periode: pra-mainnet Mei-Jun, mainnet publik 1 Jul s.d. 9 Okt 2026; semua angka = SEMUA pelaku):",
        "  1. Pola screenshot (wetharb/circarb) TIDAK ada di Robinhood: 0/21 jumlah cocok, tidak ada pembeli pecahan tetap yang",
        "     berulang di bawah acuan. Grup E1/E2 hanya memakai Robinhood untuk menebus token jembatan Arc (0,4455 ETH, 3,64 CRCL).",
        f"  2. Jendela peluncuran pool baru beraset bernilai (16 saham lama + ETH/WETH/USDG, 72 jam pertama): {len(e72)} episode diskon",
        f"     >= 5% dalam ±{pek:.0f} pekan; untung SEMUA pelaku ${_rp(nh72.untung_aksi.sum())} tanpa pool ber-hook (±${_rp(nh72.untung_aksi.sum() / pek)}/pekan).",
        f"     Diskon tertutup cepat: median {_fmt_dtk(tutup.lama_dtk.median())}; {_pct((ok.jeda_blok <= 1).mean(), 0)} episode yang menguntungkan diambil dalam",
        "     <= 1 blok (0,1 dtk) oleh ±370 kontrak/akun bot. Bot ritel dengan polling RPC (±1-3 dtk) praktis selalu kalah.",
        f"  3. Gelombang 175 token saham tambahan (30 Jun, 13-14 Agu): untung diskon >= 5% dalam 72 jam pertama ${_rp(up)} (jam bursa)",
        f"     / ${_rp(ub)} (acuan basi di luar jam bursa) untuk semua pelaku — pool token baru umumnya likuiditas SATU SISI",
        "     (dinding jual), jadi 'murah' tidak bisa dijual balik di DEX.",
        "  4. Uang besar di Robinhood datang dari KESALAHAN LP, bukan selisih harga normal: pool ETH/USDG ber-hook terkuras 39,65",
        "     ETH (±$99,7 rb, 27 Agu, 1 blok setelah likuiditas ditaruh di harga ~0), pool v2 META/WETH & WETH/USDG yang dibuat",
        "     dengan harga salah (-93…-100%, $0,5-1,8 rb per tx). Semuanya diambil bot dalam 0-1 blok; tidak bisa direncanakan.",
        f"  5. Potret 9 Okt: dari {_n(len(d))} pool aset resmi yang menyimpang >= 0,5%, hanya {int((d.untung_terbaik > 0).sum())} untung setelah fee & gas, maks "
        f"${_rp(d.untung_terbaik.max())} per $300. Gas ($0,008/swap) bukan penghalang;",
        "     penghalangnya kecepatan bot, likuiditas satu sisi, pool ber-hook, dan token/stablecoin TIRUAN (diskon palsu -16…-60%).",
        "  6. Beda dengan Arc: untung grup di Arc (±$7,6 rb) berasal dari token JEMBATAN pra-publik yang bisa ditebus 1:1 di",
        "     Robinhood. Robinhood sendiri tidak punya mekanisme itu (token dicetak langsung penerbit 0x2b94105f), jadi tidak ada",
        "     'jendela pra-publik' serupa sejak 1 Jul.",
        "  Jujur soal risiko: angka di atas adalah untung KOTOR seluruh pemenang lomba (sebelum biaya gagal/revert, gas prioritas,",
        "  dan risiko kustodian/token). Tidak ada jaminan pola ini berulang; sebagian besar sudah hilang setelah pekan pertama.",
    ]


def lapor() -> str:
    from .chain_onchain import ke_waktu
    top = json.loads((PARTS / "top_lanjut.json").read_text())["top"]
    t_top = ke_waktu(np.array([float(top)]), blok_ts())[0]
    head = ["=== ROBINHOOD CHAIN (TUGAS B): MULAI ===",
            "Robinhood Chain (L2 Arbitrum, chain 4663, mainnet publik 1 Jul 2026, gas ETH, blok ±0,1 dtk) — dibuat 9 Okt 2026 oleh",
            "research/arb_robinhood.py (lanjutan arb_cari.py; `python -m research.arb_robinhood <tahap>`).",
            f"Data: swap s.d. blok {_n(top)} ({_tgl(t_top)} UTC 9 Okt) + potret eth_call 9 Okt 08:50-09:35 UTC. Acuan: ETH = Binance",
            "ETHUSDT 1 mnt; saham = Twelve Data 1 mnt jam bursa AS (toleransi 3 mnt). Semua USD = USDG resmi 0x5fc5360d.",
            "Hanya baca RPC (eth_getLogs/eth_call/getBlock/getTransaction/receipt/getCode) + API publik — tanpa transaksi.",
            ""]
    L = head + _bagian_b1() + [""] + _bagian_b2() + [""] + _bagian_b3() + [""] + _bagian_b4() + [""] + _bagian_b4b() + [""] \
        + _kesimpulan() + ["=== ROBINHOOD CHAIN (TUGAS B): SELESAI ===", ""]
    txt = "\n".join(L)
    LAP.write_text(txt)
    return txt


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
    elif tahap == "aksi":
        print(aksi().sort_values("untung_aksi", ascending=False).head(20).to_string())
    elif tahap == "verif_hook":
        print(verif_hook().to_string())
    elif tahap == "oracle":
        unduh_oracle()
    elif tahap == "potret_resmi":
        print(potret_resmi(semua=len(sys.argv) > 2 and sys.argv[2] == "semua").head(30).to_string())
    elif tahap == "grup":
        print(json.dumps(grup(), indent=1)[:3000])
    elif tahap == "resmi_semua":
        print(resmi_semua().resmi_minter.sum(), "token saham resmi")
    elif tahap == "peluncuran":          # swap 72 jam pertama pool 175 token tambahan + acuan Twelve Data + episode
        unduh_peluncuran()
        acuan_peluncuran()
        proses_peluncuran()
        proses_peluncuran(basi=True)
    elif tahap == "lapor":
        lapor()
