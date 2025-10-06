"""
Pro-rating service for live NFL projections.

Performance notes:
- Vectorized operations using NumPy
- No loops over players (processes all at once)
- Handles finished vs live games efficiently

Pro-rating formula:
- Live games: actual_points + (original_projection × pct_game_remaining)
- Finished games: actual_points only
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


def calculate_time_remaining_pct(period: int, clock_minutes: float) -> float:
    """
    Calculate percentage of game remaining.

    Args:
        period: Quarter number (1-4, 5+ for OT)
        clock_minutes: Minutes remaining in current period (0-15)

    Returns:
        Percentage of game remaining (0.0 to 1.0)

    NFL game structure:
    - 4 quarters × 15 minutes = 60 minutes total
    - Overtime: 10 minutes (sudden death)

    Examples:
        Q1 15:00 → 100% remaining (60/60)
        Q2 7:30 → 62.5% remaining (37.5/60)
        Q4 0:00 → 0% remaining (0/60)
        OT 5:00 → Special handling (treat as 5% remaining for simplicity)
    """
    if period > 4:
        # Overtime - treat as minimal time remaining
        # Pro-rate as if 5% of game left (conservative estimate)
        return 0.05

    # Calculate total minutes remaining
    minutes_in_current_period = clock_minutes
    full_periods_remaining = max(0, 4 - period)

    total_minutes_remaining = minutes_in_current_period + (full_periods_remaining * 15)

    # Percentage remaining
    pct_remaining = total_minutes_remaining / 60.0

    return np.clip(pct_remaining, 0.0, 1.0)


def prorate_single_projection(
    original_projection: float,
    actual_points: float,
    pct_remaining: float,
    is_finished: bool = False
) -> float:
    """
    Pro-rate a single player's projection.

    Args:
        original_projection: Pregame projected fantasy points
        actual_points: Fantasy points scored so far
        pct_remaining: Percentage of game remaining (0.0-1.0)
        is_finished: If True, game is over (use actual only)

    Returns:
        Pro-rated projection for full game

    Formula:
        If finished: actual_points
        If live: actual_points + (original_projection × pct_remaining)

    Example:
        original = 20.0, actual = 15.0, remaining = 0.5 (halftime)
        prorated = 15.0 + (20.0 × 0.5) = 25.0 pts
    """
    if is_finished or pct_remaining <= 0.0:
        return actual_points

    prorated = actual_points + (original_projection * pct_remaining)

    return prorated


def prorate_projections_vectorized(
    original_projections: np.ndarray,
    actual_points: np.ndarray,
    pct_remaining: np.ndarray,
    finished_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Pro-rate projections for all players (vectorized for performance).

    ⚠️ PERFORMANCE CRITICAL - This runs every 2-3 minutes during live games.
    Must use NumPy vectorized operations, never Python loops.

    Args:
        original_projections: Original projections, shape (num_players,)
        actual_points: Actual fantasy points so far, shape (num_players,)
        pct_remaining: % of game remaining for each player, shape (num_players,)
        finished_mask: Boolean mask for finished games (True = finished), shape (num_players,)
                      If None, detect based on pct_remaining <= 0

    Returns:
        Pro-rated projections, shape (num_players,)

    Performance: O(n) where n = num_players, vectorized NumPy operations
    Target: <10ms for 500 players
    """
    # Initialize output array
    prorated = np.empty_like(original_projections)

    # Detect finished games if not provided
    if finished_mask is None:
        finished_mask = pct_remaining <= 0.0

    # Separate live vs finished games
    live_mask = ~finished_mask

    # Pro-rate live games (vectorized)
    prorated[live_mask] = (
        actual_points[live_mask] +
        (original_projections[live_mask] * pct_remaining[live_mask])
    )

    # Use actual points for finished games
    prorated[finished_mask] = actual_points[finished_mask]

    return prorated


