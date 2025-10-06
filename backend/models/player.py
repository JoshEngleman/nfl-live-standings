"""
Player data models.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Player(BaseModel):
    """
    Represents a player with projections.
    """
    name: str
    position: str
    salary: int = Field(gt=0)
    projection: float = Field(ge=0.0)
    std_dev: float = Field(ge=0.0)
    slate: str
    ceiling: Optional[float] = None
    floor: Optional[float] = None
    boom_pct: Optional[float] = None
    bust_pct: Optional[float] = None
    own_pct: Optional[float] = None

    @property
    def is_finished(self) -> bool:
        """Check if this player's game is finished (std_dev ~= 0.1)."""
        return self.std_dev <= 0.2
