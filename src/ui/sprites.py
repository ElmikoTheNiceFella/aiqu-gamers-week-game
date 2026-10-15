"""Pixel-art sprites defined as ASCII bitmaps, so they stay crisp and editable.

Each sprite is a list of equal-length strings. '.' is transparent; every other
character is looked up in a palette dict. `get(name, scale)` returns a cached
Surface. Never mutate a returned surface; copy it first.
"""
from functools import lru_cache

import pygame

import src.theme as T

# ---------------------------------------------------------------- bitmaps
HEART = [
    ".kkkk...kkkk.",
    "kwwppkkkppppk",
    "kwpppppppppdk",
    "kppppppppppdk",
    "kppppppppppdk",
    ".kppppppppdk.",
    "..kppppppdk..",
    "...kppppdk...",
    "....kppdk....",
    ".....kdk.....",
    "......k......",
]

TROPHY = [
    "..kkkkkkkkkk..",
    ".kyywyyyyyoyk.",
    "kkyywyyyyyoykk",
    "kykyywyyyyokyk",
    "kykyyyyyyyokyk",
    ".kkkyyyyyyokk.",
    "...kyyyyyok...",
    "....kyyyok....",
    ".....kyok.....",
    ".....kyok.....",
    "....kkkkkk....",
    "...kyyyyyyk...",
    "...kooooook...",
    "...kkkkkkkk...",
]

SPARKLE = [
    "...y...",
    "...y...",
    "..yyy..",
    "yyywyyy",
    "..yyy..",
    "...y...",
    "...y...",
]

# The AI mascot: helmet, dark visor with a ^_^ face, blue ear plates, antenna.
ROBOT = [
    ".............kcck...",
    ".............kcck...",
    "..............kBk...",
    "..............kBk...",
    "...kkkkkkkkkkkkkk...",
    "..kwwwwwwwwwwwwwwk..",
    ".kwwkkkkkkkkkkkkwwk.",
    ".kwkhnnnnnnnnnnnkwk.",
    ".kBknnncnnnncnnnkBk.",
    ".kBknncncnncncnnkBk.",
    ".kBknnnnnnnnnnnnkBk.",
    ".kBknnnncnncnnnnkBk.",
    ".kBknnnnnccnnnnnkBk.",
    ".kwknnnnnnnnnnnnkwk.",
    ".kwwkkkkkkkkkkkkwwk.",
    "..kwwwwwwwwwwwwwbk..",
    "...kbbbbbbbbbbbbk...",
    "....kkkkkkkkkkkk....",
]

UFO = [
    "....kkkkkk....",
    "...kccwcccck..",
    "..kcccccccck..",
    "kkkkkkkkkkkkkk",
    "kmwmwmwmwmwmmk",
    "kgggggggggggmk",
    ".kkkkkkkkkkkk.",
    "..kk......kk..",
]

SHIP = [
    ".......k.......",
    "......kwk......",
    "......kwk......",
    ".....kwcwk.....",
    "..k..kwcwk..k..",
    ".kwk.kwwwk.kwk.",
    ".kwkkkwwwkkkwk.",
    "kwwwwwwbwwwwwwk",
    "kwbwwkkkkkwwbwk",
    "kkkk.kmmmk.kkkk",
    ".....k...k.....",
]

# ---------------------------------------------------------------- palettes
_BASE = {
    "k": T.INK,
    "w": T.WHITE,
    "y": T.YELLOW,
    "o": T.ORANGE,
    "p": T.PINK,
    "d": (214, 0, 150),
    "c": T.CYAN,
    "B": T.BLUE,
    "n": (14, 10, 52),
    "h": (70, 60, 140),
    "b": (150, 150, 235),
    "m": T.MAGENTA,
    "g": (110, 110, 150),
}

PALETTES = {
    "heart": _BASE,
    "heart_empty": {**_BASE, "p": (40, 26, 84), "d": (30, 18, 64),
                    "w": (74, 58, 128), "k": T.DIM},
    "heart_hit": {**_BASE, "p": T.WHITE, "d": (255, 190, 230), "w": T.WHITE},
    "trophy": _BASE,
    "sparkle": _BASE,
    "robot": _BASE,
    "ufo": _BASE,
    "ship": _BASE,
}

BITMAPS = {
    "heart": HEART,
    "heart_empty": HEART,
    "heart_hit": HEART,
    "trophy": TROPHY,
    "sparkle": SPARKLE,
    "robot": ROBOT,
    "ufo": UFO,
    "ship": SHIP,
}


@lru_cache(maxsize=None)
def get(name: str, scale: int = 1) -> pygame.Surface:
    rows = BITMAPS[name]
    pal = PALETTES[name]
    w, h = len(rows[0]), len(rows)
    for r in rows:
        assert len(r) == w, f"{name}: ragged row {r!r} ({len(r)} != {w})"
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x, y), pal[ch] + (255,))
    if scale != 1:
        surf = pygame.transform.scale(surf, (w * scale, h * scale))
    return surf
