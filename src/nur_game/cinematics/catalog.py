"""Subtitle-only adaptation of *Noor — Yang masih di sini*, story draft 1.

Durations are seconds; ``sfx`` is optional non-verbal foley metadata, never a
voice asset. Speaker identities remain neutral until the real-world finale.
The diagnosis belongs only to the closing cards, outside the scene sequence.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cue:
    duration: float
    shot: str
    text: str = ""
    speaker: str = ""
    sfx: str = ""


@dataclass(frozen=True)
class Scene:
    key: str
    title: str
    cues: tuple[Cue, ...]
    kind: str = "memory"

    @property
    def duration(self) -> float:
        return sum(cue.duration for cue in self.cues)


SCENES: dict[str, Scene] = {
    "CS00": Scene("CS00", "Jalan yang terang", (
        Cue(5, "morning_lane"),
        Cue(5, "lantern_pickup", sfx="key"),
        Cue(5, "red_fence", "Ikuti jalan."),
    ), "opening"),
    "CS01": Scene("CS01", "Simpul yang miring", (
        Cue(3, "ribbon_hands", sfx="cloth"),
        Cue(4, "ribbon_hands", "Yang ini miring.", "ANAK"),
        Cue(5, "ribbon_school", "Kepalamu juga dari tadi tidak bisa diam.", "PEREMPUAN"),
        Cue(3, "ribbon_school", "Sudah?", "ANAK"),
        Cue(5, "ribbon_school", "Sudah. Tasnya jangan ketinggalan.", "PEREMPUAN"),
        Cue(3, "bag_door", "Nah, kan.", "PEREMPUAN"),
        Cue(2, "ribbon_hands", sfx="cloth"),
    )),
    "CS02": Scene("CS02", "Cangkir di sebelah kanan", (
        Cue(3, "mug_detail", sfx="mug"),
        Cue(4, "mug_drawing", "Ini rumah kita.", "ANAK"),
        Cue(4, "mug_drawing", "Pohonnya tinggi sekali.", "PEREMPUAN"),
        Cue(6, "mug_drawing", "Biar kelihatan dari jauh. Kalau pulang, tinggal cari pohonnya.", "ANAK"),
        Cue(6, "drawing_wall", "Ya sudah. Jangan ditutup kalender, nanti rumahnya hilang.", "PEREMPUAN"),
        Cue(3, "mug_detail", "Masih panas?", "ANAK"),
        Cue(2, "mug_detail", "Masih.", "PEREMPUAN"),
        Cue(2, "mug_detail", sfx="mug"),
    )),
    "CS03": Scene("CS03", "Jalan yang biasanya", (
        Cue(5, "crossroad_wait"),
        Cue(5, "crossroad_wait", "Tadi... lewat sini.", "PEREMPUAN"),
        Cue(5, "crossroad_together", "Bu, aku cari dari tadi.", "PEREMPUAN MUDA"),
        Cue(5, "crossroad_wait", "Pohonnya dipindah?", "PEREMPUAN"),
        Cue(7, "crossroad_together", "Rumahnya lewat sini. Kita jalan bareng, ya?", "PEREMPUAN MUDA"),
        Cue(3, "crossroad_together", "Dekat?", "PEREMPUAN"),
        Cue(3, "crossroad_together", "Dekat.", "PEREMPUAN MUDA"),
        Cue(2, "crossroad_empty"),
    )),
    "CS04": Scene("CS04", "Foto di depan rumah", (
        Cue(4, "photo_pose"),
        Cue(6, "photo_pose", "Geser sedikit. Pohonnya ikut, ya.", "DARI LUAR BINGKAI"),
        Cue(4, "photo_pose", "Bu, lihat sini.", "ANAK"),
        Cue(3, "photo_print", sfx="camera"),
        Cue(7, "photo_fold", "Ini anak siapa?", "PEREMPUAN TUA"),
        Cue(4, "photo_fold"),
        Cue(5, "photo_fading", "Sepertinya pernah ke sini.", "PEREMPUAN TUA"),
        Cue(2, "photo_fading"),
    )),
    "CS05": Scene("CS05", "Resep yang dibaca lagi", (
        Cue(6, "recipe_read"),
        Cue(5, "recipe_read", "Sudah dimasukkan?", "PEREMPUAN TUA"),
        Cue(5, "recipe_stir", "Gulanya sudah. Tinggal diaduk.", "PEREMPUAN MUDA"),
        Cue(4, "recipe_read", "Yang ini?", "PEREMPUAN TUA"),
        Cue(6, "recipe_stir", "Sudah, Bu. Tehnya boleh dicoba dulu.", "PEREMPUAN MUDA"),
        Cue(5, "recipe_tea", "Kamu bikin terlalu panas.", "PEREMPUAN TUA"),
        Cue(5, "recipe_tea", "Kita tunggu sebentar.", "PEREMPUAN MUDA"),
        Cue(4, "recipe_stir", sfx="spoon"),
    )),
    "CS06": Scene("CS06", "Nama pada kain", (
        Cue(5, "stitch_hands", sfx="cloth"),
        Cue(5, "stitch_hands", "Yang ini dibuka saja?", "ANAK"),
        Cue(7, "stitch_hands", "Tidak usah. Nanti kamu tahu yang mana buatanmu.", "PEREMPUAN"),
        Cue(6, "cloth_wait", "Anak saya belum pulang sekolah.", "PEREMPUAN TUA"),
        Cue(5, "cloth_door", "Ibu sedang menunggu dia?", "PEREMPUAN MUDA"),
        Cue(5, "cloth_wait", "Biasanya sudah sampai.", "PEREMPUAN TUA"),
        Cue(5, "cloth_seated", "Aku duduk di sini dulu, ya.", "PEREMPUAN MUDA"),
        Cue(2, "cloth_seated"),
    )),
    "CS07": Scene("CS07", "Ujung jalan", (
        Cue(3, "void_path", "Tadi ada rumah di sini.", "PENGEMBARA"),
        Cue(3, "void_fragments"),
        Cue(3, "void_dimming"),
        Cue(3, "void_black"),
    ), "void"),
    "CS08": Scene("CS08", "Di sebelah kanan meja", (
        Cue(5, "real_mug", sfx="mug"),
        Cue(5, "real_arrival", "Pagi, Bu.", "DARA"),
        Cue(7, "real_faces", "Kamu siapa?", "NUR"),
        Cue(4, "real_faces"),
        Cue(7, "real_faces", "Aku Dara, Bu. Anak Ibu.", "DARA"),
        Cue(6, "real_cloth", "Dara masih kecil.", "NUR"),
        Cue(6, "real_faces", "Aku yang dulu Ibu antar sekolah.", "DARA"),
        Cue(5, "real_seated", "Boleh aku duduk di sini?", "DARA"),
        Cue(3, "real_seated", "Boleh.", "NUR"),
        Cue(5, "real_tea", "Ini pakai gula?", "NUR"),
        Cue(5, "real_tea", "Sedikit. Ibu mau coba?", "DARA"),
        Cue(4, "real_tea", "Masih panas.", "NUR"),
        Cue(4, "real_tea", "Kita tunggu.", "DARA"),
        Cue(6, "real_cloth", "Kainnya mau dijahit?", "NUR"),
        Cue(6, "real_cloth", "Tidak, Bu. Aku bawa saja.", "DARA"),
        Cue(5, "real_hands", sfx="cloth"),
        Cue(7, "real_wide"),
    ), "realworld"),
}

CLOSING_LINES: tuple[str, ...] = (
    "Nur hidup dengan penyakit Alzheimer.",
    "Dunia yang memudar dalam Noor adalah gambaran simbolis sebuah pengalaman kehilangan ingatan. Kisah Nur adalah fiksi dan tidak mewakili pengalaman setiap orang dengan Alzheimer.",
    "Kesulitan mengenali seseorang bukan berarti ia tidak lagi layak ditemani.",
)
