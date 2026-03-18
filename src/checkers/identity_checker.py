"""
Modul 1 — Identitas & Kelengkapan Formal.
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from config import JENIS_PKM_VALID, STRUKTUR_BAB_PKM


class IdentityChecker(BaseChecker):

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 1: Identitas & Kelengkapan Formal", bobot=0.20)
        result.items.extend([
            self._check_judul_kapital(),
            self._check_judul_panjang(),
            self._check_judul_akronim(),
            self._check_jenis_pkm_valid(),
            self._check_jenis_pkm_konsisten(),
            self._check_jumlah_anggota(),
            self._check_dosen_nuptk(),
        ])
        return result

    # Kata sambung dan kata depan yang seharusnya HURUF KECIL di tengah judul
    # (kecuali jika menjadi kata pertama)
    KATA_KECIL_JUDUL = {
        # Kata depan (preposisi) Indonesia
        "di", "ke", "dari", "pada", "dalam", "untuk", "dengan", "oleh",
        "tentang", "bagi", "atas", "bawah", "luar", "antara", "melalui",
        "terhadap", "menurut", "hingga", "sampai", "selama", "sejak",
        "sekitar", "sepanjang", "sebelum", "sesudah", "setelah", "sesuai",
        "sebagai", "seperti", "selain", "kecuali", "demi", "per",
        "berdasarkan", "mengenai", "terkait",
        # Kata sambung (konjungsi) Indonesia
        "dan", "atau", "serta", "tetapi", "namun", "melainkan", "maupun",
        "yang", "agar", "bila", "jika", "karena", "sebab", "sehingga",
        "meskipun", "walaupun", "meski", "walau", "bahwa", "ketika",
        "setelah", "sebelum", "sejak", "sampai", "saat", "sedangkan",
        "supaya", "agar", "walaupun", "kendati", "biarpun",
        # Konjungsi/artikel Inggris (untuk judul bilingual/campuran)
        "and", "or", "but", "for", "nor", "yet", "so",
        "of", "in", "on", "at", "by", "to", "up", "as", "via",
        "a", "an", "the",
    }

    # ─── Judul ───────────────────────────────────────────────────────────────

    def _check_judul_kapital(self) -> CheckItem:
        """
        Cek format judul: Title Case.
        - Kata konten (noun, verb, adj, adv) → huruf pertama kapital
        - Kata sambung/depan (dan, atau, di, ke, dari, untuk, ...) → huruf kecil
        - Kata PERTAMA selalu kapital, apapun jenisnya
        - Akronim baku (AI, PKM, dst.) tetap ALL CAPS — tidak dianggap pelanggaran
        """
        judul = self.doc.judul
        if not judul:
            return CheckItem("1.1.a", "Judul menggunakan format Title Case",
                             Status.PERINGATAN,
                             "Judul tidak diisi. Silakan input judul di form atas untuk analisis ini.")

        words = judul.split()
        salah_kecil = []    # kata konten yang seharusnya huruf besar
        salah_besar = []    # kata sambung/depan yang seharusnya huruf kecil

        for i, word in enumerate(words):
            # Bersihkan tanda baca di awal/akhir kata
            clean = re.sub(r'^[^\w\u00C0-\u024F]+|[^\w\u00C0-\u024F]+$', '', word)
            if not clean or not re.search(r'[a-zA-Z\u00C0-\u024F]', clean):
                continue  # skip angka murni, simbol, dll.

            is_first_word = (i == 0)
            clean_lower = clean.lower()
            is_small_word = clean_lower in self.KATA_KECIL_JUDUL

            # Cek apakah huruf pertama huruf besar
            first_char = next((c for c in clean if c.isalpha()), None)
            starts_upper = first_char and first_char.isupper()

            if is_first_word:
                # Kata pertama WAJIB kapital
                if not starts_upper:
                    salah_kecil.append(word)
            elif is_small_word:
                # Kata sambung/depan di tengah: harus huruf kecil semua
                if clean != clean.lower():
                    salah_besar.append(word)
            else:
                # Kata konten: harus dimulai huruf kapital
                # Pengecualian: akronim/singkatan all-caps (≤6 huruf, semua kapital) = OK
                is_acronym = clean.isupper() and len(clean) <= 6
                if not starts_upper and not is_acronym:
                    salah_kecil.append(word)

        if not salah_kecil and not salah_besar:
            return CheckItem("1.1.a", "Judul menggunakan format Title Case",
                             Status.LULUS, f'Judul: "{judul}"')

        msgs = []
        if salah_kecil:
            msgs.append(f"Kata yang harus dikapitalkan: {', '.join(salah_kecil[:4])}")
        if salah_besar:
            msgs.append(
                f"Kata sambung/depan yang harus huruf kecil: {', '.join(salah_besar[:4])}"
            )
        return CheckItem("1.1.a", "Judul menggunakan format Title Case",
                         Status.TIDAK_LULUS, ". ".join(msgs) + ".")

    def _check_judul_panjang(self) -> CheckItem:
        judul = self.doc.judul
        if not judul:
            return CheckItem("1.1.b", "Judul ≤ 20 kata",
                             Status.PERINGATAN,
                             "Judul tidak diisi. Silakan input judul di form atas untuk analisis ini.")
        words = judul.split()
        count = len(words)
        if count <= 20:
            return CheckItem("1.1.b", "Judul ≤ 20 kata",
                             Status.LULUS, f"Judul memiliki {count} kata.")
        return CheckItem("1.1.b", "Judul ≤ 20 kata",
                         Status.TIDAK_LULUS,
                         f"Judul memiliki {count} kata (melebihi batas 20 kata). "
                         f"Kelebihan {count - 20} kata.")

    def _check_judul_akronim(self) -> CheckItem:
        """
        Deteksi akronim tidak baku dalam judul.
        Dengan format Title Case, akronim muncul sebagai kata ALL CAPS (2–6 huruf)
        yang bukan kata sambung/depan dan bukan akronim baku yang sudah dikenal.
        Akronim tanpa vokal (hanya konsonan) lebih dicurigai.
        """
        judul = self.doc.judul
        if not judul:
            return CheckItem("1.1.c", "Judul tidak mengandung akronim tidak baku",
                             Status.PERINGATAN,
                             "Judul tidak diisi. Silakan input judul di form atas untuk analisis ini.")

        # Akronim baku yang diizinkan (uppercase)
        AKRONIM_BAKU = {
            "AI", "ML", "DL", "IoT", "IOT", "VR", "AR", "MR", "XR",
            "PKM", "UMKM", "UKM", "SMK", "SMA", "SMP", "SD", "PT", "PTN", "PTS",
            "LED", "UV", "RNA", "DNA", "PCR", "WHO", "FAO", "PBB", "TNI", "POLRI",
            "BPOM", "KTP", "SIM", "STNK", "NIK", "NISN", "NIM", "NPM",
            "SDG", "SDM", "APBN", "APBD", "DPR", "MPR", "DPRD", "BPJS",
            "RS", "RSU", "RSUD", "BPS", "BRI", "BCA", "BNI", "OJK",
            "OCR", "CNN", "RNN", "API", "GPU", "CPU", "RAM", "ROM",
            "USB", "TCP", "HTTP", "HTTPS", "IP", "GPS", "NFC", "BLE",
            # Akronim umum lain
            "IEC", "ISO", "IEEE", "ACM", "IT", "ICT", "UI", "UX",
        }

        words = judul.split()
        suspicious = []
        for w in words:
            clean = re.sub(r'[^\w\u00C0-\u024F]', '', w)
            if not clean or not clean.isalpha():
                continue
            # Akronim: kata ALL CAPS, panjang 2–6 huruf
            if not clean.isupper() or len(clean) < 2 or len(clean) > 6:
                continue
            # Lewati akronim baku
            if clean in AKRONIM_BAKU:
                continue
            # Lewati kata sambung/depan (seharusnya sudah lowercase, tapi antisipasi)
            if clean.lower() in self.KATA_KECIL_JUDUL:
                continue
            # Flag: akronim tidak dikenal, terutama yang tanpa vokal
            vowels = set('AEIOU')
            if not any(c in vowels for c in clean):
                # Pasti akronim (tidak ada vokal)
                suspicious.append(f"{clean} (tanpa vokal)")
            else:
                # Kemungkinan akronim — tandai sebagai peringatan ringan
                suspicious.append(clean)

        if suspicious:
            return CheckItem("1.1.c", "Judul tidak mengandung akronim tidak baku",
                             Status.PERINGATAN,
                             f"Kemungkinan akronim tidak baku: {', '.join(suspicious[:5])}. "
                             "Pastikan sudah didefinisikan di teks atau ganti dengan kepanjangan.")
        return CheckItem("1.1.c", "Judul tidak mengandung akronim tidak baku",
                         Status.LULUS, "Tidak terdeteksi akronim tidak baku.")

    # ─── Jenis PKM ───────────────────────────────────────────────────────────

    def _check_jenis_pkm_valid(self) -> CheckItem:
        """Cek apakah jenis PKM (dari input user atau deteksi) termasuk yang valid."""
        jenis = self.doc.jenis_pkm
        if not jenis:
            return CheckItem("1.1.d", "Jenis PKM valid",
                             Status.PERINGATAN,
                             "Jenis PKM tidak terdeteksi. Pilih jenis PKM di form atas.")
        if jenis in JENIS_PKM_VALID:
            return CheckItem("1.1.d", "Jenis PKM valid",
                             Status.LULUS, f"PKM-{jenis}.")
        return CheckItem("1.1.d", "Jenis PKM valid",
                         Status.TIDAK_LULUS,
                         f"Jenis PKM '{jenis}' tidak dikenal. Valid: {', '.join(JENIS_PKM_VALID)}.")

    def _check_jenis_pkm_konsisten(self) -> CheckItem:
        """
        Cek konsistensi: apakah konten dokumen (nama bab, kata kunci)
        sesuai dengan jenis PKM yang diklaim.
        Ini menangkap kasus lampiran scan dari PKM lain yang salah masuk.
        """
        jenis = self.doc.jenis_pkm
        if not jenis or jenis not in STRUKTUR_BAB_PKM:
            return CheckItem("1.1.e", "Konten sesuai jenis PKM yang diklaim",
                             Status.PERINGATAN,
                             "Jenis PKM tidak diketahui, konsistensi konten tidak dapat dicek.")

        text_upper = self.doc.full_text.upper()
        struktur = STRUKTUR_BAB_PKM[jenis]

        # Cek keyword khas per jenis PKM
        keyword_checks = {
            "K": ["RENCANA USAHA", "PELUANG PASAR", "ANALISIS PASAR"],
            "KC": ["SUMBER INSPIRASI", "TAHAP PELAKSANAAN", "TEKNOLOGI"],
            "PM": ["MITRA", "PEMBERDAYAAN", "PENGABDIAN"],
            "PI": ["MITRA USAHA", "INDUSTRI", "PENERAPAN IPTEK"],
            "RE": ["HIPOTESIS", "METODOLOGI", "TINJAUAN PUSTAKA"],
            "RSH": ["TINJAUAN PUSTAKA", "SOSIAL", "HUMANIORA"],
            "KI": ["TINJAUAN PUSTAKA", "INOVASI"],
            "VGK": ["GAGASAN", "SOLUSI"],
            "GFT": ["GAGASAN", "KESIMPULAN"],
            "AI": ["ABSTRACT", "PENDAHULUAN", "METODOLOGI"],
        }

        expected_keywords = keyword_checks.get(jenis, [])
        if not expected_keywords:
            return CheckItem("1.1.e", "Konten sesuai jenis PKM yang diklaim",
                             Status.LULUS, f"Tidak ada pengecekan konsistensi khusus untuk PKM-{jenis}.")

        found_keywords = [kw for kw in expected_keywords if kw in text_upper]
        missing_keywords = [kw for kw in expected_keywords if kw not in text_upper]

        if len(found_keywords) >= max(1, len(expected_keywords) // 2):
            return CheckItem("1.1.e", "Konten sesuai jenis PKM yang diklaim",
                             Status.LULUS,
                             f"Konten konsisten dengan PKM-{jenis}. "
                             f"Kata kunci ditemukan: {', '.join(found_keywords)}.")

        return CheckItem("1.1.e", "Konten sesuai jenis PKM yang diklaim",
                         Status.PERINGATAN,
                         f"Konten kurang konsisten dengan PKM-{jenis}. "
                         f"Kata kunci tidak ditemukan: {', '.join(missing_keywords)}. "
                         "Pastikan tidak ada lampiran dari PKM bidang lain yang terselip.")

    # ─── Tim & Dosen ─────────────────────────────────────────────────────────

    def _check_jumlah_anggota(self) -> CheckItem:
        """
        Deteksi NIM dari konteks label "NIM" (lebih akurat).
        Mendukung format NIM berbagai universitas:
        - 8-12 digit (kebanyakan PTN/PTS)
        - 7 digit dengan awalan tahun 20xx (misal UPI: 2205965, 2406620)
        """
        # Pass 1: NIM yang muncul persis setelah label "NIM"
        # Dukung 7-12 digit agar mencakup format UPI dan universitas lain
        nim_near_label = re.findall(
            r'(?:NIM|N\.I\.M)[.\s:/]*(\d{7,12})',
            self.doc.full_text,
            re.IGNORECASE,
        )
        context_nims = set(nim_near_label)

        # Pass 2: fallback — pola digit 7-12 digit yang terfilter
        all_digit_sequences = re.findall(r'\b(\d{7,12})\b', self.doc.full_text)

        def likely_nim(n: str) -> bool:
            # Telepon biasanya mulai 08 atau 62
            if n.startswith('08') or n.startswith(('628', '62')):
                return False
            # Tanggal seperti 20231228, 20240101 (8 digit)
            if re.match(r'^20[12]\d(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$', n):
                return False
            # Nomor yang terlalu seragam (111111111)
            if len(set(n)) <= 2:
                return False
            # 7-digit: harus dimulai dengan tahun 20xx (UPI dan beberapa PTN)
            if len(n) == 7 and not re.match(r'^2[01234]', n):
                return False
            return True

        fallback_nims = {n for n in all_digit_sequences if likely_nim(n)}

        nims = context_nims if context_nims else fallback_nims
        count = len(nims)
        nim_list = sorted(nims)[:8]  # tampilkan maks 8

        nim_display = ", ".join(nim_list)
        if len(nims) > 8:
            nim_display += f", ... (+{len(nims) - 8} lagi)"

        source_note = "(dari label NIM)" if context_nims else "(estimasi dari pola angka)"

        if count == 0:
            return CheckItem("1.2.a", "Jumlah anggota tim 3–5 mahasiswa",
                             Status.PERINGATAN,
                             "NIM tidak terdeteksi otomatis. Periksa manual jumlah anggota tim.")
        elif 3 <= count <= 5:
            return CheckItem("1.2.a", "Jumlah anggota tim 3–5 mahasiswa",
                             Status.LULUS,
                             f"Terdeteksi {count} NIM {source_note}: {nim_display}.")
        elif count < 3:
            return CheckItem("1.2.a", "Jumlah anggota tim 3–5 mahasiswa",
                             Status.TIDAK_LULUS,
                             f"Hanya {count} NIM terdeteksi {source_note}: {nim_display}. "
                             "Minimal 3 mahasiswa (1 ketua + 2 anggota).")
        else:
            return CheckItem("1.2.a", "Jumlah anggota tim 3–5 mahasiswa",
                             Status.PERINGATAN,
                             f"Terdeteksi {count} NIM {source_note}: {nim_display}. "
                             "Jika benar > 5, ini melanggar ketentuan. "
                             "Jika tidak, kemungkinan false positive — cek manual.")

    def _check_dosen_nuptk(self) -> CheckItem:
        """
        Cek keberadaan NIP/NUPTK dosen pendamping.
        - Panduan PKM 2026: label 'NIP/NUPTK' → LULUS
        - Panduan lama: label 'NIP/NIDN' → PERINGATAN (format lama, perlu konfirmasi)
        """
        text = self.doc.full_text

        # --- Cari NIP/NUPTK (format panduan PKM 2026) ---
        pat_nuptk_label = r'NIP\s*/\s*NUPTK'
        pat_nuptk_nilai = pat_nuptk_label + r'[\s:]*(\d[\d\s./-]{8,24}\d)'

        match = re.search(pat_nuptk_nilai, text, re.IGNORECASE)
        if match:
            return CheckItem("1.3.a", "NIP/NUPTK dosen pendamping tercantum",
                             Status.LULUS,
                             f"Terdeteksi NIP/NUPTK: {match.group(1).strip()}.")

        if re.search(pat_nuptk_label, text, re.IGNORECASE):
            return CheckItem("1.3.a", "NIP/NUPTK dosen pendamping tercantum",
                             Status.PERINGATAN,
                             "Label 'NIP/NUPTK' ditemukan tetapi nilainya tidak terbaca. "
                             "Periksa manual apakah nomor sudah terisi di biodata dosen.")

        # --- Cari NIP/NIDN (format panduan lama) → PERINGATAN ---
        pat_nidn_label = r'NIP\s*/\s*NIDN'
        pat_nidn_nilai = pat_nidn_label + r'[\s:]*(\d[\d\s./-]{8,24}\d)'

        match = re.search(pat_nidn_nilai, text, re.IGNORECASE)
        if match:
            return CheckItem("1.3.a", "NIP/NUPTK dosen pendamping tercantum",
                             Status.PERINGATAN,
                             f"Terdeteksi NIP/NIDN (format lama): {match.group(1).strip()}. "
                             "Panduan PKM 2026 menggunakan label 'NIP/NUPTK' — pastikan "
                             "template biodata dosen sudah diperbarui sesuai panduan terbaru.")

        if re.search(pat_nidn_label, text, re.IGNORECASE):
            return CheckItem("1.3.a", "NIP/NUPTK dosen pendamping tercantum",
                             Status.PERINGATAN,
                             "Label 'NIP/NIDN' ditemukan (format panduan lama). "
                             "Panduan PKM 2026 menggunakan 'NIP/NUPTK'. "
                             "Perbarui template biodata dosen dan isi nilai NIP/NUPTK.")

        # --- Fallback: cari NUPTK atau NIDN standalone ---
        for label_pat in [r'\bNUPTK\b', r'\bNIDN\b']:
            m = re.search(label_pat + r'[\s:]*(\d[\d\s./-]{8,24}\d)', text, re.IGNORECASE)
            if m:
                lbl = re.search(label_pat, text, re.IGNORECASE).group(0)
                return CheckItem("1.3.a", "NIP/NUPTK dosen pendamping tercantum",
                                 Status.PERINGATAN,
                                 f"Terdeteksi {lbl}: {m.group(1).strip()} (tanpa label NIP/). "
                                 "Format yang benar di panduan PKM 2026 adalah 'NIP/NUPTK'.")

        return CheckItem("1.3.a", "NIP/NUPTK dosen pendamping tercantum",
                         Status.TIDAK_LULUS,
                         "Label NIP/NUPTK tidak ditemukan di dokumen. "
                         "Pastikan biodata dosen pendamping memuat kolom 'NIP/NUPTK' beserta nilainya "
                         "(sesuai template panduan PKM 2026).")
