"""Tema visual yang mengikuti Q Studio Tracker (gym-tracker-q/css/styles.css):
panel gelap bersudut tajam, aksen biru menyala, bracket sudut, label mono huruf kapital.

Tkinter tidak punya glow, gradien, maupun clip-path, jadi yang ditiru adalah palet,
bentuk panel, dan tipografinya.
"""
from __future__ import annotations

import ctypes
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

BG = "#05070d"
SURFACE = "#0a1120"
SURFACE_2 = "#111b2e"
BORDER = "#1e2d47"
TEXT = "#dce8f5"
MUTED = "#7d90ab"
DIM = "#4a5a74"
ACCENT = "#38bdf8"
ACCENT_DIM = "#1a6f96"
SEL = "#13334b"  # rgba(56,189,248,.2) di atas SURFACE — Tk tidak mengenal transparansi
GOOD = "#4ade80"
WARN = "#fbbf24"
DANGER = "#fb7185"
ON_ACCENT = "#04121c"

# Diisi oleh pasang(), karena font hanya bisa dibuat setelah jendela Tk ada.
UI = UI_B = H1 = H2 = MONO = MONO_S = None
SKALA = 1.0


def px(n: float) -> int:
    """Ukuran piksel desain (96 dpi) -> piksel layar. Font sudah otomatis ikut skala, piksel tidak."""
    return round(n * SKALA)


def pasang(root: tk.Tk) -> None:
    global UI, UI_B, H1, H2, MONO, MONO_S, SKALA
    SKALA = root.winfo_fpixels("1i") / 96
    keluarga = set(tkfont.families(root))
    mono = next((f for f in ("Cascadia Mono", "Cascadia Code", "Consolas") if f in keluarga), "Courier New")
    UI = ("Segoe UI", 10)
    UI_B = ("Segoe UI", 10, "bold")
    H1 = ("Segoe UI", 16, "bold")
    H2 = ("Segoe UI", 12, "bold")
    MONO = (mono, 9)
    MONO_S = (mono, 8)

    root.configure(bg=BG)
    root.option_add("*TCombobox*Listbox.background", SURFACE_2)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", ON_ACCENT)
    root.option_add("*TCombobox*Listbox.font", UI)

    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=TEXT, font=UI, bordercolor=BORDER,
                lightcolor=BG, darkcolor=BG, troughcolor=BG, focuscolor=ACCENT,
                selectbackground=SEL, selectforeground=TEXT, fieldbackground=SURFACE_2,
                insertcolor=ACCENT)

    def tombol(nama, bg, fg, garis, bg_aktif, fg_aktif=None, font=UI_B, pad=(14, 8)):
        s.configure(nama, background=bg, foreground=fg, bordercolor=garis, lightcolor=bg,
                    darkcolor=bg, relief="flat", padding=pad, font=font, focuscolor=bg,
                    focusthickness=0, anchor="center")
        s.map(nama,
              background=[("disabled", SURFACE), ("pressed", bg_aktif), ("active", bg_aktif)],
              lightcolor=[("disabled", SURFACE), ("active", bg_aktif)],
              darkcolor=[("disabled", SURFACE), ("active", bg_aktif)],
              foreground=[("disabled", DIM), ("active", fg_aktif or fg)],
              bordercolor=[("disabled", BORDER), ("active", ACCENT)])

    tombol("TButton", SURFACE_2, TEXT, BORDER, "#16243c")
    tombol("Primary.TButton", ACCENT, ON_ACCENT, ACCENT, "#5cc9fa")
    tombol("Ghost.TButton", BG, TEXT, BORDER, SURFACE_2, ACCENT)
    tombol("Done.TButton", SURFACE_2, GOOD, "#24593a", "#16243c")
    tombol("Chip.TButton", SURFACE_2, MUTED, BORDER, "#16243c", TEXT, MONO, (12, 6))
    tombol("ChipOn.TButton", SEL, ACCENT, ACCENT, SEL, ACCENT, MONO, (12, 6))

    tombol("Drop.TButton", SEL, ACCENT, ACCENT, SEL, ACCENT)  # sorotan saat berkas diseret di atasnya
    tombol("Step.TButton", SURFACE_2, MUTED, BORDER, "#16243c", TEXT, MONO_S, (6, 7))
    tombol("StepDone.TButton", SURFACE_2, GOOD, "#24593a", "#16243c", GOOD, MONO_S, (6, 7))
    tombol("StepOn.TButton", ACCENT, ON_ACCENT, ACCENT, "#5cc9fa", ON_ACCENT, MONO_S, (6, 7))

    s.configure("TNotebook", background=SURFACE, bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE,
                tabmargins=(0, 0, 0, 0))
    s.configure("TNotebook.Tab", background=SURFACE_2, foreground=MUTED, font=MONO_S, padding=(12, 6),
                bordercolor=BORDER, lightcolor=SURFACE_2, darkcolor=SURFACE_2)
    s.map("TNotebook.Tab", background=[("selected", SURFACE)], foreground=[("selected", ACCENT), ("active", TEXT)],
          lightcolor=[("selected", SURFACE)], darkcolor=[("selected", SURFACE)])

    s.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE, rowheight=px(28), font=UI)
    s.map("Treeview", background=[("selected", SEL)], foreground=[("selected", ACCENT)])
    s.configure("Treeview.Heading", background=SURFACE_2, foreground=MUTED, font=MONO_S,
                relief="flat", bordercolor=BORDER, lightcolor=SURFACE_2, darkcolor=SURFACE_2,
                padding=(6, 7))
    s.map("Treeview.Heading", background=[("active", SURFACE_2)], foreground=[("active", ACCENT)])
    s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # tanpa bingkai bawaan

    for arah in ("Vertical", "Horizontal"):
        s.configure(f"{arah}.TScrollbar", background=SURFACE_2, troughcolor=SURFACE, bordercolor=SURFACE,
                    arrowcolor=MUTED, lightcolor=SURFACE_2, darkcolor=SURFACE_2, gripcount=0)
        s.map(f"{arah}.TScrollbar", background=[("active", BORDER)], arrowcolor=[("active", ACCENT)])

    s.configure("TCombobox", fieldbackground=SURFACE_2, background=SURFACE_2, foreground=TEXT,
                arrowcolor=ACCENT, bordercolor=BORDER, lightcolor=SURFACE_2, darkcolor=SURFACE_2,
                selectbackground=SURFACE_2, selectforeground=TEXT, padding=(6, 7))
    s.map("TCombobox",
          fieldbackground=[("readonly", SURFACE_2)], foreground=[("readonly", TEXT)],
          selectbackground=[("readonly", SURFACE_2)], selectforeground=[("readonly", TEXT)],
          bordercolor=[("focus", ACCENT)], background=[("active", SURFACE_2)])

    s.configure("TCheckbutton", background=BG, foreground=MUTED, font=MONO, indicatorbackground=SURFACE_2,
                indicatorforeground=ACCENT, upperbordercolor=BORDER, lowerbordercolor=BORDER,
                focuscolor=BG)
    s.map("TCheckbutton", background=[("active", BG)], foreground=[("active", TEXT)],
          indicatorbackground=[("selected", SURFACE_2), ("active", SURFACE_2)])
    s.configure("Surface.TCheckbutton", background=SURFACE, foreground=TEXT, font=UI, focuscolor=SURFACE)
    s.map("Surface.TCheckbutton", background=[("active", SURFACE)], foreground=[("active", ACCENT)])
    s.configure("Auto.TCheckbutton", background=SURFACE, foreground=GOOD, font=UI, focuscolor=SURFACE,
                indicatorforeground=GOOD)
    s.map("Auto.TCheckbutton", background=[("active", SURFACE)], foreground=[("disabled", GOOD)],
          indicatorforeground=[("disabled", GOOD)], indicatorbackground=[("disabled", SURFACE_2)])


