"""Geometric framing regressions; these do not certify artistic quality."""

import pygame
import pytest

from nur_game.cinematics import renderer


@pytest.mark.parametrize('shot', ['ribbon_school', 'bag_door', 'mug_drawing'])
def test_family_shots_do_not_crop_the_adult_face_above_the_frame(shot, monkeypatch):
    renderer._illustration.cache_clear()
    calls = []
    original = renderer._human

    def record(brush, age='adult', pose='seated', dress=renderer.TEAL, **kwargs):
        # Conservative envelope of the head, covering both original and new art.
        head = pygame.Rect(round(brush.x + 45 * brush.scale),
                           round(brush.y + 18 * brush.scale),
                           round(100 * brush.scale), round(108 * brush.scale))
        calls.append((age, head))
        return original(brush, age, pose, dress, **kwargs)

    monkeypatch.setattr(renderer, '_human', record)
    image = renderer._illustration(shot)
    frame = image.get_rect()
    assert calls
    for age, head in calls:
        assert frame.contains(head), f'{shot}: {age} head is outside the image: {head}'
    renderer._illustration.cache_clear()


def test_renderer_paints_child_anatomy_instead_of_a_scaled_adult_template():
    from nur_game.illustration import Ink

    adult_ink, child_ink = Ink((180, 330)), Ink((180, 330))
    adult = renderer._human(renderer._Brush(adult_ink), 'adult', 'standing')
    child = renderer._human(renderer._Brush(child_ink), 'child', 'standing')
    assert adult is not None and child is not None, 'Renderer must use measured age-specific anatomy'
    assert child.body_height < adult.body_height
    assert child.head[3] / child.body_height > adult.head[3] / adult.body_height
    assert pygame.surfarray.array_alpha(adult_ink.finish()).any()
    assert pygame.surfarray.array_alpha(child_ink.finish()).any()
