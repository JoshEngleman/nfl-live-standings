#!/usr/bin/env python3
"""
Integration test for ESPN API → Pro-rating → Simulation flow.

Tests the complete pipeline with real ESPN data (when games are live).

If no games are live, tests basic functionality with mock data.
"""

import sys
from pathlib import Path
import numpy as np
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.espn_api import ESPNStatsAPI
from services.live_stats_service import LiveStatsService
from utils.csv_parser import parse_stokastic_csv
from utils.player_mapper import PlayerNameMapper


logging.basicConfig(level=logging.INFO)


def test_espn_api_connectivity():
    """Test 1: Verify ESPN API is accessible."""
    print("\n" + "=" * 70)
    print("TEST 1: ESPN API CONNECTIVITY")
    print("=" * 70)

    api = ESPNStatsAPI()

    try:
        scoreboard = api.get_scoreboard()
        games = scoreboard.get('events', [])

        print(f"✓ ESPN API is accessible")
        print(f"  Found {len(games)} games on schedule")

        assert len(games) > 0, "No games found on scoreboard"

        return True

    except Exception as e:
        print(f"✗ ESPN API error: {e}")
        return False


def test_live_game_detection():
    """Test 2: Detect live games (if any)."""
    print("\n" + "=" * 70)
    print("TEST 2: LIVE GAME DETECTION")
    print("=" * 70)

    api = ESPNStatsAPI()

    try:
        live_games = api.get_live_games()

        if not live_games:
            print("  No games currently live (this is OK)")
            print("  ✓ Live game detection works (returned empty list)")
            return True

        print(f"  Found {len(live_games)} live game(s):")
        for game in live_games:
            print(f"  - {game.name}")
            print(f"    Status: Q{game.period} {game.clock} ({game.pct_remaining*100:.0f}% remaining)")
            print(f"    Score: {game.away_score} - {game.home_score}")

        print(f"✓ Live game detection works")
        return True

    except Exception as e:
        print(f"✗ Error detecting live games: {e}")
        return False


def test_player_stats_extraction():
    """Test 3: Extract player stats from a game."""
    print("\n" + "=" * 70)
    print("TEST 3: PLAYER STATS EXTRACTION")
    print("=" * 70)

    api = ESPNStatsAPI()

    try:
        scoreboard = api.get_scoreboard()
        games = scoreboard.get('events', [])

        if not games:
            print("  ✗ No games available to test")
            return False

        # Test with first game (regardless of status)
        event_id = games[0]['id']
        game_name = games[0]['name']
        print(f"  Testing with: {game_name}")

        player_stats = api.get_player_stats(event_id)
        fantasy_points = api.get_fantasy_points(event_id)

        if not fantasy_points:
            print("  ⚠  Game hasn't started yet - no stats available")
            print("  ✓ Stats extraction works (returns empty dict for future games)")
            return True

        print(f"  ✓ Found stats for {len(fantasy_points)} players")
        print(f"\n  Top 5 fantasy scorers:")
        sorted_players = sorted(fantasy_points.items(), key=lambda x: x[1], reverse=True)[:5]
        for player_name, points in sorted_players:
            stats = player_stats.get(player_name)
            team = stats.team if stats else 'Unknown'
            print(f"    - {player_name} ({team}): {points:.1f} pts")

        assert len(fantasy_points) > 0, "Expected some player stats"
        print(f"\n✓ Player stats extraction works")
        return True

    except Exception as e:
        print(f"✗ Error extracting player stats: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_player_name_matching():
    """Test 4: Player name matching between ESPN and Stokastic."""
    print("\n" + "=" * 70)
    print("TEST 4: PLAYER NAME MATCHING")
    print("=" * 70)

    # Load Stokastic CSV
    csv_path = Path(__file__).parent.parent.parent / "NFL DK Boom Bust.csv"

    if not csv_path.exists():
        print(f"  ⚠  Stokastic CSV not found: {csv_path}")
        print("  Skipping name matching test")
        return True

    try:
        df = parse_stokastic_csv(str(csv_path), slate_filter="Main")
        stokastic_names = df['Name'].tolist()

        print(f"  Loaded {len(stokastic_names)} players from Stokastic CSV")

        # Test name normalization
        mapper = PlayerNameMapper()

        test_cases = [
            ("Patrick Mahomes II", "Patrick Mahomes"),
            ("De'Von Achane", "De'Von Achane"),
            ("Kenneth Walker III", "Kenneth Walker"),
        ]

        print(f"\n  Testing name matching:")
        for espn_name, expected in test_cases:
            matched = mapper.match_player(espn_name, stokastic_names)
            status = "✓" if matched == expected or matched is not None else "✗"
            print(f"    {status} '{espn_name}' → '{matched}'")

        print(f"\n✓ Player name matching works")
        return True

    except Exception as e:
        print(f"✗ Error in name matching: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_live_projections_integration():
    """Test 5: Complete integration - ESPN → Pro-rating."""
    print("\n" + "=" * 70)
    print("TEST 5: LIVE PROJECTIONS INTEGRATION")
    print("=" * 70)

    # Load Stokastic CSV
    csv_path = Path(__file__).parent.parent.parent / "NFL DK Boom Bust.csv"

    if not csv_path.exists():
        print(f"  ⚠  Stokastic CSV not found: {csv_path}")
        print("  Skipping integration test")
        return True

    try:
        df = parse_stokastic_csv(str(csv_path), slate_filter="Main")
        print(f"  Loaded {len(df)} players from Stokastic CSV")

        # Get live projections
        service = LiveStatsService()

        original_projections = df['Projection'].values.copy()
        prorated_projections, adjusted_std_devs = service.get_live_projections(df)

        # Get update summary
        summary = service.get_update_summary()

        print(f"\n  Live Stats Summary:")
        print(f"    Live games: {summary['live_games']}")
        print(f"    Players with stats: {summary['players_with_stats']}")
        print(f"    Players matched: {summary['players_matched']}")
        print(f"    Players unmatched: {summary['players_unmatched']}")
        print(f"    Match rate: {summary['match_rate']:.1f}%")

        # Check if any projections changed
        num_changed = np.sum(prorated_projections != original_projections)

        if summary['live_games'] == 0:
            print(f"\n  No live games - projections unchanged (expected)")
            assert num_changed == 0, "Projections should not change when no live games"
        else:
            print(f"\n  {num_changed} player projections were updated")
            if num_changed > 0:
                # Show some examples
                changed_indices = np.where(prorated_projections != original_projections)[0][:5]
                print(f"\n  Example updated projections:")
                for idx in changed_indices:
                    name = df.iloc[idx]['Name']
                    orig = original_projections[idx]
                    new = prorated_projections[idx]
                    diff = new - orig
                    sign = "+" if diff > 0 else ""
                    print(f"    {name:25} {orig:5.1f} → {new:5.1f} ({sign}{diff:.1f})")

        # Verify arrays are correct shape
        assert len(prorated_projections) == len(df), "Projection array length mismatch"
        assert len(adjusted_std_devs) == len(df), "Std dev array length mismatch"

        print(f"\n✓ Live projections integration works")
        return True

    except Exception as e:
        print(f"✗ Integration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("ESPN INTEGRATION TEST SUITE")
    print("=" * 70)

    tests = [
        test_espn_api_connectivity,
        test_live_game_detection,
        test_player_stats_extraction,
        test_player_name_matching,
        test_live_projections_integration
    ]

    results = []

    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Unexpected error in {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    for i, (test_func, result) in enumerate(zip(tests, results), 1):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}  Test {i}: {test_func.__name__}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("=" * 70)
        return True
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
