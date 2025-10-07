# NFL DFS Live Standings

**Real-time Monte Carlo simulation platform for DraftKings NFL fantasy contests**

Track your lineup's win probability in real-time as games progress. See how every touchdown, interception, and big play affects your chances of winning.

---

## 🎯 Features

- **⚡ Blazing Fast Simulations** - 141,000+ iterations/second using matrix-based Monte Carlo
- **📊 Live Updates** - Real-time player stats from ESPN API during NFL games
- **🎲 Pro-Rated Projections** - Intelligent projections: `actual + (original × remaining_time)`
- **📈 Win Rate Analysis** - Calculate win probability, ROI, and expected value
- **🏈 Contest Parser** - Extract 13,000+ lineups from DraftKings CSV exports
- **🤖 95%+ Name Matching** - Automatic player name matching between ESPN and Stokastic
- **🔄 Background Automation** - Auto-update contests every 2 minutes during live games
- **📡 WebSocket Support** - Real-time push notifications via WebSocket
- **✅ 60+ Tests Passing** - Comprehensive test suite with automation tests

---

## 🚀 Quick Start

### Backend Setup

```bash
# Clone repository
git clone https://github.com/JoshEngleman/nfl-live-standings.git
cd nfl-live-standings/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend API (on port 8001)
uvicorn main:app --reload
```

### Frontend Setup

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Access the dashboard at **http://localhost:5173**

---

## 📖 Table of Contents

