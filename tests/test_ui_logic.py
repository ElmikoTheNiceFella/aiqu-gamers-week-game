import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from src.input_source import (Smoother, SharedDirection, label_to_direction,  # noqa: E402
                          parse_labels)
from src.leaderboard import MAX_ENTRIES, Leaderboard, clean_name  # noqa: E402


def board(tmp_path):
    return Leaderboard(str(tmp_path / "lb.json"))


def test_leaderboard_orders_and_persists(tmp_path):
    lb = board(tmp_path)
    assert lb.add("bob", 50) == 0
    assert lb.add("amy", 80) == 0
    assert lb.add("cat", 50) == 2  # tie goes below the older entry
    assert [e[0] for e in lb.entries] == ["AMY", "BOB", "CAT"]
    assert board(tmp_path).entries == lb.entries  # reloaded from disk


def test_leaderboard_caps_and_rejects(tmp_path):
    lb = board(tmp_path)
    for i in range(MAX_ENTRIES):
        lb.add("AAA", 100 + i)
    assert not lb.qualifies(100)  # equal to the lowest does not qualify
    assert lb.add("ZZZ", 100) is None
    assert lb.add("ZZZ", 500) == 0
    assert len(lb.entries) == MAX_ENTRIES
    assert not lb.qualifies(0)


def test_leaderboard_survives_corrupt_file(tmp_path):
    p = tmp_path / "lb.json"
    p.write_text("{not json")
    assert Leaderboard(str(p)).entries == []


def test_clean_name():
    assert clean_name("a!b") == "AB-"
    assert clean_name("") == "AAA"
    assert clean_name("abcdef") == "ABC"


def test_parse_labels_and_directions():
    assert parse_labels("0 Left\n1 Right\n2 Idle\n") == ["left", "right", "idle"]
    assert label_to_direction("Left") == -1
    assert label_to_direction("RIGHT") == 1
    assert label_to_direction("peace sign") == 0


def test_smoother_ignores_flicker_and_low_confidence():
    s = Smoother(window=5, min_conf=0.8)
    for lab, conf in [("left", 0.95), ("left", 0.9), ("right", 0.95), ("left", 0.99)]:
        out = s.push(lab, conf)
    assert out == "left"
    s = Smoother(window=3, min_conf=0.8)
    for _ in range(3):
        out = s.push("right", 0.5)
    assert out == "idle"


def test_shared_direction():
    d = SharedDirection()
    assert d.direction() == 0
    d.set_label("Right")
    assert d.direction() == 1


def test_sprites_are_rectangular():
    pygame.init()
    pygame.display.set_mode((8, 8))
    from src.ui import sprites
    for name in sprites.BITMAPS:
        sprites.get(name)  # asserts on ragged rows


def test_hud_flashes_on_life_lost():
    pygame.init()
    from src.ui.hud import Hud
    h = Hud()
    h.update(0.0, 0, 3)
    h.update(0.016, 0, 2)
    assert h._hit_idx == 2 and h._hit_timer > 0


def test_game_over_initials_flow(tmp_path):
    pygame.init()
    pygame.display.set_mode((8, 8))
    from src.ui import GameOverScreen
    lb = board(tmp_path)
    g = GameOverScreen(300, lb)
    assert g.entering
    for ch in "abcd":
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))
    assert g.initials == "ABC"
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r"))
    assert not g.entering and lb.entries == [("ABC", 300)]
    act = g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r"))
    assert act == "restart"


def test_teachable_machine_letters():
    from src.input_source import direction_letter
    assert parse_labels("0 L\n1 R\n2 N\n") == ["l", "r", "n"]
    assert [label_to_direction(x) for x in ("L", "r", "N")] == [-1, 1, 0]
    assert [direction_letter(d) for d in (-1, 0, 1)] == ["L", "N", "R"]


def test_check_labels():
    from src.input_source import check_labels
    assert check_labels(["l", "r", "n"]) is None
    assert check_labels(["left", "right", "idle"]) is None
    assert "R" in check_labels(["l", "n"])
    assert "N" in check_labels(["l", "r"])
    assert "L" in check_labels(["r", "thumbs up", "n"])
    assert check_labels([]) is not None
