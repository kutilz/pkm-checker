"""
Modul 3 — Struktur Dokumen.
Cek kelengkapan bab, batas halaman inti, dan format Daftar Pustaka Harvard.
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from config import MAX_CORE_PAGES, STRUKTUR_BAB_PKM, DAFPUS_FORMAT

# Heading-heading yang bukan entri pustaka
NON_ENTRY_PREFIXES = re.compile(
    r'^(DAFTAR\s+PUSTAKA|LAMPIRAN|BAB\s+\d|GAMBAR\s+\d|TABEL\s+\d|GRAFIK|FOTO'
    r'|HALAMAN|KATA\s+PENGANTAR|DAFPUS|PENDAHULUAN|PENUTUP|KESIMPULAN|SARAN'
    r'|ABSTRAK|RINGKASAN)',
    re.IGNORECASE
)

# Pola AWAL entri Harvard: (YYYY) atau (YYYYa) dalam tanda kurung
ENTRY_START_HARVARD = re.compile(r'\(\d{4}[a-z]?\)')

# Pola AWAL entri APA/IEEE: Author. YYYY. atau Author. YYYY,
# Ciri: ada tahun (1900-2030) yang diikuti titik/koma, muncul di <120 karakter pertama
# dan didahului oleh tanda baca ('. ' atau ', ')
ENTRY_START_APA = re.compile(
    r'^.{0,120}[.,]\s+(?:19|20)\d{2}\s*[.,]'
)


def _is_entry_start(line: str) -> bool:
    """
    Deteksi apakah baris ini adalah awal entri pustaka baru.
    Format yang diperiksa ditentukan oleh DAFPUS_FORMAT di config.py:
      "HARVARD"  → hanya Author (YYYY) ...
      "APA"      → hanya Author. YYYY. Title...
      "KEDUANYA" → keduanya (default)
    """
    if DAFPUS_FORMAT in ("HARVARD", "KEDUANYA"):
        if ENTRY_START_HARVARD.search(line):
            return True
    if DAFPUS_FORMAT in ("APA", "KEDUANYA"):
        if ENTRY_START_APA.match(line) and re.match(r'^[A-ZÁÉÍÓÚ\u00C0-\u024F]', line):
            return True
    return False


def _parse_dafpus_entries(dafpus_text: str) -> list[str]:
    """
    Parse daftar pustaka menjadi entri-entri individual.
    Mendukung format Harvard dan APA/IEEE:

    Harvard : Surname, I. (2022) 'Judul'...
    APA     : Surname, I. 2022. Judul...  |  Lembaga. 2022. Judul...
    """
    raw_lines = [l.strip() for l in dafpus_text.split('\n')]
    entries: list[str] = []
    current: str | None = None

    for line in raw_lines:
        if not line:
            continue
        # Bersihkan nomor halaman yang melekat di awal baris ("34Bank" → "Bank")
        line = re.sub(r'^\d{1,3}([A-Z])', r'\1', line)
        # Abaikan heading non-entri
        if NON_ENTRY_PREFIXES.match(line):
            continue
        # Abaikan baris yang hanya angka (nomor halaman) atau sangat pendek
        if re.fullmatch(r'[\d\s.]+', line) or len(line) < 8:
            continue

        if _is_entry_start(line):
            if current is not None:
                entries.append(current)
            current = line
        elif current is not None:
            current += " " + line
        # else: teks sebelum entri pertama (heading), abaikan

    if current is not None:
        entries.append(current)

    return entries


class StructureChecker(BaseChecker):

    def __init__(self, doc, use_gemini: bool = False):
        super().__init__(doc)
        self.use_gemini = use_gemini

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 3: Struktur Dokumen", bobot=0.20)
        result.items.extend([
            self._check_daftar_isi(),
            self._check_bab_wajib(),
            self._check_bab_format_capslock(),
            self._check_batas_halaman_inti(),
            self._check_dafpus_ada(),
            self._check_dafpus_no_etal(),
            self._check_dafpus_alfabetis(),
            self._check_dafpus_akses_url(),
        ])

        if self.use_gemini:
            result.items.append(self._check_sitasi_gemini())

        return result

    def _check_daftar_isi(self) -> CheckItem:
        if re.search(r'daftar\s+isi', self.doc.full_text, re.IGNORECASE):
            return CheckItem("3.1.a", "Daftar Isi ada",
                             Status.LULUS, "Daftar Isi ditemukan.")
        return CheckItem("3.1.a", "Daftar Isi ada",
                         Status.TIDAK_LULUS, "Daftar Isi tidak ditemukan dalam dokumen.")

    def _check_bab_wajib(self) -> CheckItem:
        """Cek keberadaan BAB 1, BAB 2, BAB 3, BAB 4, dan Daftar Pustaka."""
        text_upper = self.doc.full_text.upper()
        missing = []

        # Pola heading bab: tidak diikuti titik-titik (bukan dari Daftar Isi)
        def bab_exists(pattern: str) -> bool:
            for m in re.finditer(pattern, text_upper):
                # Ambil teks dari posisi match hingga akhir baris
                line_end = text_upper.find('\n', m.start())
                line = text_upper[m.start(): line_end if line_end > 0 else m.start() + 80]
                if not re.search(r'\.{3,}\s*\d+\s*$', line):
                    return True
            return False

        fixed_patterns = {
            "BAB 1 PENDAHULUAN":    r'BAB\s+(?:1|I)[.\s]+PENDAHULUAN',
            "BAB 4 BIAYA DAN JADWAL KEGIATAN": r'BAB\s+(?:4|IV)[.\s]+BIAYA',
            "DAFTAR PUSTAKA":       r'DAFTAR\s+PUSTAKA',
            "LAMPIRAN":             r'\bLAMPIRAN\b',
        }

        for label, pattern in fixed_patterns.items():
            if not bab_exists(pattern):
                missing.append(label)

        pkm = self.doc.jenis_pkm
        if pkm and pkm in STRUKTUR_BAB_PKM:
            bab2_name = STRUKTUR_BAB_PKM[pkm]["bab2"].upper()
            bab3_name = STRUKTUR_BAB_PKM[pkm]["bab3"].upper()

            if not bab_exists(r'BAB\s+(?:2|II)[.\s]+' + re.escape(bab2_name[:10])):
                missing.append(f"BAB 2 ({STRUKTUR_BAB_PKM[pkm]['bab2']})")
            if bab3_name != "—" and not bab_exists(r'BAB\s+(?:3|III)[.\s]+' + re.escape(bab3_name[:10])):
                missing.append(f"BAB 3 ({STRUKTUR_BAB_PKM[pkm]['bab3']})")

        if not missing:
            return CheckItem("3.1.b", "Bab-bab wajib lengkap",
                             Status.LULUS, "Semua bab wajib ditemukan.")
        return CheckItem("3.1.b", "Bab-bab wajib lengkap",
                         Status.TIDAK_LULUS,
                         f"Tidak ditemukan: {', '.join(missing)}.")

    def _check_bab_format_capslock(self) -> CheckItem:
        """
        Cek apakah heading bab menggunakan format HURUF KAPITAL semua.
        Benar: 'BAB 3. TAHAP PELAKSANAAN'
        Salah: 'BAB 3 Tahap Pelaksanaan'
        """
        text = self.doc.full_text
        bab_lines = []

        for line in text.split('\n'):
            stripped = line.strip()
            # Cari baris yang dimulai dengan "BAB" diikuti angka/romawi
            if re.match(r'^BAB\s+[1-4IVX]+', stripped, re.IGNORECASE):
                # Pastikan bukan dari Daftar Isi
                if not re.search(r'\.{3,}\s*\d+\s*$', stripped) and len(stripped) < 80:
                    bab_lines.append(stripped)

        if not bab_lines:
            return CheckItem("3.1.c", "Heading bab menggunakan HURUF KAPITAL",
                             Status.PERINGATAN,
                             "Heading bab tidak terdeteksi. Pastikan format 'BAB 1. PENDAHULUAN' (kapital).")

        wrong = [b for b in bab_lines if b != b.upper()]
        if not wrong:
            return CheckItem("3.1.c", "Heading bab menggunakan HURUF KAPITAL",
                             Status.LULUS,
                             f"Semua {len(bab_lines)} heading bab menggunakan huruf kapital. "
                             f"Contoh: '{bab_lines[0]}'")

        wrong_examples = wrong[:3]
        return CheckItem("3.1.c", "Heading bab menggunakan HURUF KAPITAL",
                         Status.TIDAK_LULUS,
                         f"Heading bab tidak seluruhnya kapital: "
                         f"{'; '.join(wrong_examples)}. "
                         "Format yang benar: 'BAB 3. TAHAP PELAKSANAAN' (semua kapital).")

    def _check_batas_halaman_inti(self) -> CheckItem:
        """Bab 1 s.d. Daftar Pustaka maksimum 10 halaman."""
        count = len(self.doc.core_pages)
        if count == 0:
            return CheckItem("3.2", "Bagian inti ≤ 10 halaman",
                             Status.PERINGATAN,
                             "Segmentasi dokumen gagal — pastikan dokumen memiliki heading "
                             "'BAB 1 PENDAHULUAN' dan 'DAFTAR PUSTAKA' yang terbaca.")
        if count <= MAX_CORE_PAGES:
            pages_str = f"hal. {self.doc.core_pages[0]}–{self.doc.core_pages[-1]}" if len(self.doc.core_pages) > 1 else f"hal. {self.doc.core_pages[0]}"
            return CheckItem("3.2", "Bagian inti ≤ 10 halaman",
                             Status.LULUS,
                             f"Bagian inti: {count} halaman ({pages_str}).")
        pages_str = f"hal. {self.doc.core_pages[0]}–{self.doc.core_pages[-1]}"
        return CheckItem("3.2", "Bagian inti ≤ 10 halaman",
                         Status.TIDAK_LULUS,
                         f"Bagian inti {count} halaman ({pages_str}), "
                         f"melebihi batas maksimum 10 halaman.")

    def _check_dafpus_ada(self) -> CheckItem:
        dafpus = self.doc.dafpus_text.strip()
        if not dafpus:
            return CheckItem("3.4.1", "Daftar Pustaka ada dan tidak kosong",
                             Status.TIDAK_LULUS,
                             "Daftar Pustaka tidak ditemukan atau tidak terbaca.")

        entries = _parse_dafpus_entries(dafpus)
        if entries:
            return CheckItem("3.4.1", "Daftar Pustaka ada dan tidak kosong",
                             Status.LULUS,
                             f"Ditemukan {len(entries)} entri pustaka.")

        fmt_label = {"APA": "APA", "HARVARD": "Harvard", "KEDUANYA": "APA/Harvard"}.get(DAFPUS_FORMAT, DAFPUS_FORMAT)
        return CheckItem("3.4.1", "Daftar Pustaka ada dan tidak kosong",
                         Status.TIDAK_LULUS,
                         f"Daftar Pustaka kosong atau tidak terbaca (format dicek: {fmt_label}). "
                         "Pastikan PDF dapat dibaca teks (bukan scan gambar).")

    def _check_dafpus_no_etal(self) -> CheckItem:
        """
        Tidak boleh ada 'et al.' atau 'dkk' di DAFTAR NAMA PENULIS di daftar pustaka.
        Pencarian dilakukan pada teks setelah heading 'DAFTAR PUSTAKA',
        bukan seluruh dokumen, untuk menghindari false positive dari
        sitasi dalam teks bab.
        """
        dafpus = self.doc.dafpus_text
        if not dafpus:
            return CheckItem("3.4.2.d", "Tidak ada 'et al.' / 'dkk' di daftar pustaka",
                             Status.PERINGATAN, "Daftar Pustaka tidak terbaca.")

        # Hanya cari dalam entri yang sudah diparsing (bukan raw text)
        entries = _parse_dafpus_entries(dafpus)
        if not entries:
            return CheckItem("3.4.2.d", "Tidak ada 'et al.' / 'dkk' di daftar pustaka",
                             Status.PERINGATAN,
                             "Entri daftar pustaka tidak terparsing, cek manual.")

        # "et al." dalam JUDUL artikel adalah wajar; yang bermasalah adalah
        # di bagian PENULIS (sebelum tahun). Kita cek pada bagian awal tiap entri.
        etal_pattern = re.compile(r'\bet\.?\s*al\.?\b|\bdkk\.?\b', re.IGNORECASE)
        # Deteksi posisi tahun: Harvard (YYYY) atau APA YYYY.
        bad_entries = []
        for entry in entries:
            # Ambil bagian PENULIS: sebelum tahun pertama yang muncul
            m = re.search(r'\(\d{4}[a-z]?\)', entry)
            if not m:
                # Format APA: cari "YYYY." dalam 150 karakter pertama
                m = re.search(r'\b(?:19|20)\d{2}\b', entry[:150])
            author_part = entry[:m.start()] if m else entry[:120]
            if etal_pattern.search(author_part):
                bad_entries.append(entry[:80])

        if bad_entries:
            return CheckItem("3.4.2.d", "Tidak ada 'et al.' / 'dkk' di daftar pustaka",
                             Status.TIDAK_LULUS,
                             f"Ditemukan 'et al.'/'dkk' di bagian penulis pada {len(bad_entries)} entri: "
                             f'"{bad_entries[0][:60]}...". '
                             "Semua nama penulis harus ditulis lengkap.")
        return CheckItem("3.4.2.d", "Tidak ada 'et al.' / 'dkk' di daftar pustaka",
                         Status.LULUS, f"Tidak ditemukan 'et al.' atau 'dkk' ({len(entries)} entri dicek).")

    def _check_dafpus_alfabetis(self) -> CheckItem:
        """Cek apakah entri daftar pustaka diurutkan alfabetis berdasarkan nama penulis."""
        dafpus = self.doc.dafpus_text
        if not dafpus:
            return CheckItem("3.4.2.e", "Daftar Pustaka urut alfabetis",
                             Status.PERINGATAN, "Daftar Pustaka tidak terbaca.")

        entries = _parse_dafpus_entries(dafpus)
        # Semua entri yang berhasil diparsing dianggap valid
        valid_entries = entries

        if len(valid_entries) < 2:
            return CheckItem("3.4.2.e", "Daftar Pustaka urut alfabetis",
                             Status.PERINGATAN,
                             f"Hanya {len(valid_entries)} entri terdeteksi. "
                             "Tidak cukup untuk memeriksa urutan alfabetis.")

        # Ambil kata pertama (nama belakang) dari tiap entri
        first_words = [e.split()[0].rstrip(',.') for e in valid_entries if e.split()]

        is_sorted = all(
            first_words[i].lower() <= first_words[i + 1].lower()
            for i in range(len(first_words) - 1)
        )

        if is_sorted:
            return CheckItem("3.4.2.e", "Daftar Pustaka urut alfabetis",
                             Status.LULUS,
                             f"Urutan alfabetis terverifikasi ({len(valid_entries)} entri).")

        violations = []
        for i in range(len(first_words) - 1):
            if first_words[i].lower() > first_words[i + 1].lower():
                violations.append(f"'{first_words[i]}' sebelum '{first_words[i+1]}'")
                if len(violations) >= 3:
                    break

        return CheckItem("3.4.2.e", "Daftar Pustaka urut alfabetis",
                         Status.TIDAK_LULUS,
                         f"Urutan tidak alfabetis: {'; '.join(violations)}.")

    def _check_dafpus_akses_url(self) -> CheckItem:
        """Cek format tanggal akses website: (Diakses DD Bulan YYYY)."""
        dafpus = self.doc.dafpus_text
        if not dafpus:
            return CheckItem("3.4.4.b", "Format tanggal akses URL",
                             Status.PERINGATAN, "Daftar Pustaka tidak terbaca.")

        url_pat = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
        # Dua format tanggal akses yang umum digunakan:
        # 1. "(Diakses DD Bulan YYYY)" — Harvard
        # 2. "Diakses: DD Bulan YYYY." atau "Diakses DD Bulan YYYY." — APA/IEEE
        access_pat = re.compile(
            r'(?:\(Diakses\s+\d{1,2}\s+\w+\s+\d{4}\)'
            r'|Diakses\s*:?\s+\d{1,2}\s+\w+\s+\d{4})',
            re.IGNORECASE
        )

        entries = _parse_dafpus_entries(dafpus)
        url_entries = [e for e in entries if url_pat.search(e)]

        if not url_entries:
            return CheckItem("3.4.4.b", "Format tanggal akses URL",
                             Status.LULUS, "Tidak ada referensi URL dalam daftar pustaka.")

        bad = [e for e in url_entries if not access_pat.search(e)]
        if not bad:
            return CheckItem("3.4.4.b", "Format tanggal akses URL",
                             Status.LULUS,
                             f"Semua {len(url_entries)} URL memiliki format tanggal akses yang benar.")

        return CheckItem("3.4.4.b", "Format tanggal akses URL",
                         Status.TIDAK_LULUS,
                         f"{len(bad)} dari {len(url_entries)} URL tidak memiliki "
                         "format '(Diakses DD Bulan YYYY)'.")

    def _check_sitasi_gemini(self) -> CheckItem:
        """
        Gunakan Gemini API untuk cross-check sitasi di teks vs entri daftar pustaka.
        """
        from src.ai.gemini_client import check_citation_consistency

        # Ekstrak sitasi dari teks inti
        # Mendukung format Harvard "(Penulis, Tahun)" dan APA "Penulis (Tahun)"
        sitasi_pattern = re.compile(
            r'\(([A-Z][a-zA-Záéíóú]+(?:[\s,]+(?:&|dan|et al\.?)\s+[A-Z][a-zA-Z]+)?,?\s*(?:19|20)\d{2}[a-z]?)\)'
            r'|([A-Z][a-zA-Záéíóú]+(?:\s+(?:&|dan)\s+[A-Z][a-z]+)?)\s+\((?:19|20)\d{2}[a-z]?\)',
        )
        core_text = "\n".join(
            self.doc.pages[i - 1].text
            for i in self.doc.core_pages if i <= len(self.doc.pages)
        )
        sitasi_raw = sitasi_pattern.findall(core_text)
        sitasi_list = list({s[0] or s[1] for s in sitasi_raw if s[0] or s[1]})

        dafpus_entries = _parse_dafpus_entries(self.doc.dafpus_text or "")

        if not sitasi_list or not dafpus_entries:
            return CheckItem("4.4", "Konsistensi sitasi ↔ daftar pustaka (Gemini)",
                             Status.PERINGATAN,
                             "Sitasi atau daftar pustaka tidak terdeteksi untuk analisis Gemini.")

        try:
            hasil = check_citation_consistency(sitasi_list[:30], dafpus_entries[:30])
            masalah = []
            if hasil.get("tidak_ada_di_dafpus"):
                masalah.append(
                    f"Sitasi tidak ada di dafpus: {', '.join(hasil['tidak_ada_di_dafpus'][:3])}"
                )
            if hasil.get("tidak_disitasi"):
                masalah.append(
                    f"Dafpus tidak disitasi: {', '.join(hasil['tidak_disitasi'][:3])}"
                )
            if hasil.get("inkonsistensi"):
                masalah.append(
                    f"Inkonsistensi: {', '.join(hasil['inkonsistensi'][:3])}"
                )

            if not masalah:
                return CheckItem("4.4", "Konsistensi sitasi ↔ daftar pustaka (Gemini)",
                                 Status.LULUS,
                                 f"Semua sitasi ({len(sitasi_list)}) konsisten dengan daftar pustaka.")

            return CheckItem("4.4", "Konsistensi sitasi ↔ daftar pustaka (Gemini)",
                             Status.TIDAK_LULUS,
                             " | ".join(masalah))

        except Exception as e:
            return CheckItem("4.4", "Konsistensi sitasi ↔ daftar pustaka (Gemini)",
                             Status.PERINGATAN,
                             f"Gemini API error: {e}. Cek manual konsistensi sitasi.")
