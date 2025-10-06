#!/usr/bin/env python3
"""
Demo: Phase 3 Automation

Demonstrates the automated live update system with background scheduler.

This script:
1. Loads contest data (Stokastic + DraftKings CSV)
2. Runs initial pre-game simulation
3. Starts background scheduler for automatic updates every 2 minutes
4. Monitors progress and displays updates in real-time

Usage:
    python demo_automation.py

Requirements:
    - Stokastic CSV: "NFL DK Boom Bust.csv" in project root
    - Optional: DraftKings contest CSV for real contest tracking
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import time
import numpy as np
from datetime import datetime

from utils.csv_parser import (
    parse_stokastic_csv,
    create_lineup_matrix,
    create_player_index_map
)
from services.simulator import run_simulation
from services.contest_analyzer import analyze_lineup
from services.contest_state_manager import get_state_manager
from services.live_updater_service import get_updater_service


def print_separator(char='=', length=70):
    """Print a separator line."""
    print(char * length)


def print_update_callback(contest_id: str, result: dict):
    """
    Callback function for displaying updates.

    Args:
        contest_id: ID of updated contest
        result: Update result dictionary
    """
    print_separator('─')
    print(f"🔄 AUTOMATED UPDATE - {datetime.now().strftime('%H:%M:%S')}")
    print(f"Contest: {contest_id}")
    print(f"Live games: {result.get('live_games', 0)}")
    print(f"Players matched: {result.get('players_matched', 0)}")
    print(f"Match rate: {result.get('match_rate', 0):.1f}%")
    print(f"Duration: {result.get('duration_seconds', 0):.1f}s")
    print_separator('─')


def main():
    """Run the automation demo."""
    print_separator()
    print("🤖 NFL DFS AUTOMATION DEMO - PHASE 3")
    print_separator()

    # Step 1: Load Stokastic data
    print("\n📂 Step 1: Loading Stokastic projections...")
    stokastic_path = Path(__file__).parent.parent / "NFL DK Boom Bust.csv"

    if not stokastic_path.exists():
        print(f"❌ Error: {stokastic_path} not found")
        print("   Download from Stokastic.com and place in project root")
        return

    df = parse_stokastic_csv(str(stokastic_path), slate_filter="Main")
    player_index_map = create_player_index_map(df)

    print(f"✅ Loaded {len(df)} players for Main slate")

    # Step 2: Create sample lineups
    print("\n🏈 Step 2: Creating sample lineups...")
    # For demo, create 3 random lineups
    num_lineups = 3
    lineup_size = 9  # Main slate

    np.random.seed(42)
    lineups = []
    for i in range(num_lineups):
        # Random lineup (simplified - doesn't follow DK rules)
        lineup_indices = np.random.choice(len(df), lineup_size, replace=False)
        lineup = df.iloc[lineup_indices]['Name'].tolist()
        lineups.append(lineup)

        print(f"\n   Lineup {i+1}:")
        for j, player in enumerate(lineup, 1):
            print(f"      {j}. {player}")

    # Create lineup matrix
    lineup_matrix = create_lineup_matrix(lineups, player_index_map, len(df))

    # Step 3: Run pre-game simulation
    print("\n⚡ Step 3: Running pre-game simulation...")
    iterations = 10000

    pre_game_scores = run_simulation(
        projections=df['Projection'].values,
        std_devs=df['Std Dev'].values,
        lineup_matrix=lineup_matrix,
        iterations=iterations
    )

    print(f"✅ Completed {iterations:,} iterations")

    # Analyze pre-game results
    print("\n📊 Pre-Game Results:")
    for i, lineup in enumerate(lineups):
        result = analyze_lineup(
            scores=pre_game_scores,
            lineup_idx=i,
            entry_name=f"LINEUP_{i+1}",
            entry_fee=10.0
        )
        print(f"\n   Lineup {i+1}:")
        print(f"      Win Rate: {result.win_rate * 100:6.2f}%")
        print(f"      Top 3 Rate: {result.top3_rate * 100:6.2f}%")
        print(f"      Avg Finish: {result.avg_finish:6.1f}")
        print(f"      Expected Value: ${result.expected_value:6.2f}")

    # Step 4: Register contest with state manager
    print("\n🗂️  Step 4: Registering contest with state manager...")
    state_manager = get_state_manager()

    contest_id = "demo_contest_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    entry_ids = [f"ENTRY_{i+1}" for i in range(num_lineups)]
    usernames = [f"User{i+1}" for i in range(num_lineups)]

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=df,
        lineup_matrix=lineup_matrix,
        entry_ids=entry_ids,
        usernames=usernames,
        slate_type="Main",
        entry_fee=10.0,
        iterations=iterations
    )

    # Store pre-game scores
    state_manager.update_scores(contest_id, pre_game_scores, is_pre_game=True)

    print(f"✅ Contest registered: {contest_id}")

    # Step 5: Start background updater
    print("\n🔄 Step 5: Starting background updater...")
    updater_service = get_updater_service(
        update_interval_seconds=120,  # 2 minutes
        auto_start=False
    )

    # Register callback for console output
    updater_service.add_update_callback(print_update_callback)

    updater_service.start()
    print("✅ Background updater started (2 minute intervals)")

    # Get status
    status = updater_service.get_status()
    print(f"\n📡 Updater Status:")
    print(f"   Running: {status['is_running']}")
    print(f"   Active contests: {status['active_contests']}")
    print(f"   Next update: {status['next_run']}")

    # Step 6: Monitor for updates
    print("\n👀 Step 6: Monitoring for updates...")
    print_separator()
    print("\nWaiting for automated updates (every 2 minutes)...")
    print("Press Ctrl+C to stop\n")
    print_separator()

    try:
        # Keep script running
        update_count = 0
        max_updates = 5  # Stop after 5 updates for demo

        while update_count < max_updates:
            time.sleep(1)  # Check every second

            # Check if update occurred
            state = state_manager.get_contest(contest_id)
            if state and state.update_count > update_count:
                update_count = state.update_count

                # Display comparison if we have both pre-game and live
                if state.pre_game_scores is not None and state.live_scores is not None:
                    print("\n📈 PRE-GAME vs LIVE COMPARISON:")
                    print_separator('─')

                    for i in range(num_lineups):
                        # Pre-game stats
                        pre_result = analyze_lineup(
                            scores=state.pre_game_scores,
                            lineup_idx=i,
                            entry_name=f"LINEUP_{i+1}",
                            entry_fee=10.0
                        )

                        # Live stats
                        live_result = analyze_lineup(
                            scores=state.live_scores,
                            lineup_idx=i,
                            entry_name=f"LINEUP_{i+1}",
                            entry_fee=10.0
                        )

                        print(f"\n   Lineup {i+1}:")
                        print(f"      Metric          Pre-Game    Live        Change")
                        print(f"      Win Rate        {pre_result.win_rate*100:6.2f}%    {live_result.win_rate*100:6.2f}%    {(live_result.win_rate - pre_result.win_rate)*100:+6.2f}%")
                        print(f"      Expected Value  ${pre_result.expected_value:6.2f}    ${live_result.expected_value:6.2f}    ${live_result.expected_value - pre_result.expected_value:+6.2f}")

                    print_separator('─')

    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")

    finally:
        # Step 7: Cleanup
        print("\n🧹 Step 7: Cleaning up...")
        updater_service.stop()
        print("✅ Background updater stopped")

        # Optionally deactivate contest
        state_manager.deactivate_contest(contest_id)
        print(f"✅ Contest {contest_id} deactivated")

        print_separator()
        print("✅ AUTOMATION DEMO COMPLETE")
        print_separator()

        # Final summary
        final_state = state_manager.get_contest(contest_id)
        if final_state:
            print(f"\nFinal Stats:")
            print(f"   Total updates: {final_state.update_count}")
            print(f"   Last update: {final_state.last_update}")
            print(f"   Duration: {(final_state.last_update - final_state.created_at).total_seconds() / 60:.1f} minutes")


if __name__ == "__main__":
    main()
