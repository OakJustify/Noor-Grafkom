"""Original storybook cutscene illustrations, drawn with Pygame only.

All artwork is vector geometry baked into supersampled, cached surfaces. No
external images, voice clips, synthesised speech, or mixer calls are used here.
"""
from __future__ import annotations

import math
from functools import lru_cache

import pygame

from ..illustration import Ink
from .catalog import CLOSING_LINES, Cue, Scene
from .portraits import paint_figure, paint_hand

INK = (52, 57, 57)
SKIN = (211, 162, 122)
SKIN_LIGHT = (231, 186, 146)
SKIN_SHADE = (177, 122, 94)
WOOD = (121, 83, 57)
RED = (178, 57, 57)
BLUE = (68, 128, 161)
TEAL = (81, 116, 112)


@lru_cache(maxsize=32)
def _cached_font(size: int) -> pygame.font.Font:
    return pygame.font.Font(None, size)


def _font(size: int) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
        _cached_font.cache_clear()
    font = _cached_font(size)
    try:
        font.get_height()
    except pygame.error:
        # pygame.init() may already have reopened TTF since the old handle died.
        _cached_font.cache_clear()
        font = _cached_font(size)
    return font


class _Brush:
    """Local coordinates let the same hand/prop retain its shape in every shot."""

    def __init__(self, art: Ink, x: float = 0, y: float = 0, scale: float = 1):
        self.art, self.x, self.y, self.scale = art, x, y, scale

    def point(self, p) -> tuple[float, float]:
        return self.x + p[0] * self.scale, self.y + p[1] * self.scale

    def rect(self, colour, rect, width=0, radius=0):
        x, y = self.point(rect)
        self.art.rect(colour, (x, y, rect[2] * self.scale, rect[3] * self.scale),
                      round(width * self.scale), round(radius * self.scale))

    def ellipse(self, colour, rect, width=0):
        x, y = self.point(rect)
        self.art.ellipse(colour, (x, y, rect[2] * self.scale, rect[3] * self.scale), round(width * self.scale))

    def poly(self, colour, points, width=0):
        self.art.poly(colour, [self.point(p) for p in points], round(width * self.scale))

    def line(self, colour, start, end, width=1):
        self.art.line(colour, self.point(start), self.point(end), max(1, round(width * self.scale)))

    def text(self, text, pos, size, colour):
        label = _font(round(size * self.scale * 2)).render(text, True, colour)
        x, y = self.point(pos)
        self.art.surface.blit(label, (round(x * 2), round(y * 2)))


def _hand(b, x, y, direction=1, old=False):
    # Preserve the close-up helper's top-left coordinates, not its finger spokes.
    paint_hand(b, x + 16, y + 9, direction, old)


def _ribbon(b):
    # Unequal loops and a lowered right loop: the crooked knot is consistent.
    b.poly(RED, [(37, 30), (4, 4), (2, 28), (12, 38), (36, 33)])
    b.poly((203, 76, 69), [(37, 30), (71, 17), (70, 44), (56, 47), (36, 34)])
    b.poly((153, 43, 49), [(31, 31), (20, 70), (31, 62), (40, 69), (44, 35)])
    b.poly(RED, [(42, 33), (49, 65), (58, 57), (65, 62), (52, 33)])
    b.poly((122, 39, 44), [(31, 22), (43, 25), (48, 38), (35, 41)])
    b.line((233, 112, 92), (8, 11), (28, 26), 2)
    b.line((237, 124, 100), (45, 29), (64, 25), 2)


def _mug(b):
    b.ellipse((165, 144, 116), (0, 66, 112, 15))
    b.ellipse(BLUE, (77, 21, 33, 43), 8)
    b.ellipse((135, 190, 204), (79, 24, 28, 37), 2)
    b.rect(BLUE, (13, 16, 73, 54), radius=9)
    b.ellipse((54, 105, 139), (13, 58, 73, 15))
    b.rect((98, 154, 182), (17, 19, 11, 41), radius=4)
    b.ellipse((173, 213, 217), (12, 9, 74, 20))
    b.ellipse((100, 67, 45), (18, 14, 61, 11))
    b.line((190, 216, 215), (29, 66), (70, 66), 2)
    # Hairline crack just beside the right-hand handle, not an arbitrary stripe.
    for a, z in (((72, 21), (66, 31)), ((66, 31), (72, 40)), ((72, 40), (69, 49))):
        b.line((40, 72, 85), a, z, 2)


