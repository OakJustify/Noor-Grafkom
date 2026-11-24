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
from echo_game.physics import DT, Input
from .physics import NurWorld
from .state import Lantern, Memory, Narrative
from .story import CUTSCENES, FRAGMENTS, OKIR_EPILOGUE
from .wisp import WispAnimation
from .quests import QuestState

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
        self.candle_taken = False
        self.player_animation = WispAnimation()
        self.quest_progress = {}
        self.journal = {}
        self.journal_page = 0
        self.play_seconds = 0.0

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
    def _build_world(self, room: int) -> NurWorld:
        world = NurWorld(room, NUR_LEVELS[room].level)
        plan = NUR_LEVELS[room].quest
        if plan:
            world.quest = QuestState(plan, self.quest_progress.get(str(room)))
            if world.quest.stage:
                checkpoint = plan.nodes[plan.order[world.quest.stage - 1]]
                world.player.position = (checkpoint.x, 430)
        return world

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
        self.candle_taken = False
        self.player_animation = WispAnimation()
        self.quest_progress = {}
        self.journal = {}
        self.journal_page = 0
        self.play_seconds = 0.0
        self.world = self._build_world(self.room)
        self.threats = self._build_threats(self.room)
        self.boss = self._build_boss(self.room) if self.room == config.BOSS_ARENA_ROOM else None
        self.camera = 0.0
        self._save()

    def restart_room(self, keep_boss: bool = False) -> None:
        self._remember_quest()
        self.player_animation = WispAnimation()
        self.world = self._build_world(self.room)
        self.threats = self._build_threats(self.room)
        if not keep_boss and self.room == config.BOSS_ARENA_ROOM:
            self.boss = self._build_boss(self.room)
        self.death_timer = self.complete_timer = self.accumulator = 0.0
        self.state = "playing"
        self.camera = 0.0

    def _remember_quest(self):
        if self.world.quest:
            self.quest_progress[str(self.world.chapter)] = self.world.quest.snapshot()

    def _save(self) -> None:
        if not self.persist:
            return
        try:
            self._remember_quest()
            config.SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            temporary = config.SAVE_PATH.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps({"version": 2, "room": self.room, "seed": self.seed,
                            "lantern": self.lantern.snapshot(), "memory": self.memory.snapshot(),
                            "candle_taken": self.candle_taken, "journal": self.journal,
                            "quests": self.quest_progress, "play_seconds": self.play_seconds,
                            "narrative": self.narrative.snapshot()},
                           ensure_ascii=False), encoding="utf-8"
            )
            temporary.replace(config.SAVE_PATH)
        except OSError:
            pass

    def load_save(self) -> bool:
        try:
            saved = json.loads(config.SAVE_PATH.read_text(encoding="utf-8"))
            if not isinstance(saved, dict) or saved.get("version", 1) not in (1, 2):
                return False
            room, seed = int(saved["room"]), int(saved["seed"])
            if saved.get("version", 1) == 1 and room == 4:
                room = config.BOSS_ARENA_ROOM
            if not 0 <= room < room_count():
                return False
            lantern = saved.get("lantern", {})
            memory = saved.get("memory", {})
            if not isinstance(lantern, dict) or not isinstance(memory, dict):
                return False
            if not all(math.isfinite(float(lantern.get(key, 1))) for key in ("capacity", "charge")):
                return False
            capacity = max(0.0, min(1.0, float(lantern.get("capacity", 1))))
            charge = max(0.0, min(capacity, float(lantern.get("charge", capacity))))
            quests = saved.get("quests", {})
            journal = saved.get("journal", {})
            if not isinstance(quests, dict) or not isinstance(journal, dict):
                return False
            for key, value in quests.items():
                if not key.isdigit() or not 0 <= int(key) < room_count() or NUR_LEVELS[int(key)].quest is None:
                    return False
                if not isinstance(value, dict) or not isinstance(value.get("values", []), list):
                    return False
                if not all(isinstance(n, int) for n in value.get("values", [])):
                    return False
                if not isinstance(value.get("stage", 0), int) or not isinstance(value.get("inspected", []), list):
                    return False
                if not all(isinstance(n, int) and 0 <= n < 6 for n in value.get("inspected", [])):
                    return False
            fragment_keys = {fragment.key for fragment in FRAGMENTS}
            for key, value in journal.items():
                if not isinstance(value, str):
                    return False
                if key.startswith("memory:"):
                    if key.split(":", 1)[1] not in fragment_keys:
                        return False
                else:
                    parts = key.split(":")
                    if (len(parts) != 2 or not all(part.isdigit() for part in parts)
                            or not 0 <= int(parts[0]) < room_count() or not 0 <= int(parts[1]) < 6):
                        return False
            found, false = set(memory.get("found", [])), set(memory.get("false", []))
            if not found <= fragment_keys or not false <= found:
                return False
            collections, deaths = int(lantern.get("collections", 0)), int(lantern.get("deaths", 0))
            play_seconds = float(saved.get("play_seconds", 0))
            truth, candles = int(memory.get("truth", 0)), int(memory.get("candles", 0))
            narrative = saved.get("narrative", {})
            if not isinstance(narrative, dict):
                return False
            elapsed = float(narrative.get("elapsed", 0))
            shown = narrative.get("shown", [])
            if not isinstance(shown, list) or not all(isinstance(line, str) for line in shown):
                return False
            anchor = int(narrative.get("anchor_index", min(3, len(shown))))
            if (not math.isfinite(play_seconds) or not math.isfinite(elapsed)
                    or min(play_seconds, elapsed, collections, deaths, truth, candles) < 0 or candles > 1):
                return False
        except (OSError, KeyError, ValueError, TypeError):
            return False
        self.room, self.seed = room, seed
        self.lantern = Lantern()
        self.lantern.capacity, self.lantern.charge = capacity, charge
        self.lantern.collections, self.lantern.deaths = collections, deaths
        self.memory = Memory()
        self.memory.found, self.memory.false = found, false & found
        self.memory.truth, self.memory.candles = truth, candles
        self.candle_taken = bool(saved.get("candle_taken", False))
        self.quest_progress, self.journal = quests, journal
        self.play_seconds = max(0.0, play_seconds)
        self.narrative.reset(seed)
        self.narrative.elapsed = elapsed
        self.narrative.shown = tuple(shown[-12:])
        self.narrative.anchor_index = max(0, min(3, anchor))
        self.world = self._build_world(room)
        self.threats = self._build_threats(room)
        self.boss = self._build_boss(room) if room == config.BOSS_ARENA_ROOM else None
        self.player_animation = WispAnimation()
        self.camera = self.accumulator = self.death_timer = self.complete_timer = 0.0
        self.state = "playing"
        self._say("Perjalanan dilanjutkan. J membuka jurnal.")
        return True

    def _say(self, text: str, seconds: float = 4.2) -> None:
        self.notice = text
        self.notice_timer = seconds

    # ---------------------------------------------------------------- input
    def event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._save()
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
            elif key == pygame.K_c:
                if not self.load_save():
                    self._say("Belum ada checkpoint yang bisa dibuka.")
            return
        if self.state == "ending":
            if key == pygame.K_RETURN:
                self.start(0)
            elif key == pygame.K_ESCAPE:
                self.running = False
            return
        if key == pygame.K_j and self.state in ("playing", "journal"):
            if self.state == "playing":
                self.journal_page = max(0, (len(self.journal) - 1) // 3)
            self.state = "journal" if self.state == "playing" else "playing"
            return
        if self.state == "journal":
            if key in (pygame.K_ESCAPE, pygame.K_j):
                self.state = "playing"
            elif key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
                self.journal_page += 1
            elif key in (pygame.K_LEFT, pygame.K_PAGEUP):
                self.journal_page = max(0, self.journal_page - 1)
            return
        if key == pygame.K_ESCAPE:
            self.state = "paused" if self.state == "playing" else "playing"
            self._save()
            return
        if self.state == "paused":
            if key == pygame.K_r:
                self.restart_room()
            return
        if key == pygame.K_e:
            self.pending_action = True
        elif key == pygame.K_r:
            self.restart_room()

    def _control(self) -> Input:
        keys = pygame.key.get_pressed()
        action = self.pending_action or bool(keys[pygame.K_e] or keys[pygame.K_LCTRL])
        self.pending_action = False
        climbing = self.world.grab_kind == "rope"
        return Input(
            move=(-1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
                 + (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0),
            jump=bool(keys[pygame.K_SPACE] or (not climbing and (keys[pygame.K_w] or keys[pygame.K_UP]))),
            grab=bool(keys[pygame.K_e] or keys[pygame.K_LCTRL]),
            action=action,
            climb=(1.0 if keys[pygame.K_w] or keys[pygame.K_UP] else 0.0)
                  - (1.0 if keys[pygame.K_s] or keys[pygame.K_DOWN] else 0.0),
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
        self.play_seconds += dt
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
        if not self.world.dead:
            self.player_animation.update(dt, self.world.player.velocity, self.world.grounded)
        if self.world.quest:
            result = self.world.quest.update(control, self.world)
            if result:
                if result.get("note") is not None:
                    self.audio.play_note(result["note"])
                index = min(range(len(self.world.quest.plan.nodes)),
                            key=lambda n: abs(px - self.world.quest.plan.nodes[n].x))
                self.journal[f"{self.room:02d}:{index}"] = result["journal"]
                self._say(result["text"], 6)
                if result.get("solved"):
                    self.audio.play("memory", 0.45)
                    self._save()
        self._collect(px, py, control.action)
        touched = self.threats.update(dt, (px, py), self.narrative.stage, not self.world.dead,
                                     self.lantern.illumination, self.lantern.protects)
        if touched and not self.world.dead:
            self.world.kill("Sesuatu menyentuhmu dari luar cahaya.")
        self.narrative.update(dt, self.lantern.illumination, self.room, boss=self.boss is not None,
                              longform=self.world.quest is not None)

        if self.boss is not None and not self.world.dead:
            event = self.boss.update(dt, (px, py), control.action, self.lantern.illumination,
                                     self.lantern.protects)
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
                self._say(f"{NUR_LEVELS[self.room].name}\nJ: jurnal / E: periksa mekanisme", 3.0)
                self._save()
            return
        self.complete_timer = 0.0

        target = px - config.SIZE[0] * 0.42
        maximum = max(0.0, self.world.level.width - config.SIZE[0])
        self.camera += (max(0.0, min(maximum, target)) - self.camera) * min(1.0, dt * 3.5)

    def _collect(self, px: float, py: float, action: bool = False) -> None:
        for fragment in FRAGMENTS:
            if fragment.room != self.room or fragment.key in self.memory.found:
                continue
            if math.hypot(px - fragment.x, py - fragment.y) < 36.0:
                self.memory.add(fragment.key, false=fragment.key in FALSE_KEYS)
                self.lantern.collect_fragment()
                caption = fragment.false_text if fragment.key in self.memory.false else fragment.true_text
                if self.memory.candles:
                    self.memory.restore()
                    caption = fragment.true_text if fragment.key not in self.memory.false else fragment.false_text
                self.journal[f"memory:{fragment.key}"] = f"{fragment.title}: {caption}"
                self._say(f"{fragment.title}\n{caption}", 5.2)
                self.audio.play("memory", 0.65)
                return
        candle = NUR_LEVELS[self.room].candle
        if (candle and not self.candle_taken and action
                and math.hypot(px - candle[0], py - candle[1]) < 48
                and self.memory.gain_candle()):
            self.candle_taken = True
            self.memory.restore()
            self._say("Lilin ingatan meleleh. Sebuah ingatan kembali. Cahaya tidak bertambah.", 4.8)
            self.audio.play("tick", 0.7)

    def _handle_boss_event(self, event: str | None) -> None:
        if event is None:
            return
        if event == "hit":
            if self.lantern.protects:
                return
            self.lantern.charge = max(0.0, self.lantern.charge - 0.12)
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
        canvas.fill((245, 238, 224))
        px, py = self._player_xy()
        screen_x = px - self.camera

        self.art.draw_background(canvas, self.camera, self.room, self.visual_time)
        self.art.draw_terrain(canvas, self.world, self.camera, self.lantern.illumination)
        self.art.draw_exit(canvas, self.world.level.exit, self.camera, self.visual_time,
                           self.boss is not None,
                           ready=self.world.quest is None or self.world.quest.complete)
        for fragment in FRAGMENTS:
            if fragment.room == self.room:
                self.art.draw_fragment(canvas, fragment, self.camera, self.visual_time,
                                       fragment.key in self.memory.found)
        candle = NUR_LEVELS[self.room].candle
        if candle:
            self.art.draw_memory_candle(canvas, candle, self.camera, self.visual_time,
                                         not self.candle_taken)
        self.threats.draw(canvas, self.camera, self.lantern.illumination)
        if self.boss is not None:
            self.boss.draw(canvas, self.camera, self.lantern.illumination)
        if self.world.quest:
            self.world.quest.draw(canvas, self.camera, self.fonts[14], self.visual_time)
        self.art.draw_lighting(canvas, (screen_x, py), self.lantern.illumination,
                               self.narrative.stage, self.visual_time)
        # Draw player LAST so it's always clearly visible.
        self.art.draw_player(canvas, (px, py), self.camera, self.lantern.illumination,
                              self.world.facing, self.visual_time,
                              self.world.player.velocity, self.world.grounded, self.player_animation)
        self._draw_interactions(px, py)

        if self.state != "menu":
            self._draw_hud()
        show_intrusion = not self.world.quest or (self.notice_timer <= 0 and self.narrative.line_age < 6)
        if self.narrative.line and self.state == "playing" and show_intrusion:
            alpha = max(0, min(255, int(255 * min(1.0, self.narrative.line_age * 1.8))))
            self._caption(self.narrative.line, 69, 21, alpha)
        if self.notice_timer > 0 and self.state == "playing":
            alpha = min(255, int(self.notice_timer * 130))
            self._caption(self.notice, 112, 18, alpha)
        if self.boss is not None and self.state == "playing" and self.boss.phase == 1:
            self._text(self.boss.line, config.SIZE[0] // 2, 300, 26,
                       (196, 158, 138), center=True)

        if self.state == "menu":
            self._draw_menu()
        elif self.state == "paused":
            self._draw_pause()
        elif self.state == "journal":
            self._draw_journal()
        elif self.state == "ending":
            self._draw_ending()
        return canvas

    def _draw_hud(self) -> None:
        # Diegetic candle: the wax is the remaining light; no numeric bar.
        x, y = 26, 486
        height = round(26 * self.lantern.illumination)
        # Candle holder.
        pygame.draw.rect(self.canvas, (46, 42, 38), (x - 6, y - 4, 24, 40), border_radius=4)
        pygame.draw.rect(self.canvas, (69, 63, 54), (x, y, 12, 30), border_radius=2)
        if height:
            pygame.draw.rect(self.canvas, config.WAX, (x, y + 30 - height, 12, height), border_radius=2)
        flicker = 0.78 + 0.22 * math.sin(self.visual_time * 9.7)
        flame_h = round((10 + height // 3) * flicker)
        pygame.draw.ellipse(self.canvas, config.EMBER, (x - 3, y - 8 - flame_h, 10, flame_h + 6))
        if self.lantern.illumination > 0.18:
            pygame.draw.ellipse(self.canvas, config.WAX, (x, y - 4 - flame_h // 2, 4, 5))
        glow = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.circle(glow, (214, 118, 58, int(42 * self.lantern.illumination * flicker)), (32, 32), 28)
        self.canvas.blit(glow, (x - 26, y - 34))
        # Memory fragments as small paper marks.
        for index in range(len(FRAGMENTS)):
            colour = config.WAX if index < len(self.memory.found) else (48, 46, 45)
            rx = x + 30 + index * 14
            pygame.draw.rect(self.canvas, colour, (rx - 4, y + 10, 8, 11), 1, border_radius=1)
            if index < len(self.memory.found):
                pygame.draw.line(self.canvas, config.EMBER, (rx - 2, y + 13), (rx + 2, y + 13), 1)
        if self.memory.truth:
            self._text("·" * self.memory.truth, x + 30, y - 8, 21, config.WAX)
        self._text("LENTERA / TERLINDUNGI" if self.lantern.protects else "TANPA LENTERA",
                   126, 497, 12, config.WAX)
        title_colour = (54, 65, 67)
        if self.world.quest:
            panel = pygame.Surface((932, 54), pygame.SRCALPHA)
            panel.fill((19, 35, 44, 215))
            self.canvas.blit(panel, (14, 14))
            title_colour = config.BONE
        self._text(f"{self.room + 1:02d} / {room_count()}  ·  {NUR_LEVELS[self.room].name}", 25, 22, 16,
                   title_colour)
        if self.world.quest:
            quest = self.world.quest
            self._text(f"INGATAN {quest.stage} / 6  ·  {quest.goal}", 480, 48, 16, config.BONE, center=True)
            self._text("J / JURNAL", 806, 497, 12, config.WAX)
            if quest.current:
                dx = quest.current.x - self.world.player.position.x
                arrow = "←" if dx < -60 else "→" if dx > 60 else "E"
                self._text(f"{arrow}  {abs(dx):.0f} px", 864, 23, 14, config.WAX)
        if self.boss:
            taken = sum(e["taken"] for e in self.boss.echoes)
            label = f"GEMA  {taken} / 3" if self.boss.phase == 0 else f"DIAM  {self.boss.name_presses} / 3"
            self._text(label, 760, 22, 16, (54, 65, 67))

    def _caption(self, text: str, y: int, size: int, alpha: int) -> None:
        # Long memories wrap instead of disappearing beyond the screen edges.
        font = self.fonts[size]
        lines = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split():
                candidate = f"{line} {word}".strip()
                if line and font.size(candidate)[0] > 720:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        width = max(font.size(line)[0] for line in lines) + 36
        panel = pygame.Surface((width, len(lines) * (size + 4) + 18), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 31, 37, round(alpha * 0.88)), panel.get_rect(), border_radius=4)
        pygame.draw.line(panel, (*config.WAX, alpha), (12, 0), (width - 12, 0))
        self.canvas.blit(panel, (config.SIZE[0] // 2 - width // 2, y - 7))
        self._text("\n".join(lines), config.SIZE[0] // 2, y + 2, size,
                   config.BONE, center=True, alpha=alpha)

    def _draw_interactions(self, px: float, py: float) -> None:
        if self.state != "playing" or self.world.dead:
            return
        hints = []
        if self.world.quest:
            for node in self.world.quest.plan.nodes:
                if abs(px - node.x) < 70 and abs(py - node.y) < 65:
                    hints.append((node.x, node.y - 60, "E / PERIKSA" if node.kind == "source" else "E / PILIH · J / PETUNJUK"))
        for crate in self.world.crates:
            x, y = crate.body.position
            if math.hypot(px - x, py - y) < 85:
                hints.append((x, y - crate.size[1] / 2 - 30, "E  /  TAHAN & TARIK"))
        if self.world.ropes:
            nearest = min(self.world.ropes, key=lambda b: b.position.get_distance((px, py)))
            if nearest.position.get_distance((px, py)) < 80:
                hints.append((px, py - 65, "E  /  PEGANG     W/S  /  PANJAT"))
        candle = NUR_LEVELS[self.room].candle
        if candle and not self.candle_taken and math.hypot(px - candle[0], py - candle[1]) < 70:
            hints.append((candle[0], candle[1] - 54, "E  /  INGAT KEMBALI"))
        if self.boss and self.boss.phase == 1 and math.hypot(px - self.boss.x, py - self.boss.y) < 155:
            hints.append((px, py - 70, "E  /  BERHENTI MENJAWAB"))
        for x, y, label in hints[:1]:
            image = self.fonts[14].render(label, True, config.WAX)
            width = image.get_width() + 20
            sx = max(width // 2 + 8, min(config.SIZE[0] - width // 2 - 8, x - self.camera))
            area = pygame.Rect(0, 0, width, 27)
            area.midtop = (round(sx), round(y))
            pygame.draw.rect(self.canvas, (25, 39, 45), area, border_radius=4)
            self.canvas.blit(image, image.get_rect(center=area.center))

    def _draw_menu(self) -> None:
        veil = pygame.Surface(config.SIZE, pygame.SRCALPHA)
        veil.fill((12, 25, 33, 225))
        self.canvas.blit(veil, (0, 0))
        glow = pygame.Surface((360, 180), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (204, 174, 112, 26), (0, 0, 360, 180))
        self.canvas.blit(glow, (config.SIZE[0] // 2 - 180, 120))
        self._text(config.TITLE, config.SIZE[0] // 2, 148, 78, config.BONE, center=True)
        self._text("sebuah kisah tentang cahaya yang tidak bisa kembali",
                   config.SIZE[0] // 2, 248, 21, (175, 180, 170), center=True)
        self._text("RUMAH  DESA  ARSIP  HUTAN  PERAWAT  PULANG",
                   config.SIZE[0] // 2, 292, 12, (145, 158, 154), center=True)
        self._text("ENTER  —  masuk ke rumah", config.SIZE[0] // 2, 360, 18,
                   config.WAX, center=True)
        self._text("M  —  suara   /   ESC  —  keluar", config.SIZE[0] // 2, 398, 14,
                    (145, 158, 154), center=True)
        self._text("C — lanjut checkpoint / J — jurnal saat bermain", config.SIZE[0] // 2, 438, 14,
                   (145, 158, 154), center=True)

    def _draw_pause(self) -> None:
        veil = pygame.Surface(config.SIZE, pygame.SRCALPHA)
        veil.fill((12, 25, 33, 220))
        self.canvas.blit(veil, (0, 0))
        self._text("BERHENTI SEBENTAR", config.SIZE[0] // 2, 228, 32,
                   config.BONE, center=True)
        self._text("cahaya tetap menunggu", config.SIZE[0] // 2, 272, 16,
                    (175, 180, 170), center=True)
        self._text("ESC kembali  /  R mengulang ruangan", config.SIZE[0] // 2, 320, 16,
                    config.WAX, center=True)

    def _draw_journal(self):
        veil = pygame.Surface(config.SIZE, pygame.SRCALPHA)
        veil.fill((12, 25, 33, 242))
        self.canvas.blit(veil, (0, 0))
        self._text("CATATAN JALAN PULANG", 480, 28, 32, config.BONE, center=True)
        if self.world.quest:
            quest = self.world.quest
            x = self.world.player.position.x
            left, width, top = 90, 780, 86
            pygame.draw.line(self.canvas, (71, 106, 112), (left, top), (left + width, top), 3)
            for index, node in enumerate(quest.plan.nodes):
                colour = config.WAX if index in quest.plan.order[:quest.stage] else (107, 151, 148)
                nx = round(left + width * node.x / self.world.level.width)
                pygame.draw.circle(self.canvas, colour, (nx, top), 5)
            px = round(left + width * x / self.world.level.width)
            pygame.draw.polygon(self.canvas, config.BONE, [(px - 4, top - 14), (px + 4, top - 14), (px, top - 6)])
        entries = list(self.journal.items())
        pages = max(1, (len(entries) + 2) // 3)
        self.journal_page = min(self.journal_page, pages - 1)
        if not entries:
            self._text("Belum ada catatan. Dekati benda bercahaya dan tekan E.", 480, 145, 18, config.BONE, center=True)
        for offset, (key, text) in enumerate(entries[self.journal_page * 3:self.journal_page * 3 + 3]):
            title = "MEMORI" if key.startswith("memory:") else NUR_LEVELS[int(key.split(":")[0])].name
            self._text(title, 60, 100 + offset * 124, 18, config.WAX)
            words, lines, line = text.replace("\n", " ").split(), [], ""
            for word in words:
                candidate = (line + " " + word).strip()
                if self.fonts[16].size(candidate)[0] > 830:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
            self._text("\n".join(lines), 60, 130 + offset * 124, 16, config.BONE)
        self._text(f"{self.journal_page + 1} / {pages}  ·  ←/→ halaman  ·  J/ESC kembali", 480, 492, 16,
                   config.WAX, center=True)

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
            "player_animation": self.player_animation.snapshot(),
            "quest": self.world.quest.snapshot() if self.world.quest else None,
            "journal_entries": len(self.journal),
            "play_seconds": round(self.play_seconds, 3),
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
    parser.add_argument("--continue", dest="resume", action="store_true", help="Resume the saved campaign checkpoint")
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
    if args.resume and not game.load_save():
        game.state = "menu"
        game._say("Checkpoint tidak ditemukan atau rusak.")
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
