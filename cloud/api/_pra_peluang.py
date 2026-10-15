"""🎯 Persentase SEBELUM rilis untuk berita tanpa arah teruji, termasuk FOMC (16 Okt 2026).

Pengguna: "saya mau sebelum rilis pun kamu sudah predict persentase naik/turun dan berubah up to date sekaligus mengecek data
informasi tambahan di internet dan tambahkan persentasenya". research/pra_peluang.py (tick Exness 1.627 rilis 2016–2026, gaya
pengguna masuk t0−1 dtk → detik 60) menguji 8 data yang bisa dibaca live sebelum rilis (tren emas 1/4/24 jam, EMA 50/200,
petunjuk berita, yield 2 tahun FRED, dolar FRED) dengan model walk-forward per kelompok berita: TIDAK lebih baik dari angka
dasar (FOMC benar 52%, Brier lebih buruk). Maka baris di bawah XAU menampilkan peluang dasar yang jujur (mis. "Fed naik 49% •
turun 51%") + poin 🌐 data live yang dicek saat GET ini (Polymarket keputusan Fed, pernyataan Fed terbaru, tren emas 4 jam) dan
pengaruhnya yang sudah diuji. Angka tidak dibesar-besarkan. Env PRA_PELUANG=0 mematikan. Info saja, tanpa order.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import _masuk_pra

_F = Path(__file__).with_name("pra_peluang.json")
DATA = json.loads(_F.read_text(encoding="utf-8")) if _F.exists() else {}
WIB = timedelta(hours=7)


def aktif() -> bool:
    return os.environ.get("PRA_PELUANG", "1") != "0" and bool(DATA.get("grup"))


def _f(v) -> str:
    return f"{v:.0f}"


def info_live(persiapan: dict, grup: str) -> list[str]:
    """Data internet/live yang dibaca GET ini, singkat (sudah diuji: tidak menggeser peluang secara konsisten)."""
    out = []
    fed = persiapan.get("fed") if isinstance(persiapan.get("fed"), dict) else None
    if grup == "FOMC" and fed and fed.get("teks"):
        out.append(f"Polymarket {fed['teks']}")
    tr = (persiapan.get("pra") or {}).get("tren") if isinstance(persiapan.get("pra"), dict) else None
    if isinstance(tr, dict) and tr.get("teks"):
        out.append(str(tr["teks"]).replace("➕ ", "")[:90])
    pn = ((persiapan.get("pernyataan") or {}).get("penting") or []) if isinstance(persiapan.get("pernyataan"), dict) else []
    if pn and isinstance(pn[0], dict) and pn[0].get("judul"):
        out.append("berita terbaru: " + str(pn[0]["judul"])[:80])
    return out


def attach(persiapan: dict, now: datetime | None = None) -> None:
    if not isinstance(persiapan, dict) or not aktif():
        return
    ps = persiapan.get("pra_satu")
    if not isinstance(ps, dict) or ps.get("arah") in ("naik", "turun") or not ps.get("time"):
        return
    now = now or datetime.now(timezone.utc)
    g = _masuk_pra.grup(ps.get("title") or "")
    x = (DATA["grup"].get(g) or {}) if g != "SEMUA" else {}
    lingkup = g
    if not x:
        x, lingkup = DATA["grup"].get("SEMUA") or {}, "semua berita"
    if not x:
        return
    naik = float(x["dasar_naik"])
    turun = 100.0 - naik
    nama = ps.get("nama") or g
    sisa = ps.get("sisa") or str(ps.get("teks") or "").rsplit(" • ", 1)[-1]
    ps["peluang"] = {"naik": round(naik, 1), "turun": round(turun, 1), "grup": lingkup, "n": x.get("n"),
                     "lama": x.get("dasar_lama"), "baru": x.get("dasar_baru"), "dihitung": now.isoformat()}
    ps["teks"] = f"{nama} ⚪ naik {_f(naik)}% • turun {_f(turun)}% (masuk t−1 → 1 mnt) • {sisa}"
    u = ((x.get("uji") or {}).get("up60") or {})
    jam = (now + WIB).strftime("%H:%M")
    poin = [f"🎯 Sebelum rilis ({lingkup}, {x.get('n')} rilis 2016–2026, masuk t−1 → detik 60): emas naik {_f(naik)}% / turun "
            f"{_f(turun)}% • sebelum Okt 2021 naik {_f(x.get('dasar_lama', naik))}% • sejak {_f(x.get('dasar_baru', naik))}%"]
    if u:
        poin.append(f"🧮 Model 8 data live (tren emas 1/4/24 jam, EMA 50/200, petunjuk, yield 2 th, dolar): benar {u['benar']:.0f}% "
                    f"walk-forward → {'tidak lebih baik dari angka dasar' if u.get('brier', 1) >= u.get('brier_dasar', 0) else 'sedikit lebih baik'}"
                    ", jadi persen tidak digeser")
    live = info_live(persiapan, g)
    if live:
        poin.append(f"🌐 Dicek {jam} WIB: " + " • ".join(live) + " (sudah diuji: tidak menggeser peluang)")
    lama = [p for p in (ps.get("poin") or []) if not str(p).startswith(("⚪ Belum ada petunjuk", "⚪ Arah belum dihitung"))]
    ps["poin"] = poin + lama
    ps["bukti"] = "\n".join("• " + p for p in ps["poin"])
