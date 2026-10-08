"""Eksekusi order: KertasBroker (simulasi, bawaan) dan LiveBroker (bursa nyata lewat ccxt, kunci API milik pengguna).

Semua nilai uang di sini dalam USD. Bursa ber-quote IDR (Indodax) dikonversi memakai kurs USDT/IDR bursa itu.
LiveBroker TIDAK pernah memanggil penarikan dana; pakai kunci API tanpa izin withdraw + whitelist IP (tutorial).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass


@dataclass
class Isi:
    qty: float          # jumlah koin yang DITERIMA/dijual (bersih)
    harga: float        # harga rata-rata dalam USD
    usd: float          # nilai USD kotor
    biaya_usd: float
    order_id: str | None = None


class TidakBisa(RuntimeError):
    """Order tidak dikirim (di bawah minimum bursa, koin tidak ada di bursa, saldo kurang, ...)."""


class KertasBroker:
    live = False

    def __init__(self, store, modal: float, slippage: float = 0.002, biaya: float = 0.001):
        self.store, self.slip, self.fee = store, slippage, biaya
        if store.s.get("kas_kertas") is None:
            store.s["kas_kertas"] = float(modal)
        self.nama = "kertas"

    def saldo_usd(self) -> float:
        return float(self.store.s["kas_kertas"])

    def punya_pasar(self, base: str) -> bool:
        return True

    def beli(self, base: str, usd: float, harga_ref: float, limit: float | None = None) -> Isi:
        if usd > self.saldo_usd() + 1e-9:
            raise TidakBisa(f"saldo kertas ${self.saldo_usd():.2f} < ${usd:.2f}")
        px = harga_ref * (1 + self.slip)
        if limit is not None:
            px = min(px, limit)
        fee = usd * self.fee
        qty = (usd - fee) / px
        self.store.s["kas_kertas"] = self.saldo_usd() - usd
        return Isi(qty, px, usd, fee)

    def jual(self, base: str, qty: float, harga_ref: float, limit: float | None = None) -> Isi:
        px = limit if limit is not None else harga_ref * (1 - self.slip)
        kotor = qty * px
        fee = kotor * self.fee
        self.store.s["kas_kertas"] = self.saldo_usd() + kotor - fee
        return Isi(qty, px, kotor, fee)

    def isi_tp(self, base: str, qty: float, harga_tp: float) -> Isi:
        """TP mode kertas: limit jual dianggap terisi tepat di harga TP (tanpa slippage, kena biaya)."""
        return self.jual(base, qty, harga_tp, limit=harga_tp)

    # TP mode kertas dipantau mesin (harga >= tp -> jual di tp)
    def pasang_tp(self, base: str, qty: float, harga_tp: float) -> str | None:
        return None

    def cek_order(self, base: str, order_id: str) -> dict:
        return {"status": "open", "filled": 0.0, "average": None}

    def batal(self, base: str, order_id: str) -> None:
        return None


class LiveBroker:
    live = True

    def __init__(self, ccxt_id: str, api_key: str, secret: str, password: str = "", quote: str = "USDT",
                 sandbox: bool = False):
        import ccxt  # hanya dibutuhkan mode live

        if not api_key or not secret:
            raise RuntimeError("mode live butuh BURSA_API_KEY dan BURSA_API_SECRET di .env")
        kelas = getattr(ccxt, ccxt_id)
        self.ex = kelas({"apiKey": api_key, "secret": secret, "password": password or None,
                         "enableRateLimit": True, "options": {"defaultType": "spot"}})
        if sandbox:
            self.ex.set_sandbox_mode(True)
        self.ex.load_markets()
        self.quote = quote.upper()
        self.nama = ccxt_id

    # ------------------------------------------------------------ bantu
    def _sym(self, base: str) -> str:
        return f"{base}/{self.quote}"

    def _kurs(self) -> float:
        """USD -> quote. USDT = 1; IDR = harga USDT/IDR bursa."""
        if self.quote in ("USDT", "USD", "USDC", "FDUSD"):
            return 1.0
        return float(self.ex.fetch_ticker(f"USDT/{self.quote}")["last"])

    def punya_pasar(self, base: str) -> bool:
        m = self.ex.markets.get(self._sym(base))
        return bool(m and m.get("active", True) and m.get("spot", True))

    def saldo_usd(self) -> float:
        bal = self.ex.fetch_balance()
        free = float((bal.get(self.quote) or {}).get("free") or 0)
        return free / self._kurs()

    def _minimal(self, sym: str, qty: float, px: float) -> None:
        lim = self.ex.markets[sym].get("limits") or {}
        mn_amt = (lim.get("amount") or {}).get("min")
        mn_cost = (lim.get("cost") or {}).get("min")
        if mn_amt and qty < mn_amt:
            raise TidakBisa(f"{sym}: jumlah {qty} < minimum {mn_amt}")
        if mn_cost and qty * px < mn_cost:
            raise TidakBisa(f"{sym}: nilai {qty * px:.4f} < minimum {mn_cost}")

    def _tunggu(self, sym: str, oid: str, detik: float = 20) -> dict:
        o = self.ex.fetch_order(oid, sym)
        t0 = time.time()
        while o.get("status") == "open" and time.time() - t0 < detik:
            time.sleep(1)
            o = self.ex.fetch_order(oid, sym)
        return o

    def _biaya_usd(self, o: dict, base: str, px_quote: float, kurs: float) -> tuple[float, float]:
        """(biaya USD, potongan base) dari info fee order."""
        fees = o.get("fees") or ([o["fee"]] if o.get("fee") else [])
        usd, dari_base = 0.0, 0.0
        for f in fees:
            if not f or f.get("cost") is None:
                continue
            c = float(f["cost"])
            cur = (f.get("currency") or "").upper()
            if cur == base.upper():
                dari_base += c
                usd += c * px_quote / kurs
            elif cur == self.quote:
                usd += c / kurs
        return usd, dari_base

    # ------------------------------------------------------------ order
    def beli(self, base: str, usd: float, harga_ref: float, limit: float | None = None) -> Isi:
        sym = self._sym(base)
        if not self.punya_pasar(base):
            raise TidakBisa(f"{sym} tidak ada di {self.nama}")
        kurs = self._kurs()
        cost_q = usd * kurs
        tk = self.ex.fetch_ticker(sym)
        ask = float(tk.get("ask") or tk["last"])
        if limit is not None:
            px_q = float(self.ex.price_to_precision(sym, limit * kurs))
            if ask > px_q * 1.0001:
                raise TidakBisa(f"{sym}: harga jual {ask} di atas limit {px_q} (harga sudah naik)")
            qty = float(self.ex.amount_to_precision(sym, cost_q / px_q))
            self._minimal(sym, qty, px_q)
            o = self.ex.create_order(sym, "limit", "buy", qty, px_q, {"timeInForce": "IOC"}
                                     if self.ex.id in ("binance", "tokocrypto") else {})
        else:
            qty = float(self.ex.amount_to_precision(sym, cost_q / ask))
            self._minimal(sym, qty, ask)
            if self.ex.has.get("createMarketBuyOrderWithCost"):
                o = self.ex.create_market_buy_order_with_cost(sym, cost_q)
            else:
                o = self.ex.create_order(sym, "market", "buy", qty, ask)
        o = self._tunggu(sym, o["id"])
        filled = float(o.get("filled") or 0)
        if filled <= 0:
            if o.get("status") == "open":
                self.ex.cancel_order(o["id"], sym)
            raise TidakBisa(f"{sym}: order beli tidak terisi")
        avg_q = float(o.get("average") or o.get("price") or ask)
        fee_usd, dari_base = self._biaya_usd(o, base, avg_q, kurs)
        qty_bersih = filled - dari_base
        free = float((self.ex.fetch_balance().get(base) or {}).get("free") or qty_bersih)
        qty_bersih = min(qty_bersih, free)
        return Isi(qty_bersih, avg_q / kurs, filled * avg_q / kurs, fee_usd, o["id"])

    def jual(self, base: str, qty: float, harga_ref: float, limit: float | None = None) -> Isi:
        sym = self._sym(base)
        kurs = self._kurs()
        free = float((self.ex.fetch_balance().get(base) or {}).get("free") or 0)
        q = float(self.ex.amount_to_precision(sym, min(qty, free) * (1 - 1e-9)))
        if q <= 0:
            raise TidakBisa(f"{sym}: saldo {base} kosong")
        o = self.ex.create_order(sym, "market", "sell", q)
        o = self._tunggu(sym, o["id"])
        filled = float(o.get("filled") or 0)
        avg_q = float(o.get("average") or o.get("price") or harga_ref * kurs)
        fee_usd, _ = self._biaya_usd(o, base, avg_q, kurs)
        return Isi(filled, avg_q / kurs, filled * avg_q / kurs, fee_usd, o["id"])

    def pasang_tp(self, base: str, qty: float, harga_tp: float) -> str | None:
        sym = self._sym(base)
        kurs = self._kurs()
        px_q = float(self.ex.price_to_precision(sym, harga_tp * kurs))
        q = float(self.ex.amount_to_precision(sym, qty * (1 - 1e-9)))
        self._minimal(sym, q, px_q)
        o = self.ex.create_order(sym, "limit", "sell", q, px_q)
        return o["id"]

    def cek_order(self, base: str, order_id: str) -> dict:
        o = self.ex.fetch_order(order_id, self._sym(base))
        kurs = self._kurs()
        avg = o.get("average") or o.get("price")
        fee, _ = self._biaya_usd(o, base, float(avg or 0), kurs)
        return {"status": o.get("status"), "filled": float(o.get("filled") or 0),
                "average": (float(avg) / kurs) if avg else None, "biaya_usd": fee}

    def batal(self, base: str, order_id: str) -> None:
        try:
            self.ex.cancel_order(order_id, self._sym(base))
        except Exception as e:
            msg = str(e).lower()
            if "unknown order" not in msg and "not found" not in msg and "filled" not in msg:
                raise


def bulat_bawah(x: float, langkah: float) -> float:
    return math.floor(x / langkah) * langkah if langkah else x
