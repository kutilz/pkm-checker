# Blueprint: Sistem Pengecekan Otomatis Proposal PKM 2026

> Versi: 1.1 | Referensi: Panduan PKM 2026 (Panduan Umum + Panduan Bidang PKM-K s.d. PKM-KC)

---

## 1. Tujuan Sistem

Membangun sebuah program yang mampu menerima input berkas proposal PKM dalam format PDF, lalu secara otomatis mengevaluasi kesesuaiannya dengan **seluruh ketentuan Panduan PKM 2026**. Output sistem berupa laporan terstruktur yang menandai setiap komponen sebagai **LULUS / PERINGATAN / TIDAK LULUS**, dengan keterangan detail tiap poin yang bermasalah.

---

## 2. Arsitektur Umum Program

```
┌─────────────────────────────────────────────────────────┐
│                    INPUT LAYER                          │
│  Upload PDF Proposal → Parser → Ekstraksi Konten        │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               CHECKER ENGINE (6 Modul)                  │
│                                                         │
│  [1] Modul Identitas & Kelengkapan Formal               │
│  [2] Modul Format & Tipografi                           │
│  [3] Modul Struktur Dokumen                             │
│  [4] Modul Konten Isi Utama                             │
│  [5] Modul Anggaran & Keuangan                          │
│  [6] Modul Lampiran                                     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   REPORT GENERATOR                      │
│  Skor per modul → Rekomendasi → Laporan PDF/HTML        │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Teknologi yang Direkomendasikan

| Komponen | Tools |
|---|---|
| PDF Parsing & Text Extraction | `pdfplumber` (tabel + layout-aware) |
| Font & Margin Extraction | `pdfplumber` + `pymupdf` (fitz) |
| Rule-based Text Analysis | `re` (regex) — format Harvard, struktur, kata terlarang |
| AI / Semantic Analysis | **Gemini API** (`google-generativeai`, gratis via Google AI Studio) |
| Similarity Check | Integrasi API Turnitin / iThenticate (opsional) |
| Image Analysis (TTD) | `Pillow` + `OpenCV` (deteksi tanda tangan palsu/crop) |
| Output Report | `Jinja2` + `reportlab` (PDF) atau HTML |
| UI (opsional) | Streamlit / FastAPI |

---

## 4. Alur Pengecekan Berurutan (Pipeline)

Urutan ini mengikuti logika seleksi resmi: **Tahap 1 (Administrasi) dulu, baru Tahap 2 (Substansi)**. Jika gugur di tahap awal, proses bisa dihentikan atau dilanjutkan untuk laporan lengkap.

---

### FASE 0 — Pra-pemrosesan

```
Input PDF
   ↓
[0.1] Deteksi jenis PKM dari nama file / metadata / konten judul
      → Validasi: apakah sesuai format namaketua_namaPT_PKM-[jenis].pdf?
   ↓
[0.2] Ekstraksi seluruh teks, tabel, metadata, gambar, info font & layout
   ↓
