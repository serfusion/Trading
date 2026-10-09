"""Keputusan BELI / JUAL satu pasangan: harga eksekusi NYATA (Quoter) vs harga acuan, batas slippage, cek jual-balik.

Aturan (angka bawaan dari riset docs/TOKEN_BARU.md — ubah di konfigurasi):
  BELI  bila harga eksekusi beli <= acuan x (1 - beli_bawah)      [murah dibanding harga wajar]
  JUAL  bila harga eksekusi jual >= acuan x (1 + jual_atas)       [mahal dibanding harga wajar]
        atau posisi terbuka: >= harga masuk x (1 + tp) / <= harga masuk x (1 - sl) / sudah kembali ke acuan
  Slippage = harga eksekusi / harga spot pool - 1 (sudah termasuk fee pool & dampak likuiditas). Bila > max_slippage
  ukuran diperkecil (bagi dua) sampai muat; bila tetap tidak muat -> lewati (likuiditas tipis).
  Cek jual-balik: token yang dibeli dikuotasi dijual kembali; rugi pulang-pergi jauh di atas fee x2 + slippage x2
  -> tanda hook/pajak/honeypot -> lewati.
  untung_beli  = DISKON SATU ARAH (acuan / harga beli - 1 - gas): belum termasuk biaya keluar.
  untung_bersih = perkiraan setelah keluar: jual balik di DEX (acuan x (1 - biaya jual pool saat ini)) atau, untuk token
                  jembatan (tebus_manual), tebus 1:1 dikurangi biaya_tebus. Keputusan BELI memakai untung_bersih.
  tebus_manual: token jembatan kustodian (mis. WETH/CRCL/NVDA•Arc, docs/ARB_BOT.md) — keluar lewat TEBUS manual, jadi
                bot tidak memberi sinyal JUAL DEX untuk posisinya (jual DEX di pool tipis = diskon yang sama).
"""
from __future__ import annotations

from dataclasses import dataclass

from . import acuan
from .dex import Pool, quote, spot


@dataclass
class Pasangan:
    nama: str
    pool: Pool
    token: str            # token yang diperdagangkan (mis. CRCL / WETH)
    quote: str            # alat bayar (USDG / USDC / WETH)
    acuan_token: str      # spesifikasi acuan USD token (acuan.py)
    acuan_quote: str = "tetap:1"
    ukuran_usd: float = 100.0
    min_usd: float = 10.0
    beli_bawah: float = 0.02
    jual_atas: float = 0.02
    max_slippage: float = 0.01
    tp: float = 0.03
    sl: float = 0.05
    biaya_gas_usd: float = 0.05
    luar_jam: bool = False  # izinkan transaksi saat acuan saham tutup (TIDAK disarankan)
    tebus_manual: bool = False  # token jembatan: keluar lewat tebus 1:1 manual, bukan jual DEX
    biaya_tebus: float = 0.01   # biaya jembatan (Arc<->Robinhood 1%, docs/eksternal/hasil_arb_cari.txt A3)


def _dec(p: Pasangan, tok: str) -> int:
    return p.pool.d0 if tok.lower() == p.pool.c0.lower() else p.pool.d1


def harga_spot_token(rpc, p: Pasangan, state_view: str | None) -> float:
    """Harga 1 token dalam satuan quote (spot pool, sebelum fee/slippage)."""
    px, _liq = spot(rpc, p.pool, state_view)
    return px if p.token.lower() == p.pool.c0.lower() else 1 / px


