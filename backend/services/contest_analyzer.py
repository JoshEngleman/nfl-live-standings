"""
Contest analysis - calculate win rates, ROI, EV from simulation results.

Performance notes:
- Use NumPy argsort for fast ranking across iterations
- Vectorize finish position calculations
- Avoid Python loops over iterations
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from models.contest import ContestAnalysis


def calculate_finish_positions(scores: np.ndarray) -> np.ndarray:
    """
    Calculate finish positions for all lineups across all iterations.

    Args:
        scores: Score matrix (lineups × iterations)

    Returns:
        Position matrix (lineups × iterations)
        Entry [i, j] = finish position of lineup i in iteration j
        (1 = first place, 2 = second, etc.)

    Performance: O(L × I × log(L)) where L=lineups, I=iterations
    Uses NumPy argsort which is highly optimized.
    """
    # For each iteration, get lineup indices sorted by score (descending)
    # argsort sorts ascending, so negate scores for descending sort
    sorted_indices = np.argsort(-scores, axis=0)  # Shape: (lineups × iterations)

    # Create position matrix
    positions = np.empty_like(scores, dtype=np.int32)

    # For each iteration, assign positions
    num_lineups = scores.shape[0]
    for pos in range(num_lineups):
        lineup_idx = sorted_indices[pos, :]
        positions[lineup_idx, np.arange(scores.shape[1])] = pos + 1  # 1-indexed

    return positions


def calculate_win_rate(positions: np.ndarray, lineup_idx: int, top_n: int = 1) -> float:
    """
    Calculate probability of finishing in top N positions.

    Args:
        positions: Position matrix (lineups × iterations)
        lineup_idx: Index of lineup to analyze
        top_n: Top N positions to count (default 1 = win rate)

    Returns:
        Win rate as float between 0 and 1
    """
    lineup_positions = positions[lineup_idx, :]
    wins = np.sum(lineup_positions <= top_n)
    return wins / len(lineup_positions)


def calculate_average_finish(positions: np.ndarray, lineup_idx: int) -> float:
    """Calculate average finish position for a lineup."""
    return float(np.mean(positions[lineup_idx, :]))


def calculate_cash_rate(
    positions: np.ndarray,
    lineup_idx: int,
    payout_positions: int
) -> float:
    """
    Calculate probability of cashing (finishing in paid positions).

    Args:
        positions: Position matrix (lineups × iterations)
        lineup_idx: Index of lineup to analyze
        payout_positions: Number of positions that get paid

    Returns:
        Cash rate as float between 0 and 1
    """
    lineup_positions = positions[lineup_idx, :]
    cashes = np.sum(lineup_positions <= payout_positions)
    return cashes / len(lineup_positions)


def create_simple_payout_structure(
    num_lineups: int,
    entry_fee: float = 1.0,
    rake: float = 0.10
) -> Dict[int, float]:
    """
    Create a simple top-heavy GPP payout structure.

    Args:
        num_lineups: Total number of entries in contest
        entry_fee: Entry fee per lineup
        rake: Platform rake (default 10%)

    Returns:
        Dictionary mapping position -> payout amount

    Note: This is a simplified payout. Real DK payouts should be parsed from CSV.
    """
    total_pool = num_lineups * entry_fee * (1 - rake)

    # Simple top-heavy structure
    # 1st: 20%, 2nd: 10%, 3rd: 7%, 4-5: 5%, 6-10: 3%, 11-20: 2%, 21-50: 1%
    payouts = {}

    if num_lineups >= 100:
        # Large GPP
        payouts[1] = total_pool * 0.20
        payouts[2] = total_pool * 0.10
        payouts[3] = total_pool * 0.07

        remaining = total_pool * 0.63
        # Distribute remaining proportionally
        for pos in range(4, min(51, num_lineups + 1)):
            if pos <= 5:
                payouts[pos] = remaining * 0.08
            elif pos <= 10:
                payouts[pos] = remaining * 0.05
            elif pos <= 20:
                payouts[pos] = remaining * 0.03
            else:
                payouts[pos] = remaining * 0.01
    elif num_lineups >= 20:
        # Medium GPP - top 20% get paid
        payout_spots = max(1, num_lineups // 5)
        for pos in range(1, payout_spots + 1):
            if pos == 1:
                payouts[pos] = total_pool * 0.30
            elif pos == 2:
                payouts[pos] = total_pool * 0.20
            elif pos == 3:
                payouts[pos] = total_pool * 0.15
            else:
                payouts[pos] = (total_pool * 0.35) / (payout_spots - 3)
    else:
        # Small contest - winner take all or top 3
        if num_lineups <= 5:
            payouts[1] = total_pool
        else:
            payouts[1] = total_pool * 0.50
            payouts[2] = total_pool * 0.30
            payouts[3] = total_pool * 0.20

    return payouts


def calculate_expected_value(
    positions: np.ndarray,
    lineup_idx: int,
    payout_structure: Dict[int, float],
    entry_fee: float
) -> Tuple[float, float]:
    """
    Calculate expected value and ROI for a lineup.

    Args:
        positions: Position matrix (lineups × iterations)
        lineup_idx: Index of lineup to analyze
        payout_structure: Dictionary mapping position -> payout
        entry_fee: Entry fee paid

    Returns:
        Tuple of (expected_value, roi_percentage)
    """
    lineup_positions = positions[lineup_idx, :]

    # Calculate expected payout
    total_payout = 0.0
    for pos, payout in payout_structure.items():
        times_finished_at_pos = np.sum(lineup_positions == pos)
        prob_finish_at_pos = times_finished_at_pos / len(lineup_positions)
        total_payout += prob_finish_at_pos * payout

    # EV = Expected payout - Entry fee
    ev = total_payout - entry_fee

    # ROI = (EV / Entry fee) × 100
    roi = (ev / entry_fee) * 100 if entry_fee > 0 else 0.0

    return ev, roi


def analyze_lineup(
    scores: np.ndarray,
    lineup_idx: int,
    entry_name: str,
    entry_fee: float = 1.0,
    payout_structure: Optional[Dict[int, float]] = None
) -> ContestAnalysis:
    """
    Complete analysis for a single lineup.

    Args:
        scores: Score matrix (lineups × iterations)
        lineup_idx: Index of lineup to analyze
        entry_name: Name/username for this entry
        entry_fee: Entry fee paid
        payout_structure: Optional custom payout structure

    Returns:
        ContestAnalysis object with all metrics
    """
    # Calculate finish positions across all iterations
    positions = calculate_finish_positions(scores)

    # Create payout structure if not provided
    if payout_structure is None:
        num_lineups = scores.shape[0]
        payout_structure = create_simple_payout_structure(num_lineups, entry_fee)

    # Calculate metrics
    win_rate = calculate_win_rate(positions, lineup_idx, top_n=1)
    top_3_rate = calculate_win_rate(positions, lineup_idx, top_n=3)
    top_10_rate = calculate_win_rate(positions, lineup_idx, top_n=10)

    payout_positions = max(payout_structure.keys()) if payout_structure else 1
    cash_rate = calculate_cash_rate(positions, lineup_idx, payout_positions)

    ev, roi = calculate_expected_value(positions, lineup_idx, payout_structure, entry_fee)

    avg_finish = calculate_average_finish(positions, lineup_idx)

    return ContestAnalysis(
        entry_name=entry_name,
        win_rate=win_rate,
        top_3_rate=top_3_rate,
        top_10_rate=top_10_rate,
        cash_rate=cash_rate,
        expected_value=ev,
        roi=roi,
        avg_finish=avg_finish
    )


def analyze_contest(
    scores: np.ndarray,
    entry_names: List[str],
    entry_fee: float = 1.0,
    payout_structure: Optional[Dict[int, float]] = None
) -> List[ContestAnalysis]:
    """
    Analyze all lineups in a contest.

    Args:
        scores: Score matrix (lineups × iterations)
        entry_names: List of entry names (must match number of lineups)
        entry_fee: Entry fee per lineup
        payout_structure: Optional custom payout structure

    Returns:
        List of ContestAnalysis objects, one per lineup
    """
    num_lineups = scores.shape[0]

    if len(entry_names) != num_lineups:
        raise ValueError(f"entry_names length ({len(entry_names)}) != num_lineups ({num_lineups})")

    # Create payout structure once
    if payout_structure is None:
        payout_structure = create_simple_payout_structure(num_lineups, entry_fee)

    # Analyze each lineup
    results = []
    for lineup_idx in range(num_lineups):
        analysis = analyze_lineup(
            scores=scores,
            lineup_idx=lineup_idx,
            entry_name=entry_names[lineup_idx],
            entry_fee=entry_fee,
            payout_structure=payout_structure
        )
        results.append(analysis)

    return results
