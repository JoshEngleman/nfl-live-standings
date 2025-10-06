#!/usr/bin/env python3
"""
Example of using the simulation engine programmatically.

This shows how to:
1. Load your Stokastic CSV
2. Create custom lineups (or load from DK CSV)
3. Run simulations
4. Analyze results
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.csv_parser import (
    parse_stokastic_csv,
    create_player_index_map,
    create_lineup_matrix
)
from services.simulator import run_simulation
from services.contest_analyzer import analyze_lineup


def main():
    print("=" * 70)
    print("EXAMPLE: Using the Simulation Engine Programmatically")
    print("=" * 70)

    # 1. Load projections
    print("\n1. Loading Stokastic projections...")
    df = parse_stokastic_csv("../NFL DK Boom Bust.csv", slate_filter="Main")
    print(f"   Loaded {len(df)} players")

    # 2. Extract data
    projections = df['Projection'].values
    std_devs = df['Std Dev'].values
    player_names = df['Name'].tolist()
    player_index_map = create_player_index_map(df)

    # 3. Create a custom lineup (pick your own players!)
    print("\n2. Creating a custom lineup...")
    my_lineup = [
        "Justin Fields",      # QB
        "De'Von Achane",      # RB
        "Jonathan Taylor",    # RB
        "Garrett Wilson",     # WR
        "Jaxon Smith-Njigba", # WR
        "Amon-Ra St. Brown",  # WR
        "Trey McBride",       # TE
        "Breece Hall",        # FLEX
        "Jets"                # DST
    ]

    print(f"   My lineup: {', '.join(my_lineup)}")

    # Also create a few opponent lineups
    opponent_lineups = [
        ["Jalen Hurts", "Saquon Barkley", "Jahmyr Gibbs", "Ja'Marr Chase",
         "Emeka Egbuka", "Chris Godwin Jr.", "Travis Kelce", "George Pickens", "Lions"],
        ["Daniel Jones", "Cam Skattebo", "Javonte Williams", "Michael Pittman Jr.",
         "Jaylen Waddle", "Chris Olave", "Tyler Warren", "Nico Collins", "Saints"],
    ]

    all_lineups = [my_lineup] + opponent_lineups
    entry_names = ["MY_LINEUP"] + [f"Opponent_{i+1}" for i in range(len(opponent_lineups))]

    # 4. Create lineup matrix
    print("\n3. Creating lineup matrix...")
    lineup_matrix = create_lineup_matrix(all_lineups, player_index_map, len(player_names))

    # 5. Run simulation
    print("\n4. Running Monte Carlo simulation...")
    iterations = 10000

    scores = run_simulation(
        projections=projections,
        std_devs=std_devs,
        lineup_matrix=lineup_matrix,
        iterations=iterations,
        captain_indices=None,  # Main slate
        seed=None
    )

    print(f"   ✓ Simulated {iterations:,} iterations")

    # 6. Analyze YOUR lineup
    print("\n5. Analyzing YOUR lineup...")
    my_analysis = analyze_lineup(
        scores=scores,
        lineup_idx=0,  # Your lineup is first
        entry_name="MY_LINEUP",
        entry_fee=10.0
    )

    print("\n" + "=" * 70)
    print("YOUR LINEUP ANALYSIS")
    print("=" * 70)
    print(f"Win Rate:       {my_analysis.win_rate * 100:.2f}%")
    print(f"Top 3 Rate:     {my_analysis.top_3_rate * 100:.2f}%")
    print(f"Cash Rate:      {my_analysis.cash_rate * 100:.2f}%")
    print(f"Expected Value: ${my_analysis.expected_value:.2f}")
    print(f"ROI:            {my_analysis.roi:.1f}%")
    print(f"Avg Finish:     {my_analysis.avg_finish:.1f}")

    # 7. Score distribution
    print("\n" + "=" * 70)
    print("SCORE DISTRIBUTION")
    print("=" * 70)
    my_scores = scores[0, :]
    print(f"Min Score:      {np.min(my_scores):.1f}")
    print(f"25th Percentile: {np.percentile(my_scores, 25):.1f}")
    print(f"Median:         {np.median(my_scores):.1f}")
    print(f"Mean:           {np.mean(my_scores):.1f}")
    print(f"75th Percentile: {np.percentile(my_scores, 75):.1f}")
    print(f"Max Score:      {np.max(my_scores):.1f}")
    print(f"Std Dev:        {np.std(my_scores):.1f}")

    # 8. Head-to-head comparison
    print("\n" + "=" * 70)
    print("HEAD-TO-HEAD vs OPPONENTS")
    print("=" * 70)
    for i, opponent_name in enumerate(entry_names[1:], start=1):
        opponent_scores = scores[i, :]
        wins = np.sum(my_scores > opponent_scores)
        win_rate = wins / iterations
        print(f"{opponent_name}: Win {win_rate*100:.1f}% of the time")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
