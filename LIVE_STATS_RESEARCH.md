# Live NFL Stats API Research

## Summary

We need live player statistics during NFL games to pro-rate projections. This document summarizes available options.

## Recommended Solution: **ESPN API**

### Pros
✅ **Free** - No API key, no authentication required
✅ **Comprehensive** - ~500 NFL endpoints
✅ **Real-time** - Updates during live games
✅ **Complete data** - Player stats, game clock, scores, play-by-play
✅ **Tested & Working** - Proof-of-concept code validated
✅ **Simple integration** - Standard HTTP requests

### Cons
⚠️ **Undocumented** - Unofficial API, structure may change without notice
⚠️ **No SLA** - No guarantees on uptime or rate limits
⚠️ **No support** - Community-driven only

### Key Endpoints

```python
# Scoreboard - All games, scores, status
GET https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard

# Game Summary - Detailed stats, boxscore
GET https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={EVENT_ID}

# Play by Play
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{EVENT_ID}/competitions/{EVENT_ID}/plays
```

### What We Can Extract

**From Scoreboard:**
- Live/scheduled/completed games
- Current scores
- Game status (quarter, time remaining)
- Team info

**From Game Summary:**
- Individual player statistics
  - Passing: yards, TDs, INTs
  - Rushing: carries, yards, TDs
  - Receiving: receptions, yards, TDs
- DraftKings fantasy points (calculated)
- Game clock and period
- Real-time updates during games

### Proof of Concept

See `backend/services/live_stats_research.py` for working code that:
1. Fetches scoreboard
2. Identifies live games
3. Extracts player stats
4. Calculates DraftKings fantasy points

**Performance:** API responses in <500ms

## Alternative Options

### Option 2: Tank01 NFL API (RapidAPI)
- **Pricing**: Free tier (100 req/month), $9.99/mo (10K req)
- **Pros**: Specifically designed for live stats, documented
- **Cons**: Rate limits, requires API key
- **Recommendation**: Use as backup if ESPN rate limits us

### Option 3: MySportsFeeds
- **Pricing**: Free for non-commercial use
- **Pros**: Well-documented, official API
- **Cons**: Requires API key, commercial use needs paid plan
- **Recommendation**: Good for production if going commercial

### Option 4: SportsDataIO
- **Pricing**: Free trial, then paid
- **Pros**: Enterprise-grade, comprehensive
- **Cons**: Expensive for hobby project
- **Recommendation**: Not suitable for proof-of-concept

## Implementation Plan

### Phase 2A: Live Stats Integration
1. **Create ESPN API service** (`services/stats/espn.py`)
   - Wrapper for scoreboard and game summary endpoints
   - Error handling and retries
   - Rate limiting (don't hammer the API)

2. **Extract live player stats**
   - Parse boxscore data
   - Map player names to Stokastic CSV
   - Calculate current fantasy points

3. **Game clock tracking**
   - Extract quarter and time remaining
   - Calculate % game completed
   - Handle overtime

4. **Pro-rating service** (`services/prorate.py`)
   - Combine actual points + prorated projection
   - Handle finished games (use actual only)
   - Vectorized for performance

### Phase 2B: Automation
5. **Background scheduler**
   - Poll ESPN API every 2-3 minutes during live games
   - Update projections
   - Trigger re-simulation
   - Push to frontend via WebSocket

6. **Error handling**
   - API failures (use cached data)
   - Missing players (match by name fuzzy logic)
   - Rate limiting (back off)

## Player Name Matching Challenge

**Problem**: Stokastic CSV has "Patrick Mahomes", ESPN API might have "Patrick Mahomes II"

**Solution**:
1. Normalize names (remove Jr/Sr/II)
2. Fuzzy matching (Levenshtein distance)
3. Manual mapping file for edge cases
4. Match by position + team as tiebreaker

## Example Usage

```python
from services.stats.espn import ESPNLiveStats

api = ESPNLiveStats()

# Get live games
live_games = api.get_live_games()

# For each live game
for game in live_games:
    # Get current player stats
    fantasy_points = api.get_live_fantasy_points(game['event_id'])

    # Example output:
    # {'Patrick Mahomes': 18.5, 'Travis Kelce': 12.3, ...}

    # Use for pro-rating
    # actual = 18.5 (current)
    # original_projection = 20.7
    # time_remaining = 0.5 (50%)
    # prorated = actual + (original_projection * time_remaining)
    #          = 18.5 + (20.7 * 0.5) = 28.85
```

## Testing Strategy

### During Development
- Use completed games to test stats extraction
- Mock live game scenarios
- Test with Monday Night Football (weekly test)

### Production
- Monitor API response times
- Log any missing players
- Track rate limit issues
- Have fallback to cached data

## Rate Limiting Considerations

ESPN API has no documented rate limits, but best practices:
- **Poll every 2-3 minutes** (not every second)
- **Cache responses** for 60 seconds
- **Only poll during live games** (check scoreboard first)
- **Exponential backoff** on errors

With 14 games per Sunday slate, polling every 2 minutes:
- 14 games × 30 req/hour = 420 requests/hour
- Over 4 hours = ~1,680 requests per slate

This should be well within any reasonable rate limit.

## Next Steps

1. **Test during Monday Night Football** (October 6, 2025)
   - Verify stats update in real-time
   - Measure API response times
   - Check data quality

2. **Implement ESPN service wrapper**
   - Clean API interface
   - Error handling
   - Caching

3. **Build pro-rating logic**
   - Combine actual + projected
   - Handle edge cases

4. **Integrate with simulation engine**
   - Update projections automatically
   - Re-run simulations
   - Display live results

## Risk Mitigation

**Risk**: ESPN API changes or goes down
**Mitigation**:
- Have Tank01 API as backup (requires API key signup)
- Cache last-known-good projections
- Manual CSV upload as fallback

**Risk**: Player name mismatches
**Mitigation**:
- Build name normalization
- Manual mapping file
- Alert on unmatched players

**Risk**: Rate limiting
**Mitigation**:
- Respectful polling (2-3 min intervals)
- Monitor for 429 errors
- Backoff strategy

## Conclusion

**ESPN API is the best choice for Phase 2:**
- Free and accessible ✅
- Real-time data ✅
- Proof-of-concept validated ✅
- Easy integration ✅

We'll proceed with ESPN as primary source, with Tank01 as backup option if needed.
