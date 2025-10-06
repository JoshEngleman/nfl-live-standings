import { useState, useEffect } from 'react';
import { Trophy, Users, DollarSign, TrendingUp, Clock, CheckCircle2 } from 'lucide-react';
import { apiService } from '../services/api';
import { Contest } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';

export function ContestList() {
  const [contests, setContests] = useState<Contest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lastMessage } = useWebSocket();

  const fetchContests = async () => {
    try {
      const data = await apiService.getContests();
      setContests(data.contests);
      setError(null);
    } catch (err) {
      setError('Failed to load contests');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContests();
  }, []);

  // Refresh when receiving WebSocket updates
  useEffect(() => {
    if (lastMessage?.type === 'contest_update') {
      fetchContests();
    }
  }, [lastMessage]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600">{error}</div>
      </div>
    );
  }

  if (contests.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <Trophy className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Contests</h3>
          <p className="text-gray-500">
            No contests are being monitored yet. Upload CSV files to get started.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Trophy className="w-5 h-5" />
          Contests ({contests.length})
        </h2>
      </div>

      <div className="divide-y divide-gray-200">
        {contests.map(contest => (
          <ContestCard key={contest.contest_id} contest={contest} />
        ))}
      </div>
    </div>
  );
}

function ContestCard({ contest }: { contest: Contest }) {
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  const getChangeIndicator = () => {
    if (!contest.pre_game_stats || !contest.live_stats) return null;

    const change = contest.live_stats.mean_score - contest.pre_game_stats.mean_score;
    const isPositive = change > 0;

    return (
      <div className={`flex items-center gap-1 text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        <TrendingUp className={`w-4 h-4 ${!isPositive && 'rotate-180'}`} />
        {isPositive ? '+' : ''}{change.toFixed(1)}
      </div>
    );
  };

  return (
    <div className="p-6 hover:bg-gray-50 transition">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {contest.contest_id}
          </h3>
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <span className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              {contest.num_lineups} lineups
            </span>
            <span className="flex items-center gap-1">
              <DollarSign className="w-4 h-4" />
              ${contest.entry_fee}
            </span>
            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
              {contest.slate_type}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {contest.is_active ? (
            <span className="flex items-center gap-1 text-green-600 text-sm font-medium">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Active
            </span>
          ) : (
            <span className="flex items-center gap-1 text-gray-500 text-sm font-medium">
              <CheckCircle2 className="w-4 h-4" />
              Inactive
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-3">
        {contest.live_stats && (
          <div className="bg-blue-50 p-3 rounded">
            <div className="text-xs text-blue-600 font-medium mb-1">Live Avg Score</div>
            <div className="text-lg font-bold text-blue-900 flex items-center justify-between">
              {contest.live_stats.mean_score.toFixed(1)}
              {getChangeIndicator()}
            </div>
          </div>
        )}

        {contest.pre_game_stats && (
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-xs text-gray-600 font-medium mb-1">Pre-Game Avg</div>
            <div className="text-lg font-bold text-gray-900">
              {contest.pre_game_stats.mean_score.toFixed(1)}
            </div>
          </div>
        )}

        <div className="bg-purple-50 p-3 rounded">
          <div className="text-xs text-purple-600 font-medium mb-1">Updates</div>
          <div className="text-lg font-bold text-purple-900">
            {contest.update_count}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Clock className="w-3 h-3" />
        Last update: {formatDate(contest.last_update)}
      </div>
    </div>
  );
}
