#!/usr/bin/env python3
"""
Demo: Live NFL DFS Simulation

Shows the power of live pro-rating with mock halftime stats.

This demonstrates:
1. Pre-game baseline simulation
2. Halftime update with actual stats
3. Pro-rated projections
4. Live simulation with updated win rates
5. How individual player performances affect your lineup's chances
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from utils.csv_parser import (
    parse_stokastic_csv,
    create_player_index_map,
    create_lineup_matrix
)
from services.simulator import run_simulation
from services.contest_analyzer import analyze_lineup
from services.prorate import update_projections_for_live_games
from tests.mock_live_scenarios import get_halftime_scenario


def format_percentage_change(old_val, new_val):
    """Format percentage change with color indicator."""
    change = new_val - old_val
    if change > 0:
        return f"+{change:.1f}% ⬆"
    elif change < 0:
        return f"{change:.1f}% ⬇"
    else:
        return f" {change:.1f}% →"


def format_dollar_change(old_val, new_val):
    """Format dollar change with color indicator."""
    change = new_val - old_val
    if change > 0:
        return f"+${change:.2f} ⬆"
    elif change < 0:
        return f"-${abs(change):.2f} ⬇"
    else:
        return f" ${change:.2f} →"


def main():
    print("\n" + "=" * 80)
    print("  NFL DFS LIVE SIMULATION DEMO")
    print("  Simulating HALFTIME update with mock stats")
    print("=" * 80)

    # Load data
    print("\n📊 Loading Stokastic projections...")
    csv_path = Path(__file__).parent.parent / "NFL DK Boom Bust.csv"
    df = parse_stokastic_csv(str(csv_path), slate_filter="Main")
    print(f"   Loaded {len(df)} players for Main slate")

    original_projections = df['Projection'].values
    original_std_devs = df['Std Dev'].values
    player_names = df['Name'].tolist()
    player_index_map = create_player_index_map(df)

    # Create YOUR lineup
    print("\n👤 YOUR LINEUP:")
    your_lineup = [
        'Justin Fields',      # QB
        'De\'Von Achane',     # RB
        'Jonathan Taylor',    # RB
        'Garrett Wilson',     # WR
        'Jaxon Smith-Njigba', # WR
        'Amon-Ra St. Brown',  # WR
        'Trey McBride',       # TE
        'Breece Hall',        # FLEX
        'Jets'                # DST
    ]

    for i, player in enumerate(your_lineup, 1):
        pos_labels = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST']
        print(f"   {pos_labels[i-1]:4} {player}")

    # Create opponent lineups
    opponent1 = ['Kyler Murray', 'Jahmyr Gibbs', 'Saquon Barkley', 'Ja\'Marr Chase',
                 'Chris Olave', 'Michael Pittman Jr.', 'Travis Kelce', 'Nico Collins', 'Lions']

    opponent2 = ['Jalen Hurts', 'Javonte Williams', 'Cam Skattebo', 'George Pickens',
                 'Jaylen Waddle', 'Courtland Sutton', 'Tyler Warren', 'Jakobi Meyers', 'Saints']

    lineups = [your_lineup, opponent1, opponent2]
    entry_names = ['YOUR_LINEUP', 'Opponent_1', 'Opponent_2']

    lineup_matrix = create_lineup_matrix(lineups, player_index_map, len(player_names))

    # PRE-GAME SIMULATION
    print("\n" + "=" * 80)
    print("⏰ PRE-GAME SIMULATION (Before kickoff)")
    print("=" * 80)

    iterations = 10000
    print(f"Running {iterations:,} simulations...")

    baseline_scores = run_simulation(
        projections=original_projections,
        std_devs=original_std_devs,
        lineup_matrix=lineup_matrix,
        iterations=iterations,
        captain_indices=None,
        seed=42
    )

    baseline_result = analyze_lineup(
        scores=baseline_scores,
        lineup_idx=0,
        entry_name='YOUR_LINEUP',
        entry_fee=10.0
    )

    print(f"\n📈 YOUR PRE-GAME OUTLOOK:")
    print(f"   Win Rate:       {baseline_result.win_rate*100:5.1f}%")
    print(f"   Top 3 Rate:     {baseline_result.top_3_rate*100:5.1f}%")
    print(f"   Expected Value: ${baseline_result.expected_value:6.2f}")
    print(f"   ROI:            {baseline_result.roi:6.1f}%")
    print(f"   Avg Finish:     {baseline_result.avg_finish:5.1f}")

    # HALFTIME UPDATE
    print("\n" + "=" * 80)
    print("🏈 HALFTIME UPDATE (50% of games complete)")
    print("=" * 80)

    live_stats = get_halftime_scenario()

    print("\n📊 YOUR PLAYER PERFORMANCES AT HALFTIME:")
    print(f"   {'Player':<25} {'Projected':<10} {'Actual':<10} {'Status':<20}")
    print("   " + "-" * 70)

    for player in your_lineup:
        if player in live_stats:
            idx = player_index_map[player]
            original_proj = original_projections[idx]
            actual = live_stats[player]['actual_points']
            pace = (actual / 0.5)  # Project to full game at current pace

            if pace > original_proj * 1.1:
                status = "🔥 CRUSHING IT"
            elif pace > original_proj * 0.9:
                status = "✅ ON PACE"
            elif pace > original_proj * 0.7:
                status = "⚠️  BEHIND PACE"
            else:
                status = "❌ STRUGGLING"

            print(f"   {player:<25} {original_proj:>6.1f} pts   {actual:>6.1f} pts   {status}")

    # PRO-RATE PROJECTIONS
    print("\n🔄 Pro-rating projections based on actual performance...")
    prorated_projections, adjusted_std_devs = update_projections_for_live_games(
        df, live_stats, adjust_variance=True
    )

    print("\n📈 UPDATED PROJECTIONS FOR YOUR KEY PLAYERS:")
    print(f"   {'Player':<25} {'Original':<10} {'Pro-rated':<10} {'Change':<15}")
    print("   " + "-" * 70)

    for player in ['Justin Fields', 'De\'Von Achane', 'Jonathan Taylor', 'Breece Hall']:
        if player in player_index_map:
            idx = player_index_map[player]
            orig = original_projections[idx]
            prorated = prorated_projections[idx]
            change = prorated - orig
            arrow = "⬆" if change > 0 else "⬇" if change < 0 else "→"
            sign = "+" if change > 0 else ""
            print(f"   {player:<25} {orig:>6.1f} pts   {prorated:>6.1f} pts   {sign}{change:>5.1f} pts {arrow}")

    # LIVE SIMULATION
    print("\n" + "=" * 80)
    print("🔴 LIVE SIMULATION (Updated projections)")
    print("=" * 80)

    print(f"Running {iterations:,} simulations with live data...")

    live_scores = run_simulation(
        projections=prorated_projections,
        std_devs=adjusted_std_devs,
        lineup_matrix=lineup_matrix,
        iterations=iterations,
        captain_indices=None,
        seed=42
    )

    live_result = analyze_lineup(
        scores=live_scores,
        lineup_idx=0,
        entry_name='YOUR_LINEUP',
        entry_fee=10.0
    )

    print(f"\n📈 YOUR LIVE OUTLOOK:")
    print(f"   Win Rate:       {live_result.win_rate*100:5.1f}%")
    print(f"   Top 3 Rate:     {live_result.top_3_rate*100:5.1f}%")
    print(f"   Expected Value: ${live_result.expected_value:6.2f}")
    print(f"   ROI:            {live_result.roi:6.1f}%")
    print(f"   Avg Finish:     {live_result.avg_finish:5.1f}")

    # COMPARISON
    print("\n" + "=" * 80)
    print("📊 PRE-GAME vs LIVE COMPARISON")
    print("=" * 80)

    wr_change = (live_result.win_rate - baseline_result.win_rate) * 100
    roi_change = live_result.roi - baseline_result.roi
    ev_change = live_result.expected_value - baseline_result.expected_value

    print(f"\n   {'Metric':<20} {'Pre-Game':<12} {'Live':<12} {'Change':<15}")
    print("   " + "-" * 70)
    print(f"   {'Win Rate':<20} {baseline_result.win_rate*100:>6.1f}%     {live_result.win_rate*100:>6.1f}%     {format_percentage_change(baseline_result.win_rate*100, live_result.win_rate*100)}")
    print(f"   {'Top 3 Rate':<20} {baseline_result.top_3_rate*100:>6.1f}%     {live_result.top_3_rate*100:>6.1f}%     {format_percentage_change(baseline_result.top_3_rate*100, live_result.top_3_rate*100)}")
    print(f"   {'Expected Value':<20} ${baseline_result.expected_value:>6.2f}     ${live_result.expected_value:>6.2f}     {format_dollar_change(baseline_result.expected_value, live_result.expected_value)}")
    print(f"   {'ROI':<20} {baseline_result.roi:>6.1f}%     {live_result.roi:>6.1f}%     {format_percentage_change(baseline_result.roi, live_result.roi)}")

    # SUMMARY
    print("\n" + "=" * 80)
    print("💡 INSIGHTS")
    print("=" * 80)

    if wr_change > 5:
        print("\n   ✅ Your lineup is OUTPERFORMING! Chances of winning increased significantly.")
        print("      Key performers: Jonathan Taylor, Justin Fields crushing their projections!")
    elif wr_change > 0:
        print("\n   ✅ Your lineup is performing slightly better than expected.")
    elif wr_change > -5:
        print("\n   ⚠️  Your lineup is performing slightly worse than expected.")
    else:
        print("\n   ❌ Your lineup is underperforming. Key players not meeting expectations.")

    if wr_change != 0:
        print(f"\n   📈 Win rate changed by {abs(wr_change):.1f} percentage points at halftime.")
        print(f"   💰 Expected value changed by ${abs(ev_change):.2f}")

    print("\n   🎯 With 50% of the game remaining, there's still time for things to change!")
    print("      Continue monitoring for Q3 and Q4 updates.")

    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE")
    print("=" * 80)
    print("\nThis demonstrates the power of live DFS simulation:")
    print("• Real-time adjustment of win rates based on actual performance")
    print("• Pro-rated projections for remaining game time")
    print("• Updated ROI and expected value calculations")
    print("• Make informed decisions about hedging or doubling down")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
