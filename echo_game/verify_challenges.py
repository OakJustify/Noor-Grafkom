"""Measure procedural challenge generation and real endless-mode traversal.

The report is deterministic for a fixed seed range and is intended to accompany
``docs/echo/verification/challenge-generation.json``.

    .venv-echo/bin/python -m echo_game.verify_challenges
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from .challenges import ChallengeContext, PuzzleGenerator, PuzzleValidator
from .procedural import (
    EndlessPilot,
    EndlessWorld,
    GenerationProfile,
    Platform,
)


ROOT = Path(__file__).resolve().parent.parent


def _signature(seed: int, difficulty: float, count: int):
    generator = PuzzleGenerator(seed)
    rows = []
    for index in range(count):
        target = Platform(index + 1, index * 400.0, 440.0, 340.0, 28.0,
                          index, difficulty)
        challenge = generator.generate(
            target, GenerationProfile.create(difficulty),
            ChallengeContext(difficulty))
        if challenge is None:
            rows.append(None)
            continue
        rows.append((
            challenge.kind, challenge.platform_id, challenge.damage,
            tuple((barrier.x, barrier.y) for barrier in challenge.barriers),
            tuple((switch.x, switch.y) for switch in challenge.switches),
        ))
    return rows


def verify(output: Path, seeds: int = 30, frames: int = 6000,
           synthetic_seeds: int = 10, requests: int = 100):
    report: dict = {
        "method": ("Synthetic platforms through PuzzleGenerator/PuzzleValidator, "
                   "plus real EndlessWorld physics with EndlessPilot input only."),
        "difficulty_sweep": [],
        "low_resources": {},
        "soak": {},
        "determinism": {},
    }
    for difficulty in (1.0, 4.0, 7.0, 10.0):
        generated = rejected = fallbacks = 0
        by_kind: dict[str, int] = {}
        started = time.perf_counter()
        for seed in range(1, synthetic_seeds + 1):
            generator = PuzzleGenerator(seed)
            for index in range(requests):
                target = Platform(index + 1, index * 400.0, 440.0, 340.0, 28.0,
                                  index, difficulty)
                challenge = generator.generate(
                    target, GenerationProfile.create(difficulty),
                    ChallengeContext(difficulty))
                if challenge is not None:
                    generated += 1
                    by_kind[challenge.kind] = by_kind.get(challenge.kind, 0) + 1
                    reasons = PuzzleValidator().validate(
                        challenge, target, ChallengeContext(difficulty))
                    if reasons:
                        raise AssertionError((challenge.kind, reasons))
            rejected += generator.stats.rejections
            fallbacks += generator.stats.fallbacks
        total = synthetic_seeds * requests
        report["difficulty_sweep"].append({
            "difficulty": difficulty,
            "requests": total,
            "valid_generated": generated,
            "valid_rate": round(generated / total, 4),
            "rejections": rejected,
            "challenge_fallbacks": fallbacks,
            "by_kind": dict(sorted(by_kind.items())),
            "seconds": round(time.perf_counter() - started, 3),
        })

    low_generated = 0
    low_kinds: dict[str, int] = {}
    low_requests = 0
    for seed in range(1, synthetic_seeds + 1):
        generator = PuzzleGenerator(seed)
        for index in range(requests):
            low_requests += 1
            target = Platform(index + 1, index * 400.0, 440.0, 340.0, 28.0,
                              index, 4.0)
            challenge = generator.generate(
                target, GenerationProfile.create(4.0),
                ChallengeContext(4.0, health_fraction=0.1,
                                 lantern_fraction=0.1))
            if challenge is not None:
                low_generated += 1
                low_kinds[challenge.kind] = low_kinds.get(challenge.kind, 0) + 1
    report["low_resources"] = {
        "health_fraction": 0.1,
        "lantern_fraction": 0.1,
        "requests": low_requests,
        "valid_generated": low_generated,
        "by_kind": dict(sorted(low_kinds.items())),
    }

    report["determinism"] = {
        "same_seed": _signature(2026, 7.0, 120) == _signature(2026, 7.0, 120),
        "different_seed_differs": (_signature(2026, 7.0, 120)
                                   != _signature(2027, 7.0, 120)),
    }

    soak = {
        "seeds": seeds,
        "frames_requested_per_seed": frames,
        "deaths": 0,
        "min_distance": None,
        "total_valid_challenges": 0,
        "total_rejections": 0,
        "platform_fallbacks": 0,
        "challenge_fallbacks": 0,
        "min_health": 5,
        "min_lantern_energy": 1.0,
        "wall_seconds": 0.0,
    }
    started = time.perf_counter()
    distances = []
    for seed in range(1, seeds + 1):
        world = EndlessWorld(seed)
        pilot = EndlessPilot()
        for _ in range(frames):
            world.step(pilot.control(world))
            if world.dead:
                break
        snapshot = world.snapshot()
        stats = snapshot["challenge_stats"]
        distances.append(snapshot["distance"])
        soak["deaths"] += int(world.dead)
        soak["total_valid_challenges"] += stats["generated"]
        soak["total_rejections"] += stats["rejections"]
        soak["platform_fallbacks"] += snapshot["fallbacks"]
        soak["challenge_fallbacks"] += stats["fallbacks"]
        soak["min_health"] = min(soak["min_health"], snapshot["health"])
        soak["min_lantern_energy"] = min(
            soak["min_lantern_energy"], snapshot["lantern_energy"])
        # Every live challenge must still satisfy the validator.
        platforms = {platform.id: platform
                     for platform in world.generated_platforms}
        for challenge in world.challenges:
            target = platforms[challenge.platform_id]
            hazards = [hazard for hazard in world.generated_hazards
                       if hazard.platform_id == challenge.platform_id]
            reasons = PuzzleValidator().validate(
                challenge, target,
                ChallengeContext(world.difficulty, 1.0, 1.0,
                                 capabilities=world.generator.capabilities),
                hazards=hazards)
            if reasons:
                raise AssertionError((challenge.kind, reasons))
    soak["min_distance"] = round(min(distances), 2)
    soak["mean_distance"] = round(sum(distances) / len(distances), 2)
    soak["wall_seconds"] = round(time.perf_counter() - started, 3)
    report["soak"] = soak
    report["source_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "echo_game").glob("*.py"))
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs" / "echo" / "verification"
                        / "challenge-generation.json")
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--frames", type=int, default=6000)
    parser.add_argument("--synthetic-seeds", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()
    verify(args.output, args.seeds, args.frames,
           args.synthetic_seeds, args.requests)


if __name__ == "__main__":
    main()
