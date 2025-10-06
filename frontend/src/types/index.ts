export interface Contest {
  contest_id: string;
  slate_type: string;
  num_lineups: number;
  num_players: number;
  entry_fee: number;
  iterations: number;
  created_at: string;
  last_update: string | null;
  update_count: number;
  is_active: boolean;
  has_pre_game: boolean;
  has_live: boolean;
  live_stats?: ScoreStats;
  pre_game_stats?: ScoreStats;
}

export interface ScoreStats {
  mean_score: number;
  std_score: number;
  min_score: number;
  max_score: number;
}

export interface LineupResult {
  entry_name: string;
  entry_id: string;
  username: string;
  win_rate: number;
  top3_rate: number;
  avg_finish: number;
  expected_value: number;
  roi: number;
}

export interface UpdaterStatus {
  is_running: boolean;
  update_interval_seconds: number;
  active_contests: number;
  contest_ids: string[];
  next_run: string | null;
}

export interface UpdateResult {
  contest_id: string;
  update_time: string;
  duration_seconds: number;
  num_lineups: number;
  iterations: number;
  live_games: number;
  players_matched: number;
  players_unmatched: number;
  match_rate: number;
}

export interface WebSocketMessage {
  type: 'connection_established' | 'contest_update' | 'status_response' | 'error';
  timestamp?: string;
  contest_id?: string;
  data?: UpdateResult;
  updater_status?: UpdaterStatus;
  active_contests?: string[];
  message?: string;
}

export interface HealthStatus {
  status: string;
  components: {
    csv_parser: string;
    simulation_engine: string;
    contest_analyzer: string;
    live_stats_service: string;
    background_updater: string;
  };
  updater_status: UpdaterStatus;
}
