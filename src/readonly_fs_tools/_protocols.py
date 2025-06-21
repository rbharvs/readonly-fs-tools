from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Protocol

from ._budget import OutputBudget
from .common import FileContent, FileReadResult, FileWindow, GlobPattern, RegexPattern


class PathEnumerator(Protocol):
    """Protocol for enumerating paths matching glob patterns."""

    def iter_paths(self, glob_patterns: List[GlobPattern]) -> Iterable[Path]:
        """Yield paths matching the glob patterns within sandbox constraints."""
        ...


class FileReader(Protocol):
    """Protocol for reading file content windows."""

    def read_window(
        self,
        file: Path,
        window: FileWindow,
        budget: OutputBudget,
    ) -> FileReadResult:
        """Read file window with budget constraints."""
        ...


class RegexSearcher(Protocol):
    """Protocol for streaming regex matches from files."""

    def iter_matches(
        self,
        file: Path,
        search_regex: RegexPattern,
    ) -> Iterable[FileContent]:
        """Yield regex matches from file, respecting budget constraints."""
        ...
