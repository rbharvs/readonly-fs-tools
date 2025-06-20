"""Test sandbox security system."""

import os
import tempfile
from pathlib import Path

import pytest

from glob_grep_glance._sandbox import Sandbox, SandboxViolation


class TestSandboxViolation:
    """Test SandboxViolation exception."""

    def test_sandbox_violation_is_runtime_error(self) -> None:
        """Test that SandboxViolation inherits from RuntimeError."""
        exc = SandboxViolation("test message")
        assert isinstance(exc, RuntimeError)
        assert str(exc) == "test message"

    def test_sandbox_violation_without_message(self) -> None:
        """Test SandboxViolation can be raised without a message."""
        exc = SandboxViolation()
        assert isinstance(exc, RuntimeError)


class TestSandboxInitialization:
    """Test Sandbox model initialization and path resolution."""

    def test_sandbox_basic_initialization(self) -> None:
        """Test basic sandbox initialization."""
        sandbox_dir = Path("/tmp/test")
        blocked_files = [Path("blocked.txt")]

        sandbox = Sandbox(
            sandbox_dir=sandbox_dir, blocked_files=blocked_files, allow_hidden=False
        )

        assert sandbox.sandbox_dir == sandbox_dir
        assert len(sandbox.blocked_files) == 1
        assert not sandbox.allow_hidden

    def test_sandbox_default_allow_hidden(self) -> None:
        """Test that allow_hidden defaults to False."""
        sandbox = Sandbox(sandbox_dir=Path("/tmp/test"), blocked_files=[])
        assert not sandbox.allow_hidden

    def test_sandbox_allow_hidden_true(self) -> None:
        """Test setting allow_hidden to True."""
        sandbox = Sandbox(
            sandbox_dir=Path("/tmp/test"), blocked_files=[], allow_hidden=True
        )
        assert sandbox.allow_hidden

    def test_blocked_files_resolved_to_absolute_paths(self) -> None:
        """Test that blocked files are resolved to absolute paths during initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a test file to block
            blocked_file = temp_path / "blocked.txt"
            blocked_file.write_text("blocked content")

            # Initialize sandbox with relative path
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                sandbox = Sandbox(
                    sandbox_dir=temp_path,
                    blocked_files=[Path("blocked.txt")],  # Relative path
                )

                # Should be resolved to absolute path
                assert len(sandbox.blocked_files) == 1
                assert sandbox.blocked_files[0].is_absolute()
                assert sandbox.blocked_files[0] == blocked_file.resolve()
            finally:
                os.chdir(original_cwd)

    def test_multiple_blocked_files_resolution(self) -> None:
        """Test that multiple blocked files are all resolved."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple files
            file1 = temp_path / "blocked1.txt"
            file2 = temp_path / "blocked2.txt"
            file1.write_text("content1")
            file2.write_text("content2")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[file1, file2])

            assert len(sandbox.blocked_files) == 2
            resolved_paths = {p.resolve() for p in sandbox.blocked_files}
            assert file1.resolve() in resolved_paths
            assert file2.resolve() in resolved_paths


class TestPathTraversalPrevention:
    """Test path traversal attack prevention."""

    def test_parent_directory_traversal_blocked(self) -> None:
        """Test that ../ path traversal is blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Try to access parent directory
            parent_path = temp_path / ".." / "some_file.txt"
            assert not sandbox.is_allowed(parent_path)

            with pytest.raises(SandboxViolation):
                sandbox.require_allowed(parent_path)

    def test_absolute_path_outside_sandbox_blocked(self) -> None:
        """Test that absolute paths outside sandbox are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Try to access absolute path outside sandbox
            outside_path = Path("/etc/passwd")
            assert not sandbox.is_allowed(outside_path)

            with pytest.raises(SandboxViolation):
                sandbox.require_allowed(outside_path)

    def test_path_within_sandbox_allowed(self) -> None:
        """Test that paths within sandbox are allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Access file within sandbox
            within_path = temp_path / "allowed_file.txt"
            assert sandbox.is_allowed(within_path)

            # Should not raise exception
            result_path = sandbox.require_allowed(within_path)
            assert result_path == within_path

    def test_nested_directory_traversal_blocked(self) -> None:
        """Test that nested directory traversal attempts are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Try nested traversal: subdir/../../../etc/passwd
            traversal_path = (
                temp_path / "subdir" / ".." / ".." / ".." / "etc" / "passwd"
            )
            assert not sandbox.is_allowed(traversal_path)

            with pytest.raises(SandboxViolation):
                sandbox.require_allowed(traversal_path)


