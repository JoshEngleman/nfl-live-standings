"""
FastAPI application for NFL DFS simulation system.

Phase 3: Automation with WebSocket support and background updates.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import json
import logging
from datetime import datetime
import numpy as np

from services.contest_state_manager import get_state_manager
from services.live_updater_service import get_updater_service
from services.historical_replay_service import get_replay_service
from services.settings_manager import get_settings_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NFL DFS Live Simulation API",
    description="Real-time Monte Carlo simulation for DraftKings NFL contests",
    version="0.3.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

manager = ConnectionManager()

# Initialize services
state_manager = get_state_manager()
updater_service = get_updater_service(update_interval_seconds=120, auto_start=False)
settings_manager = get_settings_manager()

# Register callback to broadcast updates via WebSocket
def broadcast_update(contest_id: str, result: Dict):
    """Callback to broadcast contest updates via WebSocket."""
    import asyncio
    message = {
        'type': 'contest_update',
        'contest_id': contest_id,
        'timestamp': datetime.now().isoformat(),
        'data': result
    }
    # Create task to broadcast (handles async in sync context)
    asyncio.create_task(manager.broadcast(message))

updater_service.add_update_callback(broadcast_update)


# Pydantic models for requests
class ContestStartRequest(BaseModel):
    """Request model for starting contest monitoring."""
    contest_id: str
    slate_type: str = "Main"
    entry_fee: float = 10.0
    iterations: int = 10000
    # Note: In real implementation, would include CSV data or file references


class UpdaterControlRequest(BaseModel):
    """Request model for controlling the updater service."""
    action: str  # 'start' or 'stop'


class PayoutStructureRequest(BaseModel):
    """Request model for configuring payout structure."""
    payout_text: str
    entry_fee: Optional[float] = None


class ESPNGameIDsRequest(BaseModel):
    """Request model for saving ESPN game IDs."""
    game_ids: List[str]


class SettingsUpdateRequest(BaseModel):
    """Request model for updating simulation settings."""
    use_position_based: Optional[bool] = None
    iterations: Optional[int] = None
    use_lognormal: Optional[bool] = None


# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "NFL DFS Live Simulation API",
        "version": "0.3.0",
        "phase": "Phase 3 - Automation Complete"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    updater_status = updater_service.get_status()
    return {
        "status": "healthy",
        "components": {
            "csv_parser": "ok",
            "simulation_engine": "ok",
            "contest_analyzer": "ok",
            "live_stats_service": "ok",
            "background_updater": "running" if updater_status['is_running'] else "stopped"
        },
        "updater_status": updater_status
    }


@app.get("/api/contests")
async def list_contests():
    """Get list of all monitored contests."""
    all_contests = state_manager.get_all_contests()
    active_contests = state_manager.get_active_contests()

    return {
        "total": len(all_contests),
        "active": len(active_contests),
        "contests": [
            state_manager.get_contest_summary(cid)
            for cid in all_contests
        ]
    }


@app.get("/api/contests/{contest_id}")
async def get_contest_details(contest_id: str):
    """Get detailed information about a specific contest."""
    state = state_manager.get_contest(contest_id)

    if state is None:
        raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")

    summary = state_manager.get_contest_summary(contest_id)

    # Add score statistics if available
    if state.live_scores is not None:
        summary['live_stats'] = {
            'mean_score': float(state.live_scores.mean()),
            'std_score': float(state.live_scores.std()),
            'min_score': float(state.live_scores.min()),
            'max_score': float(state.live_scores.max())
        }

    if state.pre_game_scores is not None:
        summary['pre_game_stats'] = {
            'mean_score': float(state.pre_game_scores.mean()),
            'std_score': float(state.pre_game_scores.std()),
            'min_score': float(state.pre_game_scores.min()),
            'max_score': float(state.pre_game_scores.max())
        }

    return summary


@app.get("/api/contests/{contest_id}/lineups")
async def get_contest_lineups(
    contest_id: str,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "rank",  # rank, score, win_rate, username
    username: str = None  # Filter by username (case-insensitive partial match)
):
    """
    Get lineup-level details for a contest with leaderboard information.

    Args:
        contest_id: Contest identifier
        limit: Number of lineups to return (default: 50)
        offset: Pagination offset (default: 0)
        sort_by: Sort field - 'rank', 'score', 'win_rate', 'username' (default: 'rank')
        username: Optional username filter (case-insensitive partial match)

    Returns:
        Leaderboard data with:
        - Rank (1-indexed position)
        - Entry ID / Username / Duplicate count
        - Win rate, Top 1% rate
        - Current and projected scores
        - Individual player performance data
    """
    import numpy as np
    from collections import Counter

    state = state_manager.get_contest(contest_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")

    # Determine which scores and player sims to use
    scores = state.live_scores if state.live_scores is not None else state.pre_game_scores
    player_sims = state.live_player_sims if state.live_player_sims is not None else state.pre_game_player_sims

    if scores is None:
        raise HTTPException(status_code=400, detail="No simulation data available")

    # Calculate average scores for all lineups
    # scores shape: (lineups, iterations)
    avg_scores = scores.mean(axis=1)  # Average across iterations -> (num_lineups,)

    # Sort lineup indices by score (descending) to get ranks
    sorted_indices = np.argsort(-avg_scores)  # Negative for descending
    sorted_scores = avg_scores[sorted_indices]

    # Create rank mapping with tie handling
    # Ties get the same rank, next rank skips appropriately (1, 1, 1, 4, 5...)
    lineup_ranks = np.empty(len(sorted_indices), dtype=int)
    current_rank = 1
    for i in range(len(sorted_indices)):
        if i > 0 and abs(sorted_scores[i] - sorted_scores[i-1]) < 0.01:  # Same score (within 0.01 tolerance)
            lineup_ranks[sorted_indices[i]] = current_rank  # Same rank as previous
        else:
            current_rank = i + 1  # New rank (skips if there were ties)
            lineup_ranks[sorted_indices[i]] = current_rank

    # Count duplicates per username
    username_counts = Counter(state.usernames)

    # Apply sorting
    if sort_by == "rank" or sort_by == "score":
        # Already sorted by score/rank
        display_indices = sorted_indices
    elif sort_by == "win_rate":
        # Sort by win rate (calculate for all, then sort)
        # Win rate = % of simulations where lineup has the highest score
        max_scores_per_iteration = scores.max(axis=0)  # Max score for each iteration
        win_rates = (scores >= max_scores_per_iteration).mean(axis=1)  # Check each lineup against max
        display_indices = np.argsort(-win_rates)
    elif sort_by == "username":
        # Sort by username alphabetically
        username_order = np.argsort(state.usernames)
        display_indices = username_order
    else:
        display_indices = sorted_indices

    # Apply username filter if provided
    if username is not None and username.strip():
        username_lower = username.strip().lower()
        # Filter display_indices to only include lineups where username matches
        filtered_indices = []
        for idx in display_indices:
            if username_lower in state.usernames[idx].lower():
                filtered_indices.append(idx)
        display_indices = np.array(filtered_indices)

    # Apply pagination
    total_filtered = len(display_indices)
    start_idx = offset
    end_idx = min(offset + limit, total_filtered)
    page_indices = display_indices[start_idx:end_idx]

    lineups_data = []

    for i in page_indices:
        entry_id = state.entry_ids[i]
        username = state.usernames[i]
        rank = int(lineup_ranks[i])

        # Get player indices in this lineup
        player_indices = np.where(state.lineup_matrix[i] == 1)[0]

        # Build player data with individual scores
        players_data = []
        lineup_actual_points = 0.0
        for idx, player_idx in enumerate(player_indices):
            player_row = state.stokastic_df.iloc[player_idx]
            player_name = player_row['Name']
            player_position = player_row.get('Position', 'FLEX')
            player_projection = float(player_row['Projection'])
            player_team = player_row.get('Team', 'Unknown')

            # Get this player's simulated scores (mean across iterations)
            if player_sims is not None:
                player_sim_scores = player_sims[player_idx, :]  # (iterations,)
                player_current_score = float(player_sim_scores.mean())
            else:
                player_current_score = player_projection

            # Get actual fantasy points for this player (with backward compatibility)
            actual_player_points = getattr(state, 'actual_player_points', {})
            player_actual_points = actual_player_points.get(player_name, 0.0)

            # Check if this is the captain (for showdown - captain is always first player)
            is_captain = (idx == 0 and state.slate_type.lower() == 'showdown')

            # Apply captain multiplier to actual points if applicable
            if is_captain:
                lineup_actual_points += player_actual_points * 1.5
            else:
                lineup_actual_points += player_actual_points

            players_data.append({
                'name': player_name,
                'position': player_position,
                'projection': player_projection,
                'current_score': player_current_score,
                'actual_points': player_actual_points,
                'is_captain': is_captain,
                'team': player_team
            })

        # Calculate win rate for this lineup
        # Win rate = % of simulations where this lineup has the highest score
        # scores shape: (lineups, iterations)
        lineup_scores = scores[i, :]  # All iterations for lineup i -> (iterations,)
        # For each iteration, check if this lineup's score is the max
        max_scores_per_iteration = scores.max(axis=0)  # Max score across all lineups for each iteration
        win_rate = (lineup_scores >= max_scores_per_iteration).mean()

        # Calculate top 1% rate
        # Top 1% rate = % of simulations where this lineup finishes in top 1% of all lineups
        num_lineups = scores.shape[0]
        top_1pct_cutoff = max(1, int(num_lineups * 0.01))
        # For each iteration, count how many lineups scored higher than this lineup (lower is better rank)
        # rank = 1 means best lineup, so we count lineups that beat us + 1
        ranks_per_iteration = (scores > lineup_scores).sum(axis=0) + 1  # +1 because rank starts at 1
        top_1pct_rate = (ranks_per_iteration <= top_1pct_cutoff).mean()

        # Get pre-game and live scores
        pre_game_score = float(state.pre_game_scores[i, :].mean()) if state.pre_game_scores is not None else None
        live_score = float(state.live_scores[i, :].mean()) if state.live_scores is not None else None
        current_score = live_score if live_score is not None else pre_game_score

        # Calculate ROI metrics if payout structure is configured (with backward compatibility)
        roi_metrics = None
        payout_structure = getattr(state, 'payout_structure', None)
        if payout_structure is not None:
            from utils.payout_parser import calculate_roi_with_ties

            # Use tie-aware ROI calculation that properly splits payouts among duplicates
            roi_metrics = calculate_roi_with_ties(
                scores=scores,
                lineup_idx=i,
                lineup_matrix=state.lineup_matrix,
                payout_structure=payout_structure,
                entry_fee=state.entry_fee
            )

        lineups_data.append({
            'rank': rank,
            'entry_id': entry_id,
            'username': username,
            'duplicate_count': username_counts[username],
            'win_rate': float(win_rate),
            'top_1pct_rate': float(top_1pct_rate),
            'current_score': current_score,
            'projected_score': pre_game_score,
            'actual_points': round(lineup_actual_points, 2),
            'score_diff': (live_score - pre_game_score) if (live_score and pre_game_score) else 0.0,
            'roi_metrics': roi_metrics,
            'players': players_data
        })

    return {
        'contest_id': contest_id,
        'total_lineups': total_filtered,
        'offset': offset,
        'limit': limit,
        'sort_by': sort_by,
        'lineups': lineups_data
    }


@app.get("/api/contests/{contest_id}/optimal-lineup")
async def get_optimal_lineup(contest_id: str):
    """
    Calculate the optimal lineup based on current player simulations.

    For showdown slates: Selects 6 players (1 captain at 1.5x + 5 flex)
    For main slates: Selects 9 players by position constraints

    Returns the highest-scoring possible lineup with player details.
    """
    import numpy as np

    state = state_manager.get_contest(contest_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")

    # Get current player simulations
    player_sims = state.live_player_sims if state.live_player_sims is not None else state.pre_game_player_sims

    if player_sims is None:
        raise HTTPException(status_code=400, detail="No player simulation data available")

    # Calculate mean projected score for each player
    player_mean_scores = player_sims.mean(axis=1)  # (num_players,)

    if state.slate_type.lower() == 'showdown':
        # Showdown: Pick top 6 players, with the best as captain (1.5x)
        # Sort players by score descending
        sorted_player_indices = np.argsort(-player_mean_scores)
        top_6_indices = sorted_player_indices[:6]

        # Captain is the best player (index 0)
        captain_idx = top_6_indices[0]
        flex_indices = top_6_indices[1:]

        # Calculate optimal lineup score
        # Captain gets 1.5x multiplier
        optimal_score = player_mean_scores[captain_idx] * 1.5 + player_mean_scores[flex_indices].sum()

        # Build player list with captain first
        players_data = []

        # Add captain
        captain_row = state.stokastic_df.iloc[captain_idx]
        players_data.append({
            'name': captain_row['Name'],
            'position': captain_row.get('Position', 'FLEX'),
            'team': captain_row.get('Team', 'Unknown'),
            'projection': float(captain_row['Projection']),
            'current_score': float(player_mean_scores[captain_idx]),
            'multiplier': 1.5,
            'contribution': float(player_mean_scores[captain_idx] * 1.5),
            'is_captain': True
        })

        # Add flex players
        for idx in flex_indices:
            player_row = state.stokastic_df.iloc[idx]
            players_data.append({
                'name': player_row['Name'],
                'position': player_row.get('Position', 'FLEX'),
                'team': player_row.get('Team', 'Unknown'),
                'projection': float(player_row['Projection']),
                'current_score': float(player_mean_scores[idx]),
                'multiplier': 1.0,
                'contribution': float(player_mean_scores[idx]),
                'is_captain': False
            })

    else:
        # Main slate: Would need position constraints (QB, RB, WR, TE, FLEX, DST)
        # For now, just take top 9 players as a simple implementation
        sorted_player_indices = np.argsort(-player_mean_scores)
        top_9_indices = sorted_player_indices[:9]

        optimal_score = player_mean_scores[top_9_indices].sum()

        players_data = []
        for idx in top_9_indices:
            player_row = state.stokastic_df.iloc[idx]
            players_data.append({
                'name': player_row['Name'],
                'position': player_row.get('Position', 'FLEX'),
                'team': player_row.get('Team', 'Unknown'),
                'projection': float(player_row['Projection']),
                'current_score': float(player_mean_scores[idx]),
                'multiplier': 1.0,
                'contribution': float(player_mean_scores[idx]),
                'is_captain': False
            })

    return {
        'contest_id': contest_id,
        'slate_type': state.slate_type,
        'optimal_score': float(optimal_score),
        'num_players': len(players_data),
        'players': players_data
    }


@app.get("/api/contests/{contest_id}/players")
async def get_players_performance(contest_id: str, sort_by: str = "score"):
    """
    Get all players with their performance metrics.

    Args:
        contest_id: Contest identifier
        sort_by: Sort field - 'score', 'name', 'position' (default: 'score')

    Returns:
        List of all players with their current scores, projections, and usage in lineups
    """
    import numpy as np

    state = state_manager.get_contest(contest_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")

    # Get current player simulations
    player_sims = state.live_player_sims if state.live_player_sims is not None else state.pre_game_player_sims

    if player_sims is None:
        raise HTTPException(status_code=400, detail="No player simulation data available")

    # Calculate player stats
    player_mean_scores = player_sims.mean(axis=1)  # Mean score across iterations
    player_std_scores = player_sims.std(axis=1)  # Standard deviation

    # Calculate ownership (% of lineups that include each player)
    ownership = state.lineup_matrix.sum(axis=0) / state.lineup_matrix.shape[0] * 100  # % ownership

    # Build player data
    players_data = []
    for idx in range(len(state.stokastic_df)):
        player_row = state.stokastic_df.iloc[idx]

        players_data.append({
            'name': player_row['Name'],
            'position': player_row.get('Position', 'FLEX'),
            'team': player_row.get('Team', 'N/A'),
            'projection': float(player_row['Projection']),
            'current_score': float(player_mean_scores[idx]),
            'std_dev': float(player_std_scores[idx]),
            'ownership': float(ownership[idx]),
            'score_diff': float(player_mean_scores[idx] - player_row['Projection'])
        })

    # Apply sorting
    if sort_by == "score":
        players_data.sort(key=lambda x: x['current_score'], reverse=True)
    elif sort_by == "name":
        players_data.sort(key=lambda x: x['name'])
    elif sort_by == "position":
        players_data.sort(key=lambda x: (x['position'], -x['current_score']))
    elif sort_by == "ownership":
        players_data.sort(key=lambda x: x['ownership'], reverse=True)

    return {
        'contest_id': contest_id,
        'total_players': len(players_data),
        'sort_by': sort_by,
        'players': players_data
    }


@app.post("/api/contests/{contest_id}/deactivate")
async def deactivate_contest(contest_id: str):
    """Stop monitoring a contest."""
    try:
        state_manager.deactivate_contest(contest_id)
        return {
            "status": "success",
            "message": f"Contest {contest_id} deactivated"
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")


@app.delete("/api/contests/{contest_id}")
async def remove_contest(contest_id: str):
    """Remove a contest from tracking entirely."""
    try:
        state_manager.remove_contest(contest_id)
        return {
            "status": "success",
            "message": f"Contest {contest_id} removed"
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")


@app.post("/api/contests/{contest_id}/payout-structure")
async def update_payout_structure(contest_id: str, request: PayoutStructureRequest):
    """
    Configure payout structure for a contest.

    Accepts pasted payout text from DraftKings or other sites.

    Example formats:
        1st: $1,000.00
        2nd-5th: $100.00
        6-10: $50.00
    """
    from utils.payout_parser import parse_payout_structure

    try:
        # Parse the payout structure
        payout_structure = parse_payout_structure(request.payout_text)

        # Update contest state
        state_manager.update_payout_structure(contest_id, payout_structure)

        # Update entry fee if provided
        if request.entry_fee is not None:
            state = state_manager.get_contest(contest_id)
            if state:
                state.entry_fee = request.entry_fee
                state_manager._save_to_disk(contest_id)

        return {
            "status": "success",
            "message": "Payout structure updated",
            "payout_structure": [
                {
                    "min_rank": min_r,
                    "max_rank": max_r,
                    "payout": payout
                }
                for min_r, max_r, payout in payout_structure
            ],
            "entry_fee": request.entry_fee
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")


@app.post("/api/contests/{contest_id}/espn-game-ids")
async def update_espn_game_ids(contest_id: str, request: ESPNGameIDsRequest):
    """
    Save ESPN game IDs for historical replay mode.

    This allows the contest to remember which games to replay
    without having to re-enter them each time.
    """
    try:
        state_manager.update_espn_game_ids(contest_id, request.game_ids)

        return {
            "status": "success",
            "message": "ESPN game IDs saved",
            "game_ids": request.game_ids
        }

    except KeyError:
        raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")


@app.post("/api/updater/control")
async def control_updater(request: UpdaterControlRequest):
    """Start or stop the background updater service."""
    if request.action == "start":
        if updater_service.is_running:
            return {
                "status": "already_running",
                "message": "Updater service is already running"
            }
        updater_service.start()
        return {
            "status": "started",
            "message": "Updater service started",
            "updater_status": updater_service.get_status()
        }

    elif request.action == "stop":
        if not updater_service.is_running:
            return {
                "status": "not_running",
                "message": "Updater service is not running"
            }
        updater_service.stop()
        return {
            "status": "stopped",
            "message": "Updater service stopped"
        }

    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")


@app.get("/api/updater/status")
async def get_updater_status():
    """Get current status of the background updater."""
    return updater_service.get_status()


@app.post("/api/updater/trigger")
async def trigger_manual_update():
    """Manually trigger an update immediately (bypasses scheduler)."""
    results = updater_service.trigger_update_now()
    return {
        "status": "completed",
        "message": f"Updated {len(results)} contest(s)",
        "results": results
    }


# ============================================================================
# Settings Endpoints
# ============================================================================

@app.get("/api/settings")
async def get_settings():
    """Get current simulation settings."""
    settings = settings_manager.get_settings()
    return {
        "status": "success",
        "settings": settings.to_dict()
    }


@app.post("/api/settings")
async def update_settings(request: SettingsUpdateRequest):
    """
    Update simulation settings.

    Settings affect all future simulations:
    - use_position_based: Enable position-specific component-based modeling
    - iterations: Number of Monte Carlo iterations (100-50000)
    - use_lognormal: Use log-normal distribution (only when position_based=False)
    """
    # Build kwargs from non-None values
    kwargs = {}
    if request.use_position_based is not None:
        kwargs['use_position_based'] = request.use_position_based
    if request.iterations is not None:
        kwargs['iterations'] = request.iterations
    if request.use_lognormal is not None:
        kwargs['use_lognormal'] = request.use_lognormal

    settings = settings_manager.update_settings(**kwargs)
    logger.info(f"Settings updated: {settings.to_dict()}")

    return {
        "status": "success",
        "message": "Settings updated successfully",
        "settings": settings.to_dict()
    }


@app.post("/api/settings/reset")
async def reset_settings():
    """Reset settings to defaults."""
    settings = settings_manager.reset_to_defaults()
    logger.info("Settings reset to defaults")

    return {
        "status": "success",
        "message": "Settings reset to defaults",
        "settings": settings.to_dict()
    }


@app.get("/api/test-live-stats")
async def test_live_stats():
    """
    Test endpoint to verify ESPN API integration and live stats.

    Returns live game data, player stats, and matching information.
    """
    from services.espn_api import ESPNStatsAPI
    from services.live_stats_service import LiveStatsService
    from utils.csv_parser import parse_stokastic_csv
    from pathlib import Path
    import pandas as pd

    # Get ESPN live stats
    api = ESPNStatsAPI()
    live_games = api.get_live_games()
    all_stats = api.get_all_live_stats()

    # Try to load Stokastic file if available
    stokastic_path = Path(__file__).parent.parent / "NFL DK Boom Bust.csv"
    match_results = None
    projection_changes = []

    if stokastic_path.exists():
        try:
            df = parse_stokastic_csv(str(stokastic_path), slate_filter=None)
            service = LiveStatsService()
            prorated_proj, adjusted_std = service.get_live_projections(df)
            match_stats = service.get_update_summary()

            # Calculate biggest projection changes
            changes = []
            for i in range(len(df)):
                name = df['Name'].iloc[i]
                orig = float(df['Projection'].iloc[i])
                live = float(prorated_proj[i])
                diff = live - orig
                changes.append({
                    'name': name,
                    'original': round(orig, 1),
                    'live': round(live, 1),
                    'change': round(diff, 1)
                })

            # Sort by absolute change
            changes.sort(key=lambda x: abs(x['change']), reverse=True)
            projection_changes = changes[:10]

            match_results = match_stats
        except Exception as e:
            logger.error(f"Error testing live stats: {e}")

    # Top scorers
    top_scorers = []
    if all_stats:
        sorted_players = sorted(all_stats.items(),
                               key=lambda x: x[1]['actual_points'],
                               reverse=True)
        for name, stats in sorted_players[:10]:
            top_scorers.append({
                'name': name,
                'team': stats['team'],
                'points': round(stats['actual_points'], 1),
                'pct_remaining': round(stats['pct_remaining'] * 100, 1),
                'is_finished': stats['is_finished']
            })

    return {
        'espn_working': True,
        'live_games': len(live_games),
        'games': [
            {
                'away_team': g.away_team,
                'home_team': g.home_team,
                'away_score': g.away_score,
                'home_score': g.home_score,
                'quarter': g.period,
                'clock': g.clock
            }
            for g in live_games
        ],
        'total_players_with_stats': len(all_stats),
        'top_scorers': top_scorers,
        'matching': match_results,
        'projection_changes': projection_changes,
        'tested_at': datetime.now().isoformat()
    }


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time contest updates.

    Clients connect here to receive live updates as contests are refreshed.

    Message format:
    {
        'type': 'contest_update',
        'contest_id': 'contest_123',
        'timestamp': '2025-10-06T12:34:56',
        'data': { ... update results ... }
    }
    """
    await manager.connect(websocket)

    try:
        # Send initial status
        await websocket.send_json({
            'type': 'connection_established',
            'timestamp': datetime.now().isoformat(),
            'updater_status': updater_service.get_status(),
            'active_contests': state_manager.get_active_contests()
        })

        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()

            # Handle client commands (optional)
            try:
                message = json.loads(data)
                if message.get('command') == 'get_status':
                    await websocket.send_json({
                        'type': 'status_response',
                        'updater_status': updater_service.get_status(),
                        'active_contests': state_manager.get_active_contests()
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    'type': 'error',
                    'message': 'Invalid JSON'
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Contest loading endpoint
@app.post("/api/load-contest")
async def load_contest_from_files():
    """Load contest from CSV files in project directory."""
    from utils.csv_parser import (
        parse_stokastic_csv,
        parse_dk_contest_csv,
        create_lineup_matrix,
        create_player_index_map
    )
    from services.simulator import run_simulation
    from pathlib import Path

    # File paths
    stokastic_path = Path(__file__).parent.parent / "NFL DK Showdown Projections.csv"
    contest_path = Path(__file__).parent.parent / "contest-standings-182932585.csv"

    if not stokastic_path.exists():
        raise HTTPException(status_code=404, detail=f"Stokastic file not found: {stokastic_path.name}")
    if not contest_path.exists():
        raise HTTPException(status_code=404, detail=f"Contest file not found: {contest_path.name}")

    # Load data
    df = parse_stokastic_csv(str(stokastic_path), slate_filter=None)
    lineups, entry_ids, usernames, slate_type = parse_dk_contest_csv(str(contest_path))

    # Create lineup matrix
    player_index_map = create_player_index_map(df)
    lineup_matrix = create_lineup_matrix(lineups, player_index_map, len(df))

    # Run pre-game simulation
    iterations = 10000
    captain_indices = None
    if slate_type == 'showdown':
        import numpy as np
        try:
            from utils.csv_parser import extract_captain_indices
            captain_indices = extract_captain_indices(lineups, player_index_map)
        except ValueError as e:
            # Captain not found in projections - skip captain multiplier
            logger.warning(f"Showdown captain not found: {e}. Running without captain multiplier.")
            captain_indices = None

    # Generate player simulations (we need to keep these for individual player scores)
    from services.simulator import generate_player_simulations, calculate_lineup_scores, calculate_showdown_scores

    player_sims = generate_player_simulations(
        projections=df['Projection'].values,
        std_devs=df['Std Dev'].values,
        iterations=iterations,
        seed=None,
        use_lognormal=True  # Use log-normal for NFL volatility modeling
    )

    # Calculate lineup scores
    if captain_indices is not None:
        pre_game_scores = calculate_showdown_scores(lineup_matrix, player_sims, captain_indices)
    else:
        pre_game_scores = calculate_lineup_scores(lineup_matrix, player_sims)

    # Register with state manager
    contest_id = f"contest_{contest_path.stem}"

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=df,
        lineup_matrix=lineup_matrix,
        entry_ids=[str(e) for e in entry_ids],
        usernames=usernames,
        slate_type=slate_type,
        entry_fee=10.0,
        iterations=iterations
    )

    # Store captain indices in state
    if captain_indices is not None:
        import numpy as np
        state = state_manager.get_contest(contest_id)
        state.captain_indices = captain_indices.copy()

    # Store pre-game scores AND player simulations
    state_manager.update_scores(contest_id, pre_game_scores, player_sims=player_sims, is_pre_game=True)

    return {
        "status": "success",
        "message": "Contest loaded successfully",
        "contest_id": contest_id,
        "lineups": len(lineups),
        "players": len(df),
        "slate_type": slate_type
    }


# Placeholder endpoints for Phase 4 (full contest upload/management)
@app.post("/api/upload/stokastic")
async def upload_stokastic():
    """Upload Stokastic projections CSV. (Phase 4)"""
    return {"message": "Not implemented - Phase 4"}


@app.post("/api/upload/contest")
async def upload_contest():
    """Upload DraftKings contest CSV. (Phase 4)"""
    return {"message": "Not implemented - Phase 4"}


@app.post("/api/simulate")
async def run_simulation_endpoint():
    """Run Monte Carlo simulation. (Phase 4)"""
    return {"message": "Not implemented - Phase 4"}


@app.get("/api/results/{contest_id}")
async def get_results(contest_id: str):
    """Get simulation results. (Phase 4)"""
    return {"message": "Not implemented - Phase 4"}


# ============================================================================
# Historical Game Replay Endpoints (Testing)
# ============================================================================

class FetchGameRequest(BaseModel):
    """Request to fetch historical game data."""
    game_id: str
    season: int
    week: int


@app.post("/api/test/replay/fetch-game")
async def fetch_historical_game(request: FetchGameRequest):
    """
    Fetch and store historical game data from ESPN.

    Example:
        POST /api/test/replay/fetch-game
        {
            "game_id": "401547649",
            "season": 2024,
            "week": 5
        }
    """
    try:
        replay_service = get_replay_service()
        result = await replay_service.fetch_and_store_game(
            game_id=request.game_id,
            season=request.season,
            week=request.week
        )
        return result
    except Exception as e:
        logger.error(f"Error fetching historical game: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/replay/load/{game_id}")
async def load_game_for_replay(game_id: str):
    """
    Load a previously fetched game for replay testing.

    Args:
        game_id: ESPN game ID

    Returns:
        Status of the loaded game
    """
    try:
        replay_service = get_replay_service()
        success = replay_service.load_game(game_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

        # Save this game ID to all active contests for persistence
        active_contest_ids = state_manager.get_all_contests()
        for contest_id in active_contest_ids:
            state = state_manager.get_contest(contest_id)
            if state and state.is_active and game_id not in getattr(state, 'espn_game_ids', []):
                current_ids = getattr(state, 'espn_game_ids', [])
                state_manager.update_espn_game_ids(contest_id, current_ids + [game_id])

        status = replay_service.get_replay_status()
        return {
            'status': 'loaded',
            'message': f'Game {game_id} ready for replay (saved to active contests)',
            'replay_status': status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading game for replay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/replay/advance")
async def advance_replay_quarter():
    """
    Advance to the next quarter in the loaded replay and trigger simulation update.

    This endpoint:
    1. Advances to the next quarter
    2. Converts replay stats to live format
    3. Injects stats into the live stats service
    4. Triggers a simulation update for all active contests
    5. Broadcasts results via WebSocket

    Returns:
        Current quarter data, stats, and simulation results
    """
    try:
        replay_service = get_replay_service()

        # Advance to next quarter
        result = replay_service.advance_quarter()

        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])

        # Get the stats for this quarter
        quarter_stats = result.get('stats')
        quarter_num = result.get('quarter', 0)

        if not quarter_stats:
            logger.warning(f"No stats available for quarter {quarter_num}")
            return {**result, 'simulation_triggered': False, 'message': 'No stats to simulate'}

        # Convert replay stats to live format
        live_stats = replay_service.convert_stats_to_live_format(quarter_stats, quarter_num)
        logger.info(f"Converted {len(live_stats)} players for quarter {quarter_num}")

        # Log sample players (especially Mahomes for debugging)
        if 'Patrick Mahomes' in live_stats:
            mahomes_stats = live_stats['Patrick Mahomes']
            logger.info(f">>> MAHOMES INJECTED: actual_points={mahomes_stats['actual_points']}, pct_remaining={mahomes_stats['pct_remaining']}, is_finished={mahomes_stats['is_finished']}")

        # Log a few sample players
        sample_players = list(live_stats.keys())[:3]
        for player in sample_players:
            stats = live_stats[player]
            logger.info(f"  Injecting {player}: {stats['actual_points']} pts, {stats['pct_remaining']*100}% remaining")

        # Inject stats into live stats service
        updater_service.live_stats_service.set_replay_stats(live_stats)
        logger.info(f"Replay stats injected into live stats service (replay_mode={updater_service.live_stats_service.is_replay_mode()})")

        # Trigger simulation update
        logger.info("Triggering simulation update with replay stats")
        update_results = updater_service.trigger_update_now()

        # Return combined results
        return {
            **result,
            'simulation_triggered': True,
            'live_stats_count': len(live_stats),
            'update_results': update_results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error advancing replay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/replay/reset")
async def reset_replay():
    """Reset the replay to pre-game state and clear replay stats."""
    try:
        replay_service = get_replay_service()
        replay_service.reset_replay()

        # Clear replay stats from live stats service
        updater_service.live_stats_service.clear_replay_stats()
        logger.info("Replay stats cleared from live stats service")

        return {
            'status': 'reset',
            'message': 'Replay reset to pre-game state',
            'replay_status': replay_service.get_replay_status()
        }
    except Exception as e:
        logger.error(f"Error resetting replay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test/replay/status")
async def get_replay_status():
    """Get current replay status."""
    replay_service = get_replay_service()
    return replay_service.get_replay_status()


@app.get("/api/test/replay/debug-samples")
async def debug_replay_samples(
    player_name: str = "Patrick Mahomes",
    num_samples: int = 10,
    actual_points: Optional[float] = None,
    pct_remaining: Optional[float] = None
):
    """
    Debug endpoint: Show what samples the simulation generates for a specific player.

    Args:
        player_name: Player to debug (default: Patrick Mahomes)
        num_samples: Number of sample iterations to show (default: 10)
        actual_points: Override actual points (optional, for testing scenarios)
        pct_remaining: Override pct_remaining (optional, e.g., 0.5 for halftime)
    """
    # Get the contest
    contest_id = "contest_contest-standings-182932585"
    state = state_manager.get_contest(contest_id)
    if not state:
        raise HTTPException(status_code=404, detail="Contest not found")

    # Find the player
    player_idx = None
    for idx, name in enumerate(state.stokastic_df['Name']):
        if name == player_name:
            player_idx = idx
            break

    if player_idx is None:
        raise HTTPException(status_code=404, detail=f"Player '{player_name}' not found")

    # Get original player stats
    original_proj = float(state.stokastic_df['Projection'].iloc[player_idx])
    original_std = float(state.stokastic_df['Std Dev'].iloc[player_idx])

    # Use custom scenario if provided, otherwise use live/replay data
    if actual_points is not None and pct_remaining is not None:
        # Custom scenario
        prorated_mean = actual_points + (original_proj * pct_remaining)
        scaled_std = original_std * np.sqrt(pct_remaining)
        scenario_type = "custom"
        scenario_info = {
            'actual_points': actual_points,
            'pct_remaining': pct_remaining,
            'time_complete': round((1 - pct_remaining) * 100, 1)
        }
    else:
        # Use live/replay data
        prorated_proj, adjusted_std = updater_service.live_stats_service.get_live_projections(
            state.stokastic_df
        )
        prorated_mean = float(prorated_proj[player_idx])
        scaled_std = float(adjusted_std[player_idx])
        scenario_type = "live/replay"

        # Get replay stats if available
        scenario_info = None
        if updater_service.live_stats_service.is_replay_mode():
            replay_stats = updater_service.live_stats_service._replay_stats
            if player_name in replay_stats:
                scenario_info = replay_stats[player_name]

    # Generate sample iterations using log-normal distribution
    np.random.seed(42)  # For reproducibility

    # Convert (mean, std) to log-normal parameters
    safe_mean = max(prorated_mean, 0.5)
    cv = scaled_std / safe_mean
    sigma = np.sqrt(np.log(1 + cv**2))
    mu = np.log(safe_mean) - 0.5 * sigma**2

    samples = []
    for i in range(num_samples):
        sample = float(np.random.lognormal(mu, sigma))
        samples.append(round(sample, 2))

    # Calculate stats about the samples
    sample_mean = float(np.mean(samples))
    sample_std = float(np.std(samples))
    sample_min = float(np.min(samples))
    sample_max = float(np.max(samples))

    return {
        'player_name': player_name,
        'scenario_type': scenario_type,
        'original_projection': round(original_proj, 2),
        'original_std_dev': round(original_std, 2),
        'prorated_mean': round(prorated_mean, 2),
        'scaled_std_dev': round(scaled_std, 2),
        'scenario_info': scenario_info,
        'num_samples': num_samples,
        'samples': samples,
        'sample_stats': {
            'mean': round(sample_mean, 2),
            'std': round(sample_std, 2),
            'min': round(sample_min, 2),
            'max': round(sample_max, 2)
        },
        'explanation': {
            'formula': 'prorated_mean = actual_so_far + (original_projection × time_remaining)',
            'variance_scaling': 'No time scaling - keeps 100% of original variance for live games',
            'sampling': 'each iteration samples from LogNormal(μ, σ) for right-skewed NFL volatility'
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
