"""Default implementations for file operations."""

from __future__ import annotations

import glob
import re
from pathlib import Path
from typing import Iterable, List, Set

from pydantic import BaseModel

from ._budget import OutputBudget
from ._sandbox import Sandbox
from .common import FileContent, FileReadResult, FileWindow, GlobPattern, RegexPattern


class FilesystemPathEnumerator(BaseModel):
    """Default implementation of path enumeration with sandbox validation."""

    sandbox: Sandbox

    def iter_paths(self, glob_patterns: List[GlobPattern]) -> Iterable[Path]:
        """Yield paths matching the glob patterns within sandbox constraints.

        Features:
        - Lazy iteration (yield as we discover paths)
        - Deduplication of paths across multiple patterns
        - Error propagation for invalid glob patterns
        - Filesystem order (no sorting for memory efficiency)
        - Sandbox constraint enforcement
        """
        seen_paths: Set[Path] = set()

        for pattern in glob_patterns:
            # Use glob to find matching paths
            # This will raise an exception for invalid patterns (fail-fast)

            # Convert pattern to work from sandbox directory
            # Use glob.glob with the sandbox directory as root
            full_pattern = str(self.sandbox.sandbox_dir / pattern)

            # Include hidden files in glob search by default
            # Sandbox will filter them out if allow_hidden=False
            for path_str in glob.glob(
                full_pattern, recursive=True, include_hidden=True
            ):
                path = Path(path_str)

                # Skip if we've already seen this path (deduplication)
                if path in seen_paths:
                    continue

                # Apply sandbox validation
                if self.sandbox.is_allowed(path):
                    seen_paths.add(path)
                    yield path


class StreamingFileReader(BaseModel):
    """Default implementation of windowed file reading."""

    sandbox: Sandbox

    def read_window(
        self,
        file: Path,
        window: FileWindow,
        budget: OutputBudget,
    ) -> FileReadResult:
        """Read file window with budget constraints."""
        # Validate file access through sandbox
        self.sandbox.require_allowed(file)

        contents = ""
        truncated = False

        try:
            # Open file with UTF-8 encoding and ignore errors for binary files
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                # Skip to the starting line offset
                current_line = 0
                while current_line < window.line_offset:
                    line = f.readline()
                    if not line:  # EOF reached before offset
                        break
                    current_line += 1

                # Read the requested number of lines
                lines_read = 0
                while lines_read < window.line_count:
                    line = f.readline()
                    if not line:  # EOF reached
                        break

                    # Check if this line would exceed budget
                    if len(line) > budget.remaining:
                        truncated = True
                        break

                    # Line fits in budget, debit and add to contents
                    budget.debit(len(line))
                    contents += line
                    lines_read += 1

        except (OSError, IOError) as e:
            # Re-raise file system errors (like file not found)
            raise e

        return FileReadResult(contents=contents, truncated=truncated)


class StreamingRegexSearcher(BaseModel):
    """Line-oriented regex search. Simple and memory-friendly."""

    sandbox: Sandbox

    def iter_matches(
        self,
        file: Path,
        search_regex: RegexPattern,
        budget: OutputBudget,
    ) -> Iterable[FileContent]:
        """Yield regex matches from file, one per matching line."""
        # Validate file access through sandbox
        self.sandbox.require_allowed(file)

        # Compile regex pattern
        compiled_pattern = re.compile(search_regex)

        try:
            # Open file with UTF-8 encoding and ignore errors for binary files
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                for line_number, line in enumerate(f):
                    # Check if line matches pattern
                    if compiled_pattern.search(line):
                        # Check if this line would exceed budget
                        if len(line) > budget.remaining:
                            # Skip this line and continue to next
                            continue

                        # Line fits in budget, debit and yield match
                        budget.debit(len(line))
                        yield FileContent(
                            path=file,
                            contents=line,
                            window=FileWindow(line_offset=line_number, line_count=1),
                        )

        except (OSError, IOError) as e:
            # Re-raise file system errors (like file not found)
            raise e
