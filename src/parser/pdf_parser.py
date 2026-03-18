"""
Modul ekstraksi dan segmentasi konten dari PDF proposal PKM.
Menggunakan pdfplumber untuk teks/tabel dan pymupdf untuk detail font/layout.
"""

import re
import os
from dataclasses import dataclass, field
from typing import Optional
import pdfplumber
import fitz  # pymupdf


@dataclass
class PageInfo:
    page_number: int
    text: str
    width_pt: float
    height_pt: float
    tables: list = field(default_factory=list)
    images: list = field(default_factory=list)
    font_spans: list = field(default_factory=list)


@dataclass
class ProposalDocument:
    file_path: str
    file_name: str
    file_size_mb: float
    jenis_pkm: Optional[str] = None
    judul: Optional[str] = None
    pages: list[PageInfo] = field(default_factory=list)
    full_text: str = ""
    # Segmen-segmen dokumen
    daftar_isi_pages: list[int] = field(default_factory=list)
    core_pages: list[int] = field(default_factory=list)       # Bab 1 – Daftar Pustaka
    lampiran_pages: list[int] = field(default_factory=list)
    # Teks per segmen
    dafpus_text: str = ""
    lampiran_text: str = ""


def parse_pdf(file_path: str) -> ProposalDocument:
    """
    Entry point utama: baca PDF dan kembalikan ProposalDocument lengkap.
    """
    file_name = os.path.basename(file_path)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    doc = ProposalDocument(
        file_path=file_path,
        file_name=file_name,
        file_size_mb=file_size_mb,
    )

    doc.jenis_pkm = _detect_jenis_pkm(file_name)
    doc.pages = _extract_pages(file_path)
    doc.full_text = "\n".join(p.text for p in doc.pages)
    doc.judul = _extract_judul(doc.full_text)

    if doc.jenis_pkm is None:
        doc.jenis_pkm = _detect_jenis_pkm_from_text(doc.full_text)

    _segment_document(doc)

    return doc


