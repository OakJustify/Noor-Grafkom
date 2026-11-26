"""Every close-up hand must be attached to a forearm that leaves the frame.

The reported defect was a palm shape sitting on the table with nothing attached,
because those shots called ``_hand()`` and never drew a limb.  A colour-distance
pixel test is unreliable here (Ink supersamples, wood and skin are close in RGB),
so this file records the real drawing calls instead: each ``_hand()`` must be
accompanied by a skin-coloured line whose endpoint is at that hand's wrist and
whose other endpoint is at or beyond the frame edge.

Palm centre for ``_hand(brush, x, y, ...)`` is ``brush.point((x + 16, y + 9))``;
the wrist sits 12 px further along the palm's facing direction.
"""
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
import pytest

from nur_game import config
from nur_game.cinematics import renderer
from nur_game.cinematics.catalog import SCENES

SKIN_RGB = {(211, 162, 122), (231, 186, 146), (177, 122, 94)}

# (scene, shot, expected number of close-up hands)
HAND_SHOTS = [
    ('CS04', 'photo_print', 2),
    ('CS04', 'photo_fading', 2),
    ('CS05', 'recipe_stir', 1),
    ('CS06', 'stitch_hands', 2),
    ('CS08', 'real_hands', 4),
    ('CS01', 'ribbon_hands', 2),
]


