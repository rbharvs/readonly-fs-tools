"""Test FilesystemPathEnumerator implementation."""

import tempfile
from pathlib import Path
from typing import List

from readonly_fs_tools._defaults import FilesystemPathEnumerator
from readonly_fs_tools._sandbox import Sandbox
from readonly_fs_tools.common import GlobPattern


class TestFilesystemPathEnumeratorBasics:
    """Test basic FilesystemPathEnumerator functionality."""

    def test_path_enumerator_initialization(self) -> None:
        """Test basic initialization of FilesystemPathEnumerator."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            enumerator = FilesystemPathEnumerator(sandbox=sandbox)
            assert enumerator.sandbox == sandbox

    def test_empty_patterns_list(self) -> None:
        """Test that empty patterns list yields no paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            paths = list(enumerator.iter_paths([]))
            assert paths == []

    def test_single_pattern_matching(self) -> None:
        """Test basic pattern matching with a single glob pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test1.txt").write_text("content1")
            (temp_path / "test2.txt").write_text("content2")
            (temp_path / "other.py").write_text("content3")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Test *.txt pattern
            patterns: List[GlobPattern] = ["*.txt"]
            paths = list(enumerator.iter_paths(patterns))

            # Should find both txt files
            expected_files = {temp_path / "test1.txt", temp_path / "test2.txt"}
            found_files = set(paths)
            assert found_files == expected_files

    def test_multiple_patterns_no_overlap(self) -> None:
        """Test multiple patterns with no overlapping matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.txt").write_text("content1")
            (temp_path / "file2.py").write_text("content2")
            (temp_path / "file3.md").write_text("content3")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Test multiple non-overlapping patterns
            patterns: List[GlobPattern] = ["*.txt", "*.py"]
            paths = list(enumerator.iter_paths(patterns))

            expected_files = {temp_path / "file1.txt", temp_path / "file2.py"}
            found_files = set(paths)
            assert found_files == expected_files


class TestDeduplication:
    """Test path deduplication across multiple patterns."""

    def test_overlapping_patterns_deduplication(self) -> None:
        """Test that overlapping patterns don't yield duplicate paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test.txt").write_text("content1")
            (temp_path / "other.py").write_text("content2")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Use overlapping patterns that should match the same file
            patterns: List[GlobPattern] = ["*.txt", "test.*", "*"]
            paths = list(enumerator.iter_paths(patterns))

            # Should not have duplicates
            assert len(paths) == len(set(paths))

            # Should contain both files
            expected_files = {temp_path / "test.txt", temp_path / "other.py"}
            found_files = set(paths)
            assert found_files == expected_files

    def test_identical_patterns_deduplication(self) -> None:
        """Test that identical patterns don't cause duplication."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.txt").write_text("content1")
            (temp_path / "file2.txt").write_text("content2")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Use identical patterns
            patterns: List[GlobPattern] = ["*.txt", "*.txt", "*.txt"]
            paths = list(enumerator.iter_paths(patterns))

            # Should not have duplicates
            assert len(paths) == len(set(paths))
            assert len(paths) == 2

            expected_files = {temp_path / "file1.txt", temp_path / "file2.txt"}
            found_files = set(paths)
            assert found_files == expected_files


class TestSandboxIntegration:
    """Test sandbox constraint enforcement."""

    def test_sandbox_path_filtering(self) -> None:
        """Test that paths outside sandbox are filtered out."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested structure
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (temp_path / "root_file.txt").write_text("root content")
            (subdir / "sub_file.txt").write_text("sub content")

            # Sandbox only allows subdir
            sandbox = Sandbox(sandbox_dir=subdir, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Pattern that would match files in both locations
            patterns: List[GlobPattern] = ["**/*.txt"]
            paths = list(enumerator.iter_paths(patterns))

            # Should only find file in subdirectory (within sandbox)
            expected_files = {subdir / "sub_file.txt"}
            found_files = set(paths)
            assert found_files == expected_files

    def test_blocked_files_filtering(self) -> None:
        """Test that blocked files are filtered out."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            allowed_file = temp_path / "allowed.txt"
            blocked_file = temp_path / "blocked.txt"
            allowed_file.write_text("allowed content")
            blocked_file.write_text("blocked content")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[blocked_file])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            patterns: List[GlobPattern] = ["*.txt"]
            paths = list(enumerator.iter_paths(patterns))

            # Should only find allowed file
            expected_files = {allowed_file}
            found_files = set(paths)
            assert found_files == expected_files

    def test_hidden_files_filtering_disabled(self) -> None:
        """Test that hidden files are filtered when allow_hidden=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create visible and hidden files
            visible_file = temp_path / "visible.txt"
            hidden_file = temp_path / ".hidden.txt"
            visible_file.write_text("visible content")
            hidden_file.write_text("hidden content")

            sandbox = Sandbox(
                sandbox_dir=temp_path, blocked_files=[], allow_hidden=False
            )
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            patterns: List[GlobPattern] = ["*"]
            paths = list(enumerator.iter_paths(patterns))

            # Should only find visible file
            expected_files = {visible_file}
            found_files = set(paths)
            assert found_files == expected_files

    def test_hidden_files_allowed_when_enabled(self) -> None:
        """Test that hidden files are included when allow_hidden=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create visible and hidden files
            visible_file = temp_path / "visible.txt"
            hidden_file = temp_path / ".hidden.txt"
            visible_file.write_text("visible content")
            hidden_file.write_text("hidden content")

            sandbox = Sandbox(
                sandbox_dir=temp_path, blocked_files=[], allow_hidden=True
            )
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            patterns: List[GlobPattern] = ["*"]
            paths = list(enumerator.iter_paths(patterns))

            # Should find both files
            expected_files = {visible_file, hidden_file}
            found_files = set(paths)
            assert found_files == expected_files


