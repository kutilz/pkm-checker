"""
Modul 5 — Anggaran & Keuangan.
Validasi Tabel 4.1 Rekapitulasi RAB dan Lampiran 2 Justifikasi Anggaran:
sumber dana, komposisi per kategori, item terlarang/berbatas, dan aritmetika.

Catatan analisis proposal 2025–2026:
- "GRAND TOTAL" justifikasi = Belmawa + Perguruan Tinggi (+ instansi lain), bukan
  dana Belmawa saja. Versi lama membaca Grand Total sebagai dana Belmawa sehingga
  proposal yang didanai (Rp9,5 juta = Rp8 juta Belmawa + Rp1,5 juta PT) ikut gagal.
- Kedua proposal gagal di sampel sama-sama melewati batas "sewa & jasa 15%",
  sedangkan proposal yang didanai tidak.
"""

import re
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from .rab_utils import (
    KATEGORI, KATEGORI_LABEL, extract_rekap_text, parse_rekap, extract_justifikasi_text,
    parse_justifikasi, terbilang, terbilang_cocok,
)
from config import (
    DANA_BELMAWA_MIN, DANA_BELMAWA_MAX, DANA_PT_MAX, DANA_INSTANSI_MAX,
    BAHAN_HABIS_MAX_PCT, SEWA_JASA_MAX_PCT, TRANSPORTASI_MAX_PCT, LAIN_LAIN_MAX_PCT,
    ADS_MEDSOS_MAX, ITEM_MAX_PRICE, KUOTA_INTERNET_MAX_PER_BULAN, LISENSI_MAX_BULAN,
    KERTAS_MAX_RIM, ITEM_TERLARANG_RAB,
)

BATAS_KATEGORI = {
    "bahan": BAHAN_HABIS_MAX_PCT,
    "sewa": SEWA_JASA_MAX_PCT,
    "transport": TRANSPORTASI_MAX_PCT,
    "lain": LAIN_LAIN_MAX_PCT,
}


def rp(n) -> str:
    return "Rp" + f"{int(n):,}".replace(",", ".") if n is not None else "?"


