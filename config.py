import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Bisa di-override lewat env/secrets GEMINI_MODEL kalau model ini dipensiunkan Google.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

MAX_FILE_SIZE_MB = 5
MAX_CORE_PAGES = 10

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

JENIS_PKM_VALID = ["RE", "RSH", "K", "PM", "PI", "KC", "KI", "VGK", "GFT", "AI"]

# ─── Format Daftar Pustaka ────────────────────────────────────────────────────
# Pilihan: "APA"      → hanya terima format APA/IEEE (Author. YYYY. Title.)
#          "HARVARD"  → hanya terima format Harvard (Author (YYYY) 'Title'...)
#          "KEDUANYA" → terima keduanya (default — paling fleksibel)
DAFPUS_FORMAT: str = "KEDUANYA"

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

STRUKTUR_BAB_PKM = {
    "RE":  {"bab2": "Tinjauan Pustaka",              "bab3": "Metode Penelitian",     "bab4": "Biaya dan Jadwal Kegiatan"},
    "RSH": {"bab2": "Tinjauan Pustaka",              "bab3": "Metode Penelitian",     "bab4": "Biaya dan Jadwal Kegiatan"},
    "K":   {"bab2": "Gambaran Umum Rencana Usaha",   "bab3": "Metode Pelaksanaan",    "bab4": "Biaya dan Jadwal Kegiatan"},
    "PM":  {"bab2": "Gambaran Umum Mitra",           "bab3": "Metode Pelaksanaan",    "bab4": "Biaya dan Jadwal Kegiatan"},
    "PI":  {"bab2": "Gambaran Umum Mitra Usaha",     "bab3": "Metode Pelaksanaan",    "bab4": "Biaya dan Jadwal Kegiatan"},
    "KC":  {"bab2": "Tinjauan Pustaka",              "bab3": "Tahap Pelaksanaan",     "bab4": "Biaya dan Jadwal Kegiatan"},
    "KI":  {"bab2": "Tinjauan Pustaka",              "bab3": "Tahap Pelaksanaan",    "bab4": "Biaya dan Jadwal Kegiatan"},
    "VGK": {"bab2": "Gambaran Umum Gagasan",         "bab3": "Metode Pelaksanaan",    "bab4": "Biaya dan Jadwal Kegiatan"},
    "GFT": {"bab2": "Pendahuluan",                   "bab3": "Gagasan",               "bab4": "Kesimpulan"},
    "AI":  {"bab2": "(format artikel ilmiah)",       "bab3": "—",                     "bab4": "—"},
}

ITEM_TERLARANG_RAB = [
    "honorarium", "konsumsi tim", "hadiah tim", "konsumsi dosen", "honor dosen",
    "sewa pc", "sewa laptop", "sewa printer", "sewa ponsel", "sewa kamera", "sewa aula",
    "flashdisk", "harddisk", "flash disk", "hard disk",
    "biaya seminar", "publikasi jurnal",
    "penggandaan laporan", "penjilidan laporan",
]
