from __future__ import annotations

from pydantic import BaseModel, NonNegativeInt


class BudgetExceeded(RuntimeError):
    """Raised when an operation tries to debit more units than remain."""


class OutputBudget(BaseModel):
    """Mutable allowance tracker with runtime validation."""

    limit: NonNegativeInt  # fixed upper bound
    _remaining: int = 0  # private mutable state

    # ----- pydantic v2 -------------------------------------------------
    def model_post_init(self, __ctx: object) -> None:
        self._remaining = int(self.limit)

    # ------------------------------------------------------------------
    def debit(self, units: int) -> None:
        """Subtract units from the allowance, enforcing runtime checks."""
        if units < 0:
            raise ValueError("units must be non-negative")
        if units > self._remaining:
            raise BudgetExceeded(
                f"attempted to debit {units}, only {self._remaining} left"
            )
        self._remaining -= units

    @property
    def remaining(self) -> int:
        """Current unused allowance."""
        return self._remaining

    def reset(self) -> None:
        """Restore full allowance."""
        self._remaining = int(self.limit)
