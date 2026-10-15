# AGENTS.md

Guide for people and coding agents working on BEAT THE AI.

## What this project is

BEAT THE AI is a retro arcade shooter in the Space Invaders style, written in pygame. The player steers the ship left and right with hand gestures, not a keyboard. Gestures are recognised by an image model trained in Google Teachable Machine.

The game is built for a classroom relay. Each student plays using the gestures the previous student trained, then trains a new set of gestures for the next student. The first set is trained by the team.

Fire is automatic. Gestures only control left, right and idle.

## Commands

```bash
pip install -r requirements.txt            # pygame-ce + pytest
python src/ui_demo.py                      # playable UI sandbox (keyboard)
python -m pytest -q                        # leaderboard, input and UI logic tests
python tools/screenshot_ui.py              # renders every screen to docs/ui/*.png

pip install -r requirements-gesture.txt    # only when working on webcam control
```

`ui_demo.py` uses a stub game (falling UFOs). Keys: arrows or A/D to move, P or Esc to pause, F1 to lose a life, Enter or Space to select.

## Repo layout

```
assets/fonts/PressStart2P-Regular.ttf   OFL licensed, see OFL.txt
src/theme.py            design tokens (palette, logical size, fonts)
src/ui/                 sprites, drawing helpers, widgets, HUD, screens
src/leaderboard.py      top-10 scores in data/leaderboard.json (no pygame import)
src/input_source.py     direction() sources, label parsing, smoothing
src/ui_demo.py          UI sandbox with a placeholder game
tools/screenshot_ui.py  headless screenshots for design review
tests/                  pytest
models/<profile>/       Teachable Machine exports (git-ignored)
```

## How pygame and Teachable Machine work together

They never share a process boundary you have to think about. Teachable Machine is where a model gets trained, in the browser. pygame is where the game runs. The only things that cross between them are a model file and a label name.

```
Teachable Machine (browser)           Python process
  webcam samples -> train -> export     keras_model.h5 + labels.txt
                                          |
                          webcam -> OpenCV frame -> 224x224 -> model.predict
                                          |
                          label + confidence -> Smoother -> SharedDirection
                                          |
                          game loop: ship.x += direction() * speed * dt
```

### 1. The class contract

Every model must contain these three classes. Names are matched case-insensitively (`src/input_source.py`, `LABEL_TO_DIR`).

| Class name | Ship does |
| --- | --- |
| Left | moves left |
| Right | moves right |
| Idle | stands still |

Students pick which hand gesture means which class. The game never needs to know the gesture, only the class name. Any other class name is treated as Idle.

The Idle class matters. A classifier always picks some class, so without a class for "hand relaxed" or "no hand in frame" the ship will always be moving.

### 2. Training in Teachable Machine

1. Open Teachable Machine and start an Image Project (standard image model).
2. Create the three classes above and record webcam samples for each.
3. Vary distance, lighting, background and which hand is used. Include samples with no hand in the frame under Idle.
4. Train, then use the in-page preview to check each gesture before exporting.

Teachable Machine prepares images at 224x224 and the exported model expects that input size.

### 3. Exporting

Use Export Model, then the TensorFlow tab, then the Keras option, and download. You get `keras_model.h5` and `labels.txt`. Put both in `models/<profile>/`.

`labels.txt` has one line per class in the form `0 Left`. Use `parse_labels()` rather than splitting by hand.

### 4. Running the model in Python

Preprocessing must match what Teachable Machine does or accuracy drops:

- Convert the frame to RGB (OpenCV returns BGR).
- Make it square and resize to 224x224. The official Python snippet using PIL centre-crops with `ImageOps.fit`, and the official OpenCV snippet squashes the whole frame with `cv2.resize`. Centre-cropping is used below, so the player must stand in the middle of the camera view. Test both on a real model before settling.
- Scale pixels with `(x / 127.5) - 1`.
- Load with `load_model("keras_model.h5", compile=False)` and call `predict` on an array shaped `(1, 224, 224, 3)`.

Reference sketch for `src/gesture_worker.py`. It was written from the official snippets and has not been run against a real model or webcam in this repo yet, so treat it as a starting point.

```python
import threading, time
import cv2
import numpy as np
from keras.models import load_model

from input_source import Smoother, parse_labels


class GestureWorker(threading.Thread):
    def __init__(self, model_dir, shared, camera=0, mirror=True, fps=15):
        super().__init__(daemon=True)
        self.model = load_model(f"{model_dir}/keras_model.h5", compile=False)
        with open(f"{model_dir}/labels.txt", encoding="utf-8") as f:
            self.labels = parse_labels(f.read())
        self.shared, self.camera, self.mirror = shared, camera, mirror
        self.period = 1.0 / fps
        self.stop_event = threading.Event()
        self.last_frame = None  # RGB frame for a calibration preview

    def run(self):
        cap = cv2.VideoCapture(self.camera)
        smoother = Smoother(window=5, min_conf=0.8)
        while not self.stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            if self.mirror:
                frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.last_frame = rgb
            h, w = rgb.shape[:2]
            s = min(h, w)
            y0, x0 = (h - s) // 2, (w - s) // 2
            sq = cv2.resize(rgb[y0:y0 + s, x0:x0 + s], (224, 224), interpolation=cv2.INTER_AREA)
            x = (sq.astype(np.float32) / 127.5) - 1
            probs = self.model.predict(x[None], verbose=0)[0]
            i = int(np.argmax(probs))
            self.shared.set_label(smoother.push(self.labels[i], float(probs[i])))
            time.sleep(self.period)
        cap.release()
```

