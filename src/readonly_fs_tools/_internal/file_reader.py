"""Streaming file reading implementation."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ..budget import BudgetExceeded, OutputBudget
from ..common import FileReadResult, FileWindow
from ..sandbox import Sandbox


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
        lines_read = 0

        try:
            # Open file with UTF-8 encoding and ignore errors for binary files
            budget.debit(len(file.as_posix()))  # Debit budget for file path length
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                # Skip to the starting line offset
                current_line = 0
                while current_line < window.line_offset:
                    line = f.readline()
                    if not line:  # EOF reached before offset
                        break
                    current_line += 1

                # Read the requested number of lines
                while lines_read < window.line_count:
                    line = f.readline()
                    if not line:  # EOF reached
                        break
                    budget.debit(len(line))
                    contents += line
                    lines_read += 1

        except (OSError, IOError) as e:
            # Re-raise file system errors (like file not found)
            raise e

        except BudgetExceeded:
            truncated = True

        # Create actual window reflecting what was actually read
        actual_window = FileWindow(
            line_offset=window.line_offset, line_count=lines_read
        )

        return FileReadResult(
            contents=contents, truncated=truncated, actual_window=actual_window
        )
