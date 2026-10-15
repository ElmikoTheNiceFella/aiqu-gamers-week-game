"""The game itself: ship, waves, bullets, score and lives. No drawing, no input.

    world = World()
    world.update(dt, direction)    # direction is -1, 0 or +1 from the gesture link
    for event in world.drain_events():
        ...                        # ("kill", kind, x, y), ("player_hit", cause), ("won",) ...

world.phase is "banner" (WAVE n card), "fighting", "won" or "lost".
"""
from __future__ import annotations

import random

from . import rules as R
from .enemies import Enemy
from .waves import WAVES


class World:
    def __init__(self, waves=WAVES, rng: random.Random | None = None):
        self.waves = list(waves)
        self.rng = rng or random.Random()
        self.score = 0
        self.lives = R.START_LIVES
        self.ship_x = R.FIELD_W / 2
        self.invulnerable = 0.0
        self.fire_enabled = True
        self._fire_t = 0.0
        self.shots: list[list[float]] = []  # [x, y], player bullets
        self.bombs: list[list[float]] = []  # [x, y], enemy bullets
        self.enemies: list[Enemy] = []
        self._events: list[tuple] = []
        self._start_wave(0)

    # ---- waves
    def _start_wave(self, index: int):
        self.wave_index = index
        self.phase = "banner"
        self.banner_t = R.BANNER_TIME
        self.wave_t = 0.0
        self.speed_scale = 1.0 + R.SPEED_STEP * index
        self._pending = sorted(
            ((g.at, g.kind, g.path, x, g.fire_every) for g in self.waves[index].groups for x in g.xs),
            key=lambda s: s[0])
        self._events.append(("wave", index + 1))

    @property
    def wave_number(self) -> int:
        return self.wave_index + 1

    @property
    def wave_name(self) -> str:
        return self.waves[self.wave_index].name

    def drain_events(self) -> list[tuple]:
        events, self._events = self._events, []
        return events

    # ---- per frame
    def update(self, dt: float, direction: int):
        if self.phase in ("won", "lost"):
            return
        self.ship_x = min(R.FIELD_W - R.SHIP_MARGIN,
                          max(R.SHIP_MARGIN, self.ship_x + direction * R.SHIP_SPEED * dt))
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self._fire(dt)

        if self.phase == "banner":
            self.banner_t -= dt
            if self.banner_t <= 0:
                self.phase = "fighting"
            return

        self.wave_t += dt * self.speed_scale
        while self._pending and self._pending[0][0] <= self.wave_t:
            _, kind, path, x, fire_every = self._pending.pop(0)
            self.enemies.append(Enemy(kind, path, x, fire_every, self.rng))
        for e in self.enemies:
            e.update(dt, self.speed_scale)
            self._enemy_fire(e, dt)
        for b in self.bombs:
            b[1] += R.BOMB_SPEED * dt  # constant: bullets stay dodgeable in late waves
        self.bombs = [b for b in self.bombs if b[1] < R.FIELD_H + R.BOMB_SIZE]

        self._collide_shots()
        self._collide_ship()
        self._escapes()
        if self.lives <= 0:
            self.lives = 0
            self.phase = "lost"
            self._events.append(("lost",))
            return
        if not self._pending and not self.enemies:
            self._wave_cleared()

    def _fire(self, dt):
        for s in self.shots:
            s[1] -= R.SHOT_SPEED * dt
        self.shots = [s for s in self.shots if s[1] > R.FIELD_TOP]
        if not self.fire_enabled:
            return
        self._fire_t -= dt
        if self._fire_t <= 0:
            self._fire_t += R.FIRE_EVERY
            self.shots.append([self.ship_x, R.SHIP_Y - 12])

    def _enemy_fire(self, e: Enemy, dt):
        if e.fire_t is None or not (R.FIELD_TOP + 8 < e.y < R.FIRE_ZONE_BOTTOM):
            return
        e.fire_t -= dt * self.speed_scale
        if e.fire_t <= 0:
            e.fire_t += e.fire_every
            self.bombs.append([e.x, e.y + e.spec.h / 2])

    def _collide_shots(self):
        for s in list(self.shots):
            for e in self.enemies:
                if e.overlaps(s[0], s[1], 2, 6):
                    self.shots.remove(s)
                    if e.hit():
                        self.enemies.remove(e)
                        self.score += e.spec.points
                        self._events.append(("kill", e.kind, e.x, e.y))
                    else:
                        self._events.append(("damage", e.kind, e.x, e.y))
                    break

    def _collide_ship(self):
        for b in list(self.bombs):
            if (abs(b[0] - self.ship_x) * 2 < R.SHIP_HIT_W + R.BOMB_SIZE
                    and abs(b[1] - R.SHIP_Y) * 2 < R.SHIP_HIT_H + R.BOMB_SIZE):
                if self._player_hit("bomb"):
                    self.bombs.remove(b)
        for e in list(self.enemies):
            if e.overlaps(self.ship_x, R.SHIP_Y, R.SHIP_HIT_W, R.SHIP_HIT_H) and self._player_hit(e.kind):
                self.enemies.remove(e)
                self._events.append(("kill", e.kind, e.x, e.y))

    def _player_hit(self, cause: str) -> bool:
        if self.invulnerable > 0:
            return False
        self.lives -= 1
        self.invulnerable = R.INVULNERABLE_TIME
        self._events.append(("player_hit", cause))
        return True

    def _escapes(self):
        for e in list(self.enemies):
            if e.y > R.ESCAPE_Y:
                self.enemies.remove(e)
                self.lives -= 1
                self._events.append(("escaped", e.kind, e.x))

    def _wave_cleared(self):
        self.score += R.WAVE_BONUS * self.wave_number
        self.bombs.clear()
        self._events.append(("wave_cleared", self.wave_number))
        if self.wave_index + 1 < len(self.waves):
            if self.lives < R.START_LIVES:
                self.lives += 1  # a cleared wave mends one heart
                self._events.append(("life_up",))
            self._start_wave(self.wave_index + 1)
        else:
            self.score += R.LIFE_BONUS * self.lives
            self.phase = "won"
            self._events.append(("won",))
