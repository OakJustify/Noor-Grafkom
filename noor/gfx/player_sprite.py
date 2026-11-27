"""Player sprite animation from assets/sprites/licht/manifest.json."""

import json
import os

import pygame


class PlayerSprite:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "sprites", "licht")
        self.base_dir = base_dir
        self.manifest = None
        self.frames = {}
        self.current = "idle"
        self.index = 0
        self.timer = 0.0
        self.facing = 1
        manifest_path = os.path.join(base_dir, "manifest.json")
        try:
            with open(manifest_path, encoding="utf-8") as f:
                self.manifest = json.load(f)
            self._load()
        except Exception:  # noqa: BLE001
            self.manifest = None

    def _load(self):
        for name, info in self.manifest["animations"].items():
            sheet_path = os.path.join(self.base_dir, info["sheet"])
            sheet = pygame.image.load(sheet_path).convert_alpha()
            frames = []
            for rect in info["frame_rects"]:
                x, y, w, h = rect
                frames.append(sheet.subsurface(pygame.Rect(x, y, w, h)))
            self.frames[name] = frames

    def available(self):
        return self.manifest is not None and bool(self.frames)

    def update(self, dt, state, facing):
        if not self.available():
            return
        if state != self.current:
            self.current = state
            self.index = 0
            self.timer = 0.0
        self.facing = 1 if facing >= 0 else -1
        info = self.manifest["animations"].get(self.current)
        if not info:
            return
        fps = info.get("fps", 8)
        loop = info.get("loop", True)
        frame_time = 1.0 / max(1, fps)
        self.timer += dt
        while self.timer >= frame_time:
            self.timer -= frame_time
            if self.index < len(self.frames[self.current]) - 1:
                self.index += 1
            elif loop:
                self.index = 0
            else:
                self.index = len(self.frames[self.current]) - 1

    def get_frame(self):
        if not self.available():
            return None, (0, 0)
        frames = self.frames[self.current]
        idx = min(self.index, len(frames) - 1)
        surf = frames[idx]
        if self.facing < 0:
            surf = pygame.transform.flip(surf, True, False)
            pivot = tuple(self.manifest.get("mirrored_pivot", self.manifest["pivot"]))
        else:
            pivot = tuple(self.manifest["pivot"])
        return surf, pivot