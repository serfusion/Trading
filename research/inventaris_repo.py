"""Inventaris mendalam repo bot emas (python -m research.inventaris_repo <folder_berisi_repo> [out.csv]).

Membaca SEMUA file teks tiap repo (tanpa menjalankan apa pun) dan mencatat:
platform, timeframe, scalping, cara login MT5/broker, eksekusi order, SL/TP, trailing/BE, martingale/grid/hedging,
manajemen risiko, filter berita/sesi, AI/ML/LLM, Telegram, backtest, klaim kinerja di README/dokumen, dan hasil
pemindai keamanan (xau_bot.audit). Hasil otomatis ini adalah titik awal; kandidat tetap diperiksa manual.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

from xau_bot.audit import SKIP_DIRS, scan

CODE = {".py", ".ipynb", ".mq5", ".mq4", ".mqh", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".pine", ".gs", ".cs"}
DOCS = {".md", ".txt", ".html", ".rst"}
MAXB = 3_000_000


def _files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and not any(x in SKIP_DIRS for x in p.relative_to(root).parts):
            yield p


def _read(p: Path) -> str:
    try:
        if p.stat().st_size > MAXB:
            return ""
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def has(text: str, pat: str, flags=re.I) -> bool:
    return re.search(pat, text, flags) is not None


def claims(doc: str) -> str:
    """Angka kinerja yang ditulis penulis (README & dokumen)."""
    out = []
    pats = [
        ("WR", r"win[\s_-]*rate[^0-9\n]{0,25}(\d{1,3}(?:[.,]\d+)?)\s*%|(\d{1,3}(?:[.,]\d+)?)\s*%\s*win[\s_-]*rate"),
        ("PF", r"profit[\s_-]*factor[^0-9\n]{0,20}(\d+(?:[.,]\d+)?)"),
        ("Sharpe", r"sharpe(?:\s*ratio)?[^0-9\n-]{0,20}(-?\d+(?:[.,]\d+)?)"),
        ("DD", r"(?:max(?:imal|imum)?[\s_-]*)?drawdown[^0-9\n]{0,25}(\d+(?:[.,]\d+)?)\s*%"),
        ("Return", r"(?:total|net|annual(?:ized)?|6[- ]month)?\s*return[^0-9\n+-]{0,20}([+-]?\d+(?:[.,]\d+)?)\s*%"),
        ("Akurasi", r"(\d{2}(?:[.,]\d+)?)\s*%\s*(?:of\s+)?accuracy|accuracy[^0-9\n]{0,15}(\d{2}(?:[.,]\d+)?)\s*%"),
    ]
    for name, pat in pats:
        vals = []
        for m in re.finditer(pat, doc, re.I):
            v = next((g for g in m.groups() if g), None)
            if v and v not in vals:
                vals.append(v)
        if vals:
            out.append(f"{name} " + "/".join(vals[:3]))
    return "; ".join(out)


def timeframes(code: str) -> str:
    c = Counter()
    for m in re.finditer(r"(?:TIMEFRAME|PERIOD)_(M1|M5|M15|M30|H1|H4|D1)\b", code):
        c[m.group(1)] += 1
    for m in re.finditer(r"['\"](M1|M5|M15|M30|H1|H4|D1)['\"]", code):
        c[m.group(1)] += 1
    for m in re.finditer(r"interval\s*=\s*['\"](1m|5m|15m|30m|1h|4h|1d|1min|5min|15min)['\"]", code, re.I):
        c[m.group(1)] += 1
    return " ".join(k for k, _ in c.most_common(4))


def login_mode(code: str, ext_counter: Counter) -> str:
    modes = []
    if has(code, r"mt5\.(login|initialize)\s*\("):
        seg = " ".join(m.group(0) for m in re.finditer(r"mt5\.(?:login|initialize)\s*\([^)]{0,200}\)", code))
        if has(code, r"(MT5_)?(LOGIN|PASSWORD|ACCOUNT)\s*=\s*['\"]?[A-Za-z0-9_@!#$%^&*.-]{5,}['\"]?\s*(#.*)?$", re.M) and \
                not has(code, r"getenv|environ|dotenv|load_dotenv|config\.(get|MT5)|settings\.|st\.secrets"):
            modes.append("MT5 Python: login/password di file kode")
        elif has(code, r"getenv|environ|dotenv|load_dotenv"):
            modes.append("MT5 Python: dari .env/variabel lingkungan")
        elif has(seg, r"login\s*=|password\s*="):
            modes.append("MT5 Python: dari config")
        else:
            modes.append("MT5 Python: pakai terminal yang sudah login")
    if ext_counter[".mq5"] + ext_counter[".mq4"] and has(code, r"OnTick\s*\("):
        modes.append("EA MQL: jalan di terminal (tanpa simpan password)")
    if has(code, r"metaapi"):
        modes.append("MetaApi (token)")
    if has(code, r"oanda"):
        modes.append("Oanda API")
    if has(code, r"\bccxt\b|\bbinance\b|\bbybit\b|\bokx\b"):
        modes.append("Exchange kripto API")
    return "; ".join(dict.fromkeys(modes)) or "-"


def row(repo: Path) -> dict:
    exts = Counter()
    code, doc, n = [], [], 0
    for p in _files(repo):
        n += 1
        e = p.suffix.lower()
        if not e and p.stat().st_size < MAXB and re.search(r"#property\s|OnTick\s*\(", _read(p)[:5000]):
            e = ".mq5"  # source EA tanpa ekstensi file
        exts[e] += 1
        if e in CODE or (not e and p.stat().st_size < MAXB):
            code.append(_read(p))
        elif e in DOCS:
            doc.append(_read(p))
    code_t, doc_t = "\n".join(code), "\n".join(doc)
    all_t = code_t + "\n" + doc_t
    platform = []
    if exts[".mq5"] or exts[".mqh"]:
        platform.append("MQL5")
    if exts[".mq4"]:
        platform.append("MQL4")
    if exts[".ex5"] or exts[".ex4"]:
        platform.append(f"biner EA x{exts['.ex5'] + exts['.ex4']}")
    if has(code_t, r"import MetaTrader5|from MetaTrader5"):
        platform.append("Python-MT5")
    elif exts[".py"]:
        platform.append("Python" + ("-backtrader" if has(code_t, r"import backtrader") else ""))
    if exts[".pine"]:
        platform.append("Pine/TradingView")
    if exts[".js"] + exts[".ts"] + exts[".tsx"] + exts[".mjs"]:
        platform.append("JS/TS")
    if exts[".ipynb"]:
        platform.append("Notebook")
    orders = has(code_t, r"order_send\s*\(|ORDER_TYPE_BUY|trade\.(Buy|Sell|PositionOpen)\s*\(|OrderSend\s*\(|"
                         r"create_market_(buy|sell)_order|placeOrder|place_order|\.orders\.create|OrderCreate")
    sl = has(code_t, r"['\"]sl['\"]\s*:|\bsl\s*=|stop_?loss|StopLoss|InpSL|SL_ATR|sl_mult|stopLoss")
    return {
        "repo": repo.name.replace("__", "/", 1),
        "file": n,
        "platform": " ".join(platform) or "-",
        "timeframe": timeframes(code_t),
        "scalping": "ya" if has(all_t, r"scalp|\bHFT\b|high[- ]frequency|TIMEFRAME_M1\b|PERIOD_M1\b") else "",
        "login": login_mode(code_t, exts),
        "order_otomatis": "ya" if orders else "sinyal/analisis",
        "sl_tp": "ya" if sl else ("TIDAK terdeteksi" if orders else ""),
        "trailing_be": "ya" if has(code_t, r"trail|break[_ -]?even|\bBE\b") else "",
        "martingale": "ya" if has(code_t, r"martingale|lot_?multiplier|LotMultiplier") else "",
        "grid": "ya" if has(code_t, r"\bgrid[_ ]?(step|level|order|trading)|GridStep|averaging") else "",
        "hedging": "ya" if has(code_t, r"\bhedg") else "",
        "risiko": " ".join(k for k, p in [("%risiko", r"risk_?(pct|percent|per_trade)|RiskPercent|RISK_PER"),
                                           ("batas-harian", r"daily_?(loss|dd|drawdown)|DailyLoss|max_daily"),
                                           ("maks-posisi", r"max_?(open_)?(trades|positions)|MaxTrades|MaxPositions")]
                          if has(code_t, p)),
        "filter": " ".join(k for k, p in [("berita", r"forexfactory|economic.?calendar|CalendarValue|news_?filter|high.?impact"),
                                           ("sesi", r"session|killzone|london|new ?york")] if has(code_t, p)),
        "ai": " ".join(k for k, p in [("ML", r"xgboost|lightgbm|sklearn|RandomForest|catboost"),
                                       ("DeepL", r"import torch|tensorflow|keras|LSTM"),
                                       ("RL", r"stable_baselines3|PPO\b|gymnasium|import gym"),
                                       ("LLM", r"openai|groq|deepseek|langchain|ollama|anthropic|gemini|openrouter")]
                       if has(code_t, p)),
        "telegram": "ya" if has(code_t, r"telegram") else "",
        "backtest": "ya" if has(all_t, r"backtest|backtrader|vectorbt|strategy tester|strategy\(") else "",
        "klaim": claims(doc_t),
    }


def main(folder: str, out: str | None = None) -> list[dict]:
    rows = []
    for repo in sorted(Path(folder).iterdir()):
        if not repo.is_dir():
            continue
        r = row(repo)
        r["keamanan"] = scan(repo).verdict
        rows.append(r)
    if out:
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return rows


if __name__ == "__main__":
    res = main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    for r in res:
        print(" | ".join(f"{k}={v}" for k, v in r.items() if v not in ("", "-")))
