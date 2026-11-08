"""
Streamlit UI — PKM 2026 Proposal Checker.
Jalankan: streamlit run app.py

Dua mode:
- Cek satu proposal  : unggah 1 PDF -> daftar perbaikan + rincian per modul.
- Bandingkan versi   : unggah 2–5 versi (v1, v2, ...) -> apa yang beres, memburuk, dan masih tersisa.
"""

import hashlib
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

from config import JENIS_PKM_VALID, MAX_FILE_SIZE_MB
from src.engine import FileSizeError, run_checks
from src.parser.pdf_parser import detect_jenis_pkm
from src.samples import load_samples, with_current_timestamp
from src.ui import inject_css, legenda_html, render_banding, render_hasil

st.set_page_config(page_title="PKM Checker 2026", page_icon="📋", layout="wide")

MODES = {"tunggal": "Cek satu proposal", "banding": "Bandingkan versi"}
MAX_VERSI = 5
CACHE_MAX = 12          # hasil per sesi yang disimpan (supaya ganti label/urutan tidak memeriksa ulang)
WORKER_MAX = 3          # paralel antar-file; ekstraksi PDF tetap serial, panggilan Gemini yang tumpang tindih
OTOMATIS = "Otomatis"


# ─── Menjalankan checker ───────────────────────────────────────────────────────

def _kunci(data: bytes, judul, jenis) -> str:
    return f"{hashlib.sha1(data).hexdigest()}|{judul or ''}|{jenis or ''}"


def _hash_dari_kunci(kunci: str) -> str:
    return kunci.split("|", 1)[0]


def _nama_aman(file_name: str) -> str:
    """Nama file asli dipertahankan karena jenis PKM dideteksi dari nama file."""
    nama = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", os.path.basename(file_name or "")).strip(" .")
    return nama if nama.lower().endswith(".pdf") else (nama or "proposal") + ".pdf"


def _periksa(data: bytes, file_name: str, judul, jenis) -> dict:
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, _nama_aman(file_name))
        with open(path, "wb") as f:
            f.write(data)
        r = run_checks(path, judul_input=judul, jenis_pkm_input=jenis)
    return {"structured": r["structured_report"], "text_report": r["text_report"]}


def _cache() -> dict:
    return st.session_state.setdefault("_cache_hasil", {})


def _simpan(kunci: str, hasil: dict):
    c = _cache()
    c.pop(kunci, None)
    c[kunci] = hasil
    while len(c) > CACHE_MAX:
        c.pop(next(iter(c)))


def _pesan_error(e: Exception) -> str:
    if isinstance(e, FileSizeError):
        return str(e)
    return f"Gagal memproses PDF: {e}. Pastikan PDF berisi teks (bukan hasil scan gambar)."


# ─── Sampel ────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_samples() -> list[dict]:
    return load_samples()


# ─── Halaman ───────────────────────────────────────────────────────────────────

def _sidebar():
    with st.sidebar:
        st.markdown("### Cara membaca hasil")
        st.html(f'<div class="pk">{legenda_html()}</div>')
        st.markdown("**Skor administrasi (0–100)**")
        st.caption(
            "Rata-rata berbobot 7 modul. Tiap pemeriksaan: sesuai = 1, cek manual = ½, wajib diperbaiki = 0. "
            "Satu saja item Hard Disqualifier gagal, proposal langsung gugur berapa pun skornya."
        )
        st.caption("Layak: skor ≥85 tanpa item wajib · Perlu perbaikan: masih ada item wajib · "
                   "Tidak lolos: skor <60.")
        with st.expander("Apa saja yang dicek"):
            st.markdown(
                "- **Hard Disqualifier**: sampul, pengesahan, abstrak, similaritas\n"
                "- **Identitas**: judul kapital ≤20 kata, anggota, NUPTK\n"
                "- **Format**: Times New Roman 12, spasi 1,15, A4, margin, nomor halaman\n"
                "- **Struktur**: daftar isi, judul BAB per bidang, ≤10 halaman inti\n"
                "- **Daftar pustaka**: Harvard 2026, ketat sampai tanda baca\n"
                "- **Anggaran**: sumber dana, komposisi, item terlarang, aritmetika\n"
                "- **Lampiran**: lampiran umum & khusus bidang, tanda tangan\n"
                "- **Tema & konsistensi**: 10 tema 2026, NIM, ejaan nama"
            )
        with st.expander("Batasan"):
            st.markdown(
                f"- Ukuran file maks. {MAX_FILE_SIZE_MB} MB\n"
                "- PDF harus berisi teks (bukan scan gambar)\n"
                "- Isi halaman scan (tanggal TTD, meterai) tidak dibaca\n"
                "- Hanya administrasi Tahap 1, bukan substansi"
            )
        st.caption("Referensi: Panduan PKM 2026")


