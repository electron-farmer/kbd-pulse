# kbd-pulse

Reactive keyboard backlight daemon for System76 laptops.

## Background Service

1. Install permissions (recommended, one-time):

```bash
cd ~/git/kbd-pulse
./scripts/install-permissions.sh
```

2. Install as a user service:

```bash
./scripts/install-user-service.sh
```

Manage it:

```bash
systemctl --user status kbd-pulse.service
systemctl --user restart kbd-pulse.service
systemctl --user stop kbd-pulse.service
journalctl --user -u kbd-pulse.service -f
```

If you skip permission setup, run temporarily as root:

```bash
sudo /home/$USER/.local/bin/uv run kbd-pulse
```

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