[0.3] Segmentasi dokumen: pisahkan bagian Daftar Isi, Bagian Inti, Lampiran
```

**Aturan panduan yang dicek:**
- Nama file: `namaketua_namaPT_PKM-[JENIS].pdf`
- Ukuran file maksimum: 5 MB
- Jenis PKM valid: RE, RSH, K, PM, PI, KC, KI, VGK, GFT, AI

---

### FASE 1 — Elemen yang Langsung Gugurkan (Hard Disqualifiers)

> Jika **salah satu saja** item ini ditemukan → proposal langsung `TIDAK LOLOS Tahap 1`.
> Cek ini harus dijalankan paling awal.

| Kode | Pemeriksaan | Cara Deteksi |
|---|---|---|
| HD-01 | Ada **halaman sampul** (cover page) | Deteksi halaman pertama: apakah berisi judul besar + logo + tidak ada konten bab? |
| HD-02 | Ada **halaman pengesahan** | Cari teks "halaman pengesahan", "lembar pengesahan", tanda tangan kolom ganda di halaman awal |
| HD-03 | Ada **Ringkasan / Abstrak** di proposal (bukan laporan akhir) | Cari heading "Ringkasan", "Abstrak", "Abstract" di bagian awal |
| HD-04 | Tanda tangan biodata/surat pernyataan adalah **hasil crop/tempel** (bukan basah penuh halaman) | Analisis gambar: deteksi TTD yang terisolasi/dipotong tanpa konteks halaman |
| HD-05 | Indeks **similaritas > 25%** | Baca nilai dari lampiran hasil Turnitin/iThenticate |

---

### FASE 2 — Modul 1: Identitas & Kelengkapan Formal

#### [1.1] Identitas Dasar

- [ ] Judul ditulis **huruf kapital** semua
- [ ] Judul dalam **Bahasa Indonesia**
- [ ] Judul **≤ 20 kata** (hitung kata, abaikan kata sambung jika tidak yakin)
- [ ] Judul **tidak menggunakan akronim atau singkatan tidak baku**
- [ ] Bidang PKM yang dipilih sesuai dengan isi kegiatan

#### [1.2] Identitas Tim Pengusul

- [ ] Jumlah anggota: **3–5 mahasiswa aktif**
- [ ] Komposisi: 1 ketua + 2–4 anggota
- [ ] Jenjang pendidikan: **D-3, D-4, atau S-1** (bukan profesi/koas)
- [ ] Nama-nama sesuai format lengkap (cek konsistensi antar bagian: biodata vs surat pernyataan)
- [ ] Semua pengusul berasal dari **satu Perguruan Tinggi yang sama**

#### [1.3] Identitas Dosen Pendamping

- [ ] Dosen pendamping memiliki **NUPTK** (tertera di biodata)
- [ ] Biodata dosen pendamping **lengkap**: identitas, riwayat pendidikan, Tri Dharma PT

#### [1.4] Tanggal dan Kota

- [ ] Terdapat kota, tanggal, bulan, tahun pada surat pernyataan dan biodata
- [ ] Format tanggal konsisten (bukan hanya tahun)

---

### FASE 3 — Modul 2: Format & Tipografi

#### [2.1] Font

- [ ] Seluruh teks menggunakan **Times New Roman ukuran 12**
- [ ] Nomor halaman menggunakan **Times New Roman ukuran 12**
- [ ] Daftar pustaka: Times New Roman 12 cetak normal (bukan bold/italic untuk teks biasa)

> *Cara deteksi: ekstrak info font per blok teks menggunakan `pdfplumber` atau `pymupdf`. Hitung persentase teks yang tidak memenuhi syarat.*

#### [2.2] Spasi dan Rata Teks

- [ ] Jarak baris paragraf: **1,15 spasi** (toleransi ±0.05)
- [ ] Perataan teks: **rata kiri-kanan (justify)**
- [ ] Daftar pustaka: spasi 1,15, justify, **baris kedua dst menjorok ke dalam** (hanging indent)

#### [2.3] Ukuran Kertas dan Margin

- [ ] Kertas: **A4**
- [ ] **Satu kolom**
- [ ] Margin kiri: **4 cm**
- [ ] Margin kanan, atas, bawah: masing-masing **3 cm**

#### [2.4] Penomoran Halaman

- [ ] **Daftar Isi** dan sebelumnya: nomor **romawi kecil (i, ii, iii, ...)** di sudut **kanan bawah**
- [ ] Penomoran `i` dimulai dari halaman Daftar Isi
- [ ] **Bagian Inti dan Lampiran**: nomor **arab (1, 2, 3, ...)** di sudut **kanan atas**
- [ ] Penomoran `1` dimulai dari Bab 1 Pendahuluan

---

### FASE 4 — Modul 3: Struktur Dokumen

#### [3.1] Susunan Dokumen

Cek keberadaan dan urutan bagian-bagian berikut:

```
WAJIB ADA:
  ✓ Daftar Isi
  ✓ Daftar Gambar (jika ada gambar)
  ✓ Daftar Tabel (jika ada tabel)
  ✓ Daftar Lampiran
  ✓ BAB 1. PENDAHULUAN
  ✓ BAB 2. [sesuai bidang PKM]
  ✓ BAB 3. [sesuai bidang PKM]
  ✓ BAB 4. BIAYA DAN JADWAL KEGIATAN
    ✓ 4.1 Anggaran Biaya (tabel RAB)
    ✓ 4.2 Jadwal Kegiatan (bar chart)
  ✓ DAFTAR PUSTAKA
  ✓ LAMPIRAN (wajib sesuai bidang)

