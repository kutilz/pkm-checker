"""
Komponen tampilan Streamlit untuk PKM Checker.

Semua HTML kustom dirender lewat st.html (bukan st.markdown) supaya teks dari PDF tidak
ditafsirkan sebagai Markdown/LaTeX. Semua teks dinamis wajib lewat _e() (html.escape).
Warna memakai tint rgba + `color: inherit` agar terbaca di tema terang maupun gelap.
"""

from html import escape as _e

import streamlit as st

from src.compare import (
    GRUP_URUTAN,
    bermasalah_terakhir,
    baris_matriks,
    berubah_antarversi,
    flatten_items,
    hitung_modul,
    hitung_status,
    matriks_csv,
    modul_pendek,
    ringkas_perubahan,
    semua_modul,
    skor_modul,
)

STATUS = {
    "TIDAK_LULUS": {"cls": "bad", "label": "Wajib diperbaiki", "sym": "✕"},
    "PERINGATAN": {"cls": "warn", "label": "Cek manual", "sym": "!"},
    "LULUS": {"cls": "ok", "label": "Sesuai", "sym": "✓"},
}
STATUS_NA = {"cls": "na", "label": "Tidak diperiksa di versi ini", "sym": "–"}
EMOJI_KELAS = {"bad": "🔴", "warn": "🟠", "ok": "🟢", "na": "⚪"}

