"""👥 Follow / unfollow copy trader (aplikasi 4.16) — pantau posisi trader yang diikuti, kirim saat BUKA & TUTUP.

Permintaan pengguna 7 Okt 2026: "klik follow → otomatis dapat data saat trader open & tutup posisi, langsung ke apk".
API publik situs copy trade TIDAK punya push/webhook, jadi cloud memeriksa posisi tiap ±15 detik (Supabase pg_cron →
GET /api/ikuti?key=CRON_SECRET), membandingkan dengan potret sebelumnya, lalu mengirim SATU pesan ntfy ke topik
`<NTFY_TOPIC>-copy` berisi semua kejadian putaran itu (hemat kuota ntfy). Aplikasi mendengarkan topik itu terus (layanan
latar ⚡) sehingga notifikasi tiba ±1–15 detik setelah situs memperbarui posisinya.

Baris Supabase:
  ikuti      : {"list": [{platform, id, name, url, since}]}            ← ditulis aplikasi (POST /api/chat {"ikuti":…})
  ikuti_snap : {"t": iso, "traders": {kunci: {pos, status, t, kosong, ...}}, "log": [kejadian terbaru]}  ← ditulis cron
Kejadian: copy_open (posisi baru), copy_close (posisi hilang; harga tutup dari riwayat situs bila ada), copy_follow
(potret pertama setelah follow). Info saja — TIDAK ada order. MQL5 tidak membuka posisi → tidak bisa diikuti.
"""
from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import _copyposisi as cp

MAX_FOLLOW = 20
LOG_MAX = 60
T = 8                          # detik per permintaan (satu putaran harus selesai jauh di bawah 15 detik)
SITUS = ("Binance", "OKX", "Bitget", "Hyperliquid", "eToro")
BIN = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade"
HL = "https://api.hyperliquid.xyz/info"


def kunci(platform: str, id_: str) -> str:
    return f"{platform}|{id_}"


