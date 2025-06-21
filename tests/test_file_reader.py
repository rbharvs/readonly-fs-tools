"""Test StreamingFileReader implementation with comprehensive coverage."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from readonly_fs_tools._internal.file_reader import StreamingFileReader
from readonly_fs_tools.budget import OutputBudget
from readonly_fs_tools.common import FileWindow
from readonly_fs_tools.sandbox import Sandbox, SandboxViolation


class TestStreamingFileReader:
    """Test the StreamingFileReader class."""

    @pytest.fixture
    def temp_sandbox(self) -> Generator[tuple[Path, Sandbox], None, None]:
        """Create a temporary sandbox directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox_dir = Path(temp_dir)
            sandbox = Sandbox(
                sandbox_dir=sandbox_dir, blocked_files=[], allow_hidden=False
            )
            yield sandbox_dir, sandbox

    @pytest.fixture
    def reader(self, temp_sandbox: tuple[Path, Sandbox]) -> StreamingFileReader:
        """Create a StreamingFileReader instance."""
        _, sandbox = temp_sandbox
        return StreamingFileReader(sandbox=sandbox)

    def test_reader_instantiation(self, temp_sandbox: tuple[Path, Sandbox]) -> None:
        """Test that StreamingFileReader can be instantiated."""
        _, sandbox = temp_sandbox
        reader = StreamingFileReader(sandbox=sandbox)
        assert reader.sandbox == sandbox

    def test_read_simple_file(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test reading a simple text file."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_content = "line 1\nline 2\nline 3\n"
        test_file.write_text(test_content, encoding="utf-8")

        budget = OutputBudget(limit=200)  # Increased to account for file path cost
        window = FileWindow(line_offset=0, line_count=3)

        result = reader.read_window(test_file, window, budget)

        assert result.contents == test_content
        assert not result.truncated
        # Budget remaining = initial - file_path_length - content_length
        expected_remaining = 200 - len(test_file.as_posix()) - len(test_content)
        assert budget.remaining == expected_remaining

    def test_read_file_with_window_offset(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test reading from a specific line offset."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("line 1\nline 2\nline 3\nline 4\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=1, line_count=2)

        result = reader.read_window(test_file, window, budget)

        assert result.contents == "line 2\nline 3\n"
        assert not result.truncated

    def test_read_file_shorter_than_window(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test reading a file shorter than requested window."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("line 1\nline 2\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        window = FileWindow(
            line_offset=0, line_count=5
        )  # Request more lines than exist

        result = reader.read_window(test_file, window, budget)

        assert result.contents == "line 1\nline 2\n"
        assert not result.truncated  # Should not be truncated if file is just short

    def test_read_empty_file(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test reading an empty file."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=0, line_count=1)

        result = reader.read_window(test_file, window, budget)

        assert result.contents == ""
        assert not result.truncated

    def test_read_single_line_file(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test reading a single line file."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "single.txt"
        test_file.write_text("single line", encoding="utf-8")

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=0, line_count=1)

        result = reader.read_window(test_file, window, budget)

        assert result.contents == "single line"
        assert not result.truncated

    def test_budget_constraint_enforcement(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test that budget constraints are enforced per line."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text(
            "short\nmedium line\nvery long line that exceeds budget\n", encoding="utf-8"
        )

        # Calculate budget to allow file path + first two lines but not the third
        first_two_lines = "short\nmedium line\n"
        budget_needed = (
            len(test_file.as_posix()) + len(first_two_lines) + 5
        )  # +5 buffer
        budget = OutputBudget(limit=budget_needed)
        window = FileWindow(line_offset=0, line_count=3)

        result = reader.read_window(test_file, window, budget)

        # Should read first two lines but stop before the third
        assert "short\nmedium line\n" in result.contents
        assert "very long line" not in result.contents
        assert result.truncated

    def test_budget_exceeded_on_first_line(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test budget exceeded on the very first line."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text(
            "this is a very long first line that exceeds the tiny budget\n",
            encoding="utf-8",
        )

        budget = OutputBudget(limit=5)  # Very small budget
        window = FileWindow(line_offset=0, line_count=1)

        result = reader.read_window(test_file, window, budget)

        assert result.contents == ""
        assert result.truncated

    def test_binary_file_handling(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test graceful handling of binary files."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "binary.bin"
        # Write some binary data
        test_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=0, line_count=1)

        # Should not raise an exception due to UTF-8 errors
        result = reader.read_window(test_file, window, budget)

        # Content might be garbled but should not crash
        assert isinstance(result.contents, str)
        assert isinstance(result.truncated, bool)

    def test_file_with_very_long_lines(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test files with very long lines."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "long_lines.txt"
        long_line = "x" * 1000 + "\n"
        test_file.write_text(long_line + "short\n", encoding="utf-8")

        budget = OutputBudget(limit=500)  # Budget smaller than first line
        window = FileWindow(line_offset=0, line_count=2)

        result = reader.read_window(test_file, window, budget)

        assert result.contents == ""  # Can't read even first line
        assert result.truncated

    def test_window_offset_beyond_file_end(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test window starting beyond end of file."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("line 1\nline 2\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=10, line_count=1)  # Start way past end

        result = reader.read_window(test_file, window, budget)

        assert result.contents == ""
        assert not result.truncated  # Not truncated, just no content at that offset

    def test_sandbox_security_validation(
        self, temp_sandbox: tuple[Path, Sandbox]
    ) -> None:
        """Test that sandbox validation is enforced."""
        sandbox_dir, sandbox = temp_sandbox
        reader = StreamingFileReader(sandbox=sandbox)

        # Try to read outside sandbox
        outside_file = Path("/etc/passwd")  # System file outside sandbox

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=0, line_count=1)

        with pytest.raises(SandboxViolation):
            reader.read_window(outside_file, window, budget)

    def test_blocked_file_access(self, temp_sandbox: tuple[Path, Sandbox]) -> None:
        """Test that blocked files are rejected."""
        sandbox_dir, _ = temp_sandbox
        blocked_file = sandbox_dir / "blocked.txt"
        blocked_file.write_text("secret content", encoding="utf-8")

        # Create sandbox with blocked file
        sandbox = Sandbox(
            sandbox_dir=sandbox_dir, blocked_files=[blocked_file], allow_hidden=False
        )
        reader = StreamingFileReader(sandbox=sandbox)

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=0, line_count=1)

        with pytest.raises(SandboxViolation):
            reader.read_window(blocked_file, window, budget)

    def test_hidden_file_access_denied(
        self, temp_sandbox: tuple[Path, Sandbox]
    ) -> None:
        """Test that hidden files are denied when allow_hidden=False."""
        sandbox_dir, sandbox = temp_sandbox
        hidden_file = sandbox_dir / ".hidden"
        hidden_file.write_text("hidden content", encoding="utf-8")

        reader = StreamingFileReader(sandbox=sandbox)  # allow_hidden=False by default

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=0, line_count=1)

        with pytest.raises(SandboxViolation):
            reader.read_window(hidden_file, window, budget)

    def test_hidden_file_access_allowed(
        self, temp_sandbox: tuple[Path, Sandbox]
    ) -> None:
        """Test that hidden files are allowed when allow_hidden=True."""
        sandbox_dir, _ = temp_sandbox
        hidden_file = sandbox_dir / ".hidden"
        hidden_file.write_text("hidden content\n", encoding="utf-8")

        # Create sandbox that allows hidden files
        sandbox = Sandbox(sandbox_dir=sandbox_dir, blocked_files=[], allow_hidden=True)
        reader = StreamingFileReader(sandbox=sandbox)

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=0, line_count=1)

        result = reader.read_window(hidden_file, window, budget)

        assert result.contents == "hidden content\n"
        assert not result.truncated

    def test_nonexistent_file(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test handling of nonexistent files."""
        sandbox_dir, _ = temp_sandbox
        nonexistent_file = sandbox_dir / "does_not_exist.txt"

        budget = OutputBudget(limit=100)
        window = FileWindow(line_offset=0, line_count=1)

        # Should raise appropriate exception (FileNotFoundError or similar)
        with pytest.raises((FileNotFoundError, OSError)):
            reader.read_window(nonexistent_file, window, budget)

    def test_zero_line_count_window(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test window with zero line count (now valid for actual windows)."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("line 1\n", encoding="utf-8")

        # FileWindow should now accept line_count=0 (for actual window reporting)
        window = FileWindow(line_offset=0, line_count=0)
        assert window.line_count == 0

    def test_negative_line_offset_window(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test window with negative line offset (should be invalid)."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("line 1\n", encoding="utf-8")

        # FileWindow should reject negative line_offset during validation
        with pytest.raises(ValueError):
            FileWindow(line_offset=-1, line_count=1)

    def test_line_by_line_budget_debit(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test that budget is debited line by line, not all at once."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

        # Calculate budget: file path + first two lines exactly
        first_two_lines = "line1\nline2\n"
        budget_limit = len(test_file.as_posix()) + len(first_two_lines)
        budget = OutputBudget(limit=budget_limit)
        window = FileWindow(line_offset=0, line_count=3)

        result = reader.read_window(test_file, window, budget)

        # Should read first two lines but stop before third
        assert result.contents == "line1\nline2\n"
        assert result.truncated
        assert budget.remaining == 0  # Budget should be exactly consumed

    def test_utf8_with_special_characters(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test reading UTF-8 files with special characters."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "utf8.txt"
        test_content = "héllo wørld 🌍\nünicode tëst ñoño\n"
        test_file.write_text(test_content, encoding="utf-8")

        # Increase budget to account for file path + UTF-8 content
        budget = OutputBudget(limit=200)
        window = FileWindow(line_offset=0, line_count=2)

        result = reader.read_window(test_file, window, budget)

        assert result.contents == test_content
        assert not result.truncated

    def test_malformed_encoding_graceful_handling(
        self, temp_sandbox: tuple[Path, Sandbox], reader: StreamingFileReader
    ) -> None:
        """Test graceful handling of malformed encoding."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "malformed.txt"
        # Write some invalid UTF-8 sequences
        test_file.write_bytes(b"valid text\n\xff\xfe invalid utf8\n more text\n")

        # Increase budget to account for file path + content
        budget = OutputBudget(limit=200)
        window = FileWindow(line_offset=0, line_count=3)

        # Should not crash due to encoding errors (errors="ignore")
        result = reader.read_window(test_file, window, budget)

        assert isinstance(result.contents, str)
        assert "valid text" in result.contents
        assert "more text" in result.contents
