"""
Unit tests for simulation engine.

Tests correctness of matrix operations and captain multiplier.
"""

import pytest
import numpy as np
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.simulator import (
    generate_player_simulations,
    calculate_lineup_scores,
    calculate_showdown_scores,
    run_simulation,
    SimulationCache
)


class TestSimulationGeneration:
    """Test player simulation generation."""

    def test_simulation_shape(self):
        """Simulation matrix should have correct shape."""
        projections = np.array([10.0, 15.0, 20.0])
        std_devs = np.array([3.0, 4.0, 5.0])
        iterations = 1000

        result = generate_player_simulations(projections, std_devs, iterations, seed=42)

        assert result.shape == (3, 1000)

    def test_simulation_mean_close_to_projection(self):
        """Mean of simulations should be close to projection."""
        projections = np.array([10.0, 20.0, 30.0])
        std_devs = np.array([2.0, 3.0, 4.0])
        iterations = 10000

        result = generate_player_simulations(projections, std_devs, iterations, seed=42)

        # Mean across iterations should be close to projection
        means = result.mean(axis=1)
        np.testing.assert_allclose(means, projections, rtol=0.1)  # Within 10%

    def test_no_negative_scores(self):
        """Simulations should not produce negative scores."""
        projections = np.array([5.0, 10.0, 15.0])
        std_devs = np.array([10.0, 15.0, 20.0])  # High std dev
        iterations = 10000

        result = generate_player_simulations(projections, std_devs, iterations, seed=42)

        assert np.all(result >= 0), "Found negative scores"

    def test_reproducibility_with_seed(self):
        """Same seed should produce same results."""
        projections = np.array([10.0, 20.0])
        std_devs = np.array([3.0, 4.0])
        iterations = 100

        result1 = generate_player_simulations(projections, std_devs, iterations, seed=42)
        result2 = generate_player_simulations(projections, std_devs, iterations, seed=42)

        np.testing.assert_array_equal(result1, result2)


class TestLineupScores:
    """Test lineup score calculations."""

    def test_lineup_scores_correct_calculation(self):
        """Lineup scores should correctly sum player scores."""
        # 3 players, 2 iterations
        player_sims = np.array([
            [10.0, 12.0],  # Player 0
            [15.0, 18.0],  # Player 1
            [20.0, 22.0]   # Player 2
        ])

        # 2 lineups
        lineup_matrix = np.array([
            [1, 1, 0],  # Lineup 0: Players 0 + 1
            [0, 1, 1]   # Lineup 1: Players 1 + 2
        ], dtype=np.int8)

        result = calculate_lineup_scores(lineup_matrix, player_sims)

        expected = np.array([
            [25.0, 30.0],  # Lineup 0: 10+15=25, 12+18=30
            [35.0, 40.0]   # Lineup 1: 15+20=35, 18+22=40
        ])

        np.testing.assert_array_equal(result, expected)

    def test_lineup_scores_shape(self):
        """Result should have shape (lineups, iterations)."""
        player_sims = np.random.rand(50, 1000)  # 50 players, 1000 iterations
        lineup_matrix = np.random.randint(0, 2, (100, 50), dtype=np.int8)  # 100 lineups

        result = calculate_lineup_scores(lineup_matrix, player_sims)

        assert result.shape == (100, 1000)

    def test_single_player_lineup(self):
        """Lineup with single player should equal that player's score."""
        player_sims = np.array([
            [10.0, 12.0, 14.0],
            [20.0, 22.0, 24.0]
        ])

        # Lineup with only player 1
        lineup_matrix = np.array([[0, 1]], dtype=np.int8)

        result = calculate_lineup_scores(lineup_matrix, player_sims)

        expected = np.array([[20.0, 22.0, 24.0]])
        np.testing.assert_array_equal(result, expected)


class TestShowdownScores:
    """Test showdown captain multiplier."""

    def test_captain_multiplier_correct(self):
        """Captain should receive 1.5x multiplier."""
        # 2 players, 3 iterations
        player_sims = np.array([
            [10.0, 12.0, 14.0],  # Player 0
            [20.0, 22.0, 24.0]   # Player 1
        ])

        # 1 lineup with both players, player 0 is captain
        lineup_matrix = np.array([[1, 1]], dtype=np.int8)
        captain_indices = np.array([0])  # Player 0 is captain

        result = calculate_showdown_scores(lineup_matrix, player_sims, captain_indices)

        # Expected: (10*1.5 + 20), (12*1.5 + 22), (14*1.5 + 24)
        #         = (15 + 20), (18 + 22), (21 + 24)
        #         = 35, 40, 45
        expected = np.array([[35.0, 40.0, 45.0]])

        np.testing.assert_array_almost_equal(result, expected, decimal=5)

    def test_different_captains_per_lineup(self):
        """Each lineup can have different captain."""
        player_sims = np.array([
            [10.0, 10.0],  # Player 0
            [20.0, 20.0],  # Player 1
            [30.0, 30.0]   # Player 2
        ])

        # 2 lineups, all 3 players in each
        lineup_matrix = np.array([
            [1, 1, 1],  # Lineup 0
            [1, 1, 1]   # Lineup 1
        ], dtype=np.int8)

        # Different captains
        captain_indices = np.array([0, 2])  # Lineup 0: captain player 0, Lineup 1: captain player 2

        result = calculate_showdown_scores(lineup_matrix, player_sims, captain_indices)

        # Lineup 0: 10*1.5 + 20 + 30 = 15 + 50 = 65
        # Lineup 1: 10 + 20 + 30*1.5 = 30 + 45 = 75
        expected = np.array([
            [65.0, 65.0],
            [75.0, 75.0]
        ])

        np.testing.assert_array_almost_equal(result, expected, decimal=5)