def _iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or time.time(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ posisi saja (ringan, dipanggil tiap putaran)
def pos_binance(pid: str) -> tuple[dict, str]:
    raw = cp._req(f"{BIN}/lead-data/positions?portfolioId={pid}", timeout=T).get("data") or []
    out = {}
    for p in raw:
        amt = cp._f(p.get("positionAmount"))
        if not amt:
            continue
        buy, entry, lev = amt > 0, cp._f(p.get("entryPrice")), int(float(p.get("leverage") or 1))
        pnl, margin = cp._f(p.get("unrealizedProfit")), (abs(amt) * entry / lev if entry else None)
        out[f"{p.get('symbol')}|{'L' if buy else 'S'}"] = cp._pos(
            p.get("symbol"), buy, entry, cp._f(p.get("markPrice")), lev=lev,
            pnl=pnl / margin * 100 if pnl is not None and margin else None)
    return out, ""


def terlihat_binance(pid: str) -> bool:
    d = cp._req(f"{BIN}/lead-portfolio/detail?portfolioId={pid}", timeout=T).get("data") or {}
    return bool(d.get("positionShow"))


def pos_okx(code: str) -> tuple[dict, str]:
    raw = cp._req("https://www.okx.com/api/v5/copytrading/public-current-subpositions?instType=SWAP"
                  f"&uniqueCode={code}&limit=50", timeout=T).get("data") or []
    out, hidden = {}, False
    for p in raw:
        inst = p.get("instId") or ""
        hidden |= not inst
        k = p.get("subPosId") or f"{inst}|{p.get('posSide')}|{p.get('openTime')}"
        out[k] = cp._pos(inst.replace("-SWAP", "") or "(disembunyikan)", cp.okx_side(p),
                         cp._f(p.get("openAvgPx")), cp._f(p.get("markPx")), lev=p.get("lever"),
                         pnl=(cp._f(p.get("uplRatio")) or 0) * 100) | {"buka": cp._iso(p.get("openTime"))}
    return out, "Koin posisi disembunyikan trader." if hidden else ""


def pos_bitget(uid: str) -> tuple[dict, str]:
    raw = cp._req("https://www.bitget.com/v1/trigger/trace/public/traderPosition",
                  {"languageType": 0, "traderUid": uid}, timeout=T).get("data") or []
    side = {1: True, 2: False}
    out = {}
    for p in raw:
        if not isinstance(p, dict):
            continue
        buy = side.get(p.get("holdSide"))
        out[f"{p.get('symbolId') or p.get('symbolDisplayName')}|{p.get('holdSide')}"] = cp._pos(
            p.get("symbolDisplayName"), buy, cp._f(p.get("openAvgPrice")), None, lev=p.get("openLevel")) \
            | {"buka": cp._iso(p.get("createTime"))}
    return out, ""


def pos_hyperliquid(addr: str) -> tuple[dict, str]:
    st = cp._req(HL, {"type": "clearinghouseState", "user": addr}, timeout=T) or {}
    out = {}
    for a in st.get("assetPositions") or []:
        p = a.get("position") or {}
        szi, val = cp._f(p.get("szi")) or 0, cp._f(p.get("positionValue"))
        if not szi:
            continue
        buy = szi > 0
        out[f"{p.get('coin')}|{'L' if buy else 'S'}"] = cp._pos(
            p.get("coin"), buy, cp._f(p.get("entryPx")), abs(val / szi) if val else None, None, None,
            (p.get("leverage") or {}).get("value"), (cp._f(p.get("returnOnEquity")) or 0) * 100)
    return out, ""


def tpsl_hyperliquid(addr: str) -> tuple[dict, dict]:
    tp, sl = {}, {}
    for o in cp._req(HL, {"type": "frontendOpenOrders", "user": addr}, timeout=T) or []:
        px, t = cp._f(o.get("triggerPx")), str(o.get("orderType") or "")
        if px and "Take Profit" in t:
            tp[o.get("coin")] = px
        elif px and "Stop" in t:
            sl[o.get("coin")] = px
    return tp, sl


def pos_etoro(cid: str) -> tuple[dict, str]:
    pf = cp._req(f"https://www.etoro.com/sapi/trade-data-real/live/public/portfolios?cid={cid}&format=json", timeout=T)
    out = {}
    for a in pf.get("AggregatedPositions") or []:
        buy = a.get("Direction") != "Sell"
        out[f"{a['InstrumentID']}|{'L' if buy else 'S'}"] = cp._pos(f"ID {a['InstrumentID']}", buy, None, None,
                                                                    pnl=a.get("NetProfit")) | {"iid": a["InstrumentID"]}
    return out, ""


def detail_etoro(cid: str, items: list[dict]) -> None:
    """Lengkapi posisi eToro BARU: nama instrumen, entry, TP/SL (hanya saat posisi baru muncul → hemat)."""
    ids = sorted({p["iid"] for p in items if p.get("iid")})
    if not ids:
        return
    try:
        m = cp._req("https://api.etorostatic.com/sapi/instrumentsmetadata/V1.1/instruments?InstrumentIds="
                    + ",".join(map(str, ids)), timeout=T)
        names = {x["InstrumentID"]: x.get("SymbolFull") or x.get("InstrumentDisplayName")
                 for x in m.get("InstrumentDisplayDatas") or []}
    except Exception:  # noqa: BLE001
        names = {}
    def one(p):
        iid = p.get("iid")
        if iid in names:
            p["symbol"] = names[iid]
        try:
            d = cp._req("https://www.etoro.com/sapi/trade-data-real/live/public/positions"
                        f"?cid={cid}&InstrumentID={iid}&format=json", timeout=T)
            ps = d.get("PublicPositions") or []
            last = max(ps, key=lambda q: q.get("OpenDateTime") or "") if ps else None
            p["entry"] = cp._f(d.get("AverageOpen"))
            if last:
                e = p["entry"] or cp._f(last.get("OpenRate")) or 0
                p["now"], p["lev"] = cp._f(last.get("CurrentRate")), cp._lev(last.get("Leverage"))
                tpv, slv = cp._f(last.get("TakeProfitRate")), cp._f(last.get("StopLossRate"))
                p["tp"] = tpv if tpv and e > 0 and 0.2 <= tpv / e <= 3.0 else None
                p["sl"] = slv if slv and e > 0 and 0.2 <= slv / e <= 3.0 else None
                p["buka"] = (last.get("OpenDateTime") or "")[:16] + "Z"
        except Exception:  # noqa: BLE001
            pass
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, items))


POSISI = {"Binance": pos_binance, "OKX": pos_okx, "Bitget": pos_bitget, "Hyperliquid": pos_hyperliquid,
          "eToro": pos_etoro}


def harga_tutup(platform: str, id_: str, closed: list[dict]) -> None:
    """Harga tutup dari riwayat situs (cocokkan koin & arah, trade terbaru); gagal → harga terakhir yang terlihat."""
    try:
        _, hist, _ = cp.SITUS[platform](id_)
    except Exception:  # noqa: BLE001
        hist = []
    for p in closed:
        h = next((h for h in hist if h.get("symbol") == p.get("symbol") and h.get("arah") == p.get("arah")
                  and h.get("tutup")), None)
        p["tutup"] = h["tutup"] if h else p.get("now")
        if h and not p.get("entry"):
            p["entry"] = h.get("entry")
        p["gerak"] = cp._move(p.get("entry"), p.get("tutup"), None if p.get("arah") is None else p["arah"] == "BUY")
        p["tutup_dari"] = "riwayat situs" if h else "harga terakhir terlihat"


# ------------------------------------------------------------------ satu putaran
def _eid(*parts) -> str:
    return "CP-" + hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:14]


