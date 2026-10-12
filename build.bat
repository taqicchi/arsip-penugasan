@echo off
rem Membuat dist\ArsipPenugasan.exe (satu berkas, tanpa perlu Python di komputer tujuan).
cd /d "%~dp0"
python -m pip install --user -r requirements.txt pyinstaller || goto gagal
python -m unittest test_core test_lain || goto gagal
python -m PyInstaller --noconfirm --clean --onefile --windowed --name ArsipPenugasan --icon "%~dp0ikon.ico" --add-data "%~dp0ikon.ico;." --collect-all tkinterdnd2 --workpath "%TEMP%\arsip-penugasan-build" --specpath "%TEMP%\arsip-penugasan-build" arsip_penugasan.pyw || goto gagal
echo.
echo Selesai: dist\ArsipPenugasan.exe
pause
exit /b 0
:gagal
echo.
echo Build gagal - lihat pesan di atas.
pause
exit /b 1