- [How It Works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)
- [Performance](#performance)
- [Testing](#testing)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

---

## 🧠 How It Works

### Pre-Game Simulation

1. **Load Data** - Import Stokastic projections and DraftKings contest lineups
2. **Run Simulations** - Generate 10,000+ fantasy score scenarios using Monte Carlo method
3. **Calculate Odds** - Determine win rate, top-3 rate, ROI, and expected value for each lineup

### Live Updates (During Games)

1. **Fetch Stats** - Pull real-time player statistics from ESPN API every 2-3 minutes
2. **Pro-Rate** - Update projections based on actual performance + time remaining
3. **Re-Simulate** - Run new Monte Carlo simulations with updated projections
4. **Compare** - See how your win rate changes in real-time

### The Magic: Matrix-Based Simulation

Instead of looping through lineups, we use a single matrix multiplication:

```python
# Traditional approach (slow)
for lineup in lineups:
    for iteration in iterations:
        score = sum(player_scores for player in lineup)

# Our approach (100-1000× faster)
scores = lineup_matrix @ player_simulations
```

This single operation calculates **all lineups across all iterations simultaneously**.

---

## 💻 Installation

### Requirements

- Python 3.12+
- NumPy 1.24+
- Pandas 2.0+

### Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd nfl-live-standings

# 2. Create virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add Stokastic CSV (download from Stokastic.com)
# Place "NFL DK Boom Bust.csv" in project root

# 5. Run tests to verify
pytest
```

---

## 🎮 Usage

### Basic Simulation

```bash
# Simulate random lineups
python run_simulation.py --iterations 10000 --num-lineups 50
```

### Live ESPN Integration

```bash
# Real-time simulation during live games
python demo_espn_live.py
```

**Best run during:**
- Sunday 1pm ET / 4pm ET slates
- Sunday Night Football (~8:20pm ET)
- Monday Night Football (~8:15pm ET)

### Contest Analysis

```bash
# Parse actual DraftKings contest
python demo_contest_parser.py

# Analyze specific contest CSV
python -c "
from utils.csv_parser import parse_dk_contest_csv
lineups, entry_ids, usernames, slate_type = parse_dk_contest_csv('contest.csv')
print(f'Parsed {len(lineups)} {slate_type} lineups')
"
```

### Programmatic Usage

```python
from utils.csv_parser import parse_stokastic_csv, create_lineup_matrix, create_player_index_map
from services.simulator import run_simulation
from services.contest_analyzer import analyze_lineup

# Load data
df = parse_stokastic_csv("NFL DK Boom Bust.csv", slate_filter="Main")
player_index_map = create_player_index_map(df)

# Define lineup
your_lineup = ['Patrick Mahomes', 'Christian McCaffrey', 'Tyreek Hill', ...]
lineups = [your_lineup]

# Create lineup matrix
lineup_matrix = create_lineup_matrix(lineups, player_index_map, len(df))

# Run simulation
scores = run_simulation(
    projections=df['Projection'].values,
    std_devs=df['Std Dev'].values,
    lineup_matrix=lineup_matrix,
    iterations=10000
)

# Analyze results
result = analyze_lineup(scores, lineup_idx=0, entry_name='MY_LINEUP', entry_fee=10.0)
print(f"Win Rate: {result.win_rate * 100:.1f}%")
print(f"ROI: {result.roi:.1f}%")
```

### Live Updates (Programmatic)

```python
from services.live_stats_service import LiveStatsService
from services.simulator import run_simulation

# Initialize live stats service
service = LiveStatsService()

# Get live-updated projections
prorated_proj, adjusted_std = service.get_live_projections(df)

# Run simulation with live data
live_scores = run_simulation(prorated_proj, adjusted_std, lineup_matrix, 10000)

# Compare to pre-game results
# ... analyze changes in win rates, ROI, etc.
```

### Automation (Phase 3)

```bash
# Run automated background updates (demo)
python examples/demo_automation.py
```

**API Server with WebSocket:**
```bash
# Start FastAPI server
cd backend
uvicorn main:app --reload

# Access at http://localhost:8000
# WebSocket at ws://localhost:8000/ws
```

**API Endpoints:**
```bash
# Health check
curl http://localhost:8000/health

# List all contests
curl http://localhost:8000/api/contests

# Get contest details
curl http://localhost:8000/api/contests/{contest_id}

# Start background updater (auto-updates every 2 min)
curl -X POST http://localhost:8000/api/updater/control \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'

# Trigger manual update immediately
curl -X POST http://localhost:8000/api/updater/trigger

# Stop background updater
curl -X POST http://localhost:8000/api/updater/control \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'
```

**WebSocket Client (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update received:', data);

  if (data.type === 'contest_update') {
    // Handle live contest update
    console.log(`Contest ${data.contest_id} updated`);
    console.log(`Live games: ${data.data.live_games}`);
    console.log(`Match rate: ${data.data.match_rate}%`);
  }
};

// Request status
ws.send(JSON.stringify({command: 'get_status'}));
```

---

## 📚 Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design, data flow, performance characteristics
- **[API Reference](docs/API.md)** - Complete API documentation for all services
- **[Development Guide](docs/DEVELOPMENT.md)** - Setup, testing, debugging, code style
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Installation, configuration, production deployment
- **[CLAUDE.md](CLAUDE.md)** - AI assistant development guide (for Claude Code users)

---

## ⚡ Performance

### Simulation Speed

| Iterations | Players | Lineups | Time | Throughput |
|-----------|---------|---------|------|------------|
| 10,000 | 500 | 3 | 1.4s | 141,000 iter/s |
| 10,000 | 500 | 10 | 1.6s | 158,000 iter/s |
| 100,000 | 500 | 3 | 12.8s | 187,000 iter/s |

**Tested on:** MacBook Pro M1, NumPy 1.24

### Pro-Rating Speed

- **500 players:** <10ms
- **Vectorized operations:** O(num_players) complexity
- **No Python loops:** Pure NumPy

### ESPN API

- **Response time:** <500ms typical
- **Rate limiting:** 30 seconds between requests (self-imposed)
- **Caching:** 60-second TTL to reduce load

---

## 🧪 Testing

### Run Test Suite

```bash
# All tests
pytest

# Specific modules
pytest tests/test_simulator.py
pytest tests/test_prorate.py
pytest tests/test_espn_integration.py

# With coverage
pytest --cov=services --cov=utils

# Integration tests
python tests/test_live_integration.py
```

### Test Coverage

- **48 tests total**
  - 16 simulator tests (shapes, correctness, performance)
  - 27 pro-rating tests (time calc, formulas, edge cases)
  - 5 ESPN integration tests (API, matching, full pipeline)

- **All tests passing ✅**

### Performance Benchmarks

Tests ensure no performance regression:
- Simulator: Must complete 10K iterations in <2 seconds
- Pro-rating: Must process 500 players in <10ms

---

## 🏗️ Architecture

### System Overview

```
Data Sources → Parsers → Simulation Engine → Contest Analyzer
     ↓           ↓              ↓                  ↓
  ESPN API → Name Matcher → Pro-Rating → Updated Projections
```

### Core Components

1. **Simulator** (`services/simulator.py`)
   - Matrix-based Monte Carlo engine
   - 100-1000× faster than loop-based approaches
   - Supports main and showdown slates

2. **Pro-Rating** (`services/prorate.py`)
   - Formula: `actual + (original × pct_remaining)`
   - Variance adjustment: `std_dev × sqrt(pct_remaining)`
   - Vectorized for performance

3. **ESPN API Client** (`services/espn_api.py`)
   - Real-time NFL player stats
   - Rate limiting and caching
   - DraftKings fantasy points calculation

4. **Live Stats Service** (`services/live_stats_service.py`)
   - Orchestration layer
   - Name matching (95%+ success rate)
   - Single entry point for live updates

5. **Contest Analyzer** (`services/contest_analyzer.py`)
   - Win rate, ROI, EV calculations
   - Ranking across iterations
   - Custom payout structures

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design documentation.

---

## 🎨 Project Structure

```
nfl-live-standings/
├── backend/                   # Python backend
│   ├── services/              # Core business logic
│   │   ├── simulator.py           # Monte Carlo engine ⚡
│   │   ├── espn_api.py            # ESPN API client
│   │   ├── prorate.py             # Pro-rating logic
│   │   ├── live_stats_service.py  # Orchestration
│   │   ├── contest_analyzer.py    # Win rate analysis
│   │   ├── contest_state_manager.py  # State tracking
│   │   └── live_updater_service.py   # Background automation
│   ├── utils/                 # Utilities
│   │   ├── csv_parser.py          # Stokastic/DK parsing
│   │   └── player_mapper.py       # Name matching
│   ├── tests/                 # Test suite (60+ tests)
│   ├── data/                  # Configuration
│   │   └── player_name_overrides.json
│   ├── main.py                # FastAPI application
│   └── requirements.txt       # Dependencies
├── frontend/                  # React frontend (Phase 5)
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── services/          # API & WebSocket clients
│   │   ├── hooks/             # Custom React hooks
│   │   ├── types/             # TypeScript definitions
│   │   └── App.tsx            # Main app
│   ├── package.json
│   └── vite.config.ts
├── examples/                  # Demo scripts
│   ├── demo_espn_live.py
│   ├── demo_contest_parser.py
│   └── demo_automation.py
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEVELOPMENT.md
│   └── DEPLOYMENT.md
├── README.md                  # This file
├── CLAUDE.md                  # AI assistant guide
└── .gitignore
```

---

## 🔮 Roadmap

### ✅ Phase 1: Core Simulation (Complete)
- Matrix-based Monte Carlo simulator
- CSV parsers (Stokastic, DraftKings)
- Contest analyzer
- Main and showdown slate support

### ✅ Phase 2A: Pro-Rating (Complete)
- Pro-rating formula
- Variance adjustment
- Mock scenarios for testing

### ✅ Phase 2B: ESPN Integration (Complete)
- ESPN API client
- Player name matching
- Live stats orchestration
- Integration tests

### ✅ Phase 3: Automation (Complete)
- Background scheduler (every 2-3 minutes)
- WebSocket for real-time updates
- Contest state management
- FastAPI endpoints for contest control
- Automated live updates during games

### ✅ Phase 5: Frontend (Complete)
- React + TypeScript dashboard
- Real-time standings table
- WebSocket live updates
- Updater control panel
- Toast notifications
- Responsive design

### 📋 Phase 4: Backend API (Next)
- File upload endpoints
- Full simulation API
- Results caching
- OpenAPI documentation

---

## 🤝 Contributing

Contributions welcome! Areas of interest:

- **Performance optimization** - Make it even faster
- **Additional data sources** - Alternative APIs for live stats
- **Enhanced name matching** - Improve the 95% → 99%
- **Frontend development** - React dashboard (Phase 5)
- **Testing** - Additional edge cases, integration tests

### Development Setup

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed instructions.

### Code Style

- Type hints on all functions
- Docstrings (Google style)
- NumPy operations (not loops) for performance-critical code
- Comprehensive tests for new features

---

## 📊 Example Output

### Pre-Game Simulation
```
📈 YOUR PRE-GAME OUTLOOK:
   Win Rate:        89.1%
   Top 3 Rate:     100.0%
   Expected Value: $ 14.06
   ROI:             140.6%
   Avg Finish:       1.1
```

### Live Update
```
📊 Live Stats Summary:
   Live games: 3
   Players with stats: 42
   Players matched: 41
   Players unmatched: 1
   Match rate: 97.6%

📈 UPDATED PROJECTIONS:
   Patrick Mahomes      20.7 pts →  24.3 pts   +3.6 pts ⬆
   Travis Kelce         15.2 pts →  12.1 pts   -3.1 pts ⬇
```

### Comparison
```
📊 PRE-GAME vs LIVE COMPARISON
   Metric               Pre-Game     Live         Change
   Win Rate               89.1%       94.3%     +5.2% ⬆
   Expected Value       $ 14.06     $ 16.24    +$2.18 ⬆
```

---

## 🛠️ Tech Stack

- **Python 3.12+** - Core language
- **NumPy** - Vectorized operations, matrix math
- **Pandas** - Data manipulation, CSV parsing
- **pytest** - Testing framework
- **FastAPI** - REST API (Phase 4)
- **React** - Frontend (Phase 5)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

- **Stokastic** - For fantasy projections
- **DraftKings** - For the contest platform
- **ESPN** - For the unofficial API
- **NumPy Community** - For blazing-fast linear algebra

---

## 📞 Contact

- **Issues:** [GitHub Issues](https://github.com/yourusername/nfl-live-standings/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/nfl-live-standings/discussions)

---

## ⭐ Star This Project

If you find this useful, please star the repository! It helps others discover the project.

---

**Built with ⚡ and 🏈 for the DFS community**