class TestSymlinkDetection:
    """Test symlink detection and blocking."""

    @pytest.mark.skipif(os.name == "nt", reason="Symlink tests not reliable on Windows")
    def test_symlink_outside_sandbox_blocked(self) -> None:
        """Test that symlinks pointing outside sandbox are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Create symlink pointing outside sandbox
            symlink_path = temp_path / "evil_symlink"
            target_path = Path("/etc/passwd")

            try:
                symlink_path.symlink_to(target_path)

                assert not sandbox.is_allowed(symlink_path)

                with pytest.raises(SandboxViolation):
                    sandbox.require_allowed(symlink_path)
            except (OSError, NotImplementedError):
                pytest.skip("Cannot create symlinks in this environment")

    @pytest.mark.skipif(os.name == "nt", reason="Symlink tests not reliable on Windows")
    def test_symlink_within_sandbox_allowed(self) -> None:
        """Test that symlinks pointing within sandbox are allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Create target file and symlink within sandbox
            target_file = temp_path / "target.txt"
            target_file.write_text("target content")

            symlink_path = temp_path / "good_symlink"

            try:
                symlink_path.symlink_to(target_file)

                assert sandbox.is_allowed(symlink_path)

                result_path = sandbox.require_allowed(symlink_path)
                assert result_path == symlink_path
            except (OSError, NotImplementedError):
                pytest.skip("Cannot create symlinks in this environment")


class TestHiddenFileAccess:
    """Test hidden file access control."""

    def test_hidden_file_blocked_by_default(self) -> None:
        """Test that hidden files are blocked when allow_hidden=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            hidden_file = temp_path / ".hidden_file"
            assert not sandbox.is_allowed(hidden_file)

            with pytest.raises(SandboxViolation):
                sandbox.require_allowed(hidden_file)

    def test_hidden_file_allowed_when_enabled(self) -> None:
        """Test that hidden files are allowed when allow_hidden=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(
                sandbox_dir=temp_path, blocked_files=[], allow_hidden=True
            )

            hidden_file = temp_path / ".hidden_file"
            assert sandbox.is_allowed(hidden_file)

            result_path = sandbox.require_allowed(hidden_file)
            assert result_path == hidden_file

    def test_hidden_directory_blocked_by_default(self) -> None:
        """Test that files in hidden directories are blocked when allow_hidden=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            hidden_dir_file = temp_path / ".hidden_dir" / "file.txt"
            assert not sandbox.is_allowed(hidden_dir_file)

            with pytest.raises(SandboxViolation):
                sandbox.require_allowed(hidden_dir_file)

    def test_hidden_directory_allowed_when_enabled(self) -> None:
        """Test that files in hidden directories are allowed when allow_hidden=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(
                sandbox_dir=temp_path, blocked_files=[], allow_hidden=True
            )

            hidden_dir_file = temp_path / ".hidden_dir" / "file.txt"
            assert sandbox.is_allowed(hidden_dir_file)

            result_path = sandbox.require_allowed(hidden_dir_file)
            assert result_path == hidden_dir_file


