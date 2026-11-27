"""Developer overlay and debug actions for gameplay scenes.

Toggle with F3.  The overlay only reads the scene; cheat keys mutate it through
the systems it already owns.  See README.md for the blueprint.
"""

from __future__ import annotations

import pygame

import noor.config as C

PANEL_W = 480
LINE_H = 16
PAD = 8

COL_TEXT = (222, 232, 220)
COL_DIM = (150, 165, 155)
COL_ACCENT = (255, 210, 122)
COL_OK = (120, 220, 140)
COL_WARN = (255, 120, 120)
COL_PLAYER = (80, 220, 255)
COL_RIG = (255, 200, 90)
COL_MONSTER = (255, 120, 120)


class DevMode:
    """One instance per gameplay scene.  Inert until F3 is pressed."""

    def __init__(self):
        self.visible = False
        self.god = False
        self.freeze_clock = False
        self._font = None
        self._spawned = 0

    # -- input ---------------------------------------------------------

    def handle_event(self, event, scene):
        if event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_F3:
            self.visible = not self.visible
            return True
        if event.key == pygame.K_F4:
            self.god = not self.god
            self.visible = True
            return True
        if event.key == pygame.K_F5:
            self.refill(scene)
            return True
        if event.key == pygame.K_F6:
            self.spawn_monster(scene)
            return True
        if event.key == pygame.K_F7:
            self.freeze_clock = not self.freeze_clock
            scene.clock.set_paused(self.freeze_clock)
            self.visible = True
            return True
        if event.key == pygame.K_F8:
            self.respawn(scene)
            return True
        return False

    # -- actions -------------------------------------------------------

    def refill(self, scene):
        scene.sanity.S = scene.sanity.cap
        scene.player.stamina = scene.player.STAMINA_MAX
        self.visible = True

    def respawn(self, scene):
        x, y = scene.checkpoint.respawn_pos
        scene.player.x = float(x)
        scene.player.y = float(y)
        scene.player.vx = 0.0
        scene.player.vy = 0.0
        scene.camera.update(
            1.0,
            (
                scene.player.x + scene.player.width / 2,
                scene.player.y + scene.player.height / 2,
            ),
        )
        self.visible = True

    def spawn_monster(self, scene):
        try:
            from noor.entities.monster import Monster
            from noor.scenes import gameplay as gp
        except Exception:  # noqa: BLE001
            return
        if gp.CreatureAnimator is None:
            return
        types = ("M1", "M2", "M3")
        kinds = {"M1": "biped", "M2": "quadruped", "M3": "floating"}
        mtype = types[self._spawned % len(types)]
        self._spawned += 1
        kind = kinds[mtype]
        x = scene.player.x + scene.player.facing * 220.0
        feet = scene.player.y + scene.player.height
        ground = scene._ground_at(x, feet)
        if ground is None:
            ground = feet
        monster = Monster(
            f"dev{self._spawned}",
            mtype,
            x,
            ground - 80.0,
            stage=scene.level.get("stage", 1),
        )
        scene.monsters.append(monster)
        anchor = monster.y + (40.0 if kind == "floating" else 80.0)
        anim = gp.CreatureAnimator(
            gp.make_spec(kind, scale=0.9),
            monster.x + 20,
            anchor,
            seed=1000 + self._spawned,
        )
        scene.monster_anims[monster.id] = (anim, kind)
        self.visible = True

    # -- update --------------------------------------------------------

    def update(self, dt, scene):
        if self.god:
            scene.sanity.S = scene.sanity.cap
            scene.player.stamina = scene.player.STAMINA_MAX
        if self.freeze_clock:
            scene.clock.set_paused(True)

    # -- draw ----------------------------------------------------------

    def draw(self, surface, scene):
        if not self.visible:
            return
        self._draw_world(surface, scene)
        self._draw_panel(surface, scene)

    def _draw_world(self, surface, scene):
        ox = -scene.camera.x
        oy = -scene.camera.y
        for x, y, w, h in scene.platforms:
            rect = pygame.Rect(int(x + ox), int(y + oy), int(w), int(h))
            if (
                rect.right < 0
                or rect.left > C.SCREEN_W
                or rect.bottom < 0
                or rect.top > C.SCREEN_H
            ):
                continue
            pygame.draw.rect(surface, (90, 200, 120), rect, 1)

        for fr in scene.level.get("fragments", []):
            if fr["id"] in scene.collected_fragments:
                continue
            if not self._visible(fr["x"] + ox, fr["y"] + oy):
                continue
            pos = (int(fr["x"] + ox), int(fr["y"] + oy))
            pygame.draw.circle(surface, (255, 240, 160), pos, 9, 1)
            self._label(surface, fr["id"], pos, (255, 240, 160))

        for pr in scene.props:
            if not self._visible(pr.x + ox, pr.y + oy):
                continue
            pygame.draw.circle(
                surface, (200, 180, 120), (int(pr.x + ox), int(pr.y + oy)), 8, 1
            )

        for cp in scene.level.get("checkpoints", []):
            if not self._visible(cp["x"] + ox, cp["y"] + oy):
                continue
            active = cp["id"] == scene.checkpoint.active_id
            color = COL_OK if active else (120, 255, 200)
            pos = (int(cp["x"] + ox), int(cp["y"] + oy))
            pygame.draw.circle(surface, color, pos, 12, 2)
            self._label(surface, f"CP {cp['id']}", pos, color)

        for ex in scene.level.get("exits", []):
            sx = int(ex["x"] + ox)
            if not self._visible(sx, C.SCREEN_H / 2):
                continue
            pygame.draw.line(surface, (255, 120, 255), (sx, 0), (sx, C.SCREEN_H), 2)
            self._label(
                surface,
                f"EXIT {ex.get('to_level', 'ending')}",
                (sx, 40),
                (255, 120, 255),
            )

        player = scene.player
        rect = pygame.Rect(
            int(player.x + ox),
            int(player.y + oy),
            player.width,
            player.height,
        )
        pygame.draw.rect(surface, COL_PLAYER, rect, 1)
        pygame.draw.line(
            surface,
            COL_PLAYER,
            (rect.left, rect.bottom),
            (rect.right, rect.bottom),
            1,
        )
        arrow_x = rect.centerx + player.facing * 18
        pygame.draw.line(
            surface,
            COL_PLAYER,
            (rect.centerx, rect.centery),
            (arrow_x, rect.centery),
            2,
        )
        self._ground_probe(surface, scene, ox, oy)

        for m in scene.monsters:
            if not self._visible(m.x + ox, m.y + oy):
                continue
            mrect = pygame.Rect(int(m.x + ox), int(m.y + oy), 40, 80)
            pygame.draw.rect(surface, COL_MONSTER, mrect, 1)
            self._label(
                surface,
                f"{m.id} {m.type} {m.state}",
                (mrect.centerx, mrect.top),
                COL_MONSTER,
            )
            entry = scene.monster_anims.get(m.id)
            if entry is not None:
                self._draw_rig(surface, entry[0], ox, oy, COL_MONSTER)

        for c in scene.ambient:
            self._draw_rig(surface, c["anim"], ox, oy, COL_RIG)

    def _ground_probe(self, surface, scene, ox, oy):
        player = scene.player
        gx = player.x + player.width / 2
        feet = player.y + player.height
        gy = scene._ground_at(gx, feet)
        sx = int(gx + ox)
        if gy is None:
            sy = int(feet + oy) + 10
            pygame.draw.line(surface, COL_WARN, (sx - 5, sy - 5), (sx + 5, sy + 5), 2)
            pygame.draw.line(surface, COL_WARN, (sx - 5, sy + 5), (sx + 5, sy - 5), 2)
            return
        pygame.draw.line(surface, COL_PLAYER, (sx, int(feet + oy)), (sx, int(gy + oy)), 1)
        pygame.draw.circle(surface, COL_PLAYER, (sx, int(gy + oy)), 3, 1)

    def _draw_rig(self, surface, anim, ox, oy, color):
        def point(p):
            return (int(p[0] + ox), int(p[1] + oy))

        if not self._visible(anim.body_x + ox, anim.body_y + oy):
            return
        for leg in anim.legs:
            pygame.draw.lines(
                surface,
                color,
                False,
                [point(leg.hip), point(leg.knee), point(leg.foot)],
                2,
            )
            pygame.draw.circle(surface, (255, 255, 255), point((leg.ik_x, leg.ik_y)), 3, 1)
            pygame.draw.line(
                surface,
                (100, 200, 255),
                point(leg.foot),
                point((leg.ik_x, leg.ik_y)),
                1,
            )
        pygame.draw.circle(
            surface, color, point((anim.body_x, anim.body_y)), 6, 1
        )
        pygame.draw.circle(surface, COL_ACCENT, point(anim.head), 3)
        if anim.head_target is not None:
            pygame.draw.line(
                surface,
                (140, 140, 230),
                point(anim.head),
                point(anim.head_target),
                1,
            )
        if anim.tail is not None:
            pygame.draw.line(surface, color, point(anim.tail[0]), point(anim.tail[1]), 1)
        self._label(
            surface,
            anim.gait_name,
            (int(anim.body_x + ox) + 8, int(anim.body_y + oy) - 26),
            color,
        )

    # -- panel ---------------------------------------------------------

    @staticmethod
    def _visible(x, y, margin=160):
        return (
            -margin <= x <= C.SCREEN_W + margin
            and -margin <= y <= C.SCREEN_H + margin
        )

    def _panel_lines(self, scene):
        player = scene.player
        sanity = scene.sanity
        clock = scene.clock
        game_clock = getattr(scene.game, "clock", None)
        fps = game_clock.get_fps() if game_clock is not None else 0.0
        stage = scene.level.get("stage", 1)
        lines = [
            ("DEV MODE  F3 toggle", COL_ACCENT),
            (f"fps {fps:5.1f}  level {scene.level_id}  stage {stage}", COL_TEXT),
            (
                (
                    f"seed {scene.game.state.get('rng_seed', 0)}  "
                    f"monsters {len(scene.monsters)}  ambient {len(scene.ambient)}"
                ),
                COL_DIM,
            ),
            (f"player  x {player.x:8.1f}  y {player.y:8.1f}", COL_TEXT),
            (f"vel     vx {player.vx:7.1f}  vy {player.vy:7.1f}", COL_TEXT),
            (
                (
                    f"ground {player.on_ground}  facing {player.facing:+d}  "
                    f"stamina {player.stamina:5.1f}"
                ),
                COL_TEXT,
            ),
            (f"camera  x {scene.camera.x:8.1f}  y {scene.camera.y:8.1f}", COL_TEXT),
            (
                (
                    f"sanity  S {sanity.S:5.1f}  cap {sanity.cap:5.1f}  "
                    f"eff {sanity.s_eff:5.1f}  r {sanity.radius():5.1f}"
                ),
                COL_TEXT,
            ),
            (
                (
                    f"clock   {clock.active_time:7.1f}s  forced {clock.forced_stage()}  "
                    f"paused {clock.paused}"
                ),
                COL_TEXT,
            ),
            (
                (
                    f"fragments {len(scene.fragments.slots)}/{C.MAX_SLOTS}  "
                    f"forgotten {scene.fragments.forgotten_count}"
                ),
                COL_TEXT,
            ),
        ]
        if self.god:
            lines.append(("GOD MODE ON", COL_OK))
        if self.freeze_clock:
            lines.append(("CLOCK FROZEN", COL_ACCENT))
        for m in scene.monsters[:4]:
            lines.append(
                (
                    f"{m.id:<6} {m.type} {m.state:<7} d {abs(m.x - player.x):5.0f}",
                    COL_WARN,
                )
            )
        for c in scene.ambient[:3]:
            lines.append((f"ambient {c['kind']:<9} {c['anim'].gait_name}", COL_DIM))
        lines.append(
            ("F4 god  F5 refill  F6 spawn  F7 freeze  F8 respawn", COL_DIM)
        )
        return lines

    def _draw_panel(self, surface, scene):
        font = self._ensure_font()
        lines = self._panel_lines(scene)
        height = PAD * 2 + LINE_H * len(lines)
        x = C.SCREEN_W - PANEL_W - 10
        y = 10
        background = pygame.Surface((PANEL_W, height), pygame.SRCALPHA)
        background.fill((8, 10, 12, 190))
        surface.blit(background, (x, y))
        pygame.draw.rect(surface, (70, 80, 75), (x, y, PANEL_W, height), 1)
        for index, (text, color) in enumerate(lines):
            image = font.render(text, True, color)
            surface.blit(image, (x + PAD, y + PAD + index * LINE_H))

    def _label(self, surface, text, pos, color):
        image = self._ensure_font().render(text, True, color)
        surface.blit(image, (int(pos[0]) + 6, int(pos[1]) - 14))

    def _ensure_font(self):
        if self._font is None:
            if not pygame.font.get_init():
                pygame.font.init()
            self._font = pygame.font.SysFont("monospace", 14)
        return self._font
