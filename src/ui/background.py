"""Gameplay backdrop from ui-new: dithered nebula, a drifting ringed planet,
floating binary digits and the shared starfield on top.

    bg = SpaceBackground(stars)
    bg.update(dt)
    bg.draw(surface)       # fills the whole logical surface

The nebula is generated once (seeded, so it is the same every run) and scrolls
slowly; it tiles vertically so the scroll never shows a seam.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame

import src.theme as T
from . import draw

W, H = T.LOGICAL_W, T.LOGICAL_H
BAYER4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
NEBULA_COLORS = (T.PURPLE, T.BLUE, T.MAGENTA, (60, 30, 150))
NEBULA_SPEED = 5  # px/s
PLANET_SPEED = 3
DIGIT_SPEED = (6, 14)


@lru_cache(maxsize=1)
def nebula_surface(seed=11) -> pygame.Surface:
    """W x H, tiles vertically. Two dithered tones per cloud over the background."""
    rng = random.Random(seed)
    surf = pygame.Surface((W, H))
    surf.fill(T.BG)
    strength = [[0.0] * W for _ in range(H)]
    tint = [[None] * W for _ in range(H)]
    for _ in range(22):
        cx, cy = rng.uniform(0, W), rng.uniform(0, H)
        rx, ry = rng.uniform(26, 60), rng.uniform(18, 46)
        color = rng.choice(NEBULA_COLORS)
        for y in range(int(cy - ry), int(cy + ry) + 1):
            yy = y % H  # vertical wrap keeps the tile seamless
            dy = (y - cy) / ry
            for x in range(max(0, int(cx - rx)), min(W, int(cx + rx) + 1)):
                dx = (x - cx) / rx
                v = 1.0 - math.sqrt(dx * dx + dy * dy)
                if v > strength[yy][x]:
                    strength[yy][x], tint[yy][x] = v, color
    for y in range(H):
        for x in range(W):
            v = strength[y][x]
            if v <= 0:
                continue
            threshold = (BAYER4[y % 4][x % 4] + 0.5) / 16
            if v * 1.6 > threshold + 0.55:
                surf.set_at((x, y), draw.mix(T.BG, tint[y][x], 0.42))
            elif v * 2.2 > threshold:
                surf.set_at((x, y), draw.mix(T.BG, tint[y][x], 0.22))
    return surf


@lru_cache(maxsize=1)
def planet_surface(r=18) -> pygame.Surface:
    """Striped planet with a tilted cyan ring (back half behind, front half over)."""
    w, h = r * 4 + 4, r * 2 + 8
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    ring = pygame.Rect(0, 0, r * 4, r + 2)
    ring.center = (cx, cy)
    pygame.draw.ellipse(surf, draw.darker(T.CYAN, 0.45), ring, 2)
    bands = (T.PURPLE, draw.mix(T.PURPLE, T.MAGENTA, 0.5), (90, 40, 170), T.MAGENTA,
             draw.mix(T.PURPLE, T.BLUE, 0.4))
    for y in range(-r, r + 1):
        half = int(math.sqrt(max(0, r * r - y * y)))
        color = bands[((y + r) // 5) % len(bands)]
        if y > r // 3:  # shade the bottom
            color = draw.darker(color, 0.35)
        pygame.draw.line(surf, color, (cx - half, cy + y), (cx + half, cy + y))
    pygame.draw.circle(surf, T.INK, (cx, cy), r + 1, 1)
    front = surf.subsurface(pygame.Rect(0, cy, w, h - cy)).copy()
    front.fill((0, 0, 0, 0))
    pygame.draw.ellipse(front, T.CYAN, ring.move(0, -cy), 2)
    surf.blit(front, (0, cy))
    return surf


class SpaceBackground:
    def __init__(self, stars: draw.Starfield | None = None, seed=5):
        self.stars = stars or draw.Starfield()
        rng = random.Random(seed)
        self.rng = rng
        self.scroll = 0.0
        self.planet = [rng.uniform(60, W - 60), rng.uniform(60, 140)]
        self.digits = [[rng.uniform(0, W), rng.uniform(0, H), rng.choice("01"),
                        rng.uniform(*DIGIT_SPEED), rng.uniform(0, math.tau)] for _ in range(12)]
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        self.stars.update(dt)
        self.scroll = (self.scroll + NEBULA_SPEED * dt) % H
        self.planet[1] += PLANET_SPEED * dt
        if self.planet[1] > H + 40:
            self.planet = [self.rng.uniform(60, W - 60), -40.0]
        for d in self.digits:
            d[1] += d[3] * dt
            if d[1] > H:
                d[0], d[1], d[2] = self.rng.uniform(0, W), -8.0, self.rng.choice("01")

    def draw(self, surf):
        neb = nebula_surface()
        y = int(self.scroll)
        surf.blit(neb, (0, y))
        surf.blit(neb, (0, y - H))
        planet = planet_surface()
        surf.blit(planet, planet.get_rect(center=(int(self.planet[0]), int(self.planet[1]))))
        self.stars.draw(surf, fill=False)
        for x, y, ch, _, phase in self.digits:
            color = T.PURPLE if math.sin(self.t * 1.5 + phase) > 0 else T.DIM
            draw.draw_text(surf, ch, 8, (int(x), int(y)), top=draw.darker(color, 0.3),
                           depth=0, outline=False)
