"""📊 Peringkat semua sinyal & label aplikasi dari hasil TERUJI — python -m research.peringkat

Permintaan pengguna 8 Okt 2026: "semua teorimu WR dan profit tinggi diperingkatkan pada (i) info sinyal, mulai dari XAU,
BTC, ⚡⭐🥈🥉💎🌊🔄🎯🧪 dll". Menulis cloud/api/peringkat.json (dikirim bersama riwayat.json lewat GET /api/chat?riwayat=1,
ditampilkan di tombol ⓘ aplikasi).

Sumber angka (periode BARU = Okt 2021–2026 kecuali disebut lain):
- XAU/BTC per peringkat ⚡/🥈/🥉/biasa & lapisan 🔁: replay kode cloud live (data/research/eksternal/verifikasi/
  cloud_XAU.csv dengan ⏸️ jeda 60 jam, cloud_BTC.csv), R bersih setelah spread asli Exness (research.verifikasi.net).
- ETH: cloud/api/riwayat.json; DOGE/ADA: cloud_DOGE_tambahan.csv / cloud_ADA_tambahan.csv (replay, R riset).
- 🎯 WR tinggi (lapisan BTC volatil): _core.WR_TINGGI; 🌊 ikut arus: _arus.RULES; 📰 sinyal setelah berita:
  sinyal_berita.json; Gap pekan forex: riwayat.json "GAP"; 💎 spot: spot_teruji.json (angka JUJUR research/spot_apk.py,
  9 Okt 2026; cadangan spot_model.json "teruji") + label ⚡ Dip ringan.
- Prediksi/info: prarilis.json (model NFP/JOLTS/Fed), _prediksi.ATURAN_NFP, nfp_titik.json (🔄), uji maju
  validasi_maju.json, 🧪 sinyal trader: docs/eksternal/hasil_sinyal_trader.txt (research/sinyal_trader.py).
Urutan: grup "sinyal" (bisa ditradingkan, satuan R per sinyal) menurut profit lalu WR; grup "spot" (% per trade);
grup "info" (akurasi tebakan, bukan profit) menurut akurasi BARU. Tidak ada janji profit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "cloud" / "api"
VER = ROOT / "data" / "research" / "eksternal" / "verifikasi"
OUT = API / "peringkat.json"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
TIER = {"zap": "⚡", "silver": "🥈", "bronze": "🥉", "biasa": "biasa"}


def _j(name: str) -> dict:
    return json.loads((API / name).read_text(encoding="utf-8"))


def _cell(r: pd.Series) -> dict:
    return {"n": int(len(r)), "wr": round(float((r > 0).mean() * 100), 1), "avg": round(float(r.mean()), 3)}


def _row(grup: str, label: str, sel: dict, satuan: str = "R", status: str = "dikirim", catatan: str = "",
         lama: dict | None = None) -> dict:
    out = {"grup": grup, "label": label, "n": sel["n"], "wr": sel["wr"], "avg": sel.get("avg"), "satuan": satuan,
           "status": status, "periode": sel.get("periode", "Okt 2021–2026")}
    if lama:
        out["lama"] = lama
    if catatan:
        out["catatan"] = catatan
    return out


def sinyal() -> list[dict]:
    from research.verifikasi import load, net
    sys.path.insert(0, str(API))
    import _arus
    import _core
    rows = []
    for a in ("XAU", "BTC"):
        df = net(a, load(a))
        df["R"] = df["R"].astype(float)
        base, lay = df[~df.lapis], df[df.lapis]
        for t, emo in TIER.items():
            g = base[base.tier == t]
            b, l_ = g[g.t_signal >= SPLIT], g[g.t_signal < SPLIT]
            if len(b) >= 20:
                cats = ", ".join(sorted(g.cat.unique()))
                rows.append(_row("sinyal", f"{a} {'💰 ' + cats if t == 'biasa' else emo + ' (' + cats + ')'}", _cell(b.R), lama=_cell(l_.R) if len(l_) else None,
                                 catatan="⚡ = kesempatan emas; lot lebih besar di aplikasi" if t == "zap" else ""))
        b, l_ = lay[lay.t_signal >= SPLIT], lay[lay.t_signal < SPLIT]
        if len(b):
            rows.append(_row("sinyal", f"{a} 🔁 lapisan (lot ½)", _cell(b.R), lama=_cell(l_.R) if len(l_) else None))
    w = _core.WR_TINGGI.get("BTC")
    if w:
        rows.append(_row("sinyal", "BTC 🎯 WR tinggi (lapisan saat volatil)", {"n": w["n"], "wr": w["wr"], "avg": w["avg_r"]},
                         lama={"wr": w["wr_lama"]}, catatan="label pada lapisan BTC"))
    riw = _j("riwayat.json")
    e = (riw.get("ETH") or {}).get("baru")
    if e:
        rows.append(_row("sinyal", "ETH ⭐/konf+⭐ (saat 💰 BTC searah)", e))
    for a in ("DOGE", "ADA"):
        p = VER / f"cloud_{a}_tambahan.csv"
        if p.exists():
            d = pd.read_csv(p, parse_dates=["t_signal"])
            d = d[~d.lapis]
            rows.append(_row("sinyal", f"{a} (saat 💰 BTC searah)", _cell(d[d.t_signal >= SPLIT].r),
                             lama=_cell(d[d.t_signal < SPLIT].r), catatan="R riset (spread tetap), lot ½"))
    for a, rule in _arus.RULES.items():
        t = rule["teruji"]
        rows.append(_row("sinyal", f"{a} 🌊 ikut arus", {"n": t["baru"][0], "wr": t["baru"][1], "avg": t["baru"][2]},
                         lama={"n": t["lama"][0], "wr": t["lama"][1], "avg": t["lama"][2]}, catatan=t["tahun"]))
    try:                                  # 📰 dihitung ulang dari replay live sekarang (sama dengan verifikasi.py bagian 6)
        import numpy as np

        from research.eksternal_berita import MAIN, calendar
        from research.sinyal_berita import tag
        df = net("XAU", load("XAU"))
        base = df[~df.lapis]
        sig = base.rename(columns={"t_signal": "t"}).assign(dir=np.where(base.dir == "BUY", 1, -1))
        after, _ = tag(sig, calendar(), MAIN, 4)
        g = base[np.asarray(after)]
        b, l_ = g[g.t_signal >= SPLIT], g[g.t_signal < SPLIT]
        if len(b):
            rows.append(_row("sinyal", "XAU 📰 sinyal ≤ 4 jam setelah berita besar", _cell(b.R), status="label",
                             lama=_cell(l_.R) if len(l_) else None, catatan="tanda pada sinyal 💰 XAU (bukan sinyal terpisah)"))
    except Exception as exc:  # noqa: BLE001 - kalender riset tidak ada: lewati baris 📰
        print("📰 dilewati:", exc)
    gap = riw.get("GAP") or {}
    if gap:
        n = sum(v["baru"]["n"] for v in gap.values())
        if n:
            wr = sum(v["baru"]["wr"] * v["baru"]["n"] for v in gap.values()) / n
            avg = sum(v["baru"]["avg"] * v["baru"]["n"] for v in gap.values()) / n
            rows.append(_row("sinyal", "Gap pekan forex (5 pair)", {"n": n, "wr": round(wr, 1), "avg": round(avg, 3)},
                             catatan="sampel kecil sejak 2021"))
    rows.sort(key=lambda r: (-(r["avg"] or 0), -r["wr"]))
    return rows


def spot() -> list[dict]:
    jujur = API / "spot_teruji.json"
    tj = _j("spot_teruji.json") if jujur.exists() else {}
    t = tj.get("teruji") or _j("spot_model.json")["teruji"]
    b = t["baru"]
    rows = [_row("spot", "💎 Spot Binance (naik +3% ≤ 10 hari; 3 merah / model; semua sinyal)",
                 {"n": b["n"], "wr": b["wr"], "avg": b["avg"]}, satuan="%",
                 lama={"n": t["lama"]["n"], "wr": t["lama"]["wr"], "avg": t["lama"]["avg"]},
                 catatan=f"angka jujur (koin volume terbesar saat itu, termasuk delisting) • masuk acak "
                         f"{t['dasar_baru']}% • kalah rata-rata {b['kalah']}%, terburuk {b['terburuk']}%")]
    k = (tj.get("tier") or {}).get("kilat")
    if k:
        kb, kl = k["baru"], k["lama"]
        rows.insert(0, _row("spot", f"💎 {k['nama']} (label: harga ≤ 15% di bawah puncak 20 hari)",
                            {"n": kb["n"], "wr": kb["wr"], "avg": kb["avg"]}, satuan="%", status="label",
                            lama={"n": kl["n"], "wr": kl["wr"], "avg": kl["avg"]},
                            catatan="label saja (sinyal lain tetap dikirim); arah ditemukan setelah melihat data "
                                    "2021–2026 → perlu uji maju; rugi ≥ 20% di ±1 dari 100 sinyal"))
    return rows


def info() -> list[dict]:
    sys.path.insert(0, str(API))
    import _prediksi
    rows = []
    for k, v in (_j("prarilis.json").get("model") or {}).items():
        u = v.get("uji") or {}
        if u:
            rows.append(_row("info", f"🎯 Prediksi {k}: arah emas 1 jam (model sebelum rilis)",
                             {"n": u["n_baru"], "wr": u["baru"], "avg": None}, satuan="akurasi", status="info",
                             lama={"n": u["n_lama"], "wr": u["lama"]}, catatan=f"dasar naik {u['dasar_naik']}%"))
    rows.append(_row("info", "🎯 NFP: rilis lalu di atas perkiraan → emas naik 1 jam",
                     {"n": None, "wr": float(_prediksi.ATURAN_NFP[0]), "avg": None}, satuan="akurasi", status="info",
                     lama={"wr": 72.0}, catatan="aturan ⚡ sangat kuat (72% s.d. 2021 / 61% sejak Okt 2021)"))
    t = _j("nfp_titik.json")["uji"]
    rows.append(_row("info", "🔄 Titik balik NFP (angka NFP pulih bulan depan)",
                     {"n": t["n_walk_forward"], "wr": float(t["walk_forward"]), "avg": None, "periode": t["periode"]},
                     satuan="akurasi", status="info", catatan=f"info ekonomi, bukan arah emas; dasar {t['dasar']}%"))
    m = _j("validasi_maju.json").get("kandidat_nfp") or {}
    rows.append(_row("info", "🧪 Kandidat NFP: pendahulu membaik → emas naik 1 jam",
                     {"n": 46, "wr": 63.0, "avg": None, "periode": "2012–2021"}, satuan="akurasi", status="kandidat",
                     catatan=f"uji maju sejak 7 Okt 2026: {m.get('naik', 0)}/{m.get('n', 0)} naik; lolos bila n ≥ 30 & ≥ 58%"))
    st = _sinyal_trader()
    if st:
        rows.append(st)
    rows.sort(key=lambda r: (r["status"] == "tidak lolos", -r["wr"]))    # yang tidak lolos di akhir grup
    return rows


def _sinyal_trader() -> dict | None:
    """Ringkasan uji 🧪 sinyal trader (research/sinyal_trader.py) bila sudah ada."""
    p = ROOT / "data" / "research" / "eksternal" / "copy_multi" / "sinyal_trader_ringkas.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return _row("info" if d.get("status") != "dikirim" else "sinyal", "🧪 Sinyal trader (copy trader WR tinggi, 4 platform)",
                {"n": d["n"], "wr": d["wr"], "avg": d["avg"], "periode": d["periode"]}, satuan="%",
                status=d.get("status", "kandidat"), catatan=d.get("catatan", ""))


def filter_() -> list[dict]:
    return [
        {"grup": "filter", "label": "⏸️ Jeda XAU 60 jam sebelum NFP/CPI/Fed", "status": "dikirim",
         "catatan": "sejak Okt 2021 PF 1,56 → 1,96, WR 62,4 → 65,1%; s.d. 2021 PF 1,35 → 1,62"},
        {"grup": "filter", "label": "BTC: lewati funding ramai & September, konf dimatikan", "status": "dikirim",
         "catatan": "konsisten di kedua periode (docs/RISET_DATA_EKSTERNAL.md, VERIFIKASI.md)"},
        {"grup": "filter", "label": "👥 Saringan copy trader", "status": "info",
         "catatan": "menekan rugi/akun hancur/DD; profit tidak lebih tinggi dari indeks"},
    ]


def main() -> dict:
    rows = sinyal() + spot() + info() + filter_()
    rank = 0
    for r in rows:
        if r["grup"] in ("sinyal", "spot", "info"):
            rank += 1
            r["peringkat"] = rank
    out = {"dibuat": pd.Timestamp.now("UTC").strftime("%Y-%m-%d"),
           "keterangan": "Sinyal: profit rata-rata per sinyal dalam R (1R = jarak SL) setelah spread, urut profit lalu WR. "
                         "Spot: % per trade. Info: akurasi tebakan (bukan profit). Periode BARU = Okt 2021–2026, "
                         "'lama' = sebelum Okt 2021. Hasil historis, bukan jaminan.",
           "daftar": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for r in rows:
        avg = "" if r.get("avg") is None else f"{r['avg']:+.3f}{'R' if r['satuan'] == 'R' else '%'}"
        print(f"{r.get('peringkat', '-'):>3} [{r['grup']:6}] {r['label'][:58]:58} WR {r.get('wr', '-')!s:>5} {avg:>9} "
              f"n {r.get('n', '-')!s:>5} {r['status']}")
    return out


if __name__ == "__main__":
    main()
