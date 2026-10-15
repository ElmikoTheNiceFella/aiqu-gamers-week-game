"""Numbers that define the game. Logical pixels and seconds; no pygame here.

FIELD_W/FIELD_H match theme.LOGICAL_W/H and FIELD_TOP matches ui.hud.HUD_H
(tests/test_render.py checks that they stay in step).
"""
FIELD_W, FIELD_H = 320, 360
FIELD_TOP = 28  # gameplay sits below the HUD bar
ENTRY_Y = FIELD_TOP - 12  # enemies appear from behind the HUD
ESCAPE_Y = FIELD_H + 12  # an enemy centre past this has got through

START_LIVES = 3
WAVE_COUNT = 5
BANNER_TIME = 2.0  # "WAVE n" card before the spawns start
SPEED_STEP = 0.08  # each wave runs this much faster than the one before

SHIP_Y = FIELD_H - 20  # ship centre
SHIP_SPEED = 140
SHIP_MARGIN = 12
SHIP_HIT_W, SHIP_HIT_H = 18, 14  # smaller than the sprite, so near misses feel fair
FIRE_EVERY = 0.32
SHOT_SPEED = 260
BOMB_SPEED = 100
BOMB_SIZE = 6
INVULNERABLE_TIME = 1.5
FIRE_ZONE_BOTTOM = FIELD_H * 0.6  # enemies stop shooting once they are this low

WAVE_BONUS = 100  # times the wave number
LIFE_BONUS = 250  # per life left after the last wave
