# readonly-fs-tools

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Three safe tools for agentic code analysis: **Globber**, **Grepper**, and **Viewer**.

This package provides security-focused, sandboxed file operations designed specifically for AI agents and automated code analysis workflows. Each tool enforces strict boundaries to prevent unauthorized file access while enabling powerful code exploration capabilities.

## Installation

```bash
# Add to your project
uv add readonly-fs-tools
```

## Quick Start

```python
from readonly_fs_tools import Sandbox, Globber, Grepper, Viewer, OutputBudget
from pathlib import Path

# Create a sandbox configuration
sandbox = Sandbox(
    sandbox_dir=Path("/path/to/your/project"),
    blocked_files=["*.secret", "private/*"],
    allow_hidden=False
)

# Set up output budget to limit response sizes
budget = OutputBudget(max_chars=10000)

# 1. Find files with glob patterns
globber = Globber.from_sandbox(sandbox)
glob_result = globber.glob("**/*.py", budget)
print(f"Found {len(glob_result.paths)} Python files")

# 2. Search file contents with regex
grepper = Grepper.from_sandbox(sandbox)
grep_result = grepper.grep(r"class \w+", "**/*.py", budget)
for match in grep_result.matches:
    print(f"{match.path}:{match.line_number}: {match.line}")

# 3. View file contents safely
viewer = Viewer.from_sandbox(sandbox)
view_result = viewer.view("src/main.py", budget)
print(view_result.content.text)
```

## Core Components

### Security Model
All tools are executed in the context of a `Sandbox` which enforces:
- **Sandbox directory constraints** - Operations limited to specified directory
- **File blocklist** - Pattern-based file exclusion (e.g., `*.secret`, `private/*`)
- **Hidden file controls** - Optional access to dotfiles and hidden directories (off by default)

In addition, each tool supports:
- **Output size limits** - Configurable via `OutputBudget` to constrain token usage
- **Streaming operations** - Files are processed in a memory-efficient manner, allowing for large files to be handled safely

### Tools

**Globber** - Safe file pattern matching
- Uses glob patterns like `**/*.py` or `src/**/*.{js,ts}`
- Respects sandbox boundaries and blocklists

**Grepper** - Safe content search
- Regex-based content search across files
- Pattern matching with full regex syntax support
- Returns matches with file paths, line numbers, and the full matched line for context

**Viewer** - Safe file viewing
- Bounded file content access with configurable limits
- Support for line ranges and content windows
- Safe handling of binary files and large files

### Key Types

```python
# Pattern validation
GlobPattern     # Validated glob patterns
RegexPattern    # Validated regex patterns

# File access
FileWindow      # Line-based file access windows
FileContent     # Safe file content representation
FileReadResult  # Results with metadata

# Configuration
Sandbox         # Security boundary configuration
OutputBudget    # Output size limiting
```

## Development

This project uses `uv` for dependency management.

```
uv sync --dev
```

### Code Quality
```bash
uv run ruff check --fix    # Lint code
uv run ruff format         # Format code
uv run mypy --strict .     # Type checking
```

### Testing
```bash
uv run pytest                              # Run all tests
uv run pytest tests/test_specific_file.py  # Run specific tests
```

## Architecture

The package implements a three-layer security model:
1. **Sandbox** - Directory and file access controls
2. **Budget** - Resource usage limits
3. **Validation** - Input pattern validation and output sanitization

All operations are designed to be safe for automated/AI agent use while providing the file system access needed for code analysis tasks.

## Generative AI disclaimer

This package was designed by a human developer, with assistance from generative AI. The code however was generated almost entirely by generative AI.
The security model and design principles were carefully crafted to ensure safety and reliability for agentic code/filesystem analysis tasks. If you find any issues or have suggestions, please open an issue on GitHub.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [Homepage](https://github.com/rbharvs/readonly-fs-tools)
- [Issues](https://github.com/rbharvs/readonly-fs-tools/issues)
- [Changelog](https://github.com/rbharvs/readonly-fs-tools/releases)
