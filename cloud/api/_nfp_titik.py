"""🔄 Titik balik ekonomi NFP (mean reversion + indikator pendahulu) — detail di balik baris "NFP: peluang emas …".

Framework pengguna (NFP Mean Reversion Validation Framework, 6 Okt 2026; docs/NFP_MEAN.md): bukan "NFP buruk → pasti
memantul", melainkan apakah ekonomi mendekati titik balik, diuji terhadap indikator pendahulu. Model logistik dari
research/nfp_titik.py (data vintage ALFRED 2001–2026, walk-forward 61%): fitur = NFP z-score 24 bln, perubahan dari
rilis lalu, revisi bulan lalu, tren klaim pengangguran 4 minggu, pengangguran 3 bulan, skor pendahulu (klaim ±2,
pengangguran ±1, JOLTS ±1). Hasil = peluang NFP berikutnya (angka pertama) LEBIH TINGGI dari NFP terakhir.
Ini info EKONOMI, terpisah dari arah emas (framework bagian 14: emas digerakkan kejutan vs perkiraan).

Data live: FRED API (env FRED_API_KEY; cache baris Supabase 'nfp_titik' 12 jam). Tanpa kunci / gagal → potret
terakhir dari research (nfp_titik.json, diperbarui saat skrip riset dijalankan).
"""
from __future__ import annotations

import json
import math
import statistics
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "nfp_titik.json"
CFG = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
FRED = "https://api.stlouisfed.org/fred/series/observations?"
CACHE = timedelta(hours=12)
BULAN = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


def _d(s: str) -> date:
    return date.fromisoformat(s[:10]) if s < "9999" else date.max


def _madd(d: date, k: int) -> date:
    y, m = divmod(d.month - 1 + k, 12)
    return date(d.year + y, m + 1, 1)


def _get(sid: str, key: str, **q) -> list[dict]:
    q = {"series_id": sid, "api_key": key, "file_type": "json", "limit": 100000, **q}
    with urllib.request.urlopen(FRED + urllib.parse.urlencode(q), timeout=8) as r:
        return [o for o in json.load(r).get("observations") or [] if o.get("value") not in (".", None, "")]


def score(claims: float | None, ur_d3: float | None, jolts3: float | None, adp: int = 0) -> int:
    """Skor pendahulu (research/nfp_mean.score): klaim ±2 (±3%), pengangguran ±1 (±0,1), JOLTS ±1 (±3%), ADP ±1."""
    s = adp
    if claims is not None:
        s += 2 if claims <= -0.03 else -2 if claims >= 0.03 else 0
    if ur_d3 is not None:
        s += 1 if ur_d3 <= -0.1 + 1e-9 else -1 if ur_d3 >= 0.1 - 1e-9 else 0
    if jolts3 is not None:
        s += 1 if jolts3 >= 0.03 else -1 if jolts3 <= -0.03 else 0
    return s


def nfp_fitur(rows: list[dict]) -> dict:
    """Dari vintage PAYEMS (output_type=1): NFP angka pertama per bulan, z24, perubahan, revisi bulan lalu."""
    by: dict[date, list] = {}
    for o in rows:
        by.setdefault(_d(o["date"]), []).append((_d(o["realtime_start"]), _d(o["realtime_end"]), float(o["value"])))
    first = {m: min(rs for rs, _, _ in v) for m, v in by.items()}

    def asof(m: date, when: date) -> float | None:
        for rs, re, v in by.get(m, []):
            if rs <= when < re or (rs <= when and re == date.max):
                return v
        return None
    chg = {}
    for m in sorted(first):
        a, b = asof(m, first[m]), asof(_madd(m, -1), first[m])
        if a is not None and b is not None:
            chg[m] = a - b
    ms = sorted(chg)
    if len(ms) < 27:
        raise ValueError(f"riwayat NFP kurang ({len(ms)} bulan)")
    m, seq = ms[-1], [chg[x] for x in ms]
    prev24 = seq[-25:-1]
    a1, a2 = asof(_madd(m, -1), first[m]), asof(_madd(m, -2), first[m])
    return {"bulan": m.isoformat(), "rilis": first[m].isoformat(), "chg": seq[-1], "prev": seq[-2],
            "z24": (seq[-1] - statistics.mean(prev24)) / statistics.stdev(prev24), "d1": seq[-1] - seq[-2],
            "d1_prev": seq[-2] - seq[-3], "d2": seq[-1] - seq[-3],
            "revision": (a1 - a2) - chg[_madd(m, -1)] if a1 is not None and a2 is not None else 0.0}


def fitur(key: str, now: datetime) -> dict:
    """Fitur untuk NFP BERIKUTNYA dari FRED API (data yang sudah terbit per `now`)."""
    from concurrent.futures import ThreadPoolExecutor
    today = now.date()
    with ThreadPoolExecutor(4) as ex:                       # 4 permintaan paralel (maks ±8 detik total)
        fp = ex.submit(_get, "PAYEMS", key, observation_start=_madd(today, -31).isoformat(),
                       realtime_start=_madd(today, -33).isoformat(), realtime_end="9999-12-31", output_type=1)
        fi = ex.submit(_get, "ICSA", key, observation_start=(today - timedelta(days=90)).isoformat())
        fu = ex.submit(_get, "UNRATE", key, observation_start=_madd(today, -9).isoformat())
        fj = ex.submit(_get, "JTSJOL", key, observation_start=_madd(today, -12).isoformat())
        rows_p, rows_i, rows_u, rows_j = fp.result(), fi.result(), fu.result(), fj.result()
    f = nfp_fitur(rows_p)
    m = date.fromisoformat(f["bulan"])
    ic = sorted((_d(o["date"]), float(o["value"])) for o in rows_i)
    wk = [v for d, v in ic if d + timedelta(days=5) < today]
    claims = (sum(wk[-4:]) / 4) / (sum(wk[-8:-4]) / 4) - 1 if len(wk) >= 8 else None
    ur = {_d(o["date"]): float(o["value"]) for o in rows_u}
    ur_d3 = round(ur[m] - ur[_madd(m, -3)], 3) if m in ur and _madd(m, -3) in ur else None
    jo = [float(o["value"]) for o in sorted(rows_j, key=lambda o: o["date"])]
    jolts3 = jo[-1] / jo[-4] - 1 if len(jo) >= 4 else None
    return {**f, "n_claims": claims, "n_ur_d3": ur_d3, "n_jolts3": jolts3, "lead": score(claims, ur_d3, jolts3),
            "dihitung": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "sumber": "FRED live"}


