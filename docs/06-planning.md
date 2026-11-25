# Freebuff task list — core systems

Sumber: instruksi “FREEBUFF TASKS — Core Systems Architecture” (F1–F4) dan
kontrak integrasi O1–O3 di `assets/content/`.

> **Penting:** path di bawah adalah kontrak Unity dari spec. Path tersebut
> **tidak ada** di checkout Python/Pygame ini. Jangan membuat file Unity tiruan;
> lihat `docs/PROJECT-STATUS.md` untuk keputusan arah yang dibutuhkan.

---

## F1 — Monster bilateral animation & flee AI

**Status:** `done (Python adaptation)`  
**Prioritas:** tinggi  
**Branch spec:** `feature/monster-bilateral-ai`

### Tujuan
Monster memilih animasi kiri/kanan tanpa flip `scale.x`, lalu memiliki state
machine Patrol → Detect → Flee → Return yang bereaksi terhadap lentera.

### Output contract (Unity)
- `Assets/Scripts/Monsters/MonsterAnimator.cs`
- `Assets/Scripts/Monsters/MonsterAI.cs`
- `Assets/Scripts/Monsters/MonsterFleeBehavior.cs`
- `Assets/Animations/Monsters/MonsterAnimatorController.controller`

API wajib:
- `MonsterAnimator.SetMovement(float horizontalSpeed, bool isFleeing)`
- `MonsterAnimator.SetFacingDirection(Vector2 directionToTarget)`
- `MonsterAnimator.PlayFleeStart()`
- `MonsterAnimator.PlayFleeEnd()`
- `MonsterFleeBehavior.FleeFrom(Vector2 threatPosition)`

Parameter animator: `Speed` (float), `IsFleeing` (bool), `FacingRight` (bool).
`FacingRight` **tidak** boleh diturunkan dari arah gerak; gunakan
`directionToTarget.x > 0`.

### Acceptance checklist
- [ ] Walk_Right/Walk_Left dipilih tanpa sprite flip.
- [ ] Brightness > 0.5 + LOS: monster berbalik menjauhi pemain, memutar badan
      secara terlihat, lalu lari maju dengan `Run_Left`/`Run_Right`.
- [ ] Jalur lari memakai collision layer yang sama dengan pemain dan tidak
      menembus platform/obstacle.
- [ ] Kembali ke patrol setelah jarak aman dan LOS terputus.
- [ ] Nol error/warning console dalam playtest 5 menit dengan 10 monster.

### Input yang belum tersedia
- `BaseMonster.prefab`, animasi `Walk_*`/`Run_*`/`Idle_*`, Animator Controller.
- `LanternController.instance.currentBrightness` dan posisinya.
- `PatrolPath`, layer `Player|Platform|Obstacle`, dan `PlayerController`.
- Video/GIF 30 detik serta branch git.

---

## F2 — Dynamic monster spawn manager

**Status:** `done (Python adaptation)`  
**Prioritas:** tinggi  
**Branch spec:** `feature/dynamic-spawn-manager`

### Tujuan
Spawn monster berbasis brightness, waktu, level, dan batas variasi, dengan
pooling tanpa alokasi GC per frame.

### Output contract (Unity)
- `Assets/Scripts/Systems/MonsterSpawnManager.cs`
- `MonsterPrefabLibrary` ScriptableObject
- `Assets/Data/Monsters/MonsterLibrary.asset`

API wajib:
- `Initialize(MonsterPrefabLibrary library)`
- `Tick(float dt)`
- `SpawnStats GetStats()`
- `GetPooled(typeId)` / `ReturnToPool(monster)`

Rumus spawn:
`spawnRateByBrightness.Evaluate(1 - brightness) * (1 + timeSurvived * 0.02) * (1 + level * 0.15)`