def _jaga_mode():
    """segmented_control bisa di-unselect; kembalikan ke mode terakhir supaya selalu ada yang aktif."""
    if st.session_state.get("mode") is None:
        st.session_state["mode"] = st.session_state.get("_mode_terakhir", "tunggal")
    st.session_state["_mode_terakhir"] = st.session_state["mode"]


def main():
    inject_css()
    _sidebar()

    st.title("PKM Checker 2026")
    st.markdown("Cek administrasi proposal PKM terhadap **Panduan PKM 2026** sebelum diunggah ke SIMBELMAWA.")

    st.session_state.setdefault("mode", "tunggal")
    mode = st.segmented_control("Mode", list(MODES), format_func=MODES.get, key="mode",
                                on_change=_jaga_mode, label_visibility="collapsed") or "tunggal"
    if mode == "tunggal":
        st.caption("Unggah satu PDF dan dapatkan daftar yang perlu diperbaiki.")
        _mode_tunggal()
    else:
        st.caption("Unggah 2–5 versi dari proposal yang sama (mis. v1, v2, v3) untuk melihat "
                   "apa yang sudah beres, apa yang memburuk, dan apa yang masih tersisa.")
        _mode_banding()


# ─── Mode: cek satu proposal ───────────────────────────────────────────────────

def _format_jenis(det):
    def f(j):
        if j is None:
            return f"{OTOMATIS} (PKM-{det})" if det else f"{OTOMATIS} (tidak terdeteksi)"
        return f"PKM-{j}"
    return f


def _mode_tunggal():
    up = st.file_uploader(
        "PDF proposal", type=["pdf"], key="up_tunggal",
        help=f"Maks. {MAX_FILE_SIZE_MB} MB. Nama file sesuai panduan: namaketua_namaPT_PKM-JENIS.pdf "
             "(jenis PKM dideteksi dari nama file).",
    )
    if up is None:
        st.session_state.pop("hasil_tunggal", None)
        _contoh_tunggal()
        return

    st.session_state.pop("sampel_aktif", None)
    data = up.getvalue()
    det = detect_jenis_pkm(up.name)

    with st.container(border=True):
        st.markdown("**Data pendukung** · opsional, tapi membuat hasil lebih akurat")
        c1, c2 = st.columns([3, 1])
        judul = c1.text_area(
            "Judul proposal",
            key="judul_tunggal", height=80,
            placeholder="Kosongkan untuk dideteksi dari Surat Pernyataan",
            help="Salin persis seperti di SIMBELMAWA / Surat Pernyataan, jangan ubah kapitalisasinya, "
                 "supaya aturan judul HURUF KAPITAL ≤20 kata bisa dinilai.",
        )
        jenis = c2.selectbox("Jenis PKM", [None] + JENIS_PKM_VALID, format_func=_format_jenis(det),
                             key="jenis_tunggal")
        if det is None and jenis is None:
            c2.caption(":orange[Jenis tidak terdeteksi dari nama file. Pilih manual supaya struktur BAB "
                       "dan lampiran khusus dicek sesuai bidang.]")
        mulai = st.button("Periksa proposal", type="primary", icon=":material/search:", width="stretch")

    judul = judul.strip() or None
    kunci = _kunci(data, judul, jenis)

    if mulai:
        if kunci not in _cache():
            with st.spinner("Memeriksa proposal… biasanya 10–40 detik."):
                try:
                    _simpan(kunci, _periksa(data, up.name, judul, jenis))
                except Exception as e:  # noqa: BLE001 — tampilkan ke pengguna, jangan crash
                    st.error(_pesan_error(e))
                    with st.expander("Detail teknis"):
                        st.exception(e)
                    return
        st.session_state["hasil_tunggal"] = kunci

    aktif = st.session_state.get("hasil_tunggal")
    if not aktif:
        return
    if _hash_dari_kunci(aktif) != _hash_dari_kunci(kunci) or aktif not in _cache():
        st.session_state.pop("hasil_tunggal", None)   # file diganti
        return
    if aktif != kunci:
        st.info("Judul atau jenis PKM diubah. Klik **Periksa proposal** lagi untuk memperbarui hasil.")
    hasil = _cache()[aktif]
    st.write("")
    render_hasil(hasil["structured"], hasil["text_report"], key="tunggal")


