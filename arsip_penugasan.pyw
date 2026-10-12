"""Arsip Penugasan — aplikasi desktop untuk menyimpan surat tugas, kertas kerja,
data dukung, dan output tiap penugasan ke struktur folder yang tetap.

Jalankan dengan `Buka Arsip Penugasan.bat` (atau `pythonw arsip_penugasan.pyw`).
Tampilan ada di tema.py. Pustaka tambahan (requirements.txt) bersifat opsional:
tanpa tkinterdnd2 tidak ada seret-lepas, tanpa pypdf tidak ada isi otomatis dari
PDF, tanpa openpyxl rekap ditulis sebagai CSV.
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import baca_st  # noqa: E402
import konfig  # noqa: E402
import pengingat  # noqa: E402
import rekap  # noqa: E402
import tema as T  # noqa: E402
from core import (VERSI, BATAL, BERJALAN, DUKUNG, JENIS, JENIS_OUTPUT, KKP, LABEL, LEWAT_TENGGAT,  # noqa: E402
                  OUTPUT, PERAN, SELESAI, ST, STATUS, SUBFOLDER, TAHAP, Arsip, Penugasan, bersihkan,
                  format_tanggal, hari_kalender, hari_kerja, parse_tanggal, perlu_diingat)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BaseTk = TkinterDnD.Tk
except Exception:  # pustaka tidak terpasang / tkdnd gagal dimuat
    DND_FILES = None
    BaseTk = tk.Tk

SEMUA = "Semua"
BELUM_OUTPUT = "Belum ada output"
PERHATIAN = "Perlu perhatian"  # dipakai spanduk pengingat, tidak punya chip sendiri
BRAND = "Q Studio · Sistem Arsip"
TAHAP_PENDEK = {"Persiapan": "PERSIAPAN", "Pelaksanaan": "PELAKSANAAN", "Konsep Laporan": "KONSEP",
                "Laporan Final": "FINAL"}

WARNA_STATUS = {BERJALAN: T.ACCENT, LEWAT_TENGGAT: T.DANGER, SELESAI: T.GOOD, BATAL: T.MUTED}


def pendek(path: Path, maks: int = 42) -> str:
    """Path panjang dipotong dari depan, mis. `…/OneDrive/Penugasan`."""
    teks = str(path)
    if len(teks) <= maks:
        return teks
    bagian = Path(teks).parts
    hasil = bagian[-1]
    for b in reversed(bagian[:-1]):
        if len(hasil) + len(b) + 3 > maks:
            break
        hasil = b + os.sep + hasil
    return "…" + os.sep + hasil


def buka(path: Path) -> None:
    os.startfile(path)  # Windows


def jadikan_target(widget: tk.Widget, saat_drop, sorot=None) -> None:
    """Daftarkan `widget` sebagai tempat seret-lepas berkas dari Explorer.
    `saat_drop(list[Path])` dipanggil sesudah handler DnD selesai, jadi aman membuka dialog."""
    if not DND_FILES:
        return
    widget.drop_target_register(DND_FILES)

    def drop(e):
        if sorot:
            sorot(False)
        paths = [Path(p) for p in widget.tk.splitlist(e.data)]
        widget.after_idle(lambda: saat_drop(paths))
        return e.action

    def masuk(e):
        sorot(True)
        return e.action

    def keluar(e):
        sorot(False)
        return e.action

    widget.dnd_bind("<<Drop>>", drop)
    if sorot:
        widget.dnd_bind("<<DropEnter>>", masuk)
        widget.dnd_bind("<<DropLeave>>", keluar)


def teks_sisa(p: Penugasan) -> str:
    sisa = p.sisa_hari()
    if sisa is None:
        return ""
    return "tenggat " + pengingat.sisa_teks(sisa)


# ---------------------------------------------------------------------------
# Komponen formulir
# ---------------------------------------------------------------------------
class Form(tk.Frame):
    """Kisi isian: label mono di atas isian (seperti `.field` tracker), bisa dua per baris."""

    def __init__(self, master, kolom: int = 2, bg: str = T.BG):
        super().__init__(master, bg=bg)
        for c in range(kolom):
            self.columnconfigure(c, weight=1, uniform="k")
        self.kolom = kolom
        self._baris = 0

    def field(self, label: str, widget_fn, kolom: int = 0, span: int | None = None):
        span = span or self.kolom
        sel = tk.Frame(self, bg=self["bg"])
        sel.grid(row=self._baris, column=kolom, columnspan=span, sticky="ew", pady=5,
                 padx=(0 if kolom == 0 else 6, 0 if kolom + span >= self.kolom else 6))
        T.label_field(sel, label, bg=self["bg"]).pack(fill="x", pady=(0, 4))
        w = widget_fn(sel)
        w.pack(fill="x")
        if kolom + span >= self.kolom:
            self._baris += 1
        return w

    def tambah(self, widget: tk.Widget, **grid) -> tk.Widget:
        widget.grid(row=self._baris, column=0, columnspan=self.kolom, sticky="ew", **grid)
        self._baris += 1
        return widget


class EditorTim(tk.Frame):
    """Daftar anggota tim (peran + nama) dengan baris tambah/hapus."""

    def __init__(self, master, tim: list[dict]):
        super().__init__(master, bg=T.BG)
        bingkai = tk.Frame(self, bg=T.SURFACE, highlightthickness=1, highlightbackground=T.BORDER)
        bingkai.pack(fill="x")
        self.tree = ttk.Treeview(bingkai, columns=("peran", "nama"), show="headings", height=5,
                                 selectmode="browse")
        self.tree.heading("peran", text="PERAN")
        self.tree.heading("nama", text="NAMA")
        self.tree.column("peran", width=T.px(130), stretch=False)
        self.tree.column("nama", width=T.px(200))
        self.tree.pack(fill="x")
        self.tree.bind("<Delete>", lambda _e: self.hapus())
        baris = tk.Frame(self, bg=T.BG)
        baris.pack(fill="x", pady=(6, 0))
        self.v_peran = tk.StringVar(value=PERAN[-1])
        self.v_nama = tk.StringVar()
        ttk.Combobox(baris, textvariable=self.v_peran, values=PERAN, width=16).pack(side="left")
        e = T.entri(baris, self.v_nama, 16)
        e.pack(side="left", fill="x", expand=True, padx=6)
        e.bind("<Return>", lambda _e: (self.tambah(), "break")[1])
        ttk.Button(baris, text="＋", width=3, command=self.tambah).pack(side="left")
        ttk.Button(baris, text="−", width=3, style="Ghost.TButton", command=self.hapus).pack(side="left", padx=(6, 0))
        self.isi(tim)

    def tambah(self):
        nama = self.v_nama.get().strip()
        if nama:
            self.tree.insert("", "end", values=(self.v_peran.get().strip() or PERAN[-1], nama))
            self.v_nama.set("")

    def hapus(self):
        for i in self.tree.selection():
            self.tree.delete(i)

    def isi(self, tim: list[dict]):
        self.tree.delete(*self.tree.get_children())
        for a in tim:
            self.tree.insert("", "end", values=(a.get("peran", ""), a.get("nama", "")))

    def kosong(self) -> bool:
        return not self.tree.get_children()

    def get(self) -> list[dict]:
        self.tambah()  # nama yang sudah diketik tapi belum ditambahkan ikut tersimpan
        return [{"peran": v[0], "nama": v[1]} for v in (self.tree.item(i, "values") for i in self.tree.get_children())]


class Dialog(tk.Toplevel):
    """Kerangka dialog bertema: kepala hero, badan, baris tombol Batal/aksi."""

    def __init__(self, master, judul: str, aksi: str):
        super().__init__(master)
        self.title(judul)
        self.configure(bg=T.BG)
        self.transient(master)
        self.resizable(False, False)
        T.hero(self, BRAND, judul)
        self.badan = tk.Frame(self, bg=T.BG)
        self.badan.pack(fill="both", padx=20, pady=(14, 4))
        bawah = tk.Frame(self, bg=T.BG)
        bawah.pack(fill="x", padx=20, pady=(8, 18))
        ttk.Button(bawah, text=aksi.upper(), style="Primary.TButton", command=self.ok).pack(side="right")
        ttk.Button(bawah, text="BATAL", style="Ghost.TButton", command=self.destroy).pack(side="right", padx=8)
        self.bind("<Return>", lambda _e: self.ok())
        self.bind("<Escape>", lambda _e: self.destroy())

    def tampil(self, fokus: tk.Widget):
        T.judul_gelap(self)
        fokus.focus_set()
        self.grab_set()

    def ok(self):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Dialog isian penugasan (baru / ubah)
# ---------------------------------------------------------------------------
class DialogPenugasan(Dialog):
    def __init__(self, master, arsip: Arsip, p: Penugasan | None = None, st_awal: Path | None = None):
        super().__init__(master, "Ubah Penugasan" if p else "Penugasan Baru", "Simpan")
        self.arsip = arsip
        self.p = p
        self.hasil: tuple[Penugasan, Path | None] | None = None
        self.disentuh: set[str] = set()  # isian yang diketik pengguna — tidak ditimpa isi otomatis PDF

        sv = tk.StringVar
        self.v_nomor = sv(value=p.nomor_st if p else "")
        self.v_tgl = sv(value=format_tanggal(p.tanggal_st if p else date.today()))
        self.v_jenis = sv(value=p.jenis if p else JENIS[1])
        self.v_objek = sv(value=p.objek if p else "")
        self.v_judul = sv(value=p.judul if p else "")
        self.v_tenggat = sv(value=format_tanggal(p.tenggat) if p else "")
        self.v_catatan = sv(value=p.catatan if p else "")
        self.v_status = sv(value=p.status if p else BERJALAN)
        self.v_tahap = sv(value=p.tahap if p else TAHAP[0])
        self.v_mulai = sv(value=format_tanggal(p.mulai) if p else "")
        self.v_sampai = sv(value=format_tanggal(p.sampai) if p else "")
        self.v_hari = sv(value=str(p.jumlah_hari) if p and p.jumlah_hari else "")
        self.v_peran = sv(value=p.peran_saya if p else "")
        self.v_st = sv()
        self.v_preview = sv()
        self.v_info = sv()
        self.v_durasi = sv()
        # Judul diisi otomatis dari jenis + objek sampai pengguna mengetiknya sendiri.
        self.judul_manual = p is not None

        kiri = Form(self.badan)
        kiri.pack(side="left", fill="y", anchor="n")
        tk.Frame(self.badan, bg=T.BORDER, width=1).pack(side="left", fill="y", padx=20)
        kanan = Form(self.badan)
        kanan.pack(side="left", fill="y", anchor="n")

        # --- kiri: data surat tugas
        kiri.tambah(T.sub(kiri, "Surat tugas", bg=T.BG), pady=(0, 4))
        e_nomor = self.awasi(kiri.field("Nomor surat tugas", lambda m: T.entri(m, self.v_nomor, 44)), "nomor")
        self.awasi(kiri.field("Tanggal ST · DD-MM-YYYY", lambda m: T.entri(m, self.v_tgl, 18), 0, 1), "tgl")
        self.awasi(kiri.field("Jenis penugasan", lambda m: ttk.Combobox(m, textvariable=self.v_jenis, values=JENIS),
                              1, 1), "jenis")
        self.awasi(kiri.field("Objek / auditi", lambda m: T.entri(m, self.v_objek)), "objek")
        e_judul = self.awasi(kiri.field("Judul penugasan", lambda m: T.entri(m, self.v_judul)), "judul")
        if not p:
            def pilih_st(m):
                box = tk.Frame(m, bg=T.BG)
                e = T.entri(box, self.v_st, state="readonly")
                e.pack(side="left", fill="x", expand=True)
                ttk.Button(box, text="PILIH…", command=self.pilih_st).pack(side="left", padx=(6, 0))
                jadikan_target(e, lambda paths: self.set_st(paths[0]),
                               lambda on: e.configure(highlightbackground=T.ACCENT if on else T.BORDER))
                return box
            label = "Berkas surat tugas · bisa diseret ke sini" if DND_FILES else "Berkas surat tugas"
            kiri.field(label, pilih_st)
            kiri.tambah(tk.Label(kiri, textvariable=self.v_info, bg=T.BG, fg=T.ACCENT, font=T.MONO_S,
                                 anchor="w", justify="left", wraplength=T.px(400)))
        kartu = T.Kartu(kiri, pad=12)
        kiri.tambah(kartu, pady=(10, 0))
        T.label_field(kartu.isi, "Disimpan di", bg=T.SURFACE).pack(fill="x")
        tk.Label(kartu.isi, textvariable=self.v_preview, bg=T.SURFACE, fg=T.ACCENT, font=T.MONO,
                 anchor="w", justify="left", wraplength=T.px(380)).pack(fill="x", pady=(4, 0))

        # --- kanan: pelaksanaan & tim
        kanan.tambah(T.sub(kanan, "Pelaksanaan", bg=T.BG), pady=(0, 4))
        self.awasi(kanan.field("Mulai", lambda m: T.entri(m, self.v_mulai, 18), 0, 1), "mulai")
        self.awasi(kanan.field("Sampai", lambda m: T.entri(m, self.v_sampai, 18), 1, 1), "sampai")
        kanan.tambah(tk.Label(kanan, textvariable=self.v_durasi, bg=T.BG, fg=T.DIM, font=T.MONO_S, anchor="w"))
        self.awasi(kanan.field("Jumlah hari (sesuai ST)", lambda m: T.entri(m, self.v_hari), 0, 1), "hari")
        kanan.field("Tenggat · opsional", lambda m: T.entri(m, self.v_tenggat), 1, 1)
        kanan.field("Peran saya", lambda m: ttk.Combobox(m, textvariable=self.v_peran, values=PERAN))
        self.tim = kanan.field("Tim", lambda m: EditorTim(m, p.tim if p else []))
        kanan.field("Catatan", lambda m: T.entri(m, self.v_catatan))
        if p:
            kanan.field("Status", lambda m: ttk.Combobox(m, textvariable=self.v_status, values=STATUS,
                                                         state="readonly"), 0, 1)
            kanan.field("Tahap", lambda m: ttk.Combobox(m, textvariable=self.v_tahap, values=TAHAP,
                                                        state="readonly"), 1, 1)

        e_judul.bind("<Key>", lambda _e: setattr(self, "judul_manual", True), add="+")
        for v in (self.v_jenis, self.v_objek):
            v.trace_add("write", lambda *_: self.isi_judul_otomatis())
        for v in (self.v_tgl, self.v_judul):
            v.trace_add("write", lambda *_: self.perbarui_preview())
        for v in (self.v_mulai, self.v_sampai):
            v.trace_add("write", lambda *_: self.perbarui_durasi())
        self.perbarui_preview()
        self.perbarui_durasi()
        if st_awal:
            self.set_st(st_awal)
        self.tampil(e_nomor)

    def awasi(self, w: tk.Widget, nama: str) -> tk.Widget:
        w.bind("<Key>", lambda _e: self.disentuh.add(nama), add="+")
        w.bind("<<ComboboxSelected>>", lambda _e: self.disentuh.add(nama), add="+")
        return w

    def isi_judul_otomatis(self):
        if not self.judul_manual:
            self.v_judul.set(" ".join(x for x in (self.v_jenis.get().strip(), self.v_objek.get().strip()) if x))

    def perbarui_preview(self):
        try:
            tgl = parse_tanggal(self.v_tgl.get())
        except ValueError:
            tgl = None
        judul = bersihkan(self.v_judul.get())
        if tgl and judul:
            self.v_preview.set(str(Penugasan("", tgl, "", judul).path_relatif()))
        else:
            self.v_preview.set("— isi tanggal dan judul —")

    def perbarui_durasi(self):
        try:
            m, s = parse_tanggal(self.v_mulai.get()), parse_tanggal(self.v_sampai.get())
        except ValueError:
            m = s = None
        k = hari_kalender(m, s)
        self.v_durasi.set(f"→ {k} HARI KALENDER · {hari_kerja(m, s)} HARI KERJA (SENIN–JUMAT)" if k else "")

    def pilih_st(self):
        path = filedialog.askopenfilename(parent=self, title="Pilih berkas surat tugas")
        if path:
            self.set_st(Path(path))

    def set_st(self, path: Path):
        if path.is_dir():
            messagebox.showerror("Bukan berkas", "Yang diseret adalah folder. Pilih berkas surat tugas.", parent=self)
            return
        self.v_st.set(str(path))
        self.isi_dari_pdf(path)

    def isi_dari_pdf(self, path: Path):
        if path.suffix.lower() != ".pdf":
            self.v_info.set("")
            return
        if baca_st.PdfReader is None:
            self.v_info.set("Isi otomatis tidak aktif: pustaka pypdf belum terpasang.")
            return
        h = baca_st.baca_pdf(path)
        terisi = []

        def isi(nama, var, nilai, teks, label):
            if nilai and nama not in self.disentuh:
                var.set(teks)
                terisi.append(label)

        isi("nomor", self.v_nomor, h.nomor_st, h.nomor_st, "nomor")
        isi("tgl", self.v_tgl, h.tanggal_st, format_tanggal(h.tanggal_st), "tanggal")
        isi("jenis", self.v_jenis, h.jenis, h.jenis, "jenis")
        isi("objek", self.v_objek, h.objek, h.objek, "objek")
        if h.judul and "judul" not in self.disentuh:
            self.v_judul.set(h.judul)
            self.judul_manual = True
            terisi.append("judul")
        isi("mulai", self.v_mulai, h.mulai, format_tanggal(h.mulai), "periode")
        isi("sampai", self.v_sampai, h.sampai, format_tanggal(h.sampai), "")
        isi("hari", self.v_hari, h.jumlah_hari, str(h.jumlah_hari), "jumlah hari")
        if h.tim and self.tim.kosong():
            self.tim.isi(h.tim)
            terisi.append(f"tim ({len(h.tim)} orang)")
        terisi = [t for t in terisi if t]
        if terisi:
            self.v_info.set("✓ TERISI DARI PDF: " + ", ".join(terisi).upper() + " — PERIKSA KEMBALI.")
        else:
            self.v_info.set("Tidak ada teks yang terbaca (PDF hasil scan?). Isi manual.")

    def ok(self):
        try:
            tgl = parse_tanggal(self.v_tgl.get())
            tenggat = parse_tanggal(self.v_tenggat.get())
            mulai = parse_tanggal(self.v_mulai.get())
            sampai = parse_tanggal(self.v_sampai.get())
        except ValueError as e:
            messagebox.showerror("Tanggal salah", str(e), parent=self)
            return
        judul = self.v_judul.get().strip()
        hari_teks = self.v_hari.get().strip()
        if not tgl:
            messagebox.showerror("Belum lengkap", "Tanggal surat tugas wajib diisi.", parent=self)
            return
        if not bersihkan(judul):
            messagebox.showerror("Belum lengkap", "Judul penugasan wajib diisi.", parent=self)
            return
        if hari_teks and not hari_teks.isdigit():
            messagebox.showerror("Jumlah hari", "Jumlah hari harus angka.", parent=self)
            return
        if mulai and sampai and sampai < mulai:
            messagebox.showerror("Periode", "Tanggal sampai lebih awal dari tanggal mulai.", parent=self)
            return
        if tenggat and tenggat < tgl and not messagebox.askyesno(
                "Periksa tenggat", "Tenggat lebih awal dari tanggal surat tugas. Lanjutkan?", parent=self):
            return
        nomor = self.v_nomor.get().strip()
        kembar = self.arsip.cari_nomor(nomor, kecuali=self.p.folder if self.p else None)
        if kembar and not messagebox.askyesno(
                "Nomor ST sudah dipakai",
                f"Nomor {nomor} sudah tercatat di:\n\n" + "\n".join(f"• {k.judul}" for k in kembar[:5])
                + "\n\nTetap simpan?", parent=self):
            return
        p = Penugasan(
            nomor_st=nomor, tanggal_st=tgl, jenis=self.v_jenis.get().strip(),
            judul=judul, objek=self.v_objek.get().strip(), tenggat=tenggat,
            catatan=self.v_catatan.get().strip(), mulai=mulai, sampai=sampai,
            jumlah_hari=int(hari_teks) if hari_teks else None,
            peran_saya=self.v_peran.get().strip(), tim=self.tim.get(),
        )
        if self.p:
            lama = self.p
            p.dibuat, p.folder, p.status, p.selesai_pada = lama.dibuat, lama.folder, lama.status, lama.selesai_pada
            p.tahap, p.tgl_tahap, p.ceklis = lama.tahap, dict(lama.tgl_tahap), dict(lama.ceklis)
            if self.v_status.get() != lama.status:
                p.atur_status(self.v_status.get())
            if self.v_tahap.get() != lama.tahap:
                p.atur_tahap(self.v_tahap.get())
        self.hasil = (p, Path(self.v_st.get()) if self.v_st.get() else None)
        self.destroy()


# ---------------------------------------------------------------------------
# Dialog lampirkan output
# ---------------------------------------------------------------------------
class DialogOutput(Dialog):
    def __init__(self, master, p: Penugasan, berkas: list[Path]):
        super().__init__(master, "Lampirkan Output", "Lampirkan")
        self.p = p
        self.berkas = berkas
        self.hasil: tuple[str, bool] | None = None
        self.v_jenis = tk.StringVar(value=p.output_default())
        self.v_selesai = tk.BooleanVar(value=p.status == BERJALAN)
        self.v_nama = tk.StringVar()

        f = Form(self.badan, kolom=1)
        f.pack(fill="x")
        cb = f.field(f"Jenis dokumen · {len(berkas)} berkas",
                     lambda m: ttk.Combobox(m, textvariable=self.v_jenis, values=JENIS_OUTPUT, width=46))
        kartu = T.Kartu(f, pad=12)
        f.tambah(kartu, pady=(10, 0))
        T.label_field(kartu.isi, "Nama berkas", bg=T.SURFACE).pack(fill="x")
        tk.Label(kartu.isi, textvariable=self.v_nama, bg=T.SURFACE, fg=T.ACCENT, font=T.MONO,
                 anchor="w", justify="left", wraplength=T.px(440)).pack(fill="x", pady=(4, 0))
        if p.status == BERJALAN:
            f.tambah(ttk.Checkbutton(f, text="TANDAI PENUGASAN SELESAI", variable=self.v_selesai), pady=(12, 0))

        self.v_jenis.trace_add("write", lambda *_: self.preview())
        self.preview()
        self.tampil(cb)

    def konsep(self) -> bool:
        return "konsep" in self.v_jenis.get().lower()

    def preview(self):
        jenis = self.v_jenis.get().strip() or "Output"
        nama = [self.p.nama_output(jenis, b.suffix.lower()) for b in self.berkas[:3]]
        if len(self.berkas) > 3:
            nama.append("…")
        self.v_nama.set("\n".join(nama))
        if self.p.status == BERJALAN:
            self.v_selesai.set(not self.konsep())  # konsep laporan belum berarti selesai

    def ok(self):
        jenis = self.v_jenis.get().strip()
        if not bersihkan(jenis):
            messagebox.showerror("Belum lengkap", "Jenis dokumen wajib diisi.", parent=self)
            return
        self.hasil = (jenis, self.v_selesai.get())
        self.destroy()


# ---------------------------------------------------------------------------
# Jendela utama
# ---------------------------------------------------------------------------
class App(BaseTk):
    KOLOM = [
        # Lebar awal; Judul & Objek melebar mengisi sisa ruang.
        ("tgl", "Tgl ST", 82), ("nomor", "Nomor ST", 120), ("judul", "Judul", 160),
        ("objek", "Objek", 90), ("jenis", "Jenis", 78), ("tenggat", "Tenggat", 82),
        ("status", "Status / Tahap", 112), ("st", "ST", 34), ("output", "Output", 52),
    ]
    FILTER = [SEMUA, BERJALAN, LEWAT_TENGGAT, BELUM_OUTPUT, SELESAI, BATAL]

    def __init__(self):
        super().__init__()
        self.title(f"Arsip Penugasan {VERSI}")
        # Di versi exe, berkas bawaan diekstrak ke sys._MEIPASS.
        ikon = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "ikon.ico"
        if ikon.exists():
            try:
                self.iconbitmap(default=str(ikon))  # default= ikut berlaku untuk dialog
            except tk.TclError:
                pass
        T.pasang(self)
        self.geometry(f"{T.px(1360)}x{T.px(800)}")
        self.minsize(T.px(1150), T.px(640))
        self.state("zoomed")
        self.ok = False
        self.cfg = konfig.muat()
        self.daftar: list[Penugasan] = []
        self.terpilih: Penugasan | None = None
        self.filter = SEMUA
        self.iid: dict[str, Penugasan] = {}

        root = self.cfg.get("root")
        if not root or not Path(root).is_dir():
            root = self.minta_root(pertama=True)
            if not root:
                self.destroy()
                return
        self.arsip = Arsip(Path(root))
        self.bangun()
        self.muat_ulang()
        self.after(100, lambda: T.judul_gelap(self))  # setelah jendela tampil
        self.after(300, self.perbarui_tombol_pengingat)
        self.ok = True

    # --- folder induk ---------------------------------------------------
    def minta_root(self, pertama=False) -> str | None:
        if pertama:
            self.withdraw()
            messagebox.showinfo(
                "Arsip Penugasan",
                "Pilih folder induk tempat semua penugasan disimpan.\n\n"
                "Di dalamnya akan dibuat folder Tahun › Bulan › Penugasan.\n"
                "Bisa diganti nanti lewat tombol \"Ganti\".")
        path = filedialog.askdirectory(parent=self, title="Pilih folder induk penugasan", mustexist=True)
        if pertama:
            self.deiconify()
        if path:
            self.cfg["root"] = path
            konfig.simpan(self.cfg)
        return path or None

    def ganti_root(self):
        path = self.minta_root()
        if path:
            self.arsip = Arsip(Path(path))
            self.v_root.set(pendek(self.arsip.root))
            self.muat_ulang()

    # --- tata letak -----------------------------------------------------
    def bangun(self):
        kanan, _ = T.hero(self, BRAND, "Arsip Penugasan")
        ttk.Button(kanan, text="＋ PENUGASAN BARU", style="Primary.TButton", command=self.baru).pack(side="right")
        ttk.Button(kanan, text="REKAP EXCEL", style="Ghost.TButton", command=self.buat_rekap).pack(
            side="right", padx=8)
        ttk.Button(kanan, text="MUAT ULANG", style="Ghost.TButton", command=self.muat_ulang).pack(side="right")
        ttk.Button(kanan, text="GANTI", style="Ghost.TButton", command=self.ganti_root).pack(side="right", padx=8)
        self.v_root = tk.StringVar(value=pendek(self.arsip.root))
        lbl = tk.Label(kanan, textvariable=self.v_root, bg=T.SURFACE_2, fg=T.MUTED, font=T.MONO, cursor="hand2")
        lbl.pack(side="right")
        lbl.bind("<Button-1>", lambda _e: buka(self.arsip.root))
        lbl.bind("<Enter>", lambda _e: lbl.configure(fg=T.ACCENT))
        lbl.bind("<Leave>", lambda _e: lbl.configure(fg=T.MUTED))
        tk.Label(kanan, text="FOLDER INDUK", bg=T.SURFACE_2, fg=T.DIM, font=T.MONO_S).pack(side="right", padx=6)

        # Spanduk pengingat (dipasang/dilepas oleh perbarui_spanduk).
        self.spanduk = tk.Frame(self, bg=T.BG, cursor="hand2")
        self.spanduk_garis = tk.Frame(self.spanduk, width=T.px(4))
        self.spanduk_garis.pack(side="left", fill="y")
        self.spanduk_teks = tk.Label(self.spanduk, bg=T.BG, font=T.MONO, anchor="w", justify="left")
        self.spanduk_teks.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        for w in (self.spanduk, self.spanduk_teks):
            w.bind("<Button-1>", lambda _e: self.set_filter(PERHATIAN))

        # Baris filter: elemen kanan dipasang dulu supaya tidak terdesak chip.
        self.filt = tk.Frame(self, bg=T.BG)
        self.filt.pack(fill="x", padx=18, pady=(14, 10))
        self.v_tahun = tk.StringVar(value=SEMUA)
        self.v_cari = tk.StringVar()
        T.entri(self.filt, self.v_cari, 22).pack(side="right")
        T.label_field(self.filt, "Cari").pack(side="right", padx=(14, 6))
        self.cb_tahun = ttk.Combobox(self.filt, textvariable=self.v_tahun, width=7, state="readonly")
        self.cb_tahun.pack(side="right")
        T.label_field(self.filt, "Tahun").pack(side="right", padx=(0, 6))
        self.chip: dict[str, ttk.Button] = {}
        for f in self.FILTER:
            b = ttk.Button(self.filt, style="Chip.TButton", command=lambda f=f: self.set_filter(f))
            b.pack(side="left", padx=(0, 6))
            self.chip[f] = b
        for v in (self.v_tahun, self.v_cari):
            v.trace_add("write", lambda *_: self.tampilkan())

        # Bilah status bawah.
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", side="bottom")
        tk.Frame(bar, bg=T.BORDER, height=1).pack(fill="x")
        self.v_bar = tk.StringVar()
        tk.Label(bar, textvariable=self.v_bar, bg=T.BG, fg=T.MUTED, font=T.MONO_S).pack(
            side="left", padx=18, pady=6)
        self.b_pengingat = ttk.Button(bar, style="Chip.TButton", text="PENGINGAT HARIAN · …",
                                      command=self.toggle_pengingat)
        self.b_pengingat.pack(side="right", padx=(0, 18), pady=4)
        self.v_pindah = tk.BooleanVar(value=self.cfg.get("pindahkan", False))
        ttk.Checkbutton(bar, text="PINDAHKAN BERKAS ASLI (BUKAN SALIN)", variable=self.v_pindah,
                        command=self.simpan_opsi).pack(side="right", padx=18)

        # Isi: daftar di kiri, panel detail di kanan.
        isi = tk.Frame(self, bg=T.BG)
        isi.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        isi.columnconfigure(0, weight=1)
        isi.rowconfigure(0, weight=1)

        bingkai = tk.Frame(isi, bg=T.SURFACE, highlightthickness=1, highlightbackground=T.BORDER)
        bingkai.grid(row=0, column=0, sticky="nsew")
        self.tree = ttk.Treeview(bingkai, columns=[k for k, _, _ in self.KOLOM], show="headings",
                                 selectmode="browse")
        for k, judul, lebar in self.KOLOM:
            self.tree.heading(k, text=judul.upper())
            self.tree.column(k, width=T.px(lebar),
                             minwidth=T.px(lebar if k in ("st", "output", "tgl", "tenggat") else 40),
                             stretch=k in ("judul", "objek"),
                             anchor="center" if k in ("st", "output", "tgl", "tenggat") else "w")
        self.tree.tag_configure("telat", foreground=T.DANGER)
        self.tree.tag_configure("segera", foreground=T.WARN)
        self.tree.tag_configure("selesai", foreground=T.MUTED)
        self.tree.tag_configure("batal", foreground=T.DIM)
        self.tree.tag_configure("selang", background="#0c1424")
        sb = ttk.Scrollbar(bingkai, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.pilih())
        self.tree.bind("<Double-1>", lambda _e: self.buka_folder())
        # Seret surat tugas ke daftar = penugasan baru dengan ST itu.
        jadikan_target(self.tree, self.drop_ke_daftar,
                       lambda on: bingkai.configure(highlightbackground=T.ACCENT if on else T.BORDER))

        luar = tk.Frame(isi, bg=T.BG, width=T.px(440))
        luar.grid(row=0, column=1, sticky="ns", padx=(14, 0))
        luar.pack_propagate(False)
        self.kartu = T.Kartu(luar, pad=16)
        self.kartu.pack(fill="both", expand=True)
        self.bangun_detail(self.kartu.isi)
        self.atur_chip()

    def bangun_detail(self, k: tk.Frame):
        S = T.SURFACE
        # Keadaan kosong
        self.kosong = tk.Frame(k, bg=S)
        tk.Label(self.kosong, text="PILIH PENUGASAN", bg=S, fg=T.TEXT, font=T.H2).pack(anchor="w")
        petunjuk = "Klik salah satu baris di daftar, atau buat baru\ndengan tombol ＋ Penugasan Baru."
        if DND_FILES:
            petunjuk += "\n\nSeret PDF surat tugas ke daftar untuk langsung\nmembuat penugasan baru dari berkas itu."
        tk.Label(self.kosong, text=petunjuk, bg=S, fg=T.MUTED, font=T.UI, justify="left").pack(anchor="w", pady=(6, 0))

        # Detail
        self.detail = tk.Frame(k, bg=S)
        self.l_status = tk.Label(self.detail, bg=S, font=T.MONO_S, anchor="w")
        self.l_status.pack(fill="x")
        self.l_judul = tk.Label(self.detail, bg=S, fg=T.TEXT, font=T.H2, anchor="w", justify="left",
                                wraplength=T.px(390))
        self.l_judul.pack(fill="x", pady=(4, 10))
        self.strip = T.StripLangkah(self.detail, 4)
        self.strip.pack(fill="x")

        kepala = tk.Frame(self.detail, bg=S)
        kepala.pack(fill="x", pady=(14, 8))
        T.sub(kepala, "Langkah").pack(side="left")
        if DND_FILES:
            tk.Label(kepala, text="SERET BERKAS KE TOMBOL", bg=S, fg=T.DIM, font=T.MONO_S).pack(side="right")
        tb = tk.Frame(self.detail, bg=S)
        tb.pack(fill="x")
        tb.columnconfigure(0, weight=1, uniform="t")
        tb.columnconfigure(1, weight=1, uniform="t")
        self.b_langkah: dict[str, ttk.Button] = {}
        self.gaya_langkah: dict[str, str] = {}
        for i, (kunci, nomor) in enumerate(((ST, "①"), (KKP, "②"), (DUKUNG, "③"), (OUTPUT, "④"))):
            b = ttk.Button(tb, command=lambda k=kunci: self.lampirkan(k))
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 3, 3 if i % 2 == 0 else 0),
                   pady=3)
            b._nomor = nomor  # type: ignore[attr-defined]
            self.b_langkah[kunci] = b
            jadikan_target(b, lambda paths, k=kunci: self.lampirkan(k, paths),
                           lambda on, k=kunci, b=b: b.configure(
                               style="Drop.TButton" if on else self.gaya_langkah.get(k, "TButton")))

        aksi = tk.Frame(self.detail, bg=S)
        aksi.pack(fill="x", side="bottom", pady=(10, 0))
        ttk.Button(aksi, text="BUKA FOLDER", style="Ghost.TButton", command=self.buka_folder).pack(
            side="left", fill="x", expand=True)
        ttk.Button(aksi, text="UBAH DATA", style="Ghost.TButton", command=self.ubah).pack(
            side="left", fill="x", expand=True, padx=6)
        self.b_status = ttk.Button(aksi, style="Ghost.TButton", command=self.toggle_selesai)
        self.b_status.pack(side="left", fill="x", expand=True)

        self.tab = ttk.Notebook(self.detail)
        self.tab.pack(fill="both", expand=True, pady=(12, 0))
        # Tiga tab pertama bisa digulir: isinya bisa lebih panjang dari ruang yang tersedia.
        self.gulir = [T.Gulir(self.tab) for _ in range(3)]
        for g in self.gulir:
            g.isi.configure(padx=4, pady=10)
        self.tab_ringkas, self.tab_tim, self.tab_progres = (g.isi for g in self.gulir)
        self.tab_berkas = tk.Frame(self.tab, bg=S, padx=0, pady=6)
        for f, nama in ((self.gulir[0], "RINGKASAN"), (self.gulir[1], "TIM"),
                        (self.gulir[2], "PROGRES"), (self.tab_berkas, "BERKAS")):
            self.tab.add(f, text=nama)

        # Ringkasan
        meta = self.tab_ringkas
        meta.columnconfigure(0, weight=1, uniform="m")
        meta.columnconfigure(1, weight=1, uniform="m")
        self.meta: dict[str, tk.Label] = {}
        for i, (kunci, label) in enumerate([
                ("nomor", "Nomor ST"), ("tgl", "Tanggal ST"), ("jenis", "Jenis"), ("objek", "Objek"),
                ("periode", "Periode"), ("hari", "Jumlah hari"), ("tenggat", "Tenggat"), ("selesai", "Selesai"),
                ("catatan", "Catatan")]):
            sel = tk.Frame(meta, bg=S)
            sel.grid(row=i // 2, column=i % 2, columnspan=2 if kunci == "catatan" else 1, sticky="nw", pady=(0, 8))
            T.label_field(sel, label, bg=S).pack(anchor="w")
            v = tk.Label(sel, bg=S, fg=T.TEXT, font=T.UI, anchor="w", justify="left",
                         wraplength=T.px(380 if kunci == "catatan" else 185))
            v.pack(anchor="w")
            self.meta[kunci] = v

        # Tim — isinya dibangun ulang tiap ganti pilihan
        self.isi_tim = tk.Frame(self.tab_tim, bg=S)
        self.isi_tim.pack(fill="both", expand=True)

        # Progres: tahapan + ceklis
        T.label_field(self.tab_progres, "Tahap · klik untuk memindah", bg=S).pack(fill="x")
        tahap = tk.Frame(self.tab_progres, bg=S)
        tahap.pack(fill="x", pady=(4, 0))
        self.b_tahap: dict[str, ttk.Button] = {}
        self.l_tahap: dict[str, tk.Label] = {}
        for i, t in enumerate(TAHAP):
            tahap.columnconfigure(i, weight=1, uniform="th")
            b = ttk.Button(tahap, text=f"{i + 1} {TAHAP_PENDEK[t]}", style="Step.TButton",
                           command=lambda t=t: self.set_tahap(t))
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 2, 0))
            lbl = tk.Label(tahap, bg=S, fg=T.DIM, font=T.MONO_S)
            lbl.grid(row=1, column=i, pady=(2, 0))
            self.b_tahap[t], self.l_tahap[t] = b, lbl
        T.label_field(self.tab_progres, "Ceklis dokumen", bg=S).pack(fill="x", pady=(12, 4))
        self.isi_ceklis = tk.Frame(self.tab_progres, bg=S)
        self.isi_ceklis.pack(fill="x")
        tk.Label(self.tab_progres, bg=S, fg=T.DIM, font=T.MONO_S, justify="left", wraplength=T.px(380),
                 text="HIJAU = TERCENTANG OTOMATIS KARENA BERKASNYA ADA. DAFTAR BUTIR BISA DIUBAH "
                      "LEWAT CEKLIS.JSON DI FOLDER INDUK (LIHAT README).").pack(fill="x", pady=(8, 0))

        # Berkas
        bingkai = tk.Frame(self.tab_berkas, bg=S, highlightthickness=1, highlightbackground=T.BORDER)
        bingkai.pack(fill="both", expand=True)
        self.files = ttk.Treeview(bingkai, show="tree", selectmode="browse")
        self.files.column("#0", width=T.px(360))
        self.files.tag_configure("folder", foreground=T.MUTED, font=T.MONO_S)
        self.files.pack(fill="both", expand=True)
        self.files.bind("<Double-1>", lambda _e: self.buka_berkas())
        self.path_berkas: dict[str, Path] = {}

    def simpan_opsi(self):
        self.cfg["pindahkan"] = self.v_pindah.get()
        konfig.simpan(self.cfg)

    # --- data -----------------------------------------------------------
    def muat_ulang(self, pilih: Path | None = None):
        if not self.arsip.root.is_dir():
            messagebox.showerror("Folder tidak ada", f"Folder induk tidak ditemukan:\n{self.arsip.root}")
            self.daftar, galat = [], []
        else:
            self.daftar, galat = self.arsip.pindai()
        if galat:
            messagebox.showwarning("Sebagian tidak terbaca",
                                   "Berkas berikut rusak dan dilewati:\n\n"
                                   + "\n".join(f"{p}\n  {e}" for p, e in galat[:10]))
        tahun = sorted({str(p.tanggal_st.year) for p in self.daftar}, reverse=True)
        self.cb_tahun["values"] = [SEMUA, *tahun]
        if self.v_tahun.get() not in self.cb_tahun["values"]:
            self.v_tahun.set(SEMUA)
        pilih = pilih or (self.terpilih.folder if self.terpilih else None)
        self.perbarui_spanduk()
        self.tampilkan(pilih)

    def perbarui_spanduk(self):
        lewat, segera = perlu_diingat(self.daftar, h=pengingat.H_MINUS)
        if not lewat and not segera:
            self.spanduk.pack_forget()
            return
        warna, latar = (T.DANGER, "#1c0b12") if lewat else (T.WARN, "#1c1606")
        judul, baris = pengingat.susun_pesan(lewat, segera)
        teks = judul.replace("Arsip Penugasan: ", "⚠ ").upper() + "   ·   " + "   ·   ".join(baris)
        self.spanduk.configure(bg=latar)
        self.spanduk_garis.configure(bg=warna)
        self.spanduk_teks.configure(text=teks + "   ▸ TAMPILKAN", bg=latar, fg=warna)
        self.spanduk.pack(fill="x", padx=18, pady=(14, 0), before=self.filt)

    def set_filter(self, f: str):
        self.filter = f
        self.tampilkan()

    @staticmethod
    def kena_filter(p: Penugasan, f: str) -> bool:
        if f == SEMUA:
            return True
        if f == BELUM_OUTPUT:
            return p.status != BATAL and not p.punya(OUTPUT)
        if f == PERHATIAN:
            sisa = p.sisa_hari()
            return sisa is not None and sisa <= pengingat.H_MINUS
        return p.status_tampil() == f

    def cocok_teks(self, p: Penugasan) -> bool:
        if self.v_tahun.get() != SEMUA and str(p.tanggal_st.year) != self.v_tahun.get():
            return False
        q = self.v_cari.get().strip().lower()
        if q:
            teks = " ".join([p.nomor_st, p.judul, p.objek, p.jenis, p.catatan, p.nama_tim(), p.peran_saya]).lower()
            return all(kata in teks for kata in q.split())
        return True

    def atur_chip(self, jumlah: dict[str, int] | None = None):
        for f, b in self.chip.items():
            n = (jumlah or {}).get(f, 0)
            b.configure(text=f"{f.upper()}  {n}", style="ChipOn.TButton" if f == self.filter else "Chip.TButton")

    def tampilkan(self, pilih: Path | None = None):
        self.tree.delete(*self.tree.get_children())
        self.iid = {}
        dasar = [p for p in self.daftar if self.cocok_teks(p)]
        jumlah = {f: sum(self.kena_filter(p, f) for p in dasar) for f in self.FILTER}
        self.atur_chip(jumlah)
        lolos = {id(p) for p in dasar}
        n = 0
        for i, p in enumerate(self.daftar):
            if id(p) not in lolos or not self.kena_filter(p, self.filter):
                continue
            s = p.status_tampil()
            sisa = p.sisa_hari()
            warna = {LEWAT_TENGGAT: "telat", SELESAI: "selesai", BATAL: "batal"}.get(s)
            if s == BERJALAN and sisa is not None and sisa <= pengingat.H_MINUS:
                warna = "segera"
            tags = [t for t in (warna, "selang" if n % 2 else None) if t]
            n += 1
            iid = str(i)
            self.iid[iid] = p
            self.tree.insert("", "end", iid=iid, tags=tags, values=(
                format_tanggal(p.tanggal_st), p.nomor_st, p.judul, p.objek, p.jenis,
                format_tanggal(p.tenggat), (p.tahap if s == BERJALAN else s).upper(),
                "✓" if p.punya(ST) else "·", "✓" if p.punya(OUTPUT) else "·"))
            if pilih and p.folder and p.folder == pilih:
                self.tree.selection_set(iid)
                self.tree.see(iid)
        keterangan = "   ·   FILTER: PERLU PERHATIAN" if self.filter == PERHATIAN else ""
        self.v_bar.set(f"{len(self.daftar)} PENUGASAN TERSIMPAN   ·   DITAMPILKAN {len(self.iid)}{keterangan}")
        if not self.tree.selection():
            self.terpilih = None
            self.pilih()

    def pilih(self):
        sel = self.tree.selection()
        self.terpilih = self.iid.get(sel[0]) if sel else None
        self.isi_detail()

    def isi_detail(self):
        p = self.terpilih
        if not p:
            self.detail.pack_forget()
            self.kosong.pack(fill="both", expand=True)
            self.kartu.warna(T.ACCENT)
            return
        self.kosong.pack_forget()
        self.detail.pack(fill="both", expand=True)

        s = p.status_tampil()
        warna = WARNA_STATUS.get(s, T.ACCENT)
        sisa = p.sisa_hari()
        if s == BERJALAN and sisa is not None and sisa <= pengingat.H_MINUS:
            warna = T.WARN
        self.kartu.warna(warna)
        kepala = f"■ {s.upper()}" + (f" · {p.tahap.upper()}" if s in (BERJALAN, LEWAT_TENGGAT) else "")
        if teks_sisa(p):
            kepala += f" · {teks_sisa(p).upper()}"
        self.l_status.configure(text=kepala, fg=warna)
        self.l_judul.configure(text=p.judul)

        m = self.meta
        m["nomor"].configure(text=p.nomor_st or "—")
        m["tgl"].configure(text=format_tanggal(p.tanggal_st))
        m["jenis"].configure(text=p.jenis or "—")
        m["objek"].configure(text=p.objek or "—")
        if p.mulai and p.sampai:
            awal = p.mulai.strftime("%d-%m") if p.mulai.year == p.sampai.year else format_tanggal(p.mulai)
            periode = f"{awal} s.d. {format_tanggal(p.sampai)}"
        else:
            periode = format_tanggal(p.mulai or p.sampai) or "—"
        m["periode"].configure(text=periode)
        m["hari"].configure(text=f"{p.jumlah_hari} hari" if p.jumlah_hari else "—")
        m["tenggat"].configure(text=format_tanggal(p.tenggat) or "—",
                               fg=T.DANGER if s == LEWAT_TENGGAT else T.TEXT)
        m["selesai"].configure(text=format_tanggal(p.selesai_pada) or "—")
        m["catatan"].configure(text=p.catatan or "—")

        ada = {k: p.berkas(k) for k in (ST, KKP, DUKUNG, OUTPUT)}
        self.strip.atur([bool(ada[k]) for k in (ST, KKP, DUKUNG, OUTPUT)])
        for k, b in self.b_langkah.items():
            n = len(ada[k])
            teks = f"{b._nomor} {LABEL[k].upper()}"  # type: ignore[attr-defined]
            self.gaya_langkah[k] = "Done.TButton" if n else "TButton"
            b.configure(text=f"{teks}  ✓ {n}" if n else teks, style=self.gaya_langkah[k])
        self.b_status.configure(text="BUKA KEMBALI" if p.status != BERJALAN else "TANDAI SELESAI")

        self.isi_tab_tim(p)
        self.isi_tab_progres(p)
        for g in self.gulir:
            g.ke_atas()

        self.files.delete(*self.files.get_children())
        self.path_berkas.clear()
        for k in (ST, KKP, DUKUNG, OUTPUT):
            induk = self.files.insert("", "end", text=f"{SUBFOLDER[k].upper()}  ({len(ada[k])})",
                                      open=True, tags=("folder",))
            self.path_berkas[induk] = p.folder / SUBFOLDER[k]
            for b in ada[k]:
                self.path_berkas[self.files.insert(induk, "end", text=b.name)] = b

    def isi_tab_tim(self, p: Penugasan):
        S = T.SURFACE
        for w in self.isi_tim.winfo_children():
            w.destroy()
        T.label_field(self.isi_tim, "Peran saya", bg=S).pack(fill="x")
        tk.Label(self.isi_tim, text=p.peran_saya or "—", bg=S, fg=T.ACCENT, font=T.UI_B, anchor="w").pack(
            fill="x", pady=(2, 12))
        T.label_field(self.isi_tim, f"Susunan tim · {len(p.tim)} orang", bg=S).pack(fill="x", pady=(0, 4))
        if not p.tim:
            tk.Label(self.isi_tim, text="Belum ada data tim. Isi lewat UBAH DATA.", bg=S, fg=T.MUTED,
                     font=T.UI, anchor="w").pack(fill="x")
        for a in p.tim:
            baris = tk.Frame(self.isi_tim, bg=S)
            baris.pack(fill="x", pady=1)
            tk.Label(baris, text=a.get("peran", "").upper(), bg=S, fg=T.MUTED, font=T.MONO_S, width=18,
                     anchor="w").pack(side="left")
            tk.Label(baris, text=a.get("nama", ""), bg=S, fg=T.TEXT, font=T.UI, anchor="w").pack(side="left")

    def isi_tab_progres(self, p: Penugasan):
        idx = TAHAP.index(p.tahap) if p.tahap in TAHAP else 0
        for i, t in enumerate(TAHAP):
            gaya = "StepOn.TButton" if i == idx else ("StepDone.TButton" if i < idx else "Step.TButton")
            self.b_tahap[t].configure(style=gaya)
            tgl = p.tgl_tahap.get(t)
            self.l_tahap[t].configure(text=format_tanggal(date.fromisoformat(tgl)) if tgl and i <= idx else "")

        for w in self.isi_ceklis.winfo_children():
            w.destroy()
        for label, terpenuhi, otomatis in p.butir_ceklis(self.arsip.root):
            v = tk.BooleanVar(value=terpenuhi)
            cb = ttk.Checkbutton(self.isi_ceklis, text=label + ("  · berkas ada" if otomatis else ""), variable=v,
                                 style="Auto.TCheckbutton" if otomatis else "Surface.TCheckbutton",
                                 command=lambda l=label, v=v: self.set_ceklis(l, v.get()))
            if otomatis:
                cb.state(["disabled"])
            cb.pack(anchor="w", pady=1)

    def set_tahap(self, t: str):
        p = self.terpilih
        if not p or p.tahap == t:
            return
        # Mundur tahap: lupakan tanggal tahap-tahap sesudahnya supaya riwayatnya tetap masuk akal.
        for lanjut in TAHAP[TAHAP.index(t) + 1:]:
            p.tgl_tahap.pop(lanjut, None)
        p.atur_tahap(t)
        self.simpan_dan_muat(p)

    def set_ceklis(self, label: str, nilai: bool):
        p = self.terpilih
        if not p:
            return
        if nilai:
            p.ceklis[label] = True
        else:
            p.ceklis.pop(label, None)
        try:
            self.arsip.simpan(p)
        except OSError as e:
            messagebox.showerror("Gagal menyimpan", str(e))

    def simpan_dan_muat(self, p: Penugasan):
        try:
            self.arsip.simpan(p)
        except OSError as e:
            messagebox.showerror("Gagal menyimpan", str(e))
        tab = self.tab.index("current")
        self.muat_ulang(pilih=p.folder)
        self.tab.select(tab)

    # --- aksi -----------------------------------------------------------
    def drop_ke_daftar(self, paths: list[Path]):
        berkas = [p for p in paths if p.is_file()]
        if not berkas:
            return
        if len(berkas) > 1:
            messagebox.showinfo("Satu per satu",
                                "Untuk membuat penugasan baru, seret satu berkas surat tugas saja.\n"
                                f"Yang dipakai: {berkas[0].name}")
        self.baru(berkas[0])

    def baru(self, st_awal: Path | None = None):
        d = DialogPenugasan(self, self.arsip, st_awal=st_awal)
        self.wait_window(d)
        if not d.hasil:
            return
        p, st = d.hasil
        try:
            p = self.arsip.buat(p)
        except OSError as e:
            messagebox.showerror("Gagal membuat folder", str(e))
            return
        if st:
            try:
                self.arsip.lampirkan(p, ST, st, p.nama_surat_tugas(st.suffix.lower()), self.v_pindah.get())
            except OSError as e:
                messagebox.showerror("Folder dibuat, tapi surat tugas gagal disalin", str(e))
        self.v_cari.set("")
        self.filter = SEMUA
        self.muat_ulang(pilih=p.folder)

    def ubah(self):
        lama = self.terpilih
        if not lama:
            return
        d = DialogPenugasan(self, self.arsip, lama)
        self.wait_window(d)
        if not d.hasil:
            return
        p, _ = d.hasil
        try:
            self.arsip.ubah(p)
        except OSError as e:
            messagebox.showerror(
                "Gagal menyimpan",
                f"{e}\n\nKalau tanggal/judul diubah, foldernya perlu dipindah. Tutup dulu berkas "
                "atau jendela Explorer yang sedang membuka folder ini, lalu coba lagi.")
            return
        self.muat_ulang(pilih=p.folder)

    def lampirkan(self, kunci: str, paths: list[Path] | None = None):
        p = self.terpilih
        if not p:
            return
        if kunci == OUTPUT:
            self.lampirkan_output(paths)
            return
        if paths is None:
            if kunci == ST:
                path = filedialog.askopenfilename(parent=self, title="Pilih berkas surat tugas")
                paths = [Path(path)] if path else []
            else:
                paths = [Path(x) for x in filedialog.askopenfilenames(parent=self,
                                                                      title=f"Pilih berkas {LABEL[kunci]}")]
        if not paths:
            return
        if kunci == ST and p.punya(ST) and not messagebox.askyesno(
                "Sudah ada surat tugas",
                "Penugasan ini sudah punya surat tugas.\nTambahkan berkas lagi (mis. ST perubahan)?"):
            return
        try:
            for s in paths:
                nama = p.nama_surat_tugas(s.suffix.lower()) if kunci == ST else None
                self.arsip.lampirkan(p, kunci, s, nama, self.v_pindah.get())
        except OSError as e:
            messagebox.showerror("Gagal melampirkan", str(e))
        self.muat_ulang(pilih=p.folder)

    def lampirkan_output(self, paths: list[Path] | None = None):
        p = self.terpilih
        if not p:
            return
        if paths is None:
            paths = [Path(x) for x in filedialog.askopenfilenames(parent=self, title="Pilih berkas output")]
        if not paths:
            return
        d = DialogOutput(self, p, paths)
        self.wait_window(d)
        if not d.hasil:
            return
        jenis, selesai = d.hasil
        try:
            for s in paths:
                self.arsip.lampirkan(p, OUTPUT, s, p.nama_output(jenis, s.suffix.lower()), self.v_pindah.get())
            # Output menggeser tahap maju (tidak pernah mundur).
            tujuan = "Konsep Laporan" if "konsep" in jenis.lower() else "Laporan Final"
            if TAHAP.index(tujuan) > (TAHAP.index(p.tahap) if p.tahap in TAHAP else 0):
                p.atur_tahap(tujuan)
            if selesai:
                p.atur_status(SELESAI)
            self.arsip.simpan(p)
        except OSError as e:
            messagebox.showerror("Gagal melampirkan", str(e))
        self.muat_ulang(pilih=p.folder)

    def toggle_selesai(self):
        p = self.terpilih
        if not p:
            return
        if p.status == BERJALAN and not p.punya(OUTPUT) and not messagebox.askyesno(
                "Belum ada output", "Penugasan ini belum punya output. Tetap tandai selesai?"):
            return
        p.atur_status(SELESAI if p.status == BERJALAN else BERJALAN)
        self.simpan_dan_muat(p)

    def buka_folder(self):
        if self.terpilih and self.terpilih.folder:
            buka(self.terpilih.folder)

    def buka_berkas(self):
        sel = self.files.selection()
        if sel and sel[0] in self.path_berkas:
            buka(self.path_berkas[sel[0]])

    # --- rekap & pengingat ---------------------------------------------
    def buat_rekap(self):
        daftar = list(self.iid.values())
        if not daftar:
            messagebox.showinfo("Rekap", "Tidak ada penugasan yang ditampilkan untuk direkap.")
            return
        tahun = self.v_tahun.get()
        label = f"Tahun {tahun}" if tahun != SEMUA else "Semua Tahun"
        nama = f"Rekap Penugasan {label} ({format_tanggal(date.today())}).xlsx"
        path = filedialog.asksaveasfilename(parent=self, title="Simpan rekap", initialdir=str(self.arsip.root),
                                            initialfile=nama, defaultextension=".xlsx",
                                            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            hasil = rekap.simpan(daftar, Path(path), judul=f"Rekap Penugasan — {label}")
        except PermissionError:
            messagebox.showerror("Gagal menyimpan", "Berkas sedang terbuka di Excel. Tutup dulu, lalu coba lagi.")
            return
        except OSError as e:
            messagebox.showerror("Gagal menyimpan", str(e))
            return
        if messagebox.askyesno("Rekap tersimpan", f"{len(daftar)} penugasan direkap ke:\n{hasil}\n\nBuka sekarang?"):
            buka(hasil)

    def perbarui_tombol_pengingat(self):
        try:
            nyala = pengingat.aktif()
        except OSError:
            nyala = False
        self.b_pengingat.configure(text=f"PENGINGAT HARIAN · {'AKTIF' if nyala else 'NONAKTIF'}",
                                   style="ChipOn.TButton" if nyala else "Chip.TButton")

    def toggle_pengingat(self):
        if pengingat.aktif():
            if not messagebox.askyesno("Matikan pengingat",
                                       "Hapus tugas terjadwal pengingat harian dari Windows?"):
                return
            ok, pesan = pengingat.nonaktifkan()
        else:
            if not messagebox.askyesno(
                    "Aktifkan pengingat",
                    f"Pasang tugas terjadwal Windows \"{pengingat.TASK}\"?\n\n"
                    f"Tiap hari pukul {pengingat.JAM} (atau begitu komputer menyala bila terlewat) "
                    f"muncul notifikasi kalau ada penugasan yang lewat tenggat atau jatuh tempo "
                    f"≤ {pengingat.H_MINUS} hari — walaupun aplikasi ini tidak dibuka.\n\n"
                    "Bisa dimatikan lagi dari tombol yang sama."):
                return
            ok, pesan = pengingat.aktifkan()
        if not ok:
            messagebox.showerror("Gagal", pesan or "Perintah Task Scheduler gagal.")
        self.perbarui_tombol_pengingat()


if __name__ == "__main__":
    if "--pengingat" in sys.argv:  # dipanggil Task Scheduler (versi exe)
        sys.exit(pengingat.main())
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)  # teks tajam di layar ber-skala
    except Exception:
        pass
    app = App()
    if app.ok:
        app.mainloop()
