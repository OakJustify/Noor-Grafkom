"""Playable impossible-space puzzles: reveal, remember, align and stabilise."""

from __future__ import annotations

import itertools
import math
from collections import deque
from dataclasses import dataclass
from functools import lru_cache

import pygame

from ..geometry import Rect
from .. import config
from ..quests import QuestPlan, QuestState
from ..wisp import PIVOT, facing_sprite
from ..materials import phantom_sprite


from .projection import FAMILIES, OFFSETS, PLANES, draw_projection, hypercube_projection

@dataclass(frozen=True)
class HallucinationPlan(QuestPlan):
    dimension: int = 4
    platforms: tuple[Rect, ...] = ()

class HallucinationState(QuestState):
    def __init__(self, plan: HallucinationPlan, saved: dict | None = None):
        saved = saved or {}
        self.plan = plan
        self.stage = max(0, min(6, int(saved.get("stage", 0))))
        self.values = [int(index in plan.order[:self.stage]) for index in range(6)]
        self.inspected = set(saved.get("inspected", [])) | set(plan.order[:self.stage])
        self.pressed = self.shift_held = False
        self.phase = int(saved.get("phase", 0)) % 2
        self.clock = 0.0
        self.transition = 0.0
        self.trail = deque(maxlen=8)
        self._trail_clock = 0.0

    @property
    def required_phase(self):
        return 1 if self.current and self.current.kind in ("apparition", "fold") else 0

    @property
    def interaction_x(self):
        node = self.current
        if node is None:
            return None
        return node.x + OFFSETS[node.target] if node.kind in ("witness", "parallax") else node.x

    @property
    def instruction(self):
        if self.complete:
            return "Semua gaung terikat. Pintu pulang terbuka."
        if self.phase != self.required_phase:
            return f"Q / pindah ke {PLANES[self.required_phase]}"
        kind = self.current.kind
        if kind == "apparition":
            return "Benda muncul di GAUNG. Dekati · E / ingat bentuknya"
        if kind == "absence":
            return "Bendanya hilang; bayangannya tinggal. E / sentuh bekasnya"
        if kind == "parallax":
            return "Jalan sedikit sampai dua bentuk menyatu · E / ikat"
        if kind == "witness":
            return "Pilih bayangan yang tetap ada, bukan salinan berkedip · E"
        return "Tangga hanya ada di GAUNG. Lompat ke atas · E / ikat lipatan"

    def update(self, control, world, dt=0):
        self.clock += dt
        self.transition = max(0, self.transition - dt)
        self._trail_clock += dt
        if self._trail_clock >= 0.08:
            self.trail.append(tuple(world.player.position))
            self._trail_clock = 0
        shifted = bool(getattr(control, "shift", False)) and not self.shift_held
        self.shift_held = bool(getattr(control, "shift", False))
        result = None
        if shifted and not world.dead:
            self.phase ^= 1
            self.transition = 0.32
            result = {"text": f"{PLANES[self.phase]} · {self.instruction}", "shifted": True}
        edge = control.action and not self.pressed
        self.pressed = bool(control.action)
        if not edge or world.dead or self.complete:
            return result
        px, py = world.player.position
        index, node = min(enumerate(self.plan.nodes), key=lambda item: abs(px - item[1].x))
        if abs(px - node.x) > 76 or abs(py - node.y) > 50:
            return result
        if index != self.plan.order[self.stage]:
            return {"text": f"Gaung ini belum tersambung. Ikuti penanda {self.goal}."}
        if self.phase != self.required_phase:
            return {"text": self.instruction}
        if node.kind == "parallax" and abs(px - self.interaction_x) > 10:
            return {"text": "Dua garis belum menyatu. Geser A/D sampai lingkaran putih menutup."}
        if node.kind == "witness":
            slot = min(range(3), key=lambda n: abs(px - (node.x + OFFSETS[n])))
            if slot != node.target:
                return {"text": "Salinan itu lenyap. Bayangan yang tidak bergerak adalah jejak yang nyata."}
        # Fold anchors sit at the top of real phase-dependent platforms. Being
        # on the floor cannot confirm them through a proximity shortcut.
        if node.kind == "fold" and (not world.grounded or abs(py - node.y) > 17):
            return {"text": "Naiki tangga yang muncul. Sentuh lipatan dari rak paling atas."}
        self.inspected.add(index)
        self.values[index] = 1
        self.stage += 1
        return {"text": f"{node.hint}\nBerikutnya: {self.goal}", "journal": node.hint,
                "index": index, "solved": True, "shifted": shifted}

    def snapshot(self):
        return {"schema": "hallucination-v1", "stage": self.stage, "values": self.values[:],
                "inspected": sorted(self.inspected), "phase": self.phase}

    def draw_space(self, screen, camera, player):
        if not self.phase:
            return
        screen.fill((171, 207, 243), special_flags=pygame.BLEND_RGB_MULT)
        width, height = screen.get_size()
        for index in range(7):
            x = (index * 260 - camera * 0.4) % (width + 180) - 90
            y = 180 + math.sin(self.clock * 0.25 + index) * 32
            # Distant forms appear, then vanish as the player approaches. They
            # have no interaction ring, so scenery is not a false puzzle goal.
            if abs(x - (player[0] - camera)) > 130:
                draw_projection(screen, (x, y), self.plan.dimension,
                                int(self.clock * 5 + index * 9), (70, 129, 157), 90)
        pygame.draw.line(screen, (108, 168, 189), (0, 270), (width, 220), 1)
        pygame.draw.line(screen, (108, 168, 189), (0, 230), (width, 270), 1)

    def draw(self, screen, camera, font, time, player=None, active_platforms=None):
        player = player or (0, 430)
        done_indices = set(self.plan.order[:self.stage])
        frame = int(self.clock * 5) % 64
        for rect in self.plan.platforms:
            x = rect.x - camera
            active = self.phase and (active_platforms is None or rect in active_platforms)
            colour = (129, 220, 217) if active else (63, 113, 131)
            if active:
                screen.blit(phantom_sprite(round(rect.w), round(rect.h)), (round(x) - 6, round(rect.y) - 4))
            else:
                # A dashed ghost is not mistaken for a usable solid landing.
                for dx in range(0, rect.w, 20):
                    pygame.draw.line(screen, colour, (x + dx, rect.y), (x + min(rect.w, dx + 8), rect.y))
        for index, node in enumerate(self.plan.nodes):
            x, y = node.x - camera, node.y
            if not -150 < x < screen.get_width() + 150:
                continue
            done = index in done_indices
            current = not self.complete and index == self.plan.order[self.stage]
            source_seen = index < 3 or index - 3 in done_indices
            colour = (226, 222, 176) if done else (132, 219, 217) if current else (79, 132, 148)
            pygame.draw.ellipse(screen, (41, 67, 78), (x - 30, y + 9, 60, 15))
            pygame.draw.ellipse(screen, colour, (x - 30, y + 9, 60, 15), 2)
            pygame.draw.line(screen, colour, (x - 22, y + 16), (x + 22, y + 16), 1)
            if done:
                draw_projection(screen, (x, y - 30), 3, 6, colour, 26)
            elif node.kind == "witness" and source_seen:
                for slot, offset in enumerate(OFFSETS):
                    sx = x + offset
                    if slot == node.target:
                        pygame.draw.ellipse(screen, (208, 225, 202), (sx - 13, y + 26, 26, 7))
                        pygame.draw.line(screen, (152, 218, 206), (sx, y + 16), (sx, y + 29), 2)
                    visible = self.phase and (slot == node.target or int(self.clock * 0.8 + slot) % 3 != 0)
                    if visible:
                        draw_projection(screen, (sx, y - 29), self.plan.dimension, frame + slot * 8, colour, 23)
                    else:
                        pygame.draw.circle(screen, (69, 116, 139), (round(sx), round(y - 29)), 5, 1)
            elif node.kind == "parallax" and source_seen:
                gap = max(-38, min(38, (player[0] - (node.x + OFFSETS[node.target])) * 0.6))
                draw_projection(screen, (x - gap, y - 35), self.plan.dimension, 10, (136, 221, 214), 35)
                draw_projection(screen, (x + gap, y - 35), self.plan.dimension, 10, (233, 195, 140), 35)
                if abs(gap) <= 6 and not self.phase:
                    pygame.draw.circle(screen, (233, 249, 219), (round(x), round(y - 35)), 40, 2)
            elif self.phase and source_seen:
                draw_projection(screen, (x, y - 35 + math.sin(self.clock * 2 + index) * 3),
                                self.plan.dimension, frame, colour, 36)
            else:
                # This remembered outline is the playable trace left by an
                # absent object; it never conceals a lethal collision.
                pygame.draw.lines(screen, (79, 144, 156), False,
                                  [(x - 18, y - 20), (x - 18, y - 51), (x + 18, y - 51), (x + 18, y - 20)], 1)
            if current:
                sy = y - 94 + math.sin(self.clock * 2) * 3
                pygame.draw.polygon(screen, config.WAX, [(x - 6, sy - 5), (x + 6, sy - 5), (x, sy + 4)])
            label = font.render(node.label, True, colour)
            screen.blit(label, label.get_rect(midbottom=(x, y - 72)))

    def draw_wisp_echoes(self, screen, camera, facing):
        if not self.phase:
            return
        image = facing_sprite("idle", int(self.clock * 7) % 8, 1 if facing >= 0 else -1).copy()
        for index, (x, y) in enumerate(list(self.trail)[::2]):
            image.set_alpha(18 + index * 13)
            pivot = PIVOT[0] if facing >= 0 else image.get_width() - 1 - PIVOT[0]
            screen.blit(image, (round(x - camera - pivot + (index - 2) * 7), round(y - PIVOT[1] - index * 3)))
