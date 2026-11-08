# 📋 PKM 2026 — Sistem Pengecekan Proposal Otomatis

Alat berbasis web untuk memeriksa kesesuaian proposal **Program Kreativitas Mahasiswa (PKM) 2026** terhadap panduan resmi Kemdikbudristek secara otomatis.

Upload PDF proposal → sistem menganalisis → laporan terstruktur dengan status ✅ LULUS / ⚠️ PERINGATAN / ❌ TIDAK LULUS.

---

## ✨ Fitur

| Modul | Apa yang Dicek |
|---|---|
| **Hard Disqualifiers** | Halaman sampul, pengesahan, abstrak terlarang; indeks similaritas |
| **Modul 1 — Identitas** | Format judul (Title Case), panjang judul, akronim, jenis PKM, jumlah anggota tim, NIP/NUPTK dosen |
| **Modul 2 — Format** | Font Times New Roman 12pt, ukuran kertas A4, margin (kiri 4cm / sisanya 3cm), penomoran halaman (romawi + arab) |
| **Modul 3 — Struktur** | Daftar Isi, kelengkapan BAB, heading KAPITAL, batas 10 halaman inti, Daftar Pustaka (APA/Harvard), urutan alfabetis, format tanggal akses URL |
| **Modul 5 — Anggaran** | Rentang dana Belmawa (Rp6–8 juta), item terlarang, kuota internet, sewa lisensi, harga satuan item |
| **Modul 6 — Lampiran** | 6 lampiran wajib, deteksi meterai via gambar |
| **Gemini AI** *(opsional)* | Konsistensi sitasi ↔ daftar pustaka |

---

## 🚀 Instalasi & Menjalankan

### Prasyarat
- Python 3.11+
- pip

### Langkah

```bash
# 1. Clone repository
git clone https://github.com/kutilz/pkm-checker.git
cd pkm-checker

# 2. Buat virtual environment (direkomendasikan)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependensi
pip install -r requirements.txt

# 4. Salin template environment dan isi API key (opsional)
cp .env.example .env
# Edit .env — tambahkan GEMINI_API_KEY jika ingin fitur Gemini aktif

# 5. Jalankan aplikasi
python -m streamlit run app.py
```

Buka browser: **http://localhost:8501**

---

## ☁️ Deploy ke Streamlit Community Cloud (gratis)

1. Login ke https://share.streamlit.io pakai akun GitHub.
2. **Create app** → *Deploy a public app from GitHub*:
   - Repository: `kutilz/pkm-checker`, Branch: `main`, Main file: `app.py`
   - **App URL**: isi subdomain, misalnya `pkm-checker` → `https://pkm-checker.streamlit.app`
3. **Advanced settings**:
   - Python version: `3.11` atau `3.12`
   - Secrets (opsional, untuk fitur Gemini):
     ```toml
     GEMINI_API_KEY = "isi_api_key_kamu"
     ```
4. Klik **Deploy**. Setiap `git push` ke `main` akan otomatis redeploy.

> App gratis akan "tidur" kalau lama tidak dikunjungi; pengunjung berikutnya cukup klik tombol bangunkan (±30 detik).

---

## ⚙️ Konfigurasi

Semua parameter dapat diubah di `config.py`:

| Konstanta | Default | Keterangan |
|---|---|---|
| `DAFPUS_FORMAT` | `"KEDUANYA"` | Format daftar pustaka: `"APA"`, `"HARVARD"`, atau `"KEDUANYA"` |
| `MAX_CORE_PAGES` | `10` | Batas maksimum halaman inti |
| `DANA_BELMAWA_MIN` | `6_000_000` | Minimum dana Belmawa (Rp) |
| `DANA_BELMAWA_MAX` | `8_000_000` | Maksimum dana Belmawa (Rp) |
| `MARGIN_LEFT_CM` | `4.0` | Margin kiri (cm) |
| `MARGIN_OTHER_CM` | `3.0` | Margin kanan/atas/bawah (cm) |

### Format Daftar Pustaka

```python
# config.py
DAFPUS_FORMAT = "KEDUANYA"  # "APA" | "HARVARD" | "KEDUANYA"
```

- **`"APA"`** — Hanya terima `Author. YYYY. Judul. Penerbit.`
- **`"HARVARD"`** — Hanya terima `Author (YYYY) 'Judul'...`
- **`"KEDUANYA"`** — Terima keduanya *(default, paling fleksibel)*

---

## 📁 Struktur Proyek

```
pkm-check/
├── app.py                    # UI Streamlit
├── config.py                 # Semua konstanta & parameter
├── requirements.txt
├── .env.example              # Template environment variables
│
└── src/
    ├── engine.py             # Orkestrasi pipeline pengecekan
    ├── parser/
    │   └── pdf_parser.py     # Ekstraksi & segmentasi PDF
    ├── checkers/
    │   ├── base_checker.py   # Base class & status
    │   ├── hard_disqualifier.py
    │   ├── identity_checker.py
    │   ├── format_checker.py
    │   ├── structure_checker.py
    │   ├── budget_checker.py
    │   └── attachment_checker.py
    ├── ai/
    │   └── gemini_client.py  # Integrasi Google Gemini API
    └── report/
        └── report_generator.py
```

---

## 🔑 Variabel Environment

Buat file `.env` (jangan di-commit!) berdasarkan `.env.example`:

```env
# Opsional — untuk fitur analisis sitasi Gemini
GEMINI_API_KEY=your_api_key_here
```

Dapatkan API key gratis di: https://aistudio.google.com/app/apikey

---

## 📌 Cara Pakai

1. **Upload PDF** proposal PKM (maks. 5 MB, harus bisa dibaca teks — bukan scan penuh)
2. **Isi Judul** dalam format Title Case: *"Judul Proposal Karya Inovatif sebagai Solusi..."*
3. **Pilih Jenis PKM** (atau biarkan deteksi otomatis)
4. Klik **"Mulai Pengecekan"**
5. Lihat laporan per modul, unduh sebagai `.txt`

### Keterbatasan

- PDF yang seluruhnya hasil scan (bukan teks) tidak dapat dianalisis secara penuh
- Meterai dideteksi via keberadaan gambar pada halaman Surat Pernyataan (bukan OCR)
- Panduan PKM dapat berubah antar tahun — pastikan `config.py` sesuai edisi terbaru

---

## 🤝 Kontribusi

Pull request sangat diterima! Untuk perubahan besar, buka issue terlebih dahulu.

1. Fork repository
2. Buat branch fitur: `git checkout -b fitur/nama-fitur`
3. Commit perubahan: `git commit -m "feat: deskripsi singkat"`
4. Push ke branch: `git push origin fitur/nama-fitur`
5. Buat Pull Request

---

## 📄 Lisensi

[MIT License](LICENSE) — bebas digunakan, dimodifikasi, dan didistribusikan dengan atribusi.

---

> Dibuat untuk membantu mahasiswa mempersiapkan proposal PKM 2026 yang sesuai panduan.  
> **Bukan pengganti review resmi dari reviewer PKM.**
