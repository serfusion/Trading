"""🎯 Satu baris prediksi per berita: "NFP: peluang emas naik 1 jam 61% (teruji, belum pasti)".

Permintaan pengguna 7 Okt 2026: tampilkan cukup satu baris per berita — tanpa skenario "Act < … / Act > …". Dipakai
untuk berita pekan ini (persiapan["berita"]) dan berita besar berikutnya (persiapan["mendatang"]). Sumber, berurutan:
  1. model  : peluang model sebelum rilis NFP/JOLTS/Fed (_prarilis, walk-forward 2015–2025 benar 60–65%)
  2. aturan : NFP setelah rilis lalu DI ATAS perkiraan → emas naik 1 jam 72% (s.d. Sep 2021) / 61% (sejak Okt 2021);
              satu-satunya aturan yang konsisten dari ±216 yang diuji (research/news_semua.py)
  3. dasar  : frekuensi historis emas naik 1 jam setelah rilis itu (research/news_prediksi.py, semua tahun)
Angka besar = arah yang lebih sering (naik/turun). Info saja — bukan kepastian, tidak membuka order.
Aplikasi 4.18: baris utama saja ("NFP: peluang emas naik 1 jam 61%"); "detail" = blok show/hide (dasar angka,
🔄 titik balik ekonomi NFP dari _nfp_titik.py, 🏦 keputusan Fed).
"""
from __future__ import annotations

import json
from pathlib import Path

import _persiapan

_MAJU = Path(__file__).resolve().parent / "validasi_maju.json"   # 📈 uji maju otomatis (research/validasi_maju.py)
KANDIDAT_BARU = (8, 10)          # kandidat NFP "pendahulu membaik → emas naik": naik/n sejak Okt 2021 (news_gabung.py)


