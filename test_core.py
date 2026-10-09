"""Jalankan: python -m unittest test_core"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from core import (BATAL, BERJALAN, DUKUNG, KKP, LEWAT_TENGGAT, OUTPUT, SELESAI, ST, Arsip, Penugasan,
                  bersihkan, hari_kalender, hari_kerja, parse_tanggal, perlu_diingat)


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

    def test_data_baru_bolak_balik(self):
        p = self.arsip.buat(contoh(mulai=date(2026, 11, 3), sampai=date(2026, 11, 14), jumlah_hari=10,
                                   peran_saya="Ketua Tim", tim=[{"nama": "Budi", "peran": "Ketua Tim"}]))
        p.atur_tahap("Pelaksanaan", date(2026, 11, 4))
        p.ceklis["PKR"] = True
        p.atur_status(SELESAI, date(2026, 11, 20))
        self.arsip.simpan(p)
        q = self.arsip.pindai()[0][0]
        self.assertEqual((q.mulai, q.sampai, q.jumlah_hari), (date(2026, 11, 3), date(2026, 11, 14), 10))
        self.assertEqual(q.tim, [{"nama": "Budi", "peran": "Ketua Tim"}])
        self.assertEqual(q.tahap, "Pelaksanaan")
        self.assertEqual(q.tgl_tahap["Pelaksanaan"], "2026-11-04")
        self.assertIn("Persiapan", q.tgl_tahap)  # dicatat saat dibuat
        self.assertEqual(q.selesai_pada, date(2026, 11, 20))
        q.atur_status(BERJALAN)
        self.assertIsNone(q.selesai_pada)

    def test_json_lama_tetap_terbaca(self):
        p = Penugasan.dari_dict({"nomor_st": "1", "tanggal_st": "2026-11-03", "jenis": "Reviu", "judul": "X"})
        self.assertEqual((p.tim, p.tahap, p.ceklis, p.jumlah_hari), ([], "Persiapan", {}, None))

    def test_ceklis_otomatis(self):
        p = self.arsip.buat(contoh())
        self.arsip.lampirkan(p, ST, self.berkas("st.pdf"))
        self.arsip.lampirkan(p, KKP, self.berkas("PKR Reviu RKA.docx"))
        self.arsip.lampirkan(p, OUTPUT, self.berkas("x.pdf"), p.nama_output("Konsep LHR", ".pdf"))
        hasil = {label: (ok, oto) for label, ok, oto in p.butir_ceklis(self.root)}
        self.assertEqual(hasil["Surat tugas"], (True, True))
        self.assertEqual(hasil["Program kerja reviu (PKR)"], (True, True))
        self.assertEqual(hasil["Konsep LHR"], (True, True))
        self.assertEqual(hasil["LHR final"], (False, False))  # konsep tidak dihitung final
        p.ceklis["LHR final"] = True
        hasil = {label: (ok, oto) for label, ok, oto in p.butir_ceklis(self.root)}
        self.assertEqual(hasil["LHR final"], (True, False))

    def test_ceklis_json_menimpa_bawaan(self):
        (self.root / "ceklis.json").write_text('{"Reviu": [["Notisi", "kkp", "notisi"]]}', encoding="utf-8")
        p = self.arsip.buat(contoh())
        self.assertEqual([label for label, _, _ in p.butir_ceklis(self.root)], ["Notisi"])

    def test_pengingat(self):
        hari = date(2026, 11, 10)
        a = contoh(judul="A", tenggat=date(2026, 11, 8))
        b = contoh(judul="B", tenggat=date(2026, 11, 13))
        c = contoh(judul="C", tenggat=date(2026, 11, 20))
        d = contoh(judul="D", tenggat=date(2026, 11, 1), status=SELESAI)
        lewat, segera = perlu_diingat([a, b, c, d], hari, h=3)
        self.assertEqual([p.judul for p in lewat], ["A"])
        self.assertEqual([p.judul for p in segera], ["B"])

    def test_nomor_kembar(self):
        p = self.arsip.buat(contoh())
        self.arsip.buat(contoh(judul="Lain", nomor_st="700/9/2026"))
        self.assertEqual(len(self.arsip.cari_nomor(" 700/123/itda/2026")), 1)
        self.assertEqual(self.arsip.cari_nomor("700/123/Itda/2026", kecuali=p.folder), [])

    def test_hitung_hari(self):
        self.assertEqual(hari_kalender(date(2026, 11, 3), date(2026, 11, 14)), 12)
        self.assertEqual(hari_kerja(date(2026, 11, 3), date(2026, 11, 14)), 9)  # 3 Nov = Selasa
        self.assertIsNone(hari_kalender(date(2026, 11, 14), date(2026, 11, 3)))


if __name__ == "__main__":
    unittest.main()
