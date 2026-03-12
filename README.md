# kbd-pulse

Reactive keyboard backlight daemon for System76 laptops.

## Quality Gates

CI runs on every pull request and on pushes to `main`/feature branches:

- `ruff check .`
- `mypy`
- `coverage run -m unittest discover -s tests -v`
- `coverage report` with minimum `85%`
- `python -m compileall -q kbd_pulse tests`

## Local Check Command

```bash
SETUPTOOLS_USE_DISTUTILS=local uv sync --all-groups
uv run ruff check .
uv run mypy
uv run coverage run -m unittest discover -s tests -v
uv run coverage report
uv run python -m compileall -q kbd_pulse tests
```
