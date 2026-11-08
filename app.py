"""
Streamlit UI — PKM 2026 Proposal Checker.
Jalankan: streamlit run app.py
"""

import html
import os
import tempfile
import time
import streamlit as st

from src.engine import run_checks, FileSizeError
from src.samples import load_samples, with_current_timestamp
from config import JENIS_PKM_VALID

st.set_page_config(
    page_title="PKM 2026 Checker",
    page_icon="📋",
    layout="wide",
)

STATUS_COLOR = {
    "LULUS": "green",
    "PERINGATAN": "orange",
    "TIDAK_LULUS": "red",
}

STATUS_ICON = {
    "LULUS": "✅",
    "PERINGATAN": "⚠️",
    "TIDAK_LULUS": "❌",
}


def render_item(item: dict):
    status = item["status"]
    icon = STATUS_ICON.get(status, "❓")
    color = STATUS_COLOR.get(status, "gray")
    detail = item.get("detail", "")
    hal = f" *(hal. {item['halaman']})*" if item.get("halaman") else ""
    st.markdown(
        f"<div style='padding:4px 0'>"
        f"<span style='color:{color}'>{icon}</span> "
        f"<b>[{item['kode']}]</b> {item['deskripsi']}{hal}"
        f"</div>",
        unsafe_allow_html=True,
    )
    if detail:
        st.caption(f"↳ {detail}")
    if item.get("catatan"):
        poin = "".join(f"<li>{html.escape(c)}</li>" for c in item["catatan"])
        st.markdown(f"<ul style='margin:0 0 6px 2.2em;font-size:0.9em'>{poin}</ul>",
                    unsafe_allow_html=True)


def main():
    st.title("📋 PKM 2026 — Sistem Pengecekan Proposal Otomatis")
    st.markdown(
        "Upload file PDF proposal PKM 2026 untuk memeriksa kesesuaiannya "
        "dengan ketentuan panduan secara otomatis."
    )

    with st.sidebar:
        st.header("ℹ️ Informasi")
        st.info(
            "**Sistem ini memeriksa:**\n"
            "- Hard Disqualifiers (langsung gugur)\n"
            "- Identitas & Judul\n"
            "- Format & Tipografi\n"
            "- Struktur Dokumen\n"
            "- Daftar Pustaka & Sitasi (ketat sampai tanda baca)\n"
            "- Anggaran & Keuangan\n"
            "- Lampiran & Tanda Tangan\n"
            "- Tema & Konsistensi Data"
        )
        st.caption(
            "Hanya administrasi (Tahap 1). Lolos administrasi belum tentu didanai: "
            "Tahap 2 menilai kreativitas gagasan, urgensi masalah, dan ketepatan IPTEK."
        )
        st.warning(
            "**Batasan:**\n"
            "- Maks. ukuran file: 5 MB\n"
            "- PDF harus bisa dibaca teks (bukan scan gambar)\n"
            "- Isi halaman scan (tanggal TTD, meterai) tidak dibaca\n"
            "- Gemini API (opsional) untuk cek sitasi tambahan"
        )
        st.markdown("---")
        st.caption("Referensi: Panduan PKM 2026")

    uploaded = st.file_uploader(
        "Upload PDF Proposal PKM",
        type=["pdf"],
        help="Format nama file yang benar: namaketua_namaPT_PKM-[JENIS].pdf",
    )

    if not uploaded:
        st.info("👆 Upload file PDF proposal untuk memulai pengecekan — atau coba sampel cepat di bawah.")
        _render_sample_section()
        return

    st.markdown(f"**File:** `{uploaded.name}` — `{uploaded.size / 1024:.1f} KB`")

    # Input manual dari user (wajib diisi untuk analisis yang akurat)
    st.markdown("---")
    st.markdown("### ✏️ Informasi Proposal")
    st.caption(
        "Isi informasi berikut untuk memastikan analisis akurat. "
        "Panduan 2026: judul **HURUF KAPITAL**, maks. 20 kata, Bahasa Indonesia, tanpa akronim tidak baku."
    )

    col_a, col_b = st.columns([3, 1])
    with col_a:
        judul_input = st.text_area(
            "Judul Proposal (persis seperti di simbelmawa / Surat Pernyataan)",
            placeholder="Contoh: SISTEM PEMANTAU KUALITAS AIR BERBASIS INTERNET OF THINGS UNTUK BUDIDAYA IKAN",
            height=80,
            help=(
                "Salin judul apa adanya (jangan diubah kapitalisasinya) supaya checker bisa menilai "
                "apakah sudah ditulis huruf kapital sesuai Panduan PKM 2026."
            ),
        )
    with col_b:
        jenis_options = ["(Deteksi Otomatis)"] + [f"PKM-{j}" for j in JENIS_PKM_VALID]
        jenis_selected = st.selectbox(
            "Jenis PKM",
            options=jenis_options,
            help="Pilih jenis PKM sesuai yang diklaim di proposal.",
        )
        jenis_input = None if jenis_selected == "(Deteksi Otomatis)" else jenis_selected.replace("PKM-", "")

    st.markdown("---")

    if st.button("🔍 Mulai Pengecekan", type="primary", use_container_width=True):
        if not judul_input.strip():
            st.warning("⚠️ Judul proposal belum diisi. Pengecekan judul akan dilewati.")

        with st.spinner("Menganalisis proposal... harap tunggu."):
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = tmp.name

                result = run_checks(
                    tmp_path,
                    judul_input=judul_input.strip() or None,
                    jenis_pkm_input=jenis_input,
                )
                os.unlink(tmp_path)

                _render_results(result)

            except FileSizeError as e:
                st.error(f"❌ {e}")
            except FileNotFoundError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan saat memproses PDF: {e}")
                st.exception(e)