def periksa(item: dict, old: dict, now: float, fetch=None) -> tuple[dict, list[dict]]:
    """Bandingkan posisi trader sekarang dengan potret lama → (potret baru, kejadian)."""
    platform, id_ = item["platform"], str(item["id"])
    base = {"platform": platform, "trader": id_, "name": item.get("name") or id_, "url": item.get("url", "")}
    fn = (fetch or POSISI).get(platform)
    if fn is None:
        return {"status": "MQL5 tidak membuka posisi publik — tidak bisa diikuti.", "pos": {}, "t": _iso(now)}, []
    snap = dict(old)
    try:
        cur, note = fn(id_)
    except Exception as exc:  # noqa: BLE001 - gagal baca: potret lama dipertahankan (tanpa TUTUP palsu)
        snap["gagal"] = int(old.get("gagal", 0)) + 1
        snap["status"] = f"Gagal membaca {platform}: {type(exc).__name__}"
        return snap, []
    snap.update(gagal=0, t=_iso(now))
    if platform == "Binance" and (now - float(old.get("cek_lihat", 0)) > 600):
        try:                                    # Binance: trader bisa menyembunyikan posisi (positionShow)
            snap["terlihat"], snap["cek_lihat"] = terlihat_binance(id_), now
        except Exception:  # noqa: BLE001
            pass
    if platform == "Binance" and snap.get("terlihat") is False:
        note = "Trader menyembunyikan posisi di Binance — buka/tutup tidak bisa dipantau."
    snap["status"] = note or "Dipantau"
    prev = old.get("pos")
    if prev is None:                            # potret pertama setelah follow: tanpa notifikasi per posisi
        if platform == "eToro":
            detail_etoro(id_, list(cur.values()))
        if platform == "Hyperliquid" and cur:
            try:
                tp, sl = tpsl_hyperliquid(id_)
                for p in cur.values():
                    p["tp"], p["sl"] = tp.get(p["symbol"]), sl.get(p["symbol"])
            except Exception:  # noqa: BLE001
                pass
        snap["pos"], snap["kosong"] = cur, 0
        return snap, [base | {"type": "copy_follow", "id": _eid("f", platform, id_, now), "time": _iso(now),
                              "posisi": list(cur.values())[:10], "status": snap["status"]}]
    # daftar mendadak kosong padahal tadi ada posisi → tunggu satu putaran lagi (lindungi dari respons API kosong sesaat)
    if prev and not cur and int(old.get("kosong", 0)) < 1:
        snap["kosong"] = int(old.get("kosong", 0)) + 1
        return snap, []
    snap["kosong"] = 0
    opened = [k for k in cur if k not in prev]
    closed = [k for k in prev if k not in cur]
    merged = {}
    for k, p in cur.items():                    # pertahankan info yang hanya diambil saat buka (TP/SL, nama eToro)
        q = prev.get(k) or {}
        merged[k] = {**q, **{f: v for f, v in p.items() if v is not None}} if q else p
        if platform == "eToro" and q:
            merged[k]["symbol"] = q.get("symbol", p["symbol"])
    new_items = [merged[k] for k in opened]
    if platform == "eToro" and new_items:
        detail_etoro(id_, new_items)
    if platform == "Hyperliquid" and new_items:
        try:
            tp, sl = tpsl_hyperliquid(id_)
            for p in new_items:
                p["tp"], p["sl"] = tp.get(p["symbol"]), sl.get(p["symbol"])
        except Exception:  # noqa: BLE001
            pass
    events = [base | {"type": "copy_open", "id": _eid("o", platform, id_, k, p.get("buka") or p.get("entry")),
                      "time": _iso(now)} | {f: p.get(f) for f in ("symbol", "arah", "entry", "now", "tp", "sl", "lev")}
              for k, p in zip(opened, new_items)]
    gone = [dict(prev[k]) for k in closed]
    if gone:
        harga_tutup(platform, id_, gone)
    events += [base | {"type": "copy_close", "id": _eid("c", platform, id_, k, p.get("buka") or p.get("entry")),
                       "time": _iso(now)} | {f: p.get(f) for f in ("symbol", "arah", "entry", "tutup", "gerak", "lev",
                                                                   "buka", "tutup_dari")}
               for k, p in zip(closed, gone)]
    snap["pos"] = merged
    return snap, events


def paket(events: list[dict], limit: int = 3500) -> list[list[dict]]:
    """Pecah kejadian jadi beberapa pesan < 4 KB (batas pesan ntfy); biasanya cukup satu pesan per putaran."""
    out, cur, size = [], [], 0
    for e in events:
        n = len(json.dumps(e, ensure_ascii=False).encode())
        if cur and size + n > limit:
            out.append(cur)
            cur, size = [], 0
        if n > limit and e.get("posisi"):          # potret follow yang besar: kirim 5 posisi saja
            e = e | {"posisi": e["posisi"][:5]}
        cur.append(e)
        size += n
    return out + ([cur] if cur else [])


