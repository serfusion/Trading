"""🎯 Listing dip: token BARU di Binance yang sudah turun >= 60% dari harga 60 menit pertamanya.

Teruji (research/listing_baru.py, listing_dip_porto.py; docs/SNIPER_TELEGRAM.md): 2018-2026, beli limit P0 x 0,4 dalam 30 hari
pertama, TP +20%, SL -50%, maks 90 hari. Fungsi murni di bawah dipakai BERSAMA oleh mesin live dan replay (paritas).

P0 = rata-rata harga tipikal (h+l+c)/3 berbobot volume USDT pada 60 candle 1 menit pertama (rumus riset yang sama).
"""
from __future__ import annotations

from ..pasar import Bar

HARI = 86400.0


def p0_dari_bar(bars: list[Bar], menit: int = 60) -> float | None:
    w = bars[:menit]
    if len(w) < min(30, menit):
        return None
    q = sum(b.q for b in w)
    if q <= 0:
        return w[-1].c
    return sum((b.h + b.l + b.c) / 3 * b.q for b in w) / q


def harga_limit(p0: float, turun: float) -> float:
    return p0 * (1 - turun)


def isi_limit(limit: float, bar: Bar) -> float | None:
    """Limit beli terisi bila low <= limit; harga isi = min(open, limit) (gap turun = open)."""
    if bar.l <= limit:
        return min(bar.o, limit)
    return None


def keluar_bar(entry: float, tp: float, sl: float, bar: Bar) -> tuple[float, str] | None:
    """SL dicek DULU bila satu candle menyentuh keduanya (konservatif, sama dengan riset)."""
    slp, tpp = entry * (1 - sl), entry * (1 + tp)
    if sl and bar.l <= slp:
        return min(bar.o, slp), "SL"
    if bar.h >= tpp:
        return max(bar.o, tpp), "TP"
    return None


def kecualikan(simbol: str, base: str, t_listing: float) -> str | None:
    """Alasan dilewati (sama dengan riset), atau None."""
    if t_listing >= 1780272000 and base.endswith("B") and len(base) >= 4:   # >= 1 Jun 2026: token saham Binance (TSLAB, ...)
        return "token saham"
    return None


def simulasi(bars_1h: list[Bar], t_listing: float, p0: float, cfg: dict, biaya: float = 0.004) -> dict | None:
    """Satu listing, candle 1 jam (riset). Kembalikan trade {masuk, keluar, ret, alasan, t_masuk, t_keluar} atau None."""
    turun, tp, sl = cfg["turun"], cfg["tp"], cfg["sl"]
    w_akhir = t_listing + 3600 + cfg["hari_jendela"] * HARI     # jendela dihitung dari akhir jam pertama (riset)
    lim = harga_limit(p0, turun)
    bars = [b for b in bars_1h if b.t >= t_listing + 3600]
    for i, b in enumerate(bars):
        if b.t >= w_akhir:
            return None
        e = isi_limit(lim, b)
        if e is None:
            continue
        akhir = b.t + cfg["hari_maks"] * HARI
        sisa = [x for x in bars[i + 1:] if x.t < akhir]
        if not sisa:
            return None
        for x in sisa:
            k = keluar_bar(e, tp, sl, x)
            if k:
                return {"masuk": e, "keluar": k[0], "ret": k[0] / e - 1 - biaya, "alasan": k[1], "t_masuk": b.t,
                        "t_keluar": x.t}
        return {"masuk": e, "keluar": sisa[-1].c, "ret": sisa[-1].c / e - 1 - biaya, "alasan": "WAKTU",
                "t_masuk": b.t, "t_keluar": sisa[-1].t}
    return None


