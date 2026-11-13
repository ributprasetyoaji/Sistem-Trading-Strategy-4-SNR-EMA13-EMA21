@echo off
setlocal
title RBT FX - STRATEGY 4 (update cepat + mulai)
cd /d "%~dp0"
set "TOKEN=GANTI_TOKEN_ANDA"
if exist "%~dp0TOKEN.txt" set /p TOKEN=<"%~dp0TOKEN.txt"
set "REPO=Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
echo ================================================================
echo    RBT FX - STRATEGY 4: UPDATE CEPAT + MULAI SEMUA
echo ================================================================
echo [1/2] Update dari GitHub (%REPO%) ...
set "UURL=https://codeload.github.com/%REPO%/zip/refs/heads/main"
if exist "_rbt_upd.zip" del "_rbt_upd.zip" >nul 2>nul
where curl >nul 2>nul
if errorlevel 1 goto upd_ps
curl -L --retry 2 --ssl-no-revoke --silent -H "Authorization: Bearer %TOKEN%" -o "_rbt_upd.zip" "%UURL%"
goto upd_chk
:upd_ps
powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Headers @{Authorization='Bearer %TOKEN%'} -Uri '%UURL%' -OutFile '_rbt_upd.zip'}catch{exit 1}"
:upd_chk
if not exist "_rbt_upd.zip" goto upd_skip
for %%F in (_rbt_upd.zip) do if %%~zF LSS 50000 goto upd_skip
powershell -NoProfile -Command "Expand-Archive -Force -Path '_rbt_upd.zip' -DestinationPath '_rbt_upd'"
set "USRC="
if exist "_rbt_upd\python\command_center.py" set "USRC=_rbt_upd"
for /d %%D in (_rbt_upd\*) do if not defined USRC if exist "%%D\python\command_center.py" set "USRC=%%D"
if defined USRC robocopy "%USRC%" . /E /NFL /NDL /NJH /NJS /NP >nul
:upd_clean
if exist "_rbt_upd.zip" del "_rbt_upd.zip" >nul 2>nul
if exist "_rbt_upd" rmdir /S /Q "_rbt_upd" >nul 2>nul
goto upd_done
:upd_skip
echo    Update dilewati (internet/token belum siap) - lanjut mulai.
:upd_done
echo [2/2] Mulai STRATEGY 4 ...
call "%~dp0MULAI_SEMUA.bat"