CSS = """
<style>
.stMainBlockContainer { max-width: 1180px; }
.pk { --ok:#1a9e5c; --warn:#d68a00; --bad:#e0453a; --na:#8b929c;
      --line: rgba(128,128,128,.24); --soft: rgba(128,128,128,.06); }
.pk, .pk * { box-sizing: border-box; }
.pk .ok   { --acc: var(--ok);   --tint: rgba(26,158,92,.13); }
.pk .warn { --acc: var(--warn); --tint: rgba(214,138,0,.15); }
.pk .bad  { --acc: var(--bad);  --tint: rgba(224,69,58,.13); }
.pk .na   { --acc: var(--na);   --tint: rgba(139,146,156,.15); }
.pk .muted { opacity: .68; }
.pk .kode { font: 600 .74rem ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            padding: 1px 6px; border-radius: 6px; background: var(--soft);
            border: 1px solid var(--line); white-space: nowrap; }

/* Pil status bulat */
.pk .pill { display:inline-flex; align-items:center; justify-content:center; flex: none;
            width: 22px; height: 22px; border-radius: 50%; font-size: .78rem; font-weight: 800;
            color: var(--acc); background: var(--tint); line-height: 1; }
.pk .badge { display:inline-block; padding: 3px 11px; border-radius: 999px; font-weight: 700;
             font-size: .74rem; letter-spacing: .05em; text-transform: uppercase;
             color: var(--acc); background: var(--tint); }

/* Kartu ringkasan (hero) */
.pk .hero { display:flex; gap: 24px; justify-content: space-between; flex-wrap: wrap;
            border: 1px solid var(--line); border-left: 6px solid var(--acc); border-radius: 14px;
            padding: 20px 22px; background: var(--soft); }
.pk .hero-main { flex: 1 1 420px; min-width: 0; }
.pk .hero-title { font-size: 1.45rem; font-weight: 700; line-height: 1.25; margin: 10px 0 4px; }
.pk .hero-sub { font-size: .98rem; opacity: .8; }
.pk .hero-meta { margin-top: 12px; font-size: .85rem; opacity: .7; word-break: break-word; }
.pk .hero-judul { margin-top: 6px; font-size: .9rem; font-weight: 600; line-height: 1.4; }
.pk .hero-judul.kosong { font-weight: 400; font-style: italic; opacity: .75; }
.pk .hero-score { flex: 0 0 auto; text-align: right; align-self: center; }
.pk .hero-score b { display:block; font-size: 2.9rem; line-height: 1; color: var(--acc); }
.pk .hero-score span { font-size: .8rem; opacity: .7; }
.pk .stats { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 10px; margin-top: 12px; }
.pk .stat { border-radius: 12px; padding: 10px 14px; background: var(--tint); display:flex;
            align-items: baseline; gap: 8px; }
.pk .stat b { font-size: 1.5rem; color: var(--acc); }
.pk .stat span { font-size: .88rem; }

/* Grid skor modul */
.pk .mods { display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-top: 14px; }
.pk .mod { border: 1px solid var(--line); border-radius: 12px; padding: 11px 13px; }
.pk .mod-kicker { font-size: .7rem; text-transform: uppercase; letter-spacing: .06em; opacity: .6; }
.pk .mod-top { display:flex; justify-content: space-between; gap: 8px; align-items: flex-start; }
.pk .mod-name { font-size: .9rem; font-weight: 600; line-height: 1.25; }
.pk .mod-score { font-weight: 700; color: var(--acc); white-space: nowrap; }
.pk .bar { height: 6px; border-radius: 99px; background: rgba(128,128,128,.18); margin: 8px 0 6px; overflow: hidden; }
.pk .bar i { display:block; height: 100%; border-radius: 99px; background: var(--acc); }
.pk .mod-foot { font-size: .78rem; opacity: .75; }

/* Kartu temuan */
.pk .sec { display:flex; align-items: baseline; gap: 10px; margin: 18px 0 8px; }
.pk .sec h4 { margin: 0; padding: 0; font-size: 1.05rem; }
.pk .sec .muted { font-size: .85rem; }
.pk .issue { border: 1px solid var(--line); border-left: 4px solid var(--acc); border-radius: 10px;
             padding: 11px 14px; margin-bottom: 8px; }
.pk .issue-head { display:flex; gap: 8px; align-items: flex-start; }
.pk .issue-title { font-weight: 600; line-height: 1.35; flex: 1; }
.pk .issue-mod { font-size: .78rem; opacity: .65; margin-top: 3px; }
.pk .issue-detail { margin-top: 6px; font-size: .92rem; line-height: 1.45; }
.pk .hal { font-size: .76rem; opacity: .7; white-space: nowrap; }
.pk ul.cat { margin: 6px 0 0 0; padding-left: 1.2em; font-size: .86rem; line-height: 1.45; }
.pk ul.cat li { margin: 2px 0; }
.pk details.more > summary, .pk details.prev > summary { cursor: pointer; font-size: .82rem;
            margin-top: 6px; color: var(--acc, inherit); opacity: .9; }
.pk details.prev { margin-top: 6px; }
.pk details.prev .prev-body { border-left: 2px solid var(--line); padding: 2px 0 2px 10px; margin-top: 4px;
            font-size: .86rem; opacity: .85; }
.pk .trans { display:flex; align-items:center; gap: 6px; flex-wrap: wrap; margin-top: 6px; font-size: .84rem; }
.pk .trans .arr { opacity: .55; }
.pk .hint { font-size: .8rem; opacity: .7; margin-top: 4px; }
.pk .empty { border: 1px dashed var(--line); border-radius: 10px; padding: 14px; font-size: .92rem; opacity: .85; }

/* Baris item di rincian modul */
.pk .row { display:flex; gap: 10px; padding: 8px 2px; border-bottom: 1px solid var(--line); }
.pk .row:last-child { border-bottom: none; }
.pk .row-body { flex: 1; min-width: 0; }
.pk .row-title { line-height: 1.35; }
.pk .row-detail { font-size: .86rem; opacity: .78; margin-top: 2px; line-height: 1.4; }

/* Mode komparasi: kartu versi */
.pk .vers { display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
.pk .ver { border: 1px solid var(--line); border-top: 4px solid var(--acc); border-radius: 12px;
           padding: 12px 14px; background: var(--soft); min-width: 0; }
.pk .ver-label { font-weight: 800; font-size: 1.05rem; }
.pk .ver-file { font-size: .76rem; opacity: .65; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 8px; }
.pk .ver-score { font-size: 1.9rem; font-weight: 800; line-height: 1.1; margin-top: 8px; color: var(--acc); }
.pk .ver-score small { font-size: .8rem; font-weight: 600; }
.pk .ver-counts { font-size: .82rem; margin-top: 4px; }
.pk .up { color: var(--ok); } .pk .down { color: var(--bad); } .pk .same { opacity: .6; }
.pk .delta { font-size: .8rem; font-weight: 700; margin-left: 4px; white-space: nowrap; }

/* Strip ringkasan perubahan */
.pk .chg { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; margin: 6px 0 4px; }
.pk .chg div { border-radius: 12px; padding: 10px 12px; background: var(--tint); }
.pk .chg b { display:block; font-size: 1.5rem; color: var(--acc); line-height: 1.1; }
.pk .chg span { font-size: .84rem; }
.pk .lead { font-size: 1rem; margin: 4px 0 10px; }

/* Tabel skor */
.pk table.skor { width: 100%; border-collapse: collapse; font-size: .92rem; }
.pk table.skor th, .pk table.skor td { padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: right; }
.pk table.skor th:first-child, .pk table.skor td:first-child { text-align: left; }
.pk table.skor thead th { font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; opacity: .7; }
.pk table.skor tr.utama td { font-weight: 700; background: var(--soft); }
.pk table.skor .cell { display:inline-block; min-width: 54px; text-align: center; padding: 2px 8px;
            border-radius: 7px; background: var(--tint); color: var(--acc); font-weight: 700; }

/* Matriks semua pemeriksaan */
.pk .mx { --cols: 60px minmax(0,1fr) repeat(var(--n), 68px); }
.pk .mx-head, .pk .mx summary { display:grid; grid-template-columns: var(--cols); gap: 8px; align-items: center; }
.pk .mx-head { font-size: .74rem; text-transform: uppercase; letter-spacing: .05em; opacity: .7;
               padding: 6px 8px; border-bottom: 1px solid var(--line); }
.pk .mx-head span.v { text-align: center; text-transform: none; font-weight: 700; line-height: 1.2;
                       overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; word-break: break-word; }
.pk .mx-group { font-weight: 700; font-size: .88rem; padding: 12px 8px 4px; }
.pk .mx details { border-bottom: 1px solid var(--line); }
.pk .mx summary { list-style: none; cursor: pointer; padding: 7px 8px; border-radius: 8px; }
.pk .mx summary::-webkit-details-marker { display: none; }
.pk .mx summary:hover { background: var(--soft); }
.pk .mx details[open] > summary { background: var(--soft); }
.pk .mx .desc { font-size: .9rem; line-height: 1.3; }
.pk .mx .pc { display:flex; justify-content: center; }
.pk .mx-detail { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; padding: 8px 8px 14px; }
.pk .mx-v { border: 1px solid var(--line); border-radius: 10px; padding: 9px 11px; font-size: .86rem; line-height: 1.4; }
.pk .mx-vh { display:flex; align-items:center; gap: 6px; font-weight: 700; margin-bottom: 4px; }

/* Legenda */
.pk .legend { display:flex; flex-direction: column; gap: 8px; font-size: .88rem; }
.pk .legend div { display:flex; gap: 8px; align-items: flex-start; line-height: 1.35; }
.pk .legend.inline { flex-direction: row; flex-wrap: wrap; gap: 14px; font-size: .82rem; opacity: .85; margin-bottom: 4px; }
.pk .legend.inline div { align-items: center; }

@media (max-width: 640px) {
  .pk .stats, .pk .chg { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .pk .hero-score { text-align: left; }
  .pk .mx { --cols: 46px minmax(0,1fr) repeat(var(--n), 34px); }
  .pk .mx-head span.v { font-size: .62rem; }
}
</style>
"""


