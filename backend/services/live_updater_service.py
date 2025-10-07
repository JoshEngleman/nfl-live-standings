"""
Live Updater Service

Background service that automatically updates contest simulations
using live ESPN stats every 2-3 minutes during NFL games.

Phase 3: Automation
"""

import logging
from datetime import datetime
from typing import Optional, Callable, List, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import numpy as np

from services.contest_state_manager import get_state_manager, ContestState
from services.live_stats_service import LiveStatsService
from services.simulator import run_simulation
from services.contest_analyzer import analyze_lineup

logger = logging.getLogger(__name__)


class LiveUpdaterService:
    """
    Background service for automatic contest updates.

    Fetches live ESPN stats and re-runs simulations for all active contests
    at regular intervals (default: 2 minutes).
    """

    def __init__(
        self,
        update_interval_seconds: int = 120,
        auto_start: bool = False
    ):
        """
        Initialize the live updater service.

        Args:
            update_interval_seconds: Seconds between updates (default: 120 = 2 minutes)
            auto_start: Whether to start scheduler immediately (default: False)
        """
        self.update_interval = update_interval_seconds
        self.scheduler = BackgroundScheduler()
        self.state_manager = get_state_manager()
        self.live_stats_service = LiveStatsService()
        self.is_running = False
        self._update_callbacks: List[Callable] = []

        if auto_start:
            self.start()

    def start(self) -> None:
        """
        Start the background scheduler.

        Begins automatic updates at the configured interval.
        """
        if self.is_running:
            logger.warning("Live updater already running")
            return

        self.scheduler.add_job(
            func=self._update_all_contests,
            trigger=IntervalTrigger(seconds=self.update_interval),
            id='contest_updater',
            name='Update all active contests',
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(f"Live updater started (interval: {self.update_interval}s)")

    def stop(self) -> None:
        """
        Stop the background scheduler.

        Stops all automatic updates.
        """
        if not self.is_running:
            logger.warning("Live updater not running")
            return

        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("Live updater stopped")

    def add_update_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called after each update.

        Useful for WebSocket notifications or logging.

        Args:
            callback: Function to call after updates. Signature: callback(contest_id, results)
        """
        self._update_callbacks.append(callback)

    def trigger_update_now(self) -> Dict[str, Dict]:
        """
        Manually trigger an update immediately (bypasses scheduler).

        Returns:
            Dictionary mapping contest_id to update results
        """
        return self._update_all_contests()

    def _update_all_contests(self) -> Dict[str, Dict]:
        """
        Update all active contests with live stats.

        Internal method called by scheduler.

        Returns:
            Dictionary mapping contest_id to update results
        """
        active_contests = self.state_manager.get_active_contests()

        if not active_contests:
            logger.debug("No active contests to update")
            return {}

        logger.info(f"Updating {len(active_contests)} active contest(s)")

        results = {}
        for contest_id in active_contests:
            try:
                result = self._update_single_contest(contest_id)
                results[contest_id] = result

                # Call registered callbacks
                for callback in self._update_callbacks:
                    try:
                        callback(contest_id, result)
                    except Exception as e:
                        logger.error(f"Callback error for {contest_id}: {e}")

            except Exception as e:
                logger.error(f"Failed to update contest {contest_id}: {e}")
                results[contest_id] = {'error': str(e)}

        return results

    def _update_single_contest(self, contest_id: str) -> Dict:
        """
        Update a single contest with live stats.

        Args:
            contest_id: Contest to update

        Returns:
            Dictionary with update results

        Raises:
            KeyError: If contest not found
        """
        state = self.state_manager.get_contest(contest_id)
        if state is None:
            raise KeyError(f"Contest {contest_id} not found")

        update_start = datetime.now()

        # Get live-updated projections
        logger.debug(f"Fetching live stats for {contest_id}")
        prorated_proj, adjusted_std = self.live_stats_service.get_live_projections(
            state.stokastic_df
        )

        # Determine captain indices for showdown slates
        captain_indices = state.captain_indices if state.captain_indices is not None else None

        # Generate player simulations with live projections
        from services.simulator import generate_player_simulations, calculate_lineup_scores, calculate_showdown_scores
        from services.settings_manager import get_settings_manager

        # Get current simulation settings
        settings = get_settings_manager().get_settings()

        logger.debug(f"Generating player simulations for {contest_id} ({settings.iterations} iterations, position_based={settings.use_position_based})")

        # Extract positions if using position-based simulation
        positions = None
        if settings.use_position_based and 'Position' in state.stokastic_df.columns:
            positions = state.stokastic_df['Position'].tolist()

        player_sims = generate_player_simulations(
            projections=prorated_proj,
            std_devs=adjusted_std,
            iterations=settings.iterations,  # Use settings
            seed=None,
            use_lognormal=settings.use_lognormal,  # Use settings
            use_position_based=settings.use_position_based,  # Use settings
            positions=positions  # Pass positions if available
        )

        # Calculate lineup scores
        logger.debug(f"Calculating lineup scores for {contest_id}")
        if captain_indices is not None:
            live_scores = calculate_showdown_scores(state.lineup_matrix, player_sims, captain_indices)
        else:
            live_scores = calculate_lineup_scores(state.lineup_matrix, player_sims)

        # Store updated scores AND player simulations
        self.state_manager.update_scores(contest_id, live_scores, player_sims=player_sims, is_pre_game=False)

        # Update actual points for players
        actual_points = self.live_stats_service.get_actual_points(state.stokastic_df)
        if actual_points:
            self.state_manager.update_actual_points(contest_id, actual_points)

        update_duration = (datetime.now() - update_start).total_seconds()

        # Get match stats from live stats service
        match_stats = self.live_stats_service.get_update_summary()

        result = {
            'contest_id': contest_id,
            'update_time': update_start.isoformat(),
            'duration_seconds': round(update_duration, 2),
            'num_lineups': state.lineup_matrix.shape[0],
            'iterations': state.iterations,
            'live_games': match_stats.get('live_games', 0),
            'players_matched': match_stats.get('players_matched', 0),
            'players_unmatched': match_stats.get('players_unmatched', 0),
            'match_rate': match_stats.get('match_rate', 0.0)
        }

        logger.info(
            f"Updated {contest_id}: {result['num_lineups']} lineups, "
            f"{result['live_games']} live games, "
            f"{result['match_rate']:.1f}% match rate, "
            f"{update_duration:.1f}s"
        )

        return result

    def get_status(self) -> Dict:
        """
        Get current status of the updater service.

        Returns:
            Dictionary with service status
        """
        active_contests = self.state_manager.get_active_contests()

        return {
            'is_running': self.is_running,
            'update_interval_seconds': self.update_interval,
            'active_contests': len(active_contests),
            'contest_ids': active_contests,
            'next_run': self.scheduler.get_jobs()[0].next_run_time.isoformat()
                if self.is_running and self.scheduler.get_jobs() else None
        }


# Singleton instance
_updater_service = None


def get_updater_service(
    update_interval_seconds: int = 120,
    auto_start: bool = False
) -> LiveUpdaterService:
    """
    Get the singleton LiveUpdaterService instance.

    Args:
        update_interval_seconds: Seconds between updates (default: 120)
        auto_start: Whether to start immediately (default: False)

    Returns:
        LiveUpdaterService singleton
    """
    global _updater_service
    if _updater_service is None:
        _updater_service = LiveUpdaterService(
            update_interval_seconds=update_interval_seconds,
            auto_start=auto_start
        )
    return _updater_service