TIDAK BOLEH ADA (di proposal):
  ✗ Halaman Sampul
  ✗ Halaman Pengesahan
  ✗ Ringkasan / Abstrak
```

#### [3.2] Batas Halaman Bagian Inti

- [ ] Bagian inti (Bab 1 s.d. Daftar Pustaka): **maksimum 10 halaman**

#### [3.3] Perbedaan Struktur per Bidang PKM

Program harus memuat mapping struktur bab sesuai jenis PKM:

| Bidang | BAB 2 | BAB 3 | BAB 4 |
|---|---|---|---|
| PKM-RE / PKM-RSH | Tinjauan Pustaka | Metode Penelitian | Biaya & Jadwal |
| PKM-K | Gambaran Umum Rencana Usaha | Metode Pelaksanaan | Biaya & Jadwal |
| PKM-PM | Gambaran Umum Mitra | Metode Pelaksanaan | Biaya & Jadwal |
| PKM-PI | Gambaran Umum Mitra Usaha | Metode Pelaksanaan | Biaya & Jadwal |
| PKM-KC | Tinjauan Pustaka | Tahap Pelaksanaan | Biaya & Jadwal |
| PKM-KI | Tinjauan Pustaka | Metode Pelaksanaan | Biaya & Jadwal |
| PKM-VGK | Gambaran Umum Gagasan | Metode Pelaksanaan | Biaya & Jadwal |
| PKM-GFT | Pendahuluan | Gagasan | Kesimpulan (khusus) |
| PKM-AI | (format artikel ilmiah) | — | — |

#### [3.4] Format Daftar Pustaka (Rule-Based)

> Semua pengecekan di sini murni berbasis regex dan parsing teks — tidak butuh AI.

**[3.4.1] Keberadaan dan Posisi**
- [ ] Heading "DAFTAR PUSTAKA" ada dan posisinya setelah bab terakhir, sebelum LAMPIRAN
- [ ] Tidak kosong (minimal ada 1 entri)

**[3.4.2] Format Umum Harvard**

Setiap entri dicek dengan regex untuk pola dasar Harvard:
- [ ] Setiap entri diawali dengan `NamaBlk, Inisial. (Tahun)` atau nama lembaga
- [ ] Tahun ditulis dalam tanda kurung: `(YYYY)` atau `(n.d.)`
- [ ] Penulis yang sama di tahun yang sama dibedakan dengan suffix `a`, `b`, `c` — contoh: `(2020a)`
- [ ] **Tidak ada `"et al."` atau `"dkk"` di daftar pustaka** (semua penulis harus disebutkan)
- [ ] Entri diurutkan **alfabetis** berdasarkan nama belakang penulis pertama

**[3.4.3] Format per Tipe Sumber**

| Tipe | Elemen Wajib yang Dicek (regex) |
|---|---|
| Buku | Judul *cetak miring*, kota: penerbit |
| Jurnal | Judul artikel dalam `'tanda kutip'`, nama jurnal *miring*, volume(edisi), pp. |
| Prosiding | Judul `'kutip'`, nama prosiding *miring*, lokasi+tanggal, pp. |
| Skripsi/Tesis | Judul *miring*, pernyataan gelar (Thesis/Dissertation), nama institusi |
| Website | `Tersedia di:` + URL *miring* + `(Diakses DD Bulan YYYY)` |
| Media Sosial | Tag platform `[Facebook]` / `[Instagram]` / `[Twitter atau X]`, tanggal posting, URL |
| Undang-Undang | Nama penerbit, judul *miring*, keterangan penerbitan |

**[3.4.4] Aturan Tambahan**
- [ ] URL/alamat internet ditulis **huruf miring** (italic)
- [ ] Tanggal akses website menggunakan format `(Diakses DD Bulan YYYY)` — bukan hanya tahun
- [ ] Baris kedua dst tiap entri **menjorok ke dalam** (hanging indent) — dicek via layout PDF
- [ ] Spasi antar-entri konsisten

> *Cara deteksi: parsing teks daftar pustaka dengan `re.findall()`, cocokkan pola per baris. Italic URL dideteksi via properti font style dari `pdfplumber`/`pymupdf` per span teks.*

---

### FASE 5 — Modul 4: Konten Isi Utama

#### [4.1] Judul vs Tema PKM (Gemini API)

- [ ] Judul relevan dengan salah satu dari **10 tema PKM Tematik 2026**:
  1. Kemandirian Pangan, Energi, dan Air
  2. Kesehatan dan Gizi Masyarakat
  3. Pencegahan dan Pemberantasan Korupsi
  4. Pemberantasan Kemiskinan
  5. Pencegahan dan Pemberantasan Narkoba
  6. Penguatan Pendidikan, Sains, dan Teknologi
  7. Penguatan Kesetaraan Gender dan Perlindungan Hak Perempuan, Anak, Disabilitas
  8. Pelestarian Lingkungan dan Mitigasi Bencana
  9. Pemerataan Ekonomi, Penguatan UMKM, dan Pembangunan IKN
  10. Pelestarian Seni Budaya dan Peningkatan Ekonomi Kreatif

> *Cara deteksi: kirim judul + paragraf pertama Bab 1 ke Gemini API. Minta Gemini menentukan tema yang paling relevan dan confidence score-nya. Jika confidence rendah, tandai PERINGATAN.*

**Contoh prompt ke Gemini:**
```
Judul proposal: "[judul]"
Latar belakang: "[paragraf_pertama_bab1]"

