# Arsip Penugasan

Aplikasi desktop (Python + Tkinter) untuk menyimpan berkas tiap penugasan ke struktur
folder yang tetap. Tampilannya mengikuti tema Q Studio Tracker (`tema.py`).

## Unduh & pasang

Ambil dari halaman [Releases](https://github.com/taqicchi/arsip-penugasan/releases):

- **`ArsipPenugasan-vX.Y.Z.exe`** — satu berkas, tidak perlu Python. Klik dua kali.
  Windows SmartScreen bisa menampilkan "Windows protected your PC" karena exe tidak
  ditandatangani: pilih *More info → Run anyway*.
- **`ArsipPenugasan-python-vX.Y.Z.zip`** — untuk komputer yang memblokir exe tak bertanda
  tangan (Windows 11 dengan *Smart App Control* aktif, atau PC kantor dengan kebijakan
  aplikasi). Butuh Python 3.11+. Ekstrak, jalankan `Pasang Pustaka.bat` sekali, lalu buka
  dengan `Buka Arsip Penugasan.bat`.

Saat pertama dibuka, aplikasi meminta folder induk (disimpan di
`%APPDATA%\ArsipPenugasan\config.json`). Data tidak pernah disimpan di dalam folder aplikasi,
jadi mengganti versi cukup dengan mengganti exe/folder-nya.

**Pustaka tambahan** (opsional, tapi disarankan):

```
python -m pip install --user -r requirements.txt
```

| Pustaka | Untuk | Kalau tidak ada |
|---|---|---|
| `tkinterdnd2` | seret-lepas berkas dari Explorer | lampirkan lewat tombol saja |
| `pypdf` | isi otomatis dari PDF surat tugas | isi manual |
| `openpyxl` | rekap `.xlsx` | rekap ditulis sebagai `.csv` |

## Struktur

```
<folder induk>/
├── ceklis.json                       (opsional, lihat di bawah)
└── 2026/11 November/2026-11-03 Reviu RKA Dinas X/
    ├── 01 Surat Tugas/   ST 700-123-Itda-2026 Reviu RKA Dinas X.pdf
    ├── 02 Kertas Kerja/  (nama asli berkas)
    ├── 03 Data Dukung/   (nama asli berkas)
    ├── 04 Output/        LHR Reviu RKA Dinas X.pdf
    └── penugasan.json    data penugasan
```

- Daftar penugasan dibaca ulang dari `penugasan.json` di tiap folder; tidak ada database lain.
- Mengubah tanggal/judul lewat "Ubah Data" ikut memindah foldernya. Nama berkas yang
  sudah ada di dalamnya tidak diganti.
- Berkas disalin secara default; centang "Pindahkan berkas asli" untuk memindah.
- Nama yang bentrok diberi akhiran ` (2)`, ` (3)`, … — tidak ada yang tertimpa.

## Fitur

**Seret-lepas.** Seret berkas ke tombol ①–④ di panel detail untuk melampirkannya.
Seret PDF surat tugas ke daftar penugasan untuk langsung membuat penugasan baru.

**Isi otomatis dari surat tugas** (`baca_st.py`). Dari PDF yang punya lapisan teks
dibaca: nomor, tanggal penetapan (tanggal terakhir di dokumen), jenis, judul (kalimat
"Untuk:"), objek, jumlah hari ("selama N hari"), periode ("3 s.d. 14 November 2026"),
dan susunan tim (baris yang memuat nama peran). Hanya mengisi kolom yang belum diketik.
PDF hasil scan tidak terbaca.

**Pengingat.** Spanduk di atas daftar untuk penugasan yang lewat tenggat atau jatuh
tempo ≤ 3 hari (klik untuk menyaring). Tombol "Pengingat harian" di kanan bawah
memasang tugas Task Scheduler `Arsip Penugasan - Pengingat` yang menjalankan
`pengingat.py` tiap hari 07.30 (atau begitu komputer menyala) dan menampilkan
notifikasi Windows — walaupun aplikasi tidak dibuka.

**Rekap Excel.** Merekap penugasan yang sedang ditampilkan (ikut filter tahun/status/cari)
ke `.xlsx`: nomor & tanggal ST, jenis, judul, objek, peran, tim, periode, jumlah hari,
tenggat, tahap, status, tanggal selesai, daftar output, dan tautan ke folder.

**Data penugasan.** Selain data ST: periode mulai–sampai, jumlah hari sesuai ST, peran
saya, susunan tim (peran + nama), tahap (Persiapan → Pelaksanaan → Konsep Laporan →
Laporan Final, dengan tanggal tiap tahap), dan tanggal selesai. Melampirkan output
menggeser tahap maju otomatis. Nomor ST yang sudah pernah dicatat memunculkan peringatan.

**Ceklis dokumen** per jenis penugasan (tab Progres). Butir tercentang otomatis kalau
ada berkas di subfolder yang namanya memuat kata kunci; selain itu bisa dicentang manual.
Untuk mengganti daftar bawaan, buat `ceklis.json` di folder induk:

```json
{
  "Reviu": [["Surat tugas", "st", ""], ["Program kerja reviu", "kkp", "PKR"],
            ["LHR final", "output", "LHR"]]
}
```

Tiap butir: `[label, subfolder (st/kkp/dukung/output), kata kunci nama berkas]`.
Kata kunci kosong = berkas apa pun. Berkas bernama "Konsep …" tidak mencentang butir
yang kata kuncinya tidak memuat "konsep".

## Membuat rilis

1. Naikkan `VERSI` di `core.py` (mis. `"1.1.0"`), commit, push.
2. Buat dan push tag yang sama persis dengan awalan `v`:
   ```
   git tag v1.1.0
   git push origin v1.1.0
   ```
3. GitHub Actions (`.github/workflows/rilis.yml`) menjalankan tes, membangun exe, dan
   membuat Release berisi exe, zip versi Python, dan `SHA256SUMS.txt`. Kalau `VERSI` tidak
   sama dengan tag, build sengaja gagal.

Untuk mencoba build di komputer sendiri: `build.bat` → `dist\ArsipPenugasan.exe`.
Ikon dibuat ulang dengan `python alat/buat_ikon.py`.

## Tes

```
python -m unittest test_core test_lain
```
