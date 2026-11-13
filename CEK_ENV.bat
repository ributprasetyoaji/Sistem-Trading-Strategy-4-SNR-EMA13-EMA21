@echo off
setlocal
title RBT FX - CEK LINGKUNGAN (diagnosis)
cd /d "%~dp0"
echo ================================================================
echo   RBT FX - CEK LINGKUNGAN  (jalankan ini kalau MULAI_SEMUA gagal)
echo ================================================================
echo(
echo [1] Lokasi folder:
echo     %CD%
echo(
echo [2] Cari Python...
set "PY="
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto pyok
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto pyok
for /d %%p in ("%LOCALAPPDATA%\Programs\Python\Python*") do if exist "%%p\python.exe" set "PY=%%p\python.exe"
if defined PY goto pyok
for /d %%p in ("C:\Python*") do if exist "%%p\python.exe" set "PY=%%p\python.exe"
:pyok
if not defined PY (
    echo     [X] PYTHON TIDAK KETEMU.
    echo     -> Install dari https://www.python.org/downloads/
    echo        CENTANG "Add python.exe to PATH" di layar pertama.
    goto end
)
%PY% --version
echo     [OK] Python ketemu.
echo(
echo [3] Cek paket pip...
for %%M in (MetaTrader5 websockets PySide6) do (
    %PY% -c "import %%M" >nul 2>&1
    if errorlevel 1 (
        echo     [X] %%M belum terpasang - MULAI_SEMUA akan pasang otomatis
        echo         saat run pertama ^(butuh internet^). Atau manual:
        echo         %PY% -m pip install %%M
    ) else (
        echo     [OK] %%M
    )
)
echo(
echo [4] Cek modul strategy ^& engine (import penuh)...
%PY% -c "import sys; sys.path.insert(0,'python'); import cc_strategy3; r=cc_strategy3.evaluate('XAUUSD', {'m15':{},'m5':{},'m1':{},'h1':{}}, None, None); print('     [OK] cc_strategy3.evaluate ->', r.get('status'), '|', r.get('why'))"
if errorlevel 1 echo     [X] cc_strategy3 GAGAL IMPORT - kirim screenshot ini.
%PY% -c "import sys; sys.path.insert(0,'python'); import command_center; print('     [OK] command_center siap (engine)')"
if errorlevel 1 echo     [X] command_center GAGAL IMPORT - kirim screenshot ini.
%PY% -c "import sys; sys.path.insert(0,'python'); import cc_tkdashboard" >nul 2>&1
if errorlevel 1 (echo     [X] cc_tkdashboard gagal import - kirim screenshot ini.) else (echo     [OK] cc_tkdashboard siap ^(dashboard Tk^)())
%PY% -c "import sys; sys.path.insert(0,'python'); import cc_qtdashboard" >nul 2>&1
if errorlevel 1 (echo     [-] cc_qtdashboard belum bisa ^(PySide6 belum terpasang -> pakai Tk dulu^)()) else (echo     [OK] cc_qtdashboard siap ^(dashboard PySide6^)())
echo(
echo [5] File penting:
for %%F in (python\command_center.py python\cc_strategy3.py python\cc_qtdashboard.py python\cc_tkdashboard.py RBT_FX_Bridge.mq4) do (
    if exist "%%F" (echo     [OK] %%F) else (echo     [X] %%F HILANG - unduh ulang ZIP/clone utuh)
)
echo(
echo ================================================================
echo   KALAU SEMUA [OK] -> MULAI_SEMUA.bat pasti bisa jalan.
echo   Kalau ada [X] -> perbaiki sesuai petunjuk di atasnya,
echo   atau screenshot layar ini lalu kirim untuk dibantu.
echo ================================================================
:end
pause
