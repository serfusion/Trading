"""📊 Peluang emas naik 1 jam SEBELUM rilis NFP, JOLTS, Fed (research/prarilis.py → prarilis.json; izin pengguna 6 Okt
2026). Regresi logistik dengan fitur yang diketahui sebelum rilis: rilis lalu di atas/bawah konsensus (diingat di baris
Supabase 'prarilis'), konsensus vs angka lalu, gerak emas 4 & 24 jam, emas vs EMA ±20 hari (Twelve Data H1, cache 30
menit). Uji walk-forward 2015–2025: NFP 62%, JOLTS 65%, Fed 60% tebakan benar — info saja, bukan kepastian.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import _core

_PATH = Path(__file__).resolve().parent / "prarilis.json"
CFG = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
TITLES = {m["judul"]: k for k, m in (CFG.get("model") or {}).items()}
SEED = {"Non-Farm Employment Change": {"s": -1, "time": "2026-10-02T12:30:00+00:00"}}   # 29K vs 89K
CACHE = timedelta(minutes=30)
# 15 Okt 2026 (audit setelah bug PPI ← CPI): "rilis lalu" hanya dipakai bila memori = rilis TEPAT sebelumnya. Memori yang
# terlewat satu bulan (aplikasi tidak dibuka, Act gagal) dulu tetap dipakai → kejutan 2 bulan lalu dianggap bulan lalu.
SEGAR_HARI = {"Federal Funds Rate": 60}        # FOMC tiap 6–7 pekan; berita bulanan lain ≤ 45 hari
SEGAR_BAWAAN = 45


def segar(m: dict | None, t_kartu, title: str) -> bool:
    """True bila memori kejutan m terbit sebelum kartu dan masih rilis sebelumnya (≤ 45 hari; Fed ≤ 60 hari)."""
    if not m or not m.get("time") or t_kartu is None:
        return False
    try:
        tm = datetime.fromisoformat(str(m["time"]))
        tk = t_kartu if isinstance(t_kartu, datetime) else datetime.fromisoformat(str(t_kartu))
    except (TypeError, ValueError):
        return False
    return timedelta(0) < tk - tm <= timedelta(days=SEGAR_HARI.get(title, SEGAR_BAWAAN))


def ingat(mem: dict, calendar: list, judul) -> bool:
    """Perbarui memori kejutan terakhir per judul dari kalender (Act vs konsensus). True bila berubah."""
    changed = False
    for c in calendar or []:
        t = c.get("title")
        a, f = num(c.get("actual")), num(c.get("forecast"))
        if t in judul and a is not None and f is not None:
            when = c.get("time") or c.get("date") or ""
            lama = mem.get(t) or {}
            if lama.get("time") != when and str(when) > str(lama.get("time") or ""):
                mem[t] = {"s": (a > f) - (a < f), "time": when}
                changed = True
            elif lama.get("time") == when and lama.get("s") != (a > f) - (a < f):     # Act direvisi (isian manual → resmi)
                mem[t] = {"s": (a > f) - (a < f), "time": when}
                changed = True
    return changed


def simpan_mem(calendar: list, store) -> bool:
    """Dipanggil tiap jam oleh tick (cloud/api/_rekam.py) supaya memori tidak bergantung pada aplikasi dibuka."""
    state = store.get_state("prarilis") or {}
    mem = {**SEED, **(state.get("mem") or {})}
    if ingat(mem, calendar, TITLES):
        store.save_state({**state, "mem": mem}, "prarilis")
        return True
    return False


def num(text) -> float | None:
    if text is None:
        return None
    t = str(text).strip().replace(",", "").replace("%", "")
    mult = 1.0
    if t[-1:].upper() in "KMB" and t[:-1]:
        mult = {"K": 1e3, "M": 1e6, "B": 1e9}[t[-1].upper()]
        t = t[:-1]
    try:
        return float(t) * mult
    except ValueError:
        return None


def gold_features(bars: list) -> dict | None:
    bars = [b for b in bars if b.h > b.l and _core.market_open(b.t)]
    if len(bars) < 30:
        return None
    c = [b.c for b in bars]
    k, e = 2 / 481, c[0]
    for v in c:
        e += k * (v - e)
    return {"g4": c[-1] - c[-5], "g24": c[-1] - c[-25], "gema": 1.0 if c[-1] > e else 0.0}


def prob(key: str, feats: dict) -> float:
    m = CFG["model"][key]
    z = m["intercept"]
    for name, mu, sd, w in zip(CFG["fitur"], m["mean"], m["std"], m["coef"]):
        v = feats.get(name)
        x = 0.0 if v is None else (v - mu) / (sd or 1)      # tidak diketahui -> nilai rata-rata (netral)
        z += w * x
    return 1 / (1 + math.exp(-z))


def attach(persiapan: dict, calendar: list, store, now: datetime, fetch_gold) -> None:
    if not CFG or not isinstance(persiapan, dict):
        return
    berita = [c for c in persiapan.get("berita") or [] if c.get("title") in TITLES]
    state = store.get_state("prarilis") or {}
    mem = {**SEED, **(state.get("mem") or {})}
    changed = ingat(mem, calendar, TITLES)                   # ingat kejutan rilis terakhir
    todo = [c for c in berita if not c.get("released")]
    if todo:
        g = state.get("gold")
        if not g or now - _core.parse_iso(g["at"]) > CACHE:
            try:
                gf = gold_features(fetch_gold())
                if gf:
                    g = {"at": _core.iso(now), **gf}
                    state["gold"] = g
                    changed = True
            except Exception:  # noqa: BLE001 - tanpa emas: fitur netral
                pass
        for c in todo:
            key = TITLES[c["title"]]
            prev_actual = num(c.get("previous"))
            fc = num(c.get("forecast"))
            m = mem.get(c["title"])
            feats = {"prev_s": m.get("s") if segar(m, c.get("time"), c["title"]) else None,   # basi → netral
                     "exp_up": None if fc is None or prev_actual is None else float((fc > prev_actual) - (fc < prev_actual)),
                     **({k: g[k] for k in ("g4", "g24", "gema")} if g else {})}
            p = prob(key, feats)
            u = CFG["model"][key]["uji"]
            naik = round(p * 100)
            c["prarilis"] = {
                "naik": naik, "arah": "NAIK" if naik >= 50 else "TURUN", "kuat": abs(naik - 50) >= 10,
                "teks": f"📊 Emas 1 jam setelah {key}: {max(naik, 100 - naik)}% {'NAIK 🟢' if naik >= 50 else 'TURUN 🔴'}",
                "bukti": f"tebakan model teruji benar {u['benar']:.0f}% ({u['n']} rilis 2015–2025) • sejak Okt 2021 "
                         f"{u['baru']:.0f}% • belum pasti, dihitung {now:%H:%M} UTC",
                "dihitung": _core.iso(now), "uji": u}
    if changed:
        state["mem"] = mem
        store.save_state(state, "prarilis")
