# Deployment Guide

## Overview

This guide covers deploying the NFL DFS Live Standings platform. Currently focused on local/development deployment. Production deployment guide coming with Phase 4 (Backend API).

---

## Local Deployment

### System Requirements
- **OS:** macOS, Linux, or Windows
- **Python:** 3.12 or higher
- **RAM:** 2GB minimum (4GB recommended for large contests)
- **Storage:** 500MB for project + dependencies
- **Network:** Internet connection for ESPN API

### Installation

```bash
# Clone repository
git clone <repo-url>
cd nfl-live-standings

# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

### Data Files

**Stokastic CSV** (Required)
```bash
# Download from Stokastic.com
# Place in project root as: NFL DK Boom Bust.csv
```

**DraftKings Contest CSV** (Optional - for specific contest analysis)
```bash
# Export from DraftKings contest page
# Place anywhere, reference in scripts
```

**Player Name Overrides** (Optional)
```bash
# Edit: backend/data/player_name_overrides.json
# Add manual name mappings as needed
```

---

## Running the Application

### Basic Simulation
```bash
cd backend
source venv/bin/activate

# Run simulation with random lineups
python run_simulation.py --iterations 10000 --num-lineups 50
```

### Live ESPN Integration
```bash
# Best during live NFL games (Sunday afternoons/evenings)
python demo_espn_live.py
```

### Contest Analysis
```bash
# Parse actual DraftKings contest
python demo_contest_parser.py
```

---

## Environment Variables

Currently none required. Future configuration:

```bash
# Create .env file (future)
ESPN_API_RATE_LIMIT=30
ESPN_API_CACHE_TTL=60
DEFAULT_ITERATIONS=10000
LOG_LEVEL=INFO
```

---

## Monitoring

### Logging

Enable logging in scripts:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Performance Metrics

Monitor key metrics:
- Simulation throughput (iterations/second)
- ESPN API response times
- Player name match rate
- Memory usage

---

## Production Deployment (Future - Phase 4)

### Architecture
```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (Reverse   │
                    │   Proxy)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │
                    │   Backend   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Redis     │
                    │  (Caching)  │
                    └─────────────┘
```

### Deployment Options

**Option 1: Docker**
```dockerfile
# Dockerfile (future)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Option 2: Heroku**
```bash
# Procfile (future)
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Option 3: AWS Lambda** (for background jobs)
```python
# Lambda handler for scheduled simulations
def lambda_handler(event, context):
    # Fetch data
    # Run simulation
    # Push results to S3/DynamoDB
    pass
```

---

## Scaling Considerations

### Current Limits
- **Players:** 500 (Stokastic CSV size)
- **Lineups:** 13,000+ (tested with real contest)
- **Iterations:** 100,000 (tested, 10K recommended)

### Bottlenecks
1. **Memory:** Player simulations array (500 × 100K = ~400MB)
2. **CPU:** Matrix multiplication (vectorized, uses all cores)
3. **Network:** ESPN API polling (rate limited)

### Optimization Strategies

**For More Iterations:**
```python
# Batch processing
for batch in range(0, total_iterations, batch_size):
    batch_scores = run_simulation(..., iterations=batch_size)
    # Aggregate results
```

**For More Lineups:**
```python
# Process in chunks
for lineup_chunk in chunk_lineups(all_lineups, chunk_size=1000):
    scores = run_simulation(..., lineup_matrix=chunk_matrix)
    # Store results
```

**For Faster Updates:**
```python
# Parallel ESPN API calls (respect rate limits)
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(api.get_player_stats, game_id) for game_id in game_ids]
    results = [f.result() for f in futures]
```

---

## Security

### API Keys (Future)
```bash
# Never commit secrets
echo ".env" >> .gitignore

