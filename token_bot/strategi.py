"""Keputusan BELI / JUAL satu pasangan: harga eksekusi NYATA (Quoter) vs harga acuan, batas slippage, cek jual-balik.

Aturan (angka bawaan dari riset docs/TOKEN_BARU.md — ubah di konfigurasi):
  BELI  bila harga eksekusi beli <= acuan x (1 - beli_bawah)      [murah dibanding harga wajar]
  JUAL  bila harga eksekusi jual >= acuan x (1 + jual_atas)       [mahal dibanding harga wajar]
        atau posisi terbuka: >= harga masuk x (1 + tp) / <= harga masuk x (1 - sl) / sudah kembali ke acuan
  Slippage = harga eksekusi / harga spot pool - 1 (sudah termasuk fee pool & dampak likuiditas). Bila > max_slippage
  ukuran diperkecil (bagi dua) sampai muat; bila tetap tidak muat -> lewati (likuiditas tipis).
  Cek jual-balik: token yang dibeli dikuotasi dijual kembali; rugi pulang-pergi jauh di atas fee x2 + slippage x2
  -> tanda hook/pajak/honeypot -> lewati.
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
           "aksi": "TUNGGU", "alasan": ""}

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
    except Exception:  # noqa: BLE001
        rt = 1.0
    out["rugi_pulang_pergi"] = rt
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
    if edge_buy >= p.beli_bawah:
        out.update(aksi="BELI", alasan=f"harga beli {e_buy:.6g} = acuan {edge_buy:+.2%} lebih murah, slippage {slip:.2%}")
    elif e_sell is not None and out["untung_jual"] >= p.jual_atas:
        out.update(aksi="JUAL_ARBITRASE", alasan=f"pool {out['untung_jual']:+.2%} di atas acuan (perlu stok token)")
    return out
