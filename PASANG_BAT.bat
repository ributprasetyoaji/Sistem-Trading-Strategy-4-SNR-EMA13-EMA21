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
>>"MULAI_STRATEGY_1.bat" echo rem  MULAI STRATEGY 1 - FINAL v6 (anti-rusak versi lama)
>>"MULAI_STRATEGY_1.bat" echo rem  Letak file bebas: di dalam folder strategy, C:\RBT, Desktop,
>>"MULAI_STRATEGY_1.bat" echo rem  Downloads - folder dicari otomatis, nama folder fleksibel.
>>"MULAI_STRATEGY_1.bat" echo rem  Bisa mendeteksi MULAI_SEMUA.bat versi lama (penyebab GAGAL)
>>"MULAI_STRATEGY_1.bat" echo rem  dan menyalakan engine + dashboard LANGSUNG melewatinya.
>>"MULAI_STRATEGY_1.bat" echo rem ================================================================
>>"MULAI_STRATEGY_1.bat" echo set "DIR="
>>"MULAI_STRATEGY_1.bat" echo set "DIRF="
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
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy_1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy 1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy1*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo if defined DIR goto mulai
>>"MULAI_STRATEGY_1.bat" echo rem cadangan: folder ketemu tapi MULAI_SEMUA.bat belum ada - engine langsung
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%~dp0*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("C:\RBT\*Strategy_1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-1*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_1.bat" echo if defined DIRF goto engine
>>"MULAI_STRATEGY_1.bat" echo echo [X] Folder STRATEGY 1 tidak ketemu di lokasi manapun:
>>"MULAI_STRATEGY_1.bat" echo echo     di samping file ini, C:\RBT, Desktop, Downloads.
>>"MULAI_STRATEGY_1.bat" echo echo Pastikan folder Sistem-Trading-Strategy-1 ada di salah satu tempat itu.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 1
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :mulai
>>"MULAI_STRATEGY_1.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_1.bat" echo rem ==== DETEKSI BAT LAMA: MULAI_SEMUA.bat tanpa TOKEN.txt = versi lama ====
>>"MULAI_STRATEGY_1.bat" echo findstr /C:"TOKEN.txt" "MULAI_SEMUA.bat" >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if errorlevel 1 goto oldbat
>>"MULAI_STRATEGY_1.bat" echo echo Menyalakan STRATEGY 1 di %%DIR%% ...
>>"MULAI_STRATEGY_1.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_1.bat" echo goto selesai
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :oldbat
>>"MULAI_STRATEGY_1.bat" echo echo MULAI_SEMUA.bat versi LAMA terdeteksi - jalur update lamanya selalu GAGAL
>>"MULAI_STRATEGY_1.bat" echo echo (persis layar [0/3] GAGAL di foto). Engine + dashboard dinyalakan
>>"MULAI_STRATEGY_1.bat" echo echo LANGSUNG tanpa lewat jalur itu - Strategy 1 tetap trading.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo set "PY="
>>"MULAI_STRATEGY_1.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_1.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_1.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_1.bat" echo if defined PY goto pyok
>>"MULAI_STRATEGY_1.bat" echo echo [X] Python tidak ketemu. Buka folder %%DIR%% lalu klik 2x MULAI_SEMUA.bat.
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
>>"MULAI_STRATEGY_1.bat" echo echo Dashboard dinyalakan. Engine mulai - log hidup di jendela ini.
>>"MULAI_STRATEGY_1.bat" echo echo JANGAN tutup jendela ini selama trading.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo %%PY%% -u python\command_center.py
>>"MULAI_STRATEGY_1.bat" echo goto selesai
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :engine
>>"MULAI_STRATEGY_1.bat" echo cd /d "%%DIRF%%"
>>"MULAI_STRATEGY_1.bat" echo echo MULAI_SEMUA.bat belum ada - menyalakan engine + dashboard langsung di %%DIRF%%
>>"MULAI_STRATEGY_1.bat" echo set "PY="
>>"MULAI_STRATEGY_1.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_1.bat" echo if defined PY goto pyok2
>>"MULAI_STRATEGY_1.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_1.bat" echo if defined PY goto pyok2
>>"MULAI_STRATEGY_1.bat" echo echo [X] Python tidak ketemu.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 1
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :pyok2
>>"MULAI_STRATEGY_1.bat" echo set "DASH=python\cc_tkdashboard.py"
>>"MULAI_STRATEGY_1.bat" echo %%PY%% -c "import PySide6" >nul 2>nul
>>"MULAI_STRATEGY_1.bat" echo if errorlevel 1 goto dashgo2
>>"MULAI_STRATEGY_1.bat" echo set "DASH=python\cc_qtdashboard.py"
>>"MULAI_STRATEGY_1.bat" echo :dashgo2
>>"MULAI_STRATEGY_1.bat" echo set "PYW=%%PY%%"
>>"MULAI_STRATEGY_1.bat" echo for %%%%P in (%%PY%%) do if exist "%%%%~dpPpythonw.exe" set "PYW=%%%%~dpPpythonw.exe"
>>"MULAI_STRATEGY_1.bat" echo start "RBT FX DASHBOARD" %%PYW%% "%%DASH%%" --port 8080
>>"MULAI_STRATEGY_1.bat" echo echo Dashboard dinyalakan. Engine mulai - log hidup di jendela ini.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo %%PY%% -u python\command_center.py
>>"MULAI_STRATEGY_1.bat" echo goto selesai
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :selesai
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo echo STRATEGY 1 berhenti. Klik 2x file ini lagi untuk menyalakan.
>>"MULAI_STRATEGY_1.bat" echo echo Saran: jalankan PERBAIKI_TOKEN.bat sekali di folder ini agar
>>"MULAI_STRATEGY_1.bat" echo echo jalur update normal kembali berfungsi.
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
>>"MULAI_STRATEGY_2.bat" echo rem  MULAI STRATEGY 2 - FILE FINAL UTUH (mandiri)
>>"MULAI_STRATEGY_2.bat" echo rem  Letak file bebas: di dalam folder strategy, C:\RBT, Desktop,
>>"MULAI_STRATEGY_2.bat" echo rem  Downloads - folder strategy dicari otomatis di semua tempat,
>>"MULAI_STRATEGY_2.bat" echo rem  nama folder fleksibel (Strategy-1, Strategy_1, Strategy 1, dll).
>>"MULAI_STRATEGY_2.bat" echo rem ================================================================
>>"MULAI_STRATEGY_2.bat" echo set "DIR="
>>"MULAI_STRATEGY_2.bat" echo set "DIRF="
>>"MULAI_STRATEGY_2.bat" echo rem [1/3] file ini ada DI DALAM folder strategy?
>>"MULAI_STRATEGY_2.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_2.bat" echo rem [2/3] cari folder strategy di 4 lokasi, nama folder fleksibel
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
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy_2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy 2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy2*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo if defined DIR goto mulai
>>"MULAI_STRATEGY_2.bat" echo rem [3/3] cadangan: folder strategy ketemu tapi MULAI_SEMUA.bat belum ada - engine langsung
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%~dp0*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("C:\RBT\*Strategy_2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-2*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_2.bat" echo if defined DIRF goto engine
>>"MULAI_STRATEGY_2.bat" echo echo [X] Folder STRATEGY 2 tidak ketemu di lokasi manapun:
>>"MULAI_STRATEGY_2.bat" echo echo     di samping file ini, C:\RBT, Desktop, Downloads.
>>"MULAI_STRATEGY_2.bat" echo echo Pastikan folder Sistem-Trading-Strategy-2 ada di salah satu tempat itu.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 1
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :mulai
>>"MULAI_STRATEGY_2.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_2.bat" echo echo Menyalakan STRATEGY 2 di %%DIR%% ...
>>"MULAI_STRATEGY_2.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo echo STRATEGY 2 berhenti. Klik 2x file ini lagi untuk menyalakan.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 0
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :engine
>>"MULAI_STRATEGY_2.bat" echo cd /d "%%DIRF%%"
>>"MULAI_STRATEGY_2.bat" echo echo MULAI_SEMUA.bat belum ada - menyalakan engine langsung di %%DIRF%%
>>"MULAI_STRATEGY_2.bat" echo set "PY="
>>"MULAI_STRATEGY_2.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_2.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_2.bat" echo if defined PY goto runeng
>>"MULAI_STRATEGY_2.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_2.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_2.bat" echo if defined PY goto runeng
>>"MULAI_STRATEGY_2.bat" echo echo [X] Python tidak ketemu. Cara yang betul:
>>"MULAI_STRATEGY_2.bat" echo echo     buka folder %%DIRF%% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 1
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :runeng
>>"MULAI_STRATEGY_2.bat" echo "%%PY%%" -u python\command_center.py
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo echo STRATEGY 2 berhenti. Klik 2x file ini lagi untuk menyalakan.
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
>>"MULAI_STRATEGY_3.bat" echo rem  MULAI STRATEGY 3 - FILE FINAL UTUH (mandiri)
>>"MULAI_STRATEGY_3.bat" echo rem  Letak file bebas: di dalam folder strategy, C:\RBT, Desktop,
>>"MULAI_STRATEGY_3.bat" echo rem  Downloads - folder strategy dicari otomatis di semua tempat,
>>"MULAI_STRATEGY_3.bat" echo rem  nama folder fleksibel (Strategy-1, Strategy_1, Strategy 1, dll).
>>"MULAI_STRATEGY_3.bat" echo rem ================================================================
>>"MULAI_STRATEGY_3.bat" echo set "DIR="
>>"MULAI_STRATEGY_3.bat" echo set "DIRF="
>>"MULAI_STRATEGY_3.bat" echo rem [1/3] file ini ada DI DALAM folder strategy?
>>"MULAI_STRATEGY_3.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_3.bat" echo rem [2/3] cari folder strategy di 4 lokasi, nama folder fleksibel
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
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy_3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy 3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy3*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo if defined DIR goto mulai
>>"MULAI_STRATEGY_3.bat" echo rem [3/3] cadangan: folder strategy ketemu tapi MULAI_SEMUA.bat belum ada - engine langsung
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%~dp0*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("C:\RBT\*Strategy_3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-3*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_3.bat" echo if defined DIRF goto engine
>>"MULAI_STRATEGY_3.bat" echo echo [X] Folder STRATEGY 3 tidak ketemu di lokasi manapun:
>>"MULAI_STRATEGY_3.bat" echo echo     di samping file ini, C:\RBT, Desktop, Downloads.
>>"MULAI_STRATEGY_3.bat" echo echo Pastikan folder Sistem-Trading-Strategy-3 ada di salah satu tempat itu.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 1
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :mulai
>>"MULAI_STRATEGY_3.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_3.bat" echo echo Menyalakan STRATEGY 3 di %%DIR%% ...
>>"MULAI_STRATEGY_3.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo echo STRATEGY 3 berhenti. Klik 2x file ini lagi untuk menyalakan.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 0
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :engine
>>"MULAI_STRATEGY_3.bat" echo cd /d "%%DIRF%%"
>>"MULAI_STRATEGY_3.bat" echo echo MULAI_SEMUA.bat belum ada - menyalakan engine langsung di %%DIRF%%
>>"MULAI_STRATEGY_3.bat" echo set "PY="
>>"MULAI_STRATEGY_3.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_3.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_3.bat" echo if defined PY goto runeng
>>"MULAI_STRATEGY_3.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_3.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_3.bat" echo if defined PY goto runeng
>>"MULAI_STRATEGY_3.bat" echo echo [X] Python tidak ketemu. Cara yang betul:
>>"MULAI_STRATEGY_3.bat" echo echo     buka folder %%DIRF%% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 1
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :runeng
>>"MULAI_STRATEGY_3.bat" echo "%%PY%%" -u python\command_center.py
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo echo STRATEGY 3 berhenti. Klik 2x file ini lagi untuk menyalakan.
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
>>"MULAI_STRATEGY_4.bat" echo rem  MULAI STRATEGY 4 - FILE FINAL UTUH (mandiri)
>>"MULAI_STRATEGY_4.bat" echo rem  Letak file bebas: di dalam folder strategy, C:\RBT, Desktop,
>>"MULAI_STRATEGY_4.bat" echo rem  Downloads - folder strategy dicari otomatis di semua tempat,
>>"MULAI_STRATEGY_4.bat" echo rem  nama folder fleksibel (Strategy-1, Strategy_1, Strategy 1, dll).
>>"MULAI_STRATEGY_4.bat" echo rem ================================================================
>>"MULAI_STRATEGY_4.bat" echo set "DIR="
>>"MULAI_STRATEGY_4.bat" echo set "DIRF="
>>"MULAI_STRATEGY_4.bat" echo rem [1/3] file ini ada DI DALAM folder strategy?
>>"MULAI_STRATEGY_4.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_4.bat" echo rem [2/3] cari folder strategy di 4 lokasi, nama folder fleksibel
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
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy_4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy 4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy4*") do if exist "%%%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo if defined DIR goto mulai
>>"MULAI_STRATEGY_4.bat" echo rem [3/3] cadangan: folder strategy ketemu tapi MULAI_SEMUA.bat belum ada - engine langsung
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%~dp0*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("C:\RBT\*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("C:\RBT\*Strategy_4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Desktop\*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo for /d %%%%D in ("%%USERPROFILE%%\Downloads\*Strategy-4*") do if not defined DIRF set "DIRF=%%%%D"
>>"MULAI_STRATEGY_4.bat" echo if defined DIRF goto engine
>>"MULAI_STRATEGY_4.bat" echo echo [X] Folder STRATEGY 4 tidak ketemu di lokasi manapun:
>>"MULAI_STRATEGY_4.bat" echo echo     di samping file ini, C:\RBT, Desktop, Downloads.
>>"MULAI_STRATEGY_4.bat" echo echo Pastikan folder Sistem-Trading-Strategy-4 ada di salah satu tempat itu.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 1
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :mulai
>>"MULAI_STRATEGY_4.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_4.bat" echo echo Menyalakan STRATEGY 4 di %%DIR%% ...
>>"MULAI_STRATEGY_4.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo echo STRATEGY 4 berhenti. Klik 2x file ini lagi untuk menyalakan.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 0
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :engine
>>"MULAI_STRATEGY_4.bat" echo cd /d "%%DIRF%%"
>>"MULAI_STRATEGY_4.bat" echo echo MULAI_SEMUA.bat belum ada - menyalakan engine langsung di %%DIRF%%
>>"MULAI_STRATEGY_4.bat" echo set "PY="
>>"MULAI_STRATEGY_4.bat" echo python --version >nul 2>nul
>>"MULAI_STRATEGY_4.bat" echo if not errorlevel 1 set "PY=python"
>>"MULAI_STRATEGY_4.bat" echo if defined PY goto runeng
>>"MULAI_STRATEGY_4.bat" echo py -3 --version >nul 2>nul
>>"MULAI_STRATEGY_4.bat" echo if not errorlevel 1 set "PY=py -3"
>>"MULAI_STRATEGY_4.bat" echo if defined PY goto runeng
>>"MULAI_STRATEGY_4.bat" echo echo [X] Python tidak ketemu. Cara yang betul:
>>"MULAI_STRATEGY_4.bat" echo echo     buka folder %%DIRF%% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 1
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :runeng
>>"MULAI_STRATEGY_4.bat" echo "%%PY%%" -u python\command_center.py
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo echo STRATEGY 4 berhenti. Klik 2x file ini lagi untuk menyalakan.
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
