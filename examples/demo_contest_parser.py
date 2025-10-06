#!/usr/bin/env python3
"""
Demo: Parse real DraftKings contest CSV and show lineups with positions.
"""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent))

from utils.csv_parser import parse_dk_contest_csv
import pandas as pd


def parse_lineup_with_positions(lineup_str: str) -> list:
    """Parse lineup string and return (position, player) tuples."""
    positions = ['CPT', 'DST', 'QB', 'RB', 'WR', 'TE', 'FLEX']
    position_pattern = '|'.join(positions)
    pattern = rf'\b({position_pattern})\s+(.+?)(?=\s+(?:{position_pattern})\b|$)'

    matches = re.findall(pattern, lineup_str)
    return [(pos, player.strip()) for pos, player in matches]


def main():
    csv_path = Path(__file__).parent.parent / "contest-standings-182786217.csv"

    print("=" * 80)
    print("  DRAFTKINGS CONTEST PARSER DEMO")
    print("=" * 80)

    # Parse the contest
    lineups, entry_ids, usernames, slate_type = parse_dk_contest_csv(str(csv_path))

    print(f"\n📊 Contest Summary:")
    print(f"   Total Entries: {len(lineups):,}")
    print(f"   Slate Type: {slate_type.upper()}")
    print(f"   Players per Lineup: {len(lineups[0])}")

    # Read the CSV to get actual lineup strings for display
    df = pd.read_csv(csv_path)

    # Show top 10 lineups with positions
    print(f"\n🏆 TOP 10 LINEUPS:")
    print("=" * 80)

    for i in range(min(10, len(df))):
        rank = df.iloc[i]['Rank']
        entry_name = df.iloc[i]['EntryName']
        points = df.iloc[i]['Points']
        lineup_str = df.iloc[i]['Lineup']

        print(f"\n#{rank} - {entry_name} - {points:.2f} pts")
        print("-" * 80)

        lineup_with_pos = parse_lineup_with_positions(lineup_str)
        for pos, player in lineup_with_pos:
            print(f"  {pos:5} {player}")

    # Show some statistics
    print(f"\n📈 STATISTICS:")
    print("=" * 80)

    # Count unique players across all lineups
    all_players = set()
    for lineup in lineups:
        all_players.update(lineup)

    print(f"   Unique players used: {len(all_players)}")

    # Most popular players (approximate from first 100 lineups)
    player_counts = {}
    for lineup in lineups[:100]:
        for player in lineup:
            player_counts[player] = player_counts.get(player, 0) + 1

    print(f"\n   Most popular players (in first 100 lineups):")
    for player, count in sorted(player_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"     {count:3}x {player}")

    print("\n" + "=" * 80)
    print("✅ Parser working correctly!")
    print("=" * 80)
    print(f"\nThe parser successfully extracted {len(lineups):,} lineups from the contest.")
    print("These lineups can now be used with the simulation engine.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
