#!/usr/bin/env python3
"""Regenerate the JSON prefab libraries and the puzzle catalog from source tables.

This is the Python-v4 counterpart of the Unity prefab authoring tasks O1-O3.
The tables below are the single source of truth; generated files are deterministic
and safe to check into version control. See content/README.md for the term mapping.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLATFORM_DIR = ROOT / "assets" / "content" / "platforms" / "generated"
OBSTACLE_DIR = ROOT / "assets" / "content" / "obstacles" / "generated"
PUZZLE_DIR = ROOT / "assets" / "content" / "puzzles"

# category, variant, size(w,h), standable surface(x,y,w,h), silhouette, palette, details
PLATFORMS = [
    ("Table", "Dining", (1.60, 0.78), (0, 0.70, 1.60, 0.08),
     "long plank top on four turned legs", ("#8b5e3c", "#5c3a22"), ("plank seams", "turned legs")),
    ("Table", "Coffee", (1.10, 0.42), (0, 0.36, 1.10, 0.06),
     "low oval top on stubby legs", ("#7a5230", "#4d3520"), ("oval top", "stubby legs")),
    ("Table", "Side", (0.55, 0.62), (0, 0.55, 0.55, 0.07),
     "narrow square top with one drawer", ("#9a6b43", "#634024"), ("single drawer", "tapered legs")),
    ("Table", "Desk", (1.40, 0.76), (0, 0.68, 1.40, 0.08),
     "flat writing top between side panels", ("#6f5744", "#3f3227"), ("side panels", "cable notch")),

    ("Chair", "Dining", (0.46, 0.94), (0, 0.46, 0.46, 0.06),
     "straight slatted back and woven seat", ("#8a6b48", "#54402c"), ("slat back", "woven seat")),
    ("Chair", "Armchair", (0.86, 0.96), (0, 0.44, 0.86, 0.08),
     "upholstered seat between low arms", ("#6b4a54", "#3d2b33"), ("padded arms", "button tufting")),
    ("Chair", "Stool", (0.38, 0.52), (0, 0.46, 0.38, 0.06),
     "round seat on three splayed legs", ("#a07a4c", "#6b4e2f"), ("round seat", "splayed legs")),
    ("Chair", "Office", (0.58, 1.12), (0, 0.52, 0.58, 0.08),
     "swivel seat with a tall slatted back", ("#4a5259", "#2b3136"), ("swivel base", "tall slats")),

    ("BoxCrate", "Cardboard", (0.62, 0.50), (0, 0.44, 0.62, 0.06),
     "taped corrugated shipping box", ("#b08a5e", "#8a6b45"), ("packing tape", "folded flaps")),
    ("BoxCrate", "Wooden", (0.70, 0.58), (0, 0.52, 0.70, 0.06),
     "slatted wood crate with iron corners", ("#9c7043", "#654729"), ("slat gaps", "iron corners")),
    ("BoxCrate", "Plastic", (0.56, 0.46), (0, 0.40, 0.56, 0.06),
     "moulded tote with handle slots", ("#3f6d78", "#27474f"), ("handle slots", "ribbed sides")),
    ("BoxCrate", "Metal", (0.60, 0.54), (0, 0.48, 0.60, 0.06),
     "riveted steel case with a lid seam", ("#6e757b", "#454b50"), ("rivet row", "lid seam")),
    ("BoxCrate", "Storage", (0.80, 0.64), (0, 0.58, 0.80, 0.06),
     "lidded storage trunk with two latches", ("#7a6246", "#4b3c2b"), ("two latches", "lid seam")),

    ("BookStack", "Horizontal", (0.44, 0.18), (0, 0.12, 0.44, 0.06),
     "three books laid flat with offset spines", ("#7d3f3a", "#3f5a6b"), ("page edges", "offset spines")),
    ("BookStack", "Vertical", (0.34, 0.42), (0, 0.36, 0.34, 0.06),
     "upright books packed side by side", ("#4d5f45", "#8a5a35"), ("varying heights", "spine bands")),
    ("BookStack", "Scattered", (0.58, 0.14), (0.08, 0.08, 0.42, 0.06),
     "fan of fallen open books", ("#6b4f6e", "#9a7a4a"), ("open pages", "fanned covers")),

    ("Shelf", "Bookshelf", (0.92, 1.80), (0, 0.84, 0.92, 0.08),
     "tall shelf with three loaded levels", ("#6a4a32", "#43301f"), ("three shelves", "book rows")),
    ("Shelf", "Floating", (0.74, 0.12), (0, 0.06, 0.74, 0.06),
     "thin bracketless wall plank", ("#8e7350", "#5e4b33"), ("hidden bracket", "thin profile")),
    ("Shelf", "Corner", (0.68, 1.20), (0, 1.12, 0.68, 0.08),
     "triangular two-sided corner unit", ("#76543b", "#4a3425"), ("diagonal back", "two faces")),

    ("Cabinet", "Kitchen", (1.00, 0.90), (0, 0.82, 1.00, 0.08),
     "double-door base with a counter lip", ("#a9a394", "#6f6a5e"), ("two doors", "counter lip")),
    ("Cabinet", "Wardrobe", (0.96, 2.00), (0, 1.92, 0.96, 0.08),
     "tall wardrobe with two panelled doors", ("#6b5138", "#3f3021"), ("tall doors", "brass knobs")),
    ("Cabinet", "Bedside", (0.48, 0.58), (0, 0.52, 0.48, 0.06),
     "small cabinet with one drawer", ("#8b6a4a", "#573f2a"), ("one drawer", "rounded top")),

    ("Bed", "Single", (1.00, 0.52), (0, 0.44, 1.00, 0.08),
     "narrow mattress on a low frame", ("#8e9a94", "#5d6b66"), ("narrow mattress", "low frame")),
    ("Bed", "Double", (1.60, 0.56), (0, 0.48, 1.60, 0.08),
     "wide mattress with two pillows", ("#a7a093", "#6d675c"), ("two pillows", "wide frame")),

    ("Sofa", "TwoSeater", (1.30, 0.86), (0, 0.42, 1.30, 0.10),
     "two deep cushions with low arms", ("#6d5a66", "#433842"), ("two cushions", "low arms")),
    ("Sofa", "ThreeSeater", (1.90, 0.88), (0, 0.44, 1.90, 0.10),
     "three cushions with rolled arms", ("#5c6b67", "#394541"), ("three cushions", "rolled arms")),

    ("Appliance", "Fridge", (0.76, 1.90), (0, 1.82, 0.76, 0.08),
     "tall refrigerator with two doors", ("#c2c6c4", "#7f8787"), ("upper door", "handle strip")),
    ("Appliance", "WashingMachine", (0.64, 0.86), (0, 0.78, 0.64, 0.08),
     "front-loading drum with a round door", ("#b9bcc0", "#737a80"), ("round door", "control dial")),
    ("Appliance", "Oven", (0.62, 0.62), (0, 0.56, 0.62, 0.06),
     "built-in oven with a glass window", ("#555b60", "#303438"), ("glass window", "four knobs")),

    ("MiscHousehold", "Piano", (1.44, 1.16), (0, 0.72, 1.44, 0.08),
     "upright piano with a keyboard shelf", ("#3d322c", "#211b18"), ("keyboard shelf", "music stand")),
    ("MiscHousehold", "TVStand", (1.10, 0.48), (0, 0.42, 1.10, 0.06),
     "low media console with an open shelf", ("#5c4a3c", "#382d24"), ("open shelf", "cable holes")),
    ("MiscHousehold", "Dresser", (1.05, 1.10), (0, 1.02, 1.05, 0.08),
     "tall chest of four drawers", ("#876244", "#553c29"), ("four drawers", "carved pulls")),
    ("MiscHousehold", "Trunk", (0.92, 0.52), (0, 0.46, 0.92, 0.06),
     "domed travelling trunk with straps", ("#745337", "#472f1e"), ("domed lid", "leather straps")),
]

# category, variant, size(w,h), collider rects, silhouette, palette, details,
# trippingChance, noiseLevel, canBeCleared, clearTime
OBSTACLES = [
    ("ClothPile", "Laundry", (0.80, 0.30), ((0, 0, 0.36, 0.22), (0.36, 0, 0.44, 0.30)),
     "crumpled laundry spilling from a heap", ("#a9a394", "#726d60"), ("loose sleeve", "creased folds"), .50, .18, True, 2.0),
    ("ClothPile", "Blankets", (0.92, 0.26), ((0, 0, 0.40, 0.18), (0.40, 0, 0.52, 0.26)),
     "two folded blankets slipped askew", ("#6c7484", "#424958"), ("woven fringe", "rolled edge"), .48, .12, True, 2.4),
    ("ClothPile", "Towels", (0.56, 0.34), ((0, 0, 0.26, 0.24), (0.26, 0, 0.30, 0.34)),
     "stack of towels with one hanging corner", ("#b6b0a0", "#7d776b"), ("terry stripes", "hanging corner"), .44, .10, True, 1.6),

    ("ToyCluster", "Blocks", (0.62, 0.36), ((0, 0, 0.20, 0.20), (0.20, 0, 0.22, 0.36), (0.42, 0, 0.20, 0.28)),
     "three painted wooden blocks toppled together", ("#c2684f", "#4c7a91"), ("letter faces", "uneven stack"), .62, .72, True, 1.8),
    ("ToyCluster", "Plushies", (0.70, 0.48), ((0, 0, 0.30, 0.40), (0.30, 0, 0.40, 0.48)),
     "soft toys collapsed into a pile", ("#a8798c", "#6d5262"), ("button eyes", "limp limbs"), .58, .56, True, 1.4),
    ("ToyCluster", "Cars", (0.84, 0.24), ((0, 0, 0.26, 0.18), (0.28, 0, 0.28, 0.24), (0.58, 0, 0.26, 0.20)),
     "three little cars abandoned bumper to bumper", ("#5e8b7e", "#b09148"), ("wheel pairs", "open doors"), .68, .66, True, 1.2),
    ("ToyCluster", "Mixed", (0.94, 0.42), ((0, 0, 0.30, 0.30), (0.30, 0, 0.34, 0.42), (0.64, 0, 0.30, 0.26)),
     "blocks, a plush and a car in one heap", ("#8f6a55", "#4f6d80"), ("mixed textures", "scattered pieces"), .70, .74, True, 2.2),

    ("WireTangle", "ChargerCables", (0.52, 0.12), ((0, 0, 0.22, 0.08), (0.22, 0, 0.30, 0.12)),
     "thin black charging leads looped twice", ("#2f3336", "#4a4f52"), ("coiled loop", "small plug"), .92, .12, True, 0.9),
    ("WireTangle", "ExtensionCords", (0.96, 0.14), ((0, 0, 0.34, 0.10), (0.34, 0, 0.34, 0.14), (0.68, 0, 0.28, 0.10)),
     "long extension cord crossed over itself", ("#3b3f42", "#6a6055"), ("three crossings", "flat plug"), .88, .16, True, 1.1),
    ("WireTangle", "StringLights", (1.10, 0.20), ((0, 0, 0.36, 0.12), (0.36, 0, 0.38, 0.20), (0.74, 0, 0.36, 0.14)),
     "festoon cable with unlit bulbs", ("#4d4a42", "#c2a36b"), ("dangling bulbs", "loose knot"), .84, .22, True, 1.6),

    ("FurnitureLeg", "Table", (0.30, 0.70), ((0, 0, 0.12, 0.70), (0.12, 0, 0.18, 0.12)),
     "single square table leg and apron stub", ("#74593f", "#483727"), ("square profile", "apron stub"), .70, .42, False, 0.0),
    ("FurnitureLeg", "Chair", (0.24, 0.56), ((0, 0, 0.10, 0.56), (0.10, 0, 0.14, 0.10)),
     "tapered chair leg with a rung remnant", ("#896948", "#55402b"), ("tapered profile", "rung remnant"), .66, .38, False, 0.0),
    ("FurnitureLeg", "Bed", (0.36, 0.44), ((0, 0, 0.14, 0.44), (0.14, 0, 0.22, 0.10)),
     "short bedpost beside a low rail", ("#6b5744", "#40352a"), ("blocky post", "low rail"), .74, .46, False, 0.0),
    ("FurnitureLeg", "Cabinet", (0.28, 0.64), ((0, 0, 0.12, 0.64), (0.12, 0, 0.16, 0.14)),
     "cabinet plinth leg and base ledge", ("#5f4d3c", "#382d22"), ("plinth foot", "base ledge"), .68, .40, False, 0.0),

    ("RugEdge", "CurledCorner", (0.44, 0.16), ((0, 0, 0.30, 0.06), (0.30, 0, 0.14, 0.16)),
     "rug corner curled up from the floor", ("#9b5f52", "#6b4038"), ("lifted corner", "woven border"), .78, .12, True, 0.8),
    ("RugEdge", "Folded", (0.60, 0.20), ((0, 0, 0.32, 0.08), (0.32, 0, 0.28, 0.20)),
     "rug folded back on itself", ("#5c7384", "#3a4b57"), ("fold ridge", "frayed edge"), .72, .14, True, 1.0),
    ("RugEdge", "Torn", (0.72, 0.14), ((0, 0, 0.40, 0.06), (0.40, 0, 0.32, 0.14)),
     "rug edge torn into uneven tabs", ("#877553", "#574b36"), ("uneven tabs", "loose threads"), .68, .10, True, 1.2),

    ("Threshold", "DoorSaddle", (0.90, 0.10), ((0, 0, 0.90, 0.10),),
     "worn metal door saddle", ("#777d80", "#494e50"), ("bevelled top", "screw heads"), .56, .30, False, 0.0),
    ("Threshold", "Step", (0.74, 0.22), ((0, 0, 0.74, 0.22),),
     "single raised stone step", ("#928a7c", "#5d574d"), ("chipped nose", "mortar seam"), .64, .34, False, 0.0),
    ("Threshold", "TransitionStrip", (1.02, 0.06), ((0, 0, 1.02, 0.06),),
     "thin strip joining two floor heights", ("#8a704f", "#5a4833"), ("narrow profile", "grooved surface"), .50, .22, False, 0.0),

    ("PlantPot", "Small", (0.26, 0.34), ((0, 0, 0.26, 0.20), (0.04, 0.20, 0.18, 0.14)),
     "small ceramic pot with dry soil", ("#b58567", "#6f5c4c"), ("tapered rim", "dry soil"), .52, .58, True, 1.0),
    ("PlantPot", "Medium", (0.40, 0.52), ((0, 0, 0.40, 0.30), (0.06, 0.30, 0.28, 0.22)),
     "medium plastic planter with a saucer", ("#6d7f6a", "#455245"), ("wide saucer", "moulded rim"), .58, .66, True, 1.4),
    ("PlantPot", "Large", (0.58, 0.72), ((0, 0, 0.58, 0.42), (0.08, 0.42, 0.42, 0.30)),
     "large glazed pot holding a thin stem", ("#7e8c96", "#4e5960"), ("glazed band", "thin stem"), .64, .74, True, 2.0),

    ("DecorItem", "Vase", (0.24, 0.46), ((0.04, 0, 0.16, 0.34), (0, 0.34, 0.24, 0.12)),
     "tall narrow vase with a flared lip", ("#6a8f92", "#3f5c60"), ("flared lip", "painted band"), .46, .68, True, 1.6),
    ("DecorItem", "Lamp", (0.38, 0.72), ((0.14, 0, 0.10, 0.50), (0, 0.50, 0.38, 0.22)),
     "table lamp with a wide shade", ("#c0a878", "#7a6a4c"), ("wide shade", "weighted base"), .42, .56, True, 1.8),
    ("DecorItem", "Frame", (0.46, 0.56), ((0, 0, 0.46, 0.10), (0, 0.46, 0.46, 0.10), (0, 0.10, 0.06, 0.36), (0.40, 0.10, 0.06, 0.36)),
     "empty picture frame leaning at an angle", ("#8c6b45", "#57422c"), ("mitred corners", "bare backing"), .38, .32, True, 0.9),
    ("DecorItem", "Figurine", (0.22, 0.38), ((0.06, 0, 0.10, 0.30), (0, 0.30, 0.22, 0.08)),
     "small ceramic figure on a round plinth", ("#b2a58e", "#706758"), ("round plinth", "chipped arm"), .40, .44, True, 1.1),

    ("StackedBoxes", "TwoHigh", (0.50, 0.60), ((0, 0, 0.50, 0.30), (0, 0.30, 0.50, 0.30)),
     "two identical cartons stacked square", ("#a58259", "#775b3d"), ("flush stack", "tape line"), .66, .52, True, 2.0),
    ("StackedBoxes", "ThreeHigh", (0.46, 0.84), ((0, 0, 0.46, 0.28), (0, 0.28, 0.46, 0.28), (0, 0.56, 0.46, 0.28)),
     "three shrinking cartons in a column", ("#8f7352", "#5b4833"), ("shrinking tiers", "three tape lines"), .72, .58, True, 2.6),
    ("StackedBoxes", "LeaningTower", (0.62, 0.78), ((0, 0, 0.44, 0.26), (0.18, 0.26, 0.44, 0.26), (0.10, 0.52, 0.40, 0.26)),
     "three cartons stacked at increasing offsets", ("#9c6f4d", "#63472f"), ("offset tiers", "crushed corner"), .82, .64, True, 3.2),

    ("LaundryBasket", "Plastic", (0.54, 0.58), ((0, 0, 0.54, 0.44), (0.06, 0.44, 0.42, 0.14)),
     "plastic laundry basket with cut-out handles", ("#4f7a83", "#2f5057"), ("cut-out handles", "tapered body"), .60, .42, True, 1.6),
    ("LaundryBasket", "Wicker", (0.58, 0.62), ((0, 0, 0.58, 0.46), (0.06, 0.46, 0.46, 0.16)),
     "wicker hamper with a raised lid", ("#a88355", "#70563a"), ("woven ribs", "raised lid"), .56, .38, True, 1.9),
]


def puzzle(pid, name, category, difficulty, description, components, prefabs, params, unlock, failure):
    return {
        "id": pid,
        "name": name,
        "category": category,
        "difficulty": difficulty,
        "description": description,
        "requiredComponents": list(components),
        "prefabDependencies": list(prefabs),
        "variantParams": dict(params),
        "unlockCondition": unlock,
        "failureState": failure,
    }


PUZZLES = [
    puzzle("puzzle_001", "Lantern Color Match", "ColorLogic", 1,
           "Cycle the lantern between red, green and blue until it matches the wall sigil.",
           ("ColorCycler", "SigilDetector", "GateLock"), ("Sigil_Gate", "ColorPedestal"),
           {"colorCount": 3, "sequenceLength": 1, "timeLimit": 0},
           "All sigils match the lantern colour at once", "Sigils reset; minor sanity drain"),
    puzzle("puzzle_021", "Three-Lantern Sort", "ColorLogic", 2,
           "Sort three lit lanterns onto the plate bearing their own colour.",
           ("ColorCycler", "PressurePlate", "GateLock"), ("ColorPedestal", "Plate_Pair"),
           {"colorCount": 3, "plateCount": 3, "timeLimit": 45},
           "Each colour rests on its matching plate", "Plates clear and lanterns return to neutral"),
    puzzle("puzzle_002", "Echo Sigil Sequence", "SequenceMemory", 2,
           "Watch a short sigil sequence flash, then repeat the same presses on the altar.",
           ("SequenceMemory", "GateLock"), ("Sigil_Gate", "Echo_Recorder"),
           {"sequenceLength": 4, "repeatCount": 1, "timeLimit": 30},
           "Target sequence replayed without an error", "Sequence reshuffles; one sanity drain"),
    puzzle("puzzle_016", "Tile Step Pattern", "SequenceMemory", 3,
           "Step across floor tiles in the order shown by the brief highlight pattern.",
           ("PatternMatch", "GateLock"), ("Plate_Pair", "Sigil_Gate"),
           {"tileCount": 6, "sequenceLength": 4, "timeLimit": 40},
           "All tiles light up in the target order", "Tiles dim and the pattern restarts"),
    puzzle("puzzle_003", "Twin Plate Gate", "PressurePlate", 1,
           "Stand on one plate and push a crate onto the other to open the gate.",
           ("PressurePlate", "GateLock"), ("Plate_Pair", "Platform_BoxCrate_Wooden"),
           {"plateCount": 2, "holdSeconds": 2, "timeLimit": 25},
           "Both plates stay down for two seconds", "Plates release and the gate stays shut"),
    puzzle("puzzle_015", "Counterweight Match", "PressurePlate", 3,
           "Fill the scale with household objects until the pointer sits inside the marked band.",
           ("WeightBalance", "GateLock"), ("Counterweight_Scale", "Obstacle_PlantPot_Large"),
           {"weightSteps": 3, "tolerance": 0.1, "timeLimit": 50},
           "Scale balanced within tolerance for one second", "Weights return to their starting slots"),
    puzzle("puzzle_017", "Ghost Plate Holder", "PressurePlate", 4,
           "Record a short echo so the ghost holds the far plate while you cross to the near one.",
           ("TimeEcho", "GateLock"), ("Echo_Recorder", "Plate_Pair"),
           {"echoSeconds": 6, "plateCount": 2, "timeLimit": 60},
           "Echo holds the far plate while you hold the near one", "Echo dissolves and both plates release"),
    puzzle("puzzle_004", "Silhouette Lock", "ShadowAlignment", 2,
           "Move the lantern until its cast shadow fits the silhouette drawn on the screen.",
           ("ShadowAligner", "GateLock"), ("Silhouette_Screen", "Sigil_Gate"),
           {"silhouetteCount": 1, "tolerancePixels": 6, "timeLimit": 35},
           "Shadow overlaps the drawn silhouette", "Silhouette returns to its neutral outline"),
    puzzle("puzzle_022", "Orbiting Shadow", "ShadowAlignment", 4,
           "Hold two shadows inside their outlines while the lantern swings on a slow arc.",
           ("ShadowAligner", "TimingWindow", "GateLock"), ("Silhouette_Screen", "Lantern_Altar"),
           {"silhouetteCount": 2, "swingPeriod": 2.5, "timeLimit": 50},
           "Both shadows stay aligned through one full swing", "Swing restarts from the centre"),
    puzzle("puzzle_005", "Three Knocks", "SoundTrigger", 1,
           "Knock three times on the pillar, leaving a short pause between each knock.",
           ("SoundTrigger", "GateLock"), ("Rhythm_Pillar", "Sigil_Gate"),
           {"cueCount": 3, "cueGap": 0.8, "timeLimit": 20},
           "Three knocks are answered in order", "Knocking pattern changes"),
    puzzle("puzzle_019", "Melody Answer", "SoundTrigger", 3,
           "Listen to a short melody on the pillar, then hum it back by pressing the tone stones.",
           ("SoundMemory", "GateLock"), ("Rhythm_Pillar", "Sigil_Gate"),
           {"noteCount": 5, "repeatCount": 1, "timeLimit": 40},
           "Melody replayed note for note", "Melody resets with a soft dissonance sting"),
    puzzle("puzzle_006", "Beam Bender", "MirrorReflection", 2,
           "Rotate two mirrors so the lantern beam reaches the receptor across the room.",
           ("MirrorReflector", "GateLock"), ("Mirror_Pedestal", "Beam_Emitter"),
           {"mirrorCount": 2, "targetCount": 1, "timeLimit": 40},
           "Beam lands on the target receptor", "Mirrors snap back to their neutral angles"),
    puzzle("puzzle_014", "Prism Split", "MirrorReflection", 4,
           "Split one beam through prisms and aim both halves at separate receptors.",
           ("MirrorReflector", "LaserGrid", "GateLock"), ("Prism_Rail", "Beam_Emitter", "Sigil_Gate"),
           {"mirrorCount": 3, "targetCount": 2, "timeLimit": 55},
           "Both receptors are lit without crossing a beam", "Beams retract and prisms realign"),
    puzzle("puzzle_007", "Glyph Key", "SymbolDecoding", 2,
           "Translate the carved glyph key and enter the matching three-symbol word.",
           ("SymbolDecoder", "GateLock"), ("Glyph_Alcove", "Sigil_Gate"),
           {"glyphCount": 4, "sequenceLength": 3, "timeLimit": 45},
           "Entered glyphs match the carved key", "Glyphs scramble but the key stays visible"),
    puzzle("puzzle_023", "Mirrored Glyph", "SymbolDecoding", 4,
           "Read glyphs from a mirror and enter them in the order they appear in the reflection.",
           ("SymbolDecoder", "MirrorReflector", "GateLock"), ("Glyph_Alcove", "Mirror_Pedestal"),
           {"glyphCount": 3, "sequenceLength": 3, "timeLimit": 55},
           "Reflected glyphs are entered in the right order", "Mirror darkens and the glyphs reset"),
    puzzle("puzzle_008", "Pendulum Press", "TimingWindow", 2,
           "Press the switch as the pendulum crosses the marked centre line, three times running.",
           ("TimingWindow", "GateLock"), ("Rhythm_Pillar", "Sigil_Gate"),
           {"windowSeconds": 0.4, "cueCount": 3, "timeLimit": 30},
           "Three presses land inside successive windows", "Pendulum resets its phase"),
    puzzle("puzzle_024", "Two-Beat Lock", "TimingWindow", 4,
           "Answer a visual flash and its audio tick on the same beat to arm the latch.",
           ("TimingWindow", "SoundTrigger", "GateLock"), ("Rhythm_Pillar", "Sigil_Gate"),
           {"windowSeconds": 0.3, "cueCount": 4, "timeLimit": 50},
           "Both cues are answered on the same beat", "Cue pair desynchronises and restarts"),
    puzzle("puzzle_009", "Quarter Turn", "SpatialReasoning", 3,
           "Rotate the room in ninety-degree steps until the exit lines up with the walkway.",
           ("RoomRotator", "GateLock"), ("Sigil_Gate", "Platform_Shelf_Floating"),
           {"rotationSteps": 4, "timeLimit": 45},
           "Room rotated until the exit aligns", "Room returns to zero degrees"),
    puzzle("puzzle_018", "False Perspective", "SpatialReasoning", 4,
           "Shift the viewing angle until separated planks read as one continuous bridge.",
           ("PerspectiveShift", "GateLock"), ("Perspective_Rail", "Platform_Shelf_Floating"),
           {"angleCount": 3, "timeLimit": 50},
           "Shifted platforms form a continuous walkway", "Camera snaps back to the default angle"),
    puzzle("puzzle_010", "Fuel for Passage", "ResourceTrade", 2,
           "Spend a quarter of the lantern charge to release the latch on the passage gate.",
           ("FuelTrade", "GateLock"), ("Lantern_Altar", "Sigil_Gate"),
           {"fuelCost": 0.25, "refundOnFailure": True, "timeLimit": 25},
           "Fuel spent and the gate latch released", "Fuel refunded and the latch drops back"),
    puzzle("puzzle_025", "Two Candles", "ResourceTrade", 4,
           "Pour fuel into two counterweights to balance a scale that opens the inner door.",
           ("FuelTrade", "WeightBalance", "GateLock"), ("Fuel_Cache", "Counterweight_Scale"),
           {"fuelCost": 0.35, "weightSteps": 2, "timeLimit": 55},
           "Both counterweights filled from the reserve", "Fuel refunded and the weights empty"),
    puzzle("puzzle_011", "Rising Tide", "Environmental", 2,
           "Open the valve in stages so the floating crate rises to the high alcove.",
           ("WaterLevel", "GateLock"), ("Water_Valve", "Platform_BoxCrate_Plastic"),
           {"waterLevels": 3, "timeLimit": 45},
           "Float platform lifts to the alcove", "Water drains back to the low mark"),
    puzzle("puzzle_012", "Wind Lift", "Environmental", 3,
           "Aim two fans so a gust carries the fallen laundry off the latch.",
           ("WindCurrent", "GateLock"), ("Wind_Fan", "Obstacle_ClothPile_Laundry"),
           {"fanCount": 2, "gustSeconds": 2, "timeLimit": 45},
           "Gust carries the cloth clear of the latch", "Fans stop and the cloth settles back"),
    puzzle("puzzle_020", "Thaw and Climb", "Environmental", 5,
           "Light the candle, melt the ice, let the water feed the vine, then climb the ledge.",
           ("EnvironmentalCombo", "GateLock"), ("Vine_Anchor", "Platform_Shelf_Bookshelf"),
           {"chainLength": 4, "timeLimit": 60},
           "Ice melts, water grows the vine, vine reaches the ledge", "Ice reforms and the vine withers"),
    puzzle("puzzle_013", "Hidden Embers", "MemoryPalace", 2,
           "Four embers are revealed briefly, then hidden; touch each one from memory.",
           ("MemoryPalace", "GateLock"), ("Memory_Niche", "Sigil_Gate"),
           {"objectCount": 4, "revealSeconds": 2, "timeLimit": 45},
           "All hidden embers touched after the reveal", "Embers rehide in new slots"),
    puzzle("puzzle_026", "Hidden Order", "MemoryPalace", 4,
           "Remember both the places and the order of five embers, then touch them in sequence.",
           ("MemoryPalace", "SequenceMemory", "GateLock"), ("Memory_Niche", "Echo_Recorder"),
           {"objectCount": 5, "sequenceLength": 3, "timeLimit": 55},
           "Hidden objects touched in the revealed order", "Order reshuffles and objects rehide"),
]


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_platform(entry):
    category, variant, size, surface, silhouette, palette, details = entry
    prefab = f"Platform_{category}_{variant}"
    return {
        "schemaVersion": 1,
        "prefab": prefab,
        "category": category,
        "variant": variant,
        "tag": "Platform",
        "layer": {"name": "Standable", "index": 7},
        "collider": {
            "type": "BoxCollider2D",
            "rect": list(surface),
            "isTrigger": False,
        },
        "visual": {
            "bounds": [0, 0, size[0], size[1]],
            "standableSurface": list(surface),
            "silhouette": silhouette,
            "palette": list(palette),
            "details": list(details),
        },
        "platformData": {
            "id": f"PlatformData_{category}_{variant}",
            "platformType": category,
            "maxStandAngle": 45.0,
            "isStable": True,
            "creakSound": None,
        },
    }


def build_obstacle(entry):
    (category, variant, size, colliders, silhouette, palette, details,
     tripping, noise, clearable, clear_time) = entry
    prefab = f"Obstacle_{category}_{variant}"
    return {
        "schemaVersion": 1,
        "prefab": prefab,
        "category": category,
        "variant": variant,
        "tag": "Obstacle",
        "layer": {"name": "Obstacle", "index": 8},
        "colliders": [
            {"type": "BoxCollider2D", "rect": list(rect), "isTrigger": False}
            for rect in colliders
        ],
        "visual": {
            "bounds": [0, 0, size[0], size[1]],
            "silhouette": silhouette,
            "palette": list(palette),
            "details": list(details),
        },
        "obstacleData": {
            "id": f"ObstacleData_{category}_{variant}",
            "obstacleType": category,
            "trippingChance": tripping,
            "noiseLevel": noise,
            "canBeCleared": clearable,
            "clearTime": clear_time,
        },
    }


def params_text(params: dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in params.items())


def build_index(puzzles: list[dict]) -> str:
    lines = [
        "# Puzzle catalog index",
        "",
        f"{len(puzzles)} puzzles. Generated from `puzzle_catalog.json` by `scripts/generate_content.py`; "
        "edit the table in that script and regenerate rather than editing this file by hand.",
        "",
        "Every `requiredComponents` name is from the F4 component framework (Task F4 of "
        "`TASK_SPLIT_SPEC.md`); `GateLock` is the gate-facing lock named in the same spec. "
        "All puzzles are designed to be solvable in 60 seconds or less; a positive `timeLimit` "
        "is the authoring budget in seconds and never exceeds 60.",
        "",
        "Puzzle-specific prefab dependencies (`*_Gate`, `*_Pedestal`, etc.) are F4-owned forward "
        "references. Dependencies prefixed `Platform_` or `Obstacle_` resolve to this repository's "
        "generated libraries.",
        "",
        "| ID | Name | Category | Diff | Components | Prefabs | Variant params | Unlock | Failure |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in puzzles:
        lines.append(
            "| {id} | {name} | {category} | {difficulty} | {components} | {prefabs} | {params} | "
            "{unlock} | {failure} |".format(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                difficulty=item["difficulty"],
                components=", ".join(f"`{c}`" for c in item["requiredComponents"]),
                prefabs=", ".join(f"`{p}`" for p in item["prefabDependencies"]),
                params=params_text(item["variantParams"]),
                unlock=item["unlockCondition"],
                failure=item["failureState"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def build_prefab_index(title: str, prefabs: list[dict], kind: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"{len(prefabs)} prefabs, generated by `scripts/generate_content.py`. "
        "This is the name list from the O1/O2 delivery checklist.",
        "",
    ]
    if kind == "platform":
        lines += [
            "| Prefab | Category | Standable collider (x, y, w, h) | Visual signature | PlatformData |",
            "|---|---|---|---|---|",
        ]
        for data in prefabs:
            lines.append(
                f"| `{data['prefab']}` | {data['category']} | "
                f"{rect_text(data['collider']['rect'])} | {data['visual']['silhouette']} | "
                f"{data['platformData']['id']} |"
            )
    else:
        lines += [
            "| Prefab | Category | Colliders | Trip / noise | Clear time | Visual signature |",
            "|---|---|---|---|---|---|",
        ]
        for data in prefabs:
            stats = data["obstacleData"]
            lines.append(
                f"| `{data['prefab']}` | {data['category']} | {len(data['colliders'])} | "
                f"{stats['trippingChance']:.2f} / {stats['noiseLevel']:.2f} | "
                f"{stats['clearTime']:.1f}s | {data['visual']['silhouette']} |"
            )
    lines.append("")
    return "\n".join(lines)


def rect_text(rect: list[float]) -> str:
    return "(" + ", ".join(str(value) for value in rect) + ")"


def main() -> None:
    platforms = [build_platform(entry) for entry in PLATFORMS]
    obstacles = [build_obstacle(entry) for entry in OBSTACLES]
    for prefab in platforms:
        write_json(PLATFORM_DIR / f"{prefab['prefab']}.json", prefab)
    for prefab in obstacles:
        write_json(OBSTACLE_DIR / f"{prefab['prefab']}.json", prefab)
    write_json(PUZZLE_DIR / "puzzle_catalog.json", {"puzzles": PUZZLES})
    (PUZZLE_DIR / "puzzle_index.md").write_text(build_index(PUZZLES), encoding="utf-8")
    (PLATFORM_DIR.parent / "PLATFORM_LIBRARY.md").write_text(
        build_prefab_index("Platform prefab library", platforms, "platform"), encoding="utf-8"
    )
    (OBSTACLE_DIR.parent / "OBSTACLE_LIBRARY.md").write_text(
        build_prefab_index("Obstacle prefab library", obstacles, "obstacle"), encoding="utf-8"
    )
    print(f"platforms={len(platforms)} obstacles={len(obstacles)} puzzles={len(PUZZLES)}")


if __name__ == "__main__":
    main()
