"""Arsip berita ke GitHub (permintaan pengguna 30 Sep 2026): setiap aplikasi dibuka, hasil berita pekan ini (judul,
negara, waktu, dampak, Cons, Prev, dan Act bila sudah ada) disimpan ke repo supaya riset berikutnya punya data
lengkap tanpa mengunduh ulang.

Alur: aplikasi -> GET /api/chat (cloud) -> kalender ForexFactory (cache Supabase 10 menit untuk semua pengguna) +
Act FRED (berita USD utama) -> file JSON per pekan `data/berita/<tahun>/ff_<tanggal awal pekan>.json` di branch
ARSIP_BRANCH (bawaan `arsip-berita`, dibuat otomatis dari branch default) lewat GitHub Contents API.

Token GitHub HANYA di environment Vercel (GITHUB_TOKEN, fine-grained: repo ini, izin Contents read & write), tidak
pernah di APK. Anti-limit: GitHub ditulis hanya bila isi berubah dan paling sering tiap 15 menit (kecuali ada Act
baru); isi lama digabung (Act yang sudah tersimpan tidak hilang). Tanpa GITHUB_TOKEN arsip mati, aplikasi tetap
jalan. Hanya library standar Python.
"""
from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

MIN_GAP = timedelta(minutes=15)
FF_TTL = timedelta(minutes=10)
API = "https://api.github.com"


def _utc(date: str) -> str | None:
    try:
        return datetime.fromisoformat(date).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def records(rows: list | None, calendar: list | None) -> list[dict]:
    """Baris ForexFactory (semua negara & dampak) + Act dari calendar_json (FRED) bila ada."""
    act = {(c.get("title"), c.get("time")): (c.get("actual"), c.get("actual_src") or "")
           for c in calendar or [] if c.get("actual")}
    out = []
    for r in rows or []:
        t = _utc(r.get("date"))
        if not t:
            continue
        rec = {"title": r.get("title") or "", "country": r.get("country") or "", "time_utc": t,
               "date": r.get("date"), "impact": r.get("impact") or "", "forecast": r.get("forecast") or "",
               "previous": r.get("previous") or ""}
        for k in ("actual",):                                # bila suatu saat feed FF memuat Act
            if r.get(k):
                rec["actual"], rec["actual_src"] = r[k], "ForexFactory"
        a = act.get((rec["title"], t))
        if a and not rec.get("actual"):
            rec["actual"], rec["actual_src"] = a
        out.append(rec)
    return sorted(out, key=lambda x: (x["time_utc"], x["country"], x["title"]))


def merge(old: list, new: list, now: datetime) -> list:
    """Gabung isi lama & baru per (judul, negara, waktu); nilai kosong tidak menimpa nilai lama."""
    key = lambda r: (r.get("title"), r.get("country"), r.get("time_utc"))  # noqa: E731
    out = {key(r): dict(r) for r in old or []}
    stamp = now.isoformat()
    for r in new:
        prev = out.get(key(r), {})
        m = {**prev, **{k: v for k, v in r.items() if v not in ("", None)}}
        m["first_seen"] = prev.get("first_seen") or stamp
        if m.get("actual") and not prev.get("actual"):
            m["actual_saved"] = stamp                        # kapan Act pertama kali tercatat
        out[key(r)] = m
    return sorted(out.values(), key=lambda x: (x.get("time_utc") or "", x.get("country") or "", x.get("title") or ""))


def week_path(recs: list) -> str:
    start = min(r["time_utc"] for r in recs)[:10]
    return f"data/berita/{start[:4]}/ff_{start}.json"


