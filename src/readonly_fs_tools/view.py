"""View functionality for safe file viewing."""

from pathlib import Path

from pydantic import BaseModel, Field

from ._internal.file_reader import StreamingFileReader
from .budget import OutputBudget
from .common import FileContent, FileWindow
from .sandbox import Sandbox


class ViewOutput(BaseModel):
    """Output model for view operations."""

    view: FileContent
    truncated: bool = Field(default=False)


class Viewer:
    """Safe file viewer with sandbox constraints."""

    def __init__(self, file_reader: StreamingFileReader) -> None:
        self.file_reader = file_reader

    @classmethod
    def from_sandbox(cls, sandbox: Sandbox) -> "Viewer":
        """Create Viewer with default dependencies."""
        return cls(file_reader=StreamingFileReader(sandbox=sandbox))

    def view(
        self, file_path: Path, window: FileWindow, budget: OutputBudget
    ) -> ViewOutput:
        """View a portion of a file within the specified bounds."""
        # Read the file window using the file reader
        result = self.file_reader.read_window(file_path, window, budget)

        # Create FileContent from the result using the actual window that was read
        view = FileContent(
            path=file_path, contents=result.contents, window=result.actual_window
        )

        return ViewOutput(view=view, truncated=result.truncated)
