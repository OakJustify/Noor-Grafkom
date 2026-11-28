"""Procedural creature entity for gameplay.

Bridges prc-creature's generated morphology, utility AI, in-memory vocals,
vector renderer, lifecycle, social behaviour, and ecology into the existing
Monster physics/contact contract.
"""

from __future__ import annotations

import math
import os
import random
import sys

_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from src.procedural_generation.prc_creature import (
        ArchetypeType,
        BehaviorStateMachine,
        BodyPlanType,
        CreatureAudioGenerator,
        EnvironmentalContext,
        SizeClass,
        generate_creature,
    )
    from src.procedural_generation.prc_creature.archetype_definition import (
        ActivityCycle,
        SanityModifiers,
        SocialStructure,
    )
    from src.procedural_generation.prc_creature.vector_renderer import CreatureVector

    AVAILABLE = True
except Exception:  # noqa: BLE001 - optional module during partial checkouts
    AVAILABLE = False

from noor.entities.monster import Monster

# ── Hostility profiles ─────────────────────────────────────────────
ALWAYS_HOSTILE = frozenset({"predator", "void_walker", "parasitic"})
TERRITORIAL_HOSTILE = frozenset({"territorial", "guardian", "ambush"})
PASSIVE = frozenset({"prey", "scavenger", "curious"})
GOOD = frozenset({"gentle_light"})

PREDATOR_ARCHETYPES = frozenset({"predator", "void_walker", "ambush"})
PREY_ARCHETYPES = frozenset({"prey", "scavenger", "curious"})

CHASE_STATES = frozenset({
    "chase", "hunt", "stalk", "strike", "attack", "approach", "follow",
    "intercept", "lure", "drain", "attach", "corrupt", "threaten",
})
FLEE_STATES = frozenset({"flee", "hide", "retreat", "camouflage"})
STOP_STATES = frozenset({"idle", "rest", "feed", "wait", "camouflage"})
SCAVENGE_STATES = frozenset({"scavenge", "hoard", "steal"})
HERD_STATES = frozenset({"herd"})

SPAWN_TABLE = {
    1: ("prey", "scavenger", "curious", "territorial"),
    2: ("predator", "territorial", "scavenger", "curious"),
    3: ("predator", "ambush", "parasitic", "void_walker"),
    4: ("void_walker", "ambush", "parasitic", "predator"),
}

PLAN_AFFINITY = {
    "predator": ("quadruped", "serpentine"),
    "prey": ("biped", "quadruped"),
    "scavenger": ("hexapod", "biped"),
    "territorial": ("quadruped", "multi_limbed"),
    "curious": ("biped", "winged"),
    "parasitic": ("amorphous", "hexapod"),
    "guardian": ("quadruped", "multi_limbed"),
    "ambush": ("serpentine", "amorphous"),
    "void_walker": ("amorphous", "floating"),
    "gentle_light": ("floating",),
}

SIZE_TABLE = {
    1: ("small", "medium"),
    2: ("medium", "medium"),
    3: ("medium", "large"),
    4: ("large", "medium"),
}

# ── Helpers ─────────────────────────────────────────────────────────


def _enum_value(value):
    return value.value if hasattr(value, "value") else str(value)


def choose_archetype(stage, rng):
    return ArchetypeType(rng.choice(SPAWN_TABLE.get(int(stage), SPAWN_TABLE[1])))


def choose_body_plan(archetype, rng):
    name = _enum_value(archetype)
    return BodyPlanType(rng.choice(PLAN_AFFINITY[name]))


def choose_size(stage, rng):
    return SizeClass(rng.choice(SIZE_TABLE.get(int(stage), SIZE_TABLE[1])))


def _definition_height(definition):
    body = definition.body
    body_h = float(body.get("height", 40.0))
    leg_len = max(
        (
            sum(seg.length for seg in limb.segments)
            for limb in definition.limbs
            if limb.limb_type == "leg"
        ),
        default=0.0,
    )
    if _enum_value(definition.body_plan) in ("floating", "winged"):
        return max(36.0, body_h * 1.6)
    if _enum_value(definition.body_plan) == "serpentine":
        return max(36.0, float(body.get("width", 20.0)) * 2.2)
    return max(40.0, body_h + leg_len * 0.8)