def peluang(f: dict) -> float:
    md = CFG["model"]
    z = md["intercept"]
    for name, mu, sd, w in zip(md["fitur"], md["mean"], md["std"], md["coef"]):
        v = f.get(name)
        z += w * (0.0 if v is None else (v - mu) / (sd or 1))
    return 1 / (1 + math.exp(-z))


def _bulan(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{BULAN[d.month - 1]} {d.year}"


def _id(s: str) -> str:
    """Angka gaya Indonesia: koma desimal, tanda minus asli."""
    return s.replace(",", "#").replace(".", ",").replace("#", ".").replace("-", "−")


def _arah(v: float | None, naik_baik: bool, fmt: str, batas: float) -> str:
    if v is None:
        return "belum ada data"
    baik = (v < -batas) if not naik_baik else (v > batas)
    buruk = (v > batas) if not naik_baik else (v < -batas)
    return _id(fmt.format(v)) + (" (membaik)" if baik else " (memburuk)" if buruk else " (tetap)")


def ringkas(f: dict) -> dict:
    """Teks detail untuk aplikasi (tanpa simbol < / >)."""
    p = round(peluang(f) * 100)
    u = CFG.get("uji", {})
    g = u.get("kelompok", {})
    lemah = f["z24"] <= -1.0 or (f["d1"] < 0 and f["d1_prev"] < 0) or f["d2"] <= CFG.get("p20", -120)
    lead = int(f["lead"])
    lab = "membaik" if lead >= 2 else "memburuk" if lead <= -2 else "netral"
    if lemah:
        k = g.get(lab, {})
        kondisi = (f"NFP sedang melemah + pendahulu {lab} → historis NFP berikutnya lebih tinggi {k.get('naik', '?')}% "
                   f"(n {k.get('n', '?')})" + (" — risiko deterioration lanjutan" if lab == "memburuk" else
                                               " — mendekati titik balik"))
    else:
        z_txt = _id(f"{f['z24']:+.2f}")
        kondisi = f"Belum pelemahan ekstrem (z-score {z_txt}) • pendahulu {lab} (skor {lead:+d})"
    rev = f.get("revision") or 0.0
    rev_txt, chg_txt = _id(f"{rev:+.0f}"), _id(f"{f['chg']:+.0f}")
    pend = (f"Pendahulu: klaim pengangguran 4 mgg {_arah(f.get('n_claims'), False, '{:+.1%}', 0.03 - 1e-9)} • "
            f"pengangguran 3 bln {_arah(f.get('n_ur_d3'), False, '{:+.1f} poin', 0.1 - 1e-9)} • "
            f"JOLTS {_arah(f.get('n_jolts3'), True, '{:+.1%}', 0.03 - 1e-9)} • revisi bulan lalu {rev_txt}K")
    bukti = (f"Teruji {u.get('periode', '2001–2026')} (data vintage, {u.get('n', '?')} rilis): NFP melemah + pendahulu "
             f"membaik {g.get('membaik', {}).get('naik', '?')}% / netral {g.get('netral', {}).get('naik', '?')}% / "
             f"memburuk {g.get('memburuk', {}).get('naik', '?')}% (dasar {u.get('dasar', '?')}%) • walk-forward "
             f"{u.get('walk_forward', '?')}% • info ekonomi, BUKAN arah emas (emas digerakkan kejutan vs perkiraan) • "
             f"{f.get('sumber', '')} {f.get('dihitung', '')}".strip())
    return {"judul": "🔄 Titik balik ekonomi (mean reversion)",
            "teks": f"Peluang NFP berikutnya lebih tinggi dari {chg_txt}K ({_bulan(f['bulan'])}): {p}%",
            "kondisi": kondisi, "pendahulu": pend, "bukti": bukti, "peluang": p, "lemah": lemah, "lead": lead}


def kondisi(now: datetime, store=None, env: dict | None = None, fetch=None) -> dict | None:
    """Potret terkini: cache Supabase 12 jam → FRED live (bila ada kunci) → potret bawaan nfp_titik.json."""
    if not CFG:
        return None
    env = env or {}
    state = {}
    if store is not None:
        try:
            state = store.get_state("nfp_titik") or {}
            at = datetime.fromisoformat(state["at"]) if state.get("at") else None
            if at and now - at < CACHE and state.get("f"):
                return ringkas(state["f"])
        except Exception:  # noqa: BLE001 - cache opsional
            state = {}
    key = (env.get("FRED_API_KEY") or "").strip()
    if key or fetch:
        try:
            f = (fetch or fitur)(key, now)
            if store is not None:
                try:
                    store.save_state({"at": now.isoformat(), "f": f}, "nfp_titik")
                except Exception:  # noqa: BLE001
                    pass
            return ringkas(f)
        except Exception:  # noqa: BLE001 - FRED gagal → potret cache lama / bawaan
            if state.get("f"):
                return ringkas(state["f"])
    return ringkas(CFG["kondisi"]) if CFG.get("kondisi") else None
