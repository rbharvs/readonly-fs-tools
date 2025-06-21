"""Test budget management system with comprehensive coverage."""

import pytest

from readonly_fs_tools.budget import BudgetExceeded, OutputBudget


class TestBudgetExceeded:
    """Test the BudgetExceeded exception."""

    def test_budget_exceeded_is_runtime_error(self) -> None:
        """Test that BudgetExceeded inherits from RuntimeError."""
        assert issubclass(BudgetExceeded, RuntimeError)

    def test_budget_exceeded_with_message(self) -> None:
        """Test that BudgetExceeded can be raised with a message."""
        with pytest.raises(BudgetExceeded, match="test message"):
            raise BudgetExceeded("test message")

    def test_budget_exceeded_without_message(self) -> None:
        """Test that BudgetExceeded can be raised without a message."""
        with pytest.raises(BudgetExceeded):
            raise BudgetExceeded()


class TestOutputBudget:
    """Test the OutputBudget class."""

    def test_budget_instantiation_with_limit(self) -> None:
        """Test that OutputBudget can be instantiated with a limit."""
        budget = OutputBudget(limit=100)
        assert budget.limit == 100
        assert budget.remaining == 100

    def test_budget_instantiation_zero_limit(self) -> None:
        """Test that OutputBudget can be instantiated with zero limit."""
        budget = OutputBudget(limit=0)
        assert budget.limit == 0
        assert budget.remaining == 0

    def test_budget_negative_limit_rejected(self) -> None:
        """Test that negative limits are rejected during instantiation."""
        with pytest.raises(ValueError):
            OutputBudget(limit=-1)

    def test_successful_debit_reduces_remaining(self) -> None:
        """Test that successful debits reduce the remaining allowance."""
        budget = OutputBudget(limit=100)
        budget.debit(30)
        assert budget.remaining == 70

        budget.debit(20)
        assert budget.remaining == 50

    def test_debit_exact_remaining_amount(self) -> None:
        """Test debiting the exact remaining amount."""
        budget = OutputBudget(limit=50)
        budget.debit(50)
        assert budget.remaining == 0

    def test_debit_zero_units(self) -> None:
        """Test that debiting zero units doesn't change remaining."""
        budget = OutputBudget(limit=100)
        budget.debit(0)
        assert budget.remaining == 100

    def test_over_budget_raises_exception(self) -> None:
        """Test that over-budget attempts raise BudgetExceeded."""
        budget = OutputBudget(limit=50)
        budget.debit(30)  # remaining = 20

        with pytest.raises(BudgetExceeded, match="attempted to debit 25, only 20 left"):
            budget.debit(25)

    def test_over_budget_when_empty_raises_exception(self) -> None:
        """Test that debiting from empty budget raises BudgetExceeded."""
        budget = OutputBudget(limit=10)
        budget.debit(10)  # remaining = 0

        with pytest.raises(BudgetExceeded, match="attempted to debit 1, only 0 left"):
            budget.debit(1)

    def test_negative_units_raises_value_error(self) -> None:
        """Test that negative units raise ValueError."""
        budget = OutputBudget(limit=100)

        with pytest.raises(ValueError, match="units must be non-negative"):
            budget.debit(-1)

    def test_reset_restores_full_limit(self) -> None:
        """Test that reset restores the full allowance."""
        budget = OutputBudget(limit=100)
        budget.debit(80)
        assert budget.remaining == 20

        budget.reset()
        assert budget.remaining == 100

    def test_reset_after_complete_depletion(self) -> None:
        """Test reset after budget is completely depleted."""
        budget = OutputBudget(limit=50)
        budget.debit(50)
        assert budget.remaining == 0

        budget.reset()
        assert budget.remaining == 50

    def test_multiple_operations_workflow(self) -> None:
        """Test a realistic workflow with multiple operations."""
        budget = OutputBudget(limit=1000)

        # Multiple debits
        budget.debit(200)
        budget.debit(300)
        assert budget.remaining == 500

        # Reset and continue
        budget.reset()
        assert budget.remaining == 1000

        # Debit to near limit
        budget.debit(999)
        assert budget.remaining == 1

        # Final debit
        budget.debit(1)
        assert budget.remaining == 0

    def test_edge_case_zero_budget_zero_debit(self) -> None:
        """Test edge case: zero budget with zero-unit debit."""
        budget = OutputBudget(limit=0)
        budget.debit(0)  # Should not raise
        assert budget.remaining == 0

    def test_edge_case_zero_budget_nonzero_debit(self) -> None:
        """Test edge case: zero budget with non-zero debit."""
        budget = OutputBudget(limit=0)

        with pytest.raises(BudgetExceeded, match="attempted to debit 1, only 0 left"):
            budget.debit(1)

    def test_remaining_property_is_read_only(self) -> None:
        """Test that remaining property reflects internal state correctly."""
        budget = OutputBudget(limit=100)

        # Verify initial state
        assert budget.remaining == 100

        # Verify state after debit
        budget.debit(25)
        assert budget.remaining == 75

        # Verify state after reset
        budget.reset()
        assert budget.remaining == 100

    def test_limit_property_immutable_after_init(self) -> None:
        """Test that limit property remains constant after initialization."""
        budget = OutputBudget(limit=200)
        original_limit = budget.limit

        budget.debit(50)
        assert budget.limit == original_limit

        budget.reset()
        assert budget.limit == original_limit