class TestFullSimulation:
    """Test complete simulation workflow."""

    def test_main_slate_simulation(self):
        """Test full simulation for main slate."""
        # 5 players
        projections = np.array([20.0, 15.0, 12.0, 18.0, 10.0])
        std_devs = np.array([5.0, 4.0, 3.0, 4.5, 2.5])

        # 2 lineups
        lineup_matrix = np.array([
            [1, 1, 1, 0, 0],  # Lineup 0: players 0, 1, 2
            [0, 1, 0, 1, 1]   # Lineup 1: players 1, 3, 4
        ], dtype=np.int8)

        iterations = 100

        result = run_simulation(projections, std_devs, lineup_matrix, iterations, seed=42)

        # Check shape
        assert result.shape == (2, 100)

        # Check all scores positive
        assert np.all(result > 0)

        # Rough check: mean should be close to sum of projections
        lineup0_expected_mean = projections[[0, 1, 2]].sum()
        lineup1_expected_mean = projections[[1, 3, 4]].sum()

        lineup0_actual_mean = result[0, :].mean()
        lineup1_actual_mean = result[1, :].mean()

        # Within 20% due to randomness
        assert abs(lineup0_actual_mean - lineup0_expected_mean) < lineup0_expected_mean * 0.2
        assert abs(lineup1_actual_mean - lineup1_expected_mean) < lineup1_expected_mean * 0.2

    def test_showdown_slate_simulation(self):
        """Test full simulation for showdown slate with captain."""
        projections = np.array([25.0, 20.0, 15.0])
        std_devs = np.array([6.0, 5.0, 4.0])

        lineup_matrix = np.array([
            [1, 1, 1]  # All 3 players
        ], dtype=np.int8)

        captain_indices = np.array([0])  # Player 0 is captain
        iterations = 100

        result = run_simulation(projections, std_devs, lineup_matrix, iterations, captain_indices, seed=42)

        # Expected mean: 25*1.5 + 20 + 15 = 37.5 + 35 = 72.5
        expected_mean = 72.5
        actual_mean = result[0, :].mean()

        assert abs(actual_mean - expected_mean) < expected_mean * 0.2


class TestSimulationCache:
    """Test simulation caching."""

    def test_cache_returns_same_result(self):
        """Cache should return same simulations for same inputs."""
        cache = SimulationCache()

        projections = np.array([10.0, 20.0, 30.0])
        std_devs = np.array([2.0, 3.0, 4.0])
        iterations = 100

        # First call
        result1 = cache.get_or_generate(projections, std_devs, iterations)

        # Second call - should return cached
        result2 = cache.get_or_generate(projections, std_devs, iterations)

        np.testing.assert_array_equal(result1, result2)

    def test_cache_size_tracking(self):
        """Cache should track number of entries."""
        cache = SimulationCache()

        assert cache.size() == 0

        projections1 = np.array([10.0, 20.0])
        std_devs1 = np.array([2.0, 3.0])

        cache.get_or_generate(projections1, std_devs1, 100)
        assert cache.size() == 1

        projections2 = np.array([15.0, 25.0])
        std_devs2 = np.array([2.5, 3.5])

        cache.get_or_generate(projections2, std_devs2, 100)
        assert cache.size() == 2

    def test_cache_clear(self):
        """Cache clear should remove all entries."""
        cache = SimulationCache()

        projections = np.array([10.0, 20.0])
        std_devs = np.array([2.0, 3.0])

        cache.get_or_generate(projections, std_devs, 100)
        assert cache.size() == 1

        cache.clear()
        assert cache.size() == 0


@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks."""

    def test_simulation_speed_500_players_10k_iterations(self):
        """Should handle 500 players × 10K iterations in <2 seconds."""
        num_players = 500
        projections = np.random.uniform(5, 30, num_players)
        std_devs = np.random.uniform(2, 10, num_players)
        iterations = 10000

        start = time.time()
        result = generate_player_simulations(projections, std_devs, iterations)
        duration = time.time() - start

        assert result.shape == (num_players, iterations)
        assert duration < 2.0, f"Too slow: {duration:.2f}s"

    def test_lineup_calculation_speed(self):
        """Matrix multiplication should be fast for large contests."""
        num_players = 500
        num_lineups = 1000
        iterations = 10000

        player_sims = np.random.rand(num_players, iterations)
        lineup_matrix = np.random.randint(0, 2, (num_lineups, num_players), dtype=np.int8)

        start = time.time()
        result = calculate_lineup_scores(lineup_matrix, player_sims)
        duration = time.time() - start

        assert result.shape == (num_lineups, iterations)
        assert duration < 1.0, f"Too slow: {duration:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
