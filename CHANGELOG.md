# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [0.2.0] - 2026-03-12

### Added
- Implemented core backlight control module for System76 sysfs keyboard LEDs.
- Added keyboard input watcher module with device discovery and reconnect handling.
- Added hardware self-test and zone diagnostics commands, including slow scripted diagnostics.
- Added detailed unit tests for backlight, input watcher, diagnostics, and CLI behavior.
- Added GitHub Actions CI workflow with linting, type checking, tests, coverage, and compile checks.

### Changed
- Expanded CLI surface with `status`, `set`, `watch-input`, `self-test`, and `zone-diagnose`.
- Defaulted diagnostics and sweep behavior to global mode for more reliable hardware rendering.
- Added project-level quality tooling configuration (`ruff`, `mypy`, `coverage`) and local quality docs.
