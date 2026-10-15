"""Drawing primitives for the neon-arcade look.

Everything here draws onto the LOGICAL surface (theme.LOGICAL_W x LOGICAL_H).
Text is rendered without anti-aliasing, given a banded gradient fill, a hard
extrusion and a 1px ink outline, then cached. Cached surfaces are shared, so
never modify what text_surface() returns.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame

import src.theme as T

_DIRS8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
BANDS = 4  # gradient steps; hard bands read as pixel art, smooth ones as a blur


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def darker(c, t=0.5):
    return mix(c, T.INK, t)


def lighter(c, t=0.5):
    return mix(c, T.WHITE, t)


# ------------------------------------------------------------------- text
@lru_cache(maxsize=64)
def _gradient(w, h, top, bottom):
    s = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        t = min(int(t * BANDS), BANDS - 1) / max(BANDS - 1, 1)
        s.fill(mix(top, bottom, t), (0, y, w, 1))
    return s


@lru_cache(maxsize=512)
def text_surface(text, size, top, bottom, shadow, depth, outline):
    base = T.font(size).render(text, False, (255, 255, 255))
    mask = pygame.mask.from_surface(base)
    w, h = base.get_size()
    pad = 1 if outline else 0
    depth = depth if shadow else 0
    W, H = w + 2 * pad, h + 2 * pad + depth

    letters = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    letters.blit(_gradient(w, h, top, bottom), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    body = pygame.Surface((W, H), pygame.SRCALPHA)
    if depth:
        ext = mask.to_surface(setcolor=tuple(shadow) + (255,), unsetcolor=(0, 0, 0, 0))
        for k in range(depth, 0, -1):
            body.blit(ext, (pad, pad + k))
    body.blit(letters, (pad, pad))

    out = pygame.Surface((W, H), pygame.SRCALPHA)
    if outline:
        ink = pygame.mask.from_surface(body).to_surface(
            setcolor=T.INK + (255,), unsetcolor=(0, 0, 0, 0))
        for dx, dy in _DIRS8:
            out.blit(ink, (dx, dy))
    out.blit(body, (0, 0))
    return out


def draw_text(surf, text, size, pos, top=T.WHITE, bottom=None, shadow=None,
              depth=2, outline=True, anchor="topleft"):
    """Draw gradient text. `anchor` is any pygame.Rect attribute (center, midtop...)."""
    img = text_surface(text, size, tuple(top), tuple(bottom or top),
                       tuple(shadow) if shadow else None, depth, outline)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


def draw_small(surf, text, pos, color=T.SOFT, anchor="topleft", size=8):
    """Flat 8px label with a 1px ink drop shadow (cheap and very legible)."""
    return draw_text(surf, text, size, pos, top=color, shadow=T.INK, depth=1,
                     outline=False, anchor=anchor)


def text_width(text, size):
    return T.font(size).size(text)[0]


# ----------------------------------------------------------------- panels
def chamfer_points(r, c):
    x, y, w, h = r
    return [(x + c, y), (x + w - c - 1, y), (x + w - 1, y + c),
            (x + w - 1, y + h - c - 1), (x + w - c - 1, y + h - 1),
            (x + c, y + h - 1), (x, y + h - c - 1), (x, y + c)]


@lru_cache(maxsize=64)
def _glow(w, h, color, c):
    pad = 6
    g = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
    for i, a in ((4, 26), (2, 46)):
        r = pygame.Rect(pad - i, pad - i, w + 2 * i, h + 2 * i)
        pygame.draw.polygon(g, tuple(color) + (a,), chamfer_points(r, c + i))
    return g


def neon_panel(surf, rect, color=T.MAGENTA, fill=T.PANEL, chamfer=3, glow=True, gloss=True):
    """Chamfered panel: ink edge, 2px neon ring, dark fill, glossy top highlight."""
    rect = pygame.Rect(rect)
    if glow:
        surf.blit(_glow(rect.w, rect.h, tuple(color), chamfer), (rect.x - 6, rect.y - 6))
    pygame.draw.polygon(surf, T.INK, chamfer_points(rect, chamfer))
    pygame.draw.polygon(surf, color, chamfer_points(rect.inflate(-2, -2), max(chamfer - 1, 1)))
    pygame.draw.polygon(surf, fill, chamfer_points(rect.inflate(-6, -6), max(chamfer - 2, 1)))
    if gloss:
        y = rect.y + 1
        pygame.draw.line(surf, lighter(color, 0.6),
                         (rect.x + chamfer + 1, y), (rect.right - chamfer - 3, y))
    return rect


def dim(surf, alpha=170, color=T.INK):
    shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    shade.fill(tuple(color) + (alpha,))
    surf.blit(shade, (0, 0))


def triangle(surf, x, y, size, color, facing="right"):
    """Little pixel arrow, `size` px tall, with an ink edge. (x, y) is its top-left base."""
    tip = size // 2 + 1
    sign = 1 if facing == "right" else -1
    pts = [(x, y), (x + sign * tip, y + size // 2), (x, y + size - 1)]
    pygame.draw.polygon(surf, T.INK, [(px, py) for px, py in pts], 0)
    inner = [(x + sign * 1, y + 2), (x + sign * (tip - 2), y + size // 2), (x + sign * 1, y + size - 3)]
    pygame.draw.polygon(surf, color, inner, 0)


# -------------------------------------------------------------- background
class Starfield:
    """Slowly scrolling 3-layer starfield with twinkle, shared by every menu."""

    LAYERS = ((10, T.DIM, 1), (22, T.PURPLE, 1), (40, T.CYAN, 2))

    def __init__(self, n=54, seed=7, w=T.LOGICAL_W, h=T.LOGICAL_H):
        rng = random.Random(seed)
        self.w, self.h = w, h
        self.stars = [[rng.uniform(0, w), rng.uniform(0, h), rng.randrange(3),
                       rng.uniform(0, math.tau)] for _ in range(n)]
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        for s in self.stars:
            s[1] = (s[1] + self.LAYERS[s[2]][0] * dt) % self.h

    def draw(self, surf):
        surf.fill(T.BG)
        for x, y, layer, phase in self.stars:
            _, color, size = self.LAYERS[layer]
            if layer == 2 and math.sin(self.t * 3 + phase) < -0.4:
                color = T.SOFT
            surf.fill(color, (int(x), int(y), size, size))
