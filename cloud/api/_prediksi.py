"""🎯 Satu baris prediksi per berita: "NFP: peluang emas naik 1 jam 61% (teruji, belum pasti)".

Permintaan pengguna 7 Okt 2026: tampilkan cukup satu baris per berita — tanpa skenario "Act < … / Act > …". Dipakai
untuk berita pekan ini (persiapan["berita"]) dan berita besar berikutnya (persiapan["mendatang"]). Sumber, berurutan:
  1. model  : peluang model sebelum rilis NFP/JOLTS/Fed (_prarilis, walk-forward 2015–2025 benar 60–65%)
  2. aturan : NFP setelah rilis lalu DI ATAS perkiraan → emas naik 1 jam 72% (s.d. Sep 2021) / 61% (sejak Okt 2021);
              satu-satunya aturan yang konsisten dari ±216 yang diuji (research/news_semua.py)
  3. dasar  : frekuensi historis emas naik 1 jam setelah rilis itu (research/news_prediksi.py, semua tahun)
Angka besar = arah yang lebih sering (naik/turun). Info saja — bukan kepastian, tidak membuka order.
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


def attach(persiapan: dict, store=None) -> None:
    """Isi field "prediksi" di setiap kartu berita pekan ini & berita besar berikutnya."""
    if not isinstance(persiapan, dict):
        return
    mem = {}
    if store is not None:
        try:
            import _prarilis
            mem = {**_prarilis.SEED, **((store.get_state("prarilis") or {}).get("mem") or {})}
        except Exception:  # noqa: BLE001 - tanpa memori kejutan: pakai model/dasar
            mem = {}
    for key in ("berita", "mendatang"):
        for c in persiapan.get(key) or []:
            if isinstance(c, dict):
                pr = untuk(c, mem)
                if pr:
                    c["prediksi"] = pr
