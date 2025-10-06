# NFL DFS Live Simulation System

A real-time Monte Carlo simulation system for analyzing DraftKings NFL GPP contests during live games.

## Overview

This system combines pregame projections from Stokastic with live NFL stats to generate real-time win probability, ROI, and EV estimates for DraftKings tournament entries. It uses matrix-based Monte Carlo simulations to efficiently process thousands of iterations, updating every 2-3 minutes as games progress.

## Purpose

During live NFL slates, this tool:
1. Takes pregame projections (with variance) from Stokastic
2. Fetches live game stats and remaining time
3. Pro-rates projections: `actual_points + (original_projection × pct_game_remaining)`
4. Runs thousands of Monte Carlo simulations using matrix operations
5. Calculates win rate, ROI, and EV for each lineup in the contest
6. Displays real-time standings and probability distributions

## Tech Stack

**Backend:**
- **FastAPI** - Async web framework with WebSocket support
- **NumPy** - Vectorized operations for high-speed simulations
- **Pandas** - CSV parsing and data manipulation
- **SQLite** - Contest and projection storage
- **APScheduler** - Background task scheduling

**Frontend:**
- **React** - UI framework
- **Vite** - Fast development server
- **Recharts/D3** - Probability distribution visualization
- **TailwindCSS** - Styling

## Architecture

```
┌─────────────────┐       ┌──────────────────┐
│  Stokastic CSV  │       │ DraftKings CSV   │
│  (Projections)  │       │ (Contest Entries)│
└────────┬────────┘       └────────┬─────────┘
         │                         │
         └──────────┬──────────────┘
                    ▼
         ┌──────────────────────┐
         │   Database (SQLite)   │
         │  - Players            │
         │  - Projections        │
         │  - Lineups            │
         └──────────┬────────────┘
                    │
         ┌──────────▼────────────┐
         │  Live Stats Fetcher   │◄─── NFL/ESPN API (every 2-3 min)
         │  (Game clock, points) │
         └──────────┬────────────┘
                    ▼
         ┌──────────────────────┐
         │  Pro-Rate Projections │
         │  actual + (proj × %)  │
         └──────────┬────────────┘
                    ▼
         ┌──────────────────────────────────┐
         │  Matrix-Based Monte Carlo Sim    │
         │  1. Generate player sims matrix  │
         │  2. Create lineup matrix         │
         │  3. Matrix multiply → all scores │
         └──────────┬───────────────────────┘
                    ▼
         ┌──────────────────────┐
         │   Contest Analyzer    │
         │  - Rank lineups       │
         │  - Apply payouts      │
         │  - Calculate metrics  │
         └──────────┬────────────┘
                    ▼
         ┌──────────────────────┐
         │   WebSocket Push      │
         └──────────┬────────────┘
                    ▼
         ┌──────────────────────┐
         │   React Dashboard     │
         │  - Live standings     │
         │  - Win probabilities  │
         │  - ROI/EV metrics     │
         └───────────────────────┘
```

## Key Features

### Matrix-Based Simulations
Instead of looping through iterations, the system uses NumPy matrix operations:
```python
# Generate all simulations at once (players × iterations)
player_simulations = np.random.normal(projections, std_devs, (num_players, num_iterations))

# Create lineup matrix (lineups × players)
lineup_matrix = binary_matrix where 1 = player in lineup

# Calculate all lineup scores with single matrix multiplication
all_scores = lineup_matrix @ player_simulations  # (lineups × iterations)
```

This approach enables 10,000+ iterations in under a second.

### Real-Time Updates
- Background scheduler polls live stats every 2-3 minutes
- Pro-rates projections based on actual performance and remaining game time
- Re-runs simulations with updated data
- Pushes results to frontend via WebSocket

### Contest Analysis
- Win probability distribution for each lineup
- Expected value (EV) and ROI calculations
- Comparison of pregame vs. live win rates
- Identification of your lineups in the contest

### Slate Type Support
The system supports both DraftKings slate formats:

**Main Slates (Classic):**
- 9-player lineups: QB, RB, RB, WR, WR, WR, TE, FLEX, DST
- Multiple games (typically Sunday slate with 10+ games)
- Standard scoring

**Showdown Slates (Single Game):**
- 6-player lineups: 1 CPT (Captain) + 5 FLEX
- Captain scores 1.5x fantasy points
- No positional restrictions (any player can fill any slot)
- Single game between 2 teams

