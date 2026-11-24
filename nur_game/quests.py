"""In-world memory puzzles: carry clues, tune machines, wire circuits and move weights.

There are no time locks. A puzzle advances only through nearby ordinary E inputs
and, for scales, a crate genuinely placed on the physical pressure plate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from . import config


@dataclass(frozen=True)
class QuestNode:
    x: float
    label: str
    kind: str
    hint: str
    target: int = 0
    choices: tuple[str, ...] = ()
    y: float = 430
    pattern: tuple[int, ...] = ()
    plate: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class QuestPlan:
    family: str
    story: str
    nodes: tuple[QuestNode, ...]
    order: tuple[int, ...] = (0, 3, 1, 4, 2, 5)


class QuestState:
    def __init__(self, plan: QuestPlan, saved: dict | None = None):
        self.plan = plan
        saved = saved or {}
        self.stage = max(0, min(len(plan.order), int(saved.get("stage", 0))))
        self.values = list(saved.get("values", [0] * len(plan.nodes)))
        if len(self.values) != len(plan.nodes):
            self.values = [0] * len(plan.nodes)
        for index, node in enumerate(plan.nodes):
            bound = 8 if node.kind in ("circuit", "valve") else len(node.pattern) + 1 if node.kind == "melody" else max(1, len(node.choices))
            self.values[index] = max(0, int(self.values[index])) % bound
        self.pressed = False
        self.inspected = set(saved.get("inspected", []))

    @property
    def complete(self):
        return self.stage == len(self.plan.order)

    @property
    def current(self):
        return None if self.complete else self.plan.nodes[self.plan.order[self.stage]]

    @property
    def goal(self):
        return "Jalan terbuka. Bawa cahaya ke pintu berikutnya." if self.complete else self.current.label

    def update(self, control, world):
        edge = control.action and not self.pressed
        self.pressed = bool(control.action)
        if not edge or world.dead:
            return None
        px, py = world.player.position
        index, node = min(enumerate(self.plan.nodes), key=lambda item: abs(px - item[1].x))
        if abs(px - node.x) > 64 or abs(py - node.y) > 65:
            return None
        self.inspected.add(index)
        journal = node.hint
        if node.kind != "source" and index >= 3 and index - 3 in self.inspected:
            journal = f"{node.label}: {self.plan.nodes[index - 3].hint}"
        if self.complete:
            return {"text": node.hint, "journal": journal}
        if index != self.plan.order[self.stage]:
            return {"text": f"{node.hint}\nYang masih dibutuhkan: {self.goal}", "journal": journal}
        solved = node.kind == "source"
        note = None
        if node.kind == "match":
            slot = min(range(len(node.choices)), key=lambda n: abs(px - (node.x + (n - 1.5) * 32)))
            self.values[index] = slot
            solved = slot == node.target
        elif node.kind == "melody":
            note = min(range(4), key=lambda n: abs(px - (node.x + (n - 1.5) * 32)))
            progress = self.values[index]
            if progress >= len(node.pattern):
                progress = self.values[index] = 0
            if note == node.pattern[progress]:
                self.values[index] += 1
            else:
                self.values[index] = 1 if note == node.pattern[0] else 0
            solved = self.values[index] == len(node.pattern)
        elif node.kind == "dial":
            self.values[index] = (self.values[index] + 1) % len(node.choices)
            solved = self.values[index] == node.target
        elif node.kind in ("circuit", "valve"):
            # Three separately clickable switches, not a global 'solve' button.
            bit = min(range(3), key=lambda n: abs(px - (node.x + (n - 1) * 42)))
            self.values[index] ^= 1 << bit
            solved = self.values[index] == node.target
        elif node.kind == "weight":
            plate = node.plate
            if plate:
                for crate in world.crates:
                    crate.shape.cache_bb()
                    bb = crate.shape.bb
                    left, top, width, height = plate
                    if (bb.right > left and bb.left < left + width
                            and top - 2 <= bb.top <= top + height + 8):
                        solved = True
        if solved:
            self.stage += 1
            return {"text": f"{node.hint}\nBerikutnya: {self.goal}", "journal": journal, "solved": True, "note": note}
        if node.kind == "weight":
            text = "Tinggalkan peti di pelat. Beratmu sendiri tidak cukup."
        elif node.kind == "circuit":
            text = "Tiga saklar terpisah. Rangkaian yang menyala harus sama dengan catatan."
        elif node.kind == "valve":
            text = f"Debit saat ini: {self.values[index]} / 7. Cabang bernilai 1, 2, dan 4; cocokkan debit di catatan."
        elif node.kind == "melody":
            text = f"{node.choices[note]} · urutan {self.values[index]} / {len(node.pattern)}. Nada salah memulai ulang melodi, bukan ruangan."
        else:
            text = f"{node.label}: {node.choices[self.values[index]]}. Periksa petunjuk di jurnal (J)."
        return {"text": text, "journal": journal, "note": note}

    def snapshot(self):
        return {"stage": self.stage, "values": self.values[:], "inspected": sorted(self.inspected)}

    def draw(self, screen, camera, font, time):
        for index, node in enumerate(self.plan.nodes):
            x, y = round(node.x - camera), round(node.y)
            if not -100 < x < screen.get_width() + 100:
                continue
            done = index in self.plan.order[:self.stage]
            current = not self.complete and index == self.plan.order[self.stage]
            brass = config.WAX if done else (139, 157, 148)
            pygame.draw.rect(screen, (26, 46, 53), (x - 31, y - 59, 62, 88), border_radius=5)
            pygame.draw.rect(screen, brass, (x - 31, y - 59, 62, 88), 2, border_radius=5)
            if node.kind == "source":
                pygame.draw.rect(screen, (220, 208, 165), (x - 14, y - 47, 28, 33))
                for row in range(4):
                    pygame.draw.line(screen, (95, 108, 93), (x - 9, y - 40 + row * 6), (x + 8, y - 40 + row * 6))
            elif node.kind in ("match", "melody"):
                pygame.draw.rect(screen, (28, 47, 55), (x - 70, y - 46, 140, 39), border_radius=4)
                for slot, choice in enumerate(node.choices):
                    bx = x + (slot - 1.5) * 32
                    colour = config.WAX if (node.kind == "match" and self.values[index] == slot) or done else (83, 114, 114)
                    pygame.draw.rect(screen, colour, (bx - 12, y - 43, 24, 31), border_radius=3)
                    image = font.render(choice[:3].upper(), True, (225, 234, 202))
                    screen.blit(image, image.get_rect(center=(bx, y - 28)))
                if node.kind == "melody":
                    for n in range(len(node.pattern)):
                        pygame.draw.circle(screen, config.WAX if n < self.values[index] else (55, 84, 88), (x - 22 + n * 14, y + 6), 4)
            elif node.kind in ("circuit", "valve"):
                pygame.draw.rect(screen, (28, 47, 55), (x - 70, y - 37, 140, 26), border_radius=4)
                for bit in range(3):
                    bx = x + (bit - 1) * 42
                    colour = config.WAX if self.values[index] & (1 << bit) else (83, 114, 114)
                    pygame.draw.circle(screen, colour, (bx, y - 24), 10)
                    pygame.draw.line(screen, (201, 208, 174), (bx, y - 24), (bx, y - 34), 2)
                    if node.kind == "valve":
                        image = font.render(str(1 << bit), True, (222, 223, 192))
                        screen.blit(image, image.get_rect(center=(bx, y - 52)))
                if node.kind == "valve":
                    pygame.draw.rect(screen, (50, 90, 103), (x - 20, y - 2, 40, 23))
                    pygame.draw.rect(screen, (143, 211, 205), (x - 19, y + 21 - self.values[index] * 3, 38, self.values[index] * 3))
            elif node.kind == "weight":
                pygame.draw.lines(screen, brass, False, [(x - 20, y - 24), (x, y - 43), (x + 20, y - 24)], 3)
                pygame.draw.line(screen, brass, (x, y - 42), (x, y - 13), 2)
                left, top, width, height = node.plate
                pygame.draw.rect(screen, (120, 165, 155), (left - camera, top, width, height))
                pygame.draw.line(screen, brass, (left + width / 2 - camera, top), (x, y + 20), 2)
            else:
                pygame.draw.circle(screen, (56, 86, 92), (x, y - 30), 22)
                for n in range(len(node.choices)):
                    angle = n * math.tau / len(node.choices) - math.pi / 2
                    pygame.draw.circle(screen, brass, (round(x + math.cos(angle) * 18), round(y - 30 + math.sin(angle) * 18)), 2)
                angle = self.values[index] * math.tau / len(node.choices) - math.pi / 2
                pygame.draw.line(screen, config.WAX, (x, y - 30),
                                 (round(x + math.cos(angle) * 15), round(y - 30 + math.sin(angle) * 15)), 3)
                if self.plan.family == "mirror":
                    end = (round(x + math.cos(angle) * 130), round(y - 30 + math.sin(angle) * 100))
                    pygame.draw.line(screen, (145, 214, 202), (x, y - 30), end, 2)
                label = node.choices[self.values[index]]
                image = font.render(label, True, brass)
                screen.blit(image, image.get_rect(midtop=(x, y + 31)))
            if current:
                sy = y - 77 + math.sin(time * 3) * 3
                pygame.draw.polygon(screen, config.WAX, [(x - 5, sy - 5), (x + 5, sy - 5), (x, sy + 2)])
            image = font.render(node.label, True, (214, 219, 196))
            rect = image.get_rect(midbottom=(x, y - 83))
            pygame.draw.rect(screen, (25, 44, 52), rect.inflate(12, 6), border_radius=3)
            screen.blit(image, rect)
