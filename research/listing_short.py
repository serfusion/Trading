"""SHORT token baru di Binance USD-M perpetual (futures) — python -m research.listing_short [unduh|uji]

Latar (8 Okt 2026): research/listing_baru.py menunjukkan token spot yang baru listing turun median -52% dalam 90 hari
(BARU). Pertanyaan di sini: apakah itu bisa DIPANEN dengan SHORT perp setelah biaya, funding nyata, dan risiko squeeze?

Data (data.binance.vision, karena api/fapi.binance.com 451 dari sesi):
  - daftar perp: listing S3 data/futures/um/monthly/klines/ (USDT; simbol *SETTLED hanya berisi beberapa jam harga
    penyelesaian bervolume 0 -> dibuang);
  - kline 1 jam 120 hari pertama (monthly zip; bulan yang belum ada -> daily zip);
  - fundingRate bulanan (calc_time, funding_interval_hours, last_funding_rate). Funding HANYA tersedia bulanan ->
    bulan berjalan tidak ada (trade yang terkena ditandai `fund_kurang`).
  Disimpan di data/research/eksternal/futures_listing/{1h,funding}/<SYM>.parquet + daftar.parquet.

Hari pertama kline perp = tanggal listing perp. Data bulanan dimulai Jan 2020 -> perp dengan kline pertama tepat
2020-01-01 00:00 dianggap listing SEBELUM 2020 dan dibuang.

Tipe: "baru" = token belum ada di Binance spot >= 30 hari sebelum perp listing (dicek dari data/research/eksternal/
spot_1d); "lama" = koin lama yang baru diberi perp (mis. relisting). Dilaporkan terpisah.

Aturan (grid ditetapkan SEBELUM melihat hasil):
  entry SHORT
    A    : open jam ke-2 perp (candle indeks 1).
    B{X}{p}: harga naik >= X% di atas P0 dalam 7 hari pertama (X 20/50/100; P0 = VWAP jam pertama "v" atau close jam
           pertama "c"); order jual limit di level -> isi = max(level, open candle) (gap naik = harga lebih baik).
    C    : tembus turun di bawah LOW hari-1 (24 jam pertama) dalam 30 hari -> sell-stop di low itu; isi = min(level, open).
  keluar: TP turun Y% (20/30/50), SL naik Z% (20/30/50/100), maks T hari (7/30/60) -> tutup di close candle terakhir.
    SL dicek dulu bila satu candle menyentuh keduanya. Candle entry (B/C, intrabar): SL dicek dengan high candle itu
    (konservatif, termasuk bagian sebelum entry), TP baru dicek mulai candle berikutnya. Gap melewati SL -> isi di open.
  biaya: taker 0,05% + slippage 0,1% per sisi (x2 = 0,3% per sisi), dihitung atas notional masuk & keluar.
  funding NYATA: short menerima rate x (harga/entry) bila rate positif, membayar bila negatif; dijumlah untuk semua
    calc_time di (entry, exit].
  leverage 1x -> return terhadap margin; harga naik >= +95% dari entry = LIKUIDASI (rugi -100%, funding ikut hilang);
    "SL 100%" di grid berarti tanpa SL selain likuidasi.
Periode: LAMA = listing < Okt 2021, BARU = >= Okt 2021. Pembanding acak: short di jam acak 30 hari pertama token yang
sama, aturan keluar sama. TradFi (saham/ETF/komoditas/pra-IPO, sejak Des 2025) dibuang via exchangeInfo
(www.binance.com/fapi/v1/exchangeInfo, data publik).

Hasil 8 Okt 2026 (docs/eksternal/hasil_listing_short.txt; 672 perp kripto 2020-2026, LAMA 126 / BARU 546):
  terpilih dari LAMA = A_TP50_SL20_T7 (short open jam ke-2, TP -50%, SL +20%, tutup 7 hari):
  LAMA +5,5%/trade WR 57%, BARU +2,6% WR 47% (CI90 klaster-bulan +0,6..+4,6), 7/7 tahun +, acak token sama +1,0%
  (p ~0,02), biaya x2 +2,3%. Rapuh: tanpa 5% trade terbaik BARU ~0, 2025 = 61% jumlah return BARU, median trade -13%.
  Short lalu tahan tanpa SL (A_TP50_SL100_T60): 25% token sempat naik >= 100% -> portofolio DD -96%.
"""
from __future__ import annotations

import io
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "futures_listing"
D1 = ROOT / "data" / "research" / "eksternal" / "spot_1d"
OUT = ROOT / "docs" / "eksternal" / "hasil_listing_short.txt"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DL = "https://data.binance.vision/"
UM = "data/futures/um"
POTONG = pd.Timestamp("2021-10-01", tz="UTC")
HARI = 120
# bukan token kripto biasa: indeks, stablecoin, logam/saham TradFi
BUKAN = {"BTCDOM", "DEFI", "BLUEBIRD", "FOOTBALL", "USDC", "XAU", "XAG", "XPT", "XPD", "PAXG", "XAUT"}


# ---------------------------------------------------------------- unduh
def _get(url: str, tries: int = 4) -> bytes | None:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * i)
        except Exception:  # noqa: BLE001 - jaringan putus -> ulang
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"gagal {url}")


def _list(prefix: str) -> tuple[list[str], list[str]]:
    pre, keys, marker = [], [], ""
    while True:
        url = f"{S3}?delimiter=/&prefix={urllib.parse.quote(prefix)}&marker={urllib.parse.quote(marker)}"
        b = None
        for i in range(6):  # listing S3 kadang 404 sesaat (prefix kosong mestinya 200) -> ulang
            b = _get(url)
            if b is not None:
                break
            time.sleep(1 + 2 * i)
        if b is None:
            raise RuntimeError(f"listing gagal {prefix}")
        x = b.decode()
        p = re.findall(r"<Prefix>([^<]*)</Prefix>", x)[1:]
        k = re.findall(r"<Key>([^<]*)</Key>", x)
        pre += p
        keys += k
        if "<IsTruncated>true" not in x:
            return pre, keys
        marker = (p or k)[-1]


