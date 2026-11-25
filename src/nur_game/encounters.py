"""Lantern-dependent bestiary: different silhouettes, scales and telegraphed motion."""

import math
from dataclasses import dataclass, field
from functools import lru_cache

from .continuum import REGIONS
from .illustration import Ink
from .monsters import (
    MonsterAI,
    MonsterAnimator,
    MonsterFleeBehavior,
    MonsterState,
    _walkable,
    line_of_sight,
)

BESTIARY = (
    ("PENYAPU", .85, 78, 0, 20), ("PELANGKAH", .72, 142, 1, 90),
    ("LONCENG KOSONG", .60, 210, 2, 180), ("SERIBU KAKI", .48, 96, 3, 300),
    ("SAYAP RETAK", .36, 130, 4, 420), ("PEMBURU", .26, 118, 5, 570),
    ("AKAR BERGERAK", .18, 230, 6, 720), ("RODA MATA", .10, 104, 7, 900),
)


@lru_cache(maxsize=64)
def creature_sprite(kind, frame):
    art = Ink((240, 270))
    x, y = 120, 235
    wave = math.sin(frame * math.tau / 8)
    body, rim, light = (38, 36, 58), (112, 98, 130), (246, 175, 124)
    if kind == 0:
        art.ellipse(body, (x - 53, y - 70 + wave * 3, 106, 55))
        for n in range(6):
            dx = (n - 2.5) * 17
            art.poly(body, [(x + dx, y - 30), (x + dx + wave * 6, y - 12),
                            (x + dx + 15, y), (x + dx + 4, y - 5)])
        art.ellipse(rim, (x - 42, y - 66 + wave * 3, 86, 30), 2)
        for dx in (-13, 13):
            art.ellipse(light, (x + dx - 3, y - 49, 6, 5))
    elif kind == 1:
        for side in (-1, 1):
            knee = x + side * 33 + wave * side * 8
            art.poly(body, [(x + side * 13, y - 120), (knee, y - 66),
                            (x + side * 44, y), (x + side * 30, y - 3), (knee - side * 9, y - 65)])
            art.line(rim, (x + side * 17, y - 114), (knee, y - 65), 2)
        art.poly(body, [(x - 33, y - 136), (x - 17, y - 187), (x + 8, y - 205),
                        (x + 30, y - 181), (x + 38, y - 127), (x, y - 104)])
        art.ellipse((12, 23, 38), (x - 12, y - 181, 30, 52))
        art.line(light, (x - 5, y - 156), (x + 9, y - 153), 2)
        for side in (-1, 1):
            art.line(body, (x + side * 25, y - 155), (x + side * 70, y - 63 + wave * 9), 7)
    elif kind == 2:
        art.line(rim, (x, 0), (x + wave * 7, 44), 3)
        art.poly(body, [(x - 7, 32), (x + 15, 30), (x + 69, 82), (x + 99, 172),
                        (x + 66, 192), (x - 67, 197), (x - 103, 177), (x - 75, 86)])
        art.poly(rim, [(x - 7, 32), (x + 15, 30), (x + 69, 82), (x + 99, 172),
                       (x + 66, 192), (x - 67, 197), (x - 103, 177), (x - 75, 86)], 2)
        for dx in (-42, -15, 17, 47):
            art.line(rim, (x + dx * 0.35, 65), (x + dx, 161), 2)
            art.line(body, (x + dx, 191), (x + dx + wave * 10, 245), 6)
        art.ellipse((15, 22, 37), (x - 40, 113, 80, 37))
        art.ellipse(light, (x - 8, 126, 17, 4))
    elif kind == 3:
        for n in range(8):
            dx=x-92+n*25
            sy=y-27+math.sin(frame*.8+n)*7
            art.ellipse(body,(dx-15,sy-15,32,25))
            art.ellipse(rim,(dx-12,sy-15,26,10),2)
            for side in (-1,1):
                art.line(body,(dx,sy),(dx+side*9,sy+24),4)
                art.line(rim,(dx+side*9,sy+24),(dx+side*17,sy+19),2)
        art.line(body,(x+83,y-36),(x+107,y-55),3)
        art.ellipse(light,(x+84,y-32,7,5))
    elif kind == 4:
        art.poly(body,[(x-11,y-90),(x-93,y-145-wave*25),(x-77,y-69),
                       (x-38,y-96),(x-12,y-52),(x+7,y-50),(x+35,y-92),
                       (x+87,y-67),(x+99,y-145-wave*25),(x+13,y-92)])
        for side in (-1,1):
            art.line(rim,(x+side*9,y-87),(x+side*86,y-120-wave*20),2)
            art.line(body,(x+side*4,y-55),(x+side*21,y-25),5)
        art.ellipse(body,(x-15,y-102,30,32))
        art.ellipse(light,(x-7,y-93,5,4))
        art.ellipse(light,(x+4,y-93,5,4))
    elif kind == 5:
        art.poly(body,[(x-65,y-67),(x-14,y-87),(x+24,y-68),(x+55,y-86),
                       (x+69,y-58),(x+57,y-32),(x+18,y-44),(x-37,y-33)])
        for dx in (-48,-28,21,43):
            art.poly(body,[(x+dx-5,y-43),(x+dx+8,y-44),
                           (x+dx+wave*9,y),(x+dx-9+wave*9,y)])
        art.line(body,(x-54,y-66),(x-94,y-103+wave*13),7)
        art.line(rim,(x-49,y-63),(x-17,y-76),2)
        art.ellipse(light,(x+48,y-64,8,4))
        art.poly(body,[(x+29,y-76),(x+24,y-109),(x+44,y-80)])
    elif kind == 6:
        art.poly(body,[(x-15,y),(x-28,y-71),(x-12,y-154),(x-19,y-214),
                       (x+9,y-227),(x+26,y-176),(x+12,y-66),(x+29,y)])
        for side in (-1,1):
            for n in range(4):
                sy=y-45-n*36
                art.line(body,(x,sy),(x+side*(35+n*13),sy-36+wave*6),8-n)
                art.line(body,(x+side*(35+n*13),sy-36+wave*6),
                         (x+side*(53+n*16),sy-67),4)
            for n in range(3):
                art.line(body,(x,y-19),(x+side*(41+n*19),y-4-n*3),6)
        art.ellipse((15,22,37),(x-9,y-161,20,33))
        art.ellipse(light,(x-4,y-150,10,4))
    else:
        cy=y-64
        art.ellipse(body,(x-60,cy-60,120,120))
        art.ellipse(rim,(x-52,cy-52,104,104),4)
        for n in range(10):
            angle=(n+frame/8)*math.tau/10
            art.line(rim,(x+math.cos(angle)*22,cy+math.sin(angle)*22),
                     (x+math.cos(angle)*53,cy+math.sin(angle)*53),3)
            art.line(body,(x+math.cos(angle)*53,cy+math.sin(angle)*53),
                     (x+math.cos(angle+.17)*74,cy+math.sin(angle+.17)*74),5)
        art.ellipse(light,(x-17,cy-10,34,20))
        art.ellipse((15,22,37),(x-5,cy-9,11,18))
    return art.finish()