def _key(b):
    b.ellipse((111, 82, 42), (6, 3, 37, 37), 8)
    b.ellipse((209, 166, 79), (5, 2, 35, 35), 6)
    b.line((209, 166, 79), (29, 32), (67, 69), 9)
    b.line((245, 211, 132), (30, 32), (62, 63), 2)
    b.poly((194, 145, 60), [(57, 60), (72, 58), (78, 64), (69, 72), (75, 78), (68, 83), (55, 69)])


def _cloth(b):
    b.poly((152, 156, 133), [(3, 4), (140, 0), (152, 92), (0, 96)])
    b.poly((233, 218, 181), [(0, 0), (134, 0), (146, 86), (2, 90)])
    for y in range(8, 85, 7):
        b.line((205, 189, 152), (8, y), (135, y + 1))
    for x in range(9, 130, 9):
        b.line((217, 204, 166), (x, 7), (x + 6, 83))
    b.text("DARA", (20, 24), 32, (98, 106, 105))
    for x in range(21, 109, 5):
        b.line((75, 111, 131), (x, 54), (x + 3, 56), 2)
    # One child's stitch wanders outside the pencilled baseline.
    b.line(RED, (88, 50), (96, 63), 2)
    b.line(RED, (96, 63), (101, 53), 2)
    _ribbon(_Brush(b.art, *b.point((111, -12)), b.scale * .42))


def _recipe(b):
    b.poly((112, 86, 56), [(1, 8), (72, 4), (144, 10), (149, 94), (71, 88), (0, 95)])
    b.poly((229, 212, 173), [(0, 0), (69, 3), (72, 85), (0, 91)])
    b.poly((243, 225, 186), [(69, 3), (140, 0), (146, 90), (72, 85)])
    b.line((170, 141, 105), (69, 5), (72, 82), 2)
    b.text("Teh manis", (8, 12), 17, (94, 82, 64))
    for row in range(5):
        for left in (10, 82):
            b.line((151, 125, 91), (left, 34 + row * 8), (left + 41 - row % 2 * 7, 32 + row * 8))
    b.ellipse((187, 154, 112), (107, 52, 25, 24), 2)


def _tree(b, x, y, scale: float = 1):
    t = _Brush(b.art, *b.point((x, y)), b.scale * scale)
    t.poly((109, 95, 65), [(45, 154), (49, 28), (63, 28), (64, 155)])
    t.line((109, 95, 65), (55, 78), (18, 36), 8)
    for dx, dy, w, h, colour in ((0, 20, 75, 66, (94, 133, 105)), (37, 8, 67, 63, (116, 150, 111)), (20, -8, 62, 56, (128, 160, 118))):
        t.ellipse(colour, (dx, dy, w, h))
    for dx, dy in ((18, 25), (55, 12), (72, 36)):
        t.line((155, 180, 129), (dx, dy), (dx + 14, dy - 3), 2)


def _house(b, x, y, scale: float = 1):
    h = _Brush(b.art, *b.point((x, y)), b.scale * scale)
    h.rect((218, 198, 159), (0, 38, 169, 115))
    h.poly((116, 99, 77), [(-12, 40), (76, -5), (180, 40)])
    h.line((179, 142, 96), (-10, 40), (179, 40), 3)
    h.rect((109, 114, 103), (75, 79, 37, 75))
    for xx in (18, 123):
        h.rect((146, 170, 165), (xx, 62, 28, 41))
        h.rect((247, 222, 175), (xx, 62, 28, 41), 3)
        h.line((230, 214, 175), (xx + 14, 63), (xx + 14, 102), 2)
    h.ellipse((209, 168, 90), (103, 113, 4, 4))


def _human(b, age="adult", pose="seated", dress=TEAL, *, facing=None, identity=None):
    if facing is None:
        facing = -1 if b.x >= 480 else 1
    if identity is None:
        identity = "dara" if age == "child" or dress != TEAL else "nur"
    layout = paint_figure(b, age, pose, dress, facing, identity)
    lx, ly = layout.left_hand
    rx, ry = layout.right_hand
    if pose == "tea":
        size = .50 * layout.hand_scale
        mug_x, mug_y = b.point(((lx + rx) / 2 - 56 * size, min(ly, ry) - 36 * size))
        _mug(_Brush(b.art, mug_x, mug_y, b.scale * size))
    elif pose == "cloth":
        cloth_x, cloth_y = b.point(((lx + rx) / 2 - 57, min(ly, ry) - 12))
        _cloth(_Brush(b.art, cloth_x, cloth_y, b.scale * .78))
    if pose in {"tea", "cloth"}:
        # Fingers rest on the prop instead of being erased by its painted body.
        for palm, direction in zip((layout.left_hand, layout.right_hand), layout.hand_directions):
            hand_x, hand_y = b.point(palm)
            hand = _Brush(b.art, hand_x, hand_y, b.scale * layout.hand_scale)
            paint_hand(hand, 0, 0, direction, age == "old")
    if age == "child":
        x, y, w, _ = layout.head
        ribbon_x = x + w - 10 if facing == 1 else x - 7
        ribbon_x, ribbon_y = b.point((ribbon_x, y + 4))
        _ribbon(_Brush(b.art, ribbon_x, ribbon_y, b.scale * .38))
    return layout