# ─── Helper kecil ──────────────────────────────────────────────────────────────

def inject_css():
    st.html(CSS)


def _html(body: str):
    st.html(f'<div class="pk">{body}</div>')


def fmt(x: float, d: int = 1) -> str:
    """Angka gaya Indonesia: 85.3 -> '85,3'."""
    s = f"{x:.{d}f}".replace(".", ",")
    return s[:-2] if d == 1 and s.endswith(",0") else s


def pill(status) -> str:
    m = STATUS.get(status, STATUS_NA)
    return f'<span class="pill {m["cls"]}" title="{m["label"]}">{m["sym"]}</span>'


def kelas_status(counts: dict) -> str:
    if counts.get("TIDAK_LULUS"):
        return "bad"
    if counts.get("PERINGATAN"):
        return "warn"
    return "ok"


def _catatan(catatan: list, batas: int = 5) -> str:
    if not catatan:
        return ""
    li = lambda xs: "".join(f"<li>{_e(c)}</li>" for c in xs)
    out = f'<ul class="cat">{li(catatan[:batas])}</ul>'
    if len(catatan) > batas:
        out += (f'<details class="more"><summary>Lihat {len(catatan) - batas} rincian lainnya</summary>'
                f'<ul class="cat">{li(catatan[batas:])}</ul></details>')
    return out


def _hal(item: dict) -> str:
    return f'<span class="hal">hal. {_e(str(item["halaman"]))}</span>' if item.get("halaman") else ""


