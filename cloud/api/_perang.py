"""Mode perang Timur Tengah = guncangan minyak: WTI (FRED DCOILWTICO, CSV publik tanpa kunci) naik >= 10% dalam
10 hari bursa. Hanya LABEL ⚠️ di sinyal XAU & heartbeat (keputusan pengguna 30 Sep 2026: XAU tidak dijeda).

Riset (docs/MOMEN_PERANG.md, research/mode_perang.py): sinyal 💰 XAU di mode ini rata-rata −0,06R (2012–2021) dan
−0,53R (5 tahun terakhir) vs normal +0,23/+0,27R. Studi kejadian research/perang_peluang.py: TIDAK ada setup minyak /
pair terkait yang konsisten (emas tidak turun secara konsisten, minyak tidak lanjut naik secara konsisten).

Cadangan (izin pengguna 30 Sep 2026, env WAR_BACKUP): bila FRED gagal/basi, pakai ETF USO (≈ WTI) dari Twelve Data.
research/perang_uso.py: arah sama di FRED, USO, dan Dukascopy WTI (docs/MOMEN_PERANG.md bagian 6). USO disimpan di
baris Supabase 'perang' dan diunduh ulang paling cepat tiap 6 jam (maks ±4 kredit/hari, hanya saat FRED gagal).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone

THR = 0.10
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}"
HEADERS = {"User-Agent": "xau-signal/1.0 (python urllib)", "Accept": "text/csv,*/*"}   # UA peramban ditahan FRED
STALE_DAYS = 10                  # FRED WTI terbit mingguan: data terbaru normal berumur 5–9 hari (> 10: ±1–2%)
USO_REFRESH = timedelta(hours=6)
USO_CLOSE = time(21, 15)         # close harian USO dipakai sesudah NYSE tutup (sama dengan riset)


def fred_rows(series: str = "DCOILWTICO", days: int = 60) -> list[tuple[date, float]]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    req = urllib.request.Request(FRED_CSV.format(series, since), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=6) as r:
        lines = r.read().decode("utf-8").splitlines()[1:]
    out = []
    for ln in lines:
        d, _, v = ln.partition(",")
        try:
            out.append((date.fromisoformat(d), float(v)))
        except ValueError:
            continue                                   # "." = hari libur
    return out


def status(rows: list[tuple[date, float]] | None = None, src: str = "FRED") -> dict | None:
    """{'on', 'oil10' (% 10 hari bursa), 'wti', 'date', 'src', 'text'} atau None bila data kurang."""
    rows = fred_rows() if rows is None else rows
    if len(rows) < 11 or rows[-11][1] <= 0:
        return None
    (d, last), prev = rows[-1], rows[-11][1]
    ch = last / prev - 1
    on = ch >= THR
    what = f"minyak WTI {ch:+.1%} dalam 10 hari (${last:.2f})" if src == "FRED" else \
        f"minyak (ETF USO, cadangan) {ch:+.1%} dalam 10 hari"
    text = (f"⚠️ Mode perang: {what}. Sinyal emas di kondisi ini "
            f"historis lemah (5 th: −0,53R/sinyal) — pakai lot kecil.") if on else ""
    return {"on": on, "oil10": round(100 * ch, 1), "wti": round(last, 2) if src == "FRED" else None,
            "date": d.isoformat(), "src": src, "text": text}


def uso_rows(api_key: str, store, now: datetime) -> list[tuple[date, float]]:
    """Close harian USO (Twelve Data) yang sudah final, cache di baris Supabase 'perang'."""
    cache = store.get_state("perang") or {}
    fetched = cache.get("t")
    if not fetched or now - datetime.fromisoformat(fetched) >= USO_REFRESH:
        q = urllib.parse.urlencode({"symbol": "USO", "interval": "1day", "outputsize": 15, "order": "ASC",
                                    "apikey": api_key})
        with urllib.request.urlopen("https://api.twelvedata.com/time_series?" + q, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        if data.get("status") != "ok":
            raise RuntimeError(f"Twelve Data USO: {data.get('message')}")
        cache = {"t": now.isoformat(), "rows": [[v["datetime"][:10], float(v["close"])] for v in data["values"]]}
        store.save_state(cache, "perang")
    rows = [(date.fromisoformat(d), v) for d, v in cache.get("rows", [])]
    return [r for r in rows if datetime.combine(r[0], USO_CLOSE, timezone.utc) <= now]   # hari ini belum final


def current(now: datetime, backup=None) -> dict | None:
    """Status dari FRED; bila FRED gagal/basi dan backup (fungsi -> rows USO) ada, pakai USO."""
    try:
        rows = fred_rows()
        if rows and (now.date() - rows[-1][0]).days <= STALE_DAYS:
            st = status(rows)
            if st is not None:
                return st
        err = f"FRED basi/kurang (terakhir {rows[-1][0] if rows else '-'})"
    except Exception as exc:  # noqa: BLE001
        err = f"FRED: {exc}"
    if backup is None:
        raise RuntimeError(err)
    st = status(backup(), src="USO")
    if st is not None:
        st["fred_error"] = err
    return st
