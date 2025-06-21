"""Sandbox security system for safe file operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

from pydantic import BaseModel


class SandboxViolation(RuntimeError):
    """Raised when a path tries to leave the sandbox or is otherwise denied."""

    pass


class Sandbox(BaseModel):
    """Configuration and validator for sandboxed file operations."""

    sandbox_dir: Path
    blocked_files: List[Path]
    allow_hidden: bool = False

    def model_post_init(self, __context: dict[str, Any] | None) -> None:
        """Resolve blocked files to absolute paths during initialization."""
        # Resolve all blocked files to absolute paths for consistent comparison
        resolved_blocked = []
        for blocked_path in self.blocked_files:
            try:
                resolved_blocked.append(blocked_path.resolve())
            except (OSError, RuntimeError):
                # If resolution fails, keep the original path
                # This handles cases where the file doesn't exist
                if blocked_path.is_absolute():
                    resolved_blocked.append(blocked_path)
                else:
                    # For relative paths, make them absolute relative to cwd
                    resolved_blocked.append(Path.cwd() / blocked_path)

        # Update the blocked_files list with resolved paths
        object.__setattr__(self, "blocked_files", resolved_blocked)

    def is_allowed(self, p: Path) -> bool:
        """Check if a path is allowed within sandbox constraints."""
        try:
            # Resolve the path to handle symlinks and relative paths
            try:
                resolved_path = p.resolve()
            except (OSError, RuntimeError):
                # If resolution fails, work with the original path
                resolved_path = p.absolute() if not p.is_absolute() else p

            # Check if path is within sandbox directory
            try:
                sandbox_resolved = self.sandbox_dir.resolve()
            except (OSError, RuntimeError):
                sandbox_resolved = (
                    self.sandbox_dir.absolute()
                    if not self.sandbox_dir.is_absolute()
                    else self.sandbox_dir
                )

            # Check if the resolved path is within the sandbox
            try:
                resolved_path.relative_to(sandbox_resolved)
            except ValueError:
                # Path is not within sandbox
                return False

            # Check for hidden files/directories if not allowed
            if not self.allow_hidden:
                # Check if any part of the path is hidden
                for part in resolved_path.parts:
                    if part.startswith(".") and part not in [".", ".."]:
                        return False

            # Check if path is in blocklist
            for blocked_path in self.blocked_files:
                try:
                    if resolved_path == blocked_path:
                        return False
                    # Also check if the path is equal when resolved from sandbox_dir
                    # This handles relative paths in blocklist
                    if (
                        resolved_path
                        == (sandbox_resolved / blocked_path.name).resolve()
                    ):
                        return False
                except (OSError, RuntimeError):
                    # If comparison fails, be conservative and allow
                    continue

            return True

        except Exception:
            # If any unexpected error occurs, be conservative and deny access
            return False

    def require_allowed(self, p: Path) -> Path:
        """Validate path is allowed, raise SandboxViolation if not."""
        if not self.is_allowed(p):
            raise SandboxViolation(f"Access denied to path: {p}")
        return p
