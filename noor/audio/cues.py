"""Semantic audio cues: one call site for every sound the game already owns.

Gameplay does not need to know about WAV ids or stem names; it asks for an
event ("fragment", "death", ...) and this module resolves it through the
existing AudioManager pieces:

    play_cue(audio, "fragment")        # SFX cue from CUES (+ ambience duck)
    play_cue(audio, "music:L0")        # looping music bed (assets/audio/L0.wav)
    play_cue(audio, "music:S2")        # stage bed (started for you by load_stage)
    play_cue(audio, "ambience:3")      # looping ambience stems for stage 3

SFX names map onto the baked assets/audio/Axx.wav files and fall back to
noor.audio.recipes when a file is missing, so a cue never has to care whether
the project was baked or is running from generated audio.
"""

# cue name -> {sfx id, per-cue gain, (duck amount, duck seconds)}
# The duck is there so one-shot hits read on top of the ambience bed.
#
# Gains are a ladder, not a flat one: every baked file is peak-normalised to the
# same ceiling, so the cue gain is the only thing separating a footstep from the
# death sting. Routine movement sits ~12 dB under death, story beats cluster in
# the middle, and only contact/death are allowed to push into the bed.
CUES = {
    "jump": {"sfx": "A02", "volume": 0.28},
    "land": {"sfx": "A03", "volume": 0.48},
    "interact": {"sfx": "A04", "volume": 0.45},
    "fragment": {"sfx": "A05", "volume": 0.95, "duck": (0.35, 0.8)},
    "forget": {"sfx": "A06", "volume": 0.72, "duck": (0.50, 1.0)},
    "checkpoint": {"sfx": "A19", "volume": 0.85, "duck": (0.25, 0.9)},
    "contact": {"sfx": "A10", "volume": 0.95, "duck": (0.70, 0.6)},
    "death": {"sfx": "A17", "volume": 1.00, "duck": (0.90, 1.6)},
    "stage": {"sfx": "A18", "volume": 0.62, "duck": (0.50, 1.2)},
}


def play_cue(audio, cue, volume=1.0):
    """Play existing game audio by name. Returns True if something played.

    ``cue`` is either a key of CUES, or ``music:<name>`` / ``ambience:<stage>``.
    Everything degrades to False when there is no audio device.
    """
    if not cue:
        return False
    kind, _, arg = str(cue).partition(":")
    if kind == "ambience":
        try:
            return bool(audio.load_stage(int(arg)))
        except (TypeError, ValueError):
            return False
    if kind == "music":
        return bool(audio.play_music(arg))

    spec = CUES.get(kind)
    if spec is None:
        return False
    duck = spec.get("duck")
    if duck:
        audio.duck(duck[0], duck[1])
    gain = spec.get("volume", 1.0) * max(0.0, min(1.0, float(volume)))
    return bool(audio.play(spec["sfx"], volume=gain))
