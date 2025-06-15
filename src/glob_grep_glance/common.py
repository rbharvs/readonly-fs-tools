"""Common models and utilities shared across the glob_grep_glance package."""

from pathlib import Path
from typing import Annotated, List

from pydantic import AfterValidator, BaseModel


def validate_glob_pattern(v: str) -> str:
    """Validate glob pattern for safety and correctness."""
    # Placeholder implementation
    return v


def validate_regex_pattern(v: str) -> str:
    """Validate regex pattern for safety and correctness."""
    # Placeholder implementation
    return v


GlobPattern = Annotated[str, AfterValidator(validate_glob_pattern)]
RegexPattern = Annotated[str, AfterValidator(validate_regex_pattern)]


class ViewBounds(BaseModel):
    """Defines bounds for viewing a portion of a file."""

    start_line: int
    num_lines: int


class ViewBuffer(BaseModel):
    """Contains file content within specified bounds."""

    path: Path
    contents: str
    bounds: ViewBounds


class SandboxConfig(BaseModel):
    """Base configuration for sandboxed file operations with security constraints."""

    sandbox_dir: Path
    max_output_chars: int = 10000
    blocked_files: List[Path]
    allow_hidden: bool = False
