# Contributing

Thanks for your interest in pixelpath. Bug reports, SVG files that render
incorrectly and focused pull requests are all welcome.

## Ground rules

- **Standard library only.** Runtime code must not import anything outside the
  Python standard library. `pytest` is the only development dependency.
- **Python 3.9+.** Avoid syntax or library features newer than 3.9.
- **House style.** No comments and no docstrings in `.py` files; express intent
  through clear names and small functions. Type hints are welcome.
- **Tests first.** Add a failing test that demonstrates the bug or feature, then
  make it pass. Rendering changes should assert concrete pixel values.
- **Safety.** Do not weaken the refusal of `<!DOCTYPE` and `<!ENTITY` declarations.

## Workflow

```bash
git clone https://github.com/LiamSDD/pixelpath
cd pixelpath
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python3 -m pytest -q
python3 bench.py
```

If you change rendering output, regenerate the showcase images:

```bash
for name in keylock badge ring; do
  python3 -m pixelpath examples/$name.svg -o docs/$name.png --scale 2
done
```

When reporting a rendering bug, please attach the smallest SVG that reproduces
it and describe the expected result.
