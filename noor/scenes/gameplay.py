"""Gameplay scene."""

import json
import os
import random
import sys

import pygame

import noor.config as C
from noor.core.clock import DiseaseClock
from noor.core.input import InputState
from noor.entities.monster import Monster
from noor.entities.player import Player
from noor.entities.props import Prop
from noor.gfx.environment import draw_layer1, draw_layer3, draw_layer4
from noor.gfx.player_sprite import PlayerSprite
from noor.systems.camera import Camera
from noor.systems.checkpoint import CheckpointSystem
from noor.systems.director import SpawnDirector
from noor.systems.fragments import FragmentSystem
from noor.systems.glitch import GlitchSystem
from noor.systems.sanity import SanitySystem

try:
    from noor.entities.creature import (
        AVAILABLE as CREATURES_AVAILABLE,
    )
    from noor.entities.creature import (
        ProceduralMonster,
        choose_archetype,
        choose_body_plan,
        choose_size,
        spawn_definition,
    )
except Exception:  # noqa: BLE001 - procedural module is optional
    CREATURES_AVAILABLE = False
    ProceduralMonster = None

_SH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "shaders", "dynamic-lighting")
if _SH not in sys.path:
    sys.path.insert(0, _SH)
try:
    from renderer import apply as apply_lighting  # type: ignore
except Exception:  # noqa: BLE001
    apply_lighting = None

_PG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "procedural-generation", "prc-platform")
if _PG not in sys.path:
    sys.path.insert(0, _PG)
try:
    from generator import generate_level  # type: ignore
except Exception:  # noqa: BLE001
    generate_level = None

_ANIM = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "procedural-generation", "prc-animation")
if _ANIM not in sys.path:
    sys.path.insert(0, _ANIM)
try:
    from creature_anim import CreatureAnimator, SecondaryMotion, make_spec  # type: ignore
    from creature_draw import draw_creature  # type: ignore
except Exception:  # noqa: BLE001
    CreatureAnimator = None
    SecondaryMotion = None
    draw_creature = None

_DEV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "dev-mode")
if _DEV not in sys.path:
    sys.path.insert(0, _DEV)
try:
    from dev_mode import DevMode  # type: ignore
except Exception:  # noqa: BLE001
    DevMode = None


