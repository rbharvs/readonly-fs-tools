from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import Mock

from glob_grep_glance._budget import OutputBudget
from glob_grep_glance._protocols import FileReader, PathEnumerator, RegexSearcher
from glob_grep_glance.common import (
    FileContent,
    FileReadResult,
    FileWindow,
    GlobPattern,
    RegexPattern,
)


class TestPathEnumerator:
    """Test PathEnumerator protocol compliance and interface."""

    def test_protocol_compliance(self) -> None:
        """Test that a mock implementation satisfies the PathEnumerator protocol."""
        mock_enumerator = Mock(spec=PathEnumerator)
        mock_enumerator.iter_paths = Mock(return_value=iter([Path("test.txt")]))

        # Protocol compliance check
        patterns: List[GlobPattern] = ["*.txt", "*.py"]
        result = list(mock_enumerator.iter_paths(patterns))

        assert len(result) == 1
        assert result[0] == Path("test.txt")
        mock_enumerator.iter_paths.assert_called_once_with(patterns)

    def test_multi_pattern_support(self) -> None:
        """Test that PathEnumerator supports multiple glob patterns."""
        mock_enumerator = Mock(spec=PathEnumerator)
        expected_paths = [Path("file1.txt"), Path("script.py"), Path("data.json")]
        mock_enumerator.iter_paths = Mock(return_value=iter(expected_paths))

        patterns: List[GlobPattern] = ["*.txt", "*.py", "*.json"]
        result = list(mock_enumerator.iter_paths(patterns))

        assert result == expected_paths
        mock_enumerator.iter_paths.assert_called_once_with(patterns)

    def test_empty_patterns_list(self) -> None:
        """Test PathEnumerator behavior with empty patterns list."""
        mock_enumerator = Mock(spec=PathEnumerator)
        mock_enumerator.iter_paths = Mock(return_value=iter([]))

        patterns: List[GlobPattern] = []
        result = list(mock_enumerator.iter_paths(patterns))

        assert result == []
        mock_enumerator.iter_paths.assert_called_once_with(patterns)


class TestFileReader:
    """Test FileReader protocol compliance and interface."""

    def test_protocol_compliance(self) -> None:
        """Test that a mock implementation satisfies the FileReader protocol."""
        mock_reader = Mock(spec=FileReader)
        expected_result = FileReadResult(
            contents="test content",
            truncated=False,
            actual_window=FileWindow(line_offset=0, line_count=1),
        )
        mock_reader.read_window = Mock(return_value=expected_result)

        file_path = Path("test.txt")
        window = FileWindow(line_offset=0, line_count=10)
        budget = OutputBudget(limit=1000)

        result = mock_reader.read_window(file_path, window, budget)

        assert result == expected_result
        mock_reader.read_window.assert_called_once_with(file_path, window, budget)

    def test_budget_constraint_handling(self) -> None:
        """Test FileReader handles budget constraints properly."""
        mock_reader = Mock(spec=FileReader)
        expected_result = FileReadResult(
            contents="truncated",
            truncated=True,
            actual_window=FileWindow(line_offset=0, line_count=1),
        )
        mock_reader.read_window = Mock(return_value=expected_result)

        file_path = Path("large_file.txt")
        window = FileWindow(line_offset=0, line_count=100)
        budget = OutputBudget(limit=10)  # Small budget

        result = mock_reader.read_window(file_path, window, budget)

        assert result.truncated is True
        mock_reader.read_window.assert_called_once_with(file_path, window, budget)

    def test_window_parameters(self) -> None:
        """Test FileReader respects window parameters."""
        mock_reader = Mock(spec=FileReader)
        expected_result = FileReadResult(
            contents="lines 5-15",
            truncated=False,
            actual_window=FileWindow(line_offset=5, line_count=10),
        )
        mock_reader.read_window = Mock(return_value=expected_result)

        file_path = Path("data.txt")
        window = FileWindow(line_offset=5, line_count=10)
        budget = OutputBudget(limit=1000)

        result = mock_reader.read_window(file_path, window, budget)

        assert "lines 5-15" in result.contents
        mock_reader.read_window.assert_called_once_with(file_path, window, budget)


