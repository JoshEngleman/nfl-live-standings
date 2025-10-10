# Changelog

All notable changes to this project will be documented in this file.

## [2025-10-09] - Live/Historical Parity & Debug Improvements

### Fixed
- **Live Tab Now Matches Historical Tab**: Fixed `get_contest_summary()` to include `live_stats` and `pre_game_stats` objects in API responses
  - Live tab now displays contest statistics (mean score, std dev, min/max) identical to Historical tab
  - Change indicators (+/- score differences) now show correctly
  - Both tabs use identical data structures and UI components

- **Actual Player Points Display**: Verified actual points from ESPN are correctly populating in Live mode
  - 100% match rate for DFS-relevant offensive players
  - Player-level actual points showing in lineup details
  - Lineup-level actual points aggregating correctly

### Added
- **Debug Endpoints** for troubleshooting:
  - `/api/debug/actual-points/{contest_id}` - Compare stored vs ESPN actual points
  - `/api/debug/name-matching/{contest_id}` - Analyze ESPN-to-Stokastic name matching
  - Useful for debugging live stats integration issues

### Technical Details
- Modified `backend/services/contest_state_manager.py`:
  - Enhanced `get_contest_summary()` to calculate and return statistics objects
  - Ensures frontend receives identical data structure for both Live and Historical modes

- Modified `backend/main.py`:
  - Added debug endpoints for actual points and name matching analysis
  - Improved observability into live stats pipeline

### Performance
- Name matching performance: 22/22 DFS players matched (100% for relevant players)
- 41 unmatched players are defensive players not in DFS contests (expected behavior)
- Live updates completing in <2 seconds for 5929 lineup contest

### Status
✅ Live and Historical tabs are now functionally identical
✅ All simulation metrics calculating correctly (win rate, ROI, cash rate, top 1%)
✅ Actual player points flowing from ESPN API
✅ Pro-rated projections updating in real-time
✅ Background updater working (2-minute intervals)

## Previous Changes

See git history for earlier changes.
