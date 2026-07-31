# SPDX-License-Identifier: MIT
# Copyright: 2025-2026 Paillat-dev
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LoadingStep:
    """Represents a step in the rendering process."""

    step_name: str
    description: str
    progress: float  # 0.0 to 1.0


class ProgressReporter(ABC):
    """Abstract base class for reporting rendering progress."""

    @abstractmethod
    async def report_step(self, step: LoadingStep) -> None:
        """Report a rendering step.

        Args:
            step: The current step being executed.
        """
        ...