def _contoh_tunggal():
    samples = _load_samples()
    if not samples:
        return
    st.write("")
    with st.container(border=True):
        st.markdown("#### Belum punya file? Coba sampel")
        didanai = sum(s["status_asli"] == "Didanai" for s in samples)
        st.caption(f"{len(samples)} proposal PKM nyata ({didanai} didanai, {len(samples) - didanai} tidak). "
                   "Nama, NIM, kontak, nama produk, judul, dan perguruan tinggi disamarkan.")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        idx = c1.selectbox("Pilih sampel", range(len(samples)), format_func=lambda i: samples[i]["label"],
                           key="pilih_sampel")
        if c2.button("Jalankan sampel", type="primary", icon=":material/play_arrow:", width="stretch"):
            st.session_state["sampel_aktif"] = samples[idx]["id"]
            st.session_state["sampel_animasi"] = True
        if samples[idx].get("catatan_sampel"):
            st.caption(samples[idx]["catatan_sampel"])

    aktif = next((s for s in samples if s["id"] == st.session_state.get("sampel_aktif")), None)
    if aktif:
        _jalankan_sampel(aktif, animate=st.session_state.pop("sampel_animasi", False))


def _jalankan_sampel(sample: dict, animate: bool):
    st.write("")
    langkah = sample.get("langkah", [])
    if animate and langkah:
        with st.status("Memeriksa proposal…", expanded=True) as status:
            bar = st.progress(0.0)
            for i, step in enumerate(langkah, 1):
                time.sleep(0.45 if i <= 5 else 0.2)
                st.write(f"• {step}")
                bar.progress(i / len(langkah))
            status.update(label="Pemeriksaan selesai", state="complete", expanded=False)

    st.info(f"**{sample['label']}**: ini hasil asli checker pada proposal nyata. Status sebenarnya: "
            f"**{sample['status_asli']} (PKM {sample['siklus']})**. Bandingkan dengan temuan di bawah.",
            icon=":material/science:")
    hasil = with_current_timestamp(sample["result"])
    render_hasil(hasil["structured_report"], hasil["text_report"], key=f"sampel_{sample['id']}")


# ─── Mode: bandingkan versi ────────────────────────────────────────────────────

def _teks(x) -> str:
    return "" if x is None or pd.isna(x) else str(x).strip()


def _konfigurasi_versi(ups) -> tuple[str, list[dict]]:
    """Tabel urutan/label/judul/jenis per file. Return (id set file, daftar versi terurut)."""
    files = [(u.name, u.getvalue()) for u in ups]
    hashes = [hashlib.sha1(d).hexdigest() for _, d in files]
    set_id = hashlib.sha1("".join(hashes).encode()).hexdigest()[:12]

    jenis_opsi = [OTOMATIS] + [f"PKM-{j}" for j in JENIS_PKM_VALID]
    df = pd.DataFrame({
        "Urutan": list(range(1, len(files) + 1)),
        "Label": [f"v{i}" for i in range(1, len(files) + 1)],
        "File": [n for n, _ in files],
        "Judul (opsional)": [""] * len(files),
        "Jenis PKM": [f"PKM-{detect_jenis_pkm(n)}" if detect_jenis_pkm(n) else OTOMATIS for n, _ in files],
    })
    st.markdown("**Atur urutan dan label**")
    st.caption("Urutan awal mengikuti urutan unggah, versi paling lama di atas. Klik sel untuk mengubah. "
               "Judul boleh dikosongkan (dideteksi dari Surat Pernyataan).")
    edited = st.data_editor(
        df, key=f"editor_{set_id}", hide_index=True, num_rows="fixed", width="stretch",
        column_config={
            "Urutan": st.column_config.NumberColumn(min_value=1, max_value=len(files), step=1, width="small",
                                                    help="1 = versi paling lama"),
            "Label": st.column_config.TextColumn(max_chars=24, width="small", help="Mis. v1, Revisi dosen"),
            "File": st.column_config.TextColumn(disabled=True, width="medium"),
            "Judul (opsional)": st.column_config.TextColumn(width="medium"),
            "Jenis PKM": st.column_config.SelectboxColumn(options=jenis_opsi, width="small"),
        },
    )

    versi = []
    for i, row in edited.reset_index(drop=True).iterrows():
        urut = row["Urutan"]
        jenis_txt = _teks(row["Jenis PKM"])
        judul = _teks(row["Judul (opsional)"]) or None
        jenis = jenis_txt.replace("PKM-", "") if jenis_txt.startswith("PKM-") else None
        name, data = files[i]
        versi.append({
            "i": i, "urut": i + 1 if pd.isna(urut) else int(urut),
            "label": _teks(row["Label"]) or f"v{i + 1}",
            "file_name": name, "data": data, "judul": judul, "jenis": jenis,
            "kunci": _kunci(data, judul, jenis),
        })
    versi.sort(key=lambda v: (v["urut"], v["i"]))

    dipakai: dict[str, int] = {}
    for v in versi:
        n = dipakai.get(v["label"], 0)
        dipakai[v["label"]] = n + 1
        if n:
            v["label"] = f"{v['label']} ({n + 1})"
    return set_id, versi