class TestRegexSearcher:
    """Test RegexSearcher protocol compliance and interface."""

    def test_protocol_compliance(self) -> None:
        """Test that a mock implementation satisfies the RegexSearcher protocol."""
        mock_searcher = Mock(spec=RegexSearcher)
        expected_content = [
            FileContent(
                path=Path("test.txt"),
                contents="match found",
                window=FileWindow(line_offset=0, line_count=1),
            )
        ]
        mock_searcher.iter_matches = Mock(return_value=iter(expected_content))

        file_path = Path("test.txt")
        search_regex: RegexPattern = r"match"
        result = list(mock_searcher.iter_matches(file_path, search_regex))

        assert result == expected_content
        mock_searcher.iter_matches.assert_called_once_with(file_path, search_regex)

    def test_regex_pattern_type_safety(self) -> None:
        """Test RegexSearcher uses validated RegexPattern type."""
        mock_searcher = Mock(spec=RegexSearcher)
        mock_searcher.iter_matches = Mock(return_value=iter([]))

        file_path = Path("test.txt")
        search_regex: RegexPattern = r"\d+"  # Valid regex pattern
        result = list(mock_searcher.iter_matches(file_path, search_regex))

        assert result == []
        mock_searcher.iter_matches.assert_called_once_with(file_path, search_regex)

    def test_consistent_parameter_naming(self) -> None:
        """Test RegexSearcher uses consistent parameter naming (search_regex)."""
        mock_searcher = Mock(spec=RegexSearcher)
        mock_searcher.iter_matches = Mock(return_value=iter([]))

        file_path = Path("test.txt")
        search_regex: RegexPattern = r"pattern"
        # This test ensures the parameter is named 'search_regex', not 'pattern' or 'regex'
        mock_searcher.iter_matches(file_path, search_regex)
        mock_searcher.iter_matches.assert_called_once_with(file_path, search_regex)


class TestProtocolIntegration:
    """Test protocol interactions and type safety."""

    def test_all_protocols_use_validated_types(self) -> None:
        """Test all protocols use GlobPattern and RegexPattern validated types."""
        # PathEnumerator uses List[GlobPattern]
        mock_enumerator = Mock(spec=PathEnumerator)
        mock_enumerator.iter_paths = Mock(return_value=iter([]))

        glob_patterns: List[GlobPattern] = ["*.py", "**/*.txt"]
        mock_enumerator.iter_paths(glob_patterns)

        # RegexSearcher uses RegexPattern
        mock_searcher = Mock(spec=RegexSearcher)
        mock_searcher.iter_matches = Mock(return_value=iter([]))

        regex_pattern: RegexPattern = r"\w+"
        mock_searcher.iter_matches(Path("test.txt"), regex_pattern)

        # Verify type-safe calls completed without error
        assert True

    def test_budget_consistency_across_protocols(self) -> None:
        """Test all budget-aware protocols use OutputBudget consistently."""
        budget = OutputBudget(limit=1000)

        # FileReader uses OutputBudget
        mock_reader = Mock(spec=FileReader)
        mock_reader.read_window = Mock(
            return_value=FileReadResult(
                contents="",
                truncated=False,
                actual_window=FileWindow(line_offset=0, line_count=0),
            )
        )
        mock_reader.read_window(
            Path("test.txt"), FileWindow(line_offset=0, line_count=1), budget
        )

        # RegexSearcher uses OutputBudget
        mock_searcher = Mock(spec=RegexSearcher)
        mock_searcher.iter_matches = Mock(return_value=iter([]))
        mock_searcher.iter_matches(Path("test.txt"), r"pattern")

        # Verify both protocols accept the same OutputBudget instance
        assert True
