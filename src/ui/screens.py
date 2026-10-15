"""Full-screen UI states. Each screen exposes the same tiny interface:

    handle_event(event) -> action string | None
    update(dt)
    draw(surface)

The host game decides what each action means ("play", "scores", "back",
"restart", "menu", "retry"). Screens never change game state themselves.

The start menu and the signal-lost overlay read a gesture link (anything with
status, status_text, detail, connected and letter; see src/gesture/link.py).
"""
from __future__ import annotations

import math

import pygame

import src.theme as T
from . import sprites
from . import draw
from .widgets import Button, Menu

W, H = T.LOGICAL_W, T.LOGICAL_H
CX = W // 2


def _blink(t, hz=2.0):
    return int(t * hz * 2) % 2 == 0


def wrap(text, width=26, lines=3):
    """Split a message into at most `lines` lines of `width` 8px characters."""
    out, line = [], ""
    for word in text.upper().split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    out.append(line)
    out = [o[:width] for o in out]
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][:width - 3] + "..."
    return out


LINK_COLORS = {"ready": T.CYAN, "error": T.PINK}


# ------------------------------------------------------------------ start
class StartMenu:
    """Title, PLAY / SCORES and, with a gesture link, its connection status.

    PLAY stays disabled until the link is connected. Actions: "play", "scores",
    "retry" (R while the link reports an error).
    """

    def __init__(self, stars: draw.Starfield | None = None, link=None):
        self.stars = stars or draw.Starfield()
        self.link = link
        self.t = 0.0
        self.play = Button("PLAY", (CX - 80, 186, 160, 30), "play", T.MAGENTA)
        self.menu = Menu([self.play, Button("SCORES", (CX - 80, 224, 160, 30), "scores", T.CYAN)])

    def handle_event(self, e):
        if (self.link is not None and self.link.status == "error"
                and e.type == pygame.KEYDOWN and e.key == pygame.K_r):
            return "retry"
        return self.menu.handle_event(e)

    def update(self, dt):
        self.t += dt
        self.stars.update(dt)
        self.menu.update(dt)
        self.play.enabled = self.link is None or self.link.connected

    def draw(self, surf):
        self.stars.draw(surf)
        bob = int(round(math.sin(self.t * 3) * 2))
        robot = sprites.get("robot", 3)
        surf.blit(robot, robot.get_rect(midtop=(CX, 4 + bob)))
        for x, y, phase in ((CX - 60, 26, 0.0), (CX + 58, 44, 1.3), (CX - 46, 58, 2.1)):
            if math.sin(self.t * 4 + phase) > -0.3:
                s = sprites.get("sparkle", 1)
                surf.blit(s, s.get_rect(center=(x, y)))

        t0, t1 = T.GAME_TITLE
        draw.draw_text(surf, t0, 40, (CX, 68), top=T.YELLOW, bottom=T.ORANGE,
                       shadow=T.MAGENTA, depth=3, anchor="midtop")
        # "THE" cyan + "AI" magenta, centred as one line
        gap = draw.text_width(" ", 24)
        w_the = draw.text_width("THE", 24)
        w_ai = draw.text_width("AI", 24)
        x = CX - (w_the + gap + w_ai) // 2
        draw.draw_text(surf, "THE", 24, (x, 116), top=T.CYAN, bottom=T.BLUE,
                       shadow=T.PURPLE, depth=3)
        draw.draw_text(surf, "AI", 24, (x + w_the + gap, 116), top=(255, 140, 235),
                       bottom=T.MAGENTA, shadow=T.PURPLE, depth=3)

        draw.draw_small(surf, T.TAGLINE, (CX, 154), T.SOFT, anchor="midtop")
        self.menu.draw(surf)
        if self.link is None:
            if _blink(self.t, 1.0):
                draw.draw_small(surf, "PRESS ENTER", (CX, 282), T.DIM, anchor="midtop")
            return
        self._draw_link(surf)

    def _draw_link(self, surf):
        link = self.link
        color = LINK_COLORS.get(link.status, T.YELLOW)
        if link.status == "ready" and not link.connected:
            color = T.YELLOW
        error = link.status == "error"
        panel = pygame.Rect(CX - 112, 264, 224, 58 if error else 48)
        draw.neon_panel(surf, panel, draw.darker(color, 0.3), glow=False)
        dots = "." * (int(self.t * 3) % 4) if link.status not in ("ready", "error") else ""
        draw.draw_small(surf, f"AI LINK: {link.status_text}{dots}", (panel.x + 10, panel.y + 9), color)
        if link.connected:
            draw.draw_small(surf, "SEES", (panel.x + 10, panel.y + 25), T.DIM)
            for i, letter in enumerate("LNR"):
                r = pygame.Rect(panel.x + 52 + i * 22, panel.y + 21, 18, 16)
                on = letter == link.letter
                draw.neon_panel(surf, r, T.CYAN if on else T.PURPLE, chamfer=2, glow=False, gloss=False)
                draw.draw_small(surf, letter, r.center, T.WHITE if on else T.DIM, anchor="center")
            draw.draw_small(surf, "MOVE ME!", (panel.right - 10, panel.y + 25), T.DIM, anchor="topright")
        else:
            lines = wrap(link.detail or "PLEASE WAIT", lines=3 if error else 1)
            for i, line in enumerate(lines):
                draw.draw_small(surf, line, (panel.x + 10, panel.y + 21 + i * 10), T.SOFT)
        if link.status == "error":
            msg = "R TO RETRY"
        elif link.connected:
            msg = "PRESS ENTER"
        else:
            msg = "SHOW YOUR HAND TO THE CAMERA" if link.status == "ready" else "WARMING UP THE AI"
        if _blink(self.t, 1.0):
            draw.draw_small(surf, msg, (CX, panel.bottom + 10), T.DIM, anchor="midtop")


