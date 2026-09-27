"""Analisa statis program Windows (.exe/.dll) di dalam arsip riwayat repo — TANPA menjalankannya.

Untuk setiap biner: SHA256 (cek sendiri di https://www.virustotal.com/gui/file/<sha256>), ukuran, waktu kompilasi,
section (entropi tinggi = kemungkinan dipadatkan/tersandi), DLL & fungsi Windows yang diimpor, fungsi berisiko
(jaringan, unduh, keyboard/clipboard, injeksi proses, registry, kripto), dan URL/domain di string-nya. Juga daftar
URL di source EA (MQL) dalam arsip yang memakai WebRequest.

    python -m research.analisa_biner /path/mirrors docs/riwayat/riwayat_temuan_biner.csv --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RISKY = {
    "jaringan": r"^(Internet(Open|Connect|ReadFile|OpenUrl)|HttpSendRequest|HttpOpenRequest|WinHttp\w+|URLDownloadTo\w+|"
                r"WSAStartup|socket|connect|send|recv|gethostbyname|getaddrinfo|InternetGetConnectedState)",
    "keyboard_clipboard_layar": r"^(GetAsyncKeyState|GetKeyState|SetWindowsHookEx\w*|GetClipboardData|OpenClipboard|"
                                r"BitBlt|GetDC)$",
    "injeksi_proses": r"^(VirtualAllocEx|WriteProcessMemory|CreateRemoteThread\w*|NtUnmapViewOfSection|"
                      r"QueueUserAPC|SetThreadContext|OpenProcess)$",
    "jalankan_program": r"^(CreateProcess\w*|ShellExecute\w*|WinExec|system|_wsystem)$",
    "registry": r"^(RegSetValue\w*|RegCreateKey\w*|RegOpenKey\w*)$",
    "kripto_data_windows": r"^(CryptUnprotectData|CryptProtectData|CryptDecrypt|BCryptDecrypt)$",
    "anti_debug": r"^(IsDebuggerPresent|CheckRemoteDebuggerPresent|NtQueryInformationProcess)$",
    "muat_kode_dinamis": r"^(LoadLibrary\w*|GetProcAddress|LdrLoadDll)$",
}
RISKY = {k: re.compile(v) for k, v in RISKY.items()}
URL = re.compile(rb"(?:https?|ftp|wss?)://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{4,200}")
URLW = re.compile(rb"(?:h\x00t\x00t\x00p\x00s?\x00:\x00/\x00/\x00)(?:[\x20-\x7e]\x00){4,200}")


def entropy(b: bytes) -> float:
    if not b:
        return 0.0
    c = Counter(b)
    n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def analyze_pe(data: bytes) -> dict:
    import pefile
    out = {"sha256": hashlib.sha256(data).hexdigest(), "ukuran": len(data), "kompilasi": "", "section": "",
           "impor_dll": "", "fungsi_berisiko": "", "url": "", "catatan": ""}
    urls = {u.decode("ascii", "ignore") for u in URL.findall(data)}
    urls |= {u.replace(b"\x00", b"").decode("ascii", "ignore") for u in URLW.findall(data)}
    out["url"] = " ".join(sorted(urls))[:600]
    try:
        pe = pefile.PE(data=data, fast_load=False)
    except pefile.PEFormatError as e:
        out["catatan"] = f"bukan PE valid: {e}"[:120]
        return out
    ts = pe.FILE_HEADER.TimeDateStamp
    try:
        out["kompilasi"] = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        out["kompilasi"] = str(ts)
    secs = []
    packed = False
    for s in pe.sections:
        name = s.Name.rstrip(b"\x00").decode("ascii", "ignore")
        e = entropy(s.get_data())
        secs.append(f"{name}:{e:.1f}")
        if e > 7.2 or name.upper().startswith(("UPX", ".VMP", ".THEMIDA", ".ENIGMA", ".ASPACK")):
            packed = True
    out["section"] = " ".join(secs)
    dlls, risky = [], Counter()
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) or []:
        dll = entry.dll.decode("ascii", "ignore").lower()
        dlls.append(dll)
        for imp in entry.imports:
            fn = (imp.name or b"").decode("ascii", "ignore")
            for cat, rx in RISKY.items():
                if rx.search(fn):
                    risky[f"{cat}:{fn}"] += 1
    out["impor_dll"] = " ".join(sorted(set(dlls)))
    out["fungsi_berisiko"] = " ".join(sorted(risky))[:800]
    notes = []
    if packed:
        notes.append("section entropi tinggi / packer (isi disamarkan)")
    if len(dlls) <= 2 and packed:
        notes.append("impor sangat sedikit = pola loader/packer")
    exp = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if exp:
        names = [(s.name or b"").decode("ascii", "ignore") for s in exp.symbols]
        notes.append(f"{len(names)} fungsi diekspor: {' '.join(names[:12])}")
    sig = pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]]
    notes.append("bertanda tangan digital" if sig.Size else "tanpa tanda tangan digital")
    out["catatan"] = "; ".join(notes)
    return out


def main(argv=None) -> int:
    import libarchive
    ap = argparse.ArgumentParser()
    ap.add_argument("mirrors")
    ap.add_argument("biner_csv")
    ap.add_argument("--csv", default="")
    ap.add_argument("--mql-url", default="", help="CSV: URL di source MQL dalam arsip yang memakai WebRequest")
    a = ap.parse_args(argv)
    rows, mql = [], []
    seen = set()
    for r in csv.DictReader(open(a.biner_csv)):
        if not re.search(r"\.(zip|rar|7z)$", r["path"], re.I):
            continue
        blob = subprocess.run(["git", "-C", str(Path(a.mirrors) / (r["repo"] + ".git")), "cat-file", "blob",
                               r["blob"]], capture_output=True).stdout
        try:
            with libarchive.memory_reader(blob) as arc:
                for e in arc:
                    if not e.isfile:
                        continue
                    name = e.pathname if isinstance(e.pathname, str) else e.pathname.decode("utf-8", "replace")
                    try:
                        body = b"".join(e.get_blocks())
                    except libarchive.ArchiveError:
                        continue
                    if body[:2] == b"MZ":
                        info = analyze_pe(body)
                        if info["sha256"] in seen:
                            continue
                        seen.add(info["sha256"])
                        rows.append({"repo": r["repo"], "arsip": r["path"], "file": name, **info})
                    elif re.search(r"\.(mq4|mq5|mqh)$", name, re.I):
                        text = body.decode("utf-8", "ignore")
                        if "\x00" in text[:200]:
                            text = body.decode("utf-16", "ignore")
                        if re.search(r"\bWebRequest\s*\(|InternetOpen|SocketCreate|SendFTP", text):
                            urls = sorted(set(re.findall(r"(?:https?|ftp)://[^\s\"'<>)]+", text)))
                            acct = bool(re.search(r"ACCOUNT_LOGIN|AccountNumber\(\)|ACCOUNT_NAME|AccountName\(\)|"
                                                  r"ACCOUNT_SERVER|AccountServer\(\)|ACCOUNT_BALANCE|AccountBalance\(\)",
                                                  text))
                            dll = sorted(set(re.findall(r"#import\s+\"([^\"]+)\"", text)))
                            mql.append({"repo": r["repo"], "arsip": r["path"], "file": name, "pakai_data_akun": acct,
                                        "dll_import": " ".join(dll), "url": " ".join(urls)[:700]})
        except libarchive.ArchiveError:
            continue
    print(f"{len(rows)} program Windows unik dianalisa; {len(mql)} source EA dengan fungsi internet")
    for x in rows:
        print(f"- {x['file'][-60:]} | {x['ukuran']:,} B | {x['kompilasi']} | {x['catatan'][:90]}")
        if x["fungsi_berisiko"]:
            print(f"    berisiko: {x['fungsi_berisiko'][:300]}")
        if x["url"]:
            print(f"    url: {x['url'][:300]}")
    if a.csv:
        with open(a.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    if a.mql_url and mql:
        with open(a.mql_url, "w", newline="") as fh:
            w = csv.DictWriter(fh, list(mql[0]))
            w.writeheader()
            w.writerows(mql)
    return 0


if __name__ == "__main__":
    sys.exit(main())
