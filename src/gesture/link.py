"""Game-side handle on the gesture worker process.

    link = GestureLink(config.load())
    link.start()
    # every frame
    link.poll()
    if link.connected:
        ship.x += link.direction() * SPEED * dt

The worker (src/gesture/worker.py) runs in its own spawned process, so loading
TensorFlow and running the model never stalls the pygame loop. It sends tuples
on a queue: ("status", name, detail) and ("label", label, confidence).
This module imports neither TensorFlow nor OpenCV.
"""
from __future__ import annotations

import multiprocessing
import queue
import time

from src.input_source import direction_letter, label_to_direction

from . import worker

# What the start menu shows for each status (detail comes from the worker).
STATUS_TEXT = {
    "starting": "STARTING",
    "loading_model": "LOADING MODEL",
    "opening_camera": "OPENING CAMERA",
    "ready": "ONLINE",
    "error": "ERROR",
    "stopped": "OFFLINE",
}


class GestureLink:
    STALE_AFTER = 1.0  # seconds without a label before the link counts as lost

    def __init__(self, cfg, ctx=None, clock=time.monotonic):
        self.cfg = cfg
        self.ctx = ctx or multiprocessing.get_context("spawn")
        self.clock = clock
        self.status = "stopped"
        self.detail = ""
        self.label = "n"
        self.confidence = 0.0
        self._last_label_t = None
        self._proc = None
        self._queue = None
        self._stop = None

    # ---- lifecycle
    def start(self):
        self._queue = self.ctx.Queue()
        self._stop = self.ctx.Event()
        self._proc = self.ctx.Process(target=worker.run, args=(self.cfg, self._queue, self._stop),
                                      daemon=True)
        self._proc.start()
        self.status, self.detail = "starting", ""
        self.label, self._last_label_t = "n", None

    def stop(self):
        if self._proc is None:
            return
        self._stop.set()
        self._proc.join(timeout=1.0)
        if self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(timeout=1.0)
        self._proc = None
        self.status, self.detail = "stopped", ""

    def retry(self):
        self.stop()
        self.start()

    # ---- per frame
    def poll(self):
        if self._queue is None:
            return
        while True:
            try:
                msg = self._queue.get_nowait()
            except (queue.Empty, OSError, ValueError):
                break
            if msg[0] == "status":
                _, self.status, self.detail = msg
            elif msg[0] == "label":
                _, self.label, self.confidence = msg
                self._last_label_t = self.clock()
        alive = self._proc is not None and self._proc.is_alive()
        if self._proc is not None and not alive and self.status != "error":
            self.status = "error"
            self.detail = f"gesture worker stopped (exit code {self._proc.exitcode})"

    # ---- reading
    @property
    def connected(self) -> bool:
        return (self.status == "ready" and self._last_label_t is not None
                and self.clock() - self._last_label_t <= self.STALE_AFTER)

    def direction(self) -> int:
        return label_to_direction(self.label) if self.connected else 0

    @property
    def letter(self) -> str:
        return direction_letter(self.direction())

    @property
    def status_text(self) -> str:
        if self.status == "ready" and not self.connected:
            return "NO SIGNAL"
        return STATUS_TEXT.get(self.status, self.status.upper())


class KeyboardLink:
    """Development stand-in for GestureLink (python -m src.main --dev-keyboard).

    Arrow keys or A/D steer; it is always connected. Never the default: the
    game is meant to be played with gestures only.
    """

    status = "ready"
    status_text = "KEYBOARD (DEV)"
    detail = ""
    connected = True

    def __init__(self):
        from src.input_source import KeyboardDirection
        self._keys = KeyboardDirection()

    def start(self):
        pass

    def stop(self):
        pass

    def retry(self):
        pass

    def poll(self):
        pass

    def direction(self) -> int:
        return self._keys.direction()

    @property
    def letter(self) -> str:
        return direction_letter(self.direction())
