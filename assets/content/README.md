# Authored content catalogs (O1–O3)

The task spec describes a Unity project. This checkout is the Python/Pygame v4 game,
so the same data is authored here in tech-neutral JSON. `src/scripts/generate_content.py`
is the single source of truth; run it after editing a table and commit the generated files.

```bash
.venv-nur/bin/python src/scripts/generate_content.py
.venv-nur/bin/python src/scripts/validate_content.py
.venv-nur/bin/python -m pytest -q tests/v4/test_content_catalogs.py
```

## Unity term → JSON field

| Unity concept | This repository |
|---|---|
| `Platform_X_Y.prefab` / `Obstacle_X_Y.prefab` | `assets/content/platforms/generated/Platform_X_Y.json`, `assets/content/obstacles/generated/Obstacle_X_Y.json` |
| `BoxCollider2D` | `collider` (platform) / `colliders[]` (obstacle), each with `type`, `rect: [x,y,w,h]`, `isTrigger: false` |
| Tag and layer | `tag`, `layer: {name, index}` — layer 7 `Standable`, layer 8 `Obstacle` |
| `PlatformData` ScriptableObject (one per variant) | `platformData` object with a unique `id` per variant: `platformType`, `maxStandAngle`, `isStable`, `creakSound` |
| `ObstacleData` ScriptableObject | `obstacleData`: `obstacleType`, `trippingChance`, `noiseLevel`, `canBeCleared`, `clearTime` |
| Visual bounds | `visual.bounds`, plus `silhouette`, `palette`, `details` so duplicates can be detected |
| Editor validator tests | `src/scripts/validate_content.py` and `tests/v4/test_content_catalogs.py` |

Rect coordinates are local to each prefab, origin at its bottom-left corner, in
metre-like world units. A platform's collider is its standable top slab and must
exactly match `visual.standableSurface`. Obstacles use several adjacent
non-overlapping boxes to approximate their silhouette.

## Libraries

- 33 platform prefabs across 10 categories (table, chair, crate, books, shelf,
  cabinet, bed, sofa, appliance, household). Every `PlatformData` uses the
  specified defaults (`maxStandAngle: 45`, `isStable: true`).
- 32 obstacle prefabs across 10 categories. Tuning follows the spec's guidance:
  wire tangles trip easily and are quiet, toy clusters are medium-trip and loud,
  fixed furniture/thresholds cannot be cleared (`clearTime: 0`).
- 26 puzzle specs across all 12 categories, with `schema.json` (JSON Schema
  2020-12) and a generated `puzzle_index.md`. Component names are limited to the
  F4 framework plus `GateLock`; all `timeLimit` values are 0 or ≤60 seconds.
  Since the F4 merge, validation reads the real registry
  `nur_game.puzzles.COMPONENT_CLASSES`, and the tests also generate every spec
  at runtime to keep catalog and implementation in sync.

The full prefab name list is in `assets/content/platforms/PLATFORM_LIBRARY.md` and
`assets/content/obstacles/OBSTACLE_LIBRARY.md` (the delivery PR lists from O1/O2).

## Delivery note

There is no git repository in this checkout, so `feature/platform-library`,
`feature/obstacle-library`, `feature/puzzle-specs` and their PRs could not be
created. The files are ready to be committed under whichever branch structure
the orchestrator sets up.
