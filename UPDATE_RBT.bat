@echo off
setlocal
title RBT FX - UPDATE SEKALI JALAN
set TOKEN=GANTI_TOKEN_ANDA
rem v4-template: token bisa ditaruh di file TOKEN.txt
rem (satu baris) di samping bat ini -- TIDAK ikut ke GitHub.
if exist "%~dp0TOKEN.txt" set /p TOKEN=<"%~dp0TOKEN.txt"

echo ================================================================
echo   RBT FX - PEMBARUAN VERSI TERBARU (sekali jalan)
echo ================================================================
echo(
if not exist "MULAI_SEMUA.bat" goto SALAH_FOLDER
echo File ini benar. PASTIKAN semua jendela MULAI_SEMUA.bat dan
echo jendela dashboard SUDAH DITUTUP sebelum lanjut.
echo(
echo   [1] Strategy 1     [2] Strategy 2     [3] Strategy 3
echo   [4] Strategy 4 (BARU - kosong, untuk strategy Anda)
choice /C 1234 /N /M "Ketik 1, 2, 3, atau 4 lalu tekan Enter: "
set R=%errorlevel%
if "%R%"=="1" set REPO=Sistem-Trading-Strategy-1
if "%R%"=="2" set REPO=Sistem-Trading-Strategy-2
if "%R%"=="3" set REPO=Sistem-Trading-Strategy-3
if "%R%"=="4" set REPO=Sistem-Trading-Strategy-4-SNR-EMA13-EMA21
echo(
echo [1/4] Mengunduh %REPO% dari GitHub ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Headers @{Authorization='Bearer %TOKEN%'} -Uri 'https://codeload.github.com/ributprasetyoaji/%REPO%/zip/refs/heads/main' -OutFile \"$env:TEMP\_rbt_update.zip\""
if not exist "%TEMP%\_rbt_update.zip" goto GAGAL_UNDUH
echo [2/4] Membongkar ZIP ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force -Path \"$env:TEMP\_rbt_update.zip\" -DestinationPath \"$env:TEMP\_rbt_tmp\""
if not exist "%TEMP%\_rbt_tmp\%REPO%-main" goto GAGAL_UNDUH
echo [3/4] Menyalin file terbaru ke folder ini ...
robocopy "%TEMP%\_rbt_tmp\%REPO%-main" . /E /NFL /NDL /NJH /NJS /NP
if errorlevel 8 goto GAGAL_SALIN
echo [4/4] Membersihkan ...
rmdir /S /Q "%TEMP%\_rbt_tmp"
del /Q "%TEMP%\_rbt_update.zip"
echo(
echo  ============================================================
echo   SELESAI! Folder ini sekarang versi TERBARU.
echo   Jalankan lagi MULAI_SEMUA.bat di folder ini.
echo   (Cek dashboard: versi harus v3.88 / v3.92 / v4.09 / template)
echo  ============================================================
pause
exit /b 0

:SALAH_FOLDER
echo(
echo  File ini harus ditaruh DI DALAM folder strategy
echo  (folder yang berisi MULAI_SEMUA.bat).
echo  Pindahkan file ini ke situ, lalu klik 2x lagi.
pause
exit /b 1

:GAGAL_UNDUH
echo(
echo  GAGAL mengunduh. Cek koneksi internet VPS, lalu klik 2x lagi.
pause
exit /b 1

:GAGAL_SALIN
echo(
echo  GAGAL menyalin. Kemungkinan masih ada engine yang jalan.
echo  Tutup semua jendela bat/dashboard, lalu klik 2x lagi.
pause
exit /b 1
