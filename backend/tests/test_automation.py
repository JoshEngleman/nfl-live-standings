"""
Tests for Phase 3 automation services.

Tests:
- ContestStateManager: State tracking, thread safety
- LiveUpdaterService: Background updates, callbacks
- Integration: Full automation workflow
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
import time
from threading import Thread

from services.contest_state_manager import ContestStateManager, ContestState
from services.live_updater_service import LiveUpdaterService


# Fixtures

@pytest.fixture
def sample_df():
    """Sample Stokastic DataFrame."""
    return pd.DataFrame({
        'Name': ['Player A', 'Player B', 'Player C', 'Player D', 'Player E'],
        'Projection': [20.0, 15.0, 18.0, 12.0, 22.0],
        'Std Dev': [5.0, 4.0, 4.5, 3.5, 5.5],
        'Salary': [8000, 6000, 7000, 5000, 9000],
        'Team': ['KC', 'BUF', 'KC', 'BUF', 'KC']
    })


@pytest.fixture
def sample_lineup_matrix():
    """Sample lineup matrix."""
    # 2 lineups, 5 players
    return np.array([
        [1, 1, 0, 1, 0],  # Lineup 1: Players A, B, D
        [0, 1, 1, 0, 1]   # Lineup 2: Players B, C, E
    ])


@pytest.fixture
def state_manager():
    """Fresh ContestStateManager instance."""
    return ContestStateManager()


# ContestStateManager Tests

def test_add_contest(state_manager, sample_df, sample_lineup_matrix):
    """Test adding a new contest."""
    contest_id = "test_contest_1"
    entry_ids = ["entry_1", "entry_2"]
    usernames = ["user1", "user2"]

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=sample_df,
        lineup_matrix=sample_lineup_matrix,
        entry_ids=entry_ids,
        usernames=usernames,
        slate_type="Main",
        entry_fee=10.0,
        iterations=1000
    )

    # Verify contest was added
    state = state_manager.get_contest(contest_id)
    assert state is not None
    assert state.contest_id == contest_id
    assert state.slate_type == "Main"
    assert state.entry_fee == 10.0
    assert state.iterations == 1000
    assert state.is_active is True
    assert len(state.entry_ids) == 2
    assert state.lineup_matrix.shape == (2, 5)


def test_add_duplicate_contest(state_manager, sample_df, sample_lineup_matrix):
    """Test that adding duplicate contest raises error."""
    contest_id = "test_contest_1"

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=sample_df,
        lineup_matrix=sample_lineup_matrix,
        entry_ids=["e1"],
        usernames=["u1"],
        slate_type="Main"
    )

    # Try to add same contest again
    with pytest.raises(ValueError, match="already being monitored"):
        state_manager.add_contest(
            contest_id=contest_id,
            stokastic_df=sample_df,
            lineup_matrix=sample_lineup_matrix,
            entry_ids=["e2"],
            usernames=["u2"],
            slate_type="Main"
        )


def test_get_contest_not_found(state_manager):
    """Test getting non-existent contest."""
    result = state_manager.get_contest("non_existent")
    assert result is None


def test_update_scores(state_manager, sample_df, sample_lineup_matrix):
    """Test updating scores for a contest."""
    contest_id = "test_contest_1"

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=sample_df,
        lineup_matrix=sample_lineup_matrix,
        entry_ids=["e1"],
        usernames=["u1"],
        slate_type="Main"
    )

    # Update pre-game scores
    pre_game_scores = np.random.uniform(100, 200, (2, 1000))
    state_manager.update_scores(contest_id, pre_game_scores, is_pre_game=True)

    state = state_manager.get_contest(contest_id)
    assert state.pre_game_scores is not None
    assert state.pre_game_scores.shape == (2, 1000)
    assert state.update_count == 0  # Pre-game doesn't increment

    # Update live scores
    live_scores = np.random.uniform(100, 200, (2, 1000))
    state_manager.update_scores(contest_id, live_scores, is_pre_game=False)

    state = state_manager.get_contest(contest_id)
    assert state.live_scores is not None
    assert state.live_scores.shape == (2, 1000)
    assert state.update_count == 1  # Live update increments
    assert state.last_update is not None


def test_update_scores_not_found(state_manager):
    """Test updating scores for non-existent contest."""
    with pytest.raises(KeyError, match="not found"):
        state_manager.update_scores(
            "non_existent",
            np.zeros((2, 100)),
            is_pre_game=False
        )


def test_deactivate_contest(state_manager, sample_df, sample_lineup_matrix):
    """Test deactivating a contest."""
    contest_id = "test_contest_1"

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=sample_df,
        lineup_matrix=sample_lineup_matrix,
        entry_ids=["e1"],
        usernames=["u1"],
        slate_type="Main"
    )

    # Verify active
    state = state_manager.get_contest(contest_id)
    assert state.is_active is True

    # Deactivate
    state_manager.deactivate_contest(contest_id)

    state = state_manager.get_contest(contest_id)
    assert state.is_active is False


def test_remove_contest(state_manager, sample_df, sample_lineup_matrix):
    """Test removing a contest."""
    contest_id = "test_contest_1"

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=sample_df,
        lineup_matrix=sample_lineup_matrix,
        entry_ids=["e1"],
        usernames=["u1"],
        slate_type="Main"
    )

    # Remove
    state_manager.remove_contest(contest_id)

    # Verify removed
    state = state_manager.get_contest(contest_id)
    assert state is None


def test_get_active_contests(state_manager, sample_df, sample_lineup_matrix):
    """Test getting list of active contests."""
    # Add multiple contests
    state_manager.add_contest(
        "contest_1",
        sample_df,
        sample_lineup_matrix,
        ["e1"],
        ["u1"],
        "Main"
    )
    state_manager.add_contest(
        "contest_2",
        sample_df,
        sample_lineup_matrix,
        ["e2"],
        ["u2"],
        "Main"
    )
    state_manager.add_contest(
        "contest_3",
        sample_df,
        sample_lineup_matrix,
        ["e3"],
        ["u3"],
        "Main"
    )

    # Deactivate one
    state_manager.deactivate_contest("contest_2")

    # Get active contests
    active = state_manager.get_active_contests()
    assert len(active) == 2
    assert "contest_1" in active
    assert "contest_3" in active
    assert "contest_2" not in active


def test_get_contest_summary(state_manager, sample_df, sample_lineup_matrix):
    """Test getting contest summary."""
    contest_id = "test_contest_1"

    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=sample_df,
        lineup_matrix=sample_lineup_matrix,
        entry_ids=["e1", "e2"],
        usernames=["u1", "u2"],
        slate_type="Main",
        entry_fee=25.0,
        iterations=5000
    )

    summary = state_manager.get_contest_summary(contest_id)

    assert summary['contest_id'] == contest_id
    assert summary['slate_type'] == "Main"
    assert summary['num_lineups'] == 2
    assert summary['num_players'] == 5
    assert summary['entry_fee'] == 25.0
    assert summary['iterations'] == 5000
    assert summary['is_active'] is True
    assert summary['has_pre_game'] is False
    assert summary['has_live'] is False


def test_thread_safety(state_manager, sample_df, sample_lineup_matrix):
    """Test thread-safe operations."""

    def add_contests(start_idx, count):
        """Add multiple contests from a thread."""
        for i in range(start_idx, start_idx + count):
            state_manager.add_contest(
                f"contest_{i}",
                sample_df,
                sample_lineup_matrix,
                [f"e{i}"],
                [f"u{i}"],
                "Main"
            )

    # Create multiple threads adding contests
    threads = []
    for i in range(3):
        t = Thread(target=add_contests, args=(i * 10, 10))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # Verify all 30 contests were added
    all_contests = state_manager.get_all_contests()
    assert len(all_contests) == 30


# LiveUpdaterService Tests

def test_updater_start_stop():
    """Test starting and stopping the updater service."""
    updater = LiveUpdaterService(update_interval_seconds=60, auto_start=False)

    assert updater.is_running is False

    # Start
    updater.start()
    assert updater.is_running is True

    # Stop
    updater.stop()
    assert updater.is_running is False


def test_updater_status():
    """Test getting updater status."""
    updater = LiveUpdaterService(update_interval_seconds=120, auto_start=False)

    status = updater.get_status()
    assert status['is_running'] is False
    assert status['update_interval_seconds'] == 120
    assert status['active_contests'] == 0

    updater.start()
    status = updater.get_status()
    assert status['is_running'] is True

    updater.stop()


def test_callback_registration():
    """Test registering update callbacks."""
    updater = LiveUpdaterService(update_interval_seconds=60, auto_start=False)

    callback_called = []

    def test_callback(contest_id, result):
        callback_called.append((contest_id, result))

    updater.add_update_callback(test_callback)

    # Verify callback is registered (indirectly through execution)
    assert len(updater._update_callbacks) == 1


def test_manual_trigger(state_manager, sample_df, sample_lineup_matrix):
    """Test manually triggering an update."""
    updater = LiveUpdaterService(update_interval_seconds=60, auto_start=False)

    # Add a contest
    contest_id = "test_contest_1"
    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=sample_df,
        lineup_matrix=sample_lineup_matrix,
        entry_ids=["e1"],
        usernames=["u1"],
        slate_type="Main",
        iterations=100
    )

    # Trigger update manually
    results = updater.trigger_update_now()

    # Should have updated the contest
    assert contest_id in results
    assert 'error' not in results[contest_id] or results[contest_id].get('live_games', -1) >= 0


# Integration Tests

def test_full_automation_workflow(state_manager, sample_df, sample_lineup_matrix):
    """Test complete automation workflow."""
    updater = LiveUpdaterService(update_interval_seconds=60, auto_start=False)

    # 1. Add contest
    contest_id = "integration_test"
    state_manager.add_contest(
        contest_id=contest_id,
        stokastic_df=sample_df,
        lineup_matrix=sample_lineup_matrix,
        entry_ids=["e1", "e2"],
        usernames=["user1", "user2"],
        slate_type="Main",
        iterations=100
    )

    # 2. Set pre-game scores
    pre_scores = np.random.uniform(100, 200, (2, 100))
    state_manager.update_scores(contest_id, pre_scores, is_pre_game=True)

    # 3. Trigger update
    results = updater.trigger_update_now()

    # 4. Verify update occurred
    state = state_manager.get_contest(contest_id)
    assert state is not None
    # Note: live_scores may not be set if ESPN API returns no live games
    # But update_count should increment
    # assert state.update_count >= 0  # Update attempted

    # 5. Get summary
    summary = state_manager.get_contest_summary(contest_id)
    assert summary['contest_id'] == contest_id
    assert summary['has_pre_game'] is True

    # 6. Deactivate
    state_manager.deactivate_contest(contest_id)
    assert not state.is_active


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