Dari 10 tema PKM 2026 berikut: [daftar_tema]
Tentukan tema mana yang paling relevan dan berikan confidence score 0-100.
Jawab dalam JSON: {"tema": "...", "nomor_tema": N, "confidence": 0-100, "alasan": "..."}
```

#### [4.2] Kelengkapan Isi Bab (Rule-Based + Gemini API)

Pengecekan dibagi dua lapisan:

**Lapisan 1 — Rule-based (regex/keyword):** cek keberadaan elemen wajib
- [ ] Bab 1: ada kata kunci "tujuan", "manfaat", "target luaran" atau "luaran yang ditargetkan"
- [ ] Bab 4.2: ada gambar/tabel yang mengandung pola jadwal / bar chart (via `pdfplumber` gambar atau tabel)
- [ ] Untuk PKM-K: ada kata kunci "peluang pasar", "analisis pasar", atau "segmen pasar"
- [ ] Untuk PKM-KC: ada kata kunci "sumber inspirasi" atau "fase" di Bab 1

**Lapisan 2 — Gemini API:** cek kecukupan substansi (jika lapisan 1 lolos)
- [ ] Latar belakang memadai dan terhubung dengan tema PKM yang dipilih
- [ ] Tujuan dan manfaat dinyatakan secara spesifik (bukan generik)
- [ ] Untuk PKM-K: analisis pasar disertai data/survei, bukan asumsi kosong

> *Kirim isi tiap bab ke Gemini dengan instruksi spesifik per bidang PKM. Gunakan output JSON berisi checklist iya/tidak + catatan.*

#### [4.3] Jadwal Kegiatan (Rule-Based)

- [ ] Disusun dalam bentuk **bar chart** (bukan tabel biasa atau narasi)
- [ ] Durasi total: **3–4 bulan**
- [ ] Setiap kegiatan memiliki penanggung jawab

#### [4.4] Konsistensi Sitasi ↔ Daftar Pustaka (Gemini API)

> Pengecekan format daftar pustaka (Harvard style, urutan, italic, dll.) sudah dilakukan di **[3.4]**. Bagian ini hanya menangani **cross-reference** antara sitasi dalam teks dan entri di daftar pustaka — tugas yang membutuhkan pemahaman konteks sehingga dibantu Gemini API.

- [ ] Setiap sitasi `(NamaBlk, Tahun)` atau `NamaBlk (Tahun)` yang muncul di teks **ada pasangannya** di daftar pustaka
- [ ] Setiap entri di daftar pustaka **benar-benar dikutip** di suatu tempat dalam teks (tidak ada entri "fiktif" yang tidak dirujuk)
- [ ] Tidak ada inkonsistensi nama/tahun antara sitasi di teks dan entri di daftar pustaka

> *Cara deteksi: ekstrak semua pola sitasi dari teks (`re`), ekstrak semua entri daftar pustaka, lalu kirim keduanya ke **Gemini API** untuk mencocokkan dan mendeteksi yang tidak berpasangan. Gemini juga bisa menangani variasi penulisan nama (misalnya singkatan vs nama lengkap, karakter khusus) yang sulit dicocokkan dengan regex murni.*

**Contoh prompt ke Gemini:**
```
Berikut daftar sitasi yang ditemukan di dalam teks proposal:
[sitasi_list]

