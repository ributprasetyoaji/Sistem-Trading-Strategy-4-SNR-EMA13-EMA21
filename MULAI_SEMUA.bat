@echo off

chcp 65001 >nul

rem ---------- TAMPILAN MATRIX (permintaan user): hijau di atas hitam
rem + font Consolas tinggi (registry utk jendela console baru;
rem "color 0A" langsung efektif di jendela sekarang).
color 0A
reg add "HKCU\Console" /v FaceName /t REG_SZ /d "Consolas" /f >nul 2>&1
reg add "HKCU\Console" /v FontSize /t REG_DWORD /d 0x0012000A /f >nul 2>&1
reg add "HKCU\Console" /v FontFamily /t REG_DWORD /d 0x36 /f >nul 2>&1
reg add "HKCU\Console" /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

title RBT FX // TRADING ALGO SYSTEM [STRATEGY 4] - MATRIX MODE

cd /d "%~dp0"



echo ================================================================

echo    R B T   F X   //   T R A D I N G   A L G O   S Y S T E M
echo    [ STRATEGY 4 ]   ::   M A T R I X   M O D E   ::

echo    PYTHON CORE ...... READY      SECURE LINK ...... GITHUB
echo    MARKET LINK ...... METATRADER 5 - AKUN LIVE/SIM OTOMATIS

echo ================================================================

echo.



rem ---------- [0/6] UPDATE CEPAT (zip ringan ~170KB; jalan juga bila
rem       file ini dipanggil LANGSUNG tanpa lewat RBT_FX_STRATEGYx.bat)
echo [0/6] Cek update program dari GitHub...
set "REPO=ributprasetyoaji/Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
set "TOKEN=GANTI_TOKEN_ANDA"
rem v4-template: token bisa ditaruh di file TOKEN.txt
rem (satu baris) di samping bat ini -- TIDAK ikut ke GitHub.
if exist "%~dp0TOKEN.txt" set /p TOKEN=<"%~dp0TOKEN.txt"
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
if exist "_rbt_upd" rmdir /s /q "_rbt_upd" >nul 2>nul
powershell -NoProfile -Command "try{Expand-Archive -Force -LiteralPath '_rbt_upd.zip' '_rbt_upd'}catch{exit 1}"
set "USRC="
if exist "_rbt_upd\python\command_center.py" set "USRC=_rbt_upd"
if defined USRC goto upd_copy
for /d %%D in (_rbt_upd\*) do if not defined USRC if exist "%%D\python\command_center.py" set "USRC=%%D"
:upd_copy
if not defined USRC goto upd_clean
robocopy "%USRC%" "." /E /XF cc_state.json cc_day.json cc_status.json CC_SIGNAL.csv s2_state.json s1_state.json s3_state.json s3_journal.jsonl s3_hist_*.json MT5_PATH.txt /XD logs replay __pycache__ .git redist /NFL /NDL /NJH /NJS /NP
:upd_clean
if exist "_rbt_upd" rmdir /s /q "_rbt_upd" >nul 2>nul
if exist "_rbt_upd.zip" del "_rbt_upd.zip" >nul 2>nul
:upd_skip
echo    Update check selesai.
echo.

echo [1/5] Cari Python (beberapa cara)...

set "PY="

python --version >nul 2>&1

if not errorlevel 1 set "PY=python"

if defined PY goto py_found

py -3 --version >nul 2>&1

if not errorlevel 1 set "PY=py -3"

if defined PY goto py_found

python3 --version >nul 2>&1

if not errorlevel 1 set "PY=python3"

if defined PY goto py_found

for /d %%p in ("%LOCALAPPDATA%\Programs\Python\Python*") do if exist "%%p\python.exe" set "PY=%%p\python.exe"

if defined PY goto py_found

for /d %%p in ("C:\Python*") do if exist "%%p\python.exe" set "PY=%%p\python.exe"

if defined PY goto py_found



echo    Python belum ketemu - mencoba install OTOMATIS via winget...

where winget >nul 2>&1

if errorlevel 1 goto py_manual

winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements

