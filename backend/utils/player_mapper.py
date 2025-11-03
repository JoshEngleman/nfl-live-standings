"""
Player name matching between ESPN API and Stokastic CSV.

Handles common naming differences:
- Suffixes: "Patrick Mahomes II" vs "Patrick Mahomes"
- Apostrophes: "De'Von Achane" vs "Devon Achane"
- Nicknames: "Gabe Davis" vs "Gabriel Davis"
- Periods: "A.J. Brown" vs "AJ Brown"
"""

"""
Deegs comments 11/2/2025:
I've found that a simple uniform name cleaning function can do everything you're looking for without the overhead of a whole PlayerNameMapper.
If you just by default pipe the clean_name function into any data loading and collating, you should have very few issues with name mismatches.
There still might be a few conversions required for names that are unaligned, but a simple dict lookup should take care of it.
An initial run with a try: except: should catch the exceptions and determine the conversion dict.
I haven't done anything else besides write the function right here, so PlayerNameMapper is still in use everywhere (and will cause crashes if this PR is accepted but no changes are made elsewhere)
"""

import unidecode

CONVERSIONS = {
#     Name issues that need manual overrides

}

def clean_name(name: str) -> str:
    """
    Standardizes name across all sources/sites.
    Names different across FanDuel, DraftKings, BasketballReference, RotoGrinders, ESPN, etc.
    Takes in a name and returns just the first and last name, removing any foreign characters, suffixes, and periods.

    Perfect for __post_init__() in dataclasses or to chain with .apply with pd.read_csv()
    """
    return CONVERSIONS.get(
        name,
        unidecode.unidecode(' '.join(name.split(' ')[:2]).replace('.', '').strip())
    )

