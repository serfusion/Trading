import json
import time

import pandas as pd

from xau_bot import publish
from xau_bot.publish import NtfyPublisher, load_or_create_topic


def test_topic_created_once(tmp_path):
    f = tmp_path / "topic.txt"
    t1 = load_or_create_topic(str(f))
    t2 = load_or_create_topic(str(f))
    assert t1 == t2 and t1.startswith("xau-") and len(t1) > 20


def test_ntfy_payloads(monkeypatch):
    sent = []
    monkeypatch.setattr(publish.requests, "post", lambda url, data, timeout, headers: sent.append((url, json.loads(data))))
    pub = NtfyPublisher("https://ntfy.example/", "xau-abc")
    pub.start()
    pub.publish({"type": "signal", "time": pd.Timestamp("2026-09-17 10:00", tz="UTC"), "entry": 4300.5},
                "BUY XAUUSD", "judul", 5, ["green_circle"])
    for _ in range(50):
        if len(sent) >= 2:
            break
        time.sleep(0.02)
    pub.stop()
    data_msg, text_msg = sent[0][1], sent[1][1]
    assert sent[0][0] == "https://ntfy.example/"
    assert data_msg["topic"] == "xau-abc-data"
    event = json.loads(data_msg["message"])
    assert event["time"] == "2026-09-17T10:00:00+00:00" and event["entry"] == 4300.5
    assert text_msg["topic"] == "xau-abc" and text_msg["priority"] == 5
