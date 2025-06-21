"""Test cases for Viewer FileWindow behavior to ensure returned window reflects actual content."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from readonly_fs_tools import FileWindow, OutputBudget, Sandbox, Viewer


class TestViewerWindowBehavior:
    """Test that Viewer returns accurate FileWindow information."""

    @pytest.fixture
    def temp_sandbox(self) -> Generator[Path, None, None]:
        """Create a temporary directory for sandboxed operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox_path = Path(temp_dir)

            # Create test files
            (sandbox_path / "empty.txt").write_text("")
            (sandbox_path / "one_line.txt").write_text("single line\n")
            (sandbox_path / "three_lines.txt").write_text("line 1\nline 2\nline 3\n")

            yield sandbox_path

    @pytest.fixture
    def sandbox(self, temp_sandbox: Path) -> Sandbox:
        """Create a sandbox configuration."""
        return Sandbox(sandbox_dir=temp_sandbox, blocked_files=[], allow_hidden=False)

    @pytest.fixture
    def budget(self) -> OutputBudget:
        """Create an output budget for testing."""
        return OutputBudget(limit=1000)

    def test_empty_file_returns_correct_window(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test that empty file returns window with line_count=0."""
        viewr = Viewer.from_sandbox(sandbox)
        empty_file = sandbox.sandbox_dir / "empty.txt"
        window = FileWindow(line_offset=0, line_count=100)

        result = viewr.view(empty_file, window, budget)

        # Should return window reflecting what was actually read (0 lines)
        assert result.view.window.line_offset == 0
        assert result.view.window.line_count == 0
        assert result.view.contents == ""

    def test_request_more_lines_than_available(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test requesting more lines than file contains."""
        viewr = Viewer.from_sandbox(sandbox)
        one_line_file = sandbox.sandbox_dir / "one_line.txt"
        window = FileWindow(line_offset=0, line_count=5)

        result = viewr.view(one_line_file, window, budget)

        # Should return window reflecting what was actually read (1 line)
        assert result.view.window.line_offset == 0
        assert result.view.window.line_count == 1
        assert "single line" in result.view.contents

    def test_offset_beyond_file_end(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test offset beyond end of file."""
        viewr = Viewer.from_sandbox(sandbox)
        three_line_file = sandbox.sandbox_dir / "three_lines.txt"
        window = FileWindow(line_offset=10, line_count=5)

        result = viewr.view(three_line_file, window, budget)

        # Should return window with line_count=0 since no lines were read
        assert result.view.window.line_offset == 10
        assert result.view.window.line_count == 0
        assert result.view.contents == ""

    def test_partial_read_from_offset(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test reading from offset with more lines requested than available."""
        viewr = Viewer.from_sandbox(sandbox)
        three_line_file = sandbox.sandbox_dir / "three_lines.txt"
        window = FileWindow(line_offset=2, line_count=5)  # Start at line 2, request 5

        result = viewr.view(three_line_file, window, budget)

        # Should return window reflecting what was actually read (1 line from offset 2)
        assert result.view.window.line_offset == 2
        assert result.view.window.line_count == 1
        assert "line 3" in result.view.contents

    def test_exact_line_count_match(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test when requested lines exactly matches available lines."""
        viewr = Viewer.from_sandbox(sandbox)
        three_line_file = sandbox.sandbox_dir / "three_lines.txt"
        window = FileWindow(line_offset=0, line_count=3)

        result = viewr.view(three_line_file, window, budget)

        # Should return window reflecting what was actually read (3 lines)
        assert result.view.window.line_offset == 0
        assert result.view.window.line_count == 3
        assert "line 1" in result.view.contents
        assert "line 2" in result.view.contents
        assert "line 3" in result.view.contents
