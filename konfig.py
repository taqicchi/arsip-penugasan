"""Pengaturan aplikasi per pengguna (bukan per arsip): folder induk dan pilihan kecil."""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG = Path(os.environ.get("APPDATA", Path.home())) / "ArsipPenugasan" / "config.json"


def muat() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def simpan(cfg: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
