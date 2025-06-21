"""Test basic instantiation and API functionality."""

import tempfile
from pathlib import Path

from readonly_fs_tools import (
    FileWindow,
    Globber,
    Grepper,
    OutputBudget,
    Sandbox,
    Viewer,
)


def test_globber_from_sandbox_instantiation() -> None:
    """Test that Globber can be instantiated from sandbox."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox = Sandbox(
            sandbox_dir=Path(temp_dir), blocked_files=[], allow_hidden=False
        )
        globber = Globber.from_sandbox(sandbox)
        assert isinstance(globber, Globber)


def test_grepper_from_sandbox_instantiation() -> None:
    """Test that Grepper can be instantiated from sandbox."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox = Sandbox(
            sandbox_dir=Path(temp_dir), blocked_files=[], allow_hidden=False
        )
        grepper = Grepper.from_sandbox(sandbox)
        assert isinstance(grepper, Grepper)


def test_viewr_from_sandbox_instantiation() -> None:
    """Test that Viewer can be instantiated from sandbox."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox = Sandbox(
            sandbox_dir=Path(temp_dir), blocked_files=[], allow_hidden=False
        )
        viewr = Viewer.from_sandbox(sandbox)
        assert isinstance(viewr, Viewer)


def test_globber_basic_functionality() -> None:
    """Test that Globber.glob works with empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox = Sandbox(
            sandbox_dir=Path(temp_dir), blocked_files=[], allow_hidden=False
        )
        globber = Globber.from_sandbox(sandbox)
        budget = OutputBudget(limit=100)

        result = globber.glob(["*.py"], budget)
        assert result.paths == []
        assert not result.truncated


def test_grepper_basic_functionality() -> None:
    """Test that Grepper.grep works with empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox = Sandbox(
            sandbox_dir=Path(temp_dir), blocked_files=[], allow_hidden=False
        )
        grepper = Grepper.from_sandbox(sandbox)
        budget = OutputBudget(limit=100)

        result = grepper.grep("test", ["*.py"], budget)
        assert result.matches == []
        assert not result.truncated


def test_viewr_file_not_found() -> None:
    """Test that Viewer.view handles missing files gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox = Sandbox(
            sandbox_dir=Path(temp_dir), blocked_files=[], allow_hidden=False
        )
        viewr = Viewer.from_sandbox(sandbox)
        budget = OutputBudget(limit=100)

        # Try to read a non-existent file
        import pytest

        with pytest.raises((FileNotFoundError, OSError)):
            viewr.view(
                Path(temp_dir) / "nonexistent.py",
                FileWindow(line_offset=0, line_count=10),
                budget,
            )
