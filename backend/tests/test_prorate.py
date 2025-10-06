"""
Unit tests for pro-rating logic.

Tests correctness, edge cases, and performance.
"""

import pytest
import numpy as np
import pandas as pd
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.prorate import (
    calculate_time_remaining_pct,
    prorate_single_projection,
    prorate_projections_vectorized,
    prorate_dataframe,
    calculate_variance_adjustment,
    adjust_std_devs_vectorized,
    update_projections_for_live_games
)


class TestTimeRemainingCalculation:
    """Test game clock to percentage remaining conversion."""

    def test_q1_start(self):
        """Q1 15:00 should be 100% remaining."""
        pct = calculate_time_remaining_pct(period=1, clock_minutes=15.0)
        assert pct == 1.0

    def test_halftime(self):
        """Q2 0:00 should be 50% remaining."""
        pct = calculate_time_remaining_pct(period=2, clock_minutes=0.0)
        assert pct == 0.5

    def test_q3_midpoint(self):
        """Q3 7:30 should be ~37.5% remaining."""
        pct = calculate_time_remaining_pct(period=3, clock_minutes=7.5)
        expected = (7.5 + 15) / 60.0  # 22.5 / 60 = 0.375
        assert abs(pct - expected) < 0.01

    def test_q4_end(self):
        """Q4 0:00 should be 0% remaining."""
        pct = calculate_time_remaining_pct(period=4, clock_minutes=0.0)
        assert pct == 0.0

    def test_overtime(self):
        """Overtime should be ~5% remaining (conservative)."""
        pct = calculate_time_remaining_pct(period=5, clock_minutes=5.0)
        assert pct == 0.05

    def test_clipping(self):
        """Should clip to [0, 1] range."""
        # Negative should clip to 0
        pct = calculate_time_remaining_pct(period=4, clock_minutes=-5.0)
        assert pct == 0.0

        # Over 100% should clip to 1.0
        pct = calculate_time_remaining_pct(period=1, clock_minutes=20.0)
        assert pct == 1.0


class TestSingleProjectionProrating:
    """Test pro-rating for a single player."""

    def test_halftime_on_pace(self):
        """Player on pace at halftime."""
        # Projected 20, has 10 at halftime → prorated = 10 + (20 * 0.5) = 20
        prorated = prorate_single_projection(
            original_projection=20.0,
            actual_points=10.0,
            pct_remaining=0.5,
            is_finished=False
        )
        assert prorated == 20.0

    def test_halftime_ahead(self):
        """Player ahead of pace."""
        # Projected 20, has 15 at halftime → prorated = 15 + (20 * 0.5) = 25
        prorated = prorate_single_projection(
            original_projection=20.0,
            actual_points=15.0,
            pct_remaining=0.5
        )
        assert prorated == 25.0

    def test_halftime_behind(self):
        """Player behind pace."""
        # Projected 20, has 5 at halftime → prorated = 5 + (20 * 0.5) = 15
        prorated = prorate_single_projection(
            original_projection=20.0,
            actual_points=5.0,
            pct_remaining=0.5
        )
        assert prorated == 15.0

    def test_finished_game(self):
        """Finished game should return actual only."""
        prorated = prorate_single_projection(
            original_projection=20.0,
            actual_points=18.5,
            pct_remaining=0.0,
            is_finished=True
        )
        assert prorated == 18.5

    def test_zero_percent_remaining(self):
        """0% remaining should return actual."""
        prorated = prorate_single_projection(
            original_projection=20.0,
            actual_points=18.5,
            pct_remaining=0.0,
            is_finished=False
        )
        assert prorated == 18.5

    def test_q3_scenario(self):
        """Q3 end (25% remaining)."""
        # Projected 20, has 18 after 75% → prorated = 18 + (20 * 0.25) = 23
        prorated = prorate_single_projection(
            original_projection=20.0,
            actual_points=18.0,
            pct_remaining=0.25
        )
        assert prorated == 23.0


class TestVectorizedProrating:
    """Test vectorized pro-rating for multiple players."""

    def test_multiple_players(self):
        """Pro-rate multiple players at once."""
        originals = np.array([20.0, 15.0, 25.0])
        actuals = np.array([10.0, 8.0, 20.0])
        pct_remaining = np.array([0.5, 0.5, 0.5])

        prorated = prorate_projections_vectorized(originals, actuals, pct_remaining)

        expected = np.array([20.0, 15.5, 32.5])
        np.testing.assert_array_almost_equal(prorated, expected)

    def test_mixed_finished_and_live(self):
        """Some players finished, some live."""
        originals = np.array([20.0, 15.0, 25.0])
        actuals = np.array([18.5, 8.0, 22.0])
        pct_remaining = np.array([0.0, 0.5, 0.25])
        finished = np.array([True, False, False])

        prorated = prorate_projections_vectorized(originals, actuals, pct_remaining, finished)

        expected = np.array([
            18.5,  # Finished, use actual
            8.0 + (15.0 * 0.5),  # = 15.5
            22.0 + (25.0 * 0.25)  # = 28.25
        ])

        np.testing.assert_array_almost_equal(prorated, expected)

    def test_all_finished(self):
        """All games finished."""
        originals = np.array([20.0, 15.0, 25.0])
        actuals = np.array([18.5, 12.3, 28.7])
        pct_remaining = np.zeros(3)

        prorated = prorate_projections_vectorized(originals, actuals, pct_remaining)

        np.testing.assert_array_equal(prorated, actuals)

    def test_large_array_performance(self):
        """Should handle 500 players quickly."""
        num_players = 500
        originals = np.random.uniform(10, 30, num_players)
        actuals = np.random.uniform(5, 25, num_players)
        pct_remaining = np.random.uniform(0, 1, num_players)

        start = time.time()
        prorated = prorate_projections_vectorized(originals, actuals, pct_remaining)
        duration = time.time() - start

        assert prorated.shape == (num_players,)
        assert duration < 0.01, f"Too slow: {duration:.4f}s"  # <10ms