echo    Menunggu 10 detik pendaftaran Python...

ping -n 11 127.0.0.1 >nul

py -3 --version >nul 2>&1

if not errorlevel 1 set "PY=py -3"

if defined PY goto py_found

python --version >nul 2>&1

if not errorlevel 1 set "PY=python"

if defined PY goto py_found



:py_manual

echo.

echo    ==============================================================

echo    PYTHON BELUM TERPASANG - lakukan 1x saja (5 menit):

echo      1. Browser sudah dibuka ke halaman download Python

echo      2. Klik tombol Download Python

echo      3. Jalankan installer-nya

echo      4. CENTANG "Add python.exe to PATH" (layar pertama!) - WAJIB

echo      5. Klik Install Now, tunggu selesai

echo      Lalu klik 2x MULAI_SEMUA.bat lagi.

echo    ==============================================================

start "" https://www.python.org/downloads/

pause

exit /b 1



:py_found

echo    Python OK: %PY%
REM pythonw = GUI TANPA console hitam (hanya jendela dashboard)
set "PYW="
for %%P in (%PY%) do if exist "%%~dpPpythonw.exe" set "PYW=%%~dpPpythonw.exe"
if not defined PYW if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not defined PYW set "PYW=%PY%"

echo.



echo [2/5] Cek paket MetaTrader5 + websockets (install hanya bila belum ada)...

%PY% -c "import MetaTrader5, websockets" >nul 2>&1
if errorlevel 1 %PY% -m pip install MetaTrader5 websockets >nul 2>&1

if errorlevel 1 %PY% -m pip install --user MetaTrader5 websockets >nul 2>&1

REM [2b] PySide6 utk dashboard Qt modern - kalau gagal, otomatis pakai Tk
%PY% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo      Memasang PySide6 - dashboard Qt modern, sekali saja ~50MB...
  %PY% -m pip install --no-input --timeout 60 PySide6-Essentials >nul 2>&1
  if errorlevel 1 %PY% -m pip install --no-input --timeout 60 --user PySide6-Essentials >nul 2>&1
)

%PY% -c "import MetaTrader5" >nul 2>&1

if errorlevel 1 (

    echo    PERINGATAN: paket MetaTrader5 gagal dipasang - internet belum siap?

    echo    Robot tetap jalan MODE SIMULASI. Jalankan lagi file ini nanti.

) else (

    echo    OK.

)



echo [3/5] Panggil MT5...

set "MT5EXE="
REM v3.44 PILIH TERMINAL YANG BENAR (VPS bisa berisi beberapa MT5):
REM kalau file MT5_PATH.txt berisi path terminal64.exe, itu yang dipakai.
REM Engine juga mengingat terminal yang dipakai ke file ini (sticky).
if not exist "%~dp0MT5_PATH.txt" >"%~dp0MT5_PATH.txt" echo # GANTI baris ini dgn path terminal64.exe (contoh: C:\Program Files\BrokerAnda\terminal64.exe)
set "MT5EXE="
if exist "%~dp0MT5_PATH.txt" set /p MT5EXE=<"%~dp0MT5_PATH.txt"
if defined MT5EXE if not exist "%MT5EXE%" set "MT5EXE="
if defined MT5EXE goto mt5_have

for /d %%p in ("%ProgramFiles%\*MetaTrader*") do if exist "%%p\terminal64.exe" set "MT5EXE=%%p\terminal64.exe"

for /d %%p in ("%ProgramFiles%\*MT5*") do if exist "%%p\terminal64.exe" set "MT5EXE=%%p\terminal64.exe"

for /d %%p in ("%ProgramFiles(x86)%\*MetaTrader*") do if exist "%%p\terminal64.exe" set "MT5EXE=%%p\terminal64.exe"

for /d %%p in ("%ProgramFiles(x86)%\*MT5*") do if exist "%%p\terminal64.exe" set "MT5EXE=%%p\terminal64.exe"



:mt5_have
tasklist /FI "IMAGENAME eq terminal64.exe" 2>nul | find /I "terminal64.exe" >nul

if not errorlevel 1 goto mt5_ready

