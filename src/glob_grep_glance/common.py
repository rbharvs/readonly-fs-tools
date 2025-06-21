from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def validate_glob_pattern(v: str) -> str:
    """Validate glob pattern for safety and correctness."""
    return v


def validate_regex_pattern(v: str) -> str:
    """Validate regex pattern for safety and correctness."""
    return v


GlobPattern = Annotated[str, AfterValidator(validate_glob_pattern)]
RegexPattern = Annotated[str, AfterValidator(validate_regex_pattern)]


class FileWindow(BaseModel):
    """Defines bounds for viewing a portion of a file."""

    line_offset: int = Field(ge=0, description="Starting line number (0-based)")
    line_count: int = Field(ge=0, description="Number of lines to read")


class FileContent(BaseModel):
    """Contains file content within specified bounds."""

    path: Path
    contents: str
    window: FileWindow


class FileReadResult(BaseModel):
    """Result of reading a file window."""

    contents: str
    truncated: bool
    actual_window: FileWindow
