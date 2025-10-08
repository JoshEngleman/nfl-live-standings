import { useState, useEffect } from 'react';
import { User, TrendingUp, Trophy, DollarSign, Target, Users } from 'lucide-react';
import { apiService } from '../services/api';
import { getTeamColors } from '../data/teamColors';

interface Player {
  name: string;
  position: string;
  team: string;
  current_score: number;
  projection: number;
  actual_points: number;
  is_captain: boolean;
}

interface ROIMetrics {
  expected_payout: number;
  expected_roi: number;
  expected_roi_pct: number;
  cash_rate: number;
  num_duplicates: number;
}

interface Lineup {
  lineup_index: number;
  entry_id: string;
  avg_score: number;
  projected_score: number | null;
  actual_points: number;
  top_1pct_rate: number;
  roi_metrics: ROIMetrics | null;
  players: Player[];
}

interface PlayerExposure {
  name: string;
  position: string;
  team: string;
  user_exposure: number;
  field_exposure: number;
  exposure_diff: number;
  num_lineups: number;
  avg_score: number;
  projected_score: number;
  actual_points: number;
}

interface Stack {
  stack: string;
  count: number;
  exposure: number;
}

interface GameCorrelation {
  correlation: string;
  team: string;
  count: number;
  exposure: number;
}

interface PortfolioSummary {
  username: string;
  total_entries: number;
  total_entry_fees: number;
  total_expected_payout: number;
  total_expected_roi: number;
  total_expected_roi_pct: number;
  mean_roi_pct: number | null;
  median_roi_pct: number | null;
  portfolio_win_rate: number;
  best_lineup: { entry_id: string; avg_score: number };
  worst_lineup: { entry_id: string; avg_score: number };
}

interface PortfolioData {
  contest_id: string;
  username: string;
  portfolio_summary: PortfolioSummary;
  lineups: Lineup[];
  player_exposure: PlayerExposure[];
  qb_stacks: Stack[];
  qb_plus_2_stacks: Stack[];
  qb_plus_3_stacks: Stack[];
  qb_plus_4_stacks: Stack[];
  game_correlations: GameCorrelation[];
}

interface PortfolioViewProps {
  contestId: string;
  initialUsername?: string;
  allUsernames: string[];
}

