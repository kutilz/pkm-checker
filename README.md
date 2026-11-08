# 📋 PKM 2026 — Sistem Pengecekan Proposal Otomatis

Alat berbasis web untuk memeriksa kesesuaian proposal **Program Kreativitas Mahasiswa (PKM) 2026** terhadap panduan resmi Kemdikbudristek secara otomatis.

Upload PDF proposal → sistem menganalisis → laporan terstruktur dengan status ✅ LULUS / ⚠️ PERINGATAN / ❌ TIDAK LULUS.

---

## ✨ Fitur

| Modul | Apa yang Dicek |
|---|---|
| **Hard Disqualifiers** | Halaman sampul, pengesahan, abstrak terlarang; indeks similaritas |
| **Modul 1 — Identitas** | Judul HURUF KAPITAL, ≤20 kata, Bahasa Indonesia, tanpa akronim tidak baku; kesesuaian bidang (mis. PKM-KI wajib produk *skala penuh*); jumlah anggota; NUPTK dosen 16 digit |
| **Modul 2 — Format** | Times New Roman 12pt, spasi 1,15, kertas A4, margin 4/3/3/3 cm, nomor halaman (romawi kanan-bawah, arab kanan-atas, BAB 1 = hal. 1). Halaman laporan Turnitin dikecualikan |
| **Modul 3 — Struktur** | Daftar Isi & Daftar Lampiran, judul BAB sesuai buku panduan per bidang (termasuk VGK 5 bab), heading `BAB n. JUDUL`, bagian inti ≤10 halaman (Daftar Pustaka yang meluber ikut dihitung) |
| **Modul 4 — Daftar Pustaka & Sitasi** | Ketat sampai tanda baca: hanging indent, tahun dalam kurung `(2024)`, tanpa *et al.*/dkk, setiap entri diakhiri titik, titik ganda, `(Diakses DD Bulan YYYY)`, kutip judul artikel, nomor halaman, italic, urut alfabetis, sitasi ↔ dafpus dua arah, koma di sitasi `(Nama et al., 2020)` — dengan daftar kesalahan per entri |
| **Modul 5 — Anggaran** | Dana Belmawa dari *Rekap Sumber Dana* (bukan Grand Total), dana PT wajib ≤Rp2 jt, komposisi 60/15/30/15%, item terlarang, harga satuan ≤Rp1 jt, kuota/lisensi/kertas, Ads medsos ≤Rp500 rb, aritmetika volume×harga, subtotal, grand total, terbilang, konsistensi rekap ↔ justifikasi |
| **Modul 6 — Lampiran** | Lampiran umum + khusus bidang (KC/KI/PI/PM), halaman tanda tangan basah hasil scan (TT tempel = gugur), Surat Pernyataan scan + meterai |
| **Modul 7 — Tema & Konsistensi** | Kaitan eksplisit dengan salah satu 10 tema 2026, rujukan ke siklus PKM tahun lain (proposal daur ulang), NIM lengkap di Susunan Tim, ejaan nama anggota konsisten |
| **Gemini AI** *(opsional)* | Konsistensi sitasi ↔ daftar pustaka (tambahan di Modul 4) |

Tiap temuan berisi rincian per baris/entri (mis. *"Entri 3 — Nama (2021): entri tidak diakhiri titik"*), jadi bisa langsung diperbaiki.

### Dasar pembaruan (November 2026)

Aturan diperbarui dari **Panduan PKM 2026** (buku umum + buku per bidang) dan perbandingan 5 proposal nyata
(3 didanai, 2 tidak; siklus 2025–2026; satu PT dan satu dosen pendamping yang sama). Ringkasan:

- **Kesalahan versi lama yang diperbaiki** — proposal yang *didanai* justru mendapat skor lebih rendah karena:
  Grand Total (Belmawa + dana PT) dibaca sebagai dana Belmawa; judul diwajibkan Title Case (panduan 2026: **huruf kapital**);
  urutan alfabetis dafpus salah baca untuk daftar penulis panjang; halaman Turnitin ikut dinilai ukuran kertas/font;
  bagian inti berhenti di halaman heading Daftar Pustaka.
