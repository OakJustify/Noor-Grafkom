"""Observe the existing pipeline without changing generation or gameplay rules.

Run from the project root:
    .venv-echo/bin/python -m scripts.audit_generation

Temporary method wrappers delegate to the original implementations exactly
once. RNG wrappers record existing draws, never request additional draws.
They are installed only by this standalone command, not by the game launcher.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import time
from unittest.mock import patch

from echo_game.challenges import PuzzleComposer, PuzzleGenerator, PuzzleValidator
from echo_game.challenges import ChallengeContext
from echo_game.physics import Input
from echo_game.procedural import (
    DifficultyManager, EndlessPilot, EndlessWorld, Platform, ProceduralGenerator,
)


ROOT = Path(__file__).resolve().parent.parent
ENVIRONMENT_TYPES = ("tree", "wood", "bamboo", "grass", "dirt_block", "rock")
LOGICAL_TYPES = ("platform", "saw", "switches", "barriers", "shadows", "enemies", "caches", "environment")


@contextmanager
def record_random(rng):
    """Observe draws made by the implementation, including sampled positions."""
    draws = {"random": [], "uniform": []}
    original_random, original_uniform = rng.random, rng.uniform

    def random_draw():
        value = original_random()
        draws["random"].append(value)
        return value

    def uniform_draw(low, high):
        value = original_uniform(low, high)
        draws["uniform"].append({"low": low, "high": high, "value": value})
        return value

    with patch.object(rng, "random", random_draw), patch.object(rng, "uniform", uniform_draw):
        yield draws


def object_counts(world):
    counts = Counter(platform=len(world.generated_platforms), saw=len(world.generated_hazards))
    counts["environment"] = len(world.environment_objects)
    for challenge in world.challenges:
        for name in ("switches", "barriers", "shadows", "enemies", "caches"):
            counts[name] += len(getattr(challenge, name))
    counts["active_barrier_shapes"] = len(world.barrier_geometry)
    counts["pymunk_shapes"] = len(world.space.shapes)
    return dict(counts)


def registration_checks(world):
    """Logical damage/interaction objects intentionally are not solid shapes."""
    problems = []
    live = {p.id for p in world.generated_platforms}
    if set(world._platform_geometry) != live:
        problems.append("platform registry differs from generated platforms")
    for platform in world.generated_platforms:
        body, shape = world._platform_geometry[platform.id]
        if body not in world.space.bodies or shape not in world.space.shapes:
            problems.append(f"platform {platform.id} missing Pymunk geometry")
        if not body.position.get_distance((platform.x + platform.width / 2,
                                           platform.y + platform.height / 2)) < 1e-6:
            problems.append(f"platform {platform.id} geometry coordinate mismatch")
    if len(world.terrain_rects()) != len(live) + len(world.level.terrain):
        problems.append("terrain renderer input count mismatch")
    if len(world.saw_positions()) != len(world.generated_hazards):
        problems.append("saw renderer/collision input count mismatch")
    for hazard in world.generated_hazards:
        if hazard.platform_id not in live:
            problems.append(f"saw {hazard.id} has no live owner")
    for item in world.environment_objects:
        if item.platform_id not in live:
            problems.append(f"environment {item.id} has no live owner")
    if len({item.id for item in world.environment_objects}) != len(world.environment_objects):
        problems.append("duplicate environment IDs")
    for challenge in world.challenges:
        if challenge.platform_id not in live:
            problems.append(f"challenge {challenge.id} has no live owner")
        for barrier in challenge.barriers:
            geometry = world.barrier_geometry.get(barrier.id)
            if geometry is None and barrier.switch_id not in world.active_switches:
                problems.append(f"barrier {barrier.id} missing before switch activation")
            if geometry and any(item not in collection for item, collection in
                                zip(geometry, (world.space.bodies, world.space.shapes))):
                problems.append(f"barrier {barrier.id} geometry not registered")
        for enemy in challenge.enemies:
            if enemy.id not in world.enemy_states:
                problems.append(f"enemy {enemy.id} missing runtime state")
    return problems


def composition_failure(definition, platform, config, draws):
    """Name the exact default-composer branch that returned None (no RNG use)."""
    kind, width = definition.kind, platform.width
    if kind == "shadow_run":
        if width - 2 * config.shadow_margin - min(150.0, width * 0.5) < 0:
            return "shadow span plus two margins exceeds platform width"
    if kind in ("light_gate", "dark_gate", "lit_gauntlet"):
        if width - config.barrier_offset - config.switch_gap - config.switch_margin < 24:
            return "gate switch sampling interval is shorter than 24 px"
        if draws["uniform"]:
            switch_x = draws["uniform"][0]["value"]
            if kind == "dark_gate" and (
                switch_x - config.switch_gap * 0.55 - platform.x - config.shadow_margin < 62
            ):
                return "sampled switch leaves shadow span shorter than 62 px"
            if kind == "lit_gauntlet" and (
                platform.right - config.barrier_offset - config.enemy_margin
                - switch_x - config.enemy_patrol_margin < 78
            ):
                return "sampled switch leaves enemy patrol shorter than 78 px"
    return "composer returned None (no more specific branch identified)"


class GenerationTrace:
    """Scoped generation/spawn/cleanup tracing; no per-frame records."""

    def __init__(self, run):
        self.run = run
        self.events = []
        self.row = None
        self.request = None
        self.last_generation = None
        self.cap_hits = 0

    def __enter__(self):
        self.stack = ExitStack()

        def hook(cls, name, observe):
            original = getattr(cls, name)

            def wrapper(instance, *args, **kwargs):
                return observe(original, instance, *args, **kwargs)

            self.stack.enter_context(patch.object(cls, name, wrapper))

        def generation(original, generator, distance, context=None):
            profile = generator.profile(distance)
            row = {
                "event": "generation", "run": self.run, "seed": generator.seed,
                "segment": generator.index + 1, "player_progress": distance,
                "profile": asdict(profile), "previous_platform": asdict(generator.previous),
                "recovery": generator.index % profile.recovery_spacing == 0,
                "platform_candidates": [], "obstacle_requests": [],
                "challenge_requests": [], "segment_validations": [],
            }
            self.row = row
            try:
                result = original(generator, distance, context)
                row["accepted_segment"] = asdict(result)
                row["environment"] = generator.environment_generator.last_report
                row["challenge_call_status"] = (
                    "called" if row["challenge_requests"] else
                    "recovery segment" if row["recovery"] else
                    "disabled" if not generator.config.challenge_enabled else
                    "below configured challenge width" if result.platform.width < generator.config.challenge_min_width else
                    "platform fallback before challenge selection"
                )
                self.events.append(row)
                self.last_generation = row
                return result
            finally:
                self.row = None

        def candidate(original, generator, previous, profile, recovery):
            with record_random(generator.rng) as draws:
                result = original(generator, previous, profile, recovery)
            if self.row is not None:
                self.row["platform_candidates"].append({
                    "platform": asdict(result), "draws": draws,
                    "at_vertical_bound": result.y in (generator.config.vertical_min,
                                                       generator.config.vertical_max),
                })
            return result

        def platform_validation(original, generator, previous, candidate, profile=None):
            result = original(generator, previous, candidate, profile)
            if self.row is not None:
                self.row["platform_candidates"][-1]["validation"] = {
                    "valid": result[0], "reasons": result[1],
                }
            return result

        def hazards(original, generator, platform, profile, context=None, challenge=None):
            with record_random(generator.hazard_rng) as draws:
                result = original(generator, platform, profile, context, challenge)
            reason = "accepted" if result else "unknown empty result"
            cfg = generator.config
            roll = draws["random"][0] if draws["random"] else None
            if context and (not context.fair_for_damage() or context.lantern_fraction <= .20):
                reason = "resource fairness skipped"
            elif profile.challenge_damage_cap < 1 or (challenge and challenge.damage_cost):
                reason = "damaging challenge reserved obstacle budget"
            elif platform.width < cfg.hazard_min_platform_width:
                reason = "platform below hazard_min_platform_width"
            elif roll is not None and roll >= profile.hazard_probability:
                reason = "hazard probability roll skipped"
            elif not result and draws["uniform"]:
                radius = draws["uniform"][0]["value"]
                reason = ("landing/takeoff clearances leave less than 8 px for saw center"
                          if platform.width - cfg.hazard_left_clearance - cfg.hazard_right_clearance - 2 * radius < 8
                          else "reserved challenge footprints leave no safe saw slot")
            if self.row is not None:
                self.row["obstacle_requests"].append({
                    "type": "saw", "platform_id": platform.id, "draws": draws,
                    "accepted": [asdict(item) for item in result], "outcome": reason,
                    "placement_rejection": None if result or reason.endswith("skipped") else {
                        "world_interval": [platform.x + cfg.hazard_left_clearance
                                           + (draws["uniform"][0]["value"] if draws["uniform"] else 0),
                                           platform.right - cfg.hazard_right_clearance
                                           - (draws["uniform"][0]["value"] if draws["uniform"] else 0)],
                        "reason": reason,
                    },
                })
            return result

        def challenge_generation(original, generator, platform, profile, context,
                                 previous=None, hazards=()):
            request = {
                "platform_id": platform.id, "context": asdict(context),
                "chance": generator._chance(profile, context),
                "eligibility": [
                    {"kind": definition.kind, "reasons":
                     (["platform below composed minimum width"]
                      if platform.width < generator.composer.minimum_width(definition) else [])
                     + (["enemy type disabled"] if "enemy" in definition.tags and "sentry" not in context.enemy_types else [])
                     + (["damage budget exceeded"] if definition.damage > context.damage_cap else [])
                     + generator.rules.reasons(definition, context)}
                    for definition in generator.catalog.definitions
                ], "candidates": [],
            }
            self.request = request
            before = generator.stats.as_dict()
            try:
                with record_random(generator.rng) as draws:
                    result = original(generator, platform, profile, context, previous, hazards)
                request["probability_roll"] = draws["random"][0] if draws["random"] else None
                request["category_rolls"] = draws["random"][:3]
                request["selection"] = generator.last_selection
                request["stats_delta"] = {
                    key: getattr(generator.stats, key) - before[key]
                    for key in ("requests", "generated", "skipped", "fallbacks", "rejections")
                }
                request["accepted"] = asdict(result) if result else None
                request["outcome"] = (
                    "accepted" if result else
                    "safe no-challenge fallback" if request["stats_delta"]["fallbacks"] else
                    "no compatible requested category"
                )
                if self.row is not None:
                    self.row["challenge_requests"].append(request)
                return result
            finally:
                self.request = None

        def compose(original, composer, definition, platform, difficulty, rng, start_id):
            with record_random(rng) as draws:
                result = original(composer, definition, platform, difficulty, rng, start_id)
            if self.request is not None:
                self.request["candidates"].append({
                    "kind": definition.kind, "draws": draws,
                    "composed": asdict(result[0]) if result[0] else None,
                    "reasons": [] if result[0] else [
                        composition_failure(definition, platform, composer.config, draws)],
                })
            return result

        def validate_challenge(original, validator, challenge, platform, context, hazards=()):
            result = original(validator, challenge, platform, context, hazards)
            if self.request is not None:
                self.request["candidates"][-1]["reasons"] = list(result)
            return result

        def validate_segment(original, generator, segment, context=None):
            result = original(generator, segment, context)
            if self.row is not None:
                self.row["segment_validations"].append({
                    "has_challenge": segment.challenge is not None,
                    "valid": result[0], "reasons": result[1],
                })
            return result

        def spawn(original, world, segment):
            before = object_counts(world)
            result = original(world, segment)
            after = object_counts(world)
            if self.last_generation is not None:
                self.last_generation["spawn"] = {
                    "counts_before": before, "counts_after": after,
                    "added": {key: after.get(key, 0) - before.get(key, 0) for key in after},
                    "spawned_object_count": sum(after.get(key, 0) - before.get(key, 0) for key in LOGICAL_TYPES),
                    "registration_problems": registration_checks(world),
                }
            return result

        def cleanup(original, world):
            before = object_counts(world)
            old_ids = {platform.id for platform in world.generated_platforms}
            result = original(world)
            removed_ids = sorted(old_ids - {platform.id for platform in world.generated_platforms})
            if removed_ids:
                after = object_counts(world)
                self.events.append({
                    "event": "cleanup", "run": self.run, "seed": world.seed,
                    "segment": world.generator.index, "player_progress": world.distance,
                    "removed_platform_ids": removed_ids,
                    "removed": {key: before.get(key, 0) - after.get(key, 0) for key in before},
                    "cleaned_object_count": sum(before.get(key, 0) - after.get(key, 0) for key in LOGICAL_TYPES),
                    "active_counts": after, "registration_problems": registration_checks(world),
                })
            return result

        def activate(original, world, switch):
            already_active = switch.id in world.active_switches
            result = original(world, switch)
            if not already_active and switch.id in world.active_switches:
                self.events.append({
                    "event": "switch_activation", "run": self.run, "seed": world.seed,
                    "segment": world.generator.index, "player_progress": world.distance,
                    "switch_id": switch.id, "barrier_id": switch.barrier_id,
                    "player_position": list(world.player.position),
                    "barrier_removed": switch.barrier_id not in world.barrier_geometry,
                })
            return result

        def ensure(original, world):
            result = original(world)
            if world.generated_until < world.player.position.x + world.config.generation_distance:
                self.cap_hits += 1
            return result

        for cls, name, observer in (
            (ProceduralGenerator, "generate_next", generation),
            (ProceduralGenerator, "_candidate", candidate),
            (ProceduralGenerator, "validate_platform", platform_validation),
            (ProceduralGenerator, "_hazards", hazards),
            (ProceduralGenerator, "validate_segment", validate_segment),
            (PuzzleGenerator, "generate", challenge_generation),
            (PuzzleComposer, "compose", compose),
            (PuzzleValidator, "validate", validate_challenge),
            (EndlessWorld, "_spawn_segment", spawn),
            (EndlessWorld, "_cleanup", cleanup),
            (EndlessWorld, "activate_switch", activate),
            (EndlessWorld, "_ensure_generated", ensure),
        ):
            hook(cls, name, observer)
        return self

    def __exit__(self, *error):
        return self.stack.__exit__(*error)


def summarize(events):
    generations = [event for event in events if event["event"] == "generation"]
    cleanups = [event for event in events if event["event"] == "cleanup"]
    kinds, reasons, saw_outcomes, skip_reasons = Counter(), Counter(), Counter(), Counter()
    request_count = composed = rejected = fallback = puzzle_count = obstacle_count = 0
    max_hazards = 0
    environment_types = Counter()
    for event in generations:
        segment = event["accepted_segment"]
        environment_types.update(item["kind"] for item in segment.get("environment", []))
        max_hazards = max(max_hazards, len(segment["hazards"]))
        obstacle_count += len(segment["hazards"])
        for request in event["obstacle_requests"]:
            saw_outcomes[request["outcome"]] += 1
        for request in event["challenge_requests"]:
            request_count += 1
            fallback += request["stats_delta"]["fallbacks"]
            for candidate in request["candidates"]:
                composed += 1
                if candidate["reasons"]:
                    rejected += 1
                    reasons.update(candidate["reasons"])
            if request["accepted"] is None:
                skip_reasons[request["outcome"]] += 1
        challenge = segment["challenge"]
        if challenge:
            kinds[challenge["kind"]] += 1
            puzzle_count += bool(challenge["switches"])
            obstacle_count += len(challenge["shadows"]) + len(challenge["enemies"])
    platforms = [event["accepted_segment"]["platform"] for event in generations]
    return {
        "generations": len(generations), "challenge_requests": request_count,
        "challenge_candidates": composed, "rejected_candidates": rejected,
        "challenge_fallbacks": fallback, "accepted_challenges": sum(kinds.values()),
        "accepted_by_kind": dict(sorted(kinds.items())),
        "interactive_puzzles": puzzle_count, "obstacle_entities": obstacle_count,
        "max_saws_per_segment": max_hazards,
        "environment_by_type": dict(environment_types),
        "environment_objects": sum(environment_types.values()),
        "challenge_rejection_reasons": dict(reasons.most_common()),
        "challenge_skip_outcomes": dict(skip_reasons), "saw_outcomes": dict(saw_outcomes),
        "platform_fallbacks": sum(event["accepted_segment"]["validation"]["fallback_used"] for event in generations),
        "platform_rejections": sum(not candidate["validation"]["valid"]
                                   for event in generations for candidate in event["platform_candidates"]),
        "unique_platform_world_x": len({p["x"] for p in platforms}),
        "platform_width_min_max": [min(p["width"] for p in platforms), max(p["width"] for p in platforms)] if platforms else [],
        "platforms_at_y_470": sum(p["y"] == 470 for p in platforms),
        "cleanup_events": len(cleanups),
        "cleaned_platforms": sum(len(event["removed_platform_ids"]) for event in cleanups),
        "spawned_object_count": sum(event.get("spawn", {}).get("spawned_object_count", 0) for event in generations),
        "cleaned_object_count": sum(event["cleaned_object_count"] for event in cleanups),
        "switch_activations": sum(event["event"] == "switch_activation" for event in events),
        "registration_problems": [problem for event in events
                                  for problem in event.get("spawn", event).get("registration_problems", [])],
    }


def rendering_sample(game, frame):
    """Call actual drawing code and observe the data passed through its routes."""
    world = game.world
    calls = Counter()
    tile_calls = []
    original_terrain, original_challenges, original_tile = game._terrain, game._challenges, game.art._tile

    def terrain():
        calls["terrain"] += 1
        return original_terrain()

    def challenges():
        calls["challenges"] += 1
        return original_challenges()

    def tile(screen, name, offset, y=0):
        tile_calls.append({"name": name, "offset_mod_tile_width": offset % game.art._landscapes[name].get_width()})
        return original_tile(screen, name, offset, y)

    with patch.object(game, "_terrain", terrain), patch.object(game, "_challenges", challenges), patch.object(game.art, "_tile", tile):
        game.draw()
    visible = Counter()
    visible_objects = []
    for challenge in world.challenges:
        for name in ("switches", "barriers", "shadows", "enemies", "caches"):
            for item in getattr(challenge, name):
                if name == "barriers" and not world._barrier_is_active(item):
                    continue
                x = world.enemy_states[item.id].x if name == "enemies" else item.x
                if game.camera <= x <= game.camera + game.canvas.get_width():
                    visible[name] += 1
                    visible_objects.append({"type": name, "id": item.id, "platform_id": challenge.platform_id,
                                            "world_x": x, "world_y": item.y, "screen_x": x - game.camera})
    return {
        "frame": frame, "player_progress": world.distance,
        "camera": game.camera, "called_draw_routes": dict(calls),
        "visible_challenge_objects": dict(visible), "visible_objects": visible_objects,
        "background_tiles": tile_calls, "registry_problems": registration_checks(world),
    }


def live_run(game, seed, frames, output, event_file, idle=False):
    label = f"{'idle' if idle else 'live'}-seed-{seed}"
    with GenerationTrace(label) as trace:
        game.start_endless(seed)
        pilot = EndlessPilot()
        samples = [rendering_sample(game, 0)]
        previous_generation = game.world.generation_count
        for frame in range(1, frames + 1):
            control = Input() if idle else pilot.control(game.world)
            game.update(1 / 60, control)
            if game.world.generation_count != previous_generation:
                samples.append(rendering_sample(game, frame))
                previous_generation = game.world.generation_count
            if game.world.dead:
                break
        samples.append(rendering_sample(game, frame))
        if seed == 7 and not idle:
            import pygame
            pygame.image.save(game.canvas, output / 'audit-endless-seed7.png')
        for event in trace.events:
            event_file.write(json.dumps(event, sort_keys=True) + '\n')
        summary = summarize(trace.events)
        summary.update(run=label, seed=seed, rendered_frames=frame,
                       physics=game.world.snapshot(), cap_hits=trace.cap_hits,
                       rendering_samples=samples)
        generation_events = [event for event in trace.events if event['event'] == 'generation']
        summary['progress_windows'] = []
        for start in range(0, int(game.world.distance) + 1, 4000):
            window = [event for event in generation_events if start <= event['player_progress'] < start + 4000]
            row = summarize(window)
            summary['progress_windows'].append({
                'progress_range': [start, start + 4000],
                'difficulty_min_max': [min(event['profile']['difficulty'] for event in window),
                                       max(event['profile']['difficulty'] for event in window)] if window else [],
                **{key: row[key] for key in ('generations', 'challenge_requests', 'accepted_challenges',
                                            'accepted_by_kind', 'interactive_puzzles', 'obstacle_entities')},
            })
        return summary


def structural_sweep(seeds, count, difficulty, health=1.0, lantern=1.0):
    manager = DifficultyManager()
    distance = manager.scale * math.expm1((difficulty - manager.base) / manager.growth)
    events = []
    for seed in seeds:
        with GenerationTrace(f"structural-sweep-difficulty-{difficulty}-seed-{seed}") as trace:
            generator = ProceduralGenerator(seed, previous=Platform(0, -80, 460, 920, 180, -1, 1))
            for _ in range(count):
                generator.generate_next(distance, ChallengeContext(difficulty, health, lantern, distance,
                                                                    generator.capabilities))
        events.extend(trace.events)
    result = summarize(events)
    result.update(difficulty=difficulty, progress_for_profile=distance,
                  health_fraction=health, lantern_fraction=lantern,
                  method="real ProceduralGenerator platform widths, fixed context; not live traversal")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/echo/verification/generation-repair')
    parser.add_argument('--seeds', type=int, nargs='+', default=[1, 2, 7, 13, 21])
    parser.add_argument('--frames', type=int, default=6000, help='60 Hz application updates per live seed')
    parser.add_argument('--sweep-count', type=int, default=200, help='real segments per seed/difficulty')
    args = parser.parse_args(argv)
    if args.frames <= 0 or args.sweep_count <= 0:
        parser.error('frame and sweep counts must be positive')
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    from echo_game.game import Game
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    game = Game(chapter=0, start=True, muted=True, persist=False)
    try:
        # Explicitly test the default mode; do not label campaign data procedural.
        with GenerationTrace('default-campaign') as trace:
            for _ in range(120):
                game.update(1 / 60)
            game.draw()
        report = {
            'scope': 'current-source generation observer; wrappers do not alter gameplay; no per-frame logging',
            'default_mode': {'world_type': type(game.world).__name__, 'endless': game.world.endless,
                             'terrain_blocks': len(game.world.terrain_rects()),
                             'crates': len(game.world.crates), 'generation_events': len(trace.events)},
            'live': [],
        }
        with (args.output / 'audit-events.jsonl').open('w') as events:
            for seed in args.seeds:
                report['live'].append(live_run(game, seed, args.frames, args.output, events))
            report['idle'] = live_run(game, 7, 600, args.output, events, idle=True)
        report['structural_sweep'] = [structural_sweep(args.seeds, args.sweep_count, difficulty)
                                      for difficulty in (1.0, 4.0, 7.0, 8.2, 10.0)]
        report['low_resources'] = structural_sweep(args.seeds, args.sweep_count, 4.0, 0.1, 0.1)
        report['environment'] = {
            'runtime_generator': 'echo_game/environment.py:EnvironmentGenerator', 'types_requested': list(ENVIRONMENT_TYPES),
            'runtime_accepted': sum(run['environment_objects'] for run in report['live']), 'world_seed_controls_art': False,
            'mid_layer_tree_tile_x': [96, 352, 688, 1682, 1854],
            'tile_width': 1920, 'endless_art_chapter': game.world.chapter,
            'mid_layer_camera_repeat_distance': 1920 / 0.32,
            'foliage_camera_repeat_distance': 1920 / 0.61,
            'source': 'echo_game/art.py:_landscape, _foliage, Art._tile; not world-owned objects',
        }
        report['source_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted((ROOT / 'echo_game').glob('*.py'))}
        report['instrumentation_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report['wall_seconds'] = round(time.perf_counter() - started, 3)
        (args.output / 'audit-summary.json').write_text(json.dumps(report, indent=2) + '\n')
        # Print compact summaries, not the full candidate/render event history.
        print(json.dumps({key: value for key, value in report.items()
                          if key not in ('live', 'idle', 'source_sha256')}, indent=2))
        for run in report['live'] + [report['idle']]:
            print(json.dumps({key: value for key, value in run.items()
                              if key not in ('rendering_samples', 'physics')}
                             | {'distance': run['physics']['distance'], 'dead': run['physics']['dead']}, sort_keys=True))
    finally:
        game.close()


if __name__ == '__main__':
    main()
