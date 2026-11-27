"""Audio manager: layered ambience stems plus one-shot SFX.

The ambience is four looping stems per stage (see noor.audio.ambience). They all
play at once; only their gains are animated, so intensity changes are smooth and
never restart the music. On top of that the manager plays looping music beds
(``play_music``) and one-shot cues (``cue``, see noor.audio.cues). Each stage
also brings its own bed (``S1``..``S4``), tuned and looped to the ambience, so
entering a stage crossfades the menu music into a pad that sits under the stems.
Stage changes crossfade both the stems and the bed, and ``fade_out`` retires them
smoothly when a run ends. Everything degrades to a silent no-op when there is no
audio device, which keeps headless runs and tests working.
"""

import os

import numpy as np

import noor.config as C
from noor.audio import ambience, recipes

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SFX_DIR = os.path.join(ROOT, "assets", "audio")


class AudioManager:
    def __init__(self, accessibility=None, enabled=True):
        self.enabled = bool(enabled)
        self.volumes = {"master": 1.0, "music": 0.7, "sfx": 0.8, "whisper": 0.6}
        self.intensity = 0.0
        self.stage = 1
        self.accessibility = dict(accessibility or {})
        self._music_name = None
        self._music_channel = None
        self._music_base = 1.0
        self._music_cache = {}
        self._music_fade = 0.0  # seconds since the current bed started
        self._music_fading_in = False  # only when it replaces another bed
        self._fading = []  # outgoing beds: [channel, base gain, elapsed]
        self.apply_accessibility(self.accessibility)
        self._ready = None
        self._stems = {}
        self._channels = {}
        self._sfx_cache = {}
        self._stem_stage = None
        self._stem_fading = []  # outgoing stem sets: {channels, gains, elapsed}
        self._stem_fade = 0.0  # seconds since the current stem set started
        self._stem_fading_in = False
        self._duck = 0.0
        self._duck_rate = 0.0
        self._gain = {name: 0.0 for name in ambience.LAYERS}

    # --- device ---------------------------------------------------------

    def _ensure(self):
        if self._ready is not None:
            return self._ready
        self._ready = False
        if not self.enabled:
            return False
        try:
            import pygame

            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=C.SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(C.MIXER_CHANNELS)
            pygame.mixer.set_reserved(len(ambience.LAYERS))
            self._ready = True
        except Exception:  # noqa: BLE001
            # no device / driver: run silent instead of taking the game down
            self._ready = False
        return self._ready

    @property
    def ready(self):
        return bool(self._ready)

    def _to_sound(self, arr):
        import pygame

        arr = np.asarray(arr, dtype=np.float32)
        if arr.ndim == 1:
            arr = np.column_stack([arr, arr])
        peak = float(np.max(np.abs(arr))) if arr.size else 0.0
        target = 10 ** (C.PEAK_DBFS / 20.0)
        if peak > target:
            arr = arr / peak * target
        pcm = np.clip(arr, -1.0, 1.0) * 32767.0
        return pygame.sndarray.make_sound(np.ascontiguousarray(pcm.astype(np.int16)))

    # --- music ----------------------------------------------------------

    def load_stage(self, stage):
        """Render (or reuse) the ambience stems for a stage and start looping."""
        stage = max(1, int(stage))
        self.stage = stage
        if stage == self._stem_stage:
            return True
        # the old stems keep looping while they fade out under the new set
        self._retire_stems()
        if not self._ensure():
            self._stem_stage = stage
            return False
        for name, arr in ambience.stems_for_stage(stage).items():
            snd = self._to_sound(arr)
            ch = snd.play(loops=-1)
            if ch is not None:
                ch.set_volume(0.0)
            self._stems[name] = snd
            self._channels[name] = ch
        self._stem_stage = stage
        # stage bed: same root and loop length as the stems, mixed underneath
        self._stem_fade = 0.0
        self.play_music(f"S{stage}", volume=C.STAGE_MUSIC_GAIN)
        return True

    def set_intensity(self, I, stage=None):
        self.intensity = max(0.0, min(1.0, float(I)))
        if stage is not None:
            self.stage = int(stage)

    def set_stage(self, stage):
        if int(stage) != self.stage:
            self.load_stage(stage)

    def _music_scale(self):
        return self.volumes["master"] * self.volumes["music"] * (1.0 - 0.55 * self._duck)

    def update(self, dt):
        """Move layer gains toward the targets for the current intensity."""
        if not self._ready:
            return
        dt = max(0.0, float(dt))
        self._duck = max(0.0, self._duck - self._duck_rate * dt)
        self._music_fade += dt
        self._stem_fade += dt
        self._update_fading(dt)
        self._update_stem_fades(dt)
        if self._music_channel is not None:
            self._music_channel.set_volume(self._bed_volume() * self._fade_gain())
        weights = ambience.mix_weights(self.intensity)
        scale = self._music_scale()
        k = min(1.0, C.AMBIENCE_RAMP * dt)
        stem_fade = self._stem_fade_gain()
        for name, target_weight in weights.items():
            target = target_weight * scale
            gain = self._gain[name] + (target - self._gain[name]) * k
            self._gain[name] = gain
            ch = self._channels.get(name)
            if ch is None:
                continue
            if not ch.get_busy():
                snd = self._stems.get(name)
                if snd is not None:
                    ch = snd.play(loops=-1)
                    self._channels[name] = ch
            if ch is not None:
                ch.set_volume(max(0.0, min(1.0, gain * stem_fade)))

    def _music_volume(self):
        return max(0.0, min(1.0, self.volumes["master"] * self.volumes["music"] * 0.8))

    def _duck_gain(self):
        return 1.0 - 0.35 * self._duck

    def _bed_volume(self):
        """Bed gain: bus * per-bed base * cue duck (so hits still read)."""
        return max(0.0, min(1.0, self._music_volume() * self._music_base * self._duck_gain()))

    def _fade_gain(self):
        """Fade-in progress of the current bed, 0..1 over C.CROSSFADE_SECONDS."""
        dur = max(0.0, float(C.CROSSFADE_SECONDS))
        if dur <= 0.0 or not self._music_fading_in:
            return 1.0
        return max(0.0, min(1.0, self._music_fade / dur))

    def _stem_fade_gain(self):
        """Fade-in progress of the current stem set, 0..1 over C.CROSSFADE_SECONDS."""
        dur = max(0.0, float(C.CROSSFADE_SECONDS))
        if dur <= 0.0 or not self._stem_fading_in:
            return 1.0
        return max(0.0, min(1.0, self._stem_fade / dur))

    def _retire_stems(self):
        """Let the current stem set fade out instead of cutting it."""
        if not self._channels:
            self._stem_fade = 0.0
            self._stem_fading_in = False
            return
        if float(C.CROSSFADE_SECONDS) <= 0.0:
            self._stop_stems()
            return
        while self._stem_fading:  # one outgoing set is enough on fast stage hops
            old = self._stem_fading.pop(0)
            for ch in old["channels"].values():
                ch.stop()
        shrink = self._stem_fade_gain()
        self._stem_fading.append({
            "channels": {name: ch for name, ch in self._channels.items() if ch is not None},
            "gains": {name: gain * shrink for name, gain in self._gain.items()},
            "elapsed": 0.0,
        })
        self._channels.clear()
        self._stems.clear()
        self._stem_stage = None
        for name in self._gain:
            self._gain[name] = 0.0
        self._stem_fade = 0.0
        self._stem_fading_in = True

    def _update_stem_fades(self, dt):
        """Ramp retired stem sets down; each is stopped when the fade is over."""
        dur = max(0.0, float(C.CROSSFADE_SECONDS))
        for entry in list(self._stem_fading):
            entry["elapsed"] += dt
            progress = 1.0 if dur <= 0.0 else entry["elapsed"] / dur
            done = progress >= 1.0
            for name, ch in entry["channels"].items():
                if done or not ch.get_busy():
                    ch.stop()
                    continue
                vol = entry["gains"].get(name, 0.0) * (1.0 - progress)
                ch.set_volume(max(0.0, min(1.0, vol)))
            if done:
                self._stem_fading.remove(entry)

    def _update_fading(self, dt):
        """Ramp retired beds down; they are stopped once the fade is over."""
        dur = max(0.0, float(C.CROSSFADE_SECONDS))
        for entry in list(self._fading):
            ch, base, elapsed = entry
            elapsed += dt
            entry[2] = elapsed
            progress = 1.0 if dur <= 0.0 else elapsed / dur
            if progress >= 1.0 or not ch.get_busy():
                ch.stop()
                self._fading.remove(entry)
                continue
            vol = self._music_volume() * base * self._duck_gain() * (1.0 - progress)
            ch.set_volume(max(0.0, min(1.0, vol)))

    def _music_sound(self, name):
        if name in self._music_cache:
            return self._music_cache[name]
        import pygame

        path = os.path.join(SFX_DIR, f"{name}.wav")
        snd = None
        if os.path.exists(path):
            snd = pygame.mixer.Sound(path)
        elif name[:1] == "S" and name[1:].isdigit():
            # unbaked checkout: render the stage bed the same way as the stems
            snd = self._to_sound(recipes.stage_music_loop(int(name[1:])))
        elif name == "L0":
            # unbaked checkout: the title theme is generated, not shipped
            snd = self._to_sound(recipes.title_theme())
        self._music_cache[name] = snd
        return snd

    def play_music(self, name, volume=1.0):
        """Loop a music bed from assets/audio/<name>.wav.

        Menus use L0/L1/L5, stages use S1..S4 (started by ``load_stage``).
        Beds only stop the previous bed, never the ambience.
        """
        if not self._ensure():
            return False
        base = max(0.0, min(1.0, float(volume)))
        if (name == self._music_name and base == self._music_base
                and self._music_channel is not None and self._music_channel.get_busy()):
            return True
        self._fade_out_bed()
        try:
            snd = self._music_sound(name)
            ch = snd.play(loops=-1) if snd is not None else None
        except Exception:  # noqa: BLE001
            return False
        if ch is None:
            return False
        self._music_name = name
        self._music_channel = ch
        self._music_base = base
        self._music_fade = 0.0
        self._music_fading_in = bool(self._fading)
        ch.set_volume(self._bed_volume() * self._fade_gain())
        return True

    def duck(self, amount=0.6, seconds=0.4):
        """Dip the ambience for a moment (stingers, big hits)."""
        amount = max(0.0, min(1.0, float(amount)))
        self._duck = max(self._duck, amount)
        self._duck_rate = self._duck / max(0.05, float(seconds))

    def _fade_out_bed(self):
        """Retire the current bed; it keeps looping while it fades away."""
        ch, base = self._music_channel, self._music_base
        self._music_channel = None
        self._music_name = None
        if ch is None:
            return
        if float(C.CROSSFADE_SECONDS) <= 0.0 or not ch.get_busy():
            ch.stop()
            return
        while len(self._fading) >= 2:  # rapid bed swaps must not eat the channels
            old = self._fading.pop(0)
            old[0].stop()
        # keep whatever is left of a fade-in, so quitting early does not jump up
        self._fading.append([ch, base * self._fade_gain(), 0.0])

    def _stop_bed(self):
        if self._music_channel is not None:
            self._music_channel.stop()
        self._music_channel = None
        self._music_name = None
        self._music_fade = 0.0
        self._music_fading_in = False
        for ch, _base, _elapsed in self._fading:
            ch.stop()
        self._fading.clear()

    def _stop_stems(self):
        for ch in self._channels.values():
            if ch is not None:
                ch.stop()
        self._channels.clear()
        self._stems.clear()
        self._stem_stage = None
        for entry in self._stem_fading:
            for ch in entry["channels"].values():
                ch.stop()
        self._stem_fading.clear()
        self._stem_fade = 0.0
        self._stem_fading_in = False
        for name in self._gain:
            self._gain[name] = 0.0

    def fade_out(self):
        """Fade ambience and bed out instead of cutting them.

        Used when leaving a run (back to the title, or quitting the game). Call
        ``update`` while ``playing`` stays true so the fade actually runs.
        """
        self._retire_stems()
        self._fade_out_bed()

    @property
    def playing(self):
        """True while any bed or ambience stem is still audible."""
        if self._music_channel is not None or self._fading or self._stem_fading:
            return True
        return any(ch is not None and ch.get_busy() for ch in self._channels.values())

    def stop_music(self):
        self._stop_stems()
        self._stop_bed()

    # --- sfx ------------------------------------------------------------

    def _sfx(self, sid):
        if sid in self._sfx_cache:
            return self._sfx_cache[sid]
        snd = None
        path = os.path.join(SFX_DIR, f"{sid}.wav")
        try:
            import pygame

            if os.path.exists(path):
                snd = pygame.mixer.Sound(path)
            else:
                snd = self._to_sound(recipes.sfx(sid))
        except Exception:  # noqa: BLE001
            # a missing/undecodable asset must not stop gameplay
            snd = None
        self._sfx_cache[sid] = snd
        return snd

    def play(self, sid, volume=1.0):
        if not self._ensure():
            return False
        snd = self._sfx(sid)
        if snd is None:
            return False
        ch = snd.play()
        if ch is None:
            return False
        gain = self.volumes["master"] * self.volumes["sfx"] * max(0.0, min(1.0, float(volume)))
        ch.set_volume(max(0.0, min(1.0, gain)))
        return True

    def cue(self, name, volume=1.0):
        """Play a named cue; see noor.audio.cues.play_cue."""
        from noor.audio.cues import play_cue

        return play_cue(self, name, volume=volume)

    # --- settings -------------------------------------------------------

    def apply_accessibility(self, accessibility):
        self.accessibility = dict(accessibility or {})
        if self.accessibility.get("reduce_loud"):
            self.volumes["music"] = 0.4
            self.volumes["sfx"] = 0.5
        else:
            self.volumes["music"] = 0.7
            self.volumes["sfx"] = 0.8
        if self._music_channel is not None:
            self._music_channel.set_volume(self._bed_volume() * self._fade_gain())

    def stop(self):
        self.stop_music()
        self._sfx_cache.clear()
        self._music_cache.clear()