def _base(sym: str) -> str:
    b = re.sub(r"(SETTLED)+$", "", sym)[:-4]
    return re.sub(r"^(1000000|10000|1000|1M)(?=[A-Z])", "", b)


def symbols() -> list[str]:
    pre, _ = _list(f"{UM}/monthly/klines/")
    out = []
    for p in pre:
        s = p.rstrip("/").split("/")[-1]
        if not re.fullmatch(r"[A-Z0-9]+USDT", s):
            continue  # USDC/BUSD/kontrak berjangka/simbol non-ASCII; *SETTLED = potongan harga penyelesaian (volume 0)
        if _base(s) in BUKAN:
            continue
        out.append(s)
    return out


def _zip_csv(key: str) -> pd.DataFrame | None:
    b = _get(DL + key)
    if b is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(b))
    return pd.read_csv(z.open(z.namelist()[0]), header=None)


def _kline(key: str) -> pd.DataFrame | None:
    raw = _zip_csv(key)
    if raw is None:
        return None
    raw = raw[pd.to_numeric(raw[0], errors="coerce").notna()].iloc[:, [0, 1, 2, 3, 4, 5, 7]]
    raw.columns = ["t", "open", "high", "low", "close", "vol", "qvol"]
    t = raw.pop("t").astype("int64")
    raw.index = pd.to_datetime(t, unit="us" if t.iloc[0] > 1e14 else "ms", utc=True)
    return raw.astype(float)


def _funding(key: str) -> pd.DataFrame | None:
    raw = _zip_csv(key)
    if raw is None:
        return None
    raw = raw[pd.to_numeric(raw[0], errors="coerce").notna()]
    if raw.shape[1] >= 3:
        df = pd.DataFrame({"jam": raw[1].astype(float).values, "rate": raw[2].astype(float).values})
    else:
        df = pd.DataFrame({"jam": np.nan, "rate": raw[1].astype(float).values})
    t = raw[0].astype("int64").values
    df.index = pd.to_datetime(t, unit="us" if t[0] > 1e14 else "ms", utc=True)
    return df


def unduh_satu(sym: str) -> dict:
    f1h, ffd = DIR / "1h" / f"{sym}.parquet", DIR / "funding" / f"{sym}.parquet"
    info = {"sym": sym}
    try:
        _, keys = _list(f"{UM}/monthly/klines/{sym}/1h/")
        months = sorted(re.search(r"-(\d{4}-\d{2})\.zip$", k).group(1) for k in keys if k.endswith(".zip"))
        info.update(m0=months[0] if months else None, m1=months[-1] if months else None, nbulan=len(months))
        if not months:
            return info | {"msg": "tanpa bulan"}
        if not f1h.exists():
            m0 = pd.Period(months[0], "M")
            parts = []
            # bulan pertama dulu -> tahu t0 -> sampai t0 + 120 hari
            first = _kline(f"{UM}/monthly/klines/{sym}/1h/{sym}-1h-{m0}.zip")
            if first is None or first.empty:
                return info | {"msg": "bulan pertama kosong"}
            parts.append(first)
            t0 = first.index[0]
            akhir = (t0 + pd.Timedelta(days=HARI)).tz_localize(None)
            for m in pd.period_range(m0 + 1, akhir, freq="M"):
                if str(m) in months:
                    x = _kline(f"{UM}/monthly/klines/{sym}/1h/{sym}-1h-{m}.zip")
                    if x is not None:
                        parts.append(x)
                elif str(m) > months[-1]:  # bulan belum diterbitkan -> harian (bila simbol masih hidup)
                    for d in pd.date_range(m.start_time, min(m.end_time, pd.Timestamp.now(), akhir)):
                        y = _kline(f"{UM}/daily/klines/{sym}/1h/{sym}-1h-{d:%Y-%m-%d}.zip")
                        if y is not None:
                            parts.append(y)
            df = pd.concat(parts).sort_index()
            df = df[~df.index.duplicated()]
            df = df[df.index < t0 + pd.Timedelta(days=HARI)]
            df.to_parquet(f1h)
        df = pd.read_parquet(f1h)
        t0 = df.index[0]
        info.update(t0=t0, n1h=len(df), akhir=df.index[-1])
        if not ffd.exists():
            _, fk = _list(f"{UM}/monthly/fundingRate/{sym}/")
            fm = {re.search(r"-(\d{4}-\d{2})\.zip$", k).group(1): k for k in fk if k.endswith(".zip")}
            parts = []
            for m in pd.period_range(t0.tz_localize(None), (t0 + pd.Timedelta(days=HARI)).tz_localize(None), freq="M"):
                if str(m) in fm:
                    x = _funding(fm[str(m)])
                    if x is not None:
                        parts.append(x)
            fd = pd.concat(parts).sort_index() if parts else pd.DataFrame(columns=["jam", "rate"])
            fd = fd[~fd.index.duplicated()]
            fd.to_parquet(ffd)
        fd = pd.read_parquet(ffd)
        info.update(nfund=len(fd), fund_akhir=fd.index[-1] if len(fd) else pd.NaT)
        return info | {"msg": "ok"}
    except Exception as exc:  # noqa: BLE001
        return info | {"msg": f"gagal {exc}"}


def unduh_info() -> None:
    """exchangeInfo futures (data publik; fapi.binance.com 451, www.binance.com/fapi menjawab) -> jenis aset
    (COIN vs EQUITY/COMMODITY/PREMARKET 'TradFi' yang dibuka Binance sejak Des 2025)."""
    b = _get("https://www.binance.com/fapi/v1/exchangeInfo")
    if b:
        (DIR / "exchangeInfo.json").write_bytes(b)


def jenis() -> dict[str, str]:
    f = DIR / "exchangeInfo.json"
    if not f.exists():
        return {}
    import json
    return {x["symbol"]: x.get("underlyingType", "") for x in json.loads(f.read_text())["symbols"]}


def unduh() -> None:
    (DIR / "1h").mkdir(parents=True, exist_ok=True)
    (DIR / "funding").mkdir(parents=True, exist_ok=True)
    syms = symbols()
    print(len(syms), "simbol perp USDT", flush=True)
    rows = []
    with ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(unduh_satu, syms)):
            rows.append(r)
            if r.get("msg") != "ok" or i % 50 == 0:
                print(i, r.get("sym"), r.get("m0"), r.get("msg"), flush=True)
    pd.DataFrame(rows).to_parquet(DIR / "daftar.parquet")
    unduh_info()
    print("SELESAI", flush=True)




