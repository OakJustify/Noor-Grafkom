"""All narrative text for NÜR lives here as data, never in the game loop.

The text is deliberately split into three layers:

* ``FRAGMENTS`` are the player's unstable record of factual events.
* ``INTRUSIONS`` are out-of-context captions that do not change any puzzle.
* ``CUTSCENES`` are the static illustrated ending frames.

Three anchor lines are guaranteed to appear in a fixed order; everything else
is drawn from a seeded RNG so a run can be reproduced exactly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fragment:
    key: str
    title: str
    true_text: str
    false_text: str
    motif: str
    room: int
    x: float
    y: float


FRAGMENTS: tuple[Fragment, ...] = (
    Fragment(
        "photo",
        "FOTO / 14.00",
        "Kau berdiri di depan pintu dengan kunci di tangan. Jam di dinding menunjukkan 14.00.",
        "Kau berdiri di depan pintu tanpa kunci. Jam di dinding menunjukkan 04.00.",
        "dua nada: rumah",
        0,
        560,
        367,
    ),
    Fragment(
        "key",
        "LABEL KUNCI",
        "Laci dapur. Kunci kecil bertuliskan nama yang tidak lagi kau kenali.",
        "Laci dapur kosong. Tulisan itu adalah tulisan tanganmu sendiri.",
        "dua nada: ibu",
        10,
        3000,
        405,
    ),
    Fragment(
        "recipe",
        "RESEP / TIGA SENDOK",
        "Tiga sendok gula. Dua cangkir air. Satu orang pulang sebelum air mendidih.",
        "Tiga sendok garam. Dua cangkir air. Satu orang tidak pernah pulang.",
        "dua nada: dapur",
        16,
        3000,
        405,
    ),
    Fragment(
        "letter",
        "SURAT TANPA ALAMAT",
        "'Aku masih ingat jalan pulangnya.' — ditulis di bawah foto yang sama.",
        "'Aku tidak ingat siapa yang menuliskan ini.' — tulisan tangan yang sama.",
        "dua nada: diri",
        25,
        3000,
        405,
    ),
)

ANCHOR_LINES: tuple[str, ...] = (
    "Rumah ini lebih sunyi dari biasanya.",
    "sepertinya kamu lupa menutup pintu",
    "kau membunuhku!",
)

INTRUSIONS: tuple[str, ...] = ANCHOR_LINES + (
    "Aku sudah bilang tadi... kan?",
    "Jamnya berhenti, tapi terus berjalan.",
    "Itu bukan nama kami. Itu nama yang kauberikan.",
    "Kau kembali lebih awal dari biasanya.",
    "Jangan bilang aku yang menyimpan kunci.",
    "Ibu menyuruhmu pulang. Atau aku?",
    "Ada seseorang di belakangmu yang mengangguk.",
    "Kau tidak pernah menyalakan lilin itu.",
    "Tadi ada tiga kursi. Sekarang empat.",
    "Dengarkan. Itu bukan kaki langkahmu.",
    "Wajah di foto itu berubah setiap kau berkedip.",
    "Kau sudah memberitahuku. Dua kali. Mungkin tiga.",
)

BOSS_LINES: tuple[str, ...] = (
    "Sebut namaku.",
    "Sebut namaku dengan benar.",
    "sepertinya kamu lupa menutup pintu",
    "kau membunuhku!",
    "Itu bukan aku. Itu yang kau ingat.",
    "Berhenti menyebut nama. Berhenti.",
)


@dataclass(frozen=True)
class Cutscene:
    key: str
    title: str
    lines: tuple[str, ...]


CUTSCENES: tuple[Cutscene, ...] = (
    Cutscene(
        "phase1_warmth",
        "I / RUMAH YANG MASIH TERANG",
        (
            "Di awal, cahaya cukup untuk melihat seluruh ruangan.",
            "Meja, kursi, kunci di laci. Semua punya tempat.",
            "Kau meletakkan lilin di ambang pintu dan keluar.",
        ),
    ),
    Cutscene(
        "phase2_fractured",
        "II / YANG BERUBAH",
        (
            "Kau kembali, tapi pintunya tidak lagi ada di tempat yang sama.",
            "Foto masih menampilkan senyum yang sama. Jamnya tidak.",
            "Lilin itu lebih pendek. Kau tidak ingat meniupnya.",
        ),
    ),
    Cutscene(
        "phase3_labyrinth",
        "III / YANG TIDAK BISA DINAMAI",
        (
            "Setiap ingatan yang kaukumpulkan mengambil sedikit penglihatan.",
            "Kau memberi nama pada bayangan. Bayangan itu menjawab.",
            "Kunci, resep, surat — semuanya ditulis oleh tangan yang sama.",
        ),
    ),
    Cutscene(
        "phase4_end",
        "IV / SISA CAHAYA",
        (
            "Kau berhenti menyebut nama. Tidak ada yang menang.",
            "Lilin habis, tetapi ada garis terang di bawah pintu.",
            "Bukan untuk melihat semuanya. Cukup untuk melangkah satu kali lagi.",
        ),
    ),
)


OKIR_EPILOGUE = (
    "Cahaya tidak pernah kembali seperti semula.",
    "Itu bukan kehilangan. Itu satu-satunya bukti bahwa kau tetap melangkah.",
)
