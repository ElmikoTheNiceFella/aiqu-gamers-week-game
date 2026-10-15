"""Settings from config.toml at the repo root (stdlib tomllib, no pygame).

    cfg = load()           # missing file -> defaults
    cfg.model_dir          # absolute path to the Teachable Machine export

Bad values raise ConfigError with a message that names the key, so a teacher
editing the file sees what to fix instead of a traceback from deep inside.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PATH = os.path.join(ROOT, "config.toml")
CROPS = ("center", "squash")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    model_dir: str = os.path.join(ROOT, "models", "keras-model")
    min_confidence: float = 0.8
    smoothing_window: int = 5
    crop: str = "center"
    camera: int = 0
    mirror: bool = True
    fps: int = 15


# section -> {toml key: (Config field, type check, rule, rule text)}
_SCHEMA = {
    "model": {
        "dir": ("model_dir", str, lambda v: v.strip() != "", "a folder path"),
        "min_confidence": ("min_confidence", (int, float), lambda v: 0 <= v <= 1,
                           "a number from 0 to 1"),
        "smoothing_window": ("smoothing_window", int, lambda v: 1 <= v <= 30,
                             "a whole number from 1 to 30"),
        "crop": ("crop", str, lambda v: v in CROPS, "\"center\" or \"squash\""),
    },
    "camera": {
        "index": ("camera", int, lambda v: v >= 0, "a whole number, 0 or more"),
        "mirror": ("mirror", bool, lambda v: True, "true or false"),
        "fps": ("fps", int, lambda v: 1 <= v <= 60, "a whole number from 1 to 60"),
    },
}


def load(path: str = DEFAULT_PATH) -> Config:
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        return Config()
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"config.toml is not valid TOML: {e}") from None

    values = {}
    for section, body in raw.items():
        keys = _SCHEMA.get(section)
        if keys is None or not isinstance(body, dict):
            raise ConfigError(f"config.toml: unknown section [{section}]")
        for key, value in body.items():
            if key not in keys:
                raise ConfigError(f"config.toml: unknown key {key} in [{section}]")
            field, kind, rule, want = keys[key]
            # bool is a subclass of int; never accept it where a number is expected
            ok_type = isinstance(value, kind) and (kind is bool or not isinstance(value, bool))
            if not ok_type or not rule(value):
                raise ConfigError(f"config.toml: [{section}] {key} must be {want}, got {value!r}")
            values[field] = value

    if "model_dir" in values:
        values["model_dir"] = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(path)), values["model_dir"]))
    if "min_confidence" in values:
        values["min_confidence"] = float(values["min_confidence"])
    return Config(**values)
