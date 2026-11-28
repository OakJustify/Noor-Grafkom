"""Procedural creature entity for gameplay.

Bridges prc-creature's generated morphology, utility AI, in-memory vocals and
vector renderer into the existing Monster physics/contact contract.
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

# Hostility profiles.  "Passive" creatures never damage the player; "good" ones
# actively approach and restore light instead.
ALWAYS_HOSTILE = frozenset({"predator", "void_walker", "parasitic"})
TERRITORIAL_HOSTILE = frozenset({"territorial", "guardian", "ambush"})
PASSIVE = frozenset({"prey", "scavenger", "curious"})
GOOD = frozenset({"gentle_light"})

CHASE_STATES = frozenset({
    "chase", "hunt", "stalk", "strike", "attack", "approach", "follow",
    "intercept", "lure", "drain", "attach", "corrupt", "threaten",
})
FLEE_STATES = frozenset({"flee", "hide", "retreat", "camouflage"})
STOP_STATES = frozenset({"idle", "rest", "feed", "wait", "camouflage"})

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
    """Collision height: body plus most of the leg length."""
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


class ProceduralMonster(Monster):
    """A generated creature with physics, utility AI and vector visuals."""

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

    def _player_in_territory(self, player):
        dx = (player.x + player.width / 2) - self.spawn_x
        dy = (player.y + player.height / 2) - self.spawn_y
        return math.hypot(dx, dy) <= self.territory_radius

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

    def update(self, dt, player, sanity, platforms=(), world=None):
        self.vocal_cooldown = max(0.0, self.vocal_cooldown - dt)
        self.pending_vocal = None
        ctx = self._context(dt, player, sanity, world)
        self.state = self.behavior.update(ctx).value
        mode = self._mode(player, self.state, ctx)
        if self.vocal_cooldown <= 0 and ctx.player_distance < 560 and mode != "stop":
            self.pending_vocal = "aggressive" if mode == "toward" else "idle"
            self.vocal_cooldown = 6.0

        px = player.x + player.width / 2
        cx = self.x + self.width / 2
        direction = 1 if px >= cx else -1

        if mode == "stop":
            self.vx = 0.0
        elif mode == "roam":
            self.vx = self._walk_speed * self.dir
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

    def contact_damage(self, player):
        if self.passive or self.good:
            return False
        if self.archetype_name == "ambush":
            return abs(player.x - self.x) < 170.0
        if self.territorial:
            return self._player_in_territory(player)
        return True

    def vocal(self, call_type):
        if call_type not in self._vocal_cache:
            self._vocal_cache[call_type] = self.audio_gen.synthesize_call(
                call_type, self.definition.vocal, seed=self.definition.seed
            )
        return self._vocal_cache[call_type]

    def draw(self, surface, camera):
        self.renderer.draw(surface, (-camera.x, -camera.y))


def spawn_definition(archetype, stage, seed, body_plan=None, size_class=None):
    """Generate a deterministic definition for one spawned creature."""
    return generate_creature(
        archetype=archetype,
        body_plan=body_plan,
        size_class=size_class,
        stage=stage,
        seed=seed,
    )


def random_archetype(stage, rng: random.Random):
    return choose_archetype(stage, rng)
