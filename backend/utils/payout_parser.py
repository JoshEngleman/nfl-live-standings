"""
Payout Structure Parser

Parses payout structure text from DraftKings or other DFS sites.

Supports formats like:
- "1st: $1000.00"
- "2nd-5th: $100.00"
- "6-10: $50"
- "Place 1: $1,000.00"
"""

import re
from typing import List, Tuple


def parse_payout_structure(payout_text: str) -> List[Tuple[int, int, float]]:
    """
    Parse payout structure from text.

    Args:
        payout_text: Multi-line text describing payouts
                    Example:
                        1st: $1,000.00
                        2nd-5th: $100.00
                        6-10: $50.00

                    Or multi-line format:
                        1st
                        $200,000
                        2nd
                        $100,000

    Returns:
        List of (min_rank, max_rank, payout) tuples sorted by rank
        Example: [(1, 1, 1000.0), (2, 5, 100.0), (6, 10, 50.0)]

    Raises:
        ValueError: If text cannot be parsed
    """
    lines = [l.strip() for l in payout_text.strip().split('\n') if l.strip()]
    payouts = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Try single-line patterns first
        # Pattern 1: "1st: $1000.00" or "1st: $1,000.00" (requires colon)
        match = re.match(r'(\d+)(?:st|nd|rd|th)?\s*:\s*\$?([\d,]+\.?\d*)', line, re.IGNORECASE)
        if match:
            rank = int(match.group(1))
            amount = float(match.group(2).replace(',', ''))
            payouts.append((rank, rank, amount))
            i += 1
            continue

        # Pattern 2: "2-5: $100.00" or "2nd-5th: $100.00" (requires colon)
        match = re.match(r'(\d+)(?:st|nd|rd|th)?\s*[\-]\s*(\d+)(?:st|nd|rd|th)?\s*:\s*\$?([\d,]+\.?\d*)', line, re.IGNORECASE)
        if match:
            min_rank = int(match.group(1))
            max_rank = int(match.group(2))
            amount = float(match.group(3).replace(',', ''))
            payouts.append((min_rank, max_rank, amount))
            i += 1
            continue

        # Pattern 3: "Place 1: $1000"
        match = re.match(r'place\s+(\d+)\s*[:\-]\s*\$?([\d,]+\.?\d*)', line, re.IGNORECASE)
        if match:
            rank = int(match.group(1))
            amount = float(match.group(2).replace(',', ''))
            payouts.append((rank, rank, amount))
            i += 1
            continue

        # Pattern 4: "Places 2-5: $100"
        match = re.match(r'places?\s+(\d+)\s*[\-]\s*(\d+)\s*[:\-]\s*\$?([\d,]+\.?\d*)', line, re.IGNORECASE)
        if match:
            min_rank = int(match.group(1))
            max_rank = int(match.group(2))
            amount = float(match.group(3).replace(',', ''))
            payouts.append((min_rank, max_rank, amount))
            i += 1
            continue

        # Multi-line pattern: rank on one line, amount on next
        # Check if current line is a rank and next line is a dollar amount
        rank_match = re.match(r'(\d+)(?:st|nd|rd|th)?$', line, re.IGNORECASE)
        if rank_match and i + 1 < len(lines):
            next_line = lines[i + 1]
            amount_match = re.match(r'\$?([\d,]+\.?\d*)$', next_line)
            if amount_match:
                rank = int(rank_match.group(1))
                amount = float(amount_match.group(1).replace(',', ''))
                payouts.append((rank, rank, amount))
                i += 2  # Skip both lines
                continue

        # Multi-line range pattern: "7th - 8th" on one line, amount on next
        range_match = re.match(r'(\d+)(?:st|nd|rd|th)?\s*[\-]\s*(\d+)(?:st|nd|rd|th)?$', line, re.IGNORECASE)
        if range_match and i + 1 < len(lines):
            next_line = lines[i + 1]
            amount_match = re.match(r'\$?([\d,]+\.?\d*)$', next_line)
            if amount_match:
                min_rank = int(range_match.group(1))
                max_rank = int(range_match.group(2))
                amount = float(amount_match.group(1).replace(',', ''))
                payouts.append((min_rank, max_rank, amount))
                i += 2  # Skip both lines
                continue

        # No match, skip this line
        i += 1

    if not payouts:
        raise ValueError("Could not parse payout structure. Expected format like '1st: $100' or '2-5: $50'")

    # Sort by min_rank
    payouts.sort(key=lambda x: x[0])

    return payouts


