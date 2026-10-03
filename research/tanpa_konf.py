"""Uji varian tanpa kategori konf: kode cloud asli diputar ulang, konf tidak dikirim (cloud TIDAK diubah).
python -m research.tanpa_konf XAU|BTC -> data/research/eksternal/verifikasi/cloud_<aset>_tanpakonf.csv (3 Okt 2026).
Hasil (spread asli, sejak Okt 2021): BTC lebih baik (+0,33 vs +0,27R/sin, DD -32 vs -41); XAU campur
(LAMA lebih baik, BARU lebih buruk: +105R DD -69 vs +131R DD -42) -> XAU konf tetap.
Sejak BTC konf dimatikan, replay live BTC = cloud_BTC.csv; versi lama dengan konf = cloud_BTC_dengankonf.csv."""
import sys
import research.verifikasi_cloud as v
_core = v._core
orig = _core.category
def cat(closed, direction, cfg):
    meta, note = orig(closed, direction, cfg)
    if meta["cat"].split(" ", 1)[-1] == "konf":
        meta = {**meta, "star": False}
    return meta, note
_core.category = cat
name = sys.argv[1]
out = v.replay(name)
v.OUT.mkdir(parents=True, exist_ok=True)
out.to_csv(v.OUT / f"cloud_{name}_tanpakonf.csv", index=False)
print("selesai", len(out))
