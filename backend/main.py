"""
FastAPI application for NFL DFS simulation system.

This is a minimal stub for Phase 1. Will be expanded in Phase 2 with:
- File upload endpoints
- Simulation endpoints
- WebSocket for real-time updates
- Background scheduler for live stats
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="NFL DFS Live Simulation API",
    description="Real-time Monte Carlo simulation for DraftKings NFL contests",
    version="0.1.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "NFL DFS Live Simulation API",
        "version": "0.1.0",
        "phase": "Phase 1 - Core Engine Complete"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "csv_parser": "ok",
            "simulation_engine": "ok",
            "contest_analyzer": "ok"
        }
    }


# Placeholder endpoints for Phase 2
@app.post("/api/upload/stokastic")
async def upload_stokastic():
    """Upload Stokastic projections CSV. (Phase 2)"""
    return {"message": "Not implemented - Phase 2"}


@app.post("/api/upload/contest")
async def upload_contest():
    """Upload DraftKings contest CSV. (Phase 2)"""
    return {"message": "Not implemented - Phase 2"}


@app.post("/api/simulate")
async def run_simulation_endpoint():
    """Run Monte Carlo simulation. (Phase 2)"""
    return {"message": "Not implemented - Phase 2"}


@app.get("/api/results/{contest_id}")
async def get_results(contest_id: str):
    """Get simulation results. (Phase 2)"""
    return {"message": "Not implemented - Phase 2"}


# WebSocket endpoint for real-time updates (Phase 2)
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     # Real-time simulation updates


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
