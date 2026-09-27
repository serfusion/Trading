"""Audit keamanan statis untuk bot/EA pihak ketiga (python -m xau_bot audit <folder> [...]).

Kode TIDAK dijalankan: semua file dibaca sebagai teks lalu dicocokkan dengan pola yang umum dipakai malware
(keylogger, pencuri password/browser/wallet, unduh-lalu-jalankan, kode tersamar, pengiriman data akun MT5 ke
server asing) dan praktik berisiko (kredensial di dalam kode, file biner tanpa sumber, martingale/grid).

Tingkat:
- BAHAYA  : hampir tidak pernah ada di bot trading yang jujur -> jangan jalankan sebelum diperiksa manusia.
- WASPADA : bisa sah, bisa disalahgunakan -> baca baris yang ditunjuk.
- INFO    : risiko keuangan / kebersihan kode (mis. martingale, password tertulis di kode).
Hasil "tidak ada temuan" BUKAN jaminan aman; pemindai pola bisa dikelabui.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

TEXT_EXT = {".py", ".mq5", ".mq4", ".mqh", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".json", ".sh", ".bat",
            ".cmd", ".ps1", ".vbs", ".html", ".htm", ".md", ".txt", ".yml", ".yaml", ".toml", ".cfg", ".ini",
            ".ipynb", ".pine", ".cs", ".java", ".go", ".rs", ".php", ".rb", ".sql", ".env", ".set", ".dockerfile",
            ".r", ".c", ".cpp", ".h", ".kt", ".swift", ".lua", ".pl"}
CODE_EXT = TEXT_EXT - {".md", ".txt", ".json", ".set", ".sql"}
BINARY_DANGER = {".exe", ".dll", ".scr", ".msi", ".com", ".pif", ".hta", ".lnk", ".jar", ".cpl", ".sys", ".vbe",
                 ".wsf", ".appx", ".apk", ".dmg", ".pkg", ".deb", ".so", ".dylib", ".bin", ".elf"}
BINARY_OPAQUE = {".ex5", ".ex4", ".pyc", ".pyd", ".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".img", ".cab"}
PICKLE_EXT = {".pkl", ".pickle", ".joblib", ".pt", ".pth", ".ckpt", ".h5", ".npy", ".sav"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode"}
MAX_BYTES = 3_000_000


@dataclass(frozen=True)
class Rule:
    level: str
    code: str
    desc: str
    pattern: re.Pattern
    exts: frozenset | None = None     # None = semua file teks


def R(level, code, desc, pat, exts=None, flags=re.I):
    return Rule(level, code, desc, re.compile(pat, flags), frozenset(exts) if exts else None)


PY = {".py", ".ipynb"}
MQL = {".mq5", ".mq4", ".mqh"}
JS = {".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".html", ".htm"}
SHELL = {".sh", ".bat", ".cmd", ".ps1", ".vbs"}
ANYCODE = CODE_EXT
TRADE_CODE = PY | MQL | {".pine", ".cs"}

RULES = [
    # --- pencurian input / layar / clipboard
    R("BAHAYA", "keylogger", "Merekam ketikan keyboard",
      r"pynput\.keyboard|keyboard\.(on_press|hook|record)|GetAsyncKeyState|SetWindowsHookEx|pyHook|\bkeylog", ANYCODE),
    R("BAHAYA", "clipboard", "Membaca/mengganti clipboard (pola pencuri alamat wallet)",
      r"win32clipboard|pyperclip\.(paste|copy)|navigator\.clipboard\.readText|GetClipboardData", ANYCODE),
    R("WASPADA", "screenshot", "Mengambil tangkapan layar",
      r"ImageGrab\.grab|\bmss\(\)|pyautogui\.screenshot|screencapture", ANYCODE),
    # --- pencurian kredensial
    R("BAHAYA", "browser_theft", "Mengakses data login/cookie browser",
      r"Login Data['\"]|User Data\\\\[^'\"\n]*(Local State|Cookies)|['\"]Local State['\"]|browser_cookie3|"
      r"CryptUnprotectData|win32crypt|os_crypt", ANYCODE, flags=0),
    R("BAHAYA", "wallet_theft", "Mengakses file wallet kripto / Telegram / Discord",
      r"wallet\.dat|\\\\Exodus|Electrum\\\\wallets|MetaMask|nkbihfbeogaeaoehlefnkodbefgpgknn|tdata\\\\|"
      r"discord(app)?\\\\Local Storage|leveldb.*token", ANYCODE),
    R("BAHAYA", "mt5_accounts", "Membaca file akun/password tersimpan terminal MT5",
      r"accounts\.dat|\\\\config\\\\(common|accounts)\.ini|servers\.dat", ANYCODE),
    R("INFO", "mt5_datapath", "Memakai folder data terminal MT5 (umumnya sah: baca/tulis file sendiri)",
      r"TERMINAL_DATA_PATH|TERMINAL_COMMONDATA_PATH", ANYCODE),
    # --- unduh & jalankan / kode tersamar
    R("BAHAYA", "download_exec", "Mengunduh lalu menjalankan program",
      r"URLDownloadToFile|DownloadString|\biwr\b.+\|\s*iex|\bIEX\s*\(|Invoke-Expression|"
      r"certutil\s+-urlcache|bitsadmin\s+/transfer|mshta\s+http|curl[^\n|]*\|\s*(ba)?sh|wget[^\n|]*\|\s*(ba)?sh|"
      r"urlretrieve\([^)]*\.(exe|dll|scr|bat|ps1|msi)", ANYCODE),
    R("BAHAYA", "obfuscated_exec", "Menjalankan kode tersamar (exec/eval dari base64/zlib/marshal/hex)",
      r"(exec|eval)\s*\(\s*(base64|zlib|marshal|codecs|bytes\.fromhex|__import__\(['\"](base64|zlib|marshal))|"
      r"(exec|eval)\s*\(\s*compile\(|__pyarmor__|pyarmor_runtime|eval\(function\(p,a,c,k,e,[dr]\)|"
      r"powershell[^\n]*-e(nc(odedcommand)?)?\s+[A-Za-z0-9+/=]{40,}|FromBase64String", ANYCODE),
    R("WASPADA", "dyn_exec", "exec/eval/Function dinamis",
      r"(?<![.\w])(?<!def )exec\s*\(|(?<![.\w])(?<!def )eval\s*\(|new Function\s*\(|child_process|subprocess\.(Popen|run|call)\(.*shell\s*=\s*True|"
      r"os\.system\(|ShellExecute|WinExec|CreateProcess", ANYCODE),
    R("WASPADA", "long_blob", "String base64/hex sangat panjang (bisa payload tersembunyi)",
      r"['\"][A-Za-z0-9+/]{400,}={0,2}['\"]|(\\x[0-9a-fA-F]{2}){80,}", ANYCODE, flags=0),
    # --- persistensi & kendali jarak jauh
    R("BAHAYA", "persistence", "Memasang diri agar jalan otomatis saat Windows start",
      r"CurrentVersion\\\\Run|schtasks\s*/create|\\\\Start Menu\\\\Programs\\\\Startup|shell:startup|"
      r"New-Service|sc\.exe\s+create|reg\s+add\s+HK", ANYCODE),
    R("BAHAYA", "reverse_shell", "Pola reverse shell / remote shell",
      r"socket\.socket\([^)]*\)[\s\S]{0,300}(pty\.spawn|/bin/(ba)?sh\b|cmd\.exe)|nc\s+-e\s|"
      r"bash\s+-i\s*>&\s*/dev/tcp/|/dev/tcp/[^\s]+\s+0>&1", ANYCODE),
    R("WASPADA", "download_file", "Mengunduh file installer/program dari internet",
      r"Invoke-WebRequest[^\n]*-OutFile|DownloadFile\(|urlretrieve\(", ANYCODE),
    R("WASPADA", "av_evasion", "Mematikan/menghindari antivirus",
      r"Set-MpPreference|DisableRealtimeMonitoring|Add-MpPreference\s+-ExclusionPath|matikan antivirus|"
      r"disable (your )?(antivirus|windows defender)|turn off (your )?(antivirus|defender)", None),
    # --- MQL5 / MT5 khusus
    R("WASPADA", "mql_dll", "EA memanggil DLL Windows (#import .dll) — bisa melakukan apa saja di PC",
      r"#import\s+\"[^\"]+\.dll\"", MQL),
    R("WASPADA", "mql_webrequest", "EA mengirim/mengambil data internet (WebRequest)",
      r"\bWebRequest\s*\(|SocketCreate|InternetOpen", MQL),
    R("WASPADA", "mql_account_send", "Data akun (login/server/nama) dipakai di kode yang juga mengirim ke internet",
      r"ACCOUNT_LOGIN|ACCOUNT_SERVER|ACCOUNT_NAME|AccountNumber\(\)|AccountName\(\)", MQL),
    R("WASPADA", "license_lock", "Kunci lisensi/akun/masa berlaku (EA berhenti atau 'harus beli')",
      r"(allowed|valid|authorized)_?(account|login)s?|ExpiryDate|expir(e|ation)_?date|license_?key|"
      r"TimeCurrent\(\)\s*>\s*D'", MQL | PY),
    R("WASPADA", "cred_send", "Password/login broker ikut dikirim lewat HTTP",
      r"(requests\.(post|get)|fetch\(|axios\.(post|get)|WebRequest)[^\n]{0,200}(password|passwd|login|pwd)",
      ANYCODE),
    R("WASPADA", "hardcoded_chat", "Chat ID Telegram milik orang lain tertanam: notifikasi (saldo/trade) terkirim ke dia",
      r"chat_?id\s*[:=]\s*['\"]?-?\d{6,}", ANYCODE),
    R("WASPADA", "webhook_exfil", "Mengirim data ke webhook Discord / pastebin / layanan penampung",
      r"discord(app)?\.com/api/webhooks|pastebin\.com/api|webhook\.site|requestbin|ngrok\.io|pipedream\.net",
      ANYCODE),
    # --- umpan unduhan di README / halaman
    R("WASPADA", "download_lure", "Tautan unduhan file di luar GitHub / arsip berpassword",
      r"mediafire\.com|mega\.nz|drive\.google\.com/file|dropbox\.com/s|gofile\.io|anonfiles|bit\.ly/|tinyurl\.com|"
      r"cutt\.ly|t\.ly/|password\s*[:=]\s*\S+\s*(for|untuk)?\s*(the)?\s*(zip|rar|archive)|"
      r"releases/download/[^\s)]+\.(zip|rar|7z|exe)", {".md", ".html", ".htm", ".txt"}),
    R("INFO", "npm_hook", "Skrip npm otomatis saat install (preinstall/postinstall)",
      r"\"(pre|post)install\"\s*:", {".json"}),
    # --- risiko keuangan
    R("INFO", "martingale", "Martingale / kali-lipat lot setelah rugi",
      r"martingale|lot_?multiplier|LotMultiplier|lot\s*\*=\s*[1-9]|Multiplier\s*=\s*[12]\.\d", TRADE_CODE),
    R("INFO", "grid", "Grid / averaging (tambah posisi melawan harga)",
      r"\bgrid[_ ]?(trading|level|step|order|ea)|averaging|GridStep|grid_?step|recovery zone", TRADE_CODE),
    R("INFO", "hardcoded_secret", "Kredensial/token tertulis langsung di kode (bocor bila repo publik)",
      r"(password|passwd|api_?key|secret|token)\s*[:=]\s*['\"][^'\"\s{}$<>]{6,}['\"]|"
      r"\b\d{8,10}:AA[0-9A-Za-z_-]{30,}\b|sk-[A-Za-z0-9]{20,}", ANYCODE),
]

MQL_NET = re.compile(r"\bWebRequest\s*\(|SocketCreate|InternetOpen|SendFTP|SendMail")
VENDOR_MQL = re.compile(r"Copyright\s+2000-20\d\d,\s*MetaQuotes", re.I)
FALSE_POSITIVE_HINTS = re.compile(r"your[_-]?(password|api|token|key)|xxx|\*\*\*|<.*>|example|placeholder|"
                                  r"changeme|os\.getenv|os\.environ|getenv|process\.env", re.I)


@dataclass
class Finding:
    level: str
    code: str
    desc: str
    path: str
    line: int
    text: str


@dataclass
class Report:
    root: str
    files: int
    findings: list
    binaries: list          # (path, jenis)

    def count(self, level):
        return sum(1 for f in self.findings if f.level == level) + (
            sum(1 for _, k in self.binaries if k == "BAHAYA") if level == "BAHAYA" else 0)

    @property
    def verdict(self) -> str:
        codes = {f.code for f in self.findings if f.level == "BAHAYA"}
        if codes or any(k == "BAHAYA" for _, k in self.binaries):
            return "BAHAYA"
        if any(f.level == "WASPADA" for f in self.findings) or self.binaries:
            return "WASPADA"
        return "BERSIH"


def _iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            yield p


def _ext(p: Path) -> str:
    if p.name.lower() == "dockerfile":
        return ".dockerfile"
    ext = p.suffix.lower()
    if ext in BINARY_DANGER or ext in BINARY_OPAQUE or ext in PICKLE_EXT:
        return ext
    if _is_program(p):
        return ".exe"  # program Windows/Linux menyamar dengan ekstensi lain (mis. .jpg, .txt, .xlsx)
    if ext:
        return ext
    return _sniff(p)


def _is_program(p: Path) -> bool:
    try:
        with open(p, "rb") as fh:
            head = fh.read(4)
    except OSError:
        return False
    return head[:2] == b"MZ" or head == b"\x7fELF"


def _sniff(p: Path) -> str:
    """Tebak jenis file tanpa ekstensi (mis. source EA yang sengaja dibuang ekstensinya)."""
    try:
        head = p.read_bytes()[:4096]
    except OSError:
        return ""
    if head[:4] == b"PK\x03\x04":
        return ".zip"
    if b"\x00" in head:
        return ""
    t = head.decode("utf-8", "ignore")
    if re.search(r"#property\s|OnTick\s*\(|OnInit\s*\(", t):
        return ".mq5"
    if t.startswith("#!") or re.search(r"^\s*(import|from)\s+\w+", t, re.M):
        return ".py" if "python" in t[:80] or "import" in t else ".sh"
    if re.search(r"<html|<!doctype html", t, re.I):
        return ".html"
    return ".txt"


def scan(root: str | Path, ignore: list[str] | None = None) -> Report:
    """ignore: pola glob path relatif yang dilewati (mis. file berisi daftar pola pemindai ini sendiri)."""
    root = Path(root)
    findings, binaries, n = [], [], 0
    for p in _iter_files(root):
        rel = str(p.relative_to(root))
        if ignore and any(fnmatch(rel, pat) for pat in ignore):
            continue
        n += 1
        ext = _ext(p)
        if ext in BINARY_DANGER:
            binaries.append((rel, "BAHAYA"))
            continue
        if ext in BINARY_OPAQUE:
            binaries.append((rel, "WASPADA"))
            continue
        if ext in PICKLE_EXT:
            findings.append(Finding("WASPADA", "pickle_model", "File pickle/model: memuatnya bisa menjalankan kode",
                                    rel, 0, "(biner)"))
            continue
        if ext not in TEXT_EXT or p.stat().st_size > MAX_BYTES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if ext in MQL and VENDOR_MQL.search(text[:1500]) and "Include" in Path(rel).parts:
            continue  # pustaka standar MetaQuotes (deklarasi WinAPI dll.), bukan kode penulis
        lines = text.splitlines()
        for rule in RULES:
            if rule.exts is not None and ext not in rule.exts:
                continue
            seen, lines_hit = 0, set()
            for m in rule.pattern.finditer(text):
                ln = text.count("\n", 0, m.start()) + 1
                if ln in lines_hit:
                    continue
                lines_hit.add(ln)
                src = lines[ln - 1].strip() if ln - 1 < len(lines) else m.group(0)
                if rule.code == "hardcoded_secret" and FALSE_POSITIVE_HINTS.search(src):
                    continue
                if rule.code == "hardcoded_chat" and re.search(r"123456789|(\d)\1{5,}", src):
                    continue  # contoh/placeholder
                if rule.code == "long_blob" and re.search(r"image/(png|jpe?g|gif|svg)|data:image|font/", src):
                    continue
                if rule.code == "mql_account_send" and not MQL_NET.search(text):
                    continue  # hanya ditampilkan/dicatat di log, tidak ada kode internet di file ini
                findings.append(Finding(rule.level, rule.code, rule.desc, rel, ln, src[:160]))
                seen += 1
                if seen >= 5:
                    break
    return Report(str(root), n, findings, binaries)


def format_report(rep: Report, detail: bool = True, max_lines: int = 40) -> str:
    icon = {"BAHAYA": "🛑", "WASPADA": "⚠️", "BERSIH": "✅"}[rep.verdict]
    out = [f"{icon} {rep.verdict}  {rep.root}  ({rep.files} file, "
           f"{rep.count('BAHAYA')} bahaya, {sum(f.level == 'WASPADA' for f in rep.findings)} waspada, "
           f"{sum(f.level == 'INFO' for f in rep.findings)} info, {len(rep.binaries)} biner)"]
    if detail:
        order = {"BAHAYA": 0, "WASPADA": 1, "INFO": 2}
        for path, kind in rep.binaries[:max_lines]:
            out.append(f"   [{kind}] biner tanpa sumber yang bisa dibaca: {path}")
        for f in sorted(rep.findings, key=lambda f: (order[f.level], f.code, f.path, f.line))[:max_lines]:
            out.append(f"   [{f.level}] {f.code}: {f.path}:{f.line}  {f.text}")
    return "\n".join(out)


def main(paths: list[str], detail: bool = True, ignore: list[str] | None = None) -> int:
    worst = 0
    for p in paths:
        rep = scan(p, ignore)
        print(format_report(rep, detail))
        worst = max(worst, {"BERSIH": 0, "WASPADA": 1, "BAHAYA": 2}[rep.verdict])
    print("\nCatatan: pemindai pola hanya penyaring awal. 'BERSIH' bukan jaminan aman; jalankan bot baru hanya di"
          " akun demo / komputer terpisah.")
    return worst
