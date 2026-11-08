"""
Bangun sampel cepat (samples/sampel.json) dari PDF proposal nyata.

PDF TIDAK ikut di-commit. Checker dijalankan sungguhan pada tiap PDF, lalu
hasilnya disamarkan: nama mahasiswa/dosen, NIM, NIP/NUPTK/NIDN, email, nomor HP,
nama produk, nama perguruan tinggi, dan nama file. Judul diganti judul samaran
yang mempertahankan ciri format aslinya (kapital/tidak, kata Inggris, akronim)
agar pengecekan judul tetap memperlihatkan perilaku aslinya.

Pakai:
    python tools/build_samples.py samples/sumber.local.json

sumber.local.json (sudah di-gitignore — berisi path & nama asli, JANGAN di-commit):
    [{"id": "A", "pdf": "C:/.../proposal.pdf", "jenis": "KI", "status_asli": "Didanai",
      "siklus": 2026, "judul_samaran": "PRODUK-A: ...",
      "samaran_produk": {"NamaProdukAsli": "Produk-A"}, "samaran_lain": {"Teks asli": "pengganti"}}]
"""

import json
import os
import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
warnings.filterwarnings("ignore")

import config  # noqa: E402
config.GEMINI_API_KEY = ""          # hasil sampel harus deterministik (tanpa Gemini)
import src.engine as engine  # noqa: E402
from src.checkers.consistency_checker import baris_susunan_tim  # noqa: E402
from src.checkers.reference_checker import ReferenceChecker  # noqa: E402
from src.checkers.budget_checker import BudgetChecker, rp  # noqa: E402

engine.GEMINI_API_KEY = ""
engine.MAX_FILE_SIZE_MB = 100

OUT = ROOT / "samples" / "sampel.json"

# Kata umum yang tidak boleh diganti walau muncul di nama orang
KATA_UMUM = {"muhammad", "muhamad", "putra", "putri", "nur", "dwi", "sri", "ayu", "dan", "binti", "bin",
             "abdul", "siti", "dewi", "indah", "sari", "rahma", "ahmad"}
KATA_FORMULIR = {"jenis", "kelamin", "program", "studi", "nim", "tempat", "tanggal", "alamat", "lahir",
                 "nomor", "laki-laki", "perempuan", "email", "e-mail", "telepon", "identitas", "diri",
                 "kegiatan", "status", "tim", "ketua", "anggota", "dosen", "pendamping", "biodata"}
GELAR = re.compile(r',?\s*\b(?:S\.\s?(?:Pd|T|Kom|Si|ST)|M\.\s?(?:T|Pd|Kom|Si|Eng|Sc)|Dr|Ph\.?D|Prof)\b\.?')


def _nama_bersih(raw: str) -> str:
    nama = raw.split("\n")[0]
    nama = GELAR.sub("", nama)
    return re.sub(r'\s+', ' ', nama).strip(" ,.:;")


def kumpulkan_nama(doc, result) -> list[str]:
    tim = [_nama_bersih(n) for n, _ in baris_susunan_tim(doc)]
    nama = list(tim)
    teks = doc.full_text + "\n" + "\n".join(p.text_blocks for p in doc.pages)
    for pola in (r'Nama\s+Lengkap(?:\s*\(dengan\s+gelar\))?\s*:?\s*([A-Z][^\n]{3,80})',
                 r'Nama\s+(?:Ketua\s+Tim|Dosen\s+Pendamping)\s*:\s*([^\n]{3,80})',
                 r'\(([A-Z][A-Za-z.\' ]{3,60}?(?:,\s*S\.[^)]*)?)\)\s*\n\s*(?:NIM|NUPTK|NIP)'):
        for m in re.finditer(pola, teks):
            nama.append(_nama_bersih(m.group(1)))
    # Varian ejaan yang ditemukan Modul 7
    for modul in result["structured_report"]["modul_results"]:
        for item in modul["items"]:
            if item["kode"] == "7.4":
                for c in item.get("catatan", []):
                    nama += re.findall(r"'([^']+)'", c)
                    nama += [v.strip() for v in c.split("juga ditulis:")[-1].split(",")]
    hasil = []
    for n in nama:
        kata = {w.lower() for w in n.split()}
        # Nama satu kata hanya diterima bila berasal dari tabel Susunan Tim
        cukup = len(n.split()) >= 2 or (n in tim and len(n) >= 3)
        if cukup and n not in hasil and not re.search(r'\d', n) and not kata & KATA_FORMULIR:
            hasil.append(n)
    return sorted(hasil, key=len, reverse=True)


