"""Data-only, segment-owned decoration; never modifies structural geometry.

Every type has its own density, dimensions, layer and support rule. Decorative
wood/rocks are deliberately not solid props: adding solids requires a separate
controller-path validation feature, not an invisible collider in this layer.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import math
import random

from .challenges import rects_overlap
from .levels import Rect


@dataclass(frozen=True)
class EnvironmentRule:
    kind: str
    per_100_px: float
    width_range: tuple[float, float]
    height_range: tuple[float, float]
    edge_margin: float
    spacing: float
    layer: str


RULES = (
    EnvironmentRule("tree", .12, (48, 80), (75, 130), 30, 20, "rear"),
    EnvironmentRule("bamboo", .14, (28, 48), (64, 104), 26, 16, "rear"),
    EnvironmentRule("wood", .20, (28, 54), (8, 14), 24, 10, "front"),
    EnvironmentRule("rock", .24, (14, 26), (9, 18), 24, 8, "front"),
    EnvironmentRule("grass", 1.10, (10, 22), (4, 9), 12, 3, "front"),
    EnvironmentRule("dirt_block", .32, (28, 52), (10, 20), 8, 4, "terrain"),
)
RULE_BY_KIND = {rule.kind: rule for rule in RULES}


@dataclass(frozen=True)
class EnvironmentConfig:
    density: float = 1.0
    max_objects: int = 64  # Increased from 32 to handle wide arena platforms
    placement_attempts: int = 5

    def __post_init__(self):
        if not math.isfinite(self.density) or not 0 <= self.density <= 3:
            raise ValueError("Environment density must be a finite multiplier between 0 and 3")
        if self.max_objects < 1 or self.placement_attempts < 1:
            raise ValueError("Environment placement limits must be positive")


@dataclass(frozen=True)
class EnvironmentSpec:
    id: int
    kind: str
    x: float
    y: float
    width: float
    height: float
    layer: str
    variant: int
    platform_id: int
    generation_index: int

    @property
    def rect(self) -> Rect:
        return Rect(self.x, self.y, self.width, self.height)

    @property
    def collidable(self) -> bool:
        return False


def reserved_rects(challenge=None, hazards=()) -> tuple[Rect, ...]:
    """Keep decorations away from interactable footprints and moving sweeps."""
    rects = []
    if challenge:
        rects.extend(s.rect for s in challenge.switches)
        rects.extend(b.rect for b in challenge.barriers)
        rects.extend(z.rect for z in challenge.shadows)
        rects.extend(e.patrol_rect for e in challenge.enemies)
        rects.extend(c.rect for c in challenge.caches)
    rects.extend(Rect(h.x - h.travel - h.radius, h.y - h.radius,
                      2 * (h.radius + h.travel), 2 * h.radius) for h in hazards)
    return tuple(rects)


class EnvironmentGenerator:
    def __init__(self, seed: int, config: EnvironmentConfig | None = None):
        self.seed = int(seed)
        self.config = config or EnvironmentConfig()
        self.rng = random.Random(self.seed ^ 0xE071A0)
        self.next_id = 1
        self.total_by_type = Counter()
        self.last_report = {}

    def validate(self, item: EnvironmentSpec, platform, accepted=(), reserved=()) -> list[str]:
        reasons = []
        rule = RULE_BY_KIND.get(item.kind)
        if rule is None:
            return ["unknown environment type"]
        if (not all(math.isfinite(value) for value in (item.x, item.y, item.width, item.height))
                or not rule.width_range[0] <= item.width <= rule.width_range[1]
                or not rule.height_range[0] <= item.height <= rule.height_range[1]):
            reasons.append("environment dimensions outside type bounds")
        if item.platform_id != platform.id or item.generation_index != platform.generation_index:
            reasons.append("environment owner mismatch")
        if item.layer != rule.layer:
            reasons.append("environment layer mismatch")
        if (item.x < platform.x + rule.edge_margin
                or item.x + item.width > platform.right - rule.edge_margin):
            reasons.append("environment footprint crosses safe surface edge")
        if item.kind == "dirt_block":
            if item.y < platform.y or item.y + item.height > platform.bottom:
                reasons.append("dirt patch outside supporting terrain")
        elif abs(item.y + item.height - platform.y) > 1e-6:
            reasons.append("environment not supported by platform surface")
        if any(rects_overlap(item.rect, other.rect,
                             padding=max(rule.spacing, RULE_BY_KIND[other.kind].spacing))
               for other in accepted):
            reasons.append("environment spacing overlap")
        # Even ground decorations below a switch should not camouflage it.
        if item.kind != "dirt_block" and any(
                item.x < r.x + r.w + 12 and item.x + item.width > r.x - 12 for r in reserved):
            reasons.append("environment obscures reserved challenge or hazard footprint")
        return reasons

    def generate(self, platform, profile, reserved=()) -> tuple[EnvironmentSpec, ...]:
        accepted = []
        report = {"implemented": True, "seed": self.seed,
                  "segment": platform.generation_index, "difficulty": profile.difficulty,
                  "density": self.config.density, "candidates": [],
                  "candidates_by_type": {r.kind: 0 for r in RULES},
                  "accepted_by_type": {r.kind: 0 for r in RULES},
                  "rejected_positions": [], "cap_reached": False}
        if self.config.density == 0:
            self.last_report = report
            return ()
        for rule in RULES:
            expectation = platform.width / 100 * rule.per_100_px * self.config.density
            count = min(self.config.max_objects, int(expectation + self.rng.random()))
            for _ in range(count):
                for _ in range(self.config.placement_attempts):
                    if len(accepted) >= self.config.max_objects:
                        report["cap_reached"] = True
                        break
                    width = self.rng.uniform(*rule.width_range)
                    height = self.rng.uniform(*rule.height_range)
                    x = self.rng.uniform(platform.x + rule.edge_margin,
                                         platform.right - rule.edge_margin - width)
                    y = (platform.y + 3 if rule.kind == "dirt_block" else platform.y - height)
                    item = EnvironmentSpec(self.next_id, rule.kind, x, y, width, height,
                                           rule.layer, self.rng.randrange(3), platform.id,
                                           platform.generation_index)
                    reasons = self.validate(item, platform, accepted, reserved)
                    candidate = {"object": asdict(item), "reasons": reasons}
                    report["candidates"].append(candidate)
                    report["candidates_by_type"][rule.kind] += 1
                    if reasons:
                        report["rejected_positions"].append(candidate)
                    else:
                        accepted.append(item)
                        self.next_id += 1
                        report["accepted_by_type"][rule.kind] += 1
                        self.total_by_type[rule.kind] += 1
                        break
        self.last_report = report
        return tuple(accepted)
