# AGENTS.md

Guide for people and coding agents working on BEAT THE AI.

## What this project is

BEAT THE AI is a retro arcade shooter in the Space Invaders / Galaga style, written in pygame. The player steers the ship left and right with hand gestures only. Gestures are recognised by an image model trained in Google Teachable Machine with three classes: `L`, `R` and `N`. The goal is to survive 5 waves.

The game is built for a classroom relay. Each student plays using the gestures the previous student trained, then trains a new set of gestures for the next student. The first set is trained by the team.

Fire is automatic. Gestures only control left, right and neutral. The keyboard and mouse are for the operator: menus, pause and typing initials. They never move the ship (except with the development flag below).

## Commands

```bash
pip install -r requirements.txt            # pygame-ce + pytest
pip install -r requirements-gesture.txt    # tensorflow, tf-keras, opencv, numpy (needed to play)

python -m src.main                         # the game (gesture control, settings in config.toml)
python -m src.main --dev-keyboard          # development only: arrow keys / A-D, no camera
python -m pytest -q                        # all tests (~3 s)
python -m pytest -q tests/test_game.py::test_full_game_is_winnable   # one test
python tools/screenshot_ui.py              # renders every screen to docs/ui/*.png
```

Run from the repo root. All imports use the `src.` package (`import src.theme as T`). `pytest.ini` puts the root on the path, so bare `pytest` works as well.

Tests that need TensorFlow, OpenCV or the model export skip themselves when those are missing.

On macOS, the first run asks for camera access for the terminal app. If it was refused, the start menu shows `CAMERA 0 WON'T OPEN`. Allow it in System Settings > Privacy & Security > Camera, then press R on the menu.

## Repo layout

```
config.toml             model folder, camera index, mirror, fps, smoothing (read by src/config.py)
assets/fonts/           Press Start 2P, OFL licensed, see OFL.txt
src/main.py             entry point; stays import-light (see "Worker process")
src/app.py              App: screen flow, update, draw; run() opens the window
src/config.py           config.toml loader with validation (no pygame)
src/gesture/worker.py   child process: webcam -> model -> L/R/N messages
src/gesture/link.py     GestureLink, the game-side handle on the worker; KeyboardLink (dev)
src/game/               pure game logic: rules, paths, enemies, waves, world; render.py draws it
src/input_source.py     label parsing and validation, L/R/N -> direction, Smoother
src/leaderboard.py      top-10 scores in data/leaderboard.json (no pygame)
src/theme.py            design tokens (palette, logical size, fonts)
src/ui/                 sprites, drawing helpers, widgets, HUD, screens, gameplay background
tools/screenshot_ui.py  headless screenshots of every screen (also a test fixture)
ui-new/                 the reference design the screens are matched against
models/keras-model/     the Teachable Machine export the game loads (git-ignored)
```

## How pygame and Teachable Machine work together

Teachable Machine is where a model gets trained, in the browser. pygame is where the game runs. The only things that cross between them are a model file and a label name.

```
Teachable Machine (browser)            game process                    worker process (spawned)
  webcam samples -> train -> export      GestureLink.poll() each frame    keras_model.h5 + labels.txt
                                            ^                             webcam -> OpenCV frame
                                            |  ("status", name, detail)   -> 224x224 -> model
                                            |  ("label", L|R|N, conf)     -> Smoother
                                            +------ multiprocessing.Queue ----+
  game loop: if link.connected: world.update(dt, link.direction())
```

### 1. The class contract

Every model must contain a left, a right and a neutral class. Names are matched case-insensitively (`LABEL_TO_DIR` in `src/input_source.py`):

| Class name | Also accepted | Ship does |
| --- | --- | --- |
| `L` | Left | moves left |
| `R` | Right | moves right |
| `N` | Neutral, Idle, None | stands still |

Students pick which hand gesture means which class. The game never needs to know the gesture, only the class name. Any other class name is treated as neutral. `check_labels()` rejects a model that lacks any of the three, and the start menu shows why.

The neutral class matters. A classifier always picks some class, so without a class for "hand relaxed" or "no hand in frame" the ship would always be moving.

### 2. Training in Teachable Machine

1. Open Teachable Machine and start an Image Project (standard image model).
2. Create the classes `L`, `R` and `N` and record webcam samples for each.
3. Vary distance, lighting, background and which hand is used. Include samples with no hand in the frame under `N`.
4. Train, then use the in-page preview to check each gesture before exporting.

Teachable Machine prepares images at 224x224 and the exported model expects that input size.

### 3. Exporting

Use Export Model, then the TensorFlow tab, then the Keras option, and download. You get `keras_model.h5` and `labels.txt` in a folder called `converted_keras`. Put both files in `models/keras-model/` (or point `[model] dir` in `config.toml` at another folder).

`labels.txt` has one line per class in the form `0 L`. Use `parse_labels()` rather than splitting by hand.

### 4. Running the model (`src/gesture/worker.py`)

Preprocessing matches Teachable Machine; if it doesn't, accuracy drops:

