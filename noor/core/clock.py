"""Disease clock: global active play time forcing stage progression."""

import noor.config as C


class DiseaseClock:
    def __init__(self, stage=1, active_time=0.0, paused=False, seed=0):
        self.stage = int(stage)
        self.active_time = float(active_time)
        self.paused = bool(paused)
        self.seed = seed
        self.stage_start_time = self._stage_start_for(self.stage)

    def _stage_start_for(self, stage):
        # cumulative target durations up to previous stage
        total = 0.0
        for s in range(1, stage):
            total += C.STAGE_TARGET_DURATION[s]
        return total

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def set_paused(self, value):
        self.paused = bool(value)

    def update(self, dt, paused=None, distance_progress=None):
        if paused is not None:
            self.paused = bool(paused)
        if self.paused:
            return
        dt = float(dt)
        self.active_time += dt
        forced = self.forced_stage()
        if forced > self.stage:
            self.stage = forced
            self.stage_start_time = self._stage_start_for(self.stage)

    def forced_stage(self):
        t = self.active_time
        if t >= C.CLOCK_FINAL:
            return 4  # collapse to epilog handled by caller
        if t >= C.CLOCK_DEADLINE[4]:
            return 4
        if t >= C.CLOCK_DEADLINE[3]:
            return 3
        if t >= C.CLOCK_DEADLINE[2]:
            return 2
        return 1

    def stage_progress(self, distance_progress=None):
        # time-based progress within stage
        target = C.STAGE_TARGET_DURATION[self.stage] if self.stage in range(1, 5) else 300
        elapsed = self.active_time - self.stage_start_time
        time_p = elapsed / max(1.0, float(target))
        time_p = max(0.0, min(1.0, time_p))
        if distance_progress is None:
            return time_p
        try:
            dp = float(distance_progress)
        except (TypeError, ValueError):
            dp = 0.0
        dp = max(0.0, min(1.0, dp))
        return max(time_p, dp)

    def is_final(self):
        return self.active_time >= C.CLOCK_FINAL

    @property
    def elapsed(self):
        return self.active_time

    @property
    def seconds(self):
        return self.active_time

    def to_dict(self):
        return {"stage": self.stage, "active_time": self.active_time, "paused": self.paused}

    @classmethod
    def from_dict(cls, data):
        return cls(stage=data.get("stage", 1), active_time=data.get("active_time", 0.0), paused=data.get("paused", False))