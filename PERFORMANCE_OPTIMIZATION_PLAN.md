# Performance Optimization Plan for 100K+ Lineup Scaling

## Executive Summary

**Goal:** Scale platform to handle 100K+ lineup contests efficiently
**Current Bottlenecks:** Portfolio ROI calculation, rank recalculation, memory usage
**Target Performance:** <5 seconds for 100K lineups, <1 second for 10K lineups

---

## Current Performance Baseline

### Measured Performance
- **Simulation:** 500 players × 10K iterations = ~1-2s ✅ (already fast)
- **Standings endpoint:** 50 lineups = <1s ✅
- **Portfolio endpoint:** 52 lineups = ~20s ⚠️ (needs optimization)
- **Memory:** 500 players × 10K iterations × 8 bytes = 40MB per contest

### Projected Performance (Without Optimization)
- **100K lineups:** 100+ seconds (unusable)
- **Memory:** 100K × 10K × 8 bytes = 8GB per contest (server OOM)

### Key Bottlenecks Identified
1. **Portfolio ROI calculation:** Nested loops (lineups × iterations × rank calculations)
2. **Standings sorting/ranking:** Re-calculating ranks on every API request
3. **Player detail building:** Per-lineup loops constructing player data
4. **Memory usage:** float64 precision unnecessary, dense matrices wasteful
5. **Duplicate lineup handling:** O(n²) array comparisons

---

## Optimization Catalog

### 🔥 Tier 1: Critical (High Impact, Medium Effort)

#### 1. Pre-compute and Cache Derived Statistics
**Impact:** 🚀🚀🚀🚀🚀 (5/5) | **Ease:** 🟢🟢🟢🟢 (4/5) | **Gain:** 50-90% faster

**Problem:** Recalculating ranks, win rates, and percentiles on every API request.

**Solution:**
```python
class ContestState:
    def __init__(self, ...):
        # Add cached fields
        self.cached_ranks = None
        self.cached_win_rates = None
        self.cached_top_1pct_rates = None
        self.cached_avg_scores = None

    def compute_and_cache_statistics(self):
        """Call after simulation or live update."""
        # Cache average scores
        self.cached_avg_scores = self.scores.mean(axis=1)

        # Cache ranks with tie handling
        self.cached_ranks = self._calculate_ranks()

        # Cache win rates
        max_scores = self.scores.max(axis=0)
        self.cached_win_rates = (self.scores >= max_scores).mean(axis=1)

        # Cache top percentiles
        num_lineups = self.scores.shape[0]
        top_1pct_cutoff = max(1, int(num_lineups * 0.01))
        ranks_per_iter = (self.scores > self.scores[:, :, None]).sum(axis=0) + 1
        self.cached_top_1pct_rates = (ranks_per_iter <= top_1pct_cutoff).mean(axis=1)
```

**Impact on 100K lineups:**
- Before: Sort 100K items on every request (~100ms)
- After: Instant lookup from cache (~0.1ms)

---

#### 2. Lazy Player Details with Pagination
**Impact:** 🚀🚀🚀🚀 (4/5) | **Ease:** 🟢🟢🟢🟢🟢 (5/5) | **Gain:** 60-80% faster

**Problem:** Building detailed player data for all filtered lineups, then paginating.

**Current Flow:**
```python
# BAD: Build details for 10K filtered lineups
for lineup in filtered_lineups:  # 10K iterations
    build_player_details(lineup)

# Then paginate
return filtered_lineups[offset:offset+50]  # Only need 50!
```

**Optimized Flow:**
```python
# GOOD: Paginate first, then build details
page_indices = filtered_indices[offset:offset+50]  # 50 items

# Build details only for visible page
for idx in page_indices:  # Only 50 iterations!
    build_player_details(idx)
```

**Impact on 100K lineups:**
- Before: Build 100K lineup details (~5 seconds)
- After: Build 50 lineup details (~0.025 seconds)

---

#### 3. Vectorize Portfolio ROI Calculation
**Impact:** 🚀🚀🚀🚀🚀 (5/5) | **Ease:** 🟢🟢🟢 (3/5) | **Gain:** 5-10x faster

**Problem:** Inner loop calculating payouts per iteration.

**Current Bottleneck:**
```python
for iter_idx in range(1000):  # Slow loop
    rank = int(ranks[iter_idx])
    num_tied = int(ties_count[iter_idx])
    pooled_payout = sum(payout_array[rank:rank+num_tied])
    portfolio_payouts[iter_idx] += pooled_payout / num_tied
```

**Vectorized Solution:**
```python
# Fully vectorized - no iteration loop
from numba import jit

@jit(nopython=True)
def calculate_portfolio_payouts(ranks, ties_count, payout_array):
    """JIT-compiled payout calculation."""
    payouts = np.zeros(len(ranks))
    for i in range(len(ranks)):
        rank, num_tied = int(ranks[i]), int(ties_count[i])
        if rank + num_tied <= len(payout_array):
            payouts[i] = payout_array[rank:rank+num_tied].sum() / num_tied
    return payouts
```

