"""Authored traversal: memory shelves, safe blade routes, weight relay and rope crossing."""

from __future__ import annotations

from dataclasses import dataclass, replace

from echo_game.levels import Level, Rect
from .quests import QuestPlan
from .journey import build_journey


@dataclass(frozen=True)
class ThreatSpawn:
    x: float
    y: float
    patrol: float
    motif: str
    minimum_stage: int = 0


@dataclass(frozen=True)
class Echo:
    """A true-memory echo inside the boss arena."""

    x: float
    y: float
    label: str


@dataclass(frozen=True)
class NurLevel:
    name: str
    level: Level
    threats: tuple[ThreatSpawn, ...] = ()
    echoes: tuple[Echo, ...] = ()
    candle: tuple[float, float] | None = None
    environment: str = ""
    act: int = 1
    quest: QuestPlan | None = None


SLICE_LEVELS: tuple[NurLevel, ...] = (
    NurLevel(
        "RUMAH",
        Level(
            "01 / RUMAH",
            "Kau pulang. Lilin masih menyala.",
            "",
            1500,
            (130, 430),
            (1410, 430),
            (Rect(-80, 460, 1660, 160), Rect(500, 402, 160, 18), Rect(760, 388, 190, 18)),
            crates=((470, 431, 54, 6),),
        ),
        threats=(),
    ),
    NurLevel(
        "KORIDOR",
        Level(
            "02 / KORIDOR",
            "Pintunya ada di ujung. Atau dulu ada.",
            "",
            1700,
            (130, 430),
            (1600, 430),
            (Rect(-80, 460, 1860, 160), Rect(590, 400, 110, 18),
             Rect(700, 356, 200, 18), Rect(1090, 400, 100, 18), Rect(1190, 356, 200, 18)),
            saws=((760, 427, 28, 55, 0.7), (1240, 427, 30, 70, 0.55)),
        ),
        threats=(ThreatSpawn(1080, 425, 120, "dua nada: ibu", 0),),
    ),
    NurLevel(
        "DAPUR",
        Level(
            "03 / DAPUR",
            "Sesuatu harus tetap di sana agar pintu terbuka.",
            "",
            1700,
            (130, 430),
            (1640, 430),
            (Rect(-80, 460, 1860, 160), Rect(1180, 350, 240, 18)),
            crates=((570, 431, 58, 7),),
            gate=Rect(1120, 250, 28, 210),
            plate=Rect(860, 451, 190, 9),
        ),
        threats=(
            ThreatSpawn(700, 425, 150, "dua nada: dapur", 0),
            ThreatSpawn(1360, 425, 95, "dua nada: rumah", 1),
        ),
        candle=(1010, 418),
    ),
    NurLevel(
        "LOTENG",
        Level(
            "04 / LOTENG",
            "Kertas-kertas itu berubah ketika kau membacanya lagi.",
            "",
            1700,
            (130, 430),
            (1610, 430),
            (Rect(-80, 460, 840, 160), Rect(980, 460, 800, 160),
             Rect(600, 398, 160, 18), Rect(980, 420, 160, 18),
             Rect(1180, 350, 220, 18)),
            rope=(825, 125, 10, 28),
            saws=((1280, 427, 26, 55, 0.6),),
        ),
        threats=(
            ThreatSpawn(520, 425, 130, "dua nada: diri", 0),
            ThreatSpawn(900, 425, 105, "dua nada: ibu", 1),
            ThreatSpawn(1450, 425, 140, "dua nada: rumah", 2),
        ),
    ),
    NurLevel(
        "YANG MENYEBUT NAMA",
        Level(
            "05 / YANG MENYEBUT NAMA",
            "Jangan jawab. Berhenti menyebut nama.",
            "",
            1600,
            (140, 430),
            (1520, 430),
            (Rect(-80, 460, 1760, 160), Rect(235, 400, 90, 18),
             Rect(325, 330, 155, 18), Rect(1070, 400, 90, 18), Rect(1160, 330, 160, 18)),
        ),
        threats=(
            ThreatSpawn(520, 425, 100, "dua nada: rumah", 2),
            ThreatSpawn(1300, 425, 100, "dua nada: diri", 3),
        ),
        echoes=(Echo(390, 292, "kunci"), Echo(800, 405, "resep"), Echo(1230, 292, "surat")),
    ),
)

NUR_LEVELS = (SLICE_LEVELS[:4] + build_journey(NurLevel, ThreatSpawn)
              + (replace(SLICE_LEVELS[4], act=6, level=replace(SLICE_LEVELS[4].level,
                          title="29 / YANG MENYEBUT NAMA")),))


def room_count() -> int:
    return len(NUR_LEVELS)
