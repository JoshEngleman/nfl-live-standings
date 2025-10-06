# Development Guide

## Getting Started

### Prerequisites
- Python 3.12+
- pip or pipenv
- Git

### Initial Setup

```bash
# Clone repository
git clone <repo-url>
cd nfl-live-standings

# Create virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Project Structure

```
nfl-live-standings/
├── backend/
│   ├── services/          # Core business logic
│   │   ├── simulator.py       # Monte Carlo engine
│   │   ├── espn_api.py        # ESPN API client
│   │   ├── prorate.py         # Pro-rating logic
│   │   └── live_stats_service.py  # Orchestration
│   ├── utils/             # Utilities
│   │   ├── csv_parser.py      # CSV parsing
│   │   └── player_mapper.py   # Name matching
│   ├── tests/             # Test suite
│   ├── data/              # Configuration files
│   └── main.py           # FastAPI app (stub)
├── examples/              # Demo scripts
├── docs/                  # Documentation
└── README.md
```

---

## Running Tests

### All Tests
```bash
# Run full test suite
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=services --cov=utils
```

### Specific Test Files
```bash
# Simulator tests
pytest tests/test_simulator.py

# Pro-rating tests
pytest tests/test_prorate.py

# ESPN integration
pytest tests/test_espn_integration.py
```

### Integration Tests
```bash
# End-to-end live simulation
python tests/test_live_integration.py

# ESPN API integration (needs network)
python tests/test_espn_integration.py
```

---

## Running Demos

### Basic Simulation
```bash
python run_simulation.py --iterations 10000 --num-lineups 50
```

### Live ESPN Demo
```bash
# Best during Sunday games
python demo_espn_live.py
```

### Contest Parser Demo
```bash
python demo_contest_parser.py
```

---

## Code Organization

### Services (Hot Paths - Performance Critical)

**`simulator.py`** - THE BOTTLENECK
- Never refactor matrix multiplication to loops
- All operations must be vectorized
- Target: <2s for 10K iterations

**`prorate.py`** - Performance Critical
- Vectorized operations only
- Target: <10ms for 500 players

**`espn_api.py`** - Network I/O
- Rate limiting required (30s between requests)
- Caching (60s TTL)
- Retry logic with backoff

### Utilities (Not Performance Critical)

**`csv_parser.py`** - Data loading
- Runs once at startup
- Can use pandas operations freely

**`player_mapper.py`** - Name matching
- Runs once per update cycle
- Caching for repeated lookups

---

## Performance Profiling

### Using SnakeViz
```bash
# Profile a simulation
python -m cProfile -o profile.prof run_simulation.py

# Visualize
snakeviz profile.prof
```

### Benchmark Script
```python
import time
import numpy as np
from services.simulator import run_simulation

# Setup
projections = np.random.uniform(10, 30, 500)
std_devs = np.random.uniform(3, 8, 500)
lineup_matrix = np.random.randint(0, 2, (10, 500))

# Benchmark
start = time.time()
scores = run_simulation(projections, std_devs, lineup_matrix, 10000)
duration = time.time() - start

print(f"10K iterations: {duration:.2f}s")
print(f"Throughput: {10000/duration:.0f} iterations/second")
```

---

## Adding New Features

### Adding a New Service

1. Create file in `backend/services/`
2. Follow existing patterns (type hints, docstrings)
3. Write unit tests in `tests/test_<service>.py`
4. Update `docs/API.md` with new API

Example:
```python
# backend/services/my_service.py
"""
My new service description.
"""

import numpy as np
from typing import Dict

def my_function(data: np.ndarray) -> Dict:
    """
    Do something with data.

    Args:
        data: Input array

    Returns:
        Results dictionary
    """
    # Implementation
    return {}
