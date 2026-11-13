@echo off
setlocal enableextensions
title RBT FX - PERBAIKI SEMUA (token + update + jalan)
cd /d "%~dp0"

rem =================================================================
rem  ALAT PERBAIKAN 1 KLIK - jalankan 1x:
rem   [A] Ganti token GitHub yang MATI di dalam semua file .bat lama
rem   [B] Pasang TOKEN.txt di tiap folder strategy (sistem baru)
rem   [C] Update semua strategy ke versi TERBARU dari GitHub
rem   [D] Opsi langsung menjalankan semua strategy
rem  CATATAN: tutup dulu semua jendela trading/dashboard sebelum jalan.
rem =================================================================

rem --- ambil token: TOKEN.txt di sebelah file ini, kalau tidak ada minta paste ---
set "TOKEN="
if exist "%~dp0TOKEN.txt" set /p TOKEN=<"%~dp0TOKEN.txt"
if defined TOKEN goto tok_ok
echo   Buka pesan Telegram dari bot, lalu COPY token GitHub
echo   (baris di bawah tulisan TOKEN BARU, diawali ghp_).
set /p TOKEN="   PASTE token di sini lalu tekan Enter: "
if not defined TOKEN goto tok_bad
echo %TOKEN%| findstr /B /C:"ghp_" /C:"github_pat_" >nul
if errorlevel 1 goto tok_bad
goto tok_ok
:tok_bad
echo.
echo   [X] Token tidak terbaca/salah. Klik 2x file ini lagi dan ulangi.
echo.
pause
exit /b 1
:tok_ok
if exist "%~dp0python\command_center.py" >"%~dp0TOKEN.txt" echo %TOKEN%
echo ================================================================
echo    RBT FX - PERBAIKI SEMUA
echo    Token dipasang + semua strategy di-update ke versi terbaru
echo ================================================================
echo.

set "N=0"
set "OKCNT=0"
set "F1="
set "F2="
set "F3="
set "F4="

rem ---- lokasi yang dicek: sebelah file ini, C:\RBT, Desktop, Downloads ----
for %%B in ("%~dp0." "C:\RBT" "%USERPROFILE%\Desktop" "%USERPROFILE%\Downloads") do call :BASE "%%~B"

echo.
echo ================================================================
echo    SELESAI.  Folder strategy ketemu: %N%   sukses update: %OKCNT%
echo ================================================================
if %N%==0 (
  echo.
  echo   [X] Tidak ada folder Sistem-Trading-Strategy yang ketemu.
  echo       Taruh file ini di folder C:\RBT  lalu klik 2x lagi.
  echo.
)
if %OKCNT%==0 if not %N%==0 (
  echo   [X] Ada folder tapi update GAGAL semua - cek internet/token,
  echo       lalu klik 2x file ini lagi.
  echo.
)
choice /C YN /N /M "Jalankan SEMUA strategy sekarang?  [Y]=ya / [T]=tidak : "
if errorlevel 2 goto done
echo.
echo   Menyalakan semua strategy - masing-masing 1 jendela...
if defined F1 start "RBT FX STRATEGY 1" /D "%F1%" cmd /c MULAI_SEMUA.bat
ping -n 6 127.0.0.1 >nul
if defined F2 start "RBT FX STRATEGY 2" /D "%F2%" cmd /c MULAI_SEMUA.bat
ping -n 6 127.0.0.1 >nul
if defined F3 start "RBT FX STRATEGY 3" /D "%F3%" cmd /c MULAI_SEMUA.bat
ping -n 6 127.0.0.1 >nul
if defined F4 start "RBT FX STRATEGY 4" /D "%F4%" cmd /c MULAI_SEMUA.bat
echo   Semua yang ketemu sudah dinyalakan. JANGAN tutup jendelanya.
:done
echo.
pause
exit /b 0

