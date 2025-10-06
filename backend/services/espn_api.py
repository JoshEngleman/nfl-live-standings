"""
Production ESPN API client for live NFL stats.

Performance-critical service - runs every 2-3 minutes during live games.

Features:
- Rate limiting (max 1 request per 30 seconds per endpoint)
- Response caching (60 second TTL)
- Retry logic with exponential backoff
- Timeout protection
- Comprehensive error handling
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

# Use our existing time remaining calculator
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.prorate import calculate_time_remaining_pct


logger = logging.getLogger(__name__)


@dataclass
class LiveGame:
    """Represents a live NFL game."""
    event_id: str
    name: str  # e.g., "Kansas City Chiefs at Buffalo Bills"
    period: int  # Quarter (1-4, 5+ for OT)
    clock: str  # Display string like "3:45"
    clock_minutes: float  # Parsed minutes remaining in quarter
    pct_remaining: float  # Calculated percentage of game remaining
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    status_detail: str  # e.g., "3rd Quarter"


@dataclass
class PlayerStats:
    """Individual player stats from a game."""
    name: str
    team: str
    passing_yds: float = 0.0
    passing_tds: int = 0
    interceptions: int = 0
    rushing_yds: float = 0.0
    rushing_tds: int = 0
    receptions: int = 0
    receiving_yds: float = 0.0
    receiving_tds: int = 0


class RateLimiter:
    """Simple rate limiter with per-endpoint tracking."""

    def __init__(self, min_interval_seconds: float = 30.0):
        self.min_interval = min_interval_seconds
        self.last_call: Dict[str, float] = {}

    def wait_if_needed(self, endpoint: str):
        """Block until enough time has passed since last call to this endpoint."""
        now = time.time()
        last = self.last_call.get(endpoint, 0)
        elapsed = now - last

        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            logger.info(f"Rate limit: waiting {sleep_time:.1f}s for {endpoint}")
            time.sleep(sleep_time)

        self.last_call[endpoint] = time.time()


class ResponseCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds
        self.cache: Dict[str, Tuple[float, any]] = {}

    def get(self, key: str) -> Optional[any]:
        """Get cached value if not expired."""
        if key not in self.cache:
            return None

        timestamp, value = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None

        return value

    def set(self, key: str, value: any):
        """Store value with current timestamp."""
        self.cache[key] = (time.time(), value)

    def clear(self):
        """Clear all cached entries."""
        self.cache.clear()


class ESPNStatsAPI:
    """
    Production ESPN API client for live NFL stats.

    Usage:
        api = ESPNStatsAPI()
        live_games = api.get_live_games()
        for game in live_games:
            stats = api.get_player_stats(game.event_id)
            points = api.get_fantasy_points(game.event_id)
    """

    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

    def __init__(
        self,
        rate_limit_seconds: float = 30.0,
        cache_ttl_seconds: int = 60,
        request_timeout: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize ESPN API client.

        Args:
            rate_limit_seconds: Minimum seconds between requests to same endpoint
            cache_ttl_seconds: Cache lifetime in seconds
            request_timeout: HTTP request timeout
            max_retries: Number of retry attempts on failure
        """
        self.rate_limiter = RateLimiter(rate_limit_seconds)
        self.cache = ResponseCache(cache_ttl_seconds)
        self.timeout = request_timeout
        self.max_retries = max_retries

    def _make_request(self, endpoint: str, cache_key: Optional[str] = None) -> Dict:
        """
        Make HTTP request with rate limiting, caching, and retry logic.

        Args:
            endpoint: URL endpoint to request
            cache_key: Optional cache key (if None, no caching)

        Returns:
            JSON response as dict

        Raises:
            requests.RequestException: If all retries fail
        """
        # Check cache first
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached

        # Rate limit
        self.rate_limiter.wait_if_needed(endpoint)

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = requests.get(endpoint, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                # Cache successful response
                if cache_key:
                    self.cache.set(cache_key, data)

                return data

            except requests.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries}): {endpoint}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                else:
                    raise

            except requests.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def get_scoreboard(self) -> Dict:
        """
        Get current NFL scoreboard with all games.

        Returns:
            Scoreboard data with all games, scores, and statuses

        Caching: 60 seconds (games update every minute or two)
        """
        url = f"{self.BASE_URL}/scoreboard"
        return self._make_request(url, cache_key="scoreboard")

    def _parse_clock_to_minutes(self, clock_str: str) -> float:
        """
        Parse clock display string to minutes.

        Args:
            clock_str: e.g., "3:45", "0:08", "15:00"

        Returns:
            Minutes as float (e.g., 3.75 for "3:45")
        """
        try:
            parts = clock_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes + (seconds / 60.0)
        except:
            pass

        return 0.0

    def get_live_games(self) -> List[LiveGame]:
        """
        Get list of games currently in progress.

        Returns:
            List of LiveGame objects with game info and time remaining

        Note: Returns empty list if no games are live
        """
        scoreboard = self.get_scoreboard()
        games = scoreboard.get('events', [])

        live_games = []

        for game in games:
            status = game.get('status', {})
            status_type = status.get('type', {})

            # Only process live games
            if status_type.get('state') != 'in':
                continue

            # Extract basic info
            event_id = game['id']
            name = game['name']
            period = status.get('period', 1)
            clock_str = status.get('displayClock', '0:00')
            clock_minutes = self._parse_clock_to_minutes(clock_str)

            # Calculate percentage remaining using our prorate service function
            pct_remaining = calculate_time_remaining_pct(period, clock_minutes)

            # Get teams and scores
            competitors = game['competitions'][0]['competitors']
            home_team = competitors[0]['team']['displayName']
            away_team = competitors[1]['team']['displayName']
            home_score = int(competitors[0]['score'])
            away_score = int(competitors[1]['score'])

            live_games.append(LiveGame(
                event_id=event_id,
                name=name,
                period=period,
                clock=clock_str,
                clock_minutes=clock_minutes,
                pct_remaining=pct_remaining,
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                status_detail=status_type.get('detail', 'In Progress')
            ))

        return live_games

    def get_game_summary(self, event_id: str) -> Dict:
        """
        Get detailed game summary including boxscore with player stats.

        Args:
            event_id: ESPN event ID

        Returns:
            Game summary data including boxscore

        Caching: 60 seconds per game
        """
        url = f"{self.BASE_URL}/summary?event={event_id}"
        cache_key = f"summary_{event_id}"
        return self._make_request(url, cache_key=cache_key)

    def get_player_stats(self, event_id: str) -> Dict[str, PlayerStats]:
        """
        Extract player statistics from a game.

        Args:
            event_id: ESPN event ID

        Returns:
            Dict mapping player name -> PlayerStats object
        """
        summary = self.get_game_summary(event_id)
        boxscore = summary.get('boxscore', {})

        player_stats = {}

        # Iterate through teams
        for team in boxscore.get('players', []):
            team_name = team.get('team', {}).get('displayName', 'Unknown')

            # Iterate through stat categories (passing, rushing, receiving)
            for category in team.get('statistics', []):
                category_name = category.get('name', '').lower()
                labels = category.get('labels', [])

                # Iterate through players in this category
                for athlete in category.get('athletes', []):
                    player_name = athlete.get('athlete', {}).get('displayName')
                    if not player_name:
                        continue

                    # Initialize player if first time seeing them
                    if player_name not in player_stats:
                        player_stats[player_name] = PlayerStats(
                            name=player_name,
                            team=team_name
                        )

                    # Parse stats from the stats array using labels
                    stats = athlete.get('stats', [])

                    for i, label in enumerate(labels):
                        if i >= len(stats):
                            continue

                        value = stats[i]
                        if value == '--' or value is None:
                            continue

                        try:
                            # Most stats are numeric
                            if '/' not in str(value):
                                value = float(value)
                            else:
                                # Handle "20/30" format (completions/attempts)
                                continue
                        except:
                            continue

                        # Map label to stat field
                        label_lower = label.lower()

                        if 'passing' in category_name:
                            if 'yds' in label_lower or 'yards' in label_lower:
                                player_stats[player_name].passing_yds = value
                            elif 'td' in label_lower:
                                player_stats[player_name].passing_tds = int(value)
                            elif 'int' in label_lower:
                                player_stats[player_name].interceptions = int(value)

                        elif 'rushing' in category_name:
                            if 'yds' in label_lower or 'yards' in label_lower:
                                player_stats[player_name].rushing_yds = value
                            elif 'td' in label_lower:
                                player_stats[player_name].rushing_tds = int(value)

                        elif 'receiving' in category_name:
                            if 'rec' in label_lower and 'yds' not in label_lower:
                                player_stats[player_name].receptions = int(value)
                            elif 'yds' in label_lower or 'yards' in label_lower:
                                player_stats[player_name].receiving_yds = value
                            elif 'td' in label_lower:
                                player_stats[player_name].receiving_tds = int(value)

        return player_stats

    def calculate_dk_fantasy_points(self, stats: PlayerStats) -> float:
        """
        Calculate DraftKings fantasy points from player stats.

        DraftKings scoring:
        - Pass YD: 0.04 per yard (25 yards = 1 pt)
        - Pass TD: 4 pts
        - INT: -1 pt
        - Rush YD: 0.1 per yard
        - Rush TD: 6 pts
        - Reception: 1 pt (PPR)
        - Rec YD: 0.1 per yard
        - Rec TD: 6 pts
        - 300+ yd passing bonus: +3
        - 100+ yd rushing bonus: +3
        - 100+ yd receiving bonus: +3

        Args:
            stats: PlayerStats object

        Returns:
            Fantasy points (float)
        """
        points = 0.0

        # Passing
        points += stats.passing_yds * 0.04
        points += stats.passing_tds * 4
        points += stats.interceptions * -1

        # Passing bonus
        if stats.passing_yds >= 300:
            points += 3

        # Rushing
        points += stats.rushing_yds * 0.1
        points += stats.rushing_tds * 6

        # Rushing bonus
        if stats.rushing_yds >= 100:
            points += 3

        # Receiving
        points += stats.receptions * 1  # PPR
        points += stats.receiving_yds * 0.1
        points += stats.receiving_tds * 6

        # Receiving bonus
        if stats.receiving_yds >= 100:
            points += 3

        return round(points, 1)

    def get_fantasy_points(self, event_id: str) -> Dict[str, float]:
        """
        Get current DraftKings fantasy points for all players in a game.

        Args:
            event_id: ESPN event ID

        Returns:
            Dict mapping player name -> fantasy points
        """
        player_stats = self.get_player_stats(event_id)

        fantasy_points = {}
        for player_name, stats in player_stats.items():
            fantasy_points[player_name] = self.calculate_dk_fantasy_points(stats)

        return fantasy_points

    def get_all_live_stats(self) -> Dict[str, Dict]:
        """
        Get stats for all players across all live games.

        Returns:
            Dict mapping player name -> {
                'actual_points': float,
                'pct_remaining': float,
                'is_finished': False,
                'team': str,
                'game': str
            }

        This format is compatible with update_projections_for_live_games()
        """
        live_games = self.get_live_games()

        all_stats = {}

        for game in live_games:
            fantasy_points = self.get_fantasy_points(game.event_id)
            player_stats = self.get_player_stats(game.event_id)

            for player_name, points in fantasy_points.items():
                stats_obj = player_stats.get(player_name)

                all_stats[player_name] = {
                    'actual_points': points,
                    'pct_remaining': game.pct_remaining,
                    'is_finished': False,
                    'team': stats_obj.team if stats_obj else 'Unknown',
                    'game': game.name
                }

        return all_stats
