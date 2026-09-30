"""Mode perang Timur Tengah = guncangan minyak: WTI (FRED DCOILWTICO, CSV publik tanpa kunci) naik >= 10% dalam
10 hari bursa. Hanya LABEL ⚠️ di sinyal XAU & heartbeat (keputusan pengguna 30 Sep 2026: XAU tidak dijeda).

Riset (docs/MOMEN_PERANG.md, research/mode_perang.py): sinyal 💰 XAU di mode ini rata-rata −0,06R (2012–2021) dan
−0,53R (5 tahun terakhir) vs normal +0,23/+0,27R. Studi kejadian research/perang_peluang.py: TIDAK ada setup minyak /
pair terkait yang konsisten (emas tidak turun secara konsisten, minyak tidak lanjut naik secara konsisten).
"""
from __future__ import annotations

import urllib.request
from datetime import date, datetime, timedelta, timezone

THR = 0.10
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}"
HEADERS = {"User-Agent": "xau-signal/1.0 (python urllib)", "Accept": "text/csv,*/*"}   # UA peramban ditahan FRED


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


def status(rows: list[tuple[date, float]] | None = None) -> dict | None:
    """{'on', 'oil10' (% 10 hari bursa), 'wti', 'date', 'text'} atau None bila data kurang."""
    rows = fred_rows() if rows is None else rows
    if len(rows) < 11 or rows[-11][1] <= 0:
        return None
    (d, last), prev = rows[-1], rows[-11][1]
    ch = last / prev - 1
    on = ch >= THR
    text = (f"⚠️ Mode perang: minyak WTI {ch:+.1%} dalam 10 hari (${last:.2f}). Sinyal emas di kondisi ini "
            f"historis lemah (5 th: −0,53R/sinyal) — pakai lot kecil.") if on else ""
    return {"on": on, "oil10": round(100 * ch, 1), "wti": round(last, 2), "date": d.isoformat(), "text": text}