def maju() -> dict:
    try:
        return json.loads(_MAJU.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def kandidat_lolos(m: dict) -> tuple[bool, int, int]:
    """Kandidat naik ke 🥈 bila bukti sejak Okt 2021 (riset + uji maju) mencapai n ≥ 30 dan ≥ 58% emas naik."""
    k = m.get("kandidat_nfp") or {}
    naik, n = KANDIDAT_BARU[0] + int(k.get("naik", 0)), KANDIDAT_BARU[1] + int(k.get("n", 0))
    return n >= 30 and naik / n >= 0.58, naik, n

NAMA = {"Non-Farm Employment Change": "NFP", "CPI m/m": "CPI", "Core CPI m/m": "Core CPI", "CPI y/y": "CPI tahunan",
        "PPI m/m": "PPI", "Core PPI m/m": "Core PPI", "Unemployment Rate": "Pengangguran",
        "Average Hourly Earnings m/m": "Upah per jam", "ADP Non-Farm Employment Change": "ADP",
        "Unemployment Claims": "Klaim pengangguran", "Retail Sales m/m": "Retail Sales",
        "Core Retail Sales m/m": "Core Retail Sales", "Core PCE Price Index m/m": "Core PCE",
        "ISM Manufacturing PMI": "ISM Manufaktur", "ISM Services PMI": "ISM Jasa", "JOLTS Job Openings": "JOLTS",
        "Advance GDP q/q": "GDP", "Federal Funds Rate": "Fed"}
NFP = "Non-Farm Employment Change"
ATURAN_NFP = (61, "aturan teruji: rilis NFP lalu di atas perkiraan → emas naik 1 jam 72% (s.d. Sep 2021, n 57) • "
                  "sejak Okt 2021 61% (n 33)")
CATATAN = "teruji, belum pasti"


def nama(title: str) -> str:
    return NAMA.get(title) or title.replace(" m/m", "").replace(" q/q", "").replace(" y/y", "")


def baris(title: str, naik: int, bukti: str, sumber: str, jangka: str = "1 jam") -> dict:
    up = naik >= 50
    return {"teks": f"{nama(title)}: peluang emas {'naik' if up else 'turun'} {jangka} {naik if up else 100 - naik}%",
            "catatan": CATATAN, "bukti": bukti, "naik": int(naik), "kuat": abs(naik - 50) >= 10, "sumber": sumber}


# 🎲 peluang PASAR (Kalshi/Polymarket × reaksi emas 1 menit, _hari_h.py) — hanya judul yang lolos uji: tebakan pasar
# CPI & core CPI benar 76–78% (2022–2025, research/kalshi_uji.py); sinyal ≥ 60% benar 13 dari 17 (hari_h_uji.py).
# Permintaan pengguna 10 Okt 2026: angka berita yang akan datang harus selalu terbaru dan ikut berubah bila ada pernyataan
# penting — harga pasar prediksi bereaksi dalam hitungan menit, dibaca ulang tiap 15 menit. NFP TIDAK (Kalshi 33–57%).
PASAR = ("CPI m/m", "Core CPI m/m")
GESER = 0.05                     # perubahan peluang ≥ 5 poin dalam 24 jam → ditandai "pasar bergeser"


def uji_pasar() -> tuple[int, int]:
    """(benar, n) gabungan judul PASAR dari cloud/api/hari_h.json (sinyal ≥ 60%)."""
    try:
        import _hari_h
        v = [(_hari_h.VALID.get(t) or {}).get("Kalshi") or {} for t in PASAR]
    except Exception:  # noqa: BLE001
        return 0, 0
    n = sum(int(x.get("n") or 0) for x in v)
    benar = sum(round((x.get("benar") or 0) * (x.get("n") or 0) / 100) for x in v)
    return benar, n


def pasar(card: dict) -> dict | None:
    """Baris dari peluang pasar sebelum rilis (card["hari_h"]["p_naik"]) untuk CPI/core CPI."""
    h = card.get("hari_h") or {}
    if card.get("title") not in PASAR or card.get("released") or h.get("p_naik") is None:
        return None
    naik = int(round(float(h["p_naik"]) * 100))
    benar, n = uji_pasar()
    bukti = (f"pasar Kalshi/Polymarket × reaksi emas 1 menit (diperbarui tiap 15 menit; pernyataan Fed/Trump/negara "
             f"langsung tercermin di harga pasar) • teruji 2022–2025: sinyal ≥ 60% benar {benar} dari {n} rilis "
             "→ sampel kecil, belum pasti")
    return baris(card["title"], naik, bukti, "pasar", "1 menit")


PERINGKAT = {1: "⚡ Sangat kuat", 2: "🥈 Kuat", 3: "🥉 Lemah", 4: "Biasa"}


def peringkat(pr: dict, card: dict) -> int:
    if pr["sumber"] == "kandidat":                     # kandidat NFP yang lolos uji maju otomatis
        return 2
    """1 ⚡ = peluang ≥ 60% DAN teruji ≥ 60% di periode lama & baru; 2 = model teruji, peluang ≥ 60%;
    3 = model, peluang 55–59%; 4 = dasar historis (≈ lempar koin)."""
    pct = max(pr["naik"], 100 - pr["naik"])
    if pr["sumber"] == "pasar":                     # sampel uji kecil (n ±17) → paling tinggi 🥈
        benar, n = uji_pasar()
        return 2 if pct >= 60 and n >= 15 and benar / n >= 0.6 else 3 if pct >= 55 else 4
    if pr["sumber"] == "aturan":
        return 1 if pct >= 60 else 3
    if pr["sumber"] == "model":
        u = (card.get("prarilis") or {}).get("uji") or {}
        if pct >= 60 and u.get("lama", 0) >= 60 and u.get("baru", 0) >= 60:
            return 1
        return 2 if pct >= 60 else 3 if pct >= 55 else 4
    return 4


def untuk(card: dict, mem: dict | None = None) -> dict | None:
    title = card.get("title") or ""
    pa = pasar(card)
    if pa:
        return pa
    p = card.get("prarilis")
    if p and p.get("naik") is not None and not card.get("released"):
        return baris(title, int(p["naik"]), p.get("bukti") or "model sebelum rilis", "model")
    if title == NFP and ((mem or {}).get(NFP) or {}).get("s") == 1:
        return baris(title, ATURAN_NFP[0], ATURAN_NFP[1], "aturan")
    st = _persiapan.STATS.get("dasar", {}).get(title) or {}
    seb = st.get("emas_sebelum") or {}
    if seb.get("naik1j") is None:
        return None
    periode = str(_persiapan.STATS.get("periode") or "")
    periode = f"{periode[:4]}–{periode.split('..')[-1].strip()[:4]}" if ".." in periode else (periode or "data historis")
    baru = seb.get("baru_naik1j")
    bukti = (f"dasar: emas naik 1 jam di {seb['naik1j']}% dari {seb.get('n', '?')} rilis ({periode})"
             + (f" • sejak Okt 2021 {baru}%" if baru is not None else "") + " • tanpa petunjuk lain → mendekati lempar koin")
    return baris(title, int(seb["naik1j"]), bukti, "dasar")


def detail(card: dict, pr: dict, persiapan: dict, titik: dict | None) -> list[dict]:
    """Blok di balik show/hide: dasar angka, 🔄 titik balik ekonomi (NFP), 🏦 keputusan Fed (Polymarket)."""
    out = [{"judul": "Dasar angka", "teks": pr["catatan"], "catatan": pr["bukti"]}]
    title = card.get("title")
    h = card.get("hari_h") or {}
    if h.get("teks") and not card.get("released"):     # 🎲 peluang pasar + riwayat (bergeser = ada berita/pernyataan)
        g = h.get("geser") or {}
        geser = ""
        if g and abs(g["ke"] - g["dari"]) >= GESER:
            jam = f"{g['jam']:g}".replace(".", ",")
            geser = (f"⚠️ Peluang emas naik bergeser {round(g['dari'] * 100)}% → {round(g['ke'] * 100)}% dalam {jam} "
                     "jam — pasar bereaksi pada data/pernyataan baru. ")
        out.append({"judul": "🎲 Pasar prediksi (diperbarui tiap 15 menit)", "teks": h["teks"],
                    "catatan": geser + (h.get("bukti") or "")})
    if card.get("petunjuk_teruji"):                     # 🧭 petunjuk teruji (Kalshi, kejutan lalu, GDPNow, berbalik)
        k = card["petunjuk_teruji"]
        out.append({"judul": k["judul"], "teks": k["teks"], "catatan": k["catatan"]})
    if card.get("kalshi_sebaran"):                      # 📅 sebelum konsensus terbit: angka paling mungkin menurut pasar
        k = card["kalshi_sebaran"]
        out.append({"judul": k["judul"], "teks": k["teks"], "catatan": k["catatan"]})
    for x in (persiapan.get("pernyataan") or {}).get("penting") or []:
        if title in (x.get("untuk") or ()):            # 🗣️ pernyataan Fed/Trump/pemerintah terbaru yang relevan
            out.append({"judul": "🗣️ Pernyataan terbaru", "teks": x.get("judul") or "", "catatan": x.get("catatan") or ""})
    if title == NFP and titik and not card.get("released"):
        out.append({"judul": titik["judul"], "teks": titik["teks"],
                    "catatan": "\n".join((titik["kondisi"], titik["pendahulu"], titik["bukti"]))})
        if titik.get("lead", 0) >= 2:                   # 🧪 kandidat research/news_gabung.py
            lolos, naik, n = kandidat_lolos(maju())
            out.append({"judul": "🧪 Kandidat" + (" (lolos → 🥈)" if lolos else " (belum terbukti)"),
                        "teks": "Pendahulu membaik → emas naik 1 jam 66% setelah NFP",
                        "catatan": f"2012–2021: 63% (n 46) • sejak Okt 2021 + uji maju: {naik}/{n} naik "
                                   f"• naik ke 🥈 bila n ≥ 30 dan ≥ 58% (dicek otomatis tiap NFP dari arsip data)"})
    m = maju()
    g = (m.get("per_peringkat") or {}).get(str(pr.get("peringkat")), {})
    sm = m.get("semua") or {}
    if m:
        out.append({"judul": f"📈 Uji maju sejak {m.get('mulai', '7 Okt 2026')}",
                    "teks": (f"{pr.get('peringkat_teks', '')}: benar {g.get('benar', 0)} dari {g.get('n', 0)} rilis"
                             if g.get("n") else f"{pr.get('peringkat_teks', '')}: belum ada rilis yang dinilai"),
                    "catatan": f"Semua prediksi: benar {sm.get('benar', 0)} dari {sm.get('n', 0)} • dinilai otomatis tiap "
                               f"jam dari arsip (emas 5 menit, 1 jam setelah rilis) • diperbarui {m.get('diperbarui', '-')}"})
    fed = persiapan.get("fed") if isinstance(persiapan.get("fed"), dict) else None
    if title == "Federal Funds Rate" and fed and fed.get("teks"):
        out.append({"judul": fed.get("label") or "🏦 Keputusan Fed", "teks": fed["teks"], "catatan": fed.get("bukti", "")})
    return out


def attach(persiapan: dict, store=None, now=None, env: dict | None = None) -> None:
    """Isi field "prediksi" (+ "detail" untuk show/hide) di setiap kartu berita pekan ini & berita besar berikutnya."""
    if not isinstance(persiapan, dict):
        return
    titik = None
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)]
    if any(c.get("title") == NFP and not c.get("released") for c in kartu):
        try:                                            # 🔄 mean reversion NFP + pendahulu (_nfp_titik.py)
            import _nfp_titik
            from datetime import datetime, timezone
            titik = _nfp_titik.kondisi(now or datetime.now(timezone.utc), store, env or {})
        except Exception:  # noqa: BLE001 - detail opsional
            titik = None
    mem = {}
    if store is not None:
        try:
            import _prarilis
            mem = {**_prarilis.SEED, **((store.get_state("prarilis") or {}).get("mem") or {})}
        except Exception:  # noqa: BLE001 - tanpa memori kejutan: pakai model/dasar
            mem = {}
    promo = bool(titik and titik.get("lead", 0) >= 2 and kandidat_lolos(maju())[0])
    for c in kartu:
        pr = untuk(c, mem)
        if pr and promo and c.get("title") == NFP and not c.get("released") and pr["sumber"] == "dasar":
            pr = baris(NFP, 66, "kandidat lolos uji maju: pendahulu membaik → emas naik 1 jam 66% (2012–2025)", "kandidat")
        if pr:
            r = peringkat(pr, c)
            pr["peringkat"], pr["peringkat_teks"] = r, PERINGKAT[r]
            if r == 1:
                pr["teks"] = "⚡ " + pr["teks"]
            pr["catatan"] = f"{PERINGKAT[r]} • {pr['catatan']}"
            pr["detail"] = detail(c, pr, persiapan, titik)
            c["prediksi"] = pr
