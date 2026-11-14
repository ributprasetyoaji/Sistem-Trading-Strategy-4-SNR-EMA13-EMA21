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
>>"MULAI_STRATEGY_1.bat" echo setlocal enableextensions
>>"MULAI_STRATEGY_1.bat" echo title RBT FX - MULAI STRATEGY 1 SATU KLIK
>>"MULAI_STRATEGY_1.bat" echo cd /d "%%~dp0"
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo rem =================================================================
>>"MULAI_STRATEGY_1.bat" echo rem  MULAI STRATEGY 1 SAJA - satu klik
>>"MULAI_STRATEGY_1.bat" echo rem  Posisi file bebas: C:\RBT, Desktop, Downloads, atau di dalam
>>"MULAI_STRATEGY_1.bat" echo rem  folder strategy-nya langsung - semua dicari otomatis.
>>"MULAI_STRATEGY_1.bat" echo rem =================================================================
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo set "DIR="
>>"MULAI_STRATEGY_1.bat" echo echo [1/3] Cari folder STRATEGY 1 ...
>>"MULAI_STRATEGY_1.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" if exist "%%~dp0python\command_center.py" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_1.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-1"
>>"MULAI_STRATEGY_1.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-1"
>>"MULAI_STRATEGY_1.bat" echo call :look "C:\Sistem-Trading-Strategy-1"
>>"MULAI_STRATEGY_1.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-1"
>>"MULAI_STRATEGY_1.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-1"
>>"MULAI_STRATEGY_1.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-1-main"
>>"MULAI_STRATEGY_1.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-1-main"
>>"MULAI_STRATEGY_1.bat" echo call :look "C:\Sistem-Trading-Strategy-1-main"
>>"MULAI_STRATEGY_1.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-1-main"
>>"MULAI_STRATEGY_1.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-1-main"
>>"MULAI_STRATEGY_1.bat" echo if not defined DIR goto miss
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo echo Ketemu: %%DIR%%
>>"MULAI_STRATEGY_1.bat" echo echo [2/3] Menyalakan STRATEGY 1 - engine plus dashboard...
>>"MULAI_STRATEGY_1.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_1.bat" echo if not exist "MULAI_SEMUA.bat" goto nomulai
>>"MULAI_STRATEGY_1.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_1.bat" echo goto selesai
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :nomulai
>>"MULAI_STRATEGY_1.bat" echo if exist "RBT_FX_STRATEGY1.bat" call "RBT_FX_STRATEGY1.bat"
>>"MULAI_STRATEGY_1.bat" echo if exist "RBT_FX_STRATEGY1.bat" goto selesai
>>"MULAI_STRATEGY_1.bat" echo echo [X] MULAI_SEMUA.bat tidak ada di folder itu - update dulu:
>>"MULAI_STRATEGY_1.bat" echo echo     klik 2x PERBAIKI_TOKEN.bat sekali, lalu coba lagi.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 1
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :miss
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo echo [X] Folder STRATEGY 1 tidak ketemu di lokasi standar:
>>"MULAI_STRATEGY_1.bat" echo echo     - di samping file ini  -  C:\RBT  -  C:\
>>"MULAI_STRATEGY_1.bat" echo echo     - Desktop  -  Downloads
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo echo Solusi: taruh file ini di C:\RBT sebelah folder strategy,
>>"MULAI_STRATEGY_1.bat" echo echo atau di dalam folder strategy-nya langsung, lalu klik 2x lagi.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 1
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :selesai
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo echo [3/3] STRATEGY 1 berhenti - engine atau jendela ditutup.
>>"MULAI_STRATEGY_1.bat" echo echo Klik 2x file ini lagi untuk menyalakan kembali.
>>"MULAI_STRATEGY_1.bat" echo echo.
>>"MULAI_STRATEGY_1.bat" echo pause
>>"MULAI_STRATEGY_1.bat" echo exit /b 0
>>"MULAI_STRATEGY_1.bat" echo.
>>"MULAI_STRATEGY_1.bat" echo :look
>>"MULAI_STRATEGY_1.bat" echo if defined DIR goto :eof
>>"MULAI_STRATEGY_1.bat" echo if not exist "%%~1\MULAI_SEMUA.bat" goto :eof
>>"MULAI_STRATEGY_1.bat" echo set "DIR=%%~1"
>>"MULAI_STRATEGY_1.bat" echo echo [OK] folder ketemu: %%~1
>>"MULAI_STRATEGY_1.bat" echo goto :eof
>>"MULAI_STRATEGY_1.bat" echo.
if exist "MULAI_STRATEGY_1.bat" echo [OK] MULAI_STRATEGY_1.bat dibuat

