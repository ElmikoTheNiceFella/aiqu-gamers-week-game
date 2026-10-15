"""Gesture worker: webcam -> Teachable Machine model -> L/R/N, in its own process.

Started by GestureLink with the spawn start method. It never touches pygame.
Messages it sends (tuples on `out`):

    ("status", "loading_model" | "opening_camera" | "ready" | "error", detail)
    ("label", smoothed_label, confidence)

Preprocessing matches Teachable Machine: RGB, square, 224x224, x / 127.5 - 1.
Webcam frames are never written to disk.
"""
from __future__ import annotations

import os
import time

from src.config import ROOT
from src.input_source import Smoother, check_labels, parse_labels

SIZE = 224
NO_FRAME_TIMEOUT = 3.0  # seconds of failed reads before the camera counts as lost


class WorkerError(Exception):
    """A problem a teacher can fix; the message is shown on the start menu."""


def _short(path: str) -> str:
    """Repo-relative path for messages that must fit on the start menu."""
    rel = os.path.relpath(path, ROOT)
    return path if rel.startswith("..") else rel


def read_labels(model_dir: str) -> list[str]:
    model = os.path.join(model_dir, "keras_model.h5")
    labels_path = os.path.join(model_dir, "labels.txt")
    for path in (model, labels_path):
        if not os.path.isfile(path):
            raise WorkerError(f"{os.path.basename(path)} not found in {_short(model_dir)}")
    with open(labels_path, encoding="utf-8") as f:
        labels = parse_labels(f.read())
    problem = check_labels(labels)
    if problem:
        raise WorkerError(problem)
    return labels


def load_model(path: str):
    """Load a Teachable Machine .h5 export.

    Keras 3 (the default since TensorFlow 2.16) cannot rebuild the nested legacy
    Sequential model Teachable Machine saves, so use the Keras 2 package tf-keras.
    """
    try:
        import tf_keras
    except ImportError:
        raise WorkerError("tf-keras is not installed: pip install -r requirements-gesture.txt")
    return tf_keras.models.load_model(path, compile=False)


def preprocess(frame_bgr, mirror: bool, crop: str):
    """OpenCV BGR frame -> float32 array shaped (1, 224, 224, 3) in [-1, 1]."""
    import cv2
    import numpy as np

    if mirror:
        frame_bgr = cv2.flip(frame_bgr, 1)
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    if crop == "center":
        h, w = rgb.shape[:2]
        s = min(h, w)
        y0, x0 = (h - s) // 2, (w - s) // 2
        rgb = rgb[y0:y0 + s, x0:x0 + s]
    sq = cv2.resize(rgb, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    return ((sq.astype(np.float32) / 127.5) - 1.0)[None]


def run(cfg, out, stop):
    """Process entry point. Reports every failure as an "error" status, then exits."""
    def send(*msg):
        out.put(msg)

    cap = None
    try:
        send("status", "loading_model", "checking files")
        labels = read_labels(cfg.model_dir)
        send("status", "loading_model", "starting tensorflow")
        model = load_model(os.path.join(cfg.model_dir, "keras_model.h5"))

        send("status", "opening_camera", f"camera {cfg.camera}")
        try:
            import cv2
            import numpy as np
        except ImportError:
            raise WorkerError("OpenCV is not installed: pip install -r requirements-gesture.txt")
        cap = cv2.VideoCapture(cfg.camera)
        if not cap.isOpened():
            raise WorkerError(f"camera {cfg.camera} won't open: allow camera access "
                              "for your terminal app")

        smoother = Smoother(window=cfg.smoothing_window, min_conf=cfg.min_confidence)
        period = 1.0 / cfg.fps
        last_frame = time.monotonic()
        ready = False
        while not stop.is_set():
            t0 = time.monotonic()
            ok, frame = cap.read()
            if not ok:
                if t0 - last_frame > NO_FRAME_TIMEOUT:
                    raise WorkerError(f"camera {cfg.camera} stopped sending frames")
                time.sleep(0.05)
                continue
            last_frame = t0
            probs = np.asarray(model(preprocess(frame, cfg.mirror, cfg.crop), training=False))[0]
            i = int(np.argmax(probs))
            label = smoother.push(labels[i], float(probs[i]))
            if not ready:
                send("status", "ready", "")
                ready = True
            send("label", label, float(probs[i]))
            time.sleep(max(0.0, period - (time.monotonic() - t0)))
    except WorkerError as e:
        send("status", "error", str(e))
    except Exception as e:  # anything else still has to reach the menu, not a log
        send("status", "error", f"{type(e).__name__}: {e}")
    finally:
        if cap is not None:
            cap.release()
