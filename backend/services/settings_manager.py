"""
Global settings manager for simulation configuration.

Stores settings like:
- Position-based simulation toggle
- Number of iterations
- Other simulation parameters
"""

from typing import Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class SimulationSettings:
    """Simulation configuration settings."""
    use_position_based: bool = False
    iterations: int = 10000
    use_lognormal: bool = True  # Only used when position_based is False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationSettings':
        """Create from dictionary."""
        return cls(
            use_position_based=data.get('use_position_based', False),
            iterations=data.get('iterations', 10000),
            use_lognormal=data.get('use_lognormal', True)
        )


class SettingsManager:
    """Manages global simulation settings."""

    def __init__(self):
        self._settings = SimulationSettings()

    def get_settings(self) -> SimulationSettings:
        """Get current settings."""
        return self._settings

    def update_settings(self, **kwargs) -> SimulationSettings:
        """
        Update settings.

        Args:
            **kwargs: Settings to update (use_position_based, iterations, use_lognormal)

        Returns:
            Updated settings
        """
        if 'use_position_based' in kwargs:
            self._settings.use_position_based = kwargs['use_position_based']

        if 'iterations' in kwargs:
            iterations = kwargs['iterations']
            # Validate iterations (min 100, max 50000)
            if iterations < 100:
                iterations = 100
            elif iterations > 50000:
                iterations = 50000
            self._settings.iterations = iterations

        if 'use_lognormal' in kwargs:
            self._settings.use_lognormal = kwargs['use_lognormal']

        return self._settings

    def reset_to_defaults(self) -> SimulationSettings:
        """Reset to default settings."""
        self._settings = SimulationSettings()
        return self._settings


# Global singleton instance
_settings_manager = SettingsManager()


def get_settings_manager() -> SettingsManager:
    """Get global settings manager instance."""
    return _settings_manager
