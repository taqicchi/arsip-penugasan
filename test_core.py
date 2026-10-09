"""Jalankan: python -m unittest test_core"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from core import (BATAL, BERJALAN, DUKUNG, LEWAT_TENGGAT, OUTPUT, ST, Arsip, Penugasan,
                  bersihkan, parse_tanggal)


def contoh(**kw):
    data = dict(nomor_st="700/123/Itda/2026", tanggal_st=date(2026, 11, 3),
                jenis="Reviu", judul="Reviu RKA Dinas X", objek="Dinas X")
    data.update(kw)
    return Penugasan(**data)


class TestCore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "arsip"
        self.root.mkdir()
        self.arsip = Arsip(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def berkas(self, nama, isi="x"):
        p = Path(self.tmp.name) / "src"
        p.mkdir(exist_ok=True)
        f = p / nama
        f.write_text(isi)
        return f

    def test_struktur_folder(self):
        p = self.arsip.buat(contoh())
        self.assertEqual(p.folder, self.root / "2026" / "11 November" / "2026-11-03 Reviu RKA Dinas X")
        for sub in ("01 Surat Tugas", "02 Kertas Kerja", "03 Data Dukung", "04 Output"):
            self.assertTrue((p.folder / sub).is_dir())
        self.assertTrue((p.folder / "penugasan.json").is_file())

    def test_penamaan_st_dan_output(self):
        p = self.arsip.buat(contoh())
        st = self.arsip.lampirkan(p, ST, self.berkas("scan001.pdf"), p.nama_surat_tugas(".pdf"))
        self.assertEqual(st.name, "ST 700-123-Itda-2026 Reviu RKA Dinas X.pdf")
        out = self.arsip.lampirkan(p, OUTPUT, self.berkas("final.docx"), p.nama_output("LHR", ".docx"))
        self.assertEqual(out.name, "LHR Reviu RKA Dinas X.docx")
        out2 = self.arsip.lampirkan(p, OUTPUT, self.berkas("final.docx"), p.nama_output("LHR", ".docx"))
        self.assertEqual(out2.name, "LHR Reviu RKA Dinas X (2).docx")
        dukung = self.arsip.lampirkan(p, DUKUNG, self.berkas("RKA 2027.xlsx"))
        self.assertEqual(dukung.name, "RKA 2027.xlsx")
        self.assertTrue(p.punya(ST) and p.punya(OUTPUT))

    def test_salin_vs_pindah(self):
        p = self.arsip.buat(contoh())
        src = self.berkas("a.pdf")
        self.arsip.lampirkan(p, ST, src)
        self.assertTrue(src.exists())
        self.arsip.lampirkan(p, ST, src, pindahkan=True)
        self.assertFalse(src.exists())

    def test_pindai_bolak_balik(self):
        self.arsip.buat(contoh(tenggat=date(2026, 11, 20), catatan="tim 3"))
        self.arsip.buat(contoh(judul="Evaluasi SAKIP", tanggal_st=date(2026, 12, 1)))
        (self.root / "2026" / "11 November" / "rusak").mkdir()
        (self.root / "2026" / "11 November" / "rusak" / "penugasan.json").write_text("{bukan json")
        daftar, galat = self.arsip.pindai()
        self.assertEqual([p.judul for p in daftar], ["Evaluasi SAKIP", "Reviu RKA Dinas X"])
        self.assertEqual(daftar[1].tenggat, date(2026, 11, 20))
        self.assertEqual(daftar[1].catatan, "tim 3")
        self.assertEqual(len(galat), 1)

    def test_ubah_tanggal_memindah_folder(self):
        p = self.arsip.buat(contoh())
        self.arsip.lampirkan(p, ST, self.berkas("st.pdf"))
        p.tanggal_st = date(2026, 12, 5)
        p.judul = "Reviu RKA Dinas X Perubahan"
        self.arsip.ubah(p)
        self.assertEqual(p.folder, self.root / "2026" / "12 Desember" / "2026-12-05 Reviu RKA Dinas X Perubahan")
        self.assertTrue(p.punya(ST))
        self.assertFalse((self.root / "2026" / "11 November").exists())  # bulan kosong dibersihkan
        daftar, _ = self.arsip.pindai()
        self.assertEqual(len(daftar), 1)

    def test_duplikat_ditolak(self):
        self.arsip.buat(contoh())
        with self.assertRaises(FileExistsError):
            self.arsip.buat(contoh())

    def test_status(self):
        p = contoh(tenggat=date(2026, 11, 10))
        self.assertEqual(p.status_tampil(date(2026, 11, 10)), BERJALAN)
        self.assertEqual(p.status_tampil(date(2026, 11, 11)), LEWAT_TENGGAT)
        p.status = BATAL
        self.assertEqual(p.status_tampil(date(2026, 11, 11)), BATAL)

    def test_util(self):
        self.assertEqual(bersihkan('  Reviu: "RKA"  Dinas/X. '), "Reviu- -RKA- Dinas-X")
        self.assertEqual(parse_tanggal("03-11-2026"), date(2026, 11, 3))
        self.assertEqual(parse_tanggal("3/11/2026"), date(2026, 11, 3))
        self.assertIsNone(parse_tanggal(" "))
        with self.assertRaises(ValueError):
            parse_tanggal("31-02-2026")


if __name__ == "__main__":
    unittest.main()
