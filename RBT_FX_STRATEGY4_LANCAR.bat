@echo off

rem ---------- TAMPILAN MATRIX (dari bat lama user): hijau di atas hitam
rem + font Consolas tinggi (registry utk jendela console baru;
rem "color 0A" langsung efektif di jendela sekarang).
color 0A
reg add "HKCU\Console" /v FaceName /t REG_SZ /d "Consolas" /f >nul 2>&1
reg add "HKCU\Console" /v FontSize /t REG_DWORD /d 0x0012000A /f >nul 2>&1
reg add "HKCU\Console" /v FontFamily /t REG_DWORD /d 0x36 /f >nul 2>&1
reg add "HKCU\Console" /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1
chcp 65001 >nul
title RBT FX // TRADING ALGO - STRATEGY 4 - MATRIX MODE
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM ================================================================
REM   RBT FX - STRATEGY 4 - FILE TUNGGAL (adaptasi bat lama user)
REM   Download file ini saja. Double-click -> otomatis:
REM   [0] Python 3.8 siap (installer dari repo bila belum ada)
REM   [0b] dependency + PySide (Qt5 utk Server2012/Win7 + jembatan)
REM   [1] Program terbaru diunduh dari GitHub (S4)
REM   [2] File program diperbarui (data trading TIDAK disentuh)
REM   [3] Robot jalan: MULAI_SEMUA.bat (engine + dashboard)
REM ================================================================
set "REPO=ributprasetyoaji/Sistem-Trading-Strategy-4-SNR-EMA13-EMA21"
set "BRANCH=main"
rem TOKEN TIDAK tertanam di file ini (aman tersimpan di repo GitHub).
rem Cara pakai token: buat file TOKEN.txt di sebelah bat ini berisi
rem token (atau jalankan PERBAIKI_TOKEN.bat). Ganti token baru = ganti
rem isi TOKEN.txt saja, bat TIDAK perlu diubah. Tanpa TOKEN.txt pun
rem tetap jalan: semua unduhan dari repo PUBLIC (tanpa token).
set "TOKEN="
if exist "%~dp0TOKEN.txt" set /p TOKEN=<"%~dp0TOKEN.txt"
echo %TOKEN%| findstr /B /C:"ghp_" /C:"github_pat_" >nul
if errorlevel 1 set "TOKEN="
set "FOLDER=RBT-FX-STRATEGY4"

echo ================================================================
echo    RBT FX TRADING ALGO SYSTEM [STRATEGY 4]
echo    Repo: %REPO% (%BRANCH%)
echo ================================================================
echo.

REM ---------- [0/3] BOOTSTRAP PYTHON (dari bat lama user) ----------
echo [0/3] Cek Python 3...
set "PYEXE="
for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
if not defined PYEXE for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
if defined PYEXE echo !PYEXE!| find /i "WindowsApps" >nul
if not errorlevel 1 set "PYEXE="
if defined PYEXE if not exist "!PYEXE!" set "PYEXE="
if not defined PYEXE goto py_dl
for %%P in ("!PYEXE!") do set "PYDIR=%%~dpP"
set "PATH=!PYDIR!;!PYDIR!Scripts;%PATH%"
echo    Python OK: !PYEXE!
goto py_done
:py_dl
set "PYINST=%TEMP%\rbt_python_setup.exe"
set "PYURL1=https://raw.githubusercontent.com/%REPO%/main/redist/python-3.8.10-amd64.exe"
set "PYURL2=https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe"
if exist "%PYINST%" del "%PYINST%" >nul 2>nul
echo    Python belum terpasang - unduh installer dari repo GitHub Anda...
where curl >nul 2>nul
if errorlevel 1 goto py_dlps
curl -L --retry 3 --ssl-no-revoke --silent --show-error -o "%PYINST%" "%PYURL1%"
goto py_dlchk
:py_dlps
powershell -NoProfile -Command "try{$ProgressPreference='SilentlyContinue';[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Uri '%PYURL1%' -OutFile '%PYINST%'}catch{exit 1}"
:py_dlchk
if exist "%PYINST%" for %%F in ("%PYINST%") do if %%~zF GEQ 10000000 goto py_vfy
echo    Sumber 1 gagal - coba python.org resmi...
powershell -NoProfile -Command "try{$ProgressPreference='SilentlyContinue';[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Uri '%PYURL2%' -OutFile '%PYINST%'}catch{exit 1}"
if exist "%PYINST%" for %%F in ("%PYINST%") do if %%~zF GEQ 10000000 goto py_vfy
goto py_bad
:py_vfy
powershell -NoProfile -Command "try{$b=[IO.File]::ReadAllBytes('%PYINST%');if($b.Length -ge 10000000 -and [Text.Encoding]::ASCII.GetString($b[0..1]) -eq 'MZ'){exit 0}else{exit 1}}catch{exit 1}"
if errorlevel 1 goto py_bad
echo    Menginstall Python 3.8 diam-diam (1-2 menit, sekali saja)...
"%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Include_tcltk=1
set "PYNEW=%LOCALAPPDATA%\Programs\Python\Python38\python.exe"
set /a PYN=0
:py_wait
if exist "%PYNEW%" goto py_ready
ping -n 4 127.0.0.1 >nul
set /a PYN+=1
if %PYN% LSS 60 goto py_wait
goto py_bad
:py_ready
set "PATH=%LOCALAPPDATA%\Programs\Python\Python38;%LOCALAPPDATA%\Programs\Python\Python38\Scripts;%LOCALAPPDATA%\Programs\Python\Launcher;%PATH%"
set "PYEXE=%PYNEW%"
echo    Python 3.8 TERPASANG - lanjut otomatis.
goto py_done
:py_bad
echo.
echo    [X] GAGAL menyiapkan Python otomatis. Cek internet/antivirus lalu
echo        install Python 3.8.10 manual dari python.org, lalu jalankan lagi.
echo.
pause
exit /b 1
:py_done
echo.

