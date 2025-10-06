#!/usr/bin/env python3
"""
Integration test / CLI tool for running simulations with real data.

Usage:
    python run_simulation.py --stokastic path/to/stokastic.csv --iterations 10000
"""

import argparse
import sys
import time
from pathlib import Path
import numpy as np

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.csv_parser import (
    parse_stokastic_csv,
    create_player_index_map,
    create_lineup_matrix
)
from services.simulator import run_simulation
from services.contest_analyzer import analyze_contest


def create_sample_main_lineups(player_names, num_lineups=10):
    """
    Create sample main slate lineups (9 players each) for testing.

    Randomly selects 9 players for each lineup.
    """
    lineups = []
    entry_names = []

    for i in range(num_lineups):
        # Randomly sample 9 players
        lineup_players = list(np.random.choice(player_names, size=9, replace=False))
        lineups.append(lineup_players)
        entry_names.append(f"TestEntry_{i+1}")

    return lineups, entry_names


def main():
    parser = argparse.ArgumentParser(description="Run NFL DFS simulation")
    parser.add_argument(
        "--stokastic",
        type=str,
        default="../NFL DK Boom Bust.csv",
        help="Path to Stokastic CSV file"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10000,
        help="Number of Monte Carlo iterations"
    )
    parser.add_argument(
        "--slate",
        type=str,
        default="Main",
        help="Slate to filter (e.g., 'Main', 'Sunday')"
    )
    parser.add_argument(
        "--num-lineups",
        type=int,
        default=20,
        help="Number of sample lineups to generate"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("NFL DFS MONTE CARLO SIMULATION")
    print("=" * 70)

    # Load Stokastic projections
    print(f"\nLoading projections from: {args.stokastic}")
    try:
        df = parse_stokastic_csv(args.stokastic, slate_filter=args.slate)
    except FileNotFoundError:
        print(f"Error: File not found: {args.stokastic}")
        return 1
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return 1

    print(f"Loaded {len(df)} players for '{args.slate}' slate")
    print(f"\nTop 10 projections:")
    print(df[['Name', 'Position', 'Projection', 'Std Dev']].head(10).to_string(index=False))

    # Extract arrays for simulation
    projections = df['Projection'].values
    std_devs = df['Std Dev'].values
    player_names = df['Name'].tolist()

    # Create player index map
    player_index_map = create_player_index_map(df)

    # Generate sample lineups
    print(f"\nGenerating {args.num_lineups} random sample lineups...")
    lineups, entry_names = create_sample_main_lineups(player_names, args.num_lineups)

    # Create lineup matrix
    lineup_matrix = create_lineup_matrix(lineups, player_index_map, len(player_names))
    print(f"Lineup matrix shape: {lineup_matrix.shape}")

    # Run simulation
    print(f"\nRunning simulation with {args.iterations:,} iterations...")
    start_time = time.time()

    scores = run_simulation(
        projections=projections,
        std_devs=std_devs,
        lineup_matrix=lineup_matrix,
        iterations=args.iterations,
        captain_indices=None,  # Main slate, no captain
        seed=None  # Random
    )

    simulation_time = time.time() - start_time
    print(f"✓ Simulation complete in {simulation_time:.2f} seconds")
    print(f"  ({args.iterations / simulation_time:.0f} iterations/second)")

    # Analyze results
    print("\nAnalyzing contest results...")
    start_time = time.time()

    results = analyze_contest(
        scores=scores,
        entry_names=entry_names,
        entry_fee=10.0
    )

    analysis_time = time.time() - start_time
    print(f"✓ Analysis complete in {analysis_time:.2f} seconds")

    # Display top results
    print("\n" + "=" * 70)
    print("TOP 10 LINEUPS BY WIN RATE")
    print("=" * 70)

    # Sort by win rate
    results_sorted = sorted(results, key=lambda x: x.win_rate, reverse=True)[:10]

    print(f"{'Rank':<6} {'Entry':<20} {'Win %':<8} {'Top3 %':<8} {'Cash %':<8} {'ROI %':<10} {'Avg Finish':<12}")
    print("-" * 70)

    for rank, result in enumerate(results_sorted, 1):
        print(
            f"{rank:<6} "
            f"{result.entry_name:<20} "
            f"{result.win_rate*100:>6.2f}% "
            f"{result.top_3_rate*100:>6.2f}% "
            f"{result.cash_rate*100:>6.2f}% "
            f"{result.roi:>8.1f}% "
            f"{result.avg_finish:>11.1f}"
        )

    # Performance summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"Players:           {len(projections):,}")
    print(f"Lineups:           {len(lineups):,}")
    print(f"Iterations:        {args.iterations:,}")
    print(f"Simulation time:   {simulation_time:.2f}s")
    print(f"Analysis time:     {analysis_time:.2f}s")
    print(f"Total time:        {simulation_time + analysis_time:.2f}s")
    print(f"Throughput:        {args.iterations / simulation_time:.0f} iters/sec")

    # Check performance target
    target_time = 5.0  # Target: <5 seconds total
    total_time = simulation_time + analysis_time

    if total_time < target_time:
        print(f"\n✓ PERFORMANCE TARGET MET: {total_time:.2f}s < {target_time:.2f}s")
    else:
        print(f"\n⚠ PERFORMANCE TARGET MISSED: {total_time:.2f}s > {target_time:.2f}s")

    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
