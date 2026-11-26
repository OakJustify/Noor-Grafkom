"""Narrative state independent of lantern charge and simulation time."""

from dataclasses import dataclass, field
import math

from .catalog import SCENES
from .fragments import STORY_FRAGMENTS, FRAGMENT_KEYS, MEMORY_SCENES


@dataclass
class StoryProgress:
    seen: set[str] = field(default_factory=set)
    collected: set[str] = field(default_factory=set)
    active: str | None = None
    scene_elapsed: float = 0.0
    finale_requested: bool = False
    completed: bool = False
    replay: bool = False
    paused: bool = False

    def begin_opening(self):
        if 'CS00' not in self.seen:
            self.active = 'CS00'
            self.scene_elapsed = 0.0

    def tick(self, dt):
        if not isinstance(dt, (float, int)) or not math.isfinite(dt):
            raise ValueError('Invalid cinematic time')
        if self.active and not self.paused:
            self.scene_elapsed += max(0.0, dt)
            if self.scene_elapsed >= self.scene.duration - 1e-9:
                self.skip()

    @property
    def scene(self):
        return SCENES[self.active] if self.active else None

    @property
    def cue_index(self):
        if not self.scene:
            return 0
        elapsed = self.scene_elapsed
        for index, cue in enumerate(self.scene.cues):
            if elapsed < cue.duration - 1e-9:
                return index
            elapsed -= cue.duration
        return len(self.scene.cues) - 1

    @property
    def cue(self):
        return self.scene.cues[self.cue_index] if self.scene else None

    @property
    def cue_elapsed(self):
        return self.scene_elapsed - sum(c.duration for c in self.scene.cues[:self.cue_index]) if self.scene else 0.0

    def advance(self):
        if not self.scene:
            return
        self.scene_elapsed = sum(c.duration for c in self.scene.cues[:self.cue_index+1])
        if self.scene_elapsed >= self.scene.duration - 1e-9:
            self.skip()

    def skip(self):
        self.paused = False
        if self.active:
            finished = self.active
            self.active = None
            self.scene_elapsed = 0.0
            if self.replay:
                return
            self.seen.add(finished)
            if finished == 'CS07':
                self.active = 'CS08'
                return
            if finished == 'CS08':
                self.completed = True
                return
        self.queue_ready()

    def begin_replay(self, key):
        if key not in self.seen or key not in SCENES or self.active:
            return False
        self.active = key
        self.scene_elapsed = 0.0
        self.paused = False
        self.replay = True
        return True

    def collect(self, key):
        if key not in FRAGMENT_KEYS:
            raise ValueError('Unknown story fragment')
        if key in self.collected:
            return False
        self.collected.add(key)
        self.queue_ready()
        return True

    def queue_ready(self):
        if self.active or self.completed or self.finale_requested or 'CS00' not in self.seen:
            return
        for fragment in STORY_FRAGMENTS:
            if fragment.scene not in self.seen:
                if fragment.key in self.collected:
                    self.active = fragment.scene
                    self.scene_elapsed = 0.0
                break

    def request_finale(self):
        if not self.ready or self.active or self.completed:
            return False
        self.finale_requested = True
        self.active = 'CS07'
        self.scene_elapsed = 0.0
        return True

    def snapshot(self):
        return {'version': 1, 'collected': sorted(self.collected), 'seen': sorted(self.seen),
                'active': None if self.replay else self.active,
                'finale_requested': self.finale_requested, 'completed': self.completed}

    @property
    def ready(self):
        return self.collected >= FRAGMENT_KEYS and self.seen >= set(MEMORY_SCENES)

    @property
    def fade(self):
        # A narrative metaphor, never tied to battery capacity or a clinical scale.
        count = sum(scene in self.seen for scene in MEMORY_SCENES)
        return (0.0, .06, .18, .34, .50, .68, .86)[count]

    @classmethod
    def restore(cls, data):
        if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
            raise ValueError('Invalid story version')
        scene_keys = {f'CS{i:02d}' for i in range(9)}
        for key, allowed in (('collected', FRAGMENT_KEYS), ('seen', scene_keys)):
            values = data.get(key)
            if (not isinstance(values, list) or not all(isinstance(v, str) for v in values)
                    or len(set(values)) != len(values) or not set(values) <= allowed):
                raise ValueError('Invalid story inventory')
        active = data.get('active')
        if active is not None and (not isinstance(active, str) or active not in scene_keys):
            raise ValueError('Invalid active cutscene')
        if not all(type(data.get(key)) is bool for key in ('finale_requested', 'completed')):
            raise ValueError('Invalid ending flags')
        story = cls(seen=set(data['seen']), collected=set(data['collected']), active=active,
                    finale_requested=data['finale_requested'], completed=data['completed'])
        preceding = {'CS00'}
        for fragment in STORY_FRAGMENTS:
            if fragment.scene in story.seen or active == fragment.scene:
                if fragment.key not in story.collected or not preceding <= story.seen:
                    raise ValueError('Cutscene without its preceding fragments')
            preceding.add(fragment.scene)
        if active in story.seen:
            raise ValueError('Completed cutscene cannot remain active')
        if 'CS07' in story.seen or 'CS08' in story.seen or active in ('CS07', 'CS08') or story.finale_requested:
            if not story.ready or not story.finale_requested:
                raise ValueError('Finale requires all six memories')
        if ('CS08' in story.seen or active == 'CS08') and 'CS07' not in story.seen:
            raise ValueError('Real-world reveal must follow the void')
        if story.completed != ('CS08' in story.seen) or (story.completed and active is not None):
            raise ValueError('Invalid completed ending')
        if story.finale_requested and not story.completed and active not in ('CS07', 'CS08'):
            raise ValueError('Interrupted finale needs its active cutscene')
        return story