def _record(shot, scene_key, monkeypatch):
    """Render one shot while recording every palm draw and every skin line."""
    hands, limbs = [], []
    original_hand = renderer._hand
    original_line = renderer._Brush.line
    original_poly = renderer._Brush.poly

    def hand(brush, x, y, direction=1, old=False):
        hands.append({'brush': (brush.x, brush.y, brush.scale),
                      'palm': brush.point((x + 16, y + 9)), 'direction': direction})
        return original_hand(brush, x, y, direction, old)

    def line(self, colour, start, end, width=1):
        if tuple(colour) in SKIN_RGB:
            limbs.append({'points': [tuple(self.point(start)), tuple(self.point(end))],
                          'width': width * self.scale})
        return original_line(self, colour, start, end, width)

    def poly(self, colour, points, width=0):
        # A tapered forearm is a filled quad, not a stroke: record its long axis.
        if tuple(colour) in SKIN_RGB and len(points) >= 4:
            pts = [self.point(p) for p in points]
            span = max(_distance(a, b) for a in pts for b in pts)
            # Palms are ~80 px across and are not limbs; forearms are longer.
            if span > 130:
                edges = [_distance(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
                limbs.append({'points': [tuple(p) for p in pts], 'width': min(edges)})
        return original_poly(self, colour, points, width)

    monkeypatch.setattr(renderer, '_hand', hand)
    monkeypatch.setattr(renderer._Brush, 'line', line)
    monkeypatch.setattr(renderer._Brush, 'poly', poly)
    renderer._illustration.cache_clear()
    scene = SCENES[scene_key]
    cue = next(c for c in scene.cues if c.shot == shot)
    frame = pygame.Surface(config.SIZE)
    frame.fill((0, 0, 0))
    renderer.StoryRenderer(config.SIZE).draw(frame, scene, cue, 1.0, 6.0, False)
    return hands, limbs


def _distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5


@pytest.mark.parametrize('scene_key,shot,count', HAND_SHOTS)
def test_shot_draws_the_expected_number_of_close_up_hands(scene_key, shot, count, monkeypatch):
    hands, _limbs = _record(shot, scene_key, monkeypatch)
    assert len(hands) == count, f'{scene_key}/{shot}: expected {count} hands, recorded {len(hands)}'


@pytest.mark.parametrize('scene_key,shot,count', HAND_SHOTS)
def test_every_close_up_hand_has_a_forearm_touching_its_wrist(scene_key, shot, count, monkeypatch):
    hands, limbs = _record(shot, scene_key, monkeypatch)
    assert hands and limbs, f'{scene_key}/{shot}: no hands or no skin limbs recorded'
    for hand in hands:
        palm = hand['palm']
        wrist = (palm[0] - 12 * hand['direction'] * hand['brush'][2], palm[1])
        gap = min(min(_distance(wrist, p) for p in limb['points']) for limb in limbs)
        assert gap <= 55, (f'{scene_key}/{shot}: the hand at '
                           f'{tuple(round(v) for v in palm)} has no forearm at its wrist '
                           f'(nearest skin limb is {gap:.0f} px away)')


@pytest.mark.parametrize('scene_key,shot,count', HAND_SHOTS)
def test_palm_is_wider_than_the_forearm_it_joins(scene_key, shot, count, monkeypatch):
    """A palm the width of its arm reads as a rounded stick, not a hand."""
    hands, limbs = _record(shot, scene_key, monkeypatch)
    for hand in hands:
        brush = hand['brush']
        scale = brush[2]
        palm_width = 34 * scale          # painted palm is ~34 px at scale 1
        palm = hand['palm']
        wrist = (palm[0] - 12 * hand['direction'] * scale, palm[1])
        near = [limb for limb in limbs
                if min(_distance(wrist, p) for p in limb['points']) <= 55]
        assert near, f'{scene_key}/{shot}: no forearm at the wrist of the hand at {palm}'
        arm_width = min(limb['width'] for limb in near)
        assert palm_width >= arm_width * 1.15, (
            f'{scene_key}/{shot}: the palm at {tuple(round(v) for v in palm)} is only '
            f'{palm_width:.0f} px wide against a {arm_width:.0f} px arm — it reads as a stick')


@pytest.mark.parametrize('scene_key,shot,count', HAND_SHOTS)
def test_each_forearm_leaves_the_frame_so_the_arm_is_never_cut_mid_air(scene_key, shot, count,
                                                                      monkeypatch):
    hands, limbs = _record(shot, scene_key, monkeypatch)
    w, h = config.SIZE
    for hand in hands:
        palm = hand['palm']
        wrist = (palm[0] - 12 * hand['direction'] * hand['brush'][2], palm[1])
        candidates = [limb for limb in limbs
                      if min(_distance(wrist, p) for p in limb['points']) <= 55]
        assert candidates, f'{scene_key}/{shot}: no forearm reaches the wrist at {palm}'
        assert any(any(p[0] <= 0 or p[0] >= w or p[1] <= 0 or p[1] >= h
                       for p in limb['points'])
                   for limb in candidates), (
            f'{scene_key}/{shot}: the forearm from the palm at {tuple(round(v) for v in palm)} '
            f'ends inside the frame ({[[tuple(round(c) for c in p) for p in l["points"]] for l in candidates]})')


def test_close_up_forearms_are_thick_enough_to_read_as_limbs(monkeypatch):
    _hands, limbs = _record('photo_print', 'CS04', monkeypatch)
    assert limbs
    assert max(limb['width'] for limb in limbs) >= 20, \
        'a forearm as thin as a pen cannot read as an arm'


def test_animated_overlay_hands_also_carry_skin_limbs(monkeypatch):
    """The real_hands gesture overlay draws its own hands each frame."""
    hands, limbs = [], []
    original_hand = renderer._hand
    original_line = renderer._Brush.line

    def hand(brush, x, y, direction=1, old=False):
        hands.append(brush.point((x + 16, y + 9)))
        return original_hand(brush, x, y, direction, old)

    def line(self, colour, start, end, width=1):
        if tuple(colour) in SKIN_RGB:
            limbs.append((tuple(self.point(start)), tuple(self.point(end))))
        return original_line(self, colour, start, end, width)

    monkeypatch.setattr(renderer, '_hand', hand)
    monkeypatch.setattr(renderer._Brush, 'line', line)
    renderer._gesture.cache_clear()
    renderer._gesture('real_hands', 0)
    assert len(hands) == 2, f'overlay draws {len(hands)} hands'
    assert len(limbs) >= 2, 'overlay hands have no wrist/arm lines'