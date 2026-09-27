"""Inventaris kemampuan SETIAP file di repo pihak ketiga (tahap C). Kode TIDAK dijalankan.

Python/notebook dibaca dengan AST (impor + panggilan fungsi yang sebenarnya, bukan sekadar kata di komentar);
MQL/JS/shell/dll. dengan pola teks. Setiap file diberi label kemampuan:

  jaringan   : menghubungi internet (HTTP, socket, Telegram, API LLM, WebRequest, fetch, ...)
  server     : membuka server/port (Flask, FastAPI, http.server, express)
  tulis_file : menulis/menghapus/memindah file
  proses     : menjalankan program lain / shell / DLL / ctypes
  kode_dinamis: exec/eval/compile/importlib, memuat pickle/joblib/torch (bisa menjalankan kode)
  kredensial : membaca password/token (env, .env, keyring, argumen login)
  login_mt5  : login ke akun MT5 (mt5.initialize/login dengan akun)
  order      : mengirim/mengubah/menutup order (MT5, MQL, Oanda, ccxt, MetaApi, ...)
  sistem     : registry Windows, clipboard, keyboard/mouse, tangkapan layar, info mesin

    python -m research.inventaris_file /path/folder-berisi-repo --csv docs/inventaris_file.csv
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from xau_bot.audit import BINARY_DANGER, BINARY_OPAQUE, MAX_BYTES, MQL, PICKLE_EXT, SKIP_DIRS, TEXT_EXT, VENDOR_MQL, ext_of

CAPS = ["jaringan", "server", "tulis_file", "proses", "kode_dinamis", "kredensial", "login_mt5", "order", "sistem"]

# --- Python: modul yang diimpor -> kemampuan
PY_MODULES = {
    "jaringan": {"requests", "urllib", "urllib2", "urllib3", "http", "httpx", "aiohttp", "socket", "websocket",
                 "websockets", "telegram", "telebot", "aiogram", "pyrogram", "telethon", "smtplib", "ftplib",
                 "paramiko", "openai", "groq", "anthropic", "google", "cohere", "mistralai", "ollama", "langchain",
                 "langchain_core", "langchain_openai", "yfinance", "oandapyV20", "v20", "ccxt", "metaapi_cloud_sdk",
                 "tweepy", "praw", "newsapi", "fredapi", "alpha_vantage", "twelvedata", "polygon", "finnhub",
                 "tradingview_ta", "tvdatafeed", "feedparser", "bs4", "selenium", "playwright", "discord",
                 "slack_sdk", "twilio", "pusher", "pika", "redis", "pymongo", "psycopg2", "supabase", "firebase_admin",
                 "boto3", "grpc", "zmq", "pyzmq", "investpy", "mt5linux", "huggingface_hub",
                 "transformers", "ib_insync", "alpaca_trade_api", "binance", "pybit", "gdown", "wget"},
    "server": {"flask", "fastapi", "uvicorn", "django", "aiohttp.web", "http.server", "socketserver", "tornado",
               "streamlit", "dash", "gradio", "websockets.server", "sanic", "bottle"},
    "proses": {"subprocess", "ctypes", "win32api", "win32process", "win32com", "pywinauto", "multiprocessing",
               "pty", "cffi"},
    "kode_dinamis": {"importlib", "pickle", "joblib", "dill", "cloudpickle", "marshal", "torch", "keras",
                     "tensorflow", "stable_baselines3", "onnxruntime", "xgboost", "lightgbm", "catboost"},
    "kredensial": {"dotenv", "keyring", "getpass", "decouple", "environs"},
    "sistem": {"winreg", "_winreg", "win32clipboard", "pyperclip", "pynput", "keyboard", "mouse", "pyautogui",
               "mss", "PIL.ImageGrab", "wmi", "win32gui"},
}
PY_CALLS = {
    "jaringan": re.compile(r"^(requests|httpx|session|s|client|aiohttp\.ClientSession|urllib\.request)\.(get|post|put|"
                           r"delete|patch|request|urlopen)$|^urlopen$|^socket\.(socket|create_connection)$|"
                           r"\.send_message$|\.sendMessage$|\.chat\.completions\.create$|\.messages\.create$|"
                           r"\.generate_content$|^yf\.(download|Ticker)$|\.urlretrieve$"),
    "server": re.compile(r"\.run$|^uvicorn\.run$|\.serve_forever$|^app\.(route|get|post)$"),
    "tulis_file": re.compile(r"\.(to_csv|to_excel|to_parquet|to_pickle|to_json|to_feather|to_hdf|savefig|save_model|"
                             r"write_text|write_bytes|mkdir|makedirs|unlink|rmdir|rmtree|remove|rename|replace|move|"
                             r"copy|copyfile|copy2|copytree|touch|save|dump|dumps_to_file|write)$|^(np\.save|np\.savez|"
                             r"joblib\.dump|pickle\.dump|torch\.save|json\.dump|shutil\.\w+|os\.remove|os\.unlink|"
                             r"os\.rename|os\.makedirs|os\.mkdir|os\.rmdir)$"),
    "proses": re.compile(r"^(os\.system|os\.popen|os\.startfile|os\.exec\w*|os\.spawn\w*|subprocess\.\w+|"
                         r"ctypes\.\w+|ShellExecute\w*|win32api\.\w+)$"),
    "kode_dinamis": re.compile(r"^(exec|eval|compile|__import__|importlib\.import_module|pickle\.loads?|joblib\.load|"
                               r"dill\.loads?|marshal\.loads|torch\.load|load_model|keras\.models\.load_model|"
                               r"PPO\.load|DQN\.load|A2C\.load|SAC\.load|\w+\.load_model)$"),
    "kredensial": re.compile(r"^(os\.getenv|os\.environ\.get|getenv|load_dotenv|dotenv_values|config|getpass\.getpass|"
                             r"keyring\.get_password)$"),
    "login_mt5": re.compile(r"^(mt5|MetaTrader5|self\.mt5|mt)\.(initialize|login)$"),
    "order": re.compile(r"(^|\.)(order_send|order_check|OrderSend|create_order|createMarketBuyOrder|"
                        r"createMarketSellOrder|createLimitBuyOrder|createLimitSellOrder|createStopBuyOrder|"
                        r"createStopSellOrder|closePosition|close_position|modifyPosition|place_order|"
                        r"market_order|submit_order|OrderCreate|TradeCreate|PositionClose|position_close)$"),
    "sistem": re.compile(r"^(pyperclip\.\w+|ImageGrab\.grab|pyautogui\.\w+|keyboard\.\w+|winreg\.\w+|"
                         r"platform\.node|uuid\.getnode)$"),
}
PY_ATTR = {  # akses atribut/subscript tanpa panggilan
    "kredensial": re.compile(r"^os\.environ$"),
}

# --- bahasa lain: pola teks
TEXT_RULES = {
    "jaringan": r"\bWebRequest\s*\(|SocketCreate|InternetOpen|SendFTP|SendMail\s*\(|\bfetch\s*\(|axios\b|"
                r"XMLHttpRequest|new WebSocket|\bcurl\s+|\bwget\s+|Invoke-WebRequest|Invoke-RestMethod|"
                r"https?://|\bnet/http\b|HttpClient|requests\.",
    "server": r"express\(\)|\.listen\s*\(\s*\d|createServer|http\.server|app\.run\(",
    "tulis_file": r"\bFileOpen\s*\([^)]*FILE_WRITE|FileWrite\w*\s*\(|FileDelete|FileMove|FileCopy|fs\.(write|unlink|"
                  r"rm|rename|appendFile)|writeFile|localStorage\.setItem|>\s*\S+\.(txt|csv|log|json)|Out-File|"
                  r"\brm\s+-|\bdel\s+/|Remove-Item",
    "proses": r"#import\s+\"[^\"]+\.dll\"|ShellExecute\w*|WinExec|CreateProcess|child_process|\bspawn\s*\(|"
              r"\bexecSync\b|Start-Process|\bcmd(\.exe)?\s+/c|powershell\s|\bnohup\b|\bsystemctl\b|\bpip3?\s+install|"
              r"\bnpm\s+(i|install)\b|\bsudo\b",
    "kode_dinamis": r"(?<![.\w])eval\s*\(|new Function\s*\(|Invoke-Expression|\biex\b|\bsource\s+\S+\.sh|"
                    r"OnnxCreate|require\s*\(\s*[a-zA-Z_]",
    "kredensial": r"process\.env|import\.meta\.env|\$env:|\bpassword\b|\bpasswd\b|api[_-]?key|\btoken\b|secret",
    "login_mt5": r"\bmt5\.(initialize|login)\s*\(|AccountInfo\w*\(\s*ACCOUNT_LOGIN|TerminalInfo\w*\(|"
                 r"\bMT5_(LOGIN|PASSWORD|SERVER)\b",
    "order": r"\bOrderSend\s*\(|\btrade\.(Buy|Sell|BuyLimit|SellLimit|BuyStop|SellStop|PositionOpen|PositionClose|"
             r"PositionModify|OrderOpen|OrderDelete|OrderModify)\s*\(|\bOrderClose\s*\(|\bOrderModify\s*\(|"
             r"PositionClose\s*\(|createMarket(Buy|Sell)Order|order_send|placeOrder|create_order|strategy\.(entry|"
             r"order|exit|close)\s*\(|/accounts/\$\{[^}]+\}/(orders|trades)|/v3/accounts/[^'\"]*/orders|"
             r"MarketOrderRequest|\bmarketOrder\b",
    "sistem": r"GetAsyncKeyState|SetWindowsHookEx|navigator\.clipboard|HKEY_|RegOpenKey|RegSetValue|"
              r"GetClipboardData|screencapture|TerminalClose|crontab|schtasks|getUserMedia",
}
TEXT_RULES = {k: re.compile(v, re.I if k in {"kredensial"} else 0) for k, v in TEXT_RULES.items()}
DOC_EXT = {".md", ".txt", ".rst", ".csv", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".set", ".sql",
           ".html", ".htm", ".svg", ".xml", ".lock", ".log"}
URL = re.compile(r"(?:https?|wss?)://([A-Za-z0-9.-]+\.[A-Za-z]{2,})(?::\d+)?")
COMMON_DOMAINS = re.compile(
    r"(^|\.)(github\.com|githubusercontent\.com|github\.io|shields\.io|img\.shields\.io|python\.org|pypi\.org|"
    r"mql5\.com|metaquotes\.net|metatrader5\.com|microsoft\.com|google\.com|googleapis\.com|gstatic\.com|"
    r"youtube\.com|youtu\.be|wikipedia\.org|stackoverflow\.com|w3\.org|mozilla\.org|npmjs\.com|npmjs\.org|"
    r"jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com|fonts\.googleapis\.com|reactjs\.org|react\.dev|nextjs\.org|"
    r"vercel\.com|vercel\.app|tailwindcss\.com|localhost|127\.0\.0\.1|0\.0\.0\.0|example\.com|opensource\.org|"
    r"creativecommons\.org|apache\.org|gnu\.org|readthedocs\.io|readthedocs\.org|docs\.python\.org|"
    r"api\.telegram\.org|t\.me|telegram\.org|openai\.com|anthropic\.com|groq\.com|x\.ai|openrouter\.ai|"
    r"tradingview\.com|investing\.com|forexfactory\.com|yahoo\.com|finance\.yahoo\.com|oanda\.com|"
    r"alphavantage\.co|stlouisfed\.org|twelvedata\.com|metaapi\.cloud|agiliumtrade\.ai|kaggle\.com|"
    r"huggingface\.co|docker\.com|linkedin\.com|twitter\.com|x\.com|discord\.gg|discord\.com|reddit\.com|"
    r"medium\.com|streamlit\.io|fastapi\.tiangolo\.com|flask\.palletsprojects\.com|pandas\.pydata\.org|"
    r"numpy\.org|scikit-learn\.org|matplotlib\.org|plotly\.com|jupyter\.org|colab\.research\.google\.com|"
    r"schema\.org|json-schema\.org|supabase\.co|supabase\.com|ntfy\.sh|binance\.com|gemini\.google\.com|"
    r"generativelanguage\.googleapis\.com|anaconda\.org|conda\.io|apple\.com|ollama\.com|ollama\.ai|"
    r"polygon\.io|finnhub\.io|newsapi\.org|nasdaq\.com|cmegroup\.com|kitco\.com|gold-api\.com|goldapi\.io|"
    r"metalpriceapi\.com|exchangerate-api\.com|coingecko\.com|marketwatch\.com|bloomberg\.com|reuters\.com|"
    r"cnbc\.com|fxstreet\.com|dailyfx\.com|myfxbook\.com|babypips\.com|icmarkets\.com|exness\.com|xm\.com|"
    r"pepperstone\.com|mql5\.net|gitlab\.com|bitbucket\.org|sourceforge\.net|nvidia\.com|pytorch\.org|"
    r"tensorflow\.org|keras\.io|xgboost\.readthedocs\.io|lightgbm\.readthedocs\.io|onnx\.ai|onnxruntime\.ai)$",
    re.I)


def _dotted(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    elif isinstance(node, ast.Call):
        parts.append(_dotted(node.func) + "()")
    return ".".join(reversed(parts))


def py_caps(src: str) -> tuple[set[str], set[str], dict[str, list[str]]]:
    """-> (kemampuan, modul yang diimpor, contoh pemanggil per kemampuan)."""
    caps: set[str] = set()
    evidence: dict[str, list[str]] = defaultdict(list)
    mods: set[str] = set()
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):   # mis. Python 2: pakai pola teks
        caps, ev = text_caps(src, ".py")
        return caps, {"(gagal-parse)"}, ev
    alias: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name)
                alias[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
            for a in node.names:
                alias[a.asname or a.name] = f"{node.module}.{a.name}"
    for m in mods:
        top = m.split(".")[0]
        for cap, names in PY_MODULES.items():
            if m in names or top in names:
                caps.add(cap)
                evidence[cap].append(f"import {m}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _dotted(node.func)
            head, _, rest = name.partition(".")
            full = alias.get(head, head) + ("." + rest if rest else "")
            for cap, pat in PY_CALLS.items():
                if pat.search(name) or pat.search(full):
                    if cap == "server" and not ({"flask", "fastapi", "uvicorn", "http", "socketserver", "django",
                                                  "tornado", "sanic", "bottle"} & {x.split(".")[0] for x in mods}):
                        continue
                    if cap == "tulis_file" and name.endswith((".replace", ".copy", ".save", ".dump", ".write",
                                                              ".move")) and not _file_like(name, mods):
                        continue
                    caps.add(cap)
                    evidence[cap].append(f"{name}() L{node.lineno}")
            modes = list(node.args[1:2]) + [k.value for k in node.keywords if k.arg == "mode"]
            if name in {"open", "io.open", "codecs.open"} and any(
                    isinstance(a, ast.Constant) and isinstance(a.value, str) and set(a.value) & set("wax+")
                    for a in modes):
                caps.add("tulis_file")
                evidence["tulis_file"].append(f"open(.., 'w') L{node.lineno}")
            if "mt5" in name.lower() and name.split(".")[-1] in {"initialize", "login"} and (
                    node.keywords or len(node.args) >= 1):
                kws = {k.arg for k in node.keywords}
                if kws & {"login", "password", "server"} or name.endswith("login"):
                    caps.add("login_mt5")
                    evidence["login_mt5"].append(f"{name}(login=..) L{node.lineno}")
        elif isinstance(node, (ast.Attribute, ast.Subscript)):
            name = _dotted(node.value if isinstance(node, ast.Subscript) else node)
            for cap, pat in PY_ATTR.items():
                if pat.search(name):
                    caps.add(cap)
                    evidence[cap].append(f"{name} L{node.lineno}")
    return caps, mods, evidence


def _file_like(name: str, mods: set[str]) -> bool:
    low = name.lower()
    return any(k in low for k in ("shutil", "os.", "path", "file", "f.", "fh.", "fp.", "model", "joblib", "pickle",
                                  "json", "wb", "workbook", "writer", "df", "fig", "plt", "np."))


def text_caps(src: str, ext: str) -> tuple[set[str], dict[str, list[str]]]:
    caps: set[str] = set()
    evidence: dict[str, list[str]] = defaultdict(list)
    if ext in DOC_EXT:
        return caps, evidence
    for cap, pat in TEXT_RULES.items():
        for m in pat.finditer(src):
            if cap == "jaringan" and m.group(0).startswith("http"):
                line = src[src.rfind("\n", 0, m.start()) + 1:src.find("\n", m.end())]
                if re.match(r"\s*(//|#|\*|/\*|<!--|;)", line):
                    continue   # URL di komentar
            caps.add(cap)
            ln = src.count("\n", 0, m.start()) + 1
            evidence[cap].append(f"{m.group(0)[:40]} L{ln}")
            if len(evidence[cap]) >= 3:
                break
    return caps, evidence


def notebook_source(raw: str) -> tuple[str, bool]:
    """Gabungkan sel kode notebook. Baris '!cmd' / '%magic' dibuang dari AST tapi dicatat sebagai proses."""
    try:
        nb = json.loads(raw)
    except json.JSONDecodeError:
        return "", False
    lines, shell = [], False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        for line in src.splitlines():
            if line.lstrip().startswith(("!", "%")):
                shell = shell or line.lstrip().startswith(("!", "%%bash", "%%sh", "%system"))
                lines.append("")
            else:
                lines.append(line)
        lines.append("")
    return "\n".join(lines), shell


def inventory_file(path: Path, rel: str) -> dict:
    head = b""
    try:
        with open(path, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        pass
    ext = ext_of(path.name, head)
    size = path.stat().st_size
    row = {"path": rel, "ext": ext or "(?)", "bytes": size, "baris": 0, "jenis": "", "kemampuan": "",
           "bukti": "", "impor": "", "domain": ""}
    if ext in BINARY_DANGER:
        row["jenis"] = "program/biner"
        return row
    if ext in BINARY_OPAQUE:
        row["jenis"] = "biner/arsip tertutup"
        return row
    if ext in PICKLE_EXT:
        row["jenis"] = "model/pickle"
        row["kemampuan"] = "kode_dinamis"
        return row
    if ext not in TEXT_EXT or size > MAX_BYTES:
        row["jenis"] = "data/gambar/lainnya" if ext not in TEXT_EXT else "teks besar (dilewati)"
        return row
    raw = path.read_text(encoding="utf-8", errors="ignore")
    row["baris"] = raw.count("\n") + 1
    if ext in MQL and VENDOR_MQL.search(raw[:1500]) and "Include" in Path(rel).parts:
        row["jenis"] = "pustaka standar MetaQuotes"
        return row
    evidence: dict[str, list[str]] = {}
    if ext == ".py":
        caps, mods, evidence = py_caps(raw)
        row["jenis"] = "kode python"
        row["impor"] = " ".join(sorted({m.split(".")[0] for m in mods}))[:300]
    elif ext == ".ipynb":
        src, shell = notebook_source(raw)
        caps, mods, evidence = py_caps(src)
        if shell:
            caps.add("proses")
            evidence.setdefault("proses", []).append("!perintah shell di notebook")
        row["jenis"] = "notebook"
        row["impor"] = " ".join(sorted({m.split(".")[0] for m in mods}))[:300]
        raw = src
    else:
        caps, evidence = text_caps(raw, ext)
        row["jenis"] = "dokumen/konfigurasi" if ext in DOC_EXT else "kode"
    domains = sorted({m.group(1).lower() for m in URL.finditer(raw)})
    row["domain"] = " ".join(domains)[:400]
    row["kemampuan"] = ";".join(c for c in CAPS if c in caps)
    row["bukti"] = " | ".join(f"{c}: {', '.join(list(dict.fromkeys(evidence.get(c, [])))[:3])}"
                             for c in CAPS if c in caps)[:600]
    return row


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            yield p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="folder yang berisi satu subfolder per repo")
    ap.add_argument("--csv", default="")
    a = ap.parse_args(argv)
    rows = []
    for repo in sorted(p for p in Path(a.folder).iterdir() if p.is_dir()):
        for f in iter_files(repo):
            r = inventory_file(f, str(f.relative_to(repo)))
            rows.append({"repo": repo.name, **r})
    per_repo: dict[str, Counter] = defaultdict(Counter)
    doms: dict[str, set] = defaultdict(set)
    for r in rows:
        per_repo[r["repo"]]["file"] += 1
        for c in filter(None, r["kemampuan"].split(";")):
            per_repo[r["repo"]][c] += 1
        for d in r["domain"].split():
            if r["jenis"] not in ("dokumen/konfigurasi",):
                doms[r["repo"]].add(d)
    for repo, cnt in per_repo.items():
        rare = sorted(d for d in doms[repo] if not COMMON_DOMAINS.search(d))
        print(f"{repo[:48]:48s} file={cnt['file']:5d} " + " ".join(f"{c}={cnt[c]}" for c in CAPS if cnt[c]) +
              (f"  domain-tak-umum: {' '.join(rare)[:200]}" if rare else ""))
    if a.csv:
        with open(a.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, ["repo", "path", "ext", "bytes", "baris", "jenis", "kemampuan", "bukti", "impor",
                                    "domain"])
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
