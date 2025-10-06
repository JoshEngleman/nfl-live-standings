# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Philosophy

**Efficiency First**: This is a real-time simulation system where performance is critical. Speed is not optional—it's a core requirement.

- Every 2-3 minutes: fetch stats → pro-rate → simulate 10K+ iterations → push results
- **Target**: <5 second total cycle time
- Always profile before and after changes
- Optimize hot paths aggressively
- Be an S-tier developer: constantly look for optimization opportunities

## Performance-Critical Components (Ranked)

### 1. Simulation Engine (THE BOTTLENECK)
**Location**: `backend/services/simulator.py`

This is the most performance-critical code in the entire system. Must use matrix operations—never refactor to loops.

```python
# CORE ARCHITECTURE - NEVER BREAK THIS PATTERN
# Generate all player simulations at once: (players × iterations)
player_simulations = np.random.normal(projections, std_devs, (num_players, iterations))

# Create lineup binary matrix: (lineups × players)
lineup_matrix = create_lineup_matrix(contest_entries)

# Single matrix multiplication for ALL lineup scores
all_scores = lineup_matrix @ player_simulations  # (lineups × iterations)
```

**Why this matters**: Matrix multiplication is optimized at the BLAS level. A single `@` operation is 100-1000x faster than nested Python loops.

**Benchmark every change to this file**.

### 2. Pro-Rating Calculator (HOT PATH)
**Location**: `backend/services/prorate.py`

Called every update cycle (every 2-3 minutes during live games).

Must be vectorized:
```python
# ✅ GOOD - Vectorized across all players
live_mask = std_devs > 0.2
prorated[live_mask] = actual[live_mask] + (projections[live_mask] * pct_remaining[live_mask])

# ❌ BAD - Loops
for i, player in enumerate(players):
    if player.std_dev > 0.2:
        prorated[i] = player.actual + player.projection * pct_remaining
```

### 3. Contest Analyzer (WARM PATH)
**Location**: `backend/services/contest_analyzer.py`

Can become expensive with large contests (1000+ lineups).

Use NumPy operations for ranking/sorting:
```python
# ✅ GOOD
rankings = np.argsort(-all_scores, axis=0)  # Descending order

# ❌ BAD
for iteration in range(iterations):
    sorted_lineups = sorted(scores, reverse=True)
```

### 4. Everything Else (COLD PATH)
API endpoints, database operations, stat fetching—these are I/O bound and less critical. Don't over-optimize.

## Code Organization

```
backend/
├── services/
│   ├── simulator.py          # ⚠️ CRITICAL PATH - matrix operations only
│   ├── prorate.py            # 🔥 HOT PATH - vectorized calculations
│   ├── contest_analyzer.py   # 🌡️ WARM PATH - optimize if needed
│   └── stats/                # ❄️ I/O bound - less critical
│       ├── __init__.py
│       ├── base.py           # Abstract base class for stat sources
│       ├── espn.py           # ESPN stat adapter
│       └── nfl_data.py       # nfl-data-py adapter
├── models/
│   ├── __init__.py
│   ├── player.py
│   ├── contest.py
│   └── projection.py
├── api/
│   ├── __init__.py
│   ├── contest.py            # Contest endpoints
│   └── results.py            # Results endpoints
├── utils/
│   ├── csv_parser.py         # Stokastic & DK CSV parsers
│   └── dk_scoring.py         # DraftKings scoring rules
├── main.py                   # FastAPI app
└── scheduler.py              # Background task scheduler

frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx
│   │   ├── StandingsTable.jsx
│   │   ├── WinProbChart.jsx
│   │   └── MetricsDisplay.jsx
│   ├── hooks/
│   │   └── useWebSocket.js
│   ├── App.jsx
│   └── main.jsx
└── package.json
```

## Where to Put New Code

**Adding a new stat source:**
1. Create adapter in `backend/services/stats/`
2. Inherit from base class in `stats/base.py`
3. Implement required methods: `fetch_live_stats()`, `get_game_clock()`, etc.
4. Register in stats factory

**Modifying simulation logic:**
1. Edit `backend/services/simulator.py`
2. **Preserve matrix operations**—do not introduce loops
3. Add performance tests in `tests/test_simulator.py`
4. Benchmark before/after

