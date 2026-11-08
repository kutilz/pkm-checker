"""
Utilitas membaca Rencana Anggaran Biaya (RAB) dari teks proposal PKM.

- parse_amount       : "5.100.000,00" / "400,000.00" / "850.000" → int
- parse_rekap        : Tabel 4.1 Rekapitulasi RAB → nilai per kategori & sumber dana
- parse_justifikasi  : Lampiran 2 Justifikasi Anggaran → baris item, subtotal, grand total
- terbilang          : 9_493_000 → "sembilan juta empat ratus sembilan puluh tiga ribu"
"""

import re
from dataclasses import dataclass, field
from typing import Optional

AMOUNT_RE = r'\d[\d.,]*\d|\d'

KATEGORI = ["bahan", "sewa", "transport", "lain"]
KATEGORI_LABEL = {
    "bahan": "Bahan habis pakai",
    "sewa": "Sewa dan jasa",
    "transport": "Transportasi lokal",
    "lain": "Lain-lain",
}


def parse_amount(raw: str) -> Optional[int]:
    """
    Ubah angka Rupiah ke int. Mendukung format Indonesia (1.000.000,00),
    format Inggris yang kadang terselip (400,000.00), dan angka polos.
    Mengembalikan None bila formatnya rusak (mis. "800.00,00").
    """
    s = re.sub(r'(?i)rp\.?|\s', '', raw or '')
    if not s or s == '-':
        return None
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?', s):        # 1.000.000,00
        return int(s.split(',')[0].replace('.', ''))
    if re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?', s):        # 1,000,000.00
        return int(s.split('.')[0].replace(',', ''))
    if re.fullmatch(r'\d+(?:,\d{1,2})?', s):                         # 850000 / 850000,00
        return int(s.split(',')[0])
    if re.fullmatch(r'\d+\.\d{1,2}', s):                             # 850000.00
        return int(s.split('.')[0])
    return None


# ─── Rekapitulasi (Tabel 4.1) ────────────────────────────────────────────────

@dataclass
class Rekap:
    # Nilai per kategori per sumber, urut sesuai format panduan (bahan, sewa, transport, lain)
    kategori: dict = field(default_factory=dict)        # {"bahan": {"belmawa": x, "pt": y, "lain": z}, ...}
    jumlah_kategori: Optional[int] = None                # baris "Jumlah" di bawah 4 kategori
    sumber: dict = field(default_factory=dict)          # baris "Rekap Sumber Dana": {"belmawa": x, "pt": y, "lain": z}
    jumlah_sumber: Optional[int] = None

    @property
    def belmawa(self) -> Optional[int]:
        if self.sumber.get("belmawa"):
            return self.sumber["belmawa"]
        vals = [k.get("belmawa") for k in self.kategori.values() if k.get("belmawa")]
        return sum(vals) if vals else None

    def total_sumber(self, src: str) -> int:
        if src in self.sumber:
            return self.sumber.get(src) or 0
        return sum((k.get(src) or 0) for k in self.kategori.values())


_SRC_RE = re.compile(
    r'(Belmawa|Perguruan\s+Tinggi|Instansi\s+Lain(?:\s*\(jika\s+ada\))?)\s*:?\s*(?:Rp\.?\s*)?'
    rf'({AMOUNT_RE}|-)?'
    r'|\b(Jumlah|Total)\b\s*(?:\(Rp\))?\s*:?\s*(?:Rp\.?\s*)?'
    rf'({AMOUNT_RE})',
    re.IGNORECASE,
)


def _src_key(label: str) -> str:
    label = label.lower()
    if label.startswith("belmawa"):
        return "belmawa"
    if label.startswith("perguruan"):
        return "pt"
    return "lain"


def extract_rekap_text(core_text: str) -> str:
    """Potong teks dari judul tabel rekap sampai sub-bab Jadwal Kegiatan."""
    start = re.search(r'Rekapitulasi\s+Rencana\s+Anggaran|Rekapitulasi\s+RAB|4\.1\s+\S+', core_text, re.IGNORECASE)
    if not start:
        start = re.search(r'Anggaran\s+Biaya', core_text, re.IGNORECASE)
    if not start:
        return ""
    rest = core_text[start.start():]
    end = re.search(r'\n\s*(?:4\.2|5\.2)\s+Jadwal|Tabel\s+\d\.\d\s+Jadwal|\n\s*Jadwal\s+Kegiatan', rest, re.IGNORECASE)
    return rest[:end.start()] if end else rest[:3000]


