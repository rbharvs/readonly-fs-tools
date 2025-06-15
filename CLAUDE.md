# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This project uses `uv` for dependency management and task running.

### Setup
```bash
uv sync --dev
```

### Code Quality
```bash
uv run ruff check          # Lint code
uv run ruff format         # Format code
uv run ruff format --check # Check formatting without changing files
uv run mypy --strict .     # Type checking
```

### Testing
```bash
uv run pytest -v          # Run all tests with verbose output
uv run pytest tests/test_specific_file.py  # Run specific test file
```

## Project Architecture

This is a Python package called `glob_grep_glance` that provides "three safe tools for agentic code analysis". The project follows a standard Python package structure:

- `src/glob_grep_glance/` - Main package code (currently empty, needs implementation)
- `tests/` - Test files using pytest
- Configuration uses modern Python tooling (uv, ruff, mypy)

The CI pipeline runs linting (ruff), formatting checks, type checking (mypy --strict), and tests on every push and PR to main branch.