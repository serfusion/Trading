"""Perintah Telegram (bahasa Indonesia). Aksi uang (beli/tutup/hapus manual) selalu minta konfirmasi tombol."""
from __future__ import annotations

import math
import re
import secrets

from .mesin import jam, pct, px, usd
from .telegram import esc, sensor

TOMBOL = {"📊 status": "/status", "📂 posisi": "/posisi", "🧾 riwayat": "/riwayat", "🆕 listing": "/listing",
          "🔎 pindai": "/pindai", "⏸ jeda": "/jeda", "▶️ lanjut": "/lanjut", "❓ bantuan": "/bantuan"}

TOLERANSI_BELI = 0.01          # /beli manual: limit IOC di harga tampil +1% (tidak terisi bila harga sudah lari)
KEDALUWARSA = {"beli": 30, "tutup": 120, "hapus": 120}

BANTUAN = """<b>Sniper bot — perintah</b>
/status — mode, modal, posisi, strategi, batas risiko
/posisi — posisi terbuka + untung/rugi berjalan
/riwayat — 15 trade terakhir + statistik
/listing — token baru yang dipantau (P0 & harga sinyal)
/pindai — cek listing sekarang; 💎 di luar jendela 07:05–08:00 WIB hanya MENAMPILKAN sinyal
/strategi — daftar strategi; <code>/strategi spot_dip mati</code> / <code>hidup</code>
/beli SIMBOL USD [TP%] [SL%] — beli manual, mis. <code>/beli SOL 20 5 10</code>
/tutup ID — jual posisi sekarang (lihat ID di /posisi)
/hapus ID — hapus posisi dari catatan bot TANPA menjual (sudah dijual manual / koin delisting)
/beres — setelah cek aplikasi bursa: hapus tanda order "tidak pasti" agar bot boleh beli lagi
/jeda — stop entry baru (posisi tetap dikelola) • /lanjut — buka lagi
/saldo — saldo bursa/kertas
Mode kertas/live diatur di config.yaml (bukan lewat Telegram) demi keamanan."""


def teks_status(m) -> str:
    s = m.s
    mode = "LIVE 💸" if m.broker.live else "KERTAS (simulasi)"
    kas = m.kas()
    eks = m.eksposur()
    h = m._hari()
    r = m.cfg["risiko"]
    st = []
    for nama, x in m.strategi.items():
        mati = " (MATI)" if nama in s["strategi_mati"] else ""
        st.append(f"• {x.status_teks()}{mati}")
    riw = s["riwayat"]
    menang = sum(1 for t in riw if t.get("pnl_usd", 0) > 0)
    total = sum(t.get("pnl_usd", 0) for t in riw)
    kas_t = f"{usd(kas)} • ekuitas {usd(kas + eks)}" if kas is not None else "? (saldo gagal dibaca)"
    return (f"Mode <b>{mode}</b> • bursa {esc(m.broker.nama)}\n"
            f"Kas {kas_t} • posisi {len(s['posisi'])} senilai {usd(eks)}\n"
            f"Hari ini (sejak 07:00 WIB): {usd(m.rugi_hari_ini())} (tertutup {usd(h['pnl'])}), trade {h['trade']}"
            + (" • ⛔ jeda rugi harian" if h.get("jeda_rugi") else "") + "\n"
            f"Riwayat: {len(riw)} trade, menang {menang} ({(menang / len(riw) * 100) if riw else 0:.0f}%), "
            f"total {usd(total)}\n"
            f"Batas: {usd(r['maks_usd_per_trade'])}/trade, total {usd(r['maks_total_usd'])}, "
            f"maks {r['maks_posisi']} posisi, stop rugi harian {usd(r['stop_rugi_harian_usd'])}\n"
            + ("⏸ <b>DIJEDA</b> (/lanjut)\n" if s["jeda"] else "")
            + (f"🚨 <b>{len(s['pending'])} order tidak pasti</b> — cek bursa lalu /beres\n" if s["pending"] else "")
            + "\n".join(st)
            + (f"\nHarga terakhir {jam(m.t_harga)}" if m.t_harga else ""))