def legenda_html(inline: bool = False) -> str:
    teks = {
        "TIDAK_LULUS": "melanggar panduan; harus diperbaiki sebelum submit.",
        "PERINGATAN": "tidak bisa dipastikan otomatis atau berisiko; periksa sendiri.",
        "LULUS": "sudah sesuai panduan.",
    }
    rows = "".join(
        f'<div>{pill(s)}<span><b>{STATUS[s]["label"]}</b>{"" if inline else " — " + teks[s]}</span></div>'
        for s in ("TIDAK_LULUS", "PERINGATAN", "LULUS")
    )
    return f'<div class="legend{" inline" if inline else ""}">{rows}</div>'


def verdict(structured: dict, counts: dict) -> tuple[str, str, str, str]:
    """(kelas, badge, judul kalimat, saran) untuk kartu ringkasan."""
    w, p = counts["TIDAK_LULUS"], counts["PERINGATAN"]
    kat = structured["overall"]["kategori"]
    if structured["is_gugur"]:
        n_hd = sum(i["status"] == "TIDAK_LULUS" for i in structured["hard_disqualifiers"]["items"])
        return ("bad", "Gugur langsung", f"{n_hd} pelanggaran berat menggugurkan proposal di Tahap 1",
                "Perbaiki item Hard Disqualifier dulu; tanpa itu proposal tidak dinilai sama sekali.")
    saran_cek = f"Tinjau {p} item cek manual sebelum submit." if p else \
        "Tetap periksa hal yang tak terbaca otomatis: isi scan, tanggal tanda tangan, meterai."
    if kat == "PERFECT":
        return "ok", "Sempurna", "Semua pemeriksaan administrasi terpenuhi", saran_cek
    if kat == "LAYAK":
        return "ok", "Layak", "Tidak ada item yang wajib diperbaiki", saran_cek
    if kat == "PERLU PERBAIKAN":
        judul = f"Masih ada {w} item yang wajib diperbaiki" if w else "Skor administrasi masih di bawah 85"
        saran = "Kerjakan item merah dulu" + (f", lalu tinjau {p} item cek manual." if p else ".")
        return "warn", "Perlu perbaikan", judul, saran
    return ("bad", "Tidak lolos", "Banyak ketentuan panduan belum terpenuhi",
            f"Skor administrasi di bawah 60. Mulai dari {w} item yang wajib diperbaiki.")


def _skor_teks(structured: dict) -> str:
    return "—" if structured["is_gugur"] else fmt(structured["overall"]["skor"])


# ─── Tampilan satu proposal ────────────────────────────────────────────────────

def hero_html(structured: dict, counts: dict) -> str:
    kls, badge, judul, saran = verdict(structured, counts)
    meta = " · ".join(_e(x) for x in [
        f"PKM-{structured['jenis_pkm']}" if structured.get("jenis_pkm") else "Jenis PKM tidak terdeteksi",
        structured.get("file_name") or "",
        f"{fmt(structured['file_size_mb'], 2)} MB",
    ] if x)
    if structured.get("judul"):
        judul_html = f'<div class="hero-judul">{_e(structured["judul"])}</div>'
    else:
        judul_html = ('<div class="hero-judul kosong">Judul tidak terdeteksi otomatis. Isi judul di form '
                      'supaya pemeriksaan judul (modul Identitas) bisa dinilai.</div>')
    stats = "".join(
        f'<div class="stat {STATUS[s]["cls"]}"><b>{counts[s]}</b><span>{STATUS[s]["label"]}</span></div>'
        for s in ("TIDAK_LULUS", "PERINGATAN", "LULUS")
    )
    return (
        f'<div class="hero {kls}"><div class="hero-main">'
        f'<span class="badge">{badge}</span>'
        f'<div class="hero-title">{_e(judul)}</div><div class="hero-sub">{_e(saran)}</div>'
        f'<div class="hero-meta">{meta}</div>{judul_html}</div>'
        f'<div class="hero-score"><b>{_skor_teks(structured)}</b><span>skor administrasi / 100</span></div>'
        f'</div><div class="stats">{stats}</div>'
    )


