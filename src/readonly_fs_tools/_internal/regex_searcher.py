"""Streaming regex searching implementation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel

from ..common import FileContent, FileWindow, RegexPattern
from ..sandbox import Sandbox


class StreamingRegexSearcher(BaseModel):
    """Line-oriented regex search. Simple and memory-friendly."""

    sandbox: Sandbox

    def iter_matches(
        self,
        file: Path,
        search_regex: RegexPattern,
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
                        yield FileContent(
                            path=file,
                            contents=line,
                            window=FileWindow(line_offset=line_number, line_count=1),
                        )

        except (OSError, IOError) as e:
            # Re-raise file system errors (like file not found)
            raise e