:BASE
if not exist "%~1" goto :eof
call :FIXTOKENS "%~1"
if exist "%~1\Sistem-Trading-Strategy-1" call :ONE "%~1\Sistem-Trading-Strategy-1" "Sistem-Trading-Strategy-1" "STRATEGY 1" 1
if exist "%~1\Sistem-Trading-Strategy-1-main" call :ONE "%~1\Sistem-Trading-Strategy-1-main" "Sistem-Trading-Strategy-1" "STRATEGY 1" 1
if exist "%~1\Sistem-Trading-Strategy-2" call :ONE "%~1\Sistem-Trading-Strategy-2" "Sistem-Trading-Strategy-2" "STRATEGY 2" 2
if exist "%~1\Sistem-Trading-Strategy-2-main" call :ONE "%~1\Sistem-Trading-Strategy-2-main" "Sistem-Trading-Strategy-2" "STRATEGY 2" 2
if exist "%~1\Sistem-Trading-Strategy-3" call :ONE "%~1\Sistem-Trading-Strategy-3" "Sistem-Trading-Strategy-3" "STRATEGY 3" 3
if exist "%~1\Sistem-Trading-Strategy-3-main" call :ONE "%~1\Sistem-Trading-Strategy-3-main" "Sistem-Trading-Strategy-3" "STRATEGY 3" 3
if exist "%~1\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21" call :ONE "%~1\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21" "Sistem-Trading-Strategy-4-SNR-EMA13-EMA21" "STRATEGY 4" 4
if exist "%~1\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main" call :ONE "%~1\Sistem-Trading-Strategy-4-SNR-EMA13-EMA21-main" "Sistem-Trading-Strategy-4-SNR-EMA13-EMA21" "STRATEGY 4" 4
goto :eof

:ONE
set /a N+=1
set "F%~4=%~1"
echo.
echo ---- %~3 : %~1 ----
>"%~1\TOKEN.txt" echo %TOKEN%
echo   [OK] TOKEN.txt dipasang di folder ini.
call :FIXTOKENS "%~1"
call :UPDATE "%~1" "%~2"
goto :eof

:FIXTOKENS
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t='%TOKEN%'; $fs=Get-ChildItem -LiteralPath '%~1' -Filter '*.bat' -ErrorAction SilentlyContinue; foreach($f in $fs){ $c=Get-Content -Raw -LiteralPath $f.FullName; if(($c -match 'github_pat_[A-Za-z0-9_]{20,}') -or ($c -match 'ghp_[A-Za-z0-9]{30,}')){ $c=$c -replace 'github_pat_[A-Za-z0-9_]{20,}',$t -replace 'ghp_[A-Za-z0-9]{30,}',$t; Set-Content -LiteralPath $f.FullName -Value $c -NoNewline; Write-Output ('   [OK] token lama diganti di: ' + $f.Name) } }"
goto :eof

:UPDATE
pushd "%~1"
echo   [1/2] Unduh versi terbaru: %~2 ...
set "UURL=https://codeload.github.com/ributprasetyoaji/%~2/zip/refs/heads/main"
if exist "_rbt_upd.zip" del "_rbt_upd.zip" >nul 2>nul
where curl >nul 2>nul
if errorlevel 1 goto u_ps
curl -L --retry 2 --ssl-no-revoke --silent -H "Authorization: Bearer %TOKEN%" -o "_rbt_upd.zip" "%UURL%"
goto u_chk
:u_ps
powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -UseBasicParsing -Headers @{Authorization='Bearer %TOKEN%'} -Uri '%UURL%' -OutFile '_rbt_upd.zip'}catch{exit 1}"
:u_chk
if not exist "_rbt_upd.zip" goto u_fail
for %%F in (_rbt_upd.zip) do if %%~zF LSS 50000 goto u_fail
powershell -NoProfile -Command "try{Expand-Archive -Force -LiteralPath '_rbt_upd.zip' '_rbt_upd'}catch{exit 1}"
set "USRC="
if exist "_rbt_upd\python\command_center.py" set "USRC=_rbt_upd"
if defined USRC goto u_copy
for /d %%D in (_rbt_upd\*) do if not defined USRC if exist "%%D\python\command_center.py" set "USRC=%%D"
:u_copy
if not defined USRC goto u_fail
robocopy "%USRC%" "." /E /XF cc_state.json cc_day.json cc_status.json CC_SIGNAL.csv s2_state.json s1_state.json MT5_PATH.txt TOKEN.txt /XD logs replay __pycache__ .git redist /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto u_fail
if exist "_rbt_upd" rmdir /s /q "_rbt_upd" >nul 2>nul
if exist "_rbt_upd.zip" del "_rbt_upd.zip" >nul 2>nul
if not exist "python\command_center.py" goto u_fail
echo   [2/2] [OK] sudah versi TERBARU.
set /a OKCNT+=1
popd
goto :eof
:u_fail
if exist "_rbt_upd" rmdir /s /q "_rbt_upd" >nul 2>nul
if exist "_rbt_upd.zip" del "_rbt_upd.zip" >nul 2>nul
echo   [X] Gagal update %~2 - dilewati, lanjut yang lain.
popd
goto :eof
