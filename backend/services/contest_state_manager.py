"""
Contest State Manager

Manages the state of contests being monitored for live updates.
Tracks contest metadata, simulation results, and update history.

Phase 3: Automation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from threading import Lock


@dataclass
class ContestState:
    """
    State for a single monitored contest.

    Attributes:
        contest_id: Unique identifier for the contest
        stokastic_df: DataFrame with player projections
        lineup_matrix: Binary matrix of lineups (num_lineups × num_players)
        entry_ids: List of entry IDs from DraftKings
        usernames: List of usernames for each entry
        slate_type: 'Main' or 'Showdown'
        entry_fee: Contest entry fee
        iterations: Number of simulation iterations
        created_at: When monitoring started
        last_update: When last updated
        update_count: Number of updates performed
        pre_game_scores: Initial simulation scores
        live_scores: Current live simulation scores (updated on each refresh)
        is_active: Whether contest is still being monitored
    """
    contest_id: str
    stokastic_df: pd.DataFrame
    lineup_matrix: np.ndarray
    entry_ids: List[str]
    usernames: List[str]
    slate_type: str
    entry_fee: float
    iterations: int
    created_at: datetime = field(default_factory=datetime.now)
    last_update: Optional[datetime] = None
    update_count: int = 0
    pre_game_scores: Optional[np.ndarray] = None
    live_scores: Optional[np.ndarray] = None
    is_active: bool = True


class ContestStateManager:
    """
    Manages state for all monitored contests.
    Thread-safe singleton for managing contest tracking.
    """

    def __init__(self):
        """Initialize the contest state manager."""
        self._contests: Dict[str, ContestState] = {}
        self._lock = Lock()

    def add_contest(
        self,
        contest_id: str,
        stokastic_df: pd.DataFrame,
        lineup_matrix: np.ndarray,
        entry_ids: List[str],
        usernames: List[str],
        slate_type: str,
        entry_fee: float = 10.0,
        iterations: int = 10000
    ) -> None:
        """
        Add a new contest to monitor.

        Args:
            contest_id: Unique identifier
            stokastic_df: Player projections DataFrame
            lineup_matrix: Binary lineup matrix
            entry_ids: List of DK entry IDs
            usernames: List of usernames
            slate_type: 'Main' or 'Showdown'
            entry_fee: Contest entry fee (default: 10.0)
            iterations: Simulation iterations (default: 10000)

        Raises:
            ValueError: If contest_id already exists
        """
        with self._lock:
            if contest_id in self._contests:
                raise ValueError(f"Contest {contest_id} already being monitored")

            state = ContestState(
                contest_id=contest_id,
                stokastic_df=stokastic_df.copy(),
                lineup_matrix=lineup_matrix.copy(),
                entry_ids=entry_ids.copy(),
                usernames=usernames.copy(),
                slate_type=slate_type,
                entry_fee=entry_fee,
                iterations=iterations
            )

            self._contests[contest_id] = state

    def get_contest(self, contest_id: str) -> Optional[ContestState]:
        """
        Get contest state by ID.

        Args:
            contest_id: Contest identifier

        Returns:
            ContestState if found, None otherwise
        """
        with self._lock:
            return self._contests.get(contest_id)

    def update_scores(
        self,
        contest_id: str,
        live_scores: np.ndarray,
        is_pre_game: bool = False
    ) -> None:
        """
        Update simulation scores for a contest.

        Args:
            contest_id: Contest identifier
            live_scores: New simulation scores array
            is_pre_game: If True, sets as pre_game_scores (default: False)

        Raises:
            KeyError: If contest_id not found
        """
        with self._lock:
            if contest_id not in self._contests:
                raise KeyError(f"Contest {contest_id} not found")

            state = self._contests[contest_id]

            if is_pre_game:
                state.pre_game_scores = live_scores.copy()
            else:
                state.live_scores = live_scores.copy()
                state.last_update = datetime.now()
                state.update_count += 1

    def deactivate_contest(self, contest_id: str) -> None:
        """
        Mark a contest as inactive (stop monitoring).

        Args:
            contest_id: Contest identifier

        Raises:
            KeyError: If contest_id not found
        """
        with self._lock:
            if contest_id not in self._contests:
                raise KeyError(f"Contest {contest_id} not found")

            self._contests[contest_id].is_active = False

    def remove_contest(self, contest_id: str) -> None:
        """
        Remove a contest from tracking entirely.

        Args:
            contest_id: Contest identifier

        Raises:
            KeyError: If contest_id not found
        """
        with self._lock:
            if contest_id not in self._contests:
                raise KeyError(f"Contest {contest_id} not found")

            del self._contests[contest_id]

    def get_active_contests(self) -> List[str]:
        """
        Get list of all active contest IDs.

        Returns:
            List of contest IDs that are still active
        """
        with self._lock:
            return [
                cid for cid, state in self._contests.items()
                if state.is_active
            ]

    def get_all_contests(self) -> List[str]:
        """
        Get list of all contest IDs (active and inactive).

        Returns:
            List of all contest IDs
        """
        with self._lock:
            return list(self._contests.keys())

    def get_contest_summary(self, contest_id: str) -> Dict:
        """
        Get summary information for a contest.

        Args:
            contest_id: Contest identifier

        Returns:
            Dictionary with contest summary

        Raises:
            KeyError: If contest_id not found
        """
        state = self.get_contest(contest_id)
        if state is None:
            raise KeyError(f"Contest {contest_id} not found")

        return {
            'contest_id': state.contest_id,
            'slate_type': state.slate_type,
            'num_lineups': state.lineup_matrix.shape[0],
            'num_players': state.lineup_matrix.shape[1],
            'entry_fee': state.entry_fee,
            'iterations': state.iterations,
            'created_at': state.created_at.isoformat(),
            'last_update': state.last_update.isoformat() if state.last_update else None,
            'update_count': state.update_count,
            'is_active': state.is_active,
            'has_pre_game': state.pre_game_scores is not None,
            'has_live': state.live_scores is not None
        }


# Singleton instance
_state_manager = None


def get_state_manager() -> ContestStateManager:
    """
    Get the singleton ContestStateManager instance.

    Returns:
        ContestStateManager singleton
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = ContestStateManager()
    return _state_manager
