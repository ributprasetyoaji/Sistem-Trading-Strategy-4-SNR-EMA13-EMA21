@echo off
setlocal enableextensions
title RBT FX - PASANG 4 FILE BAT MULAI STRATEGY
cd /d "%~dp0"

rem =================================================================
rem  PEMASANG 4 FILE BAT - MULAI STRATEGY 1/2/3/4
rem  File bat DIBUAT LANGSUNG oleh program ini di folder ini:
rem  tanpa internet, tanpa token, tanpa zip - jadi PASTI UTUH
rem  dan tidak bisa diblokir/rusak saat unduh.
rem  Caranya: taruh file ini di C:\RBT lalu klik 2x.
rem =================================================================

echo ================================================================
echo    RBT FX - PASANG 4 FILE BAT MULAI STRATEGY
echo    Membuat MULAI_STRATEGY_1.bat s/d 4.bat di folder ini...
echo    Folder: %~dp0
echo ================================================================
echo.



rem ====== MULAI_STRATEGY_1.bat ======
if exist "MULAI_STRATEGY_1.bat" del "MULAI_STRATEGY_1.bat" >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo @echo off
>>"MULAI_STRATEGY_1.bat" echo setlocal
>>"MULAI_STRATEGY_1.bat" echo title RBT FX - STRATEGY 1
>>"MULAI_STRATEGY_1.bat" echo rem ================================================================
>>"MULAI_STRATEGY_1.bat" echo rem  MULAI STRATEGY 1 - FINAL v7
>>"MULAI_STRATEGY_1.bat" echo rem  Cari otomatis di: samping file ini, C:\RBT, Desktop,
>>"MULAI_STRATEGY_1.bat" echo rem  OneDrive Desktop, Documents, Downloads (nama folder bebas).
>>"MULAI_STRATEGY_1.bat" echo rem  Kalau tidak ketemu: cukup SERET folder strategy ke jendela ini
>>"MULAI_STRATEGY_1.bat" echo rem  - lokasi DIINGAT selamanya - berikutnya otomatis lagi.
>>"MULAI_STRATEGY_1.bat" echo rem ================================================================
>>"MULAI_STRATEGY_1.bat" echo set "DIR="
>>"MULAI_STRATEGY_1.bat" echo set "DIRF="
>>"MULAI_STRATEGY_1.bat" echo if exist "%%~dp0S1_LOKASI.txt" set /p DIR=<"%%~dp0S1_LOKASI.txt"
>>"MULAI_STRATEGY_1.bat" echo if defined DIR if exist "%%DIR%%\MULAI_SEMUA.bat" goto mulai
>>"MULAI_STRATEGY_1.bat" echo set "DIR="
>>"MULAI_STRATEGY_1.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%~dp0*Strategy-1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%~dp0*Strategy_1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%~dp0*Strategy 1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%~dp0*Strategy1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("C:\RBT\*Strategy_1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("C:\RBT\*Strategy 1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("C:\RBT\*Strategy1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy_1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy 1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy-1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy_1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy 1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy-1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy_1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy 1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy_1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy 1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo if defined DIR goto mulai
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%~dp0*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo if defined DIRF goto engine
>>"MULAI_STRATEGY_1.bat" echo echo [X] Folder STRATEGY 1 tidak ketemu otomatis.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo echo ---- INFO UNTUK DIAGNOSIS (kalau mampir foto layar ini) ----
>>"MULAI_STRATEGY_1.bat" echo echo Profil Windows: %%USERPROFILE%%
>>"MULAI_STRATEGY_1.bat" echo dir /b "C:\RBT" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_1.bat" echo dir /b "%%USERPROFILE%%\Desktop" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_1.bat" echo dir /b "%%USERPROFILE%%\Downloads" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_1.bat" echo dir /b "%%~dp0" | findstr /I "strategy"
>>"MULAI_STRATEGY_1.bat" echo echo ---- AKHIR INFO ----
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo echo ====== CARA PASTI (10 detik) ======
>>"MULAI_STRATEGY_1.bat" echo echo 1. Buka File Explorer (ikon folder kuning di taskbar)
>>"MULAI_STRATEGY_1.bat" echo echo 2. Cari folder Sistem-Trading-Strategy-1
>>"MULAI_STRATEGY_1.bat" echo echo 3. SERET folder itu pakai mouse ke JENDELA HITAM INI
>>"MULAI_STRATEGY_1.bat" echo echo 4. Lepaskan di dalam jendela ini, lalu tekan Enter
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo set /p "LOK=Seret folder ke sini lalu tekan Enter: "
>>"MULAI_STRATEGY_1.bat" echo set "LOK=%%LOK:"=%%"
>>"MULAI_STRATEGY_1.bat" echo if not defined LOK goto gagal_input
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%LOK%%\*Strategy-1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo if exist "%%LOK%%\Sistem-Trading-Strategy-1\MULAI_SEMUA.bat" set "DIR=%%LOK%%\Sistem-Trading-Strategy-1"
>>"MULAI_STRATEGY_1.bat" echo if exist "%%LOK%%\MULAI_SEMUA.bat" set "DIR=%%LOK%%"
>>"MULAI_STRATEGY_1.bat" echo if not defined DIR goto input_salah
>>"MULAI_STRATEGY_1.bat" echo >"%%~dp0S1_LOKASI.txt" echo %%LOK%%
>>"MULAI_STRATEGY_1.bat" echo echo [OK] Lokasi disimpan: %%DIR%%
>>"MULAI_STRATEGY_1.bat" echo goto mulai
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :input_salah
>>"MULAI_STRATEGY_1.bat" echo echo [X] Di folder yang diseret tidak ada MULAI_SEMUA.bat.
>>"MULAI_STRATEGY_1.bat" echo echo Kemungkinan yang diseret folder induk atau folder salah.
>>"MULAI_STRATEGY_1.bat" echo echo Seret folder yang DI DALAMNYA terlihat MULAI_SEMUA.bat.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 1
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :gagal_input
>>"MULAI_STRATEGY_1.bat" echo echo Tidak ada input. Klik 2x file ini lagi untuk mencoba.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 1
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :mulai
>>"MULAI_STRATEGY_1.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_1.bat" echo findstr /C:"TOKEN.txt" "MULAI_SEMUA.bat" >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if errorlevel 1 goto oldbat
>>"MULAI_STRATEGY_1.bat" echo echo Menyalakan STRATEGY 1 di %%DIR%% ...
>>"MULAI_STRATEGY_1.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_1.bat" echo goto selesai
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :oldbat
>>"MULAI_STRATEGY_1.bat" echo echo MULAI_SEMUA.bat versi LAMA terdeteksi - jalur update lamanya selalu GAGAL.
>>"MULAI_STRATEGY_1.bat" echo echo Engine plus dashboard dinyalakan LANGSUNG melewatinya.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo goto startdirect
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :engine
>>"MULAI_STRATEGY_1.bat" echo cd /d "%%DIRF%%"
>>"MULAI_STRATEGY_1.bat" echo echo MULAI_SEMUA.bat belum ada di folder itu - engine dinyalakan langsung.
>>"MULAI_STRATEGY_1.bat" echo :startdirect
>>"MULAI_STRATEGY_1.bat" echo set "PY="
>>"MULAI_STRATEGY_1.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_1.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_1.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_1.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_1.bat" echo echo [X] Python tidak ketemu di VPS ini.
>>"MULAI_STRATEGY_1.bat" echo echo Buka folder %%CD%% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 1
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :pyok
>>"MULAI_STRATEGY_1.bat" echo set "DASH=python\cc_tkdashboard.py"
>>"MULAI_STRATEGY_1.bat" echo %%PY%% -c "import PySide6" >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if errorlevel 1 goto dashgo
>>"MULAI_STRATEGY_1.bat" echo set "DASH=python\cc_qtdashboard.py"
>>"MULAI_STRATEGY_1.bat" echo :dashgo
>>"MULAI_STRATEGY_1.bat" echo set "PYW=%%PY%%"
>>"MULAI_STRATEGY_1.bat" echo for %%%%P in (%%PY%%) do if exist "%%%%~dpPpythonw.exe" set "PYW=%%%%~dpPpythonw.exe"
>>"MULAI_STRATEGY_1.bat" echo start "RBT FX DASHBOARD" %%PYW%% "%%DASH%%" --port 8080
>>"MULAI_STRATEGY_1.bat" echo echo Dashboard dinyalakan. Engine berjalan DI JENDELA INI - log hidup di bawah.
>>"MULAI_STRATEGY_1.bat" echo echo JANGAN tutup jendela ini selama trading.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo %%PY%% -u python\command_center.py
>>"MULAI_STRATEGY_1.bat" echo goto selesai
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :selesai
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo echo STRATEGY 1 berhenti. Klik 2x file ini lagi untuk menyalakan.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 0
>>"MULAI_STRATEGY_1.bat" echo.
if exist "MULAI_STRATEGY_1.bat" echo [OK] MULAI_STRATEGY_1.bat dibuat

rem ====== MULAI_STRATEGY_2.bat ======
if exist "MULAI_STRATEGY_2.bat" del "MULAI_STRATEGY_2.bat" >nul 2>nul
>>"MULAI_STRATEGY_2.bat" echo @echo off
>>"MULAI_STRATEGY_2.bat" echo setlocal
>>"MULAI_STRATEGY_2.bat" echo title RBT FX - STRATEGY 2
>>"MULAI_STRATEGY_2.bat" echo rem ================================================================
>>"MULAI_STRATEGY_2.bat" echo rem  MULAI STRATEGY 2 - FINAL v7
>>"MULAI_STRATEGY_2.bat" echo rem  Cari otomatis di: samping file ini, C:\RBT, Desktop,
>>"MULAI_STRATEGY_2.bat" echo rem  OneDrive Desktop, Documents, Downloads (nama folder bebas).
>>"MULAI_STRATEGY_2.bat" echo rem  Kalau tidak ketemu: cukup SERET folder strategy ke jendela ini
>>"MULAI_STRATEGY_2.bat" echo rem  - lokasi DIINGAT selamanya - berikutnya otomatis lagi.
>>"MULAI_STRATEGY_2.bat" echo rem ================================================================
>>"MULAI_STRATEGY_2.bat" echo set "DIR="
>>"MULAI_STRATEGY_2.bat" echo set "DIRF="
>>"MULAI_STRATEGY_2.bat" echo if exist "%%~dp0S2_LOKASI.txt" set /p DIR=<"%%~dp0S2_LOKASI.txt"
>>"MULAI_STRATEGY_2.bat" echo if defined DIR if exist "%%DIR%%\MULAI_SEMUA.bat" goto mulai
>>"MULAI_STRATEGY_2.bat" echo set "DIR="
>>"MULAI_STRATEGY_2.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%~dp0*Strategy-2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%~dp0*Strategy_2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%~dp0*Strategy 2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%~dp0*Strategy2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("C:\RBT\*Strategy_2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("C:\RBT\*Strategy 2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("C:\RBT\*Strategy2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy_2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy 2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy-2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy_2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy 2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy-2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy_2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy 2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy_2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy 2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo if defined DIR goto mulai
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%~dp0*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo if defined DIRF goto engine
>>"MULAI_STRATEGY_2.bat" echo echo [X] Folder STRATEGY 2 tidak ketemu otomatis.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo echo ---- INFO UNTUK DIAGNOSIS (kalau mampir foto layar ini) ----
>>"MULAI_STRATEGY_2.bat" echo echo Profil Windows: %%USERPROFILE%%
>>"MULAI_STRATEGY_2.bat" echo dir /b "C:\RBT" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_2.bat" echo dir /b "%%USERPROFILE%%\Desktop" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_2.bat" echo dir /b "%%USERPROFILE%%\Downloads" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_2.bat" echo dir /b "%%~dp0" | findstr /I "strategy"
>>"MULAI_STRATEGY_2.bat" echo echo ---- AKHIR INFO ----
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo echo ====== CARA PASTI (10 detik) ======
>>"MULAI_STRATEGY_2.bat" echo echo 1. Buka File Explorer (ikon folder kuning di taskbar)
>>"MULAI_STRATEGY_2.bat" echo echo 2. Cari folder Sistem-Trading-Strategy-2
>>"MULAI_STRATEGY_2.bat" echo echo 3. SERET folder itu pakai mouse ke JENDELA HITAM INI
>>"MULAI_STRATEGY_2.bat" echo echo 4. Lepaskan di dalam jendela ini, lalu tekan Enter
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo set /p "LOK=Seret folder ke sini lalu tekan Enter: "
>>"MULAI_STRATEGY_2.bat" echo set "LOK=%%LOK:"=%%"
>>"MULAI_STRATEGY_2.bat" echo if not defined LOK goto gagal_input
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%LOK%%\*Strategy-2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo if exist "%%LOK%%\Sistem-Trading-Strategy-2\MULAI_SEMUA.bat" set "DIR=%%LOK%%\Sistem-Trading-Strategy-2"
>>"MULAI_STRATEGY_2.bat" echo if exist "%%LOK%%\MULAI_SEMUA.bat" set "DIR=%%LOK%%"
>>"MULAI_STRATEGY_2.bat" echo if not defined DIR goto input_salah
>>"MULAI_STRATEGY_2.bat" echo >"%%~dp0S2_LOKASI.txt" echo %%LOK%%
>>"MULAI_STRATEGY_2.bat" echo echo [OK] Lokasi disimpan: %%DIR%%
>>"MULAI_STRATEGY_2.bat" echo goto mulai
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :input_salah
>>"MULAI_STRATEGY_2.bat" echo echo [X] Di folder yang diseret tidak ada MULAI_SEMUA.bat.
>>"MULAI_STRATEGY_2.bat" echo echo Kemungkinan yang diseret folder induk atau folder salah.
>>"MULAI_STRATEGY_2.bat" echo echo Seret folder yang DI DALAMNYA terlihat MULAI_SEMUA.bat.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 1
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :gagal_input
>>"MULAI_STRATEGY_2.bat" echo echo Tidak ada input. Klik 2x file ini lagi untuk mencoba.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 1
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :mulai
>>"MULAI_STRATEGY_2.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_2.bat" echo echo Menyalakan STRATEGY 2 di %%DIR%% ...
>>"MULAI_STRATEGY_2.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_2.bat" echo goto selesai
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :engine
>>"MULAI_STRATEGY_2.bat" echo cd /d "%%DIRF%%"
>>"MULAI_STRATEGY_2.bat" echo echo MULAI_SEMUA.bat belum ada di folder itu - engine dinyalakan langsung.
>>"MULAI_STRATEGY_2.bat" echo :startdirect
>>"MULAI_STRATEGY_2.bat" echo set "PY="
>>"MULAI_STRATEGY_2.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_2.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_2.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_2.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_2.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_2.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_2.bat" echo echo [X] Python tidak ketemu di VPS ini.
>>"MULAI_STRATEGY_2.bat" echo echo Buka folder %%CD%% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 1
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :pyok
>>"MULAI_STRATEGY_2.bat" echo set "DASH=python\cc_tkdashboard.py"
>>"MULAI_STRATEGY_2.bat" echo %%PY%% -c "import PySide6" >nul 2>nul
>>"MULAI_STRATEGY_2.bat" echo if errorlevel 1 goto dashgo
>>"MULAI_STRATEGY_2.bat" echo set "DASH=python\cc_qtdashboard.py"
>>"MULAI_STRATEGY_2.bat" echo :dashgo
>>"MULAI_STRATEGY_2.bat" echo set "PYW=%%PY%%"
>>"MULAI_STRATEGY_2.bat" echo for %%%%P in (%%PY%%) do if exist "%%%%~dpPpythonw.exe" set "PYW=%%%%~dpPpythonw.exe"
>>"MULAI_STRATEGY_2.bat" echo start "RBT FX DASHBOARD" %%PYW%% "%%DASH%%" --port 8082
>>"MULAI_STRATEGY_2.bat" echo echo Dashboard dinyalakan. Engine berjalan DI JENDELA INI - log hidup di bawah.
>>"MULAI_STRATEGY_2.bat" echo echo JANGAN tutup jendela ini selama trading.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo %%PY%% -u python\command_center.py
>>"MULAI_STRATEGY_2.bat" echo goto selesai
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :selesai
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo echo STRATEGY 2 berhenti. Klik 2x file ini lagi untuk menyalakan.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 0
>>"MULAI_STRATEGY_2.bat" echo.
if exist "MULAI_STRATEGY_2.bat" echo [OK] MULAI_STRATEGY_2.bat dibuat

rem ====== MULAI_STRATEGY_3.bat ======
if exist "MULAI_STRATEGY_3.bat" del "MULAI_STRATEGY_3.bat" >nul 2>nul
>>"MULAI_STRATEGY_3.bat" echo @echo off
>>"MULAI_STRATEGY_3.bat" echo setlocal
>>"MULAI_STRATEGY_3.bat" echo title RBT FX - STRATEGY 3
>>"MULAI_STRATEGY_3.bat" echo rem ================================================================
>>"MULAI_STRATEGY_3.bat" echo rem  MULAI STRATEGY 3 - FINAL v7
>>"MULAI_STRATEGY_3.bat" echo rem  Cari otomatis di: samping file ini, C:\RBT, Desktop,
>>"MULAI_STRATEGY_3.bat" echo rem  OneDrive Desktop, Documents, Downloads (nama folder bebas).
>>"MULAI_STRATEGY_3.bat" echo rem  Kalau tidak ketemu: cukup SERET folder strategy ke jendela ini
>>"MULAI_STRATEGY_3.bat" echo rem  - lokasi DIINGAT selamanya - berikutnya otomatis lagi.
>>"MULAI_STRATEGY_3.bat" echo rem ================================================================
>>"MULAI_STRATEGY_3.bat" echo set "DIR="
>>"MULAI_STRATEGY_3.bat" echo set "DIRF="
>>"MULAI_STRATEGY_3.bat" echo if exist "%%~dp0S3_LOKASI.txt" set /p DIR=<"%%~dp0S3_LOKASI.txt"
>>"MULAI_STRATEGY_3.bat" echo if defined DIR if exist "%%DIR%%\MULAI_SEMUA.bat" goto mulai
>>"MULAI_STRATEGY_3.bat" echo set "DIR="
>>"MULAI_STRATEGY_3.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%~dp0*Strategy-3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%~dp0*Strategy_3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%~dp0*Strategy 3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%~dp0*Strategy3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("C:\RBT\*Strategy_3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("C:\RBT\*Strategy 3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("C:\RBT\*Strategy3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy_3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy 3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy-3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy_3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy 3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy-3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy_3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy 3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy_3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy 3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo if defined DIR goto mulai
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%~dp0*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo if defined DIRF goto engine
>>"MULAI_STRATEGY_3.bat" echo echo [X] Folder STRATEGY 3 tidak ketemu otomatis.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo echo ---- INFO UNTUK DIAGNOSIS (kalau mampir foto layar ini) ----
>>"MULAI_STRATEGY_3.bat" echo echo Profil Windows: %%USERPROFILE%%
>>"MULAI_STRATEGY_3.bat" echo dir /b "C:\RBT" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_3.bat" echo dir /b "%%USERPROFILE%%\Desktop" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_3.bat" echo dir /b "%%USERPROFILE%%\Downloads" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_3.bat" echo dir /b "%%~dp0" | findstr /I "strategy"
>>"MULAI_STRATEGY_3.bat" echo echo ---- AKHIR INFO ----
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo echo ====== CARA PASTI (10 detik) ======
>>"MULAI_STRATEGY_3.bat" echo echo 1. Buka File Explorer (ikon folder kuning di taskbar)
>>"MULAI_STRATEGY_3.bat" echo echo 2. Cari folder Sistem-Trading-Strategy-3
>>"MULAI_STRATEGY_3.bat" echo echo 3. SERET folder itu pakai mouse ke JENDELA HITAM INI
>>"MULAI_STRATEGY_3.bat" echo echo 4. Lepaskan di dalam jendela ini, lalu tekan Enter
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo set /p "LOK=Seret folder ke sini lalu tekan Enter: "
>>"MULAI_STRATEGY_3.bat" echo set "LOK=%%LOK:"=%%"
>>"MULAI_STRATEGY_3.bat" echo if not defined LOK goto gagal_input
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%LOK%%\*Strategy-3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo if exist "%%LOK%%\Sistem-Trading-Strategy-3\MULAI_SEMUA.bat" set "DIR=%%LOK%%\Sistem-Trading-Strategy-3"
>>"MULAI_STRATEGY_3.bat" echo if exist "%%LOK%%\MULAI_SEMUA.bat" set "DIR=%%LOK%%"
>>"MULAI_STRATEGY_3.bat" echo if not defined DIR goto input_salah
>>"MULAI_STRATEGY_3.bat" echo >"%%~dp0S3_LOKASI.txt" echo %%LOK%%
>>"MULAI_STRATEGY_3.bat" echo echo [OK] Lokasi disimpan: %%DIR%%
>>"MULAI_STRATEGY_3.bat" echo goto mulai
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :input_salah
>>"MULAI_STRATEGY_3.bat" echo echo [X] Di folder yang diseret tidak ada MULAI_SEMUA.bat.
>>"MULAI_STRATEGY_3.bat" echo echo Kemungkinan yang diseret folder induk atau folder salah.
>>"MULAI_STRATEGY_3.bat" echo echo Seret folder yang DI DALAMNYA terlihat MULAI_SEMUA.bat.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 1
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :gagal_input
>>"MULAI_STRATEGY_3.bat" echo echo Tidak ada input. Klik 2x file ini lagi untuk mencoba.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 1
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :mulai
>>"MULAI_STRATEGY_3.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_3.bat" echo echo Menyalakan STRATEGY 3 di %%DIR%% ...
>>"MULAI_STRATEGY_3.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_3.bat" echo goto selesai
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :engine
>>"MULAI_STRATEGY_3.bat" echo cd /d "%%DIRF%%"
>>"MULAI_STRATEGY_3.bat" echo echo MULAI_SEMUA.bat belum ada di folder itu - engine dinyalakan langsung.
>>"MULAI_STRATEGY_3.bat" echo :startdirect
>>"MULAI_STRATEGY_3.bat" echo set "PY="
>>"MULAI_STRATEGY_3.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_3.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_3.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_3.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_3.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_3.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_3.bat" echo echo [X] Python tidak ketemu di VPS ini.
>>"MULAI_STRATEGY_3.bat" echo echo Buka folder %%CD%% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 1
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :pyok
>>"MULAI_STRATEGY_3.bat" echo set "DASH=python\cc_tkdashboard.py"
>>"MULAI_STRATEGY_3.bat" echo %%PY%% -c "import PySide6" >nul 2>nul
>>"MULAI_STRATEGY_3.bat" echo if errorlevel 1 goto dashgo
>>"MULAI_STRATEGY_3.bat" echo set "DASH=python\cc_qtdashboard.py"
>>"MULAI_STRATEGY_3.bat" echo :dashgo
>>"MULAI_STRATEGY_3.bat" echo set "PYW=%%PY%%"
>>"MULAI_STRATEGY_3.bat" echo for %%%%P in (%%PY%%) do if exist "%%%%~dpPpythonw.exe" set "PYW=%%%%~dpPpythonw.exe"
>>"MULAI_STRATEGY_3.bat" echo start "RBT FX DASHBOARD" %%PYW%% "%%DASH%%" --port 8082
>>"MULAI_STRATEGY_3.bat" echo echo Dashboard dinyalakan. Engine berjalan DI JENDELA INI - log hidup di bawah.
>>"MULAI_STRATEGY_3.bat" echo echo JANGAN tutup jendela ini selama trading.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo %%PY%% -u python\command_center.py
>>"MULAI_STRATEGY_3.bat" echo goto selesai
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :selesai
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo echo STRATEGY 3 berhenti. Klik 2x file ini lagi untuk menyalakan.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 0
>>"MULAI_STRATEGY_3.bat" echo.
if exist "MULAI_STRATEGY_3.bat" echo [OK] MULAI_STRATEGY_3.bat dibuat

rem ====== MULAI_STRATEGY_4.bat ======
if exist "MULAI_STRATEGY_4.bat" del "MULAI_STRATEGY_4.bat" >nul 2>nul
>>"MULAI_STRATEGY_4.bat" echo @echo off
>>"MULAI_STRATEGY_4.bat" echo setlocal
>>"MULAI_STRATEGY_4.bat" echo title RBT FX - STRATEGY 4
>>"MULAI_STRATEGY_4.bat" echo rem ================================================================
>>"MULAI_STRATEGY_4.bat" echo rem  MULAI STRATEGY 4 - FINAL v7
>>"MULAI_STRATEGY_4.bat" echo rem  Cari otomatis di: samping file ini, C:\RBT, Desktop,
>>"MULAI_STRATEGY_4.bat" echo rem  OneDrive Desktop, Documents, Downloads (nama folder bebas).
>>"MULAI_STRATEGY_4.bat" echo rem  Kalau tidak ketemu: cukup SERET folder strategy ke jendela ini
>>"MULAI_STRATEGY_4.bat" echo rem  - lokasi DIINGAT selamanya - berikutnya otomatis lagi.
>>"MULAI_STRATEGY_4.bat" echo rem ================================================================
>>"MULAI_STRATEGY_4.bat" echo set "DIR="
>>"MULAI_STRATEGY_4.bat" echo set "DIRF="
>>"MULAI_STRATEGY_4.bat" echo if exist "%%~dp0S4_LOKASI.txt" set /p DIR=<"%%~dp0S4_LOKASI.txt"
>>"MULAI_STRATEGY_4.bat" echo if defined DIR if exist "%%DIR%%\MULAI_SEMUA.bat" goto mulai
>>"MULAI_STRATEGY_4.bat" echo set "DIR="
>>"MULAI_STRATEGY_4.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%~dp0*Strategy-4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%~dp0*Strategy_4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%~dp0*Strategy 4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%~dp0*Strategy4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("C:\RBT\*Strategy_4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("C:\RBT\*Strategy 4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("C:\RBT\*Strategy4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy_4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy 4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy-4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy_4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy 4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy-4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy_4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy 4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy_4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy 4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo if defined DIR goto mulai
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%~dp0*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\OneDrive\Desktop\*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Documents\*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo if defined DIRF goto engine
>>"MULAI_STRATEGY_4.bat" echo echo [X] Folder STRATEGY 4 tidak ketemu otomatis.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo echo ---- INFO UNTUK DIAGNOSIS (kalau mampir foto layar ini) ----
>>"MULAI_STRATEGY_4.bat" echo echo Profil Windows: %%USERPROFILE%%
>>"MULAI_STRATEGY_4.bat" echo dir /b "C:\RBT" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_4.bat" echo dir /b "%%USERPROFILE%%\Desktop" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_4.bat" echo dir /b "%%USERPROFILE%%\Downloads" 2>nul | findstr /I "strategy"
>>"MULAI_STRATEGY_4.bat" echo dir /b "%%~dp0" | findstr /I "strategy"
>>"MULAI_STRATEGY_4.bat" echo echo ---- AKHIR INFO ----
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo echo ====== CARA PASTI (10 detik) ======
>>"MULAI_STRATEGY_4.bat" echo echo 1. Buka File Explorer (ikon folder kuning di taskbar)
>>"MULAI_STRATEGY_4.bat" echo echo 2. Cari folder Sistem-Trading-Strategy-4
>>"MULAI_STRATEGY_4.bat" echo echo 3. SERET folder itu pakai mouse ke JENDELA HITAM INI
>>"MULAI_STRATEGY_4.bat" echo echo 4. Lepaskan di dalam jendela ini, lalu tekan Enter
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo set /p "LOK=Seret folder ke sini lalu tekan Enter: "
>>"MULAI_STRATEGY_4.bat" echo set "LOK=%%LOK:"=%%"
>>"MULAI_STRATEGY_4.bat" echo if not defined LOK goto gagal_input
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%LOK%%\*Strategy-4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo if exist "%%LOK%%\Sistem-Trading-Strategy-4\MULAI_SEMUA.bat" set "DIR=%%LOK%%\Sistem-Trading-Strategy-4"
>>"MULAI_STRATEGY_4.bat" echo if exist "%%LOK%%\MULAI_SEMUA.bat" set "DIR=%%LOK%%"
>>"MULAI_STRATEGY_4.bat" echo if not defined DIR goto input_salah
>>"MULAI_STRATEGY_4.bat" echo >"%%~dp0S4_LOKASI.txt" echo %%LOK%%
>>"MULAI_STRATEGY_4.bat" echo echo [OK] Lokasi disimpan: %%DIR%%
>>"MULAI_STRATEGY_4.bat" echo goto mulai
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :input_salah
>>"MULAI_STRATEGY_4.bat" echo echo [X] Di folder yang diseret tidak ada MULAI_SEMUA.bat.
>>"MULAI_STRATEGY_4.bat" echo echo Kemungkinan yang diseret folder induk atau folder salah.
>>"MULAI_STRATEGY_4.bat" echo echo Seret folder yang DI DALAMNYA terlihat MULAI_SEMUA.bat.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 1
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :gagal_input
>>"MULAI_STRATEGY_4.bat" echo echo Tidak ada input. Klik 2x file ini lagi untuk mencoba.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 1
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :mulai
>>"MULAI_STRATEGY_4.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_4.bat" echo echo Menyalakan STRATEGY 4 di %%DIR%% ...
>>"MULAI_STRATEGY_4.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_4.bat" echo goto selesai
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :engine
>>"MULAI_STRATEGY_4.bat" echo cd /d "%%DIRF%%"
>>"MULAI_STRATEGY_4.bat" echo echo MULAI_SEMUA.bat belum ada di folder itu - engine dinyalakan langsung.
>>"MULAI_STRATEGY_4.bat" echo :startdirect
>>"MULAI_STRATEGY_4.bat" echo set "PY="
>>"MULAI_STRATEGY_4.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_4.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_4.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_4.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_4.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_4.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_4.bat" echo echo [X] Python tidak ketemu di VPS ini.
>>"MULAI_STRATEGY_4.bat" echo echo Buka folder %%CD%% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 1
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :pyok
>>"MULAI_STRATEGY_4.bat" echo set "DASH=python\cc_tkdashboard.py"
>>"MULAI_STRATEGY_4.bat" echo %%PY%% -c "import PySide6" >nul 2>nul
>>"MULAI_STRATEGY_4.bat" echo if errorlevel 1 goto dashgo
>>"MULAI_STRATEGY_4.bat" echo set "DASH=python\cc_qtdashboard.py"
>>"MULAI_STRATEGY_4.bat" echo :dashgo
>>"MULAI_STRATEGY_4.bat" echo set "PYW=%%PY%%"
>>"MULAI_STRATEGY_4.bat" echo for %%%%P in (%%PY%%) do if exist "%%%%~dpPpythonw.exe" set "PYW=%%%%~dpPpythonw.exe"
>>"MULAI_STRATEGY_4.bat" echo start "RBT FX DASHBOARD" %%PYW%% "%%DASH%%" --port 8082
>>"MULAI_STRATEGY_4.bat" echo echo Dashboard dinyalakan. Engine berjalan DI JENDELA INI - log hidup di bawah.
>>"MULAI_STRATEGY_4.bat" echo echo JANGAN tutup jendela ini selama trading.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo %%PY%% -u python\command_center.py
>>"MULAI_STRATEGY_4.bat" echo goto selesai
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :selesai
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo echo STRATEGY 4 berhenti. Klik 2x file ini lagi untuk menyalakan.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 0
>>"MULAI_STRATEGY_4.bat" echo.
if exist "MULAI_STRATEGY_4.bat" echo [OK] MULAI_STRATEGY_4.bat dibuat


rem ---- verifikasi ukuran file ----
set "BAD="
for %%F in ("MULAI_STRATEGY_1.bat" "MULAI_STRATEGY_2.bat" "MULAI_STRATEGY_3.bat" "MULAI_STRATEGY_4.bat") do if %%~zF LSS 800 set "BAD=%%~F"
if defined BAD goto gagal
echo [OK] 4 file bat sudah dibuat dan dicek: utuh.
echo.

rem ---- salin juga ke C:\RBT dan ke dalam tiap folder strategy ----
if /I "%~dp0"=="C:\RBT\" goto salin
if exist "C:\RBT\" (
  copy /Y "MULAI_STRATEGY_*.bat" "C:\RBT\" >nul
  echo [OK] disalin juga ke C:\RBT
)
:salin
if exist "C:\RBT\Sistem-Trading-Strategy-1\" copy /Y "MULAI_STRATEGY_1.bat" "C:\RBT\Sistem-Trading-Strategy-1\" >nul
if exist "C:\RBT\Sistem-Trading-Strategy-2\" copy /Y "MULAI_STRATEGY_2.bat" "C:\RBT\Sistem-Trading-Strategy-2\" >nul
if exist "C:\RBT\Sistem-Trading-Strategy-3\" copy /Y "MULAI_STRATEGY_3.bat" "C:\RBT\Sistem-Trading-Strategy-3\" >nul
if exist "C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21\" copy /Y "MULAI_STRATEGY_4.bat" "C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21\" >nul
if exist "C:\RBT\Sistem-Trading-Strategy-4\" copy /Y "MULAI_STRATEGY_4.bat" "C:\RBT\Sistem-Trading-Strategy-4\" >nul
echo [OK] salinan ditaruh juga di dalam tiap folder strategy yang ketemu.
echo.
echo ================================================================
echo    SELESAI!
echo    Sekarang klik 2x MULAI_STRATEGY_1.bat - atau 2 / 3 / 4 -
echo    untuk menyalakan strategy pilihan Anda.
echo ================================================================
echo.
pause
exit /b 0

:gagal
echo [X] Ada file yang gagal dibuat: %BAD%
echo     FOTO LAYAR ini lalu kirim ke chat untuk bantuan.
echo.
pause
exit /b 1
