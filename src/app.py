"""The game host: screen flow, per-frame update and drawing (see src/main.py).

    app = App(link, Leaderboard())
    app.handle_event(event); app.update(dt); app.draw(logical_surface)

run() opens the window and drives the loop.
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

import src.theme as T  # noqa: E402
from src import config  # noqa: E402
from src.game import rules  # noqa: E402
from src.game.render import Renderer  # noqa: E402
from src.game.world import World  # noqa: E402
from src.gesture.link import GestureLink, KeyboardLink  # noqa: E402
from src.leaderboard import Leaderboard  # noqa: E402
from src.ui import (GameOverScreen, Hud, LeaderboardScreen, PauseOverlay,  # noqa: E402
                    SignalLostOverlay, SpaceBackground, Starfield, StartMenu,
                    draw_wave_banner)
from src.ui.background import nebula_surface  # noqa: E402


class App:
    """Screen flow: menu <-> scores, menu -> playing <-> paused, playing -> game_over.

    Kept separate from main() so it can be stepped headless in tests.
    """

    def __init__(self, link, leaderboard: Leaderboard):
        self.link = link
        self.lb = leaderboard
        self.stars = Starfield()
        self.background = SpaceBackground(self.stars)
        self.renderer = Renderer()
        self.hud = Hud(max_lives=rules.START_LIVES, total_waves=rules.WAVE_COUNT)
        self.pause = PauseOverlay()
        self.signal = SignalLostOverlay(link)
        self.world = World()
        self.state = "menu"
        self.screen = StartMenu(self.stars, link)
        self.t = 0.0

    # ---- transitions
    def go(self, state):
        self.state = state
        if state == "menu":
            self.screen = StartMenu(self.stars, self.link)
        elif state == "scores":
            self.screen = LeaderboardScreen(self.lb, stars=self.stars)
        elif state == "game_over":
            self.screen = GameOverScreen(self.world.score, self.lb, won=self.world.phase == "won")

    def new_game(self):
        self.world = World()
        self.renderer.reset()
        self.hud.reset()
        self.state = "playing"

    # ---- input
    def handle_event(self, e):
        if self.state == "playing":
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_p, pygame.K_ESCAPE):
                self.state = "paused"
            elif self.signal_lost and self.signal.handle_event(e) == "retry":
                self.link.retry()
            return
        if self.state == "paused":
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_p, pygame.K_ESCAPE):
                self.state = "playing"
            return
        action = self.screen.handle_event(e)
        if action == "play" and self.link.connected:
            self.new_game()
        elif action == "restart":
            if self.link.connected:
                self.new_game()
            else:
                self.go("menu")  # the menu shows why PLAY is locked
        elif action == "retry":
            self.link.retry()
        elif action == "scores":
            self.go("scores")
        elif action in ("back", "menu"):
            self.go("menu")

    @property
    def signal_lost(self) -> bool:
        return self.state == "playing" and not self.link.connected

    # ---- per frame
    def update(self, dt):
        self.t += dt
        self.link.poll()
        if self.state == "playing":
            if self.signal_lost:
                self.signal.update(dt)
            else:
                self.world.update(dt, self.link.direction())
                self.renderer.on_events(self.world.drain_events())
                self.renderer.update(dt)
                self.background.update(dt)
                if self.world.phase in ("won", "lost"):
                    self.go("game_over")
        elif self.state == "paused":
            self.pause.update(dt)
        else:
            self.screen.update(dt)
            if self.state == "game_over":
                self.renderer.update(dt)
                self.background.update(dt * 0.3)
        live = self.state == "playing" and not self.signal_lost
        self.hud.update(dt if live else 0, self.world.score, self.world.lives, self.world.wave_number)

    def draw(self, surf):
        if self.state in ("menu", "scores"):
            self.screen.draw(surf)
            return
        self.background.draw(surf)
        self.renderer.draw(surf, self.world)
        self.hud.draw(surf)
        if self.state == "playing" and self.world.phase == "banner":
            draw_wave_banner(surf, self.world.wave_number, rules.WAVE_COUNT,
                             self.world.wave_name, self.t)
        if self.state == "paused":
            self.pause.draw(surf)
        elif self.signal_lost:
            self.signal.draw(surf)
        elif self.state == "game_over":
            self.screen.draw(surf)


def run(argv=None):
    args = parse_args(argv)
    try:
        cfg = config.load(args.config)
    except config.ConfigError as e:
        print(e, file=sys.stderr)
        return 2

    link = KeyboardLink() if args.dev_keyboard else GestureLink(cfg)
    link.start()  # TensorFlow loads in the worker while the window opens
    pygame.init()
    try:
        window = pygame.display.set_mode((T.LOGICAL_W * T.SCALE, T.LOGICAL_H * T.SCALE))
        pygame.display.set_caption("BEAT THE AI")
        logical = pygame.Surface((T.LOGICAL_W, T.LOGICAL_H))
        clock = pygame.time.Clock()
        nebula_surface()  # build the backdrop now, not on the first frame of play
        app = App(link, Leaderboard())
        running = True
        while running:
            dt = min(clock.tick(60) / 1000, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                else:
                    app.handle_event(e)
            app.update(dt)
            app.draw(logical)
            pygame.transform.scale(logical, window.get_size(), window)  # nearest neighbour
            pygame.display.flip()
    finally:
        link.stop()
        pygame.quit()
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="BEAT THE AI")
    parser.add_argument("--dev-keyboard", action="store_true",
                        help="steer with the arrow keys instead of gestures (development only)")
    parser.add_argument("--config", default=config.DEFAULT_PATH, help="path to config.toml")
    return parser.parse_args(argv)
