"""Application loop for NÜR: exploration, fading light, memory and the final name."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import pygame

from . import config
from .art import NurArt
from .audio import Audio
from .boss import AlzheimerBoss
from .levels import NUR_LEVELS, room_count
from echo_game.physics import DT, Input, World
from .state import Lantern, Memory, Narrative
from .story import CUTSCENES, FRAGMENTS, OKIR_EPILOGUE

FALSE_KEYS = frozenset({"key", "letter"})
EVENT_SOUNDS = {
    "jump": "breath",
    "land": "tick",
    "grab": "door",
    "gate": "door",
    "checkpoint": "memory",
    "death": "glitch",
    "tick": "tick",
}


def load_font(size: int, title: bool = False) -> pygame.font.Font:
    name = "Alegreya[wght].ttf" if title else "Carlito-Regular.ttf"
    path = config.FONT_DIR / name
    return pygame.font.Font(str(path) if path.exists() else None, size)


class Game:
    def __init__(self, room: int = 0, seed: int = config.SEED, start: bool = True,
                 muted: bool = False, persist: bool = True) -> None:
        if not pygame.get_init():
            pygame.init()
        # Establish the display before loading art. Without set_mode(),
        # pygame.display.get_surface() is None and the windowed blit crashes.
        self.display = pygame.display.set_mode(config.SIZE, pygame.RESIZABLE)
        pygame.display.set_caption(config.TITLE)
        self.seed = int(seed)
        self.persist = persist
        self.muted = muted
        self.state = "playing" if start else "menu"
        self.running = True
        self.visual_time = 0.0
        self.camera = 0.0
        self.accumulator = 0.0
        self.room = max(0, min(room_count() - 1, room))
        self.death_timer = 0.0
        self.complete_timer = 0.0
        self.notice = ""
        self.notice_timer = 0.0
        self.pending_action = False
        self.cutscene_index = 0
        self.cutscene_timer = 0.0

        self.canvas = pygame.Surface(config.SIZE)
        self.art = NurArt(config.SIZE)
        self.fonts = {size: load_font(size) for size in (14, 16, 18, 21, 26, 32)}
        self.title_font = load_font(78, True)
        self.heading_font = load_font(36, True)

        self.audio = Audio(enabled=not muted)
        self.lantern = Lantern()
        self.memory = Memory()
        self.narrative = Narrative(self.seed)
        self.world = self._build_world(self.room)
        self.threats = self._build_threats(self.room)
        self.boss = self._build_boss(self.room) if self.room == config.BOSS_ARENA_ROOM else None

    # ---------------------------------------------------------------- construction
    def _build_world(self, room: int) -> World:
        return World(room, NUR_LEVELS[room].level)

    def _build_threats(self, room: int):
        from .threats import ThreatDirector

        return ThreatDirector(NUR_LEVELS[room].threats, self.seed + room * 31)

    def _build_boss(self, room: int) -> AlzheimerBoss:
        return AlzheimerBoss(NUR_LEVELS[room].echoes, self.seed + room * 17)

    def _player_xy(self) -> tuple[float, float]:
        position = self.world.player.position
        return float(position.x), float(position.y)

    def start(self, room: int | None = None, seed: int | None = None) -> None:
        if seed is not None:
            self.seed = int(seed)
        if room is not None:
            self.room = max(0, min(room_count() - 1, room))
        self.lantern = Lantern()
        self.memory = Memory()
        self.narrative.reset(self.seed)
        self.state = "playing"
        self.notice = ""
        self.notice_timer = 0.0
        self.death_timer = self.complete_timer = self.accumulator = 0.0
        self.cutscene_index = 0
        self.cutscene_timer = 0.0
        self.world = self._build_world(self.room)
        self.threats = self._build_threats(self.room)
        self.boss = self._build_boss(self.room) if self.room == config.BOSS_ARENA_ROOM else None
        self.camera = 0.0
        self._save()

    def restart_room(self, keep_boss: bool = False) -> None:
        self.world = self._build_world(self.room)
        self.threats = self._build_threats(self.room)
        if not keep_boss and self.room == config.BOSS_ARENA_ROOM:
            self.boss = self._build_boss(self.room)
        self.death_timer = self.complete_timer = self.accumulator = 0.0
        self.state = "playing"
        self.camera = 0.0

    def _save(self) -> None:
        if not self.persist:
            return
        try:
            config.SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            config.SAVE_PATH.write_text(
                json.dumps({"room": self.room, "seed": self.seed}), encoding="utf-8"
            )
        except OSError:
            pass

    def _say(self, text: str, seconds: float = 4.2) -> None:
        self.notice = text
        self.notice_timer = seconds

    # ---------------------------------------------------------------- input
    def event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_m:
            self.muted = not self.muted
            self.audio.set_muted(self.muted)
            return
        if self.state == "menu":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start()
            elif key == pygame.K_ESCAPE:
                self.running = False
            return
        if self.state == "ending":
            if key == pygame.K_RETURN:
                self.start(0)
            elif key == pygame.K_ESCAPE:
                self.running = False
            return
        if key == pygame.K_ESCAPE:
            self.state = "paused" if self.state == "playing" else "playing"
            return
        if self.state == "paused":
            if key == pygame.K_r:
                self.restart_room()
            return
        if key == pygame.K_e:
            self.pending_action = True

    def _control(self) -> Input:
        keys = pygame.key.get_pressed()
        action = self.pending_action or bool(keys[pygame.K_e] or keys[pygame.K_LCTRL])
        self.pending_action = False
        return Input(
            move=(-1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
                 + (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0),
            jump=bool(keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]),
            grab=False,
            action=action,
            climb=0.0,
            lantern=False,
        )

    # ---------------------------------------------------------------- simulation
    def update(self, dt: float, control: Input | None = None) -> None:
        dt = min(0.1, max(0.0, dt))
        self.visual_time += dt
        self.audio.update(dt, self.narrative.stage, self.lantern.illumination,
                          boss=self.boss is not None and self.boss.phase >= 1)
        if self.notice_timer > 0:
            self.notice_timer -= dt

        if self.state == "ending":
            self.cutscene_timer += dt
            if self.cutscene_timer >= 4.6 and self.cutscene_index < len(CUTSCENES) - 1:
                self.cutscene_index += 1
                self.cutscene_timer = 0.0
                self.audio.play("memory", 0.35)
            return
        if self.state != "playing":
            return

        if control is None:
            control = self._control()
        self.lantern.step(dt)

        self.accumulator = min(0.1, self.accumulator + dt)
        while self.accumulator >= DT:
            self.world.step(control, DT)
            self.accumulator -= DT
            for event_name in self.world.drain_events():
                sound = EVENT_SOUNDS.get(event_name)
                if sound:
                    self.audio.play(sound, 0.35)
            if self.world.dead or self.world.complete:
                break

        px, py = self._player_xy()
        self._collect(px, py)
        touched = self.threats.update(dt, (px, py), self.narrative.stage, not self.world.dead)
        if touched and not self.world.dead:
            self.world.kill("Sesuatu menyentuhmu dari luar cahaya.")
        self.narrative.update(dt, self.lantern.illumination, self.room, boss=self.boss is not None)

        if self.boss is not None and not self.world.dead:
            event = self.boss.update(dt, (px, py), control.action, self.lantern.illumination)
            self._handle_boss_event(event)

        if self.world.dead:
            self.death_timer += dt
            if self.death_timer >= 1.05:
                self.lantern.die()
                self._say("Cahaya berkurang. Itu saja.", 2.5)
                self.restart_room(keep_boss=self.boss is not None)
            return
        self.death_timer = 0.0

        if self.world.complete and self.boss is None:
            self.complete_timer += dt
            if self.complete_timer >= 1.0 and self.room < room_count() - 1:
                self.room += 1
                self.restart_room()
                self._say(NUR_LEVELS[self.room].name, 2.0)
                self._save()
            return
        self.complete_timer = 0.0

        target = px - config.SIZE[0] * 0.42
        maximum = max(0.0, self.world.level.width - config.SIZE[0])
        self.camera += (max(0.0, min(maximum, target)) - self.camera) * min(1.0, dt * 3.5)

    def _collect(self, px: float, py: float) -> None:
        for fragment in FRAGMENTS:
            if fragment.room != self.room or fragment.key in self.memory.found:
                continue
            if math.hypot(px - fragment.x, py - fragment.y) < 36.0:
                self.memory.add(fragment.key, false=fragment.key in FALSE_KEYS)
                self.lantern.collect_fragment()
                caption = fragment.false_text if fragment.key in self.memory.false else fragment.true_text
                self._say(f"{fragment.title}\n{caption}", 5.2)
                self.audio.play("memory", 0.65)
                return
        candle = NUR_LEVELS[self.room].candle
        if candle and self.memory.gain_candle():
            self.memory.restore()
            self._say("Lilin ingatan meleleh. Sebuah ingatan kembali. Cahaya tidak bertambah.", 4.8)
            self.audio.play("tick", 0.7)

    def _handle_boss_event(self, event: str | None) -> None:
        if event is None:
            return
        if event == "hit":
            self.lantern.charge = max(config.LIGHT_FLOOR, self.lantern.charge - 0.12)
            self._say("Salah ingatan mengenaimu.", 1.8)
            self.audio.play("glitch", 0.7)
        elif event == "echo":
            self._say("Sebuah ingatan berhenti berteriak.", 2.4)
            self.audio.play("memory", 0.6)
        elif event == "press":
            self.audio.play("tick", 0.75)
        elif event == "phase":
            self.audio.play("door", 0.7)
        elif event == "win":
            self.state = "ending"
            self.cutscene_index = 0
            self.cutscene_timer = 0.0
            self.audio.play("memory", 0.5)

    # ---------------------------------------------------------------- presentation
    def _text(self, text: str, x: float, y: float, size: int = 18,
              colour=(190, 181, 164), center: bool = False, alpha: int = 255) -> None:
        if size not in self.fonts:
            self.fonts[size] = load_font(size)
        for index, line in enumerate(text.split("\n")):
            image = self.fonts[size].render(line, True, colour)
            image.set_alpha(alpha)
            rect = image.get_rect(midtop=(x, y + index * (size + 4))) if center else image.get_rect(topleft=(x, y + index * (size + 4)))
            self.canvas.blit(image, rect)

    def draw(self) -> pygame.Surface:
        canvas = self.canvas
        canvas.fill(config.VOID)
        px, py = self._player_xy()
        screen_x = px - self.camera

        self.art.draw_background(canvas, self.camera, self.room, self.visual_time)
        self.art.draw_terrain(canvas, self.world, self.camera, self.lantern.illumination)
        for fragment in FRAGMENTS:
            if fragment.room == self.room:
                self.art.draw_fragment(canvas, fragment, self.camera, self.visual_time,
                                       fragment.key in self.memory.found)
        candle = NUR_LEVELS[self.room].candle
        if candle:
            self.art.draw_memory_candle(canvas, candle, self.camera, self.visual_time,
                                        not self.memory.candles)
        self.threats.draw(canvas, self.camera, self.lantern.illumination)
        if self.boss is not None:
            self.boss.draw(canvas, self.camera, self.lantern.illumination)
        self.art.draw_player(canvas, (px, py), self.camera, self.lantern.illumination,
                             self.world.facing, self.visual_time)
        self.art.draw_lighting(canvas, (screen_x, py), self.lantern.illumination,
                               self.narrative.stage, self.visual_time)

        if self.state != "menu":
            self._draw_hud()
        if self.narrative.line and self.state == "playing":
            alpha = max(0, min(255, int(255 * min(1.0, self.narrative.line_age * 1.8))))
            self._text(self.narrative.line, config.SIZE[0] // 2, 72, 21,
                       (178, 168, 154), center=True, alpha=alpha)
        if self.notice_timer > 0 and self.state == "playing":
            alpha = min(255, int(self.notice_timer * 130))
            self._text(self.notice, config.SIZE[0] // 2, 424, 18,
                       config.BONE, center=True, alpha=alpha)
        if self.boss is not None and self.state == "playing" and self.boss.phase == 1:
            self._text(self.boss.line, config.SIZE[0] // 2, 300, 26,
                       (196, 158, 138), center=True)

        if self.state == "menu":
            self._draw_menu()
        elif self.state == "paused":
            self._draw_pause()
        elif self.state == "ending":
            self._draw_ending()
        return canvas

    def _draw_hud(self) -> None:
        # Diegetic candle: the wax is the remaining light; no numeric bar.
        x, y = 26, 486
        height = round(26 * self.lantern.illumination)
        pygame.draw.rect(self.canvas, (69, 63, 54), (x, y, 12, 30))
        if height:
            pygame.draw.rect(self.canvas, config.WAX, (x, y + 30 - height, 12, height))
        pygame.draw.ellipse(self.canvas, config.EMBER, (x - 2, y - 10 - height // 2, 16, 12))
        for index in range(len(FRAGMENTS)):
            colour = config.WAX if index < len(self.memory.found) else (48, 46, 45)
            pygame.draw.circle(self.canvas, colour, (x + 30 + index * 13, y + 14), 4, 1)
        if self.memory.truth:
            self._text("·" * self.memory.truth, x + 30, y - 4, 21, config.WAX)

    def _draw_menu(self) -> None:
        veil = pygame.Surface(config.SIZE, pygame.SRCALPHA)
        veil.fill((4, 5, 7, 220))
        self.canvas.blit(veil, (0, 0))
        self._text(config.TITLE, config.SIZE[0] // 2, 150, 78, config.BONE,
                   center=True)
        self._text("sebuah kisah tentang cahaya yang tidak bisa kembali",
                   config.SIZE[0] // 2, 250, 21, (120, 114, 106), center=True)
        self._text("ENTER  —  masuk ke rumah", config.SIZE[0] // 2, 360, 18,
                   config.WAX, center=True)
        self._text("M  —  suara   /   ESC  —  keluar", config.SIZE[0] // 2, 398, 14,
                   (96, 91, 86), center=True)

    def _draw_pause(self) -> None:
        veil = pygame.Surface(config.SIZE, pygame.SRCALPHA)
        veil.fill((4, 5, 7, 190))
        self.canvas.blit(veil, (0, 0))
        self._text("BERHENTI SEBENTAR", config.SIZE[0] // 2, 240, 32,
                   config.BONE, center=True)
        self._text("ESC kembali  /  R mengulang ruangan", config.SIZE[0] // 2, 300, 16,
                   (120, 114, 106), center=True)

    def _draw_ending(self) -> None:
        cut = CUTSCENES[min(self.cutscene_index, len(CUTSCENES) - 1)]
        image = self.art.cutscene(cut.key)
        self.canvas.blit(image, (0, 0))
        veil = pygame.Surface(config.SIZE, pygame.SRCALPHA)
        veil.fill((4, 5, 7, 105))
        self.canvas.blit(veil, (0, 0))
        self._text(cut.title, config.SIZE[0] // 2, 60, 32, config.BONE, center=True)
        for index, line in enumerate(cut.lines):
            self._text(line, config.SIZE[0] // 2, 360 + index * 30, 18,
                       (168, 158, 143), center=True)
        if self.cutscene_index == len(CUTSCENES) - 1:
            for index, line in enumerate(OKIR_EPILOGUE):
                self._text(line, config.SIZE[0] // 2, 468 + index * 24, 14,
                           config.WAX, center=True)
            self._text("ENTER — mulai lagi", config.SIZE[0] // 2, 520, 14,
                       (110, 104, 98), center=True)

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "room": self.room + 1,
            "room_name": NUR_LEVELS[self.room].name,
            "time": round(self.visual_time, 3),
            "camera": round(self.camera, 2),
            "lantern": self.lantern.snapshot(),
            "memory": self.memory.snapshot(),
            "narrative": self.narrative.snapshot(),
            "physics": self.world.snapshot(),
            "threats": self.threats.snapshot(),
            "boss": self.boss.snapshot() if self.boss else None,
        }


def _source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        for path in sorted(root.glob("*.py"))
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NÜR — dark memory adventure")
    parser.add_argument("--room", type=int, choices=range(1, room_count() + 1), default=1)
    parser.add_argument("--seed", type=int, default=config.SEED)
    parser.add_argument("--menu", action="store_true", help="Show the title screen instead of spawning at home")
    parser.add_argument("--mute", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    if args.headless and args.frames <= 0:
        parser.error("--headless requires --frames > 0")
    if args.screenshot or args.report:
        args.headless = True
        if args.frames <= 0:
            args.frames = 1
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    game = Game(
        room=args.room - 1,
        seed=args.seed,
        start=not args.menu,
        muted=args.mute,
        persist=not args.no_save,
    )
    clock = pygame.time.Clock()
    frames = 0
    while game.running:
        for event in pygame.event.get():
            game.event(event)
        elapsed = 1.0 / config.FPS if args.headless else min(0.1, clock.tick(config.FPS) / 1000.0)
        game.update(elapsed)
        canvas = game.draw()
        if args.screenshot and frames == args.frames - 1:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(canvas, str(args.screenshot))
        frames += 1
        if args.headless and frames >= args.frames:
            break
        if not args.headless:
            display = game.display
            display.blit(pygame.transform.smoothscale(canvas, display.get_size()), (0, 0))
            pygame.display.flip()

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(
                {"simulation": game.snapshot(), "sources": _source_hashes()},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    game.audio.close()
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
