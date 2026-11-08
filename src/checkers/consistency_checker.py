"""
Modul 7 — Tema & Konsistensi Data.

Pemeriksaan yang lahir dari perbandingan proposal didanai vs tidak didanai:
- Semua proposal didanai di sampel mengaitkan diri secara eksplisit dengan tema
  ("PKM Tematik poin 7", "tema tematik kedua", "Misi Asta Cita"). Proposal gagal
  tidak menyebut tema sama sekali, atau menyebut tema yang bukan tema tahun ini.
  Panduan: mahasiswa wajib merancang topik sesuai salah satu tema; Tahap 1 menilai
  "kesesuaian judul dengan tema yang dipilih".
- Proposal gagal memuat data identitas tidak konsisten (anggota tanpa NIM di
  Susunan Tim, ejaan nama berbeda antarbagian). Panduan: nama harus sesuai PDDikti.
"""

import re
from difflib import SequenceMatcher
from .base_checker import BaseChecker, ModulResult, CheckItem, Status
from config import PKM_TAHUN, TEMA_PKM_2026, TEMA_KATA_KUNCI

ORDINAL = {"pertama": 1, "kedua": 2, "ketiga": 3, "keempat": 4, "kelima": 5, "keenam": 6,
           "ketujuh": 7, "kedelapan": 8, "kesembilan": 9, "kesepuluh": 10}


def _skor_tema(teks: str) -> list[tuple[int, int, list[str]]]:
    """[(nomor_tema, skor, kata_yang_cocok)] urut skor tertinggi."""
    low = teks.lower()
    hasil = []
    for i, kata in enumerate(TEMA_KATA_KUNCI, start=1):
        cocok = [k for k in kata if re.search(rf'\b{re.escape(k)}', low)]
        skor = sum(len(re.findall(rf'\b{re.escape(k)}', low)) for k in cocok)
        hasil.append((i, skor, cocok))
    return sorted(hasil, key=lambda x: -x[1])


def _tema_dari_kalimat(kalimat: str) -> int | None:
    low = kalimat.lower()
    m = re.search(r'(?:poin|nomor|no\.?|ke-?)\s*(\d{1,2})\b', low)
    if m and 1 <= int(m.group(1)) <= 10:
        return int(m.group(1))
    for kata, n in ORDINAL.items():
        if re.search(rf'\b(?:tema|tematik)\b[^.]{{0,25}}\b{kata}\b', low):
            return n
    for i, nama in enumerate(TEMA_PKM_2026, start=1):
        inti = [w for w in re.findall(r'[a-z]+', nama.lower()) if len(w) > 4][:2]
        if inti and all(w in low for w in inti):
            return i
    return None


def baris_susunan_tim(doc) -> list[tuple[str, str | None]]:
    """[(nama, nim|None)] dari tabel Lampiran 3 Susunan Tim."""
    rows = []
    mulai = False
    for n in doc.lampiran_pages:
        page = doc.pages[n - 1]
        if re.search(r'Susunan\s+(?:Tim|Organisasi)', page.text, re.IGNORECASE):
            mulai = True
        elif mulai and re.search(r'Surat\s+Pernyataan|Lampiran\s*4', page.text, re.IGNORECASE):
            break
        if not mulai:
            continue
        for table in page.tables:
            col = None
            for row in table:
                cells = [(c or "").replace("\n", " ").strip() for c in row]
                if col is None:
                    for i, c in enumerate(cells):
                        if re.search(r'\bNama\b', c, re.IGNORECASE):
                            col = i
                    continue
                if not cells or not re.fullmatch(r'\d\.?', cells[0] or ""):
                    continue
                sel = cells[col] if col < len(cells) else ""
                nim = re.search(r'\d{6,}', re.sub(r'\s+', '', sel))
                nama = re.split(r'/|\d', sel)[0]
                nama = re.sub(r'-\s+', '', nama).strip(" ,")
                if nama:
                    rows.append((nama, nim.group(0) if nim else None))
    return rows


