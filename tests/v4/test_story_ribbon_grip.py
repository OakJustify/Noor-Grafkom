"""ribbon_hands: the close-up hands must actually reach the ribbon.

The first fix attached an arm to each palm, but the palms still sat beside the
ribbon — the left palm was 131 px from the ribbon's left edge — so the shot read
as two hands hovering near a ribbon rather than holding it.

Measured requirement: each palm centre must lie inside the ribbon's painted
bounding box, and each wrist must face the forearm leaving the frame.  What the
hand *shape* looks like is a separate, stylistic question: five-fingered grips
were implemented and rejected on visual review (they read as berry clusters),
so the shot uses the same mitten palm as the rest of the artwork.  These tests
therefore pin position and attachment, and deliberately do not claim anatomical
grip quality.
"""
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import numpy as np
import pygame
import pytest

from nur_game import config
from nur_game.cinematics import renderer
from nur_game.cinematics.catalog import SCENES

SKIN_RGB = {(211, 162, 122), (231, 186, 146), (177, 122, 94)}
# _ribbon() paints inside its own local (0, 0)-(71, 70).
RIBBON_LOCAL = (71, 70)


def _render(monkeypatch):
    palms, limbs, ribbons = [], [], []
    original_hand = renderer._hand
    original_ribbon = renderer._ribbon
    original_line = renderer._Brush.line
    original_poly = renderer._Brush.poly

    def hand(brush, x, y, direction=1, old=False):
        palms.append({'palm': brush.point((x + 16, y + 9)), 'direction': direction,
                      'scale': brush.scale})
        return original_hand(brush, x, y, direction, old)

    def ribbon(brush):
        ribbons.append({'x0': brush.point((0, 0))[0], 'y0': brush.point((0, 0))[1],
                        'x1': brush.point(RIBBON_LOCAL)[0],
                        'y1': brush.point(RIBBON_LOCAL)[1]})
        return original_ribbon(brush)

    def line(self, colour, start, end, width=1):
        if tuple(colour) in SKIN_RGB:
            limbs.append([tuple(self.point(start)), tuple(self.point(end))])
        return original_line(self, colour, start, end, width)

    def poly(self, colour, points, width=0):
        if tuple(colour) in SKIN_RGB and len(points) >= 4:
            pts = [self.point(p) for p in points]
            span = max(((a[0]-b[0])**2 + (a[1]-b[1])**2) ** .5 for a in pts for b in pts)
            if span > 130:
                limbs.append([tuple(p) for p in pts])
        return original_poly(self, colour, points, width)

    monkeypatch.setattr(renderer, '_hand', hand)
    monkeypatch.setattr(renderer, '_ribbon', ribbon)
    monkeypatch.setattr(renderer._Brush, 'line', line)
    monkeypatch.setattr(renderer._Brush, 'poly', poly)
    renderer._illustration.cache_clear()
    scene = SCENES['CS01']
    cue = next(c for c in scene.cues if c.shot == 'ribbon_hands')
    frame = pygame.Surface(config.SIZE)
    frame.fill((0, 0, 0))
    renderer.StoryRenderer(config.SIZE).draw(frame, scene, cue, 1.0, 6.0, False)
    return frame, palms, limbs, ribbons


def _ribbon_box(ribbons):
    assert ribbons, 'ribbon_hands must paint the ribbon'
    box = ribbons[-1]
    return pygame.Rect(round(box['x0']), round(box['y0']),
                       round(box['x1'] - box['x0']), round(box['y1'] - box['y0']))


def test_both_palms_close_on_the_ribbon_no_longer_beside_it(monkeypatch):
    _frame, palms, _limbs, ribbons = _render(monkeypatch)
    box = _ribbon_box(ribbons)
    assert len(palms) == 2, f'expected two close-up hands, recorded {len(palms)}'
    for hand in palms:
        x, y = hand['palm']
        assert box.collidepoint(x, y), (
            f'the palm at ({x:.0f}, {y:.0f}) does not touch the ribbon {tuple(box)} — '
            f'the hand sits beside it')


def test_the_ribbon_stays_readable_between_the_two_hands(monkeypatch):
    frame, _palms, _limbs, ribbons = _render(monkeypatch)
    box = _ribbon_box(ribbons)
    arr = pygame.surfarray.array3d(frame).transpose(1, 0, 2).astype(np.int16)
    window = arr[box.top:box.bottom, box.left:box.right]
    assert window.size, f'ribbon box {tuple(box)} is outside the frame'
    skin = np.zeros(window.shape[:2], bool)
    for r, g, b in SKIN_RGB:
        skin |= (np.abs(window[:, :, 0]-r) + np.abs(window[:, :, 1]-g)
                 + np.abs(window[:, :, 2]-b)) <= 6
    covered = skin.mean()
    assert 0.04 < covered < 0.80, (
        f'{covered:.1%} of the ribbon is under skin — the palms must overlap its edge '
        f'without smothering the bow')


def test_each_wrist_faces_away_from_its_own_palm(monkeypatch):
    _frame, palms, limbs, _ribbons = _render(monkeypatch)
    for hand in palms:
        palm_x, palm_y = hand['palm']
        wrist = (palm_x - 12 * hand['direction'] * hand['scale'], palm_y)
        near = [limb for limb in limbs
                if min(((wrist[0]-p[0])**2 + (wrist[1]-p[1])**2) ** .5
                       for p in limb) <= 60]
        assert near, f'no forearm reaches the wrist at {wrist}'
        far = max((p for limb in near for p in limb),
                  key=lambda p: (p[0]-wrist[0])**2 + (p[1]-wrist[1])**2)
        towards_palm = palm_x - wrist[0]
        assert towards_palm == 0 or (far[0]-wrist[0]) * towards_palm < 0, (
            f'the forearm runs back over its own hand at x={palm_x:.0f}')


def test_the_two_hands_mirror_each_other_across_the_ribbon(monkeypatch):
    _frame, palms, _limbs, _ribbons = _render(monkeypatch)
    assert len(palms) == 2
    left, right = sorted(hand['palm'][0] for hand in palms)
    assert right - left > 30, f'both hands are stacked at x={left:.0f}, {right:.0f}'
    assert sorted(hand['direction'] for hand in palms) == [-1, 1], \
        'one hand must face left and the other right'