# TASK: Implement Procedural Puzzle & Obstacle Generation System

## Project Context

Project ini merupakan game 2D side-scroller menggunakan Python dan Pygame dengan konsep Endless Survival.

Sistem Procedural Level Generation sudah tersedia. Sistem tersebut menghasilkan geometri dunia seperti platform, jarak, ketinggian, dan area permainan.

Tujuan pekerjaan ini adalah memperluas sistem yang sudah tersedia dengan Procedural Puzzle & Obstacle Generation System tanpa mengganti atau merusak generator yang sudah ada.

## Game Design Requirements

1. Challenge style: Hybrid.
   - Light-based puzzles.
   - Environmental hazards.
   - Enemy encounters.
   - Interactive puzzles.
   - Combination of multiple mechanics.

2. Lantern/light is a core gameplay mechanic.
   - Light must have meaningful gameplay functions.
   - Possible mechanics include hidden platforms, light switches, light barriers, and light-sensitive hazards.
   - Enemies may react to light.
   - Inspect the existing lantern implementation before introducing new behavior.

3. Failure consequence: Health-based.
   - Hazards and enemies can damage the player.
   - Implement or reuse damage cooldown/invulnerability frames.
   - Consider remaining health when evaluating challenge fairness.
   - Do not make every collision instantly fatal unless the existing game design explicitly requires it.

## Required Architecture

Implement or adapt these responsibilities:

- Puzzle Generator: selects candidate challenges.
- Puzzle Composer: combines compatible mechanics.
- Puzzle Catalog: stores available challenge definitions and metadata.
- Puzzle Rules: defines requirements and compatibility.
- Puzzle Validator: checks solvability, reachability, and fairness.
- Hazard System: manages environmental hazards.
- Light Mechanics: handles light-dependent interactions.
- Difficulty Manager: controls challenge complexity.
- World Manager integration: spawns and cleans up generated objects.

Do not blindly create all these files. Inspect the current project and reuse existing implementations where possible.

## Integration Requirements

The new system must consume existing level geometry and actual player physics.

It must not independently generate a disconnected level or duplicate the existing platform generator.

The challenge generator must:
1. Receive available platform and world geometry.
2. Read actual player capabilities and lantern state.
3. Read the current difficulty profile.
4. Select compatible challenge mechanics.
5. Position and configure challenge objects.
6. Validate the complete challenge.
7. Return structured generation data.
8. Allow the World Manager to spawn the generated objects.

## Validation Requirements

Implement bounded validation with:
- Geometric and overlap checks.
- Reachability and landing checks.
- Puzzle state/condition checks.
- Hazard fairness checks.
- Health and lantern-resource fairness checks.
- Deterministic random seed support.
- Safe fallback when candidate generation repeatedly fails.

Use actual game physics. Do not assume abilities that are not implemented.

## Implementation Process

Phase 1: Inspect existing architecture and document relevant files, systems, and dependencies.

Phase 2: Propose integration design before making major changes.

Phase 3: Implement light-based mechanics.

Phase 4: Implement environmental hazards.

Phase 5: Integrate enemy encounters and health.

Phase 6: Implement puzzle composition and compatibility rules.

Phase 7: Implement validation, stress tests, and optimization.

Do not implement every phase in one unreviewed change. Complete and test each phase before continuing.

## Testing

Test multiple random seeds and difficulty levels.

Measure:
- Valid challenge generation rate.
- Retry and fallback frequency.
- Invalid or impossible puzzle count.
- Performance during long sessions.
- Behavior when player health or lantern energy is low.

## Final Report

After each phase, report:

1. Objective.
2. Existing files inspected.
3. Files created or modified.
4. Architecture and implementation decisions.
5. Input, process, and output.
6. Tests executed and their results.
7. Known limitations.
8. Recommended next phase.

Do not claim that a system is fully tested if only a small number of manual tests have been performed.