- **Pola pada proposal yang tidak didanai**: sewa & jasa >15% (dihitung dari dana Belmawa maupun total),
  tidak menyebut tema / menyebut tema tahun lain, sitasi tanpa koma `(Nama et al. 2020)`, gaya dafpus bukan Harvard 2026
  dan memakai *et al.*, item terlarang (biaya publikasi jurnal), anggota tanpa NIM di Susunan Tim.
- **Tidak menggugurkan di sampel** (jadi PERINGATAN, tetap sebaiknya diperbaiki): kertas Letter, bahan habis pakai sedikit >60%
  dari dana Belmawa tapi ≤60% total, salah hitung di justifikasi, label lama `NIP/NIDN`.
- Informasi dari pengguna lapangan: kesalahan Daftar Pustaka — **walau hanya satu titik** — termasuk penyebab tersering
  proposal tidak lolos. Karena itu Modul 4 sengaja ketat.

> Checker hanya menilai **administrasi** (Tahap 1). Proposal yang rapi administrasinya tetap bisa tidak didanai
> karena substansi (Tahap 2: kreativitas gagasan, urgensi masalah, ketepatan IPTEK & metode, potensi).

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
| `PKM_TAHUN` | `2026` | Siklus PKM yang diperiksa (deteksi tema/tahun proposal daur ulang) |
| `DAFPUS_FORMAT` | `"HARVARD"` | Format daftar pustaka: `"HARVARD"`, `"APA"`, atau `"KEDUANYA"` |
| `MAX_CORE_PAGES` | `10` | Batas maksimum halaman inti |
| `DANA_BELMAWA_MIN` | `6_000_000` | Minimum dana Belmawa (Rp) |
| `DANA_BELMAWA_MAX` | `8_000_000` | Maksimum dana Belmawa (Rp) |
| `MARGIN_LEFT_CM` | `4.0` | Margin kiri (cm) |
| `MARGIN_OTHER_CM` | `3.0` | Margin kanan/atas/bawah (cm) |

### Format Daftar Pustaka

```python
# config.py
DAFPUS_FORMAT = "HARVARD"  # "HARVARD" | "APA" | "KEDUANYA"
```

- **`"HARVARD"`** *(default, sesuai Panduan 2026)* — `Nama, I. (2024) 'Judul', Jurnal, 1(2), pp. 3-4.`; gaya lama `Nama, I. 2024. Judul.` ditandai TIDAK LULUS
- **`"APA"`** — Hanya terima `Nama, I. 2024. Judul. Penerbit.`
- **`"KEDUANYA"`** — Terima keduanya

---

## 📁 Struktur Proyek