REM ---------- [0b/3] DEPENDENCY (pandas dll) - tambahan utk S4 ----------
echo [0b/3] Cek dependency (pandas/numpy/requests/websockets)...
%PYEXE% -c "import pandas" >nul 2>nul
if not errorlevel 1 goto dep_ok
%PYEXE% -m pip install -q --disable-pip-version-check pandas numpy requests websockets
%PYEXE% -c "import pandas" >nul 2>nul
if not errorlevel 1 goto dep_ok
%PYEXE% -m pip install --disable-pip-version-check pandas numpy requests websockets
%PYEXE% -c "import pandas" >nul 2>nul
if not errorlevel 1 goto dep_ok
%PYEXE% -m pip install --user --disable-pip-version-check pandas numpy requests websockets
%PYEXE% -c "import pandas" >nul 2>nul
if not errorlevel 1 goto dep_ok
goto dep_bad
:dep_ok
echo    Dependency OK.
echo.

REM ---------- [0c/3] DASHBOARD QT (PySide6 / PySide2+jembatan) ----------
echo [0c/3] Cek dashboard Qt (PySide)...
set "QTVER=6"
ver | findstr /C:"6.1" >nul 2>nul
if not errorlevel 1 set "QTVER=5"
ver | findstr /C:"6.2" >nul 2>nul
if not errorlevel 1 set "QTVER=5"
ver | findstr /C:"6.3" >nul 2>nul
if not errorlevel 1 set "QTVER=5"
set "QTBRIDGE="
if "%QTVER%"=="5" goto pyside2_only
%PYEXE% -c "import PySide6" >nul 2>nul
if not errorlevel 1 goto pyside_ok
echo     PySide6 belum ada - mencoba memasang (Win10/11)...
%PYEXE% -m pip install -q --disable-pip-version-check PySide6
%PYEXE% -c "import PySide6" >nul 2>nul
if not errorlevel 1 goto pyside_ok
:pyside2_only
echo     Memasang PySide2 (Qt5 - dukungan Server2012/Win7)...
%PYEXE% -m pip install -q --disable-pip-version-check PySide2
%PYEXE% -c "import PySide2.QtWidgets" >nul 2>nul
if not errorlevel 1 goto pyside_bridge
%PYEXE% -m pip install --disable-pip-version-check PySide2
%PYEXE% -c "import PySide2.QtWidgets" >nul 2>nul
if not errorlevel 1 goto pyside_bridge
echo [!] PySide tidak tersedia - dashboard dipakai lewat Tk bawaan.
goto pyside_done
:pyside_bridge
set "QTBRIDGE=1"
goto pyside_ok
:pyside_ok
echo    PySide siap.
:pyside_done
echo.

