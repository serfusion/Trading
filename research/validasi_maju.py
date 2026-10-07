"""📈 Uji maju otomatis prediksi berita dari arsip — python -m research.validasi_maju <folder_arsip>

Permintaan pengguna 7 Okt 2026 ("pasang di setiap news baru ... uji validasi ke depannya"). Tiap jam (workflow
arsip_data.yml) membaca branch `arsip-data`:
  prediksi/<pekan>.json   baris prediksi terakhir SEBELUM rilis (pipa cloud yang sama dengan aplikasi)
  candle/XAUUSD_5min.csv  harga emas 5 menit
Untuk setiap rilis sejak 7 Okt 2026 yang sudah lewat ≥ 65 menit: emas naik 1 jam? = close 5-mnt di +60 mnt > close
candle 5-mnt terakhir sebelum rilis. Prediksi "benar" bila arah yang ditampilkan (naik/turun) sama. Peluang tepat 50%
tidak dinilai. Hasil → cloud/api/validasi_maju.json (ditampilkan di detail prediksi; dipakai menaikkan 🧪 kandidat NFP
ke 🥈 bila bukti sejak Okt 2021 mencapai n ≥ 30 dan ≥ 58%).
"""
from __future__ import annotations

import csv
import json
import sys
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cloud" / "api" / "validasi_maju.json"
MULAI = datetime(2026, 10, 7, tzinfo=timezone.utc)
NAMA_PERINGKAT = {1: "⚡ Sangat kuat", 2: "🥈 Kuat", 3: "🥉 Lemah", 4: "Biasa"}


def harga5(root: Path) -> tuple[list[datetime], list[float]]:
    p = root / "candle" / "XAUUSD_5min.csv"
    if not p.exists():
        return [], []
    t, c = [], []
    with p.open() as f:
        for r in csv.DictReader(f):
            t.append(datetime.fromisoformat(r["time_utc"]).replace(tzinfo=timezone.utc))
            c.append(float(r["close"]))
    return t, c


def gerak_1jam(t: list[datetime], c: list[float], rilis: datetime) -> float | None:
    """close candle 5-mnt yang berakhir tepat sebelum rilis → close candle yang berakhir +60 mnt."""
    i0 = bisect_left(t, rilis - timedelta(minutes=5))           # candle [rilis−5, rilis)
    i1 = bisect_left(t, rilis + timedelta(minutes=55))          # candle [rilis+55, rilis+60)
    if i0 >= len(t) or i1 >= len(t) or t[i0] != rilis - timedelta(minutes=5) or \
            t[i1] != rilis + timedelta(minutes=55):
        return None
    return c[i1] - c[i0]


def main(root: Path, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    t, c = harga5(root)
    pred = {}
    for f in sorted((root / "prediksi").glob("*.json")):
        pred.update(json.loads(f.read_text()))
    hasil = []
    for k, p in sorted(pred.items(), key=lambda kv: kv[1]["time"]):
        rilis = datetime.fromisoformat(p["time"]).astimezone(timezone.utc)
        if rilis < MULAI or now - rilis < timedelta(minutes=65) or p.get("naik") == 50:
            continue
        g = gerak_1jam(t, c, rilis)
        if g is None or g == 0:
            continue
        naik = p["naik"] > 50
        hasil.append({"judul": p["teks"].replace("⚡ ", ""), "title": p["title"], "waktu": p["time"],
                      "peringkat": p.get("peringkat") or 4, "kandidat": bool(p.get("kandidat")),
                      "gerak": round(g, 2), "benar": (g > 0) == naik})
    per = {}
    for r in hasil:
        x = per.setdefault(str(r["peringkat"]), {"nama": NAMA_PERINGKAT.get(r["peringkat"], "?"), "benar": 0, "n": 0})
        x["n"] += 1
        x["benar"] += int(r["benar"])
    kand = [r for r in hasil if r["kandidat"]]
    obj = {"mulai": MULAI.strftime("%Y-%m-%d"), "diperbarui": now.strftime("%Y-%m-%dT%H:%MZ"),
           "semua": {"benar": sum(r["benar"] for r in hasil), "n": len(hasil)}, "per_peringkat": per,
           "kandidat_nfp": {"naik": sum(1 for r in kand if r["gerak"] > 0), "n": len(kand)},
           "terakhir": hasil[-15:][::-1]}
    lama = json.loads(OUT.read_text()) if OUT.exists() else {}
    if {k: v for k, v in lama.items() if k != "diperbarui"} != {k: v for k, v in obj.items() if k != "diperbarui"}:
        OUT.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")   # tulis hanya bila berubah
    print(json.dumps({k: obj[k] for k in ("semua", "per_peringkat", "kandidat_nfp")}, ensure_ascii=False))
    return obj


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "arsip"))
