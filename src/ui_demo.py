"""Playable UI sandbox: every screen wired together with a placeholder game.

    python src/ui_demo.py

Keys: arrows/WASD move, ENTER/SPACE select, P or ESC pause, F1 toggles the
sandbox "force hit" (lose a life) so you can see the hearts and Game Over fast.
The gameplay below is a stub. Replace StubGame with the real game; the UI
calls (Hud.update, screens, Leaderboard) stay the same.
"""
import os
import random
import sys

from src.ui import HUD_H, GameOverScreen, Hud, LeaderboardScreen, PauseOverlay, Starfield, StartMenu

sys.path.insert(0, os.path.dirname(__file__))

import pygame  # noqa: E402

import src.theme as T  # noqa: E402
from src.input_source import KeyboardDirection  # noqa: E402
from src.leaderboard import Leaderboard  # noqa: E402
from src.ui import (sprites)

START_LIVES = 3


class StubGame:
    """Falling UFOs, auto-firing ship. Just enough to exercise score and lives."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.score, self.lives = 0, START_LIVES
        self.x = T.LOGICAL_W / 2
        self.ufos, self.shots = [], []
        self.spawn_t, self.fire_t = 0.0, 0.0

    def hit(self):
        self.lives = max(0, self.lives - 1)

    def update(self, dt, direction):
        self.x = max(16, min(T.LOGICAL_W - 16, self.x + direction * 150 * dt))
        self.spawn_t -= dt
        self.fire_t -= dt
        if self.spawn_t <= 0:
            self.spawn_t = 0.9
            self.ufos.append([random.uniform(16, T.LOGICAL_W - 30), float(HUD_H)])
        if self.fire_t <= 0:
            self.fire_t = 0.3
            self.shots.append([self.x, T.LOGICAL_H - 40.0])
        for s in self.shots:
            s[1] -= 220 * dt
        for u in self.ufos:
            u[1] += 40 * dt
        for s in list(self.shots):
            for u in list(self.ufos):
                if abs(s[0] - (u[0] + 14)) < 16 and abs(s[1] - (u[1] + 8)) < 10:
                    self.shots.remove(s)
                    self.ufos.remove(u)
                    self.score += 10
                    break
        for u in list(self.ufos):
            if u[1] > T.LOGICAL_H - 40:
                self.ufos.remove(u)
                self.hit()
        self.shots = [s for s in self.shots if s[1] > HUD_H]

    def draw(self, surf):
        for u in self.ufos:
            surf.blit(sprites.get("ufo", 2), (int(u[0]), int(u[1])))
        for s in self.shots:
            pygame.draw.rect(surf, T.CYAN, (int(s[0]) - 1, int(s[1]), 2, 6))
        ship = sprites.get("ship", 2)
        surf.blit(ship, ship.get_rect(midbottom=(int(self.x), T.LOGICAL_H - 10)))


def main():
    pygame.init()
    window = pygame.display.set_mode((T.LOGICAL_W * T.SCALE, T.LOGICAL_H * T.SCALE))
    pygame.display.set_caption("BEAT THE AI - UI demo")
    logical = pygame.Surface((T.LOGICAL_W, T.LOGICAL_H))
    clock = pygame.time.Clock()

    lb = Leaderboard()
    stars = Starfield()
    game, hud, keys = StubGame(), Hud(), KeyboardDirection()
    state = "menu"
    screen = StartMenu(stars)
    pause = PauseOverlay()

    def go(new_state):
        nonlocal state, screen
        state = new_state
        if new_state == "menu":
            screen = StartMenu(stars)
        elif new_state == "scores":
            screen = LeaderboardScreen(lb, stars=stars)
        elif new_state == "game_over":
            screen = GameOverScreen(game.score, lb)
        elif new_state == "playing" and game.lives == 0:
            game.reset()

    running = True
    while running:
        dt = min(clock.tick(60) / 1000, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif state == "playing":
                if e.type == pygame.KEYDOWN and e.key in (pygame.K_p, pygame.K_ESCAPE):
                    state = "paused"
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F1:
                    game.hit()
            elif state == "paused":
                if e.type == pygame.KEYDOWN and e.key in (pygame.K_p, pygame.K_ESCAPE):
                    state = "playing"
            else:
                action = screen.handle_event(e)
                if action in ("play", "restart"):
                    game.reset()
                    hud.reset()
                    state = "playing"
                elif action == "scores":
                    go("scores")
                elif action in ("back", "menu"):
                    go("menu")

        if state == "playing":
            game.update(dt, keys.direction())
            if game.lives == 0:
                go("game_over")
        elif state != "paused":
            screen.update(dt)
        stars.update(dt if state in ("playing", "menu", "scores", "game_over") else 0)
        hud.update(dt if state != "paused" else 0, game.score, game.lives)
        pause.update(dt)

        if state in ("playing", "paused", "game_over"):
            stars.draw(logical)
            game.draw(logical)
            hud.draw(logical)
            if state == "paused":
                pause.draw(logical)
            elif state == "game_over":
                screen.draw(logical)
        else:
            screen.draw(logical)

        pygame.transform.scale(logical, window.get_size(), window)  # nearest neighbour
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
