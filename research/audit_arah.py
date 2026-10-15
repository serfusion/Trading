"""🔎 Audit angka yang tampil di aplikasi: dihitung PER ARAH tebakan? (15 Okt 2026)

python -m research.audit_arah        → docs/eksternal/hasil_audit_arah.txt + cloud/api/pra_aset.json["per_arah"]

Pengguna 15 Okt: "periksa news lain juga, saya curiga salah semua". Pemicu: PPI 74% ternyata mencampur tebakan NAIK (7/7)
& TURUN (7/12). Skrip ini menghitung ulang setiap aturan yang bisa tampil di kartu berita — varian xau_arah
(research/pra_xau_arah.py: CPI Kalshi/kejutan lalu/WTI, ISM Jasa berbalik, GDP GDPNow, NFP pengangguran, Core PPI, JOLTS),
aturan per berita (research/pra_per_berita.py: ISM Jasa -P, pengangguran PK5), dan tabel tren 4 jam (research/pra_xau_semua.py)
— TERPISAH untuk tebakan NAIK dan TURUN, LAMA (< Okt 2021) / BARU, plus pembanding "selalu NAIK" pada rilis yang sama.
Target sama dengan aplikasi: arah harga tengah tick Exness t0−1 dtk → t0+2/5/10 dtk (gerak berapa pun).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EKS = ROOT / "data" / "research" / "eksternal"
OUT = ROOT / "docs" / "eksternal" / "hasil_audit_arah.txt"
JSON = ROOT / "cloud" / "api" / "pra_aset.json"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
H = (2, 5, 10)
DASAR = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
DASAR["t0"] = pd.to_datetime(DASAR.t0, utc=True)


def dasar_naik(grup: str, h: int, mulai: pd.Timestamp) -> float | None:
    """Emas naik di detik h pada SEMUA rilis kelompok berita (sejak tebakan pertama) — pembanding TANPA syarat. (Membandingkan
    dengan selalu-NAIK pada subset tebakan itu sendiri tautologis: untuk tebakan NAIK hasilnya selalu sama persis.)"""
    x = DASAR[DASAR.grup == grup]
    x = x[x.t0 >= mulai]
    y = np.sign(x[f"y{h}_XAU_EXNESS"].where(x[f"y{h}_XAU_EXNESS"].notna(), x[f"y{h}_XAU"]))
    y = y[y != 0].dropna()
    return round(float((y > 0).mean() * 100), 1) if len(y) >= 10 else None


def ringkas(tebak: np.ndarray, y: np.ndarray, t: pd.DatetimeIndex, grup: str | None = None, h: int = 2) -> dict:
    """Ketepatan per arah tebakan (+1/−1) terhadap y (+1/−1) + pembanding tanpa syarat (emas naik di semua rilis grup)."""
    ok = (tebak != 0) & (y != 0) & ~np.isnan(y)
    out = {}
    for nm, m in (("naik", ok & (tebak > 0)), ("turun", ok & (tebak < 0)), ("semua", ok)):
        if not m.any():
            continue
        b = tebak[m] == y[m]
        lama, baru = m & (t < SPLIT), m & (t >= SPLIT)
        f = lambda q: round(float((tebak[q] == y[q]).mean() * 100), 1) if q.sum() else None  # noqa: E731
        out[nm] = {"benar": round(float(b.mean() * 100), 1), "n": int(m.sum()), "lama": f(lama), "n_lama": int(lama.sum()),
                   "baru": f(baru), "n_baru": int(baru.sum())}
    if grup and ok.any():
        dn = dasar_naik(grup, h, t[ok].min())
        for nm in ("naik", "turun"):
            if nm in out and dn is not None:
                out[nm]["dasar"] = dn if nm == "naik" else round(100 - dn, 1)      # selalu NAIK / selalu TURUN
    return out


def teks(nama: str, h: int, r: dict) -> str:
    isi = []
    for k in ("naik", "turun", "semua"):
        o = r.get(k)
        if o:
            isi.append(f"{k.upper()} {o['benar']}% (n {o['n']}; lama {o['lama']} / baru {o['baru']}"
                       + (f"; pembanding selalu-{k.upper()} {o['dasar']}%" if o.get("dasar") is not None else "") + ")")
    return f"   {nama:44s} detik {h:2d}: " + " | ".join(isi)


def xau_arah(L: list, simpan: dict) -> None:
    from .pra_xau_arah import gerak, varian
    V = varian()
    times = sorted({t for _, s in V.values() for t in s.index})
    gk = gerak(times)["XAU_EXNESS"]
    L.append("\n## A. Varian xau_arah (pra_aset.json[\"xau_arah\"]) — tick Exness, gerak berapa pun")
    for nama, (grp, s) in V.items():
        simpan[nama] = {}
        for h in H:
            rows = [(t, d, np.sign(gk[t][h])) for t, d in s.items() if t in gk and h in gk[t]]
            if not rows:
                continue
            t = pd.DatetimeIndex([r[0] for r in rows])
            r = ringkas(np.array([r[1] for r in rows], float), np.array([r[2] for r in rows], float), t, grp, h)
            simpan[nama][str(h)] = r
            L.append(teks(nama, h, r))


def per_berita(L: list, simpan: dict) -> None:
    from .pra_per_berita import kutub
    df = pd.read_parquet(EKS / "pra_per_berita.parquet")
    d = json.loads(JSON.read_text(encoding="utf-8"))
    L.append("\n## B. Aturan per berita (pra_aset.json[\"per_berita\"])")
    for kunci, st in (d.get("per_berita") or {}).items():
        ev, fit = kunci.split("|")
        x = df[df.event == ev].copy()
        x["t0"] = pd.to_datetime(x.t0, utc=True)
        g = kutub(ev) * st["arah"] * x[fit].fillna(0).to_numpy()
        simpan[kunci] = {}
        for h in H:
            y = np.sign(x[f"y{h}_XAU_EXNESS"].where(x[f"y{h}_XAU_EXNESS"].notna(), x[f"y{h}_XAU"]).to_numpy(float))
            r = ringkas(g, y, pd.DatetimeIndex(x.t0), {"ISM Services PMI": "ISM", "Unemployment Rate": "NFP"}.get(ev), h)
            simpan[kunci][str(h)] = r
            L.append(teks(kunci, h, r))


def tren(L: list, simpan: dict) -> None:
    x = pd.read_parquet(EKS / "pra_xau_semua_v2.parquet")
    x["t0"] = pd.to_datetime(x.t0, utc=True)
    L.append("\n## C. Tabel tren 4 jam (pra_aset.json[\"tren\"]): petunjuk berita (KEJ) & tren emas 4 jam (H4)")
    kej, h4 = x.KEJ.fillna(0).to_numpy(float), np.sign(x.H4.fillna(0).to_numpy(float))
    for nm, m in (("sepakat", (kej != 0) & (h4 == kej)), ("berlawanan", (kej != 0) & (h4 != 0) & (h4 != kej))):
        simpan[f"tren|{nm}"] = {}
        for h in H:
            y = np.sign(x[f"y{h}_XAU_EXNESS"].where(x[f"y{h}_XAU_EXNESS"].notna(), x[f"y{h}_XAU"]).to_numpy(float))
            r = ringkas(np.where(m, kej, 0.0), y, pd.DatetimeIndex(x.t0))
            simpan[f"tren|{nm}"][str(h)] = r
            L.append(teks(f"tren {nm}", h, r))


def main() -> None:
    L = ["# 🔎 Audit per arah tebakan (research/audit_arah.py)", __doc__.split("\n\n")[1]]
    simpan: dict = {}
    xau_arah(L, simpan)
    per_berita(L, simpan)
    tren(L, simpan)
    d = json.loads(JSON.read_text(encoding="utf-8"))
    d["per_arah"] = simpan
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
