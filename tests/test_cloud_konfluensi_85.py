"""🧩 Dokumen "ARSITEKTUR konfluensi_85" (unggahan pengguna 16 Okt 2026) di cloud (_konfluensi_85.py) — dengan ANGKA UJI ASLI.

Tes dokumen meminta PPI 15 Okt → "▼ TURUN 86% TIER 85%+" dan CPI → "▲ NAIK 88%". Angka itu tidak pernah dihitung dari data;
research/konfluensi_85.py (tick Exness 1.627 rilis) menunjukkan tak satu rezim pun lolos. Tes di sini memastikan: kelima vektor
dihitung live dengan definisi riset, poin 🧩/🧪 memakai angka konfluensi_85.json, dan arah/persen utama TIDAK ditimpa kecuali
rezim berstatus "teruji" (gerbang dokumen bagian 4)."""
import copy
import itertools
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cloud" / "api"))

import _core  # noqa: E402
import _konfluensi_85 as K  # noqa: E402
import _masuk_pra  # noqa: E402
import _pra_aset  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 10, 15, 12, 30, tzinfo=UTC)          # PPI + Retail Sales 15 Okt 2026 (19:30 WIB)


def kal(t0, *judul_f_p):
    return [{"title": j, "group": None, "time": t0.isoformat(), "forecast": f, "previous": p, "released": False}
            for j, f, p in judul_f_p]


def tren_tetap(harga, ema, atr):
    return lambda sisa: {"g4": 5.0, "harga": harga, "acuan": harga - 5, "at": "2026-10-15T11:00:00Z", "ema16": ema,
                         "atr20": atr}


def ppi_15okt():
    """Kasus contoh dokumen: PPI 0,6% vs 0,4% + Retail Sales bersamaan, PPI ← minyak panas (TURUN), emas di pucuk."""
    ps = {"title": "PPI m/m", "nama": "PPI", "time": T0.isoformat(), "arah": "turun", "persen": 58, "status": "lemah",
          "sisa": "1 jam lagi", "teks": "PPI ▼ TURUN 58% (1–10 dtk) ⚠️ • 1 jam lagi",
          "poin": ["⚠️ Belum terbukti: 58%", "👥 Orang: survei 45% naik"], "lanjut": {"posisi": {"g": "PPI"}}}
    kartu = [{"title": t, "time": T0.isoformat(), "arah_detik": {"arah": "turun", "persen": 58, "status": "lemah"}}
             for t in ("PPI m/m", "Core PPI m/m", "Retail Sales m/m")]
    prep = {"berita": kartu, "pra_satu": ps,
            "pra_daftar": [{"title": "PPI m/m", "time": T0.isoformat(), "arah": "turun", "persen": 58, "status": "lemah",
                            "dasar": "Minyak WTI bulan acuan"}]}
    calendar = kal(T0, ("PPI m/m", "0.6%", "0.4%"), ("Core PPI m/m", "0.3%", "0.2%"), ("Retail Sales m/m", "0.3%", "1.2%"),
                   ("Core Retail Sales m/m", "0.3%", "1.4%"))
    return prep, calendar


def test_json_hasil_uji_asli_bukan_angka_dokumen():
    d = K.DATA
    assert d["sumber"] == "research/konfluensi_85.py" and d["n_rilis"] >= 1500
    for var in ("A_berita", "B_kelompok"):
        for rz, klaim in K.KLAIM.items():
            o = d["varian"][var][rz]
            assert o["status"] in ("teruji", "belum terbukti", "tidak lolos", "tidak pernah terjadi")
            if o.get("n"):
                assert o["klaim_dokumen"] == klaim and o["d3"] != klaim     # angka uji, bukan salinan klaim dokumen
            if o["status"] == "teruji":                                    # standar dokumen sendiri + LAMA & BARU
                assert o["d3"] >= 75 and o["wilson_d3"] >= 70 and o["p_acak_rilis"] <= 0.01
                assert o["n_lama"] >= 5 and o["n_baru"] >= 5
    for ev in ("PPI m/m", "CPI m/m", "Non-Farm Employment Change", "Retail Sales m/m"):
        assert d["mad"][ev]["mad"] > 0


