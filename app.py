"""
Streamlit UI — PKM 2026 Proposal Checker.
Jalankan: streamlit run app.py
"""

import os
import tempfile
import streamlit as st

from src.engine import run_checks, FileSizeError
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
            "- Identitas & Kelengkapan\n"
            "- Format & Tipografi\n"
            "- Struktur Dokumen\n"
            "- Anggaran & Keuangan\n"
            "- Lampiran"
        )
        st.warning(
            "**Batasan:**\n"
            "- Maks. ukuran file: 5 MB\n"
            "- PDF harus bisa dibaca teks (bukan scan gambar)\n"
            "- Gemini API digunakan untuk cek sitasi & tema"
        )
        st.markdown("---")
        st.caption("Referensi: Panduan PKM 2026")

    uploaded = st.file_uploader(
        "Upload PDF Proposal PKM",
        type=["pdf"],
        help="Format nama file yang benar: namaketua_namaPT_PKM-[JENIS].pdf",
    )

    if not uploaded:
        st.info("👆 Upload file PDF proposal untuk memulai pengecekan.")
        return

    st.markdown(f"**File:** `{uploaded.name}` — `{uploaded.size / 1024:.1f} KB`")

    # Input manual dari user (wajib diisi untuk analisis yang akurat)
    st.markdown("---")
    st.markdown("### ✏️ Informasi Proposal")
    st.caption(
        "Isi informasi berikut untuk memastikan analisis akurat. "
        "Judul menggunakan **Title Case** — kata konten dikapitalkan, kata sambung/depan (*dan, atau, di, ke, dari, untuk, ...*) huruf kecil."
    )

    col_a, col_b = st.columns([3, 1])
    with col_a:
        judul_input = st.text_area(
            "Judul Proposal (Title Case)",
            placeholder="Contoh: Pengembangan Sistem Monitoring Kualitas Air Berbasis IoT untuk Budidaya Ikan",
            height=80,
            help=(
                "Salin judul sesuai format Title Case: "
                "kata pertama dan kata konten (noun, verb, adj) dikapitalkan, "
                "kata sambung/depan (dan, atau, di, ke, dari, untuk, dengan, ...) huruf kecil."
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
        icon = "✅" if modul["skor"] >= 85 else ("⚠️" if modul["skor"] >= 60 else "❌")
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
        st.success("✅ Tidak ada rekomendasi. Proposal siap disubmit!")

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
