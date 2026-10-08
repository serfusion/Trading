"""💎 Spot dip -> bot Telegram mandiri: fixture paritas & uji jujur spesifikasi — python -m research.spot_paritas [fixture|uji]

Permintaan pengguna (8 Okt 2026): bot sniper Telegram otomatis dengan strategi yang sudah teruji bertahun-tahun, terpisah
dari aplikasi. Bagian riset ini menyiapkan pemindahan 💎 spot dip (cloud/api/_spot.py) ke bot mandiri:

  fixture  -> tests/data/spot_dip_paritas.json: >= 30 contoh (koin, tanggal, bar harian input, bar BTC, fitur
              cloud/api/_spot.features, prob, red_rule, vol_rank, keputusan spot_tick ASLI, hasil CLOSE spot_tick ASLI,
              label riset). Semua angka harapan dihitung dengan fungsi cloud/api/_spot.py branch ini (file cloud TIDAK
              diubah; spot_tick dijalankan dengan store/pub/fetch palsu di memori, tanpa jaringan).
  uji      -> docs/eksternal/hasil_spot_paritas.txt: varian spesifikasi (terpasang di branch ini, bawaan bot sniper,
              tanpa bias penyintas, versi 100 koin + kualitas) dengan model WALK-FORWARD, LAMA (< Okt 2021) / BARU,
              per tahun, biaya 0,30% dan 0,60%, pembanding acak.

Data: data/research/eksternal/spot_1d/<KOIN>.parquet (kline 1d Binance dari data.binance.vision, termasuk koin yang sudah
dihapus). Sebagian file memakai kolom 'qvol', sebagian 'qv' (dua sesi pengunduh) -> dinormalkan ke 'qv' di sini.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "research" / "eksternal" / "spot_1d"
FIXTURE = ROOT / "tests" / "data" / "spot_dip_paritas.json"
OUT = ROOT / "docs" / "eksternal" / "hasil_spot_paritas.txt"
SPLIT = pd.Timestamp("2021-10-01", tz="UTC")
END = pd.Timestamp("2026-10-01", tz="UTC")
DAY = timedelta(days=1)
N_BAR = 400          # bar harian tutup per contoh (SMA200 + jendela vol_rank 365 + umur/puncak 1 tahun)
N_BTC = 210          # bar BTC tutup per contoh (fitur butuh >= 201 tanggal BTC <= tanggal koin)
N_SESUDAH = 11       # bar sesudah tanggal sinyal: hari entry + 10 hari (cek TP / batas waktu)
# filter kualitas yang diuji (research/spot_jatuh.py KUALITAS, versi cloud 870aed1c)
KUALITAS = {"umur_min": 365, "vol_panik": 3.0, "ambruk": -0.80}
# bukan koin bergerak bebas (gabungan research/spot_semua.STABLE + cloud 870aed1c SKIP)
SKIP = {"USDT", "USDC", "FDUSD", "TUSD", "USDP", "DAI", "BUSD", "USDE", "PYUSD", "RLUSD", "USD1", "BFUSD", "XUSD",
        "USDS", "FRAX", "LUSD", "GUSD", "UST", "USTC", "USDD", "SUSD", "USDJ", "EURC", "EUR", "EURI", "AEUR", "GBP",
        "TRY", "BRL", "AUD", "JPY", "ARS", "MXN", "ZAR", "PLN", "RON", "UAH", "IDRT", "BIDR", "BVND", "PAXG", "XAUT",
        "WBTC", "WBETH", "BETH", "STETH", "WSTETH", "BNSOL", "CBETH", "RETH", "WETH", "PAX", "BKRW", "RUB", "NGN",
        "USDSOLD", "U", "KGST", "BNCB"}


# ====================================================================== data
def muat(sym: str) -> pd.DataFrame | None:
    """Kline 1d satu koin: kolom open/high/low/close/qv, indeks UTC urut, tanpa duplikat/stempel waktu rusak."""
    f = DIR / f"{sym}.parquet"
    if not f.exists():
        return None
    d = pd.read_parquet(f)
    if d.empty:
        return None
    if "qvol" in d.columns:
        d = d.rename(columns={"qvol": "qv"})
    d = d[(d.index >= pd.Timestamp("2017-01-01", tz="UTC")) & (d.index < pd.Timestamp("2030-01-01", tz="UTC"))]
    d = d[~d.index.duplicated()].sort_index()
    d = d[(d.close > 0) & (d.low > 0)]
    return d[["open", "high", "low", "close", "qv"]].astype(float)


def segs(d: pd.DataFrame, min_len: int = 120) -> list[pd.DataFrame]:
    """Potong di celah > 3 hari (mis. LUNA lama vs LUNA baru); segmen < min_len hari dibuang (sama spot_jatuh)."""
    cut = np.where(d.index.to_series().diff() > pd.Timedelta(days=3))[0]
    out, a = [], 0
    for b in list(cut) + [len(d)]:
        if b - a >= min_len:
            out.append(d.iloc[a:b])
        a = b
    return out


def cloud():
    """Modul cloud/api/_spot.py & _core.py branch ini (tanpa mengubah file; tanpa env)."""
    p = str(ROOT / "cloud" / "api")
    if p not in sys.path:
        sys.path.insert(0, p)
    import _core  # noqa: F401
    import _spot
    return _spot


# ====================================================================== fixture
def _bar(t, o, h, lo, c):
    import _core
    return _core.Bar(t.to_pydatetime() if hasattr(t, "to_pydatetime") else t, float(o), float(h), float(lo), float(c))


def _rows(d: pd.DataFrame) -> list[list]:
    return [[t.strftime("%Y-%m-%d"), float(o), float(h), float(lo), float(c), float(q)]
            for t, o, h, lo, c, q in zip(d.index, d.open, d.high, d.low, d.close, d.qv)]


def _cbars(rows: list[list]) -> list:
    return [_bar(datetime.fromisoformat(r[0]).replace(tzinfo=timezone.utc), r[1], r[2], r[3], r[4]) for r in rows]


class _Store:
    def __init__(self):
        self.state = None

    def get_state(self):
        return json.loads(json.dumps(self.state)) if self.state is not None else None

    def save_state(self, s):
        self.state = json.loads(json.dumps(s))


class _Pub:
    def __init__(self):
        self.ev = []

    def publish(self, event, text=None, title=None, priority=3, tags=None):
        self.ev.append({"event": event, "text": text, "title": title})


def label_riset(rows_after: list[list], tp: float, n: int, cost: float) -> dict | None:
    """Label riset (research/spot_peluang.labels): beli open hari entry, limit jual +tp dalam n hari, else close hari ke-n."""
    if len(rows_after) < n:
        return None
    e = rows_after[0][1]
    tgt = e * (1 + tp)
    for k in range(n):
        r = rows_after[k]
        if r[2] >= tgt:
            px = max(r[1], tgt) if k > 0 else tgt
            return {"entry": e, "tp": tgt, "kena_tp": True, "keluar": px, "tanggal_keluar": r[0], "hari_ke": k,
                    "r": px / e - 1 - cost}
    r = rows_after[n - 1]
    return {"entry": e, "tp": tgt, "kena_tp": False, "keluar": r[4], "tanggal_keluar": r[0], "hari_ke": n - 1,
            "r": r[4] / e - 1 - cost}


def sim_spot_tick(sp, coin: str, coin_rows: list[list], btc_rows: list[list], after: list[list],
                  btc_after: list[list], max_open: int = 10) -> dict:
    """Jalankan cloud/api/_spot.spot_tick ASLI: pindai 00:05 UTC hari entry (candle hari ini 'berjalan' = open saja),
    lalu cek posisi tiap hari 23:30 UTC (candle hari itu dianggap lengkap) sampai CLOSE atau batas waktu."""
    full = {coin: coin_rows + after, "BTC": btc_rows + btc_after}
    if coin == "BTC":
        full["BTC"] = coin_rows + after
    day0 = datetime.fromisoformat(after[0][0]).replace(tzinfo=timezone.utc)
    clock = {"now": day0 + timedelta(minutes=5)}

    def fetch(c, n, key, budget):
        rows = full.get(c)
        if rows is None:
            raise RuntimeError(f"{c}: tidak ada di fixture")
        now = clock["now"]
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        closed = [r for r in rows if datetime.fromisoformat(r[0]).replace(tzinfo=timezone.utc) + DAY <= now]
        run = [r for r in rows if datetime.fromisoformat(r[0]).replace(tzinfo=timezone.utc) == today]
        bars = _cbars(closed[-(n - 1):])
        if run:
            r = run[0]
            if now - today < timedelta(hours=1):          # baru buka: harga sekarang = open
                bars.append(_bar(today, r[1], r[1], r[1], r[1]))
            else:                                         # akhir hari: candle hampir lengkap
                bars.append(_bar(today, r[1], r[2], r[3], r[4]))
        return bars, "fixture"

    model_coins = sp.MODEL["coins"]
    sp.MODEL["coins"] = [coin]                     # hanya koin contoh yang dipindai (tanpa mengubah file)
    try:
        store, pub = _Store(), _Pub()
        res = sp.spot_tick(clock["now"], store, pub, None, max_open=max_open, fetch=fetch)
        sig = [e["event"] for e in pub.ev if e["event"].get("type") == "spot_signal"]
        out = {"spot_tick": {"ok": res.get("ok"), "errors": res.get("errors")}}
        if not sig:
            out["beli"] = False
            return out
        ev = sig[0]
        out.update({"beli": True, "alasan": ev["alasan"], "p_persen": ev["p"], "entry": ev["entry"], "tp": ev["tp"],
                    "deadline": ev["deadline"], "id": ev["id"]})
        for k in range(0, 12):
            clock["now"] = day0 + k * DAY + timedelta(hours=23, minutes=30)
            st = store.get_state()
            st["scan"] = {"day": clock["now"].strftime("%Y-%m-%d"), "todo": [], "found": 0}   # tanpa pindai ulang
            store.save_state(st)
            pub.ev.clear()
            sp.spot_tick(clock["now"], store, pub, None, max_open=max_open, fetch=fetch)
            cl = [e["event"] for e in pub.ev if e["event"].get("type") == "spot_close"]
            if cl:
                c = cl[0]
                out["close"] = {"alasan": c["reason"], "exit": c["exit"], "r_persen": c["r"], "waktu": c["time"],
                                "hari_ke": k}
                break
        return out
    finally:
        sp.MODEL["coins"] = model_coins


def kualitas_riset(d_full: pd.DataFrame, t: pd.Timestamp) -> dict:
    """Komponen filter kualitas versi riset (spot_jatuh): umur sejak bar pertama koin, jarak dari high 365 hari,
    volume hari t / rata-rata 30 hari TERMASUK hari t. Juga varian bot sniper: volume t / rata-rata 30 hari SEBELUM t."""
    d = d_full[d_full.index <= t]
    age = (t - d_full.index[0]).days
    dd365 = d.close.iloc[-1] / d.high.iloc[-365:].max() - 1 if len(d) >= 200 else None
    q = d.qv.to_numpy()
    rel_riset = q[-1] / q[-30:].mean() if len(q) >= 30 and q[-30:].mean() > 0 else None
    rel_sebelum = q[-1] / q[-31:-1].mean() if len(q) >= 31 and q[-31:-1].mean() > 0 else None
    why = None
    if age < KUALITAS["umur_min"]:
        why = "koin < 1 tahun"
    elif dd365 is not None and dd365 <= KUALITAS["ambruk"]:
        why = "ambruk >= 80% dari puncak 1 tahun"
    elif rel_riset is not None and rel_riset >= KUALITAS["vol_panik"]:
        why = "volume panik >= 3x"
    return {"umur_hari": int(age), "dd365": None if dd365 is None else float(dd365),
            "qv_rel_riset": None if rel_riset is None else float(rel_riset),
            "qv_rel_30_sebelum": None if rel_sebelum is None else float(rel_sebelum), "lewati_riset": why}


def kandidat(sp, coins: list[str], btc: pd.DataFrame) -> pd.DataFrame:
    """Semua (koin, tanggal) dengan fitur riset + peluang model cloud -> dipakai MEMILIH contoh (angka harapan tetap
    dihitung ulang dengan fungsi cloud pada jendela 400 bar)."""
    from .spot_peluang import FEATS, features, labels
    rows = []
    for coin in coins:
        d0 = muat(coin)
        if d0 is None:
            continue
        for d in segs(d0, 260):
            f = features(d, btc).join(labels(d, sp.MODEL["tp"], int(sp.MODEL["hari"])))
            f["gap"] = (f.hit == 1) & (f.r > sp.MODEL["tp"] - sp.MODEL.get("biaya", 0.003) + 1e-9)
            f["vr"] = f.vol14.rolling(365, min_periods=120).rank(pct=True)
            f = f.iloc[200:].replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS)
            f = f[f.index <= d.index[-1] - pd.Timedelta(days=N_SESUDAH)]
            if f.empty:
                continue
            X = f[FEATS].to_numpy()
            f["p"] = [sp.prob(list(x)) for x in X]
            f["rule"] = (f.red >= 3) & (f.r3 <= -0.10) & (f.d200 > 0)
            f["coin"] = coin
            rows.append(f[["p", "rule", "vr", "btc_up", "red", "r3", "d200", "hit", "gap", "coin"]])
    return pd.concat(rows)


def pilih(c: pd.DataFrame, thr: float, skip_vol: float) -> list[tuple[str, pd.Timestamp, str]]:
    """Contoh per kategori, LAMA & BARU, acak dengan seed tetap."""
    rng = np.random.default_rng(2026)
    model = (c.p >= thr)
    vol_ok = ~(c.vr > skip_vol)
    cats = {
        "model": model & ~c.rule & vol_ok & (c.btc_up == 1),
        "3 merah": ~model & c.rule & vol_ok & (c.btc_up == 1),
        "model + 3 merah": model & c.rule & vol_ok,
        "dilewati vol > P90": (model | c.rule) & (c.vr > skip_vol),
        "BTC di bawah SMA200": (model | c.rule) & vol_ok & (c.btc_up == 0),
        "dekat ambang (di atas)": (c.p >= thr) & (c.p < thr + 0.004) & ~c.rule & vol_ok,
        "dekat ambang (di bawah)": (c.p >= thr - 0.004) & (c.p < thr) & ~c.rule & vol_ok,
        "sinyal gagal (batas waktu)": (model | c.rule) & vol_ok & (c.hit == 0),
        "TP lewat gap open": (model | c.rule) & vol_ok & c.gap,
        "bukan sinyal": (c.p < 0.8) & ~c.rule,
    }
    jumlah = {"model": 3, "3 merah": 2, "model + 3 merah": 1, "dilewati vol > P90": 2, "BTC di bawah SMA200": 2,
              "dekat ambang (di atas)": 1, "dekat ambang (di bawah)": 1, "sinyal gagal (batas waktu)": 2,
              "TP lewat gap open": 1, "bukan sinyal": 1}
    out, used = [], set()
    for cat, m in cats.items():
        for per, pm in (("LAMA", c.index < SPLIT), ("BARU", c.index >= SPLIT)):
            x = c[m & pm]
            if x.empty:
                continue
            k = min(jumlah[cat], len(x))
            for i in rng.choice(len(x), size=len(x), replace=False):
                if k == 0:
                    break
                key = (x.coin.iloc[i], x.index[i])
                if key in used or any(u[0] == key[0] and abs((u[1] - key[1]).days) < 30 for u in used):
                    continue
                used.add(key)
                out.append((key[0], key[1], cat))
                k -= 1
    return out


def contoh(sp, coin: str, t: pd.Timestamp, kategori: str, btc_full: pd.DataFrame, n_bar: int = N_BAR) -> dict:
    d_full = muat(coin)
    d = d_full[d_full.index <= t].iloc[-n_bar:]
    after = d_full[d_full.index > t].iloc[:N_SESUDAH]
    b = btc_full[btc_full.index <= t].iloc[-(n_bar if coin == "BTC" else N_BTC):]
    b_after = btc_full[btc_full.index > t].iloc[:N_SESUDAH]
    rows, brow, arow, barow = _rows(d), _rows(b), _rows(after), _rows(b_after)
    if coin == "BTC":
        brow = rows
    cb, cbt = _cbars(rows), _cbars(brow)
    x = sp.features(cb, cbt)
    vr = sp.vol_rank(cb)
    exp = {"features": x, "fitur": dict(zip(sp.MODEL["fitur"], x)) if x else None, "vol_rank": vr,
           "prob": sp.prob(x) if x else None, "red_rule": sp.red_rule(x) if x else None}
    btc_c = [r[4] for r in brow]
    exp["btc_atas_sma200"] = (btc_c[-1] > sum(btc_c[-200:]) / 200) if len(btc_c) >= 200 else None
    exp["lolos_vol"] = None if vr is None else not (vr > sp.MODEL.get("skip_vol", 1.1))
    exp["kualitas"] = kualitas_riset(d_full, t)
    exp["cloud_branch_ini"] = sim_spot_tick(sp, coin, rows, brow, arow, barow) if len(arow) >= N_SESUDAH else None
    lab = label_riset(arow[:10], sp.MODEL["tp"], int(sp.MODEL["hari"]), sp.MODEL.get("biaya", 0.003)) \
        if len(arow) >= 10 else None
    exp["label_riset"] = lab
    cb_ = exp["cloud_branch_ini"] or {}
    sinyal_cloud = bool(cb_.get("beli"))
    exp["bot_bawaan_beli"] = sinyal_cloud and bool(exp["btc_atas_sma200"])        # + filter BTC > SMA200 (config bot)
    exp["bot_kualitas_beli"] = exp["bot_bawaan_beli"] and exp["kualitas"]["lewati_riset"] is None
    return {"id": f"{coin}-{t:%Y%m%d}", "koin": coin, "tanggal": t.strftime("%Y-%m-%d"),
            "waktu_pindai": (t + DAY + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "periode": "LAMA" if t < SPLIT else "BARU", "kategori_pilih": kategori,
            "bars": rows, "btc_bars": None if coin == "BTC" else brow, "sesudah": arow,
            "btc_sesudah": None if coin == "BTC" else barow, "harapan": exp}


def fixture() -> None:
    sp = cloud()
    from .spot_peluang import LIVE
    btc = muat("BTC")
    thr, skip_vol = sp.MODEL["ambang"], sp.MODEL.get("skip_vol", 1.1)
    cand = kandidat(sp, LIVE, btc)
    picks = pilih(cand, thr, skip_vol)
    # contoh khusus: koin di luar 20 (filter kualitas, data pendek), BTC sendiri, hari 'red' = 6
    extra = []
    for coin in ("SUI", "PEPE", "WLD", "ARB", "TRUMP", "FTT", "LUNC", "APT"):
        d0 = muat(coin)
        if d0 is None:
            continue
        sg = segs(d0, 260)
        if not sg:
            continue
        d = sg[-1] if coin != "FTT" else sg[0]
        extra.append((coin, d))
    ex_picks = []
    # SUI umur < 1 tahun tapi fitur ada (hari ke-250); TRUMP data < 201 hari (fitur None); FTT ambruk >= 80%;
    # volume panik: hari dengan qv >= 3x rata-rata 30 hari di koin baru (PEPE/WLD/ARB)
    for coin, d in extra:
        if coin == "SUI":
            ex_picks.append((coin, d.index[250], "kualitas: umur < 1 tahun"))
        elif coin == "TRUMP":
            ex_picks.append((coin, d.index[150], "data < 201 hari"))
        elif coin == "FTT":
            dd = d.close / d.high.rolling(365, min_periods=200).max() - 1
            idx = dd[(dd <= -0.85) & (d.index > pd.Timestamp("2022-12-01", tz="UTC"))].index
            if len(idx):
                ex_picks.append((coin, idx[len(idx) // 3], "kualitas: ambruk >= 80%"))
        elif coin in ("PEPE", "WLD", "ARB"):
            rel = d.qv / d.qv.rolling(30).mean()
            idx = rel[(rel >= 3) & (d.index >= d.index[0] + pd.Timedelta(days=380))].index
            if len(idx):
                ex_picks.append((coin, idx[0], "kualitas: volume panik"))
        elif coin in ("LUNC", "APT"):
            ex_picks.append((coin, d.index[min(len(d) - 20, 420)], "koin di luar 20 (pindai bila semesta diperluas)"))
    bd = btc[btc.index >= pd.Timestamp("2019-01-01", tz="UTC")]
    ex_picks.append(("BTC", bd.index[len(bd) // 2], "BTC sebagai koin (bars = btc)"))
    red6 = cand[(cand.red >= 6)]
    if len(red6):
        ex_picks.append((red6.coin.iloc[0], red6.index[0], "hari merah dipotong 6"))
    out = []
    for coin, t, cat in picks + ex_picks:
        out.append(contoh(sp, coin, t, cat, btc))
    model_bytes = (ROOT / "cloud" / "api" / "spot_model.json").read_bytes()
    meta = {
        "dibuat": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "pembuat": "python -m research.spot_paritas fixture",
        "sumber_kode": "cloud/api/_spot.py (branch ini; versi 20 koin, pindai harian, lewati vol > P90)",
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
        "model": {k: sp.MODEL[k] for k in ("tp", "hari", "ambang", "aturan_merah", "biaya", "fitur", "coins",
                                            "skip_vol")},
        "kualitas_riset": KUALITAS,
        "format_bar": ["tanggal_utc_buka", "open", "high", "low", "close", "volume_quote_usdt"],
        "cara_pakai": (
            "bars = candle harian TUTUP s.d. 'tanggal' (urut, terakhir = tanggal). btc_bars = candle BTC tutup s.d. "
            "tanggal (null bila koin = BTC: pakai bars). harapan.features = cloud _spot.features(bars, btc_bars) persis "
            "(urutan model.fitur), prob = _spot.prob, red_rule = _spot.red_rule, vol_rank = _spot.vol_rank(bars). "
            "cloud_branch_ini = hasil spot_tick ASLI (pindai 00:05 UTC hari sesudah 'tanggal' dengan harga = open "
            "hari itu; cek posisi 23:30 UTC tiap hari dengan candle hari itu dianggap lengkap). label_riset = "
            "research/spot_peluang.labels (beli open hari entry, limit +3%, close hari ke-10). Toleransi: fitur/prob "
            "rel 1e-12; keputusan & alasan harus sama persis."),
        "catatan": [
            "RSI dihitung rekursif dari bar pertama: hasil bergantung (sangat kecil) pada panjang riwayat. Untuk "
            "paritas, beri fungsi bot PERSIS bars fixture (400 bar). Live: cloud mengambil 420 bar (419 tutup).",
            "bot_bawaan_beli = cloud_branch_ini.beli DAN btc_atas_sma200 (config sniper_bot filter_btc_sma200: true).",
            "bot_kualitas_beli = bot_bawaan_beli DAN kualitas.lewati_riset null (definisi riset spot_jatuh: volume "
            "hari t / rata-rata 30 hari TERMASUK t; qv_rel_30_sebelum = varian tanpa hari t).",
        ],
    }
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps({**meta, "contoh": out}, ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")
    # ringkasan
    n_beli = sum(1 for e in out if (e["harapan"]["cloud_branch_ini"] or {}).get("beli"))
    cocok = 0
    for e in out:
        cb, lab = e["harapan"]["cloud_branch_ini"] or {}, e["harapan"]["label_riset"]
        if cb.get("close") and lab:
            if abs(cb["close"]["r_persen"] - round(lab["r"] * 100, 2)) < 0.011:
                cocok += 1
    print(f"fixture {FIXTURE.relative_to(ROOT)}: {len(out)} contoh, {FIXTURE.stat().st_size / 1e6:.2f} MB, "
          f"cloud BELI {n_beli}, CLOSE cloud == label riset {cocok}/{n_beli}")
    for e in out:
        h = e["harapan"]
        cb = h["cloud_branch_ini"] or {}
        print(f"  {e['id']:18} {e['kategori_pilih']:34} p={h['prob'] if h['prob'] is None else round(h['prob'], 4)} "
              f"rule={h['red_rule']} vr={None if h['vol_rank'] is None else round(h['vol_rank'], 3)} "
              f"btc_up={h['btc_atas_sma200']} cloud={'BELI ' + cb.get('alasan', '') if cb.get('beli') else '-'} "
              f"close={cb.get('close', {}).get('r_persen') if cb.get('close') else '-'} "
              f"riset_r={None if not h['label_riset'] else round(h['label_riset']['r'] * 100, 2)} "
              f"kualitas={h['kualitas']['lewati_riset']}")


def cek_panjang(sp, coins: list[str], step: int = 23) -> str:
    """Pengaruh panjang riwayat (400 vs semua bar) pada fitur, peluang, dan keputusan."""
    btc = muat("BTC")
    mx_f, mx_p, flip, n = 0.0, 0.0, 0, 0
    for coin in coins:
        d = muat(coin)
        if d is None or len(d) < 900:
            continue
        cb_all = _cbars(_rows(d))
        bt_all = _cbars(_rows(btc))
        bdates = [b.t for b in bt_all]
        for end in range(700, len(cb_all), step):
            full = cb_all[:end]
            short = full[-N_BAR:]
            last = full[-1].t
            k = int(np.searchsorted(np.array([x.timestamp() for x in bdates]), last.timestamp(), side="right"))
            bt = bt_all[:k][-420:]
            x1, x2 = sp.features(full, bt), sp.features(short, bt)
            if x1 is None or x2 is None:
                continue
            n += 1
            mx_f = max(mx_f, max(abs(a - b) for a, b in zip(x1, x2)))
            p1, p2 = sp.prob(x1), sp.prob(x2)
            mx_p = max(mx_p, abs(p1 - p2))
            thr = sp.MODEL["ambang"]
            if (p1 >= thr) != (p2 >= thr):
                flip += 1
    return (f"Panjang riwayat 400 bar vs semua bar ({n} titik, {len(coins)} koin): selisih fitur maks {mx_f:.2e}, "
            f"selisih peluang maks {mx_p:.2e}, keputusan ambang berbeda {flip} kali")


# ====================================================================== uji jujur (walk-forward)
def build(stable_skip: set[str] = SKIP) -> tuple[pd.DataFrame, dict]:
    from .spot_peluang import FEATS, features, labels
    btc = muat("BTC")
    rows, data = [], {}
    for f in sorted(DIR.glob("*.parquet")):
        coin = f.stem
        if coin in stable_skip:
            continue
        d0 = muat(coin)
        if d0 is None or len(d0) < 260:
            continue
        ss = segs(d0)
        if not ss:
            continue
        data[coin] = ss
        first = d0.index[0]
        for si, d in enumerate(ss):
            name = f"{coin}#{si}" if len(ss) > 1 else coin
            x = features(d, btc).join(labels(d, 0.03, 10))
            x["vr"] = x.vol14.rolling(365, min_periods=120).rank(pct=True)       # = cloud vol_rank (seluruh segmen)
            c = d.close
            x["dd365"] = c / d.high.rolling(365, min_periods=200).max() - 1
            x["age"] = (d.index - first).days
            q = d.qv.shift(1)
            x["qv7"] = q.rolling(7).mean()
            x["qv_rel"] = d.qv / d.qv.rolling(30).mean()
            x["qv_rel_seb"] = d.qv / d.qv.shift(1).rolling(30).mean()
            k = x.k.to_numpy()
            e = d.open.shift(-1).to_numpy()
            lo = d.low.to_numpy()
            mdd = np.full(len(d), np.nan)
            for i in range(len(d) - 1):
                if k[i] >= i + 1:
                    mdd[i] = lo[i + 1:k[i] + 1].min() / e[i] - 1
            x["mdd"] = mdd
            x["e"] = e
            x["t_in"] = pd.Series(d.index, index=d.index).shift(-1)
            x["t_out"] = [d.index[j] if j >= 0 else pd.NaT for j in k.astype(int)]
            x["coin"], x["base"] = name, coin
            rows.append(x.iloc[200:])
    df = pd.concat(rows)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS + ["hit"])
    df = df[df.index < END]
    df["rank"] = df.groupby(level=0).qv7.rank(ascending=False, method="first")
    return df.sort_index(kind="stable"), data


def take(sig: pd.DataFrame, order: dict | None = None) -> pd.DataFrame:
    """Satu posisi per koin; sinyal berikutnya hanya setelah posisi sebelumnya keluar (= cloud 'coin in open_')."""
    out = []
    for coin, g in sig.sort_index().groupby("coin"):
        free = None
        for t, r in g.iterrows():
            if free is not None and r.t_in <= free:
                continue
            out.append({"coin": coin, "base": r.base, "t": r.t_in, "t_out": r.t_out, "e": r.e, "r": r.r,
                        "mdd": r.mdd, "ord": (order or {}).get(r.base, 999)})
            free = r.t_out
    return pd.DataFrame(out)


def portfolio(tr: pd.DataFrame, data: dict, slots: int, start, end, extra_cost: float = 0.0) -> dict:
    """research/spot_dip2.portfolio dengan urutan sinyal per hari mengikuti urutan koin model (seperti cloud/bot),
    bukan abjad."""
    from .spot_dip2 import portfolio as pf0
    if tr.empty:
        return {}
    x = tr.copy()
    x["r"] = x.r - extra_cost
    # spot_dip2.portfolio mengurutkan (t, coin): pakai nama berawalan urutan agar sama dengan urutan koin model
    x["coin_asli"] = x.coin
    x["coin"] = [f"{o:03d}|{c}" for o, c in zip(x.ord, x.coin)]
    d2 = {}
    for coin, ss in data.items():
        for si, d in enumerate(ss):
            name = f"{coin}#{si}" if len(ss) > 1 else coin
            d2[name] = d
    names = set(x.coin_asli)
    data2 = {}
    for full, nm in zip(x.coin, x.coin_asli):
        data2[full] = [d2[nm]]
    _ = names
    return pf0(x.drop(columns=["coin_asli"]), data2, slots, start, end)


def ringkas(tr: pd.DataFrame, extra_cost: float = 0.0) -> dict:
    out = {}
    for lab, m in (("LAMA", tr.t < SPLIT), ("BARU", tr.t >= SPLIT)):
        x = tr[m]
        r = x.r - extra_cost
        if len(x):
            out[lab] = {"n": len(x), "wr": (r > 0).mean() * 100, "avg": r.mean() * 100,
                        "kalah": r[r <= 0].mean() * 100 if (r <= 0).any() else 0.0, "terburuk": r.min() * 100,
                        "per_bulan": len(x) / (60 if lab == "BARU" else 33)}
    return out


def acak(df_uni: pd.DataFrame, tr: pd.DataFrame, data: dict, slots: int, reps: int = 20, order: dict | None = None):
    """Pembanding acak: jumlah sinyal per bulan sama, dipilih acak dari hari & koin di semesta yang sama."""
    rng = np.random.default_rng(11)
    if tr.empty:
        return {}
    per_m = tr.groupby(tr.t.dt.to_period("M")).size()
    pool = df_uni.copy()
    pool["m"] = pool.t_in.dt.to_period("M")
    groups = {m: g for m, g in pool.groupby("m")}
    res = {"LAMA": [], "BARU": [], "pfL": [], "pfB": []}
    for _ in range(reps):
        picks = []
        for m, n in per_m.items():
            g = groups.get(m)
            if g is None or g.empty:
                continue
            picks.append(g.iloc[rng.choice(len(g), size=min(len(g), int(n * 1.3)), replace=False)])
        sig = pd.concat(picks)
        t = take(sig, order)
        s = ringkas(t)
        for lab in ("LAMA", "BARU"):
            if lab in s:
                res[lab].append((s[lab]["wr"], s[lab]["avg"]))
        pl = portfolio(t, data, slots, pd.Timestamp("2019-01-01", tz="UTC"), SPLIT)
        pb = portfolio(t, data, slots, SPLIT, END)
        if pl:
            res["pfL"].append((pl["cagr"] * 100, pl["dd"] * 100))
        if pb:
            res["pfB"].append((pb["cagr"] * 100, pb["dd"] * 100))
    med = {k: tuple(np.median(np.array(v), axis=0)) if v else None for k, v in res.items()}
    p95 = {k: tuple(np.percentile(np.array(v), 95, axis=0)) if v else None for k, v in res.items()}
    return {"median": med, "p95": p95}


def uji() -> None:
    from .spot_dip2 import MATI
    from .spot_jatuh import predict, wf_models
    from .spot_peluang import LIVE
    sp = cloud()
    order = {c: i for i, c in enumerate(sp.MODEL["coins"])}
    df, data = build()
    models = wf_models(df[df.base.isin(set(LIVE) | set(MATI))])
    df["p"] = predict(models, df)
    ok = df.p.notna()
    thr, skip_vol = 0.93, 0.90
    rule3 = (df.red >= 3) & (df.r3 <= -0.10) & (df.d200 > 0)
    sig = ((df.p >= thr) | rule3) & ok
    vol_ok = ~(df.vr > skip_vol)
    btc_ok = df.btc_up == 1
    kual = (df.age >= KUALITAS["umur_min"]) & ~(df.dd365 <= KUALITAS["ambruk"]) & ~(df.qv_rel >= KUALITAS["vol_panik"])
    kual_seb = (df.age >= KUALITAS["umur_min"]) & ~(df.dd365 <= KUALITAS["ambruk"]) & \
        ~(df.qv_rel_seb >= KUALITAS["vol_panik"])
    live = df.base.isin(LIVE)
    top20 = df["rank"] <= 20
    top100 = df["rank"] <= 100
    df["t"] = df.index
    V = {
        "A. TERPASANG branch ini: 20 koin tetap, lewati vol>P90, tanpa filter BTC": (sig & live & vol_ok, live, 10),
        "B. BAWAAN bot sniper: A + BTC>SMA200": (sig & live & vol_ok & btc_ok, live, 10),
        "C. B + filter kualitas": (sig & live & vol_ok & btc_ok & kual, live, 10),
        "D. jujur: 20 koin volume terbesar SAAT ITU, lewati vol>P90 + BTC>SMA200": (sig & top20 & vol_ok & btc_ok,
                                                                                    top20, 10),
        "D2. D + filter kualitas (= C tanpa bias penyintas)": (sig & top20 & vol_ok & btc_ok & kual, top20, 10),
        "E. D tanpa filter BTC (seperti A tetapi tanpa bias penyintas)": (sig & top20 & vol_ok, top20, 10),
        "F. versi 870aed1c: 100 koin, BTC>SMA200, kualitas (tanpa vol)": (sig & top100 & btc_ok & kual, top100, 20),
        "G. F + lewati vol>P90": (sig & top100 & btc_ok & kual & vol_ok, top100, 20),
        "H. F dengan volume panik versi bot (rata 30 hari SEBELUM t)": (sig & top100 & btc_ok & kual_seb, top100, 20),
    }
    L = ["# 💎 Spot dip untuk bot Telegram mandiri: uji jujur spesifikasi (research/spot_paritas.py uji)",
         f"Data: kline 1d Binance semua pair USDT ({len(data)} koin, termasuk delisting) s.d. {df.index.max():%Y-%m-%d}.",
         "Model gradient boosting WALK-FORWARD per tahun (dilatih 20 koin + koin ambruk, seperti spot_jatuh; model live "
         "spot_model.json dilatih s.d. Sep 2026 sehingga TIDAK dipakai untuk menilai masa lalu).",
         "Sinyal: p >= 0,93 ATAU 3 merah (red>=3, r3<=-10%, di atas SMA200) pada close hari t; beli open t+1; limit jual "
         "+3%; maks 10 hari (close hari ke-10). Biaya 0,30% pulang-pergi (dan 0,60% = biaya x2). Satu posisi per koin.",
         "Portofolio: N slot, tiap posisi 1/N ekuitas, sinyal saat penuh dilewati, urutan koin = urutan model.",
         "LAMA = 2019 – Sep 2021, BARU = Okt 2021 – Sep 2026. Pembanding acak: jumlah sinyal/bulan sama, hari & koin acak "
         "di semesta yang sama (20 ulangan, median; p95 = batas atas acak).", ""]
    for name, (mask, uni, slots) in V.items():
        tr = take(df[mask.fillna(False)].assign(t=lambda x: x.index), order)
        if tr.empty:
            L.append(f"{name}: n 0")
            continue
        s = ringkas(tr)
        s2 = ringkas(tr, 0.003)
        pl = portfolio(tr, data, slots, pd.Timestamp("2019-01-01", tz="UTC"), SPLIT)
        pb = portfolio(tr, data, slots, SPLIT, END)
        pb2 = portfolio(tr, data, slots, SPLIT, END, 0.003)
        L.append(f"## {name}  (portofolio {slots} slot)")
        for lab in ("LAMA", "BARU"):
            if lab in s:
                x, x2 = s[lab], s2[lab]
                L.append(f"   {lab}: n {x['n']} ({x['per_bulan']:.1f}/bln) naik {x['wr']:.1f}% rata {x['avg']:+.2f}%/sinyal "
                         f"kalah rata {x['kalah']:+.1f}% terburuk {x['terburuk']:+.0f}% | biaya x2: naik {x2['wr']:.1f}% "
                         f"rata {x2['avg']:+.2f}%")
        if pl:
            L.append(f"   portofolio LAMA {pl['cagr'] * 100:+.1f}%/th DD {pl['dd'] * 100:.0f}%")
        if pb:
            L.append(f"   portofolio BARU {pb['cagr'] * 100:+.1f}%/th DD {pb['dd'] * 100:.0f}% | biaya x2 "
                     f"{pb2['cagr'] * 100:+.1f}%/th DD {pb2['dd'] * 100:.0f}%")
            L.append("   per tahun (portofolio): " + " ".join(f"{t.year}:{v * 100:+.0f}%" for t, v in pb["tahun"].items()))
        L.append("   per tahun (per sinyal): " + " ".join(
            f"{y}:n{len(g)} {(g.r > 0).mean() * 100:.0f}% {g.r.mean() * 100:+.1f}%" for y, g in tr.groupby(tr.t.dt.year)))
        x = tr[tr.t >= SPLIT]
        if len(x):
            for lvl in (0.10, 0.20):
                y = x[x.mdd <= -lvl]
                L.append(f"   BARU sempat turun >= {lvl * 100:.0f}%: {len(y) / len(x) * 100:.0f}% posisi, tetap kena TP "
                         f"{(y.r > 0).mean() * 100:.0f}%, rata akhir {y.r.mean() * 100:+.1f}%")
        uni_rows = df[uni & ok & df.t_in.notna()].assign(t=lambda x: x.index)
        base_rate = {lab: (uni_rows[m].hit.mean() * 100, uni_rows[m].r.mean() * 100)
                     for lab, m in (("LAMA", uni_rows.index < SPLIT), ("BARU", uni_rows.index >= SPLIT))}
        L.append("   semua hari di semesta (tanpa sinyal): " + " | ".join(
            f"{k} naik {v[0]:.1f}% rata {v[1]:+.2f}%" for k, v in base_rate.items()))
        a = acak(uni_rows, tr, data, slots, order=order)
        if a:
            md, p9 = a["median"], a["p95"]
            L.append("   ACAK (median): " + " | ".join(
                f"{k} naik {md[k][0]:.1f}% rata {md[k][1]:+.2f}%" for k in ("LAMA", "BARU") if md.get(k)) +
                (f" | pf LAMA {md['pfL'][0]:+.1f}%/th DD {md['pfL'][1]:.0f}%" if md.get("pfL") else "") +
                (f" | pf BARU {md['pfB'][0]:+.1f}%/th DD {md['pfB'][1]:.0f}%" if md.get("pfB") else ""))
            L.append("   ACAK p95 (batas atas keberuntungan): " + " | ".join(
                f"{k} rata {p9[k][1]:+.2f}%" for k in ("LAMA", "BARU") if p9.get(k)) +
                (f" | pf BARU {p9['pfB'][0]:+.1f}%/th" if p9.get("pfB") else ""))
        L.append("")
    L.append(cek_panjang(sp, ["ETH", "SOL", "XLM", "DOGE", "LINK"]))
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    if "fixture" in sys.argv:
        fixture()
    if "uji" in sys.argv:
        uji()
    if "panjang" in sys.argv:
        print(cek_panjang(cloud(), ["ETH", "SOL", "XLM", "DOGE", "LINK"]))
