"""
Live stats service - orchestration layer.

Single entry point for fetching live NFL stats and updating projections.

Flow:
1. Fetch live games from ESPN API
2. Extract player stats and fantasy points
3. Map ESPN names → Stokastic names
4. Build live_stats dict for pro-rating
5. Call update_projections_for_live_games()
6. Return updated projections

This is THE service to use for live simulation updates.
"""

import logging
from typing import Dict, Tuple, Optional, List
import numpy as np
import pandas as pd

from services.espn_api import ESPNStatsAPI, LiveGame
from services.prorate import update_projections_for_live_games
from utils.player_mapper import PlayerNameMapper


logger = logging.getLogger(__name__)


class LiveStatsService:
    """
    High-level service for live stats integration.

    Usage:
        service = LiveStatsService()
        prorated_proj, adjusted_std = service.get_live_projections(stokastic_df)
    """

    def __init__(
        self,
        espn_api: Optional[ESPNStatsAPI] = None,
        player_mapper: Optional[PlayerNameMapper] = None
    ):
        """
        Initialize live stats service.

        Args:
            espn_api: Optional ESPN API client (creates default if None)
            player_mapper: Optional player name mapper (creates default if None)
        """
        self.espn_api = espn_api or ESPNStatsAPI()
        self.player_mapper = player_mapper or PlayerNameMapper()

        # Track statistics for debugging
        self.last_update_stats = {
            'live_games': 0,
            'players_with_stats': 0,
            'players_matched': 0,
            'players_unmatched': 0,
            'match_rate': 0.0
        }

    def get_live_games_info(self) -> List[LiveGame]:
        """
        Get list of currently live games.

        Returns:
            List of LiveGame objects
        """
        return self.espn_api.get_live_games()

    def get_live_projections(
        self,
        stokastic_df: pd.DataFrame,
        adjust_variance: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get pro-rated projections based on live game data.

        This is the main entry point for live simulation updates.

        Args:
            stokastic_df: DataFrame with ['Name', 'Projection', 'Std Dev']
            adjust_variance: Whether to adjust std_dev for time remaining

        Returns:
            Tuple of (prorated_projections, adjusted_std_devs)
            Both are numpy arrays matching the length of stokastic_df

        Workflow:
            1. Fetch all live games from ESPN
            2. Extract player stats (actual fantasy points)
            3. Map ESPN player names to Stokastic names
            4. Build live_stats dict
            5. Call update_projections_for_live_games()
            6. Return updated arrays

        If no games are live:
            Returns original projections unchanged
        """
        # Get all live stats from ESPN
        espn_stats = self.espn_api.get_all_live_stats()

        if not espn_stats:
            logger.info("No live games - using original projections")
            # No live games - return originals
            return stokastic_df['Projection'].values, stokastic_df['Std Dev'].values

        logger.info(f"Found {len(espn_stats)} players with live stats across live games")

        # Get list of Stokastic player names
        stokastic_names = stokastic_df['Name'].tolist()

        # Build player info for matching
        espn_players = {
            name: {'team': stats['team']}
            for name, stats in espn_stats.items()
        }

        # Match ESPN names to Stokastic names
        name_matches = self.player_mapper.batch_match(espn_players, stokastic_names)

        # Build live_stats dict in the format expected by prorate service
        # Key = Stokastic name, Value = {actual_points, pct_remaining, is_finished}
        live_stats = {}

        matched_count = 0
        unmatched_count = 0

        for espn_name, stok_name in name_matches.items():
            if stok_name is None:
                # Could not match this player
                unmatched_count += 1
                logger.debug(f"Could not match ESPN player: {espn_name}")
                continue

            # Successfully matched
            matched_count += 1
            espn_data = espn_stats[espn_name]

            live_stats[stok_name] = {
                'actual_points': espn_data['actual_points'],
                'pct_remaining': espn_data['pct_remaining'],
                'is_finished': espn_data['is_finished']
            }

        # Update tracking stats
        self.last_update_stats = {
            'live_games': len(self.espn_api.get_live_games()),
            'players_with_stats': len(espn_stats),
            'players_matched': matched_count,
            'players_unmatched': unmatched_count,
            'match_rate': (matched_count / len(espn_stats) * 100) if espn_stats else 0.0
        }

        logger.info(
            f"Matched {matched_count}/{len(espn_stats)} players "
            f"({self.last_update_stats['match_rate']:.1f}%)"
        )

        if unmatched_count > 0:
            logger.warning(f"{unmatched_count} players could not be matched")

        # Pro-rate projections using our existing service
        prorated_proj, adjusted_std = update_projections_for_live_games(
            stokastic_df,
            live_stats,
            adjust_variance=adjust_variance
        )

        return prorated_proj, adjusted_std

    def get_update_summary(self) -> Dict:
        """
        Get summary of last update for debugging/display.

        Returns:
            Dict with stats about last update:
            - live_games: Number of live games
            - players_with_stats: Total ESPN players found
            - players_matched: Successfully matched to Stokastic
            - players_unmatched: Failed to match
            - match_rate: Percentage matched
        """
        return self.last_update_stats.copy()

    def get_unmatched_players(
        self,
        stokastic_df: pd.DataFrame
    ) -> List[str]:
        """
        Get list of ESPN players that could not be matched.

        Useful for debugging name matching issues.

        Args:
            stokastic_df: Stokastic projections DataFrame

        Returns:
            List of ESPN player names that failed to match
        """
        espn_stats = self.espn_api.get_all_live_stats()
        if not espn_stats:
            return []

        stokastic_names = stokastic_df['Name'].tolist()
        espn_players = {
            name: {'team': stats['team']}
            for name, stats in espn_stats.items()
        }

        name_matches = self.player_mapper.batch_match(espn_players, stokastic_names)

        unmatched = [espn_name for espn_name, stok_name in name_matches.items() if stok_name is None]

        return unmatched


# Convenience function for quick usage
def get_live_projections_quick(
    stokastic_df: pd.DataFrame
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Quick one-liner to get live projections.

    Args:
        stokastic_df: Stokastic projections DataFrame

    Returns:
        Tuple of (prorated_projections, adjusted_std_devs)
    """
    service = LiveStatsService()
    return service.get_live_projections(stokastic_df)