# ---------------------------------------------------------------- analisis
SISI = 0.0015          # taker 0,05% + slippage 0,1% per sisi
TP_L = (0.20, 0.30, 0.50)
SL_L = (0.20, 0.30, 0.50, 1.00)
T_L = (7, 30, 60)
X_L = (0.20, 0.50, 1.00)
H = np.int64(3_600_000_000_000)   # 1 jam dalam ns
LIKUIDASI = 0.95   # short 1x isolated terlikuidasi sekitar +95% (margin pemeliharaan 1-2,5%)
K_ACAK = 40
RNG = np.random.default_rng(20261008)


class Tok:
    """Satu perp: array 1 jam (waktu ns) + funding kumulatif (rate x harga)."""

    def __init__(self, sym, df, fd, tipe, spot_hari, hidup):
        self.sym, self.tipe, self.spot_hari, self.hidup = sym, tipe, spot_hari, hidup
        self.t0 = df.index[0]
        self.ts = df.index.as_unit("ns").asi8
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.v, self.qv = df.vol.to_numpy(float), df.qvol.to_numpy(float)
        if not isinstance(fd.index, pd.DatetimeIndex) or fd.empty:
            fd = pd.DataFrame({"rate": []}, index=pd.DatetimeIndex([], tz="UTC"))
        fd = fd[fd.index >= self.t0]
        self.ft = fd.index.floor("min").as_unit("ns").asi8
        # harga saat funding = close candle terakhir yang dimulai sebelum waktu funding
        j = np.searchsorted(self.ts, self.ft, side="left") - 1
        ok = j >= 0
        self.ft, rate, j = self.ft[ok], fd.rate.to_numpy(float)[ok], j[ok]
        self.rate = rate
        self.fcum = np.concatenate([[0.0], np.cumsum(rate * self.c[j])])
        self.fund_akhir = self.ft[-1] if len(self.ft) else np.int64(0)

    def fsum(self, t_a, t_b):
        """Jumlah rate x harga untuk funding di (t_a, t_b]."""
        a = np.searchsorted(self.ft, t_a, side="right")
        b = np.searchsorted(self.ft, t_b, side="right")
        return self.fcum[b] - self.fcum[a]


def tokens() -> list[Tok]:
    daftar = pd.read_parquet(DIR / "daftar.parquet")
    spot0 = {}
    for f in D1.glob("*.parquet"):
        ix = pd.read_parquet(f, columns=["close"]).index
        if len(ix):
            spot0[f.stem] = ix[0]
    kini = pd.Timestamp.now(tz="UTC")
    m1_maks = daftar.m1.dropna().max()
    ut = jenis()
    out = []
    for r in daftar.itertuples():
        f1h, ffd = DIR / "1h" / f"{r.sym}.parquet", DIR / "funding" / f"{r.sym}.parquet"
        if r.msg != "ok" or not f1h.exists():
            continue
        if ut.get(r.sym, "COIN") != "COIN":
            continue  # saham/ETF/komoditas/pra-IPO TradFi, indeks, FX -> bukan token kripto baru
        df = pd.read_parquet(f1h)
        if len(df) < 48 or df.index[0] <= pd.Timestamp("2020-01-01 00:00", tz="UTC"):
            continue  # listing sebelum 2020 (data bulanan mulai Jan 2020) atau terlalu pendek
        if df.vol.iloc[:24].sum() <= 0:
            continue
        df = df[df.vol > 0] if (df.vol == 0).mean() > 0.5 else df
        fd = pd.read_parquet(ffd) if ffd.exists() else pd.DataFrame(columns=["jam", "rate"])
        b = _base(r.sym)
        s0 = spot0.get(b)
        spot_hari = (df.index[0] - s0).days if s0 is not None else None
        tipe = "lama" if spot_hari is not None and spot_hari >= 30 else "baru"
        # masih diperdagangkan = data bulanan sampai bulan terbit terakhir, atau data harian sampai kini
        hidup = (r.m1 == m1_maks) or df.index[-1] >= kini - pd.Timedelta(days=3)
        out.append(Tok(r.sym, df, fd, tipe, spot_hari, hidup))
    return out


def entri(k: Tok) -> list[tuple[str, int, float, bool]]:
    """(nama aturan, indeks candle, harga isi, intrabar?) — paling banyak satu per aturan per token."""
    out = [("A", 1, k.o[1], False)]
    t0 = k.ts[0]
    w7 = np.searchsorted(k.ts, t0 + 7 * 24 * H)
    p0 = {"v": k.qv[0] / k.v[0] if k.v[0] > 0 else k.c[0], "c": k.c[0]}
    for X in X_L:
        for nm, p in p0.items():
            lv = p * (1 + X)
            j = np.flatnonzero(k.h[1:w7] >= lv)
            if len(j):
                j = j[0] + 1
                out.append((f"B{int(X * 100)}{nm}", j, max(lv, k.o[j]), True))
    d1 = np.searchsorted(k.ts, t0 + 24 * H)
    w30 = np.searchsorted(k.ts, t0 + 30 * 24 * H)
    if d1 < len(k.ts):
        L1 = k.l[:d1].min()
        j = np.flatnonzero(k.l[d1:w30] < L1)
        if len(j):
            j = j[0] + d1
            out.append(("C", j, min(L1, k.o[j]), True))
    return out


