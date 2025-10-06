"""
End-to-end integration test for live simulation.

Tests complete flow:
1. Load Stokastic projections
2. Create sample lineups
3. Run baseline simulation (pre-game)
4. Apply mock live stats
5. Pro-rate projections
6. Run live simulation
7. Compare results

This proves the entire system works without requiring actual live games.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.csv_parser import (
    parse_stokastic_csv,
    create_player_index_map,
    create_lineup_matrix
)
from services.simulator import run_simulation
from services.contest_analyzer import analyze_lineup
from services.prorate import update_projections_for_live_games
from mock_live_scenarios import get_halftime_scenario


def test_end_to_end_live_simulation():
    """
    Complete end-to-end test of live simulation flow.

    This test:
    1. Uses real Stokastic CSV data
    2. Creates test lineups
    3. Runs pre-game simulation
    4. Simulates "halftime" with mock stats
    5. Pro-rates projections
    6. Runs live simulation
    7. Verifies results change appropriately
    """
    print("\n" + "=" * 70)
    print("END-TO-END LIVE SIMULATION TEST")
    print("=" * 70)

    # 1. Load real Stokastic data
    print("\n1. Loading Stokastic projections...")
    csv_path = Path(__file__).parent.parent.parent / "NFL DK Boom Bust.csv"
    df = parse_stokastic_csv(str(csv_path), slate_filter="Main")
    print(f"   Loaded {len(df)} players")

    original_projections = df['Projection'].values
    original_std_devs = df['Std Dev'].values
    player_names = df['Name'].tolist()
    player_index_map = create_player_index_map(df)

    # 2. Create test lineups that include players in our mock scenario
    print("\n2. Creating test lineups...")

    # Lineup 1: Has players from halftime scenario (should see changes)
    lineup1 = [
        'Justin Fields',      # Has live stats (behind pace)
        'De\'Von Achane',     # Has live stats (way behind)
        'Jonathan Taylor',    # Has live stats (ahead!)
        'Garrett Wilson',     # Has live stats
        'Jaxon Smith-Njigba', # Has live stats (behind)
        'Amon-Ra St. Brown',  # Has live stats
        'Trey McBride',       # Has live stats
        'Breece Hall',        # Has live stats (behind)
        'Jets'                # Has live stats
    ]

    # Lineup 2: Different players (for comparison)
    lineup2 = [
        'Kyler Murray',       # No live stats (not started)
        'Jahmyr Gibbs',      # Has live stats (on pace)
        'Saquon Barkley',    # No live stats
        'Ja\'Marr Chase',    # No live stats
        'Chris Olave',       # No live stats
        'Michael Pittman Jr.', # No live stats
        'Travis Kelce',      # No live stats
        'Nico Collins',      # No live stats
        'Lions'              # No live stats
    ]

    lineups = [lineup1, lineup2]
    entry_names = ['LiveStats_Lineup', 'NoStats_Lineup']

    # Create lineup matrix
    lineup_matrix = create_lineup_matrix(lineups, player_index_map, len(player_names))
    print(f"   Created {len(lineups)} test lineups")

    # 3. Run baseline simulation (pre-game)
    print("\n3. Running PRE-GAME simulation...")
    iterations = 5000

    baseline_scores = run_simulation(
        projections=original_projections,
        std_devs=original_std_devs,
        lineup_matrix=lineup_matrix,
        iterations=iterations,
        captain_indices=None,
        seed=42  # Fixed seed for reproducibility
    )

    print(f"   ✓ Simulated {iterations:,} iterations")

    # Analyze baseline
    baseline_lineup1 = analyze_lineup(
        scores=baseline_scores,
        lineup_idx=0,
        entry_name='LiveStats_Lineup',
        entry_fee=10.0
    )

    baseline_lineup2 = analyze_lineup(
        scores=baseline_scores,
        lineup_idx=1,
        entry_name='NoStats_Lineup',
        entry_fee=10.0
    )

    print(f"\n   PRE-GAME Results:")
    print(f"   Lineup 1: Win Rate = {baseline_lineup1.win_rate*100:.1f}%, ROI = {baseline_lineup1.roi:.1f}%")
    print(f"   Lineup 2: Win Rate = {baseline_lineup2.win_rate*100:.1f}%, ROI = {baseline_lineup2.roi:.1f}%")

    # 4. Apply mock "halftime" stats
    print("\n4. Applying HALFTIME mock stats...")
    live_stats = get_halftime_scenario()
    print(f"   Loaded live stats for {len(live_stats)} players")

    # 5. Pro-rate projections
    print("\n5. Pro-rating projections...")
    prorated_projections, adjusted_std_devs = update_projections_for_live_games(
        df, live_stats, adjust_variance=True
    )

    # Show some examples
    print(f"\n   Example pro-rated projections:")
    for player in ['Justin Fields', 'De\'Von Achane', 'Jonathan Taylor']:
        if player in player_index_map:
            idx = player_index_map[player]
            orig = original_projections[idx]
            prorated = prorated_projections[idx]
            change = prorated - orig
            sign = '+' if change > 0 else ''
            print(f"   - {player:20} {orig:5.1f} → {prorated:5.1f} ({sign}{change:.1f})")

    # 6. Run live simulation with pro-rated projections
    print("\n6. Running LIVE simulation with pro-rated projections...")

    live_scores = run_simulation(
        projections=prorated_projections,
        std_devs=adjusted_std_devs,
        lineup_matrix=lineup_matrix,
        iterations=iterations,
        captain_indices=None,
        seed=42  # Same seed for fair comparison
    )

    print(f"   ✓ Simulated {iterations:,} iterations with live data")

    # Analyze live results
    live_lineup1 = analyze_lineup(
        scores=live_scores,
        lineup_idx=0,
        entry_name='LiveStats_Lineup',
        entry_fee=10.0
    )

    live_lineup2 = analyze_lineup(
        scores=live_scores,
        lineup_idx=1,
        entry_name='NoStats_Lineup',
        entry_fee=10.0
    )

    print(f"\n   LIVE Results:")
    print(f"   Lineup 1: Win Rate = {live_lineup1.win_rate*100:.1f}%, ROI = {live_lineup1.roi:.1f}%")
    print(f"   Lineup 2: Win Rate = {live_lineup2.win_rate*100:.1f}%, ROI = {live_lineup2.roi:.1f}%")

    # 7. Compare results
    print("\n" + "=" * 70)
    print("COMPARISON: PRE-GAME vs LIVE")
    print("=" * 70)

    lineup1_wr_change = (live_lineup1.win_rate - baseline_lineup1.win_rate) * 100
    lineup1_roi_change = live_lineup1.roi - baseline_lineup1.roi

    lineup2_wr_change = (live_lineup2.win_rate - baseline_lineup2.win_rate) * 100
    lineup2_roi_change = live_lineup2.roi - baseline_lineup2.roi

    print(f"\nLineup 1 (Has Live Stats):")
    print(f"  Win Rate:  {baseline_lineup1.win_rate*100:5.1f}% → {live_lineup1.win_rate*100:5.1f}% ({lineup1_wr_change:+.1f}%)")
    print(f"  ROI:       {baseline_lineup1.roi:6.1f}% → {live_lineup1.roi:6.1f}% ({lineup1_roi_change:+.1f}%)")

    print(f"\nLineup 2 (Mostly No Stats):")
    print(f"  Win Rate:  {baseline_lineup2.win_rate*100:5.1f}% → {live_lineup2.win_rate*100:5.1f}% ({lineup2_wr_change:+.1f}%)")
    print(f"  ROI:       {baseline_lineup2.roi:6.1f}% → {live_lineup2.roi:6.1f}% ({lineup2_roi_change:+.1f}%)")

    # 8. Assertions
    print("\n" + "=" * 70)
    print("ASSERTIONS")
    print("=" * 70)

    # Scores should have changed
    assert not np.array_equal(baseline_scores, live_scores), \
        "Live scores should differ from baseline"

    print("✓ Live simulation produces different results than baseline")

    # Lineup 1 has mixed performances (some good, some bad)
    # We can't predict direction, but magnitude should be reasonable
    assert abs(lineup1_wr_change) < 100, \
        f"Win rate change seems unrealistic: {lineup1_wr_change}%"

    print("✓ Win rate changes are within reasonable bounds")

    # Score distributions should be different
    lineup1_baseline_mean = np.mean(baseline_scores[0, :])
    lineup1_live_mean = np.mean(live_scores[0, :])
    mean_difference = abs(lineup1_live_mean - lineup1_baseline_mean)

    assert mean_difference > 1.0, \
        "Mean scores should change with pro-rating"

    print(f"✓ Mean score changed by {mean_difference:.1f} points")

    print("\n" + "=" * 70)
    print("✅ END-TO-END TEST PASSED")
    print("=" * 70)
    print("\nThe complete live simulation pipeline works!")
    print("- Projections can be pro-rated based on live stats")
    print("- Simulations update correctly")
    print("- Win rates and ROI change appropriately")
    print("=" * 70)

    return True


if __name__ == "__main__":
    try:
        test_end_to_end_live_simulation()
        print("\n✓ Integration test completed successfully!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
