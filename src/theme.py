"""Design tokens for the neon-arcade UI.

Everything draws onto a LOGICAL_W x LOGICAL_H surface that the host integer-scales
(nearest neighbour) to the window, so pixel art and Press Start 2P stay crisp.
Keep font sizes at multiples of 8 for the sharpest text.
"""
import os
from functools import lru_cache

import pygame

LOGICAL_W, LOGICAL_H = 320, 360
SCALE = 2  # window = logical * SCALE

GAME_TITLE = ("BEAT", "THE AI")  # two big lines on the start menu
TAGLINE = "THINK YOU CAN OUTSMART AI?"
SHOW_RESUME_HINT = False  # the pause menu is literally just "GAME PAUSED"

# Palette, sampled from the ChatGPT sticker set
INK = (5, 3, 18)
BG = (9, 7, 30)
PANEL = (18, 11, 52)
DIM = (96, 86, 150)
SOFT = (200, 195, 235)
CYAN = (26, 230, 255)
BLUE = (30, 100, 255)
MAGENTA = (255, 43, 214)
PINK = (255, 60, 170)
PURPLE = (124, 32, 255)
YELLOW = (255, 217, 26)
ORANGE = (255, 146, 20)
WHITE = (255, 255, 255)

FONT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "PressStart2P-Regular.ttf")
)


@lru_cache(maxsize=None)
def font(size: int) -> pygame.font.Font:
    return pygame.font.Font(FONT_PATH, size)


def to_logical(pos):
    """Window pixel -> logical pixel (for mouse events)."""
    return pos[0] // SCALE, pos[1] // SCALE
