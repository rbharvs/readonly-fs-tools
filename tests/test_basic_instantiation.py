"""Test basic instantiation and API functionality."""

import tempfile
from pathlib import Path

from glob_grep_glance import (
    FileWindow,
    Glancer,
    Globber,
    Grepper,
    OutputBudget,
    Sandbox,
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


def test_glancer_from_sandbox_instantiation() -> None:
    """Test that Glancer can be instantiated from sandbox."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox = Sandbox(
            sandbox_dir=Path(temp_dir), blocked_files=[], allow_hidden=False
        )
        glancer = Glancer.from_sandbox(sandbox)
        assert isinstance(glancer, Glancer)


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


def test_glancer_file_not_found() -> None:
    """Test that Glancer.glance handles missing files gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox = Sandbox(
            sandbox_dir=Path(temp_dir), blocked_files=[], allow_hidden=False
        )
        glancer = Glancer.from_sandbox(sandbox)
        budget = OutputBudget(limit=100)

        # Try to read a non-existent file
        import pytest

        with pytest.raises((FileNotFoundError, OSError)):
            glancer.glance(
                Path(temp_dir) / "nonexistent.py",
                FileWindow(line_offset=0, line_count=10),
                budget,
            )
