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


def simulasi(bars_1h: list[Bar], t_listing: float, p0: float, cfg: dict, biaya: float = 0.004,
             sl_mode: str = "stop") -> dict | None:
    """Satu listing, candle 1 jam — semantik research/listing_dip_porto.trade (koreksi 8 Okt 2026).

    Candle ENTRY ikut diperiksa (simulator lama melewatkannya -> BARU tampak +7,1%, sebenarnya -0,7%):
      sl_mode "stop":  SL = order stop; di candle entry low <= SL pasti SETELAH terisi -> SL; lalu close >= TP -> TP.
                       Candle berikutnya: SL dulu bila TP & SL di candle yang sama (konservatif).
      sl_mode "tutup": SL hanya dicek di CLOSE candle 1 jam (jual pasar di close); TP limit lebih dulu.
    Kembalikan trade {masuk, keluar, ret (bersih biaya), alasan, t_masuk, t_keluar} atau None."""
    turun, tp_, sl_ = cfg["turun"], cfg["tp"], cfg["sl"]
    w_akhir = t_listing + 3600 + cfg["hari_jendela"] * HARI     # jendela dihitung dari akhir jam pertama (riset)
    lim = harga_limit(p0, turun)
    bars = [b for b in bars_1h if b.t >= t_listing + 3600]

    def hasil(x, alasan, b0, b1):
        return {"masuk": e, "keluar": x, "ret": x / e - 1 - biaya, "alasan": alasan, "t_masuk": b0.t, "t_keluar": b1.t}

    for i, b in enumerate(bars):
        if b.t >= w_akhir:
            return None
        e = isi_limit(lim, b)
        if e is None:
            continue
        tp, sl = e * (1 + tp_), (e * (1 - sl_) if sl_ else -1.0)
        if sl_mode == "tutup":
            if b.c >= tp:
                return hasil(tp, "TP", b, b)
            if sl_ and b.c <= sl:
                return hasil(b.c, "SL", b, b)
        else:
            if sl_ and b.l <= sl:
                return hasil(sl, "SL", b, b)
            if b.c >= tp:
                return hasil(tp, "TP", b, b)
        akhir = b.t + cfg["hari_maks"] * HARI
        sisa = [x for x in bars[i + 1:] if x.t < akhir]
        for x in sisa:
            if sl_mode == "tutup":
                if x.h >= tp:
                    return hasil(max(x.o, tp), "TP", b, x)
                if sl_ and x.c <= sl:
                    return hasil(x.c, "SL", b, x)
            else:
                k = keluar_bar(e, tp_, sl_, x)
                if k:
                    return hasil(k[0], k[1], b, x)
        if not sisa:
            return hasil(b.c, "WAKTU", b, b)
        return hasil(sisa[-1].c, "WAKTU", b, sisa[-1])
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
            if self.m.broker.live and not self.cfg.get("izinkan_live", False):
                d.update(status="sinyal", catatan="live: hanya kabar (strategi belum lolos uji BARU)")
                from ..mesin import px
                self.m.kabar(f"🎯 <b>SINYAL {sym}</b> harga {px(p)} ≤ {px(d['limit'])} (−{self.cfg['turun'] * 100:.0f}% dari P0). "
                             f"TIDAK dieksekusi: listing dip belum lolos uji sejak 2021 (lihat tutorial). "
                             f"Untuk mengizinkan: listing_dip.izinkan_live: true (risiko sendiri).")
                continue
            pos = self.m.buka(self.nama, sym, d["base"], p, usd_, self.cfg["tp"], self.cfg["sl"],
                              self.cfg["hari_maks"], limit=d["limit"],
                              info={"p0": d["p0"], "sl_close_jam": bool(self.cfg.get("sl_close_jam", True))},
                              label=self.label)
            if pos:
                d["status"] = "dibeli"
            elif (self.m.gagal_terakhir or "").startswith("bursa:"):
                d.update(status="lewat", catatan=self.m.gagal_terakhir)      # mis. koin tidak ada di bursa pengguna

    def status_teks(self) -> str:
        n = {}
        for d in self.L.values():
            n[d["status"]] = n.get(d["status"], 0) + 1
        live = " (live: hanya kabar)" if self.m.broker.live and not self.cfg.get("izinkan_live") else ""
        return (f"{self.label}{live}: pantau {n.get('pantau', 0)}, tunggu P0 {n.get('menunggu_p0', 0)}, "
                f"dibeli {n.get('dibeli', 0)}, sinyal {n.get('sinyal', 0)}")
