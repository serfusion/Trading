"""🧪 Simulasi menyeluruh GET /api/chat (kode cloud ASLI) Okt–Nov 2026 — 15 Okt 2026, permintaan pengguna "periksa dengan seksama,
tidak ada bug lagi". Jaringan mati (urlopen → galat) kecuali tiruan: kalender ForexFactory pekan berjalan, Act resmi 3 menit
setelah rilis, minyak WTI, candle emas. Store Supabase tiruan dipakai terus (rantai hasil). Di setiap langkah dicek: tidak ada
galat tersembunyi (chat.py menelan galat per bagian), satu arah per waktu rilis (sebelum & sesudah Act), arah tidak pernah
< 50%, jam WIB benar, memori hasil terisi setelah Act. Termasuk pergantian jam musim dingin AS (1 Nov)."""
import datetime as _dt
import json
import math
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cloud" / "api"))

UTC = timezone.utc


def et(d, hm):
    y, m, dd = map(int, d.split("-"))
    h, mi = map(int, hm.split(":"))
    tz = timezone(timedelta(hours=-4 if _dt.date(y, m, dd) < _dt.date(2026, 11, 1) else -5))
    return _dt.datetime(y, m, dd, h, mi, tzinfo=tz)


EV = [("2026-10-14", "08:30", "CPI m/m", "0.6%", "0.4%", "0.6%"), ("2026-10-14", "08:30", "Core CPI m/m", "0.2%", "0.3%", "0.3%"),
      ("2026-10-14", "08:30", "CPI y/y", "3.6%", "3.4%", "3.7%"), ("2026-10-15", "08:30", "PPI m/m", "0.6%", "0.4%", "1.3%"),
      ("2026-10-15", "08:30", "Core PPI m/m", "0.3%", "0.2%", "0.7%"),
      ("2026-10-15", "08:30", "Retail Sales m/m", "0.3%", "1.2%", "0.8%"),
      ("2026-10-15", "08:30", "Unemployment Claims", "199K", "197K", "199K"),
      ("2026-10-27", "10:00", "CB Consumer Confidence", "95.0", "94.2", "93.1"),
      ("2026-10-28", "14:00", "Federal Funds Rate", "4.25%", "4.00%", "4.25%"),
      ("2026-10-29", "08:30", "Advance GDP q/q", "2.8%", "3.1%", "3.2%"),
      ("2026-10-29", "08:30", "Core PCE Price Index m/m", "0.3%", "0.3%", "0.4%"),
      ("2026-11-02", "10:00", "ISM Manufacturing PMI", "51.0", "50.5", "49.8"),
      ("2026-11-03", "10:00", "JOLTS Job Openings", "7.10M", "7.23M", "7.40M"),
      ("2026-11-04", "08:15", "ADP Non-Farm Employment Change", "60K", "45K", "80K"),
      ("2026-11-04", "10:00", "ISM Services PMI", "54.5", "54.9", "55.6"),
      ("2026-11-06", "08:30", "Non-Farm Employment Change", "70K", "29K", "95K"),
      ("2026-11-06", "08:30", "Unemployment Rate", "4.5%", "4.5%", "4.6%"),
      ("2026-11-06", "08:30", "Average Hourly Earnings m/m", "0.3%", "0.3%", "0.1%"),
      ("2026-11-10", "08:30", "CPI m/m", "0.4%", "0.6%", "0.3%"), ("2026-11-10", "08:30", "Core CPI m/m", "0.3%", "0.3%", "0.4%"),
      ("2026-11-10", "08:30", "CPI y/y", "3.6%", "3.7%", "3.5%"), ("2026-11-13", "08:30", "PPI m/m", "0.4%", "1.3%", "0.2%"),
      ("2026-11-13", "08:30", "Core PPI m/m", "0.3%", "0.7%", "0.2%")]
EVENTS = [{"t": et(d, hm), "title": ti, "forecast": f, "previous": p, "actual": a} for d, hm, ti, f, p, a in EV]


class FakeDT(_dt.datetime):
    _now = None

    @classmethod
    def now(cls, tz=None):
        return cls._now if tz is not None else cls._now.replace(tzinfo=None)


class Toko(dict):
    def get_state(self, r="main"):
        return json.loads(json.dumps(self.get(r, {})))

    def save_state(self, d, r="main"):
        self[r] = json.loads(json.dumps(d, default=str))


def week_rows(now):
    n_et = now.astimezone(timezone(timedelta(hours=-5 if now >= _dt.datetime(2026, 11, 1, 6, tzinfo=UTC) else -4)))
    start = (n_et - timedelta(days=(n_et.weekday() + 1) % 7)).replace(hour=0, minute=0, second=0, microsecond=0)
    # klaim pengangguran = dampak SEDANG (seperti FF pekan 12 Okt): kartu 🎯 tetap harus mendapat Act (dulu "menunggu Act…")
    return [{"title": e["title"], "country": "USD", "date": e["t"].isoformat(),
             "impact": "Medium" if e["title"] == "Unemployment Claims" else "High",
             "forecast": e["forecast"], "previous": e["previous"]} for e in EVENTS if start <= e["t"] < start + timedelta(days=7)]