**Adding new metrics:**
1. Add calculation logic in `backend/services/contest_analyzer.py`
2. Update API response models
3. Add frontend visualization in `frontend/src/components/`

**New CSV parser:**
1. Add parser function in `backend/utils/csv_parser.py`
2. Return standardized DataFrame format
3. Handle edge cases (missing columns, invalid data)

## Coding Standards

### Python Style

**Type hints everywhere**:
```python
def simulate_scores(
    projections: np.ndarray,
    std_devs: np.ndarray,
    iterations: int
) -> np.ndarray:
    """Generate simulation matrix via vectorized normal distribution."""
    return np.random.normal(projections, std_devs, (len(projections), iterations))
```

**Docstrings with performance notes**:
```python
def calculate_lineup_scores(
    lineup_matrix: np.ndarray,
    player_sims: np.ndarray
) -> np.ndarray:
    """
    Calculate all lineup scores via matrix multiplication.

    Performance: O(L×P×I) via optimized BLAS where L=lineups, P=players, I=iterations.
    This is THE performance bottleneck—preserve matrix operation.

    Args:
        lineup_matrix: Binary matrix (lineups × players). 1 if player in lineup.
        player_sims: Simulation matrix (players × iterations)

    Returns:
        Score matrix (lineups × iterations)
    """
    return lineup_matrix @ player_sims
```

**Vectorization examples**:
```python
# ✅ GOOD - NumPy vectorized
projections = df['Projection'].values  # Convert to NumPy array early
std_devs = df['Std Dev'].values
sims = np.random.normal(projections, std_devs, (len(projections), 10000))

# ❌ BAD - Python loops
sims = []
for proj, std in zip(projections, std_devs):
    player_sims = [np.random.normal(proj, std) for _ in range(10000)]
    sims.append(player_sims)

# ✅ GOOD - Pandas vectorized operations
df['prorated'] = df['actual'] + (df['projection'] * df['pct_remaining'])

# ❌ BAD - iterrows
for idx, row in df.iterrows():
    df.loc[idx, 'prorated'] = row['actual'] + (row['projection'] * row['pct_remaining'])
```

**Import organization**:
```python
# Standard library
import time
from typing import List, Dict, Tuple

# Third-party
import numpy as np
import pandas as pd
from fastapi import FastAPI

# Local
from services.simulator import simulate_scores
from models.player import Player
```

### JavaScript/React Patterns

**Functional components with hooks**:
```javascript
function Dashboard() {
  const { data, isConnected } = useWebSocket('ws://localhost:8000/ws');

  return (
    <div>
      <StandingsTable data={data} />
      <WinProbChart distribution={data.winProb} />
    </div>
  );
}
```

**Memoize expensive computations**:
```javascript
const sortedLineups = useMemo(
  () => lineups.sort((a, b) => b.score - a.score),
  [lineups]
);
```

## Optimization Requirements

### Before Adding ANY Feature

```bash
# 1. Baseline current performance
python -m cProfile -o profile.stats run_simulation.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# 2. Add feature with performance in mind
# ... implement ...

# 3. Re-profile and compare
python -m cProfile -o profile_after.stats run_simulation.py

# 4. If >10% slower, optimize or reconsider
```

### Optimization Workflow

**When you notice slowness:**

1. **Profile first**—never guess:
   ```bash
   python -m cProfile -o profile.stats run_simulation.py
   # Visualize with snakeviz if available
   snakeviz profile.stats
   ```

2. **Identify hot path**—what takes >5% of total time?

3. **Optimize hot path only**:
   - Replace loops with NumPy operations
   - Cache repeated calculations
   - Use better algorithms (O(n²) → O(n log n))
   - Pre-allocate arrays when size is known

4. **Benchmark improvement**:
   - Must be >20% faster to justify added complexity
   - Document the optimization in code comments

5. **Don't optimize cold paths**—premature optimization is wasteful

### Performance Checklist for New Code

