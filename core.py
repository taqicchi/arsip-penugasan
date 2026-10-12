"""Logika inti Arsip Penugasan: struktur folder, penamaan berkas, metadata.

Sengaja tanpa GUI supaya bisa diuji sendiri (lihat test_core.py).

Struktur yang dihasilkan:

    <folder induk>/
    ├── ceklis.json                (opsional — menimpa ceklis bawaan per jenis)
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
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

VERSI = "1.0.0"
META_FILE = "penugasan.json"
CEKLIS_FILE = "ceklis.json"

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
JENIS_OUTPUT = ["LHA", "LHR", "LHE", "Laporan Pemantauan", "Laporan", "Konsep LHA", "Konsep LHR",
                "Konsep LHE", "Nota Dinas", "Memo"]
OUTPUT_DEFAULT = {"Audit": "LHA", "Reviu": "LHR", "Evaluasi": "LHE",
                  "Pemantauan": "Laporan Pemantauan"}

PERAN = ["Penanggung Jawab", "Pengendali Mutu", "Pengendali Teknis", "Ketua Tim", "Anggota Tim"]

BERJALAN, SELESAI, BATAL = "Berjalan", "Selesai", "Dibatalkan"
STATUS = [BERJALAN, SELESAI, BATAL]
LEWAT_TENGGAT = "Lewat tenggat"  # hanya untuk tampilan, tidak disimpan

TAHAP = ["Persiapan", "Pelaksanaan", "Konsep Laporan", "Laporan Final"]

# Ceklis bawaan per jenis: (label, subfolder, kata kunci nama berkas).
# Butir dianggap terpenuhi otomatis kalau ada berkas di subfolder itu yang namanya
# memuat kata kunci (tanpa membedakan huruf besar/kecil). Kata kunci kosong = berkas apa pun.
# Bisa ditimpa dengan ceklis.json di folder induk, formatnya sama.
CEKLIS_BAWAAN: dict[str, list[tuple[str, str, str]]] = {
    "Audit": [("Surat tugas", ST, ""), ("Program kerja audit (PKA)", KKP, "PKA"),
              ("Kertas kerja audit (KKA)", KKP, "KKA"), ("Notisi / daftar temuan", KKP, "notisi"),
              ("Konsep LHA", OUTPUT, "konsep"), ("LHA final", OUTPUT, "LHA")],
    "Reviu": [("Surat tugas", ST, ""), ("Program kerja reviu (PKR)", KKP, "PKR"),
              ("Kertas kerja reviu (KKR)", KKP, "KKR"), ("Konsep LHR", OUTPUT, "konsep"),
              ("LHR final", OUTPUT, "LHR")],
    "Evaluasi": [("Surat tugas", ST, ""), ("Program kerja evaluasi (PKE)", KKP, "PKE"),
                 ("Kertas kerja evaluasi (KKE)", KKP, "KKE"), ("Konsep LHE", OUTPUT, "konsep"),
                 ("LHE final", OUTPUT, "LHE")],
    "Pemantauan": [("Surat tugas", ST, ""), ("Data pemantauan", DUKUNG, ""),
                   ("Kertas kerja", KKP, ""), ("Laporan pemantauan", OUTPUT, "")],
}
CEKLIS_UMUM = [("Surat tugas", ST, ""), ("Kertas kerja", KKP, ""), ("Output", OUTPUT, "")]

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


def _tgl(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


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
    # Pelaksanaan
    mulai: date | None = None
    sampai: date | None = None
    jumlah_hari: int | None = None
    peran_saya: str = ""
    tim: list[dict] = field(default_factory=list)  # [{"nama": ..., "peran": ...}]
    # Kemajuan
    tahap: str = TAHAP[0]
    tgl_tahap: dict[str, str] = field(default_factory=dict)  # tahap -> tanggal ISO
    ceklis: dict[str, bool] = field(default_factory=dict)  # centang manual per label butir
    selesai_pada: date | None = None
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

    # --- status, tahap, ceklis -----------------------------------------
    def status_tampil(self, hari_ini: date | None = None) -> str:
        hari_ini = hari_ini or date.today()
        if self.status == BERJALAN and self.tenggat and hari_ini > self.tenggat:
            return LEWAT_TENGGAT
        return self.status

    def sisa_hari(self, hari_ini: date | None = None) -> int | None:
        """Hari menuju tenggat (negatif = lewat). None kalau tidak ada tenggat atau tidak berjalan."""
        if self.status != BERJALAN or not self.tenggat:
            return None
        return (self.tenggat - (hari_ini or date.today())).days

    def atur_status(self, status: str, hari_ini: date | None = None) -> None:
        self.status = status
        self.selesai_pada = (hari_ini or date.today()) if status == SELESAI else None

    def atur_tahap(self, tahap: str, hari_ini: date | None = None) -> None:
        self.tahap = tahap
        self.tgl_tahap.setdefault(tahap, (hari_ini or date.today()).isoformat())

    def butir_ceklis(self, root: Path | None = None) -> list[tuple[str, bool, bool]]:
        """[(label, terpenuhi, otomatis)] — otomatis = terpenuhi karena berkasnya ada."""
        hasil = []
        for label, kunci, kata in muat_ceklis(root).get(self.jenis, CEKLIS_UMUM):
            nama = [b.name.lower() for b in self.berkas(kunci)] if kunci in SUBFOLDER else []
            kata = kata.lower()
            # "Konsep LHR …" tidak boleh ikut mencentang butir "LHR final".
            otomatis = any(kata in n and ("konsep" in kata or "konsep" not in n) for n in nama)
            hasil.append((label, otomatis or self.ceklis.get(label, False), otomatis))
        return hasil

    def nama_tim(self) -> str:
        return ", ".join(a["nama"] for a in self.tim if a.get("nama"))

    # --- JSON -----------------------------------------------------------
    def ke_dict(self) -> dict:
        return {
            "nomor_st": self.nomor_st,
            "tanggal_st": self.tanggal_st.isoformat(),
            "jenis": self.jenis,
            "judul": self.judul,
            "objek": self.objek,
            "tenggat": _iso(self.tenggat),
            "status": self.status,
            "catatan": self.catatan,
            "dibuat": self.dibuat,
            "mulai": _iso(self.mulai),
            "sampai": _iso(self.sampai),
            "jumlah_hari": self.jumlah_hari,
            "peran_saya": self.peran_saya,
            "tim": self.tim,
            "tahap": self.tahap,
            "tgl_tahap": self.tgl_tahap,
            "ceklis": self.ceklis,
            "selesai_pada": _iso(self.selesai_pada),
        }

    @classmethod
    def dari_dict(cls, d: dict, folder: Path | None = None) -> "Penugasan":
        return cls(
            nomor_st=d.get("nomor_st", ""),
            tanggal_st=date.fromisoformat(d["tanggal_st"]),
            jenis=d.get("jenis", ""),
            judul=d["judul"],
            objek=d.get("objek", ""),
            tenggat=_tgl(d.get("tenggat")),
            status=d.get("status", BERJALAN),
            catatan=d.get("catatan", ""),
            dibuat=d.get("dibuat", ""),
            mulai=_tgl(d.get("mulai")),
            sampai=_tgl(d.get("sampai")),
            jumlah_hari=d.get("jumlah_hari"),
            peran_saya=d.get("peran_saya", ""),
            tim=list(d.get("tim") or []),
            tahap=d.get("tahap") or TAHAP[0],
            tgl_tahap=dict(d.get("tgl_tahap") or {}),
            ceklis=dict(d.get("ceklis") or {}),
            selesai_pada=_tgl(d.get("selesai_pada")),
            folder=folder,
        )


_ceklis_cache: dict[Path, tuple[float, dict]] = {}


def muat_ceklis(root: Path | None) -> dict[str, list[tuple[str, str, str]]]:
    """Ceklis dari `<root>/ceklis.json` kalau ada dan valid, selain itu bawaan."""
    if root:
        f = Path(root) / CEKLIS_FILE
        try:
            mtime = f.stat().st_mtime
            if f in _ceklis_cache and _ceklis_cache[f][0] == mtime:
                return _ceklis_cache[f][1]
            data = json.loads(f.read_text(encoding="utf-8"))
            hasil = {jenis: [tuple(b) for b in butir] for jenis, butir in data.items()}
            _ceklis_cache[f] = (mtime, hasil)
            return hasil
        except (OSError, ValueError, TypeError):
            pass
    return CEKLIS_BAWAAN


def perlu_diingat(daftar: list[Penugasan], hari_ini: date | None = None, h: int = 3
                  ) -> tuple[list[Penugasan], list[Penugasan]]:
    """(lewat tenggat, jatuh tempo dalam `h` hari) — hanya yang masih berjalan."""
    hari_ini = hari_ini or date.today()
    lewat, segera = [], []
    for p in daftar:
        sisa = p.sisa_hari(hari_ini)
        if sisa is None:
            continue
        if sisa < 0:
            lewat.append(p)
        elif sisa <= h:
            segera.append(p)
    lewat.sort(key=lambda p: p.tenggat)
    segera.sort(key=lambda p: p.tenggat)
    return lewat, segera


def hari_kalender(mulai: date | None, sampai: date | None) -> int | None:
    if mulai and sampai and sampai >= mulai:
        return (sampai - mulai).days + 1
    return None


def hari_kerja(mulai: date | None, sampai: date | None) -> int | None:
    """Senin–Jumat saja; libur nasional tidak diperhitungkan."""
    if not (mulai and sampai and sampai >= mulai):
        return None
    return sum(1 for i in range((sampai - mulai).days + 1) if (mulai + timedelta(i)).weekday() < 5)


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
            except (OSError, ValueError, KeyError, TypeError) as e:
                galat.append((meta, str(e)))
        hasil.sort(key=lambda p: (p.tanggal_st, p.judul), reverse=True)
        return hasil, galat

    def cari_nomor(self, nomor: str, kecuali: Path | None = None) -> list[Penugasan]:
        """Penugasan lain dengan nomor ST yang sama (pembanding tanpa spasi & huruf besar/kecil)."""
        kunci = re.sub(r"\s+", "", nomor).lower()
        if not kunci:
            return []
        daftar, _ = self.pindai()
        return [p for p in daftar if re.sub(r"\s+", "", p.nomor_st).lower() == kunci
                and (kecuali is None or p.folder != kecuali)]

    def buat(self, p: Penugasan) -> Penugasan:
        target = self.root / p.path_relatif()
        if target.exists():
            raise FileExistsError(f"Folder sudah ada:\n{target}")
        target.mkdir(parents=True)
        for sub in SUBFOLDER.values():
            (target / sub).mkdir()
        p.folder = target
        p.dibuat = p.dibuat or datetime.now().isoformat(timespec="seconds")
        if not p.tgl_tahap:
            p.atur_tahap(p.tahap)
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
        if sumber.is_dir():
            raise IsADirectoryError(f"Yang dilampirkan harus berkas, bukan folder:\n{sumber}")
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
