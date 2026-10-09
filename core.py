"""Logika inti Arsip Penugasan: struktur folder, penamaan berkas, metadata.

Sengaja tanpa GUI supaya bisa diuji sendiri (lihat test_core.py).

Struktur yang dihasilkan:

    <folder induk>/
    └── 2026/
        └── 11 November/
            └── 2026-11-03 Reviu RKA Dinas X/
                ├── 01 Surat Tugas/
                ├── 02 Kertas Kerja/
                ├── 03 Data Dukung/
                ├── 04 Output/
                └── penugasan.json

`penugasan.json` di tiap folder adalah satu-satunya sumber data. Tidak ada
database terpisah: daftar penugasan dibangun ulang dengan memindai folder induk,
jadi folder bisa dipindah/disinkron OneDrive tanpa ada yang rusak.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

META_FILE = "penugasan.json"

ST, KKP, DUKUNG, OUTPUT = "st", "kkp", "dukung", "output"
SUBFOLDER = {
    ST: "01 Surat Tugas",
    KKP: "02 Kertas Kerja",
    DUKUNG: "03 Data Dukung",
    OUTPUT: "04 Output",
}
LABEL = {ST: "Surat Tugas", KKP: "Kertas Kerja", DUKUNG: "Data Dukung", OUTPUT: "Output"}

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]

JENIS = ["Audit", "Reviu", "Evaluasi", "Pemantauan", "Konsultansi", "Lainnya"]
JENIS_OUTPUT = ["LHA", "LHR", "LHE", "Laporan Pemantauan", "Laporan", "Nota Dinas", "Memo"]
OUTPUT_DEFAULT = {"Audit": "LHA", "Reviu": "LHR", "Evaluasi": "LHE",
                  "Pemantauan": "Laporan Pemantauan"}

BERJALAN, SELESAI, BATAL = "Berjalan", "Selesai", "Dibatalkan"
STATUS = [BERJALAN, SELESAI, BATAL]
LEWAT_TENGGAT = "Lewat tenggat"  # hanya untuk tampilan, tidak disimpan

JUDUL_MAX = 80  # path Windows dibatasi ~260 karakter; judul muncul di folder dan nama berkas

_ILEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def bersihkan(teks: str, max_len: int = JUDUL_MAX) -> str:
    """Jadikan teks aman dipakai sebagai nama folder/berkas Windows."""
    teks = _ILEGAL.sub("-", teks)
    teks = re.sub(r"\s+", " ", teks).strip().rstrip(". ")
    if len(teks) > max_len:
        teks = teks[:max_len].rstrip(". ")
    return teks


def parse_tanggal(teks: str) -> date | None:
    """Terima DD-MM-YYYY, DD/MM/YYYY, atau YYYY-MM-DD. String kosong -> None."""
    teks = teks.strip()
    if not teks:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(teks, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Tanggal tidak dikenali: {teks!r} (pakai DD-MM-YYYY)")


def format_tanggal(d: date | None) -> str:
    return d.strftime("%d-%m-%Y") if d else ""


def path_unik(folder: Path, nama: str) -> Path:
    """`folder/nama`, atau `nama (2)`, `nama (3)`, ... kalau sudah ada."""
    target = folder / nama
    stem, ext = target.stem, target.suffix
    n = 2
    while target.exists():
        target = folder / f"{stem} ({n}){ext}"
        n += 1
    return target


@dataclass
class Penugasan:
    nomor_st: str
    tanggal_st: date
    jenis: str
    judul: str
    objek: str = ""
    tenggat: date | None = None
    status: str = BERJALAN
    catatan: str = ""
    dibuat: str = ""
    folder: Path | None = None  # lokasi di disk; tidak disimpan ke JSON

    # --- penamaan -------------------------------------------------------
    def nama_folder(self) -> str:
        return f"{self.tanggal_st.isoformat()} {bersihkan(self.judul)}"

    def path_relatif(self) -> Path:
        d = self.tanggal_st
        return Path(str(d.year)) / f"{d.month:02d} {BULAN[d.month - 1]}" / self.nama_folder()

    def nama_surat_tugas(self, ext: str) -> str:
        nomor = bersihkan(self.nomor_st, 40)
        return f"ST {nomor} {bersihkan(self.judul)}{ext}" if nomor else f"ST {bersihkan(self.judul)}{ext}"

    def nama_output(self, jenis_dokumen: str, ext: str) -> str:
        return f"{bersihkan(jenis_dokumen, 40)} {bersihkan(self.judul)}{ext}"

    def output_default(self) -> str:
        return OUTPUT_DEFAULT.get(self.jenis, "Laporan")

    # --- isi folder -----------------------------------------------------
    def berkas(self, kunci: str) -> list[Path]:
        if not self.folder:
            return []
        sub = self.folder / SUBFOLDER[kunci]
        if not sub.is_dir():
            return []
        return sorted(p for p in sub.iterdir() if p.is_file() and not p.name.startswith("~$"))

    def punya(self, kunci: str) -> bool:
        return bool(self.berkas(kunci))

    def status_tampil(self, hari_ini: date | None = None) -> str:
        hari_ini = hari_ini or date.today()
        if self.status == BERJALAN and self.tenggat and hari_ini > self.tenggat:
            return LEWAT_TENGGAT
        return self.status

    # --- JSON -----------------------------------------------------------
    def ke_dict(self) -> dict:
        return {
            "nomor_st": self.nomor_st,
            "tanggal_st": self.tanggal_st.isoformat(),
            "jenis": self.jenis,
            "judul": self.judul,
            "objek": self.objek,
            "tenggat": self.tenggat.isoformat() if self.tenggat else None,
            "status": self.status,
            "catatan": self.catatan,
            "dibuat": self.dibuat,
        }

    @classmethod
    def dari_dict(cls, d: dict, folder: Path | None = None) -> "Penugasan":
        return cls(
            nomor_st=d.get("nomor_st", ""),
            tanggal_st=date.fromisoformat(d["tanggal_st"]),
            jenis=d.get("jenis", ""),
            judul=d["judul"],
            objek=d.get("objek", ""),
            tenggat=date.fromisoformat(d["tenggat"]) if d.get("tenggat") else None,
            status=d.get("status", BERJALAN),
            catatan=d.get("catatan", ""),
            dibuat=d.get("dibuat", ""),
            folder=folder,
        )


class Arsip:
    """Folder induk berisi semua penugasan."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def pindai(self) -> tuple[list[Penugasan], list[tuple[Path, str]]]:
        """Kembalikan (penugasan, [(berkas, pesan galat)])."""
        hasil, galat = [], []
        for meta in self.root.glob(f"*/*/*/{META_FILE}"):
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                hasil.append(Penugasan.dari_dict(data, meta.parent))
            except (OSError, ValueError, KeyError) as e:
                galat.append((meta, str(e)))
        hasil.sort(key=lambda p: (p.tanggal_st, p.judul), reverse=True)
        return hasil, galat

    def buat(self, p: Penugasan) -> Penugasan:
        target = self.root / p.path_relatif()
        if target.exists():
            raise FileExistsError(f"Folder sudah ada:\n{target}")
        target.mkdir(parents=True)
        for sub in SUBFOLDER.values():
            (target / sub).mkdir()
        p.folder = target
        p.dibuat = p.dibuat or datetime.now().isoformat(timespec="seconds")
        self.simpan(p)
        return p

    def simpan(self, p: Penugasan) -> None:
        assert p.folder is not None
        tmp = p.folder / (META_FILE + ".tmp")
        tmp.write_text(json.dumps(p.ke_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, p.folder / META_FILE)

    def ubah(self, p: Penugasan) -> None:
        """Simpan perubahan; pindahkan folder kalau tanggal/judul berubah."""
        assert p.folder is not None
        target = self.root / p.path_relatif()
        lama = p.folder
        if target.resolve() != lama.resolve():
            if target.exists():
                raise FileExistsError(f"Folder tujuan sudah ada:\n{target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(lama), str(target))
            p.folder = target
            self._hapus_induk_kosong(lama.parent)
        self.simpan(p)

    def lampirkan(self, p: Penugasan, kunci: str, sumber: Path, nama: str | None = None,
                  pindahkan: bool = False) -> Path:
        """Salin (atau pindahkan) `sumber` ke subfolder `kunci`. `nama` None = nama asli."""
        assert p.folder is not None
        sumber = Path(sumber)
        folder = p.folder / SUBFOLDER[kunci]
        folder.mkdir(exist_ok=True)
        target = path_unik(folder, nama or sumber.name)
        if pindahkan:
            shutil.move(str(sumber), str(target))
        else:
            shutil.copy2(sumber, target)
        return target

    def _hapus_induk_kosong(self, folder: Path) -> None:
        """Hapus folder bulan/tahun yang jadi kosong setelah penugasan dipindah."""
        root = self.root.resolve()
        while folder.resolve() != root and folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
            folder = folder.parent
