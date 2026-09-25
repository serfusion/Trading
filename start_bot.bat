@echo off
REM Jalankan bot dan restart otomatis bila tertutup karena error.
cd /d %~dp0
:loop
python -m xau_bot run
echo Bot berhenti, restart dalam 15 detik... (tekan Ctrl+C untuk keluar)
timeout /t 15
goto loop