def _periksa_banyak(versi: list[dict]) -> bool:
    """Periksa versi yang belum ada di cache, paralel. Return True kalau semua berhasil."""
    unik = {v["kunci"]: v for v in versi if v["kunci"] not in _cache()}
    if not unik:
        return True
    tugas = list(unik.values())
    gagal = []
    with st.status(f"Memeriksa {len(tugas)} versi… biasanya 10–40 detik per file.", expanded=True) as status:
        bar = st.progress(0.0)
        with ThreadPoolExecutor(max_workers=min(WORKER_MAX, len(tugas))) as ex:
            futs = {ex.submit(_periksa, v["data"], v["file_name"], v["judul"], v["jenis"]): v for v in tugas}
            for k, fut in enumerate(as_completed(futs), 1):
                v = futs[fut]
                try:
                    _simpan(v["kunci"], fut.result())
                    st.write(f"✓ **{v['label']}** · {v['file_name']}")
                except Exception as e:  # noqa: BLE001
                    gagal.append((v, e))
                    st.write(f"✕ **{v['label']}** · {_pesan_error(e)}")
                bar.progress(k / len(tugas))
        if gagal:
            status.update(label=f"{len(gagal)} versi gagal diperiksa", state="error", expanded=True)
        else:
            status.update(label="Semua versi selesai diperiksa", state="complete", expanded=False)
    return not gagal


def _mode_banding():
    ups = st.file_uploader(
        f"PDF tiap versi (2–{MAX_VERSI} file)", type=["pdf"], accept_multiple_files=True, key="up_banding",
        help=f"Pilih beberapa file sekaligus. Maks. {MAX_FILE_SIZE_MB} MB per file.",
    )
    if not ups:
        st.session_state.pop("banding_aktif", None)
        _contoh_banding()
        return
    st.session_state.pop("demo_banding", None)
    if len(ups) == 1:
        st.info("Tambahkan minimal satu versi lagi untuk mulai membandingkan.", icon=":material/add:")
        return
    if len(ups) > MAX_VERSI:
        st.warning(f"Maksimal {MAX_VERSI} versi. Hanya {MAX_VERSI} file pertama yang dipakai.")
        ups = ups[:MAX_VERSI]

    with st.container(border=True):
        set_id, versi = _konfigurasi_versi(ups)
        mulai = st.button(f"Bandingkan {len(versi)} versi", type="primary", icon=":material/compare_arrows:",
                          width="stretch")

    if mulai:
        if _periksa_banyak(versi):
            st.session_state["banding_aktif"] = set_id
        else:
            return

    if st.session_state.get("banding_aktif") != set_id:
        return
    if not all(v["kunci"] in _cache() for v in versi):
        st.info("Judul atau jenis PKM diubah. Klik **Bandingkan** lagi untuk memperbarui hasil.")
        return

    st.write("")
    render_banding([
        {"label": v["label"], "file_name": v["file_name"], **_cache()[v["kunci"]]} for v in versi
    ], key=f"bd_{set_id}")


def _contoh_banding():
    samples = _load_samples()
    if len(samples) < 2:
        return
    by_id = {s["id"]: s for s in samples}
    st.write("")
    with st.container(border=True):
        st.markdown("#### Belum punya beberapa versi? Coba demo")
        st.caption("Demo memakai sampel proposal yang **berbeda** (bukan versi dari proposal yang sama), "
                   "jadi hanya untuk melihat cara kerja tampilan perbandingan.")
        bawaan = [i for i in ("E", "C", "B") if i in by_id] or list(by_id)[:2]
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        pilih = c1.multiselect("Sampel, urut dari yang dianggap versi paling lama", list(by_id), default=bawaan,
                               format_func=lambda i: by_id[i]["label"], max_selections=MAX_VERSI,
                               key="demo_pilih")
        if c2.button("Jalankan demo", type="primary", icon=":material/play_arrow:", width="stretch",
                     disabled=len(pilih) < 2):
            st.session_state["demo_banding"] = list(pilih)

    aktif = [i for i in st.session_state.get("demo_banding", []) if i in by_id]
    if len(aktif) < 2:
        return
    versions = []
    for i in aktif:
        r = with_current_timestamp(by_id[i]["result"])
        versions.append({"label": f"Sampel {i}", "file_name": by_id[i]["file_name"],
                         "structured": r["structured_report"], "text_report": r["text_report"]})
    st.write("")
    render_banding(versions, key="demo_" + "".join(aktif))


if __name__ == "__main__":
    main()
