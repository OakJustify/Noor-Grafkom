# 05 — Spesifikasi teknis

Nilai di bawah adalah kontrak implementasi. Rancangan alasannya ada di
`04-design.md`; cara pengujian ada di `07-testing.md`.

## Lingkungan dan dependensi

Daftar versi resmi ada di `requirements-nur.txt` (direkomendasikan Python 3.14):

| Paket |Rentang |
|---|---|
| `pygame-ce` | ≥2,5 <3 |
| `pymunk` | ≥7 <8 |
| `numpy` | ≥2,2 <3 |
| `scipy` | ≥1,15 <2 |
| `pytest` | ≥8 <10 |

`pycairo` dipakai untuk menggambar aset vektor utama saat proses generasi.
Lingkungan pengembangan yang teruji memakai `pygame-ce 2.5.8`, SDL 2.32.10,
Python 3.14.9. Target stabil **60 FPS** pada resolusi **960×540** (`config.SIZE`,
`config.FPS`).

## Struktur dan path

```
v4/
├── assets/          # fonts, nur (audio/cutscene/sprites, CREDITS), content (JSON)
├── docs/            # dokumentasi dan bukti verifikasi
├── src/
│   ├── nur_game/    # package game; config.ROOT = parents[2]
│   ├── scripts/     # generator, validator, playtest, capture
│   └── play_nur.py  # launcher
└── tests/
    ├── nur/         # kontrak room-based v3 (baseline_game)
    └── v4/          # controller kontinu + katalog konten
```

Semua path berasal dari `src/nur_game/config.py` (`ROOT`, `CONTENT_DIR`,
`AUDIO_DIR`, `CUTSCENE_DIR`, `FONT_DIR`, `SAVE_PATH`). Modul tidak boleh memakai
path relatif terhadap direktori kerja. `pytest.ini` menetapkan
`pythonpath = src` dan `testpaths = tests`.

## Dunia dan simulasi

- 29 wilayah, total **112.360 px**, disusun `continuum.py` menjadi satu Pymunk
  space. Setiap konektor menambah jalan 720 px, lookout opsional, dan satu mesin.
- Pemain, peti, tali, gerbang, dan platform persepsi berbagi satu space;
  pergantian wilayah hanya mengubah alamat naratif.
- Perception Q bersifat edge-triggered dan global; platform collider mengikuti
  persepsi aktif.
- Parameter gerak: `WALK_SPEED 190`, `RUN_SPEED 300`, `STAMINA_DRAIN 0,26`,
  pemulihan jalan 0,08/detik, idle 0,16/detik, delay 0,9 detik, restart 0,30.
- Cahaya: `LIGHT_STEP 0,25`, `LIGHT_DECAY_PER_SECOND 0,00028`,
  `LIGHT_FLOOR 0,045`.
- `THREAT_TELEGRAPH 1,0`; boss arena di room 28; seed `0x4E00` ("NÜ").

## Format data konten (O1–O3)

Sumber kebenaran adalah `src/scripts/generate_content.py`. Output berada di
`assets/content/`; jangan mengedit file hasil generasi langsung.

| Kontrak Unity | Field JSON |
|---|---|
| `Platform_X_Y.prefab` | `assets/content/platforms/generated/Platform_X_Y.json` |
| `Obstacle_X_Y.prefab` | `assets/content/obstacles/generated/Obstacle_X_Y.json` |
| `BoxCollider2D` | `collider` / `colliders[]` berisi `type`, `rect [x,y,w,h]`, `isTrigger: false` |
| Tag & layer | `tag`, `layer {name, index}` — 7 `Standable`, 8 `Obstacle` |
| `PlatformData` | `platformData {id, platformType, maxStandAngle: 45, isStable: true, creakSound}` |
| `ObstacleData` | `obstacleData {obstacleType, trippingChance, noiseLevel, canBeCleared, clearTime}` |
| Visual bounds | `visual.bounds`, `silhouette`, `palette`, `details` |

