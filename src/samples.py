"""
Sampel cepat untuk demo UI.

samples/sampel.json berisi hasil ASLI checker pada proposal PKM nyata (3 didanai,
2 tidak didanai), dibangun oleh tools/build_samples.py. Data pribadi, judul, nama
produk, dan nama perguruan tinggi disamarkan; PDF aslinya tidak ikut di repo.
"""

import json
import re
from datetime import datetime
from pathlib import Path

SAMPLE_FILE = Path(__file__).resolve().parent.parent / "samples" / "sampel.json"


def load_samples() -> list[dict]:
    if not SAMPLE_FILE.exists():
        return []
    try:
        return json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def with_current_timestamp(result: dict) -> dict:
    """Laporan teks memakai waktu tampil, sama seperti pengecekan biasa."""
    ts = datetime.now().strftime("%d %B %Y, %H:%M")
    text = re.sub(r'(Tanggal Cek\s*:\s*)[^\n]*', lambda m: m.group(1) + ts, result["text_report"], count=1)
    return {**result, "text_report": text}