class GitHub:
    def __init__(self, token: str, repo: str, branch: str, opener=None):
        self.repo, self.branch = repo, branch
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "xau-signal-arsip"}
        self.open = opener or urllib.request.urlopen

    def req(self, method: str, path: str, body: dict | None = None):
        """(status, json). 404/409/422 dikembalikan sebagai status, bukan exception."""
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(API + path, data=data, method=method, headers=self.headers)
        try:
            with self.open(r, timeout=15) as resp:
                raw = resp.read().decode()
                return resp.status, (json.loads(raw) if raw.strip() else None)
        except urllib.error.HTTPError as e:
            if e.code in (404, 409, 422):
                return e.code, None
            raise

    def ensure_branch(self) -> None:
        code, _ = self.req("GET", f"/repos/{self.repo}/branches/{urllib.parse.quote(self.branch)}")
        if code == 200:
            return
        code, repo = self.req("GET", f"/repos/{self.repo}")
        if not repo:
            raise PermissionError(f"token tidak bisa membaca repo {self.repo} (HTTP {code}): cek Repository access "
                                  "token & izin Contents read/write")
        _, ref = self.req("GET", f"/repos/{self.repo}/git/ref/heads/{repo['default_branch']}")
        if not ref:
            raise PermissionError("branch default tidak terbaca oleh token")
        self.req("POST", f"/repos/{self.repo}/git/refs",
                 {"ref": f"refs/heads/{self.branch}", "sha": ref["object"]["sha"]})

    def get_json(self, path: str) -> tuple[dict | None, str | None]:
        code, data = self.req("GET", f"/repos/{self.repo}/contents/{path}?ref={urllib.parse.quote(self.branch)}")
        if code != 200 or not data:
            return None, None
        return json.loads(base64.b64decode(data["content"]).decode("utf-8")), data["sha"]

    def put_json(self, path: str, obj: dict, sha: str | None, message: str) -> int:
        body = {"message": message, "branch": self.branch,
                "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8")).decode()}
        if sha:
            body["sha"] = sha
        code, _ = self.req("PUT", f"/repos/{self.repo}/contents/{path}", body)
        return code


def save(rows: list | None, calendar: list | None, now: datetime, store, env: dict, gh: GitHub | None = None) -> dict:
    """Simpan kalender pekan ini ke GitHub bila berubah. Return status singkat (ikut di respons GET /api/chat)."""
    token = env.get("GITHUB_TOKEN", "")
    if not token and gh is None:
        return {"status": "mati (GITHUB_TOKEN belum diisi di Vercel)"}
    recs = records(rows, calendar)
    if not recs:
        return {"status": "kalender kosong"}
    digest = hashlib.sha256(json.dumps(recs, sort_keys=True).encode()).hexdigest()
    n_act = sum(1 for r in recs if r.get("actual"))
    state = {}
    if store is not None:
        try:
            state = store.get_state("arsip") or {}
        except Exception:  # noqa: BLE001 - state opsional
            state = {}
    if state.get("hash") == digest:
        return {"status": "tidak berubah", "path": state.get("path")}
    last = state.get("t")
    if last and now - datetime.fromisoformat(last) < MIN_GAP and n_act <= state.get("n_actual", 0):
        return {"status": "ditunda (maks 1x per 15 menit bila tidak ada Act baru)", "path": state.get("path")}
    gh = gh or GitHub(token, env.get("ARSIP_REPO", "serfusion/Trading"), env.get("ARSIP_BRANCH", "arsip-berita"))
    gh.ensure_branch()
    path = week_path(recs)
    old, sha = gh.get_json(path)
    merged = merge((old or {}).get("berita", []), recs, now)
    doc = {"sumber": "ForexFactory (nfs.faireconomy.media) + Act FRED; dikumpulkan cloud/api/_arsip.py",
           "berita": merged}
    if old and old.get("berita") == merged:
        code = 200                                            # isi sama: tidak perlu commit
    else:
        doc["diperbarui"] = now.isoformat()
        code = gh.put_json(path, doc, sha, f"Arsip berita {path[-15:-5]}: {n_act} Act, {len(merged)} berita")
    if code in (200, 201) and store is not None:
        try:
            store.save_state({"hash": digest, "t": now.isoformat(), "n_actual": n_act, "path": path}, "arsip")
        except Exception:  # noqa: BLE001
            pass
    return {"status": "tersimpan" if code in (200, 201) else f"gagal HTTP {code} (dicoba lagi nanti)", "path": path}


def calendar_cached(store, now: datetime, fetch) -> list | None:
    """Kalender ForexFactory dengan cache Supabase 10 menit (satu unduhan untuk semua pembukaan aplikasi);
    bila unduh gagal, pakai cache lama."""
    cached = {}
    if store is not None:
        try:
            cached = store.get_state("kalender") or {}
        except Exception:  # noqa: BLE001
            cached = {}
    if cached.get("t") and cached.get("rows") and now - datetime.fromisoformat(cached["t"]) < FF_TTL:
        return cached["rows"]
    rows = fetch()
    if rows and store is not None:
        try:
            store.save_state({"t": now.isoformat(), "rows": rows}, "kalender")
        except Exception:  # noqa: BLE001
            pass
    return rows or cached.get("rows")