def _photo(b, folded=False, faded=False):
    b.rect((108, 84, 61), (0, 0, 156, 119), radius=2)
    b.rect((247, 229, 190), (4, 4, 148, 111))
    b.rect((184, 199, 172), (12, 12, 132, 88))
    _house(b, 18, 33, .40)
    _tree(b, 103, 24, .46)
    if not faded:
        _human(_Brush(b.art, *b.point((37, 31)), b.scale * .21), "adult", "standing")
        _human(_Brush(b.art, *b.point((74, 52)), b.scale * .14), "child", "standing", (173, 103, 81))
    else:
        b.ellipse((155, 151, 126), (51, 38, 15, 18))
        b.ellipse((155, 151, 126), (84, 61, 10, 12))
        _ribbon(_Brush(b.art, *b.point((91, 58)), b.scale * .13))
    if folded:
        b.poly((237, 219, 183), [(91, 6), (103, 7), (105, 105), (93, 110)])
        b.line((178, 160, 125), (93, 8), (97, 105))


def _room(art, kitchen=False):
    b = _Brush(art)
    b.rect((224, 206, 168), (0, 0, 960, 540))
    for y in range(0, 302, 13):
        b.line((219, 199, 161), (0, y), (960, y))
    b.rect((134, 147, 125), (0, 294, 960, 90))
    for x in range(0, 960, 100):
        b.rect((164, 166, 139), (x + 8, 307, 84, 58), 2)
    b.rect((110, 101, 77), (0, 379, 960, 161))
    for x in range(-300, 1300, 150):
        b.line((146, 121, 86), (480 + (x - 480) * .55, 380), (x, 540), 2)
    for y in (402, 437, 486):
        b.line((130, 109, 78), (0, y), (960, y), 2)
    # Window on the left: ordinary morning, no miraculous glow in the finale.
    b.rect((95, 111, 102), (70, 51, 181, 208))
    b.rect((179, 207, 190), (79, 60, 162, 189))
    _tree(b, 99, 108, .8)
    b.rect((243, 223, 176), (69, 50, 183, 210), 7)
    b.line((235, 211, 162), (159, 53), (159, 256), 6)
    b.line((237, 214, 165), (74, 152), (248, 152), 6)
    for x in (48, 243):
        b.poly((162, 171, 147), [(x, 39), (x + 40, 39), (x + 29, 168), (x + 40, 272), (x - 4, 272), (x + 11, 169)])
        for dx in (7, 17, 26):
            b.line((197, 194, 157), (x + dx, 45), (x + dx - 2, 145), 2)
    # Panelled door, key hook, framed family photograph and the child's drawing.
    b.rect((141, 102, 72), (789, 72, 142, 309), radius=5)
    for y in (88, 205):
        b.rect((175, 137, 91), (807, y, 105, 98), 3, radius=3)
    b.ellipse((228, 184, 100), (903, 240, 10, 10))
    b.rect((95, 92, 75), (744, 156, 25, 11), radius=2)
    _key(_Brush(art, 738, 171, .38))
    _photo(_Brush(art, 567, 49, .93))
    _drawing(_Brush(art, 580, 177, .64))
    if kitchen:
        b.rect((133, 145, 126), (14, 280, 249, 101))
        b.rect((164, 158, 124), (9, 271, 259, 16))
        for x in (29, 142):
            b.rect((183, 177, 140), (x, 298, 91, 67), 2)
        for x, hh in ((34, 36), (84, 45), (148, 32)):
            b.rect((211, 215, 178), (x, 271 - hh, 28, hh), radius=4)
            b.rect((104, 108, 87), (x - 2, 266 - hh, 32, 7))
    else:
        # Sewing cabinet, spools, fabric and hand wheel.
        b.rect((123, 91, 66), (24, 290, 220, 91))
        b.rect((179, 138, 92), (19, 282, 230, 14))
        for x in (45, 109, 173):
            b.rect((160, 119, 79), (x, 312, 46, 48), 2)
            b.ellipse((218, 176, 102), (x + 20, 327, 6, 6))
        b.rect((57, 80, 79), (95, 241, 82, 31), radius=8)
        b.rect((57, 80, 79), (97, 226, 19, 56), radius=5)
        b.ellipse((57, 80, 79), (166, 231, 38, 38), 5)
        b.line((212, 179, 130), (111, 257), (111, 279), 2)
        for x, colour in ((33, RED), (62, TEAL)):
            b.rect(colour, (x, 258, 15, 21))
            b.line((230, 204, 155), (x - 2, 257), (x + 17, 257), 3)


