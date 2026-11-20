"""Real multi-step procedural puzzle generation and runtime tests."""

from echo_game.challenges import ChallengeContext
from echo_game.physics import DT, Input, PlayerCapabilities, World
from echo_game.procedural import (
    EndlessWorld,
    GenerationConfig,
    GenerationProfile,
    Platform,
)
from echo_game.puzzle_archetypes import PuzzleArchetype, PuzzleGenerator


def make_puzzle(seed=42, width=420):
    capabilities = PlayerCapabilities.from_controller()
    platform = Platform(17, 800.0, 430.0, width, 28.0, 3, 1.0)
    context = ChallengeContext(1.0, capabilities=capabilities)
    generator = PuzzleGenerator(seed, capabilities, GenerationConfig())
    puzzle = generator.generate(
        platform,
        GenerationProfile.create(1.0),
        context,
        PuzzleArchetype.CRATE_PLATE,
    )
    return generator, platform, context, puzzle


def test_crate_plate_generator_verifies_a_nontrivial_solution():
    generator, platform, _, puzzle = make_puzzle()
    assert puzzle is not None
    assert puzzle.verified_solvable
    assert puzzle.estimated_solve_time > 1.0
    assert len(puzzle.solution_trace) > 3
    assert puzzle.archetype is PuzzleArchetype.CRATE_PLATE

    # The same layout must not be solvable by simply walking/jumping through
    # without ever grabbing the crate.
    bypassed, _ = generator.verifier._simulate_crate_plate(
        puzzle, platform, push_crate=False)
    assert not bypassed


def test_crate_plate_generation_is_seed_deterministic():
    first = make_puzzle(seed=901)[3]
    replay = make_puzzle(seed=901)[3]
    other = make_puzzle(seed=902)[3]
    assert first is not None and replay is not None and other is not None
    assert first == replay
    assert first.crates != other.crates or first.plates != other.plates


def test_crate_plate_puzzle_works_in_endless_physics_and_cleans_up():
    world = EndlessWorld(
        5,
        GenerationConfig(puzzle_density=0, challenge_enabled=False),
    )
    platform = Platform(700, 5000.0, 460.0, 420.0, 28.0, 10, 1.0)
    capabilities = world.generator.capabilities
    puzzle = world.generator.puzzle_archetype_generator.generate(
        platform,
        GenerationProfile.create(1.0),
        ChallengeContext(1.0, capabilities=capabilities),
        PuzzleArchetype.CRATE_PLATE,
    )
    assert puzzle is not None

    platform_body, platform_shape = world._static_rect(platform.rect)
    world._platform_geometry[platform.id] = (platform_body, platform_shape)
    world.generated_platforms.append(platform)
    world._spawn_puzzle(puzzle)
    runtime = world.puzzle_runtimes[platform.id]
    world.player.position = (
        puzzle.crates[0]["x"] - puzzle.crates[0]["size"] / 2 - 18,
        platform.y - 22,
    )
    world.player.velocity = (0, 0)
    world.grounded = True

    # Repeat the verifier's solution: jump past the crate, pull it left, then
    # release it and move through the gate. Call the shared physics step only
    # so unrelated streaming generation does not affect this unit test.
    phase = "jump_over_crate"
    for step in range(900):
        crate = runtime.crate
        if phase == "jump_over_crate":
            control = Input(move=1, jump=(step == 0))
            if world.player.position.x > crate.body.position.x + crate.size[0] / 2 + 14:
                phase = "pull_crate"
        elif phase == "pull_crate":
            if world._puzzle_crate_on_plate(runtime):
                phase = "cross_gate"
                control = Input(move=1)
            else:
                control = Input(move=-1, grab=True)
        else:
            control = Input(move=1)

        World.step(world, control, DT)
        world._update_puzzles(DT)
        if runtime.solved and runtime.gate_fraction >= 1.0:
            break

    assert runtime.crate_was_grabbed
    assert runtime.solved
    assert runtime.gate_fraction == 1.0
    assert runtime.gate_body.position.y < runtime.gate.y - runtime.gate.h / 2

    # Streaming cleanup releases every physics object owned by the platform.
    world.player.position = (
        platform.right + world.config.cleanup_distance + 100,
        platform.y - 22,
    )
    world.support = None
    world._cleanup()
    assert platform.id not in world.puzzle_runtimes
    assert runtime.crate not in world.crates
    assert runtime.gate_body not in world.space.bodies
    assert runtime.plate_body not in world.space.bodies
