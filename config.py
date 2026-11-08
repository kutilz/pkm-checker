import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Bisa di-override lewat env/secrets GEMINI_MODEL kalau model ini dipensiunkan Google.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

MAX_FILE_SIZE_MB = 5
MAX_CORE_PAGES = 10

# Tahun siklus PKM yang diperiksa. Dipakai untuk menangkap proposal daur ulang
# (mis. masih menyebut "tema PKM 2025" atau "tahun anggaran 2025").
PKM_TAHUN = 2026

FONT_REQUIRED = "TimesNewRoman"
FONT_SIZE_REQUIRED = 12
LINE_SPACING_REQUIRED = 1.15
LINE_SPACING_TOLERANCE = 0.05

MARGIN_LEFT_CM = 4.0
MARGIN_OTHER_CM = 3.0
PAGE_WIDTH_CM = 21.0
PAGE_HEIGHT_CM = 29.7

DANA_BELMAWA_MIN = 6_000_000
DANA_BELMAWA_MAX = 8_000_000
DANA_PT_MAX = 2_000_000
DANA_INSTANSI_MAX = 1_000_000

OPERASIONAL_MIN_PCT = 0.80
ADMINISTRASI_MAX_PCT = 0.20
BAHAN_HABIS_MAX_PCT = 0.60
SEWA_JASA_MAX_PCT = 0.15
TRANSPORTASI_MAX_PCT = 0.30
LAIN_LAIN_MAX_PCT = 0.15
ADS_MEDSOS_MAX = 500_000
ITEM_MAX_PRICE = 1_000_000
KUOTA_INTERNET_MAX_PER_BULAN = 100_000
LISENSI_MAX_BULAN = 6
KERTAS_MAX_RIM = 2

JENIS_PKM_VALID = ["RE", "RSH", "K", "PM", "PI", "KC", "KI", "VGK", "GFT", "AI"]

# ─── Format Daftar Pustaka ────────────────────────────────────────────────────
# Panduan 2026 (Lampiran "Format Penyusunan Rujukan"): Harvard, tahun di dalam
# kurung setelah nama penulis → "Nama, I. (2020) 'Judul', Jurnal, 1(2), pp. 3-4."
# Pilihan: "HARVARD"  → gaya lama "Nama, I. 2020. Judul." diberi PERINGATAN (default)
#          "APA"      → hanya terima gaya "Nama, I. 2020. Judul."
#          "KEDUANYA" → terima keduanya tanpa peringatan
DAFPUS_FORMAT: str = "HARVARD"

TEMA_PKM_2026 = [
    "Kemandirian Pangan, Energi, dan Air",
    "Kesehatan dan Gizi Masyarakat",
    "Pencegahan dan Pemberantasan Korupsi",
    "Pemberantasan Kemiskinan",
    "Pencegahan dan Pemberantasan Narkoba",
    "Penguatan Pendidikan, Sains, dan Teknologi",
    "Penguatan Kesetaraan Gender dan Perlindungan Hak Perempuan, Anak, Disabilitas",
    "Pelestarian Lingkungan dan Mitigasi Bencana",
    "Pemerataan Ekonomi, Penguatan UMKM, dan Pembangunan IKN",
    "Pelestarian Seni Budaya dan Peningkatan Ekonomi Kreatif",
]

# Kata kunci per tema (dipakai untuk mendeteksi kaitan proposal dengan tema).
# Urutan sama dengan TEMA_PKM_2026 (indeks 0 = tema 1).
TEMA_KATA_KUNCI = [
    ["pangan", "pertanian", "petani", "hortikultura", "panen", "pupuk", "hama", "irigasi",
     "perikanan", "peternak", "energi", "listrik", "surya", "air bersih", "sumber air"],
    ["kesehatan", "gizi", "stunting", "penyakit", "medis", "pasien", "klinis", "rumah sakit",
     "neonat", "bayi", "foodborne", "keamanan pangan", "nutrisi", "sanitasi"],
    ["korupsi", "gratifikasi", "suap", "antikorupsi"],
    ["kemiskinan", "miskin", "prasejahtera", "pengangguran"],
    ["narkoba", "narkotika", "napza", "psikotropika"],
    ["pendidikan", "pembelajaran", "sekolah", "siswa", "guru", "literasi", "sains"],
    ["gender", "perempuan", "wanita", "disabilitas", "difabel", "tunanetra", "tunarungu",
     "tunadaksa", "pelecehan", "kekerasan seksual", "perlindungan anak"],
    ["lingkungan", "sampah", "limbah", "pencemaran", "emisi", "iklim", "bencana", "banjir",
     "gempa", "longsor", "mitigasi", "ramah lingkungan"],
    ["umkm", "usaha mikro", "pemerataan ekonomi", "ibu kota nusantara", "ikn", "koperasi",
     "pedagang"],
    ["seni", "budaya", "tradisional", "batik", "ekonomi kreatif", "pariwisata", "kearifan lokal"],
]

