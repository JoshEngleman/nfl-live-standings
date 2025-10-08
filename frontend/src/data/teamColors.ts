/**
 * NFL Team Colors Configuration
 * Using official team colors with proper contrast ratios for accessibility
 */

export interface TeamColors {
  primary: string;
  secondary: string;
  accent: string;
  text: string; // Text color for readability on primary background
}

export const NFL_TEAM_COLORS: Record<string, TeamColors> = {
  // AFC East
  'Buffalo Bills': {
    primary: '#00338D',
    secondary: '#C60C30',
    accent: '#00338D',
    text: '#FFFFFF',
  },
  'Miami Dolphins': {
    primary: '#008E97',
    secondary: '#FC4C02',
    accent: '#005778',
    text: '#FFFFFF',
  },
  'New England Patriots': {
    primary: '#002244',
    secondary: '#C60C30',
    accent: '#B0B7BC',
    text: '#FFFFFF',
  },
  'New York Jets': {
    primary: '#125740',
    secondary: '#FFFFFF',
    accent: '#000000',
    text: '#FFFFFF',
  },

  // AFC North
  'Baltimore Ravens': {
    primary: '#241773',
    secondary: '#000000',
    accent: '#9E7C0C',
    text: '#FFFFFF',
  },
  'Cincinnati Bengals': {
    primary: '#FB4F14',
    secondary: '#000000',
    accent: '#FB4F14',
    text: '#FFFFFF',
  },
  'Cleveland Browns': {
    primary: '#311D00',
    secondary: '#FF3C00',
    accent: '#311D00',
    text: '#FFFFFF',
  },
  'Pittsburgh Steelers': {
    primary: '#FFB612',
    secondary: '#101820',
    accent: '#C60C30',
    text: '#000000',
  },

  // AFC South
  'Houston Texans': {
    primary: '#03202F',
    secondary: '#A71930',
    accent: '#03202F',
    text: '#FFFFFF',
  },
  'Indianapolis Colts': {
    primary: '#002C5F',
    secondary: '#A2AAAD',
    accent: '#002C5F',
    text: '#FFFFFF',
  },
  'Jacksonville Jaguars': {
    primary: '#006778',
    secondary: '#D7A22A',
    accent: '#9F792C',
    text: '#FFFFFF',
  },
  'Tennessee Titans': {
    primary: '#0C2340',
    secondary: '#4B92DB',
    accent: '#C8102E',
    text: '#FFFFFF',
  },

  // AFC West
  'Denver Broncos': {
    primary: '#FB4F14',
    secondary: '#002244',
    accent: '#FB4F14',
    text: '#FFFFFF',
  },
  'Kansas City Chiefs': {
    primary: '#E31837',
    secondary: '#FFB81C',
    accent: '#E31837',
    text: '#FFFFFF',
  },
  'Las Vegas Raiders': {
    primary: '#000000',
    secondary: '#A5ACAF',
    accent: '#000000',
    text: '#FFFFFF',
  },
  'Los Angeles Chargers': {
    primary: '#0080C6',
    secondary: '#FFC20E',
    accent: '#0080C6',
    text: '#FFFFFF',
  },

  // NFC East
  'Dallas Cowboys': {
    primary: '#041E42',
    secondary: '#869397',
    accent: '#041E42',
    text: '#FFFFFF',
  },
  'New York Giants': {
    primary: '#0B2265',
    secondary: '#A71930',
    accent: '#A5ACAF',
    text: '#FFFFFF',
  },
  'Philadelphia Eagles': {
    primary: '#004C54',
    secondary: '#A5ACAF',
    accent: '#000000',
    text: '#FFFFFF',
  },
  'Washington Commanders': {
    primary: '#5A1414',
    secondary: '#FFB612',
    accent: '#5A1414',
    text: '#FFFFFF',
  },

  // NFC North
  'Chicago Bears': {
    primary: '#0B162A',
    secondary: '#C83803',
    accent: '#0B162A',
    text: '#FFFFFF',
  },
  'Detroit Lions': {
    primary: '#0076B6',
    secondary: '#B0B7BC',
    accent: '#000000',
    text: '#FFFFFF',
  },
  'Green Bay Packers': {
    primary: '#203731',
    secondary: '#FFB612',
    accent: '#203731',
    text: '#FFFFFF',
  },
  'Minnesota Vikings': {
    primary: '#4F2683',
    secondary: '#FFC62F',
    accent: '#4F2683',
    text: '#FFFFFF',
  },

  // NFC South
  'Atlanta Falcons': {
    primary: '#A71930',
    secondary: '#000000',
    accent: '#A5ACAF',
    text: '#FFFFFF',
  },
  'Carolina Panthers': {
    primary: '#0085CA',
    secondary: '#101820',
    accent: '#BFC0BF',
    text: '#FFFFFF',
  },
  'New Orleans Saints': {
    primary: '#D3BC8D',
    secondary: '#101820',
    accent: '#D3BC8D',
    text: '#000000',
  },
  'Tampa Bay Buccaneers': {
    primary: '#D50A0A',
    secondary: '#FF7900',
    accent: '#34302B',
    text: '#FFFFFF',
  },

  // NFC West
  'Arizona Cardinals': {
    primary: '#97233F',
    secondary: '#000000',
    accent: '#FFB612',
    text: '#FFFFFF',
  },
  'Los Angeles Rams': {
    primary: '#003594',
    secondary: '#FFA300',
    accent: '#FF8200',
    text: '#FFFFFF',
  },
  'San Francisco 49ers': {
    primary: '#AA0000',
    secondary: '#B3995D',
    accent: '#AA0000',
    text: '#FFFFFF',
  },
  'Seattle Seahawks': {
    primary: '#002244',
    secondary: '#69BE28',
    accent: '#A5ACAF',
    text: '#FFFFFF',
  },
};

