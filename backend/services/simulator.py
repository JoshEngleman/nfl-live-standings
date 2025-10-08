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
from typing import Optional, List


def generate_player_simulations(
    projections: np.ndarray,
    std_devs: np.ndarray,
    iterations: int,
    seed: Optional[int] = None,
    use_lognormal: bool = False,
    use_position_based: bool = False,
    positions: Optional[List[str]] = None
) -> np.ndarray:
    """
    Generate simulation matrix for all players across all iterations.

    Uses vectorized distribution sampling - single NumPy call generates
    all simulations at once.

    Args:
        projections: Array of player projections, shape (num_players,)
        std_devs: Array of std deviations, shape (num_players,)
        iterations: Number of Monte Carlo iterations
        seed: Random seed for reproducibility (None for production)
        use_lognormal: If True, use log-normal distribution for right-skew.
                       Creates "lottery ticket" effect for low-proj players.
                       If False, uses normal distribution (default).
        use_position_based: If True, use position-specific component-based modeling.
                           Requires positions parameter. Overrides use_lognormal.
        positions: List of position strings (e.g., ["QB", "RB", "WR"]) for each player.
                  Required if use_position_based=True.

    Returns:
        Simulation matrix of shape (num_players, iterations)
        Each row is one player's simulated scores across all iterations

    Log-normal distribution rationale:
        NFL scoring is discrete and volatile. Low-projection players have
        tight clusters with rare massive outcomes (TD lottery). High-projection
        players have higher probability of big plays. Log-normal naturally
        creates this right-skewed behavior.

    Position-based modeling rationale:
        Fantasy points are composite: yards + TDs + bonuses. Each component
        has different statistical properties (discrete TDs vs continuous yards).
        Position-specific modeling captures this structure for more realistic
        distributions with proper discrete TD steps and boom/bust patterns.

    Performance: O(players × iterations) but highly optimized in NumPy.
    Typical: 500 players × 10K iterations in ~0.1 seconds (normal/lognormal).
    Position-based: ~0.5-1 second (loops over players, but still fast).
    """
    if seed is not None:
        np.random.seed(seed)

    # Position-based simulation (more accurate, slightly slower)
    if use_position_based:
        if positions is None:
            raise ValueError("positions parameter required when use_position_based=True")

        from config.position_config import detect_position
        from services.position_simulator import simulate_player_position_based

        # Pre-allocate result matrix
        player_sims = np.zeros((len(projections), iterations))

        # Generate simulations for each player using position-specific model
        for i, (proj, std, pos_str) in enumerate(zip(projections, std_devs, positions)):
            position = detect_position(pos_str)
            player_sims[i, :] = simulate_player_position_based(
                projection=proj,
                std_dev=std,
                position=position,
                iterations=iterations,
                seed=seed + i if seed is not None else None  # Different seed per player
            )

        return player_sims.astype(np.float32)

    if use_lognormal:
        # Convert (mean, std) to log-normal parameters (μ, σ)
        # Log-normal mean = exp(μ + σ²/2), std = mean × sqrt(exp(σ²) - 1)

        # Avoid division by zero - use minimum projection of 0.5 FP
        safe_proj = np.maximum(projections, 0.5)

        # Coefficient of variation
        cv = std_devs / safe_proj

        # Convert to log-normal parameters
        sigma = np.sqrt(np.log(1 + cv**2))
        mu = np.log(safe_proj) - 0.5 * sigma**2

        # Generate log-normal samples
        player_sims = np.random.lognormal(
            mean=mu[:, np.newaxis],
            sigma=sigma[:, np.newaxis],
            size=(len(projections), iterations)
        )
    else:
        # Original normal distribution
        player_sims = np.random.normal(
            loc=projections[:, np.newaxis],  # Broadcast across iterations
            scale=std_devs[:, np.newaxis],
            size=(len(projections), iterations)
        )

    # Ensure no negative scores (redundant for log-normal but keeps for safety)
    player_sims = np.maximum(player_sims, 0.0)

    return player_sims.astype(np.float32)


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

    return scores.astype(np.float32)


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

    return scores.astype(np.float32)


def run_simulation(
    projections: np.ndarray,
    std_devs: np.ndarray,
    lineup_matrix: np.ndarray,
    iterations: int,
    captain_indices: Optional[np.ndarray] = None,
    seed: Optional[int] = None,
    use_lognormal: bool = False,
    use_position_based: bool = False,
    positions: Optional[List[str]] = None
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
        use_lognormal: If True, use log-normal distribution for volatility modeling
        use_position_based: If True, use position-specific component-based modeling
        positions: List of position strings for each player (required if use_position_based=True)

    Returns:
        Score matrix (lineups × iterations)

    Performance target: <2 seconds for 500 players, 1000 lineups, 10K iterations
    """
    # Step 1: Generate all player simulations (players × iterations)
    player_sims = generate_player_simulations(
        projections, std_devs, iterations, seed,
        use_lognormal=use_lognormal,
        use_position_based=use_position_based,
        positions=positions
    )

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