### Acceptance checklist
- [ ] Nol alokasi GC per frame setelah warmup (profiler).
- [ ] Spawn rate naik halus saat lentera meredup.
- [ ] Tidak pernah > `maxSameTypeAlive` (3) per `typeId`.
- [ ] Hanya spawn di layer `Standable`, tidak di dalam obstacle.
- [ ] Pool reuse; jumlah `MonsterController` aktif ≤ batas waktu.
- [ ] 60 FPS dengan 100 monster concurrent (mid-tier device).
- [ ] Screenshot profiler GC/CPU disertakan.

### Input yang belum tersedia
- 20+ prefab varian dan 8+ tipe di `Assets/Prefabs/Monsters/Variants/`.
- `GameManager.currentLevel`, `timeSurvived`, `PlayerController`.
- Layer `Standable|Obstacle|Monster`, `Physics2D` setup, dan profiler run.
- `MonsterPrefabLibrary` asset serta branch git.

---

## F3 — Hallucination & sanity system

**Status:** `done (Python adaptation)`  
**Prioritas:** tinggi  
**Branch spec:** `feature/hallucination-sanity`

### Tujuan
Loop Q → halusinasi → drain sanity + drain lentera lebih cepat → kematian,
dengan visual/audio yang bertahap dan cooldown 3 detik.

### Output contract (Unity)
- `Assets/Scripts/Systems/SanityManager.cs`
- `Assets/Scripts/UI/HallucinationVisuals.cs`
- `Assets/Scripts/Systems/HallucinationAudio.cs`
- `Assets/Shaders/HallucinationEffect.shader`

API wajib:
- `SanityManager.TriggerHallucination()`
- `SanityManager.RestoreSanity(float amount)`
- Event `OnSanityChanged`, `OnHallucinationToggled`, `OnBreakPointReached`
- Properti `CurrentSanity`, `IsHallucinating`, `HallucinationCount`

Mekanik:
- Drain dasar `baseSanityDrain`; saat halusinasi ditambah
  `hallucinationDrainPerSec`.
- `lanternDimMultiplier` awal 1.5; setiap entry menambah +0.2 permanen, cap 3.0.
- Sanity ≤ 0 → `PlayerController.Instance.Die()` tanpa downed state.
- Breakpoint 75/50/25/0 mengatur intensitas visual/audio.

### Acceptance checklist
- [ ] Q toggle dengan cooldown 3 detik; spam Q hanya satu toggle per 3 detik.
- [ ] Setiap entry menaikkan multiplier drain +0.2 (cap 3.0).
- [ ] Sanity dan lentera terkuras lebih cepat saat halusinasi.
- [ ] Sanity 0 → kematian instan.
- [ ] Intensitas visual/audio interpolasi halus antar breakpoint.
- [ ] Phantom monster render tanpa collider/AI dan fade dalam 2 detik.
- [ ] Objek halusinasi dipool; tidak ada memory leak.
- [ ] Balance: pemain terampil > 10 menit; spam halusinasi < 2 menit.
- [ ] Spreadsheet/CSV data playtest disertakan.

### Input yang belum tersedia
- `InputManager`, `LanternController` (`maxBrightness`, `DrainRate`,
  `AddDrainMultiplier`), `PlayerController.Die()`, `SanityPickup`.
- AudioMixer snapshots dan parameter `LowPassCutoff`, `ReverbMix`,
  `PitchWobble`, shader/post-process pipeline.
- Layer `Phantom`, tag `SanityPickup`, dan branch git.

---

## F4 — Puzzle component framework & 20+ implementations

**Status:** `done (Python adaptation)`  
**Prioritas:** sangat tinggi  
**Branch spec:** `feature/puzzle-framework`

### Tujuan
Framework puzzle yang extensible, dipakai oleh 26 spec O3 di
`assets/content/puzzles/puzzle_catalog.json`, dengan save/load dan generate runtime.

