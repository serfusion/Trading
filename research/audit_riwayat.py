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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mirrors")
    ap.add_argument("--csv", default="")
    ap.add_argument("--only", default="", help="kata kunci nama repo")
    a = ap.parse_args(argv)
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