@st.cache_data(show_spinner=False)
def _load_samples() -> list[dict]:
    return load_samples()


def _render_sample_section():
    """Sampel cepat: hasil checker asli pada proposal nyata (data pribadi disamarkan)."""
    samples = _load_samples()
    if not samples:
        return
    st.markdown("---")
    st.markdown("### 🧪 Coba Sampel Cepat")
    st.caption(
        f"{len(samples)} proposal PKM nyata — "
        f"{sum(s['status_asli'] == 'Didanai' for s in samples)} didanai, "
        f"{sum(s['status_asli'] != 'Didanai' for s in samples)} tidak didanai. "
        "Nama, NIM, kontak, nama produk, judul, dan perguruan tinggi disamarkan."
    )
    col_a, col_b = st.columns([3, 1])
    with col_a:
        idx = st.selectbox("Pilih sampel", range(len(samples)),
                           format_func=lambda i: samples[i]["label"], key="pilih_sampel")
        if samples[idx].get("catatan_sampel"):
            st.caption(samples[idx]["catatan_sampel"])
    with col_b:
        st.write("")
        if st.button("▶️ Jalankan Sampel", type="primary", use_container_width=True):
            st.session_state["sampel_aktif"] = samples[idx]["id"]
            st.session_state["sampel_animasi"] = True

    aktif = next((s for s in samples if s["id"] == st.session_state.get("sampel_aktif")), None)
    if aktif:
        _run_sample(aktif, animate=st.session_state.pop("sampel_animasi", False))


def _run_sample(sample: dict, animate: bool):
    st.markdown("---")
    st.markdown(f"**File:** `{sample['file_name']}` — `{sample['file_size_kb']:.1f} KB`")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.text_area("Judul Proposal (persis seperti di simbelmawa / Surat Pernyataan)",
                     value=sample["judul"], height=80, disabled=True, key=f"judul_sampel_{sample['id']}")
    with col_b:
        st.text_input("Jenis PKM", value=f"PKM-{sample['jenis']}", disabled=True,
                      key=f"jenis_sampel_{sample['id']}")

    langkah = sample.get("langkah", [])
    if animate and langkah:
        with st.status("Menganalisis proposal... harap tunggu.", expanded=True) as status:
            bar = st.progress(0.0)
            for i, step in enumerate(langkah, 1):
                time.sleep(0.45 if i <= 5 else 0.2)
                st.write(f"• {step}")
                bar.progress(i / len(langkah))
            status.update(label="Analisis selesai", state="complete", expanded=False)
    elif langkah:
        with st.expander("Langkah analisis"):
            st.markdown("\n".join(f"- {html.escape(s)}" for s in langkah))

    st.info(
        f"**{sample['label']}** — hasil asli checker pada proposal PKM nyata. "
        f"Status sebenarnya: **{sample['status_asli']} (PKM {sample['siklus']})**. "
        "Bandingkan dengan temuan di bawah."
    )
    _render_results(with_current_timestamp(sample["result"]))