Berikut entri daftar pustaka:
[dafpus_list]

Tugas:
1. Temukan sitasi di teks yang tidak memiliki entri di daftar pustaka
2. Temukan entri di daftar pustaka yang tidak disitasi di teks
3. Temukan inkonsistensi nama/tahun antara keduanya

Jawab dalam format JSON: {"tidak_ada_di_dafpus": [...], "tidak_disitasi": [...], "inkonsistensi": [...]}
```

#### [4.5] Surat Pernyataan Ketua

- [ ] Memuat pernyataan bahwa karya **asli dan belum pernah dibiayai**
- [ ] Memuat pernyataan kepatuhan penggunaan **AI sesuai Panduan GenAI**
- [ ] Menggunakan **materai Rp10.000**
- [ ] Tanda tangan basah (bukan digital/crop)

---

### FASE 6 — Modul 5: Anggaran & Keuangan

#### [6.1] Rentang Dana Total

- [ ] Dana dari Belmawa: **Rp 6.000.000 – Rp 8.000.000**
- [ ] Dana PT (wajib): maksimum **Rp 2.000.000** (tunai/barang)
- [ ] Dana instansi lain (opsional): maksimum **Rp 1.000.000**

#### [6.2] Komposisi Penggunaan Dana

- [ ] Operasional minimum **80%** dari total dana
- [ ] Administrasi maksimum **20%** dari total dana

#### [6.3] Batas per Kategori Pengeluaran

| Kategori | Batas Maksimum |
|---|---|
| Bahan habis pakai | 60% dari total dana |
| Sewa dan jasa | 15% dari total dana |
| Transportasi lokal | 30% dari total dana |
| Lain-lain (termasuk Ads medsos) | 15% dari total dana |
| Ads media sosial | Maks Rp 500.000 total |

#### [6.4] Item yang DILARANG dalam RAB

- [ ] Honorarium/konsumsi/hadiah untuk tim, dosen, narasumber
- [ ] Sewa PC/laptop/printer/ponsel/kamera/aula
- [ ] Pembelian alat/bahan **> Rp 1.000.000 per item**
- [ ] Pembelian storage (flashdisk, harddisk)
- [ ] Kuota internet **> Rp 100.000/bulan/tim**
- [ ] Sewa lisensi **> 6 bulan**
- [ ] Penggandaan/penjilidan laporan (kecuali PTS atau PTN yang mewajibkan)
- [ ] Biaya seminar atau publikasi jurnal

#### [6.5] Validasi Perhitungan RAB

- [ ] Hasil perkalian satuan × volume = total per item (cek masing-masing baris)
- [ ] Subtotal per kategori benar
- [ ] Grand Total = jumlah semua subtotal
- [ ] Rekap sumber dana (Belmawa + PT + Instansi Lain) = Grand Total

> *Kesalahan perhitungan dapat mempengaruhi penilaian (sesuai catatan panduan)*

---

### FASE 7 — Modul 6: Lampiran

#### [7.1] Lampiran Wajib (berlaku semua bidang)

| No | Lampiran | Hal yang Dicek |
|---|---|---|
| L-1 | Biodata Ketua & Anggota | Format lengkap (identitas, kegiatan, penghargaan), TT basah, NIM tertera |
| L-2 | Biodata Dosen Pendamping | Format lengkap (identitas, pendidikan, Tri Dharma), NUPTK tertera, TT basah |
| L-3 | Justifikasi Anggaran Kegiatan | Format sesuai template (4 kategori), perhitungan benar |
| L-4 | Susunan Tim & Pembagian Tugas | Nama/NIM/prodi/bidang ilmu/jam per minggu/uraian tugas terisi |
| L-5 | Surat Pernyataan Ketua | Materai Rp10.000, TT basah, konten lengkap |
| L-6 | Hasil Uji Similaritas | Indeks similaritas **≤ 25%**, mencakup bagian inti (Pendahuluan s.d. Daftar Pustaka) |

#### [7.2] Lampiran Tambahan per Bidang

| Bidang | Lampiran Tambahan |
|---|---|
| PKM-KC | Gambaran Teknologi yang akan Dikembangkan |
| PKM-PI | Surat Pernyataan Mitra / Gambaran Teknologi |
| PKM-PM | Surat Pernyataan Mitra |
| PKM-K | (tidak ada tambahan khusus) |

#### [7.3] Validasi Biodata

- [ ] Satu halaman penuh dengan tanda tangan **terlihat dalam konteks halaman** (bukan crop)
- [ ] Kolom Kegiatan Kemahasiswaan dan Penghargaan terisi (boleh kosong/diisi "–")
- [ ] Nama di biodata = nama di surat pernyataan = nama di isian kelengkapan

---

## 5. Logika Skoring dan Penilaian

### Kategori Hasil per Item

```
✅ LULUS      → Sesuai ketentuan panduan
⚠️  PERINGATAN → Berpotensi bermasalah, perlu dicek manual
❌ TIDAK LULUS → Melanggar ketentuan (bisa menggugurkan)
```

### Bobot Modul

| Modul | Bobot | Keterangan |
|---|---|---|
| Fase 1: Hard Disqualifiers | — | Langsung gugur jika ada |
| Modul 1: Identitas & Kelengkapan | 20% | |
| Modul 2: Format & Tipografi | 15% | |
| Modul 3: Struktur Dokumen | 20% | |
| Modul 4: Konten Isi Utama | 20% | |
| Modul 5: Anggaran & Keuangan | 15% | |
| Modul 6: Lampiran | 10% | |

### Kategori Status Akhir

```
PERFECT (100%)         → Semua lulus, siap disubmit
LAYAK (≥85%)           → Minor warnings, perlu perbaikan kecil
PERLU PERBAIKAN (≥60%) → Ada beberapa ketidaksesuaian signifikan
TIDAK LOLOS (<60%)     → Banyak pelanggaran serius
GUGUR LANGSUNG         → Salah satu Hard Disqualifier terpenuhi
```

---

## 6. Format Output Laporan

```markdown
## LAPORAN PENGECEKAN PROPOSAL PKM 2026
Nama File    : budi_universitas_PKM-K.pdf
Jenis PKM    : PKM-K
Nama Ketua   : [terdeteksi otomatis]
Tanggal Cek  : [timestamp]

