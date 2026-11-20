"""Seeded room composition, with input-only witnesses in the live physics.

Rooms are not Campaign level copies. A spatial grammar composes crate relays
around a generated water lift, oscillating bridge, rope, field or magnet rig.
Only complete rooms that pass the same World.step used by the game are admitted.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import random

import pymunk

from .levels import Level, MagneticPuzzle, Rect
from .physics import DT, GRAVITY, SOLID, Input, Prop, World
from .puzzle_archetypes import PuzzleArchetype
from .seesaw import SeesawPilot


class ProceduralRoom:
    """Placeholder class for generated room type."""
    pass


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class RoomTheme:
    name: str
    palette_index: int
    sky_tint: tuple[int, int, int]
    fog_density: float
    particle_type: str
    time_of_day: str
    scenery_seed: int


@dataclass(frozen=True)
class PuzzleStage:
    archetype: PuzzleArchetype
    start: float
    end: float
    floor_y: float
    exit_y: float
    crate_index: int = -1
    plate: Rect | None = None
    gate: Rect | None = None
    variant: str = ""


ARCHETYPES = (
    PuzzleArchetype.CRATE_PLATE, PuzzleArchetype.ROPE_PENDULUM,
    PuzzleArchetype.WATER_CRATE, PuzzleArchetype.SEESAW_LAUNCH,
    PuzzleArchetype.GRAVITY_MAZE, PuzzleArchetype.MAGNET_STAIRS,
)

blocked_archetype = PuzzleArchetype.CRATE_PLATE

HINTS = {
    PuzzleArchetype.CRATE_PLATE: "HOLD E / MOVE THE CRATE TO ITS PLATE, THEN CROSS THE GATE",
    PuzzleArchetype.WATER_CRATE: "E / OPEN COVER · PUSH BOX INTO POOL · E / VALVE · RIDE AND JUMP",
    PuzzleArchetype.SEESAW_LAUNCH: "RUN AND JUMP BETWEEN BEAM ENDS · LEAP RIGHT AT THE HIGH CREST",
    PuzzleArchetype.ROPE_PENDULUM: "HOLD E / CATCH ROPE · W / CLIMB · SPACE / RELEASE TOWARD LEDGE",
    PuzzleArchetype.GRAVITY_MAZE: "E / INVERT GRAVITY · CROSS ABOVE THE WALL · WAIT FOR GRAVITY TO RETURN",
    PuzzleArchetype.MAGNET_STAIRS: "E / POWER MAGNET · LIFT BLOCKS · REVERSE AFTER FIRST CATCH · CLIMB",
}


@dataclass
class GateRuntime:
    """Shared renderer-compatible crate relay state."""
    crate: object
    plate: Rect
    gate: Rect
    gate_body: object
    crate_was_grabbed: bool = False
    solved: bool = False
    gate_fraction: float = 0.0


class ProceduralRoomWorld(World):
    def __init__(self, seed: int, room):
        super().__init__(room.template_index, level=room.level)
        self.endless = self.room_run = True
        self.seed = int(seed)
        self.room = room
        self.room_number = room.number
        self.room_template = room.template_index
        self.room_theme = room.theme
        self.room_archetype = room.puzzle_archetype
        self.puzzle_name = room.puzzle_name
        self.puzzle_runtimes = {}
        for index, stage in enumerate(room.stages):
            if stage.gate is None:
                continue
            r = stage.gate
            body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            body.position = (r.x + r.w / 2, r.y + r.h / 2)
            shape = pymunk.Poly.create_box(body, (r.w, r.h))
            shape.friction = .7
            shape.filter = pymunk.ShapeFilter(categories=self.player_shape.filter.mask)
            self.space.add(body, shape)
            self.puzzle_runtimes[index] = GateRuntime(
                self.crates[stage.crate_index], stage.plate, r, body)
        self.mechanics_used = set()
        self.stage_index = 0

    def _gate(self, dt):
        for runtime in self.puzzle_runtimes.values():
            prop, plate = runtime.crate, runtime.plate
            runtime.crate_was_grabbed |= self.grabbed is prop.body
            prop.shape.cache_bb()
            bb = prop.shape.bb
            supported = (plate.x + prop.size[0] / 2 <= prop.body.position.x
                         <= plate.x + plate.w - prop.size[0] / 2)
            resting = abs(bb.top - (plate.y + plate.h / 2)) <= 12
            if not runtime.solved and runtime.crate_was_grabbed and supported and resting:
                runtime.solved = True
                self.events.append("gate")
            target = float(runtime.solved)
            delta = max(-dt * 1.4, min(dt * 1.4, target - runtime.gate_fraction))
            runtime.gate_fraction += delta
            runtime.gate_body.velocity = (0, -delta * (runtime.gate.h + 20) / dt)

    def interact(self):
        super().interact()
        if self.cover_open:
            self.mechanics_used.add("cover")
        if self.water_active:
            self.mechanics_used.add("valve")
        if self.gravity == -1:
            self.mechanics_used.add("gravity")
        if self.magnet and self.magnet.enabled:
            self.mechanics_used.add("magnet")

    def flip_gravity(self, direction):
        super().flip_gravity(direction)
        self.space.gravity = (0, GRAVITY)

    def _buoyancy(self):
        super()._buoyancy()
        if self.gravity == -1:
            self.player.apply_force_at_world_point((0, -2 * GRAVITY * self.player.mass), self.player.position)

    def step(self, control=Input(), dt=DT):
        super().step(control, dt)
        if self.grab_kind == "rope":
            self.mechanics_used.add("rope")
        if self.beam and self.support is self.beam.body and abs(self.beam.body.angle) > .20:
            self.mechanics_used.add("seesaw")
        if self.magnet and self.magnet.captured:
            self.mechanics_used.add("capture")
        x = self.player.position.x
        while (self.stage_index < len(self.room.stages) - 1
               and x >= self.room.stages[self.stage_index].end - 4):
            self.stage_index += 1

    @property
    def current_hint(self):
        return HINTS[self.room.stages[self.stage_index].archetype]

    def snapshot(self):
        state = super().snapshot()
        state.update(endless=True, seed=self.seed, room_number=self.room_number,
                     puzzle_template=self.room_template + 1, puzzle_name=self.puzzle_name,
                     theme=self.room_theme.name, room_seed=self.room.seed,
                     layout_signature=self.room.layout_signature,
                     puzzle_signature=self.room.puzzle_signature,
                     background_signature=self.room.background_signature,
                     verified_solvable=self.room.verified_solvable,
                     stages=len(self.room.stages), stage=self.stage_index + 1,
                     gates_solved=sum(r.solved for r in self.puzzle_runtimes.values()))
        return state


class RoomPilot:
    """Geometry-relative ordinary controls, also used for the --demo witness."""
    def __init__(self):
        self.stage_index = -1
        self.phase = "approach"
        self.seesaw = SeesawPilot()
        self.catch_distance = None

    def control(self, w: ProceduralRoomWorld):
        index = w.stage_index
        if index != self.stage_index:
            self.stage_index, self.phase = index, "approach"
            self.seesaw = SeesawPilot()
            self.catch_distance = None
        stage = w.room.stages[index]
        x, y = w.player.position
        arch = stage.archetype
        if arch is PuzzleArchetype.CRATE_PLATE:
            r = w.puzzle_runtimes[index]
            crate = r.crate
            if r.solved:
                return Input(move=1, jump=w.grounded and x < crate.body.position.x
                             and x > crate.body.position.x - crate.size[0] / 2 - 55)
            if stage.variant == "push_relay":
                center = r.plate.x + r.plate.w / 2
                move = max(-.5, min(1, (center - crate.body.position.x) * .035))
                return Input(move=move, grab=True)
            if self.phase == "approach":
                if x >= crate.body.position.x - crate.size[0] / 2 - 55:
                    self.phase = "jump"
                    return Input(move=1, jump=True)
                return Input(move=1)
            if self.phase == "jump":
                if x > crate.body.position.x + crate.size[0] / 2 + 14:
                    self.phase = "pull"
                return Input(move=1)
            return Input(move=-1, grab=True)
        if arch is PuzzleArchetype.SEESAW_LAUNCH:
            return self.seesaw.control(w)
        if arch is PuzzleArchetype.WATER_CRATE:
            crate = w.crates[stage.crate_index].body
            if self.phase == "approach":
                if abs(x - w.level.cover_switch[0]) < 10:
                    self.phase = "push"
                    return Input(action=True)
                return Input(move=1)
            if self.phase == "push":
                if w.cover_fraction < 1:
                    return Input()
                if crate.position.x > w.level.water.x + 45 and w.grounded:
                    self.phase = "board"
                    return Input(action=True, jump=True)
                return Input(move=1)
            if self.phase == "board":
                if w.support is crate:
                    self.phase = "float"
                return Input(move=1 if x < crate.position.x else 0)
            if self.phase == "float":
                if w.water_surface < stage.exit_y + 40 and w.grounded:
                    self.phase = "exit"
                    return Input(move=1, jump=True)
                return Input(move=max(-.2, min(.2, (crate.position.x - x) * .02)))
            return Input(move=1)
        if arch is PuzzleArchetype.ROPE_PENDULUM:
            anchor = w.level.rope[0]
            bank = next(r for r in w.level.terrain if r.x > anchor and r.y == stage.exit_y)
            tip = w.ropes[-1]
            if self.phase == "approach" and x > anchor - 270:
                self.phase = "wait"
            if self.phase == "wait":
                if tip.position.x < anchor - 65 and tip.velocity.x < 0:
                    self.phase = "catch"
                    return Input(jump=True)
                return Input()
            if self.phase == "catch":
                if w.grab_kind == "rope":
                    self.phase = "swing"
                    self.catch_distance = w.rope_distance
                return Input(move=1, grab=True)
            if self.phase == "swing":
                if x > bank.x - 70 and w.player.velocity.x > 0:
                    self.phase = "exit"
                    return Input(move=1, jump=True)
                return Input(move=1, grab=True,
                             climb=1 if w.rope_distance > self.catch_distance - 45 else 0)
            return Input(move=1)
        if arch is PuzzleArchetype.GRAVITY_MAZE:
            switch = w.level.switches[0]
            wall = next(r for r in w.level.terrain if r.h == 210)
            if self.phase == "approach":
                if x > switch[0] - 20:
                    self.phase = "rise"
                    return Input(action=True)
                return Input(move=1)
            if self.phase == "rise":
                if w.grounded and w.gravity == -1:
                    self.phase = "ceiling"
                return Input()
            if self.phase == "ceiling":
                if x > wall.x + wall.w + 85:
                    self.phase = "wait"
                return Input(move=1)
            if self.phase == "wait":
                if w.gravity == 1:
                    self.phase = "exit"
                return Input()
            return Input(move=1)
        if arch is PuzzleArchetype.MAGNET_STAIRS:
            rig = w.magnet
            small = rig.blocks[1]
            if self.phase == "approach":
                if x < rig.config.magnet_switch[0] - 4:
                    return Input(move=1)
                self.phase = "lift"
                return Input(action=True)
            if self.phase == "lift":
                if x < rig.config.gravity_switch[0] - 4:
                    return Input(move=1)
                self.phase = "catch"
                return Input(action=True)
            if self.phase == "catch":
                if 0 not in rig.captured:
                    return Input()
                self.phase = "cross"
                return Input(action=True)
            if self.phase == "cross":
                if x >= small.body.position.x - small.size[0] / 2 - 77 and w.grounded:
                    self.phase = "board"
                    return Input(move=1, jump=True)
                return Input(move=1)
            if self.phase == "board":
                if w.support is small.body:
                    self.phase = "bank"
                return Input(move=1 if x < small.body.position.x + 15 else 0)
            if self.phase == "bank":
                if x >= small.body.position.x + 20 and w.grounded:
                    self.phase = "exit"
                    return Input(move=1, jump=True)
                return Input(move=1)
            return Input(move=1)
        raise ValueError(f"Unsupported room mechanic: {arch}")


class RoomVerifier:
    MAX_STEPS = 14400  # Up to two minutes of fixed-step input, bounded.

    def simulate(self, room, *, interactions=True):
        world, pilot = ProceduralRoomWorld(room.seed, room), RoomPilot()
        trace = []
        stationary = 0
        for step in range(self.MAX_STEPS):
            # Demo supplies controls at 60 Hz and holds them for two 120 Hz
            # physics steps. Verify that actual application cadence, too.
            if step % 2 == 0:
                control = pilot.control(world)
                if not interactions:
                    control = replace(control, grab=False, action=False, climb=0)
                if world.room.stages[world.stage_index].archetype is blocked_archetype:
                    control = Input(move=1, jump=world.grounded)
            world.step(control, DT)
            stationary = stationary + 1 if world.player.velocity.length < 1 else 0
            if step % 120 == 0 or world.complete or world.dead:
                trace.append({"step": step, "stage": world.stage_index + 1,
                              "phase": pilot.phase,
                              "player": tuple(round(v, 2) for v in world.player.position),
                              "gates_solved": sum(r.solved for r in world.puzzle_runtimes.values()),
                              "mechanics": sorted(world.mechanics_used),
                              "complete": world.complete})
            if world.complete or world.dead:
                break
            if stationary > (1200 if interactions else 240):
                break
        return world, tuple(trace)

    def verify(self, room):
        world, trace = self.simulate(room)
        required = {
            PuzzleArchetype.WATER_CRATE: {"cover", "valve"},
            PuzzleArchetype.SEESAW_LAUNCH: {"seesaw"},
            PuzzleArchetype.ROPE_PENDULUM: {"rope"},
            PuzzleArchetype.GRAVITY_MAZE: {"gravity"},
            PuzzleArchetype.MAGNET_STAIRS: {"magnet", "capture"},
        }.get(room.puzzle_archetype, set())
        solved = (world.complete and not world.dead
                  and all(r.solved for r in world.puzzle_runtimes.values())
                  and required <= world.mechanics_used)
        if not solved:
            return False, trace
        # Remove the witness's interaction inputs; a gate cannot accept the
        # courier or an ungrabbed crate. Also probe a simple jump-forward route.
        bypass, _ = self.simulate(room, interactions=False)
        if bypass.complete:
            return False, trace
        if room.puzzle_archetype is not PuzzleArchetype.CRATE_PLATE:
            # Solving the surrounding relays cannot hide a bypassable primary
            # puzzle. Probe its jump-forward route with every other stage solved
            # normally, while omitting the primary mechanic's controls.
            bypass, _ = self.simulate(room, blocked_archetype=room.puzzle_archetype)
            if bypass.complete:
                return False, trace
        for hopping in (False, True):
            probe = ProceduralRoomWorld(room.seed, room)
            stuck = 0
            for _ in range(min(self.MAX_STEPS, 4800)):
                probe.step(Input(move=1, jump=hopping and probe.grounded), DT)
                blocked = any(abs(probe.player.position.x - (r.gate.x - 13)) < 5
                              and not r.solved for r in probe.puzzle_runtimes.values())
                stuck = stuck + 1 if blocked else 0
                if probe.complete or probe.dead:
                    break
                if stuck > 240:
                    break
            if probe.complete:
                return False, trace
        return True, trace


class ProceduralRoomGenerator:
    """Compose varied puzzle stages; reject duplicate geometry and puzzles.

    Mechanics are reusable building blocks, not an infinite catalog of rules.
    Exact layout, object/dependency and scenery signatures cannot repeat within
    a run. History stores only 32 rooms; the compact signature sets are retained.
    """
    MAX_ATTEMPTS = 64
    THEME_NAMES = ("Floodworks", "Overgrowth", "Ash Foundry", "Signal Ruins", "Deep Vault", "Night Spire")

    def __init__(self, seed):
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.rooms_generated = 0
        self.history = deque(maxlen=32)
        self._bag = []
        self.previous_template = None
        self._seen_layouts, self._seen_puzzles, self._seen_backgrounds = set(), set(), set()
        self.verifier = RoomVerifier()

    def next_room(self):
        if not self._bag:
            self._bag = list(range(6))
            self.rng.shuffle(self._bag)
            if self._bag[-1] == self.previous_template:
                self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
        primary = self._bag[-1]
        number = self.rooms_generated + 1
        seed = int(fingerprint([self.seed, number])[:16], 16)
        rng = random.Random(seed)
        for attempt in range(self.MAX_ATTEMPTS):
            room = self._candidate(number, seed, primary, rng)
            if (room.layout_signature in self._seen_layouts
                    or room.puzzle_signature in self._seen_puzzles
                    or room.background_signature in self._seen_backgrounds):
                continue
            valid, trace = self.verifier.verify(room)
            if not valid:
                continue
            room = replace(room, verified_solvable=True, solution_trace=trace)
            self.rooms_generated = number
            self.previous_template = self._bag.pop()
            self._seen_layouts.add(room.layout_signature)
            self._seen_puzzles.add(room.puzzle_signature)
            self._seen_backgrounds.add(room.background_signature)
            self.history.append(room)
            return room
        raise RuntimeError(f"No solvable {ARCHETYPES[primary].value} room after {self.MAX_ATTEMPTS} attempts")

    def _candidate(self, number, seed, primary, rng):
        # Mix the spatial sequence: relays may precede or follow the primary
        # mechanism. Different counts, push/pull goals and sizes change the task.
        count = rng.randint(2, min(4, 2 + number // 5))
        primary_slot = rng.randrange(count)
        kinds = [0] * count
        kinds[primary_slot] = primary
        terrain, crates, stages = [], [], []
        config = {}
        x = 0
        floor = 420 if primary == 3 else rng.randint(444, 456)
        initial_floor = floor
        for slot, kind in enumerate(kinds):
            if kind == 0:
                width = rng.randint(440, 580)
                size, mass = rng.randint(48, 55), rng.uniform(5.5, 6.8)
                pull = rng.choice((True, False))
                plate_width = rng.randint(90, 112)
                plate_x = x + (70 if pull else width - 230)
                crate_x = x + (width - 185 if pull else 115)
                plate = Rect(plate_x, floor - 4, plate_width, 8)
                gate = Rect(x + width - 65, floor - rng.randint(215, 255), 28, 260)
                # Seal meets the floor and is higher than a box-assisted jump.
                gate = replace(gate, h=floor - gate.y)
                stages.append(PuzzleStage(ARCHETYPES[0], x, x + width, floor, floor,
                                          len(crates), plate, gate,
                                          "pull_relay" if pull else "push_relay"))
                crates.append((crate_x, floor - size / 2, size, mass))
                terrain.append(Rect(x - (80 if slot == 0 else 0), floor,
                                    width + (80 if slot == 0 else 0), 200))
                x += width
                continue
            start, entry, crate_index = x, floor, len(crates)
            approach = rng.randint(300, 360) if kind == 2 else rng.randint(490, 560)
            if kind == 2:
                edge = x + approach
                pool_width = rng.randint(270, 288)
                exit_floor = floor - rng.randint(155, 165)
                size = rng.randint(70, 74)
                terrain.extend((Rect(x, floor, approach, 200),
                                Rect(edge, floor + 150, pool_width, 60),
                                Rect(edge + pool_width, exit_floor, rng.randint(200, 290), 400)))
                crates.append((edge - 80, floor - size / 2 - 3, size, rng.uniform(4.5, 5.5)))
                config.update(water=Rect(edge, floor + 40, pool_width, 110),
                              water_raise=rng.randint(169, 177), water_rate=rng.randint(19, 25),
                              valve=(edge - 30, floor - 35),
                              cover=Rect(edge, exit_floor + 40, pool_width, 16),
                              cover_switch=(edge - 125, floor - 35))
                x = terrain[-1].x + terrain[-1].w
                floor, variant = exit_floor, "water_lift"
            elif kind in (1, 3):
                edge = x + approach
                center = edge + (240 if kind == 1 else 225)
                bank_x = center + 250
                exit_floor = floor - rng.randint(117, 121)
                terrain.extend((Rect(x, floor, approach, 220),
                                Rect(bank_x, exit_floor, rng.randint(240, 340), 400)))
                if kind == 1:
                    config["rope"] = (center, floor - 360, 12, rng.uniform(27.8, 28.2))
                else:
                    config["seesaw"] = (center, floor + 20, rng.randint(436, 444))
                x = terrain[-1].x + terrain[-1].w
                floor, variant = exit_floor, "rope_crossing" if kind == 1 else "oscillating_bridge"
            elif kind == 4:
                width = rng.randint(1100, 1190)
                ceiling_y = floor - 350
                wall_x = x + rng.randint(590, 630)
                terrain.extend((Rect(x, floor, width, 200),
                                Rect(x + 220, ceiling_y, width - 300, 35),
                                Rect(wall_x, floor - 210, rng.randint(90, 130), 210)))
                config.update(switches=((x + 270, floor - 34),), gravity_duration=rng.uniform(5.5, 6.0),
                              saws=((wall_x + 30, floor - 33, 31, 140, .85),))
                x += width
                variant = "inverted_corridor"
            elif kind == 5:
                first_x, second_x = x + 620, x + 840
                bank_x = second_x + 110
                exit_floor = floor - rng.randint(138, 142)
                terrain.extend((Rect(x, floor, bank_x - x, 200),
                                Rect(bank_x, exit_floor, rng.randint(280, 360), 400)))
                crates.extend(((first_x, floor - 77, 150, 36), (second_x, floor - 42, 80, 20)))
                config["magnet"] = MagneticPuzzle((floor - rng.randint(228, 232), floor - 320),
                                                  (x + 245, floor - 34), (x + 365, floor - 34), floor,
                                                  (crate_index, crate_index + 1))
                x = terrain[-1].x + terrain[-1].w
                floor, variant = exit_floor, "magnetic_stair"
            stages.append(PuzzleStage(ARCHETYPES[kind], start, x, entry, floor, crate_index, variant=variant))
        # Left margin only when a non-relay is first.
        if kinds[0] != 0:
            first = terrain[0]
            terrain[0] = replace(first, x=-80, w=first.w + 80)
        level = Level(f"ROOM {number:02d} / THE CHANGING SIGNAL",
                      "Every crossing asks for a different answer.",
                      HINTS[stages[0].archetype],
                      int(x), (70, initial_floor - 22), (x - 30, floor - 22),
                      tuple(terrain), crates=tuple(crates), **config)
        # Visual randomness is independent of geometry attempts and consumed
        # by the renderer, not just attached as unused metadata.
        visual_rng = random.Random(seed ^ 0xBEC0)
        palette = visual_rng.randrange(6)
        theme = RoomTheme(self.THEME_NAMES[palette], palette,
                          tuple(visual_rng.randint(25, 80) for _ in range(3)),
                          visual_rng.uniform(.08, .35), visual_rng.choice(("dust", "mist", "embers", "leaves")),
                          visual_rng.choice(("dawn", "dusk", "night")), seed)
        layout_sig = fingerprint([asdict(r) for r in terrain])
        puzzle_sig = fingerprint([asdict(level)[key] for key in (
            "crates", "water", "water_raise", "seesaw", "rope", "magnet", "switches")]
                                 + [asdict(s) | {"archetype": s.archetype.value} for s in stages])
        room = type('ProceduralRoom', (), {
            'number': number, 'seed': seed, 'theme': theme, 'level': level,
            'stages': tuple(stages), 'template_index': primary,
            'layout_signature': layout_sig, 'puzzle_signature': puzzle_sig,
            'background_signature': fingerprint(asdict(theme)),
            'puzzle_name': " → ".join(s.variant.replace("_", " ").title() for s in stages),
            'puzzle_archetype': ARCHETYPES[primary],
            'verified_solvable': False,
            'solution_trace': ()
        })()
        return room


# Preserve the public entry names without preserving the old template shuffle.
EndlessRoomGenerator = ProceduralRoomGenerator
EndlessRoomWorld = ProceduralRoomWorld
GeneratedRoom = None
