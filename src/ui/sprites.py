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

# Engine flame frames hang below the ship's nozzle; both are the same height so
# the ship doesn't bob when they alternate.
SHIP_FLAME1 = SHIP + [
    "......oyo......",
    ".......o.......",
    "...............",
]
SHIP_FLAME2 = SHIP + [
    "......yoy......",
    "......oyo......",
    ".......y.......",
]

# Enemies from ui-new/09_sprite_sheet.png. At scale 2 their sizes match the
# hitboxes in src/game/enemies.py (tests/test_render.py checks).
DRONE = [  # 1 HP: cyan frame, pink eye
    "..m.......m..",
    "..k.......k..",
    ".kkkkkkkkkkk.",
    "kcwccccccccck",
    "kcknnnnnnnkck",
    "kcknnmmmnnkck",
    "kcknnmwmnnkck",
    "kcknnnnnnnkck",
    "kccccccccccck",
    ".kbkkkkkkkbk.",
    "..m.......m..",
]

BOT = [  # 2 HP: magenta cat-ear head, yellow eyes
    ".mm..........mm.",
    ".mmk........kmm.",
    "kmmmkkkkkkkkmmmk",
    "kmppppppppppppmk",
    "kmpkkkkkkkkkkpmk",
    "kmpkyykkkkyykpmk",
    "kmpkyykkkkyykpmk",
    "kmpkkkkkkkkkkpmk",
    "kmppppppppppppmk",
    ".kmmmmmmmmmmmmk.",
    "..kd........dk..",
]

TITAN = [  # 5 HP: gold dome with a pink screen
    "......kkkkkkkkkkkk......",
    "....kkyyyywyyyyyyykk....",
    "...kyyywwyyyyyyyyyyok...",
    "..kyyywkkkkkkkkkkyyyok..",
    ".kyyyyykknnnnnnkkyyyyok.",
    ".kyyyyyknnmmmmnnkyyyyok.",
    "kyyyyyyknnmwmmnnkyyyyyok",
    "kyyyyyyknnnnnnnnkyyyyyok",
    "kyyyyyyykkkkkkkkyyyyyyok",
    "kooooooooooooooooooooook",
    ".kkkkkkkkkkkkkkkkkkkkkk.",
    "...kmk....kyyk....kmk...",
]

ORB = [  # enemy shot
    ".pp.",
    "pwpp",
    "pppd",
    ".dd.",
]


def _paint(rows, pixels):
    """Copy of `rows` with (x, y, char) pixels painted on: cracks, sparks."""
    out = [list(r) for r in rows]
    for x, y, ch in pixels:
        out[y][x] = ch
    return ["".join(r) for r in out]


_CRACKS_1 = [(3, 5, "k"), (4, 6, "k"), (4, 7, "k"), (20, 4, "k"), (19, 5, "k")]
_CRACKS_2 = _CRACKS_1 + [(5, 8, "k"), (18, 6, "k"), (19, 7, "k"), (12, 2, "k"), (13, 1, "k")]
_SPARKS = [(7, 0, "y"), (16, 0, "y"), (5, 1, "y")]

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
# Hit flash: white silhouette with the ink lines and dark screens kept.
_FLASH = {k: (T.INK if k in "kn" else T.WHITE) for k in _BASE}
_HURT_BOT = {**_BASE, "m": (150, 20, 120), "p": (190, 40, 150), "y": T.ORANGE}
_HURT_TITAN = {**_BASE, "y": T.ORANGE, "o": (196, 84, 10), "w": T.YELLOW}

PALETTES = {
    "heart": _BASE,
    "heart_empty": {**_BASE, "p": (40, 26, 84), "d": (30, 18, 64),
                    "w": (74, 58, 128), "k": T.DIM},
    "heart_hit": {**_BASE, "p": T.WHITE, "d": (255, 190, 230), "w": T.WHITE},
    "trophy": _BASE,
    "sparkle": _BASE,
    "robot": _BASE,
    "ship": _BASE,
    "ship_flame1": _BASE,
    "ship_flame2": _BASE,
    "ship_hit": {**_BASE, "w": T.PINK, "b": T.MAGENTA, "c": T.WHITE},
    "drone": _BASE,
    "drone_flash": _FLASH,
    "bot": _BASE,
    "bot_hurt": _HURT_BOT,
    "bot_flash": _FLASH,
    "titan5": _BASE,
    "titan4": _BASE,
    "titan3": _BASE,
    "titan2": _HURT_TITAN,
    "titan1": _HURT_TITAN,
    "titan_flash": _FLASH,
    "orb": _BASE,
}

BITMAPS = {
    "heart": HEART,
    "heart_empty": HEART,
    "heart_hit": HEART,
    "trophy": TROPHY,
    "sparkle": SPARKLE,
    "robot": ROBOT,
    "ship": SHIP,
    "ship_flame1": SHIP_FLAME1,
    "ship_flame2": SHIP_FLAME2,
    "ship_hit": SHIP_FLAME1,
    "drone": DRONE,
    "drone_flash": DRONE,
    "bot": BOT,
    "bot_hurt": _paint(BOT, [(4, 0, "y"), (11, 1, "y")]),
    "bot_flash": BOT,
    "titan5": TITAN,
    "titan4": _paint(TITAN, _CRACKS_1),
    "titan3": _paint(TITAN, _CRACKS_2),
    "titan2": _paint(TITAN, _CRACKS_2),
    "titan1": _paint(TITAN, _CRACKS_2 + _SPARKS),
    "titan_flash": TITAN,
    "orb": ORB,
}


def enemy_name(kind: str, hp: int, flashing: bool) -> str:
    """Sprite for an enemy in its current state (see the ui-new sprite sheet)."""
    if flashing:
        return f"{kind}_flash"
    if kind == "bot":
        return "bot" if hp >= 2 else "bot_hurt"
    if kind == "titan":
        return f"titan{max(1, min(5, hp))}"
    return kind


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