Before committing:
- [ ] Will this run in the simulation loop? (if yes, must be vectorized)
- [ ] Can I use NumPy instead of Python loops?
- [ ] Should I cache this result?
- [ ] Is this in a hot path? (profile to verify)
- [ ] Does this add <5% overhead? (if not, reconsider or optimize)

## Testing Strategy

### Unit Tests

**Fast, focused tests**:
```python
def test_simulator_output_shape():
    """Simulation matrix should have shape (players, iterations)."""
    projections = np.array([10.0, 15.0, 20.0])
    std_devs = np.array([3.0, 4.0, 5.0])
    result = simulate_scores(projections, std_devs, iterations=1000)
    assert result.shape == (3, 1000)

def test_lineup_scores():
    """Lineup scores should sum player scores correctly."""
    player_sims = np.array([[10, 12], [15, 18], [20, 22]])  # 3 players, 2 iterations
    lineup_matrix = np.array([[1, 1, 0], [0, 1, 1]])  # 2 lineups
    scores = calculate_lineup_scores(lineup_matrix, player_sims)
    assert scores.shape == (2, 2)
    assert np.allclose(scores[0], [25, 30])  # Player 0 + Player 1
    assert np.allclose(scores[1], [35, 40])  # Player 1 + Player 2
```

### Performance Tests

**Regression detection**:
```python
import pytest
import time

@pytest.mark.performance
def test_simulation_speed():
    """Simulation should handle 500 players × 10K iterations in <2 seconds."""
    projections = np.random.uniform(5, 30, 500)
    std_devs = np.random.uniform(2, 10, 500)

    start = time.time()
    result = simulate_scores(projections, std_devs, iterations=10000)
    duration = time.time() - start

    assert duration < 2.0, f"Simulation too slow: {duration:.2f}s"
    assert result.shape == (500, 10000)

@pytest.mark.performance
def test_full_update_cycle():
    """Full update cycle should complete in <5 seconds."""
    start = time.time()
    # Load data → prorate → simulate → analyze
    result = run_full_simulation_cycle()
    duration = time.time() - start

    assert duration < 5.0, f"Update cycle too slow: {duration:.2f}s"
```

### Integration Tests

**Mock external APIs**:
```python
def test_live_stats_integration(mock_espn_api):
    """Should fetch stats and update projections."""
    mock_espn_api.return_value = {'player_123': {'points': 15.4, 'time_remaining': 0.5}}

    stats = fetch_live_stats()
    prorated = prorate_projections(original_projections, stats)

    assert prorated['player_123'] > 15.4  # Actual + prorated remaining
```

## Critical Architecture Patterns (NEVER BREAK)

### 1. Matrix-Based Simulation (THE CORE INNOVATION)

```python
# ✅ THIS IS THE WAY - Single matrix multiplication
all_scores = lineup_matrix @ player_simulations

# ❌ NEVER DO THIS - Nested loops
all_scores = []
for lineup in lineups:
    lineup_scores = []
    for iteration in range(iterations):
        score = sum(player_sims[player][iteration] for player in lineup)
        lineup_scores.append(score)
    all_scores.append(lineup_scores)
```

**Why**: The matrix approach is 100-1000x faster. This is non-negotiable.

### 2. Vectorized Pro-Rating (CORE LIVE FEATURE)

Pro-rating combines actual performance with projected remaining performance.

**Formula:**
```
For live games:  prorated = actual_points + (original_projection × pct_game_remaining)
For finished:    prorated = actual_points
```

**Example:**
- Mahomes projected 20 pts, has 15 pts at halftime (50% remaining)
- Prorated = 15 + (20 × 0.5) = 25 pts

**Vectorized implementation (REQUIRED):**
```python
# ✅ Apply to all players at once - HOT PATH
live_mask = std_devs > 0.2  # Detect live vs finished games
prorated[live_mask] = actual[live_mask] + (projections[live_mask] * pct_remaining[live_mask])
finished_mask = ~live_mask
prorated[finished_mask] = actual[finished_mask]

# ❌ NEVER loop over players - 100x slower
for i, player in enumerate(players):
    if player.std_dev > 0.2:
        prorated[i] = player.actual + player.projection * pct_remaining
    else:
        prorated[i] = player.actual
```