### Output contract (Unity)
- `Assets/Scripts/Puzzles/PuzzleComponent.cs`
- `Assets/Scripts/Puzzles/PuzzleManager.cs`
- `Assets/Scripts/Puzzles/IPuzzleComponent.cs`
- `Assets/Scripts/Puzzles/PuzzleSaveData.cs`
- `Assets/Scripts/Puzzles/Components/` (20+ implementasi)
- `Assets/Scenes/Tests/PuzzleTestBed.unity`

API wajib:
- `PuzzleManager.Register/Unregister/NotifySolved`
- `PuzzleManager.SaveProgress(string saveKey)`
- `PuzzleManager.LoadProgress(string saveKey)`
- `PuzzleManager.GenerateFromSpec(spec)`
- Setiap komponen: `ResetPuzzle()`, `SaveState()`, `LoadState()`, event
  `OnPuzzleSolved`/`OnPuzzleFailed`.

### Acceptance checklist
- [ ] 20+ komponen kompilasi tanpa error/warning.
- [ ] Setiap komponen bisa diuji terisolasi.
- [ ] `variantParams` dari JSON O3 menggerakkan perilaku; tanpa hardcode.
- [ ] State puzzle bertahan setelah reload scene.
- [ ] Tidak ada komponen > 200 baris.
- [ ] `GenerateFromSpec` membuat komponen saat runtime.
- [ ] 20 puzzle playtest: rata-rata 15–45 detik, tanpa softlock.
- [ ] `PuzzleTestBed.unity` mendemokan semua komponen.

### Catatan kesiapan
O3 sudah tersedia: `assets/content/puzzles/puzzle_catalog.json`,
`assets/content/puzzles/schema.json`, `assets/content/puzzles/puzzle_index.md` (26 puzzle,
12 kategori). Komponen yang dirujuk: `ColorCycler`, `SigilDetector`,
`SequenceMemory`, `PressurePlate`, `PatternMatch`, `WeightBalance`,
`TimeEcho`, `ShadowAligner`, `TimingWindow`, `SoundTrigger`, `SoundMemory`,
`MirrorReflector`, `LaserGrid`, `SymbolDecoder`, `RoomRotator`,
`PerspectiveShift`, `FuelTrade`, `WaterLevel`, `WindCurrent`,
`EnvironmentalCombo`, `MemoryPalace`, `GateLock`.

### Input yang belum tersedia
- Prefab puzzle (`Sigil_Gate`, `ColorPedestal`, `Plate_Pair`, dll.).
- `Interactable`, `Gate`/`Door`, `Lockable`, `PlayerController`,
  `LanternController`.
- Layer `Puzzle`, tag `PuzzleElement`/`Gate`, dan branch git.

---

## Integration contracts (ringkas)

### ScriptableObject / data
| Asset Unity | Padanan repo ini | Status |
|---|---|---|
| `PlatformData` | `assets/content/platforms/generated/*.json` | Ada (JSON) |
| `ObstacleData` | `assets/content/obstacles/generated/*.json` | Ada (JSON) |
| `MonsterPrefabLibrary` | belum ada | Belum |
| `PuzzleComponentRegistry` | `assets/content/puzzles/puzzle_catalog.json` | Ada (JSON) |

### Layer matrix yang harus dipakai
`7 Standable`, `8 Obstacle`, `9 Monster`, `10 Player`, `11 LanternLight`,
`12 Puzzle`, `13 Phantom`.

### Tag
`Platform`, `Obstacle`, `Monster`, `Player`, `Lantern`, `PuzzleElement`,
`SanityPickup`, `Gate`, `PatrolPoint`.

### Animator parameters
`Speed` (float), `IsFleeing` (bool), `FacingRight` (bool),
`SanityIntensity` (float).

---

## Urutan kerja yang disarankan (setelah arah disetujui)

1. F1 animasi + flee (fondasi perilaku monster).
2. F2 spawn + pooling (memakai prefab/varian).
3. F3 sanity + halusinasi (memakai F1/F2 untuk phantom dan tekanan spawn).
4. F4 puzzle framework (independen, bisa paralel setelah F1).
5. Integration test 10 menit + validasi layer/tag/prefab.
