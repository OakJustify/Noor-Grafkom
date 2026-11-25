"""The 22 concrete F4 puzzle components.

Each class is a small, data-driven object; ``variantParams`` from the catalog
are read with camelCase keys and mirrored as snake_case attributes.
"""

from __future__ import annotations

from typing import Any

from .base import PuzzleComponent, PuzzleEvent, _float, _int, _params


class GateLock(PuzzleComponent):
    component_name = "GateLock"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.locked = True
        self.hold_time = 0.0
        self.required_hold = _float(self.params, "holdSeconds", "hold_seconds", default=0.0)

    def unlock(self) -> None:
        self.locked = False
        self.notify_solved()

    def lock(self) -> None:
        self.locked = True
        self.solved = False

    def save_state(self):
        state = super().save_state()
        state.update({"locked": self.locked, "hold_time": self.hold_time})
        return state

    def load_state(self, state):
        super().load_state(state)
        if state:
            self.locked = bool(state.get("locked", self.locked))
            self.hold_time = float(state.get("hold_time", self.hold_time))


class ColorCycler(PuzzleComponent):
    component_name = "ColorCycler"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.color_count = _int(self.params, "colorCount", "color_count", default=3)
        self.colors = list(range(max(1, self.color_count)))
        self.index = 0
        self.target = 0

    def cycle(self, step: int = 1) -> int:
        self.index = (self.index + step) % len(self.colors)
        return self.index

    def set_color(self, value: int) -> None:
        self.index = value % len(self.colors)

    def matches(self, target: int | None = None) -> bool:
        return self.index == (self.target if target is None else target)


class SigilDetector(PuzzleComponent):
    component_name = "SigilDetector"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.detected = False
        self.color_count = _int(self.params, "colorCount", "color_count", default=3)

    def detect(self, color: int) -> bool:
        self.detected = True
        self.last_color = color
        return True


class SequenceMemory(PuzzleComponent):
    component_name = "SequenceMemory"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.sequence_length = _int(self.params, "sequenceLength", "sequence_length", default=4)
        self.repeat_count = _int(self.params, "repeatCount", "repeat_count", default=1)
        self.target = list(range(self.sequence_length))
        self.input: list[int] = []
        self.completed_repeats = 0

    def press(self, value: int) -> bool:
        self.input.append(int(value))
        if self.input[-len(self.target):] == self.target:
            self.completed_repeats += 1
            self.input.clear()
            if self.completed_repeats >= self.repeat_count:
                self.notify_solved()
            return True
        if len(self.input) >= len(self.target) and self.input != self.target:
            self.input.clear()
            self.notify_failed()
        return False

    def reset_puzzle(self):
        super().reset_puzzle()
        self.input.clear()
        self.completed_repeats = 0


class PressurePlate(PuzzleComponent):
    component_name = "PressurePlate"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.plate_count = _int(self.params, "plateCount", "plate_count", default=2)
        self.hold_seconds = _float(self.params, "holdSeconds", "hold_seconds", default=2.0)
        self.pressed = [False] * max(1, self.plate_count)
        self.hold_time = 0.0

    def set_pressed(self, index: int, value: bool = True) -> None:
        if 0 <= index < len(self.pressed):
            self.pressed[index] = bool(value)

    def all_pressed(self) -> bool:
        return all(self.pressed)

    def update(self, dt=0.0):
        if self.all_pressed():
            self.hold_time += float(dt)
            if self.hold_time >= self.hold_seconds:
                self.notify_solved()
        else:
            self.hold_time = 0.0


class PatternMatch(PuzzleComponent):
    component_name = "PatternMatch"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.tile_count = _int(self.params, "tileCount", "tile_count", default=6)
        self.sequence_length = _int(self.params, "sequenceLength", "sequence_length", default=4)
        self.target = list(range(self.sequence_length))
        self.progress = 0

    def step(self, tile: int) -> bool:
        if tile == self.target[self.progress]:
            self.progress += 1
            if self.progress >= self.sequence_length:
                self.notify_solved()
            return True
        self.progress = 0
        self.notify_failed()
        return False


class WeightBalance(PuzzleComponent):
    component_name = "WeightBalance"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.weight_steps = _int(self.params, "weightSteps", "weight_steps", default=3)
        self.tolerance = _float(self.params, "tolerance", default=0.1)
        self.weights: list[float] = [0.0] * self.weight_steps
        self.stable_time = 0.0

    def set_weight(self, index: int, value: float) -> None:
        if 0 <= index < len(self.weights):
            self.weights[index] = float(value)

    def balanced(self) -> bool:
        if not self.weights:
            return True
        avg = sum(self.weights) / len(self.weights)
        return all(abs(w - avg) <= self.tolerance for w in self.weights)

    def update(self, dt=0.0):
        if self.balanced():
            self.stable_time += float(dt)
            if self.stable_time >= 1.0:
                self.notify_solved()
        else:
            self.stable_time = 0.0