class TestDataFrameProrating:
    """Test DataFrame wrapper for pro-rating."""

    def test_prorate_dataframe(self):
        """Pro-rate projections in a DataFrame."""
        df = pd.DataFrame({
            'Name': ['Player A', 'Player B', 'Player C'],
            'Projection': [20.0, 15.0, 25.0],
            'Std Dev': [5.0, 4.0, 6.0]
        })

        live_stats = {
            'Player A': {'actual_points': 10.0, 'pct_remaining': 0.5, 'is_finished': False},
            'Player B': {'actual_points': 12.3, 'pct_remaining': 0.0, 'is_finished': True},
            # Player C not in live stats (hasn't started)
        }

        df_prorated = prorate_dataframe(df, live_stats, default_pct_remaining=1.0)

        # Player A: 10 + (20 * 0.5) = 20
        assert df_prorated.loc[0, 'Prorated_Projection'] == 20.0

        # Player B: Finished, use actual
        assert df_prorated.loc[1, 'Prorated_Projection'] == 12.3

        # Player C: Not started, use original
        assert df_prorated.loc[2, 'Prorated_Projection'] == 25.0

    def test_prorate_with_no_live_stats(self):
        """DataFrame with no live stats should return originals."""
        df = pd.DataFrame({
            'Name': ['Player A', 'Player B'],
            'Projection': [20.0, 15.0],
            'Std Dev': [5.0, 4.0]
        })

        df_prorated = prorate_dataframe(df, {})

        np.testing.assert_array_equal(
            df_prorated['Prorated_Projection'].values,
            df['Projection'].values
        )


class TestVarianceAdjustment:
    """Test variance adjustment for time remaining."""

    def test_halftime_variance(self):
        """Variance at halftime should scale by sqrt(0.5)."""
        adjusted = calculate_variance_adjustment(original_std_dev=8.0, pct_remaining=0.5)
        expected = 8.0 * np.sqrt(0.5)  # ≈ 5.66
        assert abs(adjusted - expected) < 0.1

    def test_finished_game_variance(self):
        """Finished games should have minimal variance."""
        adjusted = calculate_variance_adjustment(original_std_dev=8.0, pct_remaining=0.0)
        assert adjusted == 0.1

    def test_minimum_variance_for_live(self):
        """Live games should have minimum variance of 0.5."""
        # Small remaining time with small original variance
        adjusted = calculate_variance_adjustment(original_std_dev=2.0, pct_remaining=0.1)
        assert adjusted >= 0.5

    def test_vectorized_adjustment(self):
        """Vectorized variance adjustment."""
        originals = np.array([8.0, 6.0, 5.0])
        pct_remaining = np.array([0.5, 0.25, 0.0])

        adjusted = adjust_std_devs_vectorized(originals, pct_remaining)

        # Check finished game
        assert adjusted[2] == 0.1

        # Check live games have reasonable values
        assert adjusted[0] > 0.5
        assert adjusted[1] > 0.5


class TestCompleteWorkflow:
    """Test the complete pro-rating workflow."""

    def test_update_projections_for_live_games(self):
        """Complete workflow: pro-rate and adjust variance."""
        df = pd.DataFrame({
            'Name': ['Player A', 'Player B', 'Player C'],
            'Projection': [20.0, 15.0, 25.0],
            'Std Dev': [5.0, 4.0, 6.0]
        })

        live_stats = {
            'Player A': {'actual_points': 10.0, 'pct_remaining': 0.5, 'is_finished': False},
            'Player B': {'actual_points': 12.3, 'pct_remaining': 0.0, 'is_finished': True},
        }

        prorated_proj, adjusted_std = update_projections_for_live_games(
            df, live_stats, adjust_variance=True
        )

        # Check shapes
        assert prorated_proj.shape == (3,)
        assert adjusted_std.shape == (3,)

        # Player A: pro-rated
        assert prorated_proj[0] == 20.0

        # Player B: finished
        assert prorated_proj[1] == 12.3
        assert adjusted_std[1] == 0.1  # Minimal variance

        # Player C: not started
        assert prorated_proj[2] == 25.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_negative_actual_points(self):
        """Negative points (rare but possible with INTs)."""
        prorated = prorate_single_projection(
            original_projection=20.0,
            actual_points=-2.0,  # Bad game
            pct_remaining=0.5
        )
        # -2 + (20 * 0.5) = 8
        assert prorated == 8.0

    def test_zero_projection(self):
        """Player with 0 projected points."""
        prorated = prorate_single_projection(
            original_projection=0.0,
            actual_points=5.0,  # Surprise!
            pct_remaining=0.5
        )
        # 5 + (0 * 0.5) = 5
        assert prorated == 5.0

    def test_massive_outperformance(self):
        """Player way exceeding projection."""
        # Projected 10, has 25 at halftime!
        prorated = prorate_single_projection(
            original_projection=10.0,
            actual_points=25.0,
            pct_remaining=0.5
        )
        # 25 + (10 * 0.5) = 30
        assert prorated == 30.0

    def test_empty_arrays(self):
        """Handle empty arrays gracefully."""
        originals = np.array([])
        actuals = np.array([])
        pct_remaining = np.array([])

        prorated = prorate_projections_vectorized(originals, actuals, pct_remaining)

        assert prorated.shape == (0,)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
