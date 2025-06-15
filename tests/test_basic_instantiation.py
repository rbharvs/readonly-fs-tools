"""Test basic instantiation and API functionality."""

from pathlib import Path

import pytest

from glob_grep_glance import Glancer, Globber, Grepper, ViewBounds


def test_globber_instantiation() -> None:
    """Test that Globber can be instantiated with basic parameters."""
    globber = Globber(sandbox_dir=Path("/tmp"), blocked_files=[])
    assert globber.sandbox_dir == Path("/tmp")
    assert globber.blocked_files == []
    assert globber.max_output_chars == 10000
    assert globber.allow_hidden is False


def test_grepper_instantiation() -> None:
    """Test that Grepper can be instantiated with basic parameters."""
    grepper = Grepper(sandbox_dir=Path("/tmp"), blocked_files=[])
    assert grepper.sandbox_dir == Path("/tmp")
    assert grepper.blocked_files == []
    assert grepper.max_output_chars == 10000
    assert grepper.allow_hidden is False


def test_glancer_instantiation() -> None:
    """Test that Glancer can be instantiated with basic parameters."""
    glancer = Glancer(sandbox_dir=Path("/tmp"), blocked_files=[])
    assert glancer.sandbox_dir == Path("/tmp")
    assert glancer.blocked_files == []
    assert glancer.max_output_chars == 10000
    assert glancer.allow_hidden is False


def test_globber_method_not_implemented() -> None:
    """Test that Globber.glob raises NotImplementedError."""
    globber = Globber(sandbox_dir=Path("/tmp"), blocked_files=[])
    with pytest.raises(
        NotImplementedError, match="Glob functionality not yet implemented"
    ):
        globber.glob("*.py")


def test_grepper_method_not_implemented() -> None:
    """Test that Grepper.grep raises NotImplementedError."""
    grepper = Grepper(sandbox_dir=Path("/tmp"), blocked_files=[])
    with pytest.raises(
        NotImplementedError, match="Grep functionality not yet implemented"
    ):
        grepper.grep("test", ["*.py"])


def test_glancer_method_not_implemented() -> None:
    """Test that Glancer.glance raises NotImplementedError."""
    glancer = Glancer(sandbox_dir=Path("/tmp"), blocked_files=[])
    with pytest.raises(
        NotImplementedError, match="Glance functionality not yet implemented"
    ):
        glancer.glance(Path("test.py"), ViewBounds(start_line=1, num_lines=10))
