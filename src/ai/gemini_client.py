"""
Gemini API client untuk analisis semantik proposal PKM.
- Cross-reference sitasi ↔ daftar pustaka
- Pengecekan tema tematik PKM 2026

Rate limit free tier: 15 RPM, 1M token/hari.
Setiap call diberi jeda minimal 5 detik untuk keamanan.
"""

import json
import re
import time
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, TEMA_PKM_2026

_RATE_LIMIT_SLEEP = 5   # detik minimum antar-request (aman untuk 15 RPM)
_last_call_time: float = 0.0


def _get_client():
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY tidak ditemukan di .env")
    return genai.Client(api_key=GEMINI_API_KEY)


def _call_with_rate_limit(prompt: str, max_retries: int = 3) -> str:
    """
    Panggil Gemini dengan jeda rate limit dan auto-retry jika terkena quota error.
    """
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _RATE_LIMIT_SLEEP:
        time.sleep(_RATE_LIMIT_SLEEP - elapsed)

    client = _get_client()
    for attempt in range(max_retries):
        try:
            _last_call_time = time.time()
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            err = str(e).lower()
            if "quota" in err or "rate" in err or "429" in err:
                wait = _RATE_LIMIT_SLEEP * (2 ** attempt)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Gemini API gagal setelah beberapa percobaan. Coba lagi nanti.")


def _safe_json_parse(text: str) -> dict:
    """Parse JSON dari respons Gemini, toleran terhadap markdown code block."""
    clean = re.sub(r'```(?:json)?\s*', '', text).strip().rstrip('`').strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def check_citation_consistency(sitasi_list: list[str], dafpus_list: list[str]) -> dict:
    """
    Gunakan Gemini untuk mencocokkan sitasi di teks dengan entri daftar pustaka.

    Returns:
        dict: {
            "tidak_ada_di_dafpus": [...],  # sitasi yang tidak ada di dafpus
            "tidak_disitasi": [...],        # entri dafpus yang tidak disitasi
            "inkonsistensi": [...],         # nama/tahun tidak cocok
        }
    """
    sitasi_str = "\n".join(f"- {s}" for s in sitasi_list)
    dafpus_str = "\n".join(f"- {d[:120]}" for d in dafpus_list)

    prompt = f"""Kamu adalah asisten pemeriksa proposal ilmiah.

Berikut daftar SITASI yang ditemukan di dalam teks proposal:
{sitasi_str}

Berikut ENTRI DAFTAR PUSTAKA:
{dafpus_str}

Tugas:
1. Temukan sitasi di teks yang tidak memiliki entri yang cocok di daftar pustaka.
2. Temukan entri di daftar pustaka yang tidak disitasi di teks.
3. Temukan inkonsistensi nama atau tahun antara sitasi dan daftar pustaka.

Toleransi: variasi singkatan nama, perbedaan kecil penulisan masih dianggap cocok.

Jawab HANYA dalam format JSON berikut (tanpa teks lain):
{{"tidak_ada_di_dafpus": ["..."], "tidak_disitasi": ["..."], "inkonsistensi": ["..."]}}"""

    text = _call_with_rate_limit(prompt)
    return _safe_json_parse(text)


def check_tema_tematik(judul: str, latar_belakang: str) -> dict:
    """
    Tentukan tema PKM 2026 yang paling relevan dengan proposal.

    Returns:
        dict: {
            "tema": "...",
            "nomor": N,
            "confidence": 0-100,
            "alasan": "..."
        }
    """
    tema_str = "\n".join(f"{i+1}. {t}" for i, t in enumerate(TEMA_PKM_2026))

    prompt = f"""Kamu adalah asisten pemeriksa proposal PKM 2026.

Judul proposal: "{judul}"
Latar belakang (penggalan): "{latar_belakang[:600]}"

10 Tema PKM Tematik 2026:
{tema_str}

Tentukan tema yang PALING RELEVAN dan berikan confidence score 0-100.
- 90-100: sangat relevan, jelas terkait langsung
- 70-89: cukup relevan
- 50-69: agak relevan, perlu klarifikasi
- <50: tidak jelas kaitannya

Jawab HANYA dalam format JSON:
{{"tema": "...", "nomor": N, "confidence": 0-100, "alasan": "..."}}"""

    text = _call_with_rate_limit(prompt)
    return _safe_json_parse(text)
