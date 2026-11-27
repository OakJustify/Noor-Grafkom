"""All tuning constants for NOOR (single source of truth)."""

# --- Display / physics ---
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
FIXED_DT = 1.0 / 60.0
TILE = 40
GRAVITY = 2000
JUMP_V = 700
MOVE_SPEED = 240
COYOTE = 0.10
JUMP_BUFFER = 0.12
JUMP_CUT = 0.5
PLAYER_W = 28
PLAYER_H = 64
INTERACT_RANGE = 60
CAMERA_LERP_X = 6.0
CAMERA_LERP_Y = 4.0
CAMERA_DEADZONE_W = 80
CAMERA_DEADZONE_H = 60
CAMERA_LOOKAHEAD = 120
SHAKE_MAX = 6
SHAKE_FREQ = 24

SPEED_MULT = [1.0, 1.0, 0.9, 0.6]  # stages 1..4 (index 0 unused-ish; use stage-1)

# --- Sanity / light ---
S_MAX = 100
S_FLOOR = 3
CAP = {  # stage: (start, end)
    1: (100, 88),
    2: (88, 65),
    3: (65, 35),
    4: (35, 8),
}
DECAY = [0.0, 0.02, 0.04, 0.07, 0.10]  # index by stage
CONTACT_COST = [0, 8, 8, 10, 12]
DEATH_COST = 10
FLARE_COST = 6
FLARE_MIN_S = 15
FLARE_RADIUS_MULT = 1.8
FLARE_DURATION = 1.0
FLARE_COOLDOWN = 8.0
STUN = [0.0, 2.0, 1.5, 1.0, 0.0]
COVER_RADIUS = 48
COVER_SIGHT_MULT = 0.4
COVER_SPEED_MULT = 0.6
R_MIN = 80
R_RANGE = 340
R_EXP = 0.8
FLICKER_BASE = 0.02
FLICKER_RANGE = 0.12
DARK_A0 = [0, 120, 160, 195, 225]
DARK_K = 0.4
DARK_MAX = 240
LIT_ONLY_THRESHOLD = 0.85
LIT_ONLY_HYST = 0.05

# --- Fragments ---
FRAGMENT_VALUE = [0, 10, 9, 8, 4]
RETENTION = [0, 150, 100, 60, 25]
GLOW_DURATION = 40.0
GLOW_DECAY_MULT = 0.4
FORGET_PENALTY_RATIO = 0.5
FORGET_PENALTY_MIN = 2
MAX_SLOTS = 6
FRAGMENT_COUNT = [0, 5, 4, 3, 1]

# --- Clock ---
CLOCK_DEADLINE = {2: 480, 3: 1200, 4: 2100}
CLOCK_FINAL = 3300
STAGE_TARGET_DURATION = [0, 300, 420, 540, 300]

# --- Monsters ---
MONSTER_SPEED = {
    "M1": (90, 150),
    "M2": (70, 130),
    "M3": (120, 120),
    "M5": (100, 180),
}
SIGHT_RADIUS = 380
NOTICE_TIME_MIN = 0.4
NOTICE_TIME_MAX = 1.0
CAPTURE_CONTACTS = 3
CAPTURE_WINDOW = 12.0
INVULN = 1.0
KNOCKBACK = 200
SPAWN_MIN_DIST = 500
DESPAWN_DIST = 1600
MAX_ACTIVE_BASE = [0, 1, 3, 6, 8]
MAX_ACTIVE_EXTRA = [0, 0, 1, 2, 4]
MAX_ACTIVE_S_THRESHOLD = [0, 0, 50, 40, 20]
CROWD_MAX = [0, 0, 0, 8, 25]
GLOBAL_ENTITY_CAP = 40
PARTICLE_CAP = 300
MERCY_SPEED_PER_DEATH = 0.10
MERCY_SPEED_MIN = 0.6
MERCY_OFFER_DEATHS = 8
MERCY_CHECKPOINT_SAFE = 3  # deaths before extra checkpoint

# --- Glitch ---
GLITCH_P = [0.0, 0.02, 0.10, 0.25, 0.50]
GLITCH_MAX_CONCURRENT = [0, 1, 2, 3, 3]
TEXT_CORRUPT_R = [(0.0, 0.05), (0.05, 0.15), (0.15, 0.40), (0.50, 1.0)]
BLANKOUT_DUR = {3: (1.0, 1.5), 4: (1.5, 2.5)}
BLANKOUT_JEDA = {3: (40, 70), 4: (25, 45)}
BLANKOUT_SAFE_DIST = 300
WHISPER_INTERVAL = [0, 90, 40, 20, 0]  # stage 4 continuous -> 0
FLASH_MAX_PER_SEC = 3

# --- Audio ---
SAMPLE_RATE = 44100
BIT_DEPTH = 16
CHANNELS = 2
PEAK_DBFS = -3
HEARTBEAT_BPM = (60, 95, 140)
MUSIC_ROOT = 55.0
MIXER_CHANNELS = 32
AMBIENCE_RAMP = 1.5  # ambience layer gain smoothing per second
STAGE_MUSIC_GAIN = 0.55  # stage music bed level relative to the music bus
CROSSFADE_SECONDS = 0.8  # bed-to-bed fade on stage changes (0 disables it)

# --- i18n / levels ---
LEVEL_MAX_JUMP = 168  # px horizontal at full speed
LEVEL_MAX_JUMP_HEIGHT = 120
LEVEL_CHECKPOINT_MAX_GAP = 3500

# --- accessibility defaults ---
DEFAULT_ACCESSIBILITY = {
    "reduce_flash": False,
    "reduce_shake": False,
    "reduce_motion": False,
    "reduce_glitch": False,
    "reduce_blankout": False,
    "reduce_loud": False,
    "text_scale": 1.0,
    "honest_prompts": False,
    "show_icon": True,
    "captions": False,
}

# stage helpers
def stage_index(stage):
    return max(1, min(4, int(stage)))