"""One persistent Pymunk space; authored memories connected by open promenades.

Regions are addresses for narrative/art, not scenes to load or player resets.
The v3 hallucination plans are translated intact into absolute coordinates.
"""

from bisect import bisect_right
from dataclasses import dataclass, replace

from .engine import DT
from .geometry import Level, Rect
from .hazards import HazardField
from .levels import NUR_LEVELS
from .physics import NurInput, NurWorld
from .quests import quest_for

CONNECTOR = 720


@dataclass(frozen=True)
class Region:
    index: int
    start: int
    end: int
    source: object
    terrain: tuple
    plan: object

    @property
    def refuge(self):
        return self.start + 155, 438


def translate_rect(rect, offset):
    return replace(rect, x=rect.x + offset)


def build_regions():
    regions, offset = [], 0
    for index, source in enumerate(NUR_LEVELS):
        plan = source.quest
        if plan:
            plan = replace(plan, nodes=tuple(replace(n, x=n.x + offset) for n in plan.nodes),
                           platforms=tuple(translate_rect(r, offset) for r in plan.platforms))
        terrain = []
        for r in source.level.terrain:
            left, right = max(0, r.x), min(source.level.width, r.x + r.w)
            if right > left:
                terrain.append(Rect(offset + left, r.y, right - left, r.h))
        if index==3:
            # A broken pier offers a readable alternate route beneath the rope.
            # The old room's rope phase is no longer reset on arrival.
            terrain.append(Rect(offset+810,415,95,18))
        if index < len(NUR_LEVELS) - 1:
            terrain.append(Rect(offset + source.level.width, 460, CONNECTOR, 160))
            # Optional high lookout, not a mandatory traversal toll.
            # Leave head clearance beneath optional lookouts and a genuine
            # ground-jump run-up before the machine at +605. The old last shelf
            # ended at +550, forcing a landing directly onto the spike bed.
            for dx, y, w in ((90, 388, 100), (180, 350, 220), (400, 388, 70)):
                terrain.append(Rect(offset + source.level.width + dx, y, w, 18))
        end = offset + source.level.width + (CONNECTOR if index < len(NUR_LEVELS) - 1 else 0)
        regions.append(Region(index, offset, end, source, tuple(terrain), plan))
        offset = end
    return tuple(regions)


REGIONS = build_regions()
WORLD_WIDTH = REGIONS[-1].end
STARTS = tuple(r.start for r in REGIONS)


def region_at(x):
    return REGIONS[max(0, min(len(REGIONS) - 1, bisect_right(STARTS, x) - 1))]


class ContinuousWorld(NurWorld):
    def __init__(self, room=0, progress=None):
        terrain = tuple(rect for r in REGIONS for rect in r.terrain)
        crates = tuple((x + r.start, y, size, mass) for r in REGIONS
                       for x, y, size, mass in r.source.level.crates)
        saws = tuple((x + r.start, y, radius, travel, rate) for r in REGIONS
                     for x, y, radius, travel, rate in r.source.level.saws)
        rope = REGIONS[3].source.level.rope
        rope = (rope[0] + REGIONS[3].start, *rope[1:])
        level = Level("THE LONG WAY HOME", "One unbroken road", "Q: perception / E: remember",
                      WORLD_WIDTH, (REGIONS[room].start + 130, 430),
                      (WORLD_WIDTH - 80, 430), terrain, crates=crates, saws=saws, rope=rope)
        super().__init__(room, level)
        progress = progress or {}
        self.quests = {r.index: quest_for(r.plan, progress.get(str(r.index)))
                       for r in REGIONS if r.plan}
        self.quest = self.quests.get(room)
        self.phase = getattr(self.quest, "phase", 0)
        self.gates = {}
        for r in REGIONS:
            original = r.source.level.gate
            if original:
                rect = Rect(original.x + r.start, -120, original.w, 580)
                pair = self._static_rect(rect)
                self.gates[r.index] = {"rect": rect, "pair": pair, "open": False}
        self.phantom_shapes = {}
        self.phantom_rects = tuple(rect for q in self.quests.values() for rect in q.plan.platforms)
        self.gliding = False
        self.glide_unlocked = False
        self.focus = False
        self.hazards = HazardField(REGIONS)
        self.sync_phantoms()

    def configure_phantoms(self):
        self.sync_phantoms()

    def sync_phantoms(self):
        # No superclass assumption that one room owns every spectral surface.
        if not hasattr(self, "quests"):
            return
        saved = self.quest
        for q in self.quests.values():
            self.quest = q
            self.phantom_rects = q.plan.platforms
            NurWorld.sync_phantoms(self)
        self.quest = saved
        self.phantom_rects = tuple(rect for q in self.quests.values() for rect in q.plan.platforms)

    def set_phase(self, phase):
        self.phase = phase
        for quest in self.quests.values():
            quest.phase = phase
        self.sync_phantoms()

    def _gate(self, dt):
        for index, entry in self.gates.items():
            open_now = self.quests[index].complete if index in self.quests else self._plate_open(index)
            if open_now and not entry["open"]:
                self.space.remove(entry["pair"][1], entry["pair"][0])
                entry["open"] = True
                self.events.append("gate")
            # Opened paths stay open: safe backtracking is intentional.

    def _plate_open(self, index):
        r = REGIONS[index]
        plate = r.source.level.plate
        return bool(plate and any(plate.x + r.start < c.body.position.x < plate.x + r.start + plate.w
                                  and abs(c.body.position.y - 431) < 40 for c in self.crates))

    def step(self, control=None, dt=DT):
        control = control if control is not None else NurInput()
        self.chapter = region_at(self.player.position.x).index
        self.quest = self.quests.get(self.chapter)
        super().step(control, dt)
        self.hazards.time=self.time
        self.hazards.update(self,dt)
        self.gliding = bool(self.glide_unlocked and control.jump and not self.grounded
                            and self.player.velocity.y > 60 and self.stamina.amount > 0.03
                            and not self.grab_kind)
        if self.gliding:
            self.player.velocity = (self.player.velocity.x, min(95, self.player.velocity.y))
            self.stamina.amount = max(0, self.stamina.amount - dt * 0.18)
            self.stamina.recovery_delay = 0.9
        # Finale belongs to narrative reconciliation, not crossing a coordinate.
        self.complete = False

    def progress(self):
        return {str(index): q.snapshot() for index, q in self.quests.items()}

    def snapshot(self):
        return {**super().snapshot(), "width": WORLD_WIDTH, "persistent_space": True,
                "phase": self.phase, "gliding": self.gliding,
                "solved": sum(q.stage for q in self.quests.values()),
                "open_paths": sorted(i for i, g in self.gates.items() if g["open"]),
                "hazards": self.hazards.snapshot()}
