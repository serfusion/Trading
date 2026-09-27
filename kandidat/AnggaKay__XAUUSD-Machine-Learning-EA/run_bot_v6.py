import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from vektor_v6.main import main

LOCK_FILE = Path(__file__).resolve().parent / "bot_v6.lock"


def acquire_lock():
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            try:
                os.kill(old_pid, 0)
                print(f"[lock] Another instance running (PID {old_pid}). Exiting.", flush=True)
                sys.exit(1)
            except OSError:
                LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            LOCK_FILE.unlink(missing_ok=True)
    LOCK_FILE.write_text(str(os.getpid()))
    print(f"[lock] PID {os.getpid()} acquired.", flush=True)


def release_lock():
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if pid == os.getpid():
                LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    acquire_lock()
    try:
        while True:
            try:
                main()
            except Exception as e:
                print(f"[restart] Bot crashed: {e}", flush=True)
            time.sleep(5)
    finally:
        release_lock()