def _drawing(b):
    b.poly((243, 230, 194), [(0, 3), (122, 0), (126, 88), (2, 90)])
    _house(b, 9, 39, .41)
    _tree(b, 71, 12, .49)
    b.line((155, 163, 117), (8, 79), (115, 79), 2)
    b.text("rumah kita", (9, 7), 14, (143, 94, 72))


def _table(art, close=False):
    b = _Brush(art)
    if close:
        b.poly((163, 115, 72), [(65, 261), (879, 252), (1020, 540), (-40, 540)])
        for y in range(281, 540, 27):
            b.line((178, 131, 85), (52, y), (950, y - 4), 2)
        b.line((213, 164, 103), (68, 261), (878, 252), 4)
    else:
        b.poly((173, 125, 80), [(256, 316), (702, 316), (755, 369), (215, 369)])
        b.rect((112, 74, 52), (214, 369, 541, 14))
        for x in (243, 713):
            b.rect((100, 70, 51), (x, 383, 15, 96))
        for x in range(260, 700, 67):
            b.line((195, 148, 92), (x, 318), (x - 8, 364))
        b.line((215, 167, 107), (259, 318), (700, 318), 3)


def _outdoors(art, crossroads=False):
    b = _Brush(art)
    b.rect((174, 205, 193) if not crossroads else (198, 195, 168), (0, 0, 960, 540))
    b.ellipse((248, 222, 158), (689, 42, 73, 73))
    for x, y, w in ((91, 53, 191), (365, 77, 155)):
        b.ellipse((226, 224, 192), (x, y, w, 17))
    b.poly((139, 167, 133), [(0, 285), (174, 204), (381, 260), (618, 199), (960, 273), (960, 540), (0, 540)])
    _house(b, 105, 143, 1.3)
    _house(b, 691, 170, .9)
    _tree(b, 350, 131, 1.6)
    b.poly((184, 154, 104), [(0, 489), (436, 312), (490, 312), (960, 530), (960, 540), (0, 540)])
    if crossroads:
        b.poly((175, 149, 109), [(3, 321), (440, 315), (639, 406), (0, 398)])
    for x in range(7, 930, 63):
        y = 331 + abs(x - 470) * .10
        b.rect((157, 148, 109), (x, y, 11, 58), radius=2)
        b.line((204, 188, 143), (x, y + 14), (x + 57, y + 16), 5)
        b.line((184, 168, 128), (x, y + 37), (x + 57, y + 39), 4)
    for x in range(13, 960, 47):
        b.line((107, 142, 104), (x, 459), (x - 7, 441), 3)
        b.ellipse((224, 194, 126), (x + 4, 436, 5, 5))
    # A modest clothesline and bicycle, made of opaque ink geometry.
    b.line((104, 111, 96), (43, 150), (288, 126), 2)
    for x in (45, 91, 143):
        b.poly((213, 206, 171), [(x, 152), (x + 34, 148), (x + 37, 203), (x + 3, 207)])
    for x in (599, 662):
        b.ellipse((84, 103, 98), (x, 286, 46, 46), 3)
    b.poly((116, 108, 89), [(622, 309), (644, 278), (669, 309)], 3)
    b.line((116, 108, 89), (644, 278), (678, 277), 3)


