"""Membaca isian penugasan dari teks PDF surat tugas.

Hanya bekerja untuk PDF yang punya lapisan teks (hasil ekspor dari Word/aplikasi
persuratan). PDF hasil scan berupa gambar tidak terbaca — hasilnya kosong, dan
pengguna mengisi manual seperti biasa.

Semua hasil adalah tebakan: dialog hanya mengisi kolom yang masih kosong, dan
pengguna tetap diminta memeriksa.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from core import BULAN, PERAN

try:
    from pypdf import PdfReader
except ImportError:  # aplikasi tetap jalan, hanya tanpa isi otomatis
    PdfReader = None

_BULAN = {b.lower(): i + 1 for i, b in enumerate(BULAN)}
_BULAN.update({"pebruari": 2, "nopember": 11, "agustus": 8})
_RE_TGL = re.compile(r"\b(\d{1,2})\s+(" + "|".join(_BULAN) + r")\s+(\d{4})\b", re.I)
_RE_NOMOR = re.compile(r"\bnomor\s*[:.]?\s*([0-9A-Za-z][0-9A-Za-z.\-]*(?:\s*/\s*[0-9A-Za-z.\-]+)+)", re.I)
_RE_HARI = re.compile(r"selama\s+(\d{1,3})\s*(?:\([^)]*\))?\s*hari", re.I)
_RE_UNTUK = re.compile(r"\buntuk\s*:?\s*(?:\d+\.\s*)?(.+?)(?:\.\s|;|\n\s*\n|\n\s*\d+\.\s|$)", re.I | re.S)
_KATA_JENIS = [
    ("Audit", r"\baudit"), ("Reviu", r"\breviu|\breview"), ("Evaluasi", r"\bevaluasi"),
    ("Pemantauan", r"\bpemantauan|\bmonitoring"), ("Konsultansi", r"\bkonsultansi|\basistensi|\bpendampingan"),
]


@dataclass
class HasilBaca:
    nomor_st: str = ""
    tanggal_st: date | None = None
    jenis: str = ""
    judul: str = ""
    objek: str = ""
    jumlah_hari: int | None = None
    mulai: date | None = None
    sampai: date | None = None
    tim: list[dict] = field(default_factory=list)

    def terisi(self) -> list[str]:
        nama = {"nomor_st": "nomor", "tanggal_st": "tanggal", "jenis": "jenis", "judul": "judul",
                "objek": "objek", "jumlah_hari": "jumlah hari", "mulai": "periode", "tim": "tim"}
        return [v for k, v in nama.items() if getattr(self, k)]


def teks_pdf(path: Path, maks_halaman: int = 3) -> str:
    if PdfReader is None or Path(path).suffix.lower() != ".pdf":
        return ""
    try:
        r = PdfReader(str(path))
        return "\n".join((h.extract_text() or "") for h in r.pages[:maks_halaman])
    except Exception:  # PDF rusak/terenkripsi: anggap tidak terbaca
        return ""


def _ke_tanggal(m: re.Match) -> date | None:
    try:
        return date(int(m.group(3)), _BULAN[m.group(2).lower()], int(m.group(1)))
    except ValueError:
        return None


def _rapikan(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" ,.;:")


def baca_teks(teks: str) -> HasilBaca:
    h = HasilBaca()
    if not teks.strip():
        return h
    datar = _rapikan(teks)

    m = _RE_NOMOR.search(teks)
    if m:
        h.nomor_st = re.sub(r"\s*/\s*", "/", m.group(1)).strip(".")

    # Tanggal penetapan biasanya tanggal terakhir di dokumen (di atas tanda tangan).
    semua_tgl = [d for d in (_ke_tanggal(m) for m in _RE_TGL.finditer(datar)) if d]
    if semua_tgl:
        h.tanggal_st = semua_tgl[-1]

    m = _RE_HARI.search(datar)
    if m:
        h.jumlah_hari = int(m.group(1))

    # Periode: "tanggal 3 s.d. 14 November 2026" atau "3 November s.d. 14 November 2026".
    m = re.search(r"(\d{1,2})(?:\s+(" + "|".join(_BULAN) + r"))?(?:\s+(\d{4}))?\s*(?:s\.?\s*d\.?|sampai(?: dengan)?|-|–)\s*"
                  r"(\d{1,2})\s+(" + "|".join(_BULAN) + r")\s+(\d{4})", datar, re.I)
    if m:
        try:
            th2, bl2 = int(m.group(6)), _BULAN[m.group(5).lower()]
            h.sampai = date(th2, bl2, int(m.group(4)))
            bl1 = _BULAN[m.group(2).lower()] if m.group(2) else bl2
            th1 = int(m.group(3)) if m.group(3) else th2
            h.mulai = date(th1, bl1, int(m.group(1)))
            if h.mulai > h.sampai:
                h.mulai = h.sampai = None
        except ValueError:
            h.mulai = h.sampai = None

    m = _RE_UNTUK.search(teks)
    tugas = _rapikan(m.group(1)) if m else ""
    tugas = re.sub(r"^(melaksanakan|melakukan)\s+", "", tugas, flags=re.I)
    sumber_jenis = tugas or datar
    for jenis, pola in _KATA_JENIS:
        if re.search(pola, sumber_jenis, re.I):
            h.jenis = jenis
            break
    if tugas:
        # Judul: potong sebelum keterangan waktu/tempat yang biasanya menyusul.
        judul = re.split(r"\s+(?:selama|mulai|pada tanggal|tanggal|dengan ketentuan|dan melaporkan)\b",
                         tugas, maxsplit=1, flags=re.I)[0]
        judul = judul[:1].upper() + judul[1:]
        h.judul = judul[:80].rsplit(" ", 1)[0] if len(judul) > 80 else judul
        m = re.search(r"\b(?:pada|di lingkungan|terhadap)\s+(.+?)(?:\s+(?:tahun|TA|periode|kabupaten|kota|provinsi)\b|$)",
                      h.judul, re.I)
        if m:
            h.objek = _rapikan(m.group(1))[:60]

    h.tim = _baca_tim(teks)
    return h


def _baca_tim(teks: str) -> list[dict]:
    """Baris yang memuat nama peran, mis. "1. Budi Santoso, S.E. ... Ketua Tim"."""
    tim = []
    pola_peran = "|".join(re.escape(p) for p in sorted(PERAN, key=len, reverse=True))
    for baris in teks.splitlines():
        m = re.search(pola_peran, baris, re.I)
        if not m:
            continue
        peran = next(p for p in PERAN if p.lower() == m.group(0).lower())
        sisa = baris[:m.start()]
        sisa = re.sub(r"^\s*\d+[.)]?\s*", "", sisa)               # nomor urut
        sisa = re.sub(r"\b(NIP|Pangkat|Jabatan)\b.*", "", sisa, flags=re.I)
        sisa = re.sub(r"\b\d{8,}\b.*", "", sisa)                   # NIP 18 digit dan sesudahnya
        nama = re.sub(r"\s+", " ", re.sub(r"\s*sebagai\s*$", "", sisa, flags=re.I)).strip(" ,;:")
        if 3 <= len(nama) <= 70 and re.search(r"[A-Za-z]{2}", nama) and not nama.lower().startswith(("nama", "kepada")):
            tim.append({"nama": nama, "peran": peran})
    return tim


def baca_pdf(path: Path) -> HasilBaca:
    return baca_teks(teks_pdf(path))

