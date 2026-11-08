"""
Logika mode komparasi: bandingkan hasil checker beberapa versi proposal (v1, v2, v3, ...).

Semua fungsi di sini murni (input: structured_report dari report_generator), tanpa Streamlit,
supaya mudah dites. Item dicocokkan antarversi lewat `kode` (unik dan stabil per pemeriksaan).
"""

from typing import Optional

HD_NAMA = "Hard Disqualifier"

# Makin besar makin parah. None = item tidak ada di versi tsb (mis. lampiran khusus bidang lain).
RANK = {"LULUS": 0, "PERINGATAN": 1, "TIDAK_LULUS": 2}

# Urutan grup perubahan sesuai urgensi bagi penulis yang sedang merevisi.
GRUP_URUTAN = ["memburuk", "tetap", "membaik", "beres"]


def modul_pendek(nama: str) -> str:
    """'Modul 4: Daftar Pustaka & Sitasi' -> 'Daftar Pustaka & Sitasi'."""
    return nama.split(":", 1)[1].strip() if ":" in nama else nama


def semua_modul(structured: dict) -> list[dict]:
    """Hard Disqualifier + 7 modul, dengan format seragam {nama, skor, items}."""
    hd_items = structured["hard_disqualifiers"]["items"]
    hd = {"nama": HD_NAMA, "skor": None, "items": hd_items, "is_hd": True}
    return [hd] + [{**m, "is_hd": False} for m in structured["modul_results"]]


def flatten_items(structured: dict) -> list[dict]:
    """Semua item pemeriksaan, berurutan, masing-masing diberi nama modulnya."""
    out = []
    for m in semua_modul(structured):
        for it in m["items"]:
            out.append({**it, "modul": m["nama"], "is_hd": m["is_hd"]})
    return out


def hitung_status(structured: dict) -> dict:
    """Jumlah item per status: {'TIDAK_LULUS': n, 'PERINGATAN': n, 'LULUS': n}."""
    c = {"TIDAK_LULUS": 0, "PERINGATAN": 0, "LULUS": 0}
    for it in flatten_items(structured):
        c[it["status"]] = c.get(it["status"], 0) + 1
    return c


def hitung_modul(modul: dict) -> dict:
    c = {"TIDAK_LULUS": 0, "PERINGATAN": 0, "LULUS": 0}
    for it in modul["items"]:
        c[it["status"]] = c.get(it["status"], 0) + 1
    return c


def baris_matriks(versions: list[dict]) -> list[dict]:
    """
    Gabungan semua item dari semua versi.

    Return list baris: {kode, deskripsi, modul, per_versi: [item | None, ...]}
    Urutan mengikuti kemunculan pertama, jadi pengelompokan per modul tetap terjaga.
    """
    index: dict[str, dict] = {}
    urutan: list[str] = []
    for vi, v in enumerate(versions):
        for it in flatten_items(v["structured"]):
            k = it["kode"]
            if k not in index:
                index[k] = {"kode": k, "deskripsi": it["deskripsi"], "modul": it["modul"],
                            "per_versi": [None] * len(versions)}
                urutan.append(k)
            index[k]["per_versi"][vi] = it
    return [index[k] for k in urutan]


def _status(it: Optional[dict]) -> Optional[str]:
    return it["status"] if it else None


def klasifikasi(sebelum: Optional[dict], sesudah: Optional[dict]) -> Optional[str]:
    """
    Golongkan perubahan satu item dari versi A ke versi B.

    'beres'    : bermasalah -> LULUS
    'membaik'  : TIDAK_LULUS -> PERINGATAN
    'memburuk' : makin parah, atau masalah yang baru muncul
    'tetap'    : masalah yang sama masih ada
    None       : tidak relevan (sama-sama LULUS, atau item hilang/tidak ada di B)
    """
    a, b = _status(sebelum), _status(sesudah)
    if b is None:
        return None
    rb = RANK[b]
    ra = RANK[a] if a is not None else 0
    if rb == 0:
        return "beres" if ra > 0 else None
    if rb < ra:
        return "membaik"
    if rb > ra:
        return "memburuk"
    return "tetap"


def ringkas_perubahan(versions: list[dict], i_dari: int, i_ke: int) -> dict:
    """
    Perubahan dari versi i_dari ke i_ke.

    Return {grup: [ {kode, deskripsi, modul, sebelum, sesudah, rincian_berubah}, ... ]}
    """
    grup: dict[str, list] = {g: [] for g in GRUP_URUTAN}
    for row in baris_matriks(versions):
        a, b = row["per_versi"][i_dari], row["per_versi"][i_ke]
        g = klasifikasi(a, b)
        if g is None:
            continue
        rincian_berubah = bool(a and b and (a.get("detail") != b.get("detail")
                                            or a.get("catatan") != b.get("catatan")))
        grup[g].append({**row, "sebelum": a, "sesudah": b, "rincian_berubah": rincian_berubah})
    # Dalam tiap grup, yang paling parah (wajib diperbaiki) di atas; urutan modul tetap terjaga (sort stabil).
    for g in GRUP_URUTAN:
        grup[g].sort(key=lambda r: -RANK[r["sesudah"]["status"]])
    return grup


def berubah_antarversi(row: dict) -> bool:
    status = {_status(it) for it in row["per_versi"] if it is not None}
    return len(status) > 1


def bermasalah_terakhir(row: dict) -> bool:
    last = row["per_versi"][-1]
    return bool(last and last["status"] != "LULUS")


def skor_modul(versions: list[dict]) -> list[dict]:
    """
    Tabel skor per modul: [{nama, skor: [float|None per versi]}], diawali skor keseluruhan.
    Skor modul tetap ditampilkan walau proposal gugur (engine tetap menjalankan semua modul).
    """
    rows = [{"nama": "Skor keseluruhan", "skor": [
        None if v["structured"]["is_gugur"] else v["structured"]["overall"]["skor"] for v in versions
    ], "utama": True}]
    nama_modul: list[str] = []
    for v in versions:
        for m in v["structured"]["modul_results"]:
            if m["nama"] not in nama_modul:
                nama_modul.append(m["nama"])
    for nama in nama_modul:
        skor = []
        for v in versions:
            m = next((m for m in v["structured"]["modul_results"] if m["nama"] == nama), None)
            skor.append(m["skor"] if m else None)
        rows.append({"nama": nama, "skor": skor, "utama": False})
    return rows


def matriks_csv(versions: list[dict]) -> str:
    """Matriks status per item per versi, untuk diunduh."""
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    labels = [v["label"] for v in versions]
    w.writerow(["Modul", "Kode", "Pemeriksaan"] + labels + [f"Rincian {labels[-1]}"])
    for row in baris_matriks(versions):
        last = row["per_versi"][-1]
        w.writerow([row["modul"], row["kode"], row["deskripsi"]]
                   + [_status(it) or "-" for it in row["per_versi"]]
                   + [last.get("detail", "") if last else ""])
    return buf.getvalue()