def _render_results(result: dict):
    structured = result["structured_report"]
    overall = structured["overall"]

    st.markdown("---")

    # Header status
    kategori = overall["kategori"]
    skor = overall["skor"]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Status", kategori)
    with col2:
        st.metric("Skor Keseluruhan", f"{skor:.1f}%" if not structured["is_gugur"] else "—")
    with col3:
        st.metric("Jenis PKM", f"PKM-{structured['jenis_pkm'] or '?'}")
    with col4:
        st.metric("Ukuran File", f"{structured['file_size_mb']:.2f} MB")

    if structured["judul"]:
        st.info(f"**Judul:** {structured['judul']}")

    if structured["is_gugur"]:
        st.error("🚫 **PROPOSAL GUGUR DI TAHAP 1** — Perbaiki Hard Disqualifier berikut:")

    # Tampilan skor per modul
    if not structured["is_gugur"] and overall.get("modul_scores"):
        st.markdown("### Skor per Modul")
        cols = st.columns(len(overall["modul_scores"]))
        for col, (nama, skor_m) in zip(cols, overall["modul_scores"].items()):
            short_name = nama.split(":")[0] if ":" in nama else nama
            col.metric(short_name, f"{skor_m:.0f}%")

    st.markdown("---")

    # Hard Disqualifiers
    with st.expander("🚨 FASE 1: Hard Disqualifiers", expanded=True):
        for item in structured["hard_disqualifiers"]["items"]:
            render_item(item)

    if structured["is_gugur"]:
        st.warning("Proses pengecekan dihentikan karena proposal gugur di Fase 1.")
        _render_text_report(result["text_report"])
        return

    # Modul-modul
    for modul in structured["modul_results"]:
        ada_wajib = any(i["status"] == "TIDAK_LULUS" for i in modul["items"])
        icon = "❌" if ada_wajib else ("✅" if modul["skor"] >= 85 else "⚠️")
        with st.expander(f"{icon} {modul['nama']} — Skor: {modul['skor']:.0f}%"):
            for item in modul["items"]:
                render_item(item)

    # Rekomendasi
    st.markdown("---")
    st.markdown("### 📌 Rekomendasi Prioritas")
    all_items = (
        structured["hard_disqualifiers"]["items"]
        + [i for m in structured["modul_results"] for i in m["items"]]
    )
    wajib = [i for i in all_items if i["status"] == "TIDAK_LULUS"]
    periksa = [i for i in all_items if i["status"] == "PERINGATAN"]

    if wajib:
        st.error(f"**{len(wajib)} item WAJIB diperbaiki:**")
        for i, item in enumerate(wajib, 1):
            st.markdown(f"{i}. **[{item['kode']}] {item['deskripsi']}** — {item['detail']}")

    if periksa:
        st.warning(f"**{len(periksa)} item perlu diperiksa manual:**")
        for i, item in enumerate(periksa, 1):
            st.markdown(f"{i}. **[{item['kode']}] {item['deskripsi']}** — {item['detail']}")

    if not wajib and not periksa:
        st.success("✅ Tidak ada temuan administrasi. Tetap cek manual hal-hal yang tidak bisa dibaca "
                   "otomatis (isi scan, tanggal tanda tangan, meterai) dan perkuat substansi gagasan.")

    _render_text_report(result["text_report"])


def _render_text_report(text_report: str):
    st.markdown("---")
    with st.expander("📄 Laporan Lengkap (Teks)"):
        st.code(text_report, language="text")
        st.download_button(
            "⬇️ Unduh Laporan (.txt)",
            data=text_report,
            file_name="laporan_pkm.txt",
            mime="text/plain",
        )


if __name__ == "__main__":
    main()
