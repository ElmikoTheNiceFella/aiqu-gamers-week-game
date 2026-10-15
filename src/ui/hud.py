"""In-game HUD: score on the left, three hearts on the right.

    hud = Hud()
    hud.update(dt, score, lives, wave)   # call every frame; wave is optional
    hud.draw(surface)

Losing a life blinks the heart that just broke and nudges it sideways.
When one life is left the last heart pulses as a warning.
"""
from __future__ import annotations

import math

import pygame

import src.theme as T
from . import sprites
from . import draw

HUD_H = 28
MAX_LIVES = 3
HEART_SCALE = 2
HEART_GAP = 4


class Hud:
    def __init__(self, max_lives: int = MAX_LIVES, total_waves: int = 5):
        self.max_lives = max_lives
        self.total_waves = total_waves
        self.score = 0
        self.lives = max_lives
        self.t = 0.0
        self._hit_idx = -1
        self._hit_timer = 0.0
        self.wave = None

    def update(self, dt, score, lives, wave=None):
        self.wave = wave
        self.t += dt
        lives = max(0, min(self.max_lives, lives))
        if lives < self.lives:
            self._hit_idx = lives  # leftmost heart that just broke
            self._hit_timer = 0.7
        self._hit_timer = max(0.0, self._hit_timer - dt)
        self.score, self.lives = score, lives

    def reset(self):
        self.lives, self.score, self._hit_timer = self.max_lives, 0, 0.0

    def draw(self, surf):
        w = surf.get_width()
        pygame.draw.rect(surf, T.INK, (0, 0, w, HUD_H))
        pygame.draw.rect(surf, T.PANEL, (0, 0, w, HUD_H - 2))
        pygame.draw.line(surf, T.MAGENTA, (0, HUD_H - 2), (w, HUD_H - 2))
        pygame.draw.line(surf, T.PURPLE, (0, HUD_H - 1), (w, HUD_H - 1))

        draw.draw_small(surf, "SCORE", (8, 5), T.DIM)
        draw.draw_small(surf, f"{self.score:06d}", (8, 15), T.YELLOW)
        if self.wave is not None:
            draw.draw_small(surf, "WAVE", (w // 2 - 14, 5), T.DIM, anchor="midtop")
            draw.draw_small(surf, f"{self.wave}/{self.total_waves}", (w // 2 - 14, 15), T.CYAN,
                            anchor="midtop")
        self._draw_hearts(surf, w)

    def _draw_hearts(self, surf, w):
        hw = sprites.get("heart", HEART_SCALE).get_width()
        hh = sprites.get("heart", HEART_SCALE).get_height()
        total = self.max_lives * hw + (self.max_lives - 1) * HEART_GAP
        x0 = w - 8 - total
        y = (HUD_H - 2 - hh) // 2
        for i in range(self.max_lives):
            name = "heart" if i < self.lives else "heart_empty"
            dx = 0
            if i == self._hit_idx and self._hit_timer > 0:
                blink_on = int(self._hit_timer * 12) % 2 == 0
                name = "heart_hit" if blink_on else "heart_empty"
                dx = 1 if int(self._hit_timer * 24) % 2 else -1
            elif self.lives == 1 and i == 0 and math.sin(self.t * 6) < 0:
                name = "heart_empty"  # low-health pulse
            surf.blit(sprites.get(name, HEART_SCALE), (x0 + i * (hw + HEART_GAP) + dx, y))
