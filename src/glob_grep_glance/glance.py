"""Glance functionality for safe file viewing."""

from pathlib import Path

from pydantic import BaseModel

from .common import FileContent, FileWindow


class GlanceOutput(BaseModel):
    """Output model for glance operations."""

    view: FileContent
    truncated: bool


class Glancer(BaseModel):
    """Safe file viewer with sandbox constraints."""

    def glance(self, file_path: Path, window: FileWindow) -> GlanceOutput:
        """View a portion of a file within the specified bounds."""
        raise NotImplementedError("Glance functionality not yet implemented")
