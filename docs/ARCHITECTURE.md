# Architecture Documentation

## System Overview

NFL DFS Live Standings is a real-time Monte Carlo simulation platform for DraftKings NFL fantasy contests. The system fetches live player statistics during games, pro-rates projections, and runs thousands of simulations to calculate win rates, ROI, and expected value.

## Core Design Principles

### 1. **Performance First**
- All hot paths use NumPy vectorized operations (no Python loops)
- Matrix-based simulation: 141,000+ iterations/second
- Single matrix multiplication handles all lineups simultaneously
- Sub-10ms pro-rating for 500 players

### 2. **Real-Time Updates**
- Poll ESPN API every 2-3 minutes during live games
- 60-second response caching to respect rate limits
- Pro-rate projections: `actual + (original × pct_remaining)`
- Variance adjustment: `std_dev × sqrt(pct_remaining)`

### 3. **Simplicity & Reliability**
- Pure NumPy/Pandas (no heavy ML frameworks)
- Stateless services (no complex state management)
- Extensive test coverage (48/48 tests passing)
- Defensive error handling throughout

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                             │
├──────────────────────────┬──────────────────────────────────────┤
│ Stokastic CSV            │ DraftKings Contest CSV                │
│ - Pregame projections    │ - User lineups                        │
│ - Standard deviations    │ - Entry IDs                           │
│ - Player metadata        │ - Usernames                           │
└──────────┬───────────────┴──────────────┬───────────────────────┘
           │                               │
           ▼                               ▼
    ┌──────────────┐              ┌──────────────┐
    │  CSV Parser  │              │  CSV Parser  │
    │  (Stokastic) │              │  (DraftKings)│
    └──────┬───────┘              └───────┬──────┘
           │                              │
           │  ┌───────────────────────────┘
           │  │
           ▼  ▼
    ┌──────────────────┐
    │ Player Index Map │  ← Name → Array Index
    │ Lineup Matrix    │  ← Binary matrix (lineups × players)
    └─────────┬────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LIVE STATS PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ESPN API ─→ Player Stats ─→ Name Matching ─→ Pro-rating        │
│     ↓            ↓               ↓                  ↓            │
│  Live games  Fantasy pts    Stokastic name    Updated arrays     │
│                                                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SIMULATION ENGINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Generate Player Simulations (iterations × players)           │
│     - np.random.normal(projections, std_devs, iterations)        │
│                                                                   │
│  2. Calculate Lineup Scores (MATRIX MULTIPLY)                    │
│     - scores = lineup_matrix @ player_simulations                │
│     - Single operation, all lineups at once                      │
│                                                                   │
│  3. Handle Showdown Captain (if applicable)                      │
│     - Add 0.5× bonus for captain                                 │
│                                                                   │
│  Output: scores matrix (lineups × iterations)                    │
│                                                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEST ANALYZER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Calculate Rankings (np.argsort per iteration)                │
│  2. Compute Statistics:                                          │
│     - Win rate                                                   │
│     - Top 3 rate                                                 │
│     - Expected value                                             │
│     - ROI                                                        │
│     - Average finish                                             │
│                                                                   │
│  Output: ContestAnalysis dataclass                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### Data Layer

#### **CSV Parsers** (`utils/csv_parser.py`)
- `parse_stokastic_csv()` - Load pregame projections
- `parse_dk_contest_csv()` - Extract contest lineups
- `parse_lineup_string()` - Handle DK's position-prefixed format
- `create_player_index_map()` - Build name → index mapping
- `create_lineup_matrix()` - Binary matrix for matrix multiplication

**Performance:** O(n) parsing, O(1) lookups via index map

---

### Live Stats Layer

#### **ESPN API Client** (`services/espn_api.py`)
- **Rate Limiting:** 30 seconds between requests per endpoint
- **Caching:** 60-second TTL on responses
- **Retry Logic:** Exponential backoff (1s, 2s, 4s)
- **Endpoints:**
  - `get_scoreboard()` - All games
  - `get_live_games()` - Filter for live games
  - `get_player_stats()` - Boxscore for a game
  - `get_fantasy_points()` - Convert to DK scoring
  - `get_all_live_stats()` - All players, all live games

**Output Format:**
```python
{
    'Patrick Mahomes': {
        'actual_points': 18.5,
        'pct_remaining': 0.5,
        'is_finished': False,
        'team': 'Kansas City Chiefs',
        'game': 'KC @ BUF'
    }
}
```

