"""Render every screen to PNG with no window (SDL dummy driver).

    python tools/screenshot_ui.py            # writes docs/ui/*.png at 2x

Drives the real App (src/main.py) with a stand-in gesture link, so what you see
is what the game draws. Useful for design review against ui-new/ and as a
visual regression check. tests/test_render.py runs it into a temp folder.
"""
import os
import random
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402

import src.theme as T  # noqa: E402
from src.game.enemies import Enemy  # noqa: E402
from src.game.waves import WAVES  # noqa: E402
from src.game.world import World  # noqa: E402
from src.input_source import direction_letter  # noqa: E402
from src.leaderboard import Leaderboard  # noqa: E402
from src.app import App  # noqa: E402
from src.ui import draw, sprites  # noqa: E402

OUT = os.path.join(ROOT, "docs", "ui")


class StaticLink:
    """A gesture link frozen in one state, for screenshots and tests."""

    TEXT = {"loading_model": "LOADING MODEL", "opening_camera": "OPENING CAMERA",
            "ready": "ONLINE", "error": "ERROR"}

    def __init__(self, status="ready", detail="", connected=None, direction=0):
        self.status, self.detail = status, detail
        self.connected = status == "ready" if connected is None else connected
        self._direction = direction

    @property
    def status_text(self):
        if self.status == "ready" and not self.connected:
            return "NO SIGNAL"
        return self.TEXT.get(self.status, self.status.upper())

    @property
    def letter(self):
        return direction_letter(self.direction())

    def direction(self):
        return self._direction if self.connected else 0

    def start(self):
        pass

    def stop(self):
        pass

    def retry(self):
        pass

    def poll(self):
        pass


def sample_board():
    lb = Leaderboard(os.path.join(tempfile.mkdtemp(), "lb.json"))
    for n, s in [("AAA", 1240), ("BOT", 980), ("ZED", 760), ("MAX", 640), ("LIA", 410),
                 ("SAM", 300), ("JOY", 150)]:
        lb.add(n, s)
    return lb


def save(logical, out, name):
    big = pygame.transform.scale(logical, (T.LOGICAL_W * T.SCALE, T.LOGICAL_H * T.SCALE))
    pygame.image.save(big, os.path.join(out, name))


def mid_wave(app, wave_index, seconds):
    """Put the app into play on a given wave, `seconds` after its spawns begin."""
    app.new_game()
    app.world = World(rng=random.Random(4))
    app.world.enemies.clear()
    app.world._start_wave(wave_index)
    app.world.score = 1240
    app.world.phase = "fighting"
    for _ in range(int(seconds * 60)):
        app.world.update(1 / 60, 0)
        app.renderer.on_events(app.world.drain_events())
        app.renderer.update(1 / 60)
    app.background.update(0.5)