Koordinat rect lokal terhadap sudut kiri-bawah prefab, dalam unit menyerupai
meter. Collider platform harus sama persis dengan `visual.standableSurface`.
Collider obstacle bersebelahan dan tidak boleh saling overlap.

Jumlah: **33 platform** (10 kategori) dan **32 obstacle** (10 kategori). Daftar
nama ada di `PLATFORM_LIBRARY.md` dan `OBSTACLE_LIBRARY.md`.

## Spesifikasi puzzle

`assets/content/puzzles/puzzle_catalog.json` berisi **26 puzzle** di 12 kategori,
minimum 2 per kategori. Skema `schema.json` memakai JSON Schema 2020-12 (subset
yang bisa dicek dengan stdlib). Field wajib per entri:

| Field | Aturan |
|---|---|
| `id` | `^puzzle_[0-9]{3}$` |
| `name` | ≥3 karakter |
| `category` | salah satu dari 12 kategori |
| `difficulty` | bilangan bulat 1–5 |
| `description` | ≥20 karakter |
| `requiredComponents` | ≥1 nama unik, harus ada di registry F4 |
| `prefabDependencies` | ≥1 referensi; `Platform_*`/`Obstacle_*` harus ada di library |
| `variantParams` | objek, ≥2 kunci |
| `unlockCondition`, `failureState` | ≥5 karakter |
| `timeLimit` | 0 (tanpa batas) atau ≤60 detik |

Registry implementasi adalah `nur_game.puzzles.COMPONENT_CLASSES` (22 komponen):
GateLock, ColorCycler, SigilDetector, SequenceMemory, PressurePlate,
PatternMatch, WeightBalance, TimeEcho, ShadowAligner, TimingWindow, SoundTrigger,
MirrorReflector, SymbolDecoder, RoomRotator, FuelTrade, WaterLevel, WindCurrent,
MemoryPalace, LaserGrid, PerspectiveShift, SoundMemory, EnvironmentalCombo.
`PuzzleManager.generate_from_spec()` harus mampu membangun semua entri katalog.

## Layer dan tag (kontrak spec Unity, dipetakan ke JSON)

Layer: `0 Default`, `7 Standable`, `8 Obstacle`, `9 Monster`, `10 Player`,
`11 LanternLight`, `12 Puzzle`, `13 Phantom`.
Tag: `Platform`, `Obstacle`, `Monster`, `Player`, `Lantern`, `PuzzleElement`,
`SanityPickup`, `Gate`, `PatrolPoint`.
Animator parameter: `Speed` (float), `IsFleeing` (bool), `FacingRight` (bool),
`SanityIntensity` (float).

## Sistem F1–F4

| ID | Modul | Kontrak |
|---|---|---|
| F1 | `monsters.py`, `encounters.py` | Animasi bilateral & state Patrol → Detect → Flee → Return |
| F2 | `spawn_manager/` | Spawn/pool dinamis, maksimal 8 kandidat per wilayah |
| F3 | `sanity/`, `hallucinations/` | Akal, halusinasi render-only, tombol H, HUD, save/load |
| F4 | `puzzles/` | Framework + 22 komponen, generate dari katalog, save/load |

Modul F2–F4 kini berupa paket dengan satu berkas per tanggung jawab; semua nama
publik tetap diimpor dari `nur_game.<nama>` (misalnya `from nur_game.puzzles
import COMPONENT_CLASSES`). Alias lama `puzzle_components.py` dan
`puzzle_manager.py` sudah dihapus karena tidak digunakan.

## Checkpoint

`SAVE_PATH = saves/nur-v4.json`, terpisah dari v3. State yang disimpan: posisi
global, puzzle, persepsi, peti yang dipindah, perawatan, pita, stamina, letak
lentera, akal, dan progres akhir. `--no-save` menonaktifkan semua penulisan.

## Perintah validasi

```bash
.venv-nur/bin/python src/scripts/generate_content.py
.venv-nur/bin/python src/scripts/validate_content.py
.venv-nur/bin/python -m pytest -q
.venv-nur/bin/python src/play_nur.py --headless --frames 120 --no-save --mute --report docs/verification/smoke.json
```
