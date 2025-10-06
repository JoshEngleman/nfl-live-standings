"""
Monte Carlo simulation engine for DFS contests.

⚠️ CRITICAL PATH - This is the performance bottleneck of the entire system.

Performance requirements:
- Must handle 500 players × 10,000 iterations in <2 seconds
- MUST use matrix operations - NEVER use loops over iterations
- Matrix multiplication is 100-1000x faster than nested loops

Architecture:
1. Generate all player simulations at once: (players × iterations)
2. Create lineup binary matrix: (lineups × players)
3. Single matrix multiplication for ALL scores: lineup_matrix @ player_sims
"""

import numpy as np
from typing import Optional


def generate_player_simulations(
    projections: np.ndarray,
    std_devs: np.ndarray,
    iterations: int,
    seed: Optional[int] = None
) -> np.ndarray:
    """
    Generate simulation matrix for all players across all iterations.

    Uses vectorized normal distribution sampling - single NumPy call generates
    all simulations at once.

    Args:
        projections: Array of player projections, shape (num_players,)
        std_devs: Array of std deviations, shape (num_players,)
        iterations: Number of Monte Carlo iterations
        seed: Random seed for reproducibility (None for production)

    Returns:
        Simulation matrix of shape (num_players, iterations)
        Each row is one player's simulated scores across all iterations

    Performance: O(players × iterations) but highly optimized in NumPy.
    Typical: 500 players × 10K iterations in ~0.1 seconds.
    """
    if seed is not None:
        np.random.seed(seed)

    # Single vectorized call generates entire matrix
    # This is THE CORE OPERATION - do not refactor to loops
    player_sims = np.random.normal(
        loc=projections[:, np.newaxis],  # Broadcast across iterations
        scale=std_devs[:, np.newaxis],
        size=(len(projections), iterations)
    )

    # Ensure no negative scores
    player_sims = np.maximum(player_sims, 0.0)

    return player_sims


def calculate_lineup_scores(
    lineup_matrix: np.ndarray,
    player_sims: np.ndarray
) -> np.ndarray:
    """
    Calculate all lineup scores across all iterations via matrix multiplication.

    This is THE performance bottleneck. Uses optimized BLAS-level matrix multiply.

    Args:
        lineup_matrix: Binary matrix (lineups × players)
                      Entry [i, j] = 1 if player j in lineup i, else 0
        player_sims: Simulation matrix (players × iterations)

    Returns:
        Score matrix (lineups × iterations)
        Entry [i, j] = total score for lineup i in iteration j

    Performance: O(L×P×I) via optimized BLAS where L=lineups, P=players, I=iterations.
    The @ operator uses highly optimized linear algebra libraries.
    DO NOT replace with loops - will be 100-1000x slower.

    Example:
        3 players, 2 iterations:
        player_sims = [[10, 12],    # Player 0
                       [15, 18],    # Player 1
                       [20, 22]]    # Player 2

        2 lineups:
        lineup_matrix = [[1, 1, 0],  # Lineup 0: Players 0+1
                         [0, 1, 1]]  # Lineup 1: Players 1+2

        Result = [[25, 30],   # Lineup 0: 10+15=25, 12+18=30
                  [35, 40]]   # Lineup 1: 15+20=35, 18+22=40
    """
    # ✅ THIS IS THE WAY - Single matrix multiplication
    scores = lineup_matrix @ player_sims

    return scores


def calculate_showdown_scores(
    lineup_matrix: np.ndarray,
    player_sims: np.ndarray,
    captain_indices: np.ndarray
) -> np.ndarray:
    """
    Calculate lineup scores for showdown slate with captain multiplier (1.5x).

    Captain scores 1.5x points, so we add an extra 0.5x bonus to the base score.

    Args:
        lineup_matrix: Binary matrix (lineups × players)
        player_sims: Simulation matrix (players × iterations)
        captain_indices: Array of captain player indices for each lineup, shape (lineups,)

    Returns:
        Score matrix (lineups × iterations) with captain bonus applied

    Performance: Still uses matrix operations. Captain bonus applied vectorized.
    """
    # Base scores for all lineups (counts captain as 1x)
    base_scores = lineup_matrix @ player_sims  # (lineups × iterations)

    # Extract captain simulations for each lineup
    # captain_sims[i, :] = simulations for lineup i's captain
    captain_sims = player_sims[captain_indices, :]  # (lineups × iterations)

    # Apply 0.5x bonus (captain already counted 1x in base, so add 0.5x more for total 1.5x)
    captain_bonus = 0.5 * captain_sims

    # Add captain bonus - both arrays same shape (lineups × iterations)
    scores = base_scores + captain_bonus

    return scores


def run_simulation(
    projections: np.ndarray,
    std_devs: np.ndarray,
    lineup_matrix: np.ndarray,
    iterations: int,
    captain_indices: Optional[np.ndarray] = None,
    seed: Optional[int] = None
) -> np.ndarray:
    """
    Run complete Monte Carlo simulation.

    High-level wrapper that:
    1. Generates player simulations
    2. Calculates lineup scores (with captain multiplier if showdown)

    Args:
        projections: Player projections, shape (num_players,)
        std_devs: Player std deviations, shape (num_players,)
        lineup_matrix: Binary lineup matrix (lineups × players)
        iterations: Number of Monte Carlo iterations
        captain_indices: Optional captain indices for showdown (lineups,)
        seed: Random seed for reproducibility

    Returns:
        Score matrix (lineups × iterations)

    Performance target: <2 seconds for 500 players, 1000 lineups, 10K iterations
    """
    # Step 1: Generate all player simulations (players × iterations)
    player_sims = generate_player_simulations(projections, std_devs, iterations, seed)

    # Step 2: Calculate all lineup scores via matrix multiplication
    if captain_indices is not None:
        # Showdown slate with captain multiplier
        scores = calculate_showdown_scores(lineup_matrix, player_sims, captain_indices)
    else:
        # Main slate (standard scoring)
        scores = calculate_lineup_scores(lineup_matrix, player_sims)

    return scores


class SimulationCache:
    """
    Cache for player simulations when projections haven't changed.

    Useful for repeated simulations with same projections but different lineups.
    """

    def __init__(self):
        self._cache: dict = {}

    def get_or_generate(
        self,
        projections: np.ndarray,
        std_devs: np.ndarray,
        iterations: int
    ) -> np.ndarray:
        """
        Get cached simulations or generate new ones.

        Cache key is hash of projections + std_devs + iterations.
        """
        cache_key = hash(
            projections.tobytes() + std_devs.tobytes() + str(iterations).encode()
        )

        if cache_key not in self._cache:
            self._cache[cache_key] = generate_player_simulations(
                projections, std_devs, iterations, seed=None
            )

        return self._cache[cache_key]

    def clear(self):
        """Clear all cached simulations."""
        self._cache.clear()

    def size(self) -> int:
        """Return number of cached simulation matrices."""
        return len(self._cache)
