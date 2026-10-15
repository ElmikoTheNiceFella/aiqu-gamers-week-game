"""Local top-10 leaderboard stored as JSON.

Pure Python (no pygame), so it is easy to unit test. Writes are atomic, so a
crash mid-save cannot corrupt the file.
"""
from __future__ import annotations

import json
import os
import re
import tempfile

DEFAULT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "leaderboard.json")
)
MAX_ENTRIES = 10
NAME_LEN = 3


def clean_name(name: str) -> str:
    name = re.sub(r"[^A-Z0-9]", "", (name or "").upper())[:NAME_LEN]
    return name.ljust(NAME_LEN, "-") if name else "AAA"


class Leaderboard:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        self.entries: list[tuple[str, int]] = []
        self.load()

    # ---- queries
    @property
    def best(self) -> int:
        return self.entries[0][1] if self.entries else 0

    def qualifies(self, score: int) -> bool:
        if score <= 0:
            return False
        return len(self.entries) < MAX_ENTRIES or score > self.entries[-1][1]

    # ---- mutation
    def add(self, name: str, score: int):
        """Insert a score. Returns the 0-based rank it landed on, or None if it missed."""
        if not self.qualifies(score):
            return None
        rank = len(self.entries)
        for i, (_, s) in enumerate(self.entries):
            if score > s:  # ties go below the older entry
                rank = i
                break
        self.entries.insert(rank, (clean_name(name), int(score)))
        del self.entries[MAX_ENTRIES:]
        self.save()
        return rank

    # ---- persistence
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            rows = [(clean_name(r["name"]), int(r["score"])) for r in raw]
        except (OSError, ValueError, KeyError, TypeError):
            rows = []
        rows.sort(key=lambda r: -r[1])  # stable: keeps file order for ties
        self.entries = rows[:MAX_ENTRIES]

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path) or ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump([{"name": n, "score": s} for n, s in self.entries], f, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
