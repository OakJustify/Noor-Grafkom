"""Storybook anatomy in 180 x 330 local coordinates.

The brush owns scaling/translation; layouts are immutable prop attachment data.
This module does not initialize Pygame, fonts, audio, or load external assets.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

Point = tuple[float, float]
SKIN = (211, 162, 122)
LIGHT = (231, 186, 146)
SHADE = (177, 122, 94)


@dataclass(frozen=True)
class FigureLayout:
    head: tuple[float, float, float, float]
    left_hand: Point
    right_hand: Point
    body_height: float
    shoulders: tuple[Point, Point]
    elbows: tuple[Point, Point]
    hand_directions: tuple[int, int] = (1, -1)
    hand_scale: float = 1


def figure_layout(age="adult", pose="seated", facing=1) -> FigureLayout:
    """Return palm centers, already oriented toward the companion.

    Left/right name the original drawing's limbs, not screen-order after a turn.
    body_height is the local foot baseline, not a scale multiplier.
    """
    if age not in {"adult", "old", "child"}:
        raise ValueError(f"Unsupported age: {age}")
    if pose not in {"seated", "standing", "tea", "cloth", "offer", "sew", "tie"}:
        raise ValueError(f"Unsupported pose: {pose}")
    if facing not in (-1, 1):
        raise ValueError("facing must be -1 (left) or 1 (right)")
    child = age == "child"
    if child:
        head, bottom, scale = (55, 24, 70, 78), 252, .72
        shoulders = ((62, 119), (119, 119))
        poses = {
            "seated": ((67, 186), (114, 188), (52, 157), (133, 158), (1, -1)),
            "standing": ((59, 181), (128, 185), (51, 155), (132, 155), (1, -1)),
            "tea": ((89, 150), (129, 158), (54, 153), (136, 146), (1, -1)),
            "cloth": ((74, 184), (111, 187), (56, 163), (132, 163), (1, -1)),
            "offer": ((77, 184), (146, 166), (59, 160), (132, 146), (1, 1)),
            "sew": ((36, 168), (140, 154), (46, 150), (132, 145), (-1, 1)),
            "tie": ((184, 112), (158, 119), (135, 146), (142, 145), (1, 1)),
        }
    else:
        head, bottom, scale = (58, 20, 64, 75), 320, 1
        shoulders = ((52, 129), (125, 129))
        poses = {
            "seated": ((51, 233), (111, 235), (37, 191), (141, 192), (1, -1)),
            "standing": ((48, 220), (133, 223), (36, 181), (144, 181), (1, -1)),
            "tea": ((87, 183), (132, 194), (37, 184), (145, 172), (1, -1)),
            "cloth": ((65, 228), (112, 230), (38, 194), (142, 194), (1, -1)),
            "offer": ((64, 230), (158, 207), (38, 192), (141, 178), (1, 1)),
            "sew": ((19, 205), (149, 184), (33, 179), (144, 168), (-1, 1)),
            "tie": ((240, 114), (200, 124), (178, 173), (168, 161), (1, 1)),
        }
    left, right, le, re, directions = poses[pose]
    if facing == -1:
        left, right = (180-left[0], left[1]), (180-right[0], right[1])
        shoulders = tuple((180-x, y) for x, y in shoulders)
        le, re = (180-le[0], le[1]), (180-re[0], re[1])
        directions = tuple(-d for d in directions)
        head = (180-head[0]-head[2], *head[1:])
    return FigureLayout(head, left, right, bottom, shoulders, (le, re), directions, scale)


class _View:
    """Nest local contour transforms without depending on a concrete Brush."""
    def __init__(self, brush, x: float = 0, y: float = 0,
                 sx: float = 1, sy: float = 1):
        self.brush, self.x, self.y, self.sx, self.sy = brush, x, y, sx, sy

    def poly(self, colour, points, width=0):
        # Reflect the positive-coordinate result rather than re-associating
        # floating arithmetic: mirrored hands retain exactly paired vertices.
        transformed = []
        for x, y in points:
            px = self.x + x * abs(self.sx)
            if self.sx < 0:
                px = 2*self.x - px
            transformed.append((px, self.y + y * self.sy))
        self.brush.poly(colour, transformed, width)


def _shape(b, colour, start, *segments, outline=None):
    """Fill a closed chain of cubic Beziers, including the curved closing edge.

    Every segment is (control1, control2, endpoint); 14 subdivisions retain
    smooth silhouettes even when the parent supersamples a close-up.
    """
    points = [start]
    origin = start
    for c1, c2, end in segments:
        for step in range(1, 15):
            t = step / 14
            u = 1 - t
            points.append((u**3 * origin[0] + 3*u*u*t*c1[0] + 3*u*t*t*c2[0] + t**3*end[0],
                           u**3 * origin[1] + 3*u*u*t*c1[1] + 3*u*t*t*c2[1] + t**3*end[1]))
        origin = end
    if origin != start:
        raise ValueError("A contour must close with a cubic segment")
    b.poly(colour, points)
    if outline is not None:
        b.poly(outline, points, 1)


def _oval(b, colour, x, y, w, h, outline=None):
    k = .5522847498
    cx, cy, rx, ry = x + w/2, y + h/2, w/2, h/2
    _shape(b, colour, (cx, y),
           ((cx+k*rx, y), (x+w, cy-k*ry), (x+w, cy)),
           ((x+w, cy+k*ry), (cx+k*rx, y+h), (cx, y+h)),
           ((cx-k*rx, y+h), (x, cy+k*ry), (x, cy)),
           ((x, cy-k*ry), (cx-k*rx, y), (cx, y)), outline=outline)


def _limb(b, colour, start, bend, end, widths, outline=None):
    """A tapered, bent soft contour; shoulders and wrists are rounded caps."""
    normals = []
    for a, z in ((start, bend), (start, end), (bend, end)):
        dx, dy = z[0]-a[0], z[1]-a[1]
        length = max(math.hypot(dx, dy), 1)
        normals.append((-dy/length, dx/length))
    edges = []
    for side in (1, -1):
        edges.append([(p[0] + side*n[0]*w/2, p[1] + side*n[1]*w/2)
                      for p, n, w in zip((start, bend, end), normals, widths)])
    a, m, z = edges[0]
    aa, mm, zz = edges[1]
    # A shared nonzero tangent rounds the elbow on both sides. Collinear
    # control points would merely disguise straight rods as sampled Beziers.
    tangent = ((z[0]-a[0])*.19, (z[1]-a[1])*.19)
    back = ((aa[0]-zz[0])*.19, (aa[1]-zz[1])*.19)
    _shape(b, colour, a,
           ((a[0]+(m[0]-a[0])*.45, a[1]+(m[1]-a[1])*.45),
            (m[0]-tangent[0], m[1]-tangent[1]), m),
           ((m[0]+tangent[0], m[1]+tangent[1]),
            (z[0]-(z[0]-m[0])*.45, z[1]-(z[1]-m[1])*.45), z),
           ((z[0]+(end[0]-bend[0])*.12, z[1]+(end[1]-bend[1])*.12),
            (zz[0]+(end[0]-bend[0])*.12, zz[1]+(end[1]-bend[1])*.12), zz),
           ((zz[0]+(mm[0]-zz[0])*.45, zz[1]+(mm[1]-zz[1])*.45),
            (mm[0]-back[0], mm[1]-back[1]), mm),
           ((mm[0]+back[0], mm[1]+back[1]),
            (aa[0]-(aa[0]-mm[0])*.45, aa[1]-(aa[1]-mm[1])*.45), aa),
           ((aa[0]-(bend[0]-start[0])*.10, aa[1]-(bend[1]-start[1])*.10),
            (a[0]-(bend[0]-start[0])*.10, a[1]-(bend[1]-start[1])*.10), a),
           outline=outline)


def _palm(b, x, y, direction=1, old=False, scale: float = 1):
    hand = _View(b, x, y, direction*scale, scale)
    # Wrist at -12, fingers kept together; a single tucked thumb below the palm.
    _shape(hand, SKIN, (-16, -6),
           ((-10, -7), (-6, -11), (1, -10)),
           ((8, -11), (17, -8), (17, -3)),
           ((18, 1), (13, 5), (7, 5)),
           ((11, 9), (5, 13), (1, 11)),
           ((-3, 9), (-5, 6), (-8, 5)),
           ((-12, 4), (-15, 5), (-16, 4)),
           ((-17, 0), (-17, -3), (-16, -6)), outline=(145, 102, 82))
    _shape(hand, LIGHT, (-13, -5),
           ((-5, -9), (7, -10), (13, -5)),
           ((14, -2), (9, 0), (2, 0)),
           ((-5, 0), (-10, 1), (-13, -1)),
           ((-14, -2), (-14, -4), (-13, -5)))
    _shape(hand, SHADE, (2, 5),
           ((4, 5), (5, 6), (7, 6)),
           ((7, 7), (5, 8), (4, 8)),
           ((3, 7), (2, 6), (2, 5)))
    if old:
        _oval(hand, (192, 144, 109), -5, -4, 3, 2)


def paint_hand(b, x, y, direction=1, old=False):
    """Paint a compact palm centered on (x, y), with no attached arm.

    direction reflects the entire closed hand and tucked thumb about x.
    Figure hand anchors are palm centers, not the previous helper's top-left.
    """
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1")
    _palm(b, x, y, direction, old)


def _head(b, layout, age, identity, facing=1):
    x, y, w, h = layout.head
    face = _View(b, x, y, w/64, h/75)
    lighting = face if facing == 1 else _View(face, 64, 0, -1, 1)
    old = age == "old"
    hair = (151, 151, 139) if old else ((62, 48, 43) if identity == "nur" else (76, 53, 43))
    gleam = (186, 186, 170) if old else (104, 79, 61)
    if old:
        _oval(face, hair, -11, 18, 24, 29, (126, 126, 116))
        _oval(face, gleam, -8, 19, 15, 19)
    elif identity == "dara" and age != "child":
        _shape(face, hair, (5, 23),
               ((-7, 19), (-13, 32), (-10, 49)),
               ((-5, 66), (-14, 91), (-5, 102)),
               ((5, 93), (12, 67), (13, 42)),
               ((13, 33), (10, 27), (5, 23)))
    _shape(face, hair, (1, 5),
           ((17, -4), (45, -3), (57, 9)),
           ((68, 21), (70, 55), (63, 78)),
           ((46, 88), (9, 85), (-6, 72)),
           ((-11, 53), (-11, 18), (1, 5)))
    # Neck joins the jaw and shoulders, never a rectangular peg.
    _shape(face, SHADE, (21, 64),
           ((22, 76), (22, 83), (17, 90)),
           ((24, 100), (38, 99), (46, 88)),
           ((38, 80), (39, 75), (40, 66)),
           ((35, 62), (27, 62), (21, 64)))
    _shape(face, SKIN, (12, 14),
           ((26, 4), (48, 8), (55, 25)),
           ((58, 32), (57, 38), (61, 43)),
           ((66, 47), (63, 49), (59, 50)),
           ((59, 64), (48, 75), (35, 75)),
           ((17, 75), (7, 60), (6, 41)),
           ((4, 29), (4, 20), (12, 14)), outline=(160, 116, 91))
    _shape(lighting, LIGHT, (14, 18),
           ((22, 12), (39, 13), (43, 22)),
           ((48, 32), (45, 43), (42, 51)),
           ((39, 61), (24, 68), (17, 56)),
           ((9, 47), (8, 29), (14, 18)))
    _oval(face, SKIN, 1, 36, 11, 16)
    _oval(face, LIGHT, 3, 38, 5, 9)
    # Three-quarter turn: unequal eyes, nose offset toward the companion.
    for ex, ey, ew in ((29, 39, 3.4), (49, 38, 2.6)):
        _oval(face, (64, 55, 48), ex, ey, ew, 2.6)
        _oval(face, hair, ex-1, ey-5, ew+3, 1.5)
    _shape(face, SHADE, (47, 41),
           ((47, 46), (49, 49), (51, 51)),
           ((52, 52), (49, 53), (47, 51)),
           ((46, 48), (46, 44), (47, 41)))
    _shape(face, (145, 91, 79), (36, 62),
           ((39, 63), (43, 63), (47, 61)),
           ((45, 65), (40, 66), (36, 62)))
    if old:
        _oval(face, (198, 148, 113), 17, 50, 5, 2)
        _oval(face, (198, 148, 113), 49, 48, 4, 2)
    if identity == "dara" and age == "child":
        _shape(face, hair, (2, 9),
               ((16, -2), (46, -1), (60, 15)),
               ((63, 20), (60, 27), (55, 28)),
               ((47, 27), (46, 21), (40, 21)),
               ((29, 30), (16, 26), (10, 29)),
               ((5, 38), (3, 40), (0, 43)),
               ((-5, 29), (-4, 17), (2, 9)))
    else:
        _shape(face, hair, (1, 9),
               ((16, -3), (46, -2), (60, 15)),
               ((63, 20), (65, 25), (65, 33)),
               ((57, 27), (51, 22), (40, 17)),
               ((29, 24), (16, 25), (10, 31)),
               ((8, 45), (8, 53), (4, 57)),
               ((-3, 44), (-5, 24), (1, 9)))
    _shape(lighting, gleam, (6, 11),
           ((14, 4), (27, 3), (37, 7)),
           ((28, 6), (16, 8), (9, 14)),
           ((7, 15), (6, 13), (6, 11)))


def paint_arms(b, layout, dress=(81, 116, 112), facing=1, old=False):
    """Paint both forearms and palms for one figure, given its pose layout.

    Split out of paint_figure so a renderer can re-paint arms after a
    foreground table.  A seated arm line leaves the torso behind the table and
    rests on the tabletop surface, which is nearer to the viewer; drawing the
    table afterwards would cover the forearm and palm and leave a floating
    torso.  Applies the facing transform exactly once, so re-painted arms land
    on the same pixels as the original pass.
    """
    b = _View(b, 180 if facing == -1 else 0, 0, facing, 1)
    dark = tuple(max(0, c-19) for c in dress)
    for shoulder, elbow, palm, direction in zip(layout.shoulders, layout.elbows,
                                               (layout.left_hand, layout.right_hand),
                                               layout.hand_directions):
        scale = layout.hand_scale
        wrist = (palm[0]-12*direction*scale, palm[1])
        cuff = (shoulder[0]*.30+elbow[0]*.70, shoulder[1]*.30+elbow[1]*.70)
        bend = (elbow[0], elbow[1])
        _limb(b, SKIN, cuff, bend, wrist, (17*scale, 16*scale, 11*scale),
              outline=(159, 113, 88))
        _limb(b, LIGHT, (cuff[0]-2*facing, cuff[1]-2),
              (bend[0]-2*facing, bend[1]-2),
              (wrist[0]-facing, wrist[1]-2), (7*scale, 7*scale, 4*scale))
        _limb(b, dress, shoulder,
              (shoulder[0]*.5+cuff[0]*.5, shoulder[1]*.5+cuff[1]*.5),
              cuff, (25*scale, 24*scale, 20*scale), outline=dark)
        _palm(b, *palm, direction, old, scale)


def paint_figure(b, age="adult", pose="seated", dress=(81, 116, 112),
                 facing=1, identity="nur", arms: bool | str = True) -> FigureLayout:
    """Paint one clothed figure and its chair, without story props.

    arms=False omits the limbs, arms='only' paints them alone (used to raise
    them above a foreground table), arms=True paints the whole figure.
    """
    result = figure_layout(age, pose, facing)
    if identity not in {"nur", "dara"}:
        raise ValueError(f"Unsupported identity: {identity}")
    layout = figure_layout(age, pose, 1)
    if arms == "only":
        paint_arms(b, layout, dress, facing, age == "old")
        return result
    raw = b
    b = _View(b, 180 if facing == -1 else 0, 0, facing, 1)
    child = age == "child"
    seated = pose in {"seated", "tea", "cloth", "offer"}
    bottom = layout.body_height
    hem = 202 if child else 257
    top = 114 if child else 109
    dark = tuple(max(0, c-19) for c in dress)
    bright = tuple(min(255, c+19) for c in dress)
    if seated:
        chair = _View(b, 90, 0, .79 if child else 1, 1)
        ct, cy = (125, 204) if child else (130, 263)
        _shape(chair, (117, 82, 59), (-64, ct+15),
               ((-65, ct-2), (65, ct-2), (64, ct+15)),
               ((67, cy-10), (66, cy), (53, cy)),
               ((20, cy+3), (-30, cy+3), (-54, cy)),
               ((-66, cy), (-65, ct+35), (-64, ct+15)))
        for xx in (-55, 56):
            _limb(chair, (99, 71, 53), (xx, cy-6), (xx, bottom-30),
                  (xx-4, bottom-3), (8, 7, 6))
    for xx, tilt in ((70, -5), (113, 8)):
        _limb(b, (101, 96, 84), (xx, hem-15),
              (xx+tilt*.4, hem+23), (xx+tilt, bottom-8), (22 if not child else 16, 16, 13))
        _oval(b, (68, 61, 54), xx+tilt-18, bottom-14, 36, 14)
        _oval(b, (108, 93, 75), xx+tilt-13, bottom-13, 21, 4)
    # Broad rounded shoulder line, fitted waist, then a curved lap or skirt.
    left, right = (53, 129) if child else (42, 139)
    _shape(b, dress, (72, top),
           ((60, top+2), (left, top+14), (left, top+31)),
           ((left+2, hem-43), (left-6, hem-10), (left-3, hem)),
           ((65, hem+7), (120, hem+8), (right+13, hem)),
           ((right+19, hem-13), (right-1, hem-41), (right+7, top+34)),
           ((right+9, top+14), (113, top+2), (101, top)),
           ((91, top+4), (80, top+4), (72, top)), outline=dark)
    _shape(b, dark if facing == 1 else bright, (115, top+22),
           ((128, top+34), (119, hem-37), (141 if not child else 137, hem-1)),
           ((132, hem+3), (122, hem+4), (110, hem+4)),
           ((115, hem-25), (111, top+55), (115, top+22)))
    _shape(b, bright if facing == 1 else dark, (64, top+24),
           ((59, top+54), (57, hem-24), (51 if not child else 59, hem-2)),
           ((58, hem), (61, hem), (65, hem-1)),
           ((65, hem-24), (69, top+46), (64, top+24)))
    if seated:
        _shape(b, bright, (49 if not child else 58, hem-35),
               ((74, hem-47), (112, hem-42), (135, hem-24)),
               ((116, hem-32), (78, hem-32), (49 if not child else 58, hem-35)))
    _head(b, layout, age, identity, facing)
    # Restrained ivory collar follows the neckline, not a large angular bib.
    _shape(b, (229, 216, 183), (70, top+3),
           ((76, top+7), (91, top+17), (105, top+2)),
           ((103, top+13), (96, top+19), (89, top+20)),
           ((80, top+17), (73, top+13), (70, top+3)))
    if arms:
        # raw already carries the caller's brush; paint_arms re-applies facing.
        paint_arms(raw, layout, dress, facing, age == "old")
    return result