- Mirror the frame if `[camera] mirror` is true (the Teachable Machine webcam preview is mirrored).
- Convert to RGB (OpenCV returns BGR).
- Make it square: `crop = "center"` (default) crops the middle square, like the Teachable Machine webcam; `"squash"` resizes the whole frame. With centre crop the player must stand in the middle of the camera view.
- Resize to 224x224 and scale pixels with `(x / 127.5) - 1`.

**Load with `tf_keras`, not `keras`.** Keras 3 (the default since TensorFlow 2.16) cannot rebuild the nested legacy Sequential model Teachable Machine saves. Patching `DepthwiseConv2D(groups=...)` gets past the first error but fails later with `Layer "functional_..." expects 1 named input(s) ... but it received 2 input tensors`. The Keras 2 package `tf-keras` loads the export unchanged. Keep its version in step with `tensorflow` (tested: both 2.21 on Python 3.12, macOS). Inference takes about 24 ms per 720p frame, so 15 fps uses roughly a third of one core.

The worker validates the folder and labels before importing TensorFlow, so a missing or wrong export fails fast with a readable message. Every failure (missing files, bad labels, missing packages, camera won't open, camera stops sending frames, any exception) becomes an `("status", "error", message)` message, never a crash in the game.

### 5. Worker process

The worker runs in a separate process (`multiprocessing`, spawn start method), not a thread. Loading TensorFlow and running the model would otherwise hold the GIL and stutter the menu. The game sees:

- `link.status`: `starting`, `loading_model`, `opening_camera`, `ready`, `error` or `stopped`, plus `link.detail`.
- `link.connected`: status is `ready` and a label arrived in the last `GestureLink.STALE_AFTER` (1.0 s).
- `link.direction()`: -1, 0 or +1, and always 0 when not connected.
- `link.retry()`: stop and restart the worker (R on the start menu or the signal-lost panel after an error).

Rules that keep the game responsive and correct:

- Never run the model inside the pygame loop.
- The game reads `direction()` only. `KeyboardLink` (development flag) has the same interface.
- Keep `src/main.py` free of pygame imports. Spawn re-imports `__main__` in the child, and pygame's SDL2 next to OpenCV's bundled SDL2 makes macOS warn about duplicate classes and possible crashes. The game itself lives in `src/app.py`.
- Smoothing (`Smoother`: majority vote over `smoothing_window` predictions; anything below `min_confidence` counts as neutral) happens in the worker. Tune both in `config.toml` with real students.

### 6. Known problems

Mirroring. Players expect a mirror image. A model trained on one orientation steers backwards on the other. Check "raise left hand, ship goes left" before every session; the start menu shows the live L / N / R the model sees once it is online.

Pose models. Teachable Machine has a pose project type, but this game uses image models, the type the Keras export above covers.

Browser alternative. If installing TensorFlow in a school lab is a problem, the model could run in a browser page instead (`@teachablemachine/image` with a hosted model URL) and send the predicted class to the game. A new link class with the `GestureLink` interface would be the entry point. This path is not built.

## Game flow and rules

`src/app.py` is a small state machine: `menu` <-> `scores`, `menu` -> `playing` <-> `paused`, `playing` -> `game_over` -> `playing` or `menu`.

- PLAY is disabled until the link is connected. The menu's AI LINK panel shows loading progress, errors (with R TO RETRY), or the live L / N / R once online.
- During play, if the link stops being connected, the game freezes behind a SIGNAL LOST panel and resumes on its own when labels flow again.
- P or Esc pauses.

Game logic is in `src/game/` and has no pygame dependency, so it is fully unit-tested:

- `World.update(dt, direction)` runs ship movement, auto-fire, spawns, enemy movement and fire, collisions, lives and wave progression. It reports what happened through `drain_events()`: `wave`, `kill`, `damage`, `player_hit`, `escaped`, `wave_cleared`, `life_up`, `won`, `lost`. `Renderer.on_events` turns kills into debris.
- `world.phase` is `banner` (the WAVE n card, `BANNER_TIME`), `fighting`, `won` or `lost`.
- Enemy kinds (`enemies.py`): drone 1 HP / 10 pts, bot 2 HP / 25 pts, titan 5 HP / 100 pts. Hitboxes equal the sprite size at scale 2 (a test checks).
- Movement (`paths.py`): `straight`, `zigzag`, `circle` and `hover` (enter, strafe, then leave). These are pure functions of time. Any group can also shoot (`fire_every`).
- Waves (`waves.py`) are data: timed groups of a kind, a path and x positions. Each wave runs `SPEED_STEP` faster. Enemy bullets keep a constant speed so late waves stay dodgeable.
- A life is lost to an enemy bullet, an enemy ramming the ship, or an enemy escaping past the bottom. After a hit the ship is invulnerable for 1.5 s. Clearing a wave mends one heart, up to 3.
- Score: kills, plus 100 x wave number per cleared wave, plus 250 per heart left after wave 5. Winning or losing goes to `GameOverScreen` (won shows YOU BEAT THE AI), which asks for initials if the score makes the top 10.
- Numbers live in `rules.py`. When changing difficulty, run `tests/test_game.py`. Its autopilot plays with 1, 12 and 20 frames of lag (a smoothed 15 fps model) and checks that the game is winnable and that laggy players still reach the final wave.

## The student relay

```
Round 1:  team model        -> Student A plays, then trains model A
Round 2:  model A           -> Student B plays, then trains model B
Round 3:  model B           -> Student C plays ...
```

The game loads the folder in `config.toml` (`models/keras-model/` by default). At the start of each round, replace that folder's contents with the previous student's export and restart the game. To replay a round later, keep copies of old exports outside `models/keras-model/`.

The start menu validates the folder and labels before the round starts. A student who forgot the `N` class finds out there, not mid-game.

Not built yet: a calibration screen with the camera feed. The live L / N / R indicator on the menu is the current check.

Privacy: webcam frames are never written to disk. Do not commit anything from `models/`. Check the school's rules on student images before running this with a class.

## UI system

All UI draws on a 320x360 logical surface. The host scales it up by an integer (`SCALE = 2`) with nearest-neighbour scaling, so pixel art and Press Start 2P stay sharp. Window mouse positions are converted with `theme.to_logical`. The reference design is in `ui-new/`.

Rules:

- Take colours, sizes and strings from `src/theme.py`. Do not hard-code them in screens.
- Font sizes are multiples of 8. Text is drawn without anti-aliasing.
- Text comes from `ui/draw.py`: `draw_text` for gradient headings with an extrusion and ink outline, `draw_small` for flat 8px labels. `screens.wrap()` fits a message to 26 characters per line.
- `text_surface()` is cached and returns shared surfaces. Never modify one.
- Sprites are ASCII bitmaps in `ui/sprites.py`, so they are easy to edit and diff. `get(name, scale)` is cached too. Enemy HP states and hit flashes are palette swaps or painted cracks on the same bitmap; `enemy_name(kind, hp, flashing)` picks one.
- Menus use the plain `Starfield`. Gameplay uses `SpaceBackground` (dithered nebula, drifting ringed planet, 0/1 digits, stars).
- The look follows the ChatGPT sticker set: ink outlines, neon magenta and cyan frames, yellow to orange gradients, small yellow sparkles.

Every full screen has the same interface and returns an action string. The host decides what the action does.

| Screen | Actions | Notes |
| --- | --- | --- |
| `StartMenu(stars, link)` | `play`, `scores`, `retry` | PLAY disabled until `link.connected`; AI LINK status panel |
| `LeaderboardScreen(lb, highlight=None)` | `back` | Top 10, `highlight` blinks a new entry |
| `PauseOverlay` | none | Says GAME PAUSED and nothing else. `theme.SHOW_RESUME_HINT` is False by design |
| `SignalLostOverlay(link)` | `retry` | Shown automatically while the link is down mid-game |
| `GameOverScreen(score, lb, won=False)` | `restart`, `menu` | Asks for 3 initials first if the score makes the top 10 |

`draw_wave_banner(surf, number, total, name, t)` draws the WAVE n card.

HUD:

```python
hud = Hud(max_lives=3, total_waves=5)
hud.update(dt, score, lives, wave)   # every frame; a drop in lives flashes the broken heart
hud.draw(surface)
hud.reset()                          # on restart
```

With one life left the last heart pulses. The HUD is 28px tall (`HUD_H`, equal to `rules.FIELD_TOP`); gameplay sits below it.

Leaderboard:

```python
lb = Leaderboard()             # data/leaderboard.json
lb.qualifies(score)            # score > 0 and in the top 10
rank = lb.add("AB", score)     # 0-based rank, or None
```

Ties rank below the older entry, names are uppercased to 3 characters, and saves are atomic. The leaderboard is per machine. For a shared classroom board, put the file on a shared path or add a small server later.

To add a screen: create a class with `handle_event`, `update` and `draw`, return action strings, wire it in `App`, and add it to `tools/screenshot_ui.py` so it gets a screenshot. `test_screenshot_tool_renders_every_screen` counts the files, so update it too.

## Testing

- `tests/test_game.py`: paths, waves, world rules, and the balance autopilot.
- `tests/test_gesture.py`: link messages through a fake multiprocessing context, a real spawned worker reporting a missing model, label validation, preprocessing, and loading the real export (skipped if absent).
- `tests/test_config.py`: config parsing and error messages.
- `tests/test_render.py`: sprite sizes against hitboxes, menu locking, App signal-lost and game-over flow, and the screenshot tool rendering all 16 screens headless.
- `tests/test_ui_logic.py`: leaderboard, label parsing, smoothing, HUD flash, initials entry.

Visual changes should also be checked by eye: `python tools/screenshot_ui.py`, then compare `docs/ui/` with `ui-new/`. The camera itself can't be tested headless. Before a class, run `python -m src.main` and check each gesture against the live L / N / R on the menu.

## Not done yet

- Calibration screen with the camera feed.
- Sound.
- Browser / hosted-model gesture source.