rem ====== MULAI_STRATEGY_2.bat ======
if exist "MULAI_STRATEGY_2.bat" del "MULAI_STRATEGY_2.bat" >nul 2>nul
>>"MULAI_STRATEGY_2.bat" echo @echo off
>>"MULAI_STRATEGY_2.bat" echo setlocal enableextensions
>>"MULAI_STRATEGY_2.bat" echo title RBT FX - MULAI STRATEGY 2 SATU KLIK
>>"MULAI_STRATEGY_2.bat" echo cd /d "%%~dp0"
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo rem =================================================================
>>"MULAI_STRATEGY_2.bat" echo rem  MULAI STRATEGY 2 SAJA - satu klik
>>"MULAI_STRATEGY_2.bat" echo rem  Posisi file bebas: C:\RBT, Desktop, Downloads, atau di dalam
>>"MULAI_STRATEGY_2.bat" echo rem  folder strategy-nya langsung - semua dicari otomatis.
>>"MULAI_STRATEGY_2.bat" echo rem =================================================================
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo set "DIR="
>>"MULAI_STRATEGY_2.bat" echo echo [1/3] Cari folder STRATEGY 2 ...
>>"MULAI_STRATEGY_2.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" if exist "%%~dp0python\command_center.py" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_2.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-2"
>>"MULAI_STRATEGY_2.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-2"
>>"MULAI_STRATEGY_2.bat" echo call :look "C:\Sistem-Trading-Strategy-2"
>>"MULAI_STRATEGY_2.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-2"
>>"MULAI_STRATEGY_2.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-2"
>>"MULAI_STRATEGY_2.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-2-main"
>>"MULAI_STRATEGY_2.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-2-main"
>>"MULAI_STRATEGY_2.bat" echo call :look "C:\Sistem-Trading-Strategy-2-main"
>>"MULAI_STRATEGY_2.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-2-main"
>>"MULAI_STRATEGY_2.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-2-main"
>>"MULAI_STRATEGY_2.bat" echo if not defined DIR goto miss
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo echo Ketemu: %%DIR%%
>>"MULAI_STRATEGY_2.bat" echo echo [2/3] Menyalakan STRATEGY 2 - engine plus dashboard...
>>"MULAI_STRATEGY_2.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_2.bat" echo if not exist "MULAI_SEMUA.bat" goto nomulai
>>"MULAI_STRATEGY_2.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_2.bat" echo goto selesai
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :nomulai
>>"MULAI_STRATEGY_2.bat" echo if exist "RBT_FX_STRATEGY2.bat" call "RBT_FX_STRATEGY2.bat"
>>"MULAI_STRATEGY_2.bat" echo if exist "RBT_FX_STRATEGY2.bat" goto selesai
>>"MULAI_STRATEGY_2.bat" echo echo [X] MULAI_SEMUA.bat tidak ada di folder itu - update dulu:
>>"MULAI_STRATEGY_2.bat" echo echo     klik 2x PERBAIKI_TOKEN.bat sekali, lalu coba lagi.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 1
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :miss
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo echo [X] Folder STRATEGY 2 tidak ketemu di lokasi standar:
>>"MULAI_STRATEGY_2.bat" echo echo     - di samping file ini  -  C:\RBT  -  C:\
>>"MULAI_STRATEGY_2.bat" echo echo     - Desktop  -  Downloads
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo echo Solusi: taruh file ini di C:\RBT sebelah folder strategy,
>>"MULAI_STRATEGY_2.bat" echo echo atau di dalam folder strategy-nya langsung, lalu klik 2x lagi.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 1
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :selesai
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo echo [3/3] STRATEGY 2 berhenti - engine atau jendela ditutup.
>>"MULAI_STRATEGY_2.bat" echo echo Klik 2x file ini lagi untuk menyalakan kembali.
>>"MULAI_STRATEGY_2.bat" echo echo.
>>"MULAI_STRATEGY_2.bat" echo pause
>>"MULAI_STRATEGY_2.bat" echo exit /b 0
>>"MULAI_STRATEGY_2.bat" echo.
>>"MULAI_STRATEGY_2.bat" echo :look
>>"MULAI_STRATEGY_2.bat" echo if defined DIR goto :eof
>>"MULAI_STRATEGY_2.bat" echo if not exist "%%~1\MULAI_SEMUA.bat" goto :eof
>>"MULAI_STRATEGY_2.bat" echo set "DIR=%%~1"
>>"MULAI_STRATEGY_2.bat" echo echo [OK] folder ketemu: %%~1
>>"MULAI_STRATEGY_2.bat" echo goto :eof
>>"MULAI_STRATEGY_2.bat" echo.
if exist "MULAI_STRATEGY_2.bat" echo [OK] MULAI_STRATEGY_2.bat dibuat