def evaluasi(rpc, p: Pasangan, quoter: str, state_view: str | None = None, posisi: dict | None = None) -> dict:
    ref_tok, ref_q = acuan.harga(p.acuan_token), acuan.harga(p.acuan_quote)
    wajar = ref_tok / ref_q                    # harga wajar token dalam satuan quote
    hidup = acuan.buka(p.acuan_token) or p.luar_jam
    s = harga_spot_token(rpc, p, state_view)
    dq, dt = _dec(p, p.quote), _dec(p, p.token)
    out = {"pasangan": p.nama, "wajar": wajar, "spot": s, "selisih_spot": s / wajar - 1, "acuan_hidup": hidup,
           "quote_usd": ref_q, "aksi": "TUNGGU", "alasan": ""}

    # ---- sisi beli: kecilkan ukuran sampai slippage muat
    usd = p.ukuran_usd
    while usd >= p.min_usd:
        amt_in = int(usd / ref_q * 10 ** dq)
        try:
            got = quote(rpc, p.pool, p.quote, amt_in, quoter)
        except Exception as e:  # noqa: BLE001
            out["alasan"] = f"kuotasi beli gagal ({str(e)[:60]})"
            return out
        if got <= 0:
            break
        e_buy = (amt_in / 10 ** dq) / (got / 10 ** dt)
        slip = e_buy / s - 1
        if slip <= p.max_slippage:
            break
        usd /= 2
    else:
        out["alasan"] = f"likuiditas tipis: slippage > {p.max_slippage:.1%} bahkan untuk ${p.min_usd:g}"
        return out
    edge_buy = wajar / e_buy - 1 - p.biaya_gas_usd / usd
    out.update({"ukuran_usd": usd, "harga_beli": e_buy, "slippage_beli": slip, "untung_beli": edge_buy})

    # ---- cek jual-balik (honeypot / hook pajak)
    try:
        back = quote(rpc, p.pool, p.token, got, quoter)
        rt = 1 - (back / 10 ** dq) / (amt_in / 10 ** dq)
        biaya_keluar = max(0.0, 1 - ((back / 10 ** dq) / (got / 10 ** dt)) / s)   # fee + dampak sisi jual vs spot
    except Exception:  # noqa: BLE001
        rt, biaya_keluar = 1.0, 1.0
    out["rugi_pulang_pergi"] = rt
    keluar = wajar * (1 - p.biaya_tebus) if p.tebus_manual else wajar * (1 - biaya_keluar)
    out["untung_bersih"] = keluar / e_buy - 1 - 2 * p.biaya_gas_usd / usd
    out["tebus_manual"] = p.tebus_manual
    if p.tebus_manual:
        out["nilai_tebus"] = wajar * (1 - p.biaya_tebus)
    batas_rt = 2 * slip + 0.03
    # ---- sisi jual (pakai jumlah token posisi bila ada, kalau tidak setara ukuran)
    n_tok = (posisi or {}).get("token") or got
    try:
        q_out = quote(rpc, p.pool, p.token, int(n_tok), quoter)
        e_sell = (q_out / 10 ** dq) / (n_tok / 10 ** dt)
        out.update({"harga_jual": e_sell, "untung_jual": e_sell / wajar - 1 - p.biaya_gas_usd / usd})
    except Exception:  # noqa: BLE001
        e_sell = None

    if posisi:
        if p.tebus_manual:
            out["alasan"] = "posisi token jembatan: keluar lewat TEBUS manual (bukan jual DEX)"
            return out
        masuk = posisi["harga"]
        if e_sell is not None and e_sell >= masuk * (1 + p.tp):
            out.update(aksi="JUAL", alasan=f"TP: jual {e_sell:.6g} >= masuk {masuk:.6g} +{p.tp:.1%}")
        elif e_sell is not None and e_sell <= masuk * (1 - p.sl):
            out.update(aksi="JUAL", alasan=f"SL: jual {e_sell:.6g} <= masuk -{p.sl:.1%}")
        elif e_sell is not None and hidup and e_sell >= wajar * (1 - 0.002) and e_sell > masuk:
            out.update(aksi="JUAL", alasan="harga kembali ke acuan")
        return out
    if not hidup:
        out["alasan"] = "acuan tutup (bursa saham libur/di luar jam) -> tidak ada harga wajar terkini"
        return out
    if rt > batas_rt:
        out["alasan"] = f"jual-balik rugi {rt:.1%} > {batas_rt:.1%}: hook/pajak/honeypot? LEWATI"
        return out
    if out["untung_bersih"] >= p.beli_bawah:
        jalan = "tebus manual" if p.tebus_manual else "jual DEX"
        out.update(aksi="BELI", alasan=f"harga beli {e_buy:.6g}: diskon {edge_buy:+.2%}, bersih ±{out['untung_bersih']:+.2%} "
                                       f"setelah keluar ({jalan}), slippage {slip:.2%}")
    elif e_sell is not None and out["untung_jual"] >= p.jual_atas:
        # hanya informasi: menjual di atas acuan butuh stok token (bot tidak short / tidak meminjam)
        out.update(aksi="INFO_PREMI", alasan=f"pool {out['untung_jual']:+.2%} di atas acuan — info saja (butuh stok token)")
    return out