def teks_posisi(m) -> str:
    if not m.s["posisi"]:
        return "Tidak ada posisi terbuka."
    out = []
    for p in m.s["posisi"].values():
        h = m.harga_pos(p)
        ret = (h / p["entry"] - 1) if h else 0.0
        out.append(f"<b>{p['id']}</b> {esc(p['simbol'])} ({esc(p['strategi'])}) masuk {px(p['entry'])} • kini "
                   f"{px(h)} ({pct(ret)}) • {usd(p['usd'])}"
                   + (" • 🚨 jual tidak pasti" if p.get("tidak_pasti") else "") + "\n"
                   f"   TP {px(p['tp_px']) if p.get('tp_px') else '-'} • SL {px(p['sl_px']) if p.get('sl_px') else '-'}"
                   + (f" • batas {jam(p['deadline'])}" if p.get("deadline") else ""))
    return "\n".join(out)


def teks_riwayat(m, n: int = 15) -> str:
    riw = m.s["riwayat"]
    if not riw:
        return "Belum ada trade tertutup."
    per = {}
    for t in riw:
        d = per.setdefault(t["strategi"], [0, 0, 0.0])
        d[0] += 1
        d[1] += t.get("pnl_usd", 0) > 0
        d[2] += t.get("pnl_usd", 0)
    head = "\n".join(f"• {esc(k)}: {v[0]} trade, menang {v[1] / v[0] * 100:.0f}%, total {usd(v[2])}" for k, v in per.items())
    rows = [f"{'🟢' if t.get('pnl_usd', 0) > 0 else '🔴'} {esc(t['simbol'])} {pct(t.get('ret', 0))} {usd(t.get('pnl_usd', 0))} "
            f"• {esc(t.get('alasan', ''))} • {jam(t.get('t_tutup', 0))}" for t in riw[:n]]
    return head + "\n\n" + "\n".join(rows)


def teks_listing(m) -> str:
    L = m.s["listing"]
    aktif = [(k, d) for k, d in L.items() if d["status"] in ("pantau", "menunggu_p0", "dibeli", "sinyal")]
    if not aktif:
        return "Belum ada token baru (≤ 30 hari) yang dipantau." + (
            f" Antrian cek waktu listing: {len(m.s.get('listing_antri', []))}." if m.s.get("listing_antri") else "")
    out = []
    for k, d in sorted(aktif, key=lambda x: -x[1]["t_listing"]):
        h = m.harga.get(k)
        if d["p0"]:
            jarak = (h / d["limit"] - 1) if h else None
            out.append(f"<b>{esc(k)}</b> {d['status']} • listing {jam(d['t_listing'])}\n   P0 {px(d['p0'])} → sinyal ≤ "
                       f"{px(d['limit'])} • kini {px(h)}"
                       + (f" ({pct(jarak)} di atas harga sinyal)" if jarak is not None and jarak > 0 else ""))
        else:
            out.append(f"<b>{esc(k)}</b> menunggu P0 • listing {jam(d['t_listing'])}")
    return "\n".join(out[:40])


def _konfirmasi(m, cid: int, teks: str, perintah: str) -> None:
    tok = secrets.token_hex(6)
    m.konfirmasi[tok] = (m.now(), perintah, cid)
    m.tg.kirim(teks, chat_id=cid, tombol=[[{"text": "✅ Ya, lakukan", "callback_data": f"ya:{tok}"},
                                           {"text": "❌ Batal", "callback_data": f"tidak:{tok}"}]])


def _angka(x: str) -> float | None:
    try:
        v = float(x.replace(",", "."))
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _jalankan(m, cid: int, perintah: str) -> None:
    bag = perintah.split()
    if bag[0] == "beli":
        _, base, jumlah, tp, sl, h_tampil = bag
        sym = f"{base}USDT"
        h = m.harga.get(sym)
        if h is None:
            m.tg.kirim(f"Harga {esc(sym)} tidak ada.", chat_id=cid)
            return
        batas = float(h_tampil) * (1 + TOLERANSI_BELI)
        if h > batas:
            m.tg.kirim(f"Tidak dibeli: harga sudah {px(h)} (> {px(batas)}, +1% dari harga saat konfirmasi).", chat_id=cid)
            return
        tp_, sl_ = float(tp) / 100 or None, float(sl) / 100 or None
        pos = m.buka("manual", sym, base, h, float(jumlah), tp_, sl_, None, limit=batas, label="✋ manual")
        if not pos:
            m.tg.kirim(f"Tidak dibeli: {esc(m.gagal_terakhir or 'ditolak batas risiko')}", chat_id=cid)
    elif bag[0] == "tutup":
        pos = m.s["posisi"].get(bag[1])
        if not pos:
            m.tg.kirim("ID tidak ditemukan.", chat_id=cid)
            return
        if not m.tutup(pos, m.harga_pos(pos) or pos["entry"], "MANUAL"):
            if pos["id"] in m.s["posisi"]:
                m.tg.kirim(f"{esc(pos['simbol'])} belum tertutup penuh — lihat pesan sebelumnya / /posisi.", chat_id=cid)
    elif bag[0] == "hapus":
        pos = m.s["posisi"].get(bag[1])
        if not pos:
            m.tg.kirim("ID tidak ditemukan.", chat_id=cid)
            return
        if pos.get("tp_order") and m.broker.live:
            try:
                m.broker.batal(pos["base"], pos["tp_order"])
            except Exception as e:  # noqa: BLE001
                m.tg.kirim(f"⚠️ Order TP gagal dibatalkan ({esc(sensor(e)[:150])}) — batalkan manual di bursa.",
                           chat_id=cid)
        m.store.tutup(pos["id"], {"t_tutup": m.now(), "keluar": None, "alasan": "DIHAPUS", "pnl_usd": 0.0,
                                  "ret": 0.0, "catatan": "dihapus manual (tanpa jual); untung/rugi tidak dihitung"})
        m.store.simpan()
        m.tg.kirim(f"🗑 {esc(pos['simbol'])} ({pos['id']}) dihapus dari catatan bot. Koin (bila ada) tetap di saldo "
                   f"bursa kamu dan tidak dikelola bot.", chat_id=cid)


