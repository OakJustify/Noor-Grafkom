"""Game: loop and scene manager."""

import os
import sys
import time

import pygame

import noor.config as C
from noor.audio.manager import AudioManager
from noor.core.i18n import I18n
from noor.core.save import SaveManager
from noor.core.scene import SceneManager

_DS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "dynamic-screen")
if _DS not in sys.path:
    sys.path.insert(0, _DS)
try:
    from detect import get_monitor_size  # type: ignore
    from events import handle_resize  # type: ignore
    from scale import fit_rect  # type: ignore
    from window import create_window  # type: ignore
except Exception:  # noqa: BLE001
    create_window = None
    handle_resize = None
    get_monitor_size = None
    fit_rect = None


class Game:
    def __init__(self):
        pygame.init()
        if get_monitor_size is not None:
            phys_w, phys_h = get_monitor_size()
            self.screen = pygame.display.set_mode((phys_w, phys_h), pygame.FULLSCREEN)
            pygame.display.set_caption("NOOR")
        elif create_window is not None:
            self.screen = create_window("NOOR", fullscreen=True)
        else:
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), pygame.SCALED)
            pygame.display.set_caption("NOOR")
        # All scenes draw to this fixed logical surface; it is scaled to the monitor.
        self.logical = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.running = True
        self._dyn_state = {"phys_w": self.screen.get_width(), "phys_h": self.screen.get_height(), "scale": 1.0}
        self.scenes = SceneManager()
        self.save = SaveManager()
        settings = self.save.load_settings()
        lang = settings.get("language", "id")
        self.i18n = I18n(lang=lang)
        self.state = {
            "stage": 1,
            "level_id": "procedural",
            "checkpoint_id": None,
            "S": 100.0,
            "cap": 100.0,
            "clock_seconds": 0.0,
            "deaths": 0,
            "fragments_collected": [],
            "fragments_active": [],
            "truth_found": [],
            "rng_seed": 0,
            "mode": settings.get("mode", "normal"),
            "accessibility": settings.get("accessibility", C.DEFAULT_ACCESSIBILITY),
        }
        self.audio = AudioManager(accessibility=self.state["accessibility"])

    def run(self):
        from noor.scenes.warning import WarningScene
        self.scenes.push(WarningScene(self))
        acc = 0.0
        prev = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            frame = min(now - prev, 0.1)
            prev = now
            acc += frame
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.VIDEORESIZE and handle_resize is not None:
                    handle_resize(e, self._dyn_state)
                else:
                    self.scenes.handle_event(e)
            while acc >= C.FIXED_DT:
                self.scenes.update(C.FIXED_DT)
                acc -= C.FIXED_DT
            self.logical.fill((0, 0, 0))
            self.scenes.draw(self.logical)
            self.screen.fill((0, 0, 0))
            if fit_rect is not None:
                x, y, w, h = fit_rect(self.screen.get_width(), self.screen.get_height())
            else:
                x, y, w, h = 0, 0, self.screen.get_width(), self.screen.get_height()
            if (w, h) != (C.SCREEN_W, C.SCREEN_H):
                frame = pygame.transform.scale(self.logical, (w, h))
            else:
                frame = self.logical
            self.screen.blit(frame, (x, y))
            pygame.display.flip()
            self.clock.tick(C.FPS)
        self._fade_out_audio()
        self.audio.stop()
        pygame.quit()

    def _fade_out_audio(self):
        """Let the music ring out before the window closes."""
        if not self.audio.playing:
            return
        self.audio.fade_out()
        deadline = time.perf_counter() + C.CROSSFADE_SECONDS + 0.05
        prev = time.perf_counter()
        while self.audio.playing and time.perf_counter() < deadline:
            now = time.perf_counter()
            self.audio.update(now - prev)
            prev = now
            time.sleep(1 / 120)