def parse_rekap(text: str) -> Rekap:
    """
    Baca tabel rekap. Pdfplumber tidak selalu menjaga urutan label & angka,
    jadi yang dipakai adalah urutan kemunculan pasangan "<sumber> <angka>" dan
    baris "Jumlah": kelompok sebelum Jumlah pertama = rincian per kategori,
    kelompok berikutnya = Rekap Sumber Dana.
    """
    rekap = Rekap()
    groups: list[list[tuple[str, Optional[int]]]] = [[]]
    jumlahs: list[int] = []
    for m in _SRC_RE.finditer(text):
        if m.group(1):
            raw = m.group(2)
            val = parse_amount(raw) if raw and raw != '-' else 0
            groups[-1].append((_src_key(m.group(1)), val))
        elif m.group(3):
            val = parse_amount(m.group(4))
            if val is None or val < 100_000:
                continue
            jumlahs.append(val)
            groups.append([])

    detail = groups[0] if groups else []
    # Bagi rincian ke 4 kategori: setiap kali sumber "belmawa" muncul lagi → kategori baru
    cat_idx = -1
    for src, val in detail:
        if src == "belmawa" or cat_idx < 0:
            cat_idx += 1
            if cat_idx >= len(KATEGORI):
                break
            rekap.kategori[KATEGORI[cat_idx]] = {}
        rekap.kategori[KATEGORI[cat_idx]][src] = val
    if jumlahs:
        rekap.jumlah_kategori = jumlahs[0]
    if len(groups) > 1:
        for src, val in groups[1]:
            rekap.sumber.setdefault(src, val)
    if len(jumlahs) > 1:
        rekap.jumlah_sumber = jumlahs[1]
    return rekap


# ─── Justifikasi Anggaran (Lampiran 2) ───────────────────────────────────────

@dataclass
class Baris:
    teks: str
    kategori: Optional[str]
    volume: float
    harga: Optional[int]
    total: Optional[int]
    harga_raw: str
    total_raw: str
    # Tafsiran volume lain: nama barang bisa berakhir angka ("Akrilik 10cm x 1 buah")
    volume_alt: tuple = ()

    @property
    def nama(self) -> str:
        return self.teks.strip()[:45]

    @property
    def hitungan_cocok(self) -> bool:
        if not self.harga or not self.total:
            return True
        return any(abs(v * self.harga - self.total) <= 1 for v in (self.volume, *self.volume_alt))


@dataclass
class Justifikasi:
    baris: list[Baris] = field(default_factory=list)
    subtotal: list[tuple[Optional[str], int]] = field(default_factory=list)   # (kategori, nilai)
    grand_total: Optional[int] = None
    terbilang: Optional[str] = None
    angka_rusak: list[str] = field(default_factory=list)


# Volume bisa "2 buah", "6 x 3 orang", "9 x 5", atau "8 Kali / 5 Orang"
_ROW_RE = re.compile(
    r'(?:^|\s)(\d+(?:[.,]\d+)?)\s*(?:([A-Za-z]+)\s*)?(?:[xX×/]\s*(\d+(?:[.,]\d+)?)\s*)?'
    r'([A-Za-z][A-Za-z/.\-]*)?\s+(?:Rp\.?\s*)?(' + AMOUNT_RE + r')\s+(?:Rp\.?\s*)?(' + AMOUNT_RE + r')\s*$'
)
_SUBTOTAL_RE = re.compile(r'SUB\s*-?\s*TOTAL\s*(?:\(Rp\))?\s*:?\s*(?:Rp\.?\s*)?(' + AMOUNT_RE + ')', re.IGNORECASE)
_GRAND_RE = re.compile(r'GRAND\s*TOTAL\s*(?:\(Rp\))?\s*:?\s*(?:Rp\.?\s*)?(' + AMOUNT_RE + ')', re.IGNORECASE)
_KATEGORI_HEADER = [
    ("bahan", re.compile(r'\b(?:belanja\s+bahan|bahan\s+habis\s+pakai)\b', re.I)),
    ("sewa", re.compile(r'\b(?:belanja\s+sewa|(?:biaya\s+)?sewa\s+dan\s+jasa)\b', re.I)),
    ("transport", re.compile(r'\b(?:perjalanan(?:\s+lokal)?|transportasi\s+lo[ck]al)\s*(?:\(maks|$)', re.I)),
    ("lain", re.compile(r'\blain\s*-\s*lain\b', re.I)),
]


