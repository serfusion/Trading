"""📈 UJI MAJU tebakan CPI/PPI aplikasi — dicatat SEBELUM rilis (research/arsip_data.pra), dinilai SESUDAH rilis dengan tick Exness.

python -m research.uji_maju_berita [folder_arsip]     → docs/eksternal/hasil_uji_maju_berita.txt

Tanpa folder: ambil branch `arsip-data` (git fetch origin arsip-data). Satu-satunya validasi yang bebas semua bias riset
(data hilang, pasca-lihat, banyak uji): tebakan dibekukan sebelum rilis, hasil emas diukur setelahnya. Tick bulan rilis
diunduh dari arsip Exness bila belum ada (research/riset_dalam_data.tambah_bulan; arsip bulan berjalan biasanya tersedia
±1 hari kemudian). Satu baris per waktu rilis (CPI m/m/core/y/y = satu tebakan).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from .riset_dalam_data import satu, tambah_bulan, ticks

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "eksternal" / "hasil_uji_maju_berita.txt"


def catatan(folder: str | None) -> dict:
    out: dict = {}
    if folder:
        for f in sorted(Path(folder, "pra").glob("*.json")):
            out.update(json.loads(f.read_text(encoding="utf-8")))
        return out
    subprocess.run(["git", "fetch", "-q", "origin", "arsip-data"], cwd=ROOT, check=False)
    ls = subprocess.run(["git", "ls-tree", "-r", "--name-only", "FETCH_HEAD", "pra/"], cwd=ROOT, capture_output=True,
                        text=True).stdout.split()
    for nm in ls:
        isi = subprocess.run(["git", "show", f"FETCH_HEAD:{nm}"], cwd=ROOT, capture_output=True, text=True).stdout
        out.update(json.loads(isi or "{}"))
    return out


def main() -> None:
    c = catatan(sys.argv[1] if len(sys.argv) > 1 else None)
    now = pd.Timestamp.now(tz="UTC")
    per_waktu: dict = {}
    for v in c.values():
        t = pd.Timestamp(v["time"])
        if t < now - pd.Timedelta(minutes=20) and v.get("arah"):
            per_waktu.setdefault(v["time"], v)
    L = ["# 📈 Uji maju tebakan CPI/PPI aplikasi (research/uji_maju_berita.py)", __doc__.split("\n\n")[1], ""]
    rows = []
    for ts, v in sorted(per_waktu.items()):
        t = pd.Timestamp(ts)
        if ticks(t) is None:
            tambah_bulan((t.strftime("%Y-%m"), [t]))
        o = satu(t)
        g = 1.0 if v["arah"] == "naik" else -1.0
        r = {"time": ts, "berita": v["title"], "tebakan": v["arah"], "persen": v.get("persen"), "jalur": v.get("jalur"),
             "status": v.get("status"), "indeks_pertama": v.get("indeks_pertama")}
        for k in ("d1", "d2", "d5", "d10", "arah"):
            y = o.get(k)
            r[k] = None if y is None or y != y or y == 0 else bool(y == g)
        sk = v.get("sekilas_tren4")                       # pembanding "cara sekilas": ikut tren emas 4 jam
        gs = 1.0 if sk == "naik" else -1.0 if sk == "turun" else None
        y2 = o.get("d2")
        r["sekilas_d2"] = None if gs is None or y2 is None or y2 != y2 or y2 == 0 else bool(y2 == gs)
        rows.append(r)
        L.append(f"   {ts} {v['title']:14s} tebak {v['arah'].upper():5s} {v.get('persen')}% ({v.get('jalur')}, {v.get('status')}) → "
                 + " ".join(f"{k} {'✓' if r[k] else ('✗' if r[k] is False else '–')}" for k in ("d1", "d2", "d5", "d10", "arah"))
                 + f" | konsensus indeks pertama: {v.get('indeks_pertama') or 'tidak muncul sebelum rilis'}")
    x = pd.DataFrame(rows)
    if len(x):
        L.append("\nRingkas (benar / dinilai): " + " • ".join(
            f"{k} {int(x[k].eq(True).sum())}/{int(x[k].notna().sum())}" for k in ("d1", "d2", "d5", "d10", "arah", "sekilas_d2")))
    else:
        L.append("Belum ada rilis yang lewat sejak pencatatan dimulai (13 Okt 2026).")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
