"""BEAT THE AI: the game. Run from the repo root:

    python -m src.main                  # gesture control (config.toml)
    python -m src.main --dev-keyboard   # arrow keys, no camera (development only)

The ship is steered only by the Teachable Machine model (L / R / N). Menus,
pause (P or Esc) and initials use the keyboard or mouse, for the operator.
PLAY unlocks once the gesture link is connected. If the link drops mid-game the
game pauses itself and resumes when predictions flow again.

Keep this module import-light: the gesture worker is started with the spawn
method, which re-imports __main__ in the child. Importing pygame here would load
pygame's SDL2 next to OpenCV's bundled copy in the worker. The game lives in
src/app.py.
"""
import sys


def main(argv=None):
    from src.app import run
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
