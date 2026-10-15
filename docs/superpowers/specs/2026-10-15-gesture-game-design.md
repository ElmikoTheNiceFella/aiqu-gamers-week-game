# BEAT THE AI: gesture-controlled game design

Date: 2026-10-15. Status: approved (structure reviewed with the user; gameplay,
connection and testing sections use the defaults below).

## Decisions made with the user

| Topic | Decision |
| --- | --- |
| Model source | Local Keras export, `models/keras-model/` (fixed name), path set in `config.toml` |
| Labels | Teachable Machine classes `L`, `R`, `N` (left, right, neutral) |
| "No keyboard" | The ship only moves by gesture. Menus, pause and initials still use keyboard/mouse |
| End of game | Win (clear wave 5) or lose (0 lives). Both show the score; name entry only if top 10 |
| Name | 3 arcade initials, as in `ui-new/` |
| Enemy movement | Hybrid: timed spawn groups, each enemy on its own path; reaching the bottom costs a life |
| Inference | Separate worker process (multiprocessing, spawn) streaming status and labels over a queue |

## Structure

- `config.toml` + `src/config.py`: stdlib `tomllib`, defaults, validation, paths relative to repo root.
- `src/gesture/worker.py`: child process. Checks files, loads the model with
  `tf_keras` (Keras 3 cannot rebuild the Teachable Machine export), opens the camera, preprocesses
  (BGR->RGB, optional mirror, centre crop or squash, 224x224, `x/127.5-1`),
  predicts, smooths, sends messages. Heavy imports only here.
- `src/gesture/link.py`: `GestureLink` in the game process. `start`, `poll`,
  `status`, `detail`, `label`, `direction`, `connected`, `retry`, `stop`.
- `src/game/`: pure logic, no drawing. `paths.py`, `enemies.py`, `waves.py`, `world.py`.
- `src/game/render.py`, `src/ui/background.py`, new sprites: the `ui-new/` gameplay look.
- `src/main.py`: entry point, `python -m src.main`, import-light so the spawned
  worker never loads pygame. `src/app.py`: `App` host loop. `--dev-keyboard`
  (off by default) swaps in arrow keys and skips the camera, for development only.
- Font moves to `assets/fonts/`; all imports use the `src.` package style.

## Worker protocol

Messages on a `multiprocessing.Queue`, newest wins:

- `("status", name, detail)` where name is `loading_model`, `opening_camera`,
  `ready`, or `error` (detail is a short human message).
- `("label", label, confidence)` after smoothing, about `fps` times a second.

`ready` is sent after the first successful prediction. The game treats the link
as connected only while status is `ready` and a label arrived in the last 1.0 s.
Before loading TensorFlow the worker validates that both files exist and that
`labels.txt` maps to left, right and neutral; failures are `error` statuses.

## Gameplay

- Ship moves at 140 px/s (logical) and auto-fires every 0.32 s. A hit costs a
  life and gives 1.5 s of invulnerability (blinking hit sprite). 3 lives.
- Enemy kinds (sprites from `ui-new/09_sprite_sheet.png`): drone 1 HP 10 pts,
  bot 2 HP 25 pts, titan 5 HP 100 pts. Sprites show HP state and a hit flash.
- Paths (pure functions of time): straight, zigzag, circle, hover (enter, strafe
  while holding, then leave downward). Any enemy may also shoot (pink orbs,
  straight down).
- An enemy that leaves the bottom of the screen costs a life.
- Waves: a "WAVE n" banner (2 s), then timed spawn groups. Cleared when the
  schedule is finished and no enemies remain. Bonus 100 x wave number.
  Movement and spawn timing scale by +8% per wave; enemy bullets keep a
  constant speed (100 px/s) so late waves stay dodgeable. Clearing a wave
  mends one heart (up to 3).
  1. Drones, straight. 2. Drones zigzag, bots straight. 3. Drones circle, bots
  zigzag, hovering drone shooters. 4. Bots circle, hovering bot shooters, one
  titan. 5. Everything, two hovering titan shooters.
- Clearing wave 5 wins, plus 250 per remaining life.
- Balance is checked by an autopilot test that plays with 1, 12 and 20 frames
  of lag: the game must be winnable and laggy players must reach wave 5.

## Screens

- Start menu: as `ui-new/`, plus an "AI LINK" status line (loading, camera,
  online with the live L/R/N, or error with message and "R TO RETRY"). PLAY is
  dimmed and does nothing until connected.
- HUD: as `ui-new/`, plus a small "WAVE n/5" in the centre.
- Signal lost during play (worker error or no label for 1 s): automatic pause
  with a "SIGNAL LOST" panel; resumes when labels flow again.
- End: `GameOverScreen` with a "YOU BEAT THE AI" title on a win, "GAME OVER"
  on a loss. Initials entry when the score makes the top 10.

## Testing

- Unit: config parsing and errors, L/R/N mapping, label validation, link
  message handling (fake queue and process), preprocessing (numpy), paths,
  wave data, world rules (scoring, hits, bottom escapes, invulnerability,
  wave progression, win and loss).
- Integration: the real worker in a spawned process reports `error` for a
  missing model; the real model loads and predicts on a blank frame (skipped
  if TensorFlow or the model is absent).
- Visual: `tools/screenshot_ui.py` renders menus (each link status), gameplay
  per wave, signal lost, victory and game over.
- Manual: real webcam, "raise left hand, ship goes left".
