#!/usr/bin/env python3
"""
Load a real DraftKings contest and start monitoring it with live updates.

This script:
1. Loads your actual DraftKings contest CSV
2. Loads Stokastic projections
3. Runs pre-game simulation
4. Registers the contest with the state manager
5. Starts the background updater for live ESPN stats
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

import pandas as pd
from datetime import datetime

from utils.csv_parser import (
    parse_stokastic_csv,
    parse_dk_contest_csv,
    create_lineup_matrix,
    create_player_index_map
)
from services.simulator import run_simulation
from services.contest_state_manager import get_state_manager
from services.live_updater_service import get_updater_service
from services.contest_analyzer import analyze_lineup


def main():
    print("=" * 70)
    print("🏈 NFL DFS LIVE STANDINGS - REAL CONTEST LOADER")
    print("=" * 70)

    # File paths
    stokastic_path = Path(__file__).parent / "NFL DK Boom Bust.csv"
    contest_path = Path(__file__).parent / "contest-standings-182786217.csv"

    # Step 1: Load Stokastic projections
    print(f"\n📂 Loading Stokastic projections from: {stokastic_path.name}")
    df = parse_stokastic_csv(str(stokastic_path), slate_filter=None)  # Load all slates
    print(f"✅ Loaded {len(df)} players")

    # Show available slates
    slates = df['Slate'].unique() if 'Slate' in df.columns else ['Unknown']
    print(f"   Available slates: {', '.join(slates)}")

    # Step 2: Load DraftKings contest
    print(f"\n📂 Loading DraftKings contest from: {contest_path.name}")
    lineups, entry_ids, usernames, slate_type = parse_dk_contest_csv(str(contest_path))
    print(f"✅ Loaded {len(lineups)} lineups")
    print(f"   Slate type: {slate_type}")
    print(f"   Sample entries: {', '.join(str(e) for e in entry_ids[:3])}...")

    # Step 3: Create player index map and lineup matrix
    print(f"\n🔗 Creating lineup matrix...")
    player_index_map = create_player_index_map(df)
    lineup_matrix = create_lineup_matrix(lineups, player_index_map, len(df))
    print(f"✅ Matrix shape: {lineup_matrix.shape[0]} lineups × {lineup_matrix.shape[1]} players")

    # Step 4: Run pre-game simulation
    print(f"\n⚡ Running pre-game simulation (10,000 iterations)...")
    iterations = 10000

    # Determine captain indices for showdown
    captain_indices = None
    if slate_type == 'Showdown':
        import numpy as np
        captain_indices = np.zeros(lineup_matrix.shape[0], dtype=int)
        print("   Showdown slate detected - applying 1.5× captain multiplier")

    pre_game_scores = run_simulation(
        projections=df['Projection'].values,
        std_devs=df['Std Dev'].values,
        lineup_matrix=lineup_matrix,
        iterations=iterations,
        captain_indices=captain_indices
    )
    print(f"✅ Simulation complete!")

    # Show sample results
    print(f"\n📊 Top 5 Pre-Game Projections:")
    for i in range(min(5, len(lineups))):
        result = analyze_lineup(
            scores=pre_game_scores,
            lineup_idx=i,
            entry_name=str(entry_ids[i]),
            entry_fee=10.0  # Adjust if needed
        )
        print(f"   {i+1}. {str(entry_ids[i]):20s} Win Rate: {result.win_rate*100:6.2f}%  Avg Score: {result.avg_finish:6.1f}")

    # Step 5: Register with state manager
    print(f"\n🗂️  Registering contest with state manager...")
    state_manager = get_state_manager()

    contest_id = f"contest_{contest_path.stem}"

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=df,
        lineup_matrix=lineup_matrix,
        entry_ids=[str(e) for e in entry_ids],
        usernames=usernames,
        slate_type=slate_type,
        entry_fee=10.0,  # Adjust if needed
        iterations=iterations
    )

    # Store pre-game scores
    state_manager.update_scores(contest_id, pre_game_scores, is_pre_game=True)
    print(f"✅ Contest registered: {contest_id}")

    # Step 6: Start background updater
    print(f"\n🔄 Starting background updater (2-minute intervals)...")
    updater_service = get_updater_service(
        update_interval_seconds=120,
        auto_start=False
    )

    updater_service.start()
    print(f"✅ Background updater started!")

    # Summary
    print("\n" + "=" * 70)
    print("✅ CONTEST LOADED SUCCESSFULLY!")
    print("=" * 70)
    print(f"\n📊 Contest Details:")
    print(f"   Contest ID: {contest_id}")
    print(f"   Lineups: {len(lineups)}")
    print(f"   Players: {len(df)}")
    print(f"   Slate: {slate_type}")
    print(f"   Pre-game simulation: Complete")
    print(f"   Background updater: Running (every 2 min)")

    print(f"\n🌐 View in Dashboard:")
    print(f"   http://localhost:5173")

    print(f"\n💡 What's happening now:")
    print(f"   • Background updater fetches live ESPN stats every 2 minutes")
    print(f"   • Dashboard shows real-time updates via WebSocket")
    print(f"   • Pre-game vs Live scores update automatically")
    print(f"   • Win rates recalculated with each update")

    print(f"\n⏹️  Press Ctrl+C to stop the updater")
    print("=" * 70)

    # Keep running
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping updater...")
        updater_service.stop()
        print("✅ Done!")


if __name__ == "__main__":
    main()
