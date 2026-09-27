"""Audit riwayat git lengkap: setiap versi file yang PERNAH ada di repo (semua branch, tag, dan ref pull request),
bukan hanya versi terakhir. Kode TIDAK dijalankan; isi blob dibaca lewat `git cat-file` lalu dicocokkan dengan aturan
`xau_bot.audit` + deteksi file .env/rahasia yang sudah dihapus.

    python -m research.audit_riwayat /path/ke/mirrors --csv docs/riwayat_temuan.csv

Satu folder mirror = hasil `git clone --mirror <url> <owner>__<repo>.git`. Blob yang sama dengan versi HEAD dilewati
(sudah diperiksa di audit awal). Nilai rahasia disensor di laporan.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import csv
import re
import subprocess
import sys
import threading
from collections import Counter, defaultdict
from pathlib import Path

from xau_bot.audit import MAX_BYTES, TEXT_EXT, Finding, classify, ext_of, scan_text

ENV_SECRET = re.compile(r"^\s*(?:export\s+)?([A-Za-z0-9_]*(?:PASS|SECRET|TOKEN|API_?KEY|PRIVATE)[A-Za-z0-9_]*)\s*=\s*"
                        r"['\"]?([^'\"\s#]{4,})", re.M | re.I)
PLACEHOLDER = re.compile(r"your|xxx|\*\*\*|<|example|placeholder|changeme|here|isi_|ganti_|replace|dummy|test", re.I)
SECRET_VALUE = re.compile(r"(['\"=:]\s*['\"]?)([^'\"\s]{6,})")
IMPORTANT = {"BAHAYA", "WASPADA"}
LIB_DIR = re.compile(r"(^|/)(\.?venv[^/]*|env|site-packages|dist-packages|node_modules|vendor|third_party|"
                     r"_stdlib_backup)/", re.I)
SITE = re.compile(r"^(.*?(?:site|dist)-packages/)[^/]+\.dist-info/RECORD$")
SECRET_CODES = {"hardcoded_secret", "env_secret", "hardcoded_chat", "env_file"}


def git(repo: Path, *args: str, text: bool = True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text)
    return r.stdout


def mask(src: str) -> str:
    """Sensor nilai rahasia di baris temuan: sisakan 4 karakter pertama."""
    def rep(m):
        v = m.group(2)
        return m.group(1) + v[:4] + "…(disensor)"
    out = SECRET_VALUE.sub(rep, src)
    out = re.sub(r"\b(\d{8,10}):AA[0-9A-Za-z_-]{30,}", r"\1:AA…(disensor)", out)
    out = re.sub(r"\bsk-[A-Za-z0-9_-]{8}[A-Za-z0-9_-]+", "sk-…(disensor)", out)
    return out


def objects(repo: Path, *refs: str) -> dict[str, str]:
    """sha -> path pertama untuk semua objek yang terjangkau dari ref."""
    out = {}
    for line in git(repo, "rev-list", "--objects", *refs).splitlines():
        sha, _, path = line.partition(" ")
        if path and sha not in out:
            out[sha] = path
    return out


def blob_sizes(repo: Path, shas: list[str]) -> dict[str, int]:
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                       input="\n".join(shas) + "\n", capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) == 3 and p[1] == "blob":
            out[p[0]] = int(p[2])
    return out


def read_blobs(repo: Path, shas: list[str]):
    """Hasilkan (sha, isi bytes) memakai satu proses `git cat-file --batch`."""
    proc = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    def feed():  # tulis di thread terpisah: kalau tidak, pipa stdin/stdout saling menunggu (deadlock) di repo besar
        proc.stdin.write(("\n".join(shas) + "\n").encode())
        proc.stdin.close()
    threading.Thread(target=feed, daemon=True).start()
    for _ in shas:
        header = proc.stdout.readline().decode().split()
        if len(header) < 3:
            break
        size = int(header[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)
        yield header[0], data
    proc.wait()


def first_commits(repo: Path, wanted: set[str]) -> dict[str, tuple[int, str]]:
    """blob -> (urutan, 'hash tanggal penulis: judul') commit tertua yang memasukkannya."""
    out: dict[str, tuple[int, str]] = {}
    if not wanted:
        return out
    log = git(repo, "log", "--all", "--reverse", "--raw", "--no-abbrev", "--no-renames", "-c",
              "--format=@@%H %ad %an: %s", "--date=short")
    cur, idx = "", 0
    for line in log.splitlines():
        if line.startswith("@@"):
            idx += 1
            h, _, rest = line[2:].partition(" ")
            cur = (h[:10] + " " + rest)[:110]
        elif line.startswith(":"):
            parts = line.split("\t")[0].split()
            sha = parts[-2] if len(parts) >= 2 else ""
            # format -c (merge) punya beberapa sha sumber; sha hasil selalu kolom sebelum status
            if sha in wanted and sha not in out:
                out[sha] = (idx, cur)
    return out


def _vint(b: bytes, i: int) -> tuple[int, int]:
    v = shift = 0
    while i < len(b):
        x = b[i]
        i += 1
        v |= (x & 0x7F) << shift
        shift += 7
        if not x & 0x80:
            break
    return v, i


def archive_names(data: bytes) -> tuple[str, list[str]]:
    """Daftar nama file di dalam arsip zip/rar TANPA mengekstrak (hanya membaca header).
    -> (jenis, nama[]); jenis 'rar-terkunci' bila header RAR terenkripsi (nama tidak bisa dibaca)."""
    import io
    import struct
    import zipfile
    if data[:4] == b"PK\x03\x04":
        try:
            return "zip", zipfile.ZipFile(io.BytesIO(data)).namelist()
        except (zipfile.BadZipFile, ValueError, OSError):
            return "zip-rusak", []
    names: list[str] = []
    if data[:7] == b"Rar!\x1a\x07\x00":                          # RAR 4
        i = 7
        while i + 7 <= len(data):
            _crc, typ, flags, size = struct.unpack_from("<HBHH", data, i)
            if size < 7:
                break
            add = struct.unpack_from("<I", data, i + 7)[0] if flags & 0x8000 else 0
            if typ == 0x74 and i + 32 <= len(data):
                nlen = struct.unpack_from("<H", data, i + 26)[0]
                off = i + 32 + (8 if flags & 0x100 else 0)
                names.append(data[off:off + nlen].split(b"\x00")[0].decode("utf-8", "replace"))
            elif typ == 0x73 and flags & 0x80:
                return "rar-terkunci", names
            i += size + add
        return "rar", names
    if data[:8] == b"Rar!\x1a\x07\x01\x00":                      # RAR 5
        i = 8
        while i + 4 < len(data):
            hsize, j = _vint(data, i + 4)
            end = j + hsize
            htype, k = _vint(data, j)
            hflags, k = _vint(data, k)
            extra = data_size = 0
            if hflags & 1:
                extra, k = _vint(data, k)
            if hflags & 2:
                data_size, k = _vint(data, k)
            if htype == 4:                                         # header arsip terenkripsi
                return "rar-terkunci", names
            if htype == 2:
                fflags, k = _vint(data, k)
                _, k = _vint(data, k)
                _, k = _vint(data, k)
                k += (4 if fflags & 2 else 0) + (4 if fflags & 4 else 0)
                _, k = _vint(data, k)
                _, k = _vint(data, k)
                nlen, k = _vint(data, k)
                names.append(data[k:k + nlen].decode("utf-8", "replace"))
            if hsize == 0 or end + data_size <= i:
                break
            i = end + data_size
        return "rar", names
    return "lain", names


def _scan_blob(path: str, data: bytes) -> tuple[str | None, list[Finding]]:
    """-> (level biner atau None, daftar temuan)."""
    ext = ext_of(path, data[:4096])
    kind = classify(path, ext)
    if kind is not None:
        return (kind[1], []) if kind[0] == "biner" else (None, [kind[1]])
    if ext not in TEXT_EXT or len(data) > MAX_BYTES:
        return None, []
    text = data.decode("utf-8", "ignore")
    hits = scan_text(path, text, ext)
    if ext == ".env":
        hits.append(Finding("WASPADA", "env_file", "File .env ikut ter-commit", path, 0, "(file .env)"))
        for m in ENV_SECRET.finditer(text):
            if not PLACEHOLDER.search(m.group(2)):
                ln = text.count("\n", 0, m.start()) + 1
                hits.append(Finding("INFO", "env_secret", "Nilai rahasia di file .env", path, ln,
                                    m.group(0).strip()[:160]))
    return None, hits


def audit_repo(repo: Path) -> dict:
    """Pindai semua blob di semua ref. Temuan dikelompokkan (level, kode, path, teks); yang sudah ada di HEAD
    ditandai di_head=True (sudah tercakup audit awal)."""
    name = repo.name.removesuffix(".git")
    refs = git(repo, "for-each-ref", "--format=%(refname)").split()
    info = {"repo": name, "heads": sum(r.startswith("refs/heads/") for r in refs),
            "tags": sum(r.startswith("refs/tags/") for r in refs),
            "pull": sum(r.startswith("refs/pull/") for r in refs), "commits": 0, "blobs_all": 0, "blobs_new": 0,
            "findings": [], "binaries": []}
    if not refs:
        return info
    info["commits"] = len(git(repo, "rev-list", "--all").split())
    head_objs = {l.split()[2] for l in git(repo, "ls-tree", "-r", "HEAD").splitlines() if l.split()[1:2] == ["blob"]}
    bt_objs = objects(repo, "--branches", "--tags")
    all_objs = objects(repo, "--all")
    sizes = blob_sizes(repo, list(all_objs))
    info["blobs_all"] = len(sizes)
    info["blobs_new"] = sum(s not in head_objs for s in sizes)
    small = [s for s in sizes if sizes[s] <= MAX_BYTES * 4]
    raw_hits: list[tuple[str, Finding]] = []
    bins: list[tuple[str, str]] = []                 # (sha, level)
    for s in sizes:
        if sizes[s] > MAX_BYTES * 4:                 # file besar: klasifikasi dari nama saja
            kind = classify(all_objs[s], ext_of(all_objs[s], b""))
            if kind and kind[0] == "biner":
                bins.append((s, kind[1]))
    record: dict[str, set[str]] = defaultdict(set)   # path file pustaka -> hash sha256 menurut RECORD pip
    lib_hash: dict[str, str] = {}
    for sha, data in read_blobs(repo, small):
        path = all_objs[sha]
        m = SITE.match(path)
        if m:
            for line in data.decode("utf-8", "ignore").splitlines():
                parts = line.split(",")
                if len(parts) >= 2 and parts[1].startswith("sha256="):
                    record[m.group(1) + parts[0]].add(parts[1][7:])
        if LIB_DIR.search(path):
            lib_hash[sha] = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
        blevel, hits = _scan_blob(path, data)
        if blevel:
            bins.append((sha, blevel))
        raw_hits += [(sha, f) for f in hits]

    def lib_check(sha: str, path: str) -> str:
        if not LIB_DIR.search(path):
            return ""
        if path in record and sha in lib_hash:
            return "pustaka: cocok RECORD pip" if lib_hash[sha] in record[path] else "pustaka: BEDA dari RECORD pip"
        return "pustaka"
    keyed = [(sha, f, mask(f.text) if f.code in SECRET_CODES else f.text) for sha, f in raw_hits
             if f.level in IMPORTANT or f.code in SECRET_CODES]
    head_keys = {(f.code, t) for sha, f, t in keyed if sha in head_objs}
    want = {sha for sha, f, t in keyed if sha not in head_objs} | {b[0] for b in bins}
    intro = first_commits(repo, want)
    groups: dict[tuple, dict] = {}
    for sha, f, t in keyed:
        if sha in head_objs:
            continue
        g = groups.setdefault((f.level, f.code, f.path, t), {
            "repo": name, "level": f.level, "code": f.code, "path": f.path, "line": f.line, "versi": 0,
            "pr_only": True, "di_head": (f.code, t) in head_keys, "lokasi": lib_check(sha, f.path), "commit": "",
            "blob": sha[:10], "text": t})
        g["versi"] += 1
        g["pr_only"] = g["pr_only"] and sha not in bt_objs
        c = intro.get(sha)
        if c and (not g["commit"] or c[0] < g["_i"]):
            g["commit"], g["blob"], g["_i"], g["line"] = c[1], sha[:10], c[0], f.line
    info["findings"] = [{k: v for k, v in g.items() if k != "_i"} for g in groups.values()]
    for sha, level in bins:
        info["binaries"].append({"repo": name, "level": level, "path": all_objs[sha], "blob": sha[:10],
                                 "size": sizes[sha], "di_head": sha in head_objs, "pr_only": sha not in bt_objs,
                                 "lokasi": lib_check(sha, all_objs[sha]),
                                 "commit": intro.get(sha, (0, ""))[1]})
    return info


DANGER_INNER = re.compile(r"\.(exe|dll|scr|msi|com|pif|bat|cmd|ps1|vbs|vbe|js|jse|wsf|hta|lnk|jar|cpl|sys|so|dylib|"
                          r"apk|dmg|pkg|deb|iso|img)$", re.I)
OPAQUE_INNER = re.compile(r"\.(ex4|ex5|pyc|pyd|zip|rar|7z|gz|tar)$", re.I)


def audit_archives(mirrors: Path, biner_csv: Path, out_csv: Path) -> None:
    """Buka daftar isi setiap arsip .zip/.rar di riwayat (hanya header, tanpa ekstrak)."""
    rows = list(csv.DictReader(open(biner_csv)))
    out = []
    for r in rows:
        if not re.search(r"\.(zip|rar)$", r["path"], re.I):
            continue
        data = subprocess.run(["git", "-C", str(mirrors / (r["repo"] + ".git")), "cat-file", "blob", r["blob"]],
                              capture_output=True).stdout
        kind, names = archive_names(data)
        files = [n for n in names if n and not n.endswith("/")]
        danger = [n for n in files if DANGER_INNER.search(n)]
        opaque = [n for n in files if OPAQUE_INNER.search(n)]
        src = [n for n in files if re.search(r"\.(mq4|mq5|mqh|pine|txt|py|set)$", n, re.I)]
        out.append({"repo": r["repo"], "path": r["path"], "di_head": r["di_head"], "jenis": kind, "isi": len(files),
                    "berbahaya": len(danger), "biner_tertutup": len(opaque), "source": len(src),
                    "contoh_berbahaya": " | ".join(danger[:5]), "contoh_isi": " | ".join(files[:4])[:250]})
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, list(out[0]) if out else ["repo"])
        w.writeheader()
        w.writerows(out)
    kinds = Counter(o["jenis"] for o in out)
    print(f"{len(out)} arsip: {dict(kinds)}; berisi file berbahaya: {sum(o['berbahaya'] > 0 for o in out)}; "
          f"berisi .ex4/.ex5/arsip lain: {sum(o['biner_tertutup'] > 0 for o in out)}")


def scan_archive_bytes(data: bytes, where: str, depth: int = 0) -> tuple[list[dict], dict]:
    """Baca ISI arsip (zip/rar/7z/tar) di memori lewat libarchive — tidak ada yang ditulis ke disk atau dijalankan.
    Setiap anggota dipindai dengan aturan xau_bot.audit; arsip di dalam arsip dibuka sampai kedalaman 2."""
    import libarchive
    out: list[dict] = []
    st = Counter()
    try:
        with libarchive.memory_reader(data) as arc:
            for e in arc:
                if not e.isfile:
                    continue
                name = e.pathname or "?"
                if isinstance(name, bytes):
                    name = name.decode("utf-8", "replace")
                st["file"] += 1
                try:
                    buf = bytearray()
                    for blk in e.get_blocks():
                        buf += blk
                        if len(buf) > MAX_BYTES * 4:
                            break
                    body = bytes(buf)
                except libarchive.ArchiveError:
                    st["terkunci"] += 1
                    out.append({"lokasi": where, "anggota": name, "level": "WASPADA", "code": "arsip_terkunci",
                                "line": 0, "text": "(berpassword / tidak bisa dibaca)"})
                    continue
                ext = ext_of(name, body[:4096])
                if ext in {".zip", ".rar", ".7z", ".gz", ".tar"} and depth < 2:
                    sub, sst = scan_archive_bytes(body, f"{where} :: {name}", depth + 1)
                    out += sub
                    st.update(sst)
                    st["arsip_dalam"] += 1
                    continue
                kind = classify(name, ext)
                if kind is not None:
                    f = kind[1] if kind[0] == "temuan" else Finding(kind[1], "biner_dalam_arsip",
                                                                   "File biner/program di dalam arsip", name, 0,
                                                                   f"({ext or 'tanpa ekstensi'}, {len(body)} byte)")
                    out.append({"lokasi": where, "anggota": name, "level": f.level, "code": f.code, "line": 0,
                                "text": f.text})
                    st["biner"] += 1
                    continue
                if ext not in TEXT_EXT or len(body) > MAX_BYTES:
                    continue
                st["teks"] += 1
                for f in scan_text(name, body.decode("utf-8", "ignore"), ext):
                    out.append({"lokasi": where, "anggota": name, "level": f.level, "code": f.code, "line": f.line,
                                "text": mask(f.text) if f.code in SECRET_CODES else f.text})
    except libarchive.ArchiveError as exc:
        st["gagal"] += 1
        out.append({"lokasi": where, "anggota": "", "level": "WASPADA", "code": "arsip_gagal_dibaca", "line": 0,
                    "text": str(exc)[:120]})
    return out, dict(st)


def audit_archive_contents(mirrors: Path, biner_csv: Path, out_csv: Path) -> None:
    rows = [r for r in csv.DictReader(open(biner_csv)) if re.search(r"\.(zip|rar|7z)$", r["path"], re.I)]
    allf, tot = [], Counter()
    per = []
    for r in rows:
        data = subprocess.run(["git", "-C", str(mirrors / (r["repo"] + ".git")), "cat-file", "blob", r["blob"]],
                              capture_output=True).stdout
        found, st = scan_archive_bytes(data, r["path"])
        for f in found:
            f["repo"] = r["repo"]
        allf += found
        tot.update(st)
        lv = Counter(f["level"] for f in found)
        per.append({"repo": r["repo"], "arsip": r["path"], "di_head": r["di_head"], "file": st.get("file", 0),
                    "teks_dipindai": st.get("teks", 0), "biner": st.get("biner", 0), "BAHAYA": lv["BAHAYA"],
                    "WASPADA": lv["WASPADA"], "INFO": lv["INFO"], "terkunci": st.get("terkunci", 0) + st.get("gagal", 0)})
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, ["repo", "lokasi", "anggota", "level", "code", "line", "text"])
        w.writeheader()
        order = {"BAHAYA": 0, "WASPADA": 1, "INFO": 2}
        w.writerows(sorted(allf, key=lambda f: (f["repo"], order.get(f["level"], 3), f["code"], f["lokasi"])))
    with open(out_csv.with_name(out_csv.stem + "_per_arsip.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(per[0]))
        w.writeheader()
        w.writerows(per)
    print(f"{len(rows)} arsip, {tot.get('file', 0)} file di dalamnya, {tot.get('teks', 0)} file teks dipindai, "
          f"{tot.get('biner', 0)} biner, {tot.get('arsip_dalam', 0)} arsip-dalam-arsip, "
          f"{tot.get('terkunci', 0)} terkunci, {tot.get('gagal', 0)} gagal dibaca")
    print(Counter((f["level"], f["code"]) for f in allf).most_common(30))


def audit_fork(orig: Path, fork: Path) -> dict:
    """Bandingkan fork dengan repo asli: hanya commit & blob yang TIDAK ada di asli yang dipindai (termasuk isi arsip
    dan program Windows di dalamnya). fork dibuat dengan `git clone --mirror --reference <orig>`."""
    orig_commits = set(git(orig, "rev-list", "--all").split())
    fork_commits = git(fork, "rev-list", "--branches", "--tags").split()
    new_commits = [c for c in fork_commits if c not in orig_commits]
    orig_objs = objects(orig, "--all")
    fork_objs = objects(fork, "--branches", "--tags")
    cand = [sh for sh in fork_objs if sh not in orig_objs]
    sizes = blob_sizes(fork, cand)
    info = {"commit_baru": len(new_commits), "blob_baru": len(sizes), "file_baru": sorted({fork_objs[s] for s in sizes}),
            "temuan": [], "penulis": sorted({l for l in git(fork, "log", "--format=%an <%ae> %ad", "--date=short",
                                                              *new_commits[:200], "--no-walk").splitlines()})[:10]}
    for sha, data in read_blobs(fork, [s for s in sizes if sizes[s] <= MAX_BYTES * 4]):
        path = fork_objs[sha]
        blevel, hits = _scan_blob(path, data)
        if blevel:
            info["temuan"].append({"level": blevel, "code": "biner", "path": path, "line": 0,
                                   "text": f"({len(data)} byte)"})
            if re.search(r"\.(zip|rar|7z)$", path, re.I):
                found, _ = scan_archive_bytes(data, path)
                info["temuan"] += [{"level": f["level"], "code": f["code"], "path": f"{path} :: {f['anggota']}",
                                    "line": f["line"], "text": f["text"]} for f in found]
        for f in hits:
            info["temuan"].append({"level": f.level, "code": f.code, "path": f.path, "line": f.line,
                                   "text": mask(f.text) if f.code in SECRET_CODES else f.text})
    return info


def audit_forks(forks_dir: Path, mirrors: Path, out_csv: Path) -> None:
    rows, summ = [], []
    for fk in sorted(forks_dir.glob("*@@*.git")):
        orig_name, fork_name = fk.name.removesuffix(".git").split("@@")
        info = audit_fork(mirrors / f"{orig_name}.git", fk)
        lv = Counter(t["level"] for t in info["temuan"])
        summ.append({"asli": orig_name.replace("__", "/", 1), "fork": fork_name.replace("__", "/", 1),
                     "commit_baru": info["commit_baru"], "blob_baru": info["blob_baru"], "BAHAYA": lv["BAHAYA"],
                     "WASPADA": lv["WASPADA"], "INFO": lv["INFO"], "penulis": " | ".join(info["penulis"])[:200],
                     "file_baru": " ".join(info["file_baru"])[:500]})
        for t in info["temuan"]:
            rows.append({"fork": fork_name.replace("__", "/", 1), **t})
        print(f"{fork_name[:45]:45s} commit+{info['commit_baru']:4d} blob+{info['blob_baru']:5d} "
              f"bahaya={lv['BAHAYA']} waspada={lv['WASPADA']} info={lv['INFO']}", flush=True)
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, ["fork", "level", "code", "path", "line", "text"])
        w.writeheader()
        w.writerows(rows)
    with open(out_csv.with_name(out_csv.stem + "_ringkasan.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(summ[0]))
        w.writeheader()
        w.writerows(summ)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mirrors")
    ap.add_argument("--csv", default="")
    ap.add_argument("--only", default="", help="kata kunci nama repo")
    ap.add_argument("--arsip", default="", help="CSV keluaran: isi arsip zip/rar dari <csv>_biner.csv")
    ap.add_argument("--isi-arsip", default="", help="CSV keluaran: temuan di DALAM file arsip (butuh libarchive-c)")
    ap.add_argument("--fork", default="", help="folder berisi <asli>@@<fork>.git; hasil ke --csv")
    a = ap.parse_args(argv)
    if a.fork:
        audit_forks(Path(a.fork), Path(a.mirrors), Path(a.csv))
        return 0
    if a.isi_arsip:
        audit_archive_contents(Path(a.mirrors), Path(a.csv).with_name(Path(a.csv).stem + "_biner.csv"),
                               Path(a.isi_arsip))
        return 0
    if a.arsip:
        audit_archives(Path(a.mirrors), Path(a.csv).with_name(Path(a.csv).stem + "_biner.csv"), Path(a.arsip))
        return 0
    repos = sorted(p for p in Path(a.mirrors).iterdir() if p.name.endswith(".git") and a.only in p.name)
    rows, bin_rows, summary = [], [], []
    for repo in repos:
        info = audit_repo(repo)
        new = [f for f in info["findings"] if not f["di_head"] and not f["lokasi"]]
        nb = [b for b in info["binaries"] if not b["di_head"] and not b["lokasi"]]
        lib = [f for f in info["findings"] if not f["di_head"] and f["lokasi"]]
        libb = [b for b in info["binaries"] if not b["di_head"] and b["lokasi"]]
        bahaya = sum(f["level"] == "BAHAYA" for f in new) + sum(b["level"] == "BAHAYA" for b in nb)
        waspada = sum(f["level"] == "WASPADA" and f["code"] not in SECRET_CODES for f in new)
        rahasia = sum(f["code"] in SECRET_CODES for f in new)
        beda = sum("BEDA" in x["lokasi"] for x in lib + libb)
        summary.append((info["repo"], info["heads"], info["tags"], info["pull"], info["commits"], info["blobs_all"],
                        info["blobs_new"], bahaya, waspada, rahasia, len(nb), len(lib) + len(libb), beda))
        print(f"{info['repo'][:52]:52s} br={info['heads']:4d} tag={info['tags']} pr={info['pull']:4d} "
              f"commit={info['commits']:5d} blob={info['blobs_all']:6d} di_luar_head={info['blobs_new']:6d} | "
              f"hanya-di-riwayat: bahaya={bahaya} waspada={waspada} rahasia={rahasia} biner={len(nb)} "
              f"pustaka={len(lib) + len(libb)} (beda_RECORD={beda})", flush=True)
        rows += info["findings"]
        bin_rows += info["binaries"]
    if a.csv:
        out = Path(a.csv)
        order = {"BAHAYA": 0, "WASPADA": 1, "INFO": 2}
        with open(out, "w", newline="") as fh:
            w = csv.DictWriter(fh, ["repo", "level", "code", "di_head", "lokasi", "pr_only", "versi", "path", "line",
                                    "blob", "commit", "text"])
            w.writeheader()
            for r in sorted(rows, key=lambda r: (r["repo"], r["di_head"], r["lokasi"], order[r["level"]], r["code"], r["path"])):
                w.writerow(r)
        with open(out.with_name(out.stem + "_biner.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, ["repo", "level", "di_head", "lokasi", "pr_only", "path", "size", "blob", "commit"])
            w.writeheader()
            for r in sorted(bin_rows, key=lambda r: (r["repo"], r["di_head"], r["lokasi"], r["path"])):
                w.writerow(r)
        with open(out.with_name(out.stem + "_ringkasan.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["repo", "branch", "tag", "pr_ref", "commit", "blob_total", "blob_diluar_head",
                        "bahaya_baru", "waspada_baru", "rahasia_baru", "biner_baru", "temuan_pustaka", "pustaka_beda_record"])
            w.writerows(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
