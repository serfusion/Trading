"""Tab Tanya (POST /api/chat): penjawab berbasis DATA, tanpa AI — hanya library standar.

Jawaban disusun dari statistik historis `pengetahuan.json` (dibuat `python -m research.event_stats`: kalender
ForexFactory 2010-2026 dengan actual/forecast, reaksi XAU/USD M15 & BTC/USD H1, sinyal 💰 bot di sekitar berita)
ditambah konteks langsung: kalender USD high-impact minggu ini (ForexFactory), posisi bot (Supabase), filter BTC.
Tidak ada tebakan di luar data: bila pertanyaan tidak dikenali, balasan menjelaskan apa yang bisa ditanyakan.
Chat hanya memberi informasi; tidak membuka/menutup order.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
KB = json.loads((HERE / "pengetahuan.json").read_text(encoding="utf-8"))
MAX_TURNS = 12
MAX_CHARS = 2000
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
WIB = timedelta(hours=7)

# kata kunci -> grup berita (dicek berurutan: yang lebih spesifik dulu)
GROUP_WORDS = [
    ("PPI", ["ppi", "inflasi produsen", "producer price"]),
    ("PCE", ["pce"]),
    ("CLAIMS", ["claims", "klaim", "jobless"]),
    ("NFP", ["nfp", "non-farm", "nonfarm", "non farm", "payroll", "tenaga kerja", "lapangan kerja", "pengangguran",
             "unemployment rate", "average hourly"]),
    ("CPI", ["cpi", "inflasi"]),
    ("FOMC", ["fomc", "the fed", "fed ", "fed?", "fed,", "suku bunga", "interest rate", "rate decision", "powell",
              "federal funds", "fed funds", "funds rate",
              "warsh", "dot plot", "fedwatch"]),
    ("GDP", ["gdp", "pdb"]),
    ("RETAIL", ["retail", "ritel"]),
    ("ISM", ["ism", "pmi"]),
]
# kalender ForexFactory: judul event -> grup
TITLE_GROUP = [("Non-Farm", "NFP"), ("CPI", "CPI"), ("PPI", "PPI"), ("Federal Funds", "FOMC"), ("FOMC", "FOMC"),
               ("Retail Sales", "RETAIL"), ("PCE", "PCE"), ("GDP", "GDP"), ("ISM", "ISM"), ("Unemployment Claims", "CLAIMS")]
# arah angka dibanding perkiraan: hanya bentuk perbandingan (kata tunggal "tinggi"/"naik" terlalu ambigu, mis. "WR
# tinggi", "emas naik"); "naik"/"turun" hanya dihitung bila menempel pada nama data (DATA_MOVE)
UP = ["di atas", "lebih tinggi", "lebih besar", "melebihi", "lebih banyak", "beat", "panas"]
DOWN = ["di bawah", "lebih rendah", "lebih kecil", "lebih sedikit", "miss", "meleset", "dingin"]
DATA_MOVE = re.compile(r"(klaim|claims|pengangguran|inflasi|cpi|ppi|pce|nfp|payroll|gdp|pdb|retail|ritel|pmi|ism|data|"
                       r"angka)\s+(\w+\s+)?(naik|turun|meningkat|menurun)")
STRONG = ["kuat", "bagus", "solid", "positif"]
WEAK = ["lemah", "buruk", "jelek", "negatif"]
SAME = ["sesuai", "sama dengan perkiraan", "sama dengan forecast", "in line", "inline"]
POST = ["sudah keluar", "sudah rilis", "hasil", "keluar", "rilis", "barusan", "baru saja", "actual", "aktual", "tadi"]
PRE = ["sebelum", "akan", "besok", "nanti", "menjelang", "jelang", "survey", "survei", "polling", "fedwatch",
       "ekspektasi", "diperkirakan", "peluang", "kemungkinan"]
ASSET_WORDS = ["emas", "gold", "xau", "harga", "btc", "bitcoin", "dolar", "usd"]


def _pct(x: float) -> str:
    return f"{x:+.2f}%".replace(".", ",")


def _num_text(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _has(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _group(text: str) -> str | None:
    t = f" {text} "
    for g, words in GROUP_WORDS:
        if any(w in t for w in words):
            return g
    return None


def _numbers(text: str) -> list[float]:
    """Angka dengan satuan: 45K, 45 ribu, 0,3%, 4.25%, 150000."""
    out = []
    for m in re.finditer(r"(-?\d+(?:[.,]\d+)?)\s*(k|rb|ribu|jt|juta|m|%)?(?![a-z])", text):
        raw, unit = m.group(1), m.group(2) or ""
        if re.fullmatch(r"-?\d{1,3}([.,]\d{3})+", raw):       # 150.000 / 150,000
            v = float(re.sub(r"[.,]", "", raw))
        else:
            v = float(raw.replace(",", "."))
        v *= {"k": 1e3, "rb": 1e3, "ribu": 1e3, "jt": 1e6, "juta": 1e6, "m": 1e6}.get(unit, 1.0)
        out.append(v)
    return out


def calendar_rows_for(calendar_rows: list | None) -> list[dict]:
    """Berita USD high-impact minggu ini: [{time (UTC), title, group, forecast, previous}]."""
    out = []
    for r in calendar_rows or []:
        if r.get("country") != "USD" or r.get("impact") != "High":
            continue
        try:
            t = datetime.fromisoformat(r["date"]).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue
        grp = next((g for key, g in TITLE_GROUP if key in (r.get("title") or "")), None)
        out.append({"time": t, "title": r.get("title"), "group": grp, "forecast": r.get("forecast") or "",
                    "previous": r.get("previous") or ""})
    return sorted(out, key=lambda x: x["time"])


HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _when(t: datetime) -> str:
    w = t + WIB
    return f"{HARI[w.weekday()]} {w.day:02d} {BULAN[w.month - 1]} {w:%H:%M} WIB"


def _r(x: float) -> str:
    return f"{x:+.2f}R".replace(".", ",")


def _val(v: float) -> str:
    """45000 -> 45K; 0.3 -> 0,3."""
    if abs(v) >= 1000:
        return f"{v / 1000:g}K".replace(".", ",")
    return f"{v:g}".replace(".", ",")


# ------------------------------------------------------------------ format "Act: Cons: Prev:" (seperti ForexFactory)
LABEL = re.compile(r"(?<![a-z])(actual|act|aktual|consensus|cons|konsensus|forecast|fcst|perkiraan|previous|prev|"
                   r"sebelumnya)\s*[:=]?\s*(-?\d+(?:[.,]\d+)?\s*(?:k|rb|ribu|jt|juta|m|%)?)")
KIND = {"actual": "act", "act": "act", "aktual": "act", "consensus": "cons", "cons": "cons", "konsensus": "cons",
        "forecast": "cons", "fcst": "cons", "perkiraan": "cons", "previous": "prev", "prev": "prev",
        "sebelumnya": "prev"}
# baris pendamping NFP yang tidak ikut statistik NFP (statistik historis memakai angka Non-Farm saja)
INFO_ONLY = ["unemployment rate", "tingkat pengangguran", "average hourly", "upah", "earnings"]


def parse_rows(text: str, prev_group: str | None = None) -> list[dict]:
    """Baris 'NFP Act: 45K Cons: 98K Prev: 162K' (boleh beberapa baris / dipisah ';')."""
    rows = []
    for line in re.split(r"[\n;]+", text):
        low = " " + line.lower().strip() + " "
        vals, raw = {}, {}
        for m in LABEL.finditer(low):
            nums = _numbers(m.group(2))
            if nums and KIND[m.group(1)] not in vals:
                vals[KIND[m.group(1)]] = nums[0]
                raw[KIND[m.group(1)]] = m.group(2).strip().upper().replace("RB", "K").replace("RIBU", "K")
        if "act" not in vals:
            continue
        first = LABEL.search(low)
        name = line.strip()[:max(first.start() - 1, 0)].strip(" :-•\t") if first else line.strip()
        rows.append({"name": name, "group": _group(" " + name.lower() + " ") or _group(low), "act": vals["act"],
                     "cons": vals.get("cons"), "prev": vals.get("prev"), "raw": raw, "low": low})
    if not rows:
        return []
    default = next((r["group"] for r in rows if r["group"]), prev_group)
    for r in rows:
        r["group"] = r["group"] or default
        low = r.pop("low")
        r["inverse"] = r["group"] == "CLAIMS" or "pengangguran" in low or "unemployment" in low
        r["counts"] = not (r["group"] == "NFP" and any(w in low for w in INFO_ONLY))
        r["name"] = r["name"] or _nama(r["group"] or "?")
    return rows


def _pct_rank(grp: str, diff: float) -> int | None:
    hist = (KB.get("kejutan_hist") or {}).get(grp)
    if not hist or diff == 0:
        return None
    return round(100 * sum(1 for x in hist if x <= abs(diff) + 1e-12) / len(hist))


def _gold_dir(diff: float, inverse: bool) -> int:
    """+1 = bagus untuk emas (data lebih lemah / inflasi lebih rendah), −1 = buruk, 0 = sama."""
    if diff == 0:
        return 0
    return (1 if diff > 0 else -1) * (1 if inverse else -1)


def _arti(g: int) -> str:
    return {1: "bagus untuk emas", -1: "buruk untuk emas", 0: "netral"}[g]


def scan_answer(rows: list[dict], calendar: list[dict], now: datetime, btc: bool) -> str:
    """Pemindaian menyeluruh data rilis: Act vs Cons (arah, besar, persentil), Act vs Prev (tren), gabungan -> peluang."""
    grp = next((r["group"] for r in rows if r["group"]), None)
    if grp is None:
        return ("Nama beritanya belum saya kenali. Tulis mis. \"NFP Act: 45K Cons: 98K Prev: 162K\" atau "
                "\"CPI m/m Act: 0,4% Cons: 0,3% Prev: 0,2%\".")
    if grp == "FOMC":
        r = rows[0]
        info = {"group": "FOMC", "bias": None, "same": False, "big": False, "timing": "sesudah", "btc": btc,
                "decision": None, "text": ""}
        lines = [f"📊 Scanning FOMC — Federal Funds Rate Act {_val(r['act'])}%"
                 + (f", Cons {_val(r['cons'])}%" if r["cons"] is not None else "")
                 + (f", Prev {_val(r['prev'])}%" if r["prev"] is not None else "")]
        if r["prev"] is not None:
            info["decision"] = "naik" if r["act"] > r["prev"] else "turun" if r["act"] < r["prev"] else "tetap"
            lines.append(f"• Keputusan: suku bunga {info['decision']} (vs sebelumnya).")
        if r["cons"] is not None and r["act"] != r["cons"]:
            info["bias"] = -1 if r["act"] > r["cons"] else 1
            info["surprise"] = True
            lines.append(f"• KEJUTAN: lebih {'hawkish (bunga lebih tinggi)' if r['act'] > r['cons'] else 'dovish (bunga lebih rendah)'} "
                         f"dari perkiraan → {_arti(info['bias'])}.")
        elif r["cons"] is not None:
            lines.append("• Sesuai perkiraan (tanpa kejutan suku bunga).")
        meta = KB.get("meta", {})
        asset = "btc" if btc else "xau"
        return "\n".join(lines + fomc_lines(info, asset, meta.get("harga_btc" if btc else "harga_emas", 0) or 0))
    meta = KB.get("meta", {})
    asset = "btc" if btc and grp in (KB.get("btc") or {}) else "xau"
    price = meta.get("harga_btc" if asset == "btc" else "harga_emas", 0) or 0
    L = [f"📊 Scanning {_nama(grp)} — {'BTC/USD (H1)' if asset == 'btc' else 'XAU/USD (M15)'}, data {meta.get('kalender')}"]
    total, main = 0, None
    for r in rows:
        raw = r.get("raw") or {}
        parts = [f"• {r['name'] or _nama(grp)}: Act {raw.get('act') or _val(r['act'])}"]
        if r["cons"] is not None:
            d = r["act"] - r["cons"]
            g = _gold_dir(d, r["inverse"])
            txt = "sama dengan" if d == 0 else ("di ATAS" if d > 0 else "di BAWAH")
            parts.append(f"vs Cons {raw.get('cons') or _val(r['cons'])} → {txt} perkiraan"
                         + ("" if d == 0 else f" {_val(abs(d))}") + f" ({_arti(g)})")
            if r["counts"]:
                total += g
                if main is None:
                    main = dict(r, g=g, diff=d)
                    rank = _pct_rank(grp, d)
                    if rank is not None:
                        parts.append(f"besar kejutan melebihi {rank}% rilis sejak 2010")
        if r["prev"] is not None:
            dp = r["act"] - r["prev"]
            gp = _gold_dir(dp, r["inverse"])
            parts.append(f"vs Prev {raw.get('prev') or _val(r['prev'])} → {'naik' if dp > 0 else 'turun' if dp < 0 else 'sama'} "
                         f"({_arti(gp)})")
            if main is not None and main.get("name") == r["name"]:
                main["gp"] = gp
        if not r["counts"]:
            parts.append("[info saja — peluang memakai angka Non-Farm]")
        L.append("; ".join(parts))
    if main is None:
        L.append("Tidak ada Cons (perkiraan) untuk angka utama → arah kejutan tidak bisa dinilai. Tambahkan Cons.")
        return "\n".join(L)
    bias = 0 if total == 0 else (1 if total > 0 else -1)
    if bias == 0:
        s = ((KB.get(asset) or {}).get(grp) or {}).get("sesuai")
        L.append("Kesimpulan: tanpa kejutan arah (sesuai perkiraan / sinyal campur).")
        if s:
            L.append(f"• Historis sesuai perkiraan (n={s['n']}): naik 1 jam {s['1j']['naik']}% → ≈ 50/50.")
    else:
        tag = "bagus" if bias > 0 else "buruk"
        med = (KB.get("median_kejutan") or {}).get(grp)
        big = bool(med) and abs(main["diff"]) >= 2 * med
        L.append(f"Kesimpulan: {'BAGUS (emas cenderung naik)' if bias > 0 else 'BURUK (emas cenderung turun)'}"
                 f"{' — kejutan BESAR (≥2× median)' if big else ''}.")
        L.append("Peluang (historis):")
        L += _stat_lines(asset, grp, tag, price)
        b = ((KB.get(asset) or {}).get(grp, {}).get(tag) or {}).get("besar")
        if big and b:
            L.append(f"• Khusus kejutan besar (n={b['n']}): {b['jendela']} searah {b['searah']}%"
                     f"{' — sampel kecil' if b['n'] < 20 else ''}.")
        combo = (KB.get("xau_prev") or {}).get(grp, {}) if asset == "xau" else {}
        if "gp" in main and combo:
            key = f"{tag}_{'searah' if main['gp'] == bias else 'campur'}"
            c = combo.get(key)
            if c:
                arah = "naik" if bias > 0 else "turun"
                L.append(f"• Gabungan dengan Prev ({'searah: juga ' + ('lebih lemah' if bias > 0 else 'lebih kuat') + ' dari sebelumnya' if key.endswith('searah') else 'berlawanan dengan tren sebelumnya'}, "
                         f"n={c['n']}): emas {arah} 1 jam {c['1j']['searah']}%, 4 jam {c['4j']['searah']}%"
                         f"{' — sampel kecil' if c['n'] < 20 else ''}.")
    lanjut = ((KB.get(asset) or {}).get(grp) or {}).get("lanjut1j")
    if lanjut:
        L.append(f"⚠️ Setelah candle 15 menit pertama TUTUP, 1 jam berikutnya searah hanya {lanjut['pct']}% (n={lanjut['n']}) "
                 "≈ lempar koin → jangan mengejar lonjakan; spread melebar saat rilis.")
    L += ["Saran berbasis data:"] + _signal_news_lines(pre=False)
    return "\n".join(L)


def parse(text: str, calendar: list[dict], prev_group: str | None = None) -> dict:
    """Pahami pertanyaan: grup berita, arah kejutan dari sisi emas (+1 bagus / −1 buruk), besar, waktu, aset."""
    t = " " + text.lower().replace("\n", " ") + " "
    grp = _group(t)
    nums = _numbers(t)
    if grp is None and prev_group and (nums or _has(t, UP + DOWN + STRONG + WEAK + SAME)):
        grp = prev_group
    # kata tentang arah harga emas/BTC bukan arah data
    clean = re.sub(r"(emas|gold|xau|harga|btc|bitcoin)\s+(akan\s+)?(naik|turun)", " ", t)
    info = {"group": grp, "bias": None, "same": False, "big": False, "timing": None, "btc": _has(t, ["btc", "bitcoin"]),
            "decision": None, "actual": None, "forecast": None, "text": t}
    if grp == "FOMC":
        if _has(clean, ["naik", "hike", "kenaikan", "menaikkan"]):
            info["decision"] = "naik"
        elif _has(clean, ["turun", "cut", "pemangkasan", "penurunan", "menurunkan", "memangkas"]):
            info["decision"] = "turun"
        elif _has(clean, ["tetap", "hold", "tahan", "tidak berubah"]):
            info["decision"] = "tetap"
        if _has(clean, ["hawkish"]):
            info["bias"] = -1
        elif _has(clean, ["dovish"]):
            info["bias"] = 1
        if _has(clean, ["kejutan", "surprise", "di luar perkiraan", "tidak sesuai", "di luar ekspektasi"]):
            info["surprise"] = True
    elif grp:
        inverse = grp == "CLAIMS" or "pengangguran" in t
        data_dir = None
        forecast = None
        cal = [c for c in calendar if c["group"] == grp and c["forecast"]]
        if cal:
            f = _numbers(cal[0]["forecast"].lower())
            forecast = f[0] if f else None
        if len(nums) >= 2:
            info["actual"], info["forecast"] = nums[0], nums[1]
        elif len(nums) == 1 and forecast is not None:
            info["actual"], info["forecast"] = nums[0], forecast
        if info["actual"] is not None and info["forecast"] is not None:
            diff = info["actual"] - info["forecast"]
            data_dir = 0 if diff == 0 else (1 if diff > 0 else -1)
            med = (KB.get("median_kejutan") or {}).get(grp)
            info["big"] = bool(med) and abs(diff) >= 2 * med
        elif _has(clean, SAME):
            data_dir = 0
        elif _has(clean, UP):
            data_dir = 1
        elif _has(clean, DOWN):
            data_dir = -1
        elif (m := DATA_MOVE.search(clean)):
            data_dir = 1 if m.group(3) in ("naik", "meningkat") else -1
        if _has(clean, STRONG) and data_dir is None:
            info["bias"] = -1
        elif _has(clean, WEAK) and data_dir is None:
            info["bias"] = 1
        elif data_dir == 0:
            info["same"] = True
        elif data_dir is not None:
            info["bias"] = data_dir * (1 if inverse else -1)
        if _has(clean, ["besar", "jauh", "sangat"]):
            info["big"] = True
    if info["bias"] is not None or info["same"] or info["actual"] is not None or info.get("decision") and _has(t, POST):
        info["timing"] = "sesudah"
    elif _has(t, POST) and not _has(t, PRE):
        info["timing"] = "sesudah"
    elif _has(t, PRE):
        info["timing"] = "sebelum"
    return info


# ------------------------------------------------------------------ bagian jawaban
def _mag(pct: float, price: float) -> str:
    """Besar gerak rata-rata ke arah yang diharapkan: '0,24% ≈ $11' (negatif = justru berlawanan)."""
    txt = f"{abs(pct):.2f}% ≈ ${abs(pct) / 100 * price:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return txt if pct >= 0 else f"justru berlawanan {txt}"


def _stat_lines(asset: str, grp: str, tag: str, price: float) -> list[str]:
    s = (KB.get(asset) or {}).get(grp, {}).get(tag)
    if not s:
        return []
    arah = "naik" if tag == "bagus" else "turun"
    label = {"15m": "15 menit pertama", "1j": "1 jam", "4j": "4 jam", "1h": "1 hari"}
    out = []
    for k in ("15m", "1j", "4j", "1h"):
        if k in s:
            out.append(f"• {label[k]}: {arah} pada {s[k]['searah']}% dari {s['n']} kejadian "
                       f"(rata-rata {_mag(s[k]['rata'], price)})")
    return out


def _nama(grp: str) -> str:
    return (KB.get("nama") or {}).get(grp, grp)


def _schedule_line(grp: str, calendar: list[dict], now: datetime) -> str | None:
    rows = [c for c in calendar if c["group"] == grp]
    if not rows:
        return None
    parts = []
    for c in rows[:3]:
        when = "sudah lewat" if c["time"] < now else "akan datang"
        parts.append(f"{c['title']} {_when(c['time'])} ({when}) — forecast {c['forecast'] or '-'}, "
                     f"sebelumnya {c['previous'] or '-'}")
    return "📅 Minggu ini: " + "; ".join(parts)


def _signal_news_lines(pre: bool) -> list[str]:
    s = KB.get("sinyal_berita") or {}
    if not s:
        return []
    a, b, c = s.get("sesudah", {}), s.get("sebelum", {}), s.get("jauh", {})
    if pre:
        return [f"• Sinyal 💰 XAU yang lahir ≤ 24 jam SEBELUM NFP/CPI/FOMC: WR {b.get('wr')}%, rata "
                f"{_r(b.get('r', 0))} (n={b.get('n')}) vs jauh dari berita WR {c.get('wr')}%, {_r(c.get('r', 0))}. "
                "Tidak konsisten tiap periode (2012–18 justru untung), jadi bukan aturan pasti — cukup kecilkan risiko "
                "untuk sinyal baru menjelang berita. Posisi yang sudah jalan: tetap ikuti SL/TUTUP."]
    return [f"• Sinyal 💰 XAU yang lahir ≤ 4 jam SESUDAH NFP/CPI/FOMC: WR {a.get('wr')}%, rata {_r(a.get('r', 0))} "
            f"(n={a.get('n')}) — lebih baik dari rata-rata ({_r(c.get('r', 0))}). Berita sering memicu breakout "
            "yang ditangkap sinyal trend; jadi kalau bot mengirim sinyal 💰 setelah berita, itu layak diikuti dengan "
            "SL normal."]


def event_answer(info: dict, calendar: list[dict], now: datetime) -> str:
    grp = info["group"]
    meta = KB.get("meta", {})
    asset = "btc" if info["btc"] and grp in (KB.get("btc") or {}) else "xau"
    price = meta.get("harga_btc" if asset == "btc" else "harga_emas", 0) or 0
    nama_aset = "BTC/USD (H1)" if asset == "btc" else "XAU/USD (M15)"
    L = [f"📊 {_nama(grp)} — {nama_aset}, kalender {meta.get('kalender')}"]
    sched = _schedule_line(grp, calendar, now)
    if sched:
        L.append(sched)
    if grp == "FOMC":
        return "\n".join(L + fomc_lines(info, asset, price))
    g = (KB.get(asset) or {}).get(grp) or {}
    if not g:
        L.append("Belum ada statistik untuk berita ini di data kami.")
        return "\n".join(L)
    lanjut = g.get("lanjut1j")
    if info["timing"] == "sesudah" and (info["bias"] is not None or info["same"]):
        if info["actual"] is not None:
            L.append(f"Angka: actual {_val(info['actual'])} vs forecast {_val(info['forecast'])}.")
        if info["same"]:
            s = g.get("sesuai")
            L.append("Hasil sesuai perkiraan → tidak ada kejutan arah.")
            if s:
                L.append(f"• Historis (n={s['n']}): emas naik 1 jam {s['1j']['naik']}% (median gerak "
                         f"{_pct(s['1j']['gerak'])}); 1 hari naik {s['1h']['naik']}% → ≈ 50/50, tidak ada keunggulan arah.")
        else:
            tag = "bagus" if info["bias"] > 0 else "buruk"
            L.append(f"Kejutan: {'data lebih LEMAH / dovish' if tag == 'bagus' else 'data lebih KUAT / hawkish'} "
                     f"→ secara historis {'BAGUS (emas naik)' if tag == 'bagus' else 'BURUK (emas turun)'} untuk "
                     f"{'BTC' if asset == 'btc' else 'emas'}{', kejutan BESAR' if info['big'] else ''}.")
            L.append("Peluang (historis):")
            L += _stat_lines(asset, grp, tag, price)
            big = (g.get(tag) or {}).get("besar")
            if info["big"] and big:
                L.append(f"• Khusus kejutan besar (≥2× median, n={big['n']}): {big['jendela']} searah {big['searah']}%"
                         f" (rata {_pct(big['rata'])}){' — sampel kecil' if big['n'] < 20 else ''}.")
        if lanjut:
            L.append(f"⚠️ Setelah candle 15 menit pertama TUTUP, 1 jam berikutnya searah candle itu hanya {lanjut['pct']}% "
                     f"(n={lanjut['n']}) ≈ lempar koin → jangan mengejar lonjakan; spread melebar saat rilis.")
        L += ["Saran berbasis data:"] + _signal_news_lines(pre=False)
        return "\n".join(L)
    # sebelum rilis / hasil belum diketahui: tampilkan skenario
    after = info["timing"] == "sesudah"
    if after:
        L.append("Angka actual belum saya ketahui (kalender tidak memuat hasil rilis). Ketik angkanya, mis. "
                 "\"NFP 45K vs 98K\" atau \"CPI lebih tinggi dari perkiraan\", supaya peluangnya tepat.")
    L.append("Skenario (historis, dari rilis ke 1 jam):")
    for tag, label in (("bagus", "Data lebih LEMAH dari perkiraan"), ("buruk", "Data lebih KUAT dari perkiraan")):
        s = g.get(tag)
        if s:
            arah = "naik" if tag == "bagus" else "turun"
            L.append(f"• {label} (n={s['n']}): {'BTC' if asset == 'btc' else 'emas'} {arah} dalam 1 jam pada "
                     f"{s['1j']['searah']}% (rata-rata {_mag(s['1j']['rata'], price)}); "
                     f"15 menit pertama {s.get('15m', s['1j'])['searah']}%.")
    s = g.get("sesuai")
    if s:
        L.append(f"• Sesuai perkiraan (n={s['n']}): ≈ 50/50 (naik 1 jam {s['1j']['naik']}%).")
    if lanjut:
        L.append(f"• Arah sesudah candle 15 menit pertama: hanya {lanjut['pct']}% searah (≈ lempar koin).")
    if after:
        L += ["Saran berbasis data:"] + _signal_news_lines(pre=False)
        return "\n".join(L)
    L.append("Arah tidak bisa diketahui sebelum angka keluar — tidak ada data yang memprediksi hasil rilisnya.")
    L += ["Saran berbasis data:"] + _signal_news_lines(pre=True)
    L.append("Setelah rilis, tanya lagi dengan angkanya, mis. \"NFP 45K vs 98K\" atau \"CPI lebih tinggi dari perkiraan\".")
    return "\n".join(L)


def fomc_lines(info: dict, asset: str, price: float) -> list[str]:
    f = KB.get("fomc") or {}
    L = [f"Keputusan suku bunga hampir selalu SESUAI ekspektasi pasar (CME FedWatch/konsensus): kejutan hanya "
         f"{f.get('kejutan')} dari {f.get('n')} rapat ({f.get('dari')}–{f.get('sampai')}). Yang menggerakkan emas "
         "biasanya pernyataan, dot plot, dan konferensi pers — arahnya ≈ 50/50."]
    rows = f.get("rows") or []
    want = info.get("decision")
    surprise = info.get("surprise") or info.get("bias") is not None
    shown = 0
    for r in rows:
        if r["kejutan"] == "sesuai" and (want is None or r["jenis"] == want) and not surprise:
            L.append(f"• Bunga {r['jenis']}, sesuai ekspektasi (n={r['n']}): emas 1 jam naik {r['naik1j']}% "
                     f"(median {_pct(r['med1j'])}), 1 hari naik {r['naik1h']}% (median {_pct(r['med1h'])}); "
                     f"besar gerak 1 jam median {_mag(r['gerak1j'], price)} (naik atau turun).")
            shown += 1
    if surprise or not shown:
        for r in rows:
            if r["kejutan"] != "sesuai":
                L.append(f"• Kejutan {r['kejutan']} (n={r['n']}: {', '.join(r['tanggal'])}) — sampel terlalu kecil "
                         "untuk peluang.")
    if want and info.get("timing") != "sesudah":
        L.append(f"Kalau pasar sudah memperkirakan bunga {want} (peluang FedWatch tinggi), itu termasuk baris "
                 "'sesuai ekspektasi' di atas — keputusannya sendiri sudah diperhitungkan harga.")
    L += ["Saran berbasis data:"] + _signal_news_lines(pre=info.get("timing") != "sesudah")
    if asset == "btc":
        s = (KB.get("btc") or {}).get("FOMC", {}).get("sesuai")
        if s:
            L.append(f"• BTC saat FOMC (n={s['n']}): naik 1 jam {s['1j']['naik']}%, 1 hari {s['1h']['naik']}% "
                     f"(median gerak 1 hari {_pct(s['1h']['gerak']).replace('+', '±')}).")
    return L


def calendar_answer(calendar: list[dict], now: datetime) -> str:
    if not calendar:
        return "Kalender minggu ini tidak tersedia saat ini. Coba lagi nanti."
    L = ["📅 Berita USD high-impact minggu ini (ForexFactory):"]
    for c in calendar:
        g = (KB.get("xau") or {}).get(c["group"] or "", {})
        extra = ""
        if g.get("bagus") and g.get("buruk"):
            extra = (f" — historis: lebih lemah → emas naik 1 jam {g['bagus']['1j']['searah']}%; lebih kuat → "
                     f"turun {g['buruk']['1j']['searah']}%")
        status = "✓ lewat" if c["time"] < now else "⏳"
        L.append(f"{status} {_when(c['time'])}: {c['title']} (forecast {c['forecast'] or '-'}, sebelumnya "
                 f"{c['previous'] or '-'}){extra}")
    L += ["Saran berbasis data:"] + _signal_news_lines(pre=True)
    return "\n".join(L)


def bot_answer(states: dict, funding_cache: dict | None, now: datetime) -> str:
    L = []
    for asset, st in (states or {}).items():
        if not st:
            continue
        L.append(f"{asset}: harga {st.get('price')} (update {st.get('last_tick', '-')[:16].replace('T', ' ')} UTC)")
        any_open = False
        for name, s in sorted((st.get("systems") or {}).items()):
            v = s.get("virtual")
            if v:
                any_open = True
                L.append(f"• {name}: {v.get('dir')} entry {_num_text(float(v.get('entry', 0)))}, SL "
                         f"{_num_text(float(v.get('sl', 0)))}, TP1 {_num_text(float(v.get('tp1', 0)))}"
                         f"{' — TP1 sudah kena, SL+ aktif' if v.get('tp1_hit') or v.get('be_done') else ''}")
        if not any_open:
            L.append("• tidak ada posisi terbuka")
    if not L:
        L.append("Status bot belum tersedia (Supabase belum diatur di cloud).")
    L.append("Level TUTUP tiap set ada di kartu sinyal aktif (🚪). 4 posisi running ditutup saat close H1 menembusnya.")
    L.append(filter_text(funding_cache, now))
    return "\n".join(L)


def filter_text(funding_cache: dict | None, now: datetime) -> str:
    """Status filter BTC 💰 yang terpasang (funding ramai & September)."""
    import _core
    import _funding
    pct = _funding.percentile_last([v for _, v in (funding_cache or {}).get("f") or []])
    line = (f"Filter BTC 💰: funding Binance 24 jam persentil {'-' if pct is None else f'{pct:.0%}'} (1 tahun, data s/d "
            f"{(funding_cache or {}).get('day', '-')}); BUY dilewati bila ≥90%, SELL bila ≤10%.")
    if _core.new_york(now).month == 9:
        line += " Sekarang September: sinyal BTC 💰 dilewati (11/11 tahun rugi)."
    return line


SKEMA = """🧭 Skema bawaan (dipakai aplikasi): 5 posisi, posisi #1 TP1 = 1R; TP1 kena → SL 4 posisi ke entry (SL+);
4 posisi running ditutup saat sinyal TUTUP (close H1 menembus low 15/20/30 candle untuk BUY, high untuk SELL).
Hasil sinyal 💰 (XAU 2012–2026 / BTC 2016–2026, uji seperti cloud):
• Bawaan: WR 48% / 48%, total +324R / +766R
• SL+ saat profit 0,7R: WR 59% / 56%, total +312R / +752R (WR naik, profit sedikit turun, drawdown XAU lebih dalam)
• SL+ naik bertangga tiap 1R: WR 49% / 48%, total +308R / +453R
• TP 1R/2R/3R + 2 running: total +252R / +520R
• 3 posisi TP1 + 2 running: total +186R / +412R
• Tanpa TP1 (5 running): total +373R / +924R tetapi WR hanya 37% / 34%
Nasib 4 running (XAU): 36% kena SL awal, 19% TP1 lalu SL+ (≈ +0,1R), 17% TUTUP sebelum TP1 (median −0,54R),
29% TP1 lalu TUTUP dengan running median +1,3R (21% > +3R, 11% > +5R, maks +27,7R), ditahan median 4,4 hari.
Kesimpulan data: pertahankan skema bawaan."""

BANTUAN = """Saya menjawab dari DATA historis (bukan AI, bukan ramalan). Contoh pertanyaan:
• "NFP Act: 45K Cons: 98K Prev: 162K" (format ForexFactory; boleh beberapa baris, mis. + Unemployment Rate)
• "NFP 45K vs 98K" / "NFP lebih kecil dari perkiraan" / "CPI lebih tinggi" → peluang reaksi emas
• "Sebelum NFP / CPI / FOMC apa yang harus saya lakukan?" → skenario + saran
• "FOMC suku bunga naik sesuai ekspektasi" / "FOMC hawkish" → statistik FOMC
• "Berita minggu ini" → jadwal + statistik singkat
• "Sinyal terbuka" → posisi bot sekarang
• "SL+ / TP / running" → hasil uji skema
• "BTC funding" / "BTC September" → filter BTC
Tambahkan "BTC" untuk statistik BTC (FOMC/NFP/CPI)."""


# ------------------------------------------------------------------ utama
def clean_history(messages: list) -> list[dict]:
    """Riwayat dari aplikasi -> user/assistant bergantian, diakhiri pesan pengguna."""
    out: list[dict] = []
    for m in (messages or [])[-MAX_TURNS:]:
        role = m.get("role") if isinstance(m, dict) else None
        text = str(m.get("content", ""))[:MAX_CHARS].strip() if role else ""
        if role not in ("user", "assistant") or not text:
            continue
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n\n" + text
        else:
            out.append({"role": role, "content": text})
    while out and out[0]["role"] != "user":
        out.pop(0)
    if not out or out[-1]["role"] != "user":
        raise ValueError("pesan terakhir harus dari pengguna")
    return out


def answer(messages: list, now: datetime, calendar_rows=None, states: dict | None = None,
           funding_cache: dict | None = None) -> dict:
    msgs = clean_history(messages)
    question = msgs[-1]["content"]
    prev_group = None
    for m in reversed(msgs[:-1]):
        if m["role"] == "user" and (prev_group := _group(" " + m["content"].lower() + " ")):
            break
    calendar = calendar_rows_for(calendar_rows)
    info = parse(question, calendar, prev_group)
    t = info["text"]
    rows = parse_rows(question, prev_group)
    if not rows and info["group"] not in (None, "FOMC") and info["actual"] is not None:
        # angka bebas ("NFP 45K") -> pindai juga dengan Cons & Prev dari kalender minggu ini
        cal = [c for c in calendar if c["group"] == info["group"]]
        prev = _numbers(cal[0]["previous"].lower()) if cal and cal[0]["previous"] else []
        rows = [{"name": cal[0]["title"] if cal else _nama(info["group"]), "group": info["group"],
                 "act": info["actual"], "cons": info["forecast"], "prev": prev[0] if prev and len(_numbers(t)) < 2 else None,
                 "inverse": info["group"] == "CLAIMS" or "pengangguran" in t, "counts": True}]
    if rows:
        reply = scan_answer(rows, calendar, now, info["btc"])
        sched = _schedule_line(rows[0]["group"], calendar, now) if rows[0]["group"] else None
        if sched:
            reply = reply.replace("\n", "\n" + sched + "\n", 1)
    elif info["group"]:
        reply = event_answer(info, calendar, now)
    elif _has(t, ["sl+", "sl +", "sl plus", "tp1", "tp 1", "tp2", "running", "trailing", "tangga", "0,7", "0.7", "skema"]):
        reply = SKEMA
    elif _has(t, ["funding", "september"]) or (info["btc"] and _has(t, ["filter"])):
        reply = filter_text(funding_cache, now)
    elif _has(t, ["sinyal", "posisi", "terbuka", "aktif", "open"]):
        reply = bot_answer(states or {}, funding_cache, now)
    elif _has(t, ["minggu ini", "jadwal", "kalender", "berita apa", "berita", "kapan", "news"]):
        reply = calendar_answer(calendar, now)
    else:
        reply = BANTUAN
    reply += "\n\nHasil masa lalu bukan jaminan. Selalu pakai SL, risiko 0,25–0,5% modal per sinyal."
    return {"ok": True, "reply": reply, "sources": [], "model": "data (tanpa AI)"}


def calendar_json(calendar_rows) -> list[dict]:
    """Kalender minggu ini untuk aplikasi (kartu Act/Cons/Prev): judul, grup, waktu WIB, forecast, previous."""
    return [{"title": c["title"], "group": c["group"], "time": c["time"].isoformat(), "when": _when(c["time"]),
             "forecast": c["forecast"], "previous": c["previous"]} for c in calendar_rows_for(calendar_rows)]


def fetch_calendar() -> list | None:
    try:
        req = urllib.request.Request(CALENDAR_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - kalender opsional
        return None