```

### Adding a New CSV Parser

1. Add function to `utils/csv_parser.py`
2. Write tests in `tests/test_parser.py`
3. Document format in `docs/API.md`

### Adding ESPN API Endpoints

1. Add method to `ESPNStatsAPI` class
2. Follow rate limiting patterns
3. Add caching if appropriate
4. Test with real API

---

## Testing Strategy

### Unit Tests
- Test individual functions
- Mock external dependencies (ESPN API)
- Fast execution (<1s total)

### Integration Tests
- Test complete workflows
- Use real data when possible
- May require network access

### Performance Tests
- Benchmark critical paths
- Fail if regression detected
- Run on consistent hardware

---

## Common Development Tasks

### Update Stokastic CSV
```bash
# Download new CSV from Stokastic
# Save as "NFL DK Boom Bust.csv" in project root
```

### Add Manual Name Override
```bash
# Edit backend/data/player_name_overrides.json
{
  "ESPN Name": "Stokastic Name",
  "Patrick Mahomes II": "Patrick Mahomes"
}
```

### Test with Live Game
```bash
# Run during Sunday/Monday night games
python demo_espn_live.py

# Check ESPN API directly
python -c "from services.espn_api import ESPNStatsAPI; api = ESPNStatsAPI(); print(api.get_live_games())"
```

---

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check ESPN API Response
```python
from services.espn_api import ESPNStatsAPI

api = ESPNStatsAPI()
scoreboard = api.get_scoreboard()

# Pretty print
import json
print(json.dumps(scoreboard, indent=2))
```

### Check Player Name Matching
```python
from utils.player_mapper import PlayerNameMapper
from utils.csv_parser import parse_stokastic_csv

df = parse_stokastic_csv("NFL DK Boom Bust.csv", slate_filter="Main")
mapper = PlayerNameMapper()

# Test a name
matched = mapper.match_player('Patrick Mahomes II', df['Name'].tolist())
print(f"Matched: {matched}")

# Get match report
report = mapper.get_match_report(
    {'Patrick Mahomes II': {'team': 'KC'}},
    df['Name'].tolist()
)
print(f"Match rate: {report['match_rate']:.1f}%")
```

---

## Code Style

### Follow Existing Patterns
- Type hints on all functions
- Docstrings (Google style)
- NumPy operations (not loops) for hot paths
- Descriptive variable names

### Example Function
```python
def calculate_something(
    data: np.ndarray,
    threshold: float = 0.5
) -> Tuple[np.ndarray, float]:
    """
    Calculate something from data.

    Args:
        data: Input array, shape (n,)
        threshold: Cutoff value (default: 0.5)

    Returns:
        Tuple of:
        - result: Calculated values, shape (n,)
        - mean: Average of results

    Example:
        >>> data = np.array([1, 2, 3])
        >>> result, mean = calculate_something(data, threshold=1.5)
    """
    # Vectorized operation
    result = np.where(data > threshold, data * 2, data / 2)
    mean = np.mean(result)

    return result, mean
```

---

## Git Workflow

### Branch Strategy
```bash
# Feature branches
git checkout -b feature/my-feature

# Bug fixes
git checkout -b fix/bug-description

# Merge to master when complete
git checkout master
git merge feature/my-feature
```

### Commit Messages
```
Short description (50 chars max)

Longer explanation if needed:
- What changed
- Why it changed
- Any side effects

Fixes #123
```

---

## Dependencies

### Core (Required)
```
numpy>=1.24.0       # Vectorized operations
pandas>=2.0.0       # Data manipulation
```

### API (Phase 4)
```
fastapi>=0.104.0    # REST API
uvicorn>=0.24.0     # ASGI server
pydantic>=2.0.0     # Data validation
```

### Testing
```
pytest>=7.4.0       # Test framework
pytest-asyncio      # Async tests
```

### Adding Dependencies
```bash
# Add to requirements.txt
echo "new-package>=1.0.0" >> requirements.txt

# Install
pip install -r requirements.txt

# Commit requirements.txt
git add requirements.txt
git commit -m "Add new-package dependency"
```

---

## Troubleshooting

### Import Errors
```python
# Add to sys.path if needed
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### ESPN API Timeout
- Check internet connection
- Increase timeout in ESPNStatsAPI
- Check if ESPN API is down

### Name Matching Failures
- Check player_name_overrides.json
- Add manual override
- Check for typos in Stokastic CSV

### Slow Simulations
- Reduce iterations (try 5000)
- Check NumPy is using BLAS (python -c "import numpy; numpy.show_config()")
- Profile with SnakeViz

---

## Resources

- [NumPy Documentation](https://numpy.org/doc/stable/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)
- [ESPN API (Unofficial)](https://github.com/nntrn/espn-api-docs)
