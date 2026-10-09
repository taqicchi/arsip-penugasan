"""Arsip Penugasan — aplikasi desktop untuk menyimpan surat tugas, kertas kerja,
data dukung, dan output tiap penugasan ke struktur folder yang tetap.

Jalankan dengan klik dua kali berkas ini (atau `pythonw arsip_penugasan.pyw`).
Hanya memakai pustaka standar Python.
"""
from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import (BATAL, BERJALAN, DUKUNG, JENIS, JENIS_OUTPUT, KKP, LABEL, LEWAT_TENGGAT,  # noqa: E402
                  OUTPUT, SELESAI, ST, STATUS, SUBFOLDER, Arsip, Penugasan, bersihkan,
                  format_tanggal, parse_tanggal)

CONFIG = Path(os.environ.get("APPDATA", Path.home())) / "ArsipPenugasan" / "config.json"

SEMUA = "Semua"
BELUM_OUTPUT = "Belum ada output"


def muat_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def simpan_config(cfg: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def buka(path: Path) -> None:
    os.startfile(path)  # Windows


# ---------------------------------------------------------------------------
# Dialog isian penugasan (baru / ubah)
# ---------------------------------------------------------------------------
class DialogPenugasan(tk.Toplevel):
    def __init__(self, master, arsip: Arsip, p: Penugasan | None = None):
        super().__init__(master)
        self.arsip = arsip
        self.p = p
        self.hasil: tuple[Penugasan, Path | None] | None = None
        self.title("Ubah Penugasan" if p else "Penugasan Baru")
        self.transient(master)
        self.resizable(False, False)

        f = ttk.Frame(self, padding=14)
        f.grid(sticky="nsew")
        f.columnconfigure(1, weight=1)

        self.v_nomor = tk.StringVar(value=p.nomor_st if p else "")
        self.v_tgl = tk.StringVar(value=format_tanggal(p.tanggal_st if p else date.today()))
        self.v_jenis = tk.StringVar(value=p.jenis if p else JENIS[1])
        self.v_objek = tk.StringVar(value=p.objek if p else "")
        self.v_judul = tk.StringVar(value=p.judul if p else "")
        self.v_tenggat = tk.StringVar(value=format_tanggal(p.tenggat) if p else "")
        self.v_catatan = tk.StringVar(value=p.catatan if p else "")
        self.v_status = tk.StringVar(value=p.status if p else BERJALAN)
        self.v_st = tk.StringVar()
        self.v_preview = tk.StringVar()
        # Judul diisi otomatis dari jenis + objek sampai pengguna mengetiknya sendiri.
        self.judul_manual = p is not None

        baris = 0

        def field(label, widget, ket=""):
            nonlocal baris
            ttk.Label(f, text=label).grid(row=baris, column=0, sticky="w", pady=3, padx=(0, 10))
            widget.grid(row=baris, column=1, sticky="ew", pady=3)
            if ket:
                ttk.Label(f, text=ket, foreground="gray").grid(row=baris, column=2, sticky="w", padx=6)
            baris += 1
            return widget

        e_nomor = field("Nomor surat tugas", ttk.Entry(f, textvariable=self.v_nomor, width=44))
        field("Tanggal surat tugas", ttk.Entry(f, textvariable=self.v_tgl, width=14), "DD-MM-YYYY")
        field("Jenis penugasan", ttk.Combobox(f, textvariable=self.v_jenis, values=JENIS))
        field("Objek / auditi", ttk.Entry(f, textvariable=self.v_objek))
        e_judul = field("Judul penugasan", ttk.Entry(f, textvariable=self.v_judul))
        field("Tenggat", ttk.Entry(f, textvariable=self.v_tenggat, width=14), "opsional")
        field("Catatan", ttk.Entry(f, textvariable=self.v_catatan))
        if p:
            field("Status", ttk.Combobox(f, textvariable=self.v_status, values=STATUS, state="readonly"))
        else:
            box = ttk.Frame(f)
            ttk.Entry(box, textvariable=self.v_st, state="readonly").pack(side="left", fill="x", expand=True)
            ttk.Button(box, text="Pilih…", command=self.pilih_st).pack(side="left", padx=(6, 0))
            field("Berkas surat tugas", box, "PDF/scan")

        ttk.Label(f, text="Disimpan di:").grid(row=baris, column=0, sticky="nw", pady=(10, 0))
        ttk.Label(f, textvariable=self.v_preview, foreground="#1a5fb4", wraplength=420,
                  justify="left").grid(row=baris, column=1, columnspan=2, sticky="w", pady=(10, 0))
        baris += 1

        tombol = ttk.Frame(f)
        tombol.grid(row=baris, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(tombol, text="Batal", command=self.destroy).pack(side="right")
        ttk.Button(tombol, text="Simpan", command=self.simpan).pack(side="right", padx=6)

        e_judul.bind("<Key>", lambda _e: setattr(self, "judul_manual", True))
        for v in (self.v_jenis, self.v_objek):
            v.trace_add("write", lambda *_: self.isi_judul_otomatis())
        for v in (self.v_tgl, self.v_judul):
            v.trace_add("write", lambda *_: self.perbarui_preview())
        self.perbarui_preview()

        self.bind("<Return>", lambda _e: self.simpan())
        self.bind("<Escape>", lambda _e: self.destroy())
        e_nomor.focus_set()
        self.grab_set()

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
            tmp = Penugasan("", tgl, "", judul)
            self.v_preview.set(str(tmp.path_relatif()))
        else:
            self.v_preview.set("(isi tanggal dan judul)")

    def pilih_st(self):
        path = filedialog.askopenfilename(parent=self, title="Pilih berkas surat tugas")
        if path:
            self.v_st.set(path)

    def simpan(self):
        try:
            tgl = parse_tanggal(self.v_tgl.get())
            tenggat = parse_tanggal(self.v_tenggat.get())
        except ValueError as e:
            messagebox.showerror("Tanggal salah", str(e), parent=self)
            return
        judul = self.v_judul.get().strip()
        if not tgl:
            messagebox.showerror("Belum lengkap", "Tanggal surat tugas wajib diisi.", parent=self)
            return
        if not bersihkan(judul):
            messagebox.showerror("Belum lengkap", "Judul penugasan wajib diisi.", parent=self)
            return
        if tenggat and tenggat < tgl:
            if not messagebox.askyesno("Periksa tenggat", "Tenggat lebih awal dari tanggal surat tugas. Lanjutkan?",
                                       parent=self):
                return
        p = Penugasan(
            nomor_st=self.v_nomor.get().strip(), tanggal_st=tgl, jenis=self.v_jenis.get().strip(),
            judul=judul, objek=self.v_objek.get().strip(), tenggat=tenggat,
            status=self.v_status.get(), catatan=self.v_catatan.get().strip(),
        )
        if self.p:
            p.dibuat, p.folder = self.p.dibuat, self.p.folder
        self.hasil = (p, Path(self.v_st.get()) if self.v_st.get() else None)
        self.destroy()


# ---------------------------------------------------------------------------
# Dialog lampirkan output
# ---------------------------------------------------------------------------
class DialogOutput(tk.Toplevel):
    def __init__(self, master, p: Penugasan, berkas: list[str]):
        super().__init__(master)
        self.p = p
        self.berkas = berkas
        self.hasil: tuple[str, bool] | None = None
        self.title("Lampirkan Output")
        self.transient(master)
        self.resizable(False, False)

        f = ttk.Frame(self, padding=14)
        f.grid()
        self.v_jenis = tk.StringVar(value=p.output_default())
        self.v_selesai = tk.BooleanVar(value=p.status == BERJALAN)
        self.v_nama = tk.StringVar()

        ttk.Label(f, text=f"{len(berkas)} berkas dipilih").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(f, text="Jenis dokumen").grid(row=1, column=0, sticky="w", pady=8, padx=(0, 10))
        cb = ttk.Combobox(f, textvariable=self.v_jenis, values=JENIS_OUTPUT, width=30)
        cb.grid(row=1, column=1, sticky="w")
        ttk.Label(f, text="Nama berkas:").grid(row=2, column=0, sticky="nw")
        ttk.Label(f, textvariable=self.v_nama, foreground="#1a5fb4", wraplength=380,
                  justify="left").grid(row=2, column=1, sticky="w")
        if p.status == BERJALAN:
            ttk.Checkbutton(f, text="Tandai penugasan selesai", variable=self.v_selesai).grid(
                row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        tombol = ttk.Frame(f)
        tombol.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(tombol, text="Batal", command=self.destroy).pack(side="right")
        ttk.Button(tombol, text="Lampirkan", command=self.ok).pack(side="right", padx=6)

        self.v_jenis.trace_add("write", lambda *_: self.preview())
        self.preview()
        self.bind("<Return>", lambda _e: self.ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        cb.focus_set()
        self.grab_set()

    def preview(self):
        jenis = self.v_jenis.get().strip() or "Output"
        nama = [self.p.nama_output(jenis, Path(b).suffix.lower()) for b in self.berkas[:3]]
        if len(self.berkas) > 3:
            nama.append("…")
        self.v_nama.set("\n".join(nama))

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
class App(tk.Tk):
    KOLOM = [
        ("tgl", "Tgl ST", 82), ("nomor", "Nomor ST", 150), ("judul", "Judul", 260),
        ("objek", "Objek", 140), ("jenis", "Jenis", 80), ("tenggat", "Tenggat", 82),
        ("status", "Status", 95), ("st", "ST", 32), ("output", "Output", 50),
    ]

    def __init__(self):
        super().__init__()
        self.title("Arsip Penugasan")
        self.geometry("1280x700")
        self.minsize(980, 520)
        self.ok = False
        self.cfg = muat_config()
        self.daftar: list[Penugasan] = []
        self.terpilih: Penugasan | None = None

        root = self.cfg.get("root")
        if not root or not Path(root).is_dir():
            root = self.minta_root(pertama=True)
            if not root:
                self.destroy()
                return
        self.arsip = Arsip(Path(root))
        self.bangun()
        self.muat_ulang()
        self.ok = True

    # --- folder induk ---------------------------------------------------
    def minta_root(self, pertama=False) -> str | None:
        if pertama:
            self.withdraw()
            messagebox.showinfo(
                "Arsip Penugasan",
                "Pilih folder induk tempat semua penugasan disimpan.\n\n"
                "Di dalamnya akan dibuat folder Tahun › Bulan › Penugasan.\n"
                "Bisa diganti nanti lewat tombol \"Ganti…\".")
        path = filedialog.askdirectory(parent=self, title="Pilih folder induk penugasan", mustexist=True)
        if pertama:
            self.deiconify()
        if path:
            self.cfg["root"] = path
            simpan_config(self.cfg)
        return path or None

    def ganti_root(self):
        path = self.minta_root()
        if path:
            self.arsip = Arsip(Path(path))
            self.v_root.set(str(self.arsip.root))
            self.muat_ulang()

    # --- tata letak -----------------------------------------------------
    def bangun(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=24)
        style.configure("Judul.TLabel", font=("Segoe UI", 12, "bold"))

        atas = ttk.Frame(self, padding=(10, 8))
        atas.pack(fill="x")
        ttk.Label(atas, text="Folder induk:").pack(side="left")
        self.v_root = tk.StringVar(value=str(self.arsip.root))
        lbl = ttk.Label(atas, textvariable=self.v_root, foreground="#1a5fb4", cursor="hand2")
        lbl.pack(side="left", padx=6)
        lbl.bind("<Button-1>", lambda _e: buka(self.arsip.root))
        ttk.Button(atas, text="Ganti…", command=self.ganti_root).pack(side="left")
        ttk.Button(atas, text="＋ Penugasan Baru", command=self.baru).pack(side="right")
        ttk.Button(atas, text="Muat ulang", command=self.muat_ulang).pack(side="right", padx=6)

        filt = ttk.Frame(self, padding=(10, 0, 10, 6))
        filt.pack(fill="x")
        self.v_tahun = tk.StringVar(value=SEMUA)
        self.v_status = tk.StringVar(value=SEMUA)
        self.v_cari = tk.StringVar()
        self.v_pindah = tk.BooleanVar(value=self.cfg.get("pindahkan", False))
        ttk.Label(filt, text="Tahun").pack(side="left")
        self.cb_tahun = ttk.Combobox(filt, textvariable=self.v_tahun, width=8, state="readonly")
        self.cb_tahun.pack(side="left", padx=(4, 12))
        ttk.Label(filt, text="Status").pack(side="left")
        ttk.Combobox(filt, textvariable=self.v_status, width=16, state="readonly",
                     values=[SEMUA, BERJALAN, LEWAT_TENGGAT, BELUM_OUTPUT, SELESAI, BATAL]
                     ).pack(side="left", padx=(4, 12))
        ttk.Label(filt, text="Cari").pack(side="left")
        ttk.Entry(filt, textvariable=self.v_cari, width=30).pack(side="left", padx=4)
        ttk.Checkbutton(filt, text="Pindahkan berkas asli (bukan salin)", variable=self.v_pindah,
                        command=self.simpan_opsi).pack(side="right")
        for v in (self.v_tahun, self.v_status, self.v_cari):
            v.trace_add("write", lambda *_: self.tampilkan())

        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        kiri = ttk.Frame(pane)
        self.tree = ttk.Treeview(kiri, columns=[k for k, _, _ in self.KOLOM], show="headings",
                                 selectmode="browse")
        for k, judul, lebar in self.KOLOM:
            self.tree.heading(k, text=judul)
            self.tree.column(k, width=lebar, stretch=k in ("judul", "objek"),
                             anchor="center" if k in ("st", "output", "tgl", "tenggat") else "w")
        self.tree.tag_configure("telat", foreground="#c01c28")
        self.tree.tag_configure("selesai", foreground="#5e5c64")
        self.tree.tag_configure("batal", foreground="#9a9996")
        sb = ttk.Scrollbar(kiri, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.pilih())
        self.tree.bind("<Double-1>", lambda _e: self.buka_folder())
        pane.add(kiri, weight=3)

        kanan = ttk.Frame(pane, padding=(10, 0, 0, 0))
        pane.add(kanan, weight=2)
        self.v_detail_judul = tk.StringVar(value="Pilih penugasan")
        self.v_detail = tk.StringVar()
        ttk.Label(kanan, textvariable=self.v_detail_judul, style="Judul.TLabel",
                  wraplength=420).pack(anchor="w")
        ttk.Label(kanan, textvariable=self.v_detail, justify="left", wraplength=420).pack(anchor="w", pady=(4, 8))

        tb = ttk.Frame(kanan)
        tb.pack(fill="x")
        self.tombol = [
            ttk.Button(tb, text="① Lampirkan Surat Tugas…", command=lambda: self.lampirkan(ST)),
            ttk.Button(tb, text="② Tambah Kertas Kerja…", command=lambda: self.lampirkan(KKP)),
            ttk.Button(tb, text="③ Tambah Data Dukung…", command=lambda: self.lampirkan(DUKUNG)),
            ttk.Button(tb, text="④ Lampirkan Output…", command=self.lampirkan_output),
            ttk.Button(tb, text="Buka Folder", command=self.buka_folder),
            ttk.Button(tb, text="Ubah Data…", command=self.ubah),
        ]
        for i, b in enumerate(self.tombol):
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        tb.columnconfigure(0, weight=1)
        tb.columnconfigure(1, weight=1)
        self.b_status = ttk.Button(tb, text="Tandai Selesai", command=self.toggle_selesai)
        self.b_status.grid(row=3, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        self.tombol.append(self.b_status)

        ttk.Label(kanan, text="Isi folder (klik dua kali untuk membuka):").pack(anchor="w", pady=(10, 2))
        self.files = ttk.Treeview(kanan, show="tree", selectmode="browse")
        self.files.pack(fill="both", expand=True)
        self.files.bind("<Double-1>", lambda _e: self.buka_berkas())
        self.path_berkas: dict[str, Path] = {}

        self.v_bar = tk.StringVar()
        ttk.Label(self, textvariable=self.v_bar, padding=(10, 2), relief="sunken").pack(fill="x", side="bottom")
        self.atur_tombol()

    def simpan_opsi(self):
        self.cfg["pindahkan"] = self.v_pindah.get()
        simpan_config(self.cfg)

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
        self.tampilkan(pilih)

    def cocok(self, p: Penugasan) -> bool:
        if self.v_tahun.get() != SEMUA and str(p.tanggal_st.year) != self.v_tahun.get():
            return False
        st = self.v_status.get()
        if st == BELUM_OUTPUT:
            if p.status == BATAL or p.punya(OUTPUT):
                return False
        elif st != SEMUA and p.status_tampil() != st:
            return False
        q = self.v_cari.get().strip().lower()
        if q:
            teks = " ".join([p.nomor_st, p.judul, p.objek, p.jenis, p.catatan]).lower()
            return all(kata in teks for kata in q.split())
        return True

    def tampilkan(self, pilih: Path | None = None):
        self.tree.delete(*self.tree.get_children())
        self.iid: dict[str, Penugasan] = {}
        jumlah = {BERJALAN: 0, LEWAT_TENGGAT: 0, SELESAI: 0}
        for i, p in enumerate(self.daftar):
            s = p.status_tampil()
            if s in jumlah:
                jumlah[s] += 1
            if not self.cocok(p):
                continue
            tag = {LEWAT_TENGGAT: "telat", SELESAI: "selesai", BATAL: "batal"}.get(s, "")
            iid = str(i)
            self.iid[iid] = p
            self.tree.insert("", "end", iid=iid, tags=(tag,), values=(
                format_tanggal(p.tanggal_st), p.nomor_st, p.judul, p.objek, p.jenis,
                format_tanggal(p.tenggat), s, "✓" if p.punya(ST) else "—",
                "✓" if p.punya(OUTPUT) else "—"))
            if pilih and p.folder and p.folder == pilih:
                self.tree.selection_set(iid)
                self.tree.see(iid)
        self.v_bar.set(f"{len(self.daftar)} penugasan · {jumlah[BERJALAN]} berjalan · "
                       f"{jumlah[LEWAT_TENGGAT]} lewat tenggat · {jumlah[SELESAI]} selesai"
                       f"   |   ditampilkan: {len(self.iid)}")
        if not self.tree.selection():
            self.terpilih = None
            self.pilih()

    def pilih(self):
        sel = self.tree.selection()
        self.terpilih = self.iid.get(sel[0]) if sel else None
        self.isi_detail()
        self.atur_tombol()

    def isi_detail(self):
        self.files.delete(*self.files.get_children())
        self.path_berkas.clear()
        p = self.terpilih
        if not p:
            self.v_detail_judul.set("Pilih penugasan")
            self.v_detail.set("Atau buat baru dengan tombol ＋ Penugasan Baru.")
            return
        self.v_detail_judul.set(p.judul)
        baris = [
            f"Nomor ST : {p.nomor_st or '—'}",
            f"Tanggal  : {format_tanggal(p.tanggal_st)}",
            f"Jenis    : {p.jenis or '—'}     Objek: {p.objek or '—'}",
            f"Tenggat  : {format_tanggal(p.tenggat) or '—'}     Status: {p.status_tampil()}",
        ]
        if p.catatan:
            baris.append(f"Catatan  : {p.catatan}")
        self.v_detail.set("\n".join(baris))
        for kunci in (ST, KKP, DUKUNG, OUTPUT):
            daftar = p.berkas(kunci)
            induk = self.files.insert("", "end", text=f"{SUBFOLDER[kunci]}  ({len(daftar)})", open=True)
            self.path_berkas[induk] = p.folder / SUBFOLDER[kunci]
            for b in daftar:
                iid = self.files.insert(induk, "end", text=b.name)
                self.path_berkas[iid] = b

    def atur_tombol(self):
        state = "normal" if self.terpilih else "disabled"
        for b in self.tombol:
            b.configure(state=state)
        if self.terpilih:
            self.b_status.configure(text="Buka Kembali (status Berjalan)" if self.terpilih.status != BERJALAN
                                    else "Tandai Selesai")

    # --- aksi -----------------------------------------------------------
    def baru(self):
        d = DialogPenugasan(self, self.arsip)
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

    def lampirkan(self, kunci: str):
        p = self.terpilih
        if not p:
            return
        if kunci == ST:
            if p.punya(ST) and not messagebox.askyesno(
                    "Sudah ada surat tugas",
                    "Penugasan ini sudah punya surat tugas.\nTambahkan berkas lagi (mis. ST perubahan)?"):
                return
            path = filedialog.askopenfilename(parent=self, title="Pilih berkas surat tugas")
            paths = [path] if path else []
        else:
            paths = list(filedialog.askopenfilenames(parent=self, title=f"Pilih berkas {LABEL[kunci]}"))
        if not paths:
            return
        try:
            for s in paths:
                s = Path(s)
                nama = p.nama_surat_tugas(s.suffix.lower()) if kunci == ST else None
                self.arsip.lampirkan(p, kunci, s, nama, self.v_pindah.get())
        except OSError as e:
            messagebox.showerror("Gagal melampirkan", str(e))
        self.muat_ulang(pilih=p.folder)

    def lampirkan_output(self):
        p = self.terpilih
        if not p:
            return
        paths = filedialog.askopenfilenames(parent=self, title="Pilih berkas output")
        if not paths:
            return
        d = DialogOutput(self, p, list(paths))
        self.wait_window(d)
        if not d.hasil:
            return
        jenis, selesai = d.hasil
        try:
            for s in paths:
                s = Path(s)
                self.arsip.lampirkan(p, OUTPUT, s, p.nama_output(jenis, s.suffix.lower()), self.v_pindah.get())
            if selesai:
                p.status = SELESAI
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
        p.status = SELESAI if p.status == BERJALAN else BERJALAN
        try:
            self.arsip.simpan(p)
        except OSError as e:
            messagebox.showerror("Gagal menyimpan", str(e))
        self.muat_ulang(pilih=p.folder)

    def buka_folder(self):
        if self.terpilih and self.terpilih.folder:
            buka(self.terpilih.folder)

    def buka_berkas(self):
        sel = self.files.selection()
        if sel and sel[0] in self.path_berkas:
            buka(self.path_berkas[sel[0]])


if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)  # teks tajam di layar ber-skala
    except Exception:
        pass
    app = App()
    if app.ok:
        app.mainloop()
