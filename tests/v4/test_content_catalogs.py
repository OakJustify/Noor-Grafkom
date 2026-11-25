"""Acceptance checks for O1-O3 content, ported to the Python v4 project."""

import importlib.util
from pathlib import Path

from nur_game.puzzles import COMPONENT_CLASSES, PuzzleManager, load_puzzle_catalog

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "validate_content", ROOT / "src" / "scripts" / "validate_content.py"
)
validate_content = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_content)


def test_platform_library():
    assert validate_content.validate_platforms(ROOT) == []


def test_obstacle_library():
    assert validate_content.validate_obstacles(ROOT) == []


def test_puzzle_catalog():
    assert validate_content.validate_puzzles(ROOT) == []


def test_puzzle_catalog_matches_f4_registry():
    specs = load_puzzle_catalog()
    used = {name for spec in specs for name in spec["requiredComponents"]}
    assert used == set(COMPONENT_CLASSES)

    manager = PuzzleManager()
    for spec in specs:
        generated = manager.generate_from_spec(spec)
        assert generated.spec_id == spec["id"]
        assert generated.gate is not None


def test_catalog_load_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert len(load_puzzle_catalog()) >= 20
