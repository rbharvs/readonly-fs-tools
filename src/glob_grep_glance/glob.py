"""Glob functionality for safe file pattern matching."""

from pathlib import Path
from typing import List

from pydantic import BaseModel

from .common import GlobPattern


class GlobOutput(BaseModel):
    """Output model for glob operations."""

    paths: List[Path]
    truncated: bool


class Globber(BaseModel):
    """Safe glob pattern matcher with sandbox constraints."""

    def glob(self, glob_pattern: GlobPattern) -> GlobOutput:
        """Find files matching the given glob pattern within sandbox constraints."""
        raise NotImplementedError("Glob functionality not yet implemented")
