"""Lighting helpers."""

import noor.config as C


class LightingSystem:
    def __init__(self):
        self.cache = {}

    def radius_for(self, S):
        return C.R_MIN + C.R_RANGE * (max(0, S) / 100.0) ** C.R_EXP

    def dark_alpha(self, stage, S):
        a = C.DARK_A0[stage] + (100.0 - S) * C.DARK_K
        return max(0, min(C.DARK_MAX, a))

    def is_lit(self, rect_center, light_pos, radius):
        dx = rect_center[0] - light_pos[0]
        dy = rect_center[1] - light_pos[1]
        d = (dx * dx + dy * dy) ** 0.5
        thr = C.LIT_ONLY_THRESHOLD * radius
        return d < thr