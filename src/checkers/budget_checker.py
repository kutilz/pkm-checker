"""
Modul 5 — Anggaran & Keuangan.
Validasi RAB: rentang dana, komposisi, batas kategori, item terlarang, dan aritmatika.
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from config import (
    DANA_BELMAWA_MIN, DANA_BELMAWA_MAX, DANA_PT_MAX, DANA_INSTANSI_MAX,
    OPERASIONAL_MIN_PCT, ADMINISTRASI_MAX_PCT,
    BAHAN_HABIS_MAX_PCT, SEWA_JASA_MAX_PCT, TRANSPORTASI_MAX_PCT,
    LAIN_LAIN_MAX_PCT, ADS_MEDSOS_MAX, ITEM_MAX_PRICE, KUOTA_INTERNET_MAX_PER_BULAN,
    ITEM_TERLARANG_RAB,
)


def _parse_rupiah(text: str) -> int:
    """
    Konversi string angka format Indonesia ke integer.
    Format Indonesia: titik = pemisah ribuan, koma = pemisah desimal
    Contoh: '1.000.000,00' → 1_000_000  |  '8.000.000' → 8_000_000
    """
    clean = re.sub(r'[Rp\s]', '', text)
    # Hapus bagian desimal (setelah koma terakhir) — koma = desimal di Indonesia
    if ',' in clean:
        clean = clean[:clean.rindex(',')]
    # Hapus titik (pemisah ribuan)
    clean = clean.replace('.', '')
    try:
        return int(clean)
    except ValueError:
        return 0


class BudgetChecker(BaseChecker):

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 5: Anggaran & Keuangan", bobot=0.15)

        # Coba ekstrak tabel RAB dari halaman yang berisi kata anggaran/RAB
        rab_tables, rab_text = self._extract_rab_data()

        result.items.extend([
            self._check_rentang_dana(rab_text),
            self._check_item_terlarang(rab_text),
            self._check_kuota_internet(rab_text),
            self._check_sewa_lisensi(rab_text),
            self._check_harga_item(rab_tables),
        ])
        return result

    def _extract_rab_data(self):
        """
        Kumpulkan teks dan tabel dari halaman yang benar-benar berisi RAB/anggaran.

        Strategi spesifik (menghindari false positive dari halaman lain):
        1. Halaman dengan 'Justifikasi Anggaran' (Lampiran 2 — detail RAB)
        2. Halaman dengan 'Rekap Sumber Dana' atau 'Besaran Dana' (tabel BAB 4)
        3. Halaman dengan 'GRAND TOTAL' (baris penutup RAB)
        """
        rab_keywords = re.compile(
            r'(?:justifikasi\s+anggaran'
            r'|rekap\s+sumber\s+dana'
            r'|besaran\s+dana'
            r'|sumber\s+dana.*besaran'
            r'|grand\s+total)',
            re.IGNORECASE
        )
        rab_pages = [p for p in self.doc.pages if rab_keywords.search(p.text)]

        tables = []
        text = ""
        for page in rab_pages:
            tables.extend(page.tables)
            text += page.text + "\n"

        return tables, text

    def _check_rentang_dana(self, rab_text: str) -> CheckItem:
        """
        Cari total dana Belmawa dari bagian Rekap Sumber Dana di teks RAB.
        Prioritas pencarian:
        1. Baris 'Rekap Sumber Dana ... Belmawa <angka>' (tabel rekapitulasi)
        2. 'GRAND TOTAL <angka>' (total keseluruhan = Belmawa + PT + Instansi lain)
        3. Pola 'Belmawa <angka>' generik sebagai fallback
        """
        def _format_result(nilai: int, label: str) -> CheckItem:
            if DANA_BELMAWA_MIN <= nilai <= DANA_BELMAWA_MAX:
                return CheckItem("6.1", "Dana Belmawa dalam rentang Rp6–8 juta",
                                 Status.LULUS,
                                 f"Total dana Belmawa: Rp{nilai:,} ({label}).")
            elif nilai < DANA_BELMAWA_MIN:
                return CheckItem("6.1", "Dana Belmawa dalam rentang Rp6–8 juta",
                                 Status.TIDAK_LULUS,
                                 f"Dana Rp{nilai:,} kurang dari minimum Rp{DANA_BELMAWA_MIN:,}.")
            return CheckItem("6.1", "Dana Belmawa dalam rentang Rp6–8 juta",
                             Status.TIDAK_LULUS,
                             f"Dana Rp{nilai:,} melebihi maksimum Rp{DANA_BELMAWA_MAX:,}.")

        # 1. Cari "Rekap Sumber Dana" (baris khusus rekapitulasi sumber dana)
        #    Tabel PKM biasanya berisi: "Rekap Sumber Dana | Belmawa | 8.000.000,00"
        #    BERBEDA dari "Rekapitulasi RAB" yang memuat sub-total per kategori.
        rekap_m = re.search(r'rekap\s+sumber\s+dana(.*?)(?:instansi\s+lain|jumlah\s*\d|$)',
                            rab_text, re.IGNORECASE | re.DOTALL)
        if rekap_m:
            belmawa_m = re.search(r'belmawa[^\d]*([\d.]+(?:,\d+)?)',
                                  rekap_m.group(1), re.IGNORECASE)
            if belmawa_m:
                nilai = _parse_rupiah(belmawa_m.group(1))
                if nilai >= 1_000_000:
                    return _format_result(nilai, "dari Rekap Sumber Dana")

        # 2. GRAND TOTAL (total keseluruhan dalam RAB Lampiran)
        grand_m = re.search(r'grand\s+total[^\d]*([\d.]+(?:,\d+)?)', rab_text, re.IGNORECASE)
        if grand_m:
            nilai = _parse_rupiah(grand_m.group(1))
            if nilai >= 1_000_000:
                return _format_result(nilai, "dari Grand Total RAB")

        return CheckItem("6.1", "Dana Belmawa dalam rentang Rp6–8 juta",
                         Status.PERINGATAN,
                         "Total dana tidak terbaca otomatis. Periksa manual total RAB.")

    def _check_item_terlarang(self, rab_text: str) -> CheckItem:
        """Cek keberadaan item yang dilarang dalam RAB."""
        text_lower = rab_text.lower()
        found = [item for item in ITEM_TERLARANG_RAB if item.lower() in text_lower]

        if not found:
            return CheckItem("6.4", "Tidak ada item terlarang dalam RAB",
                             Status.LULUS, "Tidak terdeteksi item terlarang.")
        return CheckItem("6.4", "Tidak ada item terlarang dalam RAB",
                         Status.TIDAK_LULUS,
                         f"Terdeteksi item terlarang: {', '.join(found[:5])}.")

    def _check_kuota_internet(self, rab_text: str) -> CheckItem:
        """Kuota internet maksimum Rp100.000/bulan/tim."""
        pattern = re.compile(
            r'kuota\s+internet[^\d]*([\d.,]+)', re.IGNORECASE
        )
        matches = pattern.findall(rab_text)
        violations = []
        for m in matches:
            nilai = _parse_rupiah(m)
            if nilai > KUOTA_INTERNET_MAX_PER_BULAN:
                violations.append(f"Rp{nilai:,}")

        if violations:
            return CheckItem("6.4.e", "Kuota internet ≤ Rp100.000/bulan",
                             Status.TIDAK_LULUS,
                             f"Kuota internet melebihi batas: {', '.join(violations)}.")
        if matches:
            return CheckItem("6.4.e", "Kuota internet ≤ Rp100.000/bulan",
                             Status.LULUS, "Kuota internet dalam batas yang diizinkan.")
        return CheckItem("6.4.e", "Kuota internet ≤ Rp100.000/bulan",
                         Status.LULUS, "Tidak ada item kuota internet dalam RAB.")

    def _check_sewa_lisensi(self, rab_text: str) -> CheckItem:
        """Sewa lisensi software maksimum 6 bulan."""
        pattern = re.compile(
            r'(?:sewa|lisensi)[^\d]*(\d+)\s*bulan', re.IGNORECASE
        )
        matches = pattern.findall(rab_text)
        violations = [m for m in matches if int(m) > 6]

        if violations:
            return CheckItem("6.4.f", "Sewa lisensi ≤ 6 bulan",
                             Status.TIDAK_LULUS,
                             f"Sewa lisensi melebihi 6 bulan: {', '.join(violations)} bulan.")
        return CheckItem("6.4.f", "Sewa lisensi ≤ 6 bulan",
                         Status.LULUS, "Tidak ada pelanggaran sewa lisensi.")

    def _check_harga_item(self, tables: list) -> CheckItem:
        """
        Cek apakah ada item dengan harga SATUAN > Rp1.000.000.
        Hanya memeriksa kolom Harga Satuan — bukan SUB TOTAL / GRAND TOTAL / Total.

        Strategi:
        - Identifikasi kolom "Harga Satuan" dari header tabel (kolom ke-3 atau yg mengandung "harga")
        - Skip baris yang mengandung kata kunci agregat (SUB TOTAL, GRAND TOTAL, Jumlah, dll.)
        """
        # Kata kunci baris agregat yang TIDAK mewakili harga satuan item
        SKIP_ROW_KEYWORDS = re.compile(
            r'\b(sub\s+total|grand\s+total|jumlah|rekap|total|terbilang)\b',
            re.IGNORECASE
        )
        violations = []
        violation_items = []

        for table in tables:
            if not table or len(table) < 2:
                continue

            # Deteksi indeks kolom Harga Satuan dari baris header
            header_row = next((r for r in table if r and any(c for c in r if c)), None)
            harga_col_idx = None
            if header_row:
                for ci, cell in enumerate(header_row):
                    if cell and re.search(r'harga\s*satuan', str(cell), re.IGNORECASE):
                        harga_col_idx = ci
                        break

            for row in table:
                if not row:
                    continue
                row_text = ' '.join(str(c) for c in row if c)
                # Skip baris agregat (subtotal, grand total, dll.)
                if SKIP_ROW_KEYWORDS.search(row_text):
                    continue
                # Skip header
                if re.search(r'harga\s*satuan|jenis\s+pengeluaran', row_text, re.IGNORECASE):
                    continue

                # Cek kolom Harga Satuan secara spesifik (jika terdeteksi)
                # Hanya cek jika tabel punya kolom Harga Satuan yang teridentifikasi
                if harga_col_idx is not None:
                    cell = row[harga_col_idx] if harga_col_idx < len(row) else None
                    if cell:
                        nilai = _parse_rupiah(str(cell))
                        if ITEM_MAX_PRICE < nilai < 50_000_000:
                            item_name = str(row[1]) if len(row) > 1 and row[1] else "?"
                            violations.append(f"Rp{nilai:,}")
                            violation_items.append(f"{item_name[:30]} (Rp{nilai:,})")

                if len(violations) >= 5:
                    break

        if violations:
            return CheckItem(
                "6.4.c", "Pembelian item ≤ Rp1.000.000 per item",
                Status.PERINGATAN,
                f"Terdeteksi {len(violations)} item dengan harga satuan >Rp1.000.000: "
                f"{', '.join(violation_items[:3])}. Verifikasi apakah sesuai ketentuan."
            )
        return CheckItem("6.4.c", "Pembelian item ≤ Rp1.000.000 per item",
                         Status.LULUS, "Tidak terdeteksi harga satuan melebihi Rp1.000.000.")