class GameplayScene:
    def __init__(self, game, level_id):
        self.game = game
        self.level_id = level_id
        self.inp = InputState()
        self.reduce_motion = bool(
            self.game.state.get("accessibility", {}).get("reduce_motion", False)
        )
        # load or generate level
        if level_id == "procedural" and generate_level is not None:
            self.level = generate_level(
                seed=self.game.state.get("rng_seed", 0),
                length=12800,
                difficulty="medium",
                stage=1,
                level_id="procedural",
            )
        else:
            base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "levels")
            path = os.path.join(base, f"{level_id}.json")
            with open(path, encoding="utf-8") as f:
                self.level = json.load(f)
        self.platforms = []
        for p in self.level.get("platforms", []):
            self.platforms.append((p["x"], p["y"], p["w"], p["h"]))
        self.spawn = self.level.get("spawn", [160, 600])
        self.player = Player(self.spawn[0], self.spawn[1])
        self.player_sprite = PlayerSprite()
        self.camera = Camera(self.level.get("length_px", C.SCREEN_W))
        # systems
        stage = self.level.get("stage", 1)
        self.audio = self.game.audio
        self.audio.load_stage(stage)
        self.sanity = SanitySystem(stage=stage, S=self.game.state["S"], cap=self.game.state["cap"], fragments=None)
        self.fragments = FragmentSystem(stage=stage, sanity=self.sanity)
        self.clock = DiseaseClock(stage=stage, active_time=self.game.state["clock_seconds"], paused=False)
        self.glitch = GlitchSystem(stage=stage, intensity=0.0, accessibility=self.game.state["accessibility"])
        self.director = SpawnDirector(stage=stage, sanity=self.sanity, seed=self.game.state["rng_seed"])
        self.checkpoint = CheckpointSystem()
        cps = self.level.get("checkpoints", [])
        self.checkpoint.load(cps)
        if cps:
            self.checkpoint.activate(cps[0]["id"], (cps[0]["x"], cps[0]["y"]))
        # monsters
        self.monsters = []
        for m in self.level.get("monsters", []):
            self.monsters.append(Monster(m.get("id", "m"), m.get("type", "M1"), m["x"], m["y"], stage=stage))
        self.monster_anims = {}
        if CreatureAnimator is not None:
            kinds = {"M1": "biped", "M2": "quadruped", "M3": "floating"}
            for i, m in enumerate(self.monsters):
                kind = kinds.get(m.type, "biped")
                anchor = m.y + (40.0 if kind == "floating" else 80.0)
                spec = make_spec(kind, scale=0.9)
                self.monster_anims[m.id] = (
                    CreatureAnimator(spec, m.x + 20, anchor, seed=i * 5 + 1),
                    kind,
                )
        self.collected_fragments = set(self.game.state.get("fragments_collected", []))
        self._forgotten = 0
        self.transitioning = False
        self.card_timer = 2.0
        # props
        self.props = []
        for pr in self.level.get("props", []):
            self.props.append(Prop(pr.get("id", "p"), pr.get("type", "prop"), pr["x"], pr["y"], pr.get("spots")))
        self.font = pygame.font.SysFont(None, 24)
        self.dev = DevMode() if DevMode is not None else None
        self.player_motion = SecondaryMotion() if SecondaryMotion else None
        self.ambient = []
        if level_id == "procedural":
            self._spawn_ambient()
        self._spawn_creatures()

    def _spawn_creatures(self):
        """Place 3-6 deterministic generated creatures on platforms ahead."""
        if not CREATURES_AVAILABLE or ProceduralMonster is None:
            return
        stage = int(self.level.get("stage", 1))
        base = int(self.game.state.get("rng_seed", 0))
        rng = random.Random(
            base * 7919 + stage * 104729 + sum(ord(c) for c in self.level_id)
        )
        free = C.GLOBAL_ENTITY_CAP - len(self.monsters)
        count = min(rng.randint(3, 6), max(0, free))
        length = float(self.level.get("length_px", C.SCREEN_W))
        candidates = []
        for px, py, pw, _ph in self.platforms:
            if pw < 120:
                continue
            for frac in (0.25, 0.5, 0.75):
                x = px + pw * frac
                if self.spawn[0] + 300 < x < length - 100:
                    candidates.append((x, py))
        candidates.sort()
        if count <= 0 or not candidates:
            return
        picks = rng.sample(candidates, min(count, len(candidates)))
        for i, (x, py) in enumerate(picks):
            archetype = choose_archetype(stage, rng)
            plan = choose_body_plan(archetype, rng)
            size = choose_size(stage, rng)
            definition = spawn_definition(
                archetype, stage, 42 + base + i * 977, plan, size
            )
            monster = ProceduralMonster(
                f"proc{stage}_{i}", definition, x, py, stage
            )
            monster.y = py - monster.height
            self.monsters.append(monster)

    def _ground_at(self, x, anchor):
        tops = [py for px, py, pw, _ph in self.platforms if px <= x <= px + pw]
        if not tops:
            return None
        return min(tops, key=lambda ty: abs(ty - anchor))

    def _monster_state(self, monster):
        if monster.stun_timer > 0:
            return "hit"
        if monster.state == "chase":
            return "run"
        if monster.state == "patrol":
            return "walk"
        return "idle"

    def _spawn_ambient(self):
        """Three visual-only creatures so the procedural level shows the rigs."""
        if CreatureAnimator is None or draw_creature is None:
            return
        candidates = [p for p in self.platforms if p[2] >= 220 and p[0] > 500]
        if len(candidates) < 3:
            return
        picks = [candidates[int(len(candidates) * f)] for f in (0.25, 0.5, 0.75)]
        kinds = ("biped", "quadruped", "floating")
        colors = ((208, 198, 176), (188, 196, 170), (200, 214, 235))
        for i, (kind, (px, py, pw, _ph)) in enumerate(zip(kinds, picks)):
            anchor_y = py - 110.0 if kind == "floating" else py
            spec = make_spec(kind, scale=0.9, color=colors[i])
            anim = CreatureAnimator(spec, px + pw / 2, anchor_y, seed=i * 7 + 3)
            self.ambient.append({
                "kind": kind,
                "x": px + pw / 2,
                "y": anchor_y,
                "vx": 26.0 + i * 4.0,
                "min_x": px + 40,
                "max_x": px + pw - 40,
                "ground": (lambda _x, gy=anchor_y: gy),
                "anim": anim,
            })

    def _update_ambient(self, dt):
        target = (self.player.x + self.player.width / 2, self.player.y + 20)
        for c in self.ambient:
            c["x"] += c["vx"] * dt
            if c["x"] < c["min_x"]:
                c["x"] = c["min_x"]
                c["vx"] = abs(c["vx"])
            elif c["x"] > c["max_x"]:
                c["x"] = c["max_x"]
                c["vx"] = -abs(c["vx"])
            grounded = c["kind"] != "floating"
            c["anim"].update(
                dt,
                x=c["x"],
                y=c["y"],
                vx=c["vx"],
                facing=1 if c["vx"] >= 0 else -1,
                state="walk",
                on_ground=grounded,
                ground_height=c["ground"] if grounded else None,
                head_target=target,
                reduce_motion=self.reduce_motion,
            )

    def handle_event(self, event):
        if self.dev is not None and self.dev.handle_event(event, self):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a or event.key == pygame.K_LEFT:
                self.inp.left = True
            if event.key == pygame.K_d or event.key == pygame.K_RIGHT:
                self.inp.right = True
            if event.key == pygame.K_SPACE:
                self.inp.jump_pressed = True
                self.inp.jump_held = True
            if event.key == pygame.K_e:
                self.inp.interact = True
            if event.key == pygame.K_f:
                self.inp.flare = True
            if event.key == pygame.K_c:
                self.inp.cover = True
                self.player.covering = True
            if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.inp.run = True
            if event.key == pygame.K_ESCAPE:
                from noor.scenes.pause import PauseScene
                self.game.scenes.push(PauseScene(self.game, self))
        if event.type == pygame.KEYUP:
            if event.key in (pygame.K_a, pygame.K_LEFT):
                self.inp.left = False
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                self.inp.right = False
            if event.key == pygame.K_SPACE:
                self.inp.jump_held = False
            if event.key == pygame.K_c:
                self.inp.cover = False
                self.player.covering = False
            if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.inp.run = False

    def update(self, dt):
        if self.dev is not None:
            self.dev.update(dt, self)
        if self.card_timer > 0:
            self.card_timer -= dt
        stage = self.level.get("stage", 1)
        speed_mult = C.SPEED_MULT[stage - 1]
        was_ground = self.player.on_ground
        self.player.update(dt, self.inp, self.platforms, speed_mult=speed_mult)
        if self.player_sprite.available():
            if self.player.covering:
                anim_state = "focus"
            elif not self.player.on_ground:
                anim_state = "jump"
            elif abs(self.player.vx) > 1.0:
                anim_state = "run" if self.player.running else "walk"
            else:
                anim_state = "idle"
            self.player_sprite.update(dt, anim_state, self.player.facing)
        if self.player_motion is not None:
            if self.reduce_motion:
                self.player_motion.x = 0.0
                self.player_motion.y = 0.0
                self.player_motion.vx = 0.0
                self.player_motion.vy = 0.0
            else:
                self.player_motion.update(dt, self.player.vx, self.player.vy, self.player.on_ground)
        self._update_ambient(dt)
        if was_ground and not self.player.on_ground and self.player.vy < 0:
            self.audio.cue("jump")
        elif not was_ground and self.player.on_ground:
            self.audio.cue("land")
        # interact fragments (once per id)
        if self.inp.interact:
            for fr in self.level.get("fragments", []):
                if fr["id"] in self.collected_fragments:
                    continue
                if abs(fr["x"] - self.player.x) < C.INTERACT_RANGE and abs(fr["y"] - self.player.y) < C.INTERACT_RANGE:
                    self.fragments.collect(fr["id"])
                    self.collected_fragments.add(fr["id"])
                    self.game.state["fragments_collected"] = sorted(self.collected_fragments)
                    self.audio.cue("fragment")
                    break
        # checkpoint activation
        for cp in self.level.get("checkpoints", []):
            if (abs(cp["x"] - self.player.x) < C.INTERACT_RANGE
                    and abs(cp["y"] - self.player.y) < C.INTERACT_RANGE
                    and self.checkpoint.active_id != cp["id"]):
                self.checkpoint.activate(cp["id"], (cp["x"], cp["y"]))
                self.game.state["checkpoint_id"] = cp["id"]
                self.audio.cue("checkpoint")
        # sanity update
        stage_progress = self.player.x / max(1, self.level.get("length_px", 1))
        self.sanity.update(dt, stage_progress=stage_progress, fragments=self.fragments)
        self.fragments.update(dt, sanity=self.sanity)
        if self.fragments.forgotten_count > self._forgotten:
            self._forgotten = self.fragments.forgotten_count
            self.audio.cue("forget")
        # clock
        self.clock.update(dt)
        forced = self.clock.forced_stage()
        if not self.transitioning and forced > stage:
            target = {2: "s2_a", 3: "s3_a", 4: "s4_a"}.get(forced)
            if target:
                self._go_to_level(target)
                return
        if not self.transitioning and self.clock.is_final():
            self._go_to_level(None)
            return
        # glitch
        intensity = self.sanity.intensity()
        self.glitch.update(dt, stage=stage, intensity=intensity)
        # ambience follows sanity + stage
        self.audio.set_intensity(intensity, stage=stage)
        self.audio.update(dt)
        # director
        self.director.update(dt, player=self.player, camera=self.camera)
        fallen = [m.id for m in self.monsters if m.y > C.SCREEN_H + 400]
        if fallen:
            # Drop monsters that fell out of the world and their animators.
            for mid in fallen:
                self.monster_anims.pop(mid, None)
            self.monsters = [m for m in self.monsters if m.id not in fallen]
        for m in self.monsters:
            m.update(dt, self.player, self.sanity, self.platforms, world=self)
            # contact check
            mx, my, mw, mh = m.rect()
            px, py, pw, ph = self.player.rect()
            if (px < mx + mw and px + pw > mx and py < my + mh and py + ph > my
                    and self.player.invuln <= 0
                    and not (self.dev is not None and self.dev.god)):
                harmful = True
                if hasattr(m, "contact_damage"):
                    harmful = m.contact_damage(self.player)
                if harmful:
                    self.sanity.apply("contact")
                    self.player.invuln = C.INVULN
                    self.audio.cue("contact")
                    self.player.x -= 50
                elif getattr(m, "good", False):
                    self.sanity.apply("heal", 6)
                    self.player.invuln = C.INVULN
            entry = self.monster_anims.get(m.id)
            if entry is not None:
                anim, kind = entry
                anchor = m.y + (40.0 if kind == "floating" else 80.0)
                ground = None
                if kind != "floating":
                    ground = lambda x, a=anchor: self._ground_at(x, a)
                anim.update(
                    dt,
                    x=m.x + 20,
                    y=anchor,
                    vx=m.vx,
                    vy=m.vy,
                    facing=1 if m.vx > 0 else (-1 if m.vx < 0 else None),
                    state=self._monster_state(m),
                    on_ground=kind == "floating" or m.on_ground,
                    ground_height=ground,
                    head_target=(self.player.x + self.player.width / 2, self.player.y + 20),
                    reduce_motion=self.reduce_motion,
                )
            vocal = getattr(m, "pending_vocal", None)
            if vocal and hasattr(self.audio, "play_array"):
                self.audio.play_array(m.vocal(vocal), volume=0.45)
        # camera
        self.camera.update(dt, (self.player.x + self.player.width / 2, self.player.y + self.player.height / 2))
        # reset frame inputs
        self.inp.reset_frame()
        # save state
        self.game.state["S"] = self.sanity.S
        self.game.state["cap"] = self.sanity.cap
        self.game.state["clock_seconds"] = self.clock.active_time
        # fall / death
        if self.player.y > C.SCREEN_H + 400:
            self._respawn()
            return
        # exit check
        if not self.transitioning:
            for ex in self.level.get("exits", []):
                if self.player.x >= ex["x"]:
                    self._go_to_level(ex.get("to_level"))
                    return

    def _respawn(self):
        pos = self.checkpoint.respawn()
        self.player.x, self.player.y = pos
        self.player.vy = 0
        self.sanity.apply("death")
        self.audio.cue("death")
        self.game.state["deaths"] = self.game.state.get("deaths", 0) + 1
        self.game.state["S"] = self.sanity.S

    def _go_to_level(self, next_level):
        self.transitioning = True
        self.audio.cue("stage")
        self.game.state["level_id"] = next_level or "ending"
        self.game.save.save_progress(self.game.state)
        if next_level:
            self.game.scenes.replace(GameplayScene(self.game, next_level))
        else:
            from noor.scenes.ending import EndingScene
            self.game.scenes.replace(EndingScene(self.game))

    def draw(self, surface):
        stage = self.level.get("stage", 1)
        pal = [(43, 42, 61), (31, 35, 48), (18, 20, 28), (7, 7, 10)]
        t = pygame.time.get_ticks() / 1000.0
        draw_layer4(surface, self.camera, t)
        draw_layer3(surface, self.camera, t)
        # mid tint to keep readability
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((*pal[stage - 1], 40))
        surface.blit(overlay, (0, 0))
        # platforms
        for (x, y, w, h) in self.platforms:
            rx, ry = self.camera.apply((x, y))
            pygame.draw.rect(surface, (90, 80, 70), (rx, ry, w, h))
        # fragments
        for fr in self.level.get("fragments", []):
            if fr["id"] in self.collected_fragments:
                continue
            rx, ry = self.camera.apply((fr["x"], fr["y"]))
            pygame.draw.circle(surface, (255, 230, 170), (int(rx), int(ry)), 9)
        # props
        for pr in self.props:
            rx, ry = self.camera.apply((pr.x, pr.y))
            pygame.draw.circle(surface, (200, 180, 120), (int(rx), int(ry)), 8)
        # monsters
        for m in self.monsters:
            if hasattr(m, "renderer"):
                m.draw(surface, self.camera)
                continue
            entry = self.monster_anims.get(m.id)
            if entry is not None and draw_creature is not None:
                draw_creature(surface, entry[0], (-self.camera.x, -self.camera.y))
            else:
                rx, ry = self.camera.apply((m.x, m.y))
                pygame.draw.rect(surface, (60, 40, 50), (rx, ry, 40, 80))
        # ambient procedural creatures (visual placeholders)
        for c in self.ambient:
            draw_creature(surface, c["anim"], (-self.camera.x, -self.camera.y))
        # player
        mx, my = self.player_motion.offset() if self.player_motion else (0.0, 0.0)
        if self.player_sprite.available():
            frame, pivot = self.player_sprite.get_frame()
            # align sprite bottom to player's feet
            feet_x = self.player.x + self.player.width / 2 + mx
            feet_y = self.player.y + self.player.height + my
            bx = feet_x - pivot[0]
            by = feet_y - frame.get_height()
            rx, ry = self.camera.apply((bx, by))
            surface.blit(frame, (rx, ry))
        else:
            rx, ry = self.camera.apply((self.player.x + mx, self.player.y + my))
            pygame.draw.rect(surface, (237, 227, 208), (rx, ry, self.player.width, self.player.height))
        # lantern glow
        r = self.sanity.radius()
        cx, cy = self.camera.apply((self.player.x + self.player.width / 2, self.player.y + 20))
        # simple circle alpha
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 210, 122, 30), (r, r), int(r))
        surface.blit(s, (cx - r, cy - r))
        # HUD
        t = self.font.render(f"S:{self.sanity.s_eff:.0f} R:{r:.0f} stage:{stage}", True, (230, 220, 200))
        surface.blit(t, (10, 10))
        # bars (top-left): light (sanity) and stamina
        bar_w, bar_h = 180, 10
        bx, by = 10, 50
        # light bar
        pygame.draw.rect(surface, (40, 40, 50), (bx, by, bar_w, bar_h))
        pygame.draw.rect(surface, (255, 210, 122), (bx, by, int(bar_w * (self.sanity.s_eff / 100.0)), bar_h))
        # stamina bar
        by2 = by + bar_h + 6
        pygame.draw.rect(surface, (40, 40, 50), (bx, by2, bar_w, bar_h))
        pygame.draw.rect(surface, (120, 200, 120), (bx, by2, int(bar_w * (self.player.stamina / Player.STAMINA_MAX)), bar_h))
        # fragments slots
        x = 10
        for sl in self.fragments.slots:
            pygame.draw.rect(surface, (200, 180, 120), (x, 30, 12, 12))
            x += 16
        # level title card
        if self.card_timer > 0:
            name = self.game.i18n.t(f"level.{self.level_id}")
            t = pygame.font.SysFont(None, 40).render(name, True, (235, 225, 205))
            surface.blit(t, (C.SCREEN_W // 2 - t.get_width() // 2, 120))
        # foreground layer (covers player)
        draw_layer1(surface, self.camera, pygame.time.get_ticks() / 1000.0)
        # dynamic sunlight shader (CPU fallback)
        if apply_lighting is not None:
            apply_lighting(surface, pygame.time.get_ticks() / 1000.0)
        if self.dev is not None:
            self.dev.draw(surface, self)