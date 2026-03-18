"""
FASE 1 — Hard Disqualifiers.
Jika salah satu terpenuhi, proposal langsung TIDAK LOLOS Tahap 1.
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status


class HardDisqualifierChecker(BaseChecker):

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Hard Disqualifiers", bobot=0)
        result.items.extend([
            self._check_halaman_sampul(),
            self._check_halaman_pengesahan(),
            self._check_ringkasan_abstrak(),
            self._check_similaritas(),
        ])
        return result

    def _check_halaman_sampul(self) -> CheckItem:
        """
        HD-01: Deteksi halaman sampul.
        Ciri: halaman pertama berisi judul besar + logo + tidak ada konten bab.
        """
        if not self.doc.pages:
            return CheckItem("HD-01", "Halaman sampul", Status.PERINGATAN,
                             "Dokumen kosong, tidak dapat diperiksa.")

        page1_text = self.doc.pages[0].text.upper()

        patterns_cover = [
            r'\bPROGRAM\s+KREATIVITAS\s+MAHASISWA\b',
            r'\bUSULAN\s+PROGRAM\b',
            r'\bDIAJUKAN\s+KEPADA\b',
        ]
        # Jika halaman 1 tidak mengandung tanda bab/konten inti
        has_bab_content = bool(re.search(r'\bBAB\s+(1|I)\b', page1_text))
        has_cover_pattern = any(re.search(p, page1_text) for p in patterns_cover)

        # Deteksi tambahan: halaman 1 sangat pendek (< 100 kata) dan ada logo/gambar
        page1_word_count = len(page1_text.split())
        has_image_on_p1 = bool(self.doc.pages[0].images)

        if has_cover_pattern and not has_bab_content:
            return CheckItem("HD-01", "Halaman sampul (DILARANG ada di proposal)",
                             Status.TIDAK_LULUS,
                             "Terdeteksi halaman sampul pada halaman 1. "
                             "Proposal PKM tidak boleh memiliki halaman sampul.")

        if page1_word_count < 80 and has_image_on_p1 and not has_bab_content:
            return CheckItem("HD-01", "Halaman sampul (DILARANG ada di proposal)",
                             Status.PERINGATAN,
                             "Halaman 1 terindikasi sebagai halaman sampul "
                             "(sedikit teks + ada gambar/logo). Perlu cek manual.")

        return CheckItem("HD-01", "Halaman sampul (DILARANG ada di proposal)",
                         Status.LULUS, "Tidak terdeteksi halaman sampul.")

    def _check_halaman_pengesahan(self) -> CheckItem:
        """
        HD-02: Deteksi halaman pengesahan.
        Ciri: heading 'halaman pengesahan' atau 'lembar pengesahan'.
        """
        keywords = [
            r'halaman\s+pengesahan',
            r'lembar\s+pengesahan',
            r'halaman\s+persetujuan',
        ]
        for page in self.doc.pages[:5]:
            text_lower = page.text.lower()
            if any(re.search(kw, text_lower) for kw in keywords):
                return CheckItem(
                    "HD-02", "Halaman pengesahan (DILARANG ada di proposal)",
                    Status.TIDAK_LULUS,
                    f"Terdeteksi halaman pengesahan pada halaman {page.page_number}. "
                    "Proposal PKM tidak boleh memiliki halaman pengesahan."
                )

        return CheckItem("HD-02", "Halaman pengesahan (DILARANG ada di proposal)",
                         Status.LULUS, "Tidak terdeteksi halaman pengesahan.")

    def _check_ringkasan_abstrak(self) -> CheckItem:
        """
        HD-03: Deteksi ringkasan / abstrak.
        Ciri: heading 'Ringkasan', 'Abstrak', 'Abstract'.
        """
        keywords = [r'\bringkasan\b', r'\babstrak\b', r'\babstract\b']
        for page in self.doc.pages[:10]:
            text_lower = page.text.lower()
            lines = text_lower.split('\n')
            for line in lines:
                stripped = line.strip()
                if any(re.fullmatch(kw, stripped) for kw in keywords):
                    return CheckItem(
                        "HD-03", "Ringkasan/Abstrak (DILARANG ada di proposal)",
                        Status.TIDAK_LULUS,
                        f"Terdeteksi heading '{stripped.title()}' pada halaman {page.page_number}. "
                        "Ringkasan/Abstrak hanya ada di laporan akhir, bukan proposal."
                    )

        return CheckItem("HD-03", "Ringkasan/Abstrak (DILARANG ada di proposal)",
                         Status.LULUS, "Tidak terdeteksi ringkasan/abstrak.")

    def _check_similaritas(self) -> CheckItem:
        """
        HD-05: Cek indeks similaritas dari lampiran hasil Turnitin/iThenticate.
        Cari pola persentase di sekitar kata 'similarity'/'similaritas'.
        """
        pattern = re.compile(
            r'(?:similarity\s*(?:index)?|indeks?\s*similaritas|similaritas)[^\d]*(\d{1,3})\s*%',
            re.IGNORECASE
        )
        match = pattern.search(self.doc.lampiran_text or self.doc.full_text)
        if match:
            pct = int(match.group(1))
            if pct > 25:
                return CheckItem(
                    "HD-05", "Indeks similaritas ≤ 25%",
                    Status.TIDAK_LULUS,
                    f"Indeks similaritas terdeteksi: {pct}% (melebihi batas maksimum 25%)."
                )
            return CheckItem(
                "HD-05", "Indeks similaritas ≤ 25%",
                Status.LULUS,
                f"Indeks similaritas: {pct}% (memenuhi syarat ≤ 25%)."
            )

        return CheckItem(
            "HD-05", "Indeks similaritas ≤ 25%",
            Status.PERINGATAN,
            "Nilai similaritas tidak ditemukan secara otomatis. "
            "Pastikan lampiran hasil Turnitin/iThenticate tersedia dan terbaca."
        )
