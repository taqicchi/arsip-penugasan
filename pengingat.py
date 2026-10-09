"""Pengingat tenggat lewat notifikasi Windows.

Dijalankan Task Scheduler sekali sehari (`pythonw pengingat.py`), jadi tetap
mengingatkan walaupun aplikasi tidak dibuka. Jadwalnya dipasang/dilepas dari
tombol di aplikasi — lihat `aktifkan()` / `nonaktifkan()`.
"""
from __future__ import annotations

import base64
import subprocess
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import konfig  # noqa: E402
from core import Arsip, Penugasan, perlu_diingat  # noqa: E402

TASK = "Arsip Penugasan - Pengingat"
JAM = "07:30"
H_MINUS = 3
# AppUserModelID PowerShell bawaan Windows — dipakai karena aplikasi ini tidak terdaftar sendiri.
APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
_TANPA_JENDELA = 0x08000000  # CREATE_NO_WINDOW


def _ps(skrip: str, timeout: int = 30) -> subprocess.CompletedProcess:
    kode = base64.b64encode(skrip.encode("utf-16-le")).decode()
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", kode],
                          capture_output=True, text=True, timeout=timeout, creationflags=_TANPA_JENDELA)


def _kutip(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sisa_teks(sisa: int) -> str:
    if sisa < 0:
        return f"lewat {-sisa} hari"
    return {0: "hari ini", 1: "besok"}.get(sisa, f"{sisa} hari lagi")


def susun_pesan(lewat: list[Penugasan], segera: list[Penugasan], hari_ini: date | None = None
                ) -> tuple[str, list[str]] | None:
    """(judul, baris) untuk notifikasi, atau None kalau tidak ada yang perlu diingat."""
    if not lewat and not segera:
        return None
    bagian = []
    if lewat:
        bagian.append(f"{len(lewat)} lewat tenggat")
    if segera:
        bagian.append(f"{len(segera)} jatuh tempo ≤ {H_MINUS} hari")
    baris = [f"{p.judul} — {sisa_teks(p.sisa_hari(hari_ini))}" for p in (lewat + segera)[:3]]
    if len(lewat) + len(segera) > 3:
        baris.append(f"… dan {len(lewat) + len(segera) - 3} lainnya")
    return "Arsip Penugasan: " + ", ".join(bagian), baris


def tampilkan_toast(judul: str, baris: list[str]) -> bool:
    teks = "".join(f"<text>{escape(t)}</text>" for t in [judul, "\n".join(baris)])
    xml = f'<toast><visual><binding template="ToastGeneric">{teks}</binding></visual></toast>'
    skrip = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$x = New-Object Windows.Data.Xml.Dom.XmlDocument
$x.LoadXml({_kutip(xml)})
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier({_kutip(APP_ID)}).Show(
    [Windows.UI.Notifications.ToastNotification]::new($x))
"""
    return _ps(skrip).returncode == 0


# --- jadwal Task Scheduler ----------------------------------------------------

def _pythonw() -> str:
    w = Path(sys.executable).with_name("pythonw.exe")
    return str(w if w.exists() else sys.executable)


def aktif() -> bool:
    r = subprocess.run(["schtasks", "/Query", "/TN", TASK], capture_output=True, creationflags=_TANPA_JENDELA)
    return r.returncode == 0


def aktifkan(jam: str = JAM) -> tuple[bool, str]:
    """Pasang tugas harian. Kalau komputer mati pada jamnya, dijalankan begitu menyala."""
    skrip = f"""
$a = New-ScheduledTaskAction -Execute {_kutip(_pythonw())} -Argument {_kutip('"' + str(Path(__file__).resolve()) + '"')}
$t = New-ScheduledTaskTrigger -Daily -At {_kutip(jam)}
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName {_kutip(TASK)} -Action $a -Trigger $t -Settings $s -Description 'Notifikasi tenggat penugasan dari aplikasi Arsip Penugasan.' -Force | Out-Null
"""
    r = _ps(skrip)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def nonaktifkan() -> tuple[bool, str]:
    r = subprocess.run(["schtasks", "/Delete", "/TN", TASK, "/F"], capture_output=True, text=True,
                       creationflags=_TANPA_JENDELA)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def main() -> int:
    root = konfig.muat().get("root")
    if not root or not Path(root).is_dir():
        return 0
    daftar, _ = Arsip(Path(root)).pindai()
    pesan = susun_pesan(*perlu_diingat(daftar, h=H_MINUS))
    if pesan:
        tampilkan_toast(*pesan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
