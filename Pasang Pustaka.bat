@echo off
rem Sekali saja setelah mengekstrak zip versi Python: pasang pustaka tambahan.
rem Butuh Python 3.11+ dari python.org atau Microsoft Store.
python --version >/dev/null 2>&1 || goto tanpa_python
python -m pip install --user -r "%~dp0requirements.txt" || goto gagal
echo.
echo Selesai. Buka aplikasi dengan "Buka Arsip Penugasan.bat".
pause
exit /b 0
:tanpa_python
echo Python belum terpasang. Pasang dari https://www.python.org/downloads/ lalu jalankan ini lagi.
pause
exit /b 1
:gagal
echo.
echo Pemasangan gagal - lihat pesan di atas.
pause
exit /b 1