# ====================================================================== bagian live (dipakai mesin)
class ListingDipMesin:
    nama = "listing_dip"
    label = "🎯 Listing dip"

    def __init__(self, mesin):
        self.m = mesin
        self.cfg = mesin.cfg["listing_dip"]

    @property
    def L(self) -> dict:
        return self.m.s["listing"]

    def _antri(self) -> list:
        return self.m.s.setdefault("listing_antri", [])

    def tick_jadwal(self) -> None:
        if not self.m.jatuh_tempo("listing", float(self.m.cfg["jadwal"]["listing_menit"]) * 60):
            return
        self.sinkron_simbol()
        self.isi_waktu_listing(maks=600 if not self.L and len(self._antri()) > 100 else 60)
        self.hitung_p0()

    def sinkron_simbol(self) -> None:
        s = self.m.pasar.simbol_usdt()
        dikenal = set(self.m.s["simbol_dikenal"])
        pertama = not dikenal
        baru = [x for x in s if x not in dikenal]
        for sym in baru:
            self._antri().append({"sym": sym, "base": s[sym]["base"], "baru": not pertama})
        self.m.s["simbol_dikenal"] = sorted(dikenal | set(baru))
        if baru and not pertama and self.cfg.get("kabari_listing_baru", True):
            for sym in baru:
                self.m.kabar(f"🆕 <b>Listing baru Binance: {sym}</b> ({s[sym]['status']}). P0 dihitung "
                             f"{self.cfg['menit_p0']} menit setelah perdagangan mulai; beli otomatis hanya bila harga "
                             f"turun ≥ {self.cfg['turun'] * 100:.0f}% dari P0 dalam {self.cfg['hari_jendela']} hari.")

    def isi_waktu_listing(self, maks: int = 60) -> None:
        """Cari waktu listing (candle 1 menit pertama) bertahap; simpan yang listing <= 30 hari."""
        antri = self._antri()
        now = self.m.now()
        sisa = []
        for k, it in enumerate(antri):
            if k >= maks:
                sisa.append(it)
                continue
            try:
                t0 = self.m.pasar.waktu_listing(it["sym"])
            except Exception:  # noqa: BLE001
                sisa.append(it)
                continue
            if t0 is None:                       # belum diperdagangkan (PRE_TRADING) -> coba lagi nanti
                sisa.append(it)
                continue
            if now - t0 > (self.cfg["hari_jendela"] * 86400 + 3600):
                continue
            alasan = kecualikan(it["sym"], it["base"], t0)
            self.L[it["sym"]] = {"base": it["base"], "t_listing": t0, "p0": None, "limit": None,
                                 "status": "lewat" if alasan else "menunggu_p0", "catatan": alasan or ""}
        self.m.s["listing_antri"] = sisa

    def hitung_p0(self) -> None:
        now = self.m.now()
        for sym, d in self.L.items():
            if d["status"] != "menunggu_p0" or now < d["t_listing"] + self.cfg["menit_p0"] * 60 + 60:
                continue
            bars = self.m.pasar.kline(sym, "1m", start_ms=int(d["t_listing"] * 1000), limit=self.cfg["menit_p0"])
            p0 = p0_dari_bar(bars, self.cfg["menit_p0"])
            if p0 is None:
                continue
            d.update(p0=p0, limit=harga_limit(p0, self.cfg["turun"]), status="pantau")
            batas = d["t_listing"] + 3600 + self.cfg["hari_jendela"] * 86400
            from ..mesin import jam, px
            self.m.kabar(f"🎯 <b>{sym}</b> P0 (VWAP {self.cfg['menit_p0']} mnt) = {px(p0)}. Siap BELI bila ≤ "
                         f"<b>{px(d['limit'])}</b> (−{self.cfg['turun'] * 100:.0f}%) sampai {jam(batas)}. "
                         f"TP +{self.cfg['tp'] * 100:.0f}%, SL −{self.cfg['sl'] * 100:.0f}%, maks {self.cfg['hari_maks']} hari.")

    def tick_harga(self) -> None:
        now = self.m.now()
        for sym, d in self.L.items():
            if d["status"] != "pantau":
                continue
            if now >= d["t_listing"] + 3600 + self.cfg["hari_jendela"] * 86400:
                d["status"] = "kedaluwarsa"
                continue
            p = self.m.harga.get(sym)
            if p is None or p > d["limit"]:
                continue
            # harga <= limit: ukuran dibatasi % modal, batas risiko, dan 0,5% volume 24 jam
            try:
                t24 = self.m.pasar.ticker24().get(sym, {})
            except Exception:  # noqa: BLE001
                t24 = {}
            batas_vol = float(t24.get("q") or 0) * float(self.cfg["maks_persen_volume"]) if t24 else None
            usd_ = self.m.ukuran(float(self.cfg["persen_modal"]), batas_vol)
            alasan = self.m.boleh_buka(self.nama, usd_)
            if alasan:
                if d.get("catatan") != alasan:
                    d["catatan"] = alasan
                    self.m.kabar(f"⏸ {sym} sudah ≤ harga beli tetapi tidak dibeli: {alasan}")
                continue
            if usd_ < 5:
                d["catatan"] = "ukuran < $5 (volume/modal)"
                continue
            pos = self.m.buka(self.nama, sym, d["base"], p, usd_, self.cfg["tp"], self.cfg["sl"],
                              self.cfg["hari_maks"], limit=d["limit"], info={"p0": d["p0"]}, label=self.label)
            if pos:
                d["status"] = "dibeli"
            elif (self.m.gagal_terakhir or "").startswith("bursa:"):
                d.update(status="lewat", catatan=self.m.gagal_terakhir)      # mis. koin tidak ada di bursa pengguna

    def status_teks(self) -> str:
        n = {}
        for d in self.L.values():
            n[d["status"]] = n.get(d["status"], 0) + 1
        return f"{self.label}: pantau {n.get('pantau', 0)}, tunggu P0 {n.get('menunggu_p0', 0)}, dibeli {n.get('dibeli', 0)}"