REM ---------- [1/3] download program terbaru (dari bat lama user) ----------
echo [1/3] Cek program terbaru dari GitHub (S4)...
set "DLURL=https://codeload.github.com/%REPO%/zip/refs/heads/%BRANCH%"
where curl >nul 2>nul
if errorlevel 1 goto dl_ps
curl -L --retry 3 --ssl-no-revoke --silent --show-error -o "_rbt.zip" "%DLURL%"
goto dl_check
:dl_ps
echo    curl tidak ada di Windows ini - pakai PowerShell...
powershell -NoProfile -Command "try{$ProgressPreference='SilentlyContinue';[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Uri '%DLURL%' -OutFile '_rbt.zip'}catch{exit 1}"
:dl_check
if exist "_rbt.zip" for %%F in (_rbt.zip) do if %%~zF GEQ 1000 goto dl_ok
echo    Coba metode ke-2: PowerShell TLS 1.2...
powershell -NoProfile -Command "try{$ProgressPreference='SilentlyContinue';[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Uri '%DLURL%' -OutFile '_rbt.zip'}catch{exit 1}"
:dl_ok
if not exist "_rbt.zip" goto dl_fail
for %%F in (_rbt.zip) do if %%~zF LSS 1000 goto dl_fail
call :pkcheck
if not errorlevel 1 goto pk_ok
echo    File terunduh BUKAN zip valid - coba server cadangan 1: github.com...
set "MURL=https://github.com/%REPO%/archive/refs/heads/%BRANCH%.zip"
del _rbt.zip >nul 2>&1
powershell -NoProfile -Command "try{$ProgressPreference='SilentlyContinue';[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Uri '%MURL%' -OutFile '_rbt.zip'}catch{exit 1}"
call :pkcheck
if not errorlevel 1 goto pk_ok
echo    Coba server cadangan 2: api.github.com...
set "MURL=https://api.github.com/repos/%REPO%/zipball/%BRANCH%"
del _rbt.zip >nul 2>&1
powershell -NoProfile -Command "try{$ProgressPreference='SilentlyContinue';[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Uri '%MURL%' -OutFile '_rbt.zip'}catch{exit 1}"
call :pkcheck
if not errorlevel 1 goto pk_ok
goto dl_fail2
:pk_ok

REM ---------- [2/3] ekstrak + perbarui program (dari bat lama user) ----------
echo [2/3] Memperbarui file program... (data trading TIDAK disentuh)
if exist _rbt_tmp rmdir /s /q _rbt_tmp
ping -n 2 127.0.0.1 >nul
powershell -NoProfile -Command "try { Expand-Archive -Force _rbt.zip _rbt_tmp } catch { exit 1 }"
call :findsrc
if defined SRC goto ex_ok
echo    Ekstrak metode ke-2: tar...
if exist _rbt_tmp rmdir /s /q _rbt_tmp
mkdir _rbt_tmp
tar -xf _rbt.zip -C _rbt_tmp >nul 2>nul
call :findsrc
if defined SRC goto ex_ok
echo    Ekstrak metode ke-3: Python zipfile...
%PYEXE% -c "import zipfile;zipfile.ZipFile('_rbt.zip').extractall('_rbt_tmp')" >nul 2>nul
call :findsrc
if defined SRC goto ex_ok
goto dl_fail2
:ex_ok
robocopy "!SRC!\python" "%FOLDER%\python" /E /XF cc_state.json cc_day.json cc_status.json CC_SIGNAL.csv s2_state.json s3_state.json s3_journal.jsonl s3_hist_*.json cc_heartbeat.json pair_switch.json pair_lot.json MT5_PATH.txt /XD logs replay __pycache__ .git PySide6 /NFL /NDL /NJH /NJS /NP
if errorlevel 8 goto dl_fail
robocopy "!SRC!" "%FOLDER%" MULAI_SEMUA.bat /NFL /NDL /NJH /NJS /NP >nul
rmdir /s /q _rbt_tmp >nul 2>&1
del _rbt.zip >nul 2>&1
if not exist "%FOLDER%\python\command_center.py" goto dl_fail

