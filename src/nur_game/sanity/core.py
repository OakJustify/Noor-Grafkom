"""Sanity, hallucination pressure and phantom presentation (Python F3)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from ..encounters import creature_sprite


@dataclass
class SanityManager:
    max_sanity: float = 100.0
    base_sanity_drain: float = 0.05
    hallucination_drain_per_sec: float = 5.0
    hallucination_cooldown: float = 3.0
    lantern_dim_multiplier: float = 1.5
    max_lantern_multiplier: float = 3.0
    multiplier_step: float = 0.2
    sanity_break_points: tuple[float, ...] = (75.0, 50.0, 25.0, 0.0)
    current_sanity: float = 100.0
    hallucinating: bool = False
    hallucination_count: int = 0
    cooldown: float = 0.0
    dead: bool = False
    _last_break: int | None = None
    on_sanity_changed: list = field(default_factory=list)
    on_hallucination_toggled: list = field(default_factory=list)
    on_break_point_reached: list = field(default_factory=list)

    def __post_init__(self):
        self.current_sanity = max(0.0, min(self.max_sanity, float(self.current_sanity)))
        self._last_break = self.breakpoint_index

    @property
    def normalized(self) -> float:
        return 0.0 if self.max_sanity <= 0 else max(0.0, min(1.0, self.current_sanity / self.max_sanity))

    @property
    def intensity(self) -> float:
        return 1.0 - self.normalized

    @property
    def breakpoint_index(self) -> int | None:
        for index in range(len(self.sanity_break_points) - 1, -1, -1):
            if self.current_sanity <= self.sanity_break_points[index]:
                return index
        return None

    @property
    def lantern_multiplier(self) -> float:
        if self.hallucination_count <= 0:
            return 1.0
        return min(self.max_lantern_multiplier,
                   self.lantern_dim_multiplier + self.multiplier_step * self.hallucination_count)

    def subscribe(self, sanity=None, hallucination=None, breakpoint=None) -> None:
        if sanity is not None:
            self.on_sanity_changed.append(sanity)
        if hallucination is not None:
            self.on_hallucination_toggled.append(hallucination)
        if breakpoint is not None:
            self.on_break_point_reached.append(breakpoint)

    def _emit_sanity(self) -> None:
        for callback in self.on_sanity_changed:
            callback(self.normalized)

    def _emit_break(self) -> None:
        index = self.breakpoint_index
        if index is not None and (self._last_break is None or index > self._last_break):
            self._last_break = index
            for callback in self.on_break_point_reached:
                callback(index)
        elif index is None:
            self._last_break = None

    def trigger_hallucination(self) -> bool:
        if self.dead or self.cooldown > 0:
            return False
        if self.hallucinating:
            self.hallucinating = False
            for callback in self.on_hallucination_toggled:
                callback(False)
            return True
        self.hallucinating = True
        self.hallucination_count += 1
        self.cooldown = self.hallucination_cooldown
        for callback in self.on_hallucination_toggled:
            callback(True)
        return True

    def restore_sanity(self, amount: float) -> float:
        if amount <= 0:
            return self.current_sanity
        self.current_sanity = min(self.max_sanity, self.current_sanity + float(amount))
        self._emit_sanity()
        self._emit_break()
        return self.current_sanity

    def update(self, dt: float, lantern=None) -> bool:
        dt = max(0.0, float(dt))
        self.cooldown = max(0.0, self.cooldown - dt)
        if lantern is not None:
            lantern.drain_multiplier = self.lantern_multiplier
        if self.dead:
            return True
        drain = self.base_sanity_drain
        if self.hallucinating:
            drain += self.hallucination_drain_per_sec
        previous = self.current_sanity
        self.current_sanity = max(0.0, self.current_sanity - drain * dt)
        if self.current_sanity != previous:
            self._emit_sanity()
            self._emit_break()
        if self.current_sanity <= 0 and not self.dead:
            self.dead = True
            return True
        return False

    def reset(self, amount: float | None = None) -> None:
        self.current_sanity = self.max_sanity if amount is None else max(0.0, min(self.max_sanity, amount))
        self.hallucinating = False
        self.dead = False
        self.cooldown = 0.0
        self._last_break = self.breakpoint_index
        self._emit_sanity()

    def snapshot(self) -> dict:
        return {
            "current": round(self.current_sanity, 4),
            "max": round(self.max_sanity, 2),
            "hallucinating": self.hallucinating,
            "count": self.hallucination_count,
            "lantern_multiplier": round(self.lantern_multiplier, 3),
            "dead": self.dead,
        }


