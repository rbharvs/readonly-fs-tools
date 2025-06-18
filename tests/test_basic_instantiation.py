"""Test basic instantiation and API functionality."""

from pathlib import Path

import pytest

from glob_grep_glance import FileWindow, Glancer, Globber, Grepper


def test_globber_instantiation() -> None:
    """Test that Globber can be instantiated with basic parameters."""
    globber = Globber()
    assert isinstance(globber, Globber)


def test_grepper_instantiation() -> None:
    """Test that Grepper can be instantiated with basic parameters."""
    grepper = Grepper()
    assert isinstance(grepper, Grepper)


def test_glancer_instantiation() -> None:
    """Test that Glancer can be instantiated with basic parameters."""
    glancer = Glancer()
    assert isinstance(glancer, Glancer)


def test_globber_method_not_implemented() -> None:
    """Test that Globber.glob raises NotImplementedError."""
    globber = Globber()
    with pytest.raises(
        NotImplementedError, match="Glob functionality not yet implemented"
    ):
        globber.glob("*.py")


def test_grepper_method_not_implemented() -> None:
    """Test that Grepper.grep raises NotImplementedError."""
    grepper = Grepper()
    with pytest.raises(
        NotImplementedError, match="Grep functionality not yet implemented"
    ):
        grepper.grep("test", ["*.py"])


def test_glancer_method_not_implemented() -> None:
    """Test that Glancer.glance raises NotImplementedError."""
    glancer = Glancer()
    with pytest.raises(
        NotImplementedError, match="Glance functionality not yet implemented"
    ):
        glancer.glance(Path("test.py"), FileWindow(line_offset=0, line_count=10))
