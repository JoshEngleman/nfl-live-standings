#!/usr/bin/env python3
"""
Demo: Live NFL DFS Simulation with ESPN API

Shows the complete live simulation flow:
1. Fetch live NFL games from ESPN
2. Extract player stats and fantasy points
3. Pro-rate projections based on actual performance
4. Run simulation with live data
5. Compare pre-game vs live win rates

This demonstrates the power of live updates during actual NFL games!
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
from services.live_stats_service import LiveStatsService
from services.espn_api import ESPNStatsAPI


def format_percentage_change(old_val, new_val):
    """Format percentage change with indicator."""
    change = new_val - old_val
    if change > 0:
        return f"+{change:.1f}% ⬆"
    elif change < 0:
        return f"{change:.1f}% ⬇"
    else:
        return f" {change:.1f}% →"


def format_dollar_change(old_val, new_val):
    """Format dollar change with indicator."""
    change = new_val - old_val
    if change > 0:
        return f"+${change:.2f} ⬆"
    elif change < 0:
        return f"-${abs(change):.2f} ⬇"
    else:
        return f" ${change:.2f} →"


def main():
    print("\n" + "=" * 80)
    print("  NFL DFS LIVE SIMULATION with ESPN API")
    print("  Real-time simulation updates during live games")
    print("=" * 80)

    # Load Stokastic projections
    print("\n📊 Loading Stokastic projections...")
    csv_path = Path(__file__).parent.parent / "NFL DK Boom Bust.csv"

    if not csv_path.exists():
        print(f"   ✗ Error: Stokastic CSV not found at {csv_path}")
        print("   Please add the Stokastic CSV file to run this demo")
        return

    df = parse_stokastic_csv(str(csv_path), slate_filter="Main")
    print(f"   Loaded {len(df)} players for Main slate")

    original_projections = df['Projection'].values
    original_std_devs = df['Std Dev'].values
    player_names = df['Name'].tolist()
    player_index_map = create_player_index_map(df)

    # Check for live games
    print("\n🏈 Checking for live NFL games...")
    api = ESPNStatsAPI()

    try:
        live_games = api.get_live_games()

        if not live_games:
            print("   ⚠  No games currently live")
            print("\n   This demo works best during live NFL games (Sunday afternoons/evenings).")
            print("   You can still run it - it will use pregame projections.")
            print("\n   Continuing with pregame simulation...")
        else:
            print(f"   ✓ Found {len(live_games)} live game(s):")
            for game in live_games:
                print(f"      - {game.name}")
                print(f"        Q{game.period} {game.clock} | Score: {game.away_score}-{game.home_score}")
                print(f"        {game.pct_remaining*100:.0f}% of game remaining")

    except Exception as e:
        print(f"   ✗ Error checking for live games: {e}")
        print("   Continuing with pregame simulation...")

    # Create example lineup
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
    print("⏰ PRE-GAME SIMULATION (Original projections)")
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

    # LIVE UPDATE
    print("\n" + "=" * 80)
    print("🔴 LIVE UPDATE (Fetching real-time ESPN stats)")
    print("=" * 80)

    try:
        service = LiveStatsService()

        # Get live projections
        prorated_projections, adjusted_std_devs = service.get_live_projections(df)

        # Get update summary
        summary = service.get_update_summary()

        print(f"\n📊 Live Stats Summary:")
        print(f"   Live games: {summary['live_games']}")
        print(f"   Players with stats: {summary['players_with_stats']}")
        print(f"   Players matched: {summary['players_matched']}")
        print(f"   Players unmatched: {summary['players_unmatched']}")
        if summary['players_with_stats'] > 0:
            print(f"   Match rate: {summary['match_rate']:.1f}%")

        # Show updated projections for lineup players
        if summary['live_games'] > 0:
            print(f"\n📈 UPDATED PROJECTIONS FOR YOUR LINEUP:")
            print(f"   {'Player':<25} {'Original':<10} {'Live':<10} {'Change':<15}")
            print("   " + "-" * 70)

            for player in your_lineup:
                if player in player_index_map:
                    idx = player_index_map[player]
                    orig = original_projections[idx]
                    prorated = prorated_projections[idx]
                    change = prorated - orig

                    if abs(change) > 0.1:  # Only show if changed
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

        print(f"\n   {'Metric':<20} {'Pre-Game':<12} {'Live':<12} {'Change':<15}")
        print("   " + "-" * 70)
        print(f"   {'Win Rate':<20} {baseline_result.win_rate*100:>6.1f}%     {live_result.win_rate*100:>6.1f}%     {format_percentage_change(baseline_result.win_rate*100, live_result.win_rate*100)}")
        print(f"   {'Top 3 Rate':<20} {baseline_result.top_3_rate*100:>6.1f}%     {live_result.top_3_rate*100:>6.1f}%     {format_percentage_change(baseline_result.top_3_rate*100, live_result.top_3_rate*100)}")
        print(f"   {'Expected Value':<20} ${baseline_result.expected_value:>6.2f}     ${live_result.expected_value:>6.2f}     {format_dollar_change(baseline_result.expected_value, live_result.expected_value)}")
        print(f"   {'ROI':<20} {baseline_result.roi:>6.1f}%     {live_result.roi:>6.1f}%     {format_percentage_change(baseline_result.roi, live_result.roi)}")

        # INSIGHTS
        print("\n" + "=" * 80)
        print("💡 INSIGHTS")
        print("=" * 80)

        if summary['live_games'] == 0:
            print("\n   No live games at the moment.")
            print("   This demo is most powerful during live NFL games!")
            print("\n   📅 Try running during:")
            print("      - Sunday afternoons (1pm ET / 4pm ET slates)")
            print("      - Sunday Night Football (~8:20pm ET)")
            print("      - Monday Night Football (~8:15pm ET)")
        else:
            if wr_change > 5:
                print("\n   ✅ Your lineup is OUTPERFORMING! Win rate increased significantly.")
            elif wr_change > 0:
                print("\n   ✅ Your lineup is performing slightly better than expected.")
            elif wr_change > -5:
                print("\n   ⚠️  Your lineup is performing slightly worse than expected.")
            else:
                print("\n   ❌ Your lineup is underperforming expectations.")

            print(f"\n   📈 Win rate changed by {abs(wr_change):.1f} percentage points during live games.")
            print(f"   💰 Expected value changed by ${abs(live_result.expected_value - baseline_result.expected_value):.2f}")

            avg_pct_remaining = np.mean([g.pct_remaining for g in api.get_live_games()])
            print(f"\n   🎯 ~{(1-avg_pct_remaining)*100:.0f}% of games complete - still time for things to change!")

    except Exception as e:
        print(f"\n✗ Error during live update: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE")
    print("=" * 80)
    print("\nThis demonstrates live DFS simulation with ESPN API:")
    print("• Real-time player stats from live NFL games")
    print("• Automatic pro-rating based on actual performance")
    print("• Updated win rates, ROI, and expected value")
    print("• Make informed decisions about hedging or doubling down")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
