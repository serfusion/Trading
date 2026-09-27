"""Audit dependensi (tahap A2): paket yang akan terpasang bila Anda menjalankan `pip install -r` / `npm install` di
repo pihak ketiga. Tidak memasang apa pun; hanya membaca file manifest lalu menanyakan PyPI/npm (metadata publik).

Yang ditandai:
- paket TIDAK ADA di PyPI/npm (bisa diklaim orang lain = dependency confusion) atau namanya mirip paket populer
  (typosquatting, mis. `reqeusts`);
- paket yang sangat baru/sedikit rilis;
- instalasi dari git/URL/folder lokal, index tambahan (`--extra-index-url`), skrip npm `pre/postinstall`;
- versi yang dipatok tapi tidak pernah dirilis.

    python -m research.audit_dependensi /path/folder-berisi-repo --csv docs/dependensi.csv
"""
from __future__ import annotations

import argparse
import subprocess
import csv
import json
import re
import sys
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

MANIFEST = re.compile(r"(^|/)(requirements[^/]*\.txt|package\.json|pyproject\.toml|environment[^/]*\.ya?ml|setup\.py)$")
SKIP = {"node_modules", ".git", ".venv", "venv"}
NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(.*)$")
POPULAR_PY = """numpy pandas requests scipy matplotlib scikit-learn sklearn torch tensorflow keras xgboost lightgbm catboost
python-dotenv dotenv flask fastapi uvicorn pydantic sqlalchemy aiohttp httpx websockets websocket-client beautifulsoup4
lxml yfinance ta ta-lib TA-Lib pandas-ta MetaTrader5 metaapi-cloud-sdk python-telegram-bot telebot pyTelegramBotAPI
openai anthropic groq google-generativeai langchain transformers plotly seaborn streamlit dash redis celery pytest
schedule pytz tzdata python-dateutil tqdm joblib statsmodels backtrader ccxt oandapyV20 feedparser vaderSentiment
textblob nltk stable-baselines3 gymnasium gym onnxruntime onnx skl2onnx hmmlearn loguru rich click typer psutil
cryptography pyyaml PyYAML toml jinja2 werkzeug gunicorn supabase boto3 pymongo psycopg2 psycopg2-binary alembic
colorama tabulate openpyxl xlsxwriter mplfinance kaleido selenium playwright tweepy praw newsapi-python fredapi
alpha-vantage twelvedata finnhub-python polygon-api-client investpy tradingview-ta arch optuna shap mlflow wandb
pyarrow fastparquet numba cython setuptools wheel pip black ruff flake8 mypy isort pre-commit coverage hypothesis
prometheus-client structlog tenacity cachetools diskcache orjson ujson msgpack pyzmq zmq apscheduler""".split()
POPULAR_NPM = """react react-dom next vue vite typescript express axios lodash moment dayjs chart.js recharts
lightweight-charts tailwindcss postcss autoprefixer eslint prettier jest vitest webpack babel-loader @babel/core dotenv
cors body-parser mongoose mongodb pg mysql2 redis socket.io ws node-fetch cheerio puppeteer playwright nodemon
jsonwebtoken bcrypt bcryptjs uuid zod yup formik react-router-dom framer-motion clsx classnames date-fns
@tanstack/react-query swr zustand redux @reduxjs/toolkit three d3 express-rate-limit helmet morgan winston
nodemailer stripe openai @anthropic-ai/sdk @supabase/supabase-js firebase telegraf node-telegram-bot-api""".split()


def norm(n: str) -> str:
    return re.sub(r"[-_.]+", "-", n).lower()


def parse_requirements(text: str) -> list[dict]:
    out = []
    for raw in text.splitlines():
        line = raw.split(" #")[0].strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-i", "--index-url", "--extra-index-url", "-f", "--find-links", "--trusted-host")):
            out.append({"name": "", "spec": line, "flag": "index/sumber tambahan"})
            continue
        if line.startswith(("-r", "-c", "--requirement", "--constraint")):
            continue
        if line.startswith(("-e", "--editable")) or re.match(r"^(git\+|hg\+|svn\+|https?://|file:|\.{0,2}/)", line) \
                or " @ " in line:
            out.append({"name": line.split("#egg=")[-1] if "#egg=" in line else line.split(" @ ")[0], "spec": line,
                        "flag": "dari git/URL/lokal"})
            continue
        m = NAME.match(line.split(";")[0])
        if m:
            out.append({"name": m.group(1), "spec": m.group(3).strip(), "flag": ""})
    return out


