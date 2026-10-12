"""Membuat ikon.ico (gaya tema: ubin gelap, bracket sudut biru, map dokumen).

Tanpa Pillow — PNG ditulis langsung dengan zlib, lalu dibungkus ICO.
Jalankan sekali: python alat/buat_ikon.py  (hasil: ikon.ico di akar repo)
"""
import struct
import zlib
from pathlib import Path

BG = (5, 7, 13)
PANEL = (17, 27, 46)
GARIS = (30, 45, 71)
AKSEN = (56, 189, 248)
TEKS = (220, 232, 245)


def gambar(n: int) -> list[list[tuple[int, int, int, int]]]:
    s = n / 64  # dirancang di kisi 64×64
    px = [[(0, 0, 0, 0)] * n for _ in range(n)]

    def kotak(x0, y0, x1, y1, warna, alfa=255):
        for y in range(max(0, round(y0 * s)), min(n, round(y1 * s))):
            for x in range(max(0, round(x0 * s)), min(n, round(x1 * s))):
                px[y][x] = (*warna, alfa)

    kotak(2, 2, 62, 62, GARIS)            # garis tepi
    kotak(3, 3, 61, 61, BG)               # ubin
    t = max(2, 4 / s) if n < 32 else 4    # bracket tetap terlihat di ukuran kecil
    kotak(2, 2, 18, 2 + t, AKSEN); kotak(2, 2, 2 + t, 18, AKSEN)          # kiri-atas
    kotak(46, 62 - t, 62, 62, AKSEN); kotak(62 - t, 46, 62, 62, AKSEN)    # kanan-bawah
    kotak(14, 20, 30, 25, AKSEN)          # tab map
    kotak(14, 24, 50, 46, PANEL)          # badan map
    kotak(14, 24, 50, 26, AKSEN)
    kotak(20, 31, 44, 33, TEKS); kotak(20, 36, 40, 38, TEKS)              # baris dokumen
    kotak(20, 41, 34, 43, AKSEN)
    return px


def png(px) -> bytes:
    n = len(px)
    mentah = b"".join(b"\x00" + bytes(c for p in baris for c in p) for baris in px)

    def chunk(jenis, data):
        return struct.pack(">I", len(data)) + jenis + data + struct.pack(">I", zlib.crc32(jenis + data))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(mentah, 9)) + chunk(b"IEND", b""))


def ico(ukuran=(16, 24, 32, 48, 64, 128, 256)) -> bytes:
    gambar_png = [png(gambar(u)) for u in ukuran]
    kepala = struct.pack("<HHH", 0, 1, len(ukuran))
    posisi = 6 + 16 * len(ukuran)
    entri = b""
    for u, data in zip(ukuran, gambar_png):
        entri += struct.pack("<BBBBHHII", u % 256, u % 256, 0, 0, 1, 32, len(data), posisi)
        posisi += len(data)
    return kepala + entri + b"".join(gambar_png)


if __name__ == "__main__":
    tujuan = Path(__file__).resolve().parent.parent / "ikon.ico"
    tujuan.write_bytes(ico())
    print(tujuan)
