"""Deterministic RNG helpers."""

import random


def make_rng(seed):
    return random.Random(seed)


_GLOBAL = random.Random(0)


def rng():
    return _GLOBAL


def set_seed(seed):
    global _GLOBAL
    _GLOBAL = random.Random(seed)
    return _GLOBAL