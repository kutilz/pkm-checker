"""
Modul 6 — Lampiran.
Kelengkapan lampiran umum + khusus bidang (Panduan 2026), dan bukti tanda tangan
basah: panduan mensyaratkan "satu halaman penuh yang ada tanda tangannya dipindai
atau difoto"; tanda tangan hasil pemotongan/tempel → TIDAK LOLOS Tahap 1.
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from .consistency_checker import baris_susunan_tim
from config import LAMPIRAN_KHUSUS_PKM

LAMPIRAN_UMUM = {
    "L-1": ("Biodata Ketua & Anggota", [r'biodata\s+ketua', r'biodata\s+anggota', r'biodata\s+mahasiswa']),
    "L-1b": ("Biodata Dosen Pendamping", [r'biodata\s+dosen']),
    "L-2": ("Justifikasi Anggaran Kegiatan", [r'justifikasi\s+anggaran']),
    "L-3": ("Susunan Tim Pengusul & Pembagian Tugas", [r'susunan\s+(?:tim|organisasi)', r'pembagian\s+tugas']),
    "L-4": ("Surat Pernyataan Ketua Tim Pengusul", [r'surat\s+pernyataan\s+ketua', r'surat\s+pernyataan']),
    "L-6": ("Hasil Uji Similaritas (≤25%, bagian inti)", [r'similaritas', r'similarity', r'turnitin', r'ithenticate']),
}

# Di sampel, scan halaman bertanda tangan yang sah menutupi 19–59% luas halaman
# (scan sering dipotong ke area berisi teks). Potongan tanda tangan saja ≈1–4%.
SCAN_MIN_RATIO = 0.15      # gambar ≥15% luas halaman = halaman hasil scan/foto
TTD_KECIL_MAX = 0.08       # gambar kecil (≤8%) di blok tanda tangan = curiga TT tempel
BLOK_TTD = re.compile(r'(Ketua\s+Tim|Anggota\s+Tim|Dosen\s+Pendamping|Yang\s+menyatakan)[\s\S]{0,200}?'
                      r'(NIM|NUPTK|NIP|NIDN)', re.IGNORECASE)


def _small_images(page) -> list[float]:
    area = page.width_pt * page.height_pt or 1
    out = []
    for img in page.images:
        try:
            r = (float(img["x1"]) - float(img["x0"])) * (float(img["bottom"]) - float(img["top"])) / area
        except (KeyError, TypeError, ValueError):
            continue
        if 0.001 < r <= TTD_KECIL_MAX:
            out.append(r)
    return out


class AttachmentChecker(BaseChecker):

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 6: Lampiran", bobot=0.10)
        lampiran_text = (self.doc.lampiran_text or self.doc.full_text).lower()

        for kode, (nama, patterns) in LAMPIRAN_UMUM.items():
            found = any(re.search(p, lampiran_text) for p in patterns)
            result.items.append(CheckItem(
                kode, f"Lampiran: {nama}", Status.LULUS if found else Status.TIDAK_LULUS,
                f"'{nama}' ditemukan." if found else f"'{nama}' tidak ditemukan di lampiran."))

        pkm = self.doc.jenis_pkm
        for nama, patterns in LAMPIRAN_KHUSUS_PKM.get(pkm or "", []):
            found = any(re.search(p, lampiran_text) for p in patterns)
            result.items.append(CheckItem(
                f"L-{pkm}", f"Lampiran khusus PKM-{pkm}: {nama}", Status.LULUS if found else Status.TIDAK_LULUS,
                f"'{nama}' ditemukan." if found else
                f"'{nama}' wajib untuk PKM-{pkm} (Panduan 2026) tetapi tidak ditemukan."))

        result.items.append(self._check_ttd_biodata())
        result.items.append(self._check_surat_pernyataan())
        return result

    # ─── Tanda tangan ────────────────────────────────────────────────────────

    def _biodata_pages(self) -> list:
        pages = []
        for n in self.doc.lampiran_pages:
            page = self.doc.pages[n - 1]
            if pages and re.search(r'Justifikasi\s+Anggaran', page.text, re.IGNORECASE):
                break
            pages.append(page)
        return pages

    def _check_ttd_biodata(self) -> CheckItem:
        desc = "Biodata bertanda tangan basah (halaman penuh hasil scan/foto)"
        pages = self._biodata_pages()
        if not pages:
            return CheckItem("L-1.c", desc, Status.PERINGATAN, "Halaman biodata tidak teridentifikasi. Cek manual.")
        scan = [p.page_number for p in pages if p.max_image_ratio >= SCAN_MIN_RATIO]
        tempel = [p.page_number for p in pages
                  if p.max_image_ratio < SCAN_MIN_RATIO and _small_images(p) and BLOK_TTD.search(p.text)]
        anggota = len(baris_susunan_tim(self.doc))
        orang = (anggota + 1) if 3 <= anggota <= 5 else None   # + dosen pendamping

        if tempel:
            return CheckItem(
                "L-1.c", desc, Status.TIDAK_LULUS,
                f"Halaman {tempel} berisi blok tanda tangan berupa teks dengan gambar kecil — terindikasi "
                "tanda tangan hasil potong/tempel. Panduan: jika ada tanda tangan hasil pemotongan, proposal "
                "TIDAK LOLOS Tahap 1. Cetak, tanda tangani basah, lalu scan/foto SATU HALAMAN PENUH.")
        if not scan:
            return CheckItem(
                "L-1.c", desc, Status.TIDAK_LULUS,
                "Tidak ada halaman biodata hasil scan/foto. Tanda tangan digital/ketik tidak memenuhi syarat "
                "'tanda tangan asli (TT basah)' — halaman bertanda tangan harus dipindai satu halaman penuh.")
        if orang and len(scan) < orang:
            return CheckItem(
                "L-1.c", desc, Status.PERINGATAN,
                f"Hanya {len(scan)} halaman scan untuk {orang} orang ({anggota} mahasiswa + dosen). "
                f"Halaman scan: {scan}. Pastikan setiap biodata punya halaman bertanda tangan basah.")
        return CheckItem("L-1.c", desc, Status.LULUS,
                         f"{len(scan)} halaman biodata hasil scan/foto (hal. PDF {scan}). "
                         "Pastikan tanggal tanda tangan sesuai tahun pengusulan.")

    def _check_surat_pernyataan(self) -> CheckItem:
        desc = "Surat Pernyataan: scan halaman penuh, TT basah & meterai Rp10.000"
        idx = None
        for n in self.doc.lampiran_pages:
            if re.search(r'Surat\s+Pernyataan\s+Ketua', self.doc.pages[n - 1].text, re.IGNORECASE):
                idx = n
                break
        if idx is None:
            return CheckItem("L-4.c", desc, Status.PERINGATAN,
                             "Halaman Surat Pernyataan tidak ditemukan. Cek manual tanda tangan & meterai.")
        kandidat = [self.doc.pages[i - 1] for i in (idx, idx + 1) if i <= len(self.doc.pages)]
        if any(p.max_image_ratio >= SCAN_MIN_RATIO for p in kandidat):
            return CheckItem("L-4.c", desc, Status.LULUS,
                             f"Surat Pernyataan berupa scan (hal. PDF {idx}). Verifikasi visual: meterai Rp10.000 "
                             "tertempel & tertanda tangan, tanggal sesuai, judul sama dengan isian simbelmawa.")
        if any(_small_images(p) for p in kandidat):
            return CheckItem("L-4.c", desc, Status.TIDAK_LULUS,
                             "Surat Pernyataan berupa teks dengan gambar kecil (meterai/TT tempel). Panduan: "
                             "diberi tanda tangan basah lalu satu halaman penuh dipindai/difoto rapi.")
        return CheckItem("L-4.c", desc, Status.TIDAK_LULUS,
                         "Tidak ada gambar/scan di Surat Pernyataan — tanda tangan basah & meterai tidak terdeteksi.")
