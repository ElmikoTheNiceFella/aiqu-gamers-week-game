"""Render every UI screen to PNG with no window (SDL dummy driver).

    python tools/screenshot_ui.py            # writes docs/ui/*.png at 2x
Useful for design review and as a visual regression check.
"""
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

import pygame  # noqa: E402

import theme as T  # noqa: E402
from leaderboard import Leaderboard  # noqa: E402
from ui import (GameOverScreen, Hud, LeaderboardScreen, PauseOverlay,  # noqa: E402
                StartMenu, Starfield)
from ui import sprites  # noqa: E402

OUT = os.path.join(ROOT, "docs", "ui")


def sample_board():
    lb = Leaderboard(os.path.join(tempfile.mkdtemp(), "lb.json"))
    for n, s in [("AAA", 1240), ("BOT", 980), ("ZED", 760), ("MAX", 640), ("LIA", 410),
                 ("SAM", 300), ("JOY", 150)]:
        lb.add(n, s)
    return lb


def save(logical, name):
    big = pygame.transform.scale(logical, (T.LOGICAL_W * T.SCALE, T.LOGICAL_H * T.SCALE))
    pygame.image.save(big, os.path.join(OUT, name))


def fake_game_frame(surf, stars):
    stars.draw(surf)
    for i in range(12):
        u = sprites.get("ufo", 2)
        surf.blit(u, (28 + (i % 6) * 44, 52 + (i // 6) * 30))
    s = sprites.get("ship", 2)
    surf.blit(s, s.get_rect(midbottom=(T.LOGICAL_W // 2, T.LOGICAL_H - 12)))


def main():
    os.makedirs(OUT, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((T.LOGICAL_W * T.SCALE, T.LOGICAL_H * T.SCALE))
    logical = pygame.Surface((T.LOGICAL_W, T.LOGICAL_H))
    stars = Starfield()
    stars.update(0.5)

    m = StartMenu(stars)
    m.update(0.4)
    m.draw(logical)
    save(logical, "01_start_menu.png")

    hud = Hud()
    hud.update(0, 1240, 3)
    fake_game_frame(logical, stars)
    hud.draw(logical)
    save(logical, "02_hud_3_lives.png")

    hud.update(0.0, 1240, 2)
    hud.update(0.4, 1240, 2)  # mid-flash on the broken heart
    fake_game_frame(logical, stars)
    hud.draw(logical)
    save(logical, "03_hud_hit.png")

    hud.update(1.0, 1240, 1)
    hud.update(1.0, 1240, 1)
    fake_game_frame(logical, stars)
    hud.draw(logical)
    save(logical, "04_hud_1_life.png")

    fake_game_frame(logical, stars)
    hud.draw(logical)
    p = PauseOverlay()
    p.draw(logical)
    save(logical, "05_pause.png")

    lbs = LeaderboardScreen(sample_board(), highlight=2)
    lbs.draw(logical)
    save(logical, "06_leaderboard.png")

    lb = sample_board()
    g = GameOverScreen(850, lb)  # qualifies: initials entry
    g.initials = "BO"
    fake_game_frame(logical, stars)
    hud.draw(logical)
    g.draw(logical)
    save(logical, "07_game_over_initials.png")

    g = GameOverScreen(0, lb)  # no record: restart / menu
    fake_game_frame(logical, stars)
    hud.draw(logical)
    g.draw(logical)
    save(logical, "08_game_over_buttons.png")
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
