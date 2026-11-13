@echo off
setlocal enableextensions
title RBT FX - MULAI STRATEGY 4
cd /d "%~dp0"

rem =================================================================
rem  MULAI STRATEGY 4 SAJA (satu klik, strategy ini sendiri)
rem  Posisi file boleh di mana saja dari ini:
rem   - di C:\RBT (sebelah folder strategy)  ATAU
rem   - di DALAM folder strategy-nya langsung
rem =================================================================

set "DIR="
if exist "MULAI_SEMUA.bat" if exist "python\command_center.py" set "DIR=%~dp0"
if not defined DIR if exist "%~dp0Sistem-Trading-Strategy-4-SNR-EMA13-EMA21\MULAI_SEMUA.bat" set "DIR=%~dp0Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
if not defined DIR if exist "%~dp0Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main\MULAI_SEMUA.bat" set "DIR=%~dp0Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
if not defined DIR if exist "C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21\MULAI_SEMUA.bat" set "DIR=C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
if not defined DIR if exist "C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main\MULAI_SEMUA.bat" set "DIR=C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main"
if not defined DIR if exist "%~dp0Sistem-Trading-Strategy-4\MULAI_SEMUA.bat" set "DIR=%~dp0Sistem-Trading-Strategy-4"
if not defined DIR if exist "%~dp0Sistem-Trading-Strategy-4-main\MULAI_SEMUA.bat" set "DIR=%~dp0Sistem-Trading-Strategy-4-main"
if not defined DIR if exist "C:\RBT\Sistem-Trading-Strategy-4\MULAI_SEMUA.bat" set "DIR=C:\RBT\Sistem-Trading-Strategy-4"
if not defined DIR if exist "C:\RBT\Sistem-Trading-Strategy-4-main\MULAI_SEMUA.bat" set "DIR=C:\RBT\Sistem-Trading-Strategy-4-main"
if not defined DIR goto miss
goto have

:miss
echo   [X] Folder STRATEGY 4 tidak ketemu.
echo       Taruh file ini di folder C:\RBT (sebelah folder strategy),
echo       atau di dalam folder strategy-nya langsung.
echo.
pause
exit /b 1

:have
echo ================================================================
echo    MULAI STRATEGY 4  (strategy ini sendiri)
echo    Folder : %DIR%
echo ================================================================
cd /d "%DIR%"
call MULAI_SEMUA.bat