#### **Player Name Mapper** (`utils/player_mapper.py`)
- **Normalization:** Remove Jr/Sr/II, apostrophes, periods
- **Fuzzy Matching:** 85% similarity threshold (Levenshtein)
- **Manual Overrides:** JSON file for edge cases
- **Match Rate:** 95%+ in practice

**Matching Strategy:**
1. Exact match (case-insensitive)
2. Manual override lookup
3. Normalized exact match
4. Fuzzy match (threshold 0.85)

#### **Live Stats Service** (`services/live_stats_service.py`)
- **Orchestration layer** combining ESPN + mapping + pro-rating
- Single entry point: `get_live_projections(stokastic_df)`
- Returns: `(prorated_projections, adjusted_std_devs)`

**Workflow:**
```
ESPN API → Extract stats → Match names → Build live_stats dict → Pro-rate → Return arrays
```

---

### Pro-Rating Layer

#### **Pro-Rating Service** (`services/prorate.py`)
- **Formula:** `actual_points + (original_projection × pct_remaining)`
- **Time Calculation:** Quarter + clock → percentage remaining
- **Variance Adjustment:** `std_dev × sqrt(pct_remaining)`
- **Finished Games:** Use actual only, std_dev = 0.1

**Vectorized Operations:**
```python
# All players pro-rated in single operation
prorated[live_mask] = actual[live_mask] + (projections[live_mask] * pct_remaining[live_mask])
prorated[finished_mask] = actual[finished_mask]
```

**Performance:** <10ms for 500 players

---

### Simulation Layer

#### **Simulator** (`services/simulator.py`)
- **THE PERFORMANCE BOTTLENECK** - Fully optimized
- **Matrix-based approach** (not loops)

**Key Functions:**

**1. Generate Player Simulations**
```python
player_sims = np.random.normal(
    loc=projections[:, np.newaxis],
    scale=std_devs[:, np.newaxis],
    size=(num_players, iterations)
)
# Shape: (500 players, 10000 iterations)
```

**2. Calculate Lineup Scores (CRITICAL)**
```python
scores = lineup_matrix @ player_sims
# (num_lineups, num_players) @ (num_players, iterations)
# = (num_lineups, iterations)
```

This single matrix multiplication:
- Handles ALL lineups simultaneously
- 100-1000× faster than loops
- Leverages optimized BLAS libraries

**3. Showdown Captain (if applicable)**
```python
captain_bonus = 0.5 * player_sims[captain_indices, :]
scores += captain_bonus
# Adds 0.5× for 1.5× total multiplier
```

**Performance:**
- 141,000 - 209,000 iterations/second
- 10,000 iterations in <2 seconds
- Scales linearly with num_players and iterations

---

### Analysis Layer

#### **Contest Analyzer** (`services/contest_analyzer.py`)
- Calculate finish positions across all iterations
- Compute win rates, ROI, expected value
- Support custom payout structures

**Ranking Algorithm:**
```python
sorted_indices = np.argsort(-scores, axis=0)  # Descending
# Each column = finish positions for one iteration
```

**Metrics Calculated:**
- **Win Rate:** % of iterations finishing 1st
- **Top N Rate:** % finishing in top N
- **Expected Value:** Average payout - entry fee
- **ROI:** (EV / entry_fee) × 100%
- **Average Finish:** Mean finish position

---

## Data Flow

### Pregame Simulation
```
Stokastic CSV → Parse → Index Map → Lineup Matrix
                                         ↓
Contest CSV → Parse Lineups ──────────────┘
                                         ↓
                              Run Simulation (10K iterations)
                                         ↓
                              Analyze Results (win rates, ROI)
```

### Live Simulation
```
ESPN API → Live Games → Player Stats → DK Fantasy Points
                                            ↓
                                    Match Names (95% success)
                                            ↓
                                    Pro-rate Projections
                                            ↓
                              Run Simulation (10K iterations)
                                            ↓
                              Compare vs Pregame
```

---

## Performance Characteristics

### Matrix-Based Simulation
- **Speed:** 141,000 - 209,000 iterations/second
- **Scaling:** Linear with iterations and players
- **Memory:** O(num_players × iterations) for player sims
- **Bottleneck:** Matrix multiplication (BLAS optimized)

