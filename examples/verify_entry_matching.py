#!/usr/bin/env python3
"""
Verify that entry names are correctly matched to lineups.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from utils.csv_parser import parse_dk_contest_csv, parse_lineup_string


def verify_entry_matching():
    """Verify entry names match lineups correctly."""

    csv_path = Path(__file__).parent.parent / "contest-standings-182786217.csv"

    print("=" * 80)
    print("VERIFYING ENTRY NAME MATCHING")
    print("=" * 80)

    # Parse using our function
    lineups, entry_ids, usernames, slate_type = parse_dk_contest_csv(str(csv_path))

    # Read raw CSV and filter same as parser
    df = pd.read_csv(csv_path)
    df_raw_count = len(df)
    df = df[df['Lineup'].notna()].copy()

    print(f"\n📊 Counts:")
    print(f"   DataFrame rows (raw): {df_raw_count}")
    print(f"   DataFrame rows (with lineup): {len(df)}")
    print(f"   Parsed lineups: {len(lineups)}")
    print(f"   Entry IDs: {len(entry_ids)}")
    print(f"   Usernames: {len(usernames)}")

    if df_raw_count > len(df):
        print(f"   ℹ️  Note: {df_raw_count - len(df)} rows filtered out (missing lineup data)")

    # Check if counts match
    if len(lineups) == len(entry_ids) == len(usernames) == len(df):
        print(f"   ✅ All counts match!")
    else:
        print(f"   ❌ MISMATCH! Counts don't align")
        return False

    # Verify first 10 entries match
    print(f"\n🔍 VERIFYING FIRST 10 ENTRIES:")
    print("-" * 80)

    all_match = True
    for i in range(min(10, len(df))):
        # Get from DataFrame
        df_entry_name_raw = df.iloc[i]['EntryName']
        df_entry_id = df.iloc[i]['EntryId']
        df_lineup_str = df.iloc[i]['Lineup']
        df_rank = df.iloc[i]['Rank']
        df_points = df.iloc[i]['Points']

        # Get from parser
        parsed_entry_id = entry_ids[i]
        parsed_username = usernames[i]
        parsed_lineup = lineups[i]

        # Clean the expected username (remove (X/Y) suffix)
        expected_username = df_entry_name_raw.split(' (')[0] if ' (' in df_entry_name_raw else df_entry_name_raw

        # Parse the lineup from DF
        expected_lineup = parse_lineup_string(df_lineup_str)

        # Check if they match
        id_match = df_entry_id == parsed_entry_id
        username_match = expected_username == parsed_username
        lineup_match = expected_lineup == parsed_lineup

        status = "✅" if (id_match and username_match and lineup_match) else "❌"

        print(f"\n{status} Entry {i+1} (Rank #{df_rank}):")
        print(f"   EntryId: {parsed_entry_id}")
        if not id_match:
            print(f"   ⚠️  Expected EntryId: {df_entry_id}")
            all_match = False

        print(f"   Username: {parsed_username}")
        print(f"   (Raw EntryName: {df_entry_name_raw})")
        if not username_match:
            print(f"   ⚠️  Expected username: {expected_username}")
            all_match = False

        print(f"   Points: {df_points}")
        print(f"   Lineup ({len(parsed_lineup)} players): {', '.join(parsed_lineup[:3])}...")

        if not lineup_match:
            print(f"   ⚠️  Lineup mismatch!")
            print(f"   Expected: {', '.join(expected_lineup[:3])}...")
            all_match = False

    # Spot check middle and end
    print(f"\n🔍 SPOT CHECKS:")
    print("-" * 80)

    check_indices = [100, 500, 1000, 5000, len(df) - 1]

    for idx in check_indices:
        if idx >= len(df):
            continue

        df_entry_name_raw = df.iloc[idx]['EntryName']
        df_entry_id = df.iloc[idx]['EntryId']
        parsed_entry_id = entry_ids[idx]
        parsed_username = usernames[idx]
        df_lineup_str = df.iloc[idx]['Lineup']
        parsed_lineup = lineups[idx]
        expected_lineup = parse_lineup_string(df_lineup_str)
        expected_username = df_entry_name_raw.split(' (')[0] if ' (' in df_entry_name_raw else df_entry_name_raw

        match = (df_entry_id == parsed_entry_id) and (expected_username == parsed_username) and (expected_lineup == parsed_lineup)
        status = "✅" if match else "❌"

        print(f"{status} Index {idx}: EntryId={parsed_entry_id}, Username={parsed_username}")

        if not match:
            all_match = False

    print(f"\n" + "=" * 80)
    if all_match:
        print("✅ ALL ENTRIES MATCHED CORRECTLY!")
        print("   - Entry IDs properly extracted and matched")
        print("   - Usernames cleaned (removed lineup count suffix)")
        print("   - Lineups correctly linked to each entry")
    else:
        print("❌ MISMATCHES FOUND!")
        print("   Entry data may not be correctly parsed.")

    print("=" * 80)

    return all_match


if __name__ == "__main__":
    success = verify_entry_matching()
    sys.exit(0 if success else 1)
