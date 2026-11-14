@echo off
setlocal
title RBT FX - STRATEGY 4
rem ================================================================
rem  MULAI STRATEGY 4 - v15 LANGSUNG JALAN TANPA KOPI TOKEN
rem  - Token GitHub dicari DIAM-DIAM di 5 tempat: sebelah file ini,
rem    C:\RBT\TOKEN.txt, %APPDATA%\RBT_FX\gh_token.txt, folder
rem    strategy lain di C:\RBT, dan folder strategy -- TIDAK DITANYA.
rem  - Lokasi khusus (S4_LOKASI.txt) ikut dicari tiap kali mulai.
rem  - Token pernah dipaste? Disimpan permanen di 2 tempat --
rem    tidak akan pernah ditanya lagi.
rem  - Tanpa token pun tetap JALAN: pakai program lokal, update
rem    GitHub dilewati. Token cuma ditanya kalau folder strategy
rem    tidak ada DAN harus mengunduh dari GitHub.
rem  - Folder tidak ada: bat mengunduh seluruh repo dari GitHub
rem    ke C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21 secara otomatis.
rem ================================================================

set "DIR="
set "DIRF="
rem ---- [cari folder strategy dulu] ----
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
rem ---- [1b] lokasi khusus yg pernah diseret user (S4_LOKASI.txt) ----
set "LOK="
if exist "%~dp0S4_LOKASI.txt" set /p LOK=<"%~dp0S4_LOKASI.txt"
if defined LOK set "LOK=%LOK:"=%"
if defined LOK for /d %%D in ("%LOK%\*Strategy-4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
if defined LOK for /d %%D in ("%LOK%\*Strategy_4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
if defined LOK for /d %%D in ("%LOK%\*Strategy 4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
if defined LOK for /d %%D in ("%LOK%\*Strategy4*") do if exist "%%D\MULAI_SEMUA.bat" if not defined DIR set "DIR=%%D"
if defined LOK if exist "%LOK%\MULAI_SEMUA.bat" set "DIR=%LOK%"
if defined DIR goto ada_folder

rem ---- [2/4] tidak ketemu -> UNDUH OTOMATIS DARI GITHUB ----
rem ---- token dicari DIAM-DIAM di 5 tempat (v15) - TIDAK DITANYA ----
set "TOKEN="
if exist "%~dp0TOKEN.txt" set /p TOKEN=<"%~dp0TOKEN.txt"
if not defined TOKEN if exist "C:\RBT\TOKEN.txt" set /p TOKEN=<"C:\RBT\TOKEN.txt"
if not defined TOKEN if exist "%APPDATA%\RBT_FX\gh_token.txt" set /p TOKEN=<"%APPDATA%\RBT_FX\gh_token.txt"
for /d %%D in ("C:\RBT\*") do if exist "%%D\TOKEN.txt" if not defined TOKEN set /p TOKEN=<"%%D\TOKEN.txt"
if defined TOKEN goto unduh_langsung
echo Folder strategy tidak ada DAN token GitHub tidak ketemu di tempat biasa.
echo CARA PALING MUDAH: jalankan PASANG_BAT_PLUS_TOKEN.bat sekali --
echo token dipasang otomatis, TIDAK PERLU PASTE APA PUN.
echo Atau paste token GitHub sekali di bawah (disimpan permanen).
set /p "TOKEN=Paste token GitHub (Enter untuk batal): "
if not defined TOKEN goto gagal_input
if "%TOKEN:~30,1%"=="" goto tok_bad
>"%~dp0TOKEN.txt" echo %TOKEN%
if not exist "%APPDATA%\RBT_FX" mkdir "%APPDATA%\RBT_FX" >nul 2>nul
>"%APPDATA%\RBT_FX\gh_token.txt" echo %TOKEN%
echo [OK] Token GitHub disimpan di 2 tempat - TIDAK AKAN DITANYA LAGI.
:unduh_langsung
set "DST=C:\RBT\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
echo MENGUNDUH dari GitHub ke %DST% ...
if not exist "C:\RBT\" mkdir "C:\RBT"
call :unduh "Sistem-Trading-Strategy-4-SNR-EMA13-EMA21" "%DST%"
if errorlevel 1 goto unduh_gagal
echo [OK] Unduhan selesai.
set "DIR=%DST%"
goto ada_folder

:tok_bad
echo [X] Token terlalu pendek/salah. Paste token penuh yang diawali ghp_.
echo.
pause
exit /b 1

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
rem ---- token: dicari DIAM-DIAM di 5 tempat (v15) - TIDAK DITANYA ----
set "TOKEN="
if exist "%~dp0TOKEN.txt" set /p TOKEN=<"%~dp0TOKEN.txt"
if not defined TOKEN if exist "C:\RBT\TOKEN.txt" set /p TOKEN=<"C:\RBT\TOKEN.txt"
if not defined TOKEN if exist "%APPDATA%\RBT_FX\gh_token.txt" set /p TOKEN=<"%APPDATA%\RBT_FX\gh_token.txt"
for /d %%D in ("C:\RBT\*") do if exist "%%D\TOKEN.txt" if not defined TOKEN set /p TOKEN=<"%%D\TOKEN.txt"
if not defined TOKEN if exist "%DIR%\TOKEN.txt" set /p TOKEN=<"%DIR%\TOKEN.txt"
if defined TOKEN set "RBT_GH_TOKEN=%TOKEN%"
rem ---- update dari GitHub dulu (diam-diam dilewati kalau tanpa token/offline) ----
cd /d "%DIR%"
if defined TOKEN echo Update dari GitHub: Sistem-Trading-Strategy-4-SNR-EMA13-EMA21 ...
call :unduh "Sistem-Trading-Strategy-4-SNR-EMA13-EMA21" "%DIR%"
if errorlevel 1 echo    Update dilewati (tanpa token/offline) - memakai program lokal.
rem ---- nyalakan ----
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
rem ---- v11: matikan proses lama pemegang port 8082 (dashboard web S4).
rem     Kalau engine lama masih hidup, browser dapat halaman LAMA dan
rem     engine baru gagal pegang port. Dua cara (netstat+powershell),
rem     dua-duanya diam kalau tidak ada yang memegang port. ----
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8082" ^| findstr "LISTENING"') do taskkill /F /PID %%p >nul 2>&1
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8082 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessId -ne $PID -and ($_.CommandLine -like '*cc_qtdashboard*' -or $_.CommandLine -like '*cc_tkdashboard*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
wmic process where "CommandLine like '%%cc_qtdashboard%%' or CommandLine like '%%cc_tkdashboard%%'" delete >nul 2>&1
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
if not defined TOKEN exit /b 1
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
robocopy "%USRC%" "%~2" /E /XF cc_state.json cc_day.json cc_status.json CC_SIGNAL.csv s2_state.json s1_state.json MT5_PATH.txt TOKEN.txt s3_state.json s3_journal.jsonl s3_hist_*.json cc_heartbeat.json telegram_chat.txt telegram_token.txt pair_switch.json pair_lot.json /XD logs replay __pycache__ .git redist /NFL /NDL /NJH /NJS /NP
if errorlevel 8 exit /b 1
if not exist "%~2\MULAI_SEMUA.bat" exit /b 1
if defined TOKEN if not exist "%~2\TOKEN.txt" >"%~2\TOKEN.txt" echo %TOKEN%
if exist "%UDIR%" rmdir /s /q "%UDIR%" >nul 2>nul
if exist "%UZIP%" del "%UZIP%" >nul 2>nul
exit /b 0