REM ---------- jembatan PySide6->PySide2 (Server2012/Win7) ----------
if not defined QTBRIDGE goto bridge_skip
echo     Memasang jembatan PySide6->PySide2 (dashboard jalan via Qt5)...
mkdir "%FOLDER%\python\PySide6" >nul 2>nul
mkdir "%FOLDER%\PySide6" >nul 2>nul
>"%FOLDER%\PySide6\__init__.py" echo import PySide2 as _p2
>>"%FOLDER%\PySide6\__init__.py" echo from PySide2.QtCore import *
>>"%FOLDER%\PySide6\__init__.py" echo from PySide2.QtGui import *
>>"%FOLDER%\PySide6\__init__.py" echo from PySide2.QtWidgets import *
>"%FOLDER%\PySide6\QtCore.py" echo from PySide2.QtCore import *
>"%FOLDER%\PySide6\QtGui.py" echo from PySide2.QtGui import *
>>"%FOLDER%\PySide6\QtGui.py" echo try:
>>"%FOLDER%\PySide6\QtGui.py" echo     QGuiApplication.exec = QGuiApplication.exec_
>>"%FOLDER%\PySide6\QtGui.py" echo except Exception:
>>"%FOLDER%\PySide6\QtGui.py" echo     pass
>"%FOLDER%\PySide6\QtWidgets.py" echo from PySide2.QtWidgets import *
>>"%FOLDER%\PySide6\QtWidgets.py" echo try:
>>"%FOLDER%\PySide6\QtWidgets.py" echo     QApplication.exec = QApplication.exec_
>>"%FOLDER%\PySide6\QtWidgets.py" echo     QCoreApplication.exec = QCoreApplication.exec_
>>"%FOLDER%\PySide6\QtWidgets.py" echo except Exception:
>>"%FOLDER%\PySide6\QtWidgets.py" echo     pass
>"%FOLDER%\python\PySide6\__init__.py" echo import PySide2 as _p2
>>"%FOLDER%\python\PySide6\__init__.py" echo from PySide2.QtCore import *
>>"%FOLDER%\python\PySide6\__init__.py" echo from PySide2.QtGui import *
>>"%FOLDER%\python\PySide6\__init__.py" echo from PySide2.QtWidgets import *
>>"%FOLDER%\python\PySide6\__init__.py" echo __version__ = getattr(_p2, "__version__", "5.15.2")
>"%FOLDER%\python\PySide6\QtCore.py" echo from PySide2.QtCore import *
>"%FOLDER%\python\PySide6\QtGui.py" echo from PySide2.QtGui import *
>>"%FOLDER%\python\PySide6\QtGui.py" echo try:
>>"%FOLDER%\python\PySide6\QtGui.py" echo     QGuiApplication.exec = QGuiApplication.exec_
>>"%FOLDER%\python\PySide6\QtGui.py" echo except Exception:
>>"%FOLDER%\python\PySide6\QtGui.py" echo     pass
>"%FOLDER%\python\PySide6\QtWidgets.py" echo from PySide2.QtWidgets import *
>>"%FOLDER%\python\PySide6\QtWidgets.py" echo try:
>>"%FOLDER%\python\PySide6\QtWidgets.py" echo     QApplication.exec = QApplication.exec_
>>"%FOLDER%\python\PySide6\QtWidgets.py" echo     QCoreApplication.exec = QCoreApplication.exec_
>>"%FOLDER%\python\PySide6\QtWidgets.py" echo except Exception:
>>"%FOLDER%\python\PySide6\QtWidgets.py" echo     pass
%PYEXE% -c "import sys;sys.path.insert(0,'%FOLDER%\python');import PySide6.QtWidgets" >nul 2>nul
if not errorlevel 1 goto bridge_ok
echo [!] Jembatan gagal - dashboard dipakai lewat Tk bawaan.
set "QTBRIDGE="
goto bridge_skip
:bridge_ok
echo    Jembatan Qt OK.
:bridge_skip
rem ---- pythonw tersedia di folder (fix deteksi PYW di MULAI_SEMUA.bat) ----
for %%P in ("%PYEXE%") do if exist "%%~dpPpythonw.exe" copy /y "%%~dpPpythonw.exe" "%FOLDER%\pythonw.exe" >nul 2>nul
if defined TOKEN >"%FOLDER%\TOKEN.txt" echo %TOKEN%

REM ---------- [3/3] jalankan robot (persis bat lama user) ----------
echo [3/3] Menjalankan RBT FX TRADING ALGO SYSTEM [STRATEGY 4]... (dashboard jendela aplikasi)
echo.
cd /d "%FOLDER%"
call MULAI_SEMUA.bat
goto end

:pkcheck
powershell -NoProfile -Command "try{$b=[IO.File]::ReadAllBytes('_rbt.zip');if($b.Length -lt 4 -or [Text.Encoding]::ASCII.GetString($b[0..1]) -ne 'PK'){exit 1}}catch{exit 1}"
goto :eof
:findsrc
set "SRC="
if exist "_rbt_tmp\python\command_center.py" set "SRC=_rbt_tmp"
if defined SRC goto :eof
for /d %%D in (_rbt_tmp\*) do if not defined SRC if exist "%%D\python\command_center.py" set "SRC=%%D"
if defined SRC goto :eof
goto :eof

:dl_fail2
echo.
echo    --- DIAGNOSTIK FILE ZIP ---
if exist "_rbt.zip" for %%F in (_rbt.zip) do echo    Ukuran: %%~zF byte
:dl_fail
if exist _rbt.zip del _rbt.zip >nul 2>&1
if exist _rbt_tmp rmdir /s /q _rbt_tmp >nul 2>&1
echo.
echo    [X] GAGAL mengambil/menyiapkan program (semua metode dicoba).
echo        1. Internet nyambung? (tes buka youtube.com di browser)
echo        2. Antivirus/Defender memblokir? - izinkan file ini
echo        3. FOTO LAYAR INI selengkapnya lalu kirim untuk bantuan.
pause
exit /b 1

:dep_bad
echo.
echo    [X] Dependency (pandas) gagal dipasang. Cek internet VPS lalu
echo        klik 2x file ini lagi.
pause
exit /b 1

:end
endlocal
exit /b 0
