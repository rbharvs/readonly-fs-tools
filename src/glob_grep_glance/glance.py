"""Glance functionality for safe file viewing."""

from pathlib import Path

from pydantic import BaseModel, Field

from ._budget import OutputBudget
from ._defaults import StreamingFileReader
from ._protocols import FileReader
from ._sandbox import Sandbox
from .common import FileContent, FileWindow


class GlanceOutput(BaseModel):
    """Output model for glance operations."""

    view: FileContent
    truncated: bool = Field(default=False)


class Glancer:
    """Safe file viewer with sandbox constraints."""

    def __init__(self, file_reader: FileReader) -> None:
        self.file_reader = file_reader

    @classmethod
    def from_sandbox(cls, sandbox: Sandbox) -> "Glancer":
        """Create Glancer with default dependencies."""
        return cls(file_reader=StreamingFileReader(sandbox=sandbox))

    def glance(
        self, file_path: Path, window: FileWindow, budget: OutputBudget
    ) -> GlanceOutput:
        """View a portion of a file within the specified bounds."""
        # Read the file window using the file reader
        result = self.file_reader.read_window(file_path, window, budget)

        # Create FileContent from the result using the actual window that was read
        view = FileContent(
            path=file_path, contents=result.contents, window=result.actual_window
        )

        return GlanceOutput(view=view, truncated=result.truncated)
