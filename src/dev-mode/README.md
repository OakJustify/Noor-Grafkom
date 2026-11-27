# Developer Mode Blueprint

Debug overlay for NOOR gameplay. Toggle with `F3`; no build flag, no separate
executable, no new dependency.

## Goals

- Inspect live gameplay state without attaching a debugger.
- See collision boxes, exits, checkpoints and procedural creature rigs.
- Trigger a few common debug actions (god mode, refill, spawn, freeze clock,
  respawn) without editing level JSON.

## Non-goals

- Level editor, free camera, replay, remote console, save editing.
- Frame stepping and time scaling. The game loop is fixed-step; adding those
  needs a loop change, so they are deferred.
- Shipping UI. This is a developer tool and stays in the repo.

## Activation and keys

| Key | Action |
|---|---|
| `F3` | Toggle the debug overlay |
| `F4` | Toggle god mode (no contact damage; sanity and stamina stay full) |
| `F5` | Refill sanity and stamina |
| `F6` | Spawn a test monster near the player; cycles `M1`/`M2`/`M3` |
| `F7` | Freeze/unfreeze the disease clock |
| `F8` | Teleport to the active checkpoint |

Cheat keys also make the overlay visible so the developer gets feedback.
Gameplay keys (`A/D`, `Space`, `E`, `F`, `C`, `Shift`, `Esc`) are untouched.

## Overlay content

Top-right panel:

- FPS, level id, stage, RNG seed, monster/ambient counts.
- Player position, velocity, ground flag, facing, stamina, invulnerability.
- Camera position.
- Sanity `S`, cap, effective value, lantern radius.
- Disease clock time, forced stage, paused flag.
- Fragment slots and forgotten count.
- Active monsters with state and distance to the player.
- Ambient creature kind and current gait.

World overlays:

- Platform rectangles.
- Player and monster hitboxes, facing arrow, feet line.
- Fragment/prop markers, checkpoint and exit markers.
- Ground probe under the player (red cross when there is no ground).
- IK rig for every animated creature: hip, knee, foot, IK target, head target.
- Monster labels with state.

## Architecture

`src/dev-mode/dev_mode.py` exposes one class:

```python
class DevMode:
    def handle_event(self, event, scene) -> bool: ...
    def update(self, dt, scene) -> None: ...
    def draw(self, surface, scene) -> None: ...
```

- `handle_event` consumes only its own function keys and returns `True` when it
  did, so gameplay does not see them.
- `update` samples FPS and enforces god mode/clock freeze.
- `draw` reads the scene; it does not mutate it.
- Cheats mutate the scene through its public systems (`sanity`, `player`,
  `clock`, `checkpoint`, `monsters`, `monster_anims`).

Integration is limited to `noor/scenes/gameplay.py`: import the module, create
one instance, forward events/update, draw last (after lighting), and skip
contact damage while god mode is on. If the import fails, gameplay runs without
the tool.

## Tests

`src/dev-mode/tests/` covers:

- overlay toggle and drawing;
- god mode blocking contact damage;
- refill;
- clock freeze;
- monster spawn with animator;
- checkpoint teleport.

Tests use SDL dummy drivers like the rest of the suite.

## Deferred

- Frame step / slow motion.
- Free camera and zoom.
- Entity inspector and live value editing.
- Level jump and save-state snapshot.
- Performance graph and draw-call counters.
