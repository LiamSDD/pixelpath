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
python3 -m pip install --upgrade pip
pip install -e ".[dev]"
python3 -m pytest -q
python3 bench.py
```

The `pip` upgrade matters on older interpreters: the pip that ships with
Python 3.9 (21.2) cannot do an editable install from `pyproject.toml`.
`bench.py` prints the best and median time for a 512x512 scene; quote both in
the pull request if you touch the rasterizer.

If you change rendering output, regenerate the showcase images:

```bash
for name in keylock badge ring; do
  python3 -m pixelpath examples/$name.svg -o docs/$name.png --scale 2
done
```

If rendering did not change, `git status` shows the images in `docs/` unmodified.

When reporting a rendering bug, please attach the smallest SVG that reproduces
it and describe the expected result.

## Proposing a change

1. For anything bigger than a small fix, open an issue first (bug report or
   feature request) so the approach can be agreed before you write code.
   Questions go to [Discussions](https://github.com/LiamSDD/pixelpath/discussions).
2. Issues labelled
   [`good first issue`](https://github.com/LiamSDD/pixelpath/labels/good%20first%20issue)
   are small, scoped and have acceptance criteria.
3. Fork the repository, create a branch from `main` (for example
   `feat/hsl-colours`) and keep each pull request to one change.
4. Fill in the pull request template, and add an entry under `Unreleased` in
   `CHANGELOG.md` for anything a user would notice.
5. Pull requests are squash-merged once the tests pass and the review is done.

## Commit messages

Write the subject as a short imperative sentence, capitalised and without a
trailing full stop, saying what changed: `Support <use> and <symbol>`,
`Add stroke-linecap, stroke-linejoin and stroke-miterlimit`. Use the body to
explain why. The squash merge appends the pull request number.

## Code of conduct and security

Everyone taking part is expected to follow the
[code of conduct](CODE_OF_CONDUCT.md). Report vulnerabilities privately as
described in [SECURITY.md](SECURITY.md), never in a public issue.
