#!/usr/bin/env python3
"""Executable acceptance checks for the generated prefab and puzzle catalogs.

Replaces the Unity Editor validators from the task spec with dependency-free
Python checks. Run from anywhere:

    python scripts/validate_content.py
    python scripts/validate_content.py platforms
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PLATFORM_CATEGORIES = {
    "Table": 4, "Chair": 4, "BoxCrate": 5, "BookStack": 3, "Shelf": 3,
    "Cabinet": 3, "Bed": 2, "Sofa": 2, "Appliance": 3, "MiscHousehold": 4,
}
OBSTACLE_CATEGORIES = {
    "ClothPile": 3, "ToyCluster": 4, "WireTangle": 3, "FurnitureLeg": 4,
    "RugEdge": 3, "Threshold": 3, "PlantPot": 3, "DecorItem": 4,
    "StackedBoxes": 3, "LaundryBasket": 2,
}
PUZZLE_CATEGORIES = {
    "ColorLogic", "SequenceMemory", "PressurePlate", "ShadowAlignment",
    "SoundTrigger", "MirrorReflection", "SymbolDecoding", "TimingWindow",
    "SpatialReasoning", "ResourceTrade", "Environmental", "MemoryPalace",
}

# Classes named by Task F4's implementation table, plus GateLock (named in the
# puzzle_001 example and in F4's SigilDetector description).
STATIC_COMPONENTS = frozenset({
    "ColorCycler", "SigilDetector", "GateLock", "SequenceMemory", "PressurePlate",
    "ShadowAligner", "SoundTrigger", "MirrorReflector", "SymbolDecoder",
    "TimingWindow", "RoomRotator", "FuelTrade", "WaterLevel", "WindCurrent",
    "MemoryPalace", "LaserGrid", "WeightBalance", "PatternMatch", "TimeEcho",
    "PerspectiveShift", "SoundMemory", "EnvironmentalCombo",
})
try:
    # Both deliveries are merged: validate against what F4 actually implements.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from nur_game.puzzles import COMPONENT_CLASSES as _F4_CLASSES

    ALLOWED_COMPONENTS = frozenset(_F4_CLASSES)
except ImportError:  # standalone use without the game package installed
    ALLOWED_COMPONENTS = STATIC_COMPONENTS

# F4-owned puzzle hardware; other dependencies must be generated prefabs.
PUZZLE_PROPS = frozenset({
    "Sigil_Gate", "ColorPedestal", "Plate_Pair", "Echo_Recorder",
    "Counterweight_Scale", "Silhouette_Screen", "Lantern_Altar", "Rhythm_Pillar",
    "Mirror_Pedestal", "Beam_Emitter", "Prism_Rail", "Glyph_Alcove",
    "Perspective_Rail", "Fuel_Cache", "Water_Valve", "Wind_Fan",
    "Vine_Anchor", "Memory_Niche",
})

# trip min/max, noise min/max. Wires trip easily but stay quiet; toys clatter.
TUNING_BOUNDS = {
    "ClothPile": (.35, .65, .05, .30), "ToyCluster": (.50, .80, .55, .90),
    "WireTangle": (.80, 1.0, .05, .30), "FurnitureLeg": (.60, .85, .30, .55),
    "RugEdge": (.65, .90, .05, .25), "Threshold": (.45, .75, .20, .45),
    "PlantPot": (.45, .75, .50, .85), "DecorItem": (.30, .60, .25, .80),
    "StackedBoxes": (.55, .85, .40, .75), "LaundryBasket": (.50, .80, .25, .55),
}

NAME_RE = re.compile(r"^(Platform|Obstacle)_([A-Za-z]+)_([A-Za-z0-9]+)$")
PUZZLE_ID_RE = re.compile(r"^puzzle_[0-9]{3}$")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rect_str(rect: Any) -> str:
    return f"[{', '.join(str(v) for v in rect)}]"


def valid_rect(rect: Any) -> bool:
    return (
        isinstance(rect, list) and len(rect) == 4
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in rect)
        and rect[0] >= 0 and rect[1] >= 0 and rect[2] > 0 and rect[3] > 0
    )


EPS = 1e-9  # Rectangles are authored in decimal world units; allow float rounding.


def inside(rect: list[float], bounds: list[float]) -> bool:
    return (
        rect[0] >= bounds[0] - EPS and rect[1] >= bounds[1] - EPS
        and rect[0] + rect[2] <= bounds[0] + bounds[2] + EPS
        and rect[1] + rect[3] <= bounds[1] + bounds[3] + EPS
    )


def overlaps(a: list[float], b: list[float]) -> bool:
    """Positive-area intersection only; shared edges are fine."""
    return (
        a[0] < b[0] + b[2] - EPS and b[0] < a[0] + a[2] - EPS
        and a[1] < b[1] + b[3] - EPS and b[1] < a[1] + a[3] - EPS
    )


def common_checks(data: dict, path: Path, errors: list[str]) -> tuple[str, str, str] | None:
    expected = NAME_RE.match(path.stem)
    if not expected:
        errors.append(f"{path.name}: filename must be Platform_Category_Variant or Obstacle_Category_Variant")
        return None
    kind, category, variant = expected.groups()
    if data.get("prefab") != path.stem:
        errors.append(f"{path.name}: prefab field {data.get('prefab')!r} does not match filename")
    if data.get("category") != category or data.get("variant") != variant:
        errors.append(f"{path.name}: category/variant do not match filename")
    if data.get("schemaVersion") != 1:
        errors.append(f"{path.name}: schemaVersion must be 1")
    visual = data.get("visual")
    if not isinstance(visual, dict):
        errors.append(f"{path.name}: missing visual block")
        return None
    bounds = visual.get("bounds")
    if not valid_rect(bounds):
        errors.append(f"{path.name}: visual.bounds must be a positive rect")
        return None
    return kind, category, variant


def validate_platforms(root: Path = ROOT) -> list[str]:
    directory = root / "assets" / "content" / "platforms" / "generated"
    errors: list[str] = []
    files = sorted(directory.glob("Platform_*.json"))
    if len(files) < 30:
        errors.append(f"platforms: expected 30+ prefabs, found {len(files)}")
    counts: Counter[str] = Counter()
    signatures: set[tuple[Any, ...]] = set()

    for path in files:
        data = load_json(path)
        parsed = common_checks(data, path, errors)
        if not parsed:
            continue
        _, category, variant = parsed
        counts[category] += 1
        if data.get("tag") != "Platform":
            errors.append(f"{path.name}: tag must be 'Platform'")
        if data.get("layer") != {"name": "Standable", "index": 7}:
            errors.append(f"{path.name}: layer must be Standable/7")

        collider = data.get("collider")
        if not isinstance(collider, dict) or collider.get("type") != "BoxCollider2D":
            errors.append(f"{path.name}: missing BoxCollider2D")
            continue
        if collider.get("isTrigger") is not False:
            errors.append(f"{path.name}: collider must not be a trigger")
        rect = collider.get("rect")
        bounds = data["visual"]["bounds"]
        if not valid_rect(rect):
            errors.append(f"{path.name}: collider.rect must be a positive rect")
            continue
        if not inside(rect, bounds):
            errors.append(f"{path.name}: collider {rect_str(rect)} escapes visual bounds {rect_str(bounds)}")
        if rect != data["visual"].get("standableSurface"):
            errors.append(f"{path.name}: collider must match visual.standableSurface")

        platform_data = data.get("platformData")
        if not isinstance(platform_data, dict):
            errors.append(f"{path.name}: missing PlatformData")
            continue
        if platform_data.get("id") != f"PlatformData_{category}_{variant}":
            errors.append(f"{path.name}: PlatformData id must be unique per variant")
        if platform_data.get("platformType") != category:
            errors.append(f"{path.name}: platformType must match category")
        if platform_data.get("maxStandAngle") != 45.0:
            errors.append(f"{path.name}: maxStandAngle must default to 45")
        if platform_data.get("isStable") is not True:
            errors.append(f"{path.name}: isStable must default to true")
        sound = platform_data.get("creakSound", None)
        if sound is not None and not isinstance(sound, str):
            errors.append(f"{path.name}: creakSound must be null or a path")

        signature = (
            data["visual"].get("silhouette"), tuple(data["visual"].get("palette", ())),
            tuple(data["visual"].get("details", ())), tuple(bounds), tuple(rect),
        )
        if signature in signatures:
            errors.append(f"{path.name}: visual signature duplicates another prefab")
        signatures.add(signature)

    for category, minimum in PLATFORM_CATEGORIES.items():
        if counts[category] < minimum:
            errors.append(f"platforms: {category} has {counts[category]}, needs {minimum}")
    return errors


def validate_obstacles(root: Path = ROOT) -> list[str]:
    directory = root / "assets" / "content" / "obstacles" / "generated"
    errors: list[str] = []
    files = sorted(directory.glob("Obstacle_*.json"))
    if len(files) < 25:
        errors.append(f"obstacles: expected 25+ prefabs, found {len(files)}")
    counts: Counter[str] = Counter()
    signatures: set[tuple[Any, ...]] = set()

    for path in files:
        data = load_json(path)
        parsed = common_checks(data, path, errors)
        if not parsed:
            continue
        _, category, variant = parsed
        counts[category] += 1
        if data.get("tag") != "Obstacle":
            errors.append(f"{path.name}: tag must be 'Obstacle'")
        if data.get("layer") != {"name": "Obstacle", "index": 8}:
            errors.append(f"{path.name}: layer must be Obstacle/8")

        colliders = data.get("colliders")
        bounds = data["visual"]["bounds"]
        if not isinstance(colliders, list) or not colliders:
            errors.append(f"{path.name}: at least one collider is required")
            continue
        rects: list[list[float]] = []
        for index, collider in enumerate(colliders):
            if not isinstance(collider, dict) or collider.get("type") != "BoxCollider2D":
                errors.append(f"{path.name}: collider {index} must be BoxCollider2D")
                continue
            if collider.get("isTrigger") is not False:
                errors.append(f"{path.name}: collider {index} must not be a trigger")
            rect = collider.get("rect")
            if not valid_rect(rect):
                errors.append(f"{path.name}: collider {index} must be a positive rect")
                continue
            if not inside(rect, bounds):
                errors.append(f"{path.name}: collider {index} escapes visual bounds")
            for other in rects:
                if overlaps(rect, other):
                    errors.append(f"{path.name}: colliders {rect_str(rect)} and {rect_str(other)} overlap")
            rects.append(rect)

        obstacle_data = data.get("obstacleData")
        if not isinstance(obstacle_data, dict):
            errors.append(f"{path.name}: missing ObstacleData")
            continue
        if obstacle_data.get("id") != f"ObstacleData_{category}_{variant}":
            errors.append(f"{path.name}: ObstacleData id must be unique per variant")
        if obstacle_data.get("obstacleType") != category:
            errors.append(f"{path.name}: obstacleType must match category")
        trip = obstacle_data.get("trippingChance")
        noise = obstacle_data.get("noiseLevel")
        if not isinstance(trip, (int, float)) or not 0 <= trip <= 1:
            errors.append(f"{path.name}: trippingChance must be within 0..1")
        if not isinstance(noise, (int, float)) or not 0 <= noise <= 1:
            errors.append(f"{path.name}: noiseLevel must be within 0..1")
        if category in TUNING_BOUNDS and isinstance(trip, (int, float)) and isinstance(noise, (int, float)):
            trip_min, trip_max, noise_min, noise_max = TUNING_BOUNDS[category]
            if not trip_min <= trip <= trip_max:
                errors.append(f"{path.name}: trippingChance {trip} outside {category} band {trip_min}..{trip_max}")
            if not noise_min <= noise <= noise_max:
                errors.append(f"{path.name}: noiseLevel {noise} outside {category} band {noise_min}..{noise_max}")
        clearable = obstacle_data.get("canBeCleared")
        clear_time = obstacle_data.get("clearTime")
        if not isinstance(clearable, bool):
            errors.append(f"{path.name}: canBeCleared must be a bool")
        if not isinstance(clear_time, (int, float)) or clear_time < 0:
            errors.append(f"{path.name}: clearTime must be >= 0")
        elif isinstance(clearable, bool):
            if clearable and clear_time <= 0:
                errors.append(f"{path.name}: clearable obstacles need a positive clearTime")
            if not clearable and clear_time != 0:
                errors.append(f"{path.name}: fixed obstacles must have clearTime 0")

        signature = (
            data["visual"].get("silhouette"), tuple(data["visual"].get("palette", ())),
            tuple(data["visual"].get("details", ())), tuple(bounds),
            tuple(tuple(rect) for rect in rects),
        )
        if signature in signatures:
            errors.append(f"{path.name}: visual signature duplicates another prefab")
        signatures.add(signature)

    for category, minimum in OBSTACLE_CATEGORIES.items():
        if counts[category] < minimum:
            errors.append(f"obstacles: {category} has {counts[category]}, needs {minimum}")
    return errors


def schema_errors(value: Any, schema: dict, path: str = "$") -> list[str]:
    """Minimal JSON-Schema checker for the keywords used by puzzle/schema.json."""
    errors: list[str] = []
    expected = schema.get("type")
    type_checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    if expected and not type_checks[expected](value):
        return [f"{path}: expected {expected}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not an allowed value")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']} characters")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} is above maximum {schema['maximum']}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}: items must be unique")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(schema_errors(item, schema["items"], f"{path}[{index}]"))
    if isinstance(value, dict):
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            errors.append(f"{path}: needs at least {schema['minProperties']} properties")
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field {key}")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                errors.extend(schema_errors(item, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected field {key}")
    return errors


def validate_puzzles(root: Path = ROOT) -> list[str]:
    directory = root / "assets" / "content" / "puzzles"
    errors: list[str] = []
    catalog_path = directory / "puzzle_catalog.json"
    schema_path = directory / "schema.json"
    index_path = directory / "puzzle_index.md"
    for path in (catalog_path, schema_path, index_path):
        if not path.is_file():
            errors.append(f"puzzles: missing {path.relative_to(root)}")
    if errors:
        return errors

    catalog = load_json(catalog_path)
    errors.extend(schema_errors(catalog, load_json(schema_path)))
    puzzles = catalog.get("puzzles", [])
    if not isinstance(puzzles, list):
        return errors

    prefabs = {
        path.stem
        for folder in ("platforms", "obstacles")
        for path in (root / "assets" / "content" / folder / "generated").glob("*.json")
    }
    ids: set[str] = set()
    names: set[str] = set()
    mechanics: set[tuple[str, ...]] = set()
    categories: Counter[str] = Counter()

    for item in puzzles:
        if not isinstance(item, dict):
            continue
        pid = item.get("id", "?")
        if pid in ids:
            errors.append(f"puzzles: duplicate id {pid}")
        ids.add(pid)
        if isinstance(pid, str) and PUZZLE_ID_RE.fullmatch(pid) and int(pid[-3:]) < 1:
            errors.append(f"{pid}: numbering starts at 001")
        name = item.get("name")
        if name in names:
            errors.append(f"puzzles: duplicate name {name}")
        names.add(name)

        category = item.get("category")
        categories[category] += 1
        if category in PUZZLE_CATEGORIES and categories[category] > 3:
            errors.append(f"{pid}: category {category} has more than three entries")

        components = item.get("requiredComponents", [])
        if isinstance(components, list):
            unknown = [c for c in components if c not in ALLOWED_COMPONENTS]
            if unknown:
                errors.append(f"{pid}: components not implemented by F4: {', '.join(unknown)}")
            key = tuple(sorted(components))
            if key in mechanics:
                errors.append(f"{pid}: duplicate component mechanic {key}")
            mechanics.add(key)

        dependencies = item.get("prefabDependencies", [])
        if isinstance(dependencies, list):
            unresolved = [p for p in dependencies if p not in prefabs and p not in PUZZLE_PROPS]
            if unresolved:
                errors.append(f"{pid}: unresolved prefabs: {', '.join(unresolved)}")

        params = item.get("variantParams", {})
        if isinstance(params, dict):
            limit = params.get("timeLimit", 0)
            if isinstance(limit, (int, float)) and not 0 <= limit <= 60:
                errors.append(f"{pid}: timeLimit {limit} exceeds the 60-second design budget")

    for category in sorted(PUZZLE_CATEGORIES):
        if categories[category] < 2:
            errors.append(f"puzzles: category {category} has {categories[category]}, needs 2")

    index = index_path.read_text(encoding="utf-8")
    for item in puzzles:
        if not isinstance(item, dict):
            continue
        if item.get("id") not in index:
            errors.append(f"puzzles: index is missing id {item.get('id')}")
        if item.get("name") not in index:
            errors.append(f"puzzles: index is missing name {item.get('name')}")
    return errors


def validate_all(root: Path = ROOT) -> dict[str, list[str]]:
    return {
        "platforms": validate_platforms(root),
        "obstacles": validate_obstacles(root),
        "puzzles": validate_puzzles(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("part", nargs="?", choices=("all", "platforms", "obstacles", "puzzles"), default="all")
    args = parser.parse_args()
    results = validate_all()
    selected = results if args.part == "all" else {args.part: results[args.part]}
    total = 0
    for name, errors in selected.items():
        print(f"{name}: {'OK' if not errors else str(len(errors)) + ' error(s)'}")
        for error in errors:
            print(f"  - {error}")
        total += len(errors)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