def keluar(k: Tok, i0: int, pe: float, intrabar: bool, sisi: float = SISI, jalur: bool = False):
    """Semua kombinasi (TP, SL, T) untuk satu entry. Kembali list dict (atau None bila trade masih terbuka)."""
    n = len(k.ts)
    te = k.ts[i0]
    cmh = np.maximum.accumulate(k.h[i0:])
    st = i0 + 1 if intrabar else i0
    cml = np.minimum.accumulate(k.l[st:]) if st < n else np.array([np.inf])
    res = []
    for T in T_L:
        jT = np.searchsorted(k.ts, te + T * 24 * H) - 1      # candle terakhir yang dimulai sebelum te+T
        ujung_data = k.ts[-1] + H < te + T * 24 * H
        for Z in SL_L:
            lsl = pe * (1 + min(Z, LIKUIDASI))   # SL 100% = likuidasi 1x (~ +95% karena margin pemeliharaan)
            isl = np.searchsorted(cmh, lsl, side="left")
            jsl = i0 + isl if isl < len(cmh) else n + 10
            for Y in TP_L:
                ltp = pe * (1 - Y)
                itp = np.searchsorted(-cml, -ltp, side="left")
                jtp = st + itp if itp < len(cml) else n + 10
                if jsl <= jT and jsl <= jtp:
                    j, why = jsl, "SL"
                    px = lsl if j == i0 else max(lsl, k.o[j])
                    t_end = k.ts[j]
                elif jtp <= jT:
                    j, why = jtp, "TP"
                    px = ltp if j == i0 else min(ltp, k.o[j])
                    t_end = k.ts[j]
                else:
                    if ujung_data and k.hidup:
                        res.append(None)   # masih terbuka di data -> dibuang
                        continue
                    j = min(jT, n - 1)
                    why = "WAKTU" if not ujung_data else "DELIST"
                    px = k.c[j]
                    t_end = k.ts[j]
                gross = max((pe - px) / pe, -1.0)
                fund = k.fsum(te, t_end) / pe
                biaya = sisi * (1 + px / pe)
                net = max(gross - biaya + fund, -1.0)
                if px >= pe * (1 + LIKUIDASI):   # tersentuh harga likuidasi -> seluruh margin hilang
                    gross, net, why = -1.0, -1.0, "LIKUIDASI"
                d = {"T": T, "SL": Z, "TP": Y, "j": j, "why": why, "px": px, "gross": gross, "fund": fund,
                     "biaya": biaya, "net": net, "mae": cmh[j - i0] / pe - 1, "t_end": t_end,
                     "fund_kurang": (t_end > k.fund_akhir + 8 * H) and not (why == "DELIST")}
                if jalur:
                    cc = k.c[i0:j + 1]
                    fcs = np.array([k.fsum(te, t) for t in k.ts[i0:j + 1]]) / pe
                    path = np.maximum((pe - cc) / pe, -1) - sisi * (1 + cc / pe) + fcs
                    path[-1] = net
                    d["path_t"], d["path"] = k.ts[i0:j + 1], path
                res.append(d)
    return res


KOMBO = [(T, Z, Y) for T in T_L for Z in SL_L for Y in TP_L]


def grid(toks: list[Tok], sisi: float = SISI) -> pd.DataFrame:
    rows = []
    for k in toks:
        for nm, i0, pe, intra in entri(k):
            if i0 >= len(k.ts):
                continue
            for d in keluar(k, i0, pe, intra, sisi):
                if d is None:
                    continue
                d.pop("j")
                rows.append({"sym": k.sym, "tipe": k.tipe, "t0": k.t0, "entry": nm, "te": k.ts[i0], "pe": pe, **d})
    df = pd.DataFrame(rows)
    df["aturan"] = df.entry + "_TP" + (df.TP * 100).astype(int).astype(str) + "_SL" + \
        (df.SL * 100).astype(int).astype(str) + "_T" + df["T"].astype(str)
    df["periode"] = np.where(df.t0 < POTONG, "LAMA", "BARU")
    df["tahun"] = df.t0.dt.year
    return df


def acak(toks: list[Tok], sisi: float = SISI) -> pd.DataFrame:
    """K_ACAK entry acak (open candle) per token dalam 30 hari pertama, semua kombinasi keluar."""
    rows = []
    for k in toks:
        w30 = np.searchsorted(k.ts, k.ts[0] + 30 * 24 * H)
        if w30 <= 2:
            continue
        for r in range(K_ACAK):
            i0 = int(RNG.integers(1, w30))
            for (T, Z, Y), d in zip(KOMBO, keluar(k, i0, k.o[i0], False, sisi)):
                rows.append((k.sym, r, T, Z, Y, np.nan if d is None else d["net"]))
    return pd.DataFrame(rows, columns=["sym", "r", "T", "SL", "TP", "net"])


# ---------------------------------------------------------------- statistik
def boot_ci(x: np.ndarray, B: int = 2000, q=(5, 95)) -> tuple[float, float]:
    if len(x) < 2:
        return (np.nan, np.nan)
    idx = np.random.default_rng(1).integers(0, len(x), (B, len(x)))
    m = x[idx].mean(1)
    return tuple(np.percentile(m, q))


def ringkas(x: pd.DataFrame) -> dict:
    n = len(x)
    if n == 0:
        return {"n": 0}
    r = x.net.to_numpy()
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    lo, hi = boot_ci(r)
    return {"n": n, "wr": (r > 0).mean() * 100, "rata": r.mean() * 100, "median": np.median(r) * 100,
            "ci_lo": lo * 100, "ci_hi": hi * 100, "pf": pos / neg if neg > 0 else np.inf,
            "fund": x.fund.mean() * 100, "sl": (x.why == "SL").mean() * 100,
            "t": r.mean() / (r.std(ddof=1) / np.sqrt(n)) if n > 2 and r.std() > 0 else np.nan}


def banding_acak(tr: pd.DataFrame, ac: pd.DataFrame, B: int = 2000) -> dict:
    """Rata-rata acak (token & aturan keluar yang sama) + p = peluang rata-rata acak >= rata-rata aturan."""
    T, Z, Y = tr["T"].iloc[0], tr.SL.iloc[0], tr.TP.iloc[0]
    a = ac[(ac["T"] == T) & (ac.SL == Z) & (ac.TP == Y) & ac.sym.isin(tr.sym)].dropna(subset=["net"])
    if a.empty:
        return {"acak": np.nan, "p": np.nan}
    piv = a.pivot_table(index="sym", columns="r", values="net")
    piv = piv.reindex(tr.sym.unique()).dropna(how="all")
    M = piv.to_numpy()
    mean_tok = np.nanmean(M, 1)
    # replikasi: satu draw acak per token
    cols = np.random.default_rng(3).integers(0, M.shape[1], (B, M.shape[0]))
    draw = M[np.arange(M.shape[0])[None, :], cols]
    draw = np.where(np.isnan(draw), mean_tok[None, :], draw)
    reps = draw.mean(1)
    rule = tr.set_index("sym").net.reindex(piv.index).mean()
    return {"acak": mean_tok.mean() * 100, "p": (reps >= rule).mean()}