### STATUS KESELURUHAN: ⚠️ PERLU PERBAIKAN (72%)

---
### [FASE 1] HARD DISQUALIFIERS
✅ Tidak ada halaman sampul
✅ Tidak ada halaman pengesahan
✅ Tidak ada ringkasan/abstrak
⚠️  Tanda tangan biodata terdeteksi crop — perlu cek manual
✅ Similaritas: 18% (≤25%)

### [MODUL 1] IDENTITAS & KELENGKAPAN FORMAL
✅ Judul ≤ 20 kata: 15 kata
✅ Judul huruf kapital
❌ Judul mengandung akronim tidak baku: "IoT" pada kata ke-7
✅ Jumlah anggota: 4 mahasiswa (1 ketua + 3 anggota)
...

### [MODUL 2] FORMAT & TIPOGRAFI
✅ Font Times New Roman 12 (98% konten sesuai)
❌ Spasi: terdeteksi 1.5 spasi pada halaman 3-5 (bukan 1.15)
✅ Margin: kiri 4cm, kanan/atas/bawah 3cm
...

### [MODUL 5] ANGGARAN & KEUANGAN
❌ Bahan habis pakai: 67% (melebihi batas 60%)
✅ Tidak ada item terlarang
❌ Kesalahan perhitungan: Baris no. 4 subtotal bahan tidak sesuai
...

