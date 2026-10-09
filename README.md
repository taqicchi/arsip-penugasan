# Arsip Penugasan

Aplikasi desktop (Python + Tkinter, tanpa pustaka tambahan) untuk menyimpan berkas
tiap penugasan ke struktur folder yang tetap.

**Menjalankan:** klik dua kali `Buka Arsip Penugasan.bat`. Saat pertama dibuka,
aplikasi meminta folder induk (disimpan di `%APPDATA%\ArsipPenugasan\config.json`).

## Struktur

```
<folder induk>/2026/11 November/2026-11-03 Reviu RKA Dinas X/
├── 01 Surat Tugas/   ST 700-123-Itda-2026 Reviu RKA Dinas X.pdf
├── 02 Kertas Kerja/  (nama asli berkas)
├── 03 Data Dukung/   (nama asli berkas)
├── 04 Output/        LHR Reviu RKA Dinas X.pdf
└── penugasan.json    data penugasan (nomor, tanggal, jenis, objek, tenggat, status)
```

- Daftar penugasan dibaca ulang dari `penugasan.json` di tiap folder; tidak ada database lain.
- Mengubah tanggal/judul lewat "Ubah Data…" ikut memindah foldernya. Nama berkas yang
  sudah ada di dalamnya tidak diganti.
- Berkas disalin secara default; centang "Pindahkan berkas asli" untuk memindah.
- Nama yang bentrok diberi akhiran ` (2)`, ` (3)`, … — tidak ada yang tertimpa.

## Tes

```
python -m unittest test_core
```
