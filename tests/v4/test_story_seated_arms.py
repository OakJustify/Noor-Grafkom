"""Seated figures must rest their arms on the tabletop, not vanish under it.

Regression for a real defect: the room table is painted after the seated
figures in these shots, so each figure's forearm and palm (world y ~346-355,
i.e. on the tabletop surface) were covered by the table's top plank.  The
result read as a floating torso with no arms.
"""
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
import pytest

from nur_game import config
from nur_game.cinematics import renderer
from nur_game.cinematics.catalog import SCENES
from nur_game.cinematics.portraits import figure_layout

SKIN = {(211, 162, 122), (231, 186, 146), (177, 122, 94)}
TABLE_SURFACE = {(173, 125, 80), (112, 74, 52), (100, 70, 51), (195, 148, 92),
                 (215, 167, 107), (163, 115, 72), (178, 131, 85), (213, 164, 103)}
# The far table edge is y=316; the near edge is y=369 in the "room" table.
FAR_EDGE, NEAR_EDGE = 316, 369

# Shots whose scene branch paints a room table *after* its seated figures.
# Each entry lists the figures as (age, pose, x, y, scale, dress) exactly as the
# renderer draws them, so the hand band is measured where the palms really are.
TABLE_OVER_FIGURE = {
    'CS02': {'mug_drawing': [('adult', 'seated', 529, 84, .96, None)]},
    'CS05': {shot: [('old', 'tea' if shot == 'recipe_tea' else 'seated', 294, 85, 1.09, None),
                    ('adult', 'seated', 535, 113, 1.01, (166, 118, 94))]
             for shot in ('recipe_read', 'recipe_stir', 'recipe_tea')},
    'CS06': {shot: [('old', 'cloth', 279, 81, 1.15, None)]
                    + ([('adult', 'standing' if shot == 'cloth_door' else 'seated',
                          732 if shot == 'cloth_door' else 531,
                          88 if shot == 'cloth_door' else 111, 1.04, (169, 116, 91))]
                       if shot != 'cloth_wait' else [])
             for shot in ('cloth_wait', 'cloth_seated', 'cloth_door')},
    'CS08': {shot: [('old', 'tea' if shot == 'real_tea' else 'seated', 284, 90, 1.10, None),
                    ('adult', 'offer' if shot == 'real_hands' else 'cloth',
                     513, 112, 1.05, (174, 117, 90))]
             for shot in ('real_seated', 'real_tea', 'real_hands', 'real_cloth',
                          'real_wide', 'real_faces', 'real_arrival')},
}
TABLE_OVER_FIGURE['CS08']['real_faces'] = [('old', 'cloth', 224, 48, 1.37, None),
                                           ('adult', 'offer', 509, 63, 1.32, (173, 116, 91))]
TABLE_OVER_FIGURE['CS08']['real_arrival'] = TABLE_OVER_FIGURE['CS08']['real_faces']
# Shots that must keep the table in front of the body: close-ups whose whole
# point is a tabletop surface plus separately drawn hands.
TABLE_CLOSEUPS = [('CS04', 'photo_print'), ('CS04', 'photo_fading'), ('CS02', 'mug_detail'),
                  ('CS08', 'real_mug'), ('CS06', 'stitch_hands')]
TABLE_SHOTS = [(scene, shot) for scene, shots in TABLE_OVER_FIGURE.items() for shot in shots]
# Room table: far edge y=316, near edge y=369.
FAR_EDGE, NEAR_EDGE = 316, 369


def _render(scene_key, shot):
    renderer._illustration.cache_clear()
    scene = SCENES[scene_key]
    cue = next(c for c in scene.cues if c.shot == shot)
    frame = pygame.Surface(config.SIZE)
    frame.fill((0, 0, 0))
    renderer.StoryRenderer(config.SIZE).draw(frame, scene, cue, 1.0, 6.0, False)
    return frame


def _count(frame, colours, x_start=0, x_end=960, y_start=0, y_end=540, stride=2):
    return sum(1 for x in range(x_start, x_end, stride) for y in range(y_start, y_end, stride)
               if frame.get_at((x, y))[:3] in colours)


def _palm_rows(age, pose, x, y, scale):
    layout = figure_layout(age, pose)
    return [y + palm[1] * scale for palm in (layout.left_hand, layout.right_hand)]


