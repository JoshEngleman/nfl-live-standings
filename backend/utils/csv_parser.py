"""
CSV parsers for Stokastic projections and DraftKings contest exports.

Performance notes:
- Use pandas for efficient CSV reading
- Convert to NumPy arrays early for downstream processing
- Minimize DataFrame operations after initial parsing
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from pathlib import Path


def parse_stokastic_csv(file_path: str, slate_filter: Optional[str] = None) -> pd.DataFrame:
    """
    Parse Stokastic projections CSV.

    Args:
        file_path: Path to Stokastic CSV file
        slate_filter: Optional slate to filter by (e.g., "Main", "Sunday")

    Returns:
        DataFrame with columns: Name, Position, Salary, Projection, Std Dev, Slate
        Additional columns preserved if present: Ceiling, Boom%, Bust%, Own%

    Note: Players with std_dev <= 0.2 are considered finished games (actual scores).
    """
    df = pd.read_csv(file_path)

    # Required columns
    required_cols = ['Name', 'Position', 'Salary', 'Projection', 'Std Dev', 'Slate']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Clean salary column (remove commas if present)
    if df['Salary'].dtype == 'object':
        df['Salary'] = df['Salary'].str.replace(',', '').astype(int)

    # Filter by slate if specified
    if slate_filter:
        df = df[df['Slate'] == slate_filter].copy()

    # Sort by projection descending for easier debugging
    df = df.sort_values('Projection', ascending=False).reset_index(drop=True)

    return df


def parse_lineup_string(lineup_str: str) -> List[str]:
    """
    Parse DraftKings lineup string with position prefixes.

    Args:
        lineup_str: Space-separated string like "DST Saints FLEX Jonathan Taylor QB Justin Fields..."

    Returns:
        List of player names in order (without position prefixes)

    Example:
        Input: "DST Saints FLEX Jonathan Taylor QB Justin Fields"
        Output: ["Saints", "Jonathan Taylor", "Justin Fields"]
    """
    import re

    # Position keywords that appear in lineups
    positions = ['CPT', 'DST', 'QB', 'RB', 'WR', 'TE', 'FLEX']

    # Build regex pattern to match position followed by player name
    # Negative lookahead ensures we stop at the next position keyword
    position_pattern = '|'.join(positions)
    pattern = rf'\b({position_pattern})\s+(.+?)(?=\s+(?:{position_pattern})\b|$)'

    matches = re.findall(pattern, lineup_str)

    # Extract player names (second group in each match) and clean whitespace
    players = [match[1].strip() for match in matches]

    return players


def parse_dk_contest_csv(file_path: str) -> Tuple[List[List[str]], List[int], List[str], str]:
    """
    Parse DraftKings contest export CSV.

    Detects slate type (main vs showdown) and extracts lineups.

    Args:
        file_path: Path to DK contest CSV file

    Returns:
        Tuple of:
        - lineups: List of lineups, each lineup is list of player names
        - entry_ids: List of EntryId for each lineup (unique identifier)
        - usernames: List of usernames for each lineup (cleaned, without lineup count)
        - slate_type: "main" or "showdown"

    Format notes:
        - Real DK contest CSVs have a "Lineup" column (column 5)
        - Lineup format: "DST Saints FLEX Jonathan Taylor QB Justin Fields..."
        - Position prefixes: DST, QB, RB, WR, TE, FLEX (main) or CPT + FLEX (showdown)
        - EntryName format: "username" or "username (X/Y)" where X/Y indicates lineup X of Y total

    Raises:
        ValueError: If CSV format is invalid or unrecognized
    """
    df = pd.read_csv(file_path)

    # Check if this is the real DK export format (has "Lineup" column)
    if 'Lineup' in df.columns:
        # Real DK contest export format
        # Filter out rows with missing lineup data
        df = df[df['Lineup'].notna()].copy()

        lineups = []
        for lineup_str in df['Lineup']:
            players = parse_lineup_string(lineup_str)
            lineups.append(players)

        # Detect slate type by lineup length
        if lineups:
            first_lineup_len = len(lineups[0])
            if first_lineup_len == 9:
                slate_type = "main"
            elif first_lineup_len == 6:
                slate_type = "showdown"
            else:
                slate_type = "unknown"
                print(f"Warning: Unusual lineup length: {first_lineup_len}. Expected 9 (main) or 6 (showdown).")
        else:
            raise ValueError("No lineups found in CSV")

        # Extract entry IDs (unique identifier)
        if 'EntryId' in df.columns:
            entry_ids = df['EntryId'].astype(int).tolist()
        else:
            entry_ids = list(range(1, len(lineups) + 1))

        # Extract and clean usernames (remove lineup count suffix)
        if 'EntryName' in df.columns:
            raw_entry_names = df['EntryName'].tolist()
            usernames = []
            for name in raw_entry_names:
                # Remove " (X/Y)" suffix if present
                # Example: "Mainpackerfan124 (34/150)" -> "Mainpackerfan124"
                clean_name = name.split(' (')[0] if ' (' in name else name
                usernames.append(clean_name)
        else:
            usernames = [f"Entry_{i+1}" for i in range(len(lineups))]

    else:
        # Legacy format or custom format with separate position columns
        # Try to detect slate type by looking for position columns
        if 'CPT' in df.columns:
            slate_type = "showdown"
            position_cols = ['CPT', 'FLEX1', 'FLEX2', 'FLEX3', 'FLEX4', 'FLEX5']
        elif 'QB' in df.columns:
            slate_type = "main"
            position_cols = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE', 'FLEX', 'DST']
        else:
            # Fallback: Try to detect by counting player columns
            player_cols = [col for col in df.columns if not col.endswith('Id') and col not in ['EntryId', 'EntryName', 'Rank', 'Points']]
            if len(player_cols) == 6:
                slate_type = "showdown"
                position_cols = player_cols[:6]  # Use first 6 player columns
            elif len(player_cols) == 9:
                slate_type = "main"
                position_cols = player_cols[:9]
            else:
                raise ValueError(f"Cannot determine slate type. Found {len(player_cols)} player columns")

        # Extract lineups
        lineups = []
        for _, row in df.iterrows():
            lineup = [row[col] for col in position_cols if pd.notna(row.get(col))]
            if lineup:  # Only add non-empty lineups
                lineups.append(lineup)

        # Extract entry IDs
        if 'EntryId' in df.columns:
            entry_ids = df['EntryId'].astype(int).tolist()
        else:
            entry_ids = list(range(1, len(lineups) + 1))

        # Extract and clean usernames
        if 'EntryName' in df.columns:
            raw_entry_names = df['EntryName'].tolist()
            usernames = []
            for name in raw_entry_names:
                clean_name = name.split(' (')[0] if ' (' in name else name
                usernames.append(clean_name)
        elif 'User' in df.columns:
            raw_entry_names = df['User'].tolist()
            usernames = []
            for name in raw_entry_names:
                clean_name = name.split(' (')[0] if ' (' in name else name
                usernames.append(clean_name)
        else:
            # Generate default names
            usernames = [f"Entry_{i+1}" for i in range(len(lineups))]

    return lineups, entry_ids, usernames, slate_type


def create_player_index_map(stokastic_df: pd.DataFrame) -> Dict[str, int]:
    """
    Create mapping from player name to index in the projections DataFrame.

    Args:
        stokastic_df: Stokastic projections DataFrame

    Returns:
        Dictionary mapping player name -> index
    """
    return {name: idx for idx, name in enumerate(stokastic_df['Name'])}


def create_lineup_matrix(
    lineups: List[List[str]],
    player_index_map: Dict[str, int],
    num_players: int
) -> np.ndarray:
    """
    Create binary lineup matrix for matrix multiplication.

    Args:
        lineups: List of lineups, each lineup is list of player names
        player_index_map: Mapping from player name to index
        num_players: Total number of players in pool

    Returns:
        Binary matrix of shape (num_lineups, num_players)
        Entry [i, j] = 1 if player j is in lineup i, else 0

    Performance: Pre-allocate matrix for speed.
    """
    num_lineups = len(lineups)
    lineup_matrix = np.zeros((num_lineups, num_players), dtype=np.int8)

    for lineup_idx, lineup in enumerate(lineups):
        for player_name in lineup:
            if player_name in player_index_map:
                player_idx = player_index_map[player_name]
                lineup_matrix[lineup_idx, player_idx] = 1
            # Silently skip players not found (e.g., DST naming differences)

    return lineup_matrix


def extract_captain_indices(
    lineups: List[List[str]],
    player_index_map: Dict[str, int]
) -> np.ndarray:
    """
    Extract captain player indices for showdown slates.

    Args:
        lineups: List of showdown lineups (captain is first player in each)
        player_index_map: Mapping from player name to index

    Returns:
        Array of shape (num_lineups,) containing player index of captain for each lineup

    Raises:
        ValueError: If captain not found in player pool
    """
    captain_indices = []

    for lineup in lineups:
        captain_name = lineup[0]  # Captain is first in showdown lineup
        if captain_name not in player_index_map:
            raise ValueError(f"Captain player '{captain_name}' not found in projections")
        captain_indices.append(player_index_map[captain_name])

    return np.array(captain_indices, dtype=np.int32)


def validate_lineup_matrix(lineup_matrix: np.ndarray, expected_players_per_lineup: int) -> None:
    """
    Validate that lineup matrix has correct number of players per lineup.

    Args:
        lineup_matrix: Binary lineup matrix
        expected_players_per_lineup: Expected count (9 for main, 6 for showdown)

    Raises:
        ValueError: If any lineup has incorrect player count
    """
    players_per_lineup = lineup_matrix.sum(axis=1)
    invalid_lineups = np.where(players_per_lineup != expected_players_per_lineup)[0]

    if len(invalid_lineups) > 0:
        raise ValueError(
            f"Invalid lineups found. Expected {expected_players_per_lineup} players per lineup. "
            f"Lineups {invalid_lineups.tolist()} have counts: {players_per_lineup[invalid_lineups].tolist()}"
        )
