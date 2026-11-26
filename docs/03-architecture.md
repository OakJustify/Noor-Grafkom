# NUR v4 · revised architecture

## Standalone, persistent world

`src/nur_game/engine/` and `src/nur_game/geometry.py` contain NUR's required Pymunk
controller and geometry. The other game's package, tests, assets, requirements
and dedicated scripts have been removed from **v4 only**. `v3` remains separate.
`baseline_game.py` is the retained NUR room-based reference for `tests/nur/`;
`src/play_nur.py` launches the revised continuous controller in `game/`.

Modules with several responsibilities are packages with one file per concern
(`engine/`, `game/`, `puzzles/`, `art/`, `audio/`, `spawn_manager/`, `sanity/`,
`hallucinations/`); each keeps its public API at `nur_game.<name>`. Data-heavy
single-purpose modules (`levels.py`, `story.py`, `scripts/generate_content.py`)
remain intact.

`continuum.py` translates 29 authored regions and their puzzle plans into one
112,360 px world. Each connector adds a 720 px road, an optional ribbon lookout
and a lethal machine. Player, crates, rope, gates and phantom surfaces share one
Pymunk space. Region crossing updates a narrative address, not physics identity.
Opened gates and solved milestones remain open/solved on backtracking and retry.
Q is edge-triggered and changes collision-backed perception platforms globally.

## Subtitle-only story adaptation

The active controller now uses `cinematics/`: a cue catalog, a separate story
inventory/clock, ordered fragment reveals, original vector illustrations, and
the symbolic void followed by a real-world Nur–Dara ending. Six story objects
are distinct from optional fuel ribbons. Narrative grading is independent of
lantern charge. Cutscenes/gallery freeze gameplay, while replay is read-only for
story progression. The old local boss remains only behind `cinematics=False`
for mechanic regression coverage, not the default launcher.

Checkpoints keep collected/seen/active story states. Interrupted scenes restart
from their beginning; invalid checkpoints are rejected before committing live
state. See [story implementation and verification](10-story-cinematics.md).

The lookout's underside leaves ground clearance. Its last shelf ends before
the machine's run-up rather than forcing a descent onto spikes. Glide is
unlocked at an unattended wick station and limited by stamina.

## Depth: user's numbering is front to back

| Layer | Contents | Camera multiplier |
|---|---|---:|
| **1** | Solid near posts, foliage, overhead lines | 1.12 |
| **2** | Terrain, puzzles, machines, crates/rope, player, monsters, wick stations | 1 |
| **3** | Small tables, chairs, pots, crates and saplings; connected silhouettes ≤120 px | .82 |
| **4** | Large houses, hills, distant trees/forest and water | .12 |

Painting runs in reverse order. `scenery.py` generates 960 px chunks with
world-anchored identity. The scene does not swap, alpha-dissolve or erase
foreground around the player when its region address changes. Solid interiors
are opaque; antialiased contours and empty spaces still have alpha. Large-scale
hill endpoints use global coordinates to avoid tile discontinuities.
Scenery uses a bounded 32-tile cache; inspection backgrounds keep six entries.

Visual depth comes from scale, value contrast, overlap and parallax, not making
objects translucent. The dark foreground is sparse to preserve negative space.
The art is supersampled vector illustration, not studio hand-painted assets.
NumPy/Pygame CPU grading applies desaturation, local gain and a warm halo after
the four planes. At zero charge the composed world is completely black; UI
recovery instructions are drawn afterward. No GPU shader is claimed.

Design references used during the revision:
- [Jeremy Price: design elements/principles in level art](https://www.gamedeveloper.com/art/applying-the-elements-of-design-and-principles-of-design-in-level-art)
- [Godot: parallax, repetition and common gaps](https://docs.godotengine.org/en/stable/tutorials/2d/2d_parallax.html)

## Lethal environmental machinery

`hazards.py` authors 28 machines along the playable road, rotating five types:

- **Presser:** a ground button triggers .48 s warning, .14 s downward sweep,
  .55 s hold, .85 s retraction and 1.5 s cooldown.
- **Spikes:** fatal contact with the bed; jump with actual takeoff/landing space.
- **Steam:** 4.8 s cycle with a visible warning before its lethal column.
- **Falling beam:** the same fall cycle, also triggered by a red tripwire.
- **Pendulum:** a periodic circle collision at the rendered bob position.

Render and collision share machine coordinates/poses. Falling slabs use swept
collision to prevent tunnelling. Machines kill while the lantern is carried:
possession protects against monsters, not physical iron, saws or falling.
Retry moves only the existing player body to the last refuge, clears its
contact/jump state and resets nearby triggered machinery. It does not rebuild
the world or remove puzzle progress. Hazard deaths and button trips are recorded.

## Progressive encounters and protection

`EncounterDirector` places eight potential kinds in each region (232 total).
Kinds unlock cumulatively by elapsed gameplay **or** fading charge:

| Form | Time | Charge |
|---|---:|---:|
| PENYAPU | 20 s | ≤.85 |
| PELANGKAH | 90 s | ≤.72 |
| LONCENG KOSONG | 180 s | ≤.60 |
| SERIBU KAKI | 300 s | ≤.48 |
| SAYAP RETAK | 420 s | ≤.36 |
| PEMBURU | 570 s | ≤.26 |
| AKAR BERGERAK | 720 s | ≤.18 |
| RODA MATA | 900 s | ≤.10 |

Different opaque silhouettes, frame cycles, scales and attack speeds distinguish
ground, aerial, lunging and rooted forms. Only nearby encounters update/draw;
inactive remote creatures clear attack state. Refilling does not erase unlocks.
Save data retains unlocks and elapsed play time.

**Carried-lantern immunity holds at any charge, including zero.** A placed lit
lantern additionally protects inside its radius. Outside protection, creatures
telegraph for 1.2 s before a short pursuit. Retrieving the lantern cancels attacks.

## Wick stations, darkness, audio and saving

`RefugeBook` contains visited stations, collected ribbons and deposits—no
characters or dialogue. E immediately kindles a station once, replenishes a
portion of stamina, unlocks glide and optionally deposits a ribbon. Inward lines
are labelled `NUR · DALAM HATI`. Ribbons require actually climbing the lookout.

`LivingLantern` drains .00065 charge/s plus .018/s during focus. Milestones lower
capacity toward .16 over 144 steps; capacity is not a current-charge floor.
Pause/journal stop gameplay/drain. At zero, E obtains reserve kindling and returns
to the last station inside the same world. No memory test is required to recover.

Six eight-frame player sets distinguish idle, walk, run, jump, glide and focus.
`Soundscape` mixes original music/foley and synthetic wind/drone/breath layers at
light-dependent gains; M mutes continuous channels and one-shots. There is no
recorded speech or downloaded game soundtrack.

`LocalFinale` adapts the retained NUR final encounter to global coordinates. The
ending shows NUR and an unattended flame, without NPC artwork. This narrative
does not claim an illness is defeated or cured by completing a journey.

Version-4 checkpoints atomically save global position, all quests, phase, light,
stamina, station inventory, monster unlocks, crates, lantern placement and finale
state. Validation precedes live-world replacement. Old v4 ribbon inventory is
read from its legacy save key; new saves do not contain character state. V1–V3
saves remain with v3. Tests use temporary save paths; pilots use `persist=False`.