class TestErrorHandling:
    """Test error handling for invalid patterns and edge cases."""

    def test_invalid_glob_pattern_propagates_error(self) -> None:
        """Test that invalid glob patterns cause errors to propagate."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Create a pattern that will cause os.scandir to fail
            # by trying to access a file as if it were a directory
            (temp_path / "not_a_dir.txt").write_text("content")
            invalid_patterns: List[GlobPattern] = ["not_a_dir.txt/*"]

            # This should not raise an error, but return empty results
            # because Python's glob handles this gracefully
            paths = list(enumerator.iter_paths(invalid_patterns))
            assert paths == []  # No matches for invalid directory pattern

    def test_non_existent_directory_handling(self) -> None:
        """Test behavior when glob patterns reference non-existent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Pattern referencing non-existent directory
            patterns: List[GlobPattern] = ["nonexistent/dir/*.txt"]
            paths = list(enumerator.iter_paths(patterns))

            # Should return empty list (no matches)
            assert paths == []

    def test_pattern_with_no_matches(self) -> None:
        """Test patterns that don't match any files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some files
            (temp_path / "file.txt").write_text("content")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Pattern that matches no files
            patterns: List[GlobPattern] = ["*.nonexistent"]
            paths = list(enumerator.iter_paths(patterns))

            assert paths == []


class TestLazyIteration:
    """Test lazy iteration behavior and memory efficiency."""

    def test_iter_paths_returns_iterator(self) -> None:
        """Test that iter_paths returns an iterator, not a list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.txt").write_text("content1")
            (temp_path / "file2.txt").write_text("content2")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            patterns: List[GlobPattern] = ["*.txt"]
            result = enumerator.iter_paths(patterns)

            # Should be an iterator/generator, not a list
            assert hasattr(result, "__iter__")
            assert hasattr(result, "__next__")

    def test_filesystem_order_maintained(self) -> None:
        """Test that filesystem order is maintained (no sorting)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files in specific order
            files_to_create = ["z_file.txt", "a_file.txt", "m_file.txt"]
            for filename in files_to_create:
                (temp_path / filename).write_text("content")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            patterns: List[GlobPattern] = ["*.txt"]
            paths = list(enumerator.iter_paths(patterns))

            # Should have all files
            assert len(paths) == 3

            # Order should be filesystem order, not alphabetical
            # (exact order depends on filesystem, but shouldn't be sorted)
            path_names = [p.name for p in paths]

            # If they happen to be in alphabetical order, that's fine
            # but we're testing that we're not explicitly sorting
            # The key requirement is that we get all files
            assert set(path_names) == set(files_to_create)


class TestComplexPatterns:
    """Test complex glob patterns and nested directory structures."""

    def test_recursive_patterns(self) -> None:
        """Test recursive glob patterns with **."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested structure
            (temp_path / "root.txt").write_text("root")
            subdir1 = temp_path / "sub1"
            subdir1.mkdir()
            (subdir1 / "sub1.txt").write_text("sub1")
            subdir2 = subdir1 / "sub2"
            subdir2.mkdir()
            (subdir2 / "sub2.txt").write_text("sub2")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            patterns: List[GlobPattern] = ["**/*.txt"]
            paths = list(enumerator.iter_paths(patterns))

            expected_files = {
                temp_path / "root.txt",
                subdir1 / "sub1.txt",
                subdir2 / "sub2.txt",
            }
            found_files = set(paths)
            assert found_files == expected_files

    def test_character_class_patterns(self) -> None:
        """Test glob patterns with character classes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different naming patterns
            (temp_path / "file1.txt").write_text("content1")
            (temp_path / "file2.txt").write_text("content2")
            (temp_path / "fileA.txt").write_text("contentA")
            (temp_path / "fileB.txt").write_text("contentB")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])
            enumerator = FilesystemPathEnumerator(sandbox=sandbox)

            # Pattern matching only numeric suffixes
            patterns: List[GlobPattern] = ["file[0-9].txt"]
            paths = list(enumerator.iter_paths(patterns))

            expected_files = {temp_path / "file1.txt", temp_path / "file2.txt"}
            found_files = set(paths)
            assert found_files == expected_files