rem ====== MULAI_STRATEGY_3.bat ======
if exist "MULAI_STRATEGY_3.bat" del "MULAI_STRATEGY_3.bat" >nul 2>nul
>>"MULAI_STRATEGY_3.bat" echo @echo off
>>"MULAI_STRATEGY_3.bat" echo setlocal enableextensions
>>"MULAI_STRATEGY_3.bat" echo title RBT FX - MULAI STRATEGY 3 SATU KLIK
>>"MULAI_STRATEGY_3.bat" echo cd /d "%%~dp0"
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo rem =================================================================
>>"MULAI_STRATEGY_3.bat" echo rem  MULAI STRATEGY 3 SAJA - satu klik
>>"MULAI_STRATEGY_3.bat" echo rem  Posisi file bebas: C:\RBT, Desktop, Downloads, atau di dalam
>>"MULAI_STRATEGY_3.bat" echo rem  folder strategy-nya langsung - semua dicari otomatis.
>>"MULAI_STRATEGY_3.bat" echo rem =================================================================
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo set "DIR="
>>"MULAI_STRATEGY_3.bat" echo echo [1/3] Cari folder STRATEGY 3 ...
>>"MULAI_STRATEGY_3.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" if exist "%%~dp0python\command_center.py" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_3.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-3"
>>"MULAI_STRATEGY_3.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-3"
>>"MULAI_STRATEGY_3.bat" echo call :look "C:\Sistem-Trading-Strategy-3"
>>"MULAI_STRATEGY_3.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-3"
>>"MULAI_STRATEGY_3.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-3"
>>"MULAI_STRATEGY_3.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-3-main"
>>"MULAI_STRATEGY_3.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-3-main"
>>"MULAI_STRATEGY_3.bat" echo call :look "C:\Sistem-Trading-Strategy-3-main"
>>"MULAI_STRATEGY_3.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-3-main"
>>"MULAI_STRATEGY_3.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-3-main"
>>"MULAI_STRATEGY_3.bat" echo if not defined DIR goto miss
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo echo Ketemu: %%DIR%%
>>"MULAI_STRATEGY_3.bat" echo echo [2/3] Menyalakan STRATEGY 3 - engine plus dashboard...
>>"MULAI_STRATEGY_3.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_3.bat" echo if not exist "MULAI_SEMUA.bat" goto nomulai
>>"MULAI_STRATEGY_3.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_3.bat" echo goto selesai
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :nomulai
>>"MULAI_STRATEGY_3.bat" echo if exist "RBT_FX_STRATEGY3.bat" call "RBT_FX_STRATEGY3.bat"
>>"MULAI_STRATEGY_3.bat" echo if exist "RBT_FX_STRATEGY3.bat" goto selesai
>>"MULAI_STRATEGY_3.bat" echo echo [X] MULAI_SEMUA.bat tidak ada di folder itu - update dulu:
>>"MULAI_STRATEGY_3.bat" echo echo     klik 2x PERBAIKI_TOKEN.bat sekali, lalu coba lagi.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 1
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :miss
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo echo [X] Folder STRATEGY 3 tidak ketemu di lokasi standar:
>>"MULAI_STRATEGY_3.bat" echo echo     - di samping file ini  -  C:\RBT  -  C:\
>>"MULAI_STRATEGY_3.bat" echo echo     - Desktop  -  Downloads
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo echo Solusi: taruh file ini di C:\RBT sebelah folder strategy,
>>"MULAI_STRATEGY_3.bat" echo echo atau di dalam folder strategy-nya langsung, lalu klik 2x lagi.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 1
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :selesai
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo echo [3/3] STRATEGY 3 berhenti - engine atau jendela ditutup.
>>"MULAI_STRATEGY_3.bat" echo echo Klik 2x file ini lagi untuk menyalakan kembali.
>>"MULAI_STRATEGY_3.bat" echo echo.
>>"MULAI_STRATEGY_3.bat" echo pause
>>"MULAI_STRATEGY_3.bat" echo exit /b 0
>>"MULAI_STRATEGY_3.bat" echo.
>>"MULAI_STRATEGY_3.bat" echo :look
>>"MULAI_STRATEGY_3.bat" echo if defined DIR goto :eof
>>"MULAI_STRATEGY_3.bat" echo if not exist "%%~1\MULAI_SEMUA.bat" goto :eof
>>"MULAI_STRATEGY_3.bat" echo set "DIR=%%~1"
>>"MULAI_STRATEGY_3.bat" echo echo [OK] folder ketemu: %%~1
>>"MULAI_STRATEGY_3.bat" echo goto :eof
>>"MULAI_STRATEGY_3.bat" echo.
if exist "MULAI_STRATEGY_3.bat" echo [OK] MULAI_STRATEGY_3.bat dibuat