class BudgetChecker(BaseChecker):

    def __init__(self, doc):
        super().__init__(doc)
        self.rekap = parse_rekap(extract_rekap_text(doc.core_text if doc.core_pages else doc.full_text))
        self.just = parse_justifikasi(extract_justifikasi_text(doc.lampiran_text or doc.full_text))

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 5: Anggaran & Keuangan", bobot=0.15)
        result.items.extend([
            self._check_dana_belmawa(),
            self._check_dana_pendamping(),
            self._check_komposisi(),
            self._check_item_terlarang(),
            self._check_harga_item(),
            self._check_batas_khusus(),
            self._check_medsos(),
            self._check_aritmetika(),
            self._check_rekap_vs_justifikasi(),
        ])
        return result

    # ─── Sumber dana ─────────────────────────────────────────────────────────

    def _check_dana_belmawa(self) -> CheckItem:
        desc = "Dana Belmawa Rp6–8 juta (dari Rekap Sumber Dana)"
        belmawa = self.rekap.belmawa
        if not belmawa:
            return CheckItem("6.1", desc, Status.PERINGATAN,
                             "Tabel 4.1 Rekapitulasi RAB tidak terbaca otomatis. Pastikan baris "
                             "'Rekap Sumber Dana — Belmawa' ada dan berupa teks (bukan gambar).")
        sumber = "Rekap Sumber Dana" if self.rekap.sumber.get("belmawa") else "jumlah baris Belmawa per kategori"
        if DANA_BELMAWA_MIN <= belmawa <= DANA_BELMAWA_MAX:
            return CheckItem("6.1", desc, Status.LULUS, f"Dana Belmawa {rp(belmawa)} ({sumber}).")
        arah = "kurang dari minimum" if belmawa < DANA_BELMAWA_MIN else "melebihi maksimum"
        return CheckItem("6.1", desc, Status.TIDAK_LULUS,
                         f"Dana Belmawa {rp(belmawa)} {arah} (Rp6.000.000–Rp8.000.000) — dari {sumber}.")

    def _check_dana_pendamping(self) -> CheckItem:
        desc = "Dana pendamping PT wajib ada (≤ Rp2 juta); instansi lain ≤ Rp1 juta"
        if not self.rekap.kategori and not self.rekap.sumber:
            return CheckItem("6.2", desc, Status.PERINGATAN, "Tabel rekap tidak terbaca, cek manual.")
        pt = self.rekap.total_sumber("pt")
        lain = self.rekap.total_sumber("lain")
        masalah = []
        status = Status.LULUS
        if pt > DANA_PT_MAX:
            masalah.append(f"dana Perguruan Tinggi {rp(pt)} melebihi {rp(DANA_PT_MAX)}")
            status = Status.TIDAK_LULUS
        if lain > DANA_INSTANSI_MAX:
            masalah.append(f"dana instansi lain {rp(lain)} melebihi {rp(DANA_INSTANSI_MAX)}")
            status = Status.TIDAK_LULUS
        if pt == 0:
            masalah.append("dana pendamping Perguruan Tinggi tidak tercantum (panduan: wajib ada)")
            status = Status.TIDAK_LULUS if status == Status.TIDAK_LULUS else Status.PERINGATAN
        if not masalah:
            return CheckItem("6.2", desc, Status.LULUS,
                             f"Perguruan Tinggi {rp(pt)}; instansi lain {rp(lain) if lain else '-'}.")
        return CheckItem("6.2", desc, status, "; ".join(masalah).capitalize() + ".")

    def _check_komposisi(self) -> CheckItem:
        desc = "Komposisi RAB: bahan ≤60%, sewa/jasa ≤15%, transport ≤30%, lain-lain ≤15%"
        kat = self.rekap.kategori
        belmawa = self.rekap.belmawa
        if len(kat) < 4 or not belmawa:
            return CheckItem("6.3", desc, Status.PERINGATAN,
                             "Rincian 4 jenis pengeluaran di Tabel 4.1 tidak terbaca lengkap. Cek manual.")
        total_all = sum(sum(v or 0 for v in k.values()) for k in kat.values()) or 1
        berat, ringan, info = [], [], []
        for key in KATEGORI:
            k = kat.get(key, {})
            batas = BATAS_KATEGORI[key]
            pct_b = (k.get("belmawa") or 0) / belmawa
            pct_t = sum(v or 0 for v in k.values()) / total_all
            label = KATEGORI_LABEL[key]
            info.append(f"{label}: {pct_b:.1%} dana Belmawa / {pct_t:.1%} total")
            if pct_b > batas + 0.0005 and pct_t > batas + 0.0005:
                berat.append(f"{label} {pct_b:.1%} dari dana Belmawa dan {pct_t:.1%} dari total — "
                             f"melewati batas {batas:.0%}")
            elif pct_b > batas + 0.0005:
                ringan.append(f"{label} {pct_b:.1%} dari dana Belmawa (batas {batas:.0%}); "
                              f"terhadap total dana {pct_t:.1%}")
        if berat:
            return CheckItem("6.3", desc, Status.TIDAK_LULUS,
                             "Batas persentase dilanggar baik dihitung dari dana Belmawa maupun total dana.",
                             catatan=berat + ringan)
        if ringan:
            return CheckItem("6.3", desc, Status.PERINGATAN,
                             "Panduan menghitung batas dari 'jumlah dana yang diusulkan Belmawa'. "
                             "Turunkan porsi Belmawa kategori ini atau pindahkan ke dana PT.",
                             catatan=ringan)
        return CheckItem("6.3", desc, Status.LULUS, "; ".join(info) + ".")

    # ─── Item RAB ────────────────────────────────────────────────────────────

    def _rows_text(self) -> str:
        return "\n".join(b.teks for b in self.just.baris)

    def _check_item_terlarang(self) -> CheckItem:
        desc = "Tidak ada item terlarang di RAB"
        teks = extract_justifikasi_text(self.doc.lampiran_text or "") or self._rows_text()
        if not teks:
            return CheckItem("6.4", desc, Status.PERINGATAN, "Lampiran Justifikasi Anggaran tidak terbaca.")
        found = []
        for label, pat in ITEM_TERLARANG_RAB:
            m = re.search(pat, teks, re.IGNORECASE)
            if m:
                found.append(f"{label} (\"{m.group(0).strip()}\")")
        if not found:
            return CheckItem("6.4", desc, Status.LULUS, "Tidak terdeteksi item terlarang.")
        return CheckItem("6.4", desc, Status.TIDAK_LULUS,
                         "Item berikut tidak diperkenankan di RAB PKM 2026:", catatan=found)

    def _check_harga_item(self) -> CheckItem:
        desc = f"Harga satuan alat/bahan ≤ {rp(ITEM_MAX_PRICE)} per item"
        if not self.just.baris:
            return CheckItem("6.4.c", desc, Status.PERINGATAN, "Baris justifikasi anggaran tidak terbaca.")
        lebih = [f"{b.nama} — {rp(b.harga)}" for b in self.just.baris
                 if b.harga and b.harga > ITEM_MAX_PRICE and b.kategori in (None, "bahan")]
        if not lebih:
            return CheckItem("6.4.c", desc, Status.LULUS,
                             f"{len(self.just.baris)} baris dicek; tidak ada harga satuan > {rp(ITEM_MAX_PRICE)}.")
        return CheckItem("6.4.c", desc, Status.TIDAK_LULUS,
                         "Pembelian alat/bahan > Rp1.000.000 per item tidak diperkenankan.", catatan=lebih)

    def _check_batas_khusus(self) -> CheckItem:
        desc = "Batas item khusus: kuota ≤Rp100rb/bulan, lisensi ≤6 bulan, kertas ≤2 rim"
        masalah = []
        for b in self.just.baris:
            t = b.teks.lower()
            if "kuota" in t and b.harga and b.harga > KUOTA_INTERNET_MAX_PER_BULAN:
                masalah.append(f"{b.nama}: {rp(b.harga)}/bulan (maks {rp(KUOTA_INTERNET_MAX_PER_BULAN)})")
            if re.search(r'lisensi|license|langganan|premium|subscription|sewa\s+software', t) \
                    and b.volume > LISENSI_MAX_BULAN:
                masalah.append(f"{b.nama}: {b.volume:g} bulan (maks {LISENSI_MAX_BULAN} bulan)")
            if re.search(r'\bkertas\b|\bhvs\b', t) and b.volume > KERTAS_MAX_RIM:
                masalah.append(f"{b.nama}: {b.volume:g} rim (maks {KERTAS_MAX_RIM} rim)")
        if masalah:
            return CheckItem("6.4.e", desc, Status.TIDAK_LULUS, "Melewati batas panduan.", catatan=masalah)
        return CheckItem("6.4.e", desc, Status.LULUS, "Tidak ada pelanggaran batas item khusus.")

    def _check_medsos(self) -> CheckItem:
        desc = "Alokasi promosi media sosial ada & Ads ≤ Rp500.000"
        ads = [b for b in self.just.baris
               if re.search(r'\bads\b|adsense|iklan|promosi|boost|meta\s+ads|sponsored', b.teks, re.IGNORECASE)]
        if not self.just.baris:
            return CheckItem("6.5", desc, Status.PERINGATAN, "Baris justifikasi anggaran tidak terbaca.")
        if not ads:
            return CheckItem("6.5", desc, Status.TIDAK_LULUS,
                             "Tidak ditemukan alokasi Ads/promosi media sosial. Panduan: RAB harus memuat "
                             "alokasi dana publikasi/promosi di medsos (3 unggahan wajib diiklankan).")
        total = sum(b.total or 0 for b in ads)
        if total > ADS_MEDSOS_MAX:
            return CheckItem("6.5", desc, Status.TIDAK_LULUS,
                             f"Total Ads/promosi {rp(total)} melebihi {rp(ADS_MEDSOS_MAX)}.",
                             catatan=[f"{b.nama}: {rp(b.total)}" for b in ads])
        return CheckItem("6.5", desc, Status.LULUS, f"Ads/promosi media sosial {rp(total)}.")

    # ─── Aritmetika ──────────────────────────────────────────────────────────

    def _check_aritmetika(self) -> CheckItem:
        desc = "Aritmetika justifikasi (volume × harga, subtotal, grand total, terbilang)"
        j = self.just
        if not j.baris and not j.subtotal:
            return CheckItem("6.6", desc, Status.PERINGATAN, "Lampiran Justifikasi Anggaran tidak terbaca.")
        salah = []
        for raw in dict.fromkeys(j.angka_rusak):
            salah.append(f"Format angka rusak: '{raw}'")
        for b in j.baris:
            if not b.hitungan_cocok:
                salah.append(f"{b.nama}: {b.volume:g} × {rp(b.harga)} = {rp(b.volume * b.harga)}, "
                             f"tertulis {rp(b.total)}")
        if j.subtotal and j.grand_total:
            jumlah_sub = sum(v for _, v in j.subtotal)
            if jumlah_sub != j.grand_total:
                salah.append(f"Jumlah subtotal {rp(jumlah_sub)} ≠ GRAND TOTAL {rp(j.grand_total)}")
        if j.grand_total and j.terbilang and not terbilang_cocok(j.terbilang, j.grand_total):
            salah.append(f"Terbilang '{j.terbilang}' ≠ {rp(j.grand_total)} "
                         f"(seharusnya: {terbilang(j.grand_total)} rupiah)")
        if not salah:
            return CheckItem("6.6", desc, Status.LULUS,
                             f"{len(j.baris)} baris, {len(j.subtotal)} subtotal, grand total {rp(j.grand_total)} — "
                             "hitungan konsisten.")
        # PERINGATAN, bukan TIDAK_LULUS: panduan menyebut salah hitung "dapat mempengaruhi
        # hasil penilaian" (nilai kriteria anggaran), dan di sampel ada proposal didanai
        # dengan beberapa salah hitung. Tetap wajib dibereskan sebelum unggah.
        return CheckItem("6.6", desc, Status.PERINGATAN,
                         "Panduan: kesalahan hasil perkalian dan penjumlahan dapat mempengaruhi penilaian. "
                         "Perbaiki semua baris berikut.",
                         catatan=salah[:10])

    def _check_rekap_vs_justifikasi(self) -> CheckItem:
        desc = "Tabel 4.1 Rekap konsisten dengan Lampiran Justifikasi"
        r, j = self.rekap, self.just
        if not r.kategori or not j.grand_total:
            return CheckItem("6.7", desc, Status.PERINGATAN, "Rekap atau justifikasi tidak terbaca lengkap.")
        salah = []
        total_kat = sum(sum(v or 0 for v in k.values()) for k in r.kategori.values())
        if r.jumlah_kategori and r.jumlah_kategori != total_kat:
            salah.append(f"Baris 'Jumlah' rincian {rp(r.jumlah_kategori)} ≠ penjumlahan kategori {rp(total_kat)}")
        if r.sumber:
            total_sumber = sum(v or 0 for v in r.sumber.values())
            if r.jumlah_sumber and r.jumlah_sumber != total_sumber:
                salah.append(f"'Jumlah' Rekap Sumber Dana {rp(r.jumlah_sumber)} ≠ Belmawa+PT+lain {rp(total_sumber)}")
            if total_sumber != total_kat:
                salah.append(f"Rekap Sumber Dana {rp(total_sumber)} ≠ total rincian kategori {rp(total_kat)}")
        if total_kat != j.grand_total:
            salah.append(f"Total Tabel 4.1 {rp(total_kat)} ≠ GRAND TOTAL justifikasi {rp(j.grand_total)}")
        if len(j.subtotal) == len(KATEGORI) and len(r.kategori) == len(KATEGORI):
            for (_, sub), key in zip(j.subtotal, KATEGORI):
                tot = sum(v or 0 for v in r.kategori[key].values())
                if tot != sub:
                    salah.append(f"{KATEGORI_LABEL[key]}: rekap {rp(tot)} ≠ subtotal justifikasi {rp(sub)}")
        if not salah:
            return CheckItem("6.7", desc, Status.LULUS, f"Total {rp(total_kat)} cocok dengan justifikasi.")
        return CheckItem("6.7", desc, Status.PERINGATAN,
                         "Angka rekap dan justifikasi tidak sinkron — samakan sebelum unggah.",
                         catatan=salah)
