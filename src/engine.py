"""
PKM Checker Engine — orkestrasi pipeline lengkap.
Panggil run_checks(file_path) untuk mendapatkan laporan.
"""

import os
from typing import Optional
from src.parser.pdf_parser import parse_pdf, ProposalDocument
from src.checkers.hard_disqualifier import HardDisqualifierChecker
from src.checkers.identity_checker import IdentityChecker
from src.checkers.format_checker import FormatChecker
from src.checkers.structure_checker import StructureChecker
from src.checkers.reference_checker import ReferenceChecker
from src.checkers.budget_checker import BudgetChecker
from src.checkers.attachment_checker import AttachmentChecker
from src.checkers.consistency_checker import ConsistencyChecker
from src.report.report_generator import (
    generate_text_report,
    generate_structured_report,
)
from config import MAX_FILE_SIZE_MB, GEMINI_API_KEY


class FileSizeError(Exception):
    pass


def run_checks(
    file_path: str,
    judul_input: Optional[str] = None,
    jenis_pkm_input: Optional[str] = None,
) -> dict:
    """
    Jalankan seluruh pipeline pengecekan proposal PKM.

    Args:
        file_path: Path ke file PDF proposal.
        judul_input: Judul yang diinput manual oleh user (override auto-detect).
        jenis_pkm_input: Jenis PKM yang dipilih user (override auto-detect).

    Returns:
        dict dengan kunci 'text_report', 'structured_report', dll.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise FileSizeError(
            f"Ukuran file {file_size_mb:.2f} MB melebihi batas maksimum {MAX_FILE_SIZE_MB} MB."
        )

    doc: ProposalDocument = parse_pdf(file_path)

    # Override dengan input user jika tersedia
    if judul_input:
        doc.judul = judul_input
    if jenis_pkm_input:
        doc.jenis_pkm = jenis_pkm_input

    hard_checker = HardDisqualifierChecker(doc)
    hard_result = hard_checker.run()

    modul_results = [
        IdentityChecker(doc).run(),
        FormatChecker(doc).run(),
        StructureChecker(doc).run(),
        ReferenceChecker(doc, use_gemini=bool(GEMINI_API_KEY)).run(),
        BudgetChecker(doc).run(),
        AttachmentChecker(doc).run(),
        ConsistencyChecker(doc).run(),
    ]

    text_report = generate_text_report(doc, modul_results, hard_result)
    structured = generate_structured_report(doc, modul_results, hard_result)

    return {
        "text_report": text_report,
        "structured_report": structured,
        "doc": doc,
        "hard_result": hard_result,
        "modul_results": modul_results,
    }
