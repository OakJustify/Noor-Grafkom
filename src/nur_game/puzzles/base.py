"""Base state, events and parameter helpers shared by all puzzle components."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _params(*sources: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source in sources:
        if not source:
            continue
        if isinstance(source, dict):
            if "variantParams" in source and isinstance(source["variantParams"], dict):
                result.update(source["variantParams"])
            result.update({k: v for k, v in source.items() if k != "variantParams"})
    return result


def _int(params: dict[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        if key in params:
            return int(params[key])
    return default


def _float(params: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in params:
            return float(params[key])
    return default


class PuzzleEvent:
    """A tiny multicast event that supports ``+=`` and ``append``."""

    def __init__(self):
        self._listeners: list[Callable[[Any], None]] = []

    def append(self, listener: Callable[[Any], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def __iadd__(self, listener):
        self.append(listener)
        return self

    def __isub__(self, listener):
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass
        return self

    def __call__(self, *args, **kwargs) -> None:
        for listener in list(self._listeners):
            listener(*args, **kwargs)

    def __len__(self) -> int:
        return len(self._listeners)

    def clear(self) -> None:
        self._listeners.clear()


class PuzzleComponent:
    """Base class for every F4 puzzle component."""

    component_name = "PuzzleComponent"

    def __init__(self, component_id: str | None = None, params: Any = None, **kwargs):
        if isinstance(component_id, dict) and params is None:
            params = component_id
            component_id = None
        self.id = component_id
        self.params = _params(params, kwargs)
        self.solved = False
        self.failed = False
        self.enabled = True
        self.OnPuzzleSolved = PuzzleEvent()
        self.OnPuzzleFailed = PuzzleEvent()
        # Common alias expected by Python-style callers.
        self.on_puzzle_solved = self.OnPuzzleSolved
        self.on_puzzle_failed = self.OnPuzzleFailed

    def reset_puzzle(self) -> None:
        self.solved = False
        self.failed = False
        self.enabled = True

    def save_state(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.component_name,
            "solved": self.solved,
            "failed": self.failed,
            "enabled": self.enabled,
            "params": dict(self.params),
        }

    def load_state(self, state: dict[str, Any] | None) -> None:
        if not state:
            return
        self.solved = bool(state.get("solved", self.solved))
        self.failed = bool(state.get("failed", self.failed))
        self.enabled = bool(state.get("enabled", self.enabled))

    def notify_solved(self) -> None:
        if not self.solved:
            self.solved = True
            self.OnPuzzleSolved(self)

    def notify_failed(self) -> None:
        if not self.failed:
            self.failed = True
            self.OnPuzzleFailed(self)

    def update(self, dt: float = 0.0) -> None:
        return None

    # Unity-style aliases.
    ResetPuzzle = reset_puzzle
    SaveState = save_state
    LoadState = load_state

