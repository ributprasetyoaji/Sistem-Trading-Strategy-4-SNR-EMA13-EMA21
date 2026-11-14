@echo off
setlocal
title RBT FX - STRATEGY 4
rem ================================================================
rem  MULAI STRATEGY 4 - FILE FINAL UTUH (mandiri)
rem  Letak file bebas: di dalam folder strategy, C:\RBT, Desktop,
rem  Downloads - folder strategy dicari otomatis di semua tempat,
rem  nama folder fleksibel (Strategy-1, Strategy_1, Strategy 1, dll).
rem ================================================================
set "DIR="
set "DIRF="
rem [1/3] file ini ada DI DALAM folder strategy?
if exist "%~dp0MULAI_SEMUA.bat" set "DIR=%~dp0"
rem [2/3] cari folder strategy di 4 lokasi, nama folder fleksibel
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
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
if defined DIR goto mulai
rem [3/3] cadangan: folder strategy ketemu tapi MULAI_SEMUA.bat belum ada - engine langsung
for /d %%D in ("%~dp0*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("C:\RBT\*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("C:\RBT\*Strategy_4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("%USERPROFILE%\Desktop\*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
for /d %%D in ("%USERPROFILE%\Downloads\*Strategy-4*") do if not defined DIRF set "DIRF=%%D"
if defined DIRF goto engine
echo [X] Folder STRATEGY 4 tidak ketemu di lokasi manapun:
echo     di samping file ini, C:\RBT, Desktop, Downloads.
echo Pastikan folder Sistem-Trading-Strategy-4 ada di salah satu tempat itu.
echo.
pause
exit /b 1

:mulai
cd /d "%DIR%"
echo Menyalakan STRATEGY 4 di %DIR% ...
call "MULAI_SEMUA.bat"
echo.
echo STRATEGY 4 berhenti. Klik 2x file ini lagi untuk menyalakan.
pause
exit /b 0

:engine
cd /d "%DIRF%"
echo MULAI_SEMUA.bat belum ada - menyalakan engine langsung di %DIRF%
set "PY="
python --version >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto runeng
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto runeng
echo [X] Python tidak ketemu. Cara yang betul:
echo     buka folder %DIRF% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
echo.
pause
exit /b 1

:runeng
"%PY%" -u python\command_center.py
echo.
echo STRATEGY 4 berhenti. Klik 2x file ini lagi untuk menyalakan.
pause
exit /b 0
