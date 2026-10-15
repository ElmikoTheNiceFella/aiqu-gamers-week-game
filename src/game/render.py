"""Draws a World with the ui-new sprites. Holds only cosmetic state (debris).

    renderer = Renderer()
    renderer.on_events(world.drain_events())   # spawns explosion debris
    renderer.update(dt)
    renderer.draw(surface, world)

The host draws the background first and the HUD and overlays after.
"""
from __future__ import annotations

import math
import random

import pygame

import src.theme as T
from src.ui import sprites

from . import rules as R

SCALE = 2
DEBRIS_COLORS = {
    "drone": (T.CYAN, T.MAGENTA, T.WHITE),
    "bot": (T.MAGENTA, T.PINK, T.YELLOW),
    "titan": (T.YELLOW, T.ORANGE, T.PINK),
    "ship": (T.PINK, T.WHITE, T.CYAN),
}


class Renderer:
    def __init__(self, seed=None):
        self.t = 0.0
        self.rng = random.Random(seed)
        self.debris: list[list] = []  # [x, y, vx, vy, life, color]

    def reset(self):
        self.debris.clear()

    def on_events(self, events):
        for e in events:
            if e[0] == "kill":
                self._burst(e[2], e[3], DEBRIS_COLORS[e[1]], 14, 70)
            elif e[0] == "damage":
                self._burst(e[2], e[3], (T.WHITE, T.YELLOW), 4, 40)

    def _burst(self, x, y, colors, n, speed):
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(speed * 0.3, speed)
            self.debris.append([x, y, math.cos(a) * v, math.sin(a) * v,
                                self.rng.uniform(0.25, 0.5), self.rng.choice(colors)])

    def update(self, dt):
        self.t += dt
        for d in self.debris:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            d[4] -= dt
        self.debris = [d for d in self.debris if d[4] > 0]

    def draw(self, surf, world):
        for e in world.enemies:
            img = sprites.get(sprites.enemy_name(e.kind, e.hp, e.flash > 0), SCALE)
            surf.blit(img, img.get_rect(center=(round(e.x), round(e.y))))
        orb = sprites.get("orb", SCALE)
        for x, y in world.bombs:
            surf.blit(orb, orb.get_rect(center=(round(x), round(y))))
        for x, y in world.shots:
            pygame.draw.rect(surf, T.CYAN, (round(x) - 1, round(y), 2, 6))
            surf.fill(T.WHITE, (round(x) - 1, round(y), 2, 2))
        self._draw_ship(surf, world)
        for x, y, _, _, life, color in self.debris:
            size = 2 if life > 0.2 else 1
            surf.fill(color, (round(x), round(y), size, size))

    def _draw_ship(self, surf, world):
        if world.invulnerable > 0:
            if int(world.invulnerable * 10) % 2:
                return  # blink while invulnerable
            name = "ship_hit"
        else:
            name = "ship_flame1" if int(self.t * 12) % 2 == 0 else "ship_flame2"
        img = sprites.get(name, SCALE)
        # the flame hangs below the hull; anchor the hull on SHIP_Y
        hull_h = len(sprites.SHIP) * SCALE
        surf.blit(img, img.get_rect(midtop=(round(world.ship_x), R.SHIP_Y - hull_h // 2)))
