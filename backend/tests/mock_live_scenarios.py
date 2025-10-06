"""
Mock live game scenarios for testing pro-rating logic.

These scenarios simulate real game situations without requiring live API calls.
"""

from typing import Dict
import pandas as pd


def get_halftime_scenario() -> Dict[str, Dict]:
    """
    Mock scenario: Halftime (50% of game remaining).

    Mix of performances:
    - Some players outperforming (actual > projected pace)
    - Some players underperforming (actual < projected pace)
    - Some players on pace

    Returns dict: player_name -> {actual_points, pct_remaining, is_finished}
    """
    return {
        # QBs - Various performances
        'Justin Fields': {
            'actual_points': 18.5,  # Projected 21.9, slightly behind
            'pct_remaining': 0.5,
            'is_finished': False
        },
        'Justin Herbert': {
            'actual_points': 14.2,  # Projected 21.0, underperforming
            'pct_remaining': 0.5,
            'is_finished': False
        },
        'Patrick Mahomes': {
            'actual_points': 12.5,  # Projected 20.7, way behind
            'pct_remaining': 0.5,
            'is_finished': False
        },

        # RBs - Mixed bag
        'De\'Von Achane': {
            'actual_points': 8.2,  # Projected 21.8, disaster
            'pct_remaining': 0.5,
            'is_finished': False
        },
        'Jahmyr Gibbs': {
            'actual_points': 15.4,  # Projected 21.8, on pace
            'pct_remaining': 0.5,
            'is_finished': False
        },
        'Jonathan Taylor': {
            'actual_points': 18.7,  # Projected 21.6, slightly ahead!
            'pct_remaining': 0.5,
            'is_finished': False
        },
        'Breece Hall': {
            'actual_points': 12.1,  # Projected 19.3, behind pace
            'pct_remaining': 0.5,
            'is_finished': False
        },

        # WRs - Some big games, some duds
        'Garrett Wilson': {
            'actual_points': 14.8,  # Projected 16.3, on pace
            'pct_remaining': 0.5,
            'is_finished': False
        },
        'Jaxon Smith-Njigba': {
            'actual_points': 6.2,  # Projected 19.4, way behind
            'pct_remaining': 0.5,
            'is_finished': False
        },
        'Amon-Ra St. Brown': {
            'actual_points': 11.3,  # Projected 19.0, behind
            'pct_remaining': 0.5,
            'is_finished': False
        },

        # TEs
        'Trey McBride': {
            'actual_points': 9.8,  # Projected 15.6, on pace
            'pct_remaining': 0.5,
            'is_finished': False
        },

        # DST
        'Jets': {
            'actual_points': 4.0,  # Projected 5.7, close
            'pct_remaining': 0.5,
            'is_finished': False
        }
    }


def get_q3_scenario() -> Dict[str, Dict]:
    """
    Mock scenario: End of Q3 (25% of game remaining).

    Most outcomes becoming clearer. Less variance remaining.
    """
    return {
        'Justin Fields': {
            'actual_points': 24.5,  # Projected 21.9, exceeding!
            'pct_remaining': 0.25,
            'is_finished': False
        },
        'De\'Von Achane': {
            'actual_points': 12.3,  # Projected 21.8, still struggling
            'pct_remaining': 0.25,
            'is_finished': False
        },
        'Jahmyr Gibbs': {
            'actual_points': 19.2,  # Projected 21.8, on track
            'pct_remaining': 0.25,
            'is_finished': False
        },
        'Jonathan Taylor': {
            'actual_points': 23.1,  # Projected 21.6, great game!
            'pct_remaining': 0.25,
            'is_finished': False
        },
        'Garrett Wilson': {
            'actual_points': 15.7,  # Projected 16.3, solid
            'pct_remaining': 0.25,
            'is_finished': False
        },
        'Trey McBride': {
            'actual_points': 14.2,  # Projected 15.6, close
            'pct_remaining': 0.25,
            'is_finished': False
        }
    }


