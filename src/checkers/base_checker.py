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


@dataclass
class ModulResult:
    nama_modul: str
    items: list[CheckItem] = field(default_factory=list)
    bobot: float = 0.0

    @property
    def skor(self) -> float:
        """Hitung skor 0–100 berdasarkan item yang lulus."""
        if not self.items:
            return 100.0
        lulus = sum(1 for i in self.items if i.status == Status.LULUS)
        return round(lulus / len(self.items) * 100, 1)

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
