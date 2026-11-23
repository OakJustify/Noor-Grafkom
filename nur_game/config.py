"""Shared constants for NÜR. No gameplay logic lives here."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SIZE = (960, 540)
FPS = 60

TITLE = "NÜR"
SUBTITLE = "Pengembangan Game Petualangan 2D Sederhana Berbasis Grafika Komputer dengan Vector Art, Parallax, dan Efek Pencahayaan sebagai Media Penyampaian Pesan Harapan di Tengah Kegelapan"

AUDIO_DIR = ROOT / "assets" / "nur" / "audio"
CUTSCENE_DIR = ROOT / "assets" / "nur" / "cutscene"
FONT_DIR = ROOT / "assets" / "fonts"
SAVE_PATH = ROOT / "saves" / "nur.json"

# Almost-monochrome palette. Warm wax is the only colour the player owns;
# dark red appears only as a bodily suggestion, never as a gore texture.
VOID = (4, 5, 7)
INK = (10, 12, 15)
ASH = (25, 27, 32)
SLATE = (46, 49, 56)
BONE = (168, 160, 146)
WAX = (204, 174, 112)
EMBER = (214, 118, 58)
BLOOD = (76, 18, 26)

# Lantern capacity falls in fixed quarters: 100 -> 75 -> 50 -> 25 -> 0.
LIGHT_STEP = 0.25
LIGHT_DECAY_PER_SECOND = 0.0032
LIGHT_FLOOR = 0.045

# Dialogue cadence shortens as the world degrades.
DIALOGUE_COOLDOWN = (9.0, 6.0, 3.5, 2.0)

THREAT_TELEGRAPH = 1.0
BOSS_ARENA_ROOM = 4

SEED = 0x4E00  # "NÜ"