def get_mixed_slate_scenario() -> Dict[str, Dict]:
    """
    Mock scenario: Some games finished (4pm ET), some live (SNF/MNF).

    Realistic for DFS: Early games done, late games in progress.
    """
    return {
        # Finished games (4pm slate)
        'Jalen Hurts': {
            'actual_points': 18.3,  # Game finished
            'pct_remaining': 0.0,
            'is_finished': True
        },
        'Saquon Barkley': {
            'actual_points': 22.5,  # Big game, finished
            'pct_remaining': 0.0,
            'is_finished': True
        },
        'A.J. Brown': {
            'actual_points': 11.2,  # Disappointing, finished
            'pct_remaining': 0.0,
            'is_finished': True
        },

        # Live games (SNF - mid Q2)
        'Patrick Mahomes': {
            'actual_points': 8.5,  # SNF game, early
            'pct_remaining': 0.67,  # ~40 min remaining
            'is_finished': False
        },
        'Travis Kelce': {
            'actual_points': 5.2,
            'pct_remaining': 0.67,
            'is_finished': False
        },

        # Live games (MNF - halftime)
        'Trevor Lawrence': {
            'actual_points': 10.2,
            'pct_remaining': 0.5,
            'is_finished': False
        },
        'Travis Etienne Jr.': {
            'actual_points': 8.7,
            'pct_remaining': 0.5,
            'is_finished': False
        }
    }


def get_blowout_scenario() -> Dict[str, Dict]:
    """
    Mock scenario: Blowout game (starters benched in Q4).

    Some players' games effectively over despite clock remaining.
    """
    return {
        # Winning team - starters benched
        'Justin Fields': {
            'actual_points': 28.5,  # Great game, but benched
            'pct_remaining': 0.15,  # Q4, but won't play
            'is_finished': False  # Game not technically over
        },
        'Breece Hall': {
            'actual_points': 24.2,  # Also benched
            'pct_remaining': 0.15,
            'is_finished': False
        },

        # Losing team - garbage time potential
        'Bryce Young': {
            'actual_points': 8.2,  # Bad game, but passing in garbage time
            'pct_remaining': 0.15,
            'is_finished': False
        }
    }


def get_overtime_scenario() -> Dict[str, Dict]:
    """
    Mock scenario: Game in overtime.

    Treat OT as ~5% remaining (conservative).
    """
    return {
        'Justin Herbert': {
            'actual_points': 22.5,
            'pct_remaining': 0.05,  # OT
            'is_finished': False
        },
        'Quentin Johnston': {
            'actual_points': 14.8,
            'pct_remaining': 0.05,
            'is_finished': False
        }
    }


def create_mock_scenario_dataframe(scenario_name: str = 'halftime') -> pd.DataFrame:
    """
    Create a mock scenario as a DataFrame for easy testing.

    Args:
        scenario_name: One of: 'halftime', 'q3', 'mixed', 'blowout', 'overtime'

    Returns:
        DataFrame with columns: Name, Actual_Points, Pct_Remaining, Is_Finished
    """
    scenarios = {
        'halftime': get_halftime_scenario(),
        'q3': get_q3_scenario(),
        'mixed': get_mixed_slate_scenario(),
        'blowout': get_blowout_scenario(),
        'overtime': get_overtime_scenario()
    }

    if scenario_name not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario_name}. Choose from: {list(scenarios.keys())}")

    scenario = scenarios[scenario_name]

    # Convert to DataFrame
    data = []
    for player_name, stats in scenario.items():
        data.append({
            'Name': player_name,
            'Actual_Points': stats['actual_points'],
            'Pct_Remaining': stats['pct_remaining'],
            'Is_Finished': stats['is_finished']
        })

    return pd.DataFrame(data)


# Quick reference for expected pro-rated values
EXPECTED_PRORATED_EXAMPLES = {
    'halftime': {
        'Justin Fields': {
            'original': 21.9,
            'actual': 18.5,
            'prorated': 18.5 + (21.9 * 0.5),  # = 29.45
            'comment': 'Slightly behind pace, will likely exceed original projection'
        },
        'De\'Von Achane': {
            'original': 21.8,
            'actual': 8.2,
            'prorated': 8.2 + (21.8 * 0.5),  # = 19.1
            'comment': 'Way behind, unlikely to hit original projection'
        },
        'Jonathan Taylor': {
            'original': 21.6,
            'actual': 18.7,
            'prorated': 18.7 + (21.6 * 0.5),  # = 29.5
            'comment': 'Outperforming! Should beat original projection'
        }
    }
}


if __name__ == "__main__":
    """Demo the mock scenarios."""
    print("=" * 70)
    print("MOCK LIVE SCENARIOS")
    print("=" * 70)

    scenarios = ['halftime', 'q3', 'mixed', 'blowout', 'overtime']

    for scenario_name in scenarios:
        print(f"\n{scenario_name.upper()} SCENARIO:")
        print("-" * 70)

        df = create_mock_scenario_dataframe(scenario_name)
        print(df.to_string(index=False))

    print("\n" + "=" * 70)
    print("These scenarios can be used for testing without live games!")
    print("=" * 70)