def modul_grid_html(structured: dict) -> str:
    cards = []
    for i, m in enumerate(semua_modul(structured)):
        c = hitung_modul(m)
        kls = kelas_status(c)
        bagian = []
        if c["TIDAK_LULUS"]:
            bagian.append(f'{c["TIDAK_LULUS"]} {"penyebab gugur" if m["is_hd"] else "wajib"}')
        if c["PERINGATAN"]:
            bagian.append(f'{c["PERINGATAN"]} cek manual')
        foot = " · ".join(bagian) or f'{c["LULUS"]} pemeriksaan sesuai'
        if m["is_hd"]:
            kicker, skor_txt = "Fase 1 · langsung gugur", ("Gugur" if c["TIDAK_LULUS"] else "Lolos")
            lebar = 100
        else:
            kicker, skor_txt, lebar = f"Modul {i}", f'{fmt(m["skor"], 0)}%', m["skor"]
        cards.append(
            f'<div class="mod {kls}"><div class="mod-kicker">{kicker}</div>'
            f'<div class="mod-top"><span class="mod-name">{_e(modul_pendek(m["nama"]))}</span>'
            f'<span class="mod-score">{skor_txt}</span></div>'
            f'<div class="bar"><i style="width:{lebar:.0f}%"></i></div>'
            f'<div class="mod-foot">{_e(foot)}</div></div>'
        )
    return f'<div class="mods">{"".join(cards)}</div>'


def issue_html(item: dict) -> str:
    m = STATUS[item["status"]]
    detail = f'<div class="issue-detail">{_e(item["detail"])}</div>' if item.get("detail") else ""
    return (
        f'<div class="issue {m["cls"]}"><div class="issue-head"><span class="kode">{_e(item["kode"])}</span>'
        f'<span class="issue-title">{_e(item["deskripsi"])}</span>{_hal(item)}</div>'
        f'<div class="issue-mod">{_e(modul_pendek(item["modul"]))}</div>{detail}{_catatan(item.get("catatan", []))}</div>'
    )


def row_html(item: dict) -> str:
    detail = f'<div class="row-detail">{_e(item["detail"])}</div>' if item.get("detail") else ""
    return (
        f'<div class="row">{pill(item["status"])}<div class="row-body">'
        f'<div class="row-title"><span class="kode">{_e(item["kode"])}</span> {_e(item["deskripsi"])} {_hal(item)}</div>'
        f'{detail}{_catatan(item.get("catatan", []), batas=3)}</div></div>'
    )


def _section(judul: str, sub: str, cards: list[str]) -> str:
    return (f'<div class="sec"><h4>{_e(judul)}</h4><span class="muted">{_e(sub)}</span></div>'
            + "".join(cards))


def render_hasil(structured: dict, text_report: str, key: str):
    """Tampilan lengkap hasil satu proposal: ringkasan, skor modul, daftar perbaikan, rincian."""
    counts = hitung_status(structured)
    _html(hero_html(structured, counts) + modul_grid_html(structured))

    items = flatten_items(structured)
    wajib = [i for i in items if i["status"] == "TIDAK_LULUS"]
    cek = [i for i in items if i["status"] == "PERINGATAN"]

    st.write("")
    tab_fix, tab_all, tab_txt = st.tabs([
        f"Yang perlu diperbaiki ({len(wajib) + len(cek)})",
        "Rincian per modul",
        "Laporan teks",
    ])

    with tab_fix:
        if not wajib and not cek:
            _html('<div class="empty">Tidak ada temuan administrasi. Tetap periksa manual hal yang tidak '
                  'bisa dibaca otomatis (isi halaman scan, tanggal tanda tangan, meterai) dan perkuat '
                  'substansi gagasan.</div>')
        else:
            html_parts = []
            if structured["is_gugur"]:
                hd = [i for i in wajib if i["is_hd"]]
                lain = [i for i in wajib if not i["is_hd"]]
                html_parts.append(_section("Penyebab gugur", f"{len(hd)} item · perbaiki ini dulu",
                                           [issue_html(i) for i in hd]))
                if lain:
                    html_parts.append(_section("Wajib diperbaiki lainnya", f"{len(lain)} item",
                                               [issue_html(i) for i in lain]))
            elif wajib:
                html_parts.append(_section("Wajib diperbaiki", f"{len(wajib)} item · melanggar panduan",
                                           [issue_html(i) for i in wajib]))
            if cek:
                html_parts.append(_section("Cek manual", f"{len(cek)} item · pastikan sendiri",
                                           [issue_html(i) for i in cek]))
            _html("".join(html_parts))

    with tab_all:
        sembunyi = st.toggle("Sembunyikan pemeriksaan yang sudah sesuai", key=f"{key}_sembunyi")
        for i, m in enumerate(semua_modul(structured)):
            c = hitung_modul(m)
            kls = kelas_status(c)
            ringkas = []
            if c["TIDAK_LULUS"]:
                ringkas.append(f'{c["TIDAK_LULUS"]} wajib')
            if c["PERINGATAN"]:
                ringkas.append(f'{c["PERINGATAN"]} cek manual')
            skor = "" if m["is_hd"] else f' — {fmt(m["skor"], 0)}%'
            nama = m["nama"] if not m["is_hd"] else "Fase 1: Hard Disqualifier"
            label = f'{nama}{skor}' + (f'  ·  {", ".join(ringkas)}' if ringkas else "  ·  semua sesuai")
            tampil = [it for it in m["items"] if not (sembunyi and it["status"] == "LULUS")]
            with st.expander(label, icon=EMOJI_KELAS[kls], expanded=bool(sembunyi and tampil)):
                if tampil:
                    _html("".join(row_html(it) for it in tampil))
                else:
                    st.caption("Semua pemeriksaan di modul ini sudah sesuai.")

    with tab_txt:
        st.download_button("Unduh laporan (.txt)", data=text_report, icon=":material/download:",
                           file_name=_nama_laporan(structured.get("file_name")), mime="text/plain",
                           key=f"{key}_unduh")
        st.code(text_report, language="text")

    st.caption("Checker ini hanya menilai administrasi (Tahap 1). Lolos administrasi belum tentu didanai: "
               "Tahap 2 menilai kreativitas gagasan, urgensi masalah, dan ketepatan IPTEK.")