class TimeEcho(PuzzleComponent):
    component_name = "TimeEcho"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.echo_seconds = _float(self.params, "echoSeconds", "echo_seconds", default=6.0)
        self.plate_count = _int(self.params, "plateCount", "plate_count", default=2)
        self.recording = False
        self.timer = 0.0

    def record(self, active: bool = True) -> None:
        self.recording = bool(active)
        if active:
            self.timer = self.echo_seconds

    def update(self, dt=0.0):
        if self.recording:
            self.timer = max(0.0, self.timer - float(dt))
            if self.timer <= 0:
                self.recording = False


class ShadowAligner(PuzzleComponent):
    component_name = "ShadowAligner"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.silhouette_count = _int(self.params, "silhouetteCount", "silhouette_count", default=1)
        self.tolerance_pixels = _int(self.params, "tolerancePixels", "tolerance_pixels", default=6)
        self.offsets: list[int] = [0] * max(1, self.silhouette_count)
        self.aligned_frames = 0

    def set_offset(self, index: int, value: int) -> None:
        if 0 <= index < len(self.offsets):
            self.offsets[index] = int(value)

    def aligned(self) -> bool:
        return all(abs(v) <= self.tolerance_pixels for v in self.offsets)

    def update(self, dt=0.0):
        if self.aligned():
            self.aligned_frames += 1
            if self.aligned_frames >= 3:
                self.notify_solved()
        else:
            self.aligned_frames = 0


class TimingWindow(PuzzleComponent):
    component_name = "TimingWindow"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.window_seconds = _float(self.params, "windowSeconds", "window_seconds", default=0.4)
        self.cue_count = _int(self.params, "cueCount", "cue_count", default=3)
        self.hits = 0
        self.phase = 0.0

    def press(self, phase: float | None = None) -> bool:
        phase = self.phase if phase is None else float(phase)
        if abs(phase) <= self.window_seconds:
            self.hits += 1
            if self.hits >= self.cue_count:
                self.notify_solved()
            return True
        self.hits = 0
        self.notify_failed()
        return False

    def update(self, dt=0.0):
        self.phase = (self.phase + float(dt)) % 1.0


class SoundTrigger(PuzzleComponent):
    component_name = "SoundTrigger"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.cue_count = _int(self.params, "cueCount", "cue_count", default=3)
        self.cue_gap = _float(self.params, "cueGap", "cue_gap", default=0.8)
        self.knocks: list[float] = []
        self.timer = 0.0

    def knock(self) -> None:
        if not self.knocks or self.timer >= self.cue_gap:
            self.knocks.append(self.timer)
            self.timer = 0.0
            if len(self.knocks) >= self.cue_count:
                self.notify_solved()
        else:
            self.knocks.clear()
            self.notify_failed()

    def update(self, dt=0.0):
        self.timer += float(dt)


class SoundMemory(PuzzleComponent):
    component_name = "SoundMemory"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.note_count = _int(self.params, "noteCount", "note_count", default=5)
        self.target = list(range(self.note_count))
        self.input: list[int] = []

    def play_note(self, note: int) -> bool:
        self.input.append(int(note))
        if len(self.input) == len(self.target):
            if self.input == self.target:
                self.notify_solved()
                return True
            self.input.clear()
            self.notify_failed()
        return False


class MirrorReflector(PuzzleComponent):
    component_name = "MirrorReflector"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.mirror_count = _int(self.params, "mirrorCount", "mirror_count", default=2)
        self.target_count = _int(self.params, "targetCount", "target_count", default=1)
        self.angles = [0] * max(1, self.mirror_count)
        self.lit_targets = 0

    def rotate(self, index: int, delta: int = 1) -> None:
        if 0 <= index < len(self.angles):
            self.angles[index] = (self.angles[index] + delta) % 4

    def set_lit_targets(self, count: int) -> None:
        self.lit_targets = int(count)
        if self.lit_targets >= self.target_count:
            self.notify_solved()


class LaserGrid(PuzzleComponent):
    component_name = "LaserGrid"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.crossed = False
        self.beams = 0

    def set_beams(self, count: int) -> None:
        self.beams = int(count)
        if self.beams >= 2:
            self.notify_solved()

    def cross(self, value: bool = True) -> None:
        self.crossed = bool(value)
        if self.crossed:
            self.notify_failed()