def _detect_jenis_pkm(file_name: str) -> Optional[str]:
    """Deteksi jenis PKM dari nama file: namaketua_namaPT_PKM-[JENIS].pdf"""
    match = re.search(r'PKM-?([A-Z]+)', file_name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _detect_jenis_pkm_from_text(text: str) -> Optional[str]:
    """Fallback: cari jenis PKM di dalam konten dokumen."""
    match = re.search(
        r'Program\s+Kreativitas\s+Mahasiswa[^\n]*PKM[-\s]([A-Z]+)',
        text, re.IGNORECASE
    )
    if match:
        return match.group(1).upper()
    match = re.search(r'\bPKM[-\s]([A-Z]{1,3})\b', text)
    if match:
        return match.group(1).upper()
    return None


def _extract_pages(file_path: str) -> list[PageInfo]:
    """
    Gabungkan ekstraksi teks dari pdfplumber dengan info font dari pymupdf.
    """
    pages: list[PageInfo] = []

    fitz_doc = fitz.open(file_path)

    with pdfplumber.open(file_path) as pdf:
        for i, plumber_page in enumerate(pdf.pages):
            text = plumber_page.extract_text() or ""
            tables = plumber_page.extract_tables() or []
            images = plumber_page.images or []
            width_pt = plumber_page.width
            height_pt = plumber_page.height

            font_spans = _extract_font_spans(fitz_doc[i])

            pages.append(PageInfo(
                page_number=i + 1,
                text=text,
                width_pt=width_pt,
                height_pt=height_pt,
                tables=tables,
                images=images,
                font_spans=font_spans,
            ))

    fitz_doc.close()
    return pages


def _extract_font_spans(fitz_page) -> list[dict]:
    """
    Ekstrak span-span teks dengan informasi font dari satu halaman pymupdf.
    Setiap span: {text, font, size, bold, italic, bbox}
    """
    spans = []
    blocks = fitz_page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font_name = span.get("font", "")
                flags = span.get("flags", 0)
                spans.append({
                    "text": span.get("text", ""),
                    "font": font_name,
                    "size": round(span.get("size", 0), 1),
                    "bold": bool(flags & 2**4),
                    "italic": bool(flags & 2**1),
                    "bbox": span.get("bbox"),
                })
    return spans


def _extract_judul(full_text: str) -> Optional[str]:
    """Coba ekstrak baris judul: biasanya teks KAPITAL semua di awal dokumen."""
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    for line in lines[:30]:
        # Judul: huruf kapital, panjang 5-30 kata, bukan heading bab
        words = line.split()
        if (5 <= len(words) <= 30
                and line == line.upper()
                and not re.match(r'^BAB\s+[IVX\d]', line)):
            return line
    return None


def _count_toc_dot_lines(page_text: str) -> int:
    """
    Hitung baris yang mengandung titik-titik panjang (ciri halaman Daftar Isi).
    Contoh baris TOC: "BAB 1. PENDAHULUAN ........... 1"
    """
    return sum(1 for line in page_text.split('\n') if re.search(r'\.{4,}', line))


def _is_toc_page(page_text: str) -> bool:
    """Halaman dianggap Daftar Isi jika memiliki ≥3 baris ber-titik-titik."""
    return _count_toc_dot_lines(page_text) >= 3


def _is_bab1_heading(page_text: str) -> bool:
    """
    Cek apakah halaman ini benar-benar halaman BAB 1, bukan entry di Daftar Isi.
    Strategi ganda:
    1. Baris tidak diikuti titik-titik (bukan TOC entry)
    2. Halaman secara keseluruhan bukan Daftar Isi (sedikit titik-titik)
    """
    if _is_toc_page(page_text):
        return False
    for line in page_text.split('\n'):
        stripped = line.strip()
        if re.match(r'^BAB\s+(1|I)[.\s]', stripped, re.IGNORECASE):
            if re.search(r'\.{3,}\s*\d+\s*$', stripped):
                continue
            if len(stripped) < 60:
                return True
    return False


def _is_dafpus_heading(page_text: str) -> bool:
    """
    Cek apakah halaman ini halaman DAFTAR PUSTAKA yang sesungguhnya.

    Masalah umum: pdfplumber sering mengekstrak baris Daftar Isi
    "DAFTAR PUSTAKA ......... 9" menjadi dua baris terpisah:
    - baris 1: "DAFTAR PUSTAKA"
    - baris 2: "9"
    Akibatnya, _is_dafpus_heading bisa salah mendeteksi halaman Daftar Isi.

    Solusi lapis:
    1. Tolak jika halaman Daftar Isi (≥3 baris ber-titik-titik).
    2. Tetap return True meski tidak ada (YYYY) — karena ada proposal
       yang meletakkan heading DAFTAR PUSTAKA di akhir halaman BAB 4
       dan entri mulai di halaman berikutnya.
    """
    has_heading = any(
        re.match(r'^DAFTAR\s+PUSTAKA\s*$', line.strip().upper())
        for line in page_text.split('\n')
    )
    if not has_heading:
        return False
    # Daftar Isi dikenali dari banyaknya baris ber-titik-titik
    if _is_toc_page(page_text):
        return False
    # Jika halaman HANYA berisi heading + nomor halaman (Daftar Isi sparse),
    # tolak jika lebih dari setengah baris adalah angka pendek saja
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
    number_only = sum(1 for l in lines if re.match(r'^\d{1,3}$', l))
    if len(lines) > 0 and number_only / len(lines) > 0.4:
        # Kemungkinan halaman Daftar Isi sparse (kolom nomor terpisah)
        return False
    return True


def _is_lampiran_heading(page_text: str, dafpus_confirmed: bool) -> bool:
    """
    Cek apakah halaman ini adalah bagian LAMPIRAN yang sesungguhnya.
    - Hanya berlaku setelah DAFTAR PUSTAKA dikonfirmasi
    - Heading harus "LAMPIRAN" saja (bukan "DAFTAR LAMPIRAN")
    - Halaman bukan Daftar Isi
    Catatan: "LAMPIRAN ..... 11" di Daftar Isi TIDAK akan memenuhi syarat ini
    karena halaman Daftar Isi terdeteksi sebagai TOC page.
    """
    if not dafpus_confirmed or _is_toc_page(page_text):
        return False
    for line in page_text.split('\n'):
        stripped = line.strip().upper()
        # Hanya "LAMPIRAN" standalone (bukan "DAFTAR LAMPIRAN" atau "LAMPIRAN 1")
        if stripped == 'LAMPIRAN':
            return True
    return False


def _segment_document(doc: ProposalDocument):
    """
    Pisahkan halaman menjadi 3 segmen dokumen PKM:
      - daftar_isi_pages : sebelum BAB 1 (front matter)
      - core_pages       : BAB 1 s.d. DAFTAR PUSTAKA (inklusif)
      - lampiran_pages   : sesudah DAFTAR PUSTAKA

    Urutan standar PKM:
    DAFTAR ISI → DAFTAR GAMBAR → DAFTAR TABEL → DAFTAR LAMPIRAN
    → BAB 1–4 → DAFTAR PUSTAKA → LAMPIRAN
    """
    bab1_page = None
    dafpus_page = None
    lampiran_page = None

    for page in doc.pages:
        if bab1_page is None and _is_bab1_heading(page.text):
            bab1_page = page.page_number

        # Daftar Pustaka harus ditemukan SETELAH BAB 1
        if (dafpus_page is None
                and bab1_page is not None
                and page.page_number >= bab1_page
                and _is_dafpus_heading(page.text)):
            dafpus_page = page.page_number

        # Lampiran harus setelah Daftar Pustaka, bukan di TOC
        if (lampiran_page is None
                and dafpus_page is not None
                and page.page_number > dafpus_page
                and _is_lampiran_heading(page.text, dafpus_confirmed=True)):
            lampiran_page = page.page_number

    for page in doc.pages:
        n = page.page_number
        if bab1_page and dafpus_page:
            if n < bab1_page:
                doc.daftar_isi_pages.append(n)
            elif bab1_page <= n <= dafpus_page:
                doc.core_pages.append(n)
            else:
                doc.lampiran_pages.append(n)
        else:
            doc.core_pages.append(n)

    # Teks Daftar Pustaka: dari halaman dafpus sampai sebelum lampiran
    if dafpus_page:
        end_idx = (lampiran_page - 1) if lampiran_page else len(doc.pages)
        doc.dafpus_text = "\n".join(
            doc.pages[i].text
            for i in range(dafpus_page - 1, end_idx)
        )

    if lampiran_page:
        doc.lampiran_text = "\n".join(
            doc.pages[i].text for i in range(lampiran_page - 1, len(doc.pages))
        )
