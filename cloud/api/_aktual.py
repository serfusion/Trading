"""Act otomatis berlapis untuk kalender tab News (perbaikan 1 Okt 2026: Act Core PCE & Final GDP 30 Sep tidak terisi).

Penyebab: CSV publik FRED (fred.stlouisfed.org) tidak menjawab dari server Vercel (arsip berita GitHub 1 Okt: "0 Act"),
padahal dari jaringan riset menjawab < 1 detik. Sekarang dicoba berurutan, dan yang pertama punya angka bulan itu dipakai:
1. BLS API resmi (api.bls.gov, tanpa kunci; BLS_API_KEY opsional) — CPI, NFP, pengangguran, upah per jam, PPI; angka
   tersedia beberapa detik setelah rilis 08:30 ET. Satu permintaan memuat semua seri (batas tanpa kunci 25/hari).
2. FRED API (api.stlouisfed.org) bila env FRED_API_KEY diisi di Vercel — semua seri termasuk PCE, GDP, klaim.
3. CSV publik FRED (cara lama).
Act yang sudah ditemukan disimpan di Supabase (baris "aktual") sehingga tidak diambil ulang dan tidak hilang; pengambilan
untuk berita yang belum ber-Act paling sering tiap RETRY (tiap RETRY_FAST di 10 menit pertama setelah rilis; BLS tanpa
kunci dibatasi 25 permintaan/hari, jadi paling banyak ±20 di satu jam rilis). Bila tetap kosong, alasannya dikirim ke aplikasi
(calendar[].actual_info). Hanya library standar Python.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime, timedelta, timezone

import _chat

BLS_V1 = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
# seri FRED (dipakai _chat.FRED_MAP) -> seri BLS yang sama (FRED menyalin angka BLS ini)
BLS = {"CPIAUCSL": "CUSR0000SA0", "CPILFESL": "CUSR0000SA0L1E", "CPIAUCNS": "CUUR0000SA0",
       "PAYEMS": "CES0000000001", "UNRATE": "LNS14000000", "CES0500000003": "CES0500000003",
       "PPIFIS": "WPSFD4", "PPIFES": "WPSFD49104"}
FRED_API = ("https://api.stlouisfed.org/fred/series/observations?series_id={}&api_key={}&file_type=json"
            "&observation_start={}")
RETRY = timedelta(minutes=2)
RETRY_FAST = timedelta(seconds=30)  # 10 menit pertama setelah rilis: hasil & arah emas cepat tampil (2 Okt 2026)
FAST_FOR = timedelta(minutes=10)
WINDOW = timedelta(days=4)          # berita yang lebih lama dari ini tidak dicari lagi
KEEP = timedelta(days=21)           # Act tersimpan dibuang setelah 3 pekan
TIMEOUT = 8


def _short(exc: Exception) -> str:
    """Alasan singkat tanpa URL (URL FRED API memuat kunci)."""
    name = type(exc).__name__
    code = getattr(exc, "code", None)
    if code:
        return f"HTTP {code}"
    return "timeout" if "timeout" in (name + str(exc)).lower() or "timed out" in str(exc).lower() else name


class Fetcher:
    """fetch(seri FRED) -> [(tanggal, nilai)] gabungan BLS + FRED API/CSV; status per sumber dicatat."""

    def __init__(self, env: dict, needed: set[str], opener=None, csv=None):
        self.env, self.needed = env, needed
        self.open = opener or urllib.request.urlopen
        self.csv = csv or _chat.fred_fetch
        self.cache: dict[str, list] = {}
        self.bls: dict[str, list] | None = None
        self.status: dict[str, str] = {}

    def _bls(self) -> dict[str, list]:
        if self.bls is not None:
            return self.bls
        self.bls = {}
        ids = sorted({BLS[s] for s in self.needed if s in BLS})
        if not ids:
            return self.bls
        y = datetime.now(timezone.utc).year
        body = {"seriesid": ids, "startyear": str(y - 1), "endyear": str(y)}
        key = (self.env.get("BLS_API_KEY") or "").strip()
        if key:
            body["registrationkey"] = key
        try:
            req = urllib.request.Request(BLS_V2 if key else BLS_V1, data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "xau-signal/1.0"})
            with self.open(req, timeout=TIMEOUT) as r:
                d = json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - sumber opsional
            self.status["BLS"] = f"gagal ({_short(exc)})"
            return self.bls
        back = {v: k for k, v in BLS.items()}
        for s in (d.get("Results") or {}).get("series") or []:
            rows = []
            for o in s.get("data") or []:
                p = str(o.get("period", ""))
                if not p.startswith("M") or p == "M13":
                    continue
                try:
                    rows.append((date(int(o["year"]), int(p[1:]), 1), float(str(o["value"]).replace(",", ""))))
                except (KeyError, ValueError):
                    continue
            if s.get("seriesID") in back and rows:
                self.bls[back[s["seriesID"]]] = sorted(rows)
        self.status["BLS"] = "ok" if self.bls else f"kosong ({d.get('status', '?')})"
        return self.bls

    def _fred(self, sid: str) -> list:
        key = (self.env.get("FRED_API_KEY") or "").strip()
        if key:
            since = (datetime.now(timezone.utc) - timedelta(days=800)).date().isoformat()
            try:
                with self.open(urllib.request.Request(FRED_API.format(sid, key, since),
                                                      headers={"User-Agent": "xau-signal/1.0"}), timeout=TIMEOUT) as r:
                    obs = json.loads(r.read().decode("utf-8")).get("observations") or []
                out = []
                for o in obs:
                    try:
                        out.append((date.fromisoformat(o["date"]), float(o["value"])))
                    except (KeyError, ValueError):
                        continue
                self.status["FRED API"] = "ok"
                return out
            except Exception as exc:  # noqa: BLE001
                self.status["FRED API"] = f"gagal ({_short(exc)})"
        out = self.csv(sid)
        self.status["FRED CSV"] = "ok" if out else "gagal (tidak menjawab dari server cloud)"
        return out

    def __call__(self, sid: str) -> list:
        if sid not in self.cache:
            merged = dict(self._fred(sid))
            merged.update(dict(self._bls().get(sid, [])))       # BLS paling cepat & resmi: menimpa
            self.cache[sid] = sorted(merged.items())
        return self.cache[sid]


def _key(c: dict) -> str:
    return f"{c['title']}|{c['time']}"


def fill(calendar: list[dict], store, now: datetime, env: dict, fetcher: Fetcher | None = None) -> dict:
    """Isi calendar[].actual / actual_src (dan actual_info bila kosong). Return status sumber (untuk diagnosa)."""
    state = {}
    if store is not None:
        try:
            state = store.get_state("aktual") or {}
        except Exception:  # noqa: BLE001
            state = {}
    found = dict(state.get("found") or {})
    for c in calendar:
        f = found.get(_key(c))
        if f and not c.get("actual"):
            c["actual"], c["actual_src"] = f["actual"], f["src"]
    missing = [c for c in calendar if c.get("released") and not c.get("actual") and c["title"] in _chat.FRED_MAP
               and now - datetime.fromisoformat(c["time"]) <= WINDOW]
    if not missing:
        return {"status": "lengkap"}
    last = state.get("coba")
    fast = any(now - datetime.fromisoformat(c["time"]) <= FAST_FOR for c in missing)
    if fetcher is None and last and now - datetime.fromisoformat(last) < (RETRY_FAST if fast else RETRY):
        for c in missing:
            c["actual_info"] = state.get("info") or ("dicek ulang tiap 30 detik" if fast else "dicek ulang tiap 2 menit")
        return {"status": "ditunda", "sumber": state.get("sumber") or {}}
    fetcher = fetcher or Fetcher(env, {_chat.FRED_MAP[c["title"]][0] for c in missing})
    cache: dict = {}
    for c in missing:
        act = _chat.fred_actual(c["title"], datetime.fromisoformat(c["time"]), now, fetcher, cache)
        if act:
            src = "BLS" if _chat.FRED_MAP[c["title"]][0] in (fetcher.bls or {}) else "FRED"
            c["actual"], c["actual_src"] = act, src
            found[_key(c)] = {"actual": act, "src": src, "t": now.isoformat()}
    gagal = [k for k, v in fetcher.status.items() if not v.startswith("ok")]
    info = ("sumber gagal: " + ", ".join(f"{k} {fetcher.status[k]}" for k in gagal)) if gagal and \
        not any(v.startswith("ok") for v in fetcher.status.values()) else "sumber resmi belum memuat angka baru"
    for c in calendar:
        if c in missing and not c.get("actual"):
            c["actual_info"] = info
    found = {k: v for k, v in found.items() if now - datetime.fromisoformat(v["t"]) <= KEEP}
    if store is not None:
        try:
            store.save_state({"found": found, "coba": now.isoformat(), "sumber": fetcher.status, "info": info},
                             "aktual")
        except Exception:  # noqa: BLE001
            pass
    return {"status": "dicek", "sumber": fetcher.status}
