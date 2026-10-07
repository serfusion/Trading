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

import _persiapan

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


def baris(title: str, naik: int, bukti: str, sumber: str) -> dict:
    up = naik >= 50
    return {"teks": f"{nama(title)}: peluang emas {'naik' if up else 'turun'} 1 jam {naik if up else 100 - naik}%",
            "catatan": CATATAN, "bukti": bukti, "naik": int(naik), "kuat": abs(naik - 50) >= 10, "sumber": sumber}


PERINGKAT = {1: "⚡ Sangat kuat", 2: "🥈 Kuat", 3: "🥉 Lemah", 4: "Biasa"}


def peringkat(pr: dict, card: dict) -> int:
    """1 ⚡ = peluang ≥ 60% DAN teruji ≥ 60% di periode lama & baru; 2 = model teruji, peluang ≥ 60%;
    3 = model, peluang 55–59%; 4 = dasar historis (≈ lempar koin)."""
    pct = max(pr["naik"], 100 - pr["naik"])
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
    if title == NFP and titik and not card.get("released"):
        out.append({"judul": titik["judul"], "teks": titik["teks"],
                    "catatan": "\n".join((titik["kondisi"], titik["pendahulu"], titik["bukti"]))})
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
    for c in kartu:
        pr = untuk(c, mem)
        if pr:
            r = peringkat(pr, c)
            pr["peringkat"], pr["peringkat_teks"] = r, PERINGKAT[r]
            if r == 1:
                pr["teks"] = "⚡ " + pr["teks"]
            pr["catatan"] = f"{PERINGKAT[r]} • {pr['catatan']}"
            pr["detail"] = detail(c, pr, persiapan, titik)
            c["prediksi"] = pr
