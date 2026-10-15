import math
import random

import pytest

from src.game import rules
from src.game.enemies import KINDS, Enemy
from src.game.paths import Path
from src.game.waves import WAVES, Group, Wave
from src.game.world import World


# ------------------------------------------------------------------ paths
def test_straight_goes_down_at_speed():
    p = Path("straight", speed=40)
    x0, y0 = p.pos(0, 100)
    x1, y1 = p.pos(2, 100)
    assert x0 == x1 == 100 and y1 - y0 == pytest.approx(80)


def test_zigzag_swings_both_ways_within_amplitude():
    p = Path("zigzag", speed=40, amp=30, period=2.0)
    xs = [p.pos(t / 20, 160)[0] for t in range(80)]
    assert min(xs) == pytest.approx(130, abs=1) and max(xs) == pytest.approx(190, abs=1)
    ys = [p.pos(t / 20, 160)[1] for t in range(80)]
    assert ys == sorted(ys)  # always descending


def test_circle_orbits_a_descending_centre():
    p = Path("circle", speed=30, amp=20, period=2.0)
    for t in (0.0, 0.5, 1.3):
        x, y = p.pos(t, 160)
        cy = p.pos(t, 160, centre=True)[1]
        assert math.hypot(x - 160, y - cy) == pytest.approx(20)


def test_hover_enters_holds_then_leaves():
    p = Path("hover", speed=60, amp=40, period=3.0, hold_y=90, hold=4.0)
    enter = (90 - rules.ENTRY_Y) / 60
    assert p.pos(enter / 2, 160)[1] < 90
    holding = [p.pos(enter + k * 0.5, 160) for k in range(1, 8)]
    assert all(y == pytest.approx(90) for _, y in holding)
    assert len({round(x) for x, _ in holding}) >= 3  # strafes while holding
    assert p.pos(enter + 4.0 + 1.0, 160)[1] > 90


def test_unknown_path_is_rejected():
    with pytest.raises(ValueError):
        Path("teleport")


# ------------------------------------------------------------------ waves
def test_five_waves_each_with_a_different_mix():
    assert len(WAVES) == rules.WAVE_COUNT == 5
    mixes = [frozenset((g.kind, g.path.kind, g.fire_every is not None) for g in w.groups)
             for w in WAVES]
    assert len(set(mixes)) == 5
    used_paths = {g.path.kind for w in WAVES for g in w.groups}
    assert used_paths == {"straight", "zigzag", "circle", "hover"}
    assert any(g.fire_every for w in WAVES for g in w.groups)
    assert {g.kind for w in WAVES for g in w.groups} == set(KINDS)


def test_wave_spawns_stay_on_screen():
    for w in WAVES:
        for g in w.groups:
            for x in g.xs:
                assert 12 <= x - g.path.amp and x + g.path.amp <= rules.FIELD_W - 12, (w.name, g)


# ---------------------------------------------------------------- enemies
def test_enemy_takes_hits_and_flashes():
    e = Enemy("bot", Path("straight"), 100)
    assert e.hp == KINDS["bot"].hp == 2
    assert not e.hit()
    assert e.flash > 0
    assert e.hit()  # second hit kills


# ------------------------------------------------------------------ world
def one_group_wave(kind="drone", path=None, xs=(160,), fire_every=None):
    return Wave("test", (Group(0.0, kind, path or Path("straight", speed=60), xs, fire_every),))


def run(world, seconds, direction=0, dt=1 / 60):
    for _ in range(int(seconds / dt)):
        world.update(dt, direction)
        if world.phase in ("won", "lost"):
            break


def test_banner_then_spawn():
    w = World([one_group_wave(xs=(30,))])  # out of the ship's line of fire
    assert w.phase == "banner" and w.wave_number == 1
    run(w, rules.BANNER_TIME - 0.1)
    assert not w.enemies
    run(w, 0.2)
    assert w.phase == "fighting" and len(w.enemies) == 1


def test_autofire_kills_enemy_overhead_and_scores():
    w = World([one_group_wave(xs=(rules.FIELD_W / 2,))])
    run(w, 6)
    kills = [e for e in w.drain_events() if e[0] == "kill"]
    assert len(kills) == 1
    assert w.score >= KINDS["drone"].points


def test_wave_clear_bonus_and_win_with_lives_bonus():
    w = World([one_group_wave(xs=(rules.FIELD_W / 2,))])
    run(w, 10)
    assert w.phase == "won"
    events = [e[0] for e in w.drain_events()]
    assert "wave_cleared" in events and events[-1] == "won"
    expected = KINDS["drone"].points + rules.WAVE_BONUS * 1 + rules.LIFE_BONUS * rules.START_LIVES
    assert w.score == expected


