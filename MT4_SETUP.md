# PANDUAN MT4 — RBT FX mendukung MT5 **dan** MT4

Sistem ini otomatis memilih platform (`broker_mode: "auto"`):

**MT5 tersambung?** -> pakai MT5. **Tidak ada MT5?** -> coba **MT4**. **Dua-duanya tidak ada?** -> MODE SIMULASI.

Kalau ingin PAKSA MT4 (mis. MT5 & MT4 terpasang berdampingan): ubah di `python/cc_config.json` → `"broker_mode": "mt4"`.

---

## Langkah sekali saja (di VPS)

1. **Install MT4** broker Anda + login akun (window MT4 terbuka, kiri bawah terlihat koneksi).
2. Salin file **`RBT_FX_Bridge.mq4`** dari folder program ke folder MT4:
   - Di MT4: **File → Open Data Folder** → buka **`MQL4\Experts`**
   - Tempel `RBT_FX_Bridge.mq4` ke situ
3. **Compile**: di MT4 tekan **F4** (MetaEditor) → buka `RBT_FX_Bridge.mq4` → tombol **Compile (F7)** → harus **0 errors**.
4. **Pasang di chart**: kembali ke MT4 → panel **Navigator (Ctrl+N)** → **Expert Advisors** → seret **RBT_FX_Bridge** ke chart APA SAJA (mis. EURUSD M1) → di jendela izinkan **"Allow live trading"** → OK.
5. Pastikan tombol **AutoTrading** di toolbar MT4 **HIJAU (ON)**.
6. Jalankan bat seperti biasa. Di Execution Log harus muncul:
   `>>> METATRADER 4 tersambung via jembatan file (EA RBT_FX_Bridge) <<<`
   dan chip atas dashboard: **MT4 (nama-server)**.

> Jangan tutup chart yang memuat RBT_FX_Bridge — itulah "kabel"-nya.

## Cara kerja singkat

Python dan EA bertukar perintah lewat **file** di folder Common MT4
(`rbtfx_cmd_<magic>.txt` / `rbtfx_resp_<magic>.txt`) — **tanpa DLL, tanpa
setting port/firewall**. S1 dan S2 bisa jalan bersamaan ke satu MT4
(masing-masing punya nomor magic sendiri).

## Perbedaan penting MT4 vs MT5 (jujur)

| Hal | MT5 | MT4 (jembatan) |
|---|---|---|
| Latensi eksekusi | instan | ~0,3–1 detik (cukup utk strategi M5/M15) |
| Volume | real + tick | tick saja → delta flow = proxy arah tick |
| Rekap deposit/WD hari ini | terbaca | tidak tersedia (kolom tetap 0, P/L transaksi tetap benar) |
| Data historis untuk analisa | sama-sama dari broker | sama (OHLC M1–D1) |

## Sembahan cepat

- Log: `MT4 bridge tidak merespons` → EA belum dipasang / AutoTrading OFF / chart ditutup.
- Log: `folder Common MT4 belum ada` → MT4 belum pernah dijalankan.
- Pair tertentu tidak muncul di scanner → symbol tidak ada di MT4 broker itu (nama beda, mis. GOLD vs XAUUSD).
