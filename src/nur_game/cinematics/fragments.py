"""Six story objects on the mandatory road, separate from optional fuel ribbons."""

from dataclasses import dataclass

from ..continuum import REGIONS


@dataclass(frozen=True)
class StoryFragment:
    key: str
    title: str
    scene: str
    region: int
    x: float = 255.0
    y: float = 438.0

    @property
    def position(self):
        return REGIONS[self.region].start + self.x, self.y


STORY_FRAGMENTS = tuple(
    StoryFragment(f'F{index:02d}', title, f'CS{index:02d}', region)
    for index, (title, region) in enumerate((
        ('Pita merah', 1), ('Cangkir biru', 5), ('Kunci kecil', 10),
        ('Foto terlipat', 15), ('Catatan dapur', 20), ('Kain bersulam', 25),
    ), 1)
)
FRAGMENT_KEYS = frozenset(f.key for f in STORY_FRAGMENTS)
MEMORY_SCENES = tuple(f.scene for f in STORY_FRAGMENTS)
