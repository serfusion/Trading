@echo off
REM Jalankan sniper bot Telegram di Windows (docs/SNIPER_TELEGRAM.md). Jendela ini harus tetap terbuka.
cd /d %~dp0
:ulang
python -m sniper_bot jalan
echo Bot berhenti, mulai ulang 30 detik lagi... (Ctrl+C untuk keluar)
timeout /t 30
goto ulang
