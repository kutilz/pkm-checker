"""
Utilitas Daftar Pustaka & sitasi untuk format Harvard Panduan PKM 2026.

Contoh format yang dijadikan acuan (Lampiran "Format Penyusunan Rujukan"):
  Tovey, H. (2002) 'Judul artikel', Irish Journal of Sociology, 11(1), pp. 23-42.
  Kelly, M. (2004) Judul halaman. Tersedia di: http://... (Diakses 8 Februari 2025).

Catatan lapangan: kesalahan Daftar Pustaka — walau hanya satu titik — termasuk
penyebab paling sering proposal tidak lolos. Karena itu pemeriksaan di sini
sengaja ketat sampai level tanda baca.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

BULAN_ID = ["januari", "februari", "maret", "april", "mei", "juni", "juli",
            "agustus", "september", "oktober", "november", "desember"]

YEAR_PAREN = re.compile(r'\(\s*((?:19|20)\d{2}[a-z]?|n\.\s?d\.?)\s*\)')
YEAR_OLD = re.compile(r'^(.{2,300}?)([.,])\s*((?:19|20)\d{2}[a-z]?)\s*\.(?:\s|$)')
URL_RE = re.compile(r'https?://|www\.', re.IGNORECASE)
ACCESS_OK = re.compile(
    r'[\(\[]\s*(?:Diakses|Diunduh)\s*:?\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s*[\)\]]',
    re.IGNORECASE)
ETAL = re.compile(r'\bet\.?\s*al\b|\bdkk\b', re.IGNORECASE)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


@dataclass
class Entri:
    teks: str
    baris: list = field(default_factory=list)   # teks per baris visual (untuk cek per baris)
    italic: int = 0
    bold: int = 0
    chars: int = 0
    sizes: set = field(default_factory=set)
    page: Optional[int] = None
    # Hasil analisis
    gaya: str = "?"                    # "harvard" | "lama" | "?"
    penulis: str = ""
    tahun: str = ""
    setelah_tahun: str = ""

    @property
    def kunci(self) -> str:
        """Kata pertama penulis (nama belakang / nama lembaga), dinormalisasi."""
        m = re.match(r"[\w'’\-]+", norm(self.penulis).strip(" '‘’\""))
        return m.group(0) if m else ""

    @property
    def label(self) -> str:
        nama = self.penulis.split(',')[0].strip().rstrip('.').strip()[:35] or self.teks[:35]
        return f"{nama} ({self.tahun or 'tahun?'})"


# ─── Segmentasi entri ────────────────────────────────────────────────────────

_ENTRY_START = re.compile(
    r"^[A-ZÀ-ɏ'‘][\wÀ-ɏ'’\-]+.{0,250}?"
    r"(?:\(\s*(?:19|20)\d{2}[a-z]?\s*\)|\(n\.d\.\)|[.,]\s*(?:19|20)\d{2}[a-z]?\s*\.)"
)


def _join(parts: list[str]) -> str:
    out = ""
    for p in parts:
        if not out:
            out = p
        elif out.endswith(("-", "/", "–")) and not out.endswith((" -", " –")):
            out += p
        else:
            out += " " + p
    return out


def build_entries(lines: list[dict]) -> tuple[list[Entri], Optional[bool]]:
    """
    Pecah baris Daftar Pustaka menjadi entri.

    Utama: pakai hanging indent (baris di margin kiri = awal entri, baris yang
    menjorok = lanjutan). Fallback: pola "Nama ... (Tahun)" bila indentasi tidak
    terbaca. Mengembalikan (entri, hanging_indent) dengan hanging_indent
    True/False/None (None = tidak bisa ditentukan).
    """
    lines = [l for l in lines if l.get("text", "").strip()]
    if not lines:
        return [], None

    left = min(l["x0"] for l in lines)
    at_margin = [l for l in lines if l["x0"] < left + 4]
    indented = [l for l in lines if l["x0"] >= left + 8]

    hanging: Optional[bool]
    if indented and at_margin:
        # Hanging indent: baris di margin = awal entri (diawali huruf kapital / kutip).
        # Kalau justru baris di margin banyak yang diawali huruf kecil, itu indentasi
        # baris pertama (kebalikan hanging indent).
        kapital = sum(1 for l in at_margin if re.match(r"[A-ZÀ-ɏ'‘\"“]", l["text"]))
        hanging = kapital >= len(at_margin) * 0.8
    elif not indented:
        # Semua baris rata kiri: kalau ada entri lebih dari satu baris → tidak ada hanging indent
        not_start = [l for l in at_margin if not _ENTRY_START.match(l["text"])]
        hanging = False if not_start else None
    else:
        hanging = None

    entries: list[Entri] = []
    cur: Optional[Entri] = None

    def new_entry(l):
        return Entri(teks="", baris=[l["text"]], italic=l.get("italic", 0), bold=l.get("bold", 0),
                     chars=l.get("chars", 0), sizes={l.get("size")}, page=l.get("page"))

    for l in lines:
        if hanging:
            is_start = l["x0"] < left + 4
        else:
            is_start = bool(_ENTRY_START.match(l["text"]))
        if is_start or cur is None:
            cur = new_entry(l)
            entries.append(cur)
        else:
            cur.baris.append(l["text"])
            cur.italic += l.get("italic", 0)
            cur.bold += l.get("bold", 0)
            cur.chars += l.get("chars", 0)
            cur.sizes.add(l.get("size"))
    for e in entries:
        e.teks = _join(e.baris)
        analyze_entry(e)
    return entries, hanging


def build_entries_from_text(text: str) -> list[Entri]:
    """Fallback tanpa info posisi (mis. PDF hasil konversi aneh)."""
    lines = []
    for raw in text.split("\n"):
        t = raw.strip()
        if not t or re.fullmatch(r'[\d\s.]+', t) or re.fullmatch(r'DAFTAR\s+PUSTAKA', t, re.I):
            continue
        lines.append({"text": t, "x0": 0.0})
    entries: list[Entri] = []
    for l in lines:
        if _ENTRY_START.match(l["text"]) or not entries:
            entries.append(Entri(teks="", baris=[l["text"]]))
        else:
            entries[-1].baris.append(l["text"])
    for e in entries:
        e.teks = _join(e.baris)
        analyze_entry(e)
    return entries


def analyze_entry(e: Entri) -> None:
    m = YEAR_PAREN.search(e.teks[:400])
    if m:
        e.gaya = "harvard"
        e.penulis = e.teks[:m.start()].strip()
        e.tahun = m.group(1)
        e.setelah_tahun = e.teks[m.end():]
        return
    m = YEAR_OLD.match(e.teks)
    if m:
        e.gaya = "lama"
        # Titik pemisah sebelum tahun ikut milik inisial terakhir ("Rai, B. 2022.")
        e.penulis = (m.group(1) + (m.group(2) if m.group(2) == "." else "")).strip()
        e.tahun = m.group(3)
        e.setelah_tahun = e.teks[m.end():]
        return
    e.gaya = "?"
    # Format salah, tapi tahun tetap diambil agar pencocokan sitasi masih bisa jalan
    m = re.search(r'\b((?:19|20)\d{2}[a-z]?)\b', e.teks[:200])
    if m:
        e.penulis = e.teks[:m.start()].strip()
        e.tahun = m.group(1)
        e.setelah_tahun = e.teks[m.end():]
    else:
        e.penulis = e.teks.split("(")[0][:80]


# ─── Pemeriksaan per entri ───────────────────────────────────────────────────

def entry_issues(e: Entri, gaya_wajib: str = "HARVARD") -> list[tuple[str, str]]:
    """
    Kembalikan daftar (tingkat, pesan). tingkat: "berat" (wajib diperbaiki) /
    "ringan" (sebaiknya diperbaiki).
    """
    issues: list[tuple[str, str]] = []
    t = e.teks.strip()

    if e.gaya == "?":
        issues.append(("berat", "tahun terbit tidak ditemukan / tidak ditulis dalam kurung, mis. (2024)"))
    elif e.gaya == "lama" and gaya_wajib == "HARVARD":
        issues.append(("berat", "tahun harus dalam kurung setelah nama penulis: 'Nama, I. (2024) ...' "
                                "— bukan 'Nama, I. 2024.'"))
    elif e.gaya == "harvard" and gaya_wajib == "APA":
        issues.append(("ringan", "format tahun tidak sesuai setelan APA di config"))

    if ETAL.search(e.penulis):
        issues.append(("berat", "ada 'et al.'/'dkk' di daftar penulis — semua nama penulis wajib ditulis"))

    if not t.endswith((".", ")")):
        issues.append(("berat", f"entri tidak diakhiri titik (berakhir dengan '{t[-12:]}')"))
    if re.search(r'(?<!\.)\.\s?\.(?!\.)', t):
        issues.append(("berat", "ada titik ganda '..'"))
    if re.search(r'\s[,;:](?=\s|$)|\s\.(?=\s|$)', t):
        issues.append(("ringan", "ada spasi sebelum tanda baca (' ,' / ' .')"))
    if re.search(r',\s*,|;\s*;', t):
        issues.append(("ringan", "ada koma/titik koma ganda"))

    # Inisial nama harus bertitik: "Lopez, I." bukan "Lopez, I"
    if e.gaya != "?" and "," in e.penulis:
        bad_init = re.findall(r',\s*((?:[A-Z]\s?){1,3})(?=\s*(?:,|and\b|dan\b|&|$))', e.penulis)
        if bad_init:
            issues.append(("ringan", f"inisial tanpa titik: {', '.join(i.strip() for i in bad_init[:3])}"))

    after = e.setelah_tahun.strip()
    if e.gaya == "harvard" and after.startswith(("'", "‘", '"', "“")):
        # Artikel: 'Judul', Jurnal, Vol(Isu), pp. x–y.
        if not re.search(r"['’\"”]\s*,\s*\S", after):
            issues.append(("ringan", "judul artikel diapit kutip lalu diikuti koma: 'Judul', Nama Jurnal, ..."))
        if not URL_RE.search(after) and not re.search(
                r'\bpp?\.\s*\d|,\s*e?\d{2,}\s*[.,]|\barticle\b|\bID\b|doi', after, re.IGNORECASE):
            issues.append(("ringan", "nomor halaman/artikel tidak ada (mis. ', pp. 23-42.')"))
    if e.gaya == "harvard" and re.match(r'^\.\s', after):
        issues.append(("ringan", "ada titik setelah (Tahun); contoh panduan: 'Nama, I. (2020) Judul ...'"))

    # Rentang halaman: tanpa spasi di sekitar tanda hubung (cek per baris agar
    # pemenggalan baris tidak dianggap salah)
    for b in e.baris:
        if re.search(r'\bpp?\.\s*\d+\s+[–-]\s*\d|\bpp?\.\s*\d+\s*[–-]\s+\d', b):
            issues.append(("ringan", "ada spasi di rentang halaman (tulis 'pp. 71–76')"))
            break

    if URL_RE.search(t):
        acc = ACCESS_OK.search(t)
        if not acc:
            if re.search(r'diakses|diunduh|accessed', t, re.IGNORECASE):
                issues.append(("berat", "format tanggal akses salah — wajib '(Diakses 10 Februari 2026)'"))
            else:
                issues.append(("berat", "URL tanpa tanggal akses — tambahkan '(Diakses DD Bulan YYYY)'"))
        elif norm(acc.group(2)) not in BULAN_ID:
            issues.append(("ringan", f"nama bulan '{acc.group(2)}' sebaiknya bahasa Indonesia"))
        if not re.search(r'Tersedia\s+di\s*:|Available\s+at\s*:', t, re.IGNORECASE):
            issues.append(("ringan", "awali URL dengan 'Tersedia di:'"))

    if e.chars and e.italic == 0:
        issues.append(("ringan", "tidak ada bagian cetak miring (judul jurnal/buku/URL harus italic)"))
    if e.chars and e.bold > e.chars * 0.3:
        issues.append(("ringan", "daftar pustaka harus cetak normal (bukan tebal)"))
    sizes = {s for s in e.sizes if s}
    if sizes and any(abs(s - 12) > 0.6 for s in sizes):
        issues.append(("ringan", f"ukuran huruf bukan 12 pt ({', '.join(str(s) for s in sorted(sizes))})"))
    return issues


# ─── Sitasi dalam naskah ─────────────────────────────────────────────────────

@dataclass
class Sitasi:
    nama: str
    tahun: str
    teks: str
    naratif: bool

    @property
    def kata(self) -> list[str]:
        return [w for w in re.findall(r"[\w'’\-]+", norm(self.nama))
                if w not in {"et", "al", "dkk", "dan", "and"}]


_PAREN = re.compile(r'\(([^()]{1,300})\)')
_PART = re.compile(r'^(?P<nama>[A-ZÀ-ɏ][^\d();]{0,150}?)[,\s]+(?P<tahun>(?:19|20)\d{2}[a-z]?|n\.d\.)$')
_YEAR_ONLY = re.compile(r'^\s*((?:19|20)\d{2}[a-z]?)\s*$')
_NARR_BEFORE = re.compile(
    r"((?:[A-ZÀ-ɏ][\wÀ-ɏ'’\-.]*|et\s+al\.?|dkk\.?|dan|and|&|\([A-Z]{2,}\))"
    r"(?:\s+(?:[A-ZÀ-ɏ][\wÀ-ɏ'’\-.]*|et\s+al\.?|dkk\.?|dan|and|&|\([A-Z]{2,}\)))*)\s*$"
)


_PEMBUKA = re.compile(
    r'^(?:(?:Menurut|Data|Berdasarkan|Penelitian|Studi|Hasil|Laporan|Riset|Kajian|Dalam|Sejalan|'
    r'Selain|Namun|Oleh|Sebagaimana|Seperti|Sementara|Survei|Temuan|Publikasi)\s+)+')


def extract_citations(text: str) -> tuple[list[Sitasi], list[str]]:
    """
    Ambil sitasi (Nama, Tahun) dan Nama (Tahun) dari naskah.
    Kembalikan (sitasi, sitasi_tanpa_koma) — yang kedua berisi contoh
    sitasi berkurung yang tidak memakai koma sebelum tahun, mis. '(Joko et al. 2020)'.
    """
    flat = re.sub(r'\s+', ' ', text)
    out: list[Sitasi] = []
    no_comma: list[str] = []
    for m in _PAREN.finditer(flat):
        inner = m.group(1).strip()
        y = _YEAR_ONLY.match(inner)
        if y:
            before = _NARR_BEFORE.search(flat[max(0, m.start() - 120):m.start()].rstrip())
            if before:
                nama = _PEMBUKA.sub('', before.group(1)).strip()
                if nama:
                    out.append(Sitasi(nama, y.group(1), f"{nama} ({y.group(1)})", True))
            continue
        for part in re.split(r';', inner):
            part = part.strip()
            pm = _PART.match(part)
            if not pm:
                continue
            nama = pm.group("nama").strip().rstrip(",").strip()
            if len(nama) < 2 or re.search(r'\b(?:tahun|bulan|sejak|hingga|periode|edisi)\b', nama, re.I):
                continue
            out.append(Sitasi(nama, pm.group("tahun"), f"({part})", False))
            if not re.search(r',\s*(?:19|20)\d{2}[a-z]?$|,\s*n\.d\.$', part):
                no_comma.append(f"({part})")
    return out, no_comma


def citation_matches(s: Sitasi, e: Entri) -> bool:
    if not e.tahun or norm(s.tahun) != norm(e.tahun):
        return False
    kata = s.kata
    if e.kunci and e.kunci in kata:
        return True
    # Penulis lembaga: cocokkan akronim yang tertulis di entri ("Badan Pusat
    # Statistik (BPS)", "Direktorat Jenderal SDPPI") atau inisial namanya
    # ("World Health Organization" ↔ "WHO").
    akronim = {norm(a) for a in re.findall(r'\b([A-Z]{3,})\b', e.penulis)}
    kapital = re.findall(r'\b([A-Z])[a-zÀ-ɏ]+', e.penulis.split('(')[0])
    if len(kapital) >= 2:
        akronim.add("".join(kapital).lower())
    return any(a in kata for a in akronim)
