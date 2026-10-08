"""Perintah Telegram (bahasa Indonesia). Aksi uang (beli/tutup manual) selalu minta konfirmasi tombol."""
from __future__ import annotations

import secrets

from .mesin import jam, pct, px, usd
from .telegram import esc

TOMBOL = {"📊 status": "/status", "📂 posisi": "/posisi", "🧾 riwayat": "/riwayat", "🆕 listing": "/listing",
          "🔎 pindai": "/pindai", "⏸ jeda": "/jeda", "▶️ lanjut": "/lanjut", "❓ bantuan": "/bantuan"}

BANTUAN = """<b>Sniper bot — perintah</b>
/status — mode, modal, posisi, strategi, batas risiko
/posisi — posisi terbuka + untung/rugi berjalan
/riwayat — 15 trade terakhir + statistik
/listing — token baru yang dipantau (P0 & harga beli)
/pindai — pindai sekarang (listing & 💎)
/strategi — daftar strategi; <code>/strategi spot_dip mati</code> / <code>hidup</code>
/beli SIMBOL USD [TP%] [SL%] — beli manual, mis. <code>/beli SOL 20 5 10</code>
/tutup ID — jual posisi sekarang (lihat ID di /posisi)
/jeda — stop entry baru (posisi tetap dikelola) • /lanjut — buka lagi
/saldo — saldo bursa/kertas
Mode kertas/live diatur di config.yaml (bukan lewat Telegram) demi keamanan."""


def teks_status(m) -> str:
    s = m.s
    mode = "LIVE 💸" if m.broker.live else "KERTAS (simulasi)"
    try:
        kas = m.broker.saldo_usd()
    except Exception as e:  # noqa: BLE001
        kas = float("nan")
        m.galat("saldo", e)
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
    return (f"Mode <b>{mode}</b> • bursa {esc(m.broker.nama)}\n"
            f"Kas {usd(kas)} • posisi {len(s['posisi'])} senilai {usd(eks)} • ekuitas {usd(kas + eks)}\n"
            f"Hari ini (UTC): untung/rugi tertutup {usd(h['pnl'])}, trade {h['trade']}"
            + (" • ⛔ jeda rugi harian" if h.get("jeda_rugi") else "") + "\n"
            f"Riwayat: {len(riw)} trade, menang {menang} ({(menang / len(riw) * 100) if riw else 0:.0f}%), "
            f"total {usd(total)}\n"
            f"Batas: {usd(r['maks_usd_per_trade'])}/trade, total {usd(r['maks_total_usd'])}, "
            f"maks {r['maks_posisi']} posisi, stop rugi harian {usd(r['stop_rugi_harian_usd'])}\n"
            + ("⏸ <b>DIJEDA</b> (/lanjut)\n" if s["jeda"] else "")
            + "\n".join(st)
            + (f"\nHarga terakhir {jam(m.t_harga)}" if m.t_harga else ""))


def teks_posisi(m) -> str:
    if not m.s["posisi"]:
        return "Tidak ada posisi terbuka."
    out = []
    for p in m.s["posisi"].values():
        h = m.harga.get(p["simbol"])
        ret = (h / p["entry"] - 1) if h else 0.0
        out.append(f"<b>{p['id']}</b> {esc(p['simbol'])} ({esc(p['strategi'])}) masuk {px(p['entry'])} • kini "
                   f"{px(h) if h else '?'} ({pct(ret)}) • {usd(p['usd'])}\n"
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
            f"• {t.get('alasan', '')} • {jam(t.get('t_tutup', 0))}" for t in riw[:n]]
    return head + "\n\n" + "\n".join(rows)


def teks_listing(m) -> str:
    L = m.s["listing"]
    aktif = [(k, d) for k, d in L.items() if d["status"] in ("pantau", "menunggu_p0", "dibeli")]
    if not aktif:
        return "Belum ada token baru (≤ 30 hari) yang dipantau." + (
            f" Antrian cek waktu listing: {len(m.s.get('listing_antri', []))}." if m.s.get("listing_antri") else "")
    out = []
    for k, d in sorted(aktif, key=lambda x: -x[1]["t_listing"]):
        h = m.harga.get(k)
        if d["p0"]:
            jarak = (h / d["limit"] - 1) if h else None
            out.append(f"<b>{esc(k)}</b> {d['status']} • listing {jam(d['t_listing'])}\n   P0 {px(d['p0'])} → beli ≤ "
                       f"{px(d['limit'])} • kini {px(h) if h else '?'}"
                       + (f" ({pct(jarak)} di atas harga beli)" if jarak is not None and jarak > 0 else ""))
        else:
            out.append(f"<b>{esc(k)}</b> menunggu P0 • listing {jam(d['t_listing'])}")
    return "\n".join(out[:40])