class ConsistencyChecker(BaseChecker):

    def run(self) -> ModulResult:
        result = ModulResult(nama_modul="Modul 7: Tema & Konsistensi Data", bobot=0.10)
        result.items.extend([
            self._check_tema(),
            self._check_tahun(),
            self._check_nim_susunan_tim(),
            self._check_ejaan_nama(),
        ])
        return result

    # ─── Tema ────────────────────────────────────────────────────────────────

    def _check_tema(self) -> CheckItem:
        desc = f"Kaitan eksplisit dengan salah satu 10 tema PKM {PKM_TAHUN}"
        core = re.sub(r'\s+', ' ', self.doc.core_text_blocks or self.doc.core_text or "")
        if not core:
            return CheckItem("7.1", desc, Status.PERINGATAN, "Bagian inti tidak terbaca.")
        kalimat = re.split(r'(?<=[.!?])\s+', core)
        tema_kal = [k for k in kalimat if re.search(r'\btema(?:tik)?\b', k, re.IGNORECASE)]

        for k in tema_kal:
            m = re.search(r'\b(?:PKM|tema)\D{0,15}\b(20\d{2})\b', k, re.IGNORECASE)
            if m and int(m.group(1)) != PKM_TAHUN:
                return CheckItem(
                    "7.1", desc, Status.TIDAK_LULUS,
                    f"Naskah mengaitkan proposal dengan tema tahun {m.group(1)}, bukan {PKM_TAHUN}: "
                    f"\"{k.strip()[:200]}\". Ganti dengan salah satu 10 tema {PKM_TAHUN} — Tahap 1 menilai "
                    "kesesuaian judul dengan tema yang dipilih.")
        for k in tema_kal:
            n = _tema_dari_kalimat(k)
            if n:
                return CheckItem("7.1", desc, Status.LULUS,
                                 f"Tema {n}: {TEMA_PKM_2026[n - 1]} — \"{k.strip()[:160]}\"")

        terbaik = _skor_tema(core)[0]
        saran = f"Isi paling dekat dengan tema {terbaik[0]} ({TEMA_PKM_2026[terbaik[0] - 1]}; kata: " \
                f"{', '.join(terbaik[2][:5])})." if terbaik[1] else ""
        if tema_kal:
            return CheckItem("7.1", desc, Status.PERINGATAN,
                             "Ada kalimat tentang tema, tetapi tidak cocok dengan 10 tema "
                             f"{PKM_TAHUN}: \"{tema_kal[0].strip()[:160]}\". {saran}")
        if re.search(r'asta\s*cita', core, re.IGNORECASE) and terbaik[1]:
            return CheckItem("7.1", desc, Status.LULUS,
                             f"Kaitan lewat Asta Cita terdeteksi. {saran} Sebaiknya sebut juga nomor & nama "
                             "tema secara eksplisit di Bab 1.")
        return CheckItem("7.1", desc, Status.PERINGATAN,
                         "Bab 1 tidak menyebut tema PKM yang dipilih. Panduan: topik wajib sesuai salah satu "
                         f"10 tema dan Tahap 1 menilai kesesuaian judul dengan tema. {saran} Tambahkan kalimat "
                         "mis. 'Program ini sejalan dengan tema PKM 2026 poin 1: Kemandirian Pangan, Energi, dan Air'.")

    def _check_tahun(self) -> CheckItem:
        desc = f"Referensi tahun PKM konsisten ({PKM_TAHUN})"
        teks = re.sub(r'\s+', ' ', (self.doc.core_text_blocks or "") + " " + (self.doc.lampiran_text or ""))
        pola = re.compile(
            r'\b(?:PKM|tahun\s+anggaran|panduan(?:\s+PKM)?|pedoman(?:\s+PKM)?|tema\s+PKM)\s+(?:tahun\s+)?(20\d{2})\b',
            re.IGNORECASE)
        salah = []
        for m in pola.finditer(teks):
            if int(m.group(1)) != PKM_TAHUN:
                salah.append(f"\"{m.group(0)}\"")
        if not salah:
            return CheckItem("7.2", desc, Status.LULUS, "Tidak ada rujukan ke siklus PKM tahun lain.")
        return CheckItem("7.2", desc, Status.PERINGATAN,
                         f"Ada rujukan ke tahun lain: {', '.join(dict.fromkeys(salah[:5]))}. Proposal daur ulang "
                         f"wajib diperbarui ke format, tema, dan tanggal {PKM_TAHUN} (termasuk tanggal tanda tangan "
                         "di biodata & Surat Pernyataan).")

    # ─── Identitas tim ───────────────────────────────────────────────────────

    def _check_nim_susunan_tim(self) -> CheckItem:
        desc = "Susunan Tim lengkap: setiap anggota bernama & ber-NIM"
        rows = baris_susunan_tim(self.doc)
        if not rows:
            return CheckItem("7.3", desc, Status.PERINGATAN,
                             "Tabel Lampiran 3 (Susunan Tim Pengusul dan Pembagian Tugas) tidak terbaca. Cek manual.")
        tanpa_nim = [nama for nama, nim in rows if not nim]
        catatan = [f"{nama} — NIM tidak tercantum" for nama in tanpa_nim]
        if not 3 <= len(rows) <= 5:
            catatan.append(f"Jumlah baris anggota {len(rows)} (ketentuan: 3–5 mahasiswa)")
        if not catatan:
            return CheckItem("7.3", desc, Status.LULUS,
                             f"{len(rows)} anggota lengkap dengan NIM: " + ", ".join(f"{a}/{b}" for a, b in rows))
        return CheckItem("7.3", desc, Status.TIDAK_LULUS,
                         "Data anggota di Susunan Tim belum lengkap (Tahap 1 menilai kecermatan identitas).",
                         catatan=catatan)

    def _check_ejaan_nama(self) -> CheckItem:
        desc = "Ejaan nama anggota konsisten di seluruh dokumen (sesuai PDDikti)"
        nama_tim = [n for n, _ in baris_susunan_tim(self.doc)]
        nama_tim += re.findall(r'Nama\s+Lengkap\s+([A-Z][A-Za-z\'’.\- ]{3,60}?)\s*(?:\n|$)',
                               self.doc.full_text)
        nama_tim = list(dict.fromkeys(n.strip() for n in nama_tim if len(n.split()) >= 2))
        if not nama_tim:
            return CheckItem("7.4", desc, Status.PERINGATAN, "Nama anggota tidak terbaca untuk dibandingkan.")

        kata = re.findall(r"[A-Za-z'’\-]+", self.doc.full_text)
        varian = {}
        for nama in nama_tim:
            target = nama.split()
            k = len(target)
            for i in range(len(kata) - k + 1):
                window = kata[i:i + k]
                if not all(w[:1].isupper() for w in window):
                    continue
                if [w.lower() for w in window] == [t.lower() for t in target]:
                    continue
                rasio = [SequenceMatcher(None, w.lower(), t.lower()).ratio() for w, t in zip(window, target)]
                if min(rasio) >= 0.8:
                    varian.setdefault(nama, set()).add(" ".join(window))
        if not varian:
            return CheckItem("7.4", desc, Status.LULUS, f"{len(nama_tim)} nama dicek, ejaan konsisten.")
        catatan = [f"'{n}' juga ditulis: {', '.join(sorted(v))}" for n, v in varian.items()]
        return CheckItem("7.4", desc, Status.PERINGATAN,
                         "Ejaan nama berbeda antarbagian. Panduan: nama ditulis lengkap sesuai PDDikti.",
                         catatan=catatan[:6])
