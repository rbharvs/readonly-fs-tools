"""Glob functionality for safe file pattern matching."""

from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from ._budget import OutputBudget
from ._defaults import FilesystemPathEnumerator
from ._protocols import PathEnumerator
from ._sandbox import Sandbox
from .common import GlobPattern


class GlobOutput(BaseModel):
    """Output model for glob operations."""

    paths: List[Path]
    truncated: bool = Field(default=False)


class Globber:
    """Safe glob pattern matcher with sandbox constraints."""

    def __init__(self, path_enum: PathEnumerator) -> None:
        self.path_enum = path_enum

    @classmethod
    def from_sandbox(cls, sandbox: Sandbox) -> "Globber":
        """Create Globber with default dependencies."""
        return cls(path_enum=FilesystemPathEnumerator(sandbox=sandbox))

    def glob(
        self, glob_patterns: List[GlobPattern], budget: OutputBudget
    ) -> GlobOutput:
        """Find files matching the given glob patterns within sandbox constraints."""
        paths = []
        truncated = False

        for path in self.path_enum.iter_paths(glob_patterns):
            # Check if we have budget remaining
            if budget.remaining <= 0:
                truncated = True
                break

            # Count each path as 1 unit towards budget
            budget.debit(1)
            paths.append(path)

        return GlobOutput(paths=paths, truncated=truncated)
