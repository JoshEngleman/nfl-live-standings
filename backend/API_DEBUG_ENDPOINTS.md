# Debug API Endpoints

Debug endpoints for troubleshooting live stats integration and contest state.

## `/api/debug/actual-points/{contest_id}`

**Purpose**: Compare actual player points stored in contest state vs what ESPN API is currently returning.

**Method**: `GET`

**Parameters**:
- `contest_id` (path): Contest identifier

**Response**:
```json
{
  "contest_id": "tmpzoi_poem",
  "actual_player_points_count": 22,
  "actual_player_points_sample": {
    "Jalen Hurts": 18.8,
    "Saquon Barkley": 7.8,
    "A.J. Brown": 12.3,
    ...
  },
  "espn_actual_points_count": 22,
  "espn_actual_points_sample": {
    "Jalen Hurts": 18.8,
    "Saquon Barkley": 7.8,
    ...
  },
  "has_mismatch": false
}
```

**Use Cases**:
- Verify actual points are being stored correctly
- Check if ESPN API is returning current data
- Debug discrepancies between stored and live actual points

---

## `/api/debug/name-matching/{contest_id}`

**Purpose**: Analyze ESPN-to-Stokastic player name matching for a contest.

**Method**: `GET`

**Parameters**:
- `contest_id` (path): Contest identifier

**Response**:
```json
{
  "contest_id": "tmpzoi_poem",
  "stokastic_player_count": 39,
  "stokastic_players_sample": [
    "Saquon Barkley",
    "Jalen Hurts",
    "A.J. Brown",
    ...
  ],
  "espn_player_count": 63,
  "espn_players": [
    "Jalen Hurts",
    "Saquon Barkley",
    "AJ Dillon",
    ...
  ],
  "matched_count": 22,
  "matched_players": {
    "Jalen Hurts": "Jalen Hurts",
    "Saquon Barkley": "Saquon Barkley",
    "AJ Dillon": "A.J. Dillon",
    ...
  },
  "unmatched_count": 41,
  "unmatched_players": [
    "Adoree' Jackson",
    "Jordan Davis",
    "Kelee Ringo",
    ...
  ],
  "match_rate": 34.9
}
```

**Use Cases**:
- Debug player name matching issues
- Identify which players are not matching
- Verify match rate is acceptable (should be >90% for DFS-relevant players)
- Note: Many unmatched players are defensive players not in DFS contests (expected)

**Expected Behavior**:
- **Offensive Players**: Should have ~100% match rate (all DFS-relevant players matched)
- **Defensive Players**: May not match if not in Stokastic CSV (expected)
- **Overall Match Rate**: May appear low (34%) due to defensive players, but DFS player match rate should be 100%

---

## Troubleshooting Guide

### Actual Points Not Showing

1. Check `/api/debug/actual-points/{contest_id}`:
   - If `actual_player_points_count` is 0: Live updater hasn't run yet
   - If `espn_actual_points_count` is 0: No live games currently
   - If counts don't match: Check name matching

2. Trigger manual update:
   ```bash
   curl -X POST http://localhost:8001/api/updater/trigger
   ```

3. Check logs for errors during live stats fetch

### Low Match Rate

1. Check `/api/debug/name-matching/{contest_id}`

2. Look at `unmatched_players` list:
   - If mostly defensive players: **This is expected and OK**
   - If offensive players unmatched: Add to `player_name_overrides.json`

3. Verify DFS-relevant player match rate:
   ```
   DFS Match Rate = matched_count / stokastic_player_count
   ```
   This should be close to 100%.

### Simulations Not Updating

1. Check updater status:
   ```bash
   curl http://localhost:8001/api/updater/status
   ```

2. Verify `is_running: true`

3. Check `next_run` timestamp

4. Review backend logs for errors during simulation

---

## Related Files

- `backend/main.py` - Debug endpoint implementations
- `backend/utils/player_mapper.py` - Name matching logic
- `backend/services/live_stats_service.py` - Live stats fetching
- `backend/data/player_name_overrides.json` - Manual name mappings
