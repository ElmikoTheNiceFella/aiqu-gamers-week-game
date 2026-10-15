"""Enemy kinds (from the ui-new sprite sheet) and the Enemy object."""
from __future__ import annotations

import random
from dataclasses import dataclass

from .paths import Path


@dataclass(frozen=True)
class Kind:
    hp: int
    points: int
    w: int  # hitbox in logical px, the sprite size at scale 2
    h: int


KINDS = {
    "drone": Kind(hp=1, points=10, w=26, h=22),
    "bot": Kind(hp=2, points=25, w=32, h=22),
    "titan": Kind(hp=5, points=100, w=48, h=24),
}

FLASH_TIME = 0.08


class Enemy:
    def __init__(self, kind: str, path: Path, x0: float, fire_every: float | None = None,
                 rng: random.Random | None = None):
        self.kind = kind
        self.spec = KINDS[kind]
        self.hp = self.spec.hp
        self.path = path
        self.x0 = x0
        self.age = 0.0
        self.flash = 0.0
        self.fire_every = fire_every
        # stagger the first shot so a row of shooters doesn't fire in unison
        self.fire_t = (rng or random).uniform(0.4, fire_every) if fire_every else None
        self.x, self.y = path.pos(0.0, x0)

    def update(self, dt: float, scale: float = 1.0):
        self.age += dt * scale
        self.x, self.y = self.path.pos(self.age, self.x0)
        self.flash = max(0.0, self.flash - dt)

    def hit(self) -> bool:
        """Take one damage. Returns True if that destroyed it."""
        self.hp -= 1
        self.flash = FLASH_TIME
        return self.hp <= 0

    def overlaps(self, x, y, w, h) -> bool:
        """Axis-aligned overlap with a box centred on (x, y)."""
        return (abs(self.x - x) * 2 < self.spec.w + w) and (abs(self.y - y) * 2 < self.spec.h + h)
