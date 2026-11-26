"""Geometric/pixel contracts for original portraits, not proof of visual quality.

Use the actual supersampled Ink and renderer brush, with no Game/audio fixture.
A human review of the final composed shots remains necessary.
"""
import importlib
from dataclasses import FrozenInstanceError

import pygame
import pytest


def portraits():
    try:
        return importlib.import_module("nur_game.cinematics.portraits")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Curved story portrait module is missing: {exc}")


def test_layout_is_immutable_with_age_specific_anatomy_and_legacy_lap_anchors():
    module = portraits()
    adult = module.figure_layout()
    old = module.figure_layout(age="old")
    child = module.figure_layout(age="child")
    assert isinstance(adult, module.FigureLayout)
    assert adult.head == (58, 20, 64, 75)
    assert adult.head[0] + adult.head[2] / 2 == 90
    assert adult.body_height == 320
    assert adult.left_hand == (51, 233)
    assert adult.right_hand == (111, 235)
    assert old.head == adult.head
    assert child.body_height < adult.body_height * .85
    assert child.head[3] / child.body_height > adult.head[3] / adult.body_height * 1.25
    assert child.shoulders != adult.shoulders
    assert child.left_hand[1] < adult.left_hand[1]
    with pytest.raises(FrozenInstanceError):
        adult.left_hand = (0, 0)
    with pytest.raises(TypeError):
        adult.head[0] = 0


class PaintedInk:
    """Record contour detail while forwarding every operation to real Ink."""
    def __new__(cls, size):
        from nur_game.illustration import Ink

        class RecordingInk(Ink):
            def __init__(self, size):
                super().__init__(size)
                self.contours = []
                self.line_widths = []

            def poly(self, colour, points, width=0):
                self.contours.append(tuple(points))
                return super().poly(colour, points, width)

            def line(self, colour, start, end, width=1):
                self.line_widths.append(width)
                return super().line(colour, start, end, width)

        return RecordingInk(size)


def paint(**kwargs):
    from nur_game.cinematics.renderer import _Brush

    art = PaintedInk((240, 360))
    layout = portraits().paint_figure(_Brush(art, 30, 10), **kwargs)
    return art, art.finish(), layout


@pytest.mark.parametrize("pose", ["standing", "seated"])
def test_real_painting_has_curved_bounded_connected_age_specific_silhouettes(pose):
    audio_before = pygame.mixer.get_init()
    painted = {}
    for age, identity in (("adult", "nur"), ("old", "nur"),
                          ("adult", "dara"), ("child", "dara")):
        art, image, layout = paint(age=age, pose=pose, identity=identity)
        assert layout == portraits().figure_layout(age, pose)
        mask = pygame.mask.from_surface(image, 127)
        bounds = mask.get_bounding_rects()
        assert len(bounds) == 1, "Hair, head, neck, sleeves, hands and feet must join"
        assert pygame.Rect(40, 20, 170, 315).contains(bounds[0])
        assert bounds[0].bottom <= 10 + layout.body_height + 2
        assert len([p for p in art.contours if len(p) >= 32]) >= 12
        assert all(p[0] == p[-1] for p in art.contours if len(p) >= 32)
        assert max(art.line_widths, default=0) <= 2, "Limbs are contours, not thick rods"
        painted[age, identity] = image
    adult = painted["adult", "nur"]
    child = painted["child", "dara"]
    adult_bounds = pygame.mask.from_surface(adult).get_bounding_rects()[0]
    child_bounds = pygame.mask.from_surface(child).get_bounding_rects()[0]
    assert child_bounds.height < adult_bounds.height * .85
    assert child_bounds.width > adult_bounds.width * .75, "Not a uniformly shrunk adult"
    # Direct pixel differences establish artwork changes, not aesthetic approval.
    head_roi = (70, 20, 120, 115)
    heads = [pygame.image.tobytes(image.subsurface(head_roi), "RGBA")
             for image in painted.values()]
    assert len(set(heads)) == 4, "Nur's bob/bun, Dara's ponytail, and child head differ"
    assert pygame.mixer.get_init() == audio_before


