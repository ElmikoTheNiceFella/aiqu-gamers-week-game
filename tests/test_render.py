import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

import src.theme as T  # noqa: E402
from src.game import rules  # noqa: E402
from src.game.enemies import KINDS  # noqa: E402


@pytest.fixture(autouse=True)
def display():
    pygame.init()
    pygame.display.set_mode((8, 8))


def test_field_matches_screen_and_hud():
    from src.ui.hud import HUD_H
    assert (rules.FIELD_W, rules.FIELD_H) == (T.LOGICAL_W, T.LOGICAL_H)
    assert rules.FIELD_TOP == HUD_H


def test_enemy_sprites_match_hitboxes():
    from src.ui import sprites
    for kind, spec in KINDS.items():
        for hp in range(1, spec.hp + 1):
            for flashing in (False, True):
                img = sprites.get(sprites.enemy_name(kind, hp, flashing), 2)
                assert img.get_size() == (spec.w, spec.h), (kind, hp, flashing)


def test_start_menu_locks_play_until_connected():
    from tools.screenshot_ui import StaticLink
    from src.ui import StartMenu
    link = StaticLink("loading_model", "starting tensorflow")
    menu = StartMenu(link=link)
    menu.update(0.1)
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")
    assert menu.handle_event(enter) is None
    link.status, link.connected = "ready", True
    menu.update(0.1)
    assert menu.handle_event(enter) == "play"


def test_start_menu_offers_retry_on_error():
    from tools.screenshot_ui import StaticLink
    from src.ui import StartMenu
    menu = StartMenu(link=StaticLink("error", "camera 0 could not be opened"))
    r = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r, unicode="r")
    assert menu.handle_event(r) == "retry"


def test_wrap_keeps_messages_inside_the_panel():
    from src.ui.screens import wrap
    lines = wrap("keras_model.h5 not found in models/keras-model please export again", lines=2)
    assert len(lines) == 2 and all(len(x) <= 26 for x in lines)
    assert lines[-1].endswith("...")


def test_app_pauses_on_signal_loss_and_resumes():
    from tools.screenshot_ui import StaticLink, sample_board
    from src.app import App
    link = StaticLink("ready", direction=1)
    app = App(link, sample_board())
    app.new_game()
    app.update(0.5)
    x = app.world.ship_x
    assert x > rules.FIELD_W / 2  # steering right
    link.connected = False
    app.update(0.5)
    assert app.signal_lost and app.world.ship_x == x  # frozen
    link.connected = True
    app.update(0.1)
    assert not app.signal_lost and app.world.ship_x > x


def test_app_reaches_game_over_with_initials():
    from tools.screenshot_ui import StaticLink, sample_board
    from src.app import App
    app = App(StaticLink("ready"), sample_board())
    app.new_game()
    app.world.score = 500
    app.world.lives = 0
    app.world.phase = "lost"
    app.update(0.016)
    assert app.state == "game_over" and app.screen.entering and not app.screen.won


def test_screenshot_tool_renders_every_screen(tmp_path):
    from tools import screenshot_ui
    files = screenshot_ui.main(str(tmp_path))
    assert len(files) == 16
    assert all(os.path.getsize(tmp_path / f) > 1000 for f in files)
