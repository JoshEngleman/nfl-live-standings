#!/usr/bin/env python3
"""
Quick test of the DraftKings contest CSV parser.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.csv_parser import parse_dk_contest_csv

def test_contest_parser():
    """Test parsing the real contest CSV."""

    csv_path = Path(__file__).parent.parent / "contest-standings-182786217.csv"

    print("=" * 70)
    print("TESTING DRAFTKINGS CONTEST CSV PARSER")
    print("=" * 70)

    print(f"\nParsing: {csv_path.name}")

    try:
        lineups, entry_ids, usernames, slate_type = parse_dk_contest_csv(str(csv_path))

        print(f"\n✓ Successfully parsed!")
        print(f"  Slate Type: {slate_type}")
        print(f"  Total Lineups: {len(lineups)}")
        print(f"  Players per lineup: {len(lineups[0]) if lineups else 0}")

        # Show first 5 lineups
        print(f"\n📋 FIRST 5 LINEUPS:")
        print("-" * 70)

        for i in range(min(5, len(lineups))):
            print(f"\n{i+1}. {usernames[i]} (EntryId: {entry_ids[i]})")
            for j, player in enumerate(lineups[i]):
                pos_labels = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST'] if slate_type == "main" else ['CPT', 'FLEX', 'FLEX', 'FLEX', 'FLEX', 'FLEX']
                print(f"   {pos_labels[j]:5} {player}")

        # Show lineup length distribution
        lineup_lengths = [len(lineup) for lineup in lineups]
        unique_lengths = set(lineup_lengths)

        print(f"\n📊 LINEUP LENGTH DISTRIBUTION:")
        for length in sorted(unique_lengths):
            count = lineup_lengths.count(length)
            print(f"   {length} players: {count} lineups")

        # Check for any issues
        expected_length = 9 if slate_type == "main" else 6
        invalid = [i for i, lineup in enumerate(lineups) if len(lineup) != expected_length]

        if invalid:
            print(f"\n⚠️  WARNING: {len(invalid)} lineups have unexpected length")
            print(f"   Expected: {expected_length}, Found issues at indices: {invalid[:10]}")
        else:
            print(f"\n✅ All lineups have correct length ({expected_length})")

        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_contest_parser()
    sys.exit(0 if success else 1)