def calculate_roi_metrics(
    finish_probabilities: List[float],
    payout_structure: List[Tuple[int, int, float]],
    entry_fee: float
) -> dict:
    """
    Calculate ROI metrics based on finish position probabilities.

    Args:
        finish_probabilities: Probability of finishing at each rank (1-indexed)
                             Example: [0.05, 0.10, 0.15, ...] means 5% chance of 1st, 10% of 2nd, etc.
        payout_structure: List of (min_rank, max_rank, payout) tuples
        entry_fee: Cost to enter the contest

    Returns:
        Dict with:
        - expected_payout: Expected prize money
        - expected_roi: Expected return on investment (dollars)
        - expected_roi_pct: Expected ROI as percentage
        - cash_rate: Probability of winning any money
    """
    if not payout_structure:
        return {
            'expected_payout': 0.0,
            'expected_roi': -entry_fee,
            'expected_roi_pct': -100.0,
            'cash_rate': 0.0
        }

    # Calculate expected payout
    expected_payout = 0.0
    cash_prob = 0.0

    # Build rank -> payout mapping
    rank_payouts = {}
    for min_rank, max_rank, payout in payout_structure:
        for rank in range(min_rank, max_rank + 1):
            rank_payouts[rank] = payout

    # Calculate expected value
    for rank, prob in enumerate(finish_probabilities, start=1):
        if rank in rank_payouts:
            payout = rank_payouts[rank]
            expected_payout += prob * payout
            if payout > 0:
                cash_prob += prob

    # Calculate ROI
    expected_roi = expected_payout - entry_fee
    expected_roi_pct = (expected_roi / entry_fee * 100) if entry_fee > 0 else 0.0

    return {
        'expected_payout': round(expected_payout, 2),
        'expected_roi': round(expected_roi, 2),
        'expected_roi_pct': round(expected_roi_pct, 2),
        'cash_rate': round(cash_prob * 100, 2)
    }


def calculate_roi_with_ties(
    scores: 'np.ndarray',
    lineup_idx: int,
    lineup_matrix: 'np.ndarray',
    payout_structure: List[Tuple[int, int, float]],
    entry_fee: float
) -> dict:
    """
    Calculate ROI metrics accounting for duplicate lineups splitting payouts.

    When duplicate lineups tie, they split the pooled payouts for all positions
    they occupy. For example, if 10 identical lineups tie for 1st, they split
    the payouts for positions 1-10.

    Args:
        scores: Score matrix (lineups × iterations)
        lineup_idx: Index of lineup to analyze
        lineup_matrix: Binary lineup matrix (lineups × players) to identify duplicates
        payout_structure: List of (min_rank, max_rank, payout) tuples
        entry_fee: Cost to enter the contest

    Returns:
        Dict with expected_payout, expected_roi, expected_roi_pct, cash_rate
    """
    import numpy as np

    if not payout_structure:
        return {
            'expected_payout': 0.0,
            'expected_roi': -entry_fee,
            'expected_roi_pct': -100.0,
            'cash_rate': 0.0
        }

    # Build rank -> payout mapping
    rank_payouts = {}
    for min_rank, max_rank, payout in payout_structure:
        for rank in range(min_rank, max_rank + 1):
            rank_payouts[rank] = payout

    # Find duplicate lineups (identical rows in lineup_matrix)
    this_lineup = lineup_matrix[lineup_idx]
    duplicate_indices = []
    for i in range(len(lineup_matrix)):
        if np.array_equal(lineup_matrix[i], this_lineup):
            duplicate_indices.append(i)

    num_duplicates = len(duplicate_indices)

    # Calculate expected payout across all iterations
    num_iterations = scores.shape[1]
    total_payout = 0.0
    cash_iterations = 0

    for iter_idx in range(num_iterations):
        iter_scores = scores[:, iter_idx]
        this_score = iter_scores[lineup_idx]

        # Count how many lineups beat this score
        num_beating = np.sum(iter_scores > this_score)

        # This lineup's rank (1-indexed)
        rank = num_beating + 1

        # Count how many lineups tie with this score (including this one)
        num_tied = np.sum(np.abs(iter_scores - this_score) < 1e-9)

        # Positions occupied by tied lineups: rank through (rank + num_tied - 1)
        tied_positions = range(rank, rank + num_tied)

        # Pool payouts for all tied positions
        pooled_payout = sum(rank_payouts.get(pos, 0.0) for pos in tied_positions)

        # Split among tied lineups
        payout_per_tied = pooled_payout / num_tied if num_tied > 0 else 0.0

        total_payout += payout_per_tied

        if payout_per_tied > 0:
            cash_iterations += 1

    # Expected values
    expected_payout = total_payout / num_iterations
    cash_rate = (cash_iterations / num_iterations) * 100

    # Calculate ROI
    expected_roi = expected_payout - entry_fee
    expected_roi_pct = (expected_roi / entry_fee * 100) if entry_fee > 0 else 0.0

    return {
        'expected_payout': round(expected_payout, 2),
        'expected_roi': round(expected_roi, 2),
        'expected_roi_pct': round(expected_roi_pct, 2),
        'cash_rate': round(cash_rate, 2),
        'num_duplicates': num_duplicates
    }