def act_for(title, t):
    for e in EVENTS:
        if e["title"] == title and abs((e["t"] - t).total_seconds()) < 60 and FakeDT._now >= e["t"] + timedelta(minutes=3):
            return e["actual"]
    return ""


@pytest.fixture
def sim(monkeypatch):
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "PRARILIS", "PRA_TREN", "FADE_WARNING"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("TWELVEDATA_API_KEY", "sim")
    monkeypatch.setenv("FRED_API_KEY", "sim")

    def no_net(req, *a, **k):
        raise urllib.error.URLError("offline (simulasi)")
    monkeypatch.setattr(urllib.request, "urlopen", no_net)
    import _aktual
    import _arsip
    import _chat
    import _core
    import _cpi_detik
    import _hari_h
    import _jadwal
    import _kalshi
    import _keterkaitan
    import _persiapan
    import _pernyataan
    import _petunjuk
    import _polymarket
    import _ppi_wti
    import _pra_aset
    import _prarilis
    import _prediksi
    import _pudar
    import _rekam
    import _sentimen
    import _tren
    import chat

    def candles(self, n, interval="1h"):
        step = {"1h": 60, "15min": 15, "5min": 5, "1day": 1440}.get(interval, 60)
        t = FakeDT._now.replace(second=0, microsecond=0)
        t -= timedelta(minutes=(t.minute % step) if step < 60 else t.minute)
        out = []
        while len(out) < n:
            if t.weekday() < 5:
                b = 4100 + 30 * math.sin(t.timestamp() / 259200)
                out.append(_core.Bar(t, b, b + 3, b - 3, b + 0.5))
            t -= timedelta(minutes=step)
        return sorted(out, key=lambda b: b.t)

    def wti(now):
        d, out = (now - timedelta(days=100)).date(), []
        while d <= now.date():
            if d.weekday() < 5:
                out.append((d, 70 + 8 * math.sin(d.toordinal() / 9.0)))
            d += timedelta(days=1)
        return out
    toko = Toko()
    monkeypatch.setattr(_core.TwelveData, "candles", candles)
    monkeypatch.setattr(chat, "datetime", FakeDT)
    monkeypatch.setattr(chat, "_store", lambda: toko)
    monkeypatch.setattr(_chat, "fred_actual", lambda title, t, now, fetch=None, cache=None:
                        act_for(title, t) if title in _chat.FRED_MAP and now >= t else "")
    monkeypatch.setattr(_aktual, "nasdaq_act", lambda title, t, opener=None: act_for(title, t) or None)
    monkeypatch.setattr(_chat, "fetch_calendar", lambda: week_rows(FakeDT._now))
    monkeypatch.setattr(_arsip, "save", lambda *a, **k: {"status": "sim"})
    monkeypatch.setattr(_tren, "compute", lambda key, now, **k: {})
    monkeypatch.setattr(_pernyataan, "attach", lambda *a, **k: None)
    monkeypatch.setattr(_cpi_detik, "nasdaq", lambda t0, opener=None: {})
    monkeypatch.setattr(_kalshi, "fetch", lambda series, opener=None: [])
    monkeypatch.setattr(_polymarket, "search", lambda title, opener=None: [])
    monkeypatch.setattr(_ppi_wti, "minyak", lambda store, now, opener=None, env=None: (wti(now), "FRED"))
    monkeypatch.setattr(_petunjuk, "sumber", lambda store, now, env: {"t": now.timestamp(), "DCOILWTICO":
                                                                       [[d.isoformat(), v] for d, v in wti(now)]})
    monkeypatch.setattr(_petunjuk, "gdpnow", lambda env: 3.4)
    monkeypatch.setattr(_sentimen, "ambil", lambda store, now, opener=None, sumber=None:
                        {"kitco": {"ms_up": 45, "ms_down": 37, "ms_n": 200}, "fxssi": {"buy": 60}, "cot": {"long": 76}})
    monkeypatch.setattr(_pudar, "fetch_twelvedata", lambda key, symbol="XAU/USD": (lambda: (
        [[b.t.isoformat(), b.o, b.h, b.l, b.c] for b in candles(None, 90, "5min")], 25.0)))
    galat = []

    def bungkus(mod, nm):
        asli = getattr(mod, nm)

        def f(*a, **k):
            try:
                return asli(*a, **k)
            except Exception as exc:  # noqa: BLE001
                galat.append(f"{FakeDT._now:%m-%d %H:%M} {mod.__name__}.{nm}: {type(exc).__name__}: {exc}")
                raise
        monkeypatch.setattr(mod, nm, f)
    for mod, nm in [(_persiapan, "cards"), (_persiapan, "satukan"), (_kalshi, "attach"), (_kalshi, "mendatang"),
                    (_hari_h, "attach"), (_jadwal, "attach"), (_prarilis, "attach"), (_petunjuk, "attach"),
                    (_prediksi, "attach"), (_cpi_detik, "attach"), (_ppi_wti, "attach"), (_sentimen, "attach"),
                    (_pra_aset, "attach"), (_pra_aset, "daftar"), (_pra_aset, "satu"), (_pra_aset, "tandai"),
                    (_pudar, "attach"), (_aktual, "fill"), (_keterkaitan, "attach")]:
        bungkus(mod, nm)

    def get(now):
        FakeDT._now = now
        out = {}
        h = chat.handler.__new__(chat.handler)
        h.path, h._authorized = "/api/chat", (lambda: True)
        h._send = lambda c, b: out.update(b, _code=c)
        h.do_GET()
        return out

    def rekam(now):
        FakeDT._now = now
        return _rekam.jalankan(toko, now, {}, lambda: _arsip.calendar_cached(toko, now, _chat.fetch_calendar))
    return get, rekam, toko, galat