**Alternative - Fancy Indexing:**
```python
# Build rank range indices
rank_ranges = np.arange(max_rank)[:, None] + np.arange(max_tied)[None, :]
payouts = payout_array[rank_ranges].sum(axis=1) / ties_count
```

---

### 🟡 Tier 2: Important (Medium Impact, Easy Wins)

#### 4. Use float32 Instead of float64
**Impact:** 🚀🚀🚀 (3/5) | **Ease:** 🟢🟢🟢🟢🟢 (5/5) | **Gain:** 50% memory, 10-20% speed

**Rationale:** Fantasy scores don't need float64 precision (0.01 FP is smallest unit).

**Implementation:**
```python
# In simulator.py
def generate_player_simulations(...):
    player_sims = np.random.normal(
        projections, std_devs, size=(len(projections), iterations)
    ).astype(np.float32)  # Add this

# In matrix multiplication
scores = lineup_matrix.astype(np.float32) @ player_sims
```

**Memory Savings:**
- Before: 100K × 10K × 8 bytes = 8GB
- After: 100K × 10K × 4 bytes = 4GB (50% reduction)

---

#### 5. Dynamic Iteration Count (Progressive Enhancement)
**Impact:** 🚀🚀🚀🚀 (4/5) | **Ease:** 🟢🟢🟢🟢 (4/5) | **Gain:** 2-10x faster initial load

**Strategy:**
- **Initial page load:** 1,000 iterations (fast preview, ~0.1s)
- **Background refinement:** Upgrade to 10,000 iterations
- **Portfolio analysis:** Adaptive sampling (already 1,000)

**Implementation:**
```python
class ContestState:
    def __init__(self, ..., quick_mode=False):
        self.iterations = 1000 if quick_mode else 10000
        self.is_refined = not quick_mode

    async def refine_simulation(self):
        """Background task to improve accuracy."""
        if self.is_refined:
            return

        # Re-simulate with 10K iterations
        self.scores = run_simulation(..., iterations=10000)
        self.is_refined = True
        self.compute_and_cache_statistics()
```

---

#### 6. Smart Deduplication with Hashing
**Impact:** 🚀🚀🚀 (3/5) | **Ease:** 🟢🟢🟢🟢 (4/5) | **Gain:** O(n) instead of O(n²)

**Problem:** Finding duplicate lineups requires comparing every lineup to every other.

**Current:** O(n²) array comparison
```python
for i in range(len(lineups)):
    for j in range(i+1, len(lineups)):
        if np.array_equal(lineup_matrix[i], lineup_matrix[j]):
            duplicates[i].append(j)
```

**Optimized:** O(n) hashing with O(1) lookup
```python
def hash_lineup(lineup_row):
    """Hash lineup player indices."""
    player_indices = np.where(lineup_row == 1)[0]
    return hash(tuple(sorted(player_indices)))

# Build hash map
lineup_groups = defaultdict(list)
for idx, lineup in enumerate(lineup_matrix):
    h = hash_lineup(lineup)
    lineup_groups[h].append(idx)

# Duplicates are lineups with same hash
duplicates = {h: indices for h, indices in lineup_groups.items() if len(indices) > 1}
```

---

### 🟢 Tier 3: Advanced (Lower Priority or Higher Complexity)

#### 7. Sparse Matrix for Lineup Storage
**Impact:** 🚀🚀 (2/5) | **Ease:** 🟢🟢🟢🟢 (4/5) | **Gain:** 90% memory reduction

**Rationale:** Lineup matrix is sparse (6 players out of 500 = 1.2% density).

**Memory Savings:**
- Dense: 100K × 500 × 1 byte = 50MB
- Sparse: 100K × 6 × 12 bytes = 7MB (85% reduction)

**Implementation:**
```python
from scipy.sparse import csr_matrix

# Convert to sparse
lineup_matrix_sparse = csr_matrix(lineup_matrix)

# Sparse matrix multiplication still works
scores = lineup_matrix_sparse @ player_sims
```

**Caveat:** Sparse @ dense is slower than dense @ dense, but memory savings huge.

---

#### 8. Parallel Processing with Multiprocessing
**Impact:** 🚀🚀🚀🚀 (4/5) | **Ease:** 🟢🟢 (2/5) | **Gain:** Near-linear with cores

**Use Case:** Simulation for massive contests (100K+ lineups).