### REKOMENDASI PRIORITAS:
1. [WAJIB] Perbaiki tanda tangan biodata — gunakan TTD basah halaman penuh
2. [WAJIB] Hapus akronim "IoT" atau ganti dengan kepanjangan
3. [WAJIB] Perbaiki spasi teks pada halaman 3-5 menjadi 1.15
4. [WAJIB] Realokasi bahan habis pakai agar ≤ 60%
5. [WAJIB] Periksa dan perbaiki perhitungan RAB baris no. 4
```

---

## 7. Pertimbangan Implementasi

### 7.1 Deteksi Font & Layout
Gunakan `pdfplumber` yang memungkinkan akses ke properti karakter per kata. Library `pymupdf` (fitz) lebih powerful untuk ekstraksi font-level detail.

### 7.2 Deteksi Tanda Tangan Crop
Gunakan OpenCV untuk mendeteksi gambar TTD yang berdiri sendiri (isolated bounding box kecil). TTD yang sah biasanya muncul di bagian bawah halaman dan menempati area yang proporsional dengan halaman.

### 7.3 Pengecekan Daftar Pustaka Harvard (Rule-Based)
Gunakan regex patterns untuk mendeteksi elemen Harvard style di Modul 3 [3.4]:
```python
import re

# Pola dasar entri Harvard
HARVARD_ENTRY = re.compile(
    r'^([A-Z][a-záéíóúàèìòùñçãõ\'\-]+,\s[A-Z]\..*?'   # Nama, Inisial.
    r'|\w[\w\s]+\s)'                                      # atau nama lembaga
    r'\((\d{4}[a-z]?|n\.d\.)\)'                          # (Tahun) atau (n.d.)
)

# Cek "et al." atau "dkk" terlarang
NO_ETAL = re.compile(r'\bet\.?\s*al\.?\b|\bdkk\.?\b', re.IGNORECASE)

# Cek URL italic: perlu info font dari pymupdf
# Cek (Diakses DD Bulan YYYY)
ACCESSED = re.compile(r'\(Diakses\s+\d{1,2}\s+\w+\s+\d{4}\)')
```

### 7.4 Cross-Reference Sitasi via Gemini API
Untuk mencocokkan sitasi di teks dengan entri daftar pustaka (Modul 4 [4.4]):
```python
import google.generativeai as genai

