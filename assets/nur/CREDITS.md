# NÜR audio & art credits

## Downloaded audio — Creative Commons Zero (CC0 1.0)

All three downloaded beds were filtered with Freesound's **Creative Commons 0**
licence and their individual sound pages were checked on 2026-11-24. The files
in this repository are Freesound's public low-bitrate preview encodes; the
original uploads are linked below. CC0 permits copying, modification and
commercial use without attribution — credit is given here as a courtesy.

| File in game | Source sound | Author | Permanent sound page | Licence |
|---|---|---|---|---|
| `audio/creepy_vocal_ambience.ogg` | *Creepy Vocal Ambience* | HunteR4708 | https://freesound.org/people/HunteR4708/sounds/329866/ | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `audio/creepy_ambience.ogg` | *Creepy Ambience* | Janosch-JR | https://freesound.org/people/Janosch-JR/sounds/634329/ | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `audio/creepy_dungeon_ambience.ogg` | *Creepy Dungeon Ambience (Elementary Memories version).mp3* | AmaezingNooby | https://freesound.org/people/AmaezingNooby/sounds/606970/ | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

Freesound is operated by Universitat Pompeu Fabra: https://freesound.org/

## Original assets — CC0 1.0

The following are generated deterministically by `src/nur_game/generate_assets.py`
and `src/nur_game/audio.py` for this project, and are released under CC0 1.0:

- `cutscene/phase1_warmth.png`
- `cutscene/phase2_fractured.png`
- `cutscene/phase3_labyrinth.png`
- `cutscene/phase4_end.png`
- `audio/tick.wav`, `breath.wav`, `glitch.wav`, `memory.wav`,
  `heartbeat.wav`, `boss_pulse.wav`, `door.wav`
- `audio/jump.wav`, `land.wav`: original rising-pitch takeoff and soft landing,
  synthesised with NumPy and SciPy in `src/nur_game/foley.py` (no external samples).
- Seeded scenery/material generation in `src/nur_game/procedural.py` and
  `src/nur_game/materials.py`: original ink, fog, architecture and platform skins.
- Cloaked-wisp sprite frames in `sprites/wisp/`, including the updated sprint set.

Fonts in `../fonts/` keep their existing SIL Open Font License notices.

## Original music — CC0 1.0

Composed and deterministically synthesised for NÜR in `src/nur_game/music.py` using
NumPy only. No downloaded samples, external music-generation service or existing
game soundtrack is used. The compositions and generated recordings are released
under CC0 1.0 alongside the other original assets above.

| File | Scene | Instrumentation |
|---|---|---|
| `audio/music_home.wav` | NYATA / ordinary exploration | Soft keys, breathy pads, spirit bells |
| `audio/music_gaung.wav` | GAUNG / boss | Related motif with uneasy intervals and stereo reflections |
| `audio/music_return.wav` | Ending / return | Warmer harmony and resolving bell motif |

Each loop is 24 seconds, stereo 16-bit PCM at 22,050 Hz. Regenerate from `v4`:
`.venv-nur/bin/python -m nur_game.music --overwrite`.

## Version 4 additions

Revised opaque scenery in `src/nur_game/scenery.py`/`vistas.py`, unattended wick
stations, five machine designs in `src/nur_game/hazards.py`, eight creature forms in
`src/nur_game/encounters.py`, and the glide/focus wisp frames are original procedural/
vector assets. NPC identities and artwork have been removed from v4.
These additions contain no extracted Spiritfarer or Limbo assets, traced
characters, or copied machinery artwork. Those games are references for depth,
motion and readable environmental danger, not asset sources.
The same original-asset CC0 designation above applies to these additions.

`src/nur_game/soundscape.py` synthesises three stereo wind/drone/breath layers with
NumPy/SciPy. They contain no human voice recording or downloaded samples and use
the same original-audio CC0 designation. The credited Freesound beds are retained
with the baseline but are silenced in the live v4 mix. All fonts retain their OFL
notices. Spiritfarer: Farewell Edition is a visual/motion reference only; its
copyrighted illustrations, characters and soundtrack are not redistributed.
