import { useState } from 'react';
import { Zap, X, CheckCircle2, AlertCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { apiService } from '../services/api';

export function LiveStatsTest() {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTest = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.testLiveStats();
      setResult(data);
      setIsOpen(true);
    } catch (err) {
      setError('Failed to test live stats');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Test Button */}
      <button
        onClick={handleTest}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        <Zap className={`w-4 h-4 ${loading ? 'animate-pulse' : ''}`} />
        Test Live Stats
      </button>

      {/* Results Modal */}
      {isOpen && result && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Zap className="w-6 h-6 text-purple-600" />
                Live Stats Test Results
              </h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto flex-1">
              {/* ESPN Status */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                  {result.espn_working ? (
                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                  ) : (
                    <AlertCircle className="w-6 h-6 text-red-600" />
                  )}
                  <h3 className="text-lg font-semibold">
                    ESPN API: {result.espn_working ? 'Working ✅' : 'Not Working ❌'}
                  </h3>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 p-4 rounded">
                    <div className="text-sm text-blue-600 font-medium">Live Games</div>
                    <div className="text-2xl font-bold text-blue-900">{result.live_games}</div>
                  </div>
                  <div className="bg-green-50 p-4 rounded">
                    <div className="text-sm text-green-600 font-medium">Players with Stats</div>
                    <div className="text-2xl font-bold text-green-900">{result.total_players_with_stats}</div>
                  </div>
                </div>
              </div>

              {/* Live Games */}
              {result.games && result.games.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3">Live Games</h3>
                  {result.games.map((game: any, i: number) => (
                    <div key={i} className="bg-gray-50 p-4 rounded mb-2">
                      <div className="font-bold text-lg">
                        {game.away_team} {game.away_score} @ {game.home_team} {game.home_score}
                      </div>
                      <div className="text-sm text-gray-600">
                        Q{game.quarter} - {game.clock}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Top Scorers */}
              {result.top_scorers && result.top_scorers.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3">Top 10 Live Scorers</h3>
                  <div className="space-y-2">
                    {result.top_scorers.map((player: any, i: number) => (
                      <div key={i} className="flex items-center justify-between bg-gray-50 p-3 rounded">
                        <div className="flex-1">
                          <span className="font-medium">{i + 1}. {player.name}</span>
                          <span className="text-sm text-gray-600 ml-2">({player.team.split(' ').pop()})</span>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-lg">{player.points} pts</div>
                          <div className="text-xs text-gray-500">
                            {(100 - player.pct_remaining).toFixed(0)}% complete
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Player Matching */}
              {result.matching && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3">Player Name Matching</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-blue-50 p-4 rounded">
                      <div className="text-sm text-blue-600 font-medium">ESPN Players</div>
                      <div className="text-2xl font-bold text-blue-900">{result.matching.players_with_stats}</div>
                    </div>
                    <div className="bg-green-50 p-4 rounded">
                      <div className="text-sm text-green-600 font-medium">Matched</div>
                      <div className="text-2xl font-bold text-green-900">{result.matching.players_matched}</div>
                    </div>
                    <div className="bg-purple-50 p-4 rounded">
                      <div className="text-sm text-purple-600 font-medium">Match Rate</div>
                      <div className="text-2xl font-bold text-purple-900">{result.matching.match_rate.toFixed(1)}%</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Projection Changes */}
              {result.projection_changes && result.projection_changes.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3">Top Projection Changes</h3>
                  <div className="space-y-2">
                    {result.projection_changes.map((change: any, i: number) => {
                      const isPositive = change.change > 0;
                      return (
                        <div key={i} className="flex items-center justify-between bg-gray-50 p-3 rounded">
                          <div className="flex-1">
                            <span className="font-medium">{change.name}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-gray-600">{change.original}</span>
                            <span className="text-gray-400">→</span>
                            <span className="font-bold">{change.live}</span>
                            <div className={`flex items-center gap-1 min-w-[80px] justify-end ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                              {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                              <span className="font-semibold">{isPositive ? '+' : ''}{change.change}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Timestamp */}
              <div className="mt-6 text-sm text-gray-500 text-center">
                Tested at: {new Date(result.tested_at).toLocaleString()}
              </div>
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-gray-200 bg-gray-50">
              <button
                onClick={() => setIsOpen(false)}
                className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="text-red-600 text-sm mt-2">{error}</div>
      )}
    </>
  );
}
