"""Where the player's left/right comes from.

The game only ever asks for `direction()` -> -1, 0 or +1. Today that is the
keyboard; the Teachable Machine worker (see AGENTS.md) feeds a SharedDirection
from its own thread, so the game loop never blocks on the webcam or the model.
"""
from __future__ import annotations

import threading
from collections import Counter, deque

# Class names students give their gestures in Teachable Machine. Matching is
# case-insensitive, so "Left", "LEFT" and "left" all work. Anything else = idle.
LABEL_TO_DIR = {"left": -1, "right": 1, "idle": 0, "neutral": 0, "none": 0}


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