class SymbolDecoder(PuzzleComponent):
    component_name = "SymbolDecoder"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.glyph_count = _int(self.params, "glyphCount", "glyph_count", default=4)
        self.sequence_length = _int(self.params, "sequenceLength", "sequence_length", default=3)
        self.key = list(range(self.sequence_length))
        self.entered: list[int] = []

    def enter(self, glyph: int) -> bool:
        self.entered.append(int(glyph))
        if len(self.entered) == self.sequence_length:
            if self.entered == self.key:
                self.notify_solved()
                return True
            self.entered.clear()
            self.notify_failed()
        return False


class RoomRotator(PuzzleComponent):
    component_name = "RoomRotator"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.rotation_steps = _int(self.params, "rotationSteps", "rotation_steps", default=4)
        self.step = 0

    def rotate(self, delta: int = 1) -> None:
        self.step = (self.step + delta) % max(1, self.rotation_steps)
        if self.step == 0:
            self.notify_solved()


class PerspectiveShift(PuzzleComponent):
    component_name = "PerspectiveShift"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.angle_count = _int(self.params, "angleCount", "angle_count", default=3)
        self.angle = 0

    def shift(self, delta: int = 1) -> None:
        self.angle = (self.angle + delta) % max(1, self.angle_count)
        if self.angle == 0:
            self.notify_solved()


class FuelTrade(PuzzleComponent):
    component_name = "FuelTrade"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.fuel_cost = _float(self.params, "fuelCost", "fuel_cost", default=0.25)
        self.refund_on_failure = bool(self.params.get("refundOnFailure", self.params.get("refund_on_failure", True)))
        self.spent = 0.0
        self.latch = False

    def spend(self, fuel: float) -> bool:
        if fuel >= self.fuel_cost:
            self.spent += self.fuel_cost
            self.latch = True
            self.notify_solved()
            return True
        self.notify_failed()
        return False

    def refund(self) -> float:
        amount = self.spent
        self.spent = 0.0
        self.latch = False
        return amount


class WaterLevel(PuzzleComponent):
    component_name = "WaterLevel"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.water_levels = _int(self.params, "waterLevels", "water_levels", default=3)
        self.level = 0

    def raise_level(self, amount: int = 1) -> None:
        self.level = min(self.water_levels, self.level + amount)
        if self.level >= self.water_levels:
            self.notify_solved()

    def lower_level(self, amount: int = 1) -> None:
        self.level = max(0, self.level - amount)


class WindCurrent(PuzzleComponent):
    component_name = "WindCurrent"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.fan_count = _int(self.params, "fanCount", "fan_count", default=2)
        self.gust_seconds = _float(self.params, "gustSeconds", "gust_seconds", default=2.0)
        self.fans = [0] * max(1, self.fan_count)
        self.gust_timer = 0.0

    def aim(self, index: int, angle: int) -> None:
        if 0 <= index < len(self.fans):
            self.fans[index] = int(angle)

    def gust(self, dt: float = 0.0) -> None:
        self.gust_timer += float(dt)
        if self.gust_timer >= self.gust_seconds:
            self.notify_solved()


class EnvironmentalCombo(PuzzleComponent):
    component_name = "EnvironmentalCombo"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.chain_length = _int(self.params, "chainLength", "chain_length", default=4)
        self.stage = 0

    def advance(self) -> None:
        self.stage += 1
        if self.stage >= self.chain_length:
            self.notify_solved()

    def reset_puzzle(self):
        super().reset_puzzle()
        self.stage = 0


class MemoryPalace(PuzzleComponent):
    component_name = "MemoryPalace"

    def __init__(self, component_id=None, params=None, **kwargs):
        super().__init__(component_id, params, **kwargs)
        self.object_count = _int(self.params, "objectCount", "object_count", default=4)
        self.reveal_seconds = _float(self.params, "revealSeconds", "reveal_seconds", default=2.0)
        self.hidden = True
        self.touched: set[int] = set()
        self.reveal_timer = 0.0

    def reveal(self) -> None:
        self.hidden = False
        self.reveal_timer = self.reveal_seconds

    def touch(self, index: int) -> None:
        self.touched.add(int(index))
        if len(self.touched) >= self.object_count:
            self.notify_solved()

    def update(self, dt=0.0):
        if not self.hidden:
            self.reveal_timer = max(0.0, self.reveal_timer - float(dt))
            if self.reveal_timer <= 0:
                self.hidden = True

    def reset_puzzle(self):
        super().reset_puzzle()
        self.hidden = True
        self.touched.clear()
        self.reveal_timer = 0.0


