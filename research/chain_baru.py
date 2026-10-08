"""Data DEX chain baru (Robinhood Chain, Arc, ...) — python -m research.chain_baru <perintah>

Permintaan pengguna 8 Okt 2026: token/pool yang baru rilis di chain baru (pengalaman pengguna: WETH $6 -> 0,45 ETH,
token saham CRCL untung 2-5x s/d mainnet Arc, lalu harga normal & arbitrase vs Robinhood habis). Modul ini HANYA
mengunduh data publik (tanpa transaksi):

  daftar <network>            pool teratas network (10 halaman volume + 10 halaman likuiditas) -> pools_<net>.json
  token <network> <alamat>    semua pool satu token (maks 200, batas API gratis) -> tokpools_<net>_<alamat>.json
  ohlcv <network> <pool> [tok] candle 1 menit sejak pool dibuat (GeckoTerminal, paging mundur 1.000 bar)
  acuan                        ETH/BTC 1 menit Binance (data.binance.vision) + saham 1 menit Twelve Data
  semua                        pipeline lengkap yang dipakai research/chain_baru_uji.py

GeckoTerminal gratis: ±30 permintaan/menit, maks 10 halaman per daftar, candle menit tersedia sejak pool dibuat
(diuji 8 Okt 2026 untuk pool Jul 2026). Harga USD candle = harga token dalam USD (pool non-USD dikonversi GT).
Data: data/research/eksternal/chain_baru/ (parquet per pool, di-commit seperti data riset lain).
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "chain_baru"
GT = "https://api.geckoterminal.com/api/v2"
_last = [0.0]
JEDA = 2.2  # detik antar permintaan GT (±27/menit)


def _dir(*sub: str) -> Path:
    d = DIR.joinpath(*sub)
    d.mkdir(parents=True, exist_ok=True)
    return d


def gt(path: str, **params) -> dict:
    """GET GeckoTerminal dengan jeda & coba ulang 429/5xx."""
    url = f"{GT}{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    for k in range(8):
        wait = _last[0] + JEDA - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(15 * (k + 1))
                continue
            if e.code == 404:
                return {}
            body = e.read()[:300]
            raise RuntimeError(f"{e.code} {url}: {body!r}") from e
        except Exception:  # noqa: BLE001
            time.sleep(10 * (k + 1))
    raise RuntimeError(f"gagal: {url}")


def _pool_row(x: dict) -> dict:
    a = x["attributes"]
    rel = x.get("relationships", {})

    def rid(k):
        d = rel.get(k, {}).get("data") or {}
        return d.get("id", "")

    return {
        "id": x["id"], "address": a["address"], "name": a["name"], "created": a.get("pool_created_at"),
        "dex": rid("dex"), "base": rid("base_token").split("_", 1)[-1], "quote": rid("quote_token").split("_", 1)[-1],
        "base_usd": float(a.get("base_token_price_usd") or 0), "quote_usd": float(a.get("quote_token_price_usd") or 0),
        "liq": float(a.get("reserve_in_usd") or 0), "vol24": float((a.get("volume_usd") or {}).get("h24") or 0),
        "fdv": float(a.get("fdv_usd") or 0),
    }


def daftar(net: str) -> list[dict]:
    """Pool teratas: 10 halaman per urutan volume, transaksi; disatukan per alamat."""
    f = _dir() / f"pools_{net}.json"
    out: dict[str, dict] = {}
    tokens: dict[str, dict] = {}
    for sort in ("h24_volume_usd_desc", "h24_tx_count_desc"):
        for p in range(1, 11):
            d = gt(f"/networks/{net}/pools", page=p, sort=sort, include="base_token,quote_token")
            for x in d.get("data", []):
                r = _pool_row(x)
                out[r["address"]] = r
            for t in d.get("included", []):
                a = t["attributes"]
                tokens[a["address"]] = {"address": a["address"], "name": a.get("name"), "symbol": a.get("symbol"),
                                        "decimals": a.get("decimals"), "cg": a.get("coingecko_coin_id")}
            if len(d.get("data", [])) < 20:
                break
    res = {"pools": list(out.values()), "tokens": tokens, "waktu": pd.Timestamp.now("UTC").isoformat()}
    f.write_text(json.dumps(res, indent=1))
    print(f"{net}: {len(out)} pool, {len(tokens)} token -> {f}")
    return res


def token_pools(net: str, addr: str, pages: int = 10) -> dict:
    f = _dir() / f"tokpools_{net}_{addr.lower()}.json"
    if f.exists():
        return json.loads(f.read_text())
    out, tokens = {}, {}
    for p in range(1, pages + 1):
        d = gt(f"/networks/{net}/tokens/{addr}/pools", page=p, sort="h24_volume_usd_liquidity_desc",
               include="base_token,quote_token")
        for x in d.get("data", []):
            r = _pool_row(x)
            out[r["address"]] = r
        for t in d.get("included", []):
            a = t["attributes"]
            tokens[a["address"]] = {"address": a["address"], "name": a.get("name"), "symbol": a.get("symbol"),
                                    "decimals": a.get("decimals"), "cg": a.get("coingecko_coin_id")}
        if len(d.get("data", [])) < 20:
            break
    res = {"pools": list(out.values()), "tokens": tokens}
    f.write_text(json.dumps(res, indent=1))
    return res


def ohlcv(net: str, pool: str, token: str = "base", tf: str = "minute", agg: int = 1,
          created: str | None = None, refresh: bool = False) -> pd.DataFrame:
    """Candle USD token (`base`/`quote`/alamat) sejak pool dibuat; cache parquet, dilanjutkan bila ada."""
    tag = token if token in ("base", "quote") else token[:10].lower()
    f = _dir("ohlcv") / f"{net}_{pool[:18].lower()}_{tag}_{tf[0]}{agg}.parquet"
    old = pd.read_parquet(f) if f.exists() else None
    if old is not None and not refresh:
        return old
    stop = pd.Timestamp(created).timestamp() if created else 0
    rows, before = [], int(time.time()) + 60
    since = old.index.max().timestamp() if old is not None and len(old) else 0
    while True:
        d = gt(f"/networks/{net}/pools/{pool}/ohlcv/{tf}", aggregate=agg, limit=1000, before_timestamp=before,
               currency="usd", token=token)
        lst = ((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        if not lst:
            break
        rows += lst
        first = min(r[0] for r in lst)
        if first <= max(stop, since) or len(lst) < 1000:
            break
        before = int(first)
    if rows:
        df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "vol"]).drop_duplicates("t")
        df.index = pd.to_datetime(df.pop("t"), unit="s", utc=True)
        df = df.sort_index().astype(float)
        if old is not None:
            df = pd.concat([old, df]).groupby(level=0).last().sort_index()
    else:
        df = old if old is not None else pd.DataFrame(columns=["open", "high", "low", "close", "vol"])
    df.to_parquet(f)
    return df


# ---------------------------------------------------------------- acuan harga
def _zip_1m(url: str) -> pd.DataFrame | None:
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
    except urllib.error.HTTPError:
        return None
    raw = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4, 7])
    raw.columns = ["t", "open", "high", "low", "close", "qvol"]
    t = raw.pop("t").astype("int64")
    raw.index = pd.to_datetime(t, unit="us" if t.iloc[0] > 1e14 else "ms", utc=True)
    return raw.astype(float)


def binance_1m(sym: str, start: str, end: str) -> pd.DataFrame:
    """Kline 1 menit Binance spot dari data.binance.vision (zip bulanan; bila belum terbit -> zip harian)."""
    f = _dir("acuan") / f"{sym}_1m.parquet"
    old = pd.read_parquet(f) if f.exists() else pd.DataFrame()
    have = set(old.index.strftime("%Y-%m-%d")) if len(old) else set()
    parts = [old] if len(old) else []
    base = "https://data.binance.vision/data/spot"
    for m in pd.period_range(pd.Timestamp(start), pd.Timestamp(end), freq="M"):
        days = [d for d in pd.date_range(m.start_time, m.end_time.normalize()) if d <= pd.Timestamp(end)]
        need = [d for d in days if d.strftime("%Y-%m-%d") not in have]
        if not need:
            continue
        df = _zip_1m(f"{base}/monthly/klines/{sym}/1m/{sym}-1m-{m}.zip") if len(days) == m.days_in_month else None
        if df is not None:
            parts.append(df)
            print(f"  {sym} {m}: {len(df)}")
            continue
        for d in need:
            df = _zip_1m(f"{base}/daily/klines/{sym}/1m/{sym}-1m-{d:%Y-%m-%d}.zip")
            if df is not None:
                parts.append(df)
        print(f"  {sym} {m}: harian {len(need)}")
    df = pd.concat(parts).sort_index() if parts else pd.DataFrame()
    df = df[~df.index.duplicated(keep="last")]
    df.to_parquet(f)
    return df


def saham_1m(sym: str, start: str, end: str) -> pd.DataFrame:
    """Saham AS 1 menit (jam bursa reguler) dari Twelve Data, jendela 12 hari (< 5.000 candle)."""
    f = _dir("acuan") / f"{sym}_1m.parquet"
    old = pd.read_parquet(f) if f.exists() else pd.DataFrame()
    cur = pd.Timestamp(start, tz="UTC")
    if len(old):
        cur = max(cur, old.index.max().normalize() + pd.Timedelta(days=1))
    stop = pd.Timestamp(end, tz="UTC")
    key = os.environ.get("TWELVEDATA_API_KEY", "")
    parts = [old] if len(old) else []
    while cur < stop:
        nxt = min(cur + pd.Timedelta(days=12), stop)
        q = urllib.parse.urlencode({"symbol": sym, "interval": "1min", "start_date": f"{cur:%Y-%m-%d %H:%M:%S}",
                                    "end_date": f"{nxt:%Y-%m-%d %H:%M:%S}", "outputsize": 5000, "timezone": "UTC",
                                    "order": "ASC", "apikey": key})
        d = {}
        for k in range(6):
            try:
                with urllib.request.urlopen("https://api.twelvedata.com/time_series?" + q, timeout=60) as r:
                    d = json.loads(r.read())
            except Exception:  # noqa: BLE001
                time.sleep(10 * (k + 1))
                continue
            if "credits" in str(d.get("message", "")).lower():
                time.sleep(61)
                continue
            break
        time.sleep(8)
        if d.get("status") == "ok" and d.get("values"):
            df = pd.DataFrame(d["values"])
            df.index = pd.to_datetime(df.datetime, utc=True)
            parts.append(df[["open", "high", "low", "close", "volume"]].astype(float))
            print(f"  {sym} {cur:%Y-%m-%d}: {len(df)}")
        else:
            print(f"  {sym} {cur:%Y-%m-%d}: {d.get('message', d.get('status'))}")
        cur = nxt
    df = pd.concat(parts).sort_index() if parts else pd.DataFrame()
    df = df[~df.index.duplicated(keep="last")]
    if len(df):
        df.to_parquet(f)
    return df



# ---------------------------------------------------------------- daftar token resmi (dicek 8 Okt 2026)
# Robinhood Chain: token saham resmi = nama "<Perusahaan> • Robinhood Token" + id CoinGecko; ada tiruan beralamat
# mirip (awal/akhir sama) tanpa id CoinGecko -> tidak dipakai sebagai token resmi.
RH_STABLE = {"0x5fc5360d0400a0fd4f2af552add042d716f1d168": "USDG"}
RH_ETH = {"0x0bd7d308f8e1639fab988df18a8011f41eacad73": "WETH", "0x0000000000000000000000000000000000000000": "ETH"}
RH_SAHAM = {
    "CRCL": "0xdf0992e440dd0be65bd8439b609d6d4366bf1cb5", "NVDA": "0xd0601ce157db5bdc3162bbac2a2c8af5320d9eec",
    "SPY": "0x117cc2133c37b721f49de2a7a74833232b3b4c0c", "TSLA": "0x322f0929c4625ed5bad873c95208d54e1c003b2d",
    "AAPL": "0xaf3d76f1834a1d425780943c99ea8a608f8a93f9", "COIN": "0x6330d8c3178a418788df01a47479c0ce7ccf450b",
    "MSTR": "0xec262a75e413fafd0df80480274532c79d42da09", "PLTR": "0x894e1ec2d74ffe5aef8dc8a9e84686accb964f2a",
    "GOOGL": "0x2e0847e8910a9732eb3fb1bb4b70a580adad4fe3", "AMZN": "0x12f190a9f9d7d37a250758b26824b97ce941bf54",
    "META": "0xc0d6457c16cc70d6790dd43521c899c87ce02f35", "QQQ": "0xd5f3879160bc7c32ebb4dc785f8a4f505888de68",
    "AMD": "0x86923f96303d656e4aa86d9d42d1e57ad2023fdc", "MSFT": "0xe93237c50d904957cf27e7b1133b510c669c2e74",
    "GME": "0x1b0e319c6a659f002271b69db8a7df2f911c153e", "HIMS": "0xccee82fe024c36fa15e1005ede3e9e4787e23d09",
}
ARC_STABLE = {"0x3600000000000000000000000000000000000000": "USDC", "0x0000000000000000000000000000000000000000": "USDC"}
ARC_TOKEN = {  # dua alamat per aset di Arc; _b cirBTC/EURC = RESMI (dokumen Circle), _a = tiruan; WETH/CRCL: penerbit tidak jelas
    "WETH_a": ("0x41d5379e2fcce2c28802aa9f2536541b0ab9f938", "ETH"),
    "WETH_b": ("0x128cc466b61f542da60c70e3aa11c10e19b84edb", "ETH"),
    "cirBTC_a": ("0x560f6b48d41056de13983ad1601d76d3d851a30b", "BTC"),
    "cirBTC_b": ("0x171a4217b86a807a64eb94757db6849fb4bdbaa0", "BTC"),
    "EURC_a": ("0x834dcdca521657fe234f37f69546ac16afccfc0e", "EUR"),
    "EURC_b": ("0xbef5f6d51cb62b58e6a8f77868681825c6fe21c1", "EUR"),
    "CRCL_a": ("0xe071fdec0289fc1dfbc39552e5b5f67b4dd3bbfc", "CRCL"),
    "CRCL_b": ("0x2ba0f44bdfc17fba30eda9cdbecb908ca45b043b", "CRCL"),
}


def target() -> list[tuple[str, str, str, str]]:
    """(network, nama, alamat token, acuan)."""
    out = [("robinhood", s, a, s) for s, a in RH_SAHAM.items()]
    out.append(("robinhood", "WETH", "0x0bd7d308f8e1639fab988df18a8011f41eacad73", "ETH"))
    out += [("arc", n, a, ref) for n, (a, ref) in ARC_TOKEN.items()]
    return out


def semua_pool() -> None:
    for net, nama, addr, _ in target():
        r = token_pools(net, addr)
        print(f"{net} {nama}: {len(r['pools'])} pool", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "daftar":
        daftar(sys.argv[2])
    elif cmd == "token":
        r = token_pools(sys.argv[2], sys.argv[3])
        print(len(r["pools"]), "pool")
    elif cmd == "ohlcv":
        df = ohlcv(sys.argv[2], sys.argv[3], *(sys.argv[4:5] or ["base"]))
        print(df.head(), len(df))
    elif cmd == "pool":
        semua_pool()
    elif cmd == "acuan":
        for s in ("ETHUSDT", "BTCUSDT", "EURUSDT"):
            binance_1m(s, "2026-06-25", pd.Timestamp.now("UTC").strftime("%Y-%m-%d"))
    else:
        print(__doc__)