def putaran(store, publish, now: float | None = None, fetch=None) -> dict:
    """Satu putaran cron: baca daftar follow, periksa semua trader (paralel per situs), simpan potret, kirim kejadian."""
    now = now or time.time()
    lst = ((store.get_state("ikuti") or {}).get("list") or [])[:MAX_FOLLOW]
    snap = store.get_state("ikuti_snap") or {}
    traders = snap.get("traders") or {}
    by_site: dict[str, list] = {}
    for it in lst:
        by_site.setdefault(it.get("platform"), []).append(it)

    def run_site(items):
        out = []
        for i, it in enumerate(items):
            if i and it.get("platform") == "OKX":
                time.sleep(0.45)                # OKX: maks 5 permintaan / 2 detik per IP
            k = kunci(it["platform"], str(it["id"]))
            out.append((k, *periksa(it, traders.get(k) or {}, now, fetch)))
        return out

    new_traders, events = {}, []
    if by_site:
        with ThreadPoolExecutor(len(by_site)) as ex:
            for res in ex.map(run_site, by_site.values()):
                for k, s, ev in res:
                    new_traders[k] = s
                    events += ev
    log = (events[::-1] + list(snap.get("log") or []))[:LOG_MAX]
    store.save_state({"t": _iso(now), "traders": new_traders, "log": log}, "ikuti_snap")
    for batch in paket(events):
        publish({"type": "copy", "time": _iso(now), "events": batch})
    return {"ok": True, "diikuti": len(lst), "kejadian": len(events),
            "gagal": [k for k, s in new_traders.items() if s.get("gagal")]}


# ------------------------------------------------------------------ dari aplikasi
def atur(store, item: dict, now: float | None = None) -> dict:
    """POST {"ikuti": {platform, id, name, url, on}} → simpan daftar follow (maks 20)."""
    platform, id_ = str(item.get("platform", "")), str(item.get("id", ""))[:80]
    if platform.startswith("MQL5"):
        return {"ok": False, "error": "MQL5 tidak membuka posisi publik — tidak bisa diikuti."}
    if platform not in SITUS or not id_:
        return {"ok": False, "error": "platform/id tidak dikenal"}
    lst = [x for x in ((store.get_state("ikuti") or {}).get("list") or [])
           if kunci(x.get("platform"), str(x.get("id"))) != kunci(platform, id_)]
    if item.get("on", True):
        if len(lst) >= MAX_FOLLOW:
            return {"ok": False, "error": f"Maksimal {MAX_FOLLOW} trader diikuti.", "list": lst}
        url = str(item.get("url", ""))
        lst.append({"platform": platform, "id": id_, "name": str(item.get("name", ""))[:60],
                    "url": url if url.startswith("https://") else "", "since": _iso(now)})
    store.save_state({"list": lst}, "ikuti")
    return {"ok": True, "list": lst}


def status(store, now: float | None = None) -> dict:
    """GET /api/chat?ikuti=1 → daftar follow + posisi terbuka terakhir + kejadian terbaru + umur cek terakhir."""
    now = now or time.time()
    lst = (store.get_state("ikuti") or {}).get("list") or []
    snap = store.get_state("ikuti_snap") or {}
    traders = snap.get("traders") or {}
    umur = None
    try:
        umur = int(now - datetime.fromisoformat(snap["t"].replace("Z", "+00:00")).timestamp())
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    rows = []
    for it in lst:
        s = traders.get(kunci(it.get("platform"), str(it.get("id")))) or {}
        rows.append(it | {"posisi": list((s.get("pos") or {}).values())[:15],
                          "status": s.get("status") or "Menunggu cek pertama", "cek": s.get("t")})
    pantau = ("Belum pernah dicek — pasang jadwal pg_cron /api/ikuti (docs/COPY_TRADE.md)" if umur is None else
              f"Dicek {umur} dtk lalu" if umur < 120 else
              f"⚠️ Cek terakhir {umur // 60} mnt lalu — jadwal pg_cron /api/ikuti mati?")
    return {"ok": True, "list": rows, "log": (snap.get("log") or [])[:40], "umur": umur, "pantau": pantau}


def publisher(topic: str, server: str = "https://ntfy.sh"):
    """Kirim satu pesan JSON ke topik <topic>-copy (aplikasi mendengarkan topik ini; tanpa teks ganda)."""
    import _core

    def pub(msg: dict) -> None:
        _core.http("POST", server.rstrip("/") + "/", {"Content-Type": "application/json"},
                   {"topic": topic + "-copy", "message": json.dumps(msg, ensure_ascii=False), "priority": 4},
                   timeout=10)
    return pub