def _facing_toward(self_x, target_x):
    return 1 if target_x >= self_x else -1


def _nearby_same_archetype(creature, others):
    same = []
    cx = creature.x + creature.width / 2
    cy = creature.y + creature.height / 2
    for o in others:
        if o is creature:
            continue
        if getattr(o, "archetype_name", "") != creature.archetype_name:
            continue
        ox = o.x + o.width / 2
        oy = o.y + o.height / 2
        if abs(ox - cx) < 600.0 and abs(oy - cy) < 400.0:
            same.append(o)
    return same


# ── ProceduralMonster ───────────────────────────────────────────────


class ProceduralMonster(Monster):
    """A generated creature with physics, utility AI, lifecycle and vector visuals."""

    def __init__(self, mid, definition, x, y, stage=1):
        super().__init__(mid, "PROC", x, y, stage)
        self.definition = definition
        self.archetype = definition.archetype
        self.body_plan = definition.body_plan
        self.plan_name = _enum_value(definition.body_plan)
        self.archetype_name = _enum_value(definition.archetype)
        self.flying = self.plan_name in ("floating", "winged")
        self.width = max(24.0, min(96.0, float(definition.body.get("length", 60.0)) * 0.55))
        self.height = _definition_height(definition)
        self.facing = 1
        self.spawn_x = float(x)
        self.spawn_y = float(y)
        self.territory_radius = float(
            definition.population_params.get("territory_size", 400.0)
        )
        self.passive = self.archetype_name in PASSIVE
        self.good = self.archetype_name in GOOD
        self.always_hostile = self.archetype_name in ALWAYS_HOSTILE
        self.territorial = self.archetype_name in TERRITORIAL_HOSTILE
        self.is_predator = self.archetype_name in PREDATOR_ARCHETYPES
        self.is_prey = self.archetype_name in PREY_ARCHETYPES

        self.behavior = BehaviorStateMachine(
            creature_id=mid,
            archetype=definition.archetype,
            base_drives=definition.base_drives,
            state_priorities=definition.state_priorities,
            sanity_mods=SanityModifiers(thresholds=definition.sanity_modifiers),
            social=SocialStructure(definition.social_structure),
            activity_cycle=ActivityCycle(definition.activity_cycle),
            seed=definition.seed,
        )
        self.state = self.behavior.current_state.value
        self.renderer = CreatureVector(definition)
        self.audio_gen = CreatureAudioGenerator(seed=definition.seed)
        self.vocal_cooldown = 0.0
        self.pending_vocal = None
        self._vocal_cache = {}

        self._walk_speed, self._run_speed = self._speeds()

        # -- lifecycle ---------------------------------------------------
        self.age = 0.0
        self.mortality = float(
            definition.population_params.get("mortality_rate", 0.005)
        )
        self.reproduction_rate = float(
            definition.population_params.get("reproduction_rate", 0.01)
        )
        self.alive = True
        self._reproduce_timer = 0.0
        self._footstep_timer = 0.0
        self.pending_footstep = None
        self._prev_on_ground = False
        self.footprint = definition.footprint_sound_profile

    # -- speeds ----------------------------------------------------------

    def _speeds(self):
        body_len = float(self.definition.body.get("length", 80.0))
        speeds = [
            value
            for gait in self.definition.gaits.values()
            for value in gait.speed_range
        ]
        if not speeds:
            return 60.0, 110.0
        walk = max(38.0, min(150.0, min(speeds) * body_len))
        run = max(walk * 1.25, min(240.0, max(speeds) * body_len))
        return walk, run

    # -- territory -------------------------------------------------------

    def _player_in_territory(self, player):
        dx = (player.x + player.width / 2) - self.spawn_x
        dy = (player.y + player.height / 2) - self.spawn_y
        return math.hypot(dx, dy) <= self.territory_radius

    # -- context builder -------------------------------------------------

    def _context(self, dt, player, sanity, world):
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        px = player.x + player.width / 2
        py = player.y + player.height / 2
        distance = math.hypot(px - cx, py - cy)

        nearby = []
        fragments = []
        time_of_day = 0.5
        if world is not None:
            for other in getattr(world, "monsters", ()):
                if other is self:
                    continue
                ox = other.x + other.width / 2
                oy = other.y + other.height / 2
                if abs(ox - cx) < 500.0 and abs(oy - cy) < 320.0:
                    nearby.append({
                        "pos": (ox, oy),
                        "archetype": getattr(other, "archetype", None),
                        "state": getattr(other, "state", ""),
                        "distance": math.hypot(ox - cx, oy - cy),
                    })
            collected = getattr(world, "collected_fragments", set())
            for fragment in getattr(world, "level", {}).get("fragments", ()):
                if fragment.get("id") in collected:
                    continue
                fx = fragment.get("x", 0.0)
                fy = fragment.get("y", 0.0)
                if abs(fx - cx) < 500.0 and abs(fy - cy) < 320.0:
                    fragments.append({
                        "pos": (fx, fy),
                        "type": fragment.get("type", "fragment"),
                        "distance": math.hypot(fx - cx, fy - cy),
                        "id": fragment.get("id", ""),
                    })
            clock = getattr(world, "clock", None)
            if clock is not None:
                time_of_day = (float(clock.active_time) / 60.0) % 1.0

        s_eff = float(getattr(sanity, "s_eff", 100.0)) if sanity else 100.0
        return EnvironmentalContext(
            dt=dt,
            time_of_day=time_of_day,
            player_pos=(px, py),
            player_distance=distance,
            player_sanity=s_eff,
            player_moving=abs(getattr(player, "vx", 0.0)) > 1.0
            or not getattr(player, "on_ground", True),
            player_crouching=bool(getattr(player, "covering", False)),
            nearby_creatures=nearby,
            nearby_fragments=fragments,
            territory_center=(self.spawn_x, self.spawn_y),
            current_sanity_stage=self.stage,
            world_sanity=s_eff,
        )

    # -- activity cycle modifier -----------------------------------------

    def _activity_multiplier(self, time_of_day):
        """Return 0.0-1.5 factor.  Nocturnal: high at night.  Diurnal: high at day."""
        cycle = _enum_value(self.behavior.activity_cycle)
        # time_of_day: 0.0=midnight, 0.25=sunrise, 0.5=noon, 0.75=sunset
        if cycle == "diurnal":
            # peak at noon (0.5), dip at midnight (0.0)
            return 0.5 + 1.0 * (1.0 - abs(time_of_day - 0.5) * 2.0)
        if cycle == "nocturnal":
            # peak at midnight (0.0 or 1.0)
            t = (time_of_day + 0.5) % 1.0
            return 0.5 + 1.0 * (1.0 - abs(t - 0.5) * 2.0)
        if cycle == "crepuscular":
            # peak at dawn/dusk (0.25 and 0.75)
            return 0.5 + 1.0 * (1.0 - min(abs(time_of_day - 0.25), abs(time_of_day - 0.75)) * 2.0)
        if cycle == "random":
            return 0.8
        # scripted / unknown: always active
        return 1.0

    # -- movement mode ---------------------------------------------------

    def _mode(self, player, state, ctx):
        if state in FLEE_STATES:
            return "away"
        if self.good:
            return "toward" if ctx.player_distance < 700.0 else "roam"
        if self.passive:
            if ctx.player_distance < 240.0 and state in FLEE_STATES:
                return "away"
            return "stop" if state in STOP_STATES else "roam"
        if self.always_hostile:
            return "toward" if ctx.player_distance < 1200.0 else "roam"
        if self.territorial:
            if self._player_in_territory(player):
                return "toward"
            if self.archetype_name == "ambush" and ctx.player_distance < 180.0:
                return "toward"
            return "roam"
        if state in CHASE_STATES:
            return "toward"
        if state in STOP_STATES:
            return "stop"
        return "roam"

    # -- main update -----------------------------------------------------

    def update(self, dt, player, sanity, platforms=(), world=None):
        self.age += dt
        self.vocal_cooldown = max(0.0, self.vocal_cooldown - dt)
        self.pending_vocal = None
        self._footstep_timer += dt

        # -- natural mortality --------------------------------------------
        if (
            self.mortality > 0
            and self.age > 120.0
            and random.Random(self.definition.seed + int(self.age * 1000)).random() < self.mortality * dt
        ):
            self.alive = False
            self.pending_vocal = "death"
            return

        ctx = self._context(dt, player, sanity, world)

        # Apply activity cycle to drive values so nocturnal creatures are
        # more active at night, diurnal at day, etc.
        activity = self._activity_multiplier(ctx.time_of_day)
        for drive in self.behavior.drives.values():
            if activity < 0.3 and drive.value < 0.3:
                drive.value = min(1.0, drive.value + drive.decay_rate * dt * 0.3)

        self.state = self.behavior.update(ctx).value
        mode = self._mode(player, self.state, ctx)

        # -- social grouping: herd toward nearest same-archetype -----------
        herd_influence = 0.0
        herd_cx = 0.0
        if self.state in HERD_STATES or self.behavior.social.value in ("herd", "pack", "swarm", "colony", "loose_group"):
            same = _nearby_same_archetype(self, getattr(world, "monsters", ()))
            if same:
                herd_cx = sum(o.x + o.width / 2 for o in same) / len(same)
                herd_influence = 0.3

        # -- creature-vs-creature interaction ------------------------------
        self._interact_with_creatures(dt, world)

        # -- fragment scavenging -------------------------------------------
        stolen = None
        if self.state in SCAVENGE_STATES and world is not None:
            stolen = self._try_steal_fragment(ctx, world)

        # -- vocal ---------------------------------------------------------
        if self.vocal_cooldown <= 0 and ctx.player_distance < 560 and mode != "stop":
            if (
                (mode == "toward" and self.archetype_name in ALWAYS_HOSTILE)
                or self.state == "attack"
                or self.state == "strike"
            ):
                self.pending_vocal = "aggressive"
            elif self.state in FLEE_STATES:
                self.pending_vocal = "pain"
            else:
                self.pending_vocal = "idle"
            self.vocal_cooldown = 4.0 + random.Random(self.definition.seed + int(self.age * 10)).uniform(0, 3.0)

        # -- movement ------------------------------------------------------
        px = player.x + player.width / 2
        cx = self.x + self.width / 2
        direction = 1 if px >= cx else -1

        if mode == "stop":
            self.vx = 0.0
        elif mode == "roam":
            self.vx = self._walk_speed * self.dir
            if herd_influence > 0:
                herd_dir = 1 if herd_cx >= cx else -1
                self.vx += (self._walk_speed * herd_dir - self.vx) * herd_influence
            if self.vx:
                self.facing = 1 if self.vx > 0 else -1
        else:
            speed = self._run_speed if mode == "toward" else self._run_speed * 0.9
            self.vx = direction * speed if mode == "toward" else -direction * speed
            self.facing = 1 if self.vx > 0 else -1

        if self.flying:
            if mode == "toward":
                target_y = player.y + player.height / 2 - self.height / 2
                self.vy = max(-self._run_speed, min(self._run_speed, (target_y - self.y) * 3.0))
            else:
                self.vy = 0.0

        self._apply_physics(dt, platforms)

        # -- footstep audio ------------------------------------------------
        if self.on_ground and abs(self.vx) > 2.0 and self._footstep_timer > 0.35:
            if self.footprint != "silent":
                self.pending_footstep = self.footprint
            self._footstep_timer = 0.0
        elif not self.on_ground or abs(self.vx) <= 2.0:
            self._footstep_timer = min(self._footstep_timer, 0.30)

        # -- renderer pose -------------------------------------------------
        anchor_x = self.x + self.width / 2
        anchor_y = self.y + self.height / 2 if self.flying else self.y + self.height
        self.renderer.update(
            dt,
            anchor_x,
            anchor_y,
            vx=self.vx,
            vy=self.vy,
            state=self.state,
            on_ground=self.on_ground,
            facing=self.facing,
            reduce_motion=bool(getattr(world, "reduce_motion", False)),
        )

        return stolen

    # -- creature-vs-creature ---------------------------------------------

    def _interact_with_creatures(self, dt, world):
        """Predators hunt prey. Territorial creatures fight each other."""
        if world is None:
            return
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        for other in list(getattr(world, "monsters", ())):
            if other is self:
                continue
            if not isinstance(other, ProceduralMonster):
                continue
            if not getattr(other, "alive", True):
                continue
            ox = other.x + other.width / 2
            oy = other.y + other.height / 2
            dist = math.hypot(ox - cx, oy - cy)

            # Predator attacks prey
            if self.is_predator and other.is_prey and dist < 80.0:
                other.alive = False
                other.pending_vocal = "death"
            # Territorial fights same archetype
            elif (
                self.territorial
                and other.territorial
                and self.archetype_name == other.archetype_name
                and dist < 60.0
            ):
                loser = self if random.Random(int(self.age * 1000)).random() < 0.5 else other
                loser.alive = False
                loser.pending_vocal = "death"

    # -- fragment scavenging ----------------------------------------------

    def _try_steal_fragment(self, ctx, world):
        """Scavengers can steal nearby uncollected fragments."""
        if len(ctx.nearby_fragments) == 0:
            return None
        frag = ctx.nearby_fragments[0]
        fid = frag.get("id", "")
        if not fid:
            return None
        frag_x, frag_y = frag["pos"]
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        if math.hypot(frag_x - cx, frag_y - cy) < 60.0:
            collected = getattr(world, "collected_fragments", set())
            collected.add(fid)
            self.vocal_cooldown = 0.0
            self.pending_vocal = "alert"
            return fid
        return None

    # -- reproduction -----------------------------------------------------

    def should_reproduce(self, dt, world):
        """Return True when conditions are right to spawn an offspring."""
        if self.reproduction_rate <= 0:
            return False
        self._reproduce_timer += dt
        if self._reproduce_timer < 60.0:
            return False
        # Only social/herd/pack creatures reproduce in-game
        social = _enum_value(self.behavior.social)
        if social in ("solitary", "scripted"):
            return False
        # Need at least one nearby same-archetype
        same = _nearby_same_archetype(self, getattr(world, "monsters", ()))
        if not same:
            return False
        rng = random.Random(self.definition.seed + int(self._reproduce_timer))
        if rng.random() < self.reproduction_rate * 0.5:
            self._reproduce_timer = 0.0
            return True
        return False

    # -- contact ----------------------------------------------------------

    def contact_damage(self, player):
        if self.passive or self.good:
            return False
        if self.archetype_name == "ambush":
            return abs(player.x - self.x) < 170.0
        if self.territorial:
            return self._player_in_territory(player)
        return True

    def contact_heal(self, player):
        """Good creatures heal the player on contact."""
        if not self.good:
            return 0.0
        if self.state in ("heal", "sing", "guide"):
            return 12.0
        if abs(player.x - self.x) < 120.0:
            return 5.0
        return 0.0

    # -- audio ------------------------------------------------------------

    def vocal(self, call_type):
        if call_type not in self._vocal_cache:
            self._vocal_cache[call_type] = self.audio_gen.synthesize_call(
                call_type, self.definition.vocal, seed=self.definition.seed
            )
        return self._vocal_cache[call_type]

    # -- draw -------------------------------------------------------------

    def draw(self, surface, camera):
        self.renderer.draw(surface, (-camera.x, -camera.y))


# ── Module helpers ────────────────────────────────────────────────────


def spawn_definition(archetype, stage, seed, body_plan=None, size_class=None):
    return generate_creature(
        archetype=archetype,
        body_plan=body_plan,
        size_class=size_class,
        stage=stage,
        seed=seed,
    )


def random_archetype(stage, rng: random.Random):
    return choose_archetype(stage, rng)
