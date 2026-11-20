"""Procedural puzzle archetypes for ECHO's endless mode.

Each archetype generates a multi-step physics/logic challenge with verified solvability.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
import random
from typing import Callable, Optional

from .levels import Level, Rect
from typing import TYPE_CHECKING

from .physics import (
    GRAVITY, JUMP_SPEED, MOVE_SPEED, PLAYER_SIZE, DT,
    Input, World
)
from .challenges import Challenge, ChallengeContext, ChallengeConfig, LightBarrier, LightSwitch

if TYPE_CHECKING:
    from .procedural import Platform, GenerationConfig, GenerationProfile, PlayerCapabilities


class PuzzleArchetype(Enum):
    CRATE_PLATE = "crate_plate"           # Push crate onto pressure plate to open gate
    WATER_CRATE = "water_crate"           # Open cover, raise water, float crate to exit
    SEESAW_LAUNCH = "seesaw_launch"       # Build momentum on seesaw to reach high platform
    GRAVITY_MAZE = "gravity_maze"         # Navigate vertical corridor with gravity flips
    MAGNET_STAIRS = "magnet_stairs"       # Stack crates with magnet to climb
    ROPE_PENDULUM = "rope_pendulum"       # Swing on rope to reach distant platform
    PRESSURE_CHAIN = "pressure_chain"     # Multiple plates, multiple crates, one gate
    LIGHT_REDIRECT = "light_redirect"     # Aim lantern beam through mirrors to sensor


@dataclass(frozen=True)
class PuzzleTemplate:
    """Parameterized template for a puzzle archetype."""
    archetype: PuzzleArchetype
    # Variable parameters (filled by generator)
    params: dict
    # Fixed constraints for validation
    constraints: dict
    # Expected solution steps (for verification)
    solution_steps: list[str]
    # Minimum platform requirements
    min_platform_width: float
    min_platform_height: float
    # Difficulty range
    min_difficulty: float
    max_difficulty: float


@dataclass(frozen=True)
class PuzzleInstance:
    """A fully instantiated, validated puzzle ready for runtime."""
    archetype: PuzzleArchetype
    platform_id: int
    generation_index: int
    difficulty: float
    # Physics objects to spawn
    crates: list[dict]           # {x, y, size, mass}
    plates: list[dict]           # {x, y, w, h, gate_id}
    gates: list[dict]            # {x, y, w, h, plate_ids}
    water: Optional[dict]        # {x, y, w, h, raise, rate, valve, cover, cover_switch}
    seesaw: Optional[dict]       # {x, y, length}
    magnet: Optional[dict]       # {ceilings, magnet_switch, gravity_switch, floor_y, crates}
    rope: Optional[dict]         # {x, y, count, length, anchor}
    gravity_switches: list[dict] # {x, y, duration}
    mirrors: list[dict]          # {x, y, angle, target_sensor}
    light_sensor: Optional[dict] # {x, y, radius, barrier_id}
    # Validation
    verified_solvable: bool
    solution_trace: list[dict]   # Simulated player states
    estimated_solve_time: float  # seconds


class PuzzleVerifier:
    """Verify puzzles using the game's actual fixed-step Pymunk simulation.

    The first supported archetype is deliberately narrow: the verifier only
    accepts a crate-plate puzzle if a scripted player must move the crate onto
    the plate, the seal opens, and the player can then pass it. A no-crate
    traversal is also simulated to reject trivial layouts.
    """

    MAX_STEPS = 1200

    def __init__(self, capabilities: PlayerCapabilities):
        self.capabilities = capabilities

    @staticmethod
    def _level(puzzle: PuzzleInstance, platform: Platform) -> Level:
        crate, plate, gate = puzzle.crates[0], puzzle.plates[0], puzzle.gates[0]
        size = float(crate["size"])
        spawn = (crate["x"] - size / 2 - 18, platform.y - PLAYER_SIZE[1] / 2)
        exit_point = (platform.right - 12, platform.y - PLAYER_SIZE[1] / 2)
        return Level(
            "Puzzle verification", "", "", int(platform.right + 200), spawn,
            exit_point, (Rect(platform.x, platform.y, platform.width, 180),),
            crates=((crate["x"], crate["y"], int(size), crate["mass"]),),
            gate=Rect(gate["x"], gate["y"], gate["w"], gate["h"]),
            plate=Rect(plate["x"], plate["y"], plate["w"], plate["h"]),
        )

    def _simulate_crate_plate(self, puzzle: PuzzleInstance, platform: Platform,
                              push_crate: bool) -> tuple[bool, list[dict]]:
        # Local subclass applies the generated puzzle's rule: only the crate
        # can activate the plate, and it must have been explicitly grabbed.
        # Activation latches the gate open so the player can leave the crate.
        class VerificationWorld(World):
            crate_was_grabbed = False

            def _gate(inner_self, dt):
                if inner_self.gate_body is None:
                    return
                prop = inner_self.crates[0]
                if inner_self.grabbed is prop.body:
                    inner_self.crate_was_grabbed = True
                plate_rect = inner_self.level.plate
                prop.shape.cache_bb()
                bb = prop.shape.bb
                size_x = prop.size[0]
                fully_on_plate = (
                    plate_rect.x + size_x / 2 <= prop.body.position.x
                    <= plate_rect.x + plate_rect.w - size_x / 2
                )
                resting = abs(bb.top - (plate_rect.y + plate_rect.h / 2)) <= 12
                if inner_self.crate_was_grabbed and fully_on_plate and resting:
                    inner_self.gate_open = True
                target = 1.0 if inner_self.gate_open else 0.0
                delta = max(-dt * 1.4, min(dt * 1.4, target - inner_self.gate_fraction))
                inner_self.gate_fraction += delta
                gate = inner_self.level.gate
                inner_self.gate_body.velocity = (0, -delta * (gate.h + 20) / dt)

        level = self._level(puzzle, platform)
        world = VerificationWorld(0, level=level)
        trace: list[dict] = []
        phase = "jump_over_crate"
        crate_start_x = world.crates[0].body.position.x
        for step in range(self.MAX_STEPS):
            crate = world.crates[0]
            plate = world.level.plate
            crate.shape.cache_bb()
            bb = crate.shape.bb
            crate_on_plate = (
                plate.x + crate.size[0] / 2 <= crate.body.position.x
                <= plate.x + plate.w - crate.size[0] / 2
                and abs(bb.top - (plate.y + plate.h / 2)) <= 12
            )
            if phase == "jump_over_crate":
                control = Input(move=1, jump=(step == 0))
                if world.player.position.x > crate.body.position.x + crate.size[0] / 2 + 14:
                    phase = "pull_crate"
            elif phase == "pull_crate":
                if crate_on_plate:
                    phase = "cross_open_gate"
                    control = Input(move=1)
                else:
                    control = Input(move=-1, grab=push_crate)
            else:
                control = Input(move=1)
            world.step(control, DT)
            crate = world.crates[0]
            if step % 24 == 0 or world.gate_open or world.complete:
                trace.append({
                    "step": step,
                    "phase": phase,
                    "player_x": round(world.player.position.x, 2),
                    "crate_x": round(crate.body.position.x, 2),
                    "gate_open": world.gate_open,
                    "gate_fraction": round(world.gate_fraction, 3),
                })
            if world.complete:
                moved = abs(crate.body.position.x - crate_start_x) >= 60
                return world.gate_open and world.crate_was_grabbed and moved, trace
        return False, trace

    def verify_crate_plate(self, puzzle: PuzzleInstance, platform: Platform) -> bool:
        return self._simulate_crate_plate(puzzle, platform, push_crate=True)[0]

    def verify(self, puzzle: PuzzleInstance, platform: Platform) -> tuple[bool, list[dict]]:
        """Verify puzzle solvability and reject layouts bypassable without solving."""
        if puzzle.archetype is not PuzzleArchetype.CRATE_PLATE:
            return False, []
        solved, trace = self._simulate_crate_plate(puzzle, platform, push_crate=True)
        if not solved:
            return False, trace
        bypassed, _ = self._simulate_crate_plate(puzzle, platform, push_crate=False)
        return not bypassed, trace


class PuzzleGenerator:
    """Generates procedural puzzles from archetypes."""
    
    def __init__(self, seed: int, capabilities: PlayerCapabilities, config: GenerationConfig):
        self.seed = seed
        self.rng = random.Random(seed ^ 0x7F3A1C)
        self.capabilities = capabilities
        self.config = config
        self.verifier = PuzzleVerifier(capabilities)
        self.next_object_id = 1
    
    # ==================== CRATE_PLATE ====================
    
    def generate_crate_plate(self, platform: Platform, profile: GenerationProfile,
                              context: ChallengeContext) -> Optional[PuzzleInstance]:
        """Generate a multi-step crate → pressure plate → gate puzzle."""
        crate_size = self.rng.uniform(48, 56)
        crate_mass = self.rng.uniform(5.5, 7.0)
        plate_width = crate_size + self.rng.uniform(38, 52)
        gate_width = 28.0
        gate_height = max(160.0, 2 * self.capabilities.max_jump_height + 28)

        # Put the plate behind the crate. A forward-only run pushes the crate
        # away from the goal; the player must jump past it, grab it from the
        # far side, and pull it back onto the plate.
        crate_x = platform.x + platform.width - self.rng.uniform(182, 198)
        gate_x = platform.right - 88
        plate_center = platform.x + self.rng.uniform(96, 112)
        plate_x = plate_center - plate_width / 2
        if (platform.width < 400
                or plate_x < platform.x + 28
                or plate_x + plate_width + 20 >= crate_x - crate_size / 2):
            return None
        crate_y = platform.y - crate_size / 2
        plate_y = platform.y - 4
        gate_y = platform.y - gate_height

        puzzle = PuzzleInstance(
            archetype=PuzzleArchetype.CRATE_PLATE,
            platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=profile.difficulty,
            crates=[{
                'x': crate_x,
                'y': crate_y,
                'size': crate_size,
                'mass': crate_mass
            }],
            plates=[{
                'x': plate_x,
                'y': plate_y,
                'w': plate_width,
                'h': 8,
                'gate_id': 1
            }],
            gates=[{
                'x': gate_x,
                'y': gate_y,
                'w': gate_width,
                'h': gate_height,
                'plate_ids': [1]
            }],
            water=None,
            seesaw=None,
            magnet=None,
            rope=None,
            gravity_switches=[],
            mirrors=[],
            light_sensor=None,
            verified_solvable=False,
            solution_trace=[],
            estimated_solve_time=0.0
        )
        
        solvable, trace = self.verifier.verify(puzzle, platform)
        if not solvable:
            return None
        solve_time = (trace[-1]["step"] * DT) if trace else 0.0
        return replace(puzzle, verified_solvable=True, solution_trace=trace,
                       estimated_solve_time=solve_time)
    
    # ==================== WATER_CRATE ====================
    
    def generate_water_crate(self, platform: Platform, profile: GenerationProfile,
                              context: ChallengeContext) -> Optional[PuzzleInstance]:
        """Generate: water pool + cover + valve + crate."""
        if platform.width < 500:
            return None
        
        pool_width = self.rng.uniform(250, 350)
        pool_x = platform.x + (platform.width - pool_width) / 2
        
        puzzle = PuzzleInstance(
            archetype=PuzzleArchetype.WATER_CRATE,
            platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=profile.difficulty,
            crates=[{
                'x': pool_x + 50,
                'y': platform.y - 72,
                'size': 72,
                'mass': 8
            }],
            plates=[],
            gates=[],
            water={
                'x': pool_x,
                'y': platform.y,
                'w': pool_width,
                'h': 120,
                'raise': 100,
                'rate': 25,
                'valve': {'x': pool_x - 80, 'y': platform.y - 22},
                'cover': {'x': pool_x, 'y': platform.y - 16, 'w': pool_width, 'h': 16},
                'cover_switch': {'x': pool_x - 150, 'y': platform.y - 22}
            },
            seesaw=None,
            magnet=None,
            rope=None,
            gravity_switches=[],
            mirrors=[],
            light_sensor=None,
            verified_solvable=False,
            solution_trace=[],
            estimated_solve_time=25.0
        )
        
        solvable, trace = self.verifier.verify(puzzle, platform)
        if not solvable:
            return None
        
        return replace(puzzle, verified_solvable=True, solution_trace=trace)
    
    # ==================== SEESAW_LAUNCH ====================
    
    def generate_seesaw_launch(self, platform: Platform, profile: GenerationProfile,
                                context: ChallengeContext) -> Optional[PuzzleInstance]:
        """Generate: seesaw that launches to higher platform."""
        if platform.width < 600:
            return None
        
        seesaw_x = platform.x + self.rng.uniform(100, platform.width - 500)
        target_height = self.rng.uniform(-120, -60)  # Above platform
        
        puzzle = PuzzleInstance(
            archetype=PuzzleArchetype.SEESAW_LAUNCH,
            platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=profile.difficulty,
            crates=[],
            plates=[],
            gates=[],
            water=None,
            seesaw={
                'x': seesaw_x,
                'y': platform.y,
                'length': 440,
                'target_delta_y': target_height
            },
            magnet=None,
            rope=None,
            gravity_switches=[],
            mirrors=[],
            light_sensor=None,
            verified_solvable=False,
            solution_trace=[],
            estimated_solve_time=20.0
        )
        
        solvable, trace = self.verifier.verify(puzzle, platform)
        if not solvable:
            return None
        
        return replace(puzzle, verified_solvable=True, solution_trace=trace)
    
    # ==================== GRAVITY_MAZE ====================
    
    def generate_gravity_maze(self, platform: Platform, profile: GenerationProfile,
                               context: ChallengeContext) -> Optional[PuzzleInstance]:
        """Generate: vertical corridor with gravity flip switches."""
        if profile.difficulty < 2.0:
            return None
        
        num_flips = min(3, int(profile.difficulty / 1.5))
        corridor_width = 200
        corridor_x = platform.x + (platform.width - corridor_width) / 2
        
        switches = []
        for i in range(num_flips):
            switches.append({
                'x': corridor_x + self.rng.uniform(30, corridor_width - 30),
                'y': platform.y - 100 - i * 180,
                'duration': 4.0 + i * 1.5
            })
        
        puzzle = PuzzleInstance(
            archetype=PuzzleArchetype.GRAVITY_MAZE,
            platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=profile.difficulty,
            crates=[],
            plates=[],
            gates=[],
            water=None,
            seesaw=None,
            magnet=None,
            rope=None,
            gravity_switches=switches,
            mirrors=[],
            light_sensor=None,
            verified_solvable=False,
            solution_trace=[],
            estimated_solve_time=30.0
        )
        
        solvable, trace = self.verifier.verify(puzzle, platform)
        if not solvable:
            return None
        
        return replace(puzzle, verified_solvable=True, solution_trace=trace)
    
    # ==================== MAGNET_STAIRS ====================
    
    def generate_magnet_stairs(self, platform: Platform, profile: GenerationProfile,
                                context: ChallengeContext) -> Optional[PuzzleInstance]:
        """Generate: magnet ceiling with crates to stack."""
        if profile.difficulty < 3.0 or platform.width < 500:
            return None
        
        puzzle = PuzzleInstance(
            archetype=PuzzleArchetype.MAGNET_STAIRS,
            platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=profile.difficulty,
            crates=[
                {'x': platform.x + 100, 'y': platform.y - 150, 'size': 150, 'mass': 70},
                {'x': platform.x + 300, 'y': platform.y - 80, 'size': 80, 'mass': 20}
            ],
            plates=[],
            gates=[],
            water=None,
            seesaw=None,
            magnet={
                'ceilings': (platform.y - 100, platform.y - 250),
                'magnet_switch': {'x': platform.x + 50, 'y': platform.y - 22},
                'gravity_switch': {'x': platform.x + 450, 'y': platform.y - 22},
                'floor_y': platform.y,
                'crates': [0, 1]  # indices into crates list
            },
            rope=None,
            gravity_switches=[],
            mirrors=[],
            light_sensor=None,
            verified_solvable=False,
            solution_trace=[],
            estimated_solve_time=40.0
        )
        
        solvable, trace = self.verifier.verify(puzzle, platform)
        if not solvable:
            return None
        
        return replace(puzzle, verified_solvable=True, solution_trace=trace)
    
    # ==================== ROPE_PENDULUM ====================
    
    def generate_rope_pendulum(self, platform: Platform, profile: GenerationProfile,
                                context: ChallengeContext) -> Optional[PuzzleInstance]:
        """Generate: rope swing to distant platform."""
        if platform.width < 400:
            return None
        
        puzzle = PuzzleInstance(
            archetype=PuzzleArchetype.ROPE_PENDULUM,
            platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=profile.difficulty,
            crates=[],
            plates=[],
            gates=[],
            water=None,
            seesaw=None,
            magnet=None,
            rope={
                'x': platform.right - 80,
                'y': platform.y - 200,
                'count': 12,
                'length': 28,
                'target_platform_x': platform.right + 300,
                'target_platform_y': platform.y - 100
            },
            gravity_switches=[],
            mirrors=[],
            light_sensor=None,
            verified_solvable=False,
            solution_trace=[],
            estimated_solve_time=15.0
        )
        
        solvable, trace = self.verifier.verify(puzzle, platform)
        if not solvable:
            return None
        
        return replace(puzzle, verified_solvable=True, solution_trace=trace)
    
    # ==================== PRESSURE_CHAIN ====================
    
    def generate_pressure_chain(self, platform: Platform, profile: GenerationProfile,
                                 context: ChallengeContext) -> Optional[PuzzleInstance]:
        """Generate: multiple plates + crates, one gate."""
        if platform.width < 800 or profile.difficulty < 2.5:
            return None
        
        num_plates = self.rng.randint(2, 3)
        crate_size = 54
        plate_spacing = platform.width / (num_plates + 1)
        
        crates = []
        plates = []
        for i in range(num_plates):
            plate_x = platform.x + (i + 1) * plate_spacing - 80
            plates.append({
                'x': plate_x, 'y': platform.y - 4, 'w': 160, 'h': 8, 'gate_id': 1
            })
            crates.append({
                'x': plate_x - 100, 'y': platform.y - crate_size,
                'size': crate_size, 'mass': 6
            })
        
        gate_x = platform.right - 40
        
        puzzle = PuzzleInstance(
            archetype=PuzzleArchetype.PRESSURE_CHAIN,
            platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=profile.difficulty,
            crates=crates,
            plates=plates,
            gates=[{'x': gate_x, 'y': platform.y - 200, 'w': 28, 'h': 200, 'plate_ids': [1,2,3]}],
            water=None,
            seesaw=None,
            magnet=None,
            rope=None,
            gravity_switches=[],
            mirrors=[],
            light_sensor=None,
            verified_solvable=False,
            solution_trace=[],
            estimated_solve_time=35.0
        )
        
        solvable, trace = self.verifier.verify(puzzle, platform)
        if not solvable:
            return None
        
        return replace(puzzle, verified_solvable=True, solution_trace=trace)
    
    # ==================== LIGHT_REDIRECT ====================
    
    def generate_light_redirect(self, platform: Platform, profile: GenerationProfile,
                                 context: ChallengeContext) -> Optional[PuzzleInstance]:
        """Generate: lantern beam + mirrors + sensor."""
        if profile.difficulty < 2.0:
            return None
        
        num_mirrors = self.rng.randint(2, 4)
        mirrors = []
        beam_y = platform.y - 80
        
        for i in range(num_mirrors):
            mirrors.append({
                'x': platform.x + 100 + i * 150,
                'y': beam_y,
                'angle': self.rng.uniform(-math.pi/4, math.pi/4),
                'target': i == num_mirrors - 1
            })
        
        sensor_x = platform.x + 100 + num_mirrors * 150
        
        puzzle = PuzzleInstance(
            archetype=PuzzleArchetype.LIGHT_REDIRECT,
            platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=profile.difficulty,
            crates=[],
            plates=[],
            gates=[],
            water=None,
            seesaw=None,
            magnet=None,
            rope=None,
            gravity_switches=[],
            mirrors=mirrors,
            light_sensor={
                'x': sensor_x, 'y': beam_y, 'radius': 30, 'barrier_id': 1
            },
            verified_solvable=False,
            solution_trace=[],
            estimated_solve_time=20.0
        )
        
        solvable, trace = self.verifier.verify(puzzle, platform)
        if not solvable:
            return None
        
        return replace(puzzle, verified_solvable=True, solution_trace=trace)
    
    # ==================== MAIN GENERATE ====================
    
    def generate(self, platform: Platform, profile: GenerationProfile,
                 context: ChallengeContext, archetype: Optional[PuzzleArchetype] = None
                 ) -> Optional[PuzzleInstance]:
        """The legacy streaming world supports only the verified crate slice.

        Full multi-mechanic room composition lives in echo_game.rooms, where
        generation, runtime and verification share the same complete geometry.
        """
        supported = {PuzzleArchetype.CRATE_PLATE: self.generate_crate_plate}
        if archetype is not None and archetype not in supported:
            return None
        if profile.difficulty < 1.0 or platform.width < 400:
            return None
        return self.generate_crate_plate(platform, profile, context)


# ==================== INTEGRATION HELPERS ====================

def puzzle_to_endless_world_objects(puzzle: PuzzleInstance) -> dict:
    """Convert PuzzleInstance to objects EndlessWorld can spawn."""
    objects = {
        'crates': [],
        'plates': [],
        'gates': [],
        'water': None,
        'seesaw': None,
        'magnet': None,
        'rope': None,
        'gravity_switches': [],
        'mirrors': [],
        'light_sensor': None
    }
    
    for crate in puzzle.crates:
        objects['crates'].append({
            'x': crate['x'], 'y': crate['y'],
            'size': crate['size'], 'mass': crate['mass']
        })
    
    for plate in puzzle.plates:
        objects['plates'].append({
            'x': plate['x'], 'y': plate['y'],
            'w': plate['w'], 'h': plate['h'],
            'gate_id': plate['gate_id']
        })
    
    for gate in puzzle.gates:
        objects['gates'].append({
            'x': gate['x'], 'y': gate['y'],
            'w': gate['w'], 'h': gate['h'],
            'plate_ids': gate['plate_ids']
        })
    
    if puzzle.water:
        objects['water'] = puzzle.water
    if puzzle.seesaw:
        objects['seesaw'] = puzzle.seesaw
    if puzzle.magnet:
        objects['magnet'] = puzzle.magnet
    if puzzle.rope:
        objects['rope'] = puzzle.rope
    
    objects['gravity_switches'] = puzzle.gravity_switches
    objects['mirrors'] = puzzle.mirrors
    objects['light_sensor'] = puzzle.light_sensor
    
    return objects


# Attach min_difficulty to generator methods for auto-selection
PuzzleGenerator.generate_crate_plate.min_difficulty = 1.0
PuzzleGenerator.generate_water_crate.min_difficulty = 2.0
PuzzleGenerator.generate_seesaw_launch.min_difficulty = 2.5
PuzzleGenerator.generate_gravity_maze.min_difficulty = 2.0
PuzzleGenerator.generate_magnet_stairs.min_difficulty = 3.0
PuzzleGenerator.generate_rope_pendulum.min_difficulty = 1.5
PuzzleGenerator.generate_pressure_chain.min_difficulty = 2.5
PuzzleGenerator.generate_light_redirect.min_difficulty = 2.0