class TestBlocklistEnforcement:
    """Test blocklist enforcement with various path representations."""

    def test_blocked_file_rejected(self) -> None:
        """Test that blocked files are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            blocked_file = temp_path / "blocked.txt"
            blocked_file.write_text("blocked content")

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[blocked_file])

            assert not sandbox.is_allowed(blocked_file)

            with pytest.raises(SandboxViolation):
                sandbox.require_allowed(blocked_file)

    def test_blocked_file_with_relative_path(self) -> None:
        """Test that blocked files work with relative path representations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            blocked_file = temp_path / "blocked.txt"
            blocked_file.write_text("blocked content")

            sandbox = Sandbox(
                sandbox_dir=temp_path,
                blocked_files=[Path("blocked.txt")],  # Relative path
            )

            # Both absolute and relative references should be blocked
            assert not sandbox.is_allowed(blocked_file)
            assert not sandbox.is_allowed(temp_path / "blocked.txt")

    def test_non_blocked_file_allowed(self) -> None:
        """Test that non-blocked files are allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            blocked_file = temp_path / "blocked.txt"
            allowed_file = temp_path / "allowed.txt"

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[blocked_file])

            assert sandbox.is_allowed(allowed_file)

            result_path = sandbox.require_allowed(allowed_file)
            assert result_path == allowed_file

    def test_multiple_blocked_files(self) -> None:
        """Test that multiple blocked files are all enforced."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            blocked1 = temp_path / "blocked1.txt"
            blocked2 = temp_path / "blocked2.txt"
            allowed = temp_path / "allowed.txt"

            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[blocked1, blocked2])

            assert not sandbox.is_allowed(blocked1)
            assert not sandbox.is_allowed(blocked2)
            assert sandbox.is_allowed(allowed)


class TestEdgeCases:
    """Test edge cases: non-existent files, permission issues, malformed paths."""

    def test_non_existent_file_handling(self) -> None:
        """Test that non-existent files can still be validated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Non-existent file within sandbox should be allowed
            non_existent = temp_path / "does_not_exist.txt"
            assert sandbox.is_allowed(non_existent)

            result_path = sandbox.require_allowed(non_existent)
            assert result_path == non_existent

    def test_non_existent_file_outside_sandbox(self) -> None:
        """Test that non-existent files outside sandbox are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Non-existent file outside sandbox should be blocked
            outside_non_existent = Path("/tmp/definitely_does_not_exist_12345.txt")
            assert not sandbox.is_allowed(outside_non_existent)

            with pytest.raises(SandboxViolation):
                sandbox.require_allowed(outside_non_existent)

    def test_empty_path_handling(self) -> None:
        """Test handling of empty or minimal paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Empty path should be handled gracefully
            empty_path = Path("")
            # This should not crash, behavior depends on implementation
            result = sandbox.is_allowed(empty_path)
            assert isinstance(result, bool)

    def test_root_path_handling(self) -> None:
        """Test handling of root path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sandbox = Sandbox(sandbox_dir=temp_path, blocked_files=[])

            # Root path should be blocked
            root_path = Path("/")
            assert not sandbox.is_allowed(root_path)

            with pytest.raises(SandboxViolation):
                sandbox.require_allowed(root_path)

    def test_sandbox_dir_does_not_need_to_exist(self) -> None:
        """Test that sandbox_dir doesn't need to exist for initialization."""
        non_existent_sandbox = Path("/tmp/does_not_exist_sandbox_12345")

        # Should not raise exception during initialization
        sandbox = Sandbox(sandbox_dir=non_existent_sandbox, blocked_files=[])

        assert sandbox.sandbox_dir == non_existent_sandbox

    def test_blocked_files_do_not_need_to_exist(self) -> None:
        """Test that blocked files don't need to exist for initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            non_existent_blocked = Path("/tmp/does_not_exist_blocked_12345.txt")

            # Should not raise exception during initialization
            sandbox = Sandbox(
                sandbox_dir=temp_path, blocked_files=[non_existent_blocked]
            )

            # The non-existent blocked file should still be in the blocklist
            assert len(sandbox.blocked_files) == 1
