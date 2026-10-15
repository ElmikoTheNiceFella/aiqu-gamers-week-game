"""Where the player's left/right comes from.

The game only ever asks for `direction()` -> -1, 0 or +1. Today that is the
keyboard; the Teachable Machine worker (see AGENTS.md) feeds a SharedDirection
from its own thread, so the game loop never blocks on the webcam or the model.
"""
from __future__ import annotations

import threading
from collections import Counter, deque

# Class names students give their gestures in Teachable Machine. Matching is
# case-insensitive, so "L", "Left" and "LEFT" all work. Anything else = neutral.
# The team model uses the single letters L, R and N.
LABEL_TO_DIR = {"l": -1, "left": -1, "r": 1, "right": 1,
                "n": 0, "neutral": 0, "idle": 0, "none": 0}


def parse_labels(text: str) -> list[str]:
    """Parse a Teachable Machine labels.txt ("0 Left" per line) into ["left", ...]."""
    labels = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        head, _, rest = line.partition(" ")
        labels.append((rest if head.isdigit() and rest else line).strip().lower())
    return labels


def label_to_direction(label: str) -> int:
    return LABEL_TO_DIR.get(label.strip().lower(), 0)


def direction_letter(direction: int) -> str:
    """-1/0/+1 -> "L"/"N"/"R", for showing what the model sees."""
    return {-1: "L", 1: "R"}.get(direction, "N")


def check_labels(labels: list[str]) -> str | None:
    """Return a problem description if the model can't steer the ship, else None.

    A model needs a left class, a right class and an explicit neutral class:
    a classifier always picks something, so without neutral the ship never stops.
    """
    known = {lab: LABEL_TO_DIR[lab] for lab in labels if lab in LABEL_TO_DIR}
    missing = [name for name, d in (("L", -1), ("R", 1), ("N", 0)) if d not in known.values()]
    if missing:
        found = ", ".join(lab.upper() for lab in labels) or "none"
        return f"labels.txt needs classes L, R and N. Missing {', '.join(missing)} (found {found})"
    return None


class Smoother:
    """Majority vote over the last N predictions, ignoring low-confidence ones.

    Raw per-frame predictions flicker; steering with them makes the ship jitter.
    """

    def __init__(self, window: int = 5, min_conf: float = 0.8):
        self.min_conf = min_conf
        self.recent: deque[str] = deque(maxlen=window)

    def push(self, label: str, confidence: float) -> str:
        self.recent.append(label.lower() if confidence >= self.min_conf else "idle")
        return Counter(self.recent).most_common(1)[0][0]


class SharedDirection:
    """Thread-safe latest direction, written by the gesture thread, read by the game."""

    def __init__(self):
        self._lock = threading.Lock()
        self._dir = 0

    def set_label(self, label: str):
        with self._lock:
            self._dir = label_to_direction(label)

    def direction(self) -> int:
        with self._lock:
            return self._dir


class KeyboardDirection:
    """Arrow keys or A/D. Used for development and as the fallback if no camera works."""

    def direction(self) -> int:
        import pygame
        k = pygame.key.get_pressed()
        return int(k[pygame.K_RIGHT] or k[pygame.K_d]) - int(k[pygame.K_LEFT] or k[pygame.K_a])