def portofolio(trs: list[dict], porsi: float = 0.10, maks: int = 10) -> dict:
    """Hitung ekuitas per jam (mark-to-market) — 10% ekuitas per trade, maks 10 posisi."""
    if not trs:
        return {}
    trs = sorted(trs, key=lambda d: d["te"])
    t_a = min(d["te"] for d in trs)
    t_b = max(d["path_t"][-1] for d in trs)
    jam = np.arange(t_a, t_b + 2 * H, H)
    kas, buka, eq_hist = 1.0, [], []
    i, ambil, lewat = 0, 0, 0
    for t in jam:
        # tutup
        sisa = []
        for b in buka:
            d, m = b
            if d["path_t"][-1] <= t:
                kas += m * (1 + d["net"])
            else:
                sisa.append(b)
        buka = sisa
        eq = kas + sum(m * (1 + d["path"][np.searchsorted(d["path_t"], t, side="right") - 1]) for d, m in buka)
        while i < len(trs) and trs[i]["te"] <= t:
            if len(buka) < maks:
                m = porsi * eq
                kas -= m
                buka.append((trs[i], m))
                ambil += 1
            else:
                lewat += 1
            i += 1
        eq_hist.append(eq)
    eq = np.array(eq_hist)
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    th = (jam[-1] - jam[0]) / (365.25 * 24 * H)
    s = pd.Series(eq, index=pd.to_datetime(jam, utc=True))
    per_th = s.resample("YE").last().pct_change()
    per_th.iloc[0] = s.resample("YE").last().iloc[0] / 1.0 - 1
    return {"akhir": eq[-1], "cagr": (eq[-1] ** (1 / th) - 1) * 100 if eq[-1] > 0 else -100, "dd": dd * 100,
            "ambil": ambil, "lewat": lewat, "per_tahun": (per_th * 100).round(1).to_dict(), "seri": s}


def boot_klaster(x: pd.DataFrame, B: int = 2000) -> tuple[float, float]:
    """CI90 rata-rata per trade dengan resampling per BULAN listing (trade sebulan saling berkorelasi)."""
    g = x.groupby(x.t0.dt.strftime("%Y-%m")).net.agg(["sum", "count"])
    if len(g) < 3:
        return (np.nan, np.nan)
    idx = np.random.default_rng(2).integers(0, len(g), (B, len(g)))
    s, c = g["sum"].to_numpy()[idx].sum(1), g["count"].to_numpy()[idx].sum(1)
    return tuple(np.percentile(s / c, (5, 95)) * 100)


def _fmt(d: dict) -> str:
    if not d or d.get("n", 0) == 0:
        return "n 0"
    return (f"n {d['n']:4d} WR {d['wr']:5.1f}% rata {d['rata']:+6.2f}% med {d['median']:+6.2f}% "
            f"CI90 [{d['ci_lo']:+6.2f}, {d['ci_hi']:+6.2f}] PF {d['pf']:4.2f} SL {d['sl']:4.1f}% fund {d['fund']:+5.2f}%")


def pilih(df: pd.DataFrame, min_n: int = 30) -> pd.DataFrame:
    """Skor tiap aturan: n, rata-rata, t (rata/se). Hanya aturan dengan n >= min_n."""
    g = df.groupby("aturan").net.agg(["count", "mean", "std"])
    g = g[g["count"] >= min_n]
    g["t"] = g["mean"] / (g["std"] / np.sqrt(g["count"]))
    return g.sort_values("t", ascending=False)


def _parse(a: str) -> tuple[str, float, float, int]:
    e, tp, sl, t = a.split("_")
    return e, int(tp[2:]) / 100, int(sl[2:]) / 100, int(t[1:])


