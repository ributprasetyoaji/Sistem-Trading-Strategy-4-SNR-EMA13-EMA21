@echo off
setlocal enableextensions
title RBT FX - MULAI STRATEGY 4 SATU KLIK
cd /d "%~dp0"

rem =================================================================
rem  MULAI STRATEGY 4 SAJA - satu klik
rem  Posisi file bebas: C:\RBT, Desktop, Downloads, atau di dalam
rem  folder strategy-nya langsung - semua dicari otomatis.
rem =================================================================

set "DIR="
echo [1/3] Cari folder STRATEGY 4 ...
if exist "%~dp0MULAI_SEMUA.bat" if exist "%~dp0python\command_center.py" set "DIR=%~dp0"
call :look "%~dp0Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
call :look "C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
call :look "C:\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
call :look "%USERPROFILE%\Desktop\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
call :look "%USERPROFILE%\Downloads\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
call :look "%~dp0Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
call :look "C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
call :look "C:\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
call :look "%USERPROFILE%\Desktop\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
call :look "%USERPROFILE%\Downloads\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
call :look "%~dp0Sistem-Trading-Strategy-4"
call :look "C:\RBT\Sistem-Trading-Strategy-4"
call :look "C:\Sistem-Trading-Strategy-4"
call :look "%USERPROFILE%\Desktop\Sistem-Trading-Strategy-4"
call :look "%USERPROFILE%\Downloads\Sistem-Trading-Strategy-4"
call :look "%~dp0Sistem-Trading-Strategy-4-main"
call :look "C:\RBT\Sistem-Trading-Strategy-4-main"
call :look "C:\Sistem-Trading-Strategy-4-main"
call :look "%USERPROFILE%\Desktop\Sistem-Trading-Strategy-4-main"
call :look "%USERPROFILE%\Downloads\Sistem-Trading-Strategy-4-main"
if not defined DIR goto miss

echo Ketemu: %DIR%
echo [2/3] Menyalakan STRATEGY 4 - engine plus dashboard...
cd /d "%DIR%"
if not exist "MULAI_SEMUA.bat" goto nomulai
call "MULAI_SEMUA.bat"
goto selesai

:nomulai
if exist "RBT_FX_STRATEGY4.bat" call "RBT_FX_STRATEGY4.bat"
if exist "RBT_FX_STRATEGY4.bat" goto selesai
echo [X] MULAI_SEMUA.bat tidak ada di folder itu - update dulu:
echo     klik 2x PERBAIKI_TOKEN.bat sekali, lalu coba lagi.
echo.
pause
exit /b 1

:miss
echo.
echo [X] Folder STRATEGY 4 tidak ketemu di lokasi standar:
echo     - di samping file ini  -  C:\RBT  -  C:\
echo     - Desktop  -  Downloads
echo.
echo Solusi: taruh file ini di C:\RBT sebelah folder strategy,
echo atau di dalam folder strategy-nya langsung, lalu klik 2x lagi.
echo.
pause
exit /b 1

:selesai
echo.
echo [3/3] STRATEGY 4 berhenti - engine atau jendela ditutup.
echo Klik 2x file ini lagi untuk menyalakan kembali.
echo.
pause
exit /b 0

:look
if defined DIR goto :eof
if not exist "%~1\MULAI_SEMUA.bat" goto :eof
set "DIR=%~1"
echo [OK] folder ketemu: %~1
goto :eof