def parse_package_json(text: str) -> tuple[list[dict], list[str]]:
    try:
        j = json.loads(text)
    except json.JSONDecodeError:
        return [], ["package.json rusak"]
    deps, notes = [], []
    for sec in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        for n, v in (j.get(sec) or {}).items():
            v = str(v)
            flag = "dari git/URL/lokal" if re.match(r"^(git|github:|gitlab:|bitbucket:|https?:|file:|link:|\.|/)", v) \
                or re.match(r"^[\w-]+/[\w.-]+(#.*)?$", v) else ""
            deps.append({"name": n, "spec": v, "flag": flag})
    for k, v in (j.get("scripts") or {}).items():
        if k in ("preinstall", "install", "postinstall", "prepare", "prepublish"):
            notes.append(f"skrip {k}: {v}")
    return deps, notes


def parse_pyproject(text: str) -> list[dict]:
    try:
        t = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    reqs = list((t.get("project") or {}).get("dependencies") or [])
    for grp in ((t.get("project") or {}).get("optional-dependencies") or {}).values():
        reqs += grp
    poetry = ((t.get("tool") or {}).get("poetry") or {})
    for sec in ("dependencies", "dev-dependencies"):
        for n, v in (poetry.get(sec) or {}).items():
            if n.lower() != "python":
                reqs.append(f"{n} {v if isinstance(v, str) else ''}")
    for grp in (poetry.get("group") or {}).values():
        for n, v in (grp.get("dependencies") or {}).items():
            reqs.append(f"{n} {v if isinstance(v, str) else ''}")
    return parse_requirements("\n".join(reqs))


def parse_env_yml(text: str) -> list[dict]:
    out, pip = [], False
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("- pip:"):
            pip = True
            continue
        if pip and s.startswith("- "):
            out += parse_requirements(s[2:])
    return out


_cache: dict[tuple[str, str], dict] = {}


def registry(eco: str, name: str) -> dict:
    key = (eco, norm(name) if eco == "pypi" else name)
    if key in _cache:
        return _cache[key]
    url = f"https://pypi.org/pypi/{name}/json" if eco == "pypi" else f"https://registry.npmjs.org/{name.replace('/', '%2F')}"
    info = {"ada": None, "rilis": 0, "pertama": "", "terakhir": "", "versi": set()}
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "audit-dependensi"}), timeout=20) as r:
                j = json.load(r)
            info["ada"] = True
            if eco == "pypi":
                rel = j.get("releases") or {}
                times = sorted(f["upload_time"] for fs in rel.values() for f in fs if f.get("upload_time"))
                info.update(rilis=len(rel), versi=set(rel), pertama=times[0][:10] if times else "",
                            terakhir=times[-1][:10] if times else "")
            else:
                t = {k: v for k, v in (j.get("time") or {}).items() if k not in ("created", "modified")}
                info.update(rilis=len(j.get("versions") or {}), versi=set(j.get("versions") or {}),
                            pertama=(j.get("time") or {}).get("created", "")[:10],
                            terakhir=max(t.values())[:10] if t else "")
            break
        except HTTPError as e:
            if e.code == 404:
                info["ada"] = False
                break
            time.sleep(2 ** attempt)
        except Exception:  # jaringan
            time.sleep(2 ** attempt)
    _cache[key] = info
    return info


def typo_of(name: str, popular: list[str]) -> str:
    n = norm(name)
    pops = {norm(p): p for p in popular}
    if n in pops:
        return ""
    best, score = "", 0.0
    for pn, p in pops.items():
        r = SequenceMatcher(None, n, pn).ratio()
        if r > score:
            best, score = p, r
    if score >= 0.88 and abs(len(n) - len(norm(best))) <= 2:
        return best
    return ""


def pinned_version(spec: str) -> str:
    m = re.match(r"^\s*==\s*([\w.\-+]+)\s*$", spec or "")
    return m.group(1) if m else ""


