from research.inventaris_file import inventory_file, py_caps, text_caps


def test_py_caps_dari_ast():
    src = (
        "import requests, os\n"
        "import MetaTrader5 as mt5\n"
        "# requests.post('https://contoh.org') di komentar tidak dihitung\n"
        "mt5.initialize(login=1, password=os.getenv('P'), server='x')\n"
        "requests.post('https://api.telegram.org/bot/sendMessage')\n"
        "open('log.csv', 'a').write('x')\n"
        "mt5.order_send({})\n"
    )
    caps, mods, ev = py_caps(src)
    assert {"jaringan", "login_mt5", "order", "kredensial", "tulis_file"} <= caps
    assert "proses" not in caps and "kode_dinamis" not in caps
    assert "MetaTrader5" in mods


def test_mql_order_dan_dll():
    caps, _ = text_caps('#import "user32.dll"\nvoid OnTick(){ trade.Buy(0.1); }\n', ".mq5")
    assert {"proses", "order"} <= caps


def test_inventory_file_biner(tmp_path):
    f = tmp_path / "gambar.jpg"
    f.write_bytes(b"MZ\x90\x00" + b"\x00" * 60)
    assert inventory_file(f, "gambar.jpg")["jenis"] == "program/biner"
