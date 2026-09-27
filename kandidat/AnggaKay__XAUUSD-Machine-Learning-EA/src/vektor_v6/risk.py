import time
from datetime import datetime

from vektor_v6.bridge import read_tracker, write_tracker
from vektor_v6.config import (
    MAX_CONSECUTIVE_LOSSES,
    PAUSE_MINUTES,
    MAX_POSITIONS,
    MAX_SPREAD,
)

# ── Internal Python-side counters (tidak tergantung tracker EA) ──────
_grief_until       = 0.0
_prev_pos_count    = 0
_session_losses    = 0      # loss counter sejak bot start (session ini)
_cb_until          = 0.0    # circuit breaker sampai timestamp ini


def reset_day():
    """Dipanggil saat bot start. Bersihkan counter internal."""
    global _session_losses, _cb_until
    _session_losses = 0
    _cb_until = 0.0

    # Juga reset file tracker jika hari baru
    today = datetime.now().strftime("%Y-%m-%d")
    tracker = read_tracker()
    if tracker.get("date") != today:
        tracker = {
            "date": today,
            "loss_pips": 0.0,
            "profit_usd": 0.0,
            "consecutive_losses": 0,
            "wins_today": 0,
            "losses_today": 0,
            "circuit_breaker_until": "",
        }
        write_tracker(tracker)
    return tracker


def check_risk(open_positions: int, spread: float) -> str:
    """
    Cek kondisi risiko sebelum buka posisi baru.
    Menggunakan counter Python internal — tidak tergantung nilai loss_pips
    dari tracker EA yang bisa berisi data akumulasi lama.

    Return "ok" jika boleh entry, string alasan jika diblokir.
    """
    global _grief_until, _cb_until

    # 1. Grief period (jeda wajib antar entry)
    if time.time() < _grief_until:
        remaining = int(_grief_until - time.time())
        return f"grief ({remaining}s)"

    # 2. Circuit breaker dari consecutive losses
    if time.time() < _cb_until:
        remaining = int((_cb_until - time.time()) / 60)
        return f"circuit_breaker ({remaining}min)"

    # 3. Max posisi terbuka
    if open_positions >= MAX_POSITIONS:
        return f"max_positions ({open_positions}/{MAX_POSITIONS})"

    # 4. Spread terlalu tinggi
    if spread > MAX_SPREAD:
        return f"spread_too_high ({spread:.1f} > {MAX_SPREAD})"

    return "ok"


def on_loss():
    """Dipanggil setiap kali terjadi trade rugi (dari bridge atau sinyal luar)."""
    global _session_losses, _cb_until
    _session_losses += 1
    if _session_losses >= MAX_CONSECUTIVE_LOSSES:
        _cb_until = time.time() + PAUSE_MINUTES * 60
        _session_losses = 0


def on_win():
    """Dipanggil setiap kali terjadi trade profit."""
    global _session_losses
    _session_losses = 0


def update_on_close(was_profitable: bool, pips: float = 0.0):
    """Dipanggil setiap kali posisi ditutup."""
    if was_profitable:
        on_win()
    else:
        on_loss()


def set_grief(seconds: float = None):
    global _grief_until
    from vektor_v6.config import GRIEF_SECONDS
    _grief_until = time.time() + (seconds if seconds is not None else GRIEF_SECONDS)


def sync_position_count(open_count: int):
    global _prev_pos_count
    _prev_pos_count = open_count