def _nama_laporan(file_name) -> str:
    stem = (file_name or "proposal").rsplit(".", 1)[0]
    return f"laporan_{stem}.txt"


# ─── Mode komparasi ────────────────────────────────────────────────────────────

GRUP_INFO = {
    "memburuk": ("bad", "Memburuk atau baru muncul", "sebelumnya sesuai atau lebih ringan"),
    "tetap": ("warn", "Masih bermasalah", "belum berubah"),
    "membaik": ("ok", "Membaik", "dari wajib jadi cek manual"),
    "beres": ("ok", "Sudah beres", "sekarang sesuai"),
}


def _kelas_versi(structured: dict) -> str:
    return verdict(structured, hitung_status(structured))[0]


def _delta(now, prev, d: int = 1) -> str:
    if now is None or prev is None:
        return ""
    diff = round(now - prev, d)
    if diff > 0:
        return f'<span class="delta up">▲ {fmt(diff, d)}</span>'
    if diff < 0:
        return f'<span class="delta down">▼ {fmt(-diff, d)}</span>'
    return '<span class="delta same">= 0</span>'


def _skor(structured: dict):
    return None if structured["is_gugur"] else structured["overall"]["skor"]


def _hitung(n: int, teks: str, warna: str) -> str:
    gaya = f' style="color:var(--{warna})"' if n else ' class="muted"'
    return f'<span{gaya}>{n} {teks}</span>'


def versi_cards_html(versions: list[dict]) -> str:
    cards = []
    for i, v in enumerate(versions):
        s = v["structured"]
        c = hitung_status(s)
        kls, badge, _, _ = verdict(s, c)
        delta = _delta(_skor(s), _skor(versions[i - 1]["structured"])) if i else ""
        skor = "Gugur" if s["is_gugur"] else f'{fmt(s["overall"]["skor"])}<small>/100</small>'
        cards.append(
            f'<div class="ver {kls}"><div class="ver-label">{_e(v["label"])}</div>'
            f'<div class="ver-file" title="{_e(v["file_name"])}">{_e(v["file_name"])}</div>'
            f'<span class="badge">{badge}</span><div class="ver-score">{skor}{delta}</div>'
            f'<div class="ver-counts">{_hitung(c["TIDAK_LULUS"], "wajib", "bad")}'
            f' · {_hitung(c["PERINGATAN"], "cek manual", "warn")}</div></div>'
        )
    return f'<div class="vers">{"".join(cards)}</div>'