### Pro-Rating
- **Speed:** <10ms for 500 players
- **Scaling:** O(num_players), vectorized
- **Memory:** O(num_players) for arrays
- **Bottleneck:** ESPN API network latency

### ESPN API
- **Rate Limit:** 30 seconds between requests (self-imposed)
- **Cache TTL:** 60 seconds
- **Network:** <500ms typical response time
- **Bottleneck:** Network I/O, not computation

---

## Scalability Considerations

### Current Limits
- **Players:** Tested up to 500 (Stokastic CSV size)
- **Lineups:** Tested up to 13,000 (real contest)
- **Iterations:** Tested up to 100,000 (diminishing returns after 10K)

### Bottlenecks
1. **Memory:** Player simulations matrix (500 × 100,000 = 50M floats ≈ 400MB)
2. **Matrix Multiply:** O(lineups × players × iterations) time complexity
3. **ESPN API:** Network latency during live games

### Optimization Opportunities
- **Sparse matrices:** If many lineups share players
- **Batch processing:** Split large simulations
- **GPU acceleration:** CUDA for massive parallelization (overkill for current scale)

---

## Testing Strategy

### Unit Tests
- **Simulator:** Shape validation, mean correctness, captain multiplier
- **Pro-rating:** Time calculation, formula correctness, edge cases
- **Parser:** CSV format handling, name cleaning, lineup extraction

### Integration Tests
- **End-to-end flow:** Stokastic → Pro-rate → Simulate → Analyze
- **ESPN API:** Live data fetching, name matching, full pipeline
- **Performance:** Speed benchmarks, regression detection

### Test Coverage
- **48/48 tests passing** (16 simulator + 27 prorate + 5 ESPN integration)
- **Performance tests:** Ensure <2s for 10K iterations
- **Edge cases:** Empty arrays, zero variance, finished games

---

## Future Architecture Considerations

### Phase 3: Automation
- Background scheduler (APScheduler or similar)
- WebSocket for real-time frontend updates
- Contest state management (detect game start/end)

### Phase 4: Backend API
- FastAPI endpoints (already stubbed)
- Request/response models (Pydantic)
- Results caching (Redis or in-memory)

### Phase 5: Frontend
- React dashboard
- Real-time standings table
- Player performance drill-down
- WebSocket client for live updates

---

## Technology Stack

### Core
- **Python 3.12+**
- **NumPy 1.24+** - Vectorized operations, matrix math
- **Pandas 2.0+** - CSV parsing, data manipulation

### API/Services
- **FastAPI 0.104+** - REST API framework (Phase 4)
- **Requests** - HTTP client for ESPN API
- **Pydantic 2.0+** - Data validation

### Testing
- **pytest 7.4+** - Unit and integration tests
- **pytest-asyncio** - Async test support

### Development
- **SnakeViz** - Profiling visualization

---

## Key Design Decisions

### Why Matrix Multiplication?
- **100-1000× faster** than loops
- Leverages optimized BLAS libraries (OpenBLAS, MKL)
- Natural representation: lineups select players

### Why ESPN API?
- **Free** and accessible
- Real-time during live games
- Comprehensive player stats
- No authentication required

### Why NumPy (not ML frameworks)?
- **Simplicity:** No need for TensorFlow/PyTorch overhead
- **Speed:** NumPy is fast enough for our scale
- **Portability:** Easier deployment, smaller dependencies

### Why Vectorized Pro-Rating?
- **Performance:** <10ms for 500 players
- **Consistency:** All players updated atomically
- **Correctness:** No loop indexing errors

---

## Monitoring & Observability

### Current Logging
- ESPN API requests (rate limiting, errors)
- Player name matching (unmatched players logged)
- Simulation performance (timing)

### Metrics to Track (Future)
- API response times
- Name match rate
- Simulation throughput
- Cache hit rate
- Error rates

---

## Security Considerations

### Data Privacy
- **No user authentication** (public contests only)
- **No PII storage** (usernames from public contests)
- **No financial transactions** (read-only simulation)

### API Usage
- **Respectful polling** (2-3 minute intervals)
- **Rate limiting** (30 second minimum)
- **Caching** (reduce load on ESPN)

---

## References

- [DraftKings Scoring Rules](https://www.draftkings.com/help/rules)
- [ESPN API (Unofficial)](https://github.com/nntrn/espn-api-docs)
- [NumPy Performance Guide](https://numpy.org/doc/stable/user/basics.performance.html)