def ketahanan(toks, df, ac, a, w) -> None:
    """Uji ketahanan aturan terpilih: tetangga, telat masuk, isi terburuk, tanpa tahun terbaik, kapasitas volume."""
    e, Y, Z, T = _parse(a)
    x = df[df.aturan == a]
    w("-" * 110)
    w(f"UJI KETAHANAN {a}")
    # tetangga: semua aturan keluar untuk entry yang sama
    g = df[df.entry == e].groupby(["periode", "T", "SL", "TP"]).net.agg(["mean", lambda r: (r > 0).mean()])
    g.columns = ["rata", "wr"]
    w(f"  tetangga entry {e} (rata % / WR %), baris = T hari & SL, kolom = TP:")
    for per in ("LAMA", "BARU"):
        w(f"   {per}:" + "".join(f"{'TP' + str(int(y * 100)):>16s}" for y in TP_L))
        for TT in T_L:
            for ZZ in SL_L:
                cel = []
                for YY in TP_L:
                    try:
                        r = g.loc[(per, TT, ZZ, YY)]
                        cel.append(f"{r.rata * 100:+6.2f}/{r.wr * 100:3.0f}%")
                    except KeyError:
                        cel.append("-")
                w(f"     T{TT:<3d} SL{int(ZZ * 100):<4d}" + "".join(f"{c:>16s}" for c in cel))
    pos = g.groupby(level=0).rata.apply(lambda r: f"{(r > 0).sum()}/{len(r)}")
    w(f"  aturan keluar positif untuk entry {e}: LAMA {pos.get('LAMA')}, BARU {pos.get('BARU')}")
    # telat masuk (hanya entry A): candle ke-d
    if e == "A":
        w("  telat masuk (open candle ke-d sejak listing, keluar sama) — rata % (n) LAMA | BARU:")
        for d in (1, 2, 3, 4, 6, 12, 24, 48, 72, 168):
            rr = {"LAMA": [], "BARU": []}
            for k in toks:
                if d >= len(k.ts):
                    continue
                for (TT, ZZ, YY), q in zip(KOMBO, keluar(k, d, k.o[d], False)):
                    if (TT, ZZ, YY) == (T, Z, Y) and q is not None:
                        rr["LAMA" if k.t0 < POTONG else "BARU"].append(q["net"])
            w(f"    d={d:3d} jam: LAMA {np.mean(rr['LAMA']) * 100:+6.2f}% (n {len(rr['LAMA'])}) | "
              f"BARU {np.mean(rr['BARU']) * 100:+6.2f}% (n {len(rr['BARU'])})")
        # isi terburuk: jual di LOW candle jam ke-2 (mustahil lebih buruk dalam jam itu)
        rr = {"LAMA": [], "BARU": []}
        for k in toks:
            for (TT, ZZ, YY), q in zip(KOMBO, keluar(k, 1, k.l[1], True)):
                if (TT, ZZ, YY) == (T, Z, Y) and q is not None:
                    rr["LAMA" if k.t0 < POTONG else "BARU"].append(q["net"])
        w(f"  stres isi terburuk (short di LOW jam ke-2, SL dicek dengan high jam itu): LAMA {np.mean(rr['LAMA']) * 100:+.2f}% "
          f"| BARU {np.mean(rr['BARU']) * 100:+.2f}%")
        vol = pd.Series({k.sym: k.qv[1] for k in toks if k.t0 >= POTONG})
        w(f"  volume USDT candle jam ke-2 (BARU): median {vol.median() / 1e6:.1f} jt, P10 {vol.quantile(.1) / 1e6:.2f} jt, "
          f"P1 {vol.quantile(.01) / 1e6:.2f} jt -> posisi $1.000 = {1000 / vol.quantile(.1) * 100:.3f}% volume jam itu (P10)")
    for per in ("LAMA", "BARU"):
        xp = x[x.periode == per]
        th_best = xp.groupby("tahun").net.sum().idxmax()
        q = xp.net.quantile(0.95)
        w(f"  {per}: tanpa tahun terbaik ({th_best}) {xp[xp.tahun != th_best].net.mean() * 100:+.2f}%; tanpa 5% trade "
          f"terbaik {xp[xp.net <= q].net.mean() * 100:+.2f}%; median {xp.net.median() * 100:+.2f}%")
    bl = x.groupby(x.t0.dt.strftime("%Y-%m")).net.sum() * 100
    w(f"  per bulan listing (jumlah %, 10% margin/trade -> x0,1 = % modal): bulan positif {(bl > 0).sum()}/{len(bl)}, "
      f"terburuk {bl.min():+.1f}% ({bl.idxmin()}), terbaik {bl.max():+.1f}% ({bl.idxmax()})")
    s = (x.sort_values("te").net < 0).astype(int).to_numpy()
    run = mx = 0
    for v in s:
        run = run + 1 if v else 0
        mx = max(mx, run)
    w(f"  kalah beruntun terpanjang (urut waktu entry): {mx}")
    w("  leverage: return per trade x leverage (SL 20% -> rugi ~-20%/-40%/-60% margin di 1x/2x/3x; likuidasi 3x ~ +31% "
      "jadi SL 20% masih di depan kecuali gap). Angka di atas = 1x.")


