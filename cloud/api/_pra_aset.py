"""⏱️ Rencana pengguna "entry 1 detik SEBELUM rilis, tutup 1–5 setelah rilis" — angka terbaik per aset (XAU, BTC, ETH)
untuk berita besar berikutnya, ditampilkan di bawah tile sinyal (MarketStrip, aplikasi 4.27).

Data: cloud/api/pra_aset.json (research/pra_aset.py: tick Dukascopy & Exness XAU, Binance & Exness BTC, Binance ETH;
entry t0−1 dtk + slippage realistis, tutup t0+1/2/3/5 dtk atau t0+1…5 mnt; keluar terbaik dipilih dari periode LAMA
lalu dilaporkan apa adanya). Arah = petunjuk teruji berita itu (_petunjuk.py → arah emas; kripto searah) bila ada;
tanpa petunjuk → ditampilkan "arah ≈ 50:50". Permintaan pengguna 10 Okt 2026. INFORMASI saja, tanpa order.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import _persiapan
import _prediksi

_PATH = Path(__file__).resolve().parent / "pra_aset.json"
DATA = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
ASET = ("XAU", "BTC", "ETH")


def grup(title: str) -> str | None:
    if "JOLTS" in title:
        return "JOLTS"
    if title.startswith("ADP"):
        return "ADP"
    return _persiapan.group_of(title)


def _angka(aset: str, v: float) -> str:
    if aset == "XAU":
        return f"{'+' if v >= 0 else '−'}${abs(v):.2f}".replace(".", ",")
    return f"{'+' if v >= 0 else '−'}{abs(v):.3f}%".replace(".", ",")


def sel(aset: str, stats: dict, arah: str | None) -> dict | None:
    """Satu sel: arah, keluar terbaik (detik atau menit), % rilis untung, rata-rata, status jujur."""
    cara = "petunjuk" if arah else None
    pilihan = []
    for rentang in ("dtk", "mnt"):
        r = stats.get(f"{cara}|{rentang}") if cara else None
        if r:
            pilihan.append(r)
    if not pilihan:
        return {"arah": "—", "teks": "arah ≈ 50:50", "kecil": "tanpa petunjuk teruji", "status": "acak"}
    r = max(pilihan, key=lambda x: x.get("avg") if x.get("avg") is not None else -9)
    avg, wr = r.get("avg") or 0.0, r.get("wr") or 0.0
    if r.get("teruji"):
        status, tanda = "teruji", "✅"
    elif avg > 0:
        status, tanda = "belum terbukti", "⚠️"
    else:
        status, tanda = "rugi", "🔴"
    satuan = "/0,01 lot" if aset == "XAU" else ""
    return {"arah": arah, "keluar": r.get("keluar"), "wr": wr, "avg": avg, "n": r.get("n"), "status": status,
            "teks": f"{arah} • tutup {r.get('keluar')}",
            "kecil": f"untung {wr:.0f}% rilis • rata {_angka(aset, avg)}{satuan} {tanda}".replace(".", ","),
            "bukti": f"n {r.get('n')} rilis • sejak Okt 2021 rata {_angka(aset, r['baru']) if r.get('baru') is not None else '-'}"
                     f" (untung {r.get('wr_baru') or 0:.0f}%)".replace(".", ",")}


def attach(persiapan: dict, now: datetime | None = None) -> None:
    """persiapan["pra"] = berita besar berikutnya + sel XAU/BTC/ETH untuk rencana entry 1 detik sebelum rilis."""
    if not isinstance(persiapan, dict) or not DATA:
        return
    now = now or datetime.now(timezone.utc)
    kartu = [c for k in ("berita", "mendatang") for c in persiapan.get(k) or [] if isinstance(c, dict)
             and not c.get("released") and grup(c.get("title") or "") in (DATA.get("berita") or {})]
    kartu = [c for c in kartu if datetime.fromisoformat(c["time"]) > now]
    if not kartu:
        return
    t0 = min(c["time"] for c in kartu)
    sama = [c for c in kartu if c["time"] == t0]
    c = next((x for x in sama if x.get("petunjuk_teruji", {}).get("arah_emas")), sama[0])
    g = grup(c["title"])
    arah_emas = (c.get("petunjuk_teruji") or {}).get("arah_emas")
    arah = None if not arah_emas else ("BUY" if arah_emas == "naik" else "SELL")
    stats = DATA["berita"][g]
    persiapan["pra"] = {
        "judul": f"⏱️ Entry 1 dtk sebelum {_prediksi.nama(c['title'])}",
        "title": c["title"], "time": c["time"], "when": c.get("when", ""), "grup": g,
        "aset": {a: sel(a, stats.get(a) or {}, arah) for a in ASET},
        "catatan": "Riwayat tick 2010–2026: entry t−1 dtk + slippage, tutup terbaik 1–5 dtk / 1–5 mnt. ⚠️ = positif "
                   "tapi belum terbukti, 🔴 = rata-rata rugi. Info saja, bukan jaminan."}