@pytest.mark.parametrize('scene_key,shot', TABLE_SHOTS)
def test_every_seated_palm_area_shows_skin_not_table(scene_key, shot):
    """The original defect: the table plank covered each forearm and palm."""
    frame = _render(scene_key, shot)
    for age, pose, x, y, scale, _dress in TABLE_OVER_FIGURE[scene_key][shot]:
        for row in _palm_rows(age, pose, x, y, scale):
            band = range(round(row) - 22, round(row) + 23)
            near_hand = _count(frame, SKIN, y_start=max(0, band[0]), y_end=min(540, band[-1]))
            assert near_hand > 20, (f'{scene_key}/{shot} {age}/{pose}: no skin near the palm '
                                    f'(row {row:.0f}); the table is covering the hand ({near_hand} px)')


@pytest.mark.parametrize('scene_key,shot', TABLE_SHOTS)
def test_arm_is_continuous_from_torso_across_the_table_edge(scene_key, shot):
    frame = _render(scene_key, shot)
    for age, pose, x, y, scale, _dress in TABLE_OVER_FIGURE[scene_key][shot]:
        layout = figure_layout(age, pose)
        palm = _palm_rows(age, pose, x, y, scale)[0]
        if palm <= FAR_EDGE:
            continue  # figure sits entirely above the table edge in this shot
        shoulder = y + layout.shoulders[0][1] * scale
        # Band from just under the shoulder to the far table edge must carry
        # skin: that is the upper arm/forearm crossing toward the tabletop.
        above = _count(frame, SKIN, y_start=round(shoulder) + 12, y_end=FAR_EDGE)
        below = _count(frame, SKIN, y_start=FAR_EDGE, y_end=round(palm) + 20)
        assert above > 0 and below > 0, (f'{scene_key}/{shot} {age}/{pose}: arm breaks at the table '
                                         f'edge (shoulder={shoulder:.0f}, above={above}, below={below})')


@pytest.mark.parametrize('age,brush', [
    ('old', (284, 90, 1.10)), ('adult', (513, 112, 1.05)), ('adult', (535, 113, 1.01)),
])
def test_seated_palm_lands_on_the_tabletop_surface(age, brush):
    layout = figure_layout(age, 'seated')
    for palm in (layout.left_hand, layout.right_hand):
        world_y = brush[1] + palm[1] * brush[2]
        assert FAR_EDGE < world_y < NEAR_EDGE, f'{age} {brush}: palm y={world_y:.1f} is not on the tabletop'


@pytest.mark.parametrize('scene_key,shot', [(k, s) for k, shots in TABLE_OVER_FIGURE.items() for s in shots])
def test_repaint_keeps_the_table_visible_and_the_skirt_behind_it(scene_key, shot):
    frame = _render(scene_key, shot)
    assert _count(frame, TABLE_SURFACE) > 2000, f'{scene_key}/{shot}: the table was painted away'
    # Below the table's near edge the apron/legs must stay table-coloured, not dress.
    assert _count(frame, TABLE_SURFACE, y_start=NEAR_EDGE + 6, y_end=NEAR_EDGE + 90) > 200


@pytest.mark.parametrize('scene_key,shot', TABLE_CLOSEUPS)
def test_table_closeups_keep_their_tabletop_foreground(scene_key, shot):
    frame = _render(scene_key, shot)
    assert _count(frame, TABLE_SURFACE) > 2000, f'{scene_key}/{shot}: close-up table surface regressed'


@pytest.mark.parametrize('age,pose', [('adult', 'seated'), ('old', 'seated'), ('adult', 'standing'),
                                      ('old', 'standing'), ('child', 'standing'), ('adult', 'tea'),
                                      ('old', 'cloth'), ('adult', 'offer')])
def test_splitting_arms_into_two_passes_is_pixel_identical(age, pose):
    """The refactor must not change a single pixel of an already-correct shot."""
    from nur_game.illustration import Ink

    direct, split = Ink((320, 420)), Ink((320, 420))
    renderer._human(renderer._Brush(direct, 40, 20, 1.1), age, pose)
    renderer._human(renderer._Brush(split, 40, 20, 1.1), age, pose, arms=False)
    renderer._human(renderer._Brush(split, 40, 20, 1.1), age, pose, arms='only')
    assert (pygame.image.tobytes(direct.finish(), 'RGBA')
            == pygame.image.tobytes(split.finish(), 'RGBA')), f'{age}/{pose}: two-pass arms differ from one pass'
