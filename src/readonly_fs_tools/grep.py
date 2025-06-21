"""Grep functionality for safe content searching."""

from typing import List

from pydantic import BaseModel, Field

from ._internal.path_enumerator import FilesystemPathEnumerator
from ._internal.regex_searcher import StreamingRegexSearcher
from .budget import BudgetExceeded, OutputBudget
from .common import FileContent, GlobPattern, RegexPattern
from .sandbox import Sandbox


class GrepOutput(BaseModel):
    """Output model for grep operations."""

    matches: List[FileContent]
    truncated: bool = Field(default=False)


class Grepper:
    """Safe content searcher with sandbox constraints."""

    def __init__(
        self,
        path_enum: FilesystemPathEnumerator,
        regex_searcher: StreamingRegexSearcher,
    ) -> None:
        self.path_enum = path_enum
        self.regex_searcher = regex_searcher

    @classmethod
    def from_sandbox(cls, sandbox: Sandbox) -> "Grepper":
        """Create Grepper with default dependencies."""
        return cls(
            path_enum=FilesystemPathEnumerator(sandbox=sandbox),
            regex_searcher=StreamingRegexSearcher(sandbox=sandbox),
        )

    def grep(
        self,
        search_regex: RegexPattern,
        glob_patterns: List[GlobPattern],
        budget: OutputBudget,
    ) -> GrepOutput:
        """Search for regex pattern within files matching glob patterns."""
        matches = []
        truncated = False

        # First get all files matching the glob patterns
        for file_path in self.path_enum.iter_paths(glob_patterns):
            try:
                # Search for matches in this file
                for match in self.regex_searcher.iter_matches(file_path, search_regex):
                    budget.debit(len(match.model_dump_json()))
                    matches.append(match)

            except BudgetExceeded:
                # If budget exceeded, set truncated flag and break
                truncated = True
                break

            except Exception:
                # Continue to next file if this one fails
                continue

        return GrepOutput(matches=matches, truncated=truncated)