# Use environment variables
export ESPN_API_KEY=your_key_here
```

### Rate Limiting
- ESPN API: 30 seconds between requests (self-imposed)
- FastAPI: Add rate limiting middleware (future)

### Data Privacy
- No user authentication in current version
- Contest data is public (exported from DK)
- No PII stored

---

## Backup & Recovery

### Data to Backup
```bash
# Stokastic CSV (daily during season)
cp "NFL DK Boom Bust.csv" backups/stokastic_$(date +%Y%m%d).csv

# Player overrides
cp backend/data/player_name_overrides.json backups/

# Contest results (if saving)
cp results/*.json backups/
```

### Disaster Recovery
1. Reinstall dependencies from `requirements.txt`
2. Restore data files from backup
3. Re-run simulations if needed

---

## Health Checks

### System Health
```bash
# Check Python version
python --version  # Should be 3.12+

# Check dependencies
pip list | grep numpy  # Should be 1.24+
pip list | grep pandas  # Should be 2.0+

# Run tests
pytest tests/ -v
```

### ESPN API Health
```bash
# Quick check
python -c "from services.espn_api import ESPNStatsAPI; api = ESPNStatsAPI(); print('Live games:', len(api.get_live_games()))"
```

### Performance Health
```bash
# Benchmark simulation
python -c "
from services.simulator import run_simulation
import numpy as np
import time

proj = np.random.uniform(10, 30, 500)
std = np.random.uniform(3, 8, 500)
matrix = np.random.randint(0, 2, (10, 500))

start = time.time()
scores = run_simulation(proj, std, matrix, 10000)
duration = time.time() - start
print(f'10K iterations: {duration:.2f}s')
print(f'Throughput: {10000/duration:.0f} iter/s')
print('Status: ' + ('OK' if duration < 2.0 else 'SLOW'))
"
```

---

## Maintenance

### Regular Tasks
- **Weekly:** Update Stokastic CSV during NFL season
- **Monthly:** Review player name overrides (add new players)
- **Quarterly:** Update dependencies (`pip install --upgrade -r requirements.txt`)

### Dependency Updates
```bash
# Check outdated packages
pip list --outdated

# Update specific package
pip install --upgrade numpy

# Test after updates
pytest tests/
```

---

## Troubleshooting

### Common Issues

**Import Error: No module named 'numpy'**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**ESPN API Timeout**
```bash
# Increase timeout
# Edit services/espn_api.py: request_timeout=20
```

**Memory Error During Simulation**
```bash
# Reduce iterations
python run_simulation.py --iterations 5000
```

**Slow Simulations**
```bash
# Check NumPy is using optimized BLAS
python -c "import numpy; numpy.show_config()"

# Install optimized NumPy
pip install numpy[full]
```

---

## Rollback Procedure

If an update causes issues:

```bash
# Revert to previous commit
git log --oneline  # Find good commit
git checkout <commit-hash>

# Reinstall dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

---

## Monitoring Dashboard (Future)

Metrics to track in production:

- **Simulation Performance**
  - Iterations per second
  - Average execution time
  - 95th percentile latency

- **ESPN API**
  - Request count
  - Success rate
  - Average response time
  - Cache hit rate

- **Name Matching**
  - Match success rate
  - Unmatched players list
  - Override usage

- **System**
  - Memory usage
  - CPU usage
  - Disk usage

---

## Cost Considerations

### Current (Free Tier)
- ESPN API: Free (undocumented)
- Compute: Local machine
- Storage: Negligible (<100MB)

### Future Production Costs
- **Heroku:** ~$25/month (Hobby dyno)
- **AWS Lambda:** ~$5/month (estimated)
- **Vercel:** Free (frontend)
- **Redis:** ~$15/month (caching)

**Total:** ~$50/month for production deployment

---

## Future Enhancements

### Phase 3: Automation
- Background scheduler (APScheduler)
- Automatic contest updates every 2-3 minutes
- WebSocket for real-time frontend

### Phase 4: Backend API
- FastAPI REST endpoints
- Pydantic models
- OpenAPI documentation
- Authentication (if needed)

### Phase 5: Frontend
- React dashboard
- Real-time standings table
- Responsive design
- WebSocket client
