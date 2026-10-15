"""Enemy movement patterns as pure functions of time.

    p = Path("zigzag", speed=40, amp=30, period=2.0)
    x, y = p.pos(age, spawn_x)

Every path starts at (spawn_x, rules.ENTRY_Y) and works its way down the screen.
Being functions of time (not velocities) keeps them deterministic and testable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import rules

KINDS = ("straight", "zigzag", "circle", "hover")


@dataclass(frozen=True)
class Path:
    kind: str
    speed: float = 40  # px/s downward
    amp: float = 0  # zigzag/hover: sideways reach; circle: radius
    period: float = 2.0  # seconds per swing or orbit
    hold_y: float = 90  # hover: height it parks at
    hold: float = 4.0  # hover: seconds parked before leaving

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown path {self.kind!r}, expected one of {KINDS}")

    def pos(self, t: float, x0: float, centre: bool = False) -> tuple[float, float]:
        y = rules.ENTRY_Y + self.speed * t
        if self.kind == "straight":
            return x0, y
        if self.kind == "zigzag":
            phase = (t / self.period + 0.25) % 1.0
            return x0 + self.amp * (1 - 4 * abs(phase - 0.5)), y
        if self.kind == "circle":
            if centre:
                return x0, y
            a = math.tau * t / self.period
            return x0 + self.amp * math.sin(a), y - self.amp * math.cos(a)
        return self._hover(t, x0)

    def _hover(self, t, x0):
        enter = (self.hold_y - rules.ENTRY_Y) / self.speed
        if t < enter:
            return x0, rules.ENTRY_Y + self.speed * t
        held = min(t - enter, self.hold)
        x = x0 + self.amp * math.sin(math.tau * held / self.period)
        if t - enter <= self.hold:
            return x, self.hold_y
        return x, self.hold_y + self.speed * 1.3 * (t - enter - self.hold)
