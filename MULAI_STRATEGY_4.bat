@echo off
setlocal
title RBT FX - STRATEGY 4
rem ================================================================
rem  MULAI STRATEGY 4 - v9 OTOMATIS DARI GITHUB
rem  1. Folder strategy dicari otomatis di lokasi standar
rem  2. Kalau TIDAK ada: bat MENGUNDUH SELURUH REPO dari GitHub
rem     ke C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21 - tanpa perlu apa pun lagi
rem  3. Kalau folder SUDAH ada: bat UPDATE dulu dari GitHub,
rem     lalu menyalakan. Data login/state tidak pernah tertimpa.
rem  Token dibaca dari TOKEN.txt di sebelah file ini; kalau belum
rem  ada, diminta sekali lalu disimpan otomatis.
rem ================================================================

set "TOKEN="
if exist "%~dp0TOKEN.txt" set /p TOKEN=<"%~dp0TOKEN.txt"
if defined TOKEN goto tok_ok
echo Token GitHub belum ada - hanya sekali ini saja.
set /p "TOKEN=Paste token GitHub lalu tekan Enter: "
if not defined TOKEN goto tok_bad
echo %TOKEN%| findstr /B /C:"ghp_" /C:"github_pat_" >nul
if errorlevel 1 goto tok_bad
>"%~dp0TOKEN.txt" echo %TOKEN%
echo [OK] Token disimpan di TOKEN.txt - berikutnya tidak ditanya lagi.
goto tok_ok
:tok_bad
echo [X] Token tidak terbaca/salah format. Klik 2x file ini lagi.
echo Token dikirim bot Telegram, diawali ghp_.
echo.
pause
exit /b 1
:tok_ok
if defined TOKEN set "RBT_GH_TOKEN=%TOKEN%"

rem ---- [1/4] cari folder strategy yang sudah ada ----
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
if defined DIR goto ada_folder

rem ---- [2/4] tidak ketemu -> UNDUH OTOMATIS DARI GITHUB ----
set "DST=C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
echo Folder lokal tidak ada - MENGUNDUH dari GitHub ke %DST% ...
if not exist "C:\RBT\" mkdir "C:\RBT"
call :unduh "Sistem-Trading-Strategy-4-SNR-EMA13-EMA21" "%DST%"
if errorlevel 1 goto unduh_gagal
echo [OK] Unduhan selesai.
set "DIR=%DST%"
goto ada_folder

:unduh_gagal
echo [X] Unduhan GAGAL - cek internet/koneksi VPS.
echo Kalau folder strategy ternyata ada di tempat lain, seret ke sini:
set /p "LOK=Seret folder lalu tekan Enter (atau kosongkan utk batal): "
set "LOK=%LOK:"=%"
if not defined LOK goto gagal_input
for /d %%D in ("%LOK%\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%LOK%\*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%LOK%\*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
for /d %%D in ("%LOK%\*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
if exist "%LOK%\MULAI_SEMUA.bat" set "DIR=%LOK%"
if not defined DIR goto input_salah
>"%~dp0S4_LOKASI.txt" echo %LOK%
echo [OK] Lokasi disimpan: %DIR%
goto ada_folder

:input_salah
echo [X] Di folder yang diseret tidak ada MULAI_SEMUA.bat.
echo.
pause
exit /b 1

:gagal_input
echo Dibatalkan. Klik 2x file ini lagi untuk mencoba.
echo.
pause
exit /b 1

:ada_folder
rem ---- [3/4] folder ada: UPDATE dari GitHub dulu (data login aman) ----
cd /d "%DIR%"
echo Update dari GitHub: Sistem-Trading-Strategy-4-SNR-EMA13-EMA21 ...
call :unduh "Sistem-Trading-Strategy-4-SNR-EMA13-EMA21" "%DIR%"
if errorlevel 1 echo    Update dilewati (offline?) - memakai versi lokal.
rem ---- [4/4] nyalakan ----
if not exist "MULAI_SEMUA.bat" goto startdirect
echo Menyalakan STRATEGY 4 di %CD% ...
call "MULAI_SEMUA.bat"
goto selesai

:startdirect
set "PY="
python --version >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto pyok
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto pyok
echo [X] Python tidak ketemu di VPS ini.
echo Jalankan sekali: buka folder %CD% lalu klik 2x MULAI_SEMUA.bat di dalamnya.
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
echo Dashboard dinyalakan. Engine berjalan DI JENDELA INI - log hidup.
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

:unduh
rem args: %1 = nama repo, %2 = folder tujuan
set "USRC="
set "UZIP=%TEMP%\_rbt_dl.zip"
set "UDIR=%TEMP%\_rbt_dl"
if exist "%UZIP%" del "%UZIP%" >nul 2>nul
if exist "%UDIR%" rmdir /s /q "%UDIR%" >nul 2>nul
set "UURL=https://codeload.github.com/ributprasetyoaji/%~1/zip/refs/heads/main"
curl -L --retry 2 --ssl-no-revoke --silent -H "Authorization: Bearer %TOKEN%" -o "%UZIP%" "%UURL%"
if errorlevel 1 goto u_ps
goto u_chk
:u_ps
powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Headers @{Authorization='Bearer %TOKEN%'} -Uri '%UURL%' -OutFile '%UZIP%'}catch{exit 1}"
:u_chk
if not exist "%UZIP%" exit /b 1
for %%F in ("%UZIP%") do if %%~zF LSS 50000 exit /b 1
powershell -NoProfile -Command "try{Expand-Archive -Force -LiteralPath '%UZIP%' '%UDIR%'}catch{exit 1}"
if exist "%UDIR%\%~1-main" set "USRC=%UDIR%\%~1-main"
if defined USRC goto u_have
for /d %%D in ("%UDIR%\*") do if exist "%%D\MULAI_SEMUA.bat" if not defined USRC set "USRC=%%D"
if not defined USRC exit /b 1
:u_have
robocopy "%USRC%" "%~2" /E /XF cc_state.json cc_day.json cc_status.json CC_SIGNAL.csv s2_state.json s1_state.json MT5_PATH.txt TOKEN.txt /XD logs replay __pycache__ .git redist /NFL /NDL /NJH /NJS /NP
if errorlevel 8 exit /b 1
if not exist "%~2\MULAI_SEMUA.bat" exit /b 1
>"%~2\TOKEN.txt" echo %TOKEN%
if exist "%UDIR%" rmdir /s /q "%UDIR%" >nul 2>nul
if exist "%UZIP%" del "%UZIP%" >nul 2>nul
exit /b 0
