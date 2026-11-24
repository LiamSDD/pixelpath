import os
import subprocess
import sys
from pathlib import Path

import pytest

import pixelpath
from pixelpath.cli import main
from pixelpath.png import decode_png

SOURCE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><rect x="5" width="10" height="10" fill="red"/></svg>'
SRC_DIRECTORY = Path(__file__).resolve().parent.parent / "src"


@pytest.fixture
def input_file(tmp_path):
    path = tmp_path / "input.svg"
    path.write_text(SOURCE, encoding="utf-8")
    return path


def read_png(path):
    return decode_png(Path(path).read_bytes())


def pixel(pixels, width, x, y):
    offset = (y * width + x) * 4
    return tuple(pixels[offset : offset + 4])


def test_renders_to_output_file(input_file, tmp_path):
    output = tmp_path / "out.png"
    assert main([str(input_file), "-o", str(output)]) == 0
    width, height, pixels = read_png(output)
    assert (width, height) == (20, 10)
    assert pixel(pixels, width, 10, 5) == (255, 0, 0, 255)
    assert pixel(pixels, width, 1, 5) == (0, 0, 0, 0)


def test_default_output_replaces_suffix(input_file):
    assert main([str(input_file)]) == 0
    assert input_file.with_suffix(".png").exists()


def test_width_option(input_file, tmp_path):
    output = tmp_path / "wide.png"
    assert main([str(input_file), "-o", str(output), "--width", "80"]) == 0
    assert read_png(output)[:2] == (80, 40)


def test_height_option(input_file, tmp_path):
    output = tmp_path / "tall.png"
    assert main([str(input_file), "-o", str(output), "--height", "30"]) == 0
    assert read_png(output)[:2] == (60, 30)


def test_scale_option(input_file, tmp_path):
    output = tmp_path / "scaled.png"
    assert main([str(input_file), "-o", str(output), "--scale", "1.5"]) == 0
    assert read_png(output)[:2] == (30, 15)


def test_background_option(input_file, tmp_path):
    output = tmp_path / "background.png"
    assert main([str(input_file), "-o", str(output), "--background", "#00ff00"]) == 0
    width, _, pixels = read_png(output)
    assert pixel(pixels, width, 1, 1) == (0, 255, 0, 255)


def test_size_options_are_mutually_exclusive(input_file, tmp_path, capsys):
    with pytest.raises(SystemExit) as raised:
        main([str(input_file), "-o", str(tmp_path / "x.png"), "--width", "10", "--scale", "2"])
    assert raised.value.code == 2


def test_missing_input_reports_error(tmp_path, capsys):
    assert main([str(tmp_path / "missing.svg"), "-o", str(tmp_path / "x.png")]) == 1
    assert "missing.svg" in capsys.readouterr().err


def test_unsafe_input_reports_error(tmp_path, capsys):
    evil = tmp_path / "evil.svg"
    evil.write_text('<!DOCTYPE svg [<!ENTITY a "b">]><svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    assert main([str(evil), "-o", str(tmp_path / "x.png")]) == 1
    assert "DOCTYPE" in capsys.readouterr().err
    assert not (tmp_path / "x.png").exists()


def test_invalid_background_reports_error(input_file, tmp_path, capsys):
    assert main([str(input_file), "-o", str(tmp_path / "x.png"), "--background", "nope"]) == 1
    assert "nope" in capsys.readouterr().err


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as raised:
        main(["--version"])
    assert raised.value.code == 0
    assert pixelpath.__version__ in capsys.readouterr().out


def test_module_entry_point_end_to_end(input_file, tmp_path):
    output = tmp_path / "module.png"
    environment = dict(os.environ, PYTHONPATH=str(SRC_DIRECTORY))
    completed = subprocess.run(
        [sys.executable, "-m", "pixelpath", str(input_file), "-o", str(output), "--scale", "2"],
        capture_output=True,
        text=True,
        env=environment,
        cwd=str(tmp_path),
    )
    assert completed.returncode == 0, completed.stderr
    assert read_png(output)[:2] == (40, 20)
