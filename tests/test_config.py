import os

import pytest

from src.config import ROOT, Config, ConfigError, load


def write(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text)
    return str(p)


def test_missing_file_gives_defaults(tmp_path):
    cfg = load(str(tmp_path / "nope.toml"))
    assert cfg == Config()
    assert cfg.model_dir == os.path.join(ROOT, "models", "keras-model")


def test_repo_config_loads():
    cfg = load()
    assert cfg.model_dir == os.path.join(ROOT, "models", "keras-model")
    assert cfg.mirror is True


def test_values_override_defaults(tmp_path):
    cfg = load(write(tmp_path, """
[model]
dir = "models/other"
min_confidence = 0.6
smoothing_window = 3
crop = "squash"

[camera]
index = 1
mirror = false
fps = 10
"""))
    assert cfg.model_dir == os.path.join(str(tmp_path), "models", "other")  # relative to the file
    assert (cfg.min_confidence, cfg.smoothing_window, cfg.crop) == (0.6, 3, "squash")
    assert (cfg.camera, cfg.mirror, cfg.fps) == (1, False, 10)


def test_absolute_model_dir_is_kept(tmp_path):
    cfg = load(write(tmp_path, f'[model]\ndir = "{tmp_path}"\n'))
    assert cfg.model_dir == str(tmp_path)


@pytest.mark.parametrize("text, words", [
    ("[model]\nmin_confidence = 1.5\n", "min_confidence"),
    ("[model]\nsmoothing_window = 0\n", "smoothing_window"),
    ("[model]\ncrop = \"zoom\"\n", "crop"),
    ("[camera]\nfps = \"fast\"\n", "fps"),
    ("[camera]\nmirror = 1\n", "mirror"),
    ("[model]\ndir = \"\"\n", "dir"),
    ("[model]\nnot_a_key = 1\n", "not_a_key"),
    ("[model\n", "config.toml"),
])
def test_bad_values_raise_clear_errors(tmp_path, text, words):
    with pytest.raises(ConfigError, match=words):
        load(write(tmp_path, text))
