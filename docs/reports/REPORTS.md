# Game Visual Consistency Report

## Summary
Found 5 critical issues affecting visual consistency between campaign and endless game modes, risking immersion and player experience.

## Detailed Findings

### Critical Issue 1: Inconsistent Asset Loading in PlayerSprite
- **File**: `noor/gfx/player_sprite.py` (line 1)
- **Issue**: PlayerSprite loads animations from JSON manifest without considering current game mode
- **Failure Scenario**: Campaign mode (colored assets) vs endless mode (grayscale assets) cause inconsistent visual feedback
- **Severity**: Important
- **Impact**: Breaks player immersion through mismatched visual feedback

### Critical Issue 2: Missing Grayscale Constants in config.py
- **File**: `noor/config.py` (line 1)
- **Issue**: Defines color constants (INK, PAPER, ACCENT) for campaign mode but lacks grayscale constants (INK, LIGHT) for endless mode
- **Failure Scenario**: Using campaign constants in endless mode renders colored visuals instead of grayscale, breaking aesthetic
- **Severity**: Important
- **Impact**: Creates visual confusion and reduces game's intended aesthetic

### Critical Issue 3: Unenforced Mode Consistency in Game Class
- **File**: `noor/game.py` (line 64)
- **Issue**: Stores 'mode' setting but provides no mechanism to enforce visual consistency between campaign and endless modes
- **Failure Scenario**: Same assets rendered with inconsistent color schemes cause jarring visual transitions
- **Severity**: Nit
- **Impact**: Reduces visual cohesion and player immersion

### Critical Issue 4: Uncoordinated Scene Rendering in SceneManager
- **File**: `noor/core/scene.py` (line 1)
- **Issue**: SceneManager manages scene stacking but doesn't coordinate visual pipelines across different rendering pipelines (campaign vs. endless)
- **Failure Scenario**: Campaign and endless scenes may render simultaneously, causing visual artifacts and conflicting imagery
- **Severity**: Important
- **Impact**: Creates visual contradictions that break immersion

### Critical Issue 5: Unsynchronized Timing in DiseaseClock
- **File**: `noor/core/clock.py` (line 1)
- **Issue**: DiseaseClock updates stage progression based on elapsed time without incorporating mode-specific timing
- **Failure Scenario**: Campaign mode expects faster transitions than endless mode, causing desynchronization
- **Severity**: Nit
- **Impact**: Leads to mismatched visual pacing and player confusion

## Recommendations

1. **Implement Mode-Aware Asset Loading**  
   Modify PlayerSprite to load different JSON manifests based on current game mode

2. **Add Grayscale Constants to config.py**  
   Define INK_LIGHT, PAPER_LIGHT, ACCENT_LIGHT constants for endless mode

3. **Enforce Visual Consistency via Mode**  
   Modify Game class to use mode-specific rendering parameters and asset selection

4. **Coordinate Scene Rendering Pipelines**  
   Update SceneManager to track and manage visual pipelines by game mode

5. **Implement Mode-Specific Timing**  
   Modify DiseaseClock to incorporate mode-specific timing parameters

## Steps to Reproduce
1. Set game mode to campaign (colored) and endless (grayscale)
2. Load same level in both modes
3. Observe inconsistent visual feedback between modes
4. Notice inconsistent color schemes in player sprites and UI elements
5. Observe potential scene conflicts when switching between modes

## Impact
These issues collectively threaten the game's core aesthetic integrity and player immersion. The inconsistent visual presentation between modes creates confusion, reduces immersion, and undermines the narrative experience centered around Alzheimer's themes and symbolic darkness.