export function PortfolioView({ contestId, initialUsername, allUsernames }: PortfolioViewProps) {
  const [selectedUsername, setSelectedUsername] = useState<string>(initialUsername || '');
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPortfolio = async (username: string) => {
    if (!username) return;

    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getPortfolio(contestId, username);
      setPortfolioData(data);
    } catch (err) {
      console.error('Failed to fetch portfolio:', err);
      setError('Failed to load portfolio data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedUsername) {
      fetchPortfolio(selectedUsername);
    }
  }, [selectedUsername, contestId]);

  // Unique sorted usernames
  const uniqueUsernames = Array.from(new Set(allUsernames)).sort();

  return (
    <div className="space-y-6">
      {/* Username Selector */}
      <div className="bg-white rounded-lg shadow p-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Username
        </label>
        <select
          value={selectedUsername}
          onChange={(e) => setSelectedUsername(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">-- Choose a user --</option>
          {uniqueUsernames.map((username) => (
            <option key={username} value={username}>
              {username}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-500">Loading portfolio...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {portfolioData && !loading && (
        <>
          {/* Portfolio Summary */}
          <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg shadow-lg p-6 border-2 border-blue-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-gray-900">{portfolioData.portfolio_summary.username}</h3>
                <p className="text-sm text-gray-600">Portfolio Analysis</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg p-4 shadow">
                <div className="text-xs text-gray-600 font-medium mb-1">Total Entries</div>
                <div className="text-2xl font-bold text-blue-700">
                  {portfolioData.portfolio_summary.total_entries}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  ${portfolioData.portfolio_summary.total_entry_fees.toLocaleString()} invested
                </div>
              </div>

              <div className="bg-white rounded-lg p-4 shadow">
                <div className="text-xs text-gray-600 font-medium mb-1">Expected ROI</div>
                <div className={`text-2xl font-bold ${
                  portfolioData.portfolio_summary.total_expected_roi_pct > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {portfolioData.portfolio_summary.total_expected_roi_pct > 0 ? '+' : ''}
                  {portfolioData.portfolio_summary.total_expected_roi_pct.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  ${portfolioData.portfolio_summary.total_expected_roi > 0 ? '+' : ''}
                  {portfolioData.portfolio_summary.total_expected_roi.toLocaleString()}
                </div>
              </div>

              <div className="bg-white rounded-lg p-4 shadow">
                <div className="text-xs text-gray-600 font-medium mb-1">Mean / Median ROI</div>
                <div className="text-lg font-bold text-gray-900">
                  {portfolioData.portfolio_summary.mean_roi_pct?.toFixed(1)}% / {portfolioData.portfolio_summary.median_roi_pct?.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Per-lineup avg
                </div>
              </div>

              <div className="bg-white rounded-lg p-4 shadow">
                <div className="text-xs text-gray-600 font-medium mb-1">Win Probability</div>
                <div className="text-2xl font-bold text-purple-700">
                  {portfolioData.portfolio_summary.portfolio_win_rate.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  At least 1 wins
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-4">
              <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                <div className="text-xs text-green-700 font-medium mb-1">Best Lineup</div>
                <div className="text-lg font-bold text-green-900">
                  {portfolioData.portfolio_summary.best_lineup.avg_score.toFixed(1)} pts
                </div>
                <div className="text-xs text-green-600">
                  Entry: {portfolioData.portfolio_summary.best_lineup.entry_id.slice(-6)}
                </div>
              </div>

              <div className="bg-red-50 rounded-lg p-3 border border-red-200">
                <div className="text-xs text-red-700 font-medium mb-1">Worst Lineup</div>
                <div className="text-lg font-bold text-red-900">
                  {portfolioData.portfolio_summary.worst_lineup.avg_score.toFixed(1)} pts
                </div>
                <div className="text-xs text-red-600">
                  Entry: {portfolioData.portfolio_summary.worst_lineup.entry_id.slice(-6)}
                </div>
              </div>
            </div>
          </div>

          {/* Lineups Performance Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Trophy className="w-5 h-5" />
                Lineup Performance ({portfolioData.lineups.length} lineups)
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">RANK</th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ENTRY</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">PROJ</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">SIM</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">ACTUAL</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">TOP 1%</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">EXP ROI</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">CASH%</th>
                    <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">PLAYERS</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {portfolioData.lineups.slice(0, 10).map((lineup, idx) => (
                    <tr key={lineup.entry_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-3 py-2 text-sm font-semibold text-gray-600">
                        #{idx + 1}
                      </td>
                      <td className="px-3 py-2 text-sm font-medium text-gray-900">
                        {lineup.entry_id.slice(-6)}
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-gray-600">
                        {lineup.projected_score?.toFixed(1) || '-'}
                      </td>
                      <td className="px-3 py-2 text-right text-sm font-bold text-gray-900">
                        {lineup.avg_score.toFixed(1)}
                      </td>
                      <td className="px-3 py-2 text-right text-sm font-bold text-blue-700">
                        {lineup.actual_points.toFixed(1)}
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-gray-700">
                        {(lineup.top_1pct_rate * 100).toFixed(1)}%
                      </td>
                      <td className="px-3 py-2 text-right">
                        {lineup.roi_metrics && (
                          <span className={`text-sm font-semibold ${
                            lineup.roi_metrics.expected_roi_pct > 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {lineup.roi_metrics.expected_roi_pct > 0 ? '+' : ''}
                            {lineup.roi_metrics.expected_roi_pct.toFixed(1)}%
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-gray-700">
                        {lineup.roi_metrics?.cash_rate.toFixed(1)}%
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1 justify-center">
                          {lineup.players.map((player, pidx) => {
                            const teamColors = getTeamColors(player.team);
                            return (
                              <div
                                key={pidx}
                                className="inline-flex items-center px-2 py-1 rounded text-xs font-medium"
                                style={{
                                  backgroundColor: teamColors.primary,
                                  color: teamColors.text,
                                }}
                                title={`${player.name} (${player.position}): ${player.actual_points.toFixed(1)} pts actual`}
                              >
                                <span className="font-medium">{player.name.split(' ').pop()}</span>
                                <span className="ml-1 opacity-90">{player.actual_points.toFixed(1)}</span>
                              </div>
                            );
                          })}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {portfolioData.lineups.length > 10 && (
              <div className="px-6 py-3 bg-gray-50 text-center text-sm text-gray-500">
                Showing top 10 of {portfolioData.lineups.length} lineups (sorted by expected ROI)
              </div>
            )}
          </div>

          {/* Player Exposure */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Users className="w-5 h-5" />
                Player Exposure
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PLAYER</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">PROJ FP</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">ACTUAL FP</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">FIELD %</th>
                    <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">DIFF</th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" style={{ minWidth: '200px' }}>PORTFOLIO %</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {portfolioData.player_exposure.slice(0, 15).map((player) => {
                    const teamColors = getTeamColors(player.team);
                    const isLeverage = player.exposure_diff > 5;
                    const isFade = player.exposure_diff < -5;

                    return (
                      <tr key={player.name} className="hover:bg-gray-50 transition-colors">
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <div
                              className="px-2 py-1 rounded text-xs font-bold"
                              style={{
                                backgroundColor: teamColors.primary,
                                color: teamColors.text,
                              }}
                            >
                              {player.position}
                            </div>
                            <div>
                              <div className="text-sm font-semibold text-gray-900">{player.name}</div>
                              <div className="text-xs text-gray-500">{player.num_lineups} lineups</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right text-sm text-gray-600">
                          {player.projected_score.toFixed(1)}
                        </td>
                        <td className="px-3 py-2 text-right text-sm font-bold text-blue-700">
                          {player.actual_points.toFixed(1)}
                        </td>
                        <td className="px-3 py-2 text-right text-sm text-gray-600">
                          {player.field_exposure.toFixed(1)}%
                        </td>
                        <td className="px-3 py-2 text-right">
                          <span className={`text-sm font-semibold ${
                            isLeverage ? 'text-green-600' : isFade ? 'text-orange-600' : 'text-gray-600'
                          }`}>
                            {player.exposure_diff > 0 ? '+' : ''}
                            {player.exposure_diff.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <div className="relative">
                            <div className="bg-gray-200 rounded-full h-6 overflow-hidden">
                              <div
                                className="bg-blue-600 h-full transition-all duration-300 flex items-center justify-end pr-2"
                                style={{ width: `${Math.min(player.user_exposure, 100)}%` }}
                              >
                                <span className="text-xs font-bold text-white">
                                  {player.user_exposure.toFixed(1)}%
                                </span>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Stack Analysis */}
          <div className="space-y-6">
            {/* QB + 1 Pass Catcher */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  QB + Pass Catcher Stacks
                </h3>
              </div>
              <div className="p-4 space-y-2">
                {portfolioData.qb_stacks.slice(0, 8).map((stack) => (
                  <div key={stack.stack} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">{stack.stack}</div>
                      <div className="text-xs text-gray-500">{stack.count} lineups</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-blue-700">{stack.exposure.toFixed(1)}%</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Multi-Receiver Stacks Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* QB + 2 */}
              {portfolioData.qb_plus_2_stacks.length > 0 && (
                <div className="bg-white rounded-lg shadow overflow-hidden flex flex-col h-full">
                  <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-blue-50">
                    <h4 className="text-sm font-bold text-gray-900">QB + 2 Stacks</h4>
                  </div>
                  <div className="p-3 space-y-2 flex-1">
                    {portfolioData.qb_plus_2_stacks.slice(0, 5).map((stack) => (
                      <div key={stack.stack} className="p-2 bg-purple-50 rounded">
                        <div className="text-xs font-medium text-gray-900 truncate">{stack.stack}</div>
                        <div className="flex justify-between mt-1">
                          <span className="text-xs text-gray-500">{stack.count} lineups</span>
                          <span className="text-sm font-bold text-purple-700">{stack.exposure.toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* QB + 3 */}
              {portfolioData.qb_plus_3_stacks.length > 0 && (
                <div className="bg-white rounded-lg shadow overflow-hidden flex flex-col h-full">
                  <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-green-50 to-teal-50">
                    <h4 className="text-sm font-bold text-gray-900">QB + 3 Stacks</h4>
                  </div>
                  <div className="p-3 space-y-2 flex-1">
                    {portfolioData.qb_plus_3_stacks.slice(0, 5).map((stack) => (
                      <div key={stack.stack} className="p-2 bg-green-50 rounded">
                        <div className="text-xs font-medium text-gray-900 truncate">{stack.stack}</div>
                        <div className="flex justify-between mt-1">
                          <span className="text-xs text-gray-500">{stack.count} lineups</span>
                          <span className="text-sm font-bold text-green-700">{stack.exposure.toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* QB + 4 */}
              {portfolioData.qb_plus_4_stacks.length > 0 && (
                <div className="bg-white rounded-lg shadow overflow-hidden flex flex-col h-full">
                  <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-orange-50 to-red-50">
                    <h4 className="text-sm font-bold text-gray-900">QB + 4 Stacks</h4>
                  </div>
                  <div className="p-3 space-y-2 flex-1">
                    {portfolioData.qb_plus_4_stacks.slice(0, 5).map((stack) => (
                      <div key={stack.stack} className="p-2 bg-orange-50 rounded">
                        <div className="text-xs font-medium text-gray-900 truncate">{stack.stack}</div>
                        <div className="flex justify-between mt-1">
                          <span className="text-xs text-gray-500">{stack.count} lineups</span>
                          <span className="text-sm font-bold text-orange-700">{stack.exposure.toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Game Correlations */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Game Stack Correlations
                </h3>
                <p className="text-xs text-gray-500 mt-1">Team distribution patterns (e.g., 5-1 KC = 5 from Chiefs, 1 from opponent)</p>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
                  {portfolioData.game_correlations.map((corr) => {
                    const teamColors = getTeamColors(corr.team);
                    return (
                      <div
                        key={`${corr.correlation}-${corr.team}`}
                        className="rounded-lg p-3 border-2"
                        style={{
                          backgroundColor: `${teamColors.primary}15`,
                          borderColor: teamColors.primary,
                        }}
                      >
                        <div className="text-center">
                          <div className="text-2xl font-bold" style={{ color: teamColors.primary }}>
                            {corr.correlation}
                          </div>
                          <div
                            className="text-sm font-bold mt-1 px-2 py-0.5 rounded inline-block"
                            style={{
                              backgroundColor: teamColors.primary,
                              color: teamColors.text,
                            }}
                          >
                            {corr.team}
                          </div>
                          <div className="text-xs text-gray-600 mt-1">{corr.count} lineups</div>
                          <div className="text-base font-bold text-gray-900 mt-1">{corr.exposure.toFixed(1)}%</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {!selectedUsername && !loading && (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <User className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Username</h3>
          <p className="text-gray-500">Choose a user from the dropdown to view their portfolio analysis</p>
        </div>
      )}
    </div>
  );
}