# Sistematika isi utama proposal per bidang (Panduan PKM 2026, buku per bidang).
# Elemen ke-i = judul BAB (i+1). None = format khusus (artikel), cek bab dilewati.
STRUKTUR_BAB_PKM = {
    "RE":  ["Pendahuluan", "Tinjauan Pustaka", "Metode Penelitian", "Biaya dan Jadwal Kegiatan"],
    "RSH": ["Pendahuluan", "Tinjauan Pustaka", "Metode Penelitian", "Biaya dan Jadwal Kegiatan"],
    "K":   ["Pendahuluan", "Gambaran Umum Rencana Usaha", "Metode Pelaksanaan", "Biaya dan Jadwal Kegiatan"],
    "PM":  ["Pendahuluan", "Gambaran Umum Masyarakat Mitra", "Metode Pelaksanaan", "Biaya dan Jadwal Kegiatan"],
    "PI":  ["Pendahuluan", "Tinjauan Pustaka", "Metode Pelaksanaan", "Biaya dan Jadwal Kegiatan"],
    "KC":  ["Pendahuluan", "Tinjauan Pustaka", "Tahap Pelaksanaan", "Biaya dan Jadwal Kegiatan"],
    "KI":  ["Pendahuluan", "Tinjauan Pustaka", "Tahap Pelaksanaan", "Biaya dan Jadwal Kegiatan"],
    "VGK": ["Pendahuluan", "Gagasan", "Skenario Konten", "Metode Pelaksanaan", "Biaya dan Jadwal Kegiatan"],
    "GFT": None,
    "AI":  None,
}

# Lampiran khusus per bidang di luar 5 lampiran umum
# (biodata, justifikasi, susunan tim, surat pernyataan, uji similaritas).
LAMPIRAN_KHUSUS_PKM = {
    "KC": [("Gambaran Teknologi yang akan Dikembangkan", [r'gambaran\s+teknologi'])],
    "KI": [("Gambaran Konsep Karya Inovatif", [r'gambaran\s+konsep', r'konsep\s+karya\s+inovatif'])],
    "PI": [("Surat Pernyataan Kesediaan Bekerja Sama dari Mitra", [r'kesediaan\s+bekerja\s*sama', r'pernyataan\s+mitra']),
           ("Gambaran IPTEK yang akan Diterapkan", [r'gambaran\s+iptek']),
           ("Denah Detail Lokasi Mitra", [r'denah'])],
    "PM": [("Surat Pernyataan Kesediaan Bekerja Sama dari Mitra", [r'kesediaan\s+bekerja\s*sama', r'pernyataan\s+mitra']),
           ("Denah Detail Lokasi Mitra", [r'denah'])],
}

# Item yang tidak diperkenankan di RAB (Panduan 2026). (label, regex)
ITEM_TERLARANG_RAB = [
    ("honorarium/honor", r'\bhonor(?:arium)?\b'),
    ("konsumsi", r'\bkonsumsi\b'),
    ("hadiah", r'\bhadiah\b'),
    ("sewa PC/laptop/printer/ponsel/kamera/ruangan", r'\bsewa\s+(?:pc|komputer|laptop|printer|ponsel|hp|kamera|tempat|ruang(?:an)?|aula)\b'),
    ("penyimpanan data (flashdisk/harddisk)", r'\b(?:flash\s*dis[ck]|hard\s*dis[ck]|ssd|micro\s*sd|kartu\s+memori)\b'),
    ("biaya seminar", r'\bseminar\b'),
    ("publikasi hasil di jurnal", r'\bpubli(?:sh|kasi)\s+(?:artikel|jurnal|ilmiah)|\bpendaftaran\s+(?:jurnal|publish|publikasi)|\barticle\s+processing|\bAPC\b'),
    ("penggandaan/penjilidan laporan", r'\b(?:penggandaan|penjilidan|jilid|cetak)\s+laporan\b'),
]