# ------------------------------------------------------------ leaderboard
class LeaderboardScreen:
    ROW_H = 21
    TOP = 62

    def __init__(self, leaderboard, highlight: int | None = None,
                 stars: draw.Starfield | None = None):
        self.lb = leaderboard
        self.highlight = highlight
        self.stars = stars or draw.Starfield()
        self.t = 0.0
        self.menu = Menu([Button("BACK", (CX - 60, 322, 120, 28), "back", T.CYAN, size=8)])

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            return "back"
        return self.menu.handle_event(e)

    def update(self, dt):
        self.t += dt
        self.stars.update(dt)
        self.menu.update(dt)

    def draw(self, surf):
        self.stars.draw(surf)
        trophy = sprites.get("trophy", 2)
        title_w = draw.text_width("LEADERBOARD", 16)
        draw.draw_text(surf, "LEADERBOARD", 16, (CX, 28), top=T.YELLOW, bottom=T.ORANGE,
                       shadow=T.MAGENTA, depth=2, anchor="midtop")
        surf.blit(trophy, trophy.get_rect(midright=(CX - title_w // 2 - 8, 38)))
        surf.blit(trophy, trophy.get_rect(midleft=(CX + title_w // 2 + 8, 38)))

        panel = pygame.Rect(18, 56, W - 36, self.ROW_H * 10 + 14)
        draw.neon_panel(surf, panel, T.MAGENTA)
        medal = (T.YELLOW, T.SOFT, T.ORANGE)
        for i in range(10):
            y = self.TOP + 4 + i * self.ROW_H
            if i % 2 == 0:
                pygame.draw.rect(surf, draw.mix(T.PANEL, T.PURPLE, 0.25),
                                 (panel.x + 5, y - 3, panel.w - 10, self.ROW_H - 1))
            if i < len(self.lb.entries):
                name, score = self.lb.entries[i]
                color = medal[i] if i < 3 else T.CYAN
                if i == self.highlight and _blink(self.t, 3):
                    color = T.PINK
            else:
                name, score, color = "---", 0, T.DIM
            draw.draw_small(surf, f"{i + 1:>2}", (panel.x + 14, y), color)
            draw.draw_small(surf, name, (panel.x + 56, y), color)
            draw.draw_small(surf, f"{score:06d}", (panel.right - 14, y), color, anchor="topright")
        self.menu.draw(surf)


# ------------------------------------------------------------------ pause
class PauseOverlay:
    """Dim the frozen game and say GAME PAUSED. Nothing else, no settings.
    theme.SHOW_RESUME_HINT adds a small hint line if the team ever wants one."""

    def __init__(self):
        self.t = 0.0

    def handle_event(self, e):
        return None  # the host toggles pause with its own key

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        draw.dim(surf, 160)
        h = 76 if T.SHOW_RESUME_HINT else 64
        panel = pygame.Rect(0, 0, 240, h)
        panel.center = (CX, H // 2)
        ring = T.CYAN if _blink(self.t, 1.0) else T.BLUE
        draw.neon_panel(surf, panel, ring)
        y = panel.centery - (6 if T.SHOW_RESUME_HINT else 0)
        draw.draw_text(surf, "GAME PAUSED", 16, (CX, y), top=T.WHITE, bottom=T.CYAN,
                       shadow=T.BLUE, depth=2, anchor="center")
        if T.SHOW_RESUME_HINT:
            draw.draw_small(surf, "PRESS P TO RESUME", (CX, panel.bottom - 18), T.DIM, anchor="midtop")


# ------------------------------------------------------------ wave banner
def draw_wave_banner(surf, number, total, name, t):
    """The "WAVE n" card shown at the start of each wave (over the game)."""
    panel = pygame.Rect(0, 0, 220, 78)
    panel.center = (CX, H // 2 - 20)
    draw.neon_panel(surf, panel, T.MAGENTA if number < total else T.YELLOW)
    draw.draw_text(surf, f"WAVE {number}", 24, (CX, panel.y + 12), top=T.YELLOW, bottom=T.ORANGE,
                   shadow=T.MAGENTA, depth=2, anchor="midtop")
    draw.draw_small(surf, name, (CX, panel.y + 46), T.CYAN, anchor="midtop")
    label = "FINAL WAVE" if number == total else f"OF {total}"
    if _blink(t, 2.0) or number < total:
        draw.draw_small(surf, label, (CX, panel.y + 60), T.DIM if number < total else T.PINK,
                        anchor="midtop")


# ------------------------------------------------------------ signal lost
class SignalLostOverlay:
    """Shown over the frozen game while the gesture link is down. The game
    resumes by itself when labels flow again. Action: "retry" on R after an error."""

    def __init__(self, link):
        self.link = link
        self.t = 0.0

    def handle_event(self, e):
        if self.link.status == "error" and e.type == pygame.KEYDOWN and e.key == pygame.K_r:
            return "retry"
        return None

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        draw.dim(surf, 170)
        error = self.link.status == "error"
        lines = wrap(self.link.detail, lines=2) if error else ["SHOW YOUR HAND", "TO THE CAMERA"]
        panel = pygame.Rect(0, 0, 250, 96)
        panel.center = (CX, H // 2)
        draw.neon_panel(surf, panel, T.PINK if _blink(self.t, 1.0) else T.MAGENTA)
        draw.draw_text(surf, "SIGNAL LOST", 16, (CX, panel.y + 14), top=T.WHITE, bottom=T.PINK,
                       shadow=T.PURPLE, depth=2, anchor="midtop")
        for i, line in enumerate(lines):
            draw.draw_small(surf, line, (CX, panel.y + 44 + i * 12), T.SOFT, anchor="midtop")
        draw.draw_small(surf, "R TO RETRY" if error else "GAME RESUMES BY ITSELF",
                        (CX, panel.bottom - 18), T.DIM, anchor="midtop")


# -------------------------------------------------------------- game over
class GameOverScreen:
    """Shows the final score. If it makes the leaderboard, asks for 3 initials first.

    won=True (all waves cleared) swaps GAME OVER for YOU BEAT THE AI.
    Actions: "restart", "menu". `self.saved_rank` holds the rank (0-based) once saved.
    """

    def __init__(self, score, leaderboard, won=False):
        self.won = won
        self.score = score
        self.lb = leaderboard
        self.best = max(leaderboard.best, score)
        self.is_record = score > 0 and score >= leaderboard.best
        self.entering = leaderboard.qualifies(score)
        self.initials = ""
        self.saved_rank = None
        self.t = 0.0
        self.menu = Menu([
            Button("RESTART", (CX - 85, 232, 170, 30), "restart", T.MAGENTA),
            Button("MENU", (CX - 85, 270, 170, 30), "menu", T.CYAN),
        ])

    # ---- input
    def handle_event(self, e):
        if self.entering:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._save()
                elif e.key == pygame.K_BACKSPACE:
                    self.initials = self.initials[:-1]
                elif len(self.initials) < 3 and e.unicode and e.unicode.isalnum() and e.unicode.isascii():
                    self.initials += e.unicode.upper()
            return None
        return self.menu.handle_event(e)

    def _save(self):
        name = self.initials or "AAA"
        self.saved_rank = self.lb.add(name, self.score)
        self.initials = self.lb.entries[self.saved_rank][0] if self.saved_rank is not None else name
        self.entering = False

    def update(self, dt):
        self.t += dt
        self.menu.update(dt)

    # ---- drawing
    def draw(self, surf):
        draw.dim(surf, 205)
        if self.won:
            draw.draw_text(surf, "YOU BEAT", 24, (CX, 26), top=T.YELLOW, bottom=T.ORANGE,
                           shadow=T.MAGENTA, depth=3, anchor="midtop")
            draw.draw_text(surf, "THE AI", 32, (CX, 60), top=(255, 140, 235), bottom=T.MAGENTA,
                           shadow=T.PURPLE, depth=3, anchor="midtop")
        else:
            draw.draw_text(surf, "GAME", 32, (CX, 22), top=(255, 160, 235), bottom=T.MAGENTA,
                           shadow=T.PURPLE, depth=3, anchor="midtop")
            draw.draw_text(surf, "OVER", 32, (CX, 62), top=(255, 160, 235), bottom=T.MAGENTA,
                           shadow=T.PURPLE, depth=3, anchor="midtop")

        panel = pygame.Rect(CX - 105, 112, 210, 70)
        draw.neon_panel(surf, panel, T.CYAN)
        draw.draw_small(surf, "SCORE", (CX, panel.y + 10), T.DIM, anchor="midtop")
        draw.draw_text(surf, f"{self.score:06d}", 24, (CX, panel.y + 24), top=T.YELLOW,
                       bottom=T.ORANGE, shadow=T.MAGENTA, depth=2, anchor="midtop")
        draw.draw_small(surf, f"BEST {self.best:06d}", (CX, panel.bottom - 14), T.CYAN, anchor="midtop")

        if self.entering:
            self._draw_entry(surf)
        else:
            if self.saved_rank is not None:
                msg = f"RANK {self.saved_rank + 1}!"
                draw.draw_small(surf, msg, (CX, 198), T.YELLOW, anchor="midtop")
            elif self.is_record and self.score > 0:
                draw.draw_small(surf, "NEW HIGH SCORE!", (CX, 198), T.YELLOW, anchor="midtop")
            self.menu.draw(surf)

    def _draw_entry(self, surf):
        if _blink(self.t, 2):
            msg = "NEW HIGH SCORE!" if self.is_record else "YOU MADE THE TOP 10!"
            draw.draw_small(surf, msg, (CX, 196), T.YELLOW, anchor="midtop")
        draw.draw_small(surf, "ENTER YOUR INITIALS", (CX, 212), T.SOFT, anchor="midtop")
        box_w, gap = 30, 8
        x0 = CX - (3 * box_w + 2 * gap) // 2
        for i in range(3):
            r = pygame.Rect(x0 + i * (box_w + gap), 232, box_w, 38)
            active = i == len(self.initials)
            draw.neon_panel(surf, r, T.PINK if active else T.PURPLE, chamfer=2, glow=active)
            if i < len(self.initials):
                draw.draw_text(surf, self.initials[i], 16, r.center, top=T.WHITE,
                               bottom=T.CYAN, shadow=T.BLUE, depth=1, anchor="center")
            elif active and _blink(self.t, 3):
                pygame.draw.rect(surf, T.YELLOW, (r.x + 8, r.bottom - 11, r.w - 16, 3))
        draw.draw_small(surf, "ENTER TO SAVE", (CX, 288), T.DIM, anchor="midtop")