def test_escaping_enemy_costs_a_life():
    w = World([one_group_wave(xs=(30,))])  # far from the ship's column
    run(w, 12)
    assert w.lives == rules.START_LIVES - 1
    assert "escaped" in [e[0] for e in w.drain_events()]


def test_enemy_bullet_hits_ship_then_invulnerable():
    hover = Path("hover", speed=80, amp=0, hold_y=80, hold=30)
    w = World([one_group_wave(kind="titan", path=hover, xs=(rules.FIELD_W / 2,), fire_every=0.4)])
    w.fire_enabled = False  # ship holds fire so the titan survives
    for _ in range(60 * 10):
        w.update(1 / 60, 0)
        if w.lives < rules.START_LIVES:
            break
    assert w.lives == rules.START_LIVES - 1
    assert "player_hit" in [e[0] for e in w.drain_events()]
    run(w, rules.INVULNERABLE_TIME - 0.1)
    assert w.lives == rules.START_LIVES - 1  # bullets pass through while invulnerable
    run(w, 1.5)
    assert w.lives == rules.START_LIVES - 2


def test_losing_all_lives_ends_the_game():
    w = World([one_group_wave(xs=(30, 290))] * 3)
    run(w, 60)
    assert w.phase == "lost" and w.lives == 0
    assert w.drain_events()[-1][0] == "lost"


def test_ship_stays_inside_the_field():
    w = World([one_group_wave()])
    run(w, 1.5, direction=-1)  # still on the banner, nothing to collide with
    assert w.ship_x == rules.SHIP_MARGIN
    w = World([one_group_wave()])
    run(w, 1.5, direction=1)
    assert w.ship_x == rules.FIELD_W - rules.SHIP_MARGIN


def test_later_waves_are_faster():
    w = World()
    assert w.speed_scale == 1.0
    w._start_wave(4)
    assert w.speed_scale == pytest.approx(1 + 4 * rules.SPEED_STEP)


# ------------------------------------------------------- balance check
def autopilot(world, lag_frames=12):
    """A cautious player: sidestep bullets about to land, else line up under the
    lowest enemy. Reacts `lag_frames` late, like a smoothed gesture model."""
    history = []

    def decide():
        for bx, by in world.bombs:
            if abs(bx - world.ship_x) < 26 and -4 < rules.SHIP_Y - by < 110:
                away = 1 if world.ship_x >= bx else -1
                if not rules.SHIP_MARGIN + 20 < world.ship_x + away * 20 < rules.FIELD_W - rules.SHIP_MARGIN - 20:
                    away = -away
                return away
        shootable = [e for e in world.enemies if e.y < rules.SHIP_Y - 50]
        if not shootable:
            return 0
        target = max(shootable, key=lambda e: e.y)
        dx = target.x - world.ship_x
        # people learn the lag and let go early; aim where the ship will coast to
        settle = 4 + rules.SHIP_SPEED * lag_frames / 60 * 0.8
        return 0 if abs(dx) < settle else (1 if dx > 0 else -1)

    def step():
        history.append(decide())
        return history[-lag_frames] if len(history) >= lag_frames else 0
    return step


def play(seed, lag_frames):
    w = World(rng=random.Random(seed))
    steer = autopilot(w, lag_frames)
    for _ in range(60 * 60 * 4):
        w.update(1 / 60, steer())
        if w.phase in ("won", "lost"):
            break
    return w


def test_full_game_is_winnable():
    for seed in range(5):
        w = play(seed, lag_frames=1)
        assert w.phase == "won", f"seed {seed}: lost on wave {w.wave_number}"


def test_gesture_lag_still_reaches_the_final_wave():
    """0.2 s and 0.33 s of lag (a smoothed 15 fps model) must not wall players early."""
    for lag in (12, 20):
        for seed in range(5):
            w = play(seed, lag)
            assert w.wave_number == rules.WAVE_COUNT, f"lag {lag} seed {seed}: wave {w.wave_number}"


def test_clearing_a_wave_mends_a_heart():
    w = World([one_group_wave(xs=(30,)), one_group_wave(xs=(30,))])
    run(w, 14)  # first enemy escapes -> lose a life, wave clears
    assert w.wave_number == 2 and w.lives == rules.START_LIVES
    assert "life_up" in [e[0] for e in w.drain_events()]


def test_a_player_who_never_moves_loses():
    w = World(rng=random.Random(1))
    run(w, 60 * 4)
    assert w.phase == "lost"
