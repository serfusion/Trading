"""Eksekusi order: KertasBroker (simulasi, bawaan) dan LiveBroker (bursa nyata lewat ccxt, kunci API milik pengguna).

Semua nilai uang di sini dalam USD (bursa ber-quote USDT/USDC/FDUSD). LiveBroker TIDAK pernah memanggil penarikan
dana; pakai kunci API tanpa izin withdraw + whitelist IP (tutorial).

Dua jenis kegagalan (penting untuk keselamatan uang):
  TidakBisa  order PASTI tidak dieksekusi (ditolak: saldo kurang, di bawah minimum, pasar tidak ada, IOC tidak
             terisi). `sementara=True` = layak dicoba lagi nanti.
  TidakPasti order MUNGKIN sudah terkirim/terisi tetapi status tidak diketahui (jaringan putus, timeout, galat lain).
             Mesin menjeda bot dan meminta pengguna mengecek aplikasi bursa — TIDAK pernah dicoba ulang otomatis.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass


@dataclass
class Isi:
    qty: float          # beli: koin DITERIMA (bersih biaya); jual: koin TERJUAL
    harga: float        # harga rata-rata (USD)
    usd: float          # beli: uang keluar (termasuk biaya non-koin); jual: hasil kotor
    biaya_usd: float
    order_id: str | None = None
    diminta: float | None = None   # jual: qty yang diminta (isi sebagian bila qty < diminta)


class TidakBisa(RuntimeError):
    def __init__(self, pesan: str, sementara: bool = False):
        super().__init__(pesan)
        self.sementara = sementara


class TidakPasti(RuntimeError):
    def __init__(self, pesan: str, order_id: str | None = None, client_id: str | None = None):
        super().__init__(pesan)
        self.order_id, self.client_id = order_id, client_id


def hingga(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


class KertasBroker:
    """Simulasi: order PASAR kena slippage + biaya; order LIMIT (TP, entry listing) terisi tepat di limit + biaya."""

    live = False

    def __init__(self, store, modal: float, slippage: float = 0.001, biaya: float = 0.001):
        self.store, self.slip, self.fee = store, slippage, biaya
        if store.s.get("kas_kertas") is None:
            store.s["kas_kertas"] = float(modal)
        self.nama = "kertas"

    def saldo_usd(self) -> float:
        return float(self.store.s["kas_kertas"])

    def punya_pasar(self, base: str) -> bool:
        return True

    def harga_venue(self, base: str) -> float | None:
        return None

    def beli(self, base: str, usd: float, harga_ref: float, limit: float | None = None,
             client_id: str | None = None) -> Isi:
        if not (hingga(usd) and usd > 0 and hingga(harga_ref) and harga_ref > 0):
            raise TidakBisa(f"angka tidak valid (usd {usd}, harga {harga_ref})")
        if usd > self.saldo_usd() + 1e-9:
            raise TidakBisa(f"saldo kertas ${self.saldo_usd():.2f} < ${usd:.2f}")
        if limit is not None:
            if harga_ref > limit * 1.000001:
                raise TidakBisa(f"harga {harga_ref} di atas limit {limit}", sementara=True)
            px = harga_ref                      # pemanggil memberi harga isi limit = min(open, limit)
        else:
            px = harga_ref * (1 + self.slip)
        fee = usd * self.fee
        self.store.s["kas_kertas"] = self.saldo_usd() - usd
        return Isi((usd - fee) / px, px, usd, fee)

    def jual(self, base: str, qty: float, harga_ref: float, limit: float | None = None) -> Isi:
        if not (hingga(qty) and qty > 0 and hingga(harga_ref) and harga_ref > 0):
            raise TidakBisa(f"angka tidak valid (qty {qty}, harga {harga_ref})")
        px = limit if limit is not None else harga_ref * (1 - self.slip)
        kotor = qty * px
        fee = kotor * self.fee
        self.store.s["kas_kertas"] = self.saldo_usd() + kotor - fee
        return Isi(qty, px, kotor, fee, diminta=qty)

    def isi_tp(self, base: str, qty: float, harga_tp: float) -> Isi:
        return self.jual(base, qty, harga_tp, limit=harga_tp)

    def pasang_tp(self, base: str, qty: float, harga_tp: float) -> str | None:
        return None                              # TP kertas dipantau mesin dengan high candle 1 menit

    def cek_order(self, base: str, order_id: str) -> dict:
        return {"status": "open", "filled": 0.0, "average": None, "biaya_usd": 0.0}

    def batal(self, base: str, order_id: str) -> None:
        return None


class LiveBroker:
    live = True
    QUOTE_OK = ("USDT", "USDC", "FDUSD")

    def __init__(self, ccxt_id: str, api_key: str, secret: str, password: str = "", quote: str = "USDT",
                 sandbox: bool = False, ex=None):
        quote = quote.upper()
        if quote not in self.QUOTE_OK:
            raise RuntimeError(f"quote {quote} belum didukung (sinyal memakai harga Binance USDT). Pakai pair USDT.")
        if ex is None:
            import ccxt  # hanya dibutuhkan mode live

            if not api_key or not secret:
                raise RuntimeError("mode live butuh BURSA_API_KEY dan BURSA_API_SECRET di sniper_bot/.env")
            ex = getattr(ccxt, ccxt_id)({"apiKey": api_key, "secret": secret, "password": password or None,
                                         "enableRateLimit": True, "options": {"defaultType": "spot"}})
            if sandbox:
                ex.set_sandbox_mode(True)
            ex.load_markets()
        self.ex, self.quote, self.nama = ex, quote, ccxt_id

    # ------------------------------------------------------------ bantu
    def _sym(self, base: str) -> str:
        return f"{base}/{self.quote}"

    def punya_pasar(self, base: str) -> bool:
        m = self.ex.markets.get(self._sym(base))
        return bool(m and m.get("active", True) is not False and m.get("spot", True))

    def harga_venue(self, base: str) -> float | None:
        try:
            return float(self.ex.fetch_ticker(self._sym(base))["last"])
        except Exception:  # noqa: BLE001
            return None

    def cek_izin(self) -> dict | None:
        """Binance: izin kunci API dari /sapi/v1/account/apiRestrictions. Bursa lain: None (cek manual di web bursa)."""
        f = getattr(self.ex, "sapi_get_account_apirestrictions", None)
        if self.nama != "binance" or f is None:
            return None
        d = f()
        return {"tarik": bool(d.get("enableWithdrawals")), "transfer": bool(d.get("enableInternalTransfer")),
                "ip": bool(d.get("ipRestrict")), "spot": bool(d.get("enableSpotAndMarginTrading")),
                "futures": bool(d.get("enableFutures"))}

    def _bebas(self, aset: str) -> float:
        return float((self.ex.fetch_balance().get(aset) or {}).get("free") or 0)

    def saldo_usd(self) -> float:
        return self._bebas(self.quote)

    def _tick(self, sym: str) -> float | None:
        p = (self.ex.markets[sym].get("precision") or {}).get("price")
        if p is None:
            return None
        try:
            import ccxt
            tick_mode = getattr(self.ex, "precisionMode", None) == ccxt.TICK_SIZE
        except ImportError:
            tick_mode = float(p) < 1
        return float(p) if tick_mode else 10 ** -float(p)

    def _harga(self, sym: str, x: float, atas: bool) -> float:
        """Bulatkan ke tick: TP ke ATAS (tidak lebih rendah dari target), limit beli ke BAWAH."""
        t = self._tick(sym)
        if t:
            x = (math.ceil(x / t - 1e-9) if atas else math.floor(x / t + 1e-9)) * t
        return float(self.ex.price_to_precision(sym, x))

    def _minimal(self, sym: str, qty: float, px: float) -> None:
        lim = self.ex.markets[sym].get("limits") or {}
        mn_amt = (lim.get("amount") or {}).get("min")
        mn_cost = (lim.get("cost") or {}).get("min")
        if qty <= 0 or (mn_amt and qty < mn_amt):
            raise TidakBisa(f"{sym}: jumlah {qty} < minimum {mn_amt}")
        if mn_cost and qty * px < mn_cost:
            raise TidakBisa(f"{sym}: nilai {qty * px:.4f} < minimum {mn_cost}")

    def _kirim(self, fn, *a, client_id: str | None = None):
        """Ditolak bursa -> TidakBisa (pasti tidak tereksekusi); galat lain -> TidakPasti."""
        import ccxt
        try:
            return fn(*a)
        except (ccxt.InsufficientFunds, ccxt.InvalidOrder, ccxt.BadSymbol, ccxt.PermissionDenied,
                ccxt.AuthenticationError, ccxt.BadRequest) as e:
            raise TidakBisa(f"ditolak bursa: {type(e).__name__}: {str(e)[:150]}") from e
        except Exception as e:  # noqa: BLE001
            raise TidakPasti(f"status order tidak diketahui: {type(e).__name__}: {str(e)[:150]}",
                             client_id=client_id) from e

    def _final(self, sym: str, o: dict, detik: float = 15) -> dict:
        """Tunggu order selesai; bila masih terbuka -> batalkan lalu ambil status AKHIR. Galat -> TidakPasti."""
        oid = o.get("id")
        try:
            t0 = time.time()
            while o.get("status") not in ("closed", "canceled", "expired", "rejected") and time.time() - t0 < detik:
                time.sleep(1)
                o = {**o, **{k: v for k, v in self.ex.fetch_order(oid, sym).items() if v is not None}}
            if o.get("status") not in ("closed", "canceled", "expired", "rejected"):
                try:
                    self.ex.cancel_order(oid, sym)
                except Exception:  # noqa: BLE001 - mungkin terisi tepat saat dibatalkan
                    pass
                o = {**o, **{k: v for k, v in self.ex.fetch_order(oid, sym).items() if v is not None}}
                if o.get("status") == "open":
                    raise TidakPasti(f"order {oid} masih terbuka setelah dibatalkan", order_id=oid)
        except TidakPasti:
            raise
        except Exception as e:  # noqa: BLE001
            raise TidakPasti(f"order {oid} terkirim, status tidak terbaca: {str(e)[:150]}", order_id=oid) from e
        return o

    def _biaya(self, o: dict, base: str, avg: float) -> tuple[float | None, float]:
        """(biaya USD di luar koin base atau None bila bursa tidak memberi info, potongan dalam koin base)."""
        fees = o.get("fees") or ([o["fee"]] if o.get("fee") else [])
        lain, dari_base, ada = 0.0, 0.0, False
        for f in fees:
            if not f or f.get("cost") is None:
                continue
            ada = True
            c = float(f["cost"])
            cur = (f.get("currency") or "").upper()
            if cur == base.upper():
                dari_base += c
            elif cur in self.QUOTE_OK:
                lain += c
            elif cur:
                try:                                   # mis. BNB
                    lain += c * float(self.ex.fetch_ticker(f"{cur}/{self.quote}")["last"])
                except Exception:  # noqa: BLE001
                    pass
        return (lain if ada else None), dari_base

    # ------------------------------------------------------------ order
    def beli(self, base: str, usd: float, harga_ref: float, limit: float | None = None,
             client_id: str | None = None) -> Isi:
        if not (hingga(usd) and usd > 0):
            raise TidakBisa(f"jumlah tidak valid: {usd}")
        sym = self._sym(base)
        if not self.punya_pasar(base):
            raise TidakBisa(f"{sym} tidak ada di {self.nama}")
        try:
            bebas_q, base0 = self._bebas(self.quote), self._bebas(base)
            tk = self.ex.fetch_ticker(sym)
        except Exception as e:  # noqa: BLE001 - belum ada order dikirim
            raise TidakBisa(f"gagal membaca saldo/harga: {str(e)[:120]}", sementara=True) from e
        if usd > bebas_q * 0.995:
            raise TidakBisa(f"saldo {self.quote} bebas {bebas_q:.2f} < {usd:.2f}")
        ask = float(tk.get("ask") or tk["last"])
        params = {"clientOrderId": client_id} if client_id else {}
        if limit is not None:
            px = self._harga(sym, limit, atas=False)
            if ask > px * 1.0001:
                raise TidakBisa(f"{sym}: harga jual {ask} di atas limit {px}", sementara=True)
            qty = float(self.ex.amount_to_precision(sym, usd / px))
            self._minimal(sym, qty, px)
            o = self._kirim(self.ex.create_order, sym, "limit", "buy", qty, px, {**params, "timeInForce": "IOC"},
                            client_id=client_id)
        else:
            qty = float(self.ex.amount_to_precision(sym, usd / ask))
            self._minimal(sym, qty, ask)
            if self.ex.has.get("createMarketBuyOrderWithCost"):
                o = self._kirim(self.ex.create_market_buy_order_with_cost, sym, usd, params, client_id=client_id)
            else:
                o = self._kirim(self.ex.create_order, sym, "market", "buy", qty, None, params, client_id=client_id)
        o = self._final(sym, o)
        filled = float(o.get("filled") or 0)
        if filled <= 0:
            raise TidakBisa(f"{sym}: order beli tidak terisi ({o.get('status')})", sementara=True)
        avg = float(o.get("average") or o.get("price") or ask)
        lain, dari_base = self._biaya(o, base, avg)
        try:
            diterima = self._bebas(base) - base0       # qty bersih = selisih saldo (fee dalam koin ikut terhitung)
        except Exception:  # noqa: BLE001
            diterima = None
        if diterima is not None and 0 < diterima <= filled * 1.0001:
            qty_bersih = diterima
            fee_koin = max(filled - diterima, 0.0) * avg
        elif lain is not None:
            qty_bersih, fee_koin = filled - dari_base, dari_base * avg
        else:
            qty_bersih, fee_koin = filled * 0.999, filled * avg * 0.001   # perkiraan bila tidak ada info fee
        lain = lain or 0.0
        return Isi(qty_bersih, avg, filled * avg + lain, fee_koin + lain, o.get("id"))

    def jual(self, base: str, qty: float, harga_ref: float, limit: float | None = None) -> Isi:
        sym = self._sym(base)
        try:
            bebas = self._bebas(base)
        except Exception as e:  # noqa: BLE001
            raise TidakBisa(f"gagal membaca saldo {base}: {str(e)[:120]}", sementara=True) from e
        q = float(self.ex.amount_to_precision(sym, min(qty, bebas) * (1 - 1e-9)))
        if q <= 0:
            raise TidakBisa(f"{sym}: saldo {base} kosong")
        ref = self.harga_venue(base) or harga_ref
        self._minimal(sym, q, ref)
        o = self._kirim(self.ex.create_order, sym, "market", "sell", q)
        o = self._final(sym, o)
        filled = float(o.get("filled") or 0)
        avg = float(o.get("average") or o.get("price") or ref)
        lain, dari_base = self._biaya(o, base, avg)
        fee = (lain or 0.0) + dari_base * avg if lain is not None else filled * avg * 0.001
        return Isi(filled, avg, filled * avg, fee, o.get("id"), diminta=q)

    def pasang_tp(self, base: str, qty: float, harga_tp: float) -> str | None:
        sym = self._sym(base)
        px = self._harga(sym, harga_tp, atas=True)
        q = float(self.ex.amount_to_precision(sym, qty * (1 - 1e-9)))
        self._minimal(sym, q, px)
        o = self._kirim(self.ex.create_order, sym, "limit", "sell", q, px)
        return o["id"]

    def cek_order(self, base: str, order_id: str) -> dict:
        o = self.ex.fetch_order(order_id, self._sym(base))
        avg = o.get("average") or o.get("price")
        lain, dari_base = self._biaya(o, base, float(avg or 0))
        filled = float(o.get("filled") or 0)
        fee = ((lain or 0.0) + dari_base * float(avg or 0)) if lain is not None else filled * float(avg or 0) * 0.001
        return {"status": o.get("status"), "filled": filled, "average": float(avg) if avg else None, "biaya_usd": fee}

    def batal(self, base: str, order_id: str) -> None:
        try:
            self.ex.cancel_order(order_id, self._sym(base))
        except Exception as e:  # noqa: BLE001 - order mungkin sudah terisi/batal
            msg = str(e).lower()
            if not any(k in msg for k in ("unknown order", "not found", "filled", "does not exist", "-2011")):
                raise
