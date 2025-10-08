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
import pickle
import os
from pathlib import Path


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
        pre_game_scores: Initial simulation scores (num_lineups × iterations)
        live_scores: Current live simulation scores (num_lineups × iterations)
        pre_game_player_sims: Player simulation matrix (num_players × iterations)
        live_player_sims: Live player simulation matrix (num_players × iterations)
        captain_indices: Captain player indices for showdown slates (num_lineups,)
        is_active: Whether contest is still being monitored
        payout_structure: List of payout ranges and amounts [(min_rank, max_rank, payout), ...]
        actual_player_points: Dict mapping player names to actual fantasy points scored so far
        espn_game_ids: List of ESPN game IDs for historical replay mode
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
    pre_game_player_sims: Optional[np.ndarray] = None
    live_player_sims: Optional[np.ndarray] = None
    captain_indices: Optional[np.ndarray] = None
    is_active: bool = True
    payout_structure: Optional[List[Tuple[int, int, float]]] = None
    actual_player_points: Dict[str, float] = field(default_factory=dict)
    espn_game_ids: List[str] = field(default_factory=list)

    # Performance optimization: Pre-computed cached statistics
    # These are computed once after simulation/update and reused across API requests
    cached_avg_scores: Optional[np.ndarray] = None  # (num_lineups,) - average score per lineup
    cached_ranks: Optional[np.ndarray] = None  # (num_lineups,) - rank with tie handling
    cached_win_rates: Optional[np.ndarray] = None  # (num_lineups,) - probability of winning
    cached_top_1pct_rates: Optional[np.ndarray] = None  # (num_lineups,) - probability of top 1%
    cached_top_10pct_rates: Optional[np.ndarray] = None  # (num_lineups,) - probability of top 10%

    def compute_and_cache_statistics(self):
        """
        Pre-compute and cache expensive statistics for fast API responses.

        This method should be called:
        - After initial simulation load
        - After each live update
        - Whenever scores change

        Performance: O(n log n) for n lineups, but only computed once.
        API requests then become O(1) lookups instead of O(n log n) re-computation.
        """
        # Determine which scores to use (live if available, otherwise pre-game)
        scores = self.live_scores if self.live_scores is not None else self.pre_game_scores

        if scores is None:
            return  # No scores to cache yet

        # 1. Cache average scores
        self.cached_avg_scores = scores.mean(axis=1)  # (num_lineups,)

        # 2. Cache ranks with tie handling
        # Sort indices by score (descending)
        sorted_indices = np.argsort(-self.cached_avg_scores)
        sorted_scores = self.cached_avg_scores[sorted_indices]

        # Calculate ranks with ties (1, 1, 1, 4, 5...)
        ranks = np.empty(len(sorted_indices), dtype=np.int32)
        current_rank = 1
        for i in range(len(sorted_indices)):
            if i > 0 and abs(sorted_scores[i] - sorted_scores[i-1]) < 0.01:
                # Same score (tie) - use same rank
                ranks[sorted_indices[i]] = current_rank
            else:
                # New score - update rank (skips if there were ties)
                current_rank = i + 1
                ranks[sorted_indices[i]] = current_rank

        self.cached_ranks = ranks

        # 3. Cache win rates
        # Win rate = % of simulations where this lineup has max score
        max_scores_per_iteration = scores.max(axis=0)  # (iterations,)
        self.cached_win_rates = (scores >= max_scores_per_iteration).mean(axis=1)

        # 4. Cache top percentile rates
        num_lineups = scores.shape[0]
        num_iterations = scores.shape[1]

        # Top 1% cutoff
        top_1pct_cutoff = max(1, int(num_lineups * 0.01))
        # Top 10% cutoff
        top_10pct_cutoff = max(1, int(num_lineups * 0.10))

        # Calculate ranks per iteration
        # For each iteration, count how many lineups beat this lineup
        self.cached_top_1pct_rates = np.zeros(num_lineups, dtype=np.float32)
        self.cached_top_10pct_rates = np.zeros(num_lineups, dtype=np.float32)

        for lineup_idx in range(num_lineups):
            lineup_scores = scores[lineup_idx, :]  # (iterations,)
            # Count how many lineups beat this one in each iteration
            ranks_per_iter = (scores > lineup_scores).sum(axis=0) + 1  # (iterations,)

            # Calculate percentile rates
            self.cached_top_1pct_rates[lineup_idx] = (ranks_per_iter <= top_1pct_cutoff).mean()
            self.cached_top_10pct_rates[lineup_idx] = (ranks_per_iter <= top_10pct_cutoff).mean()