if "%MT5EXE%"=="" goto mt5_missing

echo    Menjalankan: %MT5EXE%

start "" "%MT5EXE%"

echo    Menunggu MT5 siap - maksimal 25 detik...

set /a tries=0

:waitloop

ping -n 2 127.0.0.1 >nul

tasklist /FI "IMAGENAME eq terminal64.exe" 2>nul | find /I "terminal64.exe" >nul

if not errorlevel 1 goto mt5_ready

set /a tries+=1

if %tries% LSS 25 goto waitloop

echo    MT5 lambat membuka - lanjut. Robot konek OTOMATIS begitu MT5 siap.

goto mt5_done

:mt5_missing
set "MT4EXE="
for /d %%p in ("%ProgramFiles%\*MetaTrader 4*") do if exist "%%p\terminal.exe" set "MT4EXE=%%p\terminal.exe"
for /d %%p in ("%ProgramFiles(x86)%\*MetaTrader 4*") do if exist "%%p\terminal.exe" set "MT4EXE=%%p\terminal.exe"
if defined MT4EXE goto mt4_found
echo    MT5/MT4 tidak ketemu di lokasi standar. Kalau terpasang di
echo    folder lain, buka manual lalu login. Robot konek otomatis nanti.
goto mt5_done
:mt4_found
echo    MT5 tidak ada, tapi MT4 ditemukan: %MT4EXE%
echo    Wajib: pasang EA RBT_FX_Bridge di chart + AutoTrading ON
echo    (langkah lengkap: MT4_SETUP.md di folder ini).
start "" "%MT4EXE%"
echo    Menunggu MT4 siap - maksimal 25 detik...
set /a m4tries=0
:mt4_waitloop
ping -n 2 127.0.0.1 >nul
tasklist /FI "IMAGENAME eq terminal.exe" 2>nul | find /I "terminal.exe" >nul
if not errorlevel 1 goto mt4_ready
set /a m4tries+=1
if %m4tries% LSS 25 goto mt4_waitloop
:mt4_ready
echo    MT4 siap.
goto mt5_done

:mt5_ready
echo    MT5 siap.
:mt5_done

echo    CATATAN: kalau MT5 terbuka tapi belum login, login saja di jendela

echo    MT5 - robot konek OTOMATIS dalam 30 detik (SIM-MODE jadi CONNECTED).

echo.



echo [4/5] Nyalakan engine + buka DASHBOARD TRADING ALGO SYSTEM (jendela aplikasi)...
REM Buka firewall Windows utk dashboard STRATEGY 4 (akses dari luar VPS).
REM Kalau bukan admin, langkah ini dilewati senyap - localhost tetap jalan.
netsh advfirewall firewall add rule name="RBT FX STRATEGY 4 Dashboard" dir=in action=allow protocol=TCP localport=8082 >nul 2>&1

REM Browser dibuka setelah 12 dtk (dashboard S2 sudah pasti bind)
REM (dashboard S2 bind di awal -- browser dibuka setelah 12 dtk aman)
set "DASH=python\cc_tkdashboard.py"
%PY% -c "import PySide6" >nul 2>&1
if not errorlevel 1 set "DASH=python\cc_qtdashboard.py"
start "RBT FX DASHBOARD" %PYW% %DASH% --port 8082

Rem v-fix: engine jalan DI JENDELA INI (permintaan user: tidak ada
rem jendela python kedua yang kosong/tak berfungsi). Log engine tampil
rem langsung di jendela ini.
echo    Engine berjalan DI JENDELA INI -- log hidup muncul di bawah.
echo    PENTING: JANGAN TUTUP jendela ini selama trading --
echo    kalau ditutup, dashboard jadi DATA BEKU (tidak hidup).
echo    Tekan Ctrl+C untuk menghentikan engine.
echo.
if defined TOKEN set "RBT_GH_TOKEN=%TOKEN%"
%PY% -u python\command_center.py
echo.
echo [5/5] Engine berhenti (dashboard akan menampilkan DATA BEKU).
echo    Jalankan lagi bat ini untuk menyalakan kembali.
pause
