# API Documentation

## Service Layer APIs

Complete reference for all services, utilities, and data structures in the NFL DFS Live Standings platform.

---

## Table of Contents

1. [CSV Parsers](#csv-parsers)
2. [Simulator](#simulator)
3. [Contest Analyzer](#contest-analyzer)
4. [Pro-Rating Service](#pro-rating-service)
5. [ESPN API Client](#espn-api-client)
6. [Player Name Mapper](#player-name-mapper)
7. [Live Stats Service](#live-stats-service)
8. [Data Structures](#data-structures)

---

## CSV Parsers

**Module:** `utils.csv_parser`

### `parse_stokastic_csv(file_path, slate_filter=None)`

Parse Stokastic projections CSV.

**Parameters:**
- `file_path` (str): Path to Stokastic CSV file
- `slate_filter` (str, optional): Filter by slate (e.g., "Main", "Sunday")

**Returns:**
- `pandas.DataFrame`: Columns: `Name`, `Position`, `Salary`, `Projection`, `Std Dev`, `Slate`

**Example:**
```python
df = parse_stokastic_csv("NFL DK Boom Bust.csv", slate_filter="Main")
print(f"Loaded {len(df)} players")
```

---

### `parse_dk_contest_csv(file_path)`

Parse DraftKings contest export CSV.

**Parameters:**
- `file_path` (str): Path to DK contest CSV file

**Returns:**
- `Tuple[List[List[str]], List[int], List[str], str]`:
  - `lineups`: List of lineups (each is list of player names)
  - `entry_ids`: List of EntryId for each lineup
  - `usernames`: List of cleaned usernames
  - `slate_type`: "main" or "showdown"

**Example:**
```python
lineups, entry_ids, usernames, slate_type = parse_dk_contest_csv("contest.csv")
print(f"Parsed {len(lineups)} {slate_type} lineups")
```

---

### `create_player_index_map(stokastic_df)`

Create mapping from player name to array index.

**Parameters:**
- `stokastic_df` (DataFrame): Stokastic projections

**Returns:**
- `Dict[str, int]`: Player name → index

**Example:**
```python
player_index_map = create_player_index_map(df)
mahomes_idx = player_index_map['Patrick Mahomes']
```

---

### `create_lineup_matrix(lineups, player_index_map, num_players)`

Create binary lineup matrix for simulation.

**Parameters:**
- `lineups` (List[List[str]]): List of lineups
- `player_index_map` (Dict[str, int]): Name → index mapping
- `num_players` (int): Total players in pool

**Returns:**
- `numpy.ndarray`: Binary matrix, shape `(num_lineups, num_players)`

**Example:**
```python
lineup_matrix = create_lineup_matrix(lineups, player_index_map, len(df))
# Shape: (3 lineups, 500 players)
```

---

## Simulator

**Module:** `services.simulator`

### `run_simulation(projections, std_devs, lineup_matrix, iterations, captain_indices=None, seed=None)`

Run Monte Carlo simulation.

**Parameters:**
- `projections` (np.ndarray): Player projections, shape `(num_players,)`
- `std_devs` (np.ndarray): Standard deviations, shape `(num_players,)`
- `lineup_matrix` (np.ndarray): Binary lineup matrix, shape `(num_lineups, num_players)`
- `iterations` (int): Number of simulations to run
- `captain_indices` (np.ndarray, optional): Captain indices for showdown (1.5× multiplier)
- `seed` (int, optional): Random seed for reproducibility

**Returns:**
- `numpy.ndarray`: Scores matrix, shape `(num_lineups, iterations)`

**Performance:** 141,000+ iterations/second

**Example:**
```python
scores = run_simulation(
    projections=df['Projection'].values,
    std_devs=df['Std Dev'].values,
    lineup_matrix=lineup_matrix,
    iterations=10000,
    seed=42
)
# Shape: (3 lineups, 10000 iterations)
```

---

## Contest Analyzer

**Module:** `services.contest_analyzer`

### `analyze_lineup(scores, lineup_idx, entry_name, entry_fee, payout_structure=None)`

Analyze simulation results for a specific lineup.

**Parameters:**
- `scores` (np.ndarray): Scores matrix from simulation
- `lineup_idx` (int): Index of lineup to analyze
- `entry_name` (str): Name/identifier for this entry
- `entry_fee` (float): Entry fee in dollars
- `payout_structure` (Dict, optional): Custom payout structure

**Returns:**
- `ContestAnalysis`: Dataclass with:
  - `entry_name` (str)
  - `win_rate` (float): Probability of finishing 1st
  - `top_3_rate` (float): Probability of top 3
  - `cash_rate` (float): Probability of cashing
  - `expected_value` (float): Average payout - entry fee
  - `roi` (float): Return on investment percentage
  - `avg_finish` (float): Average finish position

**Example:**
```python
result = analyze_lineup(
    scores=scores,
    lineup_idx=0,
    entry_name='MY_LINEUP',
    entry_fee=10.0
)

print(f"Win Rate: {result.win_rate * 100:.1f}%")
print(f"ROI: {result.roi:.1f}%")
```

---

## Pro-Rating Service

**Module:** `services.prorate`

### `update_projections_for_live_games(projections_df, live_stats, adjust_variance=True)`

Pro-rate projections based on live stats.

**Parameters:**
- `projections_df` (DataFrame): Stokastic projections with `['Name', 'Projection', 'Std Dev']`
- `live_stats` (Dict): Player name → `{actual_points, pct_remaining, is_finished}`
- `adjust_variance` (bool): Whether to adjust std_dev for time remaining

**Returns:**
- `Tuple[np.ndarray, np.ndarray]`: (prorated_projections, adjusted_std_devs)

**Formula:**
- Live: `actual_points + (original_projection × pct_remaining)`
- Finished: `actual_points`
- Variance: `std_dev × sqrt(pct_remaining)`

**Example:**
```python
live_stats = {
    'Patrick Mahomes': {
        'actual_points': 18.5,
        'pct_remaining': 0.5,
        'is_finished': False
    }
}

prorated_proj, adjusted_std = update_projections_for_live_games(
    df, live_stats, adjust_variance=True
)
```

---

### `calculate_time_remaining_pct(period, clock_minutes)`

Convert game clock to percentage remaining.

**Parameters:**
- `period` (int): Quarter (1-4, 5+ for OT)
- `clock_minutes` (float): Minutes remaining in quarter

**Returns:**
- `float`: Percentage remaining (0.0 to 1.0)

**Example:**
```python
pct = calculate_time_remaining_pct(period=2, clock_minutes=0.0)  # Halftime
# Returns: 0.5 (50% of game remaining)
```

---

## ESPN API Client

**Module:** `services.espn_api`

### `ESPNStatsAPI(rate_limit_seconds=30.0, cache_ttl_seconds=60, request_timeout=10, max_retries=3)`

ESPN API client with rate limiting, caching, and retry logic.

**Attributes:**
- `rate_limit_seconds` (float): Minimum seconds between requests (default: 30)
- `cache_ttl_seconds` (int): Cache lifetime (default: 60)
- `request_timeout` (int): HTTP timeout (default: 10)
- `max_retries` (int): Retry attempts on failure (default: 3)

---

### `get_scoreboard()`

Get current NFL scoreboard with all games.

**Returns:**
- `Dict`: Scoreboard data

**Caching:** 60 seconds

**Example:**
```python
api = ESPNStatsAPI()
scoreboard = api.get_scoreboard()
games = scoreboard.get('events', [])
```

---

### `get_live_games()`

Get list of games currently in progress.

**Returns:**
- `List[LiveGame]`: Live games with timing info

**Example:**
```python
live_games = api.get_live_games()
for game in live_games:
    print(f"{game.name} - Q{game.period} {game.clock}")
    print(f"  {game.pct_remaining*100:.0f}% remaining")
```

---

### `get_player_stats(event_id)`

Extract player statistics from a game.

**Parameters:**
- `event_id` (str): ESPN event ID

**Returns:**
- `Dict[str, PlayerStats]`: Player name → stats object

**Example:**
```python
stats = api.get_player_stats(event_id)
mahomes_stats = stats['Patrick Mahomes']
print(f"Passing: {mahomes_stats.passing_yds} yds, {mahomes_stats.passing_tds} TDs")
```

---

### `get_fantasy_points(event_id)`

Get DraftKings fantasy points for all players in a game.

**Parameters:**
- `event_id` (str): ESPN event ID

**Returns:**
- `Dict[str, float]`: Player name → fantasy points

**Example:**
```python
fantasy_points = api.get_fantasy_points(event_id)
print(f"Mahomes: {fantasy_points['Patrick Mahomes']:.1f} pts")
```

---

### `get_all_live_stats()`

Get stats for all players across all live games.

**Returns:**
- `Dict[str, Dict]`: Player name → `{actual_points, pct_remaining, is_finished, team, game}`

**Example:**
```python
all_stats = api.get_all_live_stats()
for player, stats in all_stats.items():
    print(f"{player}: {stats['actual_points']:.1f} pts ({stats['game']})")
```

---

## Player Name Mapper

**Module:** `utils.player_mapper`

### `PlayerNameMapper(override_file=None)`

Map player names between ESPN and Stokastic.

**Parameters:**
- `override_file` (str, optional): Path to JSON override file

**Methods:**

#### `match_player(espn_name, stokastic_names, espn_team=None, espn_position=None)`

Match ESPN player name to Stokastic name.

**Parameters:**
- `espn_name` (str): Player name from ESPN
- `stokastic_names` (List[str]): All Stokastic names
- `espn_team` (str, optional): Team for tiebreaking
- `espn_position` (str, optional): Position for tiebreaking

**Returns:**
- `str | None`: Matched Stokastic name or None

**Example:**
```python
mapper = PlayerNameMapper()
matched = mapper.match_player(
    'Patrick Mahomes II',
    stokastic_names=['Patrick Mahomes', 'Travis Kelce', ...]
)
# Returns: 'Patrick Mahomes'
```

---

#### `batch_match(espn_players, stokastic_names)`

Match multiple players at once.

**Parameters:**
- `espn_players` (Dict): ESPN_name → `{team, position}`
- `stokastic_names` (List[str]): All Stokastic names

**Returns:**
- `Dict[str, str | None]`: ESPN_name → matched Stokastic name

**Example:**
```python
espn_players = {
    'Patrick Mahomes II': {'team': 'Kansas City Chiefs'},
    'Travis Kelce': {'team': 'Kansas City Chiefs'}
}
matches = mapper.batch_match(espn_players, stokastic_names)
```

---

## Live Stats Service

**Module:** `services.live_stats_service`

### `LiveStatsService(espn_api=None, player_mapper=None)`

High-level orchestration for live stats integration.

**Parameters:**
- `espn_api` (ESPNStatsAPI, optional): ESPN API client
- `player_mapper` (PlayerNameMapper, optional): Name mapper

---

### `get_live_projections(stokastic_df, adjust_variance=True)`

Get pro-rated projections based on live game data.

**⭐ MAIN ENTRY POINT for live simulation**

**Parameters:**
- `stokastic_df` (DataFrame): Stokastic projections
- `adjust_variance` (bool): Adjust std_dev for time remaining

**Returns:**
- `Tuple[np.ndarray, np.ndarray]`: (prorated_projections, adjusted_std_devs)

**Workflow:**
1. Fetch live games from ESPN
2. Extract player stats and fantasy points
3. Match ESPN names → Stokastic names
4. Build live_stats dict
5. Call `update_projections_for_live_games()`
6. Return updated arrays

**Example:**
```python
service = LiveStatsService()

# Get live-updated projections
prorated_proj, adjusted_std = service.get_live_projections(df)

# Run simulation with live data
scores = run_simulation(prorated_proj, adjusted_std, lineup_matrix, 10000)
```

---

### `get_update_summary()`

Get summary of last update.

**Returns:**
- `Dict`: Stats about last update
  - `live_games` (int): Number of live games
  - `players_with_stats` (int): Total ESPN players found
  - `players_matched` (int): Successfully matched to Stokastic
  - `players_unmatched` (int): Failed to match
  - `match_rate` (float): Percentage matched

**Example:**
```python
summary = service.get_update_summary()
print(f"Match rate: {summary['match_rate']:.1f}%")
print(f"Unmatched: {summary['players_unmatched']}")
```

---

## Data Structures

### LiveGame

**Dataclass representing a live NFL game.**

**Fields:**
- `event_id` (str): ESPN event ID
- `name` (str): Game description (e.g., "KC @ BUF")
- `period` (int): Quarter (1-4, 5+ for OT)
- `clock` (str): Display string (e.g., "3:45")
- `clock_minutes` (float): Minutes remaining in quarter
- `pct_remaining` (float): Percentage of game remaining (0.0-1.0)
- `home_team` (str): Home team name
- `away_team` (str): Away team name
- `home_score` (int): Home team score
- `away_score` (int): Away team score
- `status_detail` (str): Status description

---

### PlayerStats

**Dataclass for individual player statistics.**

**Fields:**
- `name` (str): Player name
- `team` (str): Team name
- `passing_yds` (float): Passing yards
- `passing_tds` (int): Passing touchdowns
- `interceptions` (int): Interceptions
- `rushing_yds` (float): Rushing yards
- `rushing_tds` (int): Rushing touchdowns
- `receptions` (int): Receptions
- `receiving_yds` (float): Receiving yards
- `receiving_tds` (int): Receiving touchdowns

---

### ContestAnalysis

**Dataclass for simulation results analysis.**

**Fields:**
- `entry_name` (str): Lineup identifier
- `win_rate` (float): Probability of 1st place
- `top_3_rate` (float): Probability of top 3
- `cash_rate` (float): Probability of cashing
- `expected_value` (float): Average payout - entry fee
- `roi` (float): Return on investment (%)
- `avg_finish` (float): Average finish position

---

## DraftKings Scoring Reference

### Main Slate Scoring

| Stat | Points |
|------|--------|
| Passing Yard | 0.04 (25 yds = 1 pt) |
| Passing TD | 4 |
| Interception | -1 |
| Rushing Yard | 0.1 |
| Rushing TD | 6 |
| Reception | 1 (PPR) |
| Receiving Yard | 0.1 |
| Receiving TD | 6 |
| 300+ yd passing | +3 bonus |
| 100+ yd rushing | +3 bonus |
| 100+ yd receiving | +3 bonus |

### Showdown Scoring

- Captain gets **1.5× multiplier** on all points
- All other scoring same as main slate

---

## Performance Benchmarks

### Simulation
- **Speed:** 141,000 - 209,000 iterations/second
- **10K iterations:** <2 seconds (500 players, 3 lineups)
- **Scaling:** Linear with iterations and players

### Pro-Rating
- **Speed:** <10ms for 500 players
- **Scaling:** O(num_players), vectorized
- **Memory:** O(num_players)

### ESPN API
- **Response Time:** <500ms typical
- **Rate Limit:** 30 seconds between requests (self-imposed)
- **Cache:** 60 second TTL

---

## Error Handling

### ESPN API
- **Timeout:** 10 second timeout, 3 retries with exponential backoff
- **Rate Limiting:** Automatic throttling with 30 second minimum
- **Network Errors:** Retry with backoff, raise after 3 failures

### Name Matching
- **No Match:** Returns None, logs warning
- **Multiple Matches:** Takes highest similarity score
- **Override File Missing:** Continues without overrides

### Simulation
- **Empty Arrays:** Graceful handling, returns empty results
- **Invalid Lineups:** Raises ValueError with details
- **Missing Players:** Skipped in lineup matrix (row sum ≠ 9)

---

## Rate Limits & Best Practices

### ESPN API Usage
- **Poll Interval:** 2-3 minutes during live games
- **Per-Endpoint Limit:** 30 seconds minimum
- **Cache Responses:** 60 seconds to reduce load
- **Only During Live Games:** Check scoreboard first

### Simulation Performance
- **Recommended Iterations:** 10,000 (good balance of speed vs accuracy)
- **Max Iterations Tested:** 100,000 (diminishing returns)
- **Memory Consideration:** 500 players × 100K iterations = ~400MB

---

## Environment Variables (Future)

```bash
# ESPN API (future configuration)
ESPN_API_RATE_LIMIT=30  # Seconds between requests
ESPN_API_CACHE_TTL=60   # Cache lifetime in seconds
ESPN_API_TIMEOUT=10     # Request timeout

# Simulation
DEFAULT_ITERATIONS=10000
RANDOM_SEED=42  # For reproducible testing
```

---

## Version History

- **v0.1.0** - Initial implementation
  - Matrix-based simulator
  - Stokastic/DK CSV parsers
  - Contest analyzer

- **v0.2.0** - Pro-rating engine
  - Halftime/live projections
  - Variance adjustment
  - Mock scenarios for testing

- **v0.3.0** - ESPN API integration
  - Live stats fetching
  - Player name matching
  - Orchestration service