**Implementation:**
```python
from multiprocessing import Pool
import numpy as np

def simulate_chunk(args):
    projections, std_devs, iterations, seed = args
    np.random.seed(seed)
    return np.random.normal(projections, std_devs, (len(projections), iterations))

def parallel_simulation(projections, std_devs, iterations, n_processes=4):
    chunks = np.array_split(np.arange(len(projections)), n_processes)

    with Pool(n_processes) as pool:
        results = pool.map(simulate_chunk, [
            (projections[chunk], std_devs[chunk], iterations, seed + i)
            for i, chunk in enumerate(chunks)
        ])

    return np.vstack(results)
```

---

#### 9. Database Backend for Massive Contests
**Impact:** 🚀🚀🚀🚀 (4/5) | **Ease:** 🟢 (1/5) | **Gain:** Unlimited scale

**Use Case:** 1M+ lineup contests, persistent storage.

**Implementation:**
```python
# SQLite with indexes
CREATE TABLE lineups (
    id INTEGER PRIMARY KEY,
    contest_id TEXT,
    entry_id TEXT,
    username TEXT,
    avg_score REAL,
    rank INTEGER,
    win_rate REAL,
    INDEX idx_contest_rank (contest_id, rank),
    INDEX idx_username (username)
);

# Fast pagination
SELECT * FROM lineups
WHERE contest_id = ? AND username LIKE ?
ORDER BY rank
LIMIT 50 OFFSET 1000;
```

**Advantages:**
- Efficient pagination for millions of lineups
- Fast filtering with indexes
- Persistent storage across server restarts

---

#### 10. GPU Acceleration with CuPy
**Impact:** 🚀🚀🚀🚀🚀 (5/5) | **Ease:** 🟢 (1/5) | **Gain:** 10-100x on GPU

**Implementation:**
```python
import cupy as cp

# GPU-accelerated simulation
def run_simulation_gpu(projections, std_devs, lineup_matrix, iterations):
    # Move to GPU
    proj_gpu = cp.array(projections)
    std_gpu = cp.array(std_devs)
    lineup_gpu = cp.array(lineup_matrix)

    # Simulate on GPU
    player_sims = cp.random.normal(proj_gpu[:, None], std_gpu[:, None],
                                   size=(len(proj_gpu), iterations))

    # Matrix multiply on GPU
    scores = lineup_gpu @ player_sims

    # Move back to CPU
    return cp.asnumpy(scores)
```

**Requirements:**
- NVIDIA GPU with CUDA
- CuPy library
- Deployment complexity

---

#### 11. Compression for Score Storage
**Impact:** 🚀🚀 (2/5) | **Ease:** 🟢🟢🟢🟢 (4/5) | **Gain:** 50-90% memory

**Use Case:** Storing multiple contest states in memory.

**Implementation:**
```python
import blosc  # Fast compression

class ContestState:
    def compress_scores(self):
        self.scores_compressed = blosc.compress_ptr(
            self.scores.__array_interface__['data'][0],
            self.scores.size,
            typesize=self.scores.itemsize
        )
        self.scores = None  # Free memory

    def decompress_scores(self):
        if self.scores is None:
            self.scores = blosc.decompress(self.scores_compressed)
```

---

#### 12. Incremental Ranking Updates
**Impact:** 🚀🚀🚀 (3/5) | **Ease:** 🟢🟢 (2/5) | **Gain:** O(log n) vs O(n log n)

**Use Case:** Live updates where only a few players change.

**Algorithm:**
```python
def update_rank_incremental(old_score, new_score, lineup_idx, ranks):
    """Update rank when one lineup's score changes."""
    if new_score > old_score:
        # Score increased - rank might improve
        better_lineups = (scores > new_score).sum()
        new_rank = better_lineups + 1
    else:
        # Score decreased - rank might worsen
        better_lineups = (scores >= new_score).sum()
        new_rank = better_lineups

    # Shift affected ranks
    if new_rank < ranks[lineup_idx]:
        # Improved - shift down ranks between new and old
        mask = (ranks >= new_rank) & (ranks < ranks[lineup_idx])
        ranks[mask] += 1

    ranks[lineup_idx] = new_rank
```

---

## Implementation Plan

### Phase 1: Quick Wins (Priority: HIGH)
**Timeline:** 1-2 days
**Expected Gain:** 5-10x faster for 100K lineups

**Tasks:**
1. ✅ Pre-compute and cache statistics (ranks, win rates, percentiles)
2. ✅ Lazy player details - paginate first, build details after
3. ✅ Use float32 instead of float64 throughout
4. ✅ Smart deduplication with hashing

**Success Metrics:**
- Standings endpoint: <2s for 100K lineups
- Portfolio endpoint: <10s for 100K lineups
- Memory usage: <4GB for 100K lineups

---

### Phase 2: Major Optimizations (Priority: MEDIUM)
**Timeline:** 3-5 days
**Expected Gain:** Additional 2-5x faster

**Tasks:**
1. ✅ Fully vectorize portfolio ROI calculation (remove all loops)
2. ✅ Dynamic iteration count with progressive enhancement
3. ✅ Sparse matrix for lineup storage
4. ✅ Add benchmarking suite to track improvements