rem ====== MULAI_STRATEGY_4.bat ======
if exist "MULAI_STRATEGY_4.bat" del "MULAI_STRATEGY_4.bat" >nul 2>nul
>>"MULAI_STRATEGY_4.bat" echo @echo off
>>"MULAI_STRATEGY_4.bat" echo setlocal enableextensions
>>"MULAI_STRATEGY_4.bat" echo title RBT FX - MULAI STRATEGY 4 SATU KLIK
>>"MULAI_STRATEGY_4.bat" echo cd /d "%%~dp0"
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo rem =================================================================
>>"MULAI_STRATEGY_4.bat" echo rem  MULAI STRATEGY 4 SAJA - satu klik
>>"MULAI_STRATEGY_4.bat" echo rem  Posisi file bebas: C:\RBT, Desktop, Downloads, atau di dalam
>>"MULAI_STRATEGY_4.bat" echo rem  folder strategy-nya langsung - semua dicari otomatis.
>>"MULAI_STRATEGY_4.bat" echo rem =================================================================
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo set "DIR="
>>"MULAI_STRATEGY_4.bat" echo echo [1/3] Cari folder STRATEGY 4 ...
>>"MULAI_STRATEGY_4.bat" echo if exist "%%~dp0MULAI_SEMUA.bat" if exist "%%~dp0python\command_center.py" set "DIR=%%~dp0"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
>>"MULAI_STRATEGY_4.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
>>"MULAI_STRATEGY_4.bat" echo call :look "C:\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "C:\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-4"
>>"MULAI_STRATEGY_4.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-4"
>>"MULAI_STRATEGY_4.bat" echo call :look "C:\Sistem-Trading-Strategy-4"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-4"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-4"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%~dp0Sistem-Trading-Strategy-4-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "C:\RBT\Sistem-Trading-Strategy-4-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "C:\Sistem-Trading-Strategy-4-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%USERPROFILE%%\Desktop\Sistem-Trading-Strategy-4-main"
>>"MULAI_STRATEGY_4.bat" echo call :look "%%USERPROFILE%%\Downloads\Sistem-Trading-Strategy-4-main"
>>"MULAI_STRATEGY_4.bat" echo if not defined DIR goto miss
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo echo Ketemu: %%DIR%%
>>"MULAI_STRATEGY_4.bat" echo echo [2/3] Menyalakan STRATEGY 4 - engine plus dashboard...
>>"MULAI_STRATEGY_4.bat" echo cd /d "%%DIR%%"
>>"MULAI_STRATEGY_4.bat" echo if not exist "MULAI_SEMUA.bat" goto nomulai
>>"MULAI_STRATEGY_4.bat" echo call "MULAI_SEMUA.bat"
>>"MULAI_STRATEGY_4.bat" echo goto selesai
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :nomulai
>>"MULAI_STRATEGY_4.bat" echo if exist "RBT_FX_STRATEGY4.bat" call "RBT_FX_STRATEGY4.bat"
>>"MULAI_STRATEGY_4.bat" echo if exist "RBT_FX_STRATEGY4.bat" goto selesai
>>"MULAI_STRATEGY_4.bat" echo echo [X] MULAI_SEMUA.bat tidak ada di folder itu - update dulu:
>>"MULAI_STRATEGY_4.bat" echo echo     klik 2x PERBAIKI_TOKEN.bat sekali, lalu coba lagi.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 1
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :miss
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo echo [X] Folder STRATEGY 4 tidak ketemu di lokasi standar:
>>"MULAI_STRATEGY_4.bat" echo echo     - di samping file ini  -  C:\RBT  -  C:\
>>"MULAI_STRATEGY_4.bat" echo echo     - Desktop  -  Downloads
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo echo Solusi: taruh file ini di C:\RBT sebelah folder strategy,
>>"MULAI_STRATEGY_4.bat" echo echo atau di dalam folder strategy-nya langsung, lalu klik 2x lagi.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 1
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :selesai
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo echo [3/3] STRATEGY 4 berhenti - engine atau jendela ditutup.
>>"MULAI_STRATEGY_4.bat" echo echo Klik 2x file ini lagi untuk menyalakan kembali.
>>"MULAI_STRATEGY_4.bat" echo echo.
>>"MULAI_STRATEGY_4.bat" echo pause
>>"MULAI_STRATEGY_4.bat" echo exit /b 0
>>"MULAI_STRATEGY_4.bat" echo.
>>"MULAI_STRATEGY_4.bat" echo :look
>>"MULAI_STRATEGY_4.bat" echo if defined DIR goto :eof
>>"MULAI_STRATEGY_4.bat" echo if not exist "%%~1\MULAI_SEMUA.bat" goto :eof
>>"MULAI_STRATEGY_4.bat" echo set "DIR=%%~1"
>>"MULAI_STRATEGY_4.bat" echo echo [OK] folder ketemu: %%~1
>>"MULAI_STRATEGY_4.bat" echo goto :eof
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
