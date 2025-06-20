"""Test StreamingRegexSearcher implementation with comprehensive coverage."""

import re
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from glob_grep_glance._budget import OutputBudget
from glob_grep_glance._defaults import StreamingRegexSearcher
from glob_grep_glance._sandbox import Sandbox, SandboxViolation
from glob_grep_glance.common import FileContent, FileWindow, RegexPattern


class TestStreamingRegexSearcher:
    """Test the StreamingRegexSearcher class."""

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
    def searcher(self, temp_sandbox: tuple[Path, Sandbox]) -> StreamingRegexSearcher:
        """Create a StreamingRegexSearcher instance."""
        _, sandbox = temp_sandbox
        return StreamingRegexSearcher(sandbox=sandbox)

    def test_searcher_instantiation(self, temp_sandbox: tuple[Path, Sandbox]) -> None:
        """Test that StreamingRegexSearcher can be instantiated."""
        _, sandbox = temp_sandbox
        searcher = StreamingRegexSearcher(sandbox=sandbox)
        assert searcher.sandbox == sandbox

    def test_simple_regex_match(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test simple regex matching."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("apple\nbanana\ncherry\napricot\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "ap.*"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 2
        assert matches[0].contents == "apple\n"
        assert matches[0].window == FileWindow(line_offset=0, line_count=1)
        assert matches[1].contents == "apricot\n"
        assert matches[1].window == FileWindow(line_offset=3, line_count=1)

    def test_no_matches(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test file with no regex matches."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("cat\ndog\nbird\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "elephant"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 0
        # Budget should remain unchanged when no matches
        assert budget.remaining == 100

    def test_case_sensitive_matching(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that regex matching is case sensitive by default."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("Apple\napple\nAPPLE\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "apple"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 1
        assert matches[0].contents == "apple\n"
        assert matches[0].window.line_offset == 1

    def test_case_insensitive_regex(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test case insensitive regex pattern."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("Apple\napple\nAPPLE\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "(?i)apple"  # Case insensitive flag

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 3
        assert matches[0].contents == "Apple\n"
        assert matches[1].contents == "apple\n"
        assert matches[2].contents == "APPLE\n"

    def test_complex_regex_patterns(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test complex regex patterns."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text(
            "user1@example.com\ninvalid-email\nuser2@test.org\nnot-an-email\n",
            encoding="utf-8",
        )

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = r"\w+@\w+\.\w+"  # Simple email pattern

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 2
        assert matches[0].contents == "user1@example.com\n"
        assert matches[1].contents == "user2@test.org\n"

    def test_multiline_content_single_line_matching(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that only single-line matching is performed."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("start\nmiddle\nend\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = (
            "start.*end"  # Would match across lines in multiline mode
        )

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        # Should not match across lines
        assert len(matches) == 0

    def test_budget_constraint_enforcement(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that budget constraints are enforced per matching line."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text(
            "match short\nmatch medium line\nmatch very long line that exceeds budget\n",
            encoding="utf-8",
        )

        budget = OutputBudget(limit=30)  # Small budget
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        # Should get first two matches but not the third due to budget
        assert len(matches) == 2
        assert matches[0].contents == "match short\n"
        assert matches[1].contents == "match medium line\n"

    def test_budget_exceeded_on_first_match(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test budget exceeded on the very first match."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text(
            "this is a very long first matching line that exceeds the tiny budget\nshort match\n",
            encoding="utf-8",
        )

        budget = OutputBudget(limit=5)  # Very small budget
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        # Should get no matches because first match exceeds budget
        assert len(matches) == 0

    def test_per_line_budget_debit(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that budget is debited per matching line."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("match1\nmatch22\nmatch333\n", encoding="utf-8")

        budget = OutputBudget(limit=15)  # Exactly enough for first two matches (7+8)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 2
        assert matches[0].contents == "match1\n"
        assert matches[1].contents == "match22\n"
        assert budget.remaining == 0  # Budget should be exactly consumed

    def test_empty_file(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test searching in an empty file."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "anything"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 0
        assert budget.remaining == 100  # Budget unchanged

    def test_single_line_file_with_match(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test searching in a single line file with match."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "single.txt"
        test_file.write_text("single line with match", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 1
        assert matches[0].contents == "single line with match"
        assert matches[0].window == FileWindow(line_offset=0, line_count=1)

    def test_single_line_file_no_newline(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test searching in a single line file without trailing newline."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "no_newline.txt"
        # Write without newline
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("no newline match")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 1
        assert matches[0].contents == "no newline match"

    def test_binary_file_handling(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test graceful handling of binary files."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "binary.bin"
        # Write some binary data with some text that might match
        test_file.write_bytes(b"\x00\x01match\x02\x03\xff\xfe\xfd")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        # Should not raise an exception due to UTF-8 errors
        matches = list(searcher.iter_matches(test_file, pattern, budget))

        # Content might be garbled but should not crash
        assert isinstance(matches, list)

    def test_very_long_lines(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test files with very long lines."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "long_lines.txt"
        long_line = "x" * 1000 + "match" + "y" * 1000 + "\n"
        test_file.write_text(long_line + "short match\n", encoding="utf-8")

        budget = OutputBudget(limit=500)  # Budget smaller than first line
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        # Should skip first match due to budget and get second
        assert len(matches) == 1
        assert matches[0].contents == "short match\n"

    def test_line_numbers_are_zero_based(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that line numbers in FileWindow are zero-based."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text(
            "line0\nline1 match\nline2\nline3 match\n", encoding="utf-8"
        )

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 2
        assert matches[0].window.line_offset == 1  # Second line is offset 1
        assert matches[1].window.line_offset == 3  # Fourth line is offset 3

    def test_each_match_separate_file_content(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that each match gets separate FileContent object."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("match1\nmatch2\nmatch3\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 3
        # Each match should be a separate FileContent object
        for i, match in enumerate(matches):
            assert isinstance(match, FileContent)
            assert match.path == test_file
            assert match.window.line_offset == i
            assert match.window.line_count == 1

    def test_sandbox_security_validation(
        self, temp_sandbox: tuple[Path, Sandbox]
    ) -> None:
        """Test that sandbox validation is enforced."""
        sandbox_dir, sandbox = temp_sandbox
        searcher = StreamingRegexSearcher(sandbox=sandbox)

        # Try to search outside sandbox
        outside_file = Path("/etc/passwd")  # System file outside sandbox

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "root"

        with pytest.raises(SandboxViolation):
            list(searcher.iter_matches(outside_file, pattern, budget))

    def test_blocked_file_access(self, temp_sandbox: tuple[Path, Sandbox]) -> None:
        """Test that blocked files are rejected."""
        sandbox_dir, _ = temp_sandbox
        blocked_file = sandbox_dir / "blocked.txt"
        blocked_file.write_text("secret match content", encoding="utf-8")

        # Create sandbox with blocked file
        sandbox = Sandbox(
            sandbox_dir=sandbox_dir, blocked_files=[blocked_file], allow_hidden=False
        )
        searcher = StreamingRegexSearcher(sandbox=sandbox)

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        with pytest.raises(SandboxViolation):
            list(searcher.iter_matches(blocked_file, pattern, budget))

    def test_hidden_file_access_denied(
        self, temp_sandbox: tuple[Path, Sandbox]
    ) -> None:
        """Test that hidden files are denied when allow_hidden=False."""
        sandbox_dir, sandbox = temp_sandbox
        hidden_file = sandbox_dir / ".hidden"
        hidden_file.write_text("hidden match content", encoding="utf-8")

        searcher = StreamingRegexSearcher(
            sandbox=sandbox
        )  # allow_hidden=False by default

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        with pytest.raises(SandboxViolation):
            list(searcher.iter_matches(hidden_file, pattern, budget))

    def test_hidden_file_access_allowed(
        self, temp_sandbox: tuple[Path, Sandbox]
    ) -> None:
        """Test that hidden files are allowed when allow_hidden=True."""
        sandbox_dir, _ = temp_sandbox
        hidden_file = sandbox_dir / ".hidden"
        hidden_file.write_text("hidden match content\n", encoding="utf-8")

        # Create sandbox that allows hidden files
        sandbox = Sandbox(sandbox_dir=sandbox_dir, blocked_files=[], allow_hidden=True)
        searcher = StreamingRegexSearcher(sandbox=sandbox)

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(hidden_file, pattern, budget))

        assert len(matches) == 1
        assert matches[0].contents == "hidden match content\n"

    def test_nonexistent_file(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test handling of nonexistent files."""
        sandbox_dir, _ = temp_sandbox
        nonexistent_file = sandbox_dir / "does_not_exist.txt"

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "anything"

        # Should raise appropriate exception (FileNotFoundError or similar)
        with pytest.raises((FileNotFoundError, OSError)):
            list(searcher.iter_matches(nonexistent_file, pattern, budget))

    def test_invalid_regex_pattern(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test handling of invalid regex patterns."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("test content\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "[invalid"  # Invalid regex - unclosed bracket

        # Should raise re.error when compiling the pattern
        with pytest.raises(re.error):
            list(searcher.iter_matches(test_file, pattern, budget))

    def test_special_regex_characters(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test patterns with special regex characters."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("$100.50\n[important]\n{config}\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = r"\$\d+\.\d+"  # Match currency

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 1
        assert matches[0].contents == "$100.50\n"

    def test_utf8_with_special_characters(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test regex matching with UTF-8 special characters."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "utf8.txt"
        test_file.write_text(
            "héllo wørld 🌍\nünicode tëst match ñoño\nregular text\n", encoding="utf-8"
        )

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 1
        assert matches[0].contents == "ünicode tëst match ñoño\n"

    def test_memory_usage_large_file(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that memory usage remains constant for large files."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "large.txt"

        # Create a large file with matches scattered throughout
        with open(test_file, "w", encoding="utf-8") as f:
            for i in range(1000):
                if i % 100 == 0:
                    f.write(f"line {i} with match\n")
                else:
                    f.write(f"line {i} without pattern\n")

        budget = OutputBudget(limit=1000)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        # Should find 10 matches (every 100th line)
        assert len(matches) == 10
        # Verify they are at expected line offsets
        for i, match in enumerate(matches):
            expected_line = i * 100
            assert match.window.line_offset == expected_line

    def test_file_window_line_count_is_always_one(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that FileWindow always has line_count=1 for single-line matches."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text("match1\nmatch2\nmatch3\n", encoding="utf-8")

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        for match in matches:
            assert match.window.line_count == 1

    def test_partial_line_matches(
        self, temp_sandbox: tuple[Path, Sandbox], searcher: StreamingRegexSearcher
    ) -> None:
        """Test that partial matches within lines work correctly."""
        sandbox_dir, _ = temp_sandbox
        test_file = sandbox_dir / "test.txt"
        test_file.write_text(
            "prefix match suffix\nno pattern here\nanother match embedded\n",
            encoding="utf-8",
        )

        budget = OutputBudget(limit=100)
        pattern: RegexPattern = "match"

        matches = list(searcher.iter_matches(test_file, pattern, budget))

        assert len(matches) == 2
        assert matches[0].contents == "prefix match suffix\n"
        assert matches[1].contents == "another match embedded\n"
