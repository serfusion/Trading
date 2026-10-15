"""🔗 Keterkaitan berita (15 Okt 2026, pengguna setelah PPI tertebak TURUN: "semua news tepat predict seperti ini, rangkumkan
dari semua informasi yang ada, buat secara keterkaitan").

Setiap berita yang belum rilis mendapat blok "🔗 Keterkaitan berita sebelumnya": hasil TERAKHIR berita lain yang terbit ≤ 35
hari sebelumnya (Act vs perkiraan, memori baris Supabase 'hasil_rilis', diisi tiap GET & tiap jam oleh _rekam) dan seberapa
sering dulu angka berita ini ikut searah/berbalik serta arah emas menit 1 bila mengikutinya — angka tutup kertas per tahun
dari research/keterkaitan.py (cloud/api/keterkaitan.json["tampil"]; FF 2010–2026 × tick). Contoh: CPI di atas perkiraan →
Retail Sales (nominal, ikut harga) cenderung di atas.

PENTING (jujur): keterkaitan ANGKA 60–70%, tetapi emas hanya mengikuti angka ±80% walau angkanya pasti → peluang emas
≈ 20% + 60% × peluang angka tertebak (angka 65% → emas ±59%). Karena itu blok ini INFO; arah utama tetap aturan teruji
(_pra_aset). Env KETERKAITAN=0 mematikan. Tidak membuka order.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import _persiapan
import _prarilis
import _prediksi

_F = Path(__file__).with_name("keterkaitan.json")
DATA = json.loads(_F.read_text(encoding="utf-8")) if _F.exists() else {}
ROW = "hasil_rilis"
JENDELA = timedelta(days=35)
SIMPAN = timedelta(days=120)
INVERS = ("Unemployment Rate", "Unemployment Claims")      # angka naik = buruk bagi USD
BULAN = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")
RUMUS = ("Catatan: walau angka sudah pasti, emas hanya mengikutinya ±80% di menit 1 → keterkaitan angka 65% ≈ arah emas "
         "±59%. Blok ini info; arah utama tetap aturan teruji.")


def aktif() -> bool:
    return os.environ.get("KETERKAITAN", "1") != "0" and bool(DATA.get("tampil"))


def nama(title: str) -> str:
    n = _persiapan.NAMA_PENDEK.get(title) or _prediksi.nama(title)
    return n[:1].upper() + n[1:]


def ingat(calendar: list, store) -> dict:
    """Memori hasil terakhir per judul {title: {s, act, f, time}} (s = angka vs perkiraan: +1 di atas / −1 di bawah / 0)."""
    state = {}
    if store is not None:
        try:
            state = store.get_state(ROW) or {}
        except Exception:  # noqa: BLE001
            state = {}
    mem, ubah = dict(state.get("mem") or {}), False
    for c in calendar or []:
        t, a, f, w = c.get("title"), c.get("actual"), c.get("forecast"), c.get("time")
        an, fn = _prarilis.num(a), _prarilis.num(f)
        if not t or not w or an is None or fn is None:
            continue
        lama = mem.get(t) or {}
        baru = {"s": (an > fn) - (an < fn), "act": str(a), "f": str(f), "time": str(w)}
        if str(w) > str(lama.get("time") or "") or (lama.get("time") == str(w) and lama != baru):
            mem[t], ubah = baru, True                     # rilis lebih baru / Act direvisi (isian manual → resmi)
    if mem:
        terbaru = max(str(m.get("time") or "") for m in mem.values())
        try:
            batas = datetime.fromisoformat(terbaru) - SIMPAN
            sisa = {k: m for k, m in mem.items() if datetime.fromisoformat(str(m["time"])) >= batas}
        except (TypeError, ValueError):
            sisa = mem
        ubah = ubah or len(sisa) != len(mem)
        mem = sisa
    if ubah and store is not None:
        try:
            store.save_state({**state, "mem": mem}, ROW)
        except Exception:  # noqa: BLE001
            pass
    return mem


def _tgl(t: datetime) -> str:
    w = t + timedelta(hours=7)
    return f"{w.day} {BULAN[w.month - 1]}"


def _kata(s: int) -> str:
    return "DI ATAS" if s > 0 else "DI BAWAH" if s < 0 else "SAMA DENGAN"


def baris(card: dict, mem: dict, nanti: dict | None = None) -> dict | None:
    """Blok keterkaitan untuk satu kartu yang belum rilis (None bila tidak ada berita terkait yang baru terbit). `nanti` =
    {judul: [waktu rilis berikutnya]}: bila berita A masih terbit lagi SEBELUM kartu ini (mis. CPI 10 Nov sebelum PPI 13 Nov),
    hasil A yang lama tidak dipakai — keterkaitan diuji dengan rilis A TERAKHIR sebelum B."""
    links = (DATA.get("tampil") or {}).get(card.get("title") or "") or []
    try:
        t0 = datetime.fromisoformat(card["time"])
    except (KeyError, TypeError, ValueError):
        return None
    out, arah = [], []
    nb = nama(card["title"])
    for x in links:
        m = mem.get(x["A"]) or {}
        try:
            tm = datetime.fromisoformat(str(m.get("time")))
        except (TypeError, ValueError):
            continue
        if not timedelta(0) < t0 - tm <= JENDELA:
            continue
        if any(tm < t < t0 for t in (nanti or {}).get(x["A"], [])):
            continue
        na = nama(x["A"])
        hasil = f"{na} {_tgl(tm)} {_kata(m['s'])} perkiraan ({m['act']} vs {m['f']})"
        if not m["s"]:
            out.append(f"{hasil} → tidak memberi arah")
            continue
        usd_a = m["s"] * (-1 if x["A"] in INVERS else 1)          # +1 = kuat untuk USD
        usd_b = usd_a * (1 if x["hubungan"] == "searah" else -1)
        s_b = usd_b * (-1 if card["title"] in INVERS else 1)
        emas = "TURUN" if usd_b > 0 else "NAIK"
        ew = x.get("emas_wf")
        angka = f"{hasil} → {nb} cenderung {_kata(s_b)} perkiraan (dulu {x['angka_wf']:.0f}% dari {x['n_angka_wf']} rilis)"
        if ew is None or ew < 52 or x.get("status_emas") == "≈ acak":
            # angka berkaitan, tetapi arah emas tidak ikut (mis. PPI → GDP: emas searah hanya 35%) → tanpa arah emas
            out.append((angka + " • arah emas tidak ikut (≈ 50:50)").replace(".", ","))
            continue
        arah.append(emas)
        out.append((angka + f" → emas {emas} {ew:.0f}% ({x['status_emas']})").replace(".", ","))
    if not out:
        return None
    if arah and len(set(arah)) == 1:
        teks = f"{len(out)} berita terkait condong emas {arah[0]} (lemah, info)"
    elif arah:
        teks = "berita terkait saling berlawanan → ≈ 50:50"
    else:
        teks = "berita terkait tidak memberi arah"
    return {"judul": "🔗 Keterkaitan berita sebelumnya", "teks": teks, "baris": out,
            "catatan": "\n".join(out + [RUMUS])}


def attach(persiapan: dict, calendar: list, store, now: datetime | None = None) -> None:
    if not isinstance(persiapan, dict) or not aktif():
        return
    mem = ingat(calendar, store)
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)
             and not c.get("released") and c.get("time")]
    nanti: dict[str, list] = {}
    for c in kartu:
        try:
            nanti.setdefault(c["title"], []).append(datetime.fromisoformat(c["time"]))
        except (TypeError, ValueError):
            pass
    per_waktu: dict[str, dict] = {}
    for c in kartu:
        b = baris(c, mem, nanti)
        if not b:
            continue
        c["keterkaitan"] = b
        p = c.get("prediksi")
        if isinstance(p, dict) and isinstance(p.get("detail"), list) and not any(
                isinstance(d, dict) and str(d.get("judul", "")).startswith("🔗 Keterkaitan") for d in p["detail"]):
            p["detail"].append({"judul": b["judul"], "teks": b["teks"], "catatan": b["catatan"]})
        if not (c.get("arah_detik") or {}).get("ganda") or c["time"] not in per_waktu:
            per_waktu[c["time"]] = b
    ps = persiapan.get("pra_satu")
    b = per_waktu.get((ps or {}).get("time")) if isinstance(ps, dict) else None
    if b and isinstance(ps.get("poin"), list) and not any(str(x).startswith("🔗") for x in ps["poin"]):
        i = next((k for k, x in enumerate(ps["poin"]) if str(x).startswith(("👥", "Setelah rilis"))), len(ps["poin"]))
        ps["poin"].insert(i, "🔗 " + b["baris"][0] + (f" (+{len(b['baris']) - 1} lainnya)" if len(b["baris"]) > 1 else ""))
        ps["bukti"] = "\n".join("• " + x for x in ps["poin"])
        ps["keterkaitan"] = b