/**
 * Mapping from team abbreviations to full team names
 */
const TEAM_ABBREVIATIONS: Record<string, string> = {
  // AFC East
  'BUF': 'Buffalo Bills',
  'MIA': 'Miami Dolphins',
  'NE': 'New England Patriots',
  'NYJ': 'New York Jets',

  // AFC North
  'BAL': 'Baltimore Ravens',
  'CIN': 'Cincinnati Bengals',
  'CLE': 'Cleveland Browns',
  'PIT': 'Pittsburgh Steelers',

  // AFC South
  'HOU': 'Houston Texans',
  'IND': 'Indianapolis Colts',
  'JAX': 'Jacksonville Jaguars',
  'TEN': 'Tennessee Titans',

  // AFC West
  'DEN': 'Denver Broncos',
  'KC': 'Kansas City Chiefs',
  'LV': 'Las Vegas Raiders',
  'LAC': 'Los Angeles Chargers',

  // NFC East
  'DAL': 'Dallas Cowboys',
  'NYG': 'New York Giants',
  'PHI': 'Philadelphia Eagles',
  'WAS': 'Washington Commanders',

  // NFC North
  'CHI': 'Chicago Bears',
  'DET': 'Detroit Lions',
  'GB': 'Green Bay Packers',
  'MIN': 'Minnesota Vikings',

  // NFC South
  'ATL': 'Atlanta Falcons',
  'CAR': 'Carolina Panthers',
  'NO': 'New Orleans Saints',
  'TB': 'Tampa Bay Buccaneers',

  // NFC West
  'ARI': 'Arizona Cardinals',
  'LAR': 'Los Angeles Rams',
  'SF': 'San Francisco 49ers',
  'SEA': 'Seattle Seahawks',
};

/**
 * Get team colors by team name or abbreviation
 * Returns default colors if team not found
 */
export function getTeamColors(teamName: string): TeamColors {
  // Try direct lookup first (full name)
  if (NFL_TEAM_COLORS[teamName]) {
    return NFL_TEAM_COLORS[teamName];
  }

  // Try abbreviation lookup
  const fullName = TEAM_ABBREVIATIONS[teamName];
  if (fullName && NFL_TEAM_COLORS[fullName]) {
    return NFL_TEAM_COLORS[fullName];
  }

  // Return default gray colors if not found
  return {
    primary: '#6B7280',
    secondary: '#9CA3AF',
    accent: '#6B7280',
    text: '#FFFFFF',
  };
}

/**
 * Get all unique teams from a list of player objects
 */
export function getTeamsFromPlayers(players: Array<{ team: string }>): string[] {
  const teams = new Set(players.map(p => p.team));
  return Array.from(teams);
}