The system automatically detects slate type from lineup structure and applies appropriate scoring logic.

## Setup

### Requirements
- Python 3.9+
- Node.js 16+

### Installation

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### Running the Application

**Backend:**
```bash
cd backend
uvicorn main:app --reload
```
Backend runs on `http://localhost:8000`

**Frontend:**
```bash
cd frontend
npm run dev
```
Frontend runs on `http://localhost:5173`

## Usage

### 1. Prepare CSV Files

**Stokastic Projections CSV:**
Required columns:
- `Name` - Player name
- `Position` - QB, RB, WR, TE, DST
- `Salary` - DraftKings salary
- `Projection` - Projected fantasy points
- `Std Dev` - Standard deviation for simulations
- `Slate` - Slate identifier (e.g., "Main", "Sunday")

Optional columns: `Ceiling`, `Boom%`, `Bust%`, `Own%`

**DraftKings Contest CSV:**
Export your contest from DraftKings with all entries. Must include:
- Player names/IDs for each lineup
- Usernames
- Lineup compositions:
  - Main slate: 9 players (QB, RB, RB, WR, WR, WR, TE, FLEX, DST)
  - Showdown slate: 6 players (CPT + 5 FLEX)

### 2. Upload CSVs
Navigate to the dashboard and upload both CSV files.

### 3. Monitor Live Games
The system automatically:
- Fetches live stats every 2-3 minutes
- Updates pro-rated projections
- Re-runs simulations
- Displays updated win rates and standings

### 4. View Results
Dashboard shows:
- Current contest standings
- Your lineup positions
- Win probability distributions
- ROI and EV estimates
- Pregame vs. live comparison

## CSV Format Examples

### Stokastic CSV
```csv
Name,Team,Salary,Position,Projection,Std Dev,Ceiling,Slate
Jahmyr Gibbs,DET,7700,RB,21.8,8.1,27.3,Main
Patrick Mahomes,KC,6600,QB,20.7,6.9,25.4,Main
```

### DraftKings Contest CSV

**Main Slate:**
```csv
EntryId,EntryName,QB,QBId,RB1,RB1Id,RB2,RB2Id,WR1,WR1Id,...,DST,DSTId
12345,User1,Patrick Mahomes,1234,Jahmyr Gibbs,5678,...
```

**Showdown Slate:**
```csv
EntryId,EntryName,CPT,CPTId,FLEX1,FLEX1Id,FLEX2,FLEX2Id,...,FLEX5,FLEX5Id
12345,User1,Patrick Mahomes,1234,Travis Kelce,5678,...
```
Note: CPT player receives 1.5x scoring multiplier

## Data Flow Details

### Pro-Rating Logic
For each player:
1. **Finished game** (std_dev ≈ 0.1): Use actual fantasy points
2. **Live game**:
   - Get actual points scored so far
   - Calculate % of game remaining
   - Pro-rated projection = `actual + (original_projection × pct_remaining)`
   - Example: Player has 10 pts at halftime, projected 20 → `10 + (20 × 0.5) = 20`

### Simulation Process
1. Generate simulation matrix (players × iterations)
2. For each iteration:
   - Each player gets randomized score from normal distribution
   - Mean = pro-rated projection
   - Std dev = original std dev (or scaled by time remaining)
3. Calculate all lineup scores via matrix multiplication
4. Rank lineups in each iteration
5. Apply payout structure
6. Aggregate win rate, ROI, EV across all iterations

## Performance

- **Simulation speed**: 10,000 iterations in <2 seconds (typical)
- **Update cycle**: <5 seconds total (fetch stats → simulate → push results)
- **Handles**: 500+ players, 1000+ lineups efficiently

## Development Roadmap

**Current (v1):**
- Matrix-based simulations
- Simple pro-rating logic
- Single slate support
- No player correlation

**Future (v2+):**
- Player correlation (QB-WR stacks, RB-DST anti-correlation)
- Improved variance modeling
- Multi-slate support
- Historical result tracking
- Advanced payout structures

## Troubleshooting

**Slow simulations:**
- Check number of iterations (reduce if needed)
- Verify NumPy is using optimized BLAS libraries
- Profile code to identify bottlenecks

**Live stats not updating:**
- Check API rate limits
- Verify game is in progress
- Check scheduler is running

**Incorrect win rates:**
- Verify DraftKings payout structure
- Check CSV data quality
- Ensure slate filtering is correct

## License

Private project for personal use.