def test_rezim_sama_dengan_riset():
    from research.konfluensi_85 import ARAH, rezim as rezim_riset
    assert K.ARAH == {k: "naik" if v > 0 else "turun" for k, v in ARAH.items()}
    for a, b, c, e in itertools.product((-1.0, 0.0, 1.0), repeat=4):
        for ko in (True, False):
            assert K.rezim(a, b, c, e, ko)[0] == rezim_riset(a, b, c, e, ko)


def test_vektor_live_definisi_riset():
    mad = K.DATA["mad"]
    t = T0.isoformat()
    nfp = K.palang("NFP", kal(T0, ("Non-Farm Employment Change", "120K", "50K")))
    assert nfp["z"] == round(70000 / mad["Non-Farm Employment Change"]["mad"], 2) and nfp["v"] == 1.0
    klaim = K.palang("CLAIMS", kal(T0, ("Unemployment Claims", "240K", "200K")))
    assert klaim["z"] > 0.6 and klaim["v"] == -1.0                       # pengangguran/klaim dibalik
    assert K.palang("PPI", kal(T0, ("PPI m/m", "", "0.4%"))) == {"v": 0.0, "ada": False, "judul": "PPI m/m"}
    assert K.palang("JOLTS", []) is None
    kk = lambda atas, bawah: [{"title": "CPI m/m", "time": t, "kalshi": {"atas": atas, "bawah": bawah}}]  # noqa: E731
    assert K.kalshi("CPI", kk(0.70, 0.10))["v"] == -1.0                   # di atas perkiraan ≥ 65% → emas turun
    assert K.kalshi("CPI", kk(0.20, 0.66))["v"] == 1.0
    assert K.kalshi("CPI", kk(0.30, 0.20))["v"] == 1.0                    # di bawah ATAU sama ≥ 65%
    assert K.kalshi("CPI", kk(0.50, 0.40))["v"] == 0.0
    assert K.kalshi("CPI", [])["ada"] is False and K.kalshi("PPI", []) is None
    assert K.sapuan({"harga": 4108, "ema16": 4100, "atr20": 10})["v"] == -1.0     # D +0,8: pucuk → disapu turun
    assert K.sapuan({"harga": 4092, "ema16": 4100, "atr20": 10})["v"] == 1.0
    assert K.sapuan({"harga": 4105, "ema16": 4100, "atr20": 10})["v"] == 0.0
    assert K.sapuan({"g4": 5.0, "harga": 4105}) is None                   # cache lama tanpa EMA/ATR
    ps = {"time": t, "arah": "naik"}
    assert K.petunjuk(ps, {"pra_daftar": [{"time": t, "dasar": "Konsensus indeks"}]})["v"] == 1.0
    assert K.petunjuk(ps, {"pra_daftar": [{"time": t, "dasar": "Tren emas 4 jam (berita tanpa petunjuk)"}]})["v"] == 0.0
    assert K.petunjuk({"time": t, "arah": None}, {})["v"] == 0.0


