"""🎯 Perkiraan hari H (sebelum rilis) & ✅ hasil (setelah Act keluar) per berita di kartu 🎯.

Permintaan pengguna 1 Okt 2026: "persiapan berita tidak berubah apapun? Bagaimana saya tau hasil pastinya untuk hari H
news ini akan kemana?"
- SEBELUM rilis: peluang emas NAIK 1 menit setelah rilis = P(di bawah) x naik|bawah + P(sama) x naik|sama + P(di atas)
  x naik|atas. P(...) = rata-rata pasar prediksi yang tersedia (Kalshi & Polymarket, diperbarui tiap 15 menit);
  naik|hasil = reaksi emas 1 menit per judul (cloud/api/reaksi.json, research/reaksi_menit.py). Riwayat angka disimpan
  (Supabase baris "hari_h") sehingga terlihat perubahannya. Bukti uji per judul: cloud/api/hari_h.json
  (research/hari_h_uji.py). Warna hijau/merah hanya bila >= 60% / <= 40% DAN uji judul itu mendukung.
- SETELAH rilis: Act otomatis (_aktual.py) dibanding konsensus -> arah emas 1 menit dari data historis
  (_persiapan.kesimpulan). Inilah "hasil pasti" yang bisa diketahui: arah baru jelas setelah angka keluar.
INFORMASI saja: tidak membuka order. Hanya library standar Python.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import _persiapan

_DIR = Path(__file__).resolve().parent
REAKSI = (json.loads((_DIR / "reaksi.json").read_text(encoding="utf-8")).get("judul") or {}) \
    if (_DIR / "reaksi.json").exists() else {}
VALID = (json.loads((_DIR / "hari_h.json").read_text(encoding="utf-8")).get("validasi") or {}) \
    if (_DIR / "hari_h.json").exists() else {}
WIB = timedelta(hours=7)
TH = 0.10
STEP = timedelta(minutes=14)            # riwayat: satu titik per pembaruan pasar (±15 menit)
KEEP = 200


def p_naik(parts: list[dict], title: str) -> tuple[float | None, dict | None]:
    """(peluang naik 1 menit, rata-rata P(atas/sama/bawah)) dari beberapa sumber."""
    r = REAKSI.get(title)
    parts = [p for p in parts if p and p.get("atas") is not None]
    if not r or not parts:
        return None, None
    avg = {k: sum(p.get(k, 0.0) for p in parts) / len(parts) for k in ("atas", "bawah")}
    avg["sama"] = max(0.0, 1 - avg["atas"] - avg["bawah"])
    num = sum(avg[k] * r[k]["naik60"] for k in avg if k in r)
    den = sum(avg[k] for k in avg if k in r)
    return (num / den if den > 0 else None), avg


def _pct(x: float) -> int:
    return int(round(x * 100))


def _valid(title: str, sources: list[str]) -> dict:
    """Hasil uji untuk kombinasi sumber yang benar-benar dipakai (gabungan bila keduanya ada)."""
    v = VALID.get(title) or {}
    for name in (["gabungan"] if len(sources) > 1 else []) + sources:
        if (v.get(name) or {}).get("n", 0) >= 1:
            return {**v[name], "sumber": name}
    return {}


def _history(state: dict, key: str, now: datetime, p: float) -> list:
    h = list(state.get(key) or [])
    if not h or now - datetime.fromisoformat(h[-1][0]) >= STEP:
        h.append([now.isoformat(), round(p, 3)])
    return h[-KEEP:]


def _ago(h: list, now: datetime) -> str:
    """"24 jam lalu 51%" / "6 jam lalu ..." dari titik riwayat tertua yang masih dalam 24 jam."""
    if len(h) < 2:
        return ""
    for hours in (24, 12, 6, 3, 1):
        ts = now - timedelta(hours=hours)
        old = [x for x in h if datetime.fromisoformat(x[0]) <= ts + timedelta(minutes=20)]
        if old:
            return f"{hours} jam lalu {_pct(old[-1][1])}%"
    first = h[0]
    mins = int((now - datetime.fromisoformat(first[0])).total_seconds() // 60)
    return f"{mins} menit lalu {_pct(first[1])}%" if mins >= 15 else ""


def forecast(card: dict, kalshi: dict, poly: dict, state: dict, now: datetime) -> dict | None:
    key = f"{card['title']}|{card['time']}"
    src = {"Kalshi": kalshi.get(key), "Polymarket": poly.get(key)}
    src = {k: v for k, v in src.items() if v and v.get("atas") is not None}
    p, avg = p_naik(list(src.values()), card["title"])
    if p is None:
        return None
    state[key] = _history(state, key, now, p)
    v = _valid(card["title"], list(src))
    teruji = v.get("benar") is not None and v.get("benar", 0) >= 60 and v.get("n", 0) >= 15
    up = p >= 0.5
    pct = _pct(p if up else 1 - p)
    if abs(p - 0.5) >= TH and teruji:
        teks, kuat = (f"{pct}% NAIK 🟢" if up else f"{pct}% TURUN 🔴"), True
    else:
        teks, kuat = f"{pct}% {'naik' if up else 'turun'} ⚪", False
    pasar = " • ".join(f"{k}: di atas {_pct(x['atas'])}% / di bawah {_pct(x['bawah'])}%" for k, x in src.items())
    if v.get("benar") is not None:
        catatan = "" if teruji else (" → sampel kecil, belum terbukti" if v["benar"] >= 60
                                     else " → tidak lebih baik dari lempar koin")
        uji = f"teruji {v['tahun']} ({v['sumber']}): sinyal ≥ 60% benar {v['benar']:.0f}% ({v['n']} rilis){catatan}"
    else:
        uji = "belum ada uji untuk berita ini → anggap ≈ lempar koin"
    ago = _ago(state[key], now)
    w = now + WIB
    bukti = " • ".join(x for x in (pasar, uji, f"diperbarui {w:%H:%M} WIB" + (f" • {ago}" if ago else "")) if x)
    return {"label": "🎯 Perkiraan hari H • emas 1 menit setelah rilis", "teks": teks, "kuat": kuat,
            "bukti": bukti, "p_naik": round(p, 3),
            "riwayat": [x[1] for x in state[key][-24:]], "pasar": avg}


def result(card: dict, actual: str) -> dict:
    k = _persiapan.kesimpulan(card["title"], actual, card.get("forecast") or "")
    if not k:
        return {"label": "✅ Hasil rilis", "teks": f"Act {actual}", "kuat": False,
                "bukti": f"Perkiraan {card.get('forecast') or '-'} • arah emas: data historis tidak cukup"}
    return {"label": "✅ Hasil rilis • emas 1 menit", "teks": k["teks"], "kuat": k["kuat"],
            "bukti": f"Act {actual} vs perkiraan {card.get('forecast') or '-'} • {k['catatan']}"}


def fed_line(fed: dict | None, now: datetime) -> dict | None:
    if not fed or not fed.get("pilihan"):
        return None
    nama = {"No change": "TETAP", "25 bps increase": "NAIK 25 bps", "25 bps decrease": "TURUN 25 bps",
            "50+ bps increase": "NAIK ≥ 50 bps", "50+ bps decrease": "TURUN ≥ 50 bps"}
    (top, p), rest = next(iter(fed["pilihan"].items())), list(fed["pilihan"].items())[1:]
    akhir = datetime.fromisoformat(fed["akhir"]) - timedelta(hours=4)        # tanggal New York
    hist = fed.get("riwayat") or []
    old = [x for x in hist if datetime.fromisoformat(x[0]) <= now - timedelta(hours=23) and x[1] == top]
    bukti = " • ".join(f"{nama.get(k, k).lower()} {_pct(v)}%" for k, v in rest if v >= 0.01)
    bukti = f"Polymarket (volume ${fed.get('volume', 0) / 1e6:.1f} jt): " + bukti
    if old:
        bukti += f" • 24 jam lalu {nama.get(top, top).lower()} {_pct(old[-1][2])}%"
    bukti += " • arah emas sesudah keputusan Fed tidak konsisten di data kita (info saja)"
    return {"label": f"🏦 Keputusan Fed {akhir.day} {_persiapan.BULAN[akhir.month - 1]}",
            "teks": f"{_pct(p)}% {nama.get(top, top)}", "kuat": False, "bukti": bukti}


def attach(persiapan: dict, calendar: list[dict], store, now: datetime, kalshi: dict, poly: dict,
           fed: dict | None = None) -> None:
    """Tambahkan berita[].hari_h (sebelum rilis) atau berita[].hasil_rilis (setelah Act), dan persiapan.fed."""
    acts = {f"{c['title']}|{c['time']}": c.get("actual") for c in calendar or [] if c.get("actual")}
    state = {}
    if store is not None:
        try:
            state = store.get_state("hari_h") or {}
        except Exception:  # noqa: BLE001
            state = {}
    keys = set()
    for card in persiapan.get("berita") or []:
        key = f"{card['title']}|{card['time']}"
        keys.add(key)
        if acts.get(key):
            card["hasil_rilis"] = result(card, acts[key])
        elif card.get("released"):
            card["hasil_rilis"] = {"label": "✅ Hasil rilis", "teks": "menunggu Act…", "kuat": False,
                             "bukti": "angka resmi diambil otomatis (BLS/FRED) beberapa menit setelah rilis"}
        else:
            f = forecast(card, kalshi or {}, poly or {}, state, now)
            if f:
                card["hari_h"] = f
    line = fed_line(fed, now)
    if line:
        persiapan["fed"] = line
    state = {k: v for k, v in state.items() if k in keys}
    if store is not None:
        try:
            store.save_state(state, "hari_h")
        except Exception:  # noqa: BLE001
            pass