**Variance adjustment:**
Uncertainty decreases as game progresses. Scale std_dev by sqrt(time_remaining):
```python
adjusted_std = original_std * np.sqrt(pct_remaining)
adjusted_std[finished_mask] = 0.1  # Minimal variance for finished
```

**Performance:** Must complete in <10ms for 500 players

### 3. Batch Database Operations

```python
# ✅ Bulk operations
db.bulk_insert_mappings(Player, player_dicts)

# ❌ Loop with individual commits
for player in players:
    db.add(Player(**player))
    db.commit()  # This is especially bad
```

## Common Optimizations

### Cache Simulation Matrices

If projections haven't changed, reuse the matrix:
```python
class SimulationCache:
    def __init__(self):
        self._cache = {}

    def get_or_create(self, projections: np.ndarray, std_devs: np.ndarray, iterations: int):
        cache_key = hash(projections.tobytes() + std_devs.tobytes() + str(iterations))

        if cache_key not in self._cache:
            self._cache[cache_key] = np.random.normal(
                projections, std_devs, (len(projections), iterations)
            )

        return self._cache[cache_key]
```

### Reduce DataFrame Operations

```python
# ✅ Convert to NumPy early, work with arrays
values = df[['Projection', 'Std Dev', 'Salary']].values
projections = values[:, 0]
std_devs = values[:, 1]
salaries = values[:, 2]

# ❌ Multiple DataFrame column accesses
projections = df['Projection'].values
std_devs = df['Std Dev'].values
salaries = df['Salary'].values
```

### Pre-allocate Arrays

```python
# ✅ Pre-allocate when size is known
results = np.empty((num_lineups, iterations))

# ❌ Grow array dynamically
results = []
for lineup in lineups:
    results.append(calculate_score(lineup))
results = np.array(results)
```

## Development Priorities (In Order)

1. **Make it work**—correct results first
2. **Make it fast**—profile and optimize hot paths
3. **Make it clean**—refactor without losing performance
4. **Make it robust**—error handling, edge cases
5. **Make it maintainable**—comments on performance-critical sections

## Common Commands

### Backend

```bash
# Run development server
cd backend
uvicorn main:app --reload

# Run tests
pytest

# Run performance tests only
pytest -m performance

# Profile simulation
python -m cProfile -o profile.stats run_simulation.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# Run full simulation with sample data
python run_simulation.py --iterations 10000 --slate Main
```

### Frontend

```bash
# Run development server
cd frontend
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

## Critical Implementation Details

### Slate Filtering
Only process players matching the target slate:
```python
df_filtered = df[df['Slate'] == 'Main']
```

### Finished Games Detection
Players with `std_dev <= 0.2` are considered finished (actual scores):
```python
finished_mask = df['Std Dev'] <= 0.2
actual_scores[finished_mask] = df.loc[finished_mask, 'Projection']
```

### Slate Types: Main vs Showdown

**CRITICAL**: The system must support two different slate types with different structures.

#### Main Slates (Classic)
- **9 positions**: QB, RB, RB, WR, WR, WR, TE, FLEX, DST
- **Scoring**: Standard DK scoring
- **Multiple games**: Usually 10+ games on slate
- **Lineup matrix shape**: (lineups, players) where each lineup has exactly 9 players

#### Showdown Slates (Single Game)
- **6 positions**: 1 CPT (Captain), 5 FLEX
- **CPT multiplier**: Captain scores 1.5x fantasy points (costs 1.5x salary)
- **No position restrictions**: Any position can fill any slot (except CPT designation)
- **Single game focus**: Only players from 2 teams
- **Lineup matrix shape**: (lineups, players) but need to track captain multiplier

**Implementation considerations:**
```python
# Detect slate type from lineup structure
def get_slate_type(lineup_length: int) -> str:
    return "showdown" if lineup_length == 6 else "main"

# Apply captain multiplier for showdown
def calculate_showdown_scores(lineup_matrix: np.ndarray, player_sims: np.ndarray, captain_indices: np.ndarray) -> np.ndarray:
    """
    For showdown slates, apply 1.5x multiplier to captain position.

    Performance: Still use matrix operations, but apply multiplier vectorized.
    """
    # Base scores
    scores = lineup_matrix @ player_sims

    # Apply captain multiplier (vectorized)
    # captain_indices shape: (lineups,) - which player index is captain for each lineup
    captain_bonus = 0.5 * player_sims[captain_indices, :]  # 0.5 because already counted 1x
    scores += captain_bonus

    return scores