def _ubah_html(row: dict, grup: str, lbl_dari: str) -> str:
    a, b = row["sebelum"], row["sesudah"]
    kls = STATUS[b["status"]]["cls"] if grup != "beres" else "ok"
    la = STATUS[a["status"]]["label"] if a else "Belum diperiksa"
    trans = (f'<div class="trans">{pill(a["status"] if a else None)}<span>{la}</span><span class="arr">→</span>'
             f'{pill(b["status"])}<span>{STATUS[b["status"]]["label"]}</span></div>')
    if grup == "beres":
        body = (f'<div class="issue-detail muted">Sebelumnya: {_e(a.get("detail", ""))}</div>'
                if a and a.get("detail") else "")
    else:
        body = (f'<div class="issue-detail">{_e(b.get("detail", ""))}</div>' if b.get("detail") else "")
        body += _catatan(b.get("catatan", []))
        if grup == "tetap" and row["rincian_berubah"]:
            na, nb = len(a.get("catatan", [])), len(b.get("catatan", []))
            if na != nb:
                arah = "berkurang" if nb < na else "bertambah"
                body += f'<div class="hint">Rincian temuan {arah}: {na} → {nb}.</div>'
            else:
                body += f'<div class="hint">Rinciannya berbeda dari {_e(lbl_dari)}.</div>'
        if a and row["rincian_berubah"]:
            body += (f'<details class="prev"><summary>Lihat rincian di {_e(lbl_dari)}</summary>'
                     f'<div class="prev-body">{_e(a.get("detail", ""))}{_catatan(a.get("catatan", []), 3)}</div></details>')
    return (f'<div class="issue {kls}"><div class="issue-head"><span class="kode">{_e(row["kode"])}</span>'
            f'<span class="issue-title">{_e(row["deskripsi"])}</span></div>'
            f'<div class="issue-mod">{_e(modul_pendek(row["modul"]))}</div>{trans}{body}</div>')


def perubahan_html(versions: list[dict], i_dari: int, i_ke: int) -> str:
    grup = ringkas_perubahan(versions, i_dari, i_ke)
    lbl_a, lbl_b = versions[i_dari]["label"], versions[i_ke]["label"]
    n = {g: len(grup[g]) for g in GRUP_URUTAN}

    bagian = []
    if n["beres"] + n["membaik"]:
        bagian.append(f'<b>{n["beres"] + n["membaik"]} membaik</b>')
    if n["memburuk"]:
        bagian.append(f'<b style="color:var(--bad)">{n["memburuk"]} memburuk</b>')
    if n["tetap"]:
        bagian.append(f'{n["tetap"]} masih bermasalah')
    lead = (f'Dari <b>{_e(lbl_a)}</b> ke <b>{_e(lbl_b)}</b>: ' + ", ".join(bagian) + "."
            if bagian else f'Tidak ada perubahan status dari <b>{_e(lbl_a)}</b> ke <b>{_e(lbl_b)}</b>.')

    strip = "".join(
        f'<div class="{GRUP_INFO[g][0]}"><b>{n[g]}</b><span>{GRUP_INFO[g][1]}</span></div>' for g in GRUP_URUTAN
    )
    out = [f'<div class="lead">{lead}</div><div class="chg">{strip}</div>']
    for g in GRUP_URUTAN:
        if not grup[g]:
            continue
        kls, judul, sub = GRUP_INFO[g]
        sub_teks = f'{n[g]} item · {sub}' + (f" sejak {lbl_a}" if g == "tetap" else "")
        out.append(_section(judul, sub_teks, [_ubah_html(r, g, lbl_a) for r in grup[g]]))
    if not any(n.values()):
        out.append('<div class="empty">Kedua versi sama-sama tidak punya temuan.</div>')
    return "".join(out)


