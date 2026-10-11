"""🔁 Uji maju otomatis aturan snipe X1 — python -m research.snipe_x1_maju <folder_arsip> [--tanpa-unduh]

Dijalankan GitHub Actions (.github/workflows/snipe_maju.yml) tiap jam. Token baru X1 (pool XDEX yang dibuat SETELAH
riset, ≥ 25 jam lalu supaya jendela 24 jam lengkap) diunduh dari RPC publik, lalu aturan kandidat di
research/snipe_x1_aturan.json diputar ulang dengan simulator yang SAMA persis dengan riset (sisip beli 2 XNT,
biaya DEX + bot 1%/sisi, jual telat 1 transaksi). Hasil = persentase snipe untung pada data yang belum pernah dilihat.

Folder arsip (branch `arsip-snipe`) menyimpan hanya file BARU (tanda/swap pool baru, penyandang, hasil). Saat jalan,
data riset di repo (data/research/eksternal/snipe_x1) disalin ke folder kerja sementara lalu ditimpa file arsip →
kode riset dipakai apa adanya. Tanpa kunci, tanpa wallet, tanpa order: hanya membaca data publik.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from research import snipe_x1 as S

ROOT = Path(__file__).resolve().parent.parent
ATURAN_F = ROOT / "research" / "snipe_x1_aturan.json"
JEDA_LENGKAP = 25 * 3600  # pool baru diproses setelah jendela 24 jam (+1 jam) lengkap
T_RISET = pd.Timestamp("2026-10-10T12:20:00Z").timestamp()  # waktu unduh data riset (tanda lama tanpa "diunduh")


def siapkan(arsip: Path) -> Path:
    """Folder kerja = data riset + file arsip (arsip menang)."""
    kerja = arsip / "_kerja"
    if kerja.exists():
        shutil.rmtree(kerja)
    shutil.copytree(S.DIR, kerja, ignore=shutil.ignore_patterns("*.pkl"))
    simpanan = arsip / "snipe_x1"
    if simpanan.exists():
        shutil.copytree(simpanan, kerja, dirs_exist_ok=True)
    return kerja


def unduh_baru(kerja: Path, simpanan: Path) -> list[str]:
    """Pool baru: tanda (24 jam) + swap peluncuran; salin file baru ke simpanan arsip. Kembalikan pool baru."""
    S.DIR = kerja
    pools = S.unduh_pool()
    S.unduh_cadangan(pools)
    now = time.time()
    baru = []
    for p in pools:
        f = kerja / "tanda" / f"{p['pool']}.json.gz"
        if f.exists():
            lama = S.muat(f)
            if not lama.get("t0") or lama.get("diunduh", T_RISET) - lama["t0"] >= 24 * 3600 + 600:
                continue  # jendela 24 jam sudah lengkap saat diunduh
            (kerja / "swap" / f"{p['pool']}.json.gz").unlink(missing_ok=True)  # jendela belum lengkap → unduh ulang
        s = S._sigs(p["pool"], batas_jam=24, maks_hal=40)
        if s.get("terpotong") or not s["t0"] or now - s["t0"] < JEDA_LENGKAP:
            continue  # terlalu muda (jendela belum lengkap) atau riwayat terlalu panjang
        s["diunduh"] = now
        S.simpan(f, s)
        baru.append(p["pool"])
    from research import snipe_x1_uji as U
    L = U.peluncuran()
    S.unduh_pasok([q["mint"] for q in L])
    S.unduh_otoritas([q["mint"] for q in L])
    perlu = [q for q in L if not (kerja / "swap" / f"{q['pool']}.json.gz").exists()]
    S.unduh_swap(perlu, maks=3000, pekerja=6)
    U.dana()
    for sub in ("tanda", "swap"):
        (simpanan / sub).mkdir(parents=True, exist_ok=True)
        for pl in baru + [q["pool"] for q in perlu]:
            src = kerja / sub / f"{pl}.json.gz"
            if src.exists():
                shutil.copy2(src, simpanan / sub / src.name)
    for nama in ("penyandang.json.gz",):
        shutil.copy2(kerja / nama, simpanan / nama)
    return baru


def pemain_ulang() -> None:
    """pemain.csv (dipakai reputasi wallet) dihitung ulang untuk semua peluncuran, tanpa simulasi berat."""
    from research import snipe_x1_uji as U
    out = []
    for L in U.peluncuran():
        d = U.kejadian(L)
        if d is None or (d.jenis == "buat").sum() == 0:
            continue
        g = U.pnl_wallet(d, L["fee"])
        if g.empty:
            continue
        g = g.reset_index()
        g["pool"], g["dtk"], g["pembuat"] = L["pool"], g.t1 - int(d.t.iloc[0]), g.w == L["creator"]
        out.append(g)
    pd.concat(out, ignore_index=True).to_csv(S.DIR / "pemain.csv", index=False)


def saring_dari(teks: str):
    """Saringan tertulis di JSON → fungsi (r, J). Hanya nama fitur & operator sederhana (eval dibatasi)."""
    kode = compile(teks, "<saringan>", "eval")
    for nama in kode.co_names:
        if nama not in ("r", "J", "get", "isnan", "np", "nan", "abs", "min", "max", "len"):
            raise ValueError(f"nama tidak diizinkan di saringan: {nama}")

    def f(r, J):
        return bool(eval(kode, {"__builtins__": {}, "np": np, "isnan": np.isnan, "nan": np.nan, "abs": abs, "min": min,
                                "max": max, "len": len}, {"r": r, "J": J}))
    return f


def nilai(arsip: Path) -> dict:
    from research import snipe_x1_wr as R
    R.F_JALUR = S.DIR / "wr_jalur.pkl"
    R.bangun()
    data = R.muat_siap()
    cfg = json.loads(ATURAN_F.read_text())
    mulai = pd.Timestamp(cfg["mulai_maju"]).timestamp()
    maju = [r for r in data if r["t0"] >= mulai]
    out = {"diperbarui": pd.Timestamp.now(tz="UTC").isoformat(timespec="minutes"), "mulai_maju": cfg["mulai_maju"],
           "peluncuran_maju": len(maju), "aturan": []}
    for a in cfg["aturan"]:
        sar = saring_dari(a["saringan"]) if a.get("saringan") else None
        h = R.hasil(maju, a["jeda"], tuple(a["keluar"]), sar)
        z = {"nama": a["nama"], "n": len(h), "wr": float(h.untung.mean()) if len(h) else None,
             "roi": float(h.out.mean() / R.MODAL - 1) if len(h) else None,
             "untung_xnt": float((h.out - R.MODAL).sum()) if len(h) else 0.0,
             "riset": a.get("riset")}
        if len(h):
            k, n = int(h.untung.sum()), len(h)
            p, zz = k / n, 1.96
            c = (p + zz * zz / (2 * n)) / (1 + zz * zz / n)
            e = zz * np.sqrt(p * (1 - p) / n + zz * zz / (4 * n * n)) / (1 + zz * zz / n)
            z["wr_ci95"] = [round(c - e, 3), round(c + e, 3)]
        out["aturan"].append(z)
    (arsip / "snipe_x1").mkdir(parents=True, exist_ok=True)
    (arsip / "snipe_x1" / "hasil_maju.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    baris = [f"🔁 UJI MAJU SNIPE X1 — diperbarui {out['diperbarui']} UTC, token baru sejak {cfg['mulai_maju']}: "
             f"{len(maju)}"]
    for z in out["aturan"]:
        wr = f"{z['wr']:.0%}" if z["wr"] is not None else "-"
        ci = f" (CI95 {z['wr_ci95'][0]:.0%}–{z['wr_ci95'][1]:.0%})" if z.get("wr_ci95") else ""
        roi = f"{z['roi']:+.0%}" if z["roi"] is not None else "-"
        baris.append(f"- {z['nama']}: n {z['n']}, untung {wr}{ci}, ROI {roi}, total {z['untung_xnt']:+.1f} XNT "
                     f"| riset: {z['riset']}")
    (arsip / "snipe_x1" / "HASIL_MAJU.md").write_text("\n".join(baris) + "\n")
    print("\n".join(baris))
    return out


def main(argv: list[str]) -> None:
    arsip = Path(argv[0]).resolve()
    simpanan = arsip / "snipe_x1"
    simpanan.mkdir(parents=True, exist_ok=True)
    asal = S.DIR
    kerja = siapkan(arsip)
    S.DIR = kerja
    try:
        if "--tanpa-unduh" not in argv:
            baru = unduh_baru(kerja, simpanan)
            print(f"pool baru diproses: {len(baru)}")
        pemain_ulang()
        nilai(arsip)
    finally:
        S.DIR = asal
        shutil.rmtree(kerja, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1:])
