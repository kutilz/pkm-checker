"""
Modul 1 — Identitas & Kelengkapan Formal.

Aturan judul Panduan PKM 2026 (sama di semua buku bidang):
"Judul dibuat ringkas maksimum 20 kata, tidak boleh menggunakan akronim atau
singkatan yang tidak baku, ... ditulis menggunakan huruf kapital, ditulis dalam
Bahasa Indonesia."
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from config import JENIS_PKM_VALID, STRUKTUR_BAB_PKM

# Akronim/singkatan baku yang lazim dan boleh muncul di judul
AKRONIM_BAKU = {
    "AI", "ML", "DL", "IOT", "VR", "AR", "MR", "XR", "PKM", "UMKM", "UKM", "SMK", "SMA", "SMP",
    "SD", "PT", "PTN", "PTS", "LED", "UV", "RNA", "DNA", "PCR", "WHO", "FAO", "PBB", "TNI", "POLRI",
    "BPOM", "KTP", "SIM", "NIK", "SDG", "SDGS", "SDM", "APBN", "APBD", "DPR", "BPJS", "RS", "RSUD",
    "BPS", "OJK", "OCR", "CNN", "API", "GPU", "CPU", "USB", "GPS", "NFC", "IKN", "TBC", "HIV", "ASI",
    "MPASI", "PAUD", "SNI", "ISO", "IT", "ICT", "UI", "UX", "CCTV", "QR", "PH", "RFID", "LORA",
}

# Kata bahasa Inggris yang sering terselip di judul PKM (judul wajib Bahasa Indonesia)
KATA_INGGRIS = {
    "for", "with", "based", "system", "systems", "smart", "the", "of", "and", "to", "on",
    "tool", "tools", "comprehensive", "enhanced", "guardian", "device", "using", "detection",
    "adaptive", "short", "distance", "portable", "food", "safety", "glasses", "application",
    "learning", "machine", "deep", "real", "time", "design", "development", "implementation",
    "management", "early", "warning", "wearable", "chemical", "intelligent", "artificial",
    "intelligence", "recognition", "tracking", "automatic", "automated", "security", "women",
    "protection", "sustainable", "green", "water", "energy", "monitor", "assistant", "vision",
    "computer", "integrated", "innovation", "framework", "platform",
}


def _pisah_nama_produk(judul: str) -> tuple[str, str]:
    """'PRODUK-X: ALAT PINTAR ...' → ('PRODUK-X', 'ALAT PINTAR ...')."""
    if ":" in judul:
        nama, sisa = judul.split(":", 1)
        if len(nama.split()) <= 3:
            return nama.strip(), sisa.strip()
    return "", judul


class IdentityChecker(BaseChecker):

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 1: Identitas & Kelengkapan Formal", bobot=0.15)
        result.items.extend([
            self._check_judul_kapital(),
            self._check_judul_panjang(),
            self._check_judul_akronim(),
            self._check_judul_bahasa(),
            self._check_jenis_pkm_valid(),
            self._check_jenis_pkm_konsisten(),
            self._check_jumlah_anggota(),
            self._check_dosen_nuptk(),
        ])
        return result

    # ─── Judul ───────────────────────────────────────────────────────────────

    def _judul_kosong(self, kode: str, desc: str) -> CheckItem:
        return CheckItem(kode, desc, Status.PERINGATAN,
                         "Judul tidak diisi/tidak terbaca (Surat Pernyataan biasanya berupa scan). "
                         "Isi judul di form atas untuk analisis ini.")

    def _check_judul_kapital(self) -> CheckItem:
        """Panduan 2026: judul ditulis menggunakan huruf kapital (bukan Title Case)."""
        desc = "Judul ditulis HURUF KAPITAL"
        judul = self.doc.judul
        if not judul:
            return self._judul_kosong("1.1.a", desc)
        huruf = [c for c in judul if c.isalpha()]
        if huruf and all(c.isupper() for c in huruf):
            return CheckItem("1.1.a", desc, Status.LULUS, f'Judul: "{judul}"')
        return CheckItem("1.1.a", desc, Status.TIDAK_LULUS,
                         "Panduan 2026: judul 'ditulis menggunakan huruf kapital'. Samakan di isian "
                         f'simbelmawa dan Surat Pernyataan: "{judul.upper()}"')

    def _check_judul_panjang(self) -> CheckItem:
        judul = self.doc.judul
        if not judul:
            return self._judul_kosong("1.1.b", "Judul ≤ 20 kata")
        count = len(judul.split())
        if count <= 20:
            return CheckItem("1.1.b", "Judul ≤ 20 kata", Status.LULUS, f"Judul memiliki {count} kata.")
        return CheckItem("1.1.b", "Judul ≤ 20 kata", Status.TIDAK_LULUS,
                         f"Judul memiliki {count} kata (melebihi batas 20 kata). Kelebihan {count - 20} kata.")

    def _check_judul_akronim(self) -> CheckItem:
        """
        Akronim tidak baku di judul. Karena judul 2026 ditulis kapital semua, akronim
        tidak bisa dikenali dari huruf besarnya. Sebagai gantinya dipakai naskah:
        kata judul yang di naskah SELALU ditulis kapital (mis. 'NIRS', 'ITDRS')
        dianggap akronim. Nama produk sebelum titik dua tidak dicek.
        """
        desc = "Judul tanpa akronim/singkatan tidak baku"
        judul = self.doc.judul
        if not judul:
            return self._judul_kosong("1.1.c", desc)
        nama, isi = _pisah_nama_produk(judul)
        judul_kapital = all(c.isupper() for c in judul if c.isalpha())
        teks = self.doc.full_text
        curiga = []
        for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]*", isi):
            for token in w.split("-"):
                up = token.upper()
                if len(token) < 2 or up in AKRONIM_BAKU or up in curiga:
                    continue
                if judul_kapital:
                    variasi = set(re.findall(rf'\b{re.escape(token)}\b', teks, re.IGNORECASE))
                    is_akronim = bool(variasi) and all(v.isupper() for v in variasi)
                else:
                    is_akronim = token.isupper() and len(token) <= 6
                if is_akronim:
                    curiga.append(up)
        catatan = [f"Nama produk '{nama}' sebelum titik dua tidak dicek."] if nama else []
        if not curiga:
            return CheckItem("1.1.c", desc, Status.LULUS, "Tidak terdeteksi akronim tidak baku.", catatan=catatan)
        return CheckItem("1.1.c", desc, Status.PERINGATAN,
                         f"Kemungkinan akronim tidak baku: {', '.join(curiga[:6])}. Panduan melarang akronim/"
                         "singkatan tidak baku di judul — tulis kepanjangannya.", catatan=catatan)

    def _check_judul_bahasa(self) -> CheckItem:
        desc = "Judul dalam Bahasa Indonesia"
        judul = self.doc.judul
        if not judul:
            return self._judul_kosong("1.1.f", desc)
        _, isi = _pisah_nama_produk(judul)
        inggris = [w for w in re.findall(r"[A-Za-z]+", isi) if w.lower() in KATA_INGGRIS]
        if not inggris:
            return CheckItem("1.1.f", desc, Status.LULUS, "Tidak terdeteksi kata bahasa Inggris.")
        return CheckItem("1.1.f", desc, Status.PERINGATAN,
                         f"Kata bahasa Inggris di judul: {', '.join(dict.fromkeys(inggris))}. Panduan: judul "
                         "'ditulis dalam Bahasa Indonesia' — pakai padanan Indonesia bila ada.")

    # ─── Jenis PKM ───────────────────────────────────────────────────────────

    def _check_jenis_pkm_valid(self) -> CheckItem:
        """Cek apakah jenis PKM (dari input user atau deteksi) termasuk yang valid."""
        jenis = self.doc.jenis_pkm
        if not jenis:
            return CheckItem("1.1.d", "Jenis PKM valid", Status.PERINGATAN,
                             "Jenis PKM tidak terdeteksi. Pilih jenis PKM di form atas.")
        if jenis in JENIS_PKM_VALID:
            return CheckItem("1.1.d", "Jenis PKM valid", Status.LULUS, f"PKM-{jenis}.")
        return CheckItem("1.1.d", "Jenis PKM valid", Status.TIDAK_LULUS,
                         f"Jenis PKM '{jenis}' tidak dikenal. Valid: {', '.join(JENIS_PKM_VALID)}.")

    def _check_jenis_pkm_konsisten(self) -> CheckItem:
        """
        Tahap 1 menilai 'kesesuaian program dengan bidang PKM yang dipilih'.
        Cek kata kunci khas bidang di naskah.
        """
        desc = "Isi sesuai bidang PKM yang dipilih"
        jenis = self.doc.jenis_pkm
        if not jenis or jenis not in STRUKTUR_BAB_PKM:
            return CheckItem("1.1.e", desc, Status.PERINGATAN,
                             "Jenis PKM tidak diketahui, kesesuaian bidang tidak dapat dicek.")

        text_upper = self.doc.full_text.upper()
        keyword_checks = {
            "K": ["RENCANA USAHA", "PELUANG PASAR", "ANALISIS PASAR"],
            "KC": ["PROTOTIPE|PURWARUPA|PROTOTYPE", "TAHAP PELAKSANAAN", "TEKNOLOGI"],
            "PM": ["MITRA", "PEMBERDAYAAN", "MASYARAKAT"],
            "PI": ["MITRA", "PENERAPAN IPTEK|IPTEK", "USAHA"],
            "RE": ["HIPOTESIS", "METODE PENELITIAN", "TINJAUAN PUSTAKA"],
            "RSH": ["TINJAUAN PUSTAKA", "SOSIAL", "METODE PENELITIAN"],
            "KI": ["SKALA PENUH", "TARGET PENGGUNA|PENGGUNA", "TINJAUAN PUSTAKA"],
            "VGK": ["GAGASAN", "SKENARIO KONTEN", "VIDEO"],
            "GFT": ["GAGASAN", "KESIMPULAN"],
            "AI": ["ABSTRAK|ABSTRACT", "PENDAHULUAN", "METODE"],
        }
        expected = keyword_checks.get(jenis, [])
        found = [kw.split("|")[0] for kw in expected if re.search(kw, text_upper)]
        missing = [kw.split("|")[0] for kw in expected if not re.search(kw, text_upper)]

        if jenis == "KI" and "SKALA PENUH" in missing:
            return CheckItem("1.1.e", desc, Status.PERINGATAN,
                             "Proposal PKM-KI tidak menyebut 'skala penuh'. Panduan: luaran utama PKM-KI adalah "
                             "produk fungsional skala penuh (1:1) yang siap dipakai target pengguna, BUKAN "
                             "prototipe. Tegaskan di Bab 1 (luaran) agar tidak dinilai salah bidang.")
        if len(found) >= max(1, len(expected) // 2 + len(expected) % 2):
            return CheckItem("1.1.e", desc, Status.LULUS,
                             f"Konten konsisten dengan PKM-{jenis}. Kata kunci: {', '.join(found)}.")
        return CheckItem("1.1.e", desc, Status.PERINGATAN,
                         f"Konten kurang mencerminkan PKM-{jenis}. Kata kunci tidak ditemukan: "
                         f"{', '.join(missing)}. Tahap 1 menilai kesesuaian program dengan bidang.")

    # ─── Tim & Dosen ─────────────────────────────────────────────────────────

    def _check_jumlah_anggota(self) -> CheckItem:
        """
        Deteksi NIM dari konteks label "NIM" (lebih akurat).
        Mendukung format NIM 7-12 digit (7 digit berawalan tahun 20xx).
        """
        nim_near_label = re.findall(r'(?:NIM|N\.I\.M)[.\s:/]*(\d{7,12})', self.doc.full_text, re.IGNORECASE)
        context_nims = set(nim_near_label)

        all_digit_sequences = re.findall(r'\b(\d{7,12})\b', self.doc.full_text)

        def likely_nim(n: str) -> bool:
            if n.startswith('08') or n.startswith(('628', '62')):
                return False
            if re.match(r'^20[12]\d(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$', n):
                return False
            if len(set(n)) <= 2:
                return False
            if len(n) == 7 and not re.match(r'^2[01234]', n):
                return False
            return True

        fallback_nims = {n for n in all_digit_sequences if likely_nim(n)}
        nims = context_nims if context_nims else fallback_nims
        count = len(nims)
        nim_display = ", ".join(sorted(nims)[:8]) + (f", ... (+{len(nims) - 8} lagi)" if len(nims) > 8 else "")
        source_note = "(dari label NIM)" if context_nims else "(estimasi dari pola angka)"

        desc = "Jumlah anggota tim 3–5 mahasiswa"
        if count == 0:
            return CheckItem("1.2.a", desc, Status.PERINGATAN,
                             "NIM tidak terdeteksi otomatis (biodata berupa scan). Periksa manual jumlah anggota.")
        if 3 <= count <= 5:
            return CheckItem("1.2.a", desc, Status.LULUS, f"Terdeteksi {count} NIM {source_note}: {nim_display}.")
        if count < 3:
            return CheckItem("1.2.a", desc, Status.PERINGATAN,
                             f"Hanya {count} NIM terbaca {source_note}: {nim_display}. Minimal 3 mahasiswa — "
                             "bisa juga karena biodata berupa scan. Periksa manual.")
        return CheckItem("1.2.a", desc, Status.PERINGATAN,
                         f"Terdeteksi {count} NIM {source_note}: {nim_display}. Jika benar > 5, ini melanggar "
                         "ketentuan; jika tidak, kemungkinan false positive.")

    def _check_dosen_nuptk(self) -> CheckItem:
        """
        Panduan 2026: dosen pendamping WAJIB punya NUPTK (16 digit); biodata memakai
        label 'NIP/NUPTK'. NIDN (10 digit) bukan NUPTK.
        """
        desc = "NIP/NUPTK dosen pendamping (NUPTK 16 digit)"
        text = self.doc.full_text

        m = re.search(r'NIP\s*/\s*NUPTK[ \t:]*(\d[\d ./-]{8,45}\d)', text, re.IGNORECASE)
        if m:
            angka = re.findall(r'\d+', m.group(1))
            if any(len(a) == 16 for a in angka):
                return CheckItem("1.3.a", desc, Status.LULUS, f"NIP/NUPTK: {m.group(1).strip()}.")
            if any(len(a) == 10 for a in angka):
                return CheckItem("1.3.a", desc, Status.PERINGATAN,
                                 f"Kolom NIP/NUPTK berisi '{m.group(1).strip()}' — angka 10 digit itu format NIDN, "
                                 "bukan NUPTK (16 digit). Panduan 2026: dosen tanpa NUPTK tidak boleh menjadi "
                                 "pendamping; cantumkan NUPTK yang benar dan samakan dengan halaman tanda tangan.")
            return CheckItem("1.3.a", desc, Status.PERINGATAN,
                             f"NIP/NUPTK terbaca '{m.group(1).strip()}' tetapi tidak ada angka 16 digit (NUPTK). "
                             "Periksa manual.")
        if re.search(r'NIP\s*/\s*NUPTK', text, re.IGNORECASE):
            return CheckItem("1.3.a", desc, Status.PERINGATAN,
                             "Label 'NIP/NUPTK' ditemukan tetapi nilainya tidak terbaca (mungkin scan). Periksa manual.")
        m = re.search(r'NIP\s*/\s*NIDN[ \t:]*(\d[\d ./-]{8,45}\d)', text, re.IGNORECASE)
        if m or re.search(r'NIP\s*/\s*NIDN', text, re.IGNORECASE):
            nilai = f": {m.group(1).strip()}" if m else ""
            return CheckItem("1.3.a", desc, Status.PERINGATAN,
                             f"Biodata dosen memakai label lama 'NIP/NIDN'{nilai}. Template 2026 memakai "
                             "'NIP/NUPTK' — perbarui label dan isi NUPTK.")
        m = re.search(r'\bNUPTK\b[\s:.]*(\d{16})', text)
        if m:
            return CheckItem("1.3.a", desc, Status.PERINGATAN,
                             f"NUPTK {m.group(1)} ditemukan, tetapi tabel biodata dosen tidak memakai label 'NIP/NUPTK'.")
        return CheckItem("1.3.a", desc, Status.PERINGATAN,
                         "NIP/NUPTK dosen tidak terbaca sebagai teks (biodata mungkin scan). Pastikan kolom "
                         "'NIP/NUPTK' terisi NUPTK 16 digit.")
