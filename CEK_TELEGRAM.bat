@echo off
title RBT FX - CEK KONEKSI TELEGRAM DARI VPS
set TOKEN=8160801093:AAExq30rSIkpo9_x1qZooEdnKOcMQ5pMPw8
set CHAT=6560789003
cd /d "%~dp0"
echo Mengetes koneksi VPS ini ke server Telegram (tunggu +-30 detik) ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Write-Host '=== 1. DNS api.telegram.org ==='; try { [System.Net.Dns]::GetHostAddresses('api.telegram.org') | ForEach-Object { Write-Host ('   IP: ' + $_.IPAddressToString) } } catch { Write-Host ('   GAGAL: ' + $_.Exception.Message) }; Write-Host '=== 2. CEK TOKEN (getMe) langsung dari VPS ==='; try { $r = Invoke-WebRequest -UseBasicParsing -Uri ('https://api.telegram.org/bot%TOKEN%/getMe') -TimeoutSec 15; Write-Host ('   HASIL: ' + $r.Content) } catch { Write-Host ('   GAGAL: ' + $_.Exception.Message); if ($_.Exception.Response) { $b = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream()); Write-Host ('   ISI: ' + $b.ReadToEnd()) } }; Write-Host '=== 3. KIRIM PESAN TES dari VPS ke chat Anda ==='; try { $r = Invoke-WebRequest -UseBasicParsing -Method Post -Body @{ chat_id = '%CHAT%'; text = 'TES KIRIM dari VPS - RBT FX' } -Uri ('https://api.telegram.org/bot%TOKEN%/sendMessage') -TimeoutSec 15; Write-Host ('   HASIL: ' + $r.Content) } catch { Write-Host ('   GAGAL: ' + $_.Exception.Message); if ($_.Exception.Response) { $b = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream()); Write-Host ('   ISI: ' + $b.ReadToEnd()) } }; Write-Host '=== SELESAI ==='" > cek_telegram_hasil.txt 2>&1
type cek_telegram_hasil.txt
echo.
echo Hasil lengkap juga tersimpan di file: cek_telegram_hasil.txt
echo (Foto/screenshot layar ini lalu kirimkan ke asisten)
pause
