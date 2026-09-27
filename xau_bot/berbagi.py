"""Dompet Berbagi: sisihkan profit untuk sedekah/zakat dengan aturan yang jujur, plus rencana tabungan emas.

- `alokasi_berbagi`  : X% dari profit BERSIH yang baru (di atas puncak sebelumnya / high-water mark).
  Setelah periode rugi, kerugian harus tertutup dulu sebelum ada alokasi lagi, jadi tidak ada
  "sedekah dari profit semu" yang kemudian hilang.
- `zakat_mal`        : 2,5% bila harta simpanan >= nisab 85 gram emas dan sudah haul (1 tahun hijriah).
- `rencana_tabungan_emas`: beli emas rutin tanpa leverage (untuk modal kecil / kaum dhuafa lebih aman
  daripada trading berleverage, lihat docs/RISET_GITHUB.md).

Catatan: modul ini alat hitung, bukan fatwa. Untuk kepastian hukum zakat, tanyakan ke BAZNAS/LAZ atau ustadz.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

WIB = "Asia/Jakarta"
NISAB_GRAM = 85.0
TARIF_ZAKAT = 0.025


@dataclass
class Alokasi:
    periode: str
    profit: float          # profit bersih periode ini (boleh negatif)
    kumulatif: float       # profit bersih kumulatif sejak awal
    puncak: float          # high-water mark setelah periode ini
    profit_baru: float     # bagian profit di atas puncak sebelumnya
    alokasi: float         # yang disisihkan untuk berbagi
    total_alokasi: float


def alokasi_berbagi(pnl: pd.Series, persen: float = 10.0, periode: str = "M",
                    puncak_awal: float = 0.0) -> list[Alokasi]:
    """pnl: profit/rugi per trade tertutup (sudah termasuk komisi & swap), index = waktu tutup.

    periode: "W" mingguan, "M" bulanan (kalender WIB). Periode tanpa trade tidak ditampilkan."""
    if not 0 <= persen <= 100:
        raise ValueError("persen harus 0-100")
    if pnl.empty:
        return []
    idx = pd.DatetimeIndex(pnl.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    local = idx.tz_convert(WIB).tz_localize(None)
    per = pnl.groupby(local.to_period(periode)).sum().sort_index()
    out, cum, peak, total = [], 0.0, puncak_awal, 0.0
    for p, x in per.items():
        cum += float(x)
        baru = max(0.0, cum - peak)
        peak = max(peak, cum)
        alok = round(baru * persen / 100, 2)
        total = round(total + alok, 2)
        out.append(Alokasi(str(p), round(float(x), 2), round(cum, 2), round(peak, 2), round(baru, 2), alok, total))
    return out


@dataclass
class Zakat:
    harta: float
    nisab: float
    wajib: bool
    zakat: float
    catatan: str


def zakat_mal(harta: float, harga_emas_per_gram: float, haul: bool = True, hutang_jatuh_tempo: float = 0.0,
              nisab_gram: float = NISAB_GRAM, tarif: float = TARIF_ZAKAT) -> Zakat:
    """Zakat mal atas harta simpanan (tabungan, saldo trading, emas simpanan) setelah dikurangi hutang
    yang jatuh tempo. Wajib bila bersih >= nisab (85 gram emas) dan sudah haul."""
    if harga_emas_per_gram <= 0:
        raise ValueError("harga emas per gram harus > 0")
    bersih = max(0.0, harta - hutang_jatuh_tempo)
    nisab = nisab_gram * harga_emas_per_gram
    if bersih < nisab:
        return Zakat(bersih, nisab, False, 0.0, "Belum mencapai nisab: belum wajib zakat mal (sedekah tetap dianjurkan).")
    if not haul:
        return Zakat(bersih, nisab, False, 0.0, "Sudah nisab tetapi belum haul 1 tahun: catat tanggal mulai nisab.")
    return Zakat(bersih, nisab, True, round(bersih * tarif, 2), f"Wajib zakat {tarif * 100:.1f}% dari harta bersih.")


@dataclass
class RencanaTabungan:
    bulan: int
    total_setor: float
    gram: float
    nilai: dict            # skenario kenaikan harga per tahun -> nilai jual (setelah selisih buyback)


def rencana_tabungan_emas(setoran_per_bulan: float, harga_per_gram: float, bulan: int,
                          kenaikan_tahunan: tuple[float, ...] = (-0.10, 0.0, 0.05, 0.10),
                          selisih_buyback_pct: float = 5.0) -> RencanaTabungan:
    """Beli emas setiap bulan dengan uang tetap. Tanpa leverage: harga turun berarti nilai turun, tetapi
    akun tidak bisa 'habis' seperti trading. Nilai = gram x harga akhir x (1 - selisih buyback).
    Gram dihitung dengan harga skenario 0% (harga sekarang) agar jumlah gram tidak bergantung ramalan."""
    if setoran_per_bulan <= 0 or harga_per_gram <= 0 or bulan <= 0:
        raise ValueError("setoran, harga dan bulan harus > 0")
    nilai = {}
    gram_datar = 0.0
    for g in kenaikan_tahunan:
        gram = 0.0
        for m in range(bulan):
            gram += setoran_per_bulan / (harga_per_gram * (1 + g) ** (m / 12))
        akhir = harga_per_gram * (1 + g) ** (bulan / 12)
        nilai[g] = round(gram * akhir * (1 - selisih_buyback_pct / 100), 0)
        if g == 0.0:
            gram_datar = gram
    if 0.0 not in kenaikan_tahunan:
        gram_datar = setoran_per_bulan * bulan / harga_per_gram
    return RencanaTabungan(bulan, round(setoran_per_bulan * bulan, 0), round(gram_datar, 4), nilai)


def baca_pnl_csv(path: str | Path) -> pd.Series:
    """CSV riwayat trade: kolom waktu (close_time/time/exit_time/waktu) dan profit (pnl/profit/laba)."""
    df = pd.read_csv(path)
    cols = {c.lower().strip(): c for c in df.columns}
    tcol = next((cols[c] for c in ("close_time", "exit_time", "time", "waktu", "tanggal") if c in cols), None)
    pcol = next((cols[c] for c in ("pnl", "profit", "laba", "net") if c in cols), None)
    if tcol is None or pcol is None:
        raise ValueError(f"CSV butuh kolom waktu & profit, ada: {list(df.columns)}")
    t = pd.to_datetime(df[tcol], utc=True)
    return pd.Series(df[pcol].astype(float).to_numpy(), index=t).sort_index()


def rupiah(x: float) -> str:
    return f"Rp{x:,.0f}".replace(",", ".")


def format_alokasi(rows: list[Alokasi], persen: float, mata_uang: str = "USD", kurs: float | None = None) -> str:
    def m(x):
        s = f"{x:+,.2f} {mata_uang}"
        return s + (f" ({rupiah(x * kurs)})" if kurs else "")
    lines = [f"Dompet Berbagi {persen:g}% dari profit bersih baru (high-water mark)"]
    for r in rows:
        tanda = "🟢" if r.alokasi > 0 else ("🔴" if r.profit < 0 else "⚪")
        lines.append(f"{tanda} {r.periode}: profit {m(r.profit)} | kumulatif {m(r.kumulatif)} | "
                     f"sisihkan {m(r.alokasi)}")
    if rows:
        belum = rows[-1].puncak - rows[-1].kumulatif
        lines.append(f"Total untuk berbagi: {m(rows[-1].total_alokasi)}")
        if belum > 0:
            lines.append(f"Masih harus menutup rugi {m(belum)} sebelum ada alokasi berikutnya.")
    return "\n".join(lines)
