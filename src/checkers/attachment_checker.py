"""
Modul 6 — Lampiran.
Cek keberadaan lampiran wajib dan kelengkapannya.
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status


LAMPIRAN_WAJIB = {
    "L-1": ("Biodata Ketua & Anggota", [r'biodata\s+ketua', r'biodata\s+anggota', r'biodata\s+mahasiswa']),
    "L-2": ("Biodata Dosen Pendamping", [r'biodata\s+dosen', r'dosen\s+pendamping']),
    "L-3": ("Justifikasi Anggaran", [r'justifikasi\s+anggaran', r'rincian\s+anggaran']),
    "L-4": ("Susunan Tim & Pembagian Tugas", [r'susunan\s+(organisasi|tim)', r'pembagian\s+tugas']),
    "L-5": ("Surat Pernyataan Ketua", [r'surat\s+pernyataan']),
    "L-6": ("Hasil Uji Similaritas", [r'similaritas', r'similarity', r'turnitin', r'ithenticate']),
}

LAMPIRAN_TAMBAHAN = {
    "KC": [("Gambaran Teknologi", [r'gambaran\s+teknologi'])],
    "PI": [("Surat Pernyataan Mitra", [r'pernyataan\s+mitra', r'surat\s+mitra'])],
    "PM": [("Surat Pernyataan Mitra", [r'pernyataan\s+mitra', r'surat\s+mitra'])],
}


class AttachmentChecker(BaseChecker):

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 6: Lampiran", bobot=0.10)
        lampiran_text = (self.doc.lampiran_text or self.doc.full_text).lower()

        for kode, (nama, patterns) in LAMPIRAN_WAJIB.items():
            found = any(re.search(p, lampiran_text) for p in patterns)
            if found:
                result.items.append(CheckItem(
                    kode, f"Lampiran {kode}: {nama}", Status.LULUS,
                    f"Lampiran '{nama}' ditemukan."
                ))
            else:
                result.items.append(CheckItem(
                    kode, f"Lampiran {kode}: {nama}", Status.TIDAK_LULUS,
                    f"Lampiran '{nama}' tidak ditemukan dalam dokumen."
                ))

        # Lampiran tambahan per bidang PKM
        pkm = self.doc.jenis_pkm
        if pkm and pkm in LAMPIRAN_TAMBAHAN:
            for nama, patterns in LAMPIRAN_TAMBAHAN[pkm]:
                found = any(re.search(p, lampiran_text) for p in patterns)
                status = Status.LULUS if found else Status.TIDAK_LULUS
                detail = (f"Lampiran tambahan PKM-{pkm} '{nama}' ditemukan."
                          if found else
                          f"Lampiran tambahan PKM-{pkm} '{nama}' tidak ditemukan.")
                result.items.append(CheckItem(
                    f"L-tambahan-{pkm}", f"Lampiran Tambahan PKM-{pkm}: {nama}",
                    status, detail
                ))

        # Cek meterai di surat pernyataan (via deteksi gambar)
        result.items.append(self._check_meterai())

        return result

    def _check_meterai(self) -> CheckItem:
        """
        Deteksi meterai pada Surat Pernyataan melalui keberadaan gambar/scan.

        Mengapa tidak pakai deteksi teks?
        Meterai fisik (tempel) selalu berbentuk stempel/gambar yang ditempelkan
        pada dokumen lalu discan. Tidak ada teks "meterai" yang bisa dibaca
        secara otomatis dari PDF scan tersebut.

        Strategi: cek apakah halaman Surat Pernyataan mengandung gambar
        (images/XObjects). Jika ya, kemungkinan besar meterai ada di sana.
        """
        # Cari halaman surat pernyataan di lampiran
        surat_pages = [
            p for p in self.doc.pages
            if p.page_number in self.doc.lampiran_pages
            and re.search(r'surat\s+pernyataan', p.text, re.IGNORECASE)
        ]

        if not surat_pages:
            return CheckItem(
                "L-5.c", "Meterai Rp10.000 pada surat pernyataan",
                Status.PERINGATAN,
                "Halaman Surat Pernyataan tidak ditemukan. "
                "Periksa manual apakah meterai Rp10.000 sudah terpasang."
            )

        # Kumpulkan semua gambar dari halaman surat pernyataan
        total_images = sum(len(p.images) for p in surat_pages)

        if total_images > 0:
            return CheckItem(
                "L-5.c", "Meterai Rp10.000 pada surat pernyataan",
                Status.LULUS,
                f"Terdeteksi {total_images} gambar pada halaman Surat Pernyataan "
                "(kemungkinan scan meterai). Verifikasi visual tetap disarankan."
            )

        return CheckItem(
            "L-5.c", "Meterai Rp10.000 pada surat pernyataan",
            Status.PERINGATAN,
            "Tidak terdeteksi gambar/scan pada halaman Surat Pernyataan. "
            "Pastikan meterai Rp10.000 ditempelkan dan dokumen discan ulang."
        )