**Success Metrics:**
- Standings endpoint: <1s for 100K lineups
- Portfolio endpoint: <5s for 100K lineups
- Initial page load: <1s (using 1K iterations)

---

### Phase 3: Scale to Millions (Priority: LOW)
**Timeline:** 1-2 weeks
**Expected Gain:** 100x+ faster, unlimited scale

**Tasks:**
1. ✅ Database backend for massive contests (SQLite/PostgreSQL)
2. ✅ Parallel processing with multiprocessing
3. ⚡ GPU acceleration (if NVIDIA GPU available)
4. ✅ Compression for multi-contest storage

**Success Metrics:**
- Support 1M+ lineup contests
- Sub-second API responses at any scale
- <100ms incremental updates during live games

---

## Performance Projections

### Estimated Performance After Each Phase

| Contest Size | Baseline | Phase 1   | Phase 2   | Phase 3   |
|--------------|----------|-----------|-----------|-----------|
| 1K lineups   | 1s       | 0.2s      | 0.1s      | <0.05s    |
| 10K lineups  | 10s      | 1s        | 0.5s      | 0.1s      |
| 100K lineups | 100s+    | 10-20s    | 2-5s      | 0.5-1s    |
| 1M lineups   | N/A      | N/A       | 30-60s    | 5-10s     |

### Memory Usage Projections

| Contest Size | Baseline | Phase 1   | Phase 2   | Phase 3   |
|--------------|----------|-----------|-----------|-----------|
| 10K lineups  | 800MB    | 400MB     | 200MB     | 100MB     |
| 100K lineups | 8GB      | 4GB       | 2GB       | 500MB     |
| 1M lineups   | 80GB     | 40GB      | 20GB      | 5GB       |

---

## Testing & Validation

### Benchmarking Suite
```python
# benchmark.py
import time
import numpy as np

def benchmark_contest(num_lineups, num_players=500, iterations=10000):
    # Generate test data
    lineups = generate_random_lineups(num_lineups, num_players)

    # Benchmark simulation
    start = time.time()
    scores = run_simulation(lineups, iterations)
    sim_time = time.time() - start

    # Benchmark standings
    start = time.time()
    get_contest_lineups(contest_id, limit=50)
    standings_time = time.time() - start

    # Benchmark portfolio
    start = time.time()
    get_portfolio(contest_id, username)
    portfolio_time = time.time() - start

    print(f"{num_lineups:,} lineups:")
    print(f"  Simulation: {sim_time:.2f}s")
    print(f"  Standings:  {standings_time:.2f}s")
    print(f"  Portfolio:  {portfolio_time:.2f}s")
    print(f"  Total:      {sim_time + standings_time + portfolio_time:.2f}s")

# Run benchmarks
for size in [1000, 10000, 100000]:
    benchmark_contest(size)
```

### Correctness Tests
```python
def test_optimization_correctness():
    """Ensure optimizations don't change results."""
    # Test with baseline
    baseline_ranks = calculate_ranks_baseline(scores)

    # Test with optimized
    optimized_ranks = calculate_ranks_optimized(scores)

    # Must be identical
    assert np.array_equal(baseline_ranks, optimized_ranks)
```

---

## Monitoring & Alerting

### Key Metrics to Track
- **API Response Time:** p50, p95, p99 for each endpoint
- **Memory Usage:** Peak and average per contest
- **Simulation Time:** Breakdown by contest size
- **Cache Hit Rate:** For pre-computed statistics

### Alerts
- ⚠️ Response time > 5s for any endpoint
- ⚠️ Memory usage > 80% of available
- ⚠️ Simulation taking > 3s for 10K lineups

---

## Risk Assessment

### Low Risk (Safe to implement)
- ✅ Pre-compute caching
- ✅ Lazy pagination
- ✅ float32 conversion
- ✅ Deduplication hashing

### Medium Risk (Test thoroughly)
- ⚠️ Vectorization changes (verify correctness)
- ⚠️ Dynamic iterations (ensure accuracy)
- ⚠️ Sparse matrices (performance tradeoffs)

### High Risk (Proceed with caution)
- 🔴 Database migration (data consistency)
- 🔴 GPU acceleration (deployment complexity)
- 🔴 Parallel processing (race conditions)

---

## Appendix: Alternative Approaches

### A. Client-Side Rendering
Move pagination/sorting to frontend for massive datasets.

### B. Server-Side Caching (Redis)
Cache API responses in Redis with TTL.

### C. CDN for Static Results
Pre-compute and serve final standings via CDN.

### D. WebAssembly
Compile simulation to WASM for browser-side execution.

---

**Last Updated:** October 2025
**Status:** Planning Phase
**Next Steps:** Implement Phase 1