def extract_justifikasi_text(lampiran_text: str) -> str:
    start = re.search(r'Justifikasi\s+Anggaran', lampiran_text, re.IGNORECASE)
    if not start:
        return ""
    rest = lampiran_text[start.start():]
    end = re.search(r'Lampiran\s*3\b|Susunan\s+(?:Tim|Organisasi)', rest[30:], re.IGNORECASE)
    return rest[: end.start() + 30] if end else rest[:8000]


def _to_float(s: Optional[str]) -> float:
    if not s:
        return 1.0
    try:
        return float(s.replace(',', '.'))
    except ValueError:
        return 1.0


def parse_justifikasi(text: str) -> Justifikasi:
    j = Justifikasi()
    kategori: Optional[str] = None
    lines = [l.strip() for l in text.split('\n')]
    for line in lines:
        if not line:
            continue
        for key, pat in _KATEGORI_HEADER:
            if pat.search(line) and not _ROW_RE.search(line):
                kategori = key
        if re.search(r'GRAND\s*TOTAL', line, re.I):
            m = _GRAND_RE.search(line)
            if m and j.grand_total is None:
                j.grand_total = parse_amount(m.group(1))
            continue
        m = _SUBTOTAL_RE.search(line)
        if m:
            val = parse_amount(m.group(1))
            if val is None:
                j.angka_rusak.append(m.group(1))
            else:
                j.subtotal.append((kategori, val))
            # Baris subtotal sering menempel dengan nomor & judul kategori berikutnya
            rest = line[m.end():]
            for key, pat in _KATEGORI_HEADER:
                if pat.search(rest):
                    kategori = key
            continue
        m = _ROW_RE.search(line)
        if not m:
            continue
        vol1, _unit1, vol2, _unit2, harga_raw, total_raw = m.groups()
        harga, total = parse_amount(harga_raw), parse_amount(total_raw)
        for raw, val in ((harga_raw, harga), (total_raw, total)):
            if val is None:
                j.angka_rusak.append(raw)
        j.baris.append(Baris(
            teks=line[:m.start()].strip() or line,
            kategori=kategori,
            volume=_to_float(vol1) * _to_float(vol2),
            harga=harga, total=total,
            harga_raw=harga_raw, total_raw=total_raw,
            volume_alt=(_to_float(vol2),) if vol2 else (),
        ))

    flat = " ".join(lines)
    t = re.search(r'\(\s*(?:terbilang\s*:?\s*)?([A-Za-z][A-Za-z\s]*?rupiah)\s*\)', flat, re.IGNORECASE)
    if t:
        j.terbilang = re.sub(r'\s+', ' ', t.group(1)).strip()
    return j


# ─── Terbilang ───────────────────────────────────────────────────────────────

_SATUAN = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan",
           "sembilan", "sepuluh", "sebelas"]


def terbilang(n: int) -> str:
    n = int(n)
    if n < 12:
        return _SATUAN[n]
    if n < 20:
        return f"{_SATUAN[n - 10]} belas"
    if n < 100:
        return f"{_SATUAN[n // 10]} puluh {terbilang(n % 10)}".strip()
    if n < 200:
        return f"seratus {terbilang(n - 100)}".strip()
    if n < 1000:
        return f"{_SATUAN[n // 100]} ratus {terbilang(n % 100)}".strip()
    if n < 2000:
        return f"seribu {terbilang(n - 1000)}".strip()
    if n < 1_000_000:
        return f"{terbilang(n // 1000)} ribu {terbilang(n % 1000)}".strip()
    if n < 1_000_000_000:
        return f"{terbilang(n // 1_000_000)} juta {terbilang(n % 1_000_000)}".strip()
    return f"{terbilang(n // 1_000_000_000)} miliar {terbilang(n % 1_000_000_000)}".strip()


def normalisasi_terbilang(s: str) -> str:
    s = s.lower()
    s = re.sub(r'\b(?:terbilang|rupiah|rp)\b', ' ', s)
    s = re.sub(r'[^a-z ]', ' ', s)
    s = re.sub(r'\bsatu juta\b', 'satu juta', s)
    return re.sub(r'\s+', ' ', s).strip()


def terbilang_cocok(tulisan: str, nilai: int) -> bool:
    got = normalisasi_terbilang(tulisan)
    expected = terbilang(nilai)
    alt = re.sub(r'^satu juta', 'sejuta', expected)
    return got in (expected, alt)