def history_items(mirrors: Path) -> list[tuple[str, str, str, dict]]:
    """Semua versi file manifest di riwayat git (semua ref) dari folder mirror."""
    items = []
    for m in sorted(mirrors.glob("*.git")):
        objs = subprocess.run(["git", "-C", str(m), "rev-list", "--objects", "--all"], capture_output=True,
                              text=True).stdout.splitlines()
        seen = set()
        for line in objs:
            sha, _, path = line.partition(" ")
            if not path or not MANIFEST.search(path) or any(x in SKIP for x in path.split("/")) or sha in seen:
                continue
            seen.add(sha)
            text = subprocess.run(["git", "-C", str(m), "cat-file", "blob", sha], capture_output=True).stdout.decode(
                "utf-8", "ignore")
            name = path.rsplit("/", 1)[-1]
            if name == "package.json":
                deps, eco = parse_package_json(text)[0], "npm"
            elif name == "pyproject.toml":
                deps, eco = parse_pyproject(text), "pypi"
            elif name.startswith("environment"):
                deps, eco = parse_env_yml(text), "pypi"
            elif name == "setup.py":
                continue
            else:
                deps, eco = parse_requirements(text), "pypi"
            items += [(m.name.removesuffix(".git"), f"{path} @{sha[:8]}", eco, d) for d in deps]
    return items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--csv", default="")
    ap.add_argument("--riwayat", action="store_true", help="folder = kumpulan mirror *.git; baca semua versi manifest")
    a = ap.parse_args(argv)
    items = []          # (repo, file, eco, dep)
    notes = []          # (repo, file, catatan)
    if a.riwayat:
        items = history_items(Path(a.folder))
    for repo in ([] if a.riwayat else sorted(p for p in Path(a.folder).iterdir() if p.is_dir())):
        for f in sorted(repo.rglob("*")):
            rel = f.relative_to(repo)
            if not f.is_file() or any(x in SKIP for x in rel.parts) or not MANIFEST.search(str(rel)):
                continue
            text = f.read_text(errors="ignore")
            if f.name == "package.json":
                deps, nts = parse_package_json(text)
                eco = "npm"
                notes += [(repo.name, str(rel), n) for n in nts]
            elif f.name == "pyproject.toml":
                deps, eco = parse_pyproject(text), "pypi"
            elif f.name.startswith("environment"):
                deps, eco = parse_env_yml(text), "pypi"
            elif f.name == "setup.py":
                deps = parse_requirements("\n".join(re.findall(r"['\"]([A-Za-z0-9_.\-]+[^'\"]*)['\"]",
                                                                "".join(re.findall(r"install_requires\s*=\s*\[([^\]]*)\]",
                                                                                   text, re.S)))))
                eco = "pypi"
            else:
                deps, eco = parse_requirements(text), "pypi"
            items += [(repo.name, str(rel), eco, d) for d in deps]
    uniq = sorted({(eco, d["name"]) for _, _, eco, d in items if d["name"] and not d["flag"]})
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda x: registry(*x), uniq))
    rows = []
    for repo, rel, eco, d in items:
        flag = [d["flag"]] if d["flag"] else []
        info = registry(eco, d["name"]) if d["name"] and not d["flag"] else {}
        if info:
            if info["ada"] is False:
                flag.append("TIDAK ADA di registry")
            elif info["ada"] is None:
                flag.append("registry tidak terjangkau")
            else:
                if info["rilis"] <= 2:
                    flag.append(f"hanya {info['rilis']} rilis")
                if info["pertama"] >= "2025-06-01":
                    flag.append(f"baru dibuat {info['pertama']}")
                pv = pinned_version(d["spec"])
                if pv and pv not in info["versi"]:
                    flag.append(f"versi {pv} tidak pernah dirilis")
            t = typo_of(d["name"], POPULAR_PY if eco == "pypi" else POPULAR_NPM)
            if t:
                flag.append(f"mirip '{t}'")
        rows.append({"repo": repo, "file": rel, "ekosistem": eco, "paket": d["name"], "versi": d["spec"],
                     "ada": info.get("ada", ""), "rilis": info.get("rilis", ""), "pertama": info.get("pertama", ""),
                     "tanda": "; ".join(flag)})
    for repo, rel, n in notes:
        rows.append({"repo": repo, "file": rel, "ekosistem": "npm", "paket": "", "versi": "", "ada": "", "rilis": "",
                     "pertama": "", "tanda": n})
    flagged = [r for r in rows if r["tanda"]]
    print(f"{len({(r['repo'], r['file']) for r in rows})} file manifest, {len(rows)} baris dependensi, "
          f"{len(uniq)} paket unik dicek ke registry, {len(flagged)} baris bertanda")
    for r in flagged:
        print(f"  {r['repo'][:30]:30s} {r['file'][-38:]:38s} {r['paket'][:28]:28s} {r['versi'][:22]:22s} {r['tanda']}")
    if a.csv:
        with open(a.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
