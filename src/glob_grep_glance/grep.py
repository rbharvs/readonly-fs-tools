"""Grep functionality for safe content searching."""

from typing import List

from pydantic import BaseModel

from .common import GlobPattern, RegexPattern, SandboxConfig, ViewBuffer


class GrepOutput(BaseModel):
    """Output model for grep operations."""

    matches: List[ViewBuffer]
    truncated: bool


class Grepper(SandboxConfig):
    """Safe content searcher with sandbox constraints."""

    def grep(
        self, search_regex: RegexPattern, glob_patterns: List[GlobPattern]
    ) -> GrepOutput:
        """Search for regex pattern within files matching glob patterns."""
        raise NotImplementedError("Grep functionality not yet implemented")
