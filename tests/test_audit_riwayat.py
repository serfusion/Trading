import subprocess

import pytest

from research.audit_riwayat import audit_repo, mask


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q", "-b", "main")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    (work / "bot.py").write_text("import MetaTrader5 as mt5\n")
    (work / ".env").write_text("MT5_PASSWORD=Rahasia123\nMT5_LOGIN=1\n")
    (work / "tool.exe").write_bytes(b"MZ\x90\x00" + b"\x00" * 64)
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "awal")
    (work / "bot.py").write_text("import MetaTrader5 as mt5\nimport pynput.keyboard\n")
    _git(work, "commit", "-q", "-am", "tambah")
    for f in (".env", "tool.exe"):
        (work / f).unlink()
    (work / "bot.py").write_text("import MetaTrader5 as mt5\n")
    _git(work, "commit", "-q", "-am", "hapus jejak")
    bare = tmp_path / "x__y.git"
    subprocess.run(["git", "clone", "-q", "--mirror", str(work), str(bare)], check=True)
    return bare


def test_temuan_hanya_di_riwayat(repo):
    info = audit_repo(repo)
    codes = {(f["code"], f["di_head"]) for f in info["findings"]}
    assert ("keylogger", False) in codes          # versi lama bot.py yang sudah dihapus dari HEAD
    assert ("env_file", False) in codes
    secret = [f for f in info["findings"] if f["code"] == "env_secret"]
    assert secret and "Rahasia123" not in secret[0]["text"]   # nilai rahasia disensor
    assert secret[0]["commit"].split()[2] == "t:"            # commit pertama yang memasukkannya
    assert [b["level"] for b in info["binaries"]] == ["BAHAYA"]
    assert info["commits"] == 3


def test_mask():
    assert "abcdefgh" not in mask('password = "abcdefgh123"')
    assert mask('TOKEN="1234567890:AAabcdefghijklmnopqrstuvwxyz0123456789"').count("disensor") == 1