genai.configure(api_key="YOUR_GEMINI_API_KEY")  # gratis via Google AI Studio
model = genai.GenerativeModel("gemini-1.5-flash")

def check_citation_consistency(sitasi_list, dafpus_list):
    prompt = f"""
    Sitasi dalam teks: {sitasi_list}
    Entri daftar pustaka: {dafpus_list}
    
    Temukan: (1) sitasi tidak ada di dafpus, (2) dafpus tidak disitasi, (3) inkonsistensi nama/tahun.
    Jawab HANYA dalam JSON: {{"tidak_ada_di_dafpus": [], "tidak_disitasi": [], "inkonsistensi": []}}
    """
    response = model.generate_content(prompt)
    return json.loads(response.text)
```

### 7.5 Pengecekan Tema Tematik via Gemini API
```python
TEMA_PKM = [
    "Kemandirian Pangan, Energi, dan Air",
    "Kesehatan dan Gizi Masyarakat",
    # ... dst
]

def check_tema(judul, latar_belakang):
    prompt = f"""
    Judul: "{judul}"
    Latar belakang (penggalan): "{latar_belakang[:500]}"
    
    Dari tema PKM 2026: {TEMA_PKM}
    Tentukan tema paling relevan dan confidence 0-100.
    Jawab HANYA dalam JSON: {{"tema": "...", "nomor": N, "confidence": 0-100, "alasan": "..."}}
    """
    response = model.generate_content(prompt)
    return json.loads(response.text)
```

> **Catatan biaya:** Gemini 1.5 Flash gratis hingga 15 RPM dan 1 juta token/hari via Google AI Studio. Cukup untuk kebutuhan pengecekan proposal tanpa biaya.

### 7.6 Validasi Perhitungan RAB
Ekstrak tabel anggaran dengan `pdfplumber.extract_tables()`, parse angka, validasi operasi aritmatika per baris dan per subtotal.

### 7.7 Seleksi Jenis PKM Otomatis
Deteksi dari:
1. Nama file (`PKM-K`, `PKM-KC`, dst.)
2. Heading utama dalam teks
3. Isian pada "Bidang PKM" di isian kelengkapan (jika ada dalam dokumen)

---

## 8. Rencana Pengembangan Bertahap

| Fase | Fitur | Prioritas |
|---|---|---|
| MVP | Hard disqualifiers + format dasar + struktur dokumen + [3.4] daftar pustaka rule-based | Tinggi |
| v1.0 | + Validasi RAB lengkap + Lampiran checker | Tinggi |
| v1.1 | + Font/margin/spasi extractor (`pymupdf`) | Sedang |
| v1.2 | + Gemini API: cross-reference sitasi ↔ daftar pustaka [4.4] | Sedang |
| v2.0 | + Gemini API: pengecekan tema tematik [4.1] + kelengkapan substansi bab [4.2] | Rendah |
| v2.1 | + Deteksi TTD crop (OpenCV) | Rendah |
| v3.0 | + Dashboard web + batch processing multi-proposal | Opsional |

---

## 9. Referensi Aturan Sumber

Semua aturan dalam blueprint ini bersumber dari:

- **Buku Panduan Umum PKM 2026** — hal. 1–35 (Kriteria, Tahapan, Penilaian, Lampiran Format)
- **Panduan PKM-K 2026** — hal. 1–35 (Format, Sistematika, RAB, Lampiran)
- **Panduan PKM-KC 2026** — hal. 1–26 (Format, Sistematika, RAB, Lampiran)
- Pola yang ditemukan berlaku konsisten di seluruh bidang PKM lainnya

> **Catatan:** Untuk bidang PKM-RE, RSH, PM, PI, KI, VGK, GFT, dan AI — lakukan ekstraksi ulang dari halaman panduan masing-masing bidang untuk mengkonfirmasi detail struktur bab dan lampiran tambahan, karena panduan ini memiliki 11 buku terpisah.