class ContestStateManager:
    """
    Manages state for all monitored contests.
    Thread-safe singleton for managing contest tracking.
    Automatically persists state to disk.
    """

    def __init__(self, storage_dir: str = "data/contests"):
        """
        Initialize the contest state manager.

        Args:
            storage_dir: Directory to store contest state files
        """
        self._contests: Dict[str, ContestState] = {}
        self._lock = Lock()

        # Use absolute path to ensure consistency across processes
        # If relative path given, make it relative to the backend directory
        storage_path = Path(storage_dir)
        if not storage_path.is_absolute():
            # Get the backend directory (parent of services/)
            backend_dir = Path(__file__).parent.parent
            storage_path = backend_dir / storage_dir

        self._storage_dir = storage_path
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        # Load existing contests from disk
        self._load_all_from_disk()

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
            self._save_to_disk(contest_id)

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
        player_sims: Optional[np.ndarray] = None,
        is_pre_game: bool = False
    ) -> None:
        """
        Update simulation scores for a contest.

        Args:
            contest_id: Contest identifier
            live_scores: New simulation scores array (num_lineups × iterations)
            player_sims: Player simulation matrix (num_players × iterations), optional
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
                if player_sims is not None:
                    state.pre_game_player_sims = player_sims.copy()
            else:
                state.live_scores = live_scores.copy()
                if player_sims is not None:
                    state.live_player_sims = player_sims.copy()
                state.last_update = datetime.now()
                state.update_count += 1

            # Pre-compute and cache statistics for fast API responses
            state.compute_and_cache_statistics()

            # Persist after update
            self._save_to_disk(contest_id)

    def update_payout_structure(
        self,
        contest_id: str,
        payout_structure: List[Tuple[int, int, float]]
    ) -> None:
        """
        Update payout structure for a contest.

        Args:
            contest_id: Contest identifier
            payout_structure: List of (min_rank, max_rank, payout) tuples
                             Example: [(1, 1, 1000.0), (2, 5, 100.0), (6, 10, 50.0)]

        Raises:
            KeyError: If contest_id not found
        """
        with self._lock:
            if contest_id not in self._contests:
                raise KeyError(f"Contest {contest_id} not found")

            self._contests[contest_id].payout_structure = payout_structure
            self._save_to_disk(contest_id)

    def update_actual_points(
        self,
        contest_id: str,
        actual_points: Dict[str, float]
    ) -> None:
        """
        Update actual fantasy points for players.

        Args:
            contest_id: Contest identifier
            actual_points: Dict mapping player names to actual points scored

        Raises:
            KeyError: If contest_id not found
        """
        with self._lock:
            if contest_id not in self._contests:
                raise KeyError(f"Contest {contest_id} not found")

            state = self._contests[contest_id]
            # Backward compatibility: initialize if missing
            if not hasattr(state, 'actual_player_points'):
                state.actual_player_points = {}

            state.actual_player_points.update(actual_points)
            self._save_to_disk(contest_id)

    def update_espn_game_ids(
        self,
        contest_id: str,
        game_ids: List[str]
    ) -> None:
        """
        Update ESPN game IDs for historical replay mode.

        Args:
            contest_id: Contest identifier
            game_ids: List of ESPN game IDs

        Raises:
            KeyError: If contest_id not found
        """
        with self._lock:
            if contest_id not in self._contests:
                raise KeyError(f"Contest {contest_id} not found")

            self._contests[contest_id].espn_game_ids = game_ids
            self._save_to_disk(contest_id)

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
            self._save_to_disk(contest_id)

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

            # Delete from disk
            filepath = self._get_filepath(contest_id)
            if filepath.exists():
                filepath.unlink()

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

    def _get_filepath(self, contest_id: str) -> Path:
        """Get the filepath for a contest's state file."""
        # Sanitize contest_id for filename
        safe_id = contest_id.replace("/", "_").replace("\\", "_")
        return self._storage_dir / f"{safe_id}.pkl"

    def _save_to_disk(self, contest_id: str) -> None:
        """
        Save a contest's state to disk.

        Args:
            contest_id: Contest identifier

        Note: Does not acquire lock - should be called from within locked methods
        """
        try:
            state = self._contests[contest_id]
            filepath = self._get_filepath(contest_id)

            with open(filepath, 'wb') as f:
                pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)

        except Exception as e:
            # Log error but don't fail - persistence is best-effort
            print(f"Warning: Failed to save contest {contest_id} to disk: {e}")

    def _load_all_from_disk(self) -> None:
        """
        Load all contests from disk storage.

        Called during initialization to restore state from previous session.
        """
        try:
            for filepath in self._storage_dir.glob("*.pkl"):
                try:
                    with open(filepath, 'rb') as f:
                        state = pickle.load(f)

                    if isinstance(state, ContestState):
                        self._contests[state.contest_id] = state
                        print(f"Loaded contest {state.contest_id} from disk (active={state.is_active})")
                    else:
                        print(f"Warning: Invalid state file: {filepath}")

                except Exception as e:
                    print(f"Warning: Failed to load contest from {filepath}: {e}")

        except Exception as e:
            print(f"Warning: Failed to load contests from disk: {e}")


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
