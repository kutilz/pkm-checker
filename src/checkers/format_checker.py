"""
Modul 2 — Format & Tipografi.
Cek font, spasi, margin, ukuran kertas, dan penomoran halaman.
"""

import re
from collections import Counter
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from config import MARGIN_LEFT_CM, MARGIN_OTHER_CM

PT_TO_CM = 1 / 28.3465
PAGE_NUM_AREA_RATIO = 0.08   # 8% dari tinggi halaman = zona nomor halaman


def _is_tnr(font_name: str) -> bool:
    """
    Cek apakah nama font adalah Times New Roman atau variannya.
    PDF sering menggunakan nama embedded seperti 'ABCDEF+TimesNewRomanPSMT'
    atau 'TimesNewRomanPS-BoldMT', dsb.
    """
    n = font_name.lower().replace(" ", "").replace("-", "").replace("+", "")
    # Hapus prefix hash (ABCDEF+...)
    if '+' in font_name.lower():
        n = font_name.lower().split('+', 1)[-1].replace(" ", "").replace("-", "")
    return (
        "timesnewroman" in n
        or n.startswith("times")
        or "timesroman" in n
        or n == "times"
    )


def _is_page_number_span(span: dict, page_height: float) -> bool:
    """
    Tentukan apakah span ini adalah nomor halaman.
    Ciri: teks pendek (digit/romawi), posisi di zona atas atau bawah halaman.
    """
    text = span.get("text", "").strip()
    bbox = span.get("bbox")
    if not text or not bbox:
        return False
    # Hanya teks yang mengandung digit atau romawi
    if not re.fullmatch(r'[\divxlcmIVXLCM\s.]+', text):
        return False
    # Harus pendek
    if len(text) > 5:
        return False
    # Posisi: zona nomor halaman (atas 8% atau bawah 8%)
    y_center = (bbox[1] + bbox[3]) / 2
    top_zone = page_height * PAGE_NUM_AREA_RATIO
    bottom_zone = page_height * (1 - PAGE_NUM_AREA_RATIO)
    return y_center < top_zone or y_center > bottom_zone


def _extract_page_numbers(page) -> list[str]:
    """
    Ekstrak teks nomor halaman (di zona atas/bawah) dari satu halaman.
    """
    nums = []
    for span in page.font_spans:
        if _is_page_number_span(span, page.height_pt):
            nums.append(span["text"].strip())
    return nums


