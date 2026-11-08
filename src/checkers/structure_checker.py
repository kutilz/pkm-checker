"""
Modul 3 — Struktur Dokumen.
Cek Daftar Isi, kelengkapan & penamaan bab per bidang, heading kapital, dan
batas halaman bagian inti. Daftar Pustaka & sitasi ada di Modul 4.
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from config import MAX_CORE_PAGES, STRUKTUR_BAB_PKM

ROMAWI = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}


def _bab_exists(text_upper: str, nomor: int, judul: str) -> bool:
    """Heading 'BAB n. JUDUL' yang bukan baris Daftar Isi (tanpa titik-titik + nomor halaman)."""
    kata = judul.upper().split()
    # Cocokkan 2 kata pertama judul agar toleran variasi ("BAB 4. BIAYA DAN JADWAL ...")
    judul_pat = r'\s+'.join(re.escape(k) for k in kata[:2])
    pat = rf'BAB\s+(?:{nomor}|{ROMAWI[nomor]})\b[.\s]*{judul_pat}'
    for m in re.finditer(pat, text_upper):
        line_end = text_upper.find('\n', m.start())
        line = text_upper[m.start(): line_end if line_end > 0 else m.start() + 100]
        if not re.search(r'\.{3,}\s*\d+\s*$', line):
            return True
    return False


class StructureChecker(BaseChecker):

    def __init__(self, doc, use_gemini: bool = False):
        super().__init__(doc)
        self.use_gemini = use_gemini

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 3: Struktur Dokumen", bobot=0.15)
        result.items.extend([
            self._check_daftar_isi(),
            self._check_bab_wajib(),
            self._check_bab_format_capslock(),
            self._check_batas_halaman_inti(),
        ])
        return result

    def _check_daftar_isi(self) -> CheckItem:
        front = "\n".join(self.doc.pages[n - 1].text for n in self.doc.daftar_isi_pages) \
            or self.doc.full_text
        missing = [label for label, pat in (("DAFTAR ISI", r'DAFTAR\s+ISI'),
                                            ("DAFTAR LAMPIRAN", r'DAFTAR\s+LAMPIRAN'))
                   if not re.search(pat, front, re.IGNORECASE)]
        if not missing:
            return CheckItem("3.1.a", "Daftar Isi & Daftar Lampiran ada", Status.LULUS,
                             "Daftar Isi dan Daftar Lampiran ditemukan "
                             "(Daftar Gambar/Tabel wajib hanya jika ada gambar/tabel).")
        return CheckItem("3.1.a", "Daftar Isi & Daftar Lampiran ada", Status.TIDAK_LULUS,
                         f"Tidak ditemukan: {', '.join(missing)}. Sistematika panduan: DAFTAR ISI → "
                         "DAFTAR GAMBAR (jika ada) → DAFTAR TABEL (jika ada) → DAFTAR LAMPIRAN.")

    def _check_bab_wajib(self) -> CheckItem:
        """Cek BAB sesuai sistematika bidang + DAFTAR PUSTAKA + LAMPIRAN."""
        text_upper = self.doc.full_text.upper()
        pkm = self.doc.jenis_pkm
        struktur = STRUKTUR_BAB_PKM.get(pkm) if pkm else None

        if pkm in STRUKTUR_BAB_PKM and struktur is None:
            return CheckItem("3.1.b", "Bab-bab wajib lengkap & sesuai bidang", Status.PERINGATAN,
                             f"PKM-{pkm} memakai format khusus (artikel); sistematika bab tidak dicek otomatis.")
        if struktur is None:
            # Bidang belum diketahui: cek kerangka umum saja
            struktur = ["Pendahuluan", None, None, "Biaya dan Jadwal Kegiatan"]

        missing = []
        for i, judul in enumerate(struktur, start=1):
            if judul and not _bab_exists(text_upper, i, judul):
                missing.append(f"BAB {i}. {judul.upper()}")
        for label, pat in (("DAFTAR PUSTAKA", r'^\s*DAFTAR\s+PUSTAKA\s*$'),
                           ("LAMPIRAN", r'^\s*(?:\d{1,3}\s+)?LAMPIRAN\s*$|^\s*LAMPIRAN\s+1\b')):
            if not re.search(pat, text_upper, re.MULTILINE):
                missing.append(label)

        bidang = f"PKM-{pkm}" if pkm in STRUKTUR_BAB_PKM else "kerangka umum"
        if not missing:
            return CheckItem("3.1.b", "Bab-bab wajib lengkap & sesuai bidang", Status.LULUS,
                             f"Semua bab wajib ({bidang}) ditemukan.")
        return CheckItem("3.1.b", "Bab-bab wajib lengkap & sesuai bidang", Status.TIDAK_LULUS,
                         f"Tidak ditemukan / judul bab tidak sesuai panduan ({bidang}): {', '.join(missing)}. "
                         "Judul bab harus sama persis dengan sistematika di buku panduan bidang.")

    def _check_bab_format_capslock(self) -> CheckItem:
        """
        Heading bab ditulis kapital dengan titik setelah nomor: 'BAB 3. TAHAP PELAKSANAAN'.
        """
        bab_lines = []
        for line in self.doc.core_text.split('\n'):
            stripped = line.strip()
            if re.match(r'^BAB\s+[1-5IVX]+\b', stripped, re.IGNORECASE):
                if not re.search(r'\.{3,}\s*\d+\s*$', stripped) and len(stripped) < 80:
                    bab_lines.append(stripped)

        if not bab_lines:
            return CheckItem("3.1.c", "Heading bab kapital & bertitik ('BAB 1. PENDAHULUAN')",
                             Status.PERINGATAN,
                             "Heading bab tidak terdeteksi. Pastikan format 'BAB 1. PENDAHULUAN'.")

        bukan_kapital = [b for b in bab_lines if b != b.upper()]
        tanpa_titik = [b for b in bab_lines if not re.match(r'^BAB\s+[1-5IVX]+\.\s', b, re.IGNORECASE)]
        if not bukan_kapital and not tanpa_titik:
            return CheckItem("3.1.c", "Heading bab kapital & bertitik ('BAB 1. PENDAHULUAN')",
                             Status.LULUS, f"{len(bab_lines)} heading bab sesuai. Contoh: '{bab_lines[0]}'")
        def _dengan_titik(heading: str) -> str:
            return re.sub(r'^(BAB\s+\w+)\s+', r'\1. ', heading)

        catatan = [f"Tidak kapital: '{b}'" for b in bukan_kapital[:3]] + \
                  [f"Tanpa titik setelah nomor bab: '{b}' → '{_dengan_titik(b)}'" for b in tanpa_titik[:3]]
        status = Status.TIDAK_LULUS if bukan_kapital else Status.PERINGATAN
        return CheckItem("3.1.c", "Heading bab kapital & bertitik ('BAB 1. PENDAHULUAN')", status,
                         "Format heading bab belum seragam dengan panduan.", catatan=catatan)

    def _check_batas_halaman_inti(self) -> CheckItem:
        """Bab 1 s.d. akhir Daftar Pustaka maksimum 10 halaman."""
        count = len(self.doc.core_pages)
        if not self.doc.bab1_page or not self.doc.dafpus_page:
            return CheckItem("3.2", "Bagian inti ≤ 10 halaman", Status.PERINGATAN,
                             "Segmentasi dokumen gagal — pastikan heading 'BAB 1. PENDAHULUAN' dan "
                             "'DAFTAR PUSTAKA' terbaca sebagai teks.")
        pages_str = f"hal. PDF {self.doc.core_pages[0]}–{self.doc.core_pages[-1]}"
        if count <= MAX_CORE_PAGES:
            return CheckItem("3.2", "Bagian inti ≤ 10 halaman", Status.LULUS,
                             f"Bagian inti (BAB 1 s.d. akhir Daftar Pustaka): {count} halaman ({pages_str}).")
        return CheckItem("3.2", "Bagian inti ≤ 10 halaman", Status.TIDAK_LULUS,
                         f"Bagian inti {count} halaman ({pages_str}), melebihi batas {MAX_CORE_PAGES} halaman. "
                         "Daftar Pustaka yang meluber ke halaman berikutnya ikut dihitung.")
