"""Default implementations for file operations."""

from __future__ import annotations

import glob
from pathlib import Path
from typing import Iterable, List, Set

from pydantic import BaseModel

from ._sandbox import Sandbox
from .common import GlobPattern


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