def sprite_sheet(logical):
    logical.fill(T.BG)
    draw.draw_text(logical, "SPRITES", 8, (T.LOGICAL_W // 2, 8), top=T.YELLOW, bottom=T.ORANGE,
                   shadow=T.MAGENTA, depth=1, anchor="midtop")
    rows = [
        ("SHIP  FLAME 1 / 2 / HIT    ENEMY SHOT", ["ship_flame1", "ship_flame2", "ship_hit"], ["orb", "orb"]),
        ("DRONE  1 HP  /  HIT FLASH", ["drone", "drone_flash"], []),
        ("BOT  2 HP  /  1 HP  /  HIT FLASH", ["bot", "bot_hurt", "bot_flash"], []),
        ("TITAN  5 HP  /  4 HP  /  3 HP", ["titan5", "titan4", "titan3"], []),
        ("TITAN  2 HP  /  1 HP  /  HIT FLASH", ["titan2", "titan1", "titan_flash"], []),
    ]
    y = 24
    for label, names, extras in rows:
        draw.draw_small(logical, label, (16, y), T.DIM)
        x, h = 16, 0
        for n in names:
            img = sprites.get(n, 2)
            logical.blit(img, (x, y + 12))
            x += img.get_width() + 18
            h = max(h, img.get_height())
        for i, n in enumerate(extras):
            img = sprites.get(n, 2)
            logical.blit(img, (244 + i * 30, y + 16))
        y += h + 26


def main(out=OUT):
    os.makedirs(out, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((T.LOGICAL_W * T.SCALE, T.LOGICAL_H * T.SCALE))
    logical = pygame.Surface((T.LOGICAL_W, T.LOGICAL_H))

    def menu_shot(link, name):
        app = App(link, sample_board())
        app.update(0.4)
        app.draw(logical)
        save(logical, out, name)

    menu_shot(StaticLink("loading_model", "starting tensorflow"), "01_start_menu_connecting.png")
    menu_shot(StaticLink("ready", direction=-1), "01_start_menu.png")
    menu_shot(StaticLink("error", "camera 0 won't open: allow camera access for your "
                                  "terminal app"), "01_start_menu_error.png")

    link = StaticLink("ready")
    app = App(link, sample_board())
    mid_wave(app, 1, 3.0)
    app.hud.update(0, app.world.score, 3, app.world.wave_number)
    app.draw(logical)
    save(logical, out, "02_hud_3_lives.png")

    app.world.lives = 2
    app.hud.update(0.0, app.world.score, 2, app.world.wave_number)
    app.hud.update(0.4, app.world.score, 2, app.world.wave_number)  # mid-flash
    app.draw(logical)
    save(logical, out, "03_hud_hit.png")

    app.world.lives = 1
    app.hud.update(1.0, app.world.score, 1, app.world.wave_number)
    app.hud.update(1.0, app.world.score, 1, app.world.wave_number)
    app.draw(logical)
    save(logical, out, "04_hud_1_life.png")

    app.state = "paused"
    app.draw(logical)
    save(logical, out, "05_pause.png")

    lb_app = App(link, sample_board())
    lb_app.go("scores")
    lb_app.screen.highlight = 2
    lb_app.update(0.1)
    lb_app.draw(logical)
    save(logical, out, "06_leaderboard.png")

    app.world.score, app.world.phase = 850, "lost"
    app.go("game_over")
    app.screen.initials = "BO"
    app.draw(logical)
    save(logical, out, "07_game_over_initials.png")

    app.world.score = 0
    app.go("game_over")
    app.draw(logical)
    save(logical, out, "08_game_over_buttons.png")

    sprite_sheet(logical)
    save(logical, out, "09_sprite_sheet.png")

    mid_wave(app, 4, 6.0)
    app.world.enemies.append(Enemy("titan", WAVES[3].groups[0].path, 160))
    app.world.enemies[-1].update(4.0)
    app.world.enemies[-1].hit()
    app.hud.update(0, app.world.score, 3, app.world.wave_number)
    app.draw(logical)
    save(logical, out, "10_gameplay_enemies.png")

    bg_app = App(link, sample_board())
    bg_app.new_game()
    bg_app.world.phase = "fighting"
    bg_app.background.planet = [110, 90]
    bg_app.update(0.016)
    bg_app.draw(logical)
    save(logical, out, "11_background_particles.png")

    banner = App(link, sample_board())
    banner.new_game()
    banner.world._start_wave(2)
    banner.update(0.3)
    banner.draw(logical)
    save(logical, out, "12_wave_banner.png")

    lost = App(StaticLink("ready", connected=False), sample_board())
    mid_wave(lost, 2, 4.0)
    lost.update(0.3)
    lost.draw(logical)
    save(logical, out, "13_signal_lost.png")

    win = App(link, sample_board())
    mid_wave(win, 4, 1.0)
    win.world.enemies.clear()
    win.world.score, win.world.phase = 2995, "won"
    win.go("game_over")
    win.update(0.016)
    win.draw(logical)
    save(logical, out, "14_victory_initials.png")
    files = sorted(os.listdir(out))
    print("wrote", files)
    return files


if __name__ == "__main__":
    main()