Usage in the game:

```python
shared = SharedDirection()
GestureWorker("models/team", shared).start()
# game loop
ship.x += shared.direction() * SPEED * dt
```

Rules that keep the game responsive:

- Never call `predict` inside the pygame loop. It is slow enough to drop frames. The worker thread writes, the game thread reads.
- The game reads `direction()` only. That keeps the keyboard and gesture sources swappable, and the keyboard stays as a fallback when no camera works.
- Smooth predictions with `Smoother`. Raw per-frame output flickers and makes the ship jitter. The defaults are a 5 frame window and a minimum confidence of 0.8; tune them with real students.

### 5. Known problems

Mirroring. Players expect a mirror image. Teachable Machine's preview and your OpenCV frame may differ in orientation, and a model trained on one orientation steers backwards on the other. Keep the `mirror` flag, and check "raise left hand, ship goes left" before every session.

Keras 3 loading. Teachable Machine's `.h5` files contain a legacy `DepthwiseConv2D` setting that Keras 3 rejects. Keras 3 is the default since TensorFlow 2.16. The `teachable-machine` package, from version 1.3.0, patches the loader. Alternatively pin an older TensorFlow. Check which one the machine has before debugging anything else.

Pose models. Teachable Machine has a pose project type, but this game uses image models, the type the Keras export above covers. Do not switch project types without checking that export path.

Browser alternative. If installing TensorFlow in a school lab is a problem, the model can run in a browser page instead. Teachable Machine can host a model at a shareable URL, and the `@teachablemachine/image` library loads `model.json` and `metadata.json` from it. A small local page can then send the predicted class to the game over a websocket or HTTP. `SharedDirection.set_label()` is already the right entry point. This path is not built.

## The student relay

```
Round 1:  team model        -> Student A plays, then trains model A
Round 2:  model A           -> Student B plays, then trains model B
Round 3:  model B           -> Student C plays ...
```

Each profile is a folder under `models/`, for example `models/team`, `models/student-a`. The game loads the profile of the previous student. Keep old profiles so a round can be replayed.

Before each round, check that the folder holds both files and that `labels.txt` contains Left, Right and Idle. A student who forgot the Idle class should find out before their game starts, not during it.

Not built yet: a calibration screen that shows the camera feed and the predicted class so the new player can confirm the gestures work, and a profile picker.

Privacy: do not write webcam frames to disk and do not commit anything from `models/`. Check the school's rules on student images before running this with a class.

## UI system

All UI draws on a 320x360 logical surface. The host scales it up by an integer (`SCALE = 2`) with nearest-neighbour scaling, so pixel art and Press Start 2P stay sharp. Window mouse positions are converted with `theme.to_logical`.

Rules:

- Take colours, sizes and strings from `src/theme.py`. Do not hard-code them in screens.
- Font sizes are multiples of 8. Text is drawn without anti-aliasing.
- Text comes from `ui/draw.py`: `draw_text` for gradient headings with an extrusion and ink outline, `draw_small` for flat 8px labels.
- `text_surface()` is cached and returns shared surfaces. Never modify one.
- Sprites are ASCII bitmaps in `ui/sprites.py`, so they are easy to edit and diff. `get(name, scale)` is cached too.
- The look follows the ChatGPT sticker set: ink outlines, neon magenta and cyan frames, yellow to orange gradients, small yellow sparkles.

Every full screen has the same interface and returns an action string. The host decides what the action does.

| Screen | Actions | Notes |
| --- | --- | --- |
| `StartMenu` | `play`, `scores` | Title strings and tagline come from `theme.GAME_TITLE` and `theme.TAGLINE` |
| `LeaderboardScreen(lb, highlight=None)` | `back` | Top 10, `highlight` blinks a new entry |
| `PauseOverlay` | none | Says GAME PAUSED and nothing else. The host toggles pause with its own key. `theme.SHOW_RESUME_HINT` is False by design |
| `GameOverScreen(score, lb)` | `restart`, `menu` | Asks for 3 initials first if the score makes the top 10 |

HUD:

```python
hud = Hud()                    # three hearts by default
hud.update(dt, score, lives)   # every frame; a drop in lives flashes the broken heart
hud.draw(surface)
hud.reset()                    # on restart
```

With one life left the last heart pulses. The HUD is 28px tall (`HUD_H`); keep gameplay below it.

Leaderboard:

```python
lb = Leaderboard()             # data/leaderboard.json
lb.qualifies(score)            # score > 0 and in the top 10
rank = lb.add("AB", score)     # 0-based rank, or None
```

Ties rank below the older entry, names are uppercased to 3 characters, and saves are atomic. The leaderboard is per machine. For a shared classroom board, put the file on a shared path or add a small server later.

To add a screen: create a class with `handle_event`, `update` and `draw`, return action strings, and add it to `tools/screenshot_ui.py` so it gets a screenshot.

## Testing

`python -m pytest -q` covers the leaderboard, label parsing, smoothing, sprite sizes, the HUD flash and the initials flow. Visual changes should be checked with `python tools/screenshot_ui.py` and the PNGs in `docs/ui/`.

## Not done yet

- Real gameplay (the demo uses a stub).
- `gesture_worker.py` is a sketch and has not been tested against a real model.
- Calibration screen and profile picker for the student relay.
- Sound.
