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

from services.contest_state_manager import get_state_manager
from services.live_updater_service import get_updater_service

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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
