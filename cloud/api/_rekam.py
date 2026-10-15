"""📝 Rekam hasil berita TIAP JAM (15 Okt 2026, audit setelah bug "PPI 74% → 55%").

Hasil rilis (Act vs perkiraan) dipakai berita berikutnya: PPI ← CPI inti bulan yang sama (_ppi_wti), "kejutan rilis lalu"
NFP/JOLTS/Fed (_prarilis, _prediksi) dan petunjuk CPI/PPI/ISM/JOLTS/pengangguran (_petunjuk). Dulu memori itu hanya
diperbarui saat aplikasi memanggil GET /api/chat ketika berita masih ada di kalender pekan ini — bila aplikasi tidak dibuka
sampai pekan berganti (kalender ForexFactory hanya pekan ini), hasilnya hilang. Kini cron tick (tiap jam) juga merekam:
kalender pekan ini (cache Supabase 'kalender') → Act resmi (_aktual: BLS → FRED, cache 'aktual') → memori Supabase
'prarilis', 'petunjuk', 'ppi_cpi' + 'hasil_rilis' (🔗 keterkaitan: hasil terakhir semua berita berdampak tinggi). Hanya bekerja bila ada berita yang dipantau terbit ≤ 4 hari terakhir. Env REKAM_HASIL=0
mematikan. Tidak menyentuh sinyal/order.
"""
from __future__ import annotations

from datetime import datetime

import _aktual
import _chat
import _petunjuk
import _ppi_wti
import _prarilis

JUDUL = set(_prarilis.TITLES) | set(_petunjuk.ATURAN) | {"Core CPI m/m"}


def jalankan(store, now: datetime, env: dict, rows_fn) -> dict:
    if (env or {}).get("REKAM_HASIL", "1") == "0" or store is None:
        return {"status": "mati"}
    # 15 Okt (keterkaitan): Act diisi untuk SEMUA berita berdampak tinggi (Retail, klaim, GDP, keyakinan konsumen …), memori
    # prarilis/petunjuk/ppi_cpi tetap hanya judul JUDUL (objek kalender yang sama → Act ikut terisi)
    rows = rows_fn() or []
    semua = _chat.calendar_json(rows, now, fetch=lambda s: []) + [   # + berdampak sedang yang ber-Act resmi (mis. klaim)
        c for c in _chat.calendar_json(rows, now, fetch=lambda s: [], dampak=("Medium",)) if c["title"] in _chat.FRED_MAP]
    cal = [c for c in semua if c.get("title") in JUDUL]
    baru = [c for c in semua if c.get("released") and now - datetime.fromisoformat(c["time"]) <= _aktual.WINDOW]
    if not baru:
        return {"status": "tidak ada rilis"}
    out = {"aktual": _aktual.fill(semua, store, now, env).get("status")}
    out["prarilis"] = _prarilis.simpan_mem(cal, store)
    _petunjuk.ingat(cal, store, now)
    try:                                                  # 🔗 memori hasil terakhir semua judul (keterkaitan, 15 Okt)
        import _keterkaitan
        _keterkaitan.ingat(semua, store)
    except Exception:  # noqa: BLE001
        pass
    ci = _ppi_wti.simpan_cpi(cal, store)
    out["cpi_inti"] = ci.get("time") if ci else None
    out["act"] = sum(1 for c in baru if c.get("actual"))
    return {"status": "ok", **out}
