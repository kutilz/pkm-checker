"""
Base class untuk semua modul checker.
Setiap hasil item disimpan sebagai CheckItem dengan status LULUS / PERINGATAN / TIDAK_LULUS.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Status(str, Enum):
    LULUS = "LULUS"
    PERINGATAN = "PERINGATAN"
    TIDAK_LULUS = "TIDAK_LULUS"


@dataclass
class CheckItem:
    kode: str
    deskripsi: str
    status: Status
    detail: str = ""
    halaman: Optional[int] = None
    # Rincian per temuan (mis. kesalahan per entri daftar pustaka), ditampilkan sebagai poin
    catatan: list[str] = field(default_factory=list)


@dataclass
class ModulResult:
    nama_modul: str
    items: list[CheckItem] = field(default_factory=list)
    bobot: float = 0.0

    @property
    def skor(self) -> float:
        """Skor 0–100: LULUS = 1, PERINGATAN = 0,5 (perlu cek manual), TIDAK_LULUS = 0."""
        if not self.items:
            return 100.0
        nilai = sum(1.0 if i.status == Status.LULUS else 0.5 if i.status == Status.PERINGATAN else 0.0
                    for i in self.items)
        return round(nilai / len(self.items) * 100, 1)

    @property
    def ada_tidak_lulus(self) -> bool:
        return any(i.status == Status.TIDAK_LULUS for i in self.items)

    @property
    def ada_peringatan(self) -> bool:
        return any(i.status == Status.PERINGATAN for i in self.items)


class BaseChecker:
    def __init__(self, doc):
        self.doc = doc

    def run(self) -> ModulResult:
        raise NotImplementedError
