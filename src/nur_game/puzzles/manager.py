"""Generated puzzle objects and the manager that builds, saves and resets them."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import PuzzleComponent, _params
from .catalog import load_puzzle_catalog
from .components import GateLock
from .registry import COMPONENT_CLASSES


@dataclass
class GeneratedPuzzle:
    spec_id: str
    name: str
    params: dict[str, Any]
    components: list[PuzzleComponent] = field(default_factory=list)
    gate: GateLock | None = None

    @property
    def solved(self) -> bool:
        return bool(self.gate is not None and not self.gate.locked)

    def reset_puzzle(self) -> None:
        for component in self.components:
            component.reset_puzzle()
        if self.gate is not None:
            self.gate.lock()

    def save_state(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "name": self.name,
            "params": dict(self.params),
            "components": {c.id or c.component_name: c.save_state() for c in self.components},
        }

    def load_state(self, state: dict[str, Any] | None) -> None:
        if not state:
            return
        saved = state.get("components", {})
        for component in self.components:
            key = component.id or component.component_name
            if key in saved:
                component.load_state(saved[key])

    def update(self, dt: float = 0.0) -> None:
        for component in self.components:
            component.update(dt)

    ResetPuzzle = reset_puzzle
    SaveState = save_state
    LoadState = load_state


class PuzzleManager:
    def __init__(self, save_path: str | Path | None = None):
        self.save_path = Path(save_path) if save_path is not None else None
        self.components: dict[str, PuzzleComponent] = {}
        self.component_order: list[str] = []
        self.puzzles: dict[str, GeneratedPuzzle] = {}
        self._progress: dict[str, dict[str, Any]] = {}

    def register(self, component: PuzzleComponent) -> PuzzleComponent:
        key = component.id or f"{component.component_name}_{len(self.component_order)}"
        if component.id is None:
            component.id = key
        self.components[key] = component
        if key not in self.component_order:
            self.component_order.append(key)
        return component

    def unregister(self, component_or_id) -> None:
        if isinstance(component_or_id, PuzzleComponent):
            key = component_or_id.id
        else:
            key = str(component_or_id)
        self.components.pop(key, None)
        if key in self.component_order:
            self.component_order.remove(key)

    def notify_solved(self, component: PuzzleComponent) -> None:
        if isinstance(component, PuzzleComponent):
            component.notify_solved()
        if isinstance(component, GateLock):
            return
        # A generated puzzle completes when its GateLock has been unlocked by
        # an explicit unlock call; components only mark themselves solved.

    def notify_failed(self, component: PuzzleComponent) -> None:
        if isinstance(component, PuzzleComponent):
            component.notify_failed()

    def generate_from_spec(self, spec: dict[str, Any] | str | None = None, catalog: Iterable[dict[str, Any]] | None = None) -> GeneratedPuzzle:
        if isinstance(spec, str):
            spec = self._find_spec(spec, catalog)
        spec = dict(spec or {})
        params = _params(spec)
        components: list[PuzzleComponent] = []
        for name in spec.get("requiredComponents", []):
            cls = COMPONENT_CLASSES.get(name)
            if cls is None:
                raise ValueError(f"unknown puzzle component: {name}")
            component = cls(params=dict(params))
            component.id = f"{spec.get('id', 'puzzle')}:{name}"
            self.register(component)
            components.append(component)
        gate = GateLock(params=dict(params))
        gate.id = f"{spec.get('id', 'puzzle')}:GateLock"
        self.register(gate)
        components.append(gate)
        puzzle = GeneratedPuzzle(
            spec_id=str(spec.get("id", "")),
            name=str(spec.get("name", "")),
            params=params,
            components=components,
            gate=gate,
        )
        if spec.get("id"):
            self.puzzles[str(spec["id"])] = puzzle
        # Link GateLock unlock to all non-gate components being solved.
        non_gates = [c for c in components if not isinstance(c, GateLock)]

        def _maybe_unlock(_component=None):
            if non_gates and all(c.solved for c in non_gates) and gate.locked:
                gate.locked = False
                gate.notify_solved()

        for component in non_gates:
            component.OnPuzzleSolved.append(_maybe_unlock)
        puzzle._maybe_unlock = _maybe_unlock
        return puzzle

    def _find_spec(self, spec_id: str, catalog=None) -> dict[str, Any]:
        if catalog is None:
            catalog = load_puzzle_catalog()
        for item in catalog:
            if item.get("id") == spec_id:
                return item
        raise KeyError(spec_id)

    def save_progress(self, save_key: str | None = None) -> dict[str, Any]:
        data = {
            "components": {
                key: component.save_state() for key, component in self.components.items()
            },
            "puzzles": {pid: puzzle.save_state() for pid, puzzle in self.puzzles.items()},
        }
        key = save_key if save_key is not None else "default"
        self._progress[str(key)] = data
        if self.save_path is not None and str(key).endswith(".json"):
            path = Path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return data

    def load_progress(self, save_key: str | None = None, data: dict[str, Any] | None = None) -> bool:
        key = save_key if save_key is not None else "default"
        if data is None:
            if str(key).endswith(".json"):
                path = Path(key)
                if not path.exists():
                    return False
                data = json.loads(path.read_text(encoding="utf-8"))
            else:
                data = self._progress.get(str(key))
        if not data:
            return False
        saved_components = data.get("components", {})
        for key_name, component in self.components.items():
            if key_name in saved_components:
                component.load_state(saved_components[key_name])
        saved_puzzles = data.get("puzzles", {})
        for pid, puzzle in self.puzzles.items():
            if pid in saved_puzzles:
                puzzle.load_state(saved_puzzles[pid])
        self._progress[str(key)] = data
        return True

    def reset_all(self) -> None:
        for component in self.components.values():
            component.reset_puzzle()
        for puzzle in self.puzzles.values():
            puzzle.reset_puzzle()

    # Unity-style aliases.
    Register = register
    Unregister = unregister
    NotifySolved = notify_solved
    NotifyFailed = notify_failed
    SaveProgress = save_progress
    LoadProgress = load_progress
    GenerateFromSpec = generate_from_spec