def prorate_dataframe(
    projections_df: pd.DataFrame,
    live_stats: Dict[str, Dict],
    default_pct_remaining: float = 1.0
) -> pd.DataFrame:
    """
    Pro-rate projections in a DataFrame based on live stats.

    High-level wrapper for common use case.

    Args:
        projections_df: DataFrame with columns ['Name', 'Projection', 'Std Dev']
        live_stats: Dict mapping player name -> {
            'actual_points': float,
            'pct_remaining': float,
            'is_finished': bool
        }
        default_pct_remaining: Default % remaining for players not in live_stats (1.0 = not started)

    Returns:
        DataFrame with added 'Prorated_Projection' column

    Example:
        live_stats = {
            'Patrick Mahomes': {
                'actual_points': 18.5,
                'pct_remaining': 0.5,
                'is_finished': False
            },
            'Travis Kelce': {
                'actual_points': 8.2,
                'pct_remaining': 0.5,
                'is_finished': False
            }
        }

        df_prorated = prorate_dataframe(df, live_stats)
    """
    df = projections_df.copy()

    # Extract arrays for vectorized operation
    num_players = len(df)
    original_projections = df['Projection'].values
    actual_points = np.zeros(num_players)
    pct_remaining = np.full(num_players, default_pct_remaining)
    finished_mask = np.zeros(num_players, dtype=bool)

    # Update with live stats
    for idx, player_name in enumerate(df['Name']):
        if player_name in live_stats:
            stats = live_stats[player_name]
            actual_points[idx] = stats.get('actual_points', 0.0)
            pct_remaining[idx] = stats.get('pct_remaining', default_pct_remaining)
            finished_mask[idx] = stats.get('is_finished', False)

    # Pro-rate (vectorized)
    prorated_projections = prorate_projections_vectorized(
        original_projections,
        actual_points,
        pct_remaining,
        finished_mask
    )

    # Add to dataframe
    df['Prorated_Projection'] = prorated_projections
    df['Actual_Points'] = actual_points
    df['Pct_Remaining'] = pct_remaining

    return df


def detect_finished_games_from_stdev(std_devs: np.ndarray, threshold: float = 0.2) -> np.ndarray:
    """
    Detect finished games based on std_dev threshold.

    Stokastic CSV convention: std_dev ≈ 0.1 for finished games (actual scores).

    Args:
        std_devs: Array of standard deviations
        threshold: Threshold below which game is considered finished (default 0.2)

    Returns:
        Boolean mask where True = finished game
    """
    return std_devs <= threshold


def calculate_variance_adjustment(
    original_std_dev: float,
    pct_remaining: float
) -> float:
    """
    Adjust variance for remaining game time.

    As game progresses, uncertainty decreases. Scale std_dev by sqrt(pct_remaining).

    Args:
        original_std_dev: Original standard deviation
        pct_remaining: Percentage of game remaining (0.0-1.0)

    Returns:
        Adjusted standard deviation

    Example:
        original_std_dev = 8.0, pct_remaining = 0.5 (halftime)
        adjusted = 8.0 × sqrt(0.5) ≈ 5.66

    Rationale: Variance scales with time in random processes.
    """
    if pct_remaining <= 0.0:
        return 0.1  # Minimal variance for finished games

    adjusted = original_std_dev * np.sqrt(pct_remaining)

    # Ensure some minimum variance for live games
    return max(adjusted, 0.5)


def adjust_std_devs_vectorized(
    original_std_devs: np.ndarray,
    pct_remaining: np.ndarray,
    finished_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Adjust standard deviations for all players based on time remaining.

    Args:
        original_std_devs: Original standard deviations, shape (num_players,)
        pct_remaining: % remaining for each player, shape (num_players,)
        finished_mask: Boolean mask for finished games

    Returns:
        Adjusted standard deviations, shape (num_players,)
    """
    if finished_mask is None:
        finished_mask = pct_remaining <= 0.0

    adjusted = original_std_devs * np.sqrt(pct_remaining)

    # Minimal variance for finished games
    adjusted[finished_mask] = 0.1

    # Ensure minimum variance for live games
    live_mask = ~finished_mask
    adjusted[live_mask] = np.maximum(adjusted[live_mask], 0.5)

    return adjusted


# Convenience function for common workflow
def update_projections_for_live_games(
    projections_df: pd.DataFrame,
    live_stats: Dict[str, Dict],
    adjust_variance: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Complete workflow: pro-rate projections and adjust variance.

    Args:
        projections_df: DataFrame with ['Name', 'Projection', 'Std Dev']
        live_stats: Live stats dictionary
        adjust_variance: Whether to adjust std_dev for time remaining

    Returns:
        Tuple of (prorated_projections, adjusted_std_devs)

    This is the main entry point for integration with simulation engine.
    """
    # Pro-rate projections
    df_prorated = prorate_dataframe(projections_df, live_stats)

    prorated_projections = df_prorated['Prorated_Projection'].values

    if adjust_variance:
        pct_remaining = df_prorated['Pct_Remaining'].values
        original_std_devs = df_prorated['Std Dev'].values
        adjusted_std_devs = adjust_std_devs_vectorized(original_std_devs, pct_remaining)
    else:
        adjusted_std_devs = df_prorated['Std Dev'].values

    return prorated_projections, adjusted_std_devs
