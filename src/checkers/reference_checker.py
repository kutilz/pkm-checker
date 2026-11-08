"""
Modul 4 — Daftar Pustaka & Sitasi.

Dipisah dari Modul Struktur dan dibuat ketat karena kesalahan Daftar Pustaka
(walau hanya satu titik) termasuk penyebab paling sering proposal tidak lolos.
Acuan: Lampiran "Format Penyusunan Rujukan dan Daftar Pustaka" Panduan PKM 2026.
"""

import re
from collections import Counter
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from .dafpus_utils import (
    build_entries, build_entries_from_text, entry_issues, extract_citations,
    citation_matches, norm,
)
from config import DAFPUS_FORMAT

MAX_CATATAN = 12


class ReferenceChecker(BaseChecker):

    def __init__(self, doc, use_gemini: bool = False):
        super().__init__(doc)
        self.use_gemini = use_gemini
        if doc.dafpus_lines:
            self.entries, self.hanging = build_entries(doc.dafpus_lines)
        else:
            self.entries, self.hanging = build_entries_from_text(doc.dafpus_text or ""), None
        self.citations, self.no_comma = extract_citations(doc.core_text_blocks) if doc.core_pages else ([], [])

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 4: Daftar Pustaka & Sitasi", bobot=0.20)
        if not self.entries:
            result.items.append(CheckItem(
                "4.1", "Daftar Pustaka ada dan terbaca", Status.TIDAK_LULUS,
                "Daftar Pustaka tidak ditemukan atau tidak terbaca sebagai teks. "
                "Pastikan heading 'DAFTAR PUSTAKA' ada sesudah BAB 4 dan PDF bukan hasil scan."))
            return result

        result.items.extend([
            CheckItem("4.1", "Daftar Pustaka ada dan terbaca", Status.LULUS,
                      f"{len(self.entries)} entri terbaca."),
            self._check_hanging_indent(),
            self._check_format_berat(),
            self._check_format_ringan(),
            self._check_alfabetis(),
            self._check_konsistensi_gaya(),
            self._check_sitasi_vs_dafpus(),
            self._check_format_sitasi(),
        ])
        if self.use_gemini:
            result.items.append(self._check_sitasi_gemini())
        return result

    # ─── Daftar Pustaka ──────────────────────────────────────────────────────

    def _check_hanging_indent(self) -> CheckItem:
        desc = "Hanging indent (baris ke-2 dst. tiap entri menjorok)"
        if self.hanging is True:
            return CheckItem("4.2", desc, Status.LULUS, "Hanging indent terdeteksi.")
        if self.hanging is False:
            return CheckItem("4.2", desc, Status.TIDAK_LULUS,
                             "Baris lanjutan entri tidak menjorok ke dalam. Panduan: 'baris kedua dan "
                             "setelahnya menjorok ke dalam' (Word: Paragraph → Special → Hanging).")
        return CheckItem("4.2", desc, Status.PERINGATAN,
                         "Indentasi tidak dapat dipastikan (entri satu baris semua / PDF tanpa info posisi). "
                         "Cek manual.")

    def _collect(self, tingkat: str) -> list[str]:
        catatan = []
        for i, e in enumerate(self.entries, 1):
            msgs = [m for lvl, m in entry_issues(e, DAFPUS_FORMAT) if lvl == tingkat]
            if msgs:
                catatan.append(f"Entri {i} — {e.label}: " + "; ".join(msgs))
        return catatan

    def _check_format_berat(self) -> CheckItem:
        desc = "Format entri Harvard (tahun dalam kurung, tanpa et al./dkk, diakhiri titik, tanggal akses URL)"
        catatan = self._collect("berat")
        if not catatan:
            return CheckItem("4.3", desc, Status.LULUS,
                             f"Semua {len(self.entries)} entri memenuhi aturan pokok format Harvard.")
        return CheckItem(
            "4.3", desc, Status.TIDAK_LULUS,
            f"{len(catatan)} dari {len(self.entries)} entri melanggar aturan pokok. Kesalahan Daftar Pustaka — "
            "walau hanya titik — sering menjadi penyebab proposal tidak lolos.",
            catatan=catatan[:MAX_CATATAN] + ([f"... dan {len(catatan) - MAX_CATATAN} entri lain"]
                                             if len(catatan) > MAX_CATATAN else []))

    def _check_format_ringan(self) -> CheckItem:
        desc = "Detail tanda baca & gaya entri (kutip judul, nomor halaman, inisial, italic, spasi)"
        catatan = self._collect("ringan")
        if not catatan:
            return CheckItem("4.4", desc, Status.LULUS, "Tidak ditemukan masalah tanda baca/gaya.")
        return CheckItem(
            "4.4", desc, Status.PERINGATAN,
            f"{len(catatan)} entri perlu dirapikan. Samakan dengan contoh di lampiran panduan "
            "(mis. Tovey, H. (2002) 'Judul', Nama Jurnal, 11(1), pp. 23-42.).",
            catatan=catatan[:MAX_CATATAN] + ([f"... dan {len(catatan) - MAX_CATATAN} entri lain"]
                                             if len(catatan) > MAX_CATATAN else []))

    def _check_alfabetis(self) -> CheckItem:
        desc = "Daftar Pustaka urut alfabetis (nama belakang penulis pertama)"
        if len(self.entries) < 2:
            return CheckItem("4.5", desc, Status.PERINGATAN, "Entri terlalu sedikit untuk dicek.")

        def key(e):
            return re.sub(r'[^a-z0-9 ]', '', norm(e.penulis or e.teks)).strip()

        salah = []
        for a, b in zip(self.entries, self.entries[1:]):
            if key(a) > key(b):
                salah.append(f"'{a.label}' sebelum '{b.label}'")
        if not salah:
            return CheckItem("4.5", desc, Status.LULUS, f"{len(self.entries)} entri terurut alfabetis.")
        return CheckItem("4.5", desc, Status.TIDAK_LULUS,
                         f"{len(salah)} pasangan entri tidak urut.", catatan=salah[:8])

    def _check_konsistensi_gaya(self) -> CheckItem:
        desc = "Konsistensi gaya antarentri (penghubung penulis, sufiks a/b tahun sama)"
        catatan = []
        penghubung = Counter()
        for e in self.entries:
            for word in re.findall(r'\s(and|dan|&)\s', e.penulis):
                penghubung[word] += 1
        if len(penghubung) > 1:
            catatan.append("Penghubung penulis terakhir bercampur: "
                           + ", ".join(f"'{k}' ({v}x)" for k, v in penghubung.items())
                           + ". Pilih satu (contoh panduan memakai 'and').")
        seen = Counter((norm(e.penulis), e.tahun) for e in self.entries if e.tahun)
        for (pen, th), n in seen.items():
            if n > 1 and not re.search(r'[a-z]$', th):
                catatan.append(f"Penulis & tahun sama muncul {n}x ({pen[:30]} {th}) — beri sufiks 2020a, 2020b.")
        if not catatan:
            return CheckItem("4.6", desc, Status.LULUS, "Gaya antarentri konsisten.")
        return CheckItem("4.6", desc, Status.PERINGATAN, "Gaya antarentri belum konsisten.", catatan=catatan)

    # ─── Sitasi ──────────────────────────────────────────────────────────────

    def _check_sitasi_vs_dafpus(self) -> CheckItem:
        desc = "Setiap sitasi ada di Daftar Pustaka dan sebaliknya"
        if not self.citations:
            return CheckItem("4.7", desc, Status.PERINGATAN,
                             "Sitasi (Nama, Tahun) tidak terdeteksi di naskah. Panduan mewajibkan "
                             "perujukan gaya Harvard (nama belakang, tahun).")
        tidak_ada = []
        for s in self.citations:
            if not any(citation_matches(s, e) for e in self.entries):
                if s.teks not in tidak_ada:
                    tidak_ada.append(s.teks)
        tidak_disitasi = [e.label for e in self.entries
                          if not any(citation_matches(s, e) for s in self.citations)]
        if not tidak_ada and not tidak_disitasi:
            return CheckItem("4.7", desc, Status.LULUS,
                             f"{len(self.citations)} sitasi cocok dengan {len(self.entries)} entri pustaka.")
        catatan = ([f"Disitasi tapi tidak ada di Daftar Pustaka (atau nama/tahun beda): {t}" for t in tidak_ada[:8]]
                   + [f"Ada di Daftar Pustaka tapi tidak disitasi di naskah: {t}" for t in tidak_disitasi[:8]])
        return CheckItem(
            "4.7", desc, Status.TIDAK_LULUS,
            f"{len(tidak_ada)} sitasi tanpa pasangan, {len(tidak_disitasi)} entri tidak disitasi. "
            "Panduan: setiap pustaka yang dirujuk harus muncul di Daftar Pustaka, dan sebaliknya. "
            "(Deteksi otomatis — pastikan ejaan nama & tahun identik.)",
            catatan=catatan)

    def _check_format_sitasi(self) -> CheckItem:
        desc = "Format sitasi dalam naskah (Nama, Tahun)"
        text = re.sub(r'\s+', ' ', self.doc.core_text_blocks or "")
        berat, ringan = [], []
        if self.no_comma:
            berat.append("Sitasi berkurung tanpa koma sebelum tahun: " + ", ".join(dict.fromkeys(self.no_comma[:6]))
                         + " → tulis '(Nama et al., 2020)'.")
        subjek = re.findall(
            r'\b(?:oleh|menurut|studi|penelitian|kajian|riset)\s+(\([A-Z][^()]{1,80}?(?:19|20)\d{2}[a-z]?\))',
            text, re.IGNORECASE)
        if subjek:
            ringan.append("Sitasi berkurung dipakai sebagai subjek kalimat: " + ", ".join(subjek[:4])
                          + " → pakai sitasi naratif, mis. 'Joko et al. (2020) menunjukkan ...'.")
        pakai_etal = re.search(r'\bet\s+al\b', text)
        pakai_dkk = re.search(r'\bdkk\b', text)
        if pakai_etal and pakai_dkk:
            ringan.append("Sitasi mencampur 'et al.' dan 'dkk.' — pilih salah satu.")
        if berat:
            return CheckItem("4.8", desc, Status.TIDAK_LULUS, "Format sitasi tidak konsisten.",
                             catatan=berat + ringan)
        if ringan:
            return CheckItem("4.8", desc, Status.PERINGATAN, "Format sitasi perlu dirapikan.", catatan=ringan)
        return CheckItem("4.8", desc, Status.LULUS, f"{len(self.citations)} sitasi berformat konsisten.")

    def _check_sitasi_gemini(self) -> CheckItem:
        from src.ai.gemini_client import check_citation_consistency
        sitasi = list(dict.fromkeys(s.teks for s in self.citations))
        if not sitasi:
            return CheckItem("4.G", "Konsistensi sitasi ↔ daftar pustaka (Gemini)", Status.PERINGATAN,
                             "Sitasi tidak terdeteksi untuk analisis Gemini.")
        try:
            hasil = check_citation_consistency(sitasi[:40], [e.teks for e in self.entries][:40])
        except Exception as e:  # noqa: BLE001 — layanan eksternal, cukup diberi peringatan
            return CheckItem("4.G", "Konsistensi sitasi ↔ daftar pustaka (Gemini)", Status.PERINGATAN,
                             f"Gemini API error: {e}. Cek manual konsistensi sitasi.")
        catatan = ([f"Sitasi tidak ada di dafpus: {x}" for x in hasil.get("tidak_ada_di_dafpus", [])[:5]]
                   + [f"Dafpus tidak disitasi: {x}" for x in hasil.get("tidak_disitasi", [])[:5]]
                   + [f"Inkonsistensi: {x}" for x in hasil.get("inkonsistensi", [])[:5]])
        if not catatan:
            return CheckItem("4.G", "Konsistensi sitasi ↔ daftar pustaka (Gemini)", Status.LULUS,
                             "Gemini tidak menemukan ketidaksesuaian.")
        return CheckItem("4.G", "Konsistensi sitasi ↔ daftar pustaka (Gemini)", Status.PERINGATAN,
                         "Temuan Gemini (verifikasi manual):", catatan=catatan)