def tangani(m, cid: int, teks: str, cbid: str | None = None) -> None:
    if cbid:                                   # tombol konfirmasi
        jenis, _, tok = teks.partition(":")
        t, perintah, cid_asal = m.konfirmasi.pop(tok, (0, "", None))
        batas = KEDALUWARSA.get(perintah.split()[0] if perintah else "", 30)
        if not perintah or cid_asal != cid or m.now() - t > batas:
            m.tg.jawab_tombol(cbid, "Kedaluwarsa, ulangi perintah.")
            return
        m.tg.jawab_tombol(cbid, "OK" if jenis == "ya" else "Dibatalkan")
        if jenis == "ya":
            _jalankan(m, cid, perintah)
        return
    t = teks.strip()
    t = TOMBOL.get(t.lower(), t)
    if not t.startswith("/"):
        m.tg.kirim("Ketik /bantuan untuk daftar perintah.", chat_id=cid, menu=True)
        return
    cmd, *arg = t.split()
    cmd = cmd.split("@")[0].lower()
    if cmd in ("/start", "/bantuan", "/help", "/menu"):
        m.tg.kirim(BANTUAN, chat_id=cid, menu=True)
    elif cmd == "/status":
        m.tg.kirim(teks_status(m), chat_id=cid)
    elif cmd == "/posisi":
        m.tg.kirim(teks_posisi(m), chat_id=cid)
    elif cmd == "/riwayat":
        m.tg.kirim(teks_riwayat(m), chat_id=cid)
    elif cmd == "/listing":
        m.tg.kirim(teks_listing(m), chat_id=cid)
    elif cmd == "/saldo":
        kas = m.kas()
        m.tg.kirim(f"Saldo {esc(m.broker.nama)}: {usd(kas)}" if kas is not None else "Gagal baca saldo (lihat galat).",
                   chat_id=cid)
    elif cmd == "/jeda":
        m.s["jeda"] = True
        m.tg.kirim("⏸ Entry baru DIJEDA. Posisi terbuka tetap dikelola (TP/SL/batas waktu). /lanjut untuk membuka.",
                   chat_id=cid)
    elif cmd == "/lanjut":
        if m.s["pending"]:
            m.tg.kirim("🚨 Masih ada order berstatus tidak pasti. Cek aplikasi bursa dulu, lalu /beres.", chat_id=cid)
            return
        m.s["jeda"] = False
        m.tg.kirim("▶️ Entry baru diizinkan lagi.", chat_id=cid)
    elif cmd == "/beres":
        pend = m.s["pending"]
        ragu = [p for p in m.s["posisi"].values() if p.get("tidak_pasti")]
        if not pend and not ragu:
            m.tg.kirim("Tidak ada order berstatus tidak pasti.", chat_id=cid)
            return
        baris = [f"• BELI {esc(v['simbol'])} {usd(v['usd'])} id {esc(k)} ({jam(v['t'])})" for k, v in pend.items()]
        baris += [f"• JUAL {esc(p['simbol'])} posisi {p['id']}" for p in ragu]
        m.s["pending"] = {}
        for p in ragu:
            p.pop("tidak_pasti", None)
        m.store.simpan()
        m.tg.kirim("✅ Tanda tidak pasti dihapus:\n" + "\n".join(baris) + "\nBila order BELI di atas ternyata TERISI, "
                   "koinnya ada di saldo bursa tetapi TIDAK dikelola bot (jual manual bila perlu). Posisi JUAL yang "
                   "masih ada akan dicoba lagi; bila sudah terjual di bursa → /hapus ID. Bot masih dijeda: /lanjut.",
                   chat_id=cid)
    elif cmd == "/pindai":
        m.jadwal.pop("listing", None)
        m.s["spot_paksa"] = True
        m.tg.kirim("🔎 Pindai dijadwalkan sekarang (💎 di luar 07:05–08:00 WIB = hanya menampilkan sinyal).",
                   chat_id=cid)
    elif cmd == "/strategi":
        if len(arg) == 2 and arg[0] in m.strategi and arg[1] in ("mati", "hidup", "off", "on"):
            mati = set(m.s["strategi_mati"])
            (mati.add if arg[1] in ("mati", "off") else mati.discard)(arg[0])
            m.s["strategi_mati"] = sorted(mati)
        m.tg.kirim("\n".join(f"{'⛔' if n in m.s['strategi_mati'] else '✅'} {esc(n)} — {x.status_teks()}"
                             for n, x in m.strategi.items()) or "Tidak ada strategi aktif.", chat_id=cid)
    elif cmd == "/beli":
        if len(arg) < 2:
            m.tg.kirim("Format: /beli SIMBOL USD [TP%] [SL%] — mis. /beli SOL 20 5 10", chat_id=cid)
            return
        base = arg[0].upper()
        base = base[:-4] if base.endswith("USDT") and len(base) > 4 else base
        if not re.fullmatch(r"[A-Z0-9]{2,15}", base):
            m.tg.kirim("Simbol tidak valid.", chat_id=cid)
            return
        jumlah = _angka(arg[1])
        tp = _angka(arg[2]) if len(arg) > 2 else 0.0
        sl = _angka(arg[3]) if len(arg) > 3 else 0.0
        maks = float(m.cfg["risiko"]["maks_usd_per_trade"])
        if jumlah is None or tp is None or sl is None:
            m.tg.kirim("Angka tidak valid.", chat_id=cid)
            return
        if not 5 <= jumlah <= maks:
            m.tg.kirim(f"Jumlah harus $5 – {usd(maks)} (Maks per trade di config risiko).", chat_id=cid)
            return
        if not (0 <= tp <= 500 and 0 <= sl < 100):
            m.tg.kirim("TP harus 0–500%, SL 0–99% (0 = tidak dipakai).", chat_id=cid)
            return
        h = m.harga.get(f"{base}USDT")
        if h is None:
            m.tg.kirim(f"{esc(base)}USDT tidak ada di data Binance.", chat_id=cid)
            return
        mode = "LIVE (uang sungguhan)" if m.broker.live else "kertas"
        peringatan = "" if tp and sl else "\n⚠️ Tanpa " + " & ".join(x for x, v in (("TP", tp), ("SL", sl)) if not v) + \
            " — posisi ditahan sampai kamu /tutup."
        _konfirmasi(m, cid, f"Beli <b>{esc(base)}</b> {usd(jumlah)} ({mode}) di harga ±{px(h)} (maks {px(h * 1.01)})"
                            f"{f', TP +{tp:g}%' if tp else ''}{f', SL −{sl:g}%' if sl else ''}?{peringatan}\n"
                            f"Tombol berlaku 30 detik.",
                    f"beli {base} {jumlah} {tp} {sl} {h!r}")
    elif cmd in ("/tutup", "/hapus"):
        if not arg or arg[0].upper() not in m.s["posisi"]:
            m.tg.kirim(f"Format: {cmd} ID (lihat /posisi)", chat_id=cid)
            return
        p = m.s["posisi"][arg[0].upper()]
        if cmd == "/tutup":
            _konfirmasi(m, cid, f"Jual sekarang <b>{esc(p['simbol'])}</b> ({p['id']}) di harga pasar?", f"tutup {p['id']}")
        else:
            _konfirmasi(m, cid, f"Hapus <b>{esc(p['simbol'])}</b> ({p['id']}) dari catatan bot TANPA menjual?",
                        f"hapus {p['id']}")
    else:
        m.tg.kirim("Perintah tidak dikenal. /bantuan", chat_id=cid)
