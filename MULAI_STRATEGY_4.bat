@echo off
setlocal
title RBT FX - STRATEGY 4
rem ================================================================
rem  MULAI STRATEGY 4 - FINAL v7
rem  Cari otomatis di: samping file ini, C:\RBT, Desktop,
rem  OneDrive Desktop, Documents, Downloads (nama folder bebas).
rem  Kalau tidak ketemu: cukup SERET folder strategy ke jendela ini
rem  - lokasi DIINGAT selamanya - berikutnya otomatis lagi.
rem ================================================================
set "DIR="
set "DIRF="
if exist "%~dp0S4_LOKASI.txt" set /p DIR=<"%~dp0S4_LOKASI.txt"
if defined DIR if exist "%DIR%\MULAI_SEMUA.bat" goto mulai
set "DIR="
if exist "%~dp0MULAI_SEMUA.bat" set "DIR=%~dp0"
for /d %%D in ("%~dp0*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%~dp0*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%~dp0*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%~dp0*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("C:\RBT\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("C:\RBT\*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("C:\RBT\*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("C:\RBT\*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Desktop\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Desktop\*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Desktop\*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Desktop\*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\OneDrive\Desktop\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\OneDrive\Desktop\*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\OneDrive\Desktop\*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\OneDrive\Desktop\*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Documents\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Documents\*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Documents\*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Documents\*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
if defined DIR goto mulai
for /d %%D in ("%~dp0*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("C:\RBT\*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("%USERPROFILE%\Desktop\*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("%USERPROFILE%\OneDrive\Desktop\*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("%USERPROFILE%\Documents\*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
if defined DIRF goto engine
echo [X] Folder STRATEGY 4 tidak ketemu otomatis.
echo.
echo ---- INFO UNTUK DIAGNOSIS (kalau mampir foto layar ini) ----
echo Profil Windows: %USERPROFILE%
dir /b "C:\RBT" 2>nul | findstr /I "strategy"
dir /b "%USERPROFILE%\Desktop" 2>nul | findstr /I "strategy"
dir /b "%USERPROFILE%\Downloads" 2>nul | findstr /I "strategy"
dir /b "%~dp0." | findstr /I "strategy"
echo ---- AKHIR INFO ----
echo.
echo ====== CARA PASTI (10 detik) ======
echo 1. Buka File Explorer (ikon folder kuning di taskbar)
echo 2. Cari folder Sistem-Trading-Strategy-4
echo 3. SERET folder itu pakai mouse ke JENDELA HITAM INI
echo 4. Lepaskan di dalam jendela ini, lalu tekan Enter
echo.
set /p "LOK=Seret folder ke sini lalu tekan Enter: "
set "LOK=%LOK:"=%"
if not defined LOK goto gagal_input
for /d %%D in ("%LOK%\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
if exist "%LOK%\Sistem-Trading-Strategy-4\MULAI_SEMUA.bat" set "DIR=%LOK%\Sistem-Trading-Strategy-4"
if exist "%LOK%\MULAI_SEMUA.bat" set "DIR=%LOK%"
if not defined DIR goto input_salah
>"%~dp0S4_LOKASI.txt" echo %LOK%
echo [OK] Lokasi disimpan: %DIR%
goto mulai

:input_salah
echo [X] Di folder yang diseret tidak ada MULAI_SEMUA.bat.
echo Kemungkinan yang diseret folder induk atau folder salah.
echo Seret folder yang DI DALAMNYA terlihat MULAI_SEMUA.bat.
echo.
pause
exit /b 1

:gagal_input
echo Tidak ada input. Klik 2x file ini lagi untuk mencoba.
echo.
pause
exit /b 1

:mulai
cd /d "%DIR%"
echo Menyalakan STRATEGY 4 di %DIR% ...
call "MULAI_SEMUA.bat"
goto selesai

:engine
cd /d "%DIRF%"
echo MULAI_SEMUA.bat belum ada di folder itu - engine dinyalakan langsung.
:startdirect
set "PY="
python --version >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto pyok
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto pyok
echo [X] Python tidak ketemu di VPS ini.
echo Buka folder %CD% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
echo.
pause
exit /b 1

:pyok
set "DASH=python\cc_tkdashboard.py"
%PY% -c "import PySide6" >nul 2>nul
if errorlevel 1 goto dashgo
set "DASH=python\cc_qtdashboard.py"
:dashgo
set "PYW=%PY%"
for %%P in (%PY%) do if exist "%%~dpPpythonw.exe" set "PYW=%%~dpPpythonw.exe"
start "RBT FX DASHBOARD" %PYW% "%DASH%" --port 8082
echo Dashboard dinyalakan. Engine berjalan DI JENDELA INI - log hidup di bawah.
echo JANGAN tutup jendela ini selama trading.
echo.
%PY% -u python\command_center.py
goto selesai

:selesai
echo.
echo STRATEGY 4 berhenti. Klik 2x file ini lagi untuk menyalakan.
echo.
pause
exit /b 0