# import json
# import re
# from pathlib import Path
# from typing import Dict, List, Optional, Tuple
# from difflib import SequenceMatcher
#
#
# class PlayerNameMapper:
#     """
#     Maps player names from ESPN API to Stokastic CSV format.
#
#     Uses multi-tiered approach:
#     1. Exact match
#     2. Manual override map
#     3. Normalized name match
#     4. Fuzzy match with high confidence
#     5. Position + team match as tiebreaker
#     """
#
#     def __init__(self, override_file: Optional[str] = None):
#         """
#         Initialize player name mapper.
#
#         Args:
#             override_file: Path to JSON file with manual name mappings
#         """
#         self.overrides = self._load_overrides(override_file)
#         self.match_cache: Dict[str, str] = {}  # ESPN name -> Stokastic name
#
#     def _load_overrides(self, override_file: Optional[str]) -> Dict[str, str]:
#         """Load manual name override mappings from JSON file."""
#         if not override_file:
#             # Try default location
#             default_path = Path(__file__).parent.parent / 'data' / 'player_name_overrides.json'
#             if default_path.exists():
#                 override_file = str(default_path)
#             else:
#                 return {}
#
#         try:
#             with open(override_file, 'r') as f:
#                 return json.load(f)
#         except (FileNotFoundError, json.JSONDecodeError):
#             return {}
#
#     def normalize_name(self, name: str) -> str:
#         """
#         Normalize player name for matching.
#
#         Removes:
#         - Suffixes: Jr., Sr., II, III, IV, V
#         - Extra whitespace
#         - Periods
#         - Apostrophes (standardized)
#
#         Examples:
#             "Patrick Mahomes II" -> "patrick mahomes"
#             "De'Von Achane" -> "devon achane"
#             "A.J. Brown" -> "aj brown"
#         """
#         # Lowercase
#         name = name.lower().strip()
#
#         # Remove suffixes
#         suffixes = [' jr.', ' jr', ' sr.', ' sr', ' ii', ' iii', ' iv', ' v']
#         for suffix in suffixes:
#             if name.endswith(suffix):
#                 name = name[:-len(suffix)].strip()
#
#         # Remove periods
#         name = name.replace('.', '')
#
#         # Remove apostrophes (or standardize them)
#         name = name.replace("'", "").replace("'", "").replace("`", "")
#
#         # Normalize whitespace
#         name = re.sub(r'\s+', ' ', name).strip()
#
#         return name
#
#     def fuzzy_match_score(self, name1: str, name2: str) -> float:
#         """
#         Calculate fuzzy match score between two names.
#
#         Uses SequenceMatcher for similarity ratio.
#
#         Args:
#             name1: First name (normalized)
#             name2: Second name (normalized)
#
#         Returns:
#             Similarity score 0.0 to 1.0 (1.0 = perfect match)
#         """
#         return SequenceMatcher(None, name1, name2).ratio()
#
#     def find_best_match(
#         self,
#         espn_name: str,
#         stokastic_names: List[str],
#         espn_team: Optional[str] = None,
#         espn_position: Optional[str] = None,
#         threshold: float = 0.85
#     ) -> Optional[str]:
#         """
#         Find best matching Stokastic name for ESPN name.
#
#         Matching strategy:
#         1. Check cache
#         2. Exact match (case-insensitive)
#         3. Manual override map
#         4. Normalized exact match
#         5. Fuzzy match (threshold = 0.85)
#         6. If multiple high matches, use team/position to decide
#
#         Args:
#             espn_name: Player name from ESPN API
#             stokastic_names: List of all player names from Stokastic CSV
#             espn_team: Optional team name for tiebreaking
#             espn_position: Optional position for tiebreaking
#             threshold: Minimum fuzzy match score (0.85 = 85% similar)
#
#         Returns:
#             Best matching Stokastic name, or None if no good match
#         """
#         # Check cache
#         if espn_name in self.match_cache:
#             return self.match_cache[espn_name]
#
#         # Exact match (case-insensitive)
#         for stok_name in stokastic_names:
#             if espn_name.lower() == stok_name.lower():
#                 self.match_cache[espn_name] = stok_name
#                 return stok_name
#
#         # Manual override
#         if espn_name in self.overrides:
#             matched = self.overrides[espn_name]
#             # Verify the override name exists in stokastic list
#             if matched in stokastic_names:
#                 self.match_cache[espn_name] = matched
#                 return matched
#
#         # Normalize names
#         espn_normalized = self.normalize_name(espn_name)
#
#         # Normalized exact match
#         for stok_name in stokastic_names:
#             if espn_normalized == self.normalize_name(stok_name):
#                 self.match_cache[espn_name] = stok_name
#                 return stok_name
#
#         # Fuzzy matching - find all candidates above threshold
#         candidates: List[Tuple[str, float]] = []
#
#         for stok_name in stokastic_names:
#             stok_normalized = self.normalize_name(stok_name)
#             score = self.fuzzy_match_score(espn_normalized, stok_normalized)
#
#             if score >= threshold:
#                 candidates.append((stok_name, score))
#
#         # No matches
#         if not candidates:
#             return None
#
#         # Sort by score descending
#         candidates.sort(key=lambda x: x[1], reverse=True)
#
#         # If top match is significantly better (0.05+ higher), use it
#         if len(candidates) == 1 or (candidates[0][1] - candidates[1][1] > 0.05):
#             matched = candidates[0][0]
#             self.match_cache[espn_name] = matched
#             return matched
#
#         # Multiple close matches - would need team/position to decide
#         # For now, take the best one
#         # TODO: Add team/position matching if this becomes an issue
#         matched = candidates[0][0]
#         self.match_cache[espn_name] = matched
#         return matched
#
#     def match_player(
#         self,
#         espn_name: str,
#         stokastic_names: List[str],
#         espn_team: Optional[str] = None,
#         espn_position: Optional[str] = None
#     ) -> Optional[str]:
#         """
#         Public API: Match ESPN player name to Stokastic name.
#
#         Args:
#             espn_name: Player name from ESPN
#             stokastic_names: All available names in Stokastic CSV
#             espn_team: Optional team for tiebreaking
#             espn_position: Optional position for tiebreaking
#
#         Returns:
#             Matched Stokastic name, or None if no match found
#         """
#         return self.find_best_match(espn_name, stokastic_names, espn_team, espn_position)
#
#     def batch_match(
#         self,
#         espn_players: Dict[str, Dict],
#         stokastic_names: List[str]
#     ) -> Dict[str, Optional[str]]:
#         """
#         Match multiple ESPN players at once.
#
#         Args:
#             espn_players: Dict of ESPN_name -> {'team': ..., 'position': ...}
#             stokastic_names: All available names in Stokastic CSV
#
#         Returns:
#             Dict mapping ESPN_name -> matched Stokastic name (or None)
#         """
#         results = {}
#
#         for espn_name, info in espn_players.items():
#             team = info.get('team')
#             position = info.get('position')
#             matched = self.match_player(espn_name, stokastic_names, team, position)
#             results[espn_name] = matched
#
#         return results
#
#     def get_match_report(
#         self,
#         espn_players: Dict[str, Dict],
#         stokastic_names: List[str]
#     ) -> Dict:
#         """
#         Generate detailed match report for debugging.
#
#         Args:
#             espn_players: Dict of ESPN_name -> {'team': ..., 'position': ...}
#             stokastic_names: All available names in Stokastic CSV
#
#         Returns:
#             Dict with:
#             - matched: List of (ESPN name, Stokastic name) tuples
#             - unmatched: List of ESPN names that couldn't be matched
#             - match_rate: Percentage of successful matches
#         """
#         matches = self.batch_match(espn_players, stokastic_names)
#
#         matched = [(espn, stok) for espn, stok in matches.items() if stok is not None]
#         unmatched = [espn for espn, stok in matches.items() if stok is None]
#
#         match_rate = (len(matched) / len(matches) * 100) if matches else 0.0
#
#         return {
#             'matched': matched,
#             'unmatched': unmatched,
#             'match_rate': match_rate,
#             'total_espn_players': len(espn_players),
#             'total_stokastic_players': len(stokastic_names)
#         }
#
#
# # Convenience function for one-off matching
# def match_player_name(
#     espn_name: str,
#     stokastic_names: List[str],
#     override_file: Optional[str] = None
# ) -> Optional[str]:
#     """
#     Quick one-off player name matching.
#
#     Args:
#         espn_name: Player name from ESPN
#         stokastic_names: All available Stokastic names
#         override_file: Optional path to JSON override file
#
#     Returns:
#         Matched Stokastic name or None
#     """
#     mapper = PlayerNameMapper(override_file)
#     return mapper.match_player(espn_name, stokastic_names)