def _wanderer(art, x, y, scale: float = 1):
    b = _Brush(art, x, y, scale)
    b.ellipse((84, 80, 64), (4, 91, 95, 14))
    b.poly((75, 104, 109), [(26, 31), (64, 30), (87, 89), (73, 101), (14, 96)])
    b.ellipse((102, 135, 134), (15, 2, 58, 58))
    b.ellipse((42, 64, 71), (29, 15, 33, 38))
    b.line((196, 173, 119), (32, 26), (30, 48), 2)
    b.line((91, 119, 119), (62, 52), (94, 65), 9)
    b.rect((168, 125, 66), (91, 70, 25, 28), radius=4)
    b.ellipse((174, 140, 77), (96, 56, 16, 22), 2)
    b.rect((240, 213, 131), (97, 75, 13, 17), radius=2)
    b.poly((255, 232, 156), [(103, 77), (99, 88), (108, 88)])
    b.line((208, 166, 90), (94, 96), (114, 96), 3)


@lru_cache(maxsize=48)
def _illustration(shot: str) -> pygame.Surface:
    art = Ink((960, 540))
    b = _Brush(art)
    if shot in {"morning_lane", "lantern_pickup", "red_fence"}:
        _outdoors(art)
        _wanderer(art, 396 if shot == "morning_lane" else 492, 291, 1.1)
        _ribbon(_Brush(art, 765, 333, .56 if shot != "red_fence" else .88))
        if shot == "lantern_pickup":
            _key(_Brush(art, 120, 290, .35))
    elif shot.startswith("crossroad"):
        _outdoors(art, True)
        if shot != "crossroad_empty":
            _human(_Brush(art, 335, 110, .89), "adult", "standing")
            _key(_Brush(art, 396, 308, .30))
            b.poly((189, 164, 116), [(357, 303), (398, 307), (404, 352), (352, 353)])
            b.ellipse((184, 156, 109), (366, 288, 24, 24), 3)
        if shot == "crossroad_together":
            _human(_Brush(art, 520, 123, .88), "adult", "standing", (173, 115, 89))
    elif shot == "photo_pose":
        _outdoors(art)
        _human(_Brush(art, 409, 95, .95), "adult", "standing")
        _human(_Brush(art, 558, 212, .60), "child", "standing", (187, 113, 83))
        _drawing(_Brush(art, 591, 328, .48))
    elif shot in {"photo_print", "photo_fading"}:
        _room(art)
        _table(art, True)
        _photo(_Brush(art, 290, 90, 2.42), faded=shot == "photo_fading")
        _hand(_Brush(art, 0, 0), 258, 313, old=True)
        _hand(_Brush(art, 0, 0), 670, 307, direction=-1, old=True)
    elif shot == "photo_fold":
        _room(art)
        _human(_Brush(art, 252, 85, 1.13), "old")
        _human(_Brush(art, 541, 99, 1.07), dress=(174, 115, 88))
        _photo(_Brush(art, 376, 293, .88), folded=True)
    elif shot in {"ribbon_hands", "ribbon_school", "bag_door"}:
        _room(art)
        if shot == "ribbon_hands":
            # Close hands preserve the adult's identity, rather than reveal a portrait.
            b.ellipse((68, 52, 46), (324, 167, 261, 250))
            b.ellipse((94, 71, 53), (326, 174, 251, 151))
            _ribbon(_Brush(art, 464, 159, 1.5))
            b.line(SKIN, (720, 67), (592, 188), 42)
            _hand(_Brush(art, 511, 144, 1.8), 0, 0)
            b.line(SKIN, (160, 160), (326, 209), 38)
            _hand(_Brush(art, 316, 187, 1.7), 0, 0)
        else:
            child_x = 302 if shot == "ribbon_school" else 704
            _human(_Brush(art, child_x, 183 if shot == "ribbon_school" else 178, .80), "child", "standing", (181, 111, 82))
            _human(_Brush(art, 430 if shot == "ribbon_school" else 450, 93 if shot == "ribbon_school" else 82, .98),
                   "adult", "tie" if shot == "ribbon_school" else "standing", facing=-1 if shot == "ribbon_school" else 1)
            bag_x = 348 if shot == "ribbon_school" else 708
            b.rect((119, 124, 98), (bag_x, 301, 53, 64), radius=8)
            b.ellipse((119, 124, 98), (bag_x + 7, 288, 36, 32), 4)
            if shot == "bag_door":
                b.line((98, 107, 85), (746, 279), (bag_x + 7, 305), 4)
    elif shot in {"mug_detail", "mug_drawing", "drawing_wall"}:
        _room(art)
        if shot == "mug_detail":
            _table(art, True)
            _mug(_Brush(art, 554, 192, 2.16))
            _drawing(_Brush(art, 177, 241, 1.64))
        elif shot == "mug_drawing":
            _human(_Brush(art, 267, 180, .84), "child", "standing", (181, 111, 82))
            _human(_Brush(art, 529, 84, .96), "adult", "seated")
            _table(art)
            _drawing(_Brush(art, 392, 303, .84))
            _mug(_Brush(art, 632, 294, .72))
        else:
            _drawing(_Brush(art, 341, 49, 2.25))
            b.rect((199, 178, 135), (660, 100, 90, 118))
            b.text("NOV", (676, 114), 25, INK)
            for x in range(675, 741, 14):
                for y in range(148, 204, 14):
                    b.ellipse((126, 119, 97), (x, y, 4, 4))
            _table(art)
            _mug(_Brush(art, 626, 291, .76))
    elif shot.startswith("recipe_"):
        _room(art, True)
        _human(_Brush(art, 294, 85, 1.09), "old", "tea" if shot == "recipe_tea" else "seated")
        _human(_Brush(art, 535, 113, 1.01), dress=(166, 118, 94))
        _table(art)
        _recipe(_Brush(art, 342, 308, 1.0))
        _mug(_Brush(art, 627, 294, .80))
        b.rect((224, 219, 179), (521, 301, 50, 43), radius=5)
        b.ellipse((154, 151, 125), (519, 296, 53, 10))
        b.text("gula", (526, 314), 17, (106, 103, 80))
        b.line((194, 194, 160), (651, 307), (675, 260), 3)
        b.ellipse((192, 194, 163), (665, 250, 17, 12))
        if shot == "recipe_stir":
            _hand(_Brush(art, 0, 0), 595, 276, old=True)
    elif shot == "stitch_hands":
        _room(art)
        _table(art, True)
        _cloth(_Brush(art, 235, 197, 3.08))
        _hand(_Brush(art, 161, 240, 2.0), 0, 0)
        _hand(_Brush(art, 626, 200, 2.25), 0, 0)
        b.line((80, 114, 134), (531, 342), (609, 232), 2)
        b.line((196, 192, 156), (607, 223), (631, 195), 2)
    elif shot.startswith("cloth_"):
        _room(art)
        _human(_Brush(art, 279, 81, 1.15), "old", "cloth")
        if shot != "cloth_wait":
            _human(_Brush(art, 732 if shot == "cloth_door" else 531, 88 if shot == "cloth_door" else 111, 1.04),
                   "adult", "standing" if shot == "cloth_door" else "seated", (169, 116, 91))
        _table(art)
        _ribbon(_Brush(art, 639, 337, .50))
    elif shot.startswith("void_"):
        b.rect((28, 36, 40), (0, 0, 960, 540))
        b.poly((76, 79, 70), [(0, 477), (418, 360), (536, 360), (850, 540), (0, 540)])
        b.line((106, 110, 93), (1, 477), (419, 360), 2)
        _wanderer(art, 421, 259, 1.35)
        if shot == "void_fragments":
            for index, key in enumerate(("F01", "F02", "F03", "F04", "F05", "F06")):
                image = pygame.transform.smoothscale(_fragment(key), (110, 110))
                art.surface.blit(image, (490 + index * 107, 400 - abs(index - 2) * 24))
    elif shot.startswith("real_"):
        _room(art)
        if shot == "real_mug":
            _table(art, True)
            _mug(_Brush(art, 572, 193, 2.1))
            _recipe(_Brush(art, 185, 273, 1.65))
        elif shot in {"real_faces", "real_arrival"}:
            _human(_Brush(art, 224, 48, 1.37), "old", "cloth")
            _human(_Brush(art, 509, 63, 1.32), "adult", "offer", (173, 116, 91))
            _table(art)
            _mug(_Brush(art, 664, 296, .79))
        else:
            _human(_Brush(art, 284, 90, 1.10), "old", "tea" if shot == "real_tea" else "seated")
            _human(_Brush(art, 513, 112, 1.05), "adult", "offer" if shot == "real_hands" else "cloth", (174, 117, 90))
            _table(art)
            _mug(_Brush(art, 640, 302, .73))
            _recipe(_Brush(art, 343, 320, .85))
            _ribbon(_Brush(art, 530, 331, .40))
            if shot == "real_cloth":
                _cloth(_Brush(art, 445, 265, 1.24))
            elif shot == "real_hands":
                b.line(SKIN, (575, 315), (493, 302), 13)
                _hand(b, 474, 294, old=True)
                _hand(b, 466, 301)
    else:
        raise ValueError(f"Unknown story shot: {shot}")
    return art.finish()


