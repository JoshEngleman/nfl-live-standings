"""
Contest data models.
"""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
import numpy as np


class Lineup(BaseModel):
    """
    Represents a single DFS lineup entry.
    """
    entry_name: str
    players: List[str]
    is_captain: Optional[List[bool]] = None  # For showdown: which player is captain

    class Config:
        arbitrary_types_allowed = True


class Contest(BaseModel):
    """
    Represents a DFS contest with multiple entries.
    """
    slate_type: Literal["main", "showdown"]
    lineups: List[Lineup]
    num_lineups: int = Field(ge=1)
    players_per_lineup: int = Field(ge=1)

    def __init__(self, **data):
        super().__init__(**data)
        # Validate lineup counts
        if self.num_lineups != len(self.lineups):
            raise ValueError(f"num_lineups ({self.num_lineups}) != len(lineups) ({len(self.lineups)})")

        expected_players = 6 if self.slate_type == "showdown" else 9
        if self.players_per_lineup != expected_players:
            raise ValueError(f"For {self.slate_type} slate, expected {expected_players} players, got {self.players_per_lineup}")

    class Config:
        arbitrary_types_allowed = True


class SimulationResult(BaseModel):
    """
    Results from a Monte Carlo simulation.
    """
    num_iterations: int
    lineup_scores: np.ndarray  # Shape: (num_lineups, num_iterations)
    entry_names: List[str]

    class Config:
        arbitrary_types_allowed = True


class ContestAnalysis(BaseModel):
    """
    Analysis results for a contest.
    """
    entry_name: str
    win_rate: float = Field(ge=0.0, le=1.0)  # Probability of finishing 1st
    top_3_rate: float = Field(ge=0.0, le=1.0)
    top_10_rate: float = Field(ge=0.0, le=1.0)
    cash_rate: float = Field(ge=0.0, le=1.0)  # Probability of cashing
    expected_value: float  # EV in dollars
    roi: float  # Return on investment as percentage
    avg_finish: float = Field(gt=0)  # Average finish position

    class Config:
        arbitrary_types_allowed = True