def _konfirmasi(m, cid: int, teks: str, perintah: str) -> None:
    tok = secrets.token_hex(4)
    m.konfirmasi[tok] = (m.now(), perintah)
    m.tg.kirim(teks, chat_id=cid, tombol=[[{"text": "✅ Ya, lakukan", "callback_data": f"ya:{tok}"},
                                           {"text": "❌ Batal", "callback_data": f"tidak:{tok}"}]])


def _jalankan(m, cid: int, perintah: str) -> None:
    bag = perintah.split()
    if bag[0] == "beli":
        _, base, jumlah, tp, sl = bag
        sym = f"{base}USDT"
        h = m.harga.get(sym)
        if h is None:
            m.tg.kirim(f"Harga {esc(sym)} tidak ada.", chat_id=cid)
            return
        tp_, sl_ = float(tp) / 100 or None, float(sl) / 100 or None
        pos = m.buka("manual", sym, base, h, float(jumlah), tp_, sl_, None, label="✋ manual")
        if not pos:
            m.tg.kirim(f"Tidak dibeli: {esc(m.gagal_terakhir or 'ditolak batas risiko')}", chat_id=cid)
    elif bag[0] == "tutup":
        pos = m.s["posisi"].get(bag[1])
        if not pos:
            m.tg.kirim("ID tidak ditemukan.", chat_id=cid)
            return
        m.tutup(pos, m.harga.get(pos["simbol"], pos["entry"]), "MANUAL")


def tangani(m, cid: int, teks: str, cbid: str | None = None) -> None:
    if cbid:                                   # tombol konfirmasi
        jenis, _, tok = teks.partition(":")
        t, perintah = m.konfirmasi.pop(tok, (0, ""))
        if not perintah or m.now() - t > 120:
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
        try:
            m.tg.kirim(f"Saldo {esc(m.broker.nama)}: {usd(m.broker.saldo_usd())}", chat_id=cid)
        except Exception as e:  # noqa: BLE001
            m.tg.kirim(f"Gagal baca saldo: {esc(e)}", chat_id=cid)
    elif cmd == "/jeda":
        m.s["jeda"] = True
        m.tg.kirim("⏸ Entry baru DIJEDA. Posisi terbuka tetap dikelola (TP/SL/batas waktu). /lanjut untuk membuka.",
                   chat_id=cid)
    elif cmd == "/lanjut":
        m.s["jeda"] = False
        m.tg.kirim("▶️ Entry baru diizinkan lagi.", chat_id=cid)
    elif cmd == "/pindai":
        m.jadwal.pop("listing", None)
        m.s["spot_paksa"] = True
        m.tg.kirim("🔎 Pindai dijadwalkan sekarang.", chat_id=cid)
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
        base = arg[0].upper().replace("USDT", "")
        try:
            jumlah = float(arg[1])
            tp = float(arg[2]) if len(arg) > 2 else 0.0
            sl = float(arg[3]) if len(arg) > 3 else 0.0
        except ValueError:
            m.tg.kirim("Angka tidak valid.", chat_id=cid)
            return
        if jumlah > float(m.cfg["risiko"]["maks_usd_per_trade"]):
            m.tg.kirim(f"Maks {usd(m.cfg['risiko']['maks_usd_per_trade'])} per trade (config risiko).", chat_id=cid)
            return
        h = m.harga.get(f"{base}USDT")
        mode = "LIVE (uang sungguhan)" if m.broker.live else "kertas"
        _konfirmasi(m, cid, f"Beli <b>{esc(base)}</b> {usd(jumlah)} ({mode}) di harga ±{px(h) if h else '?'}"
                            f"{f', TP +{tp:g}%' if tp else ''}{f', SL −{sl:g}%' if sl else ''}?",
                    f"beli {base} {jumlah} {tp} {sl}")
    elif cmd == "/tutup":
        if not arg or arg[0].upper() not in m.s["posisi"]:
            m.tg.kirim("Format: /tutup ID (lihat /posisi)", chat_id=cid)
            return
        p = m.s["posisi"][arg[0].upper()]
        _konfirmasi(m, cid, f"Jual sekarang <b>{esc(p['simbol'])}</b> ({p['id']}) di harga pasar?", f"tutup {p['id']}")
    else:
        m.tg.kirim("Perintah tidak dikenal. /bantuan", chat_id=cid)