class FormatChecker(BaseChecker):

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 2: Format & Tipografi", bobot=0.15)
        result.items.extend([
            self._check_font(),
            self._check_ukuran_font(),
            self._check_ukuran_kertas(),
            self._check_margin(),
            self._check_penomoran_halaman(),
        ])
        return result

    def _check_font(self) -> CheckItem:
        """
        Cek apakah mayoritas teks menggunakan Times New Roman.
        Mengabaikan: span kosong, simbol/karakter tunggal, nomor halaman.
        Threshold LULUS: ≥ 95%.
        """
        all_spans = []
        for page in self.doc.pages:
            for span in page.font_spans:
                # Abaikan span kosong, terlalu pendek, atau nomor halaman
                text = span.get("text", "").strip()
                if not text:
                    continue
                if _is_page_number_span(span, page.height_pt):
                    continue
                # Abaikan span yang isinya hanya simbol non-alfanumerik
                if re.fullmatch(r'[^\w\s]+', text):
                    continue
                all_spans.append(span)

        if not all_spans:
            return CheckItem("2.1.a", "Font Times New Roman",
                             Status.PERINGATAN, "Info font tidak tersedia dari PDF.")

        total = len(all_spans)
        tnr_count = sum(1 for s in all_spans if _is_tnr(s["font"]))
        pct = round(tnr_count / total * 100, 1)

        non_tnr = Counter(
            s["font"] for s in all_spans
            if not _is_tnr(s["font"]) and s.get("text", "").strip()
        )
        top_other = non_tnr.most_common(3)

        if pct >= 95:
            return CheckItem("2.1.a", "Font Times New Roman",
                             Status.LULUS,
                             f"{pct}% teks menggunakan Times New Roman. "
                             "(Sisa ≤5% biasanya karakter simbol/rumus yang memang tidak bisa TNR.)")
        elif pct >= 80:
            other_info = ", ".join(f"{f} ({c}x)" for f, c in top_other)
            return CheckItem("2.1.a", "Font Times New Roman",
                             Status.PERINGATAN,
                             f"Hanya {pct}% teks TNR. Font lain ditemukan: {other_info}. "
                             "Seleksi semua teks (Ctrl+A) lalu ubah ke Times New Roman 12.")
        else:
            other_info = ", ".join(f"{f} ({c}x)" for f, c in top_other)
            return CheckItem("2.1.a", "Font Times New Roman",
                             Status.TIDAK_LULUS,
                             f"Hanya {pct}% teks TNR. Font dominan lain: {other_info}. "
                             "Seluruh teks harus Times New Roman.")

    def _check_ukuran_font(self) -> CheckItem:
        """
        Cek apakah mayoritas teks berukuran 12pt.
        Mengabaikan: bold (heading), span simbol, nomor halaman.
        """
        body_spans = []
        for page in self.doc.pages:
            for span in page.font_spans:
                text = span.get("text", "").strip()
                if not text:
                    continue
                if _is_page_number_span(span, page.height_pt):
                    continue
                if re.fullmatch(r'[^\w\s]+', text):
                    continue
                # Abaikan heading bold untuk mengurangi noise
                if span.get("bold") and len(text.split()) <= 8:
                    continue
                body_spans.append(span)

        if not body_spans:
            return CheckItem("2.1.b", "Ukuran font 12pt",
                             Status.PERINGATAN, "Info font tidak tersedia dari PDF.")

        size_counts = Counter(round(s["size"]) for s in body_spans)
        total = sum(size_counts.values())
        size_12_count = size_counts.get(12, 0)
        pct = round(size_12_count / total * 100, 1) if total else 0

        if pct >= 85:
            return CheckItem("2.1.b", "Ukuran font 12pt",
                             Status.LULUS, f"{pct}% teks body berukuran 12pt.")

        other = {k: v for k, v in size_counts.most_common(5) if k != 12}
        return CheckItem("2.1.b", "Ukuran font 12pt",
                         Status.TIDAK_LULUS,
                         f"Hanya {pct}% teks berukuran 12pt. "
                         f"Ukuran lain yang ditemukan: {dict(list(other.items())[:3])}.")

    def _check_ukuran_kertas(self) -> CheckItem:
        """Cek apakah semua halaman berukuran A4 (595.28 × 841.89 pt)."""
        A4_W, A4_H, TOL = 595.28, 841.89, 5
        non_a4 = [
            p.page_number for p in self.doc.pages
            if abs(p.width_pt - A4_W) > TOL or abs(p.height_pt - A4_H) > TOL
        ]
        if not non_a4:
            return CheckItem("2.3.a", "Ukuran kertas A4",
                             Status.LULUS, "Semua halaman berukuran A4.")
        return CheckItem("2.3.a", "Ukuran kertas A4",
                         Status.TIDAK_LULUS,
                         f"Halaman tidak berukuran A4: {non_a4}.")

    def _check_margin(self) -> CheckItem:
        """
        Estimasi margin dari posisi teks, dengan mengabaikan nomor halaman
        (yang posisinya di tepi atas/bawah dan tidak mewakili margin konten).
        Margin kiri: 4 cm, lainnya: 3 cm. Toleransi: ±0.5 cm.
        """
        if not self.doc.pages:
            return CheckItem("2.3.b", "Margin (kiri 4cm, kanan/atas/bawah 3cm)",
                             Status.PERINGATAN, "Tidak ada halaman untuk diperiksa.")

        TOL_PT = 0.5 * 28.3465
        TARGET_LEFT = MARGIN_LEFT_CM * 28.3465
        TARGET_OTHER = MARGIN_OTHER_CM * 28.3465

        issues = []
        # Sampel halaman dari bagian inti (lebih representatif dari front matter)
        sample_pages = (
            [self.doc.pages[i - 1] for i in self.doc.core_pages[:5] if i <= len(self.doc.pages)]
            or self.doc.pages[2:7]
        )

        for page in sample_pages:
            if not page.font_spans:
                continue

            # Kumpulkan bbox HANYA dari konten utama (bukan nomor halaman)
            bboxes = [
                s["bbox"] for s in page.font_spans
                if s["bbox"]
                and s.get("text", "").strip()
                and not _is_page_number_span(s, page.height_pt)
                and not re.fullmatch(r'[^\w\s]+', s.get("text", "").strip())
            ]
            if not bboxes:
                continue

            left_pts = min(b[0] for b in bboxes)
            right_pts = page.width_pt - max(b[2] for b in bboxes)
            # Atas dan bawah: hanya dari konten yang bukan di zona header/footer
            inner_bboxes = [
                b for b in bboxes
                if b[1] > page.height_pt * PAGE_NUM_AREA_RATIO
                and b[3] < page.height_pt * (1 - PAGE_NUM_AREA_RATIO)
            ]
            if not inner_bboxes:
                continue
            top_pts = min(b[1] for b in inner_bboxes)
            bottom_pts = page.height_pt - max(b[3] for b in inner_bboxes)

            # Hanya flag ketika margin TERLALU KECIL dari minimum yang disyaratkan.
            # Margin yang lebih besar dari target TIDAK bermasalah.
            checks = [
                ("kiri", left_pts, TARGET_LEFT, TOL_PT),
                ("kanan", right_pts, TARGET_OTHER, TOL_PT),
                ("atas", top_pts, TARGET_OTHER, TOL_PT),
                ("bawah", bottom_pts, TARGET_OTHER, TOL_PT),
            ]
            target_map = {"kiri": MARGIN_LEFT_CM, "kanan": MARGIN_OTHER_CM,
                          "atas": MARGIN_OTHER_CM, "bawah": MARGIN_OTHER_CM}
            for label, val, target, tol in checks:
                # Hanya masalah jika margin LEBIH KECIL dari target (minus toleransi)
                if val < target - tol:
                    issues.append(
                        f"Hal.{page.page_number}: margin {label} "
                        f"≈{val * PT_TO_CM:.1f}cm (minimum {target_map[label]}cm)"
                    )

        if not issues:
            return CheckItem("2.3.b", "Margin (kiri 4cm, kanan/atas/bawah 3cm)",
                             Status.LULUS, "Margin sesuai ketentuan.")
        if len(issues) <= 2:
            return CheckItem("2.3.b", "Margin (kiri 4cm, kanan/atas/bawah 3cm)",
                             Status.PERINGATAN,
                             "Potensi ketidaksesuaian margin: " + "; ".join(issues[:3]))
        return CheckItem("2.3.b", "Margin (kiri 4cm, kanan/atas/bawah 3cm)",
                         Status.TIDAK_LULUS,
                         "Margin tidak sesuai di banyak halaman: " + "; ".join(issues[:5]))

    def _check_penomoran_halaman(self) -> CheckItem:
        """
        Validasi penomoran halaman per segmen dokumen:
        - Front matter (daftar_isi_pages): harus mengandung romawi kecil (i, ii, iii...)
        - Bagian inti (core_pages): harus mengandung angka arab (1, 2, 3...)
        """
        front_pages = [
            self.doc.pages[i - 1] for i in self.doc.daftar_isi_pages
            if i <= len(self.doc.pages)
        ]
        core_pages = [
            self.doc.pages[i - 1] for i in self.doc.core_pages
            if i <= len(self.doc.pages)
        ]

        issues = []

        # Kumpulkan semua nomor halaman dari masing-masing segmen
        front_nums = []
        for page in front_pages:
            front_nums.extend(_extract_page_numbers(page))

        core_nums = []
        for page in core_pages:
            core_nums.extend(_extract_page_numbers(page))

        # Cek front matter: harus ada romawi kecil
        has_roman_front = any(
            re.fullmatch(r'[ivxlcm]+', n.lower()) for n in front_nums if n
        )
        has_arabic_front = any(re.fullmatch(r'\d+', n) for n in front_nums if n)

        if front_pages:
            if has_roman_front:
                pass  # OK
            elif has_arabic_front:
                issues.append(
                    "Bagian Daftar Isi menggunakan nomor arab — seharusnya romawi kecil (i, ii, iii)."
                )
            else:
                issues.append(
                    "Nomor halaman romawi kecil (i, ii, iii) tidak terdeteksi di bagian Daftar Isi. "
                    "Periksa manual."
                )

        # Cek bagian inti: harus ada angka arab
        has_arabic_core = any(re.fullmatch(r'\d+', n) for n in core_nums if n)
        has_roman_core = any(
            re.fullmatch(r'[ivxlcm]+', n.lower()) for n in core_nums if n
        )

        if core_pages:
            if has_arabic_core:
                pass  # OK
            elif has_roman_core:
                issues.append(
                    "Bagian inti (Bab 1 dst) menggunakan nomor romawi — seharusnya angka arab (1, 2, 3)."
                )
            else:
                issues.append(
                    "Nomor halaman arab (1, 2, 3) tidak terdeteksi di bagian inti. "
                    "Periksa manual."
                )

        if not front_pages and not core_pages:
            return CheckItem("2.4", "Penomoran halaman (romawi kecil + arab)",
                             Status.PERINGATAN,
                             "Segmentasi dokumen gagal — tidak bisa memvalidasi penomoran halaman.")

        if not issues:
            roman_info = f"romawi di {len(front_pages)} hal. front matter" if front_pages and has_roman_front else ""
            arabic_info = f"arab di {len(core_pages)} hal. inti" if core_pages and has_arabic_core else ""
            detail = " | ".join(filter(None, [roman_info, arabic_info])) or "Terdeteksi sesuai."
            return CheckItem("2.4", "Penomoran halaman (romawi kecil + arab)",
                             Status.LULUS, detail)

        return CheckItem("2.4", "Penomoran halaman (romawi kecil + arab)",
                         Status.TIDAK_LULUS,
                         " ".join(issues))
