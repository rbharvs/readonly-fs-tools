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

This is a Python package called `readonly_fs_tools` that provides "three safe tools for agentic code analysis". The package implements three main tools with security-focused sandboxed file operations:

### Core Components
- `Globber` - Safe file pattern matching with glob patterns
- `Grepper` - Safe content search with regex patterns  
- `Glancer` - Safe file viewing with bounded content access

### Security Model
All tools inherit from `SandboxConfig` which enforces:
- Sandbox directory constraints (`sandbox_dir`)
- File blocklist (`blocked_files`) 
- Output size limits (`max_output_chars`)
- Hidden file access controls (`allow_hidden`)

### Key Types
- `GlobPattern` and `RegexPattern` - Validated input patterns
- `ViewBounds` and `ViewBuffer` - Safe file content access
- Dedicated output models for each tool (`GlobOutput`, `GrepOutput`, `GlanceOutput`)

The project uses Pydantic for data validation and type safety. Configuration uses modern Python tooling (uv, ruff, mypy) with strict type checking enabled.