def uji() -> None:
    toks = tokens()
    L = []
    w = L.append
    w("SHORT token baru di Binance USD-M perpetual — research/listing_short.py (dibuat 8 Okt 2026)")
    w("=" * 110)
    w("Biaya: taker 0,05% + slippage 0,1% per sisi (x2 diuji), funding NYATA per calc_time, leverage 1x, rugi maks -100%.")
    w("LAMA = perp listing < Okt 2021, BARU = >= Okt 2021. Return = % terhadap margin per trade.")
    w("Aturan & grid ditetapkan sebelum melihat hasil (lihat docstring). Satu trade per token per aturan.")
    w("")
    dft = pd.read_parquet(DIR / "daftar.parquet")
    ut = jenis()
    w(f"Perp USDT di data.binance.vision: {len(dft)}; dibuang bukan kripto (TradFi saham/ETF/komoditas/pra-IPO, indeks, "
      f"FX; dari exchangeInfo): {sum(ut.get(x, 'COIN') != 'COIN' for x in dft.sym)}; listing sebelum 2020 / data < 2 hari "
      f"dibuang juga.")
    meta = pd.DataFrame([{"sym": k.sym, "t0": k.t0, "tipe": k.tipe, "hidup": k.hidup} for k in toks])
    meta["th"] = meta.t0.dt.year
    w(f"Perp USDT listing 2020-2026 yang dipakai: {len(toks)}  (tipe 'baru' = belum ada di Binance spot >= 30 hari "
      f"sebelum perp: {(meta.tipe == 'baru').sum()}, 'lama' = koin lama diberi perp: {(meta.tipe == 'lama').sum()})")
    w("Per tahun listing (baru/lama): " + ", ".join(
        f"{y}: {int(((meta.th == y) & (meta.tipe == 'baru')).sum())}/{int(((meta.th == y) & (meta.tipe == 'lama')).sum())}"
        for y in sorted(meta.th.unique())))
    w(f"LAMA {int((meta.t0 < POTONG).sum())} perp, BARU {int((meta.t0 >= POTONG).sum())} perp.")
    w("")

    df = grid(toks)
    df["net2"] = np.maximum(df.gross - 2 * df.biaya + df.fund, -1.0)
    ac = acak(toks)
    df.to_parquet(DIR / "grid_short.parquet")
    w(f"Trade tersimulasi: {len(df)} baris ({df.aturan.nunique()} aturan). Funding tidak lengkap (bulan berjalan belum "
      f"terbit): {df.fund_kurang.mean() * 100:.1f}% baris.")
    w("")

    # ---- ringkasan grid
    agg = df.groupby(["aturan", "periode"]).net.mean().unstack() * 100
    nn = df.groupby(["aturan", "periode"]).net.count().unstack()
    w("RINGKASAN GRID (288 aturan): rata-rata net per trade")
    for per in ("LAMA", "BARU"):
        w(f"  {per}: aturan positif {(agg[per] > 0).sum()}/{agg[per].notna().sum()}, median aturan {agg[per].median():+.2f}%, "
          f"terbaik {agg[per].max():+.2f}% ({agg[per].idxmax()}), terburuk {agg[per].min():+.2f}%")
    both = ((agg.LAMA > 0) & (agg.BARU > 0)).sum()
    w(f"  positif di KEDUA periode: {both}/{len(agg)}")
    w("")
    w("Per entry (rata-rata semua 36 aturan keluar; n = token yang terpicu):")
    for e, g in df.groupby("entry"):
        a = g.groupby("periode").net.mean() * 100
        nt = g.groupby("periode").sym.nunique()
        w(f"  {e:6s} LAMA n {nt.get('LAMA', 0):3d} {a.get('LAMA', np.nan):+6.2f}% | BARU n {nt.get('BARU', 0):3d} "
          f"{a.get('BARU', np.nan):+6.2f}%")
    w("")

    # ---- pembanding acak semua token (tanpa aturan entry)
    acm = ac.merge(meta[["sym", "t0"]], on="sym")
    acm["periode"] = np.where(acm.t0 < POTONG, "LAMA", "BARU")
    a2 = acm.groupby(["T", "SL", "TP", "periode"]).net.mean().unstack() * 100
    w("Pembanding: short di jam ACAK 30 hari pertama (semua token, 40 draw/token) — rata-rata 36 aturan keluar: "
      f"LAMA {a2.LAMA.mean():+.2f}% (terbaik {a2.LAMA.max():+.2f}%), BARU {a2.BARU.mean():+.2f}% (terbaik {a2.BARU.max():+.2f}%)")
    w("")

    # ---- seleksi dari LAMA
    lama, baru = df[df.periode == "LAMA"], df[df.periode == "BARU"]
    sk = pilih(lama)
    w("SELEKSI DARI LAMA (n >= 30, urut t = rata/se). 10 teratas dan hasilnya di BARU:")
    w(f"  {'aturan':24s} {'LAMA n':>6s} {'rata':>7s} {'t':>5s} | {'BARU n':>6s} {'rata':>7s} {'WR':>5s} {'biaya x2':>8s}")
    for a, r in sk.head(10).iterrows():
        b = baru[baru.aturan == a]
        w(f"  {a:24s} {int(r['count']):6d} {r['mean'] * 100:+6.2f}% {r.t:5.2f} | {len(b):6d} {b.net.mean() * 100:+6.2f}% "
          f"{(b.net > 0).mean() * 100:4.0f}% {b.net2.mean() * 100:+7.2f}%")
    w("")
    terpilih = sk.index[0] if len(sk) else None

    # ---- walk-forward per tahun
    w("WALK-FORWARD per tahun (aturan dipilih dari SEMUA tahun sebelumnya, n >= 30, t terbesar; diuji di tahun itu):")
    oos = []
    for y in range(2021, 2027):
        tr = df[df.tahun < y]
        sk2 = pilih(tr)
        if sk2.empty:
            continue
        a = sk2.index[0]
        x = df[(df.tahun == y) & (df.aturan == a)]
        oos.append(x)
        d = ringkas(x)
        w(f"  {y}: pilih {a:24s} (latih n {int(sk2.iloc[0]['count'])}, {sk2.iloc[0]['mean'] * 100:+.2f}%) -> {_fmt(d)}")
    if oos:
        o = pd.concat(oos)
        for per in ("LAMA", "BARU"):
            w(f"  gabungan OOS {per}: {_fmt(ringkas(o[o.periode == per]))}")
        w(f"  gabungan OOS semua: {_fmt(ringkas(o))}  biaya x2 rata {o.net2.mean() * 100:+.2f}%")
    w("")

    # ---- detail aturan terpilih (LAMA) + aturan terbaik BARU (melihat hasil -> hanya info)
    sk_b = pilih(baru)
    calon = [(terpilih, "TERPILIH dari LAMA")]
    if len(sk_b) and sk_b.index[0] != terpilih:
        calon.append((sk_b.index[0], "terbaik di BARU (MELIHAT HASIL -> bukan bukti)"))
    if "A_TP50_SL100_T60" not in [c[0] for c in calon]:
        calon.append(("A_TP50_SL100_T60", "acuan sederhana: short jam ke-2, tahan 60 hari"))
    for a, judul in calon:
        if a is None:
            continue
        x = df[df.aturan == a]
        w("-" * 110)
        w(f"ATURAN {a} — {judul}")
        for per in ("LAMA", "BARU"):
            xp = x[x.periode == per]
            lo, hi = boot_klaster(xp)
            ba = banding_acak(xp, ac) if len(xp) else {"acak": np.nan, "p": np.nan}
            w(f"  {per}: {_fmt(ringkas(xp))}")
            w(f"        CI90 klaster-bulan [{lo:+.2f}, {hi:+.2f}]  biaya x2 rata {xp.net2.mean() * 100:+.2f}%  "
              f"acak token sama {ba['acak']:+.2f}% (p acak >= aturan {ba['p']:.3f})  "
              f"tanpa funding-kurang {xp[~xp.fund_kurang].net.mean() * 100:+.2f}%")
        for tp in ("baru", "lama"):
            xt = x[x.tipe == tp]
            w(f"  tipe {tp:4s}: LAMA {_fmt(ringkas(xt[xt.periode == 'LAMA']))}")
            w(f"             BARU {_fmt(ringkas(xt[xt.periode == 'BARU']))}")
        w("  per tahun listing:")
        th_pos = 0
        ths = sorted(x.tahun.unique())
        for y in ths:
            xy = x[x.tahun == y]
            th_pos += xy.net.mean() > 0
            w(f"    {y}: {_fmt(ringkas(xy))}  x2 {xy.net2.mean() * 100:+6.2f}%")
        w(f"  tahun positif: {th_pos}/{len(ths)}")
        why = x.why.value_counts()
        w(f"  keluar: " + ", ".join(f"{k} {v}" for k, v in why.items()) +
          f"; rugi -100% (likuidasi 1x): {(x.net <= -0.999).sum()}; SL tembus gap (isi > level SL): "
          f"{((x.why == 'SL') & (x.px > x.pe * (1 + x.SL) * 1.001)).sum()}")
        w(f"  5 trade terburuk: " + "; ".join(f"{r.sym} {r.t0:%Y-%m} {r.net * 100:+.0f}% (fund {r.fund * 100:+.1f}%)"
                                             for r in x.nsmallest(5, "net").itertuples()))
        w(f"  funding: rata {x.fund.mean() * 100:+.2f}%, terburuk {x.fund.min() * 100:+.2f}%, terbaik {x.fund.max() * 100:+.2f}%")
        # portofolio
        tk = {k.sym: k for k in toks}
        T, Z, Y = int(x["T"].iloc[0]), float(x.SL.iloc[0]), float(x.TP.iloc[0])
        trs = []
        e = x.entry.iloc[0]
        for k in toks:
            for nm, i0, pe, intra in entri(k):
                if nm != e or i0 >= len(k.ts):
                    continue
                for (TT, ZZ, YY), d in zip(KOMBO, keluar(k, i0, pe, intra, jalur=True)):
                    if (TT, ZZ, YY) == (T, Z, Y) and d is not None:
                        d["te"] = k.ts[i0]
                        trs.append(d)
        for per, cond in (("SEMUA", lambda d: True), ("BARU", lambda d: d["te"] >= POTONG.value),
                          ("LAMA", lambda d: d["te"] < POTONG.value)):
            pf = portofolio([d for d in trs if cond(d)])
            if pf:
                w(f"  portofolio {per} (10% ekuitas/trade, maks 10 posisi, mark-to-market per jam): CAGR {pf['cagr']:+.1f}%/th, "
                  f"max DD {pf['dd']:.1f}%, akhir {pf['akhir']:.2f}x, trade {pf['ambil']} (lewat {pf['lewat']})")
                if per == "SEMUA":
                    w("    per tahun kalender: " + ", ".join(f"{k.year}: {v:+.1f}%" for k, v in pf["per_tahun"].items()))
    w("")

    if terpilih is not None:
        ketahanan(toks, df, ac, terpilih, w)

    # ---- risiko ekor
    w("-" * 110)
    w("RISIKO EKOR (entry A = open jam ke-2):")
    sq = []
    for k in toks:
        n60 = np.searchsorted(k.ts, k.ts[1] + 60 * 24 * H)
        if n60 <= 2:
            continue
        mx = k.h[1:n60].max() / k.o[1] - 1
        sq.append((k.sym, k.t0, mx, k.tipe))
    sq = pd.DataFrame(sq, columns=["sym", "t0", "naik", "tipe"]).sort_values("naik", ascending=False)
    w("  squeeze terbesar (naik maks dari open jam ke-2 dalam 60 hari): " +
      "; ".join(f"{r.sym} {r.t0:%Y-%m} +{r.naik * 100:.0f}%" for r in sq.head(12).itertuples()))
    for th in (0.5, 1.0, 2.0):
        w(f"  token yang sempat naik >= {th * 100:.0f}% di atas harga short: {(sq.naik >= th).mean() * 100:.1f}% "
          f"(LAMA {(sq[sq.t0 < POTONG].naik >= th).mean() * 100:.1f}%, BARU {(sq[sq.t0 >= POTONG].naik >= th).mean() * 100:.1f}%)")
    fr = []
    for k in toks:
        m = k.ft < k.ts[0] + 30 * 24 * H
        if m.any():
            fr.append((k.sym, k.t0, k.rate[m].min(), k.rate[m].max(), k.rate[m].sum()))
    fr = pd.DataFrame(fr, columns=["sym", "t0", "min", "maks", "jumlah"])
    w("  funding 30 hari pertama — rate terendah (short MEMBAYAR): " +
      "; ".join(f"{r.sym} {r.min * 100:+.2f}%/periode" for r in fr.nsmallest(8, "min").itertuples()))
    w("  jumlah funding 30 hari terburuk bagi short: " +
      "; ".join(f"{r.sym} {r.jumlah * 100:+.1f}%" for r in fr.nsmallest(8, "jumlah").itertuples()))
    w(f"  median jumlah funding 30 hari: {fr.jumlah.median() * 100:+.2f}% (positif = short menerima); "
      f"token dengan jumlah < -5%: {(fr.jumlah < -0.05).sum()} dari {len(fr)}")
    w("")
    # ---- vonis (kriteria ditetapkan sebelumnya)
    if terpilih is not None:
        x = df[df.aturan == terpilih]
        xb, xl = x[x.periode == "BARU"], x[x.periode == "LAMA"]
        th = x.groupby("tahun").net.mean()
        ba = banding_acak(xb, ac)
        lo, _ = boot_klaster(xb)
        syarat = {
            "LAMA positif": xl.net.mean() > 0,
            "BARU positif (CI90 klaster-bulan > 0)": xb.net.mean() > 0 and lo > 0,
            f"mayoritas tahun positif ({(th > 0).sum()}/{len(th)})": (th > 0).sum() > len(th) / 2,
            f"mengalahkan acak token sama (p {ba['p']:.3f} <= 0,10)": ba["p"] <= 0.10,
            "biaya x2 tetap positif LAMA & BARU": xl.net2.mean() > 0 and xb.net2.mean() > 0,
        }
        w("-" * 110)
        w(f"VONIS {terpilih}: " + ("LOLOS" if all(syarat.values()) else "TIDAK LOLOS"))
        for k_, v_ in syarat.items():
            w(f"  [{'x' if v_ else ' '}] {k_}")
        tb = xb.groupby("tahun").net.sum()
        w(f"  Catatan jujur: WR BARU {(xb.net > 0).mean() * 100:.0f}%, median {xb.net.median() * 100:+.1f}%; tanpa 5% trade "
          f"terbaik BARU {xb[xb.net <= xb.net.quantile(.95)].net.mean() * 100:+.2f}%; tahun {tb.idxmax()} menyumbang "
          f"{tb.max() / tb.sum() * 100:.0f}% jumlah return BARU. Keunggulan bergantung pada sedikit trade TP besar.")
    w("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    if "unduh" in sys.argv:
        unduh()
    if "uji" in sys.argv:
        uji()