def buat_pengganti(doc, result, src: dict, file_samaran: str) -> list[tuple[re.Pattern, str]]:
    rules: list[tuple[re.Pattern, str]] = []
    for asli, ganti in src.get("samaran_produk", {}).items():
        rules.append((re.compile(re.escape(asli), re.I), ganti))
    for asli, ganti in src.get("samaran_lain", {}).items():
        rules.append((re.compile(re.escape(asli), re.I), ganti))
    rules.append((re.compile(re.escape(os.path.basename(src["pdf"])), re.I), file_samaran))
    # Nama perguruan tinggi & singkatannya: isi lewat "samaran_lain" di sumber.local.json

    nama = kumpulkan_nama(doc, result)
    for i, n in enumerate(nama, 1):
        rules.append((re.compile(r'\s+'.join(re.escape(t) for t in n.split()), re.I), f"Nama Samaran {i}"))
    token = {t for n in nama for t in re.findall(r"[A-Za-z'’\-]{4,}", n) if t.lower() not in KATA_UMUM}
    for t in sorted(token, key=len, reverse=True):
        rules.append((re.compile(rf'\b{re.escape(t)}\b', re.I), "Samaran"))

    rules.append((re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+'), "email@disamarkan"))
    rules.append((re.compile(r'(?<![\d.,])\d{6,}(?![\d.,]\d)'), lambda m: "•" * len(m.group(0))))
    return rules


def samarkan(obj, rules):
    if isinstance(obj, str):
        for pat, ganti in rules:
            obj = pat.sub(ganti, obj)
        return obj
    if isinstance(obj, list):
        return [samarkan(x, rules) for x in obj]
    if isinstance(obj, dict):
        return {k: samarkan(v, rules) for k, v in obj.items()}
    return obj


def langkah_proses(doc, structured) -> list[str]:
    """Langkah yang ditampilkan saat 'memproses' sampel — semuanya fakta dari run asli."""
    n = len(doc.pages)
    spans = sum(len(p.font_spans) for p in doc.pages)
    gambar = sum(len(p.images) for p in doc.pages)
    spans_id = f"{spans:,}".replace(",", ".")
    lk = [f"Membuka PDF: {n} halaman", f"Ekstraksi teks, font & tata letak: {spans_id} span teks, {gambar} gambar"]
    if doc.bab1_page and doc.core_pages:
        seg = (f"Segmentasi: Daftar Isi hal. 1–{doc.bab1_page - 1} · bagian inti hal. "
               f"{doc.core_pages[0]}–{doc.core_pages[-1]} ({len(doc.core_pages)} hal.)")
        if doc.lampiran_page:
            seg += f" · lampiran hal. {doc.lampiran_page}–{n}"
        lk.append(seg)
    rc = ReferenceChecker(doc)
    lk.append(f"Daftar Pustaka: {len(rc.entries)} entri"
              f"{' (hanging indent terbaca)' if rc.hanging else ''} · {len(rc.citations)} sitasi di naskah")
    bc = BudgetChecker(doc)
    if bc.just.grand_total:
        lk.append(f"RAB: {len(bc.rekap.kategori)} kategori rekap · {len(bc.just.baris)} baris justifikasi · "
                  f"grand total {rp(bc.just.grand_total)}")
    for m in structured["modul_results"]:
        c = {s: sum(1 for i in m["items"] if i["status"] == s) for s in ("LULUS", "PERINGATAN", "TIDAK_LULUS")}
        lk.append(f"{m['nama']}: {len(m['items'])} item — ✅ {c['LULUS']} · ⚠️ {c['PERINGATAN']} · ❌ {c['TIDAK_LULUS']}")
    return lk


def main(sumber_path: str):
    sumber = json.loads(Path(sumber_path).read_text(encoding="utf-8"))
    sampel = []
    for src in sumber:
        jenis = src["jenis"]
        status = src["status_asli"]
        file_samaran = f"sampel_{src['id']}_PKM-{jenis}_{status.lower().replace(' ', '-')}-{src['siklus']}.pdf"
        print(f"→ {src['id']}: memproses ...", flush=True)
        result = engine.run_checks(src["pdf"], judul_input=src["judul_samaran"], jenis_pkm_input=jenis)
        doc = result["doc"]
        structured, text_report = result["structured_report"], result["text_report"]
        langkah = langkah_proses(doc, structured)
        rules = buat_pengganti(doc, result, src, file_samaran)
        payload = samarkan({
            "id": src["id"],
            "label": f"Sampel {src['id']} · PKM-{jenis} · {status} {src['siklus']}",
            "status_asli": status,
            "siklus": src["siklus"],
            "jenis": jenis,
            "file_name": file_samaran,
            "file_size_kb": round(os.path.getsize(src["pdf"]) / 1024, 1),
            "judul": src["judul_samaran"],
            "catatan_sampel": src.get("catatan", ""),
            "langkah": langkah,
            "result": {"structured_report": structured, "text_report": text_report},
        }, rules)
        payload["result"]["structured_report"]["file_name"] = file_samaran
        sampel.append(payload)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(sampel, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Selesai: {OUT} ({OUT.stat().st_size / 1024:.0f} KB, {len(sampel)} sampel)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "samples" / "sumber.local.json"))
