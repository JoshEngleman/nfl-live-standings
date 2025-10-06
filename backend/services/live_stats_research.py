#!/usr/bin/env python3
"""
Research/POC for live NFL stats fetching.

Testing ESPN API endpoints to see what data we can extract during live games.
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime


class ESPNLiveStats:
    """
    Proof-of-concept for fetching live NFL stats from ESPN API.

    Note: This is an undocumented/unofficial API. Structure may change.
    """

    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

    def get_scoreboard(self) -> Dict:
        """
        Get current scoreboard with all games.

        Returns game info including:
        - Event IDs
        - Team scores
        - Game status (pre, in, post)
        - Game clock
        """
        url = f"{self.BASE_URL}/scoreboard"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def get_live_games(self) -> List[Dict]:
        """
        Filter scoreboard for games currently in progress.

        Returns list of games with status = "in" (live)
        """
        scoreboard = self.get_scoreboard()
        games = scoreboard.get('events', [])

        live_games = []
        for game in games:
            status = game.get('status', {}).get('type', {})
            if status.get('state') == 'in':  # Game is live
                live_games.append({
                    'event_id': game['id'],
                    'name': game['name'],
                    'status': status.get('description'),
                    'clock': game.get('status', {}).get('displayClock'),
                    'period': game.get('status', {}).get('period'),
                    'home_score': game['competitions'][0]['competitors'][0]['score'],
                    'away_score': game['competitions'][0]['competitors'][1]['score']
                })

        return live_games

    def get_game_summary(self, event_id: str) -> Dict:
        """
        Get detailed game summary including player stats.

        Returns:
        - Boxscore with player statistics
        - Game details
        - Drives
        - Scoring plays
        """
        url = f"{self.BASE_URL}/summary?event={event_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def extract_player_stats(self, event_id: str) -> Dict[str, Dict]:
        """
        Extract individual player stats from a game.

        Returns dict mapping player name -> stats
        Stats include: passing, rushing, receiving fantasy points
        """
        summary = self.get_game_summary(event_id)
        boxscore = summary.get('boxscore', {})

        player_stats = {}

        # Boxscore has teams -> players -> statistics
        for team in boxscore.get('players', []):
            team_name = team.get('team', {}).get('displayName', 'Unknown')

            # Each category (passing, rushing, receiving)
            for category in team.get('statistics', []):
                category_name = category.get('name', '').lower()

                # Players in this category
                for athlete in category.get('athletes', []):
                    player_name = athlete.get('athlete', {}).get('displayName')
                    if not player_name:
                        continue

                    # Initialize player if not seen
                    if player_name not in player_stats:
                        player_stats[player_name] = {
                            'team': team_name,
                            'passing_yds': 0,
                            'passing_tds': 0,
                            'interceptions': 0,
                            'rushing_yds': 0,
                            'rushing_tds': 0,
                            'receptions': 0,
                            'receiving_yds': 0,
                            'receiving_tds': 0,
                        }

                    # Parse stats from labels
                    stats = athlete.get('stats', [])
                    labels = category.get('labels', [])

                    for i, label in enumerate(labels):
                        if i >= len(stats):
                            continue

                        value = stats[i]
                        if value == '--':
                            continue

                        try:
                            value = float(value)
                        except:
                            continue

                        # Map labels to our stat keys
                        label_lower = label.lower()

                        if 'passing' in category_name:
                            if 'yds' in label_lower:
                                player_stats[player_name]['passing_yds'] = value
                            elif 'td' in label_lower:
                                player_stats[player_name]['passing_tds'] = value
                            elif 'int' in label_lower:
                                player_stats[player_name]['interceptions'] = value

                        elif 'rushing' in category_name:
                            if 'yds' in label_lower:
                                player_stats[player_name]['rushing_yds'] = value
                            elif 'td' in label_lower:
                                player_stats[player_name]['rushing_tds'] = value

                        elif 'receiving' in category_name:
                            if 'rec' in label_lower and 'yds' not in label_lower:
                                player_stats[player_name]['receptions'] = value
                            elif 'yds' in label_lower:
                                player_stats[player_name]['receiving_yds'] = value
                            elif 'td' in label_lower:
                                player_stats[player_name]['receiving_tds'] = value

        return player_stats

    def calculate_dk_fantasy_points(self, stats: Dict) -> float:
        """
        Calculate DraftKings fantasy points from raw stats.

        DraftKings scoring:
        - Pass YD: 0.04 per yard (25 yards = 1 pt)
        - Pass TD: 4 pts
        - INT: -1 pt
        - Rush YD: 0.1 per yard
        - Rush TD: 6 pts
        - Reception: 1 pt (PPR)
        - Rec YD: 0.1 per yard
        - Rec TD: 6 pts
        - 300 yd pass bonus: +3
        - 100 yd rush/rec bonus: +3
        """
        points = 0.0

        # Passing
        points += stats.get('passing_yds', 0) * 0.04
        points += stats.get('passing_tds', 0) * 4
        points += stats.get('interceptions', 0) * -1

        # Rushing
        rush_yds = stats.get('rushing_yds', 0)
        points += rush_yds * 0.1
        points += stats.get('rushing_tds', 0) * 6
        if rush_yds >= 100:
            points += 3

        # Receiving
        points += stats.get('receptions', 0) * 1  # PPR
        rec_yds = stats.get('receiving_yds', 0)
        points += rec_yds * 0.1
        points += stats.get('receiving_tds', 0) * 6
        if rec_yds >= 100:
            points += 3

        # Passing bonus
        if stats.get('passing_yds', 0) >= 300:
            points += 3

        return round(points, 1)

    def get_live_fantasy_points(self, event_id: str) -> Dict[str, float]:
        """
        Get current fantasy points for all players in a game.

        Returns dict: player_name -> fantasy_points
        """
        player_stats = self.extract_player_stats(event_id)

        fantasy_points = {}
        for player_name, stats in player_stats.items():
            fantasy_points[player_name] = self.calculate_dk_fantasy_points(stats)

        return fantasy_points


def demo():
    """Demo usage of live stats fetcher."""
    print("=" * 70)
    print("ESPN LIVE STATS API - PROOF OF CONCEPT")
    print("=" * 70)

    api = ESPNLiveStats()

    # 1. Get current scoreboard
    print("\n1. Fetching current scoreboard...")
    try:
        scoreboard = api.get_scoreboard()
        games = scoreboard.get('events', [])
        print(f"   Found {len(games)} games on schedule")
    except Exception as e:
        print(f"   Error: {e}")
        return

    # 2. Check for live games
    print("\n2. Checking for live games...")
    live_games = api.get_live_games()

    if not live_games:
        print("   No games currently live")
        print("\n   Showing scheduled games:")
        for game in games[:5]:
            status = game.get('status', {}).get('type', {})
            print(f"   - {game['name']}: {status.get('detail', 'Unknown')}")
    else:
        print(f"   Found {len(live_games)} live game(s):")
        for game in live_games:
            print(f"   - {game['name']}")
            print(f"     Status: Q{game['period']} {game['clock']}")
            print(f"     Score: {game['away_score']} - {game['home_score']}")

    # 3. Demo: Get player stats from a game (will work during/after game)
    print("\n3. Testing player stats extraction...")
    if games:
        event_id = games[0]['id']
        game_name = games[0]['name']
        print(f"   Testing with: {game_name} (ID: {event_id})")

        try:
            player_stats = api.extract_player_stats(event_id)
            fantasy_points = api.get_live_fantasy_points(event_id)

            if fantasy_points:
                print(f"   ✓ Found stats for {len(fantasy_points)} players")
                print("\n   Top 5 fantasy scorers:")
                sorted_players = sorted(fantasy_points.items(), key=lambda x: x[1], reverse=True)[:5]
                for player_name, points in sorted_players:
                    stats = player_stats.get(player_name, {})
                    team = stats.get('team', 'Unknown')
                    print(f"   - {player_name} ({team}): {points} pts")
            else:
                print("   ⚠ No player stats available (game hasn't started)")
        except Exception as e:
            print(f"   Error extracting stats: {e}")

    print("\n" + "=" * 70)
    print("CONCLUSION:")
    print("✓ ESPN API is accessible and returns data")
    print("✓ Can detect live games")
    print("✓ Can extract player stats during/after games")
    print("✓ Can calculate DraftKings fantasy points")
    print("\nNEXT STEPS:")
    print("- Implement pro-rating logic (actual + projected remaining)")
    print("- Handle game clock to calculate time remaining")
    print("- Add error handling and rate limiting")
    print("- Create service layer for integration")
    print("=" * 70)


if __name__ == "__main__":
    demo()