def judul_gelap(win: tk.Misc) -> None:
    """Bilah judul Windows ikut gelap (Windows 10 20H1+ / 11). Diam-diam gagal di tempat lain."""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        satu = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(satu), ctypes.sizeof(satu))
        r, g, b = (int(SURFACE_2[i:i + 2], 16) for i in (1, 3, 5))
        warna = ctypes.c_int(r | g << 8 | b << 16)  # COLORREF = 0x00BBGGRR
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(warna), ctypes.sizeof(warna))
        # Atribut baru terlihat setelah bingkai digambar ulang: SWP_NOSIZE|NOMOVE|NOZORDER|FRAMECHANGED.
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x1 | 0x2 | 0x4 | 0x20)
    except Exception:
        pass


# --- komponen ----------------------------------------------------------------

class Kartu(tk.Frame):
    """Panel `.card`: latar SURFACE, garis tipis, bracket sudut kiri-atas & kanan-bawah.
    Isi ditaruh di `self.isi`."""

    def __init__(self, master, warna: str = ACCENT, pad: int = 16, **kw):
        super().__init__(master, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=BORDER, **kw)
        self.isi = tk.Frame(self, bg=SURFACE)
        self.isi.pack(fill="both", expand=True, padx=pad, pady=pad)
        self._braket = []
        for relx, rely, anchor in ((0, 0, "nw"), (1, 1, "se")):
            for w, h in ((px(11), px(2)), (px(2), px(11))):
                b = tk.Frame(self, bg=warna, width=w, height=h)
                b.place(relx=relx, rely=rely, anchor=anchor, bordermode="outside")
                self._braket.append(b)

    def warna(self, warna: str) -> None:
        for b in self._braket:
            b.configure(bg=warna)


