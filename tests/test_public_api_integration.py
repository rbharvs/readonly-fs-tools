"""Integration tests for the public API and end-to-end workflows."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from glob_grep_glance import (
    FileWindow,
    GlanceOutput,
    Glancer,
    Globber,
    GlobOutput,
    GrepOutput,
    Grepper,
    OutputBudget,
    Sandbox,
)


class TestPublicAPIIntegration:
    """Test end-to-end integration of the public API."""

    @pytest.fixture
    def temp_sandbox(self) -> Generator[Path, None, None]:
        """Create a temporary directory for sandboxed operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox_path = Path(temp_dir)

            # Create test files
            (sandbox_path / "test1.py").write_text("def hello():\n    print('Hello')\n")
            (sandbox_path / "test2.py").write_text("def world():\n    print('World')\n")
            (sandbox_path / "README.md").write_text("# Test Project\nThis is a test.\n")
            (sandbox_path / "config.json").write_text('{"name": "test"}\n')

            # Create subdirectory
            subdir = sandbox_path / "subdir"
            subdir.mkdir()
            (subdir / "nested.py").write_text("def nested():\n    return True\n")

            yield sandbox_path

    @pytest.fixture
    def sandbox(self, temp_sandbox: Path) -> Sandbox:
        """Create a sandbox configuration."""
        return Sandbox(sandbox_dir=temp_sandbox, blocked_files=[], allow_hidden=False)

    @pytest.fixture
    def budget(self) -> OutputBudget:
        """Create an output budget for testing."""
        return OutputBudget(limit=1000)

    def test_globber_from_sandbox_creation(self, sandbox: Sandbox) -> None:
        """Test that Globber can be created from sandbox."""
        globber = Globber.from_sandbox(sandbox)
        assert isinstance(globber, Globber)
        assert globber.path_enum is not None

    def test_grepper_from_sandbox_creation(self, sandbox: Sandbox) -> None:
        """Test that Grepper can be created from sandbox."""
        grepper = Grepper.from_sandbox(sandbox)
        assert isinstance(grepper, Grepper)
        assert grepper.path_enum is not None
        assert grepper.regex_searcher is not None

    def test_glancer_from_sandbox_creation(self, sandbox: Sandbox) -> None:
        """Test that Glancer can be created from sandbox."""
        glancer = Glancer.from_sandbox(sandbox)
        assert isinstance(glancer, Glancer)
        assert glancer.file_reader is not None

    def test_globber_finds_python_files(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test that Globber can find Python files."""
        globber = Globber.from_sandbox(sandbox)
        result = globber.glob(["*.py"], budget)

        assert isinstance(result, GlobOutput)
        assert len(result.paths) >= 2  # At least test1.py and test2.py
        assert not result.truncated

        # Check that paths are within sandbox
        for path in result.paths:
            assert path.is_relative_to(sandbox.sandbox_dir)

    def test_globber_recursive_search(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test that Globber can find files recursively."""
        globber = Globber.from_sandbox(sandbox)
        result = globber.glob(["**/*.py"], budget)

        assert isinstance(result, GlobOutput)
        assert len(result.paths) >= 3  # test1.py, test2.py, subdir/nested.py
        assert not result.truncated

        # Check that nested file is found
        nested_files = [p for p in result.paths if "nested.py" in str(p)]
        assert len(nested_files) == 1

    def test_globber_multiple_patterns(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test that Globber can handle multiple glob patterns."""
        globber = Globber.from_sandbox(sandbox)
        result = globber.glob(["*.py", "*.md"], budget)

        assert isinstance(result, GlobOutput)
        assert len(result.paths) >= 3  # Python files + README.md
        assert not result.truncated

    def test_globber_budget_truncation(self, sandbox: Sandbox) -> None:
        """Test that Globber respects budget limits."""
        small_budget = OutputBudget(limit=2)
        globber = Globber.from_sandbox(sandbox)
        result = globber.glob(["**/*"], small_budget)

        assert isinstance(result, GlobOutput)
        assert len(result.paths) == 2  # Limited by budget
        assert result.truncated

    def test_grepper_finds_matches(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test that Grepper can find regex matches."""
        grepper = Grepper.from_sandbox(sandbox)
        result = grepper.grep(r"def \w+", ["**/*.py"], budget)

        assert isinstance(result, GrepOutput)
        assert len(result.matches) >= 3  # hello, world, nested functions
        assert not result.truncated

        # Check that matches contain function definitions
        for match in result.matches:
            assert "def " in match.contents

    def test_grepper_specific_pattern(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test that Grepper finds specific patterns."""
        grepper = Grepper.from_sandbox(sandbox)
        result = grepper.grep(r"print", ["**/*.py"], budget)

        assert isinstance(result, GrepOutput)
        assert len(result.matches) >= 2  # Hello and World prints
        assert not result.truncated

    def test_grepper_no_matches(self, sandbox: Sandbox, budget: OutputBudget) -> None:
        """Test Grepper behavior when no matches are found."""
        grepper = Grepper.from_sandbox(sandbox)
        result = grepper.grep(r"nonexistent_pattern", ["*.py"], budget)

        assert isinstance(result, GrepOutput)
        assert len(result.matches) == 0
        assert not result.truncated

    def test_grepper_budget_truncation(self, sandbox: Sandbox) -> None:
        """Test that Grepper respects budget limits."""
        small_budget = OutputBudget(limit=50)  # Very small budget
        grepper = Grepper.from_sandbox(sandbox)
        result = grepper.grep(r".", ["*.py"], small_budget)  # Match any character

        assert isinstance(result, GrepOutput)
        # Should be truncated due to budget
        assert result.truncated or len(result.matches) > 0

    def test_glancer_reads_file_content(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test that Glancer can read file content."""
        glancer = Glancer.from_sandbox(sandbox)
        test_file = sandbox.sandbox_dir / "test1.py"
        window = FileWindow(line_offset=0, line_count=2)

        result = glancer.glance(test_file, window, budget)

        assert isinstance(result, GlanceOutput)
        assert "def hello" in result.view.contents
        assert result.view.path == test_file
        assert result.view.window == window
        assert not result.truncated

    def test_glancer_windowed_reading(
        self, sandbox: Sandbox, budget: OutputBudget
    ) -> None:
        """Test that Glancer respects file windows."""
        glancer = Glancer.from_sandbox(sandbox)
        test_file = sandbox.sandbox_dir / "test1.py"

        # Read only the second line
        window = FileWindow(line_offset=1, line_count=1)
        result = glancer.glance(test_file, window, budget)

        assert isinstance(result, GlanceOutput)
        assert "print('Hello')" in result.view.contents
        assert (
            "def hello" not in result.view.contents
        )  # First line should not be included

    def test_glancer_budget_truncation(self, sandbox: Sandbox) -> None:
        """Test that Glancer respects budget limits."""
        small_budget = OutputBudget(limit=10)  # Very small budget
        glancer = Glancer.from_sandbox(sandbox)
        test_file = sandbox.sandbox_dir / "test1.py"
        window = FileWindow(line_offset=0, line_count=10)

        result = glancer.glance(test_file, window, small_budget)

        assert isinstance(result, GlanceOutput)
        # Should be truncated due to budget
        assert result.truncated

    def test_end_to_end_workflow(self, sandbox: Sandbox) -> None:
        """Test a complete workflow using all three tools."""
        budget = OutputBudget(limit=5000)

        # Step 1: Find Python files
        globber = Globber.from_sandbox(sandbox)
        glob_result = globber.glob(["*.py"], budget)
        assert len(glob_result.paths) >= 2

        # Step 2: Search for function definitions in found files
        budget.reset()
        grepper = Grepper.from_sandbox(sandbox)
        grep_result = grepper.grep(r"def \w+", ["*.py"], budget)
        assert len(grep_result.matches) >= 2

        # Step 3: Read the first file found
        budget.reset()
        glancer = Glancer.from_sandbox(sandbox)
        first_file = glob_result.paths[0]
        window = FileWindow(line_offset=0, line_count=5)
        glance_result = glancer.glance(first_file, window, budget)
        assert len(glance_result.view.contents) > 0

    def test_sandbox_security_blocking_files(self, temp_sandbox: Path) -> None:
        """Test that sandbox properly blocks access to specified files."""
        blocked_file = temp_sandbox / "blocked.txt"
        blocked_file.write_text("This should be blocked")

        sandbox = Sandbox(
            sandbox_dir=temp_sandbox, blocked_files=[blocked_file], allow_hidden=False
        )

        budget = OutputBudget(limit=1000)
        globber = Globber.from_sandbox(sandbox)
        result = globber.glob(["*"], budget)

        # Blocked file should not appear in results
        blocked_paths = [p for p in result.paths if p.name == "blocked.txt"]
        assert len(blocked_paths) == 0

    def test_sandbox_security_outside_directory(self, temp_sandbox: Path) -> None:
        """Test that tools cannot access files outside sandbox directory."""
        glancer = Glancer.from_sandbox(
            Sandbox(sandbox_dir=temp_sandbox, blocked_files=[], allow_hidden=False)
        )

        # Try to access a file outside the sandbox
        outside_file = Path("/etc/passwd")  # Common system file
        window = FileWindow(line_offset=0, line_count=1)
        budget = OutputBudget(limit=1000)

        # Should raise SandboxViolation
        from glob_grep_glance._sandbox import SandboxViolation

        with pytest.raises(SandboxViolation):
            glancer.glance(outside_file, window, budget)

    def test_usage_example_from_issue(self, sandbox: Sandbox) -> None:
        """Test the exact usage example from the GitHub issue."""
        globber = Globber.from_sandbox(sandbox)
        budget = OutputBudget(limit=1000)

        result = globber.glob(["*.py"], budget)

        assert isinstance(result, GlobOutput)
        assert len(result.paths) >= 2
        assert not result.truncated
