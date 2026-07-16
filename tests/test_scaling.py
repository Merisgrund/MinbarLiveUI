"""Tests for the display-scaling clamp (gui/scaling.py).

fit_factor is a pure function, so the sizing rule is testable headlessly —
no CTk root, no display. The real-world numbers below come from measuring
the app's fixed logical window sizes against the DPI scalings Windows
offers as "recommended" defaults.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.scaling import (
    DESIGN_H,
    DESIGN_W,
    MAX_SCREEN_FRACTION,
    fit_factor,
)

# (label, screen w, screen h, dpi) — work area is the screen minus a taskbar
# of 48 logical px, which is how these are measured in practice.
DESKTOP_2560_125 = (2560, 1380, 1.25)  # the monitor the design was tuned on
LAPTOP_1920_150 = (1920, 1008, 1.5)  # the reported case
LAPTOP_1920_175 = (1920, 996, 1.75)  # clipped before the clamp


class TestFitFactorNeverUpscales:
    """The clamp may only ever shrink: a user who picks 150% on a large
    monitor asked for bigger text and must keep it."""

    @pytest.mark.parametrize(
        ("work_w", "work_h", "dpi"),
        [
            DESKTOP_2560_125,
            (3840, 2100, 1.5),  # 4K at 150% — roomy despite the high DPI
            (2560, 1380, 1.0),
            (1920, 1040, 1.0),  # plain 1080p, no scaling
        ],
    )
    def test_roomy_screens_are_untouched(self, work_w, work_h, dpi):
        assert fit_factor(dpi, work_w, work_h) == 1.0

    def test_never_exceeds_one_on_a_huge_screen(self):
        assert fit_factor(1.0, 7680, 4320) == 1.0


class TestFitFactorShrinksWhenNeeded:
    def test_laptop_1920_at_150_percent_is_clamped(self):
        work_w, work_h, dpi = LAPTOP_1920_150
        fit = fit_factor(dpi, work_w, work_h)
        assert fit < 1.0, "the reported case must actually engage the clamp"
        # The tallest window must land within the target fraction.
        assert DESIGN_H * dpi * fit <= work_h * MAX_SCREEN_FRACTION + 1

    def test_laptop_1920_at_175_percent_fits_after_clamping(self):
        """Before the clamp this configuration clipped the wizard's buttons
        off the bottom of the screen."""
        work_w, work_h, dpi = LAPTOP_1920_175
        assert DESIGN_H * dpi > work_h, "premise: unclamped, this overflows"

        fit = fit_factor(dpi, work_w, work_h)
        assert DESIGN_H * dpi * fit <= work_h * MAX_SCREEN_FRACTION + 1
        assert DESIGN_W * dpi * fit <= work_w * MAX_SCREEN_FRACTION + 1

    def test_small_low_dpi_laptop_is_clamped_too(self):
        """A 1366x768 panel at 100% is as tight as a high-DPI one — the rule
        is about the work area, not the DPI on its own."""
        fit = fit_factor(1.0, 1366, 728)
        assert fit < 1.0
        assert DESIGN_H * fit <= 728 * MAX_SCREEN_FRACTION + 1

    def test_height_is_the_binding_constraint_on_16_9(self):
        """Width has slack on 16:9 screens; a regression that only checked
        width would silently stop clamping."""
        work_w, work_h, dpi = LAPTOP_1920_150
        by_w = (work_w * MAX_SCREEN_FRACTION) / (DESIGN_W * dpi)
        by_h = (work_h * MAX_SCREEN_FRACTION) / (DESIGN_H * dpi)
        assert by_h < by_w
        assert fit_factor(dpi, work_w, work_h) == pytest.approx(by_h)

    def test_shrinks_monotonically_as_dpi_rises(self):
        factors = [fit_factor(d, 1920, 1008) for d in (1.0, 1.25, 1.5, 1.75, 2.0)]
        assert factors == sorted(factors, reverse=True)


class TestFitFactorBadInput:
    """A failed measurement must never shrink the app to nothing."""

    @pytest.mark.parametrize(
        ("dpi", "work_w", "work_h"),
        [
            (0, 1920, 1008),
            (-1.5, 1920, 1008),
            (1.5, 0, 1008),
            (1.5, 1920, 0),
            (1.5, -1920, -1008),
        ],
    )
    def test_nonsense_input_returns_no_clamp(self, dpi, work_w, work_h):
        assert fit_factor(dpi, work_w, work_h) == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
