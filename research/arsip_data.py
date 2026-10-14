"""🗄️ Arsip data otomatis untuk uji validasi ke depan — python -m research.arsip_data <folder_arsip>

Permintaan pengguna 7 Okt 2026: "setiap data keluar (news, candle, copy trader, dll) simpan di repo GitHub dan selalu up
to date". Dijalankan GitHub Actions tiap jam (.github/workflows/arsip_data.yml) dan di-commit ke branch `arsip-data`
(terpisah dari main supaya Vercel & APK tidak ikut build). Setiap pengumpul berdiri sendiri: satu gagal, lainnya jalan.
Data ditambahkan (append + buang duplikat), tidak pernah ditimpa:
  candle/<SIMBOL>_1h.csv      XAU/USD (Twelve Data, butuh secret TWELVEDATA_API_KEY), BTC/ETH/DOGE/ADA (Binance publik)
  candle/XAUUSD_5min.csv      XAU/USD 5 menit (untuk menilai reaksi emas 1 jam setelah tiap berita)
  prediksi/<pekan>.json       baris prediksi berita PERSIS seperti di aplikasi (pipa cloud yang sama), terakhir sebelum rilis
  pra/<pekan>.json            tebakan arah 1–10 dtk CPI/PPI (pra_satu) + jalur + konsensus + jam pertama konsensus indeks
                              → uji maju: python -m research.uji_maju_berita
  nfp_titik/<tgl>.json        potret harian 🔄 titik balik NFP (FRED live)
  berita/ff_<pekan>.json      kalender ForexFactory pekan ini (Act/Cons/Prev, diperbarui tiap jam)
  berita/aktual.jsonl         Act resmi FRED (NFP, CPI, PPI, Retail, klaim, JOLTS, PCE; butuh secret FRED_API_KEY)
  copytrader/<tgl>.json.gz    potret harian OKX/Bitget/Hyperliquid (vault + 300 trader leaderboard teratas)
  kalshi/<tgl>.json.gz        peluang pasar Kalshi CPI/NFP/Fed (harian)
  sentimen/fxssi.jsonl        👥 % posisi BUY XAUUSD per broker ritel (FXSSI, tiap jam) + harian_<bln>.jsonl Kitco & COT
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

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 "
                    "Safari/537.36", "Accept": "application/json", "Content-Type": "application/json"}
ROOT = Path(__file__).resolve().parent.parent
MULAI = "2026-10-07"                       # awal uji maju (validasi ke depan) prediksi berita


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
    for interval, lebar, nama in (("1h", timedelta(hours=1), "1h"), ("5min", timedelta(minutes=5), "5min")):
        d = get("https://api.twelvedata.com/time_series?" + urllib.parse.urlencode(
            {"symbol": "XAU/USD", "interval": interval, "outputsize": 500, "timezone": "UTC", "apikey": key}))
        if d.get("status") == "error":
            raise RuntimeError(str(d.get("message"))[:80])
        vals = d.get("values") or []
        n = append_csv(root / "candle" / f"XAUUSD_{nama}.csv",
                       [[v["datetime"][:16], v["open"], v["high"], v["low"], v["close"]] for v in vals
                        if datetime.fromisoformat(v["datetime"]).replace(tzinfo=timezone.utc) + lebar <= now],
                       ["time_utc", "open", "high", "low", "close"])
        out.append(f"{nama}+{n}")
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
                                           {"languageType": 0, "pageNo": 1, "pageSize": 50})),
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


def _cloud():
    sys.path.insert(0, str(ROOT / "cloud" / "api"))


def mem_nfp(root: Path) -> dict:
    """Kejutan NFP terakhir (Act vs perkiraan) dari arsip ForexFactory → memori aturan NFP (seperti baris 'prarilis')."""
    _cloud()
    import _prarilis
    mem = dict(_prarilis.SEED)
    rows = []
    for f in sorted((root / "berita").glob("ff_*.json")):
        rows += json.loads(f.read_text())
    for r in sorted(rows, key=lambda r: r.get("date", "")):
        t = r.get("title")
        if t in _prarilis.TITLES and r.get("country") == "USD":
            a, f_ = _prarilis.num(r.get("actual")), _prarilis.num(r.get("forecast"))
            if a is not None and f_ is not None:
                mem[t] = {"s": (a > f_) - (a < f_), "time": r.get("date")}
    return mem


class _Store:
    def __init__(self, d: dict):
        self.d = d

    def get_state(self, row: str) -> dict:
        return self.d.get(row, {})

    def save_state(self, data: dict, row: str) -> None:
        self.d[row] = data


def prediksi(root: Path, now: datetime) -> str:
    """Hitung baris prediksi dengan pipa cloud yang sama dengan GET /api/chat, simpan versi terakhir SEBELUM rilis."""
    _cloud()
    import _chat
    import _core
    import _jadwal
    import _persiapan
    import _prarilis
    import _prediksi
    senin = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    ff = root / "berita" / f"ff_{senin}.json"
    rows = json.loads(ff.read_text()) if ff.exists() else get("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
    prep = _persiapan.cards(rows, now)
    calendar = _chat.calendar_json(rows, now, fetch=lambda s: [])
    _jadwal.attach(prep, now)
    store = _Store({"prarilis": {"mem": mem_nfp(root)}})
    key = os.environ.get("TWELVEDATA_API_KEY", "")
    if key:
        try:
            _prarilis.attach(prep, calendar, store, now, lambda: _core.TwelveData(key, "XAU/USD").candles(600, "1h"))
        except Exception:  # noqa: BLE001 - tanpa model prarilis: aturan/dasar
            pass
    try:                                                # 🎲 sumber "pasar" CPI & 🧭 petunjuk teruji (10 Okt 2026)
        import _hari_h
        import _kalshi
        import _petunjuk
        _kalshi.attach(prep, store, now)
        ks = _kalshi.cached_snapshot(prep.get("berita") or [], store, now)[0] if prep.get("berita") else {}
        _hari_h.attach(prep, calendar, store, now, ks, {})
        _petunjuk.attach(prep, calendar, store, now, os.environ)
    except Exception:  # noqa: BLE001 - tanpa pasar: aturan/dasar
        pass
    _prediksi.attach(prep, store, now, os.environ)
    p = root / "prediksi" / f"{senin}.json"
    old = json.loads(p.read_text()) if p.exists() else {}
    n = 0
    for c in (prep.get("berita") or []) + (prep.get("mendatang") or []):
        pr = c.get("prediksi")
        t = datetime.fromisoformat(c["time"]).astimezone(timezone.utc)
        if not pr or t <= now or t - now > timedelta(days=8):
            continue                                    # hanya prediksi yang masih berlaku sebelum rilis
        titik = next((d for d in pr.get("detail") or [] if d.get("judul", "").startswith("🔄")), None)
        old[f"{c['title']}|{c['time']}"] = {"title": c["title"], "time": c["time"], "teks": pr["teks"], "naik": pr["naik"],
                                            "peringkat": pr.get("peringkat"), "sumber": pr.get("sumber"),
                                            "kandidat": any(d.get("judul", "").startswith("🧪") for d in pr.get("detail") or []),
                                            "titik": titik.get("teks") if titik else None, "dicatat": now.isoformat()}
        n += 1
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(old, ensure_ascii=False, indent=1))
    return f"{n} prediksi aktif"


def tren4(root: Path) -> str | None:
    """Arah emas 4 jam terakhir dari arsip candle XAU 1 jam (naik/turun) — pembanding "cara sekilas" di uji maju."""
    f = root / "candle" / "XAUUSD_1h.csv"
    if not f.exists():
        return None
    rows = list(csv.reader(f.open()))[1:]
    if len(rows) < 5:
        return None
    try:
        a, b = float(rows[-1][4]), float(rows[-5][4])
    except (ValueError, IndexError):
        return None
    return "naik" if a > b else "turun" if a < b else None


def pra(root: Path, now: datetime) -> str:
    """UJI MAJU CPI/PPI (13 Okt 2026, pengguna: "yakin tidak ada uji validasi yang terlewat?"): rekam baris arah 1–10 dtk
    (pra_satu) PERSIS seperti aplikasi — arah, persen, status, jalur (indeks/Kalshi), konsensus, peluang Kalshi — untuk berita
    berikutnya, versi terakhir sebelum rilis; plus jam PERTAMA konsensus indeks CPI terlihat (bukti bebas look-ahead).
    Dinilai setelah rilis dengan tick Exness: python -m research.uji_maju_berita."""
    _cloud()
    import _cpi_detik
    import _jadwal
    import _persiapan
    import _ppi_wti
    import _pra_aset
    senin = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    ff = root / "berita" / f"ff_{senin}.json"
    rows = json.loads(ff.read_text()) if ff.exists() else get("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
    prep = _persiapan.cards(rows, now)
    _jadwal.attach(prep, now)
    store = _Store({})
    try:                                   # 14 Okt: Act resmi ke kartu supaya PPI ← CPI tercatat seperti di aplikasi
        import _aktual
        import _chat
        import chat as _chat_api
        cal = _chat.calendar_json(rows, now, fetch=lambda s: [])
        _aktual.fill(cal, None, now, os.environ)
        _chat_api.isi_act(prep, cal)
    except Exception:  # noqa: BLE001
        pass
    _cpi_detik.attach(prep, store, now)
    _ppi_wti.attach(prep, store, now)
    _pra_aset.attach(prep, now, None)
    s = prep.get("pra_satu") or {}
    p = root / "pra" / f"{senin}.json"
    old = json.loads(p.read_text()) if p.exists() else {}
    n = 0
    for c in (prep.get("berita") or []) + (prep.get("mendatang") or []):
        g = c.get("cpi_detik") or c.get("ppi_wti")
        t = datetime.fromisoformat(c["time"]).astimezone(timezone.utc)
        if not g or t <= now or t - now > timedelta(days=8):
            continue
        k = f"{c['title']}|{c['time']}"
        lama = old.get(k) or {}
        ix = (g.get("indeks") or {}).get("selisih") or {}
        ada_ix = any(v is not None for v in ix.values())
        old[k] = {"title": c["title"], "time": c["time"], "arah": g.get("arah"), "persen": g.get("persen"),
                  "status": g.get("status"), "jalur": g.get("jalur") or ("minyak" if c.get("ppi_wti") else None),
                  "konsensus": g.get("konsensus"), "indeks": ix, "kalshi": (g.get("terbaru") or {}).get("kalshi"),
                  "situasi": (g.get("terbaru") or {}).get("situasi"),
                  "indeks_pertama": lama.get("indeks_pertama") or (now.isoformat() if ada_ix else None),
                  "pra_satu": s.get("teks") if s.get("time") == c["time"] else lama.get("pra_satu"),
                  # 14 Okt: pembanding "cara sekilas" (AI lain): ikut tren emas 4 jam terakhir sebelum rilis
                  "sekilas_tren4": tren4(root) if t - now <= timedelta(hours=2) else lama.get("sekilas_tren4"),
                  "dicatat": now.isoformat()}
        n += 1
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(old, ensure_ascii=False, indent=1))
    return f"{n} tebakan CPI/PPI aktif"


def nfp_titik(root: Path, now: datetime) -> str:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        return "dilewati (secret FRED_API_KEY belum ada)"
    p = root / "nfp_titik" / f"{now:%Y-%m-%d}.json"
    if p.exists():
        return "sudah ada hari ini"
    _cloud()
    import _nfp_titik
    f = _nfp_titik.fitur(key, now)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({**f, "ringkas": _nfp_titik.ringkas(f)}, ensure_ascii=False, indent=1))
    return f"lead {f['lead']:+d}, peluang {_nfp_titik.ringkas(f)['peluang']}%"


def sentimen(root: Path, now: datetime) -> str:
    """👥 posisi ritel XAUUSD per broker (FXSSI, tiap jam) + survei Kitco & COT trader kecil (harian) → uji maju
    sentimen orang (riwayat FXSSI tidak tersedia gratis, jadi dikumpulkan sendiri mulai 14 Okt 2026)."""
    d = get("https://fxssi.com/api/current-ratios")
    br = {k: float(v["XAUUSD"]) for k, v in (d.get("brokers") or {}).items() if isinstance(v, dict) and v.get("XAUUSD")}
    if not br:
        return "FXSSI kosong"
    p = root / "sentimen" / "fxssi.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps({"t": now.strftime("%Y-%m-%dT%H:%MZ"), "formed": d.get("formed"), "xau": br}) + "\n")
    harian = root / "sentimen" / f"harian_{now:%Y-%m}.jsonl"
    hari = now.strftime("%Y-%m-%d")
    if not (harian.exists() and f'"{hari}"' in harian.read_text()):
        _cloud()
        import _sentimen
        row = {"hari": hari}
        for k in ("kitco", "cot"):
            try:
                row[k] = getattr(_sentimen, k)()
            except Exception as e:  # noqa: BLE001
                row[k] = f"GAGAL {type(e).__name__}"
        with harian.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return f"FXSSI {len(br)} broker, BUY rata-rata {sum(br.values()) / len(br):.0f}%"


def main(root: Path) -> None:
    now = datetime.now(timezone.utc)
    hasil = {"waktu": now.strftime("%Y-%m-%dT%H:%MZ")}
    for lab, fn in (("candle_kripto", candle_binance), ("candle_xau", candle_xau), ("berita_ff", berita_ff),
                    ("berita_fred", berita_fred), ("copytrader", copytrader), ("kalshi", kalshi),
                    ("nfp_titik", nfp_titik), ("prediksi", prediksi), ("pra", pra), ("sentimen", sentimen)):
        try:
            hasil[lab] = fn(root, now)
        except Exception as e:  # noqa: BLE001 - satu sumber gagal, lainnya tetap
            hasil[lab] = f"GAGAL {type(e).__name__}: {str(e)[:80]}"
    root.mkdir(parents=True, exist_ok=True)
    with (root / "log.jsonl").open("a") as f:
        f.write(json.dumps(hasil, ensure_ascii=False) + "\n")
    print(json.dumps(hasil, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "arsip"))