def arah_teks(t):
    t = t or ""
    return "naik" if ("NAIK" in t or " naik" in t) else "turun" if ("TURUN" in t or " turun" in t) else None


def test_simulasi_okt_nov_tanpa_galat_dan_satu_arah(sim):
    get, rekam, toko, galat = sim
    pts = set()
    for e in EVENTS:
        t = e["t"].astimezone(UTC)
        for d in (-timedelta(hours=6), -timedelta(minutes=1), timedelta(minutes=5), timedelta(hours=2)):
            pts.add(t + d)
    masalah = []
    for now in sorted(x for x in pts if x >= _dt.datetime(2026, 10, 15, 6, tzinfo=UTC)):
        rekam(now)
        out = get(now)
        assert out["_code"] == 200 and out["ok"], out
        p = out["persiapan"]
        kartu = [c for k in ("berita", "mendatang") for c in p.get(k) or []]
        per = defaultdict(set)
        for c in kartu:
            w = _dt.datetime.fromisoformat(c["time"]) + timedelta(hours=7)
            if f"{w:%H:%M} WIB" not in c.get("when", ""):
                masalah.append(f"{now} jam WIB {c['title']} {c.get('when')}")
            ad = c.get("arah_detik")
            if ad and not c.get("released"):
                per[c["time"]].add(ad.get("arah"))
                if ad.get("arah") and (ad.get("persen") or 0) < 50:
                    masalah.append(f"{now} arah_detik < 50% {ad}")
        masalah += [f"{now} arah ganda {t}: {s}" for t, s in per.items() if len(s) > 1]
        ps = p.get("pra_satu") or {}
        if ps.get("time") in per and per[ps["time"]] != {ps.get("arah")}:
            masalah.append(f"{now} pra_satu {ps.get('teks')} ≠ kartu {per[ps['time']]}")
        if ps.get("arah") and (ps.get("persen") or 0) < 50:
            masalah.append(f"{now} pra_satu < 50%: {ps.get('teks')}")
        for r in p.get("pra_daftar") or []:
            if r.get("arah") and r["time"] in per and per[r["time"]] != {r["arah"]}:
                masalah.append(f"{now} daftar {r.get('teks')} ≠ kartu {per[r['time']]}")
        for c in p.get("berita") or []:                      # Act resmi tersedia → kartu tidak boleh "menunggu Act…"
            t = _dt.datetime.fromisoformat(c["time"])
            if c.get("released") and now - t > timedelta(minutes=4) and act_for(c["title"], t) and not c.get("actual"):
                masalah.append(f"{now} Act kosong di kartu {c['title']} {c['time']}")
        for kunci, rows in (("arah", out["calendar"]), ("hasil_rilis", p.get("berita") or [])):
            sesudah = defaultdict(set)
            for c in rows:
                a = arah_teks((c.get(kunci) or {}).get("teks"))
                if a:
                    sesudah[c["time"]].add(a)
            masalah += [f"{now} {kunci} bertentangan {t}: {s}" for t, s in sesudah.items() if len(s) > 1]
    assert not galat, galat[:5]
    assert not masalah, masalah[:8]
    # rantai hasil: memori terisi tanpa aplikasi dibuka (rekam tiap jam) — NFP 6 Nov, CPI & PPI 10/13 Nov, Retail 15 Okt
    assert toko["prarilis"]["mem"]["Non-Farm Employment Change"]["time"] == "2026-11-06T13:30:00+00:00"
    assert toko["petunjuk"]["mem"]["CPI m/m"]["time"] == "2026-11-10T13:30:00+00:00"
    assert toko["ppi_cpi"]["time"] == "2026-11-10T13:30:00+00:00" and toko["ppi_cpi"]["s"] == 1
    hr = toko["hasil_rilis"]["mem"]
    assert hr["Retail Sales m/m"]["s"] == 1 and hr["PPI m/m"]["time"] == "2026-11-13T13:30:00+00:00"
    assert hr["Core PPI m/m"]["act"] == "0.2%"