```

**CSV parsing differences:**
- Main slate: Position columns (QB, RB1, RB2, WR1, WR2, WR3, TE, FLEX, DST)
- Showdown slate: CPT + FLEX1-5 columns, need to track which player is captain

### DraftKings Scoring
Standard DraftKings NFL scoring rules (same for both slate types):
- Passing: 0.04 pts/yard, 4 pts/TD, -1 pt/INT
- Rushing/Receiving: 0.1 pts/yard, 6 pts/TD
- Receptions: 1 pt (full PPR)
- Bonus: +3 pts for 100/300 yard games

**Showdown captain**: Apply 1.5x multiplier to total fantasy points

### Payout Structure
Parse from DK contest CSV or use common structures:
- GPP top-heavy (e.g., 1st = 20%, 2nd = 10%, etc.)
- Double-up (top 50% double money)
- 50/50 (top 50% win)

## Development Workflows

### Adding a New CSV Parser

1. Add function to `backend/utils/csv_parser.py`
2. Return standardized DataFrame with required columns
3. Handle missing/invalid data gracefully
4. Add tests with sample CSV

### Modifying Pro-Rating Logic

1. Edit `backend/services/prorate.py`
2. Keep vectorized operations
3. Update tests
4. Benchmark performance impact

### Adding New Metrics

1. Calculate in `backend/services/contest_analyzer.py`
2. Add to API response model
3. Update WebSocket message format
4. Display in frontend component

## Common Gotchas

- **Don't break matrix operations**—loops are 100x slower
- **Finished games have std_dev ≈ 0.1**—detect and handle separately
- **Filter by slate before simulations**—don't simulate irrelevant players
- **Main vs Showdown slates**—detect slate type and apply captain multiplier for showdown (1.5x)
- **Captain multiplier must be vectorized**—don't loop over lineups to apply 1.5x
- **DK player ID matching**—ensure consistency between Stokastic and DK CSVs
- **NumPy random seed**—set for reproducible tests, remove for production
- **WebSocket disconnections**—implement reconnection logic in frontend
- **Memory usage**—with large iterations (100K+), monitor RAM usage

## Live Stats Integration (ESPN API)

### ESPN API Client (`backend/services/espn_api.py`)

**CRITICAL**: Respect rate limits to avoid getting blocked.

```python
# ✅ GOOD - Rate limiting + caching built-in
api = ESPNStatsAPI(
    rate_limit_seconds=30.0,    # 30 seconds between requests
    cache_ttl_seconds=60,        # 60 second cache
    request_timeout=10,          # 10 second timeout
    max_retries=3                # Retry on failure
)

live_games = api.get_live_games()
player_stats = api.get_player_stats(event_id)
fantasy_points = api.get_fantasy_points(event_id)

# ❌ BAD - Hammering the API
while True:
    stats = requests.get(espn_url)  # No rate limiting!
    time.sleep(1)  # Too frequent
```

**Key methods:**
- `get_live_games()` - Returns list of live games with timing info
- `get_player_stats(event_id)` - BoxScore for specific game
- `get_fantasy_points(event_id)` - Calculated DK points
- `get_all_live_stats()` - All players, all live games (orchestration)

**Rate limiting strategy:**
- Per-endpoint tracking (scoreboard vs game summary)
- Automatic waiting if called too soon
- 60-second response caching
- Exponential backoff on errors (1s, 2s, 4s)

### Player Name Matching (`backend/utils/player_mapper.py`)

**Challenge**: ESPN API returns "Patrick Mahomes II", Stokastic CSV has "Patrick Mahomes"

**Strategy:**
1. Exact match (case-insensitive)
2. Manual override lookup (JSON file)
3. Normalized match (remove Jr/Sr/II, apostrophes, periods)
4. Fuzzy match (85% similarity threshold)

```python
# ✅ GOOD - Use the mapper
mapper = PlayerNameMapper()
matched = mapper.match_player(
    espn_name='Patrick Mahomes II',
    stokastic_names=df['Name'].tolist()
)
# Returns: 'Patrick Mahomes'