def test_ema_atr_m15_sama_dengan_pandas():
    pd = pytest.importorskip("pandas")
    now = datetime(2026, 10, 15, 12, 7, tzinfo=UTC)
    bars = [_core.Bar(now - timedelta(minutes=7 + 15 * i), 4000 + (i % 7) * 1.3, 4003 + (i % 5), 3997 - (i % 3),
                      4000 + ((i * 3) % 11) * 0.9) for i in range(63, -1, -1)]
    bars.append(_core.Bar(now - timedelta(minutes=7) + timedelta(minutes=15), 1, 9999, 0, 9999))   # belum tutup: diabaikan
    bars.sort(key=lambda b: b.t)
    got = _pra_aset.ema_atr_m15(bars, now)
    tutup = [b for b in bars if b.t + timedelta(minutes=15) <= now]
    c = pd.Series([b.c for b in tutup])
    h, lo = pd.Series([b.h for b in tutup]), pd.Series([b.l for b in tutup])
    tr = pd.concat([h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    assert got["ema16"] == round(float(c.ewm(span=16, adjust=False).mean().iloc[-1]), 3)
    assert got["atr20"] == round(float(tr.iloc[1:].rolling(20).mean().iloc[-1]), 3)
    assert _pra_aset.ema_atr_m15(bars[:15], now) == {}
    t = _pra_aset.hitung_tren(bars[:-1], now)                              # tren 4 jam tetap sama + EMA/ATR ikut cache
    assert t["g4"] and t["ema16"] == got["ema16"]


def test_ppi_15_okt_contoh_dokumen_tidak_menimpa_arah():
    prep, calendar = ppi_15okt()
    asli = copy.deepcopy(prep)
    K.attach(prep, T0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    ps, k = prep["pra_satu"], prep["pra_satu"]["konfluensi"]
    # MAD asli PPI 12 rilis terakhir (0,4) → Z (0,6 − 0,4)/0,4 = 0,5 < 0,6: palang netral (dokumen memakai MAD karangan 0,15)
    assert k["vektor"]["palang"]["v"] == 0.0 and k["vektor"]["palang"]["z"] == round(0.2 / K.DATA["mad"]["PPI m/m"]["mad"], 2)
    assert k["vektor"]["petunjuk"]["v"] == -1.0 and k["vektor"]["sapuan"]["v"] == -1.0     # D = 26/18 = +1,4 → pucuk
    assert k["bersamaan"] is True and k["n_berita"] == 4 and k["n_kelompok"] == 2
    o = K.DATA["varian"]["A_berita"][k["rezim"]]
    assert k["rezim"] == "KONFLUENSI_MENENGAH_TURUN" and k["uji"] == o and k["timpa"] is False
    for kunci in ("arah", "persen", "status", "teks", "lanjut"):           # arah utama, persen & ⚡LIVE posisi tidak berubah
        assert ps[kunci] == asli["pra_satu"][kunci]
    assert prep["berita"] == asli["berita"] and prep["pra_daftar"] == asli["pra_daftar"]
    pz = [p for p in ps["poin"] if p.startswith("🧩")]
    pu = [p for p in ps["poin"] if p.startswith("🧪")]
    assert len(pz) == 1 and len(pu) == 1
    assert "palang netral (Z +0,5)" in pz[0] and "sapuan ▼ (D +1,4)" in pz[0] and "bersamaan ya (4 berita)" in pz[0]
    assert f"diuji {o['n']} rilis" in pu[0] and "klaim dokumen 76,9%" in pu[0] and "arah utama tetap" in pu[0]
    assert ps["poin"].index(pz[0]) < ps["poin"].index("👥 Orang: survei 45% naik")
    assert ps["bukti"] == "\n".join("• " + x for x in ps["poin"])
    K.attach(prep, T0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    assert sum(p.startswith(("🧩", "🧪")) for p in prep["pra_satu"]["poin"]) == 2     # GET berulang tidak menggandakan
    _masuk_pra.attach(prep)                                               # 📍 masuk t−1 tampil SEBELUM 🧩
    poin = prep["pra_satu"]["poin"]
    i_pin = next(i for i, p in enumerate(poin) if p.startswith("📍"))
    assert i_pin < next(i for i, p in enumerate(poin) if p.startswith("🧩"))


def test_cpi_contoh_dokumen_penuh_naik_tidak_menimpa():
    t0 = datetime(2026, 11, 10, 13, 30, tzinfo=UTC)
    t = t0.isoformat()
    ps = {"title": "CPI m/m", "nama": "CPI", "time": t, "arah": "naik", "persen": 52, "status": "lemah", "sisa": "2 jam lagi",
          "teks": "CPI ▲ NAIK 52% (detik 2) ⚠️ • 2 jam lagi", "poin": []}
    prep = {"berita": [{"title": "CPI m/m", "time": t, "kalshi": {"atas": 0.20, "bawah": 0.70}}], "pra_satu": ps,
            "pra_daftar": [{"time": t, "dasar": "Konsensus indeks & Kalshi"}]}
    calendar = kal(t0, ("CPI m/m", "0.5%", "0.2%"), ("Core CPI m/m", "0.3%", "0.3%"), ("CPI y/y", "3.0%", "2.9%"))
    K.attach(prep, t0 - timedelta(hours=2), calendar=calendar, tren=tren_tetap(4080.0, 4100.0, 20.0))
    k = prep["pra_satu"]["konfluensi"]
    assert [k["vektor"][x]["v"] for x in ("palang", "kalshi", "petunjuk", "sapuan")] == [1.0, 1.0, 1.0, 1.0]
    # CPI selalu terbit bersama core & y/y → varian A dokumen = "bersamaan" → bukan PENUH; varian kelompok (B) = PENUH NAIK
    assert k["rezim"] == "KONFLUENSI_MENENGAH_NAIK" and k["varian_b"]["rezim"] == "KONFLUENSI_PENUH_NAIK"
    assert k["timpa"] is False and prep["pra_satu"]["persen"] == 52 and prep["pra_satu"]["status"] == "lemah"
    ob = K.DATA["varian"]["B_kelompok"]["KONFLUENSI_PENUH_NAIK"]
    pu = next(p for p in prep["pra_satu"]["poin"] if p.startswith("🧪"))
    assert f"varian kelompok: PENUH NAIK {ob['d3']:.0f}% ({ob['n']} rilis, {ob['status']})" in pu


def test_gerbang_timpa_hanya_bila_rezim_teruji(monkeypatch):
    data = copy.deepcopy(K.DATA)
    o = data["varian"]["A_berita"]["KONFLUENSI_MENENGAH_TURUN"]
    o.update(status="belum terbukti", d3=80.0, arah="turun")
    monkeypatch.setattr(K, "DATA", data)
    prep, calendar = ppi_15okt()
    K.attach(prep, T0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    assert prep["pra_satu"]["persen"] == 58 and prep["pra_satu"]["konfluensi"]["timpa"] is False   # belum terbukti
    o.update(status="teruji")
    prep, calendar = ppi_15okt()
    K.attach(prep, T0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    ps = prep["pra_satu"]
    assert ps["konfluensi"]["timpa"] is True and ps["arah"] == "turun" and ps["persen"] == 80 and ps["status"] == "teruji"
    assert ps["teks"] == "PPI ▼ TURUN 80% (detik 3) ✅ • 1 jam lagi" and ps["lanjut"] == {"posisi": {"g": "PPI"}}
    assert all(c["arah_detik"]["persen"] == 80 and c["arah_detik"]["arah"] == "turun" for c in prep["berita"])
    assert prep["pra_daftar"][0]["persen"] == 80
    assert "✅ teruji, dipakai sebagai arah utama" in next(p for p in ps["poin"] if p.startswith("🧪"))
    assert "berlawanan" not in next(p for p in ps["poin"] if p.startswith("🧩"))
    o.update(d3=56.0)                                                    # teruji tapi < 75% → tetap tidak menimpa
    prep, calendar = ppi_15okt()
    K.attach(prep, T0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    assert prep["pra_satu"]["konfluensi"]["timpa"] is False and prep["pra_satu"]["persen"] == 58


def test_tanpa_rezim_sapuan_belum_waktunya_dan_env_mati(monkeypatch):
    prep, calendar = ppi_15okt()
    prep["pra_satu"].update(arah=None, persen=50, status="acak")
    K.attach(prep, T0 - timedelta(days=2), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    k = prep["pra_satu"]["konfluensi"]
    assert k["rezim"] is None and k["vektor"]["sapuan"] is None and k["sapuan_jendela"] is False
    pz = next(p for p in prep["pra_satu"]["poin"] if p.startswith("🧩"))
    pu = next(p for p in prep["pra_satu"]["poin"] if p.startswith("🧪"))
    assert "sapuan – (dihitung ≤ 6 jam sebelum rilis)" in pz and "tanpa rezim" in pz
    assert "tak satu rezim pun lolos" in pu and "76,9–87,5%" in pu
    prep2, _ = ppi_15okt()
    K.attach(prep2, T0 - timedelta(hours=1), calendar=None, tren=None)  # pekan depan: kalender tidak mencakup
    k2 = prep2["pra_satu"]["konfluensi"]
    assert k2["bersamaan"] is None and "varian_b" not in k2
    assert "bersamaan belum diketahui" in next(p for p in prep2["pra_satu"]["poin"] if p.startswith("🧩"))
    assert "sapuan – (candle belum ada)" in next(p for p in prep2["pra_satu"]["poin"] if p.startswith("🧩"))
    monkeypatch.setenv("KONFLUENSI_85", "0")
    prep3, calendar = ppi_15okt()
    asli = copy.deepcopy(prep3)
    K.attach(prep3, T0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    assert prep3 == asli


def test_rezim_berlawanan_arah_utama_dan_tren_saja_diberi_keterangan():
    t0 = datetime(2026, 11, 10, 13, 30, tzinfo=UTC)
    t = t0.isoformat()
    calendar = kal(t0, ("CPI m/m", "0.5%", "0.2%"), ("Core CPI m/m", "0.3%", "0.3%"))

    def buat(arah, dasar):
        ps = {"title": "CPI m/m", "nama": "CPI", "time": t, "arah": arah, "persen": 60, "status": "lemah", "poin": []}
        return {"berita": [{"title": "CPI m/m", "time": t, "kalshi": {"atas": 0.2, "bawah": 0.7}}], "pra_satu": ps,
                "pra_daftar": [{"time": t, "dasar": dasar}]}
    prep = buat("turun", "Konsensus indeks")                 # palang ▲ + Kalshi ▲ + sapuan ▲ melawan petunjuk ▼ → skor +2,0
    K.attach(prep, t0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4080.0, 4100.0, 20.0))
    k = prep["pra_satu"]["konfluensi"]
    assert k["rezim"] == "KONFLUENSI_MENENGAH_NAIK" and k["skor"] == 2.0 and prep["pra_satu"]["arah"] == "turun"
    pz = next(p for p in prep["pra_satu"]["poin"] if p.startswith("🧩"))
    assert "rezim MENENGAH NAIK (berlawanan dengan arah utama — tidak dipakai)" in pz and "skor +2,0" in pz
    prep = buat("naik", "Tren emas 4 jam (berita tanpa petunjuk)")
    K.attach(prep, t0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4100.0, 4100.4, 20.0))
    pz = next(p for p in prep["pra_satu"]["poin"] if p.startswith("🧩"))
    assert "petunjuk – (hanya tren 4 jam)" in pz and "sapuan netral (D +0,0)" in pz and "berlawanan" not in pz


def test_sejam_kalender_pekan_ini_vs_pekan_depan():
    rabu = datetime(2026, 10, 14, 12, 30, tzinfo=UTC)                   # CPI Rabu (kalender pekan 11–17 Okt)
    cal = kal(rabu, ("CPI m/m", "0.6%", "0.4%"), ("Core CPI m/m", "0.2%", "0.3%"))
    jumat = datetime(2026, 10, 16, 14, 0, tzinfo=UTC)                   # berita sedang setelah berita High terakhir pekan ini
    assert len(K.sejam(cal, rabu)) == 2
    assert K.sejam(cal, jumat) == []                                     # pekan yang sama: memang tidak ada berita High
    assert K.sejam(cal, datetime(2026, 10, 20, 12, 30, tzinfo=UTC)) is None   # pekan depan: tidak diketahui
    assert K.sejam(None, rabu) is None


def test_rezim_sapuan_pola_v_dan_fase_hanya_bila_teruji(monkeypatch):
    """Dokumen: SAPUAN PUCUK = turun detik 1–3 lalu V naik (klaim 85,7%). Angka V asli ditampilkan; saran TP kilat detik 3 hanya
    bila rezim teruji DAN pola V ≥ 65% (dokumen bagian 4)."""
    t0 = T0
    prep, calendar = ppi_15okt()
    calendar[0]["forecast"] = "1.2%"                                      # Z (1,2 − 0,4)/MAD ≥ 0,6 → palang ▲
    K.attach(prep, t0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    k = prep["pra_satu"]["konfluensi"]
    assert k["rezim"] == "SAPUAN_PUCUK_V_SHAPE_NAIK" and k["timpa"] is False
    o = K.DATA["varian"]["A_berita"]["SAPUAN_PUCUK_V_SHAPE_NAIK"]
    pu = next(p for p in prep["pra_satu"]["poin"] if p.startswith("🧪"))
    assert f"pola V (searah detik 3 lalu berbalik di detik 10) {o['v_shape']:.0f}% vs klaim 85,7%" in pu
    assert "SAPUAN PUCUK (turun → V naik)" in pu and not any(p.startswith("⚡ Fase") for p in prep["pra_satu"]["poin"])
    data = copy.deepcopy(K.DATA)
    data["varian"]["A_berita"]["SAPUAN_PUCUK_V_SHAPE_NAIK"].update(status="teruji", d3=86.0, v_shape=70.0, arah="turun", n=40)
    monkeypatch.setattr(K, "DATA", data)
    prep, calendar = ppi_15okt()
    calendar[0]["forecast"] = "1.2%"
    for _ in range(2):                                                   # GET berulang: poin fase tidak dobel
        K.attach(prep, t0 - timedelta(hours=1), calendar=calendar, tren=tren_tetap(4156.0, 4130.0, 18.0))
    fase = [p for p in prep["pra_satu"]["poin"] if p.startswith("⚡ Fase")]
    assert len(fase) == 1 and "pola V ▲ NAIK 70%" in fase[0] and prep["pra_satu"]["persen"] == 86
