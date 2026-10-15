"""The five waves, as data.

Each Group spawns one enemy per x position at `at` seconds into the wave.
Wave time runs faster in later waves (rules.SPEED_STEP), so the timings below
are for wave 1 speed. Keep x - amp and x + amp inside 12..308 (a test checks).
"""
from __future__ import annotations

from dataclasses import dataclass

from .paths import Path


@dataclass(frozen=True)
class Group:
    at: float
    kind: str
    path: Path
    xs: tuple[float, ...]
    fire_every: float | None = None  # seconds between shots; None = never shoots


@dataclass(frozen=True)
class Wave:
    name: str
    groups: tuple[Group, ...]


STRAIGHT = Path("straight", speed=38)
SLOW = Path("straight", speed=22)
ZIGZAG = Path("zigzag", speed=34, amp=36, period=2.2)
CIRCLE = Path("circle", speed=28, amp=22, period=2.4)
HOVER = Path("hover", speed=50, amp=44, period=3.2, hold_y=84, hold=6.0)
HOVER_HIGH = Path("hover", speed=40, amp=36, period=4.0, hold_y=64, hold=7.0)

WAVES = (
    Wave("FIRST CONTACT", (
        Group(0.0, "drone", STRAIGHT, (60, 160, 260)),
        Group(3.0, "drone", STRAIGHT, (100, 220)),
        Group(6.0, "drone", STRAIGHT, (60, 160, 260)),
        Group(9.0, "drone", STRAIGHT, (40, 120, 200, 280)),
    )),
    Wave("ZIG ZAG", (
        Group(0.0, "drone", ZIGZAG, (80, 240)),
        Group(2.5, "bot", STRAIGHT, (160,)),
        Group(4.5, "drone", ZIGZAG, (60, 160, 260)),
        Group(7.5, "bot", STRAIGHT, (100, 220)),
        Group(10.0, "drone", ZIGZAG, (120, 200)),
    )),
    Wave("INCOMING FIRE", (
        Group(0.0, "drone", HOVER, (80, 240), fire_every=2.8),
        Group(1.5, "drone", CIRCLE, (100, 220)),
        Group(4.5, "bot", ZIGZAG, (160,)),
        Group(7.0, "drone", CIRCLE, (60, 160, 260)),
        Group(10.0, "bot", ZIGZAG, (90, 230)),
    )),
    Wave("THE TITAN", (
        Group(0.0, "titan", SLOW, (160,)),
        Group(1.0, "bot", HOVER, (70, 250), fire_every=2.6),
        Group(4.5, "bot", CIRCLE, (110, 210)),
        Group(7.5, "drone", ZIGZAG, (60, 160, 260)),
        Group(10.5, "bot", CIRCLE, (160,)),
    )),
    Wave("BEAT THE AI", (
        Group(0.0, "titan", HOVER_HIGH, (90, 230), fire_every=3.0),
        Group(2.0, "drone", ZIGZAG, (50, 160, 270)),
        Group(5.0, "bot", CIRCLE, (110, 210)),
        Group(7.5, "drone", HOVER, (60, 260), fire_every=3.2),
        Group(10.0, "bot", ZIGZAG, (160,)),
        Group(12.5, "drone", STRAIGHT, (60, 160, 260)),
    )),
)