@dataclass
class Encounter:
    kind: int
    home: float
    x: float
    clock: float = 0
    warning: float = 0
    attack: float = 0
    visible: float = 0
    y: float = 425
    animator: MonsterAnimator = field(default_factory=MonsterAnimator)
    ai: MonsterAI = field(default_factory=MonsterAI)
    flee: MonsterFleeBehavior = field(default_factory=MonsterFleeBehavior)

    def __post_init__(self):
        self.ai.reset(self.home)


class EncounterDirector:
    def __init__(self):
        self.elapsed=0
        # Every region has all eight potential shapes, correctly within its bounds.
        # Time/charge unlocks are cumulative, so refilling never resets variety.
        self.unlocked=set()
        self.creatures = [Encounter(kind, r.start+410+kind*(r.end-r.start-670)/8,
                                   r.start+410+kind*(r.end-r.start-670)/8)
                          for r in REGIONS for kind in range(len(BESTIARY))]

    def update(self, dt, player, lantern, light_origin, elapsed=None, world=None):
        self.elapsed=max(self.elapsed+dt,elapsed or 0)
        self.unlocked.update(kind for kind,spec in enumerate(BESTIARY)
                             if lantern.illumination<=spec[1] or self.elapsed>=spec[4])
        hit = False
        for c in self.creatures:
            if abs(c.home - player[0]) > 1550:
                c.visible = c.warning = c.attack = 0
                c.ai.state = MonsterState.PATROL
                continue
            target = 1 if c.kind in self.unlocked else 0
            c.visible += (target - c.visible) * min(1, dt * 2)
            c.clock += dt
            c.animator.update(dt)
            if c.attack<=0:
                c.y=330+math.sin(c.clock*1.3)*32 if c.kind==4 else 405+math.sin(c.clock)*15 if c.kind==2 else 425
            if not target:
                c.warning = c.attack = 0
                c.ai.state = MonsterState.PATROL
                c.animator.set_movement(0, False)
                continue
            protected = lantern.protects or (lantern.charge > 0 and
                         math.hypot(player[0] - light_origin[0], player[1] - light_origin[1]) < lantern.radius)
            if protected:
                c.warning = c.attack = 0
                # Flee far enough to be safe, but do not sprint out of the
                # authored encounter pocket and vanish from the camera.
                if abs(c.x - c.home) >= 360:
                    direction = 1 if c.home > c.x else -1
                    next_x = c.x + direction * c.ai.patrol_speed * dt
                    if _walkable(world, next_x, c.y, c.kind):
                        c.x = next_x
                    c.ai.state = MonsterState.RETURN
                    c.animator.set_facing_direction((direction, 0))
                    c.animator.set_movement(c.ai.patrol_speed, False)
                else:
                    c.ai.state = MonsterState.FLEE
                    threat = light_origin if not lantern.carried else player
                    velocity = c.flee.flee_from((c.x, c.y), threat, dt, world, c.kind)
                    c.x += velocity * dt
                    c.animator.set_facing_direction((1 if c.flee.facing_right else -1, 0))
                    c.animator.set_movement(abs(velocity), True)
                continue
            distance = abs(c.x - player[0])
            los = line_of_sight(world, (c.x, c.y), player) if world is not None else True
            move, fleeing = c.ai.update(dt, c.x, player, lantern.illumination, los, world, c.kind)
            if fleeing or c.ai.state == MonsterState.FLEE:
                c.warning = c.attack = 0
                velocity = c.flee.flee_from((c.x, c.y), light_origin, dt, world, c.kind)
                c.x += velocity * dt
                c.animator.set_facing_direction((1 if c.flee.facing_right else -1, 0))
                c.animator.set_movement(abs(velocity), True)
                continue
            if move:
                next_x = c.x + move * dt
                if _walkable(world, next_x, c.y, c.kind):
                    c.x = next_x
                c.animator.set_facing_direction((move, 0))
                c.animator.set_movement(abs(move), False)
            else:
                c.animator.set_movement(0, False)
            if c.attack > 0:
                c.attack = max(0,c.attack-dt)
                speed=(205,145,180,260,290,330,0,310)[c.kind]
                c.x += math.copysign(dt*speed,player[0]-c.x)
                c.animator.set_facing_direction((player[0]-c.x or 1, 0))
                c.animator.set_movement(speed, False)
                if c.kind in (2,4):
                    c.y+=(player[1]-c.y)*min(1,dt*8)
                elif c.kind==5:
                    c.y=425-math.sin(min(1,c.attack/.8)*math.pi)*48
                reach=82 if c.kind==6 else 25
                hit |= abs(c.x - player[0]) < reach and abs(player[1]-c.y) < 42
            elif c.warning > 0:
                c.warning -= dt
                c.animator.set_facing_direction((player[0]-c.x or 1, 0))
                c.animator.set_movement(0, False)
                if c.warning <= 0:
                    c.attack = .8
            elif distance < (100 if c.kind==6 else 320):
                c.warning = 1.2
                c.animator.set_facing_direction((player[0]-c.x or 1, 0))
                c.animator.set_movement(0, False)
        return hit

    def draw(self, screen, camera, lantern):
        import pygame
        for c in self.creatures:
            x = c.x - camera
            if c.visible < 0.02 or not -200 < x < screen.get_width() + 200:
                continue
            image = c.animator.sprite(c.kind)
            scale = (.65,.95,1.05,.74,.76,.88,1.15,.76)[c.kind]
            image = pygame.transform.smoothscale(image, (round(240 * scale), round(270 * scale)))
            # A creature is a solid shape, not a translucent scenery smear.
            screen.blit(image, (round(x - 120 * scale), round(c.y+35 - 235 * scale)))
            if c.warning:
                pygame.draw.circle(screen, (236, 130, 109), (round(x), 335), round(15 + 24 * (1 - c.warning / 1.2)), 2)

    def snapshot(self):
        return {"active": sum(c.visible > 0.5 for c in self.creatures),
                "kinds": sorted({BESTIARY[c.kind][0] for c in self.creatures if c.visible > 0.5}),
                "warnings": sum(c.warning > 0 for c in self.creatures),
                 "attacks": sum(c.attack > 0 for c in self.creatures),
                 "unlocked":sorted(BESTIARY[k][0] for k in self.unlocked),
                 "elapsed":round(self.elapsed,3),"population":len(self.creatures),
                 "fleeing":sum(c.ai.state == MonsterState.FLEE for c in self.creatures),
                 "facing_left":sum(not c.animator.facing_right for c in self.creatures)}
