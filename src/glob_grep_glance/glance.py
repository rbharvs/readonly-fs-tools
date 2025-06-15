"""Glance functionality for safe file viewing."""

from pathlib import Path

from pydantic import BaseModel

from .common import SandboxConfig, ViewBounds, ViewBuffer


class GlanceOutput(BaseModel):
    """Output model for glance operations."""

    view: ViewBuffer
    truncated: bool


class Glancer(SandboxConfig):
    """Safe file viewer with sandbox constraints."""

    def glance(self, file_path: Path, window: ViewBounds) -> GlanceOutput:
        """View a portion of a file within the specified bounds."""
        raise NotImplementedError("Glance functionality not yet implemented")