def sub(master, teks: str, bg: str = SURFACE) -> tk.Frame:
    """Judul bagian `.sub`: balok aksen kecil di kiri, teks mono kapital."""
    f = tk.Frame(master, bg=bg)
    tk.Frame(f, bg=ACCENT, width=px(3), height=px(13)).pack(side="left", padx=(0, 8))
    tk.Label(f, text=teks.upper(), bg=bg, fg=TEXT, font=MONO).pack(side="left")
    return f


def label_field(master, teks: str, bg: str = BG) -> tk.Label:
    """Label isian `.field > span`: mono kecil, kapital, redup."""
    return tk.Label(master, text=teks.upper(), bg=bg, fg=MUTED, font=MONO_S, anchor="w")


def entri(master, var: tk.StringVar, width: int = 20, **kw) -> tk.Entry:
    return tk.Entry(master, textvariable=var, width=width, bg=SURFACE_2, fg=TEXT,
                    insertbackground=ACCENT, relief="flat", bd=6, font=UI,
                    highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
                    disabledbackground=SURFACE, disabledforeground=MUTED,
                    readonlybackground=SURFACE, selectbackground=ACCENT_DIM, **kw)


def hero(master, brand: str, judul: str) -> tuple[tk.Frame, tk.Label]:
    """Kepala `.hero`: brand mono aksen di atas judul besar kapital, garis bawah
    dengan potongan aksen 72px di kiri. Kembalikan (frame kanan untuk tombol, label judul)."""
    f = tk.Frame(master, bg=SURFACE_2)
    f.pack(fill="x")
    kiri = tk.Frame(f, bg=SURFACE_2)
    kiri.pack(side="left", padx=18, pady=(16, 14))
    tk.Label(kiri, text=brand.upper(), bg=SURFACE_2, fg=ACCENT, font=MONO_S).pack(anchor="w")
    lbl = tk.Label(kiri, text=judul.upper(), bg=SURFACE_2, fg=TEXT, font=H1)
    lbl.pack(anchor="w")
    kanan = tk.Frame(f, bg=SURFACE_2)
    kanan.pack(side="right", padx=18)
    garis = tk.Frame(master, bg=BORDER, height=px(2))
    garis.pack(fill="x")
    tk.Frame(garis, bg=ACCENT).place(x=0, y=0, width=px(72), height=px(2))
    return kanan, lbl


class StripLangkah(tk.Canvas):
    """Bilah bersegmen seperti `.progress-strip`: satu segmen per langkah, menyala kalau terisi."""

    def __init__(self, master, jumlah: int, bg: str = SURFACE):
        super().__init__(master, height=px(6), bg=bg, highlightthickness=0)
        self.jumlah = jumlah
        self.terisi: list[bool] = [False] * jumlah
        self.bind("<Configure>", lambda _e: self.gambar())

    def atur(self, terisi: list[bool]) -> None:
        self.terisi = terisi
        self.gambar()

    def gambar(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        celah = px(4)
        lebar = (w - celah * (self.jumlah - 1)) / self.jumlah
        for i, isi in enumerate(self.terisi):
            x = i * (lebar + celah)
            self.create_rectangle(x, 0, x + lebar, px(6), width=0, fill=ACCENT if isi else BORDER)


class Gulir(tk.Frame):
    """Bingkai yang isinya (`self.isi`) bisa digulir kalau lebih tinggi dari tempatnya.
    Bilah gulir hanya muncul saat dibutuhkan; roda tetikus aktif selama kursor di atasnya."""

    def __init__(self, master, bg: str = SURFACE):
        super().__init__(master, bg=bg)
        self.kanvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.kanvas.yview)
        self.isi = tk.Frame(self.kanvas, bg=bg)
        self._win = self.kanvas.create_window(0, 0, window=self.isi, anchor="nw")
        self.kanvas.configure(yscrollcommand=self.sb.set)
        self.kanvas.pack(side="left", fill="both", expand=True)
        self.isi.bind("<Configure>", lambda _e: self._atur())
        self.kanvas.bind("<Configure>", self._lebar)
        self.bind("<Enter>", lambda _e: self.bind_all("<MouseWheel>", self._roda))
        self.bind("<Leave>", lambda _e: self.unbind_all("<MouseWheel>"))

    def _lebar(self, e):
        self.kanvas.itemconfigure(self._win, width=e.width)
        self._atur()

    def _perlu(self) -> bool:
        return self.isi.winfo_reqheight() > self.kanvas.winfo_height() + 1

    def _atur(self):
        self.kanvas.configure(scrollregion=(0, 0, 0, self.isi.winfo_reqheight()))
        if self._perlu():
            self.sb.pack(side="right", fill="y", before=self.kanvas)
        else:
            self.sb.pack_forget()
            self.kanvas.yview_moveto(0)

    def _roda(self, e):
        if self._perlu():
            self.kanvas.yview_scroll(-e.delta // 120, "units")

    def ke_atas(self):
        self.kanvas.yview_moveto(0)
