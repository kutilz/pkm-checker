"""
Report Generator: ambil semua ModulResult, hitung skor, dan hasilkan laporan teks.
"""

from datetime import datetime
from src.checkers.base_checker import ModulResult, Status


STATUS_EMOJI = {
    Status.LULUS: "✅",
    Status.PERINGATAN: "⚠️",
    Status.TIDAK_LULUS: "❌",
}


def compute_overall(modul_results: list[ModulResult], is_gugur: bool) -> dict:
    """
    Hitung skor keseluruhan berbobot.
    Kembalikan dict: {skor, kategori, modul_scores}
    """
    if is_gugur:
        return {"skor": 0, "kategori": "GUGUR LANGSUNG", "modul_scores": {}}

    total_bobot = sum(m.bobot for m in modul_results if m.bobot > 0)
    weighted_sum = sum(
        m.skor * m.bobot for m in modul_results if m.bobot > 0
    )
    skor = round(weighted_sum / total_bobot, 1) if total_bobot > 0 else 0

    ada_wajib = any(m.ada_tidak_lulus for m in modul_results)
    if skor >= 100:
        kategori = "PERFECT"
    elif skor >= 85 and not ada_wajib:
        kategori = "LAYAK"
    elif skor >= 60:
        # Masih ada item TIDAK_LULUS → belum layak walau skor tinggi
        kategori = "PERLU PERBAIKAN"
    else:
        kategori = "TIDAK LOLOS"

    modul_scores = {m.nama_modul: m.skor for m in modul_results}
    return {"skor": skor, "kategori": kategori, "modul_scores": modul_scores}


def generate_text_report(
    doc,
    modul_results: list[ModulResult],
    hard_result: ModulResult,
) -> str:
    """Buat laporan teks lengkap seperti format di blueprint."""

    is_gugur = hard_result.ada_tidak_lulus
    overall = compute_overall(modul_results, is_gugur)
    timestamp = datetime.now().strftime("%d %B %Y, %H:%M")

    lines = [
        "=" * 60,
        "  LAPORAN PENGECEKAN PROPOSAL PKM 2026",
        "=" * 60,
        f"Nama File    : {doc.file_name}",
        f"Jenis PKM    : PKM-{doc.jenis_pkm or 'tidak terdeteksi'}",
        f"Judul        : {doc.judul or '(tidak terdeteksi)'}",
        f"Ukuran File  : {doc.file_size_mb:.2f} MB",
        f"Tanggal Cek  : {timestamp}",
        "",
    ]

    # Status keseluruhan
    skor = overall["skor"]
    kategori = overall["kategori"]
    if kategori == "GUGUR LANGSUNG":
        status_line = "🚫 GUGUR LANGSUNG"
    elif kategori == "PERFECT":
        status_line = f"✅ {kategori} ({skor:.0f}%)"
    elif kategori == "LAYAK":
        status_line = f"✅ {kategori} ({skor:.1f}%)"
    elif kategori == "PERLU PERBAIKAN":
        status_line = f"⚠️  {kategori} ({skor:.1f}%)"
    else:
        status_line = f"❌ {kategori} ({skor:.1f}%)"

    lines += [
        f"STATUS KESELURUHAN: {status_line}",
        "=" * 60,
        "",
    ]

    # Hard disqualifiers
    lines.append(f"[FASE 1] {hard_result.nama_modul.upper()}")
    lines.append("-" * 40)
    for item in hard_result.items:
        emoji = STATUS_EMOJI[item.status]
        lines.append(f"{emoji} [{item.kode}] {item.deskripsi}")
        if item.detail:
            lines.append(f"    → {item.detail}")
        lines.extend(f"      • {c}" for c in item.catatan)
    lines.append("")

    if is_gugur:
        lines += [
            "🚫 PROPOSAL GUGUR DI TAHAP 1.",
            "   Perbaiki Hard Disqualifier sebelum melanjutkan.",
            "=" * 60,
        ]
        return "\n".join(lines)

    # Tiap modul
    for modul in modul_results:
        lines.append(f"[{modul.nama_modul.upper()}]  Skor: {modul.skor:.0f}%")
        lines.append("-" * 40)
        for item in modul.items:
            emoji = STATUS_EMOJI[item.status]
            hal = f" (hal. {item.halaman})" if item.halaman else ""
            lines.append(f"{emoji} [{item.kode}] {item.deskripsi}{hal}")
            if item.detail:
                lines.append(f"    → {item.detail}")
            lines.extend(f"      • {c}" for c in item.catatan)
        lines.append("")

    # Rekomendasi prioritas
    lines += ["=" * 60, "REKOMENDASI PRIORITAS:", "-" * 40]
    prioritas = []
    for modul in [hard_result] + modul_results:
        for item in modul.items:
            if item.status == Status.TIDAK_LULUS:
                prioritas.append(f"[WAJIB] {item.deskripsi}: {item.detail}")
            elif item.status == Status.PERINGATAN:
                prioritas.append(f"[PERIKSA] {item.deskripsi}: {item.detail}")

    if prioritas:
        for i, rec in enumerate(prioritas, 1):
            lines.append(f"{i}. {rec}")
    else:
        lines.append("✅ Tidak ada rekomendasi perbaikan administrasi.")

    lines += [
        "",
        "CATATAN: checker ini hanya menilai ADMINISTRASI & FORMAT (Tahap 1).",
        "Lolos administrasi tidak menjamin didanai — Tahap 2 menilai substansi",
        "(kreativitas gagasan, urgensi masalah, ketepatan IPTEK/metode, potensi).",
        "=" * 60,
    ]
    return "\n".join(lines)


def generate_structured_report(
    doc,
    modul_results: list[ModulResult],
    hard_result: ModulResult,
) -> dict:
    """
    Kembalikan laporan dalam format dict/JSON-friendly.
    Berguna untuk Streamlit UI.
    """
    is_gugur = hard_result.ada_tidak_lulus
    overall = compute_overall(modul_results, is_gugur)

    return {
        "file_name": doc.file_name,
        "jenis_pkm": doc.jenis_pkm,
        "judul": doc.judul,
        "file_size_mb": doc.file_size_mb,
        "is_gugur": is_gugur,
        "overall": overall,
        "hard_disqualifiers": {
            "items": [
                {
                    "kode": i.kode,
                    "deskripsi": i.deskripsi,
                    "status": i.status.value,
                    "detail": i.detail,
                    "catatan": list(i.catatan),
                }
                for i in hard_result.items
            ]
        },
        "modul_results": [
            {
                "nama": m.nama_modul,
                "skor": m.skor,
                "bobot": m.bobot,
                "items": [
                    {
                        "kode": i.kode,
                        "deskripsi": i.deskripsi,
                        "status": i.status.value,
                        "detail": i.detail,
                        "halaman": i.halaman,
                        "catatan": list(i.catatan),
                    }
                    for i in m.items
                ],
            }
            for m in modul_results
        ],
    }
