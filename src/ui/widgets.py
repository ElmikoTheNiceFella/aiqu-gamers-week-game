"""Buttons and a keyboard + mouse menu. Mouse positions are window pixels and are
converted with theme.to_logical, so the host passes events through untouched."""
from __future__ import annotations

import math

import pygame

import src.theme as T
from . import draw


class Button:
    def __init__(self, label, rect, action, color=T.MAGENTA, size=16):
        self.enabled = True  # a disabled button is drawn dim and never fires
        self.label = label
        self.rect = pygame.Rect(rect)
        self.action = action
        self.color = color
        self.size = size

    def draw(self, surf, focused, t):
        focused = focused and self.enabled
        c = self.color if focused else draw.mix(self.color, T.INK, 0.55)
        fill = draw.mix(T.PANEL, self.color, 0.22) if focused else T.PANEL
        draw.neon_panel(surf, self.rect, c, fill=fill, chamfer=3, glow=focused)
        top, bottom = (T.WHITE, draw.lighter(self.color, 0.15)) if focused else (T.SOFT, T.DIM)
        draw.draw_text(surf, self.label, self.size, self.rect.center,
                       top=top, bottom=bottom, shadow=draw.darker(self.color, 0.35) if focused else None,
                       depth=2 if focused else 0, outline=focused, anchor="center")
        if focused:
            bob = int(round(math.sin(t * 9)))
            ay = self.rect.centery - 4
            draw.triangle(surf, self.rect.x + 8 + bob, ay, 9, T.YELLOW, "right")
            draw.triangle(surf, self.rect.right - 9 - bob, ay, 9, T.YELLOW, "left")


class Menu:
    """Vertical list of buttons. handle_event() returns an action string or None."""

    def __init__(self, buttons):
        self.buttons = buttons
        self.index = 0
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.buttons)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.buttons)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._fire(self.buttons[self.index])
        elif e.type == pygame.MOUSEMOTION:
            self._hover(T.to_logical(e.pos))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            pos = T.to_logical(e.pos)
            self._hover(pos)
            if self.buttons[self.index].rect.collidepoint(pos):
                return self._fire(self.buttons[self.index])
        return None

    @staticmethod
    def _fire(button):
        return button.action if button.enabled else None

    def _hover(self, pos):
        for i, b in enumerate(self.buttons):
            if b.rect.collidepoint(pos):
                self.index = i

    def draw(self, surf):
        for i, b in enumerate(self.buttons):
            b.draw(surf, i == self.index, self.t)
