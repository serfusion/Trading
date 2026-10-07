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
    changed = False
    for c in calendar or []:                                 # ingat kejutan rilis terakhir
        t = c.get("title")
        a, f = num(c.get("actual")), num(c.get("forecast"))
        if t in TITLES and a is not None and f is not None:
            when = c.get("time") or c.get("date") or ""
            if mem.get(t, {}).get("time") != when:
                mem[t] = {"s": (a > f) - (a < f), "time": when}
                changed = True
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
            feats = {"prev_s": mem.get(c["title"], {}).get("s"),
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