```
pkm-check/
├── app.py                    # UI Streamlit: alur halaman, mode cek & bandingkan
├── config.py                 # Semua konstanta & parameter
├── requirements.txt
├── .env.example              # Template environment variables
├── samples/
│   └── sampel.json           # Sampel cepat (hasil asli, data pribadi disamarkan)
├── tools/
│   └── build_samples.py      # Bangun ulang sampel dari PDF lokal
│
└── src/
    ├── engine.py             # Orkestrasi pipeline pengecekan
    ├── samples.py            # Loader sampel cepat untuk UI
    ├── ui.py                 # Komponen tampilan (kartu ringkasan, daftar perbaikan, tampilan komparasi)
    ├── compare.py            # Logika komparasi antarversi (murni, tanpa Streamlit)
    ├── parser/
    │   └── pdf_parser.py     # Ekstraksi & segmentasi PDF
    ├── checkers/
    │   ├── base_checker.py         # Base class & status
    │   ├── hard_disqualifier.py
    │   ├── identity_checker.py     # Modul 1
    │   ├── format_checker.py       # Modul 2
    │   ├── structure_checker.py    # Modul 3
    │   ├── reference_checker.py    # Modul 4 (pakai dafpus_utils.py)
    │   ├── budget_checker.py       # Modul 5 (pakai rab_utils.py)
    │   ├── attachment_checker.py   # Modul 6
    │   ├── consistency_checker.py  # Modul 7
    │   ├── dafpus_utils.py         # Segmentasi entri (hanging indent) & aturan Harvard
    │   └── rab_utils.py            # Parser rekap RAB, justifikasi, terbilang
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

### Cek satu proposal

1. **Unggah PDF** proposal PKM (maks. 5 MB, harus bisa dibaca teks — bukan scan penuh)
2. *(Opsional)* **Isi judul** persis seperti di SIMBELMAWA/Surat Pernyataan (Panduan 2026: HURUF KAPITAL).
   Kosongkan untuk dideteksi dari Surat Pernyataan.
3. *(Opsional)* **Jenis PKM** — otomatis dari nama file (`..._PKM-KC.pdf`), atau pilih manual
4. Klik **Periksa proposal**
5. Hasil tampil berurutan: ringkasan status & skor → skor per modul → tab **Yang perlu diperbaiki**
   (wajib dulu, lalu cek manual) → **Rincian per modul** → **Laporan teks** (unduh `.txt`)

### Bandingkan versi (v1, v2, v3, …)

Pilih mode **Bandingkan versi**, unggah 2–5 PDF dari proposal yang sama, atur urutan & label
(mis. `v1`, `Revisi dosen`) di tabel, lalu klik **Bandingkan**. Semua versi diperiksa paralel, lalu tampil:

- **Kartu tiap versi** — status, skor, selisih skor dari versi sebelumnya, jumlah temuan
- **Apa yang berubah** — dari versi mana ke versi mana (default: pertama → terakhir), dikelompokkan jadi
  *memburuk/baru muncul*, *masih bermasalah*, *membaik*, *sudah beres*
- **Skor per modul** — tabel skor tiap modul per versi beserta selisihnya
- **Semua pemeriksaan** — matriks status tiap item per versi (filter: berubah / masih bermasalah / semua),
  klik baris untuk melihat rincian tiap versi berdampingan; bisa diunduh `.csv`
- **Detail per versi** — laporan lengkap satu versi, sama seperti mode cek satu proposal

Item dicocokkan antarversi lewat kodenya (`4.3`, `HD-05`, …). Mengganti label atau urutan tidak memeriksa
ulang; mengganti judul/jenis memeriksa ulang versi itu saja.

### 🧪 Sampel cepat

Tanpa upload, halaman utama menyediakan **5 sampel** (3 didanai, 2 tidak didanai, siklus 2025–2026).
Pilih sampel → **Jalankan sampel** → laporan lengkap tampil seperti pengecekan biasa.
Mode **Bandingkan versi** juga punya demo dari sampel yang sama (proposal berbeda, hanya untuk mencoba tampilan).
Isinya adalah hasil *asli* checker pada proposal nyata, dengan nama, NIM, kontak, nama produk, judul,
dan perguruan tinggi **disamarkan**. PDF aslinya tidak disimpan di repo.

Membangun ulang sampel (mis. setelah aturan checker berubah), dari PDF lokal:

```bash
# daftar PDF & nama yang disamarkan — file ini di-gitignore
cp samples/sumber.local.example.json samples/sumber.local.json   # lalu isi path PDF
python tools/build_samples.py samples/sumber.local.json          # → samples/sampel.json
```

Setelah membangun ulang, periksa `samples/sampel.json` sebelum di-commit untuk memastikan tidak ada data pribadi yang lolos.

### Keterbatasan

- PDF yang seluruhnya hasil scan (bukan teks) tidak dapat dianalisis secara penuh
- Isi halaman scan (tanggal tanda tangan, judul di Surat Pernyataan, meterai) tidak dibaca — tanpa OCR;
  yang dicek hanya bahwa halaman bertanda tangan berupa scan/foto halaman penuh
- Pencocokan sitasi ↔ dafpus dan deteksi tema bersifat heuristik; baca rincian temuannya sebelum mengubah naskah
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