# Batch matching for efficiency
matches = mapper.batch_match(espn_players, stokastic_names)
```

**Manual overrides** (`backend/data/player_name_overrides.json`):
```json
{
  "Patrick Mahomes II": "Patrick Mahomes",
  "Kenneth Walker III": "Kenneth Walker"
}
```

**Expected match rate:** 95%+

### Live Stats Service (`backend/services/live_stats_service.py`)

**THIS IS THE MAIN ENTRY POINT** for live simulation updates.

```python
# ✅ ONE-LINE USAGE - Handles everything
from services.live_stats_service import LiveStatsService

service = LiveStatsService()
prorated_proj, adjusted_std = service.get_live_projections(stokastic_df)

# Now simulate with live data
scores = run_simulation(prorated_proj, adjusted_std, lineup_matrix, 10000)
```

**What it does automatically:**
1. Fetch live games from ESPN
2. Extract player stats and fantasy points
3. Match ESPN names → Stokastic names (95%+ success)
4. Build `live_stats` dict for pro-rating
5. Call `update_projections_for_live_games()`
6. Return updated arrays ready for simulation

**Monitoring:**
```python
summary = service.get_update_summary()
print(f"Live games: {summary['live_games']}")
print(f"Match rate: {summary['match_rate']:.1f}%")

# Check for unmatched players
unmatched = service.get_unmatched_players(df)
if unmatched:
    print(f"Unmatched: {unmatched}")
```

### Complete Live Update Flow

```python
# Pre-game simulation
baseline_scores = run_simulation(original_proj, original_std, lineup_matrix, 10000)

# During live games
service = LiveStatsService()

while games_in_progress:
    # Get live projections (handles everything)
    live_proj, live_std = service.get_live_projections(stokastic_df)

    # Re-simulate with live data
    live_scores = run_simulation(live_proj, live_std, lineup_matrix, 10000)

    # Analyze and compare
    live_result = analyze_lineup(live_scores, 0, 'MY_LINEUP', 10.0)
    print(f"Win rate: {baseline_result.win_rate} → {live_result.win_rate}")

    # Wait 2-3 minutes before next update (respect rate limits)
    time.sleep(120)
```

### ESPN API Performance Considerations

**Network I/O is the bottleneck** (not computation):

```python
# ✅ GOOD - Parallel API calls (respect rate limits)
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(api.get_player_stats, game_id): game_id
        for game_id in live_game_ids
    }

    all_stats = {}
    for future in concurrent.futures.as_completed(futures):
        game_stats = future.result()
        all_stats.update(game_stats)

# ❌ BAD - Sequential API calls
all_stats = {}
for game_id in live_game_ids:
    stats = api.get_player_stats(game_id)  # Blocks each time
    all_stats.update(stats)
```

**Caching strategy:**
- Scoreboard: 60 seconds (games don't change that fast)
- Game summary: 60 seconds (stats update every minute)
- Never cache during final 2 minutes of quarter (more volatile)

### Error Handling for Live Stats

```python
# ✅ GOOD - Graceful degradation
try:
    live_proj, live_std = service.get_live_projections(df)
except requests.RequestException:
    # ESPN API down - use pregame projections
    logger.warning("ESPN API unavailable, using pregame projections")
    live_proj, live_std = df['Projection'].values, df['Std Dev'].values

except Exception as e:
    # Unexpected error - log and use pregame
    logger.error(f"Live stats error: {e}")
    live_proj, live_std = df['Projection'].values, df['Std Dev'].values
```

**Never let API failures crash the simulation.**

## When in Doubt

1. **Profile first**—never guess what's slow
2. **Vectorize**—use NumPy operations over loops
3. **Cache**—expensive calculations that don't change
4. **Benchmark**—measure performance impact of changes
5. **Ask**—if optimization adds significant complexity, discuss tradeoffs

Remember: This is a performance-critical real-time system. Every optimization matters. Be an S-tier developer—constantly seek efficiency improvements.