@lru_cache(maxsize=6)
def _fragment(key: str) -> pygame.Surface:
    art = Ink((100, 100))
    if key == "F01":
        _ribbon(_Brush(art, 16, 13, .94))
    elif key == "F02":
        _mug(_Brush(art, 1, 13, .86))
    elif key == "F03":
        _key(_Brush(art, 15, 8, .98))
    elif key == "F04":
        _photo(_Brush(art, 4, 15, .59), folded=True)
    elif key == "F05":
        _recipe(_Brush(art, 3, 19, .64))
    elif key == "F06":
        _cloth(_Brush(art, 4, 23, .60))
    else:
        raise ValueError(f"Unknown story fragment: {key}")
    return art.finish()


@lru_cache(maxsize=96)
def _gesture(shot: str, frame: int) -> tuple[pygame.Surface, tuple[int, int]]:
    """Small cached overlays, rather than rerasterising a whole room each frame."""
    art = Ink((160, 100))
    b = _Brush(art)
    motion = math.sin(frame * math.tau / 24) * 1.8
    if shot == "stitch_hands":
        b.line((91, 121, 137), (7, 88), (86 + motion, 5), 2)
        b.line((200, 196, 162), (80 + motion, 14), (98 + motion, 0), 2)
        pos = (525, 250)
    elif shot == "real_hands":
        _hand(b, 24 + motion * .5, 18, old=True)
        _hand(b, 16, 27 + motion * .25)
        pos = (450, 276)
    elif shot == "recipe_stir":
        b.line((193, 193, 162), (21, 74), (46 + motion, 28), 3)
        b.ellipse((204, 202, 171), (36 + motion, 19, 17, 12))
        pos = (630, 232)
    else:
        # Steam is a small household movement, not a halo or victory effect.
        for i in range(3):
            start = (35 + i * 12, 71)
            middle = (30 + i * 12 + motion, 50 - i * 4)
            end = (36 + i * 12 - motion, 31 - i * 4)
            b.line((235, 224, 190, 80), start, middle, 2)
            b.line((235, 224, 190, 48), middle, end, 2)
        pos = (628, 237)
    return art.finish(), pos


