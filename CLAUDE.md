# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

AGENTS.md (imported above) is the main guide: commands, architecture, the gesture worker, game rules, UI rules and testing. Notes below are extra context for working in this repo.

## Environment

- Use the local venv: `.venv/bin/python -m pytest -q`, `.venv/bin/python -m src.main`. It already has pygame-ce, pytest, tensorflow 2.21, tf-keras 2.21, opencv-python-headless and pyflakes.
- Lint with `.venv/bin/python -m pyflakes src tools tests`. There is no formatter config; match the surrounding style (`# noqa: E402` on imports that follow `sys.path` or env setup).
- The shell here may not have macOS camera permission, so the real worker reports `camera 0 won't open` when run from it. Gesture control can only be verified by the user running the game. Use `--dev-keyboard` or `tools/screenshot_ui.StaticLink` to exercise the game without a camera.
- `multiprocessing` spawn can't re-import a script fed through stdin. Put ad-hoc scripts that start a `GestureLink` in a file, behind `if __name__ == "__main__":`.

## Design decisions

- The spec in README.md says "the Teachable Machine link should be configurable". This means the local export folder (`[model] dir` in `config.toml`), not a hosted URL. That was the user's choice.
- "No keyboard" applies to steering the ship only. Menus, pause and initials stay on keyboard and mouse, also the user's choice.
- The design record is `docs/superpowers/specs/2026-10-15-gesture-game-design.md`.