@pytest.mark.parametrize("pose,expected", [
    ("seated", ((51, 233), (111, 235))),
    ("standing", ((48, 220), (133, 223))),
    ("tea", ((87, 183), (132, 194))),
    ("cloth", ((65, 228), (112, 230))),
    ("offer", ((64, 230), (158, 207))),
    ("sew", ((19, 205), (149, 184))),
    ("tie", ((240, 114), (200, 124))),
])
def test_pose_anchors_turn_with_connected_painted_forearms(pose, expected):
    module = portraits()
    canonical = module.figure_layout(pose=pose)
    assert (canonical.left_hand, canonical.right_hand) == expected
    if pose == "offer":
        assert canonical.right_hand[0] > canonical.shoulders[1][0]
    for age in ("adult", "old", "child"):
        for facing in (1, -1):
            layout = module.figure_layout(age, pose, facing)
            original = module.figure_layout(age, pose, 1)
            mirror = lambda p: (180-p[0], p[1])
            assert layout.left_hand == (original.left_hand if facing == 1 else mirror(original.left_hand))
            assert layout.right_hand == (original.right_hand if facing == 1 else mirror(original.right_hand))
            assert layout.shoulders == (original.shoulders if facing == 1 else tuple(map(mirror, original.shoulders)))
            assert layout.elbows == (original.elbows if facing == 1 else tuple(map(mirror, original.elbows)))
            assert layout.hand_directions == tuple(d*facing for d in original.hand_directions)
            # Larger canvas accommodates tie's intentional reach beyond 180-wide body.
            from nur_game.cinematics.renderer import _Brush
            art = PaintedInk((400, 360))
            returned = module.paint_figure(_Brush(art, 90, 10), age, pose, facing=facing)
            assert returned == layout
            image = art.finish()
            mask = pygame.mask.from_surface(image, 127)
            assert len(mask.get_bounding_rects()) == 1
            for anchor in (layout.left_hand, layout.right_hand):
                assert mask.get_at((round(anchor[0]+90), round(anchor[1]+10)))
            assert max(art.line_widths, default=0) <= 2
    # Turn the silhouette and the face, not only attachment metadata.
    _, right, _ = paint(pose=pose, facing=1)
    _, left, _ = paint(pose=pose, facing=-1)
    if pose != "tie":
        r = pygame.mask.from_surface(right)
        l = pygame.mask.from_surface(pygame.transform.flip(left, True, False))
        assert r.overlap_area(l, (0, 0)) / r.count() > .97
    roi = (75, 35, 100, 80)
    assert pygame.image.tobytes(right.subsurface(roi), "RGBA") != pygame.image.tobytes(left.subsurface(roi), "RGBA")


@pytest.mark.parametrize("old", [False, True])
def test_compact_closed_hands_mirror_thumb_exactly_without_finger_spokes(old):
    from nur_game.cinematics.renderer import _Brush

    module = portraits()
    arts = []
    for direction in (1, -1):
        art = PaintedInk((121, 80))
        module.paint_hand(_Brush(art), 60, 40, direction, old)
        raw = art.surface.subsurface((0, 0, 241, 160))
        image = art.finish()
        mask = pygame.mask.from_surface(image)
        bounds = mask.get_bounding_rects()
        assert len(bounds) == 1
        assert 30 <= bounds[0].width <= 36
        assert 18 <= bounds[0].height <= 25
        assert pygame.Rect(42, 28, 37, 25).contains(bounds[0])
        assert not art.line_widths
        assert all(p[0] == p[-1] and len(p) >= 43 for p in art.contours)
        arts.append((art, raw))
    a, b = arts
    assert len(a[0].contours) == len(b[0].contours)
    for right, left in zip(a[0].contours, b[0].contours):
        assert left == tuple((120-x, y) for x, y in right)
    # Rasterization of reflected edge vertices can differ by one edge pixel;
    # require near-exact raw alpha agreement in addition to exact geometry.
    r = pygame.mask.from_surface(a[1])
    l = pygame.mask.from_surface(pygame.transform.flip(b[1], True, False))
    assert r.overlap_area(l, (0, 0)) / r.count() > .985


@pytest.mark.parametrize("age,identity", [("adult", "nur"), ("old", "nur"),
                                           ("adult", "dara"), ("child", "dara")])
def test_head_painting_preserves_parent_face_envelope(age, identity):
    from nur_game.cinematics.renderer import _Brush

    module = portraits()
    art = PaintedInk((180, 150))
    module._head(_Brush(art), module.figure_layout(age), age, identity)
    bounds = pygame.mask.from_surface(art.finish()).get_bounding_rects()
    assert len(bounds) == 1
    assert pygame.Rect(45, 18, 101, 109).contains(bounds[0])


@pytest.mark.parametrize("kwargs", [{"age": "baby"}, {"pose": "dance"},
                                    {"facing": 0}, {"identity": "unknown"}])
def test_invalid_figure_options_fail_before_any_pixels_are_painted(kwargs):
    from nur_game.cinematics.renderer import _Brush

    art = PaintedInk((180, 330))
    with pytest.raises(ValueError):
        portraits().paint_figure(_Brush(art), **kwargs)
    assert pygame.mask.from_surface(art.finish()).count() == 0


def test_bent_limb_edges_are_curved_at_elbow_not_straight_rods_with_round_caps():
    from nur_game.cinematics.renderer import _Brush

    module = portraits()
    art = PaintedInk((200, 220))
    module._limb(_Brush(art), module.SKIN, (40, 60), (90, 130),
                 (160, 70), (22, 18, 11))
    points = art.contours[0]
    a, middle, bend = points[0], points[7], points[14]
    area = abs((bend[0]-a[0])*(middle[1]-a[1]) -
               (bend[1]-a[1])*(middle[0]-a[0]))
    assert area > 25, "A sampled cubic on a straight rod is still a straight rod"
    mask = pygame.mask.from_surface(art.finish())
    assert len(mask.get_bounding_rects()) == 1
    assert mask.get_at((90, 130))