def _animated_image(shot: str, time: float) -> pygame.Surface:
    image = _illustration(shot)
    if shot in {"stitch_hands", "recipe_stir", "real_hands", "real_tea", "real_wide"}:
        stamp, pos = _gesture(shot, int(max(time, 0) * 4) % 24)
        image = image.copy()
        image.blit(stamp, pos)
    return image


def _wrap(text: str, font: pygame.font.Font, width: int) -> tuple[str, ...]:
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            if current and font.size(current + " " + word)[0] > width:
                lines.append(current)
                current = ""
            # Also keep an unbroken word inside the viewport.
            while font.size(word)[0] > width and len(word) > 1:
                cut = len(word) - 1
                while cut > 1 and font.size(word[:cut])[0] > width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            current = (current + " " + word).strip()
        if current:
            lines.append(current)
    return tuple(lines)


class StoryRenderer:
    """Draw in place; timing, input, scene selection and audio belong to the caller."""

    def __init__(self, size=(960, 540)):
        self.size = tuple(size)
        self.last_subtitle_panel = None
        self.last_subtitle_layout = ()
        self.last_hint_text = ""
        self.last_hint_rect = pygame.Rect(0, 0, 0, 0)
        self.last_pause_text = ""

    def _subtitles(self, screen, text, speaker="", paused=False,
                   hints="Enter lanjut / Space jeda / Esc lewati"):
        w, h = screen.get_size()
        scale = min(w / 960, h / 540)
        font = _font(max(24, round(34 * scale)))
        label_font = _font(max(17, round(23 * scale)))
        margin = max(16, round(w * .05))
        padding = max(12, round(18 * scale))
        hint_font = _font(max(17, round(23 * scale)))
        # Size hint text to the viewport instead of clipping the Escape control.
        while hint_font.size(hints)[0] > w - 2 * margin:
            hint_font = _font(hint_font.get_height())
        hint = hint_font.render(hints, True, (239, 225, 193))
        self.last_hint_rect = hint.get_rect(midbottom=(w // 2, h - max(7, round(12 * scale))))
        self.last_hint_text = hints
        pygame.draw.rect(screen, (19, 29, 34), self.last_hint_rect.inflate(20, 8), border_radius=4)
        screen.blit(hint, self.last_hint_rect)
        self.last_subtitle_panel = None
        self.last_subtitle_layout = ()
        if text:
            width = min(w - margin * 2 - padding * 2, round(w * .70))
            lines = _wrap(text, font, width)
            step = font.get_linesize() + max(3, round(4 * scale))
            label_height = label_font.get_linesize() + 5 if speaker else 0
            height = padding * 2 + label_height + step * len(lines)
            bottom = self.last_hint_rect.top - max(12, round(17 * scale))
            panel = pygame.Rect(margin, bottom - height, w - 2 * margin, height)
            pygame.draw.rect(screen, (19, 29, 34), panel, border_radius=8)
            pygame.draw.line(screen, (167, 139, 94), (panel.left + padding, panel.top), (panel.right - padding, panel.top), 2)
            self.last_subtitle_panel = panel
            y = panel.top + padding
            if speaker:
                label = label_font.render(speaker, True, (230, 191, 128))
                screen.blit(label, (panel.left + padding, y))
                y += label_height
            layout = []
            for line in lines:
                glyphs = font.render(line, True, (248, 243, 231))
                rect = glyphs.get_rect(midtop=(w // 2, y))
                screen.blit(glyphs, rect)
                layout.append((line, rect))
                y += step
            self.last_subtitle_layout = tuple(layout)
        self.last_pause_text = "JEDA" if paused else ""
        if paused:
            glyphs = label_font.render("JEDA", True, (248, 243, 231))
            rect = glyphs.get_rect(topright=(w - margin, padding))
            pygame.draw.rect(screen, (19, 29, 34), rect.inflate(18, 10), border_radius=4)
            screen.blit(glyphs, rect)

    def draw(self, screen: pygame.Surface, scene: Scene, cue: Cue,
             cue_elapsed: float, scene_elapsed: float = 0.0,
             paused: bool = False) -> pygame.Surface:
        elapsed = max(0.0, scene_elapsed)
        if scene.kind == "void" and scene_elapsed <= 0:
            for item in scene.cues:
                if item is cue or item == cue:
                    break
                elapsed += item.duration
            elapsed += max(0.0, cue_elapsed)
        if scene.kind == "void" and elapsed >= scene.duration - 3:
            self.last_subtitle_panel = None
            self.last_subtitle_layout = ()
            self.last_hint_text = ""
            self.last_hint_rect = pygame.Rect(0, 0, 0, 0)
            self.last_pause_text = ""
            clip = screen.get_clip()
            screen.set_clip(None)
            screen.fill((0, 0, 0, 255))
            screen.set_clip(clip)
            return screen
        image = _animated_image(cue.shot, scene_elapsed + cue_elapsed)
        # A restrained camera move; never a flashing effect or restoration reward.
        zoom = 1 + .012 * min(max(cue_elapsed / max(cue.duration, .01), 0), 1)
        w, h = screen.get_size()
        frame = pygame.transform.smoothscale(image, (round(w * zoom), round(h * zoom)))
        pan = math.sin(scene_elapsed * .13) * 2
        screen.fill((0, 0, 0, 255))
        screen.blit(frame, (round((w - frame.get_width()) / 2 + pan), round((h - frame.get_height()) / 2)))
        self._subtitles(screen, cue.text, cue.speaker, paused)
        if scene.kind == "void":
            level = round(255 * (1 - min(elapsed / (scene.duration - 3), 1)) ** 1.2)
            screen.fill((level, level, level), special_flags=pygame.BLEND_RGB_MULT)
        return screen

    def draw_fragment(self, screen: pygame.Surface, key: str, x: float, y: float,
                      time: float = 0.0) -> pygame.Surface:
        image = _fragment(key)
        bob = math.sin(time * 1.2) * 1.5
        screen.blit(image, (round(x - 50), round(y - 50 + bob)))
        return screen

    def draw_ending(self, screen: pygame.Surface, page: int = 0,
                    time: float = 0.0) -> pygame.Surface:
        screen.blit(pygame.transform.smoothscale(_animated_image("real_wide", time), screen.get_size()), (0, 0))
        self._subtitles(screen, CLOSING_LINES[page % len(CLOSING_LINES)],
                        hints="Enter lanjut / K fragmen / R baru / Esc menu")
        w, h = screen.get_size()
        label = _font(max(20, round(27 * min(w / 960, h / 540)))).render(
            "Yang masih di sini", True, (49, 68, 66))
        screen.blit(label, (round(w * .05), round(h * .035)))
        return screen
