"""Tes pembaca surat tugas, rekap, dan pesan pengingat. Jalankan: python -m unittest"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pengingat
import rekap
from baca_st import baca_teks
from core import Arsip, Penugasan

CONTOH_ST = """PEMERINTAH KABUPATEN CONTOH
INSPEKTORAT DAERAH
SURAT TUGAS
NOMOR : 700.1.2.1 / 123 / ITDA / 2026
Dasar : 1. Peraturan Pemerintah Nomor 12 Tahun 2017 tentang Pembinaan dan Pengawasan;
MENUGASKAN:
Kepada :
1. Drs. Ahmad Fauzi, M.Si. NIP 197001011990031001 Penanggung Jawab
2. Siti Rahma, S.E. NIP 198005052005012002 Pengendali Teknis
3. Budi Santoso, S.Ak. NIP 199001012015031003 Ketua Tim
4. Dewi Lestari, S.E. NIP 199505052020122004 Anggota Tim
Untuk : Melaksanakan Reviu atas Rencana Kerja dan Anggaran pada Dinas Pendidikan Tahun Anggaran 2027
selama 10 (sepuluh) hari kerja mulai tanggal 3 s.d. 14 November 2026.
Ditetapkan di : Contoh
pada tanggal 30 Oktober 2026
"""


class TestBacaST(unittest.TestCase):
    def test_surat_tugas_lengkap(self):
        h = baca_teks(CONTOH_ST)
        self.assertEqual(h.nomor_st, "700.1.2.1/123/ITDA/2026")
        self.assertEqual(h.tanggal_st, date(2026, 10, 30))
        self.assertEqual(h.jenis, "Reviu")
        self.assertEqual(h.objek, "Dinas Pendidikan")
        self.assertTrue(h.judul.startswith("Reviu atas Rencana Kerja"))
        self.assertEqual(h.jumlah_hari, 10)
        self.assertEqual((h.mulai, h.sampai), (date(2026, 11, 3), date(2026, 11, 14)))
        self.assertEqual([a["peran"] for a in h.tim],
                         ["Penanggung Jawab", "Pengendali Teknis", "Ketua Tim", "Anggota Tim"])
        self.assertEqual(h.tim[1]["nama"], "Siti Rahma, S.E.")

    def test_teks_kosong(self):
        self.assertEqual(baca_teks("").terisi(), [])

    def test_periode_lintas_bulan(self):
        h = baca_teks("Untuk: audit kinerja pada RSUD selama 5 hari, tanggal 28 Oktober s.d. 3 November 2026")
        self.assertEqual((h.mulai, h.sampai), (date(2026, 10, 28), date(2026, 11, 3)))
        self.assertEqual(h.jenis, "Audit")


class TestRekap(unittest.TestCase):
    def test_xlsx_dan_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            arsip = Arsip(Path(tmp) / "a")
            arsip.root.mkdir()
            p = arsip.buat(Penugasan("700/1", date(2026, 11, 3), "Reviu", "Reviu RKA", "Dinas X",
                                     tim=[{"nama": "Budi", "peran": "Ketua Tim"}], jumlah_hari=10))
            hasil = rekap.simpan([p], Path(tmp) / "r.xlsx")
            self.assertTrue(hasil.exists())
            if rekap.Workbook:
                from openpyxl import load_workbook
                ws = load_workbook(hasil).active
                kepala = [c.value for c in ws[4]]
                baris = dict(zip(kepala, [c.value for c in ws[5]]))
                self.assertEqual(baris["Judul"], "Reviu RKA")
                self.assertEqual(baris["Tim"], "Budi (Ketua Tim)")
                self.assertEqual(baris["Jumlah Hari"], 10)
            rekap._csv([p], Path(tmp) / "r.csv")
            self.assertIn("Reviu RKA", (Path(tmp) / "r.csv").read_text(encoding="utf-8-sig"))


class TestPesanPengingat(unittest.TestCase):
    def test_susun(self):
        hari = date(2026, 11, 10)
        a = Penugasan("1", date(2026, 11, 1), "Reviu", "A", tenggat=date(2026, 11, 8))
        b = Penugasan("2", date(2026, 11, 1), "Reviu", "B", tenggat=date(2026, 11, 11))
        judul, baris = pengingat.susun_pesan([a], [b], hari)
        self.assertIn("1 lewat tenggat", judul)
        self.assertEqual(baris, ["A — lewat 2 hari", "B — besok"])
        self.assertIsNone(pengingat.susun_pesan([], [], hari))


if __name__ == "__main__":
    unittest.main()
