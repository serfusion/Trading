"""🗄️ Arsip data otomatis untuk uji validasi ke depan — python -m research.arsip_data <folder_arsip>

Permintaan pengguna 7 Okt 2026: "setiap data keluar (news, candle, copy trader, dll) simpan di repo GitHub dan selalu up
to date". Dijalankan GitHub Actions tiap jam (.github/workflows/arsip_data.yml) dan di-commit ke branch `arsip-data`
(terpisah dari main supaya Vercel & APK tidak ikut build). Setiap pengumpul berdiri sendiri: satu gagal, lainnya jalan.
Data ditambahkan (append + buang duplikat), tidak pernah ditimpa:
  candle/<SIMBOL>_1h.csv      XAU/USD (Twelve Data, butuh secret TWELVEDATA_API_KEY), BTC/ETH/DOGE/ADA (Binance publik)
  berita/ff_<pekan>.json      kalender ForexFactory pekan ini (Act/Cons/Prev, diperbarui tiap jam)
  berita/aktual.jsonl         Act resmi FRED (NFP, CPI, PPI, Retail, klaim, JOLTS, PCE; butuh secret FRED_API_KEY)
  copytrader/<tgl>.json.gz    potret harian OKX/Bitget/Hyperliquid (vault + 300 trader leaderboard teratas)
  kalshi/<tgl>.json.gz        peluang pasar Kalshi CPI/NFP/Fed (harian)
  log.jsonl                   ringkasan tiap putaran (berhasil/gagal per pengumpul)
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (arsip-data)", "Accept": "application/json", "Content-Type": "application/json"}


def get(url: str, body: dict | None = None, timeout: int = 30):
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=timeout) as r:
        return json.load(r)


def append_csv(path: Path, rows: list[list], header: list[str]) -> int:
    """Gabung dengan isi lama (kunci = kolom pertama), urut, tulis ulang. Return jumlah baris baru."""
    old = {}
    if path.exists():
        with path.open() as f:
            r = csv.reader(f)
            next(r, None)
            old = {x[0]: x for x in r}
    n0 = len(old)
    for x in rows:
        old[str(x[0])] = [str(v) for v in x]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(old[k] for k in sorted(old))
    return len(old) - n0


def candle_binance(root: Path, now: datetime) -> str:
    out = []
    for coin in ("BTC", "ETH", "DOGE", "ADA"):
        rows = []
        for base in ("https://data-api.binance.vision", "https://api.binance.us"):
            try:
                rows = get(f"{base}/api/v3/klines?symbol={coin}USDT&interval=1h&limit=1000")
                break
            except Exception:  # noqa: BLE001
                continue
        closed = [r for r in rows if r[6] < now.timestamp() * 1000]
        n = append_csv(root / "candle" / f"{coin}USDT_1h.csv",
                       [[datetime.fromtimestamp(r[0] / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M"), *r[1:6]]
                        for r in closed], ["time_utc", "open", "high", "low", "close", "volume"])
        out.append(f"{coin}+{n}")
    return " ".join(out)


def candle_xau(root: Path, now: datetime) -> str:
    key = os.environ.get("TWELVEDATA_API_KEY", "")
    if not key:
        return "dilewati (secret TWELVEDATA_API_KEY belum ada)"
    out = []
    for sym in ("XAU/USD",):
        d = get("https://api.twelvedata.com/time_series?" + urllib.parse.urlencode(
            {"symbol": sym, "interval": "1h", "outputsize": 500, "timezone": "UTC", "apikey": key}))
        vals = d.get("values") or []
        n = append_csv(root / "candle" / f"{sym.replace('/', '')}_1h.csv",
                       [[v["datetime"][:16], v["open"], v["high"], v["low"], v["close"]] for v in vals
                        if datetime.fromisoformat(v["datetime"]).replace(tzinfo=timezone.utc) + timedelta(hours=1) <= now],
                       ["time_utc", "open", "high", "low", "close"])
        out.append(f"{sym}+{n}")
    return " ".join(out)


def berita_ff(root: Path, now: datetime) -> str:
    rows = get("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
    senin = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    p = root / "berita" / f"ff_{senin}.json"
    old = {(r.get("title"), r.get("date"), r.get("country")): r for r in json.loads(p.read_text())} if p.exists() else {}
    for r in rows:
        k = (r.get("title"), r.get("date"), r.get("country"))
        if r.get("actual") or k not in old:          # Act yang sudah ada tidak dihapus bila sumber kosong
            old[k] = {**old.get(k, {}), **{a: b for a, b in r.items() if b not in ("", None)}}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(old.values(), key=lambda r: r.get("date", "")), ensure_ascii=False, indent=0))
    return f"{len(old)} baris, Act {sum(1 for r in old.values() if r.get('actual'))}"


FRED_SERIES = {"PAYEMS": "NFP level", "CPIAUCSL": "CPI", "CPILFESL": "Core CPI", "PPIFIS": "PPI", "RSAFS": "Retail",
               "ICSA": "Klaim", "JTSJOL": "JOLTS", "PCEPILFE": "Core PCE", "UNRATE": "Pengangguran"}


def berita_fred(root: Path, now: datetime) -> str:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        return "dilewati (secret FRED_API_KEY belum ada)"
    p = root / "berita" / "aktual.jsonl"
    seen = set(p.read_text().splitlines()) if p.exists() else set()
    new = []
    for sid in FRED_SERIES:
        obs = get("https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(
            {"series_id": sid, "api_key": key, "file_type": "json",
             "observation_start": (now - timedelta(days=120)).strftime("%Y-%m-%d")}))["observations"]
        for o in obs:
            line = json.dumps({"seri": sid, "tanggal": o["date"], "nilai": o["value"],
                               "vintage": o["realtime_start"]}, sort_keys=True)
            if line not in seen:
                seen.add(line)
                new.append(line)
    if new:
        with p.open("a") as f:
            f.write("\n".join(new) + "\n")
    return f"+{len(new)}"


def _gz(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(obj, separators=(",", ":")).encode()))


def copytrader(root: Path, now: datetime) -> str:
    p = root / "copytrader" / f"{now:%Y-%m-%d}.json.gz"
    if p.exists():
        return "sudah ada hari ini"
    snap, ok = {"waktu": now.isoformat()}, []
    for lab, fn in (("okx", lambda: get("https://www.okx.com/api/v5/copytrading/public-lead-traders?instType=SWAP"
                                        "&sortType=overview&limit=20&page=1")),
                    ("bitget", lambda: get("https://www.bitget.com/v1/trigger/trace/public/traderView",
                                           {"languageType": 0, "pageNo": 1, "pageSize": 50, "sortRule": "profit"})),
                    ("hl_vault", lambda: get("https://stats-data.hyperliquid.xyz/Mainnet/vaults", timeout=60)),
                    ("hl_leaderboard", lambda: sorted(get("https://stats-data.hyperliquid.xyz/Mainnet/leaderboard",
                                                          timeout=120)["leaderboardRows"],
                                                      key=lambda r: -float(r.get("accountValue") or 0))[:300])):
        try:
            snap[lab] = fn()
            ok.append(lab)
        except Exception as e:  # noqa: BLE001
            snap[lab + "_galat"] = f"{type(e).__name__}"
    _gz(p, snap)
    return ",".join(ok)


def kalshi(root: Path, now: datetime) -> str:
    p = root / "kalshi" / f"{now:%Y-%m-%d}.json.gz"
    if p.exists():
        return "sudah ada hari ini"
    out = {}
    for s in ("KXCPI", "KXCPICORE", "KXPAYROLLS", "KXFED", "KXU3"):
        try:
            out[s] = get(f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={s}&status=open&limit=200")
            time.sleep(0.4)
        except Exception as e:  # noqa: BLE001
            out[s + "_galat"] = type(e).__name__
    _gz(p, {"waktu": now.isoformat(), **out})
    return f"{sum(1 for k in out if not k.endswith('_galat'))} seri"


def main(root: Path) -> None:
    now = datetime.now(timezone.utc)
    hasil = {"waktu": now.strftime("%Y-%m-%dT%H:%MZ")}
    for lab, fn in (("candle_kripto", candle_binance), ("candle_xau", candle_xau), ("berita_ff", berita_ff),
                    ("berita_fred", berita_fred), ("copytrader", copytrader), ("kalshi", kalshi)):
        try:
            hasil[lab] = fn(root, now)
        except Exception as e:  # noqa: BLE001 - satu sumber gagal, lainnya tetap
            hasil[lab] = f"GAGAL {type(e).__name__}: {str(e)[:80]}"
    with (root / "log.jsonl").open("a") as f:
        f.write(json.dumps(hasil, ensure_ascii=False) + "\n")
    print(json.dumps(hasil, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "arsip"))
