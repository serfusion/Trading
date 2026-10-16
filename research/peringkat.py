"""📊 Peringkat semua sinyal & label aplikasi dari hasil TERUJI — python -m research.peringkat

Permintaan pengguna 8 Okt 2026: "semua teorimu WR dan profit tinggi diperingkatkan pada (i) info sinyal, mulai dari XAU,
BTC, ⚡⭐🥈🥉💎🌊🔄🎯🧪 dll". Menulis cloud/api/peringkat.json (dikirim bersama riwayat.json lewat GET /api/chat?riwayat=1,
ditampilkan di tombol ⓘ aplikasi).

Sumber angka (periode BARU = Okt 2021–2026 kecuali disebut lain):
- XAU/BTC per peringkat ⚡/🥈/🥉/biasa & lapisan 🔁: replay kode cloud live (data/research/eksternal/verifikasi/
  cloud_XAU.csv dengan ⏸️ jeda 60 jam, cloud_BTC.csv), R bersih setelah spread asli Exness (research.verifikasi.net).
- ETH: cloud/api/riwayat.json; DOGE/ADA: cloud_DOGE_tambahan.csv / cloud_ADA_tambahan.csv (replay, R riset).
- 🎯 WR tinggi (lapisan BTC volatil): _core.WR_TINGGI; 🌊 ikut arus: _arus.RULES; 📰 sinyal setelah berita:
  sinyal_berita.json; Gap pekan forex: riwayat.json "GAP"; 💎 spot: spot_model.json "teruji"; 🔗 _pulih.TERUJI.
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
    t = _j("spot_model.json")["teruji"]
    b = t["baru"]
    return [_row("spot", "💎 Spot Binance (peluang naik +3% ≤ 10 hari; 3 merah / model)",
                 {"n": b["n"], "wr": b["wr"], "avg": b["avg"]}, satuan="%",
                 lama={"n": t["lama"]["n"], "wr": t["lama"]["wr"], "avg": t["lama"]["avg"]},
                 catatan=f"masuk acak {t['dasar_baru']}% • kalah rata-rata {b['kalah']}%, terburuk {b['terburuk']}%"),
            _pulih_row()]


def _pulih_row() -> dict:
    """🔗 emas jatuh dalam lalu pulih → keranjang kripto 48 jam (cloud/api/_pulih.py, docs/XAU_KRIPTO.md)."""
    sys.path.insert(0, str(API))
    import _pulih
    t = _pulih.TERUJI
    return _row("spot", "🔗 Emas pulih → beli keranjang kripto, tahan 48 jam",
                {"n": t["baru"][0], "wr": float(t["baru"][1]), "avg": t["baru"][2]}, satuan="%",
                lama={"n": t["lama"][0], "wr": float(t["lama"][1]), "avg": t["lama"][2]},
                catatan=f"beli acak saat emas & BTC searah {t['dasar_baru'][1]:+.1f}% • terburuk {t['terburuk']:.0f}% • "
                        "2025 −0,5% • aturan korelasi ditemukan setelah melihat 2026")


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


def berita() -> list[dict]:
    """📰 Aturan berita yang DIPAKAI aplikasi sekarang (15 Okt 2026, pengguna: "rangkumkan dari semua informasi") — angka
    PER ARAH tebakan dari JSON yang sama dengan cloud (cpi_detik, ppi_wti, pra_aset per_arah, live_tingkat, rilis_gabung,
    keterkaitan). Dulu ⓘ hanya memuat model "1 jam" yang bukan arah utama lagi."""
    sys.path.insert(0, str(API))
    import _pra_aset
    rows = []
    sr = ((_j("cpi_detik.json").get("uji") or {}).get("saring")) or {}
    if sr:
        k, n = sr.get("naik_2024") or [0, 0]
        lm = sr.get("lemah") or {}
        rows.append(_row("info", "📰 CPI sebelum rilis (konsensus indeks / Kalshi, tersaring) → arah emas detik 2",
                         {"n": sr["n_rilis"], "wr": sr["semua"], "avg": None, "periode": "2016–2026"},
                         satuan="akurasi", status="dikirim", lama={"wr": sr.get("lama")},
                         catatan=(f"sejak Okt 2021 {sr['baru']:.0f}%, 2024+ {sr['s2024']:.0f}% (NAIK {k}/{n}); tebakan TURUN "
                                  f"saat emas tren naik = ⚠️ lemah {lm.get('semua', 0):.0f}% ({lm.get('n_rilis')} rilis)")
                         .replace(".", ",")))
    pw = ((_j("ppi_wti.json").get("cpi_ppi") or {}).get("per_arah")) or {}
    for arah, kata in (("naik", "minyak turun → emas NAIK"), ("turun", "minyak naik → emas TURUN")):
        x = pw.get(arah) or {}
        if x:
            st = "dikirim" if x["semua"]["persen"] >= 60 else "lemah"
            rows.append(_row("info", f"📰 PPI sebelum rilis: {kata} (lonjakan menit 1)",
                             {"n": x["semua"]["n"], "wr": x["semua"]["persen"], "avg": None, "periode": "2016–2026"},
                             satuan="akurasi", status=st, lama={"wr": x["lama"]["persen"]},
                             catatan=(f"sejak Okt 2021 {x['baru']['persen']:.0f}%; setelah CPI inti bulan sama: angka per "
                                      "arah situasi (searah/sesuai/berlawanan), berlawanan → ≈ 50:50").replace(".", ",")))
    for kunci, label, arah in (("ISM Jasa • berbalik", "📰 ISM Jasa: kejutan lalu berbalik → emas TURUN", "turun"),
                               ("ISM Jasa • berbalik", "📰 ISM Jasa: kejutan lalu berbalik → emas NAIK", "naik"),
                               ("Unemployment Rate|PK5", "📰 NFP: kalender survei BLS → emas NAIK", "naik"),
                               ("Unemployment Rate|PK5", "📰 NFP: kalender survei BLS → emas TURUN", "turun")):
        st = _pra_aset.per_arah(kunci, arah)
        if st:
            status = {"teruji": "dikirim"}.get(_pra_aset.status_arah(st), "lemah")
            rows.append(_row("info", label + " (detik 2–10)", {"n": st["n"], "wr": round(st["benar"], 1), "avg": None,
                                                                 "periode": "2010–2026"},
                             satuan="akurasi", status=status, lama={"wr": None if st.get("lama") is None else round(st["lama"])},
                             catatan=(f"sejak Okt 2021 {st['baru']:.0f}%" if st.get("baru") is not None else "")
                             + (f" • pembanding selalu-{arah.upper()} {st['dasar']:.0f}%" if st.get("dasar") is not None else "")))
    lt = (_j("live_tingkat.json").get("grup") or {})
    s = ((lt.get("SEMUA") or {}).get("tingkat") or {}).get("0.5") or {}
    if s:
        per = " • ".join(f"{g} {((lt.get(g) or {}).get('tingkat') or {}).get('0.5', {}).get('d5', '-')}%"
                         for g in ("CPI", "PPI", "NFP", "FOMC", "ISM", "RETAIL"))
        rows.append(_row("info", "⚡ LIVE setelah rilis: gerak emas detik 2 ≥ $0,50 → arah bertahan s/d detik 5",
                         {"n": s["n"], "wr": float(s["d5"]), "avg": None, "periode": "2016–2026"}, satuan="akurasi",
                         status="dikirim", lama={"wr": s.get("d5_lama")},
                         catatan=f"menit 1 {s.get('m1')}% • per berita: {per} • masuk SETELAH detik 2 rata-rata rugi "
                                 "kecuali gerak ≥ $2 (spread & telat)"))
    # 📍 15 Okt 2026 (pengguna: "entry 1 detik sebelum release, bertahan 1 detik hingga 1–3 menit"): masuk t−1 searah tebakan
    # (spread asli Exness, research/masuk_pra.py) + keputusan tahan/tutup di detik 2 untuk posisi apa pun
    mp = _j("masuk_pra.json") if (API / "masuk_pra.json").exists() else {}
    for g, arah in (("CPI", "naik"), ("CPI", "turun"), ("PPI", "naik"), ("PPI", "turun")):
        x = ((mp.get("t1") or {}).get(g) or {}).get(arah)
        if not x:
            continue
        w60, r60 = x["H"]["60"]
        lama, baru = x.get("lama") or [None, None, 0], x.get("baru") or [None, None, 0]
        rows.append(_row("info", f"📍 Masuk 1 dtk sebelum {g} searah tebakan {arah.upper()}, tahan 1 mnt (lot biasa)",
                         {"n": x["n"], "wr": float(w60), "avg": r60, "periode": "2016–2026"}, satuan="$/oz",
                         status="kandidat" if w60 >= 55 and r60 >= 0.2 else "lemah", lama={"wr": lama[0], "avg": lama[1]},
                         catatan=(f"sejak Okt 2021 {baru[0]}% ({baru[1]:+.2f} $/oz) • tutup di detik 1 {x['H']['1'][0]}% • "
                                  "spread asli Exness saat berita").replace(".", ",")))
    sp = (((mp.get("posisi") or {}).get("SEMUA") or {}).get("2") or {})
    s5, l5 = sp.get("s|0.5"), sp.get("l|0.5")
    if s5 and l5:
        rows.append(_row("info", "📍 Posisi t−1, emas detik 2 ≥ $0,50 SEARAH posisi → tahan 1 mnt",
                         {"n": s5["n"], "wr": float(s5["60"][0]), "avg": s5["60"][1], "periode": "2016–2026"}, satuan="$/oz",
                         status="dikirim", lama={"wr": (s5.get("wr60") or [None])[0]},
                         catatan=(f"sejak Okt 2021 {(s5.get('wr60') or [None, None])[1]}% • 30 dtk {s5['30'][0]}% • 3 mnt "
                                  f"{s5['180'][0]}% • BERLAWANAN: ditahan 1 mnt hanya {l5['60'][0]}% balik untung "
                                  f"(rata-rata {l5['60'][1]:+.2f} vs tutup detik 3 {l5['tutup'][1]:+.2f} $/oz) → tutup")
                         .replace(".", ",")))
    kf = (_j("rilis_gabung.json").get("konflik") or {})
    x = kf.get("Non-Farm Employment Change|Unemployment Rate") or {}
    if x:
        rows.append(_row("info", "🔗 Rilis bersamaan berlawanan: emas ikut NFP, bukan pengangguran (menit 1)",
                         {"n": x["n"], "wr": x["m1"], "avg": None, "periode": "2010–2026"}, satuan="akurasi",
                         status="dikirim", lama={"wr": x.get("lama")},
                         catatan=(f"sejak Okt 2021 {x.get('baru'):.0f}% • NFP vs upah sejak 2021 50% → ≈ 50:50 • Retail vs "
                                  "PPI 67% (12 rilis) • CPI inti vs tahunan 54% → ≈ 50:50 (research/rilis_gabung.py)")
                         .replace(".", ",")))
    # 🧩 16 Okt 2026: dokumen "konfluensi_85" unggahan pengguna (klaim 77–88%) diuji data asli — semua rezim digabung
    k85 = _j("konfluensi_85.json") if (API / "konfluensi_85.json").exists() else {}
    va = (k85.get("varian") or {}).get("A_berita") or {}
    rz = [o for nm, o in va.items() if nm.startswith(("KONFLUENSI", "SAPUAN")) and isinstance(o, dict) and o.get("n")]
    if rz:
        n = sum(o["n"] for o in rz)
        hit = lambda kunci, nk: sum(o[nk] * o.get(kunci, 0) / 100 for o in rz)  # noqa: E731
        nl, nb = sum(o["n_lama"] for o in rz), sum(o["n_baru"] for o in rz)
        lolos = [nm for nm, o in va.items() if isinstance(o, dict) and o.get("status") == "teruji"]
        rows.append(_row("info", "🧩 Dokumen konfluensi 5 metode (semua rezim) → arah emas detik 3",
                         {"n": n, "wr": round(hit("d3", "n") / n * 100, 1), "avg": None, "periode": k85.get("tahun", "2016–2026")},
                         satuan="akurasi", status="dikirim" if lolos else "tidak lolos",
                         lama={"wr": round(hit("d3_lama", "n_lama") / nl * 100, 1) if nl else None},
                         catatan=(f"sejak Okt 2021 {hit('d3_baru', 'n_baru') / nb * 100:.0f}% • klaim dokumen 77–88% • rezim "
                                  f"lolos: {len(lolos)} dari 6 • tampil sebagai info 🧩 di detail baris XAU, arah utama tidak "
                                  "diubah (research/konfluensi_85.py)" if nb else "")))
    kt = _j("keterkaitan.json") if (API / "keterkaitan.json").exists() else {}
    if kt.get("tampil"):
        terbaik = max(({**r, "B": b} for b, v in kt["tampil"].items() for r in v if r.get("status_emas") != "≈ acak"),
                      key=lambda r: r.get("emas_wf") or 0, default=None)
        if terbaik:
            rows.append(_row("info", "🔗 Keterkaitan berita sebelumnya → angka berita berikutnya (info)",
                             {"n": terbaik["n_emas_wf"], "wr": terbaik["emas_wf"], "avg": None, "periode": "2010–2026"},
                             satuan="akurasi", status="info",
                             catatan=(f"angka ikut 58–72% tetapi arah emas paling tinggi {terbaik['emas_wf']:.0f}% "
                                      f"({terbaik['A']} → {terbaik['B']}); emas ±20% + 60% × angka tertebak "
                                      "(research/keterkaitan.py)").replace(".", ",")))
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
    rows = sinyal() + spot() + sorted(info() + berita(), key=lambda r: (r["status"] == "tidak lolos", -r["wr"])) \
        + filter_()
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
