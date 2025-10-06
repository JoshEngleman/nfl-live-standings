#!/usr/bin/env python3
"""
Show users with multiple entries to demonstrate clean username parsing.
"""

import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from utils.csv_parser import parse_dk_contest_csv


def main():
    csv_path = Path(__file__).parent.parent / "contest-standings-182786217.csv"

    print("=" * 80)
    print("  MULTI-ENTRY USERS DEMO")
    print("  Showing how usernames are cleaned and entries are tracked")
    print("=" * 80)

    # Parse the contest
    lineups, entry_ids, usernames, slate_type = parse_dk_contest_csv(str(csv_path))

    # Count entries per username
    username_counts = Counter(usernames)

    # Find users with multiple entries
    multi_entry_users = {user: count for user, count in username_counts.items() if count > 1}

    print(f"\n📊 Summary:")
    print(f"   Total entries: {len(lineups):,}")
    print(f"   Unique users: {len(username_counts)}")
    print(f"   Users with multiple entries: {len(multi_entry_users)}")

    # Show top users by entry count
    print(f"\n🏆 TOP USERS BY NUMBER OF ENTRIES:")
    print("-" * 80)

    for i, (user, count) in enumerate(sorted(multi_entry_users.items(), key=lambda x: x[1], reverse=True)[:10], 1):
        print(f"   {i:2}. {user:30} {count:3} entries")

    # Show example: Find all entries for a specific user
    example_user = sorted(multi_entry_users.items(), key=lambda x: x[1], reverse=True)[0][0]

    print(f"\n🔍 EXAMPLE: All entries for '{example_user}':")
    print("-" * 80)

    user_entries = [(i, entry_ids[i], lineups[i]) for i in range(len(usernames)) if usernames[i] == example_user]

    for idx, (position, entry_id, lineup) in enumerate(user_entries[:5], 1):
        print(f"\n   Entry {idx} of {len(user_entries)}:")
        print(f"   EntryId: {entry_id}")
        print(f"   Lineup: {', '.join(lineup[:4])}...")

    print(f"\n💡 KEY INSIGHT:")
    print("   - Username: Clean, no (X/Y) suffix")
    print("   - EntryId: Unique identifier for each entry")
    print("   - This allows tracking multiple entries per user correctly")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