def skor_tabel_html(versions: list[dict]) -> str:
    head = "".join(f"<th>{_e(v['label'])}</th>" for v in versions)
    rows = []

    # Baris skor keseluruhan + Hard Disqualifier
    sel = []
    for i, v in enumerate(versions):
        s = v["structured"]
        prev = _skor(versions[i - 1]["structured"]) if i else None
        isi = "Gugur" if s["is_gugur"] else fmt(s["overall"]["skor"])
        sel.append(f'<td><span class="cell {_kelas_versi(s)}">{isi}</span>{_delta(_skor(s), prev)}</td>')
    rows.append(f'<tr class="utama"><td>Skor keseluruhan</td>{"".join(sel)}</tr>')

    sel = []
    for v in versions:
        hd = semua_modul(v["structured"])[0]
        c = hitung_modul(hd)
        isi = "Gugur" if c["TIDAK_LULUS"] else "Lolos"
        sel.append(f'<td><span class="cell {kelas_status(c)}">{isi}</span></td>')
    rows.append(f'<tr><td>Hard Disqualifier</td>{"".join(sel)}</tr>')

    for r in skor_modul(versions)[1:]:
        sel = []
        for i, (skor, v) in enumerate(zip(r["skor"], versions)):
            if skor is None:
                sel.append('<td><span class="cell na">–</span></td>')
                continue
            m = next(m for m in semua_modul(v["structured"]) if m["nama"] == r["nama"])
            prev = r["skor"][i - 1] if i else None
            sel.append(f'<td><span class="cell {kelas_status(hitung_modul(m))}">{fmt(skor, 0)}</span>'
                       f'{_delta(skor, prev, 0)}</td>')
        rows.append(f'<tr><td>{_e(r["nama"])}</td>{"".join(sel)}</tr>')

    return (f'<table class="skor"><thead><tr><th>Modul</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def matriks_html(versions: list[dict], rows: list[dict]) -> str:
    n = len(versions)
    head = ('<div class="mx-head"><span>Kode</span><span>Pemeriksaan</span>'
            + "".join(f'<span class="v" title="{_e(v["label"])}">{_e(v["label"])}</span>' for v in versions)
            + "</div>")
    out, modul_aktif = [head], None
    for r in rows:
        if r["modul"] != modul_aktif:
            modul_aktif = r["modul"]
            out.append(f'<div class="mx-group">{_e(modul_aktif)}</div>')
        pills = "".join(f'<span class="pc">{pill(it["status"] if it else None)}</span>' for it in r["per_versi"])
        detail = []
        for v, it in zip(versions, r["per_versi"]):
            if it is None:
                isi = '<span class="muted">Tidak diperiksa di versi ini.</span>'
                st_ = None
            else:
                st_ = it["status"]
                isi = _e(it.get("detail") or STATUS[st_]["label"]) + _catatan(it.get("catatan", []), 3)
            detail.append(f'<div class="mx-v"><div class="mx-vh">{pill(st_)}{_e(v["label"])}</div>{isi}</div>')
        out.append(
            f'<details><summary><span class="kode">{_e(r["kode"])}</span><span class="desc">{_e(r["deskripsi"])}</span>'
            f'{pills}</summary><div class="mx-detail">{"".join(detail)}</div></details>'
        )
    if len(rows) == 0:
        out.append('<div class="empty" style="margin-top:10px">Tidak ada pemeriksaan untuk filter ini.</div>')
    return f'<div class="mx" style="--n:{n}">{"".join(out)}</div>'


def render_banding(versions: list[dict], key: str):
    """
    versions: [{label, file_name, structured, text_report}] berurutan dari versi terlama.
    """
    n = len(versions)
    _html(versi_cards_html(versions))
    st.write("")

    tab_ubah, tab_skor, tab_mx, tab_det = st.tabs(
        ["Apa yang berubah", "Skor per modul", "Semua pemeriksaan", "Detail per versi"]
    )
    labels = [v["label"] for v in versions]

    with tab_ubah:
        if n > 2:
            c1, c2, _ = st.columns([1, 1, 2])
            i_dari = c1.selectbox("Dari versi", range(n), index=0, format_func=lambda i: labels[i],
                                  key=f"{key}_dari")
            i_ke = c2.selectbox("Ke versi", range(n), index=n - 1, format_func=lambda i: labels[i],
                                key=f"{key}_ke")
        else:
            i_dari, i_ke = 0, 1
        if i_dari == i_ke:
            st.info("Pilih dua versi yang berbeda untuk dibandingkan.")
        else:
            _html(perubahan_html(versions, i_dari, i_ke))

    with tab_skor:
        st.caption("Angka kecil di samping skor = selisih dibanding versi sebelumnya. "
                   "Warna mengikuti temuan terparah di modul itu.")
        _html(skor_tabel_html(versions))

    with tab_mx:
        semua = baris_matriks(versions)
        filters = {
            "berubah": (f"Berubah antarversi", [r for r in semua if berubah_antarversi(r)]),
            "masalah": (f"Masih bermasalah di {labels[-1]}", [r for r in semua if bermasalah_terakhir(r)]),
            "semua": ("Semua", semua),
        }
        pilih = st.segmented_control(
            "Tampilkan", list(filters), default="berubah", key=f"{key}_filter",
            format_func=lambda k: f"{filters[k][0]} ({len(filters[k][1])})",
        ) or "berubah"
        _html(legenda_html(inline=True)
              + '<div class="hint" style="margin-bottom:6px">Klik satu baris untuk melihat rincian di tiap versi.</div>'
              + matriks_html(versions, filters[pilih][1]))
        st.write("")
        st.download_button("Unduh matriks (.csv)", data=matriks_csv(versions), icon=":material/download:",
                           file_name="perbandingan_pkm.csv", mime="text/csv", key=f"{key}_csv")

    with tab_det:
        i = st.segmented_control("Versi", range(n), default=n - 1, format_func=lambda i: labels[i],
                                 key=f"{key}_detail")
        i = n - 1 if i is None else i
        v = versions[i]
        render_hasil(v["structured"], v["text_report"], key=f"{key}_det{i}